import unittest

from evaluator.factor_score import calculate_factor_score


class FactorScoreTests(unittest.TestCase):
    def test_negative_drawdown_is_penalized(self):
        score = calculate_factor_score(
            {
                "ICIR": 0,
                "Long Short Return": 0,
                "Sharpe Ratio": 0,
                "Win Rate": 0.5,
                "Max Drawdown": -0.3,
            }
        )
        self.assertEqual(score, 0.0)

    def test_daily_return_is_annualized_and_direction_neutral(self):
        positive = calculate_factor_score(
            {
                "ICIR": 0.25,
                "Long Short Return": 0.001,
                "Sharpe Ratio": 1,
                "Win Rate": 0.6,
                "Max Drawdown": -0.1,
            }
        )
        negative = calculate_factor_score(
            {
                "ICIR": -0.25,
                "Long Short Return": -0.001,
                "Sharpe Ratio": -1,
                "Win Rate": 0.4,
                "Max Drawdown": -0.1,
            }
        )
        self.assertEqual(positive, negative)
        self.assertGreater(positive, 50)

    def test_score_is_capped_at_one_hundred(self):
        score = calculate_factor_score(
            {
                "ICIR": 100,
                "Long Short Return": 1,
                "Sharpe Ratio": 100,
                "Win Rate": 1,
                "Max Drawdown": 0,
            }
        )
        self.assertEqual(score, 100.0)


if __name__ == "__main__":
    unittest.main()
