from pathlib import Path

import pandas as pd
import pytest

from backtest.configured import create_configured_backtest
from config.stock_pool import DEFAULT_STOCK_POOL
from factor_analysis.ic_analysis import analyze_factor_ic, generate_ic_report


def _factor_data():
    rows = []
    stocks = ["600519", "000001", "300750", "601318", "600036"]
    factors = [
        "momentum_20",
        "momentum_60",
        "volatility_20",
        "volatility_60",
        "volume_change_20",
        "PE",
        "PB",
        "ROE",
    ]
    for day_index, date in enumerate(pd.bdate_range("2024-01-01", periods=8)):
        for stock_index, stock in enumerate(stocks):
            future_return = stock_index * 0.01 + day_index * 0.0001
            for factor_index, factor in enumerate(factors):
                direction = -1 if factor in {"volatility_20", "volatility_60", "PE", "PB"} else 1
                value = direction * stock_index + day_index * 0.01 * (factor_index + 1)
                rows.append([date, stock, factor, value, future_return])
    return pd.DataFrame(
        rows, columns=["date", "stock", "factor_name", "factor_value", "return"]
    )


def _market_loader(code, start_date=None, end_date=None):
    periods = 90
    offset = int(code[-2:]) / 100
    index = pd.Series(range(periods), dtype=float)
    close = 50 + offset + index * (0.05 + offset / 100) + (index % 9) * 0.1
    result = pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=periods),
            "open": close - 0.1,
            "high": close + 0.5,
            "low": close - 0.5,
            "close": close,
            "volume": 1_000_000 + (index % 20) * 20_000,
        }
    )
    result.attrs["stock_code"] = code
    return result


def _financial_loader(code):
    periods = 90
    index = pd.Series(range(periods), dtype=float)
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=periods),
            "stock": [code] * periods,
            "pe": 25 - index * 0.02 + int(code[-1]),
            "pb": 5 - index * 0.003 + int(code[-1]) / 10,
            "roe": 12 + index * 0.01 + int(code[-1]),
        }
    )


def _benchmark_loader(start_date, end_date):
    return pd.DataFrame(
        {
            "date": pd.bdate_range("2024-01-01", periods=90),
            "close": 3500 + pd.Series(range(90), dtype=float),
        }
    )


def test_ic_analysis_calculates_all_supported_factors():
    result = analyze_factor_ic(_factor_data())
    assert len(result) == 8
    assert set(result["Factor"]) == {
        "momentum_20", "momentum_60", "volatility_20", "volatility_60",
        "volume_change_20", "PE", "PB", "ROE"
    }
    momentum = result[result["Factor"] == "momentum_20"].iloc[0]
    assert momentum["IC Mean"] == pytest.approx(1.0)
    assert momentum["Rank IC Mean"] == pytest.approx(1.0)


def test_configured_multi_stock_pool_runs():
    engine = create_configured_backtest(
        "2024-01-01",
        "2024-05-03",
        market_loader=_market_loader,
        financial_loader=_financial_loader,
        benchmark_loader=_benchmark_loader,
    )
    returns = engine.run()
    assert len(DEFAULT_STOCK_POOL) >= 10
    assert engine.stocks == DEFAULT_STOCK_POOL
    assert not returns.empty


def test_ic_report_is_generated(tmp_path):
    analysis = analyze_factor_ic(_factor_data())
    report = generate_ic_report(analysis, tmp_path / "factor_ic_report.md")
    content = Path(report).read_text(encoding="utf-8")
    assert report.exists()
    assert "# Factor IC Report" in content
    assert "| Rank | Factor | IC Mean | Rank IC Mean | ICIR |" in content
    assert "momentum_20" in content
