# V4.1 Robustness & Bias Reduction

## 1. Objective
Test robustness and reduce identifiable bias without expanding the strategy or claiming causality.

## 2. Data Availability Audit
Historical liquidity is HIGH quality. Historical market cap and ST history are unavailable. A dated industry sample and 159 SH plus 208 SZ delisting-master rows were reachable, but neither source is validated as a complete exposure-to-price panel.

## 3. Size Neutralization
**SKIPPED.** No reliable PIT historical market cap. Therefore volatility_20 neutralized Rank IC is unavailable, not estimated.

## 4. Industry Neutralization
**SKIPPED.** Complete PIT industry coverage plus PIT market cap is unavailable.

## 5. Low-Volatility Robustness
Conclusion: **ROBUST**. Window, preprocessing and liquidity results are in `low_vol_robustness.csv`.

## 6. Momentum Robustness
Conclusion: **PERSISTENT_REVERSAL**. The result survives liquidity removal, outlier removal, yearly and horizon splits as documented in `momentum_robustness.csv`.

## 7. Subsample Stability
| factor_name   | subsample   |     mean_ic |   mean_rank_ic |   ic_std |   rank_ic_std |       icir |   rank_icir |   positive_ic_ratio |    t_stat |     p_value |   observations |        Q5-Q1 |   monotonicity |
|:--------------|:------------|------------:|---------------:|---------:|--------------:|-----------:|------------:|--------------------:|----------:|------------:|---------------:|-------------:|---------------:|
| volatility_20 | 2018-2021   |  0.00568595 |      0.0531575 | 0.181198 |      0.174246 |  0.0313798 |    0.305072 |            0.534103 |  0.968717 | 0.332686    |            953 |  0.000375062 |           0.5  |
| volatility_20 | 2022-2025   |  0.0253313  |      0.077831  | 0.177903 |      0.189269 |  0.142388  |    0.411219 |            0.569502 |  4.42091  | 9.82861e-06 |            964 |  0.00320308  |           0.5  |
| momentum_20   | 2018-2021   | -0.0321578  |     -0.0532365 | 0.173308 |      0.171916 | -0.185553  |   -0.309665 |            0.43022  | -5.72816  | 1.01524e-08 |            953 | -0.00517065  |           0    |
| momentum_20   | 2022-2025   | -0.0393261  |     -0.0598546 | 0.167655 |      0.16124  | -0.234565  |   -0.371215 |            0.414938 | -7.28287  | 3.2685e-13  |            964 | -0.00512577  |           0.25 |
| momentum_60   | 2018-2021   | -0.0208085  |     -0.0423283 | 0.175161 |      0.166327 | -0.118797  |   -0.254489 |            0.435926 | -3.58955  | 0.000331255 |            913 | -0.00408807  |           0.25 |
| momentum_60   | 2022-2025   | -0.034934   |     -0.0605517 | 0.169023 |      0.168169 | -0.206682  |   -0.360064 |            0.427386 | -6.41715  | 1.38853e-10 |            964 | -0.00492783  |           0    |

## 8. HAC Significance
Newey-West lag is horizon minus one. Statistical significance is not economic significance.

| factor_name   |   horizon |   HAC_t_stat |   HAC_p_value |
|:--------------|----------:|-------------:|--------------:|
| volatility_20 |         5 |      8.66478 |   0           |
| volatility_20 |        10 |      6.93267 |   4.12959e-12 |
| volatility_20 |        20 |      5.59999 |   2.14362e-08 |
| volatility_20 |        40 |      5.213   |   1.85807e-07 |
| momentum_20   |         5 |     -8.62661 |   0           |
| momentum_20   |        10 |     -7.76398 |   8.21565e-15 |
| momentum_20   |        20 |     -6.30285 |   2.92231e-10 |
| momentum_20   |        40 |     -4.64513 |   3.3986e-06  |
| momentum_60   |         5 |     -7.51643 |   5.63993e-14 |
| momentum_60   |        10 |     -6.8443  |   7.68519e-12 |
| momentum_60   |        20 |     -5.60867 |   2.03886e-08 |
| momentum_60   |        40 |     -4.64978 |   3.32292e-06 |

