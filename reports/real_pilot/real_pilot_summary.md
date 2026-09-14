# Real A-Share Pilot Research

> **Research validity status: SMALL_SAMPLE_RESEARCH**

- Period: 2024-01-01 to 2025-12-31
- Requested stocks: 50
- Successful real downloads: 50
- Average daily cross-section: 49.2
- Real market data: true
- Financial factors included: false (market-based pilot only)
- Neutralization validated: false (no reliable PIT industry/market-cap exposures)
- Walk-forward real pilot: not_run_due_to_time

## Five-day IC summary

| factor_name      |   period |    mean_ic |   mean_rank_ic |   ic_std |   rank_ic_std |      icir |   rank_icir |   positive_ic_ratio |   t_stat |     p_value |   observations |
|:-----------------|---------:|-----------:|---------------:|---------:|--------------:|----------:|------------:|--------------------:|---------:|------------:|---------------:|
| momentum_20      |        5 | -0.0584265 |     -0.0688194 | 0.247569 |      0.210021 | -0.236001 |   -0.327678 |            0.426593 | -4.48402 | 7.32504e-06 |            361 |
| momentum_60      |        5 | -0.053419  |     -0.0736449 | 0.237043 |      0.215117 | -0.225355 |   -0.342349 |            0.437673 | -4.28175 | 1.85429e-05 |            361 |
| volatility_20    |        5 |  0.0463063 |      0.0705545 | 0.252328 |      0.243667 |  0.183517 |    0.289552 |            0.573407 |  3.48681 | 0.000488811 |            361 |
| volatility_60    |        5 |  0.0296432 |      0.0542781 | 0.263375 |      0.268644 |  0.112551 |    0.202045 |            0.584488 |  2.13848 | 0.0324779   |            361 |
| volume_change_20 |        5 | -0.0441537 |     -0.0566791 | 0.225566 |      0.183334 | -0.195746 |   -0.309157 |            0.426593 | -3.71918 | 0.000199871 |            361 |

## IC decay (5/10/20/40 trading days)

| factor_name      |   period |    mean_ic |   mean_rank_ic |       icir |   rank_icir |   positive_ic_ratio |
|:-----------------|---------:|-----------:|---------------:|-----------:|------------:|--------------------:|
| momentum_20      |        5 | -0.0584265 |     -0.0688194 | -0.236001  |   -0.327678 |            0.426593 |
| momentum_20      |       10 | -0.0630561 |     -0.067165  | -0.274606  |   -0.329771 |            0.424157 |
| momentum_20      |       20 | -0.0839339 |     -0.0869763 | -0.412332  |   -0.441713 |            0.387283 |
| momentum_20      |       40 | -0.0682681 |     -0.0775014 | -0.393196  |   -0.442725 |            0.374233 |
| momentum_60      |        5 | -0.053419  |     -0.0736449 | -0.225355  |   -0.342349 |            0.437673 |
| momentum_60      |       10 | -0.0638996 |     -0.0908119 | -0.278976  |   -0.436643 |            0.412921 |
| momentum_60      |       20 | -0.0723634 |     -0.107781  | -0.377364  |   -0.609552 |            0.387283 |
| momentum_60      |       40 | -0.0779925 |     -0.117437  | -0.432024  |   -0.619523 |            0.325153 |
| volatility_20    |        5 |  0.0463063 |      0.0705545 |  0.183517  |    0.289552 |            0.573407 |
| volatility_20    |       10 |  0.057494  |      0.0700107 |  0.238307  |    0.292929 |            0.595506 |
| volatility_20    |       20 |  0.0554674 |      0.0533375 |  0.249098  |    0.225077 |            0.563584 |
| volatility_20    |       40 |  0.0267336 |      0.0572329 |  0.113251  |    0.222381 |            0.542945 |
| volatility_60    |        5 |  0.0296432 |      0.0542781 |  0.112551  |    0.202045 |            0.584488 |
| volatility_60    |       10 |  0.0289864 |      0.0514475 |  0.110617  |    0.197757 |            0.553371 |
| volatility_60    |       20 |  0.0192395 |      0.0477609 |  0.076949  |    0.179519 |            0.526012 |
| volatility_60    |       40 |  0.0106979 |      0.0459848 |  0.0467646 |    0.166442 |            0.496933 |
| volume_change_20 |        5 | -0.0441537 |     -0.0566791 | -0.195746  |   -0.309157 |            0.426593 |
| volume_change_20 |       10 | -0.0553339 |     -0.0551673 | -0.286589  |   -0.327061 |            0.339888 |
| volume_change_20 |       20 | -0.0598989 |     -0.0661188 | -0.356622  |   -0.41899  |            0.343931 |
| volume_change_20 |       40 | -0.0466078 |     -0.0577723 | -0.284709  |   -0.342711 |            0.334356 |

## Five-day quantile monotonicity and Q5-Q1

| factor_name      | monotonic_increasing   |        Q5-Q1 |
|:-----------------|:-----------------------|-------------:|
| momentum_20      | False                  | -0.00609357  |
| momentum_60      | False                  | -0.00341917  |
| volatility_20    | False                  |  0.0008206   |
| volatility_60    | False                  | -0.000892358 |
| volume_change_20 | False                  | -0.0018966   |

## Limitations

- Candidate stocks come from a current real A-share list; historical delistings are unavailable, so survivorship bias remains.
- Listing date is inferred from the first downloaded observation and may predate the requested window.
- No PIT market cap or industry exposure was used; neutralization was intentionally skipped.
- Failed endpoints and all real-endpoint fallbacks are recorded in `real_pilot_data_quality.json`.

## Stability and Regime Diagnostics

### Yearly direction

- momentum_20: same sign (2024=-0.0766, 2025=-0.0648)
- momentum_60: same sign (2024=-0.0612, 2025=-0.0801)
- volatility_20: same sign (2024=0.0586, 2025=0.0767)
- volatility_60: same sign (2024=0.0544, 2025=0.0542)
- volume_change_20: same sign (2024=-0.0790, 2025=-0.0451)

### Momentum diagnosis

- momentum_20: momentum broadly ineffective in this sample.
- momentum_60: momentum broadly ineffective in this sample.
- Both momentum signals remain negative through 40 days, so this sample does not support a short-only reversal interpretation.

### Low-volatility diagnosis

- volatility_20 Rank IC by horizon: 1D=0.0561, 5D=0.0706, 10D=0.0700, 20D=0.0533, 40D=0.0572.
- Low volatility is more horizon-stable than momentum, but yearly consistency and quintile spreads must still be considered before treating it as robust.

### Redundancy

- Pairs with absolute average daily Spearman correlation above 0.8: none.

These results describe the cached 50-stock pilot only and do not represent the full A-share market.
