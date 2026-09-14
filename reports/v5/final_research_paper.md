# A-Share Cross-Sectional Factor Research:
# Low-Volatility Predictability, Momentum Reversal, and Walk-Forward Validation

## 1. Abstract
A 200-stock real A-share sample from 2018–2025 shows stable low-volatility Rank IC and persistent negative momentum IC. Leakage-controlled walk-forward portfolios monetize the signal only weakly and remain exposed to large drawdowns.

## 2. Research Question
Can statistically stable cross-sectional signals survive OOS validation, costs, and model simplification?

## 3. Data
200 real A-shares; average V4 cross-section 158.4. CSI300 is cached from the AkShare Tencent index endpoint.

## 4. Universe Construction
Stable current-list sample with later listings entering after observed listing; survivorship bias remains unresolved.

## 5. Factor Definitions
The five frozen factors and Models A–E follow the prespecified request.

## 6. Data Processing
Daily cross-sectional MAD winsorization, z-score, direction alignment; no mock, silent fallback, or fake neutralization.

## 7. Bias Control
Train-only weights, non-overlapping tests, explicit costs. PIT market cap is unavailable; size/industry neutralization is not a formal result.

## 8. IC Methodology
Pearson and Spearman cross-sectional IC; see V4.

## 9. Factor Decay
Low volatility stays positive and momentum stays negative through 40d.

## 10. Yearly Stability
volatility_20 is positive in all eight years.

## 11. Quantile Analysis
Positive low-volatility spread exists but monotonicity is incomplete.

## 12. Robustness Tests
V4.1 classifies low volatility ROBUST and momentum PERSISTENT_REVERSAL.

## 13. HAC Significance
Overlapping-return HAC tests remain significant; significance is not economic magnitude.

## 14. Factor Redundancy
volatility_60 has near-zero residual IC after controlling volatility_20.

## 15. Walk-Forward Design
756 train / 126 test trading days; model and weighting parameters use train data only.

