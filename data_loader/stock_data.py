"""Load daily A-share OHLCV data with an offline mock fallback."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
import logging
from typing import Literal

import pandas as pd

from data.market_data import fetch_stock_history, normalize_stock_code


PRICE_COLUMNS = ["date", "open", "high", "low", "close", "volume"]
logger = logging.getLogger(__name__)


def _timestamp(value: str | date | datetime | None, name: str) -> pd.Timestamp | None:
    if value is None:
        return None
    try:
        return pd.Timestamp(value).normalize()
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid {name}: {value!r}") from exc


def _standardize(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a validated, date-sorted OHLCV frame."""
    missing = set(PRICE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Stock data is missing columns: {sorted(missing)}")

    result = frame[PRICE_COLUMNS].copy()
    result["date"] = pd.to_datetime(result["date"], errors="raise")
    for column in PRICE_COLUMNS[1:]:
        result[column] = pd.to_numeric(result[column], errors="raise")
    result = result.drop_duplicates("date", keep="last").sort_values("date")
    return result.reset_index(drop=True)


def _fetch_akshare_history(
    stock_code: str,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
    adjust: str,
    timeout: int,
) -> pd.DataFrame:
    """Fetch real data through AkShare, preferring its responsive Tencent source."""
    try:
        import akshare as ak
    except ImportError as exc:
        raise RuntimeError("AkShare is not installed") from exc

    effective_end = end_date or pd.Timestamp.today().normalize()
    # Two years is ample for 60-day factors and keeps interactive requests fast.
    effective_start = start_date or (effective_end - pd.DateOffset(years=2))
    market_prefix = "sh" if stock_code.startswith(("5", "6", "9")) else "sz"

    tencent_error: Exception | None = None
    try:
        raw = ak.stock_zh_a_hist_tx(
            symbol=f"{market_prefix}{stock_code}",
            start_date=effective_start.strftime("%Y%m%d"),
            end_date=effective_end.strftime("%Y%m%d"),
            adjust=adjust,
            timeout=timeout,
        )
        if raw is not None and not raw.empty:
            return raw
        tencent_error = ValueError("Tencent endpoint returned no rows")
    except Exception as exc:  # AkShare can expose several request exception types.
        tencent_error = exc

    logger.warning("AkShare Tencent endpoint failed for %s: %s", stock_code, tencent_error)
    try:
        return fetch_stock_history(stock_code, start_date, end_date, adjust=adjust)
    except Exception as eastmoney_error:
        raise RuntimeError(
            f"AkShare endpoints failed for {stock_code}; "
            f"Tencent: {tencent_error}; Eastmoney: {eastmoney_error}"
        ) from eastmoney_error


def generate_mock_stock_data(
    stock_code: str,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    periods: int = 252,
) -> pd.DataFrame:
    """Generate deterministic business-day OHLCV data for offline development."""
    code = normalize_stock_code(stock_code)
    start = _timestamp(start_date, "start_date")
    end = _timestamp(end_date, "end_date") or pd.Timestamp.today().normalize()
    if start is not None and start > end:
        raise ValueError("start_date must not be later than end_date")

    dates = (
        pd.bdate_range(start=start, end=end)
        if start is not None
        else pd.bdate_range(end=end, periods=periods)
    )
    if dates.empty:
        raise ValueError("The requested date range contains no business days")

    # A tiny local pseudo-random generator avoids an additional dependency while
    # making repeated runs for the same code and date range reproducible.
    seed = int(hashlib.sha256(code.encode("ascii")).hexdigest()[:8], 16)
    state = seed or 1

    def random_unit() -> float:
        nonlocal state
        state = (1664525 * state + 1013904223) % (2**32)
        return state / (2**32)

    previous_close = 20.0 + (seed % 8000) / 100
    rows: list[list[float | pd.Timestamp]] = []
    for current_date in dates:
        daily_return = (random_unit() - 0.49) * 0.04
        open_price = previous_close * (1 + (random_unit() - 0.5) * 0.012)
        close_price = previous_close * (1 + daily_return)
        high_price = max(open_price, close_price) * (1 + random_unit() * 0.012)
        low_price = min(open_price, close_price) * (1 - random_unit() * 0.012)
        volume = int(500_000 + random_unit() * 9_500_000)
        rows.append(
            [
                current_date,
                round(open_price, 2),
                round(high_price, 2),
                round(low_price, 2),
                round(close_price, 2),
                volume,
            ]
        )
        previous_close = close_price

    result = pd.DataFrame(rows, columns=PRICE_COLUMNS)
    result.attrs["data_source"] = "mock"
    result.attrs["stock_code"] = code
    return result


def load_stock_data(
    stock_code: str,
    start_date: str | date | datetime | None = None,
    end_date: str | date | datetime | None = None,
    adjust: Literal["", "qfq", "hfq"] = "qfq",
    allow_mock: bool = True,
    timeout: int = 20,
) -> pd.DataFrame:
    """Load one stock's daily OHLCV history.

    AkShare is used first. When it is unavailable or its public endpoints fail,
    deterministic mock data is returned if ``allow_mock`` is true. The source is
    exposed through ``result.attrs['data_source']``.
    """
    code = normalize_stock_code(stock_code)
    start = _timestamp(start_date, "start_date")
    end = _timestamp(end_date, "end_date")
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must not be later than end_date")
    if not isinstance(timeout, int) or timeout <= 0:
        raise ValueError("timeout must be a positive integer")

    try:
        raw = _fetch_akshare_history(code, start, end, adjust, timeout)
        result = _standardize(raw)
        result.attrs["data_source"] = "akshare"
        result.attrs["stock_code"] = code
        logger.info("Data Source: AkShare")
        return result
    except Exception as exc:
        if not allow_mock:
            raise
        logger.warning("Real market data unavailable for %s: %s", code, exc)
        result = generate_mock_stock_data(code, start, end)
        logger.info("Data Source: Mock")
        return result


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(description="Load one A-share stock's OHLCV history.")
    parser.add_argument("stock", nargs="?", help="Six-digit stock code, e.g. 600519")
    parser.add_argument("--start", help="Start date, e.g. 2024-01-01")
    parser.add_argument("--end", help="End date, e.g. 2024-12-31")
    parser.add_argument("--no-mock", action="store_true", help="Fail if real data is unavailable")
    args = parser.parse_args()

    stock = args.stock or input("请输入股票代码: ").strip()
    data = load_stock_data(stock, args.start, args.end, allow_mock=not args.no_mock)
    print(f"Stock: {stock}")
    source = "AkShare" if data.attrs["data_source"] == "akshare" else "Mock"
    print(f"Data Source: {source}")
    print(f"Rows: {len(data)}")
    print(data.tail().to_string(index=False))


if __name__ == "__main__":
    main()
