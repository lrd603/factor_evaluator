"""Leakage-safe rolling IC and ICIR factor weights."""

from __future__ import annotations

from typing import Literal

import pandas as pd


def calculate_rolling_weights(
    daily_ic: pd.DataFrame,
    method: Literal["rolling_ic", "rolling_icir"] = "rolling_ic",
    lookback: int = 252,
    min_history: int = 60,
) -> pd.DataFrame:
    """Estimate date-t weights exclusively from IC observations through t-1."""
    required = {"date", "factor_name", "ic"}
    missing = required - set(daily_ic.columns)
    if missing:
        raise ValueError(f"Daily IC data is missing columns: {sorted(missing)}")
    if method not in {"rolling_ic", "rolling_icir"}:
        raise ValueError("method must be 'rolling_ic' or 'rolling_icir'")
    if lookback <= 0 or min_history <= 0 or min_history > lookback:
        raise ValueError("require 0 < min_history <= lookback")
    data = daily_ic.copy(); data["date"] = pd.to_datetime(data["date"])
    wide = data.pivot_table(index="date", columns="factor_name", values="ic").sort_index()
    historical = wide.shift(1)
    mean = historical.rolling(lookback, min_periods=min_history).mean()
    signal = mean
    if method == "rolling_icir":
        std = historical.rolling(lookback, min_periods=min_history).std(ddof=1)
        signal = mean / std.where(std.abs() > 1e-12)
    weights = signal.div(signal.abs().sum(axis=1).replace(0, pd.NA), axis=0)
    fallback = pd.DataFrame(1 / len(wide.columns), index=wide.index, columns=wide.columns)
    weights = weights.where(weights.notna().any(axis=1), fallback).fillna(0.0)
    return weights.stack().rename("weight").reset_index()


def rolling_ic_weight(daily_ic: pd.DataFrame, lookback: int = 252, min_history: int = 60) -> pd.DataFrame:
    """Convenience wrapper for rolling mean-IC weights."""
    return calculate_rolling_weights(daily_ic, "rolling_ic", lookback, min_history)


def rolling_icir_weight(daily_ic: pd.DataFrame, lookback: int = 252, min_history: int = 60) -> pd.DataFrame:
    """Convenience wrapper for rolling ICIR weights."""
    return calculate_rolling_weights(daily_ic, "rolling_icir", lookback, min_history)
