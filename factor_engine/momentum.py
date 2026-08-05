"""Price momentum factors."""

from __future__ import annotations

import pandas as pd


def calculate_momentum(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of *data* with 20-day and 60-day momentum columns."""
    if "close" not in data.columns:
        raise ValueError("Price data must include a 'close' column")

    result = data.copy()
    close = pd.to_numeric(result["close"], errors="raise")
    result["momentum_20"] = close / close.shift(20) - 1
    result["momentum_60"] = close / close.shift(60) - 1
    return result
