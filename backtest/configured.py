"""Configuration-aware entry points around the unchanged backtest engine."""

from __future__ import annotations

from config.stock_pool import get_stock_pool

from .engine import BacktestEngine


def create_configured_backtest(
    start_date: str,
    end_date: str,
    stocks: list[str] | None = None,
    **engine_options,
) -> BacktestEngine:
    """Create a BacktestEngine using the default configured pool when omitted."""
    return BacktestEngine(
        get_stock_pool(stocks), start_date, end_date, **engine_options
    )
