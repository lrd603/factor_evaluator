import pandas as pd

from factor_analysis.sample_guard import assess_formal_research
from scripts.run_v4_empirical_research import _covers_requested_range, stable_sample


def test_stable_sample_is_order_independent():
    stocks = pd.DataFrame({"stock": ["000001", "600000", "300001"], "stock_name": ["A", "B", "C"]})
    first = stable_sample(stocks, 2, 7).stock.tolist()
    second = stable_sample(stocks.iloc[::-1], 2, 7).stock.tolist()
    assert first == second


def test_formal_guard_requires_breadth_and_five_years():
    dates = pd.to_datetime(["2018-01-01", "2024-01-02"])
    rows = [{"date": date, "stock": f"{stock:06d}"} for date in dates for stock in range(100)]
    result = assess_formal_research(pd.DataFrame(rows), stock_count=100)
    assert result["formal_status"] == "FORMAL_EMPIRICAL_RESEARCH"
    assert result["time_span_status"] == "VALID_TIME_SPAN"


def test_calendar_end_accepts_nearby_last_trading_day():
    data = pd.DataFrame({"date": pd.to_datetime(["2018-01-02", "2025-12-30"])})
    assert _covers_requested_range(data, "2018-01-01", "2025-12-31")


def test_late_listing_full_download_is_accepted():
    data = pd.DataFrame({"date": pd.date_range("2023-01-01", periods=200).append(pd.DatetimeIndex(["2025-12-30"]))})
    assert _covers_requested_range(data, "2018-01-01", "2025-12-31", {"source": "akshare_tencent"})
