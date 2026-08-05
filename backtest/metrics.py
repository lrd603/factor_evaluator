"""Performance and risk metrics for daily portfolio returns."""

from __future__ import annotations

import math

import pandas as pd


TRADING_DAYS = 252


def calculate_total_return(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    return float((1 + clean).prod() - 1) if not clean.empty else 0.0


def calculate_annual_return(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    growth = float((1 + clean).prod())
    if growth <= 0:
        return -1.0
    return growth ** (TRADING_DAYS / len(clean)) - 1


def calculate_sharpe_ratio(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    volatility = float(clean.std(ddof=1)) if len(clean) > 1 else 0.0
    return float(clean.mean() / volatility * math.sqrt(TRADING_DAYS)) if volatility else 0.0


def calculate_max_drawdown(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    if clean.empty:
        return 0.0
    wealth = (1 + clean).cumprod()
    return float((wealth / wealth.cummax() - 1).min())


def calculate_win_rate(returns: pd.Series) -> float:
    clean = pd.to_numeric(returns, errors="coerce").dropna()
    return float((clean > 0).mean()) if not clean.empty else 0.0


def calculate_information_ratio(
    returns: pd.Series, benchmark_returns: pd.Series | None = None
) -> float:
    clean = pd.to_numeric(returns, errors="coerce")
    if benchmark_returns is None:
        active = clean.dropna()
    else:
        benchmark = pd.to_numeric(benchmark_returns, errors="coerce")
        aligned = pd.concat([clean, benchmark], axis=1).dropna()
        active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    tracking_error = float(active.std(ddof=1)) if len(active) > 1 else 0.0
    return float(active.mean() / tracking_error * math.sqrt(TRADING_DAYS)) if tracking_error else 0.0


def calculate_backtest_metrics(
    returns: pd.Series, benchmark_returns: pd.Series | None = None
) -> dict[str, float]:
    """Calculate the five metrics required by the V4 backtest report."""
    strategy_return = calculate_total_return(returns)
    benchmark_return = (
        calculate_total_return(benchmark_returns) if benchmark_returns is not None else 0.0
    )
    return {
        "Strategy Return": strategy_return,
        "Benchmark Return": benchmark_return,
        "Alpha": strategy_return - benchmark_return,
        "Annual Return": calculate_annual_return(returns),
        "Sharpe Ratio": calculate_sharpe_ratio(returns),
        "Max Drawdown": calculate_max_drawdown(returns),
        "Win Rate": calculate_win_rate(returns),
        "Information Ratio": calculate_information_ratio(returns, benchmark_returns),
    }
