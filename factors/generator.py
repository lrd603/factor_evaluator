"""Generate evaluator-compatible factors from raw A-share daily data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


RAW_COLUMNS = ["date", "stock", "open", "high", "low", "close", "volume"]
FORWARD_PERIODS = [1, 5, 10, 20, 40]
FORWARD_COLUMNS = [f"forward_return_{period}d" for period in FORWARD_PERIODS]
OUTPUT_COLUMNS = ["date", "stock", "factor_name", "factor_value", "return", *FORWARD_COLUMNS]
FACTOR_COLUMNS = ["momentum", "volatility", "volume_factor"]


def load_raw_stock_data(input_path: str | Path) -> pd.DataFrame:
    """Load and validate the raw market-data CSV."""
    source = Path(input_path)
    if not source.exists():
        raise FileNotFoundError(f"Raw stock data not found: {source}")

    data = pd.read_csv(source, dtype={"stock": str})
    missing = set(RAW_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(f"Raw stock data is missing columns: {sorted(missing)}")
    if data.empty:
        raise ValueError("Raw stock data is empty")

    data = data[RAW_COLUMNS].copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["stock"] = data["stock"].str.strip().str.zfill(6)
    for column in ["open", "high", "low", "close", "volume"]:
        data[column] = pd.to_numeric(data[column], errors="raise")

    duplicate_rows = data.duplicated(["date", "stock"])
    if duplicate_rows.any():
        raise ValueError("Raw stock data contains duplicate date-stock rows")
    if (data["close"] <= 0).any():
        raise ValueError("close must be greater than zero")

    return data.sort_values(["stock", "date"]).reset_index(drop=True)


def calculate_factors(raw_data: pd.DataFrame) -> pd.DataFrame:
    """Calculate three 20-day factors and the forward five-day return."""
    frames = []
    for _, stock_data in raw_data.groupby("stock", sort=True):
        stock_data = stock_data.sort_values("date").copy()
        daily_return = stock_data["close"].pct_change(fill_method=None)

        stock_data["momentum"] = stock_data["close"] / stock_data["close"].shift(20) - 1
        stock_data["volatility"] = daily_return.rolling(window=20, min_periods=20).std()
        stock_data["volume_factor"] = (
            stock_data["volume"] / stock_data["volume"].rolling(window=20, min_periods=20).mean() - 1
        )
        for period in FORWARD_PERIODS:
            stock_data[f"forward_return_{period}d"] = stock_data["close"].shift(-period) / stock_data["close"] - 1
        stock_data["return"] = stock_data["forward_return_5d"]
        frames.append(stock_data)

    calculated = pd.concat(frames, ignore_index=True)
    long_data = calculated.melt(
        id_vars=["date", "stock", "return", *FORWARD_COLUMNS],
        value_vars=FACTOR_COLUMNS,
        var_name="factor_name",
        value_name="factor_value",
    )
    long_data = long_data.dropna(subset=["factor_value", "return"])
    long_data["date"] = long_data["date"].dt.strftime("%Y-%m-%d")
    return long_data[OUTPUT_COLUMNS].sort_values(
        ["date", "stock", "factor_name"], kind="stable"
    ).reset_index(drop=True)


def generate_factor_data(
    input_path: str | Path = "data/raw_stock_data.csv",
    output_path: str | Path = "data/factor_data_generated.csv",
) -> pd.DataFrame:
    """Read raw data, calculate factors, and save evaluator-compatible CSV."""
    raw_data = load_raw_stock_data(input_path)
    factor_data = calculate_factors(raw_data)
    if factor_data.empty:
        raise ValueError(
            "No factor rows were generated; each stock needs at least 26 daily observations"
        )

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    factor_data.to_csv(destination, index=False, encoding="utf-8-sig")
    return factor_data
