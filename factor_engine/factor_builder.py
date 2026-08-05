"""Build evaluator-compatible long-form factor data from daily prices."""

from __future__ import annotations

import re

import pandas as pd

from .momentum import calculate_momentum
from .volatility import calculate_volatility
from .volume_factor import calculate_volume_factor


PRICE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
FACTOR_COLUMNS = [
    "momentum_20",
    "momentum_60",
    "volatility_20",
    "volatility_60",
    "volume_change_20",
]
OUTPUT_COLUMNS = ["date", "stock", "factor_name", "factor_value", "return"]


def _normalize_stock_code(value: object) -> str:
    code = str(value).strip()
    if code.endswith(".0") and code[:-2].isdigit():
        code = code[:-2]
    code = code.zfill(6)
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError(f"Invalid A-share stock code: {value!r}")
    return code


def _prepare_prices(data: pd.DataFrame, stock_code: str | None) -> pd.DataFrame:
    if data is None or data.empty:
        raise ValueError("Price data must not be empty")
    missing = set(PRICE_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"Price data is missing columns: {sorted(missing)}")

    result = data.copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    for column in PRICE_COLUMNS[1:]:
        result[column] = pd.to_numeric(result[column], errors="raise")
    if (result["close"] <= 0).any():
        raise ValueError("close must be greater than zero")
    if (result["volume"] < 0).any():
        raise ValueError("volume must not be negative")

    if "stock" in result.columns:
        result["stock"] = result["stock"].map(_normalize_stock_code)
    else:
        inferred_code = stock_code or data.attrs.get("stock_code")
        if inferred_code is None:
            raise ValueError(
                "stock_code is required when price data has no 'stock' column or stock_code attribute"
            )
        result["stock"] = _normalize_stock_code(inferred_code)

    if result.duplicated(["date", "stock"]).any():
        raise ValueError("Price data contains duplicate date-stock rows")
    return result.sort_values(["stock", "date"]).reset_index(drop=True)


def _calculate_one_stock(data: pd.DataFrame, forward_period: int) -> pd.DataFrame:
    calculated = calculate_momentum(data)
    calculated = calculate_volatility(calculated)
    calculated = calculate_volume_factor(calculated)
    calculated["return"] = (
        calculated["close"].shift(-forward_period) / calculated["close"] - 1
    )
    return calculated


def build_factor_data(
    data: pd.DataFrame,
    stock_code: str | None = None,
    forward_period: int = 5,
) -> pd.DataFrame:
    """Create the long-form factor input expected by the existing evaluator."""
    if not isinstance(forward_period, int) or forward_period <= 0:
        raise ValueError("forward_period must be a positive integer")

    prices = _prepare_prices(data, stock_code)
    frames = [
        _calculate_one_stock(group.copy(), forward_period)
        for _, group in prices.groupby("stock", sort=True)
    ]
    calculated = pd.concat(frames, ignore_index=True)
    factor_data = calculated.melt(
        id_vars=["date", "stock", "return"],
        value_vars=FACTOR_COLUMNS,
        var_name="factor_name",
        value_name="factor_value",
    )
    factor_data = factor_data.dropna(subset=["factor_value", "return"])
    factor_data["date"] = factor_data["date"].dt.strftime("%Y-%m-%d")
    return factor_data[OUTPUT_COLUMNS].sort_values(
        ["date", "stock", "factor_name"], kind="stable"
    ).reset_index(drop=True)
