"""Value factors derived from PE and PB ratios."""

from __future__ import annotations

import pandas as pd


def calculate_value_factors(data: pd.DataFrame) -> pd.DataFrame:
    """Add earnings-yield and book-yield factors; higher values are cheaper."""
    missing = {"pe", "pb"} - set(data.columns)
    if missing:
        raise ValueError(f"Financial data is missing columns: {sorted(missing)}")
    result = data.copy()
    pe = pd.to_numeric(result["pe"], errors="raise")
    pb = pd.to_numeric(result["pb"], errors="raise")
    result["pe_factor"] = (1 / pe).where(pe > 0)
    result["pb_factor"] = (1 / pb).where(pb > 0)
    return result
