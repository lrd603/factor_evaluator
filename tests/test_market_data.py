import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from data.market_data import (
    OUTPUT_COLUMNS,
    fetch_and_save_stock_data,
    fetch_stock_history,
    normalize_stock_code,
)


class MarketDataTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame(
            {
                "日期": ["2024-01-03", "2024-01-02"],
                "开盘": [10.2, 10.0],
                "收盘": [10.3, 10.1],
                "最高": [10.5, 10.4],
                "最低": [10.0, 9.9],
                "成交量": [1200, 1000],
                "成交额": [12360, 10100],
            }
        )

    def test_normalize_stock_code_preserves_leading_zero(self):
        self.assertEqual(normalize_stock_code("000001"), "000001")
        with self.assertRaises(ValueError):
            normalize_stock_code("123")

    def test_fetch_stock_history_maps_akshare_columns(self):
        fake_akshare = types.SimpleNamespace(stock_zh_a_hist=lambda **kwargs: self.raw.copy())
        with patch.dict(sys.modules, {"akshare": fake_akshare}):
            result = fetch_stock_history("600519", "2024-01-01", "2024-01-31")

        self.assertEqual(result.columns.tolist(), OUTPUT_COLUMNS)
        self.assertEqual(result["date"].tolist(), ["2024-01-02", "2024-01-03"])
        self.assertEqual(result["stock"].unique().tolist(), ["600519"])

    def test_fetch_stock_history_uses_tencent_fallback(self):
        fallback = self.raw.rename(
            columns={"日期": "date", "开盘": "open", "最高": "high", "最低": "low", "收盘": "close", "成交量": "volume"}
        )

        def primary_failure(**kwargs):
            raise ConnectionError("primary endpoint unavailable")

        calls = []

        def fallback_fetch(**kwargs):
            calls.append(kwargs)
            return fallback.copy()

        fake_akshare = types.SimpleNamespace(
            stock_zh_a_hist=primary_failure,
            stock_zh_a_hist_tx=fallback_fetch,
        )
        with patch.dict(sys.modules, {"akshare": fake_akshare}):
            result = fetch_stock_history("600519", "2024-01-01", "2024-01-31")

        self.assertEqual(result.columns.tolist(), OUTPUT_COLUMNS)
        self.assertEqual(calls[0]["symbol"], "sh600519")

    def test_fetch_and_save_combines_stocks(self):
        def fake_fetch(code, **kwargs):
            return pd.DataFrame(
                [["2024-01-02", code, 10, 11, 9, 10.5, 1000]],
                columns=OUTPUT_COLUMNS,
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "raw.csv"
            with patch("data.market_data.fetch_stock_history", side_effect=fake_fetch):
                result = fetch_and_save_stock_data(["600519", "000001"], output_path=output)
            saved = pd.read_csv(output, dtype={"stock": str})

        self.assertEqual(len(result), 2)
        self.assertEqual(saved.columns.tolist(), OUTPUT_COLUMNS)
        self.assertEqual(set(saved["stock"]), {"600519", "000001"})


if __name__ == "__main__":
    unittest.main()
