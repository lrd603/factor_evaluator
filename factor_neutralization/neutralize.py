"""Daily OLS neutralization against size and industry exposures."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class NeutralizationConfig:
    """Controls which observable factor exposures are removed."""

    enabled: bool = True
    use_size: bool = True
    use_industry: bool = True
    rezscore: bool = True
    min_observations: int = 5


def _neutralize_group(group: pd.DataFrame, value_col: str, config: NeutralizationConfig) -> pd.DataFrame:
    result = group.copy()
    result["neutralized_value"] = pd.to_numeric(result[value_col], errors="coerce")
    exposure_columns = []
    design = pd.DataFrame({"intercept": 1.0}, index=result.index)
    if config.use_size and "market_cap" in result:
        market_cap = pd.to_numeric(result["market_cap"], errors="coerce")
        design["log_market_cap"] = np.log(market_cap.where(market_cap > 0))
        exposure_columns.append("log_market_cap")
    if config.use_industry and "industry" in result:
        dummies = pd.get_dummies(result["industry"], prefix="industry", drop_first=True, dtype=float)
        design = pd.concat([design, dummies], axis=1)
        exposure_columns.extend(dummies.columns)
    if not exposure_columns:
        result["neutralization_status"] = "missing_requested_exposures"
        return result
    valid = result[value_col].notna() & design.notna().all(axis=1)
    parameter_count = design.shape[1]
    if valid.sum() < max(config.min_observations, parameter_count + 1):
        result["neutralization_status"] = "insufficient_sample_fallback"
        return result
    x = design.loc[valid].astype(float).to_numpy()
    y = pd.to_numeric(result.loc[valid, value_col]).to_numpy(dtype=float)
    coefficients, *_ = np.linalg.lstsq(x, y, rcond=None)
    residuals = y - x @ coefficients
    if config.rezscore:
        std = residuals.std(ddof=0)
        residuals = (residuals - residuals.mean()) / std if std > 1e-12 else np.zeros_like(residuals)
    result.loc[valid, "neutralized_value"] = residuals
    result["neutralization_status"] = "neutralized"
    result.loc[~valid, "neutralization_status"] = "missing_exposure_fallback"
    return result


def neutralize_factors(
    data: pd.DataFrame,
    value_col: str = "normalized_value",
    config: NeutralizationConfig | None = None,
) -> pd.DataFrame:
    """Neutralize each date-factor cross-section and safely preserve fallbacks."""
    settings = config or NeutralizationConfig()
    if not settings.enabled:
        result = data.copy(); result["neutralized_value"] = result[value_col]
        result["neutralization_status"] = "disabled"; return result
    required = {"date", "factor_name", value_col}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Factor data is missing columns: {sorted(missing)}")
    frames = [
        _neutralize_group(group, value_col, settings)
        for _, group in data.groupby(["date", "factor_name"], sort=False)
    ]
    return pd.concat(frames, ignore_index=True) if frames else data.copy()
