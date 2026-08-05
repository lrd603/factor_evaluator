from pathlib import Path

import pandas as pd

from stock_evaluator import calculate_stock_scores, evaluate_stock


def _mock_prices(periods=100):
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
    data.attrs["data_source"] = "mock"
    return data


def test_mock_market_data_generates_scores(monkeypatch, tmp_path):
    monkeypatch.setattr("stock_evaluator.load_stock_data", lambda *args, **kwargs: _mock_prices())
    result = evaluate_stock(
        "600519", report_path=tmp_path / "stock_report.md", include_financial=False
    )

    assert result["stock"] == "600519"
    assert result["data_source"] == "mock"
    assert Path(result["report_path"]).exists()


def test_score_output_has_complete_fields(monkeypatch, tmp_path):
    monkeypatch.setattr("stock_evaluator.load_stock_data", lambda *args, **kwargs: _mock_prices())
    result = evaluate_stock(
        "600519", report_path=tmp_path / "stock_report.md", include_financial=False
    )

    assert {
        "stock",
        "momentum_score",
        "volatility_score",
        "volume_score",
        "final_score",
        "data_source",
        "report_path",
    } == set(result)


def test_all_scores_are_between_zero_and_one_hundred():
    from factor_engine.factor_builder import build_factor_data

    scores = calculate_stock_scores(build_factor_data(_mock_prices()))
    for field in ["momentum_score", "volatility_score", "volume_score", "final_score"]:
        assert 0 <= scores[field] <= 100
