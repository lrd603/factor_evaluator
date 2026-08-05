"""Quality factors derived from profitability metrics."""

from __future__ import annotations

import pandas as pd


def calculate_quality_factor(data: pd.DataFrame) -> pd.DataFrame:
    """Add an ROE factor where higher profitability is better."""
    if "roe" not in data.columns:
        raise ValueError("Financial data must include an 'roe' column")
    result = data.copy()
    result["roe_factor"] = pd.to_numeric(result["roe"], errors="raise")
    return result