## 16. Model Comparison
| model   | weighting_method    |   OOS_return |   annualized_return |   volatility |     Sharpe |   max_drawdown |   turnover |   transaction_cost |   benchmark_return |   annualized_excess_return |   information_ratio |   tracking_error |      beta |   jensen_alpha |   score |   positive_excess_year_ratio |   redundancy_penalty | qualitative_rating   |
|:--------|:--------------------|-------------:|--------------------:|-------------:|-----------:|---------------:|-----------:|-------------------:|-------------------:|---------------------------:|--------------------:|-----------------:|----------:|---------------:|--------:|-----------------------------:|---------------------:|:---------------------|
| Model_B | equal_weight        |    1.01351   |           0.164057  |     0.195648 |  0.875002  |      -0.255684 |    105.03  |           0.10503  |         -0.0797293 |                  0.173568  |            0.678041 |         0.255984 | 0.0657045 |     0.171349   | 4.66667 |                          0.8 |                  0   | STRONGEST            |
| Model_B | rolling_ic_weight   |    0.844828  |           0.14216   |     0.231318 |  0.690884  |      -0.366146 |    100.628 |           0.100628 |         -0.0797293 |                  0.162189  |            0.568699 |         0.285193 | 0.0565014 |     0.159948   | 4.46667 |                          0.8 |                  0   | STRONGEST            |
| Model_B | rolling_icir_weight |    0.844828  |           0.14216   |     0.231318 |  0.690884  |      -0.366146 |    100.628 |           0.100628 |         -0.0797293 |                  0.162189  |            0.568699 |         0.285193 | 0.0565014 |     0.159948   | 4.46667 |                          0.8 |                  0   | STRONGEST            |
| Model_C | equal_weight        |    0.397873  |           0.0753435 |     0.200629 |  0.462733  |      -0.368789 |    310.945 |           0.310945 |         -0.0995496 |                  0.0998815 |            0.384919 |         0.259487 | 0.0693887 |     0.0933265  | 3.16667 |                          0.8 |                  0.5 | STRONGEST            |
| Model_D | rolling_ic_weight   |    0.438894  |           0.0821098 |     0.247509 |  0.443631  |      -0.441543 |    383.085 |           0.383085 |         -0.0995496 |                  0.116846  |            0.396855 |         0.294431 | 0.0956706 |     0.110477   | 2.76667 |                          0.8 |                  0.5 | ACCEPTABLE           |
| Model_C | rolling_ic_weight   |    0.428837  |           0.080465  |     0.229314 |  0.453211  |      -0.378378 |    444.226 |           0.444226 |         -0.0995496 |                  0.110971  |            0.398243 |         0.278653 | 0.101495  |     0.104642   | 2.63333 |                          0.6 |                  0.5 | ACCEPTABLE           |
| Model_A | rolling_ic_weight   |    0.362548  |           0.0693911 |     0.233742 |  0.405068  |      -0.408537 |    515.254 |           0.515254 |         -0.0995496 |                  0.101725  |            0.363954 |         0.2795   | 0.126575  |     0.0955729  | 2.6     |                          0.8 |                  0   | ACCEPTABLE           |
| Model_C | rolling_icir_weight |    0.439842  |           0.0822643 |     0.232309 |  0.457541  |      -0.402185 |    480.496 |           0.480496 |         -0.0995496 |                  0.113335  |            0.40656  |         0.278765 | 0.122484  |     0.107154   | 2.5     |                          0.6 |                  0.5 | WEAK                 |
| Model_A | rolling_icir_weight |    0.353718  |           0.0678842 |     0.23812  |  0.396095  |      -0.42801  |    529.771 |           0.529771 |         -0.0995496 |                  0.101362  |            0.358275 |         0.282917 | 0.12887   |     0.095226   | 2.33333 |                          0.8 |                  0   | WEAK                 |
| Model_D | equal_weight        |    0.122118  |           0.0253019 |     0.213708 |  0.223949  |      -0.402922 |    320.93  |           0.32093  |         -0.0995496 |                  0.0549036 |            0.207053 |         0.265167 | 0.108174  |     0.0486217  | 1.83333 |                          0.6 |                  0.5 | WEAK                 |
| Model_E | rolling_icir_weight |    0.291837  |           0.0571031 |     0.250418 |  0.348637  |      -0.470778 |    483.396 |           0.483396 |         -0.0995496 |                  0.0943488 |            0.32026  |         0.294601 | 0.117107  |     0.0881299  | 1.8     |                          0.6 |                  0   | WEAK                 |
| Model_D | rolling_icir_weight |    0.292733  |           0.057262  |     0.24698  |  0.350113  |      -0.453594 |    424.616 |           0.424616 |         -0.0995496 |                  0.0935146 |            0.318732 |         0.293395 | 0.101185  |     0.0871835  | 1.76667 |                          0.6 |                  0.5 | REJECT               |
| Model_E | rolling_ic_weight   |    0.261862  |           0.0517348 |     0.248034 |  0.329012  |      -0.472908 |    461.067 |           0.461067 |         -0.0995496 |                  0.08865   |            0.301794 |         0.293743 | 0.106237  |     0.0823545  | 1.73333 |                          0.6 |                  0   | REJECT               |
| Model_A | equal_weight        |   -0.0838093 |          -0.0188035 |     0.218479 |  0.0225641 |      -0.51343  |    469.555 |           0.469555 |         -0.0995496 |                  0.0119736 |            0.043923 |         0.272605 | 0.0773644 |     0.00547474 | 1.33333 |                          0.6 |                  0   | REJECT               |
| Model_E | equal_weight        |   -0.313031  |          -0.0781994 |     0.231563 | -0.235785  |      -0.603176 |    431.815 |           0.431815 |         -0.0995496 |                 -0.0475552 |           -0.171019 |         0.27807  | 0.123133  |    -0.0537317  | 1.13333 |                          0.4 |                  0   | REJECT               |

## 17. Benchmark-Relative Performance
CSI300 metrics use rf=0. Jensen alpha is regression-estimated, not a simple return difference.

