from pathlib import Path

import pandas as pd
import pytest

from backtest.engine import BacktestEngine
from backtest.metrics import calculate_backtest_metrics


def _market_loader(code, start_date=None, end_date=None):
    periods = 140
    offset = int(code[-2:]) / 100
    index = pd.Series(range(periods), dtype=float)
    close = 50 + offset + index * (0.05 + offset / 100) + (index % 9) * 0.1
    data = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=periods),
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000_000 + (index % 20) * 20_000,
        }
    )
    data.attrs["stock_code"] = code
    return data


def _financial_loader(code):
    periods = 140
    offset = int(code[-2:]) / 10
    index = pd.Series(range(periods), dtype=float)
    data = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=periods),
            "stock": [code] * periods,
            "pe": 25 + offset - index * 0.02,
            "pb": 5 + offset / 10 - index * 0.003,
            "roe": 12 + offset + index * 0.01,
        }
    )
    data.attrs["data_source"] = "mock"
    return data


def _benchmark_loader(start_date, end_date):
    dates = pd.bdate_range("2024-01-01", periods=140)
    return pd.DataFrame(
        {"date": dates, "close": 3500 + pd.Series(range(140), dtype=float) * 0.5}
    )


def _engine():
    return BacktestEngine(
        ["600519", "000001", "300750", "601318", "600036"],
        "2024-01-01",
        "2024-07-12",
        market_loader=_market_loader,
        financial_loader=_financial_loader,
        benchmark_loader=_benchmark_loader,
    )


def test_mock_data_can_run_backtest():
    engine = _engine()
    returns = engine.run()
    assert not returns.empty
    assert returns.name == "portfolio_return"
    assert engine.holdings.sum(axis=1).between(0.999999, 1.000001).all()
    assert engine.transaction_cost == pytest.approx(0.001)
    assert engine.transaction_costs.sum() > 0
    assert len(engine.score_history["stock"].unique()) == 5


def test_metrics_are_calculated_correctly():
    returns = pd.Series([0.01, -0.02, 0.03, 0.01])
    benchmark = pd.Series([0.005, -0.01, 0.01, 0.005])
    metrics = calculate_backtest_metrics(returns, benchmark)
    expected_annual = (1.01 * 0.98 * 1.03 * 1.01) ** (252 / 4) - 1
    assert metrics["Annual Return"] == pytest.approx(expected_annual)
    assert metrics["Max Drawdown"] == pytest.approx(-0.02)
    assert metrics["Win Rate"] == pytest.approx(0.75)
    assert set(metrics) == {
        "Strategy Return", "Benchmark Return", "Alpha", "Annual Return",
        "Sharpe Ratio", "Max Drawdown", "Win Rate", "Information Ratio"
    }
    assert metrics["Alpha"] == pytest.approx(
        metrics["Strategy Return"] - metrics["Benchmark Return"]
    )


def test_report_is_generated(tmp_path):
    engine = _engine()
    engine.run()
    report = engine.generate_report(tmp_path / "backtest_report.md")
    assert report.exists()
    content = Path(report).read_text(encoding="utf-8")
    assert "# Backtest Report" in content
    assert "600519" in content
    assert "Annual Return" in content
    assert "CSI 300 Benchmark Return" in content
    assert "Alpha" in content
