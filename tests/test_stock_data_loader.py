import unittest
from unittest.mock import patch

import pandas as pd

from data_loader.stock_data import PRICE_COLUMNS, generate_mock_stock_data, load_stock_data


class StockDataLoaderTests(unittest.TestCase):
    def test_real_data_is_standardized(self):
        raw = pd.DataFrame(
            {
                "date": ["2024-01-03", "2024-01-02"],
                "stock": ["600519", "600519"],
                "open": [11, 10],
                "high": [12, 11],
                "low": [10, 9],
                "close": [11.5, 10.5],
                "volume": [1200, 1000],
            }
        )
        with patch("data_loader.stock_data._fetch_akshare_history", return_value=raw):
            result = load_stock_data("600519", allow_mock=False)

        self.assertEqual(result.columns.tolist(), PRICE_COLUMNS)
        self.assertEqual(result["date"].tolist(), list(pd.to_datetime(["2024-01-02", "2024-01-03"])))
        self.assertEqual(result.attrs["data_source"], "akshare")

    def test_mock_fallback_has_required_columns(self):
        with patch("data_loader.stock_data._fetch_akshare_history", side_effect=RuntimeError("offline")):
            result = load_stock_data("600519", "2024-01-01", "2024-01-10")

        self.assertEqual(result.columns.tolist(), PRICE_COLUMNS)
        self.assertEqual(result.attrs["data_source"], "mock")
        self.assertTrue((result["high"] >= result[["open", "close"]].max(axis=1)).all())
        self.assertTrue((result["low"] <= result[["open", "close"]].min(axis=1)).all())

    def test_mock_is_deterministic(self):
        first = generate_mock_stock_data("000001", "2024-01-01", "2024-01-10")
        second = generate_mock_stock_data("000001", "2024-01-01", "2024-01-10")
        pd.testing.assert_frame_equal(first, second)

    def test_invalid_stock_code_is_rejected(self):
        with self.assertRaises(ValueError):
            load_stock_data("60051")


if __name__ == "__main__":
    unittest.main()
