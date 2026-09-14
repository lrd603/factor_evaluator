"""Tests for universe, PIT, neutralization, rolling weights and walk-forward."""

import numpy as np
import pandas as pd
import pytest

from factor_combination.rolling_weight import rolling_ic_weight
from factor_neutralization import NeutralizationConfig, neutralize_factors
from financial_loader.point_in_time import align_fundamentals_point_in_time
from universe import HistoricalUniverseProvider, UniverseConfig
from walk_forward import WalkForwardConfig, build_walk_forward_folds, run_walk_forward


def test_universe_changes_and_never_includes_stock_before_listing():
    dates = pd.bdate_range("2024-01-01", periods=150)
    history = pd.concat([
        pd.DataFrame({"date": dates, "stock": "A", "close": 10, "volume": 100}),
        pd.DataFrame({"date": dates[50:], "stock": "B", "close": 20, "volume": 100}),
    ])
    provider = HistoricalUniverseProvider(history, UniverseConfig(min_listing_days=20))
    assert "B" not in provider.get_universe(dates[49])
    assert provider.get_universe(dates[60]) == ["A"]
    assert set(provider.get_universe(dates[100])) == {"A", "B"}


def test_point_in_time_fundamental_is_not_visible_before_announcement():
    dates = pd.DataFrame({"date": pd.to_datetime(["2024-03-29", "2024-03-30", "2024-04-01"]), "stock": ["A"] * 3})
    fundamentals = pd.DataFrame({"stock": ["A"], "report_period": ["2023-12-31"], "announcement_date": ["2024-03-30"], "roe": [0.12]})
    aligned = align_fundamentals_point_in_time(dates, fundamentals)
    assert pd.isna(aligned.loc[0, "roe"])
    assert aligned.loc[1, "roe"] == pytest.approx(0.12)
    assert aligned.loc[2, "roe"] == pytest.approx(0.12)


def test_size_neutralization_removes_log_market_cap_exposure():
    market_cap = np.exp(np.linspace(10, 20, 30))
    frame = pd.DataFrame({"date": "2024-01-02", "stock": range(30), "factor_name": "f", "normalized_value": np.log(market_cap) * 2 + np.sin(np.arange(30)), "market_cap": market_cap})
    before = frame.normalized_value.corr(pd.Series(np.log(market_cap)))
    result = neutralize_factors(frame, config=NeutralizationConfig(use_size=True, use_industry=False, rezscore=False))
    after = result.neutralized_value.corr(pd.Series(np.log(market_cap)))
    assert abs(before) > 0.9
    assert abs(after) < 1e-10


def test_rolling_weight_uses_only_prior_ic():
    data = pd.DataFrame({"date": list(pd.date_range("2024-01-01", periods=4)) * 2, "factor_name": ["a"] * 4 + ["b"] * 4, "ic": [1, 1, 1, -999, 0.5, 0.5, 0.5, 999]})
    original = rolling_ic_weight(data, lookback=3, min_history=2)
    changed = data.copy(); changed.loc[changed.date == pd.Timestamp("2024-01-04"), "ic"] *= -1
    other = rolling_ic_weight(changed, lookback=3, min_history=2)
    target = pd.Timestamp("2024-01-04")
    assert original[original.date == target].weight.tolist() == other[other.date == target].weight.tolist()


def _walk_data(periods=14):
    rows = []
    for day, date in enumerate(pd.bdate_range("2024-01-01", periods=periods)):
        for stock in range(5):
            ret = (stock - 2) * 0.001
            rows.extend([[date, str(stock), "a", stock, ret], [date, str(stock), "b", -stock, ret]])
    return pd.DataFrame(rows, columns=["date", "stock", "factor_name", "directed_value", "forward_return_1d"])


def test_walk_forward_dates_do_not_overlap_and_oos_changes_do_not_change_train_weights():
    config = WalkForwardConfig(train_window=6, test_window=4, min_train=6)
    folds = build_walk_forward_folds(_walk_data().date, config)
    assert all(fold["train_end"] < fold["test_start"] for fold in folds)
    data = _walk_data()
    _, first, _ = run_walk_forward(data, methods=("rolling_ic_weight",), config=config)
    changed = data.copy(); changed.loc[changed.date >= folds[0]["test_start"], "directed_value"] *= -100
    _, second, _ = run_walk_forward(changed, methods=("rolling_ic_weight",), config=config)
    assert first.iloc[0].train_weights == second.iloc[0].train_weights
