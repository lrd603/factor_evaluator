"""Point-in-time alignment of fundamental observations to factor dates."""

from __future__ import annotations

import pandas as pd


def align_fundamentals_point_in_time(
    factor_dates: pd.DataFrame,
    fundamentals: pd.DataFrame,
    announcement_col: str = "announcement_date",
) -> pd.DataFrame:
    """As-of join each stock using only announcements available by factor date."""
    required_left = {"date", "stock"}
    missing = required_left - set(factor_dates.columns)
    if missing:
        raise ValueError(f"Factor dates are missing columns: {sorted(missing)}")
    if announcement_col not in fundamentals:
        result = factor_dates.copy()
        result["point_in_time_available"] = False
        result["data_quality"] = "missing_announcement_date"
        return result
    left = factor_dates.copy(); right = fundamentals.copy()
    left["date"] = pd.to_datetime(left["date"])
    right[announcement_col] = pd.to_datetime(right[announcement_col], errors="coerce")
    left["stock"] = left["stock"].astype(str); right["stock"] = right["stock"].astype(str)
    pieces = []
    for stock, dates in left.groupby("stock", sort=False):
        observations = right[right["stock"] == stock].dropna(subset=[announcement_col]).sort_values(announcement_col)
        merged = pd.merge_asof(
            dates.sort_values("date"), observations.drop(columns="stock"),
            left_on="date", right_on=announcement_col, direction="backward",
        )
        merged["stock"] = stock; pieces.append(merged)
    result = pd.concat(pieces, ignore_index=True) if pieces else left
    result["available_date"] = result.get(announcement_col)
    result["factor_date"] = result["date"]
    result["point_in_time_available"] = True
    result["data_quality"] = "announcement_date_asof"
    return result.sort_values(["date", "stock"]).reset_index(drop=True)


def build_point_in_time_fundamental_panel(
    factor_dates: pd.DataFrame, fundamentals: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Join daily PE/PB by market date and accounting factors by announcement date."""
    dates = factor_dates[["date", "stock"]].copy()
    dates["date"] = pd.to_datetime(dates["date"])
    raw = fundamentals.copy(); raw["stock"] = raw["stock"].astype(str)
    daily_columns = [column for column in ["pe", "pb"] if column in raw]
    if daily_columns:
        valuation = raw[["date", "stock", *daily_columns]].copy()
        valuation["date"] = pd.to_datetime(valuation["date"])
        panel = dates.merge(valuation, on=["date", "stock"], how="left")
    else:
        panel = dates.copy()
    accounting_columns = [column for column in ["report_period", "announcement_date", "roe"] if column in raw]
    if "roe" in accounting_columns:
        aligned = align_fundamentals_point_in_time(dates, raw[["stock", *accounting_columns]])
        keep = [column for column in aligned if column not in {"date", "stock"}]
        panel = panel.merge(aligned[["date", "stock", *keep]], on=["date", "stock"], how="left")
    rows = []
    for factor, source, pit in [("PE", "daily_market_valuation", True), ("PB", "daily_market_valuation", True), ("ROE", "accounting_announcement_asof", "announcement_date" in raw)]:
        column = factor.lower()
        if column not in panel: continue
        values = pd.to_numeric(panel[column], errors="coerce")
        rows.append({"factor": factor, "point_in_time_available": bool(pit), "source": source, "latest_valid_date": panel.loc[values.notna(), "date"].max() if values.notna().any() else pd.NaT, "missing_ratio": float(values.isna().mean())})
    return panel.sort_values(["date", "stock"]), pd.DataFrame(rows)
