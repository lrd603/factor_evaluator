"""Point-in-time-safe preprocessing for long-form factor observations."""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd


WinsorMethod = Literal["percentile", "mad", "none"]


def winsorize_factor(
    values: pd.Series,
    method: WinsorMethod = "percentile",
    lower_percentile: float = 0.01,
    upper_percentile: float = 0.99,
    mad_k: float = 3.0,
) -> pd.Series:
    """Clip one cross-section while preserving its index and missing values."""
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.dropna()
    if valid.empty or method == "none":
        return numeric
    if method == "percentile":
        if not 0 <= lower_percentile <= upper_percentile <= 1:
            raise ValueError("percentiles must satisfy 0 <= lower <= upper <= 1")
        lower, upper = valid.quantile([lower_percentile, upper_percentile])
    elif method == "mad":
        if mad_k < 0:
            raise ValueError("mad_k must be non-negative")
        median = valid.median()
        mad = (valid - median).abs().median()
        lower, upper = median - mad_k * mad, median + mad_k * mad
    else:
        raise ValueError("method must be 'percentile', 'mad', or 'none'")
    return numeric.clip(lower=lower, upper=upper)


def cross_sectional_zscore(
    data: pd.DataFrame,
    value_col: str = "factor_value",
    date_col: str = "date",
) -> pd.Series:
    """Standardize values using only other observations from the same date."""
    values = pd.to_numeric(data[value_col], errors="coerce")
    grouped = values.groupby(data[date_col], sort=False)
    means = grouped.transform("mean")
    stds = grouped.transform(lambda x: x.std(ddof=0))
    result = (values - means) / stds.where(stds.abs() > 1e-12)
    return result.fillna(0.0).where(values.notna(), np.nan)


def percentile_rank_cross_sectional(
    data: pd.DataFrame,
    value_col: str = "factor_value",
    date_col: str = "date",
) -> pd.Series:
    """Map each daily cross-section to percentile ranks on the 0-100 scale."""
    values = pd.to_numeric(data[value_col], errors="coerce")
    return values.groupby(data[date_col], sort=False).rank(method="average", pct=True) * 100


def preprocess_factors(
    data: pd.DataFrame,
    normalization_method: str = "cross_sectional_zscore",
    winsor_method: WinsorMethod = "percentile",
    value_col: str = "factor_value",
) -> pd.DataFrame:
    """Winsorize and normalize each date-factor cross-section without look-ahead."""
    required = {"date", "factor_name", value_col}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Factor data is missing columns: {sorted(missing)}")
    result = data.copy()
    result[value_col] = pd.to_numeric(result[value_col], errors="coerce")
    keys = [result["date"], result["factor_name"]]
    result["winsorized_value"] = result[value_col].groupby(keys, sort=False).transform(
        lambda x: winsorize_factor(x, method=winsor_method)
    )
    if normalization_method == "cross_sectional_zscore":
        groups = result["winsorized_value"].groupby([result["date"], result["factor_name"]], sort=False)
        means = groups.transform("mean")
        stds = groups.transform(lambda x: x.std(ddof=0))
        result["normalized_value"] = (
            (result["winsorized_value"] - means) / stds.where(stds.abs() > 1e-12)
        ).fillna(0.0).where(result["winsorized_value"].notna(), np.nan)
    elif normalization_method == "cross_sectional_percentile":
        result["normalized_value"] = result["winsorized_value"].groupby(
            [result["date"], result["factor_name"]], sort=False
        ).rank(method="average", pct=True) * 100
    elif normalization_method == "time_series_percentile":
        result["normalized_value"] = result.groupby(["stock", "factor_name"], sort=False)[value_col].rank(
            method="average", pct=True
        ) * 100
    else:
        raise ValueError(f"Unknown normalization_method: {normalization_method}")
    return result
