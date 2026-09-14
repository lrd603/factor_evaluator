"""Cross-sectional quantile, IC-decay, significance, and correlation research."""

from __future__ import annotations

from math import erf, sqrt

import numpy as np
import pandas as pd


def calculate_forward_returns(
    prices: pd.DataFrame,
    periods: list[int] | tuple[int, ...] = (1, 5, 10, 20, 40),
    price_col: str = "close",
) -> pd.DataFrame:
    """Add close-to-future-close returns per stock for each requested horizon."""
    required = {"date", "stock", price_col}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Price data is missing columns: {sorted(missing)}")
    if any(not isinstance(period, int) or period <= 0 for period in periods):
        raise ValueError("periods must contain positive integers")
    result = prices.copy().sort_values(["stock", "date"])
    current = pd.to_numeric(result[price_col], errors="coerce")
    for period in periods:
        future = current.groupby(result["stock"], sort=False).shift(-period)
        result[f"forward_return_{period}d"] = future / current - 1
    return result.sort_index()


def assign_quantiles(values: pd.Series, quantiles: int = 5) -> pd.Series:
    """Assign robust 1..N quantiles; ties and small cross-sections do not fail."""
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.dropna()
    output = pd.Series(pd.NA, index=values.index, dtype="Int64")
    if valid.empty:
        return output
    ranks = valid.rank(method="first", pct=True)
    output.loc[valid.index] = np.ceil(ranks * quantiles).clip(1, quantiles).astype(int)
    return output


def calculate_quantile_returns(
    data: pd.DataFrame,
    value_col: str = "directed_value",
    return_col: str = "return",
    quantiles: int = 5,
) -> pd.DataFrame:
    """Calculate daily mean forward returns for ordered factor quantiles."""
    required = {"date", value_col, return_col}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Factor data is missing columns: {sorted(missing)}")
    work = data.copy()
    work["quantile"] = work.groupby("date", sort=False)[value_col].transform(
        lambda x: assign_quantiles(x, quantiles)
    )
    daily = work.dropna(subset=["quantile", return_col]).groupby(
        ["date", "quantile"], observed=True
    )[return_col].mean().unstack("quantile")
    daily = daily.reindex(columns=range(1, quantiles + 1))
    daily.columns = [f"Q{i}" for i in range(1, quantiles + 1)]
    daily["Q5-Q1"] = daily[f"Q{quantiles}"] - daily["Q1"]
    return daily


def calculate_daily_ic_series(
    data: pd.DataFrame, value_col: str, return_col: str, method: str = "pearson"
) -> pd.Series:
    """Calculate a daily cross-sectional Pearson or Spearman IC series."""
    if method not in {"pearson", "spearman"}:
        raise ValueError("method must be 'pearson' or 'spearman'")
    def correlate(group: pd.DataFrame) -> float:
        clean = group[[value_col, return_col]].dropna()
        if len(clean) < 2 or clean[value_col].nunique() < 2 or clean[return_col].nunique() < 2:
            return float("nan")
        return float(clean[value_col].corr(clean[return_col], method=method))
    return data.groupby("date", sort=True).apply(correlate).dropna()


def summarize_ic(ic: pd.Series, rank_ic: pd.Series) -> dict[str, float | int]:
    """Summarize IC sequences including conventional two-sided t statistics."""
    ic, rank_ic = pd.Series(ic).dropna(), pd.Series(rank_ic).dropna()
    mean, std, count = float(ic.mean()), float(ic.std(ddof=1)), len(ic)
    rank_mean, rank_std = float(rank_ic.mean()), float(rank_ic.std(ddof=1))
    t_stat = mean / (std / sqrt(count)) if count > 1 and std > 1e-12 else 0.0
    # Normal approximation avoids adding scipy solely for a p-value.
    p_value = 2 * (1 - 0.5 * (1 + erf(abs(t_stat) / sqrt(2))))
    return {
        "mean_ic": mean, "mean_rank_ic": rank_mean,
        "ic_std": std, "rank_ic_std": rank_std,
        "icir": mean / std if std > 1e-12 else 0.0,
        "rank_icir": rank_mean / rank_std if rank_std > 1e-12 else 0.0,
        "positive_ic_ratio": float((ic > 0).mean()) if count else float("nan"),
        "t_stat": t_stat, "p_value": p_value, "observations": count,
    }


def analyze_ic_decay(
    data: pd.DataFrame,
    periods: list[int] | tuple[int, ...] = (1, 5, 10, 20, 40),
    value_col: str = "directed_value",
) -> pd.DataFrame:
    """Compute Pearson and rank IC statistics by factor and holding period."""
    rows = []
    for factor, group in data.groupby("factor_name", sort=True):
        for period in periods:
            return_col = f"forward_return_{period}d"
            if return_col not in group:
                continue
            ic = calculate_daily_ic_series(group, value_col, return_col)
            rank_ic = calculate_daily_ic_series(group, value_col, return_col, "spearman")
            rows.append({"factor_name": factor, "period": period, **summarize_ic(ic, rank_ic)})
    return pd.DataFrame(rows)


def average_factor_correlations(
    data: pd.DataFrame, value_col: str = "directed_value"
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Average daily cross-sectional factor correlations and flag abs > 0.8."""
    wide = data.pivot_table(index=["date", "stock"], columns="factor_name", values=value_col)
    pearsons, spearmans = [], []
    for _, daily in wide.groupby(level="date"):
        cross_section = daily.droplevel("date")
        pearsons.append(cross_section.corr(method="pearson"))
        spearmans.append(cross_section.corr(method="spearman"))
    if not pearsons:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(columns=["factor_1", "factor_2", "correlation"])
    pearson = sum(matrix.fillna(0) for matrix in pearsons) / len(pearsons)
    spearman = sum(matrix.fillna(0) for matrix in spearmans) / len(spearmans)
    redundant = []
    for row, first in enumerate(spearman.columns):
        for second in spearman.columns[row + 1:]:
            value = spearman.loc[first, second]
            if abs(value) > 0.8:
                redundant.append({"factor_1": first, "factor_2": second, "correlation": value})
    return pearson, spearman, pd.DataFrame(redundant)
