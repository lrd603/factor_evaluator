"""Static-weight factor combination."""

from collections.abc import Mapping

import pandas as pd


def normalize_weights(weights: Mapping[str, float]) -> dict[str, float]:
    """Normalize weights by the sum of their absolute values."""
    denominator = sum(abs(float(value)) for value in weights.values())
    if denominator <= 0:
        raise ValueError("At least one weight must be non-zero")
    return {name: float(value) / denominator for name, value in weights.items()}


def combine_static_weight(values: pd.DataFrame, weights: Mapping[str, float]) -> pd.Series:
    """Combine factor columns with automatically normalized static weights."""
    normalized = normalize_weights(weights)
    available = {name: weight for name, weight in normalized.items() if name in values.columns}
    if not available:
        return pd.Series(float("nan"), index=values.index, name="score")
    # Re-normalize after unavailable factors are omitted.
    available = normalize_weights(available)
    weighted = values[list(available)].mul(pd.Series(available), axis=1)
    denominator = values[list(available)].notna().mul(pd.Series(available).abs(), axis=1).sum(axis=1)
    return weighted.sum(axis=1, min_count=1) / denominator.where(denominator > 0)
