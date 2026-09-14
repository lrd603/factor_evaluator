"""A small, transparent multi-factor stock-selection backtest engine."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import logging

import pandas as pd

from data_loader.stock_data import load_stock_data
from factor_engine.factor_builder import build_factor_data
from financial_loader.financial_data import load_financial_data
from stock_evaluator import calculate_multifactor_scores
from universe import HistoricalUniverseProvider, UniverseConfig, enforce_trade_constraints

from .metrics import calculate_backtest_metrics
from .portfolio import build_portfolio

logger = logging.getLogger(__name__)


def load_csi300_data(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Load the CSI 300 daily close series through AkShare's Tencent endpoint."""
    import akshare as ak

    raw = ak.stock_zh_index_daily_tx(
        symbol="sh000300",
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
    )
    if raw is None or raw.empty or not {"date", "close"}.issubset(raw.columns):
        raise ValueError("AkShare returned no usable CSI 300 benchmark data")
    result = raw[["date", "close"]].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    result["close"] = pd.to_numeric(result["close"], errors="raise")
    return result.sort_values("date").drop_duplicates("date", keep="last")


class BacktestEngine:
    """Rebalance a top-ranked, equal-weight portfolio every N trading days."""

    def __init__(
        self,
        stocks: list[str],
        start_date: str,
        end_date: str,
        rebalance_period: int = 20,
        top_fraction: float = 0.20,
        mode: str = "long_only",
        transaction_cost: float = 0.001,
        market_loader: Callable = load_stock_data,
        financial_loader: Callable = load_financial_data,
        benchmark_loader: Callable = load_csi300_data,
        universe_provider=None,
        universe_mode: str = "dynamic",
        universe_config: UniverseConfig | None = None,
    ) -> None:
        if not stocks:
            raise ValueError("stocks must not be empty")
        if rebalance_period <= 0:
            raise ValueError("rebalance_period must be positive")
        if transaction_cost < 0:
            raise ValueError("transaction_cost must not be negative")
        self.stocks = list(dict.fromkeys(str(code).strip().zfill(6) for code in stocks))
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be later than end_date")
        self.rebalance_period = rebalance_period
        self.top_fraction = top_fraction
        self.mode = mode
        self.transaction_cost = float(transaction_cost)
        self.market_loader = market_loader
        self.financial_loader = financial_loader
        self.benchmark_loader = benchmark_loader
        if universe_mode not in {"dynamic", "fixed"}:
            raise ValueError("universe_mode must be 'dynamic' or 'fixed'")
        self.universe_mode = universe_mode
        self.universe_provider = universe_provider
        self.universe_config = universe_config or UniverseConfig()
        self.research_metadata = {"universe_mode": universe_mode, "warnings": []}
        self._market_history = pd.DataFrame()

        self.metrics: dict[str, float] = {}
        self.score_history = pd.DataFrame(columns=["date", "stock", "score"])
        self.holdings = pd.DataFrame()
        self.benchmark_returns = pd.Series(dtype=float, name="benchmark_return")
        self.daily_returns = pd.Series(dtype=float, name="portfolio_return")
        self.transaction_costs = pd.Series(dtype=float, name="transaction_cost")

    def _load_inputs(self) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
        close_series = []
        market_frames = []
        factors: dict[str, pd.DataFrame] = {}
        financials: dict[str, pd.DataFrame] = {}
        for code in self.stocks:
            prices = self.market_loader(
                code,
                start_date=self.start_date,
                end_date=self.end_date,
            )
            prices = prices.copy()
            prices["date"] = pd.to_datetime(prices["date"])
            prices = prices.sort_values("date")
            prices["stock"] = code
            market_frames.append(prices)
            close_series.append(prices.set_index("date")["close"].rename(code))
            factors[code] = build_factor_data(prices, stock_code=code)
            financials[code] = self.financial_loader(code)
        closes = pd.concat(close_series, axis=1).sort_index()
        self._market_history = pd.concat(market_frames, ignore_index=True)
        if self.universe_mode == "dynamic" and self.universe_provider is None:
            self.universe_provider = HistoricalUniverseProvider(self._market_history, self.universe_config)
        closes = closes.loc[
            (closes.index >= self.start_date) & (closes.index <= self.end_date)
        ]
        return closes, factors, financials

    def _scores_at_date(
        self,
        current_date: pd.Timestamp,
        factors: dict[str, pd.DataFrame],
        financials: dict[str, pd.DataFrame],
    ) -> pd.Series:
        scores: dict[str, float] = {}
        eligible = set(self.stocks)
        if self.universe_mode == "dynamic":
            eligible = set(self.universe_provider.get_universe(current_date))
            if not eligible:
                warning = "dynamic_universe_empty_insufficient_prelisting_history_fixed_candidate_fallback"
                if warning not in self.research_metadata["warnings"]:
                    logger.warning(warning); self.research_metadata["warnings"].append(warning)
                eligible = set(self.stocks)
        technical_frames = []
        financial_frames = []
        for code in self.stocks:
            if code not in eligible:
                continue
            technical = factors[code].copy()
            technical_dates = pd.to_datetime(technical["date"])
            technical = technical.loc[technical_dates <= current_date]
            financial = financials[code].copy()
            financial_dates = pd.to_datetime(financial["date"])
            financial = financial.loc[financial_dates <= current_date]
            if technical.empty or financial.empty:
                continue
            technical_frames.append(technical)
            financial_frames.append(financial.assign(stock=code))
        if not technical_frames or not financial_frames:
            return pd.Series(dtype=float, name="score")
        technical_universe = pd.concat(technical_frames, ignore_index=True)
        financial_universe = pd.concat(financial_frames, ignore_index=True)
        for code in self.stocks:
            try:
                result = calculate_multifactor_scores(
                    technical_universe, financial_universe, code
                )
            except ValueError:
                continue
            scores[code] = result["final_score"]
        return pd.Series(scores, dtype=float, name="score")

    def run(self) -> pd.Series:
        """Run the backtest and return the daily portfolio return series."""
        closes, factors, financials = self._load_inputs()
        if len(closes) < 66:
            raise ValueError("Backtest requires at least 66 trading days for 60-day factors")

        asset_returns = closes.pct_change(fill_method=None)
        weights = pd.DataFrame(0.0, index=closes.index, columns=closes.columns)
        score_rows = []
        rebalance_dates = closes.index[65:: self.rebalance_period]
        current_weights = pd.Series(dtype=float)
        rebalance_set = set(rebalance_dates)
        for current_date in closes.index:
            if current_date in rebalance_set:
                scores = self._scores_at_date(current_date, factors, financials)
                if not scores.empty:
                    target_weights = build_portfolio(
                        scores, top_fraction=self.top_fraction, mode=self.mode
                    )
                    market_state = self._market_history[pd.to_datetime(self._market_history["date"]) == current_date]
                    current_weights = enforce_trade_constraints(current_weights, target_weights, market_state)
                    score_rows.extend(
                        {"date": current_date, "stock": code, "score": score}
                        for code, score in scores.items()
                    )
            if not current_weights.empty:
                weights.loc[current_date, current_weights.index] = current_weights.values

        # Scores observed at today's close are tradable from the next session.
        effective_weights = weights.shift(1).fillna(0.0)
        gross_returns = (asset_returns * effective_weights).sum(axis=1, min_count=1)
        weight_changes = effective_weights.diff()
        if not weight_changes.empty:
            weight_changes.iloc[0] = effective_weights.iloc[0]
        turnover = weight_changes.abs().sum(axis=1)
        transaction_costs = turnover * self.transaction_cost
        portfolio_returns = gross_returns - transaction_costs
        invested = effective_weights.sum(axis=1) > 0
        self.daily_returns = portfolio_returns.loc[invested].dropna().rename("portfolio_return")
        if self.daily_returns.empty:
            raise ValueError("No portfolio returns were generated from the available scores")

        benchmark = self.benchmark_loader(self.start_date, self.end_date).copy()
        benchmark["date"] = pd.to_datetime(benchmark["date"], errors="raise")
        benchmark_close = benchmark.set_index("date")["close"].sort_index()
        benchmark_daily = benchmark_close.pct_change(fill_method=None)
        self.benchmark_returns = benchmark_daily.reindex(self.daily_returns.index).dropna().rename(
            "benchmark_return"
        )
        if self.benchmark_returns.empty:
            raise ValueError("No CSI 300 benchmark returns overlap the strategy period")
        self.daily_returns = self.daily_returns.reindex(self.benchmark_returns.index)
        self.score_history = pd.DataFrame(score_rows)
        self.holdings = effective_weights.loc[self.daily_returns.index]
        self.transaction_costs = transaction_costs.reindex(self.daily_returns.index).rename(
            "transaction_cost"
        )
        self.metrics = calculate_backtest_metrics(
            self.daily_returns, self.benchmark_returns
        )
        return self.daily_returns

    def generate_report(self, output_path: str | Path = "reports/backtest_report.md") -> Path:
        """Write a Markdown summary after ``run`` has completed."""
        if self.daily_returns.empty or not self.metrics:
            raise RuntimeError("Run the backtest before generating a report")
        stock_pool = ", ".join(self.stocks)
        content = f"""# Backtest Report

## Backtest Period

{self.start_date.date()} to {self.end_date.date()}

## Stock Pool

{stock_pool}

## Portfolio Rules

- Mode: Long-Only
- Universe mode: {self.universe_mode}
- Rebalance: Every {self.rebalance_period} trading days
- Selection: Top {self.top_fraction:.0%}
- Transaction cost: {self.transaction_cost:.2%} of traded notional
- Slippage: Not included

## Return Metrics

- Strategy Return: {self.metrics['Strategy Return']:.2%}
- CSI 300 Benchmark Return: {self.metrics['Benchmark Return']:.2%}
- Alpha: {self.metrics['Alpha']:.2%}
- Annual Return: {self.metrics['Annual Return']:.2%}
- Win Rate: {self.metrics['Win Rate']:.2%}

## Risk Metrics

- Sharpe Ratio: {self.metrics['Sharpe Ratio']:.4f}
- Max Drawdown: {self.metrics['Max Drawdown']:.2%}
- Information Ratio: {self.metrics['Information Ratio']:.4f}
"""
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
        return destination