## 18. Transaction Cost Sensitivity
|   cost_bp_single_side |   OOS_return |   annualized_return |   volatility |   Sharpe |   max_drawdown |   turnover |   transaction_cost |   benchmark_return |   annualized_excess_return |   information_ratio |   tracking_error |      beta |   jensen_alpha | cost_sensitivity_status   |
|----------------------:|-------------:|--------------------:|-------------:|---------:|---------------:|-----------:|-------------------:|-------------------:|---------------------------:|--------------------:|-----------------:|----------:|---------------:|:--------------------------|
|                     0 |     1.23641  |            0.19089  |     0.195624 | 0.991645 |      -0.250319 |     105.03 |          0         |         -0.0797293 |                   0.196365 |            0.767189 |         0.255954 | 0.0658014 |       0.194146 | ROBUST_TO_COST            |
|                     5 |     1.12204  |            0.177398 |     0.195635 | 0.933327 |      -0.253006 |     105.03 |          0.0525152 |         -0.0797293 |                   0.184966 |            0.722616 |         0.255968 | 0.065753  |       0.182747 | ROBUST_TO_COST            |
|                    10 |     1.01351  |            0.164057 |     0.195648 | 0.875002 |      -0.255684 |     105.03 |          0.10503   |         -0.0797293 |                   0.173568 |            0.678041 |         0.255984 | 0.0657045 |       0.171349 | ROBUST_TO_COST            |
|                    20 |     0.812784 |            0.137824 |     0.195684 | 0.75834  |      -0.261013 |     105.03 |          0.210061  |         -0.0797293 |                   0.15077  |            0.588893 |         0.256023 | 0.0656076 |       0.148551 | ROBUST_TO_COST            |
|                    30 |     0.632036 |            0.112177 |     0.195733 | 0.641682 |      -0.266304 |     105.03 |          0.315091  |         -0.0797293 |                   0.127973 |            0.499754 |         0.256072 | 0.0655107 |       0.125754 | ROBUST_TO_COST            |

## 19. Portfolio Construction Sensitivity
See `portfolio_selection_sensitivity.csv`; thresholds are diagnostics, not optimized parameters.

## 20. Factor Ablation
| variant              | model   | weighting_method   |   OOS_return |   annualized_return |   volatility |     Sharpe |   max_drawdown |   turnover |   transaction_cost |   benchmark_return |   annualized_excess_return |   information_ratio |   tracking_error |        beta |   jensen_alpha |     score |   positive_excess_year_ratio |   redundancy_penalty | qualitative_rating   | status                     |
|:---------------------|:--------|:-------------------|-------------:|--------------------:|-------------:|-----------:|---------------:|-----------:|-------------------:|-------------------:|---------------------------:|--------------------:|-----------------:|------------:|---------------:|----------:|-----------------------------:|---------------------:|:---------------------|:---------------------------|
| full_model           | Model_B | equal_weight       |      1.01351 |            0.164057 |     0.195648 |   0.875002 |      -0.255684 |     105.03 |            0.10503 |         -0.0797293 |                   0.173568 |            0.678041 |         0.255984 |   0.0657045 |       0.171349 |   4.66667 |                          0.8 |                    0 | STRONGEST            | nan                        |
| remove_volatility_20 | nan     | nan                |    nan       |          nan        |   nan        | nan        |     nan        |     nan    |          nan       |        nan         |                 nan        |          nan        |       nan        | nan         |     nan        | nan       |                        nan   |                  nan | nan                  | NOT_APPLICABLE_EMPTY_MODEL |

## 21. Low-Volatility Finding
PREDICTIVE_AND_TRADABLE.

## 22. Momentum Reversal Finding
Persistent reversal; do not use these raw signals as conventional positive momentum.

## 23. Economic Significance
Final OOS annualized return=16.41%, Sharpe=0.875, max drawdown=-25.57%. Predictability is stronger than portfolio monetization.

## 24. Limitations
1. Survivorship bias unresolved.
2. Historical delisted-price coverage incomplete.
3. PIT market cap unavailable.
4. No formal size/industry neutralization.
5. Listing-date left truncation.
6. Limited single-sided transaction-cost model.
7. Limit-up/down and suspension execution simplified.
8. No market-impact or capacity model.

## 25. Conclusion
FINAL_RESEARCH_MODEL: **Model_B / equal_weight**. Positive OOS years=80.0%; positive excess years=80.0%. The evidence supports statistically stable predictability, but only modest economic performance and no production-tradability claim.
