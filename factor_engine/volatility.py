"""Historical volatility factors."""

from __future__ import annotations

import pandas as pd


def calculate_volatility(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of *data* with 20-day and 60-day return volatility."""
    if "close" not in data.columns:
        raise ValueError("Price data must include a 'close' column")

    result = data.copy()
    close = pd.to_numeric(result["close"], errors="raise")
    returns = close.pct_change(fill_method=None)
    result["volatility_20"] = returns.rolling(20, min_periods=20).std()
    result["volatility_60"] = returns.rolling(60, min_periods=60).std()
    return result
