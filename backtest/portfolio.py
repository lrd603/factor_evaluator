"""Portfolio construction rules for the simple V4 backtester."""

from __future__ import annotations

import math

import pandas as pd


def build_portfolio(
    scores: pd.Series,
    top_fraction: float = 0.20,
    mode: str = "long_only",
) -> pd.Series:
    """Select the highest-scoring stocks and return equal long-only weights."""
    if mode == "long_short":
        raise NotImplementedError("Long-short portfolio construction is reserved for a future version")
    if mode != "long_only":
        raise ValueError("mode must be 'long_only' or 'long_short'")
    if not 0 < top_fraction <= 1:
        raise ValueError("top_fraction must be in (0, 1]")

    valid_scores = pd.to_numeric(scores, errors="coerce").dropna().sort_values(ascending=False)
    if valid_scores.empty:
        return pd.Series(dtype=float, name="weight")
    count = max(1, math.ceil(len(valid_scores) * top_fraction))
    selected = valid_scores.iloc[:count]
    return pd.Series(1 / count, index=selected.index, name="weight", dtype=float)
