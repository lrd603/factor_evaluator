# Low-Volatility Study

- Full-period volatility_20 Rank IC: 0.065565
- Positive IC ratio: 0.552
- Rolling expected-sign stability: {'momentum_20_60d_expected_sign_ratio': 0.9041980624327234, 'momentum_20_120d_expected_sign_ratio': 0.9688542825361512, 'momentum_60_60d_expected_sign_ratio': 0.8745874587458746, 'momentum_60_120d_expected_sign_ratio': 0.9891922639362912, 'volatility_20_60d_expected_sign_ratio': 0.9343379978471474, 'volatility_20_120d_expected_sign_ratio': 1.0, 'volatility_60_60d_expected_sign_ratio': 0.9284928492849285, 'volatility_60_120d_expected_sign_ratio': 0.9880546075085325}
- Most stable factor by yearly sign consistency, then |full Rank IC| / yearly standard deviation: volatility_20

## Yearly Rank IC

|   year |   mean_rank_ic |
|-------:|---------------:|
|   2018 |      0.0444555 |
|   2019 |      0.051928  |
|   2020 |      0.0438057 |
|   2021 |      0.0717299 |
|   2022 |      0.0662934 |
|   2023 |      0.0961078 |
|   2024 |      0.078558  |
|   2025 |      0.0702392 |

## Factor decay

| factor_name   |   period |    mean_ic |   mean_rank_ic |   ic_std |   rank_ic_std |       icir |   rank_icir |   positive_ic_ratio |    t_stat |     p_value |   observations |
|:--------------|---------:|-----------:|---------------:|---------:|--------------:|-----------:|------------:|--------------------:|----------:|------------:|---------------:|
| volatility_20 |        1 | 0.00279116 |      0.0452045 | 0.192274 |      0.191589 | 0.0145166  |    0.235946 |            0.50965  | 0.635586  | 0.525046    |           1917 |
| volatility_20 |        5 | 0.015565   |      0.0655651 | 0.17977  |      0.182326 | 0.0865825  |    0.359603 |            0.551904 | 3.79089   | 0.000150107 |           1917 |
| volatility_20 |       10 | 0.0209793  |      0.0725731 | 0.172224 |      0.179766 | 0.121814   |    0.403709 |            0.562238 | 5.3265    | 1.00125e-07 |           1912 |
| volatility_20 |       20 | 0.0259153  |      0.0788156 | 0.17174  |      0.180342 | 0.150898   |    0.437035 |            0.567823 | 6.58095   | 4.67448e-11 |           1902 |
| volatility_20 |       40 | 0.033146   |      0.0897797 | 0.167478 |      0.171171 | 0.197913   |    0.524503 |            0.548884 | 8.58587   | 0           |           1882 |
| volatility_60 |        1 | 0.00027616 |      0.0383919 | 0.193343 |      0.202863 | 0.00142835 |    0.18925  |            0.50666  | 0.0618821 | 0.950657    |           1877 |
| volatility_60 |        5 | 0.00982336 |      0.0570626 | 0.187784 |      0.198167 | 0.0523119  |    0.287953 |            0.522643 | 2.26638   | 0.0234281   |           1877 |
| volatility_60 |       10 | 0.015056   |      0.066801  | 0.183923 |      0.197481 | 0.0818606  |    0.338266 |            0.531517 | 3.54183   | 0.000397362 |           1872 |
| volatility_60 |       20 | 0.0212752  |      0.0773091 | 0.189121 |      0.199684 | 0.112495   |    0.387157 |            0.546724 | 4.85428   | 1.20827e-06 |           1862 |
| volatility_60 |       40 | 0.0268988  |      0.0847988 | 0.183875 |      0.186166 | 0.146288   |    0.455502 |            0.558089 | 6.27848   | 3.41892e-10 |           1842 |

## Quantiles

| factor_name   |   horizon |          Q1 |          Q2 |          Q3 |          Q4 |          Q5 |       Q5-Q1 |   monotonicity |
|:--------------|----------:|------------:|------------:|------------:|------------:|------------:|------------:|---------------:|
| volatility_20 |         1 | 0.000579134 | 0.000621194 | 0.000501284 | 0.000853833 | 0.000730299 | 0.000151165 |           0.5  |
| volatility_20 |         5 | 0.00202341  | 0.00398585  | 0.0032374   | 0.00479408  | 0.0038206   | 0.00179719  |           0.5  |
| volatility_20 |        10 | 0.00483481  | 0.0072387   | 0.00728559  | 0.00893898  | 0.00772691  | 0.0028921   |           0.75 |
| volatility_20 |        20 | 0.00965277  | 0.0148773   | 0.0160989   | 0.0156411   | 0.0141753   | 0.00452253  |           0.5  |

## Walk-forward contribution

Best composite OOS method: rolling_icir_weight. This is portfolio-level evidence, not an isolated causal contribution.

## Pilot comparison

Pilot 2024-2025 Rank IC=0.070554; expanded sample=0.065565.

## Answer

Volatility_20 remains the most stable factor under the declared stability rule.
