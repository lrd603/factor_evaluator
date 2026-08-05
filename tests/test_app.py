from pathlib import Path

import pandas as pd
import pytest

from app import (
    load_backtest_curves,
    load_markdown_report,
    parse_backtest_metrics,
    run_stock_analysis,
    validate_stock_code,
)


def test_stock_analysis_calls_existing_evaluator():
    calls = []

    def fake_evaluator(code):
        calls.append(code)
        return {
            "stock": code,
            "technical_score": 70.0,
            "value_score": 80.0,
            "quality_score": 75.0,
            "final_score": 74.5,
        }

    result = run_stock_analysis("600519", evaluator=fake_evaluator)
    assert calls == ["600519"]
    assert result["final_score"] == 74.5


def test_stock_code_validation():
    assert validate_stock_code(" 000001 ") == "000001"
    with pytest.raises(ValueError):
        validate_stock_code("60051")


def test_report_and_backtest_helpers(tmp_path):
    report_path = tmp_path / "backtest_report.md"
    report_path.write_text(
        "Annual Return: 14.92%\nSharpe Ratio: 0.7070\n"
        "Max Drawdown: -16.50%\nAlpha: -3.22%\n",
        encoding="utf-8",
    )
    report = load_markdown_report(report_path)
    metrics = parse_backtest_metrics(report)
    assert metrics == {
        "annual_return": pytest.approx(0.1492),
        "sharpe_ratio": pytest.approx(0.7070),
        "max_drawdown": pytest.approx(-0.1650),
        "alpha": pytest.approx(-0.0322),
    }

    returns_path = tmp_path / "backtest_returns.csv"
    pd.DataFrame(
        {"date": ["2024-01-01", "2024-01-02"], "portfolio_return": [0.1, -0.05]}
    ).to_csv(returns_path, index=False)
    curves = load_backtest_curves(returns_path)
    assert curves.iloc[-1]["equity"] == pytest.approx(1.045)
    assert curves.iloc[-1]["drawdown"] == pytest.approx(-0.05)
    assert Path(report_path).exists()
