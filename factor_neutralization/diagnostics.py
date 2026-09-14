"""Diagnostics that verify neutralization reduces observable exposures."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _industry_r2(values: pd.Series, industry: pd.Series) -> float:
    valid = values.notna() & industry.notna()
    if valid.sum() < 3 or industry[valid].nunique() < 2:
        return float("nan")
    x = pd.concat([pd.Series(1.0, index=values[valid].index, name="intercept"), pd.get_dummies(industry[valid], drop_first=True, dtype=float)], axis=1).to_numpy()
    y = values[valid].to_numpy(dtype=float)
    fitted = x @ np.linalg.lstsq(x, y, rcond=None)[0]
    total = ((y - y.mean()) ** 2).sum()
    return float(1 - ((y - fitted) ** 2).sum() / total) if total > 1e-12 else 0.0


def neutralization_diagnostics(
    data: pd.DataFrame,
    before_col: str = "normalized_value",
    after_col: str = "neutralized_value",
) -> pd.DataFrame:
    """Report average before/after size correlation and industry explanatory R²."""
    rows = []
    for factor, factor_data in data.groupby("factor_name", sort=True):
        daily = []
        for _, group in factor_data.groupby("date"):
            log_cap = np.log(pd.to_numeric(group.get("market_cap"), errors="coerce")) if "market_cap" in group else pd.Series(np.nan, index=group.index)
            industry = group.get("industry", pd.Series(pd.NA, index=group.index))
            daily.append({
                "before_size_corr": pd.to_numeric(group[before_col], errors="coerce").corr(log_cap),
                "after_size_corr": pd.to_numeric(group[after_col], errors="coerce").corr(log_cap),
                "before_industry_R2": _industry_r2(pd.to_numeric(group[before_col], errors="coerce"), industry),
                "after_industry_R2": _industry_r2(pd.to_numeric(group[after_col], errors="coerce"), industry),
            })
        means = pd.DataFrame(daily).mean()
        rows.append({"factor_name": factor, **means.to_dict()})
    return pd.DataFrame(rows)