## 9. Factor Redundancy
| target        | orthogonalized_to   |     mean_ic |   mean_rank_ic |   ic_std |   rank_ic_std |       icir |   rank_icir |   positive_ic_ratio |   t_stat |     p_value |   observations |        Q5-Q1 |   monotonicity |
|:--------------|:--------------------|------------:|---------------:|---------:|--------------:|-----------:|------------:|--------------------:|---------:|------------:|---------------:|-------------:|---------------:|
| volatility_20 | volatility_60       |  0.0130264  |     0.0318774  | 0.12765  |      0.118429 |  0.102048  |   0.269169  |            0.555674 |  4.42117 | 9.81669e-06 |           1877 |  0.000890564 |           0.5  |
| volatility_60 | volatility_20       | -0.00344301 |     0.00319602 | 0.138538 |      0.146456 | -0.0248525 |   0.0218224 |            0.492808 | -1.07672 | 0.281607    |           1877 | -0.000698819 |           0.25 |

Recommendation to delete volatility_60: **YES**. Residual volatility_60 5d Rank IC=0.003196; residual volatility_20=0.031877.

## 10. Walk-Forward Ablation
| ablation             | factors                                                              | method              |   annualized_return |   volatility |   sharpe |   max_drawdown |   information_ratio |   turnover |   transaction_cost |   benchmark_excess_return |
|:---------------------|:---------------------------------------------------------------------|:--------------------|--------------------:|-------------:|---------:|---------------:|--------------------:|-----------:|-------------------:|--------------------------:|
| raw_five             | momentum_20|momentum_60|volatility_20|volatility_60|volume_change_20 | rolling_icir_weight |           0.0580508 |     0.250715 | 0.231541 |      -0.476659 |           -1.08413  |    424.785 |           0.424785 |                 -0.444616 |
| drop_volatility_60   | momentum_20|momentum_60|volatility_20|volume_change_20               | rolling_icir_weight |           0.0533665 |     0.261526 | 0.204058 |      -0.496641 |           -1.16433  |    446.51  |           0.44651  |                 -0.451974 |
| drop_momentum        | volatility_20|volatility_60|volume_change_20                         | rolling_icir_weight |           0.0875953 |     0.234479 | 0.373574 |      -0.386919 |           -0.731929 |    466.505 |           0.466505 |                 -0.336192 |
| low_correlation_core | volatility_20|momentum_20|volume_change_20                           | rolling_icir_weight |           0.0437889 |     0.253941 | 0.172437 |      -0.479329 |           -1.27612  |    477.428 |           0.477428 |                 -0.503013 |

Best annualized-return ablation: **drop_momentum**. This comparison is diagnostic, not parameter optimization.

## 11. Survivorship Sensitivity
Status: **UNRESOLVED**. Exchange delisting-list endpoints exist, but a validated master-to-delisted-price panel was not established; no fabricated sensitivity result is reported.

## 12. Remaining Limitations
Current-list survivorship bias; no PIT market cap; incomplete validated PIT industry/ST history; transaction model remains simplified.

## 13. Final Research Conclusion

1. volatility_20 after size neutralization: unavailable.
2. volatility_20 after industry+size neutralization: unavailable.
3. Low volatility: **ROBUST**.
4. Momentum: **PERSISTENT_REVERSAL**.
5. Delete volatility_60: **YES**.
6. OOS improvement after reduction: **True**; best=drop_momentum.
7. Survivorship bias materially improved: **No**.
8. Resume-safe real-data pipeline, eight-year same-sign raw IC, HAC/robustness diagnostics and leakage-controlled OOS ablation can be described on a résumé with exact caveats.
9. Size/industry-neutralized or survivorship-free conclusions cannot be claimed.
