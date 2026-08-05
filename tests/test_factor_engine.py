import pandas as pd
import pytest

from factor_engine.factor_builder import FACTOR_COLUMNS, OUTPUT_COLUMNS, build_factor_data
from factor_engine.momentum import calculate_momentum
from factor_engine.volatility import calculate_volatility
from factor_engine.volume_factor import calculate_volume_factor


@pytest.fixture
def price_data():
    periods = 80
    data = pd.DataFrame(
        {
            "date": pd.date_range("2024-01-01", periods=periods, freq="D"),
            "open": range(100, 100 + periods),
            "high": range(101, 101 + periods),
            "low": range(99, 99 + periods),
            "close": range(100, 100 + periods),
            "volume": range(1000, 1000 + periods),
        }
    )
    data.attrs["stock_code"] = "600519"
    return data


def test_momentum_factors_are_generated(price_data):
    result = calculate_momentum(price_data)
    assert result.loc[20, "momentum_20"] == pytest.approx(120 / 100 - 1)
    assert result.loc[60, "momentum_60"] == pytest.approx(160 / 100 - 1)


def test_volatility_factors_are_generated(price_data):
    result = calculate_volatility(price_data)
    expected_returns = price_data["close"].pct_change(fill_method=None)
    assert result.loc[20, "volatility_20"] == pytest.approx(expected_returns.iloc[1:21].std())
    assert result.loc[60, "volatility_60"] == pytest.approx(expected_returns.iloc[1:61].std())


def test_volume_factor_is_generated(price_data):
    result = calculate_volume_factor(price_data)
    assert result.loc[19, "volume_change_20"] == pytest.approx(
        price_data.loc[19, "volume"] / price_data.loc[:19, "volume"].mean()
    )


def test_builder_outputs_evaluator_format(price_data):
    result = build_factor_data(price_data)
    assert result.columns.tolist() == OUTPUT_COLUMNS
    assert set(result["factor_name"]) == set(FACTOR_COLUMNS)
    assert result["stock"].unique().tolist() == ["600519"]
    assert result[["factor_value", "return"]].notna().all().all()

    momentum = result[result["factor_name"] == "momentum_20"].iloc[0]
    assert momentum["factor_value"] == pytest.approx(120 / 100 - 1)
    assert momentum["return"] == pytest.approx(125 / 120 - 1)
