# V4 Empirical Research Report

## 1. Research Question
Stability of low-volatility and momentum signals, and translation into quantile and OOS performance.

## 2. Data
2018-01-29 to 2025-12-24; 200 real A-share histories.

## 3. Universe Construction
Stable SHA256 sample from a real current ALL_A list. Later listings enter only after their first observation. Historical delistings remain incomplete.

## 4. Factors
momentum_20, momentum_60, volatility_20, volatility_60, volume_change_20. No financial factors.

## 5. Methodology
Winsorization, cross-sectional normalization, direction alignment, IC/Rank IC, quantiles and walk-forward. PIT exposure was unavailable, so neutralization was intentionally skipped.

## 6. IC Results
| factor_name      |   full_period_mean_rank_ic |   yearly_same_sign_ratio |   best_year |   worst_year |   std_across_yearly_rank_ic |
|:-----------------|---------------------------:|-------------------------:|------------:|-------------:|----------------------------:|
| momentum_20      |                 -0.0565646 |                        1 |        2020 |         2019 |                   0.0283453 |
| momentum_60      |                 -0.0516875 |                        1 |        2018 |         2024 |                   0.0292262 |
| volatility_20    |                  0.0655651 |                        1 |        2023 |         2020 |                   0.0179955 |
| volatility_60    |                  0.0570626 |                        1 |        2023 |         2019 |                   0.0181494 |
| volume_change_20 |                 -0.0372503 |                        1 |        2021 |         2025 |                   0.0160723 |

## 7. Factor Decay
See `factor_decay.csv`.

## 8. Yearly Stability
See `yearly_factor_ic.csv`.

## 9. Quantile Results
See `quantile_analysis.csv`.

## 10. Regime Analysis
{'momentum_20_60d_expected_sign_ratio': 0.9041980624327234, 'momentum_20_120d_expected_sign_ratio': 0.9688542825361512, 'momentum_60_60d_expected_sign_ratio': 0.8745874587458746, 'momentum_60_120d_expected_sign_ratio': 0.9891922639362912, 'volatility_20_60d_expected_sign_ratio': 0.9343379978471474, 'volatility_20_120d_expected_sign_ratio': 1.0, 'volatility_60_60d_expected_sign_ratio': 0.9284928492849285, 'volatility_60_120d_expected_sign_ratio': 0.9880546075085325}

## 11. Factor Correlation
| factor_1      | factor_2         |   mean_correlation |   p95_absolute_correlation | high_correlation_pair   |
|:--------------|:-----------------|-------------------:|---------------------------:|:------------------------|
| momentum_20   | momentum_60      |          0.489     |                   0.698874 | False                   |
| momentum_20   | volatility_20    |         -0.207773  |                   0.546616 | False                   |
| momentum_20   | volatility_60    |         -0.0462143 |                   0.440992 | False                   |
| momentum_20   | volume_change_20 |          0.246907  |                   0.432312 | False                   |
| momentum_60   | volatility_20    |         -0.307116  |                   0.619655 | False                   |
| momentum_60   | volatility_60    |         -0.256818  |                   0.577641 | False                   |
| momentum_60   | volume_change_20 |          0.0567873 |                   0.27017  | False                   |
| volatility_20 | volatility_60    |          0.789085  |                   0.872842 | True                    |
| volatility_20 | volume_change_20 |          0.0564367 |                   0.300184 | False                   |
| volatility_60 | volume_change_20 |          0.0780586 |                   0.314153 | False                   |

## 12. Walk-Forward OOS
| method              |   annualized_return |   volatility |     sharpe |   max_drawdown |   information_ratio |   turnover |   transaction_cost |   benchmark_excess_return |
|:--------------------|--------------------:|-------------:|-----------:|---------------:|--------------------:|-----------:|-------------------:|--------------------------:|
| equal_weight        |         -0.00985859 |     0.216343 | -0.0455692 |      -0.479792 |            -1.35069 |    323.518 |           0.323518 |                 -0.788893 |
| static_weight       |         -0.00985859 |     0.216343 | -0.0455692 |      -0.479792 |            -1.35069 |    323.518 |           0.323518 |                 -0.788893 |
| rolling_ic_weight   |          0.0529213  |     0.251179 |  0.210691  |      -0.484616 |            -1.12206 |    398.83  |           0.39883  |                 -0.466559 |
| rolling_icir_weight |          0.0580508  |     0.250715 |  0.231541  |      -0.476659 |            -1.08413 |    424.785 |           0.424785 |                 -0.444616 |

## 13. Low-Volatility Finding
See `low_volatility_study.md`.

## 14. Momentum Finding
See `momentum_study.md`.

## 15. Limitations
Current-list survivorship bias; listing dates at/before the research start are left-censored; no reliable PIT market-cap/industry exposures.

## 16. Conclusion
Research validity: **FORMAL_EMPIRICAL_RESEARCH**. Results are statistical associations and are not causal claims.
