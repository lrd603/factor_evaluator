"""Transparent filters for data-derived historical universes."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class UniverseConfig:
    """Configurable eligibility rules applied using information at each date."""

    min_listing_days: int = 120
    exclude_st: bool = True
    exclude_suspended: bool = True
    min_adv20: float | None = None


def filter_universe(history: pd.DataFrame, date: object, config: UniverseConfig) -> pd.DataFrame:
    """Return eligible rows on ``date`` using only history through that date."""
    required = {"date", "stock", "close", "volume"}
    missing = required - set(history.columns)
    if missing:
        raise ValueError(f"Universe history is missing columns: {sorted(missing)}")
    cutoff = pd.Timestamp(date)
    data = history.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data = data[data["date"] <= cutoff].sort_values(["stock", "date"])
    if data.empty:
        return data
    data["trading_age"] = data.groupby("stock").cumcount() + 1
    volume = pd.to_numeric(data["volume"], errors="coerce")
    close = pd.to_numeric(data["close"], errors="coerce")
    liquidity = pd.to_numeric(data["amount"], errors="coerce") if "amount" in data else close * volume
    data["adv20"] = liquidity.groupby(data["stock"]).transform(lambda x: x.rolling(20, min_periods=20).mean())
    current = data[data["date"] == cutoff].copy()
    eligible = current["trading_age"] >= config.min_listing_days
    eligible &= current["close"].notna() & current["volume"].notna()
    if config.exclude_suspended:
        eligible &= pd.to_numeric(current["volume"], errors="coerce") > 0
        if "is_suspended" in current:
            eligible &= ~current["is_suspended"].fillna(False).astype(bool)
    if config.exclude_st and "is_st" in current:
        eligible &= ~current["is_st"].fillna(False).astype(bool)
    if config.min_adv20 is not None:
        eligible &= current["adv20"] >= config.min_adv20
    return current.loc[eligible].reset_index(drop=True)


def enforce_trade_constraints(
    previous_weights: pd.Series,
    target_weights: pd.Series,
    market_state: pd.DataFrame,
) -> pd.Series:
    """Block buys/sells when explicit suspension or price-limit flags forbid them."""
    stocks = previous_weights.index.union(target_weights.index)
    previous = previous_weights.reindex(stocks, fill_value=0.0).astype(float)
    target = target_weights.reindex(stocks, fill_value=0.0).astype(float)
    state = market_state.copy()
    if "stock" not in state:
        raise ValueError("market_state must include stock")
    state["stock"] = state["stock"].astype(str)
    state = state.drop_duplicates("stock", keep="last").set_index("stock")
    suspended = state.get("is_suspended", pd.Series(False, index=state.index)).fillna(False)
    if "volume" in state:
        suspended |= pd.to_numeric(state["volume"], errors="coerce").fillna(0).le(0)
    limit_up = state.get("limit_up", pd.Series(False, index=state.index)).fillna(False)
    limit_down = state.get("limit_down", pd.Series(False, index=state.index)).fillna(False)
    is_st = state.get("is_st", pd.Series(False, index=state.index)).fillna(False)
    for stock in stocks:
        blocked = bool(suspended.get(stock, False))
        if target[stock] > previous[stock] and (blocked or bool(limit_up.get(stock, False)) or bool(is_st.get(stock, False))):
            target[stock] = previous[stock]
        elif target[stock] < previous[stock] and (blocked or bool(limit_down.get(stock, False))):
            target[stock] = previous[stock]
    return target
