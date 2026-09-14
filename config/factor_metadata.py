"""Central factor definitions used by preprocessing and score combination."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FactorMetadata:
    """Research metadata for one factor."""

    name: str
    category: str
    higher_is_better: bool
    weight: float = 1.0
    transform: str | None = None


FACTOR_METADATA: dict[str, FactorMetadata] = {
    item.name: item
    for item in [
        FactorMetadata("momentum", "technical", True),
        FactorMetadata("momentum_20", "technical", True),
        FactorMetadata("momentum_60", "technical", True),
        FactorMetadata("volatility", "technical", False),
        FactorMetadata("volatility_20", "technical", False),
        FactorMetadata("volatility_60", "technical", False),
        FactorMetadata("volume_factor", "technical", True),
        FactorMetadata("volume_change_20", "technical", True),
        FactorMetadata("earnings_yield", "value", True),
        FactorMetadata("book_yield", "value", True),
        FactorMetadata("pe_factor", "value", True),
        FactorMetadata("pb_factor", "value", True),
        FactorMetadata("PE", "value", False),
        FactorMetadata("PB", "value", False),
        FactorMetadata("roe", "quality", True),
        FactorMetadata("roe_factor", "quality", True),
        FactorMetadata("ROE", "quality", True),
    ]
}

DEFAULT_NORMALIZATION_METHOD = "cross_sectional_zscore"
CATEGORY_WEIGHTS = {"technical": 0.4, "value": 0.3, "quality": 0.3}


def apply_factor_directions(data, value_col: str = "normalized_value"):
    """Return a copy whose factor values consistently mean higher is better."""
    result = data.copy()
    directions = result["factor_name"].map(
        lambda name: FACTOR_METADATA.get(str(name), FactorMetadata(str(name), "other", True)).higher_is_better
    )
    result[value_col] = result[value_col].where(directions, -result[value_col])
    return result
