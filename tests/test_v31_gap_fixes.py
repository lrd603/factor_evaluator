"""V3.1 regression tests for previously documented research gaps."""

import json

import pandas as pd
import pytest

from factor_analysis.sample_guard import assess_research_sample
from financial_loader.point_in_time import build_point_in_time_fundamental_panel
from universe import CSVUniverseProvider, UniverseConfig, enforce_trade_constraints
from universe.filters import filter_universe


def test_listing_and_delisting_intervals_are_respected():
    metadata = pd.DataFrame({"stock": ["000001"], "listing_date": ["2024-01-02"], "delisting_date": ["2024-03-01"]})
    provider = CSVUniverseProvider(metadata)
    assert provider.get_universe("2024-01-01") == []
    assert provider.get_universe("2024-02-01") == ["000001"]
    assert provider.get_universe("2024-03-02") == []


def test_index_provider_refuses_current_constituent_backfill():
    provider = CSVUniverseProvider(pd.DataFrame({"date": ["2024-01-01"], "stock": ["000001"], "close": [10], "volume": [1]}), UniverseConfig(min_listing_days=1))
    with pytest.raises(RuntimeError, match="historical_index_constituents_unavailable"):
        provider.get_universe("2024-01-01", "CSI300")


def test_st_filter_is_date_specific_and_suspension_requires_zero_volume():
    history = pd.DataFrame({"date": pd.to_datetime(["2024-01-01", "2024-01-02"] * 2), "stock": ["A", "A", "B", "B"], "close": [10, 10, 20, 20], "volume": [100, 100, 100, 0], "is_st": [False, True, False, False]})
    config = UniverseConfig(min_listing_days=1)
    assert set(filter_universe(history, "2024-01-01", config).stock) == {"A", "B"}
    assert filter_universe(history, "2024-01-02", config).empty


def test_limit_and_suspension_trade_constraints_are_directional():
    previous = pd.Series({"A": 0.2, "B": 0.3, "C": 0.4})
    target = pd.Series({"A": 0.5, "B": 0.0, "C": 0.0})
    state = pd.DataFrame({"stock": ["A", "B", "C"], "volume": [100, 100, 0], "limit_up": [True, False, False], "limit_down": [False, True, False]})
    constrained = enforce_trade_constraints(previous, target, state)
    assert constrained.to_dict() == previous.to_dict()


def test_daily_valuations_are_not_lagged_by_accounting_announcement():
    dates = pd.DataFrame({"date": pd.to_datetime(["2024-03-29", "2024-03-30"]), "stock": ["A", "A"]})
    raw = pd.DataFrame({"date": pd.to_datetime(["2024-03-29", "2024-03-30"]), "stock": ["A", "A"], "pe": [10, 11], "pb": [1, 2], "report_period": ["2023-12-31"] * 2, "announcement_date": ["2024-03-30"] * 2, "roe": [0.1, 0.1]})
    panel, quality = build_point_in_time_fundamental_panel(dates, raw)
    assert panel.pe.tolist() == [10, 11]
    assert pd.isna(panel.loc[0, "roe"]) and panel.loc[1, "roe"] == pytest.approx(0.1)
    assert quality.set_index("factor").loc["PE", "point_in_time_available"]


def test_small_sample_guard_forbids_formal_research_claim():
    data = pd.DataFrame({"date": ["2024-01-01"] * 3, "stock": ["A", "B", "C"]})
    result = assess_research_sample(data)
    assert result["status"] == "ENGINEERING_SMOKE_TEST"
    assert not result["quintile_available"]


def test_research_data_quality_artifact_from_smoke_run(tmp_path):
    from factor_analysis.v3 import run_v3_research
    from walk_forward import WalkForwardConfig
    dates = pd.bdate_range("2024-01-01", periods=12)
    prices = pd.DataFrame([{"date": d, "stock": f"{s:06d}", "open": 10+s, "high": 10+s, "low": 10+s, "close": 10+s+d.day/100, "volume": 100} for d in dates for s in range(5)])
    factors = pd.DataFrame([{"date": d, "stock": f"{s:06d}", "factor_name": f, "factor_value": s if f == "a" else -s, "return": s/1000, "forward_return_1d": s/1000} for d in dates for s in range(5) for f in ["a", "b"]])
    report = tmp_path / "factor_research_v3_report.md"
    run_v3_research(prices, factors, report, UniverseConfig(min_listing_days=2), walk_config=WalkForwardConfig(train_window=6, test_window=3, min_train=6))
    quality_path = tmp_path / "research_data_quality.json"
    quality = json.loads(quality_path.read_text(encoding="utf-8"))
    assert quality["sample_size"]["status"] == "ENGINEERING_SMOKE_TEST"
    assert quality["fallback_warnings"]
    assert "Research validity status: ENGINEERING_SMOKE_TEST" in report.read_text(encoding="utf-8")
