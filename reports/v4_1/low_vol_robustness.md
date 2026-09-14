# Low-Volatility Robustness

Conclusion: **ROBUST**

|                                                |   mean_rank_ic |       Q5-Q1 |   monotonicity |
|:-----------------------------------------------|---------------:|------------:|---------------:|
| ('volatility_10', 'mad_zscore')                |      0.0740647 | 0.00383415  |           0.65 |
| ('volatility_10', 'percentile_rank')           |      0.0744533 | 0.00383415  |           0.65 |
| ('volatility_10', 'percentile_zscore')         |      0.0744632 | 0.00383415  |           0.65 |
| ('volatility_20', 'mad_zscore')                |      0.0702151 | 0.00318571  |           0.5  |
| ('volatility_20', 'percentile_rank')           |      0.0703812 | 0.00318571  |           0.5  |
| ('volatility_20', 'percentile_zscore')         |      0.0703876 | 0.00318571  |           0.5  |
| ('volatility_20', 'remove_bottom_10pct_ADV20') |      0.062511  | 0.00177797  |           0.5  |
| ('volatility_20', 'remove_bottom_20pct_ADV20') |      0.0625839 | 0.00131723  |           0.75 |
| ('volatility_40', 'mad_zscore')                |      0.0676017 | 0.0014888   |           0.5  |
| ('volatility_40', 'percentile_rank')           |      0.0677629 | 0.0014888   |           0.5  |
| ('volatility_40', 'percentile_zscore')         |      0.0677687 | 0.0014888   |           0.5  |
| ('volatility_60', 'mad_zscore')                |      0.0647969 | 3.88156e-05 |           0.45 |
| ('volatility_60', 'percentile_rank')           |      0.0648671 | 3.88156e-05 |           0.45 |
| ('volatility_60', 'percentile_zscore')         |      0.0648727 | 3.88156e-05 |           0.45 |
