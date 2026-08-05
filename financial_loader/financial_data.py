"""Load A-share valuation and profitability history with a mock fallback."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
import math
import re

import pandas as pd


FINANCIAL_COLUMNS = ["date", "stock", "pe", "pb", "roe"]
logger = logging.getLogger(__name__)


def _normalize_stock_code(stock_code: str) -> str:
    code = str(stock_code).strip()
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError(f"Invalid A-share stock code: {stock_code!r}")
    return code


def _market_symbol(code: str) -> str:
    suffix = "SH" if code.startswith(("5", "6", "9")) else "SZ"
    return f"{code}.{suffix}"


def _fetch_real_financial_data(code: str) -> pd.DataFrame:
    import akshare as ak

    # These independent public endpoints can be queried concurrently.
    with ThreadPoolExecutor(max_workers=3) as executor:
        pe_future = executor.submit(
            ak.stock_zh_valuation_baidu, code, "市盈率(TTM)", "近五年"
        )
        pb_future = executor.submit(
            ak.stock_zh_valuation_baidu, code, "市净率", "近五年"
        )
        roe_future = executor.submit(
            ak.stock_financial_analysis_indicator_em, _market_symbol(code), "按报告期"
        )
        pe_raw = pe_future.result()
        pb_raw = pb_future.result()
        roe_raw = roe_future.result()

    if pe_raw.empty or pb_raw.empty or roe_raw.empty:
        raise ValueError("AkShare returned incomplete financial data")

    pe = pe_raw[["date", "value"]].rename(columns={"value": "pe"})
    pb = pb_raw[["date", "value"]].rename(columns={"value": "pb"})
    valuation = pe.merge(pb, on="date", how="inner")
    valuation["date"] = pd.to_datetime(
        valuation["date"], errors="raise"
    ).astype("datetime64[ns]")

    required_roe_columns = {"NOTICE_DATE", "ROEJQ"}
    missing = required_roe_columns - set(roe_raw.columns)
    if missing:
        raise ValueError(f"AkShare ROE data is missing columns: {sorted(missing)}")
    roe = roe_raw[["NOTICE_DATE", "ROEJQ"]].rename(
        columns={"NOTICE_DATE": "date", "ROEJQ": "roe"}
    )
    roe["date"] = pd.to_datetime(roe["date"], errors="coerce").astype(
        "datetime64[ns]"
    )
    roe["roe"] = pd.to_numeric(roe["roe"], errors="coerce")
    roe = roe.dropna().drop_duplicates("date", keep="last").sort_values("date")
    if roe.empty:
        raise ValueError("AkShare returned no usable ROE observations")

    result = pd.merge_asof(
        valuation.sort_values("date"), roe, on="date", direction="backward"
    )
    result["stock"] = code
    for column in ["pe", "pb", "roe"]:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    result = result.dropna(subset=["pe", "pb", "roe"])
    if result.empty:
        raise ValueError("Financial series have no overlapping observations")
    return result[FINANCIAL_COLUMNS].reset_index(drop=True)


def generate_mock_financial_data(stock_code: str, periods: int = 252) -> pd.DataFrame:
    """Generate deterministic financial history for offline development."""
    code = _normalize_stock_code(stock_code)
    dates = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=periods)
    seed = int(code) % 97
    rows = []
    for index, current_date in enumerate(dates):
        pe = 12 + seed / 10 + 3 * math.sin(index / 23)
        pb = 1.5 + seed / 100 + 0.4 * math.sin(index / 31)
        roe = 8 + seed / 12 + 2 * math.sin(index / 63)
        rows.append([current_date, code, round(pe, 4), round(pb, 4), round(roe, 4)])
    result = pd.DataFrame(rows, columns=FINANCIAL_COLUMNS)
    result.attrs["data_source"] = "mock"
    return result


def load_financial_data(stock_code: str, allow_mock: bool = True) -> pd.DataFrame:
    """Return historical PE, PB and disclosed ROE data for one A-share."""
    code = _normalize_stock_code(stock_code)
    try:
        result = _fetch_real_financial_data(code)
        result.attrs["data_source"] = "akshare"
        logger.info("Financial Data Source: AkShare")
        return result
    except Exception as exc:
        if not allow_mock:
            raise
        logger.warning("Real financial data unavailable for %s: %s", code, exc)
        result = generate_mock_financial_data(code)
        logger.info("Financial Data Source: Mock")
        return result
