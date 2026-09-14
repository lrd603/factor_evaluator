"""Expanding and rolling walk-forward evaluation without parameter leakage."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

import numpy as np
import pandas as pd

from factor_analysis.research import calculate_daily_ic_series
from factor_combination.static_weight import normalize_weights


@dataclass(frozen=True)
class WalkForwardConfig:
    """Trading-day window configuration for walk-forward folds."""

    mode: str = "rolling"
    train_window: int = 756
    test_window: int = 126
    min_train: int = 252
    transaction_cost: float = 0.001


def build_walk_forward_folds(dates: pd.Series | pd.Index, config: WalkForwardConfig | None = None) -> list[dict]:
    """Build strictly non-overlapping train/test folds from sorted trading dates."""
    settings = config or WalkForwardConfig()
    unique = pd.DatetimeIndex(pd.to_datetime(pd.Series(dates).dropna().unique())).sort_values()
    folds = []
    test_start = settings.min_train
    while test_start < len(unique):
        train_start = 0 if settings.mode == "expanding" else max(0, test_start - settings.train_window)
        train = unique[train_start:test_start]
        test = unique[test_start:min(test_start + settings.test_window, len(unique))]
        if len(train) >= settings.min_train and len(test):
            folds.append({"train_start": train[0], "train_end": train[-1], "test_start": test[0], "test_end": test[-1]})
        test_start += settings.test_window
    if settings.mode not in {"rolling", "expanding"}:
        raise ValueError("mode must be 'rolling' or 'expanding'")
    return folds


def _estimate_weights(train: pd.DataFrame, method: str, value_col: str, return_col: str) -> dict[str, float]:
    factors = sorted(train["factor_name"].unique())
    if method == "equal_weight":
        return {factor: 1 / len(factors) for factor in factors}
    if method == "static_weight":
        supplied = train.attrs.get("static_weights", {factor: 1.0 for factor in factors})
        return normalize_weights({factor: supplied.get(factor, 0.0) for factor in factors})
    signals = {}
    for factor, group in train.groupby("factor_name"):
        series = calculate_daily_ic_series(group, value_col, return_col)
        if method == "rolling_ic_weight":
            signals[factor] = float(series.mean())
        elif method == "rolling_icir_weight":
            std = float(series.std(ddof=1)); signals[factor] = float(series.mean()) / std if std > 1e-12 else 0.0
        else:
            raise ValueError(f"Unknown strategy method: {method}")
    if not signals or sum(abs(value) for value in signals.values()) <= 1e-12:
        return {factor: 1 / len(factors) for factor in factors}
    return normalize_weights(signals)


def _metrics(returns: pd.Series, benchmark: pd.Series, turnover: pd.Series, costs: pd.Series) -> dict[str, float]:
    returns = returns.dropna(); benchmark = benchmark.reindex(returns.index).fillna(0)
    volatility = float(returns.std(ddof=1) * sqrt(252)) if len(returns) > 1 else 0.0
    annualized = float((1 + returns).prod() ** (252 / len(returns)) - 1) if len(returns) else 0.0
    excess = returns - benchmark
    return {
        "annualized_return": annualized, "volatility": volatility,
        "sharpe": annualized / volatility if volatility > 1e-12 else 0.0,
        "max_drawdown": float(((1 + returns).cumprod() / (1 + returns).cumprod().cummax() - 1).min()) if len(returns) else 0.0,
        "information_ratio": float(excess.mean() / excess.std(ddof=1) * sqrt(252)) if len(excess) > 1 and excess.std(ddof=1) > 1e-12 else 0.0,
        "turnover": float(turnover.sum()), "transaction_cost": float(costs.sum()),
        "benchmark_excess_return": float(returns.sum() - benchmark.sum()),
    }


def _portfolio_period(data: pd.DataFrame, weights: dict[str, float], value_col: str, return_col: str, transaction_cost: float) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """Evaluate one period with supplied, already-estimated factor weights."""
    wide = data.pivot_table(index=["date", "stock"], columns="factor_name", values=value_col)
    score = wide.mul(pd.Series(weights)).sum(axis=1, min_count=1)
    observations = data.drop_duplicates(["date", "stock"]).set_index(["date", "stock"])[return_col]
    panel = pd.concat([score.rename("score"), observations.rename("return")], axis=1).dropna()
    selected = panel.groupby(level="date")["score"].transform(lambda x: x >= x.quantile(0.8))
    gross = panel[selected].groupby(level="date")["return"].mean()
    benchmark = panel.groupby(level="date")["return"].mean()
    holdings = panel[selected].reset_index().groupby("date")["stock"].agg(lambda x: frozenset(x))
    turnover = holdings.combine(holdings.shift(), lambda a, b: 1.0 if not isinstance(b, frozenset) else len(a.symmetric_difference(b)) / max(len(a) + len(b), 1)).fillna(1.0)
    costs = turnover * transaction_cost
    return gross - costs.reindex(gross.index).fillna(0), benchmark, turnover, costs


def run_walk_forward(
    data: pd.DataFrame,
    methods: tuple[str, ...] = ("equal_weight", "static_weight", "rolling_ic_weight", "rolling_icir_weight"),
    config: WalkForwardConfig | None = None,
    value_col: str = "directed_value",
    return_col: str = "forward_return_1d",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run fixed-within-fold parameter estimates and combine true OOS returns."""
    settings = config or WalkForwardConfig()
    work = data.copy(); work["date"] = pd.to_datetime(work["date"])
    folds = build_walk_forward_folds(work["date"], settings)
    fold_rows, return_rows = [], []
    for fold_id, fold in enumerate(folds):
        train = work[(work.date >= fold["train_start"]) & (work.date <= fold["train_end"])]
        test = work[(work.date >= fold["test_start"]) & (work.date <= fold["test_end"])]
        for method in methods:
            weights = _estimate_weights(train, method, value_col, return_col)
            net, benchmark, turnover, costs = _portfolio_period(test, weights, value_col, return_col, settings.transaction_cost)
            metrics = _metrics(net, benchmark, turnover, costs)
            is_net, is_benchmark, is_turnover, is_costs = _portfolio_period(train, weights, value_col, return_col, settings.transaction_cost)
            is_metrics = {f"is_{key}": value for key, value in _metrics(is_net, is_benchmark, is_turnover, is_costs).items()}
            fold_rows.append({"fold": fold_id, "method": method, **fold, **is_metrics, **metrics, "train_weights": weights})
            return_rows.extend({"date": date, "method": method, "fold": fold_id, "return": value} for date, value in net.items())
    returns = pd.DataFrame(return_rows)
    combined = returns.pivot_table(index="date", columns="method", values="return") if not returns.empty else pd.DataFrame()
    summary_rows = []
    for method in methods:
        series = combined[method].dropna() if method in combined else pd.Series(dtype=float)
        benchmark = work.drop_duplicates(["date", "stock"]).groupby("date")[return_col].mean().reindex(series.index)
        subset = pd.DataFrame(fold_rows); subset = subset[subset.method == method] if not subset.empty else subset
        summary_rows.append({"method": method, **_metrics(series, benchmark, pd.Series([subset.turnover.sum()]) if not subset.empty else pd.Series(dtype=float), pd.Series([subset.transaction_cost.sum()]) if not subset.empty else pd.Series(dtype=float))})
    return pd.DataFrame(summary_rows), pd.DataFrame(fold_rows), combined
