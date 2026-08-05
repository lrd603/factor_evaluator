"""Trading-volume factors."""

from __future__ import annotations

import pandas as pd


def calculate_volume_factor(data: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of *data* with volume relative to its 20-day mean."""
    if "volume" not in data.columns:
        raise ValueError("Price data must include a 'volume' column")

    result = data.copy()
    volume = pd.to_numeric(result["volume"], errors="raise")
    average_volume = volume.rolling(20, min_periods=20).mean()
    result["volume_change_20"] = volume / average_volume
    return result
