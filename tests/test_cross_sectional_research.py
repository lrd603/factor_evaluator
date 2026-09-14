"""Regression tests for point-in-time cross-sectional factor research."""

import numpy as np
import pandas as pd
import pytest

from config.factor_metadata import apply_factor_directions
from factor_analysis.research import (
    assign_quantiles,
    calculate_daily_ic_series,
    calculate_forward_returns,
)
from factor_processing import (
    cross_sectional_zscore,
    percentile_rank_cross_sectional,
    preprocess_factors,
    winsorize_factor,
)
from factor_combination.static_weight import combine_static_weight, normalize_weights


def test_percentile_and_mad_winsorization_are_missing_safe():
    values = pd.Series([1.0, 2.0, 3.0, 100.0, np.nan])
    percentile = winsorize_factor(values, "percentile", 0.0, 0.75)
    mad = winsorize_factor(values, "mad", mad_k=2)
    assert percentile.iloc[3] == pytest.approx(values.dropna().quantile(0.75))
    assert mad.iloc[3] == pytest.approx(4.5)
    assert pd.isna(percentile.iloc[4]) and pd.isna(mad.iloc[4])


def test_zscore_uses_only_the_same_date_and_handles_constant_or_nan():
    frame = pd.DataFrame({"date": ["d1"] * 3 + ["d2"] * 3, "factor_value": [1, 2, 3, 100, 100, np.nan]})
    result = cross_sectional_zscore(frame)
    assert result.iloc[:3].mean() == pytest.approx(0)
    assert result.iloc[3:5].tolist() == [0.0, 0.0]
    assert pd.isna(result.iloc[5])
    changed = frame.copy(); changed.loc[changed.date == "d2", "factor_value"] = [999, -999, 0]
    assert cross_sectional_zscore(changed).iloc[:3].equals(result.iloc[:3])


def test_cross_sectional_percentile_is_daily_not_time_series():
    frame = pd.DataFrame({"date": [1, 1, 2, 2], "factor_value": [1, 2, 100, 200]})
    assert percentile_rank_cross_sectional(frame).tolist() == [50.0, 100.0, 50.0, 100.0]


def test_preprocessing_has_no_future_date_leakage():
    base = pd.DataFrame({
        "date": ["2024-01-01"] * 3 + ["2024-01-02"] * 3,
        "stock": ["1", "2", "3"] * 2,
        "factor_name": ["momentum_20"] * 6,
        "factor_value": [1, 2, 3, 10, 20, 30],
    })
    first = preprocess_factors(base)
    changed = base.copy(); changed.loc[3:, "factor_value"] = [1000, -500, 7]
    second = preprocess_factors(changed)
    assert first.loc[:2, "normalized_value"].equals(second.loc[:2, "normalized_value"])


def test_lower_is_better_direction_is_negated():
    frame = pd.DataFrame({"factor_name": ["volatility_20", "momentum_20"], "normalized_value": [2.0, 2.0]})
    assert apply_factor_directions(frame)["normalized_value"].tolist() == [-2.0, 2.0]


def test_quantile_assignment_orders_low_to_high_and_handles_degenerate_inputs():
    assigned = assign_quantiles(pd.Series(range(1, 11)))
    assert assigned.iloc[0] == 1 and assigned.iloc[-1] == 5
    assert assign_quantiles(pd.Series([np.nan, np.nan])).isna().all()
    assert assign_quantiles(pd.Series([1, 1, 1])).notna().all()


def test_pearson_and_rank_ic_calculation():
    data = pd.DataFrame({"date": [1] * 4, "factor": [1, 2, 3, 4], "future": [10, 20, 30, 40]})
    assert calculate_daily_ic_series(data, "factor", "future").iloc[0] == pytest.approx(1)
    assert calculate_daily_ic_series(data, "factor", "future", "spearman").iloc[0] == pytest.approx(1)


def test_forward_return_uses_future_price_within_each_stock():
    prices = pd.DataFrame({
        "date": list(pd.date_range("2024-01-01", periods=3)) * 2,
        "stock": ["A"] * 3 + ["B"] * 3,
        "close": [10, 11, 12, 20, 18, 21],
    })
    result = calculate_forward_returns(prices, [1])
    assert result.loc[0, "forward_return_1d"] == pytest.approx(0.1)
    assert result.loc[2, "forward_return_1d"] != result.loc[2, "forward_return_1d"]
    assert result.loc[3, "forward_return_1d"] == pytest.approx(-0.1)


def test_static_weights_are_normalized_by_absolute_sum():
    assert normalize_weights({"a": 2, "b": -1}) == {"a": pytest.approx(2 / 3), "b": pytest.approx(-1 / 3)}
    score = combine_static_weight(pd.DataFrame({"a": [3.0], "b": [0.0]}), {"a": 2, "b": 1})
    assert score.iloc[0] == pytest.approx(2.0)
