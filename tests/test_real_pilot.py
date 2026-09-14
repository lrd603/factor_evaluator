"""Minimal offline tests for the real-data pilot safeguards."""

import json

import pandas as pd
import pytest

from scripts.run_real_research_pilot import PRICE_COLUMNS, get_or_download_price, load_cached_real_price


def _real_frame():
    frame = pd.DataFrame([["2024-01-02", "000001", 1, 1, 1, 1, 100, 100]], columns=PRICE_COLUMNS)
    frame.attrs["source"] = "akshare_test_double"
    return frame


def test_real_cache_round_trip(tmp_path):
    data, metadata = get_or_download_price("000001", "2024-01-01", "2024-01-31", tmp_path, fetcher=lambda *_: _real_frame())
    cached, cached_metadata = get_or_download_price("000001", "2024-01-01", "2024-01-31", tmp_path, fetcher=lambda *_: pytest.fail("cache not used"))
    assert len(data) == len(cached) == 1
    assert metadata["is_real_data"] and cached_metadata["cache_hit"]


def test_mock_cache_is_rejected(tmp_path):
    path = tmp_path / "mock.csv"; _real_frame().to_csv(path, index=False)
    path.with_suffix(".json").write_text(json.dumps({"source": "mock", "is_real_data": False}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="Non-real cache rejected"):
        load_cached_real_price(path)
