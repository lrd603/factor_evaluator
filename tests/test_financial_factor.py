import pandas as pd
import pytest

from factor_engine.factor_builder import build_factor_data
from factor_engine.quality import calculate_quality_factor
from factor_engine.value import calculate_value_factors
from financial_loader.financial_data import FINANCIAL_COLUMNS, load_financial_data
from stock_evaluator import calculate_multifactor_scores


def _financial_data():
    periods = 80
    index = pd.Series(range(periods), dtype=float)
    data = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=periods, freq="B"),
            "stock": ["600519"] * periods,
            "pe": 30 - index * 0.1,
            "pb": 10 - index * 0.03,
            "roe": 20 + index * 0.05,
        }
    )
    data.attrs["data_source"] = "mock"
    return data


def _prices():
    periods = 100
    index = pd.Series(range(periods), dtype=float)
    close = 100 + index * 0.25 + (index % 7) * 0.4
    data = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=periods, freq="B"),
            "open": close - 0.2,
            "high": close + 0.8,
            "low": close - 0.8,
            "close": close,
            "volume": 1_000_000 + (index % 20) * 25_000,
        }
    )
    data.attrs["stock_code"] = "600519"
    return data


def test_financial_data_is_loaded(monkeypatch):
    expected = _financial_data()
    monkeypatch.setattr(
        "financial_loader.financial_data._fetch_real_financial_data",
        lambda code: expected.copy(),
    )
    result = load_financial_data("600519", allow_mock=False)
    assert result.columns.tolist() == FINANCIAL_COLUMNS
    assert result.attrs["data_source"] == "akshare"


def test_real_financial_sources_with_different_date_precision_are_merged(monkeypatch):
    import sys
    import types
    from financial_loader.financial_data import _fetch_real_financial_data

    valuation_dates = pd.Series(pd.date_range("2024-01-01", periods=3, freq="D")).astype(
        "datetime64[s]"
    )
    roe_dates = pd.Series(pd.to_datetime(["2023-12-31"])).astype("datetime64[us]")

    def valuation(symbol, indicator, period):
        values = [20.0, 19.0, 18.0] if "市盈率" in indicator else [6.0, 5.9, 5.8]
        return pd.DataFrame({"date": valuation_dates, "value": values})

    fake_akshare = types.SimpleNamespace(
        stock_zh_valuation_baidu=valuation,
        stock_financial_analysis_indicator_em=lambda *args, **kwargs: pd.DataFrame(
            {"NOTICE_DATE": roe_dates, "ROEJQ": [25.0]}
        ),
    )
    monkeypatch.setitem(sys.modules, "akshare", fake_akshare)
    result = _fetch_real_financial_data("600519")
    assert len(result) == 3
    assert result["roe"].tolist() == [25.0, 25.0, 25.0]


def test_value_and_quality_factors_are_calculated():
    result = calculate_value_factors(_financial_data())
    result = calculate_quality_factor(result)
    assert result.loc[0, "pe_factor"] == pytest.approx(1 / result.loc[0, "pe"])
    assert result.loc[0, "pb_factor"] == pytest.approx(1 / result.loc[0, "pb"])
    assert result.loc[0, "roe_factor"] == result.loc[0, "roe"]


def test_multifactor_stock_score_is_generated():
    scores = calculate_multifactor_scores(
        build_factor_data(_prices()), _financial_data(), "600519"
    )
    assert {"technical_score", "value_score", "quality_score", "final_score"} <= set(scores)
    for name in ["technical_score", "value_score", "quality_score", "final_score"]:
        assert 0 <= scores[name] <= 100
    expected = (
        scores["technical_score"] * 0.4
        + scores["value_score"] * 0.3
        + scores["quality_score"] * 0.3
    )
    assert scores["final_score"] == pytest.approx(expected, abs=0.02)
