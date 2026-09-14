"""Derive auditable daily A-share trading metadata from available fields."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _price_limit_rate(stock: pd.Series, is_st: pd.Series) -> pd.Series:
    """Return simplified prevailing board limit rates; IPO exceptions are excluded."""
    codes = stock.astype(str).str.zfill(6)
    rates = pd.Series(0.10, index=stock.index)
    rates.loc[codes.str.startswith(("300", "301", "688"))] = 0.20
    rates.loc[codes.str.startswith(("8", "4"))] = 0.30
    rates.loc[is_st.fillna(False)] = 0.05
    return rates


def enrich_market_metadata(data: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Add amount, suspension and conservative limit flags with quality metadata."""
    result = data.copy().sort_values(["stock", "date"])
    result["date"] = pd.to_datetime(result["date"])
    quality = {"warnings": []}
    if "amount" not in result:
        result["amount"] = pd.to_numeric(result["close"], errors="coerce") * pd.to_numeric(result["volume"], errors="coerce")
        quality["amount_source"] = "close_times_volume_proxy"
        quality["warnings"].append("amount_approximated")
        logger.warning("amount unavailable; using close*volume proxy")
    else:
        quality["amount_source"] = "source_field"
    if "is_st" not in result:
        if "stock_name" in result:
            result["is_st"] = result["stock_name"].astype(str).str.upper().str.contains(r"\*?ST", regex=True)
            quality["st_point_in_time"] = bool(result.get("stock_name_point_in_time", False).all()) if "stock_name_point_in_time" in result else False
        else:
            result["is_st"] = False; quality["st_point_in_time"] = False
            quality["warnings"].append("st_history_unavailable")
    else:
        quality["st_point_in_time"] = True
    if "is_suspended" not in result:
        volume_zero = pd.to_numeric(result["volume"], errors="coerce").fillna(0).eq(0)
        amount_zero = pd.to_numeric(result["amount"], errors="coerce").fillna(0).eq(0)
        ohlc_missing = result[[column for column in ["open", "high", "low", "close"] if column in result]].isna().all(axis=1)
        result["is_suspended"] = volume_zero & amount_zero & ohlc_missing
        quality["suspension_source"] = "conservative_zero_volume_amount_and_missing_ohlc"
        quality["warnings"].append("explicit_suspension_status_unavailable")
    else:
        quality["suspension_source"] = "source_field"
    previous_close = pd.to_numeric(result["close"], errors="coerce").groupby(result["stock"]).shift(1)
    rate = _price_limit_rate(result["stock"], result["is_st"])
    if "limit_up_price" not in result:
        result["limit_up_price"] = (previous_close * (1 + rate)).round(2)
        result["limit_down_price"] = (previous_close * (1 - rate)).round(2)
        quality["limit_price_source"] = "board_rule_approximation"
        quality["warnings"].extend(["limit_price_approximated", "ipo_limit_rules_unavailable"])
    else:
        quality["limit_price_source"] = "source_field"
    # Touching a limit is not automatically untradable. A one-price bar is the conservative proxy.
    one_price = result.get("high", result["close"]).eq(result.get("low", result["close"]))
    result["limit_up"] = result.get("limit_up", one_price & result["close"].ge(result["limit_up_price"] - 1e-9))
    result["limit_down"] = result.get("limit_down", one_price & result["close"].le(result["limit_down_price"] + 1e-9))
    quality["limit_execution_model"] = "one_price_bar_only"
    return result, quality
