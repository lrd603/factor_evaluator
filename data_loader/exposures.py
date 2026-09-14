"""Market-cap and industry exposure construction with explicit PIT quality."""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def build_exposures(market: pd.DataFrame, industry: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    """Build daily exposures without presenting current classifications as historical."""
    result = market.copy(); quality = {"warnings": []}
    if "market_cap" in result:
        quality["market_cap_point_in_time"] = bool(result.get("market_cap_point_in_time", True).all())
        quality["market_cap_source"] = "source_field"
    elif "shares_outstanding" in result:
        result["market_cap"] = pd.to_numeric(result["close"], errors="coerce") * pd.to_numeric(result["shares_outstanding"], errors="coerce")
        pit = bool(result.get("shares_outstanding_point_in_time", False).all()) if "shares_outstanding_point_in_time" in result else False
        quality["market_cap_point_in_time"] = pit
        quality["market_cap_source"] = "close_times_shares_outstanding"
        if not pit: quality["warnings"].append("market_cap_not_point_in_time")
    else:
        result["market_cap"] = pd.NA; quality["market_cap_point_in_time"] = False
        quality["market_cap_source"] = "unavailable"; quality["warnings"].append("market_cap_unavailable")
        logger.warning("market cap unavailable; size neutralization will fall back")
    if "industry" in result:
        quality["industry_point_in_time"] = bool(result.get("industry_point_in_time", True).all())
    elif industry is not None and {"stock", "industry"}.issubset(industry.columns):
        if "effective_date" in industry:
            pieces = []
            for stock, group in result.groupby("stock", sort=False):
                mapping = industry[industry.stock.astype(str) == str(stock)].copy()
                mapping["effective_date"] = pd.to_datetime(mapping["effective_date"])
                pieces.append(pd.merge_asof(group.sort_values("date"), mapping[["effective_date", "industry"]].sort_values("effective_date"), left_on="date", right_on="effective_date", direction="backward"))
            result = pd.concat(pieces, ignore_index=True); quality["industry_point_in_time"] = True
        else:
            quality["industry_point_in_time"] = False; quality["warnings"].append("industry_point_in_time_unavailable")
            logger.warning("current industry mapping not backfilled into history")
            result["industry"] = pd.NA
    else:
        result["industry"] = pd.NA; quality["industry_point_in_time"] = False
        quality["warnings"].append("industry_unavailable")
    return result, quality
