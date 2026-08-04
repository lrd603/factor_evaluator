import tempfile
import unittest
from pathlib import Path

import pandas as pd

from factors.generator import OUTPUT_COLUMNS, generate_factor_data


class FactorGeneratorTests(unittest.TestCase):
    def test_generate_factor_data(self):
        dates = pd.date_range("2024-01-01", periods=30, freq="D")
        raw = pd.DataFrame(
            {
                "date": dates,
                "stock": ["000001"] * 30,
                "open": range(100, 130),
                "high": range(101, 131),
                "low": range(99, 129),
                "close": range(100, 130),
                "volume": range(1000, 1030),
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "raw.csv"
            output_path = Path(temp_dir) / "factors.csv"
            raw.to_csv(input_path, index=False)
            result = generate_factor_data(input_path, output_path)
            saved = pd.read_csv(output_path, dtype={"stock": str})

        self.assertEqual(result.columns.tolist(), OUTPUT_COLUMNS)
        self.assertEqual(saved.columns.tolist(), OUTPUT_COLUMNS)
        self.assertEqual(set(result["factor_name"]), {"momentum", "volatility", "volume_factor"})
        self.assertEqual(result["stock"].unique().tolist(), ["000001"])
        # volume_factor is available on observation 20; momentum and
        # volatility require the preceding 20 returns and start on day 21.
        self.assertEqual(len(result), 16)

        first_momentum = result[result["factor_name"] == "momentum"].iloc[0]
        self.assertAlmostEqual(first_momentum["factor_value"], 120 / 100 - 1)
        self.assertAlmostEqual(first_momentum["return"], 125 / 120 - 1)


if __name__ == "__main__":
    unittest.main()
