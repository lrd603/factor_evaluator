# Momentum Final Assessment

20/60/120-day signals remain negative across robustness tests. Adding momentum is tested by Model E against Model A.

| model   | weighting_method    |   OOS_return |   annualized_return |   volatility |     Sharpe |   max_drawdown |   turnover |   transaction_cost |   benchmark_return |   annualized_excess_return |   information_ratio |   tracking_error |      beta |   jensen_alpha |
|:--------|:--------------------|-------------:|--------------------:|-------------:|-----------:|---------------:|-----------:|-------------------:|-------------------:|---------------------------:|--------------------:|-----------------:|----------:|---------------:|
| Model_A | equal_weight        |   -0.0838093 |          -0.0188035 |     0.218479 |  0.0225641 |      -0.51343  |    469.555 |           0.469555 |         -0.0995496 |                  0.0119736 |            0.043923 |         0.272605 | 0.0773644 |     0.00547474 |
| Model_A | rolling_ic_weight   |    0.362548  |           0.0693911 |     0.233742 |  0.405068  |      -0.408537 |    515.254 |           0.515254 |         -0.0995496 |                  0.101725  |            0.363954 |         0.2795   | 0.126575  |     0.0955729  |
| Model_A | rolling_icir_weight |    0.353718  |           0.0678842 |     0.23812  |  0.396095  |      -0.42801  |    529.771 |           0.529771 |         -0.0995496 |                  0.101362  |            0.358275 |         0.282917 | 0.12887   |     0.095226   |
| Model_E | equal_weight        |   -0.313031  |          -0.0781994 |     0.231563 | -0.235785  |      -0.603176 |    431.815 |           0.431815 |         -0.0995496 |                 -0.0475552 |           -0.171019 |         0.27807  | 0.123133  |    -0.0537317  |
| Model_E | rolling_ic_weight   |    0.261862  |           0.0517348 |     0.248034 |  0.329012  |      -0.472908 |    461.067 |           0.461067 |         -0.0995496 |                  0.08865   |            0.301794 |         0.293743 | 0.106237  |     0.0823545  |
| Model_E | rolling_icir_weight |    0.291837  |           0.0571031 |     0.250418 |  0.348637  |      -0.470778 |    483.396 |           0.483396 |         -0.0995496 |                  0.0943488 |            0.32026  |         0.294601 | 0.117107  |     0.0881299  |

Conclusion: traditional medium-short momentum should **not** be used as a positive factor in this 2018–2025 sample. Empirical classification: **PERSISTENT_REVERSAL**.
