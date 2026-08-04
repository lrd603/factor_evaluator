"""A-share historical market data acquisition via AkShare."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
import re

import pandas as pd


OUTPUT_COLUMNS = ["date", "stock", "open", "high", "low", "close", "volume"]
_COLUMN_MAPPING = {
    "日期": "date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
}
_STANDARD_SOURCE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def normalize_stock_code(stock_code: str) -> str:
    """Validate and normalize a six-digit A-share stock code."""
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError(f"Invalid A-share stock code: {stock_code!r}")
    return code


def _normalize_date(value: str | date | datetime | None, name: str) -> str:
    if value is None:
        return ""
    try:
        return pd.Timestamp(value).strftime("%Y%m%d")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}: {value!r}") from exc


def fetch_stock_history(
    stock_code: str,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    adjust: str = "qfq",
) -> pd.DataFrame:
    """Fetch one stock's daily history and return the standard seven columns."""
    code = normalize_stock_code(stock_code)
    start = _normalize_date(start_date, "start_date")
    end = _normalize_date(end_date, "end_date")
    if start and end and start > end:
        raise ValueError("start_date must not be later than end_date")
    if adjust not in {"", "qfq", "hfq"}:
        raise ValueError("adjust must be one of: '', 'qfq', 'hfq'")

    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError(
            "AkShare is not installed. Run: pip install -r requirements.txt"
        ) from exc

    try:
        raw = ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start,
            end_date=end,
            adjust=adjust,
        )
    except Exception as primary_error:
        # AkShare's primary endpoint is Eastmoney. Tencent provides the same
        # daily OHLCV data and is a useful fallback when that endpoint is down.
        market_prefix = "sh" if code.startswith(("5", "6", "9")) else "sz"
        try:
            raw = ak.stock_zh_a_hist_tx(
                symbol=f"{market_prefix}{code}",
                start_date=start or "19000101",
                end_date=end or "20500101",
                adjust=adjust,
                timeout=30,
            )
            print(f"Primary AkShare endpoint unavailable; used Tencent fallback for {code}.")
        except Exception as fallback_error:
            raise RuntimeError(
                f"All AkShare history endpoints failed for stock {code}"
            ) from fallback_error
    if raw is None or raw.empty:
        raise ValueError(f"No market data returned for stock {code}")

    if set(_COLUMN_MAPPING).issubset(raw.columns):
        result = raw.rename(columns=_COLUMN_MAPPING)[list(_COLUMN_MAPPING.values())].copy()
    else:
        missing = set(_STANDARD_SOURCE_COLUMNS) - set(raw.columns)
        if missing:
            raise ValueError(f"AkShare response is missing columns: {sorted(missing)}")
        result = raw[_STANDARD_SOURCE_COLUMNS].copy()

    result.insert(1, "stock", code)
    result["date"] = pd.to_datetime(result["date"], errors="raise").dt.strftime("%Y-%m-%d")
    for column in ["open", "high", "low", "close", "volume"]:
        result[column] = pd.to_numeric(result[column], errors="raise")
    return result[OUTPUT_COLUMNS].sort_values("date").reset_index(drop=True)


def fetch_and_save_stock_data(
    stock_codes: Iterable[str],
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    output_path: str | Path = "data/raw_stock_data.csv",
    adjust: str = "qfq",
) -> pd.DataFrame:
    """Fetch multiple stocks, combine them, and save a standard CSV file."""
    codes = [normalize_stock_code(code) for code in stock_codes]
    if not codes:
        raise ValueError("At least one stock code is required")

    frames = [
        fetch_stock_history(code, start_date=start_date, end_date=end_date, adjust=adjust)
        for code in dict.fromkeys(codes)
    ]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["date", "stock"]).reset_index(drop=True)

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(destination, index=False, encoding="utf-8-sig")
    return combined
