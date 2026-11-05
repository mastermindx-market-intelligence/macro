# Commodity Vector — calibration report

Split-half boundary: 2013-01-01. Forward horizons: [21, 63, 126] days.

House rule: a relationship is trusted (labeled a *signal* in the UI) only if its forward-return rank-trend holds in the expected direction in the full sample AND survives both halves. The Risk Index is judged on forward DRAWDOWN (its real job). **shock_z** (the residual exogenous-bid detector) is judged directionally: CONFIRMED = bids persist (momentum), INVERTED = bids fade (mean-reversion) — both honest. Anything failing is context-only.


## GOLD — 2001-01-02..2026-09-25 (6472 days)

| Signal | Verdict | full | pre | post | want |
|---|---|--:|--:|--:|--:|
| momentum | **CONTEXT-ONLY** | 0 | -1 | 1 | 1 |
| ts_momentum | **DIRECTIONAL (one half weak)** | 1 | 0 | 1 | 1 |
| structure | **CONTEXT-ONLY** | 0 | -1 | 1 | 1 |
| gsr_pctile | **CONFIRMED** | 1 | 1 | 1 | 1 |
| driver_score | **INVERTED** | -1 | -1 | -1 | 1 |
| shock_z | **DIRECTIONAL (one half weak)** | 1 | 0 | 1 | 1 |
| pos_pctile | **INVERTED** | 1 | 0 | 1 | -1 |
| risk_index (drawdown) | **CONFIRMED near-term risk gauge** | -1 | -1 | -1 | -1 |

### gold · momentum — forward returns by band (full)

| band    |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:--------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-0.5   | 1346 |      60.2 |       1    |      62.5 |       2.36 |       68.4 |        4.96 |
| -0.5..0 | 1122 |      59.7 |       1.34 |      65.5 |       2.63 |       70.1 |        6    |
| 0..0.5  | 1178 |      55.6 |       0.87 |      67.4 |       4.09 |       73.7 |        7.23 |
| >0.5    | 2826 |      55.6 |       1    |      63.5 |       3.22 |       71.7 |        6.79 |

### gold · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down |  477 |      56.2 |       0.71 |      57   |       1.47 |       45.7 |        1.17 |
| down        | 1077 |      53.5 |       0.77 |      59.7 |       1.75 |       67.2 |        4.22 |
| up          | 1261 |      54.6 |       0.73 |      60.2 |       2.69 |       71.6 |        5.66 |
| strong-up   | 3489 |      59.4 |       1.28 |      67.7 |       3.92 |       74.8 |        8.11 |

### gold · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 1719 |      60   |       1.3  |      62.2 |       2.29 |       68.6 |        5.39 |
| neutral      | 1996 |      55.4 |       0.75 |      67.7 |       3.63 |       72.2 |        6.94 |
| constructive | 2757 |      56.9 |       1.08 |      63.2 |       3.21 |       71.8 |        6.54 |

### gold · gsr_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-20   | 1292 |      53.6 |       0.73 |      56.4 |       2.04 |       68.2 |        4.26 |
| 20-40  |  874 |      52.3 |       0.54 |      55.2 |       2.07 |       61.9 |        5.68 |
| 40-60  |  791 |      59.2 |       1.33 |      65.1 |       3.54 |       65   |        4.7  |
| 60-80  |  997 |      54.7 |       0.78 |      68.3 |       3.48 |       79.7 |        8.8  |
| 80-100 | 2414 |      61.5 |       1.41 |      69.4 |       3.76 |       73.6 |        7.26 |

### gold · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 1700 |      61.7 |       1.53 |      74.1 |       4.62 |       79.4 |        8.71 |
| neutral  | 2730 |      54.9 |       0.74 |      62   |       2.2  |       67.5 |        5.25 |
| tailwind | 2042 |      56.6 |       1.02 |      59.5 |       3.02 |       69.1 |        5.92 |

### gold · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +3.3% 66.8%hit (n=336) [flat]; high >1.5: +7.1% 69.4%hit (n=586) [flat]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  336 |      66.1 |       1.93 |      51.8 |       0.93 |       66.8 |        3.29 |
| -1.5..-.5 | 1284 |      57.3 |       0.91 |      65.6 |       3.24 |       68.4 |        6.13 |
| -.5..5    | 2061 |      58   |       1.37 |      65.4 |       3.71 |       70.8 |        6.91 |
| .5..1.5   | 1124 |      54   |       0.84 |      60.2 |       2.92 |       65.9 |        6.27 |
| >1.5      |  586 |      51   |       0.14 |      62.1 |       2.45 |       69.4 |        7.07 |

### gold · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   |  951 |      63   |       1.33 |      67.1 |       2.99 |       69.3 |        5.23 |
| 15-50  | 1814 |      54.4 |       0.58 |      58.7 |       1.88 |       69.7 |        5.72 |
| 50-85  | 2158 |      56.6 |       1.25 |      65.8 |       3.73 |       70.3 |        6.67 |
| 85-100 | 1437 |      58.2 |       1.14 |      66.8 |       3.87 |       74.1 |        7.63 |

### gold · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1544 |      58.6 |       1.08 |      61.8 |       2.83 |       68.9 |        6.13 |
| Stagflation     | 1659 |      52.9 |       0.95 |      62.2 |       3.25 |       72.3 |        6.86 |
| Goldilocks      | 1551 |      60.9 |       1.28 |      67.5 |       2.78 |       70.2 |        6.02 |
| Deflation-scare | 1718 |      56.8 |       0.86 |      65.9 |       3.47 |       72.8 |        6.4  |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    5.2 |          6   |            0.7 |        11.4 |     0.62 |          0.69 |      0.48 |           0.92 |   -14.3 |        -44.4 |             35.2 |               8.8 |            0.23 |
| moderate     |    4.4 |          5.3 |            0.9 |        11.4 |     0.44 |          0.69 |      0.44 |           0.92 |   -33.3 |        -44.4 |             58   |              10.3 |            0.19 |
| aggressive   |    5.3 |          6.2 |            0.9 |        11.4 |     0.46 |          0.69 |      0.49 |           0.92 |   -32.2 |        -44.4 |             68.4 |              10.1 |            0.24 |
| optimal      |    4.9 |          5.7 |            0.8 |        11.4 |     0.48 |          0.69 |      0.48 |           0.92 |   -33.7 |        -44.4 |             60.7 |               9.9 |            0.21 |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.5805**; observed SR 0.48 ann vs haircut SR0 0.44 ann (N=40 trials, T=6472d, skew=-0.822, kurt=18.713).

## SILVER — 2001-01-02..2026-09-25 (6473 days)

| Signal | Verdict | full | pre | post | want |
|---|---|--:|--:|--:|--:|
| momentum | **CONTEXT-ONLY** | 0 | 0 | 0 | 1 |
| ts_momentum | **DIRECTIONAL (one half weak)** | 1 | -1 | 1 | 1 |
| structure | **CONTEXT-ONLY** | 0 | -1 | 1 | 1 |
| gsr_pctile | **CONFIRMED** | 1 | 1 | 1 | 1 |
| driver_score | **CONTEXT-ONLY** | 0 | -1 | 0 | 1 |
| shock_z | **CONTEXT-ONLY** | 0 | 0 | -1 | 1 |
| pos_pctile | **CONTEXT-ONLY** | 0 | -1 | 1 | -1 |
| risk_index (drawdown) | **CONFIRMED near-term risk gauge** | -1 | -1 | -1 | -1 |

### silver · momentum — forward returns by band (full)

| band    |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:--------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-0.5   | 1847 |      56.2 |       1.29 |      64.3 |       3.6  |       62.9 |        6.93 |
| -0.5..0 | 1167 |      57.5 |       2.17 |      60   |       4.47 |       61   |        6.6  |
| 0..0.5  | 1051 |      53.3 |       1.28 |      56.3 |       3.98 |       58.1 |        8.94 |
| >0.5    | 2408 |      49.4 |       0.85 |      50   |       3.61 |       56.1 |        9.08 |

### silver · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down | 1552 |      52.4 |       1.35 |      60.8 |       3.48 |       59.6 |        5.83 |
| down        |  786 |      47.8 |      -0.04 |      52   |       1.16 |       58.4 |        4.75 |
| up          |  791 |      51.3 |       1.22 |      58.5 |       4.82 |       58.2 |        7.72 |
| strong-up   | 3176 |      56.7 |       1.69 |      57.4 |       4.72 |       60.4 |       10.54 |

### silver · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 2009 |      56.5 |       1.47 |      63.5 |       3.43 |       64.4 |        6.37 |
| neutral      | 1995 |      54.4 |       1.1  |      59.1 |       3.34 |       55.4 |        6.97 |
| constructive | 2469 |      50.1 |       1.27 |      49.6 |       4.53 |       58.1 |       10.15 |

### silver · gsr_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-20   | 1293 |      51.3 |       0.85 |      48.2 |       1.35 |       47.4 |        1.41 |
| 20-40  |  874 |      48   |       0.74 |      51.6 |       2.5  |       52.7 |        7.08 |
| 40-60  |  791 |      56.8 |       1.58 |      55.8 |       4.91 |       55.6 |        4.93 |
| 60-80  |  996 |      47.6 |       0.44 |      59   |       3.6  |       66   |       11.91 |
| 80-100 | 2415 |      58.4 |       2.06 |      64.6 |       5.62 |       67.4 |       11.53 |

### silver · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 1589 |      55.3 |       1.6  |      61.8 |       4.06 |       68.8 |        9.47 |
| neutral  | 2787 |      49.9 |       0.66 |      55.4 |       2.94 |       55.5 |        6.14 |
| tailwind | 2097 |      56.7 |       1.86 |      55.1 |       4.8  |       56.9 |        9.36 |

### silver · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +13.7% 65.0%hit (n=361) [STRONG]; high >1.5: +6.6% 54.1%hit (n=482) [flat]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  361 |      63.4 |       2.33 |      65.4 |       5.44 |       65   |       13.72 |
| -1.5..-.5 | 1390 |      55.5 |       1.3  |      62.7 |       4.22 |       61.1 |        7.05 |
| -.5..5    | 2005 |      49.9 |       0.99 |      55.1 |       2.91 |       55.6 |        6.98 |
| .5..1.5   | 1153 |      51.8 |       1.18 |      49.7 |       4.28 |       57.3 |       11.1  |
| >1.5      |  482 |      51.2 |       2.29 |      50.2 |       5.46 |       54.1 |        6.61 |

### silver · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   | 1146 |      60.2 |       2.13 |      68.7 |       5.98 |       63.4 |        7.32 |
| 15-50  | 2050 |      53.3 |       1.5  |      51.8 |       2.53 |       61.3 |        5.63 |
| 50-85  | 2040 |      51.2 |       1.12 |      57   |       4.82 |       57   |       10.91 |
| 85-100 | 1125 |      52   |       0.58 |      57.6 |       2.77 |       59   |        8.66 |

### silver · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1545 |      56.7 |       2.04 |      61.8 |       4.5  |       67   |        9.95 |
| Stagflation     | 1660 |      53.7 |       1.51 |      55   |       3.94 |       53.8 |        7.39 |
| Goldilocks      | 1551 |      50.1 |       0.75 |      52.9 |       1.04 |       53.4 |        4.86 |
| Deflation-scare | 1717 |      53.3 |       0.86 |      57.7 |       5.54 |       62.3 |        9.52 |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    1.3 |          2   |            0.7 |        10.8 |     0.16 |          0.48 |      0.11 |           0.59 |   -50.5 |        -75.8 |             28.2 |               8.6 |            0.1  |
| moderate     |    1.4 |          2.2 |            0.8 |        10.8 |     0.17 |          0.48 |      0.14 |           0.59 |   -59.4 |        -75.8 |             47.2 |               9.9 |            0.1  |
| aggressive   |    2.3 |          3.1 |            0.8 |        10.8 |     0.22 |          0.48 |      0.2  |           0.59 |   -73   |        -75.8 |             59   |              10.1 |            0.13 |
| optimal      |    1.5 |          2.3 |            0.8 |        10.8 |     0.18 |          0.48 |      0.15 |           0.59 |   -61.7 |        -75.8 |             51.1 |              10   |            0.1  |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.0945**; observed SR 0.18 ann vs haircut SR0 0.44 ann (N=40 trials, T=6473d, skew=-2.74, kurt=74.575).

## COPPER — 2001-01-02..2026-09-25 (6476 days)

| Signal | Verdict | full | pre | post | want |
|---|---|--:|--:|--:|--:|
| momentum | **DIRECTIONAL (one half weak)** | 1 | 1 | 0 | 1 |
| ts_momentum | **CONTEXT-ONLY** | 0 | 0 | 1 | 1 |
| structure | **DIRECTIONAL (one half weak)** | 1 | 1 | 0 | 1 |
| driver_score | **DIRECTIONAL (one half weak)** | 1 | 1 | 0 | 1 |
| shock_z | **CONTEXT-ONLY** | 0 | 1 | 0 | 1 |
| pos_pctile | **CONTEXT-ONLY** | 0 | -1 | 1 | -1 |
| risk_index (drawdown) | **DIRECTIONAL** | -1 | -1 | 1 | -1 |

### copper · momentum — forward returns by band (full)

| band    |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:--------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-0.5   | 1707 |      54.1 |      -0.17 |      56.2 |       1.13 |       58.9 |        4.51 |
| -0.5..0 | 1088 |      56.1 |       1.45 |      61.8 |       3.5  |       58.2 |        5.19 |
| 0..0.5  | 1203 |      57.6 |       1.68 |      57.3 |       3.98 |       56.3 |        6.23 |
| >0.5    | 2478 |      54.2 |       1.19 |      58.6 |       3.85 |       60.3 |        8.59 |

### copper · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down | 1597 |      59   |       1.14 |      63.1 |       4.45 |       58.6 |        8.44 |
| down        | 1030 |      45.4 |      -0.38 |      42.7 |      -1.13 |       39.1 |       -0.48 |
| up          |  764 |      51.2 |       0.09 |      55.7 |      -0.35 |       65.9 |        2.75 |
| strong-up   | 2917 |      59.8 |       1.81 |      64.8 |       5.44 |       66.5 |        9.94 |

### copper · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 1893 |      54   |      -0.09 |      55.4 |       1.46 |       59.8 |        4.62 |
| neutral      | 1941 |      55.8 |       1.09 |      58.2 |       2.3  |       54.5 |        3.3  |
| constructive | 2642 |      55.4 |       1.63 |      60.3 |       4.86 |       61.2 |       10.22 |

### copper · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 1337 |      53.3 |       0.05 |      57.7 |       1.02 |       63.2 |        5.37 |
| neutral  | 2852 |      54   |       1.16 |      53.8 |       2.3  |       53.7 |        4.29 |
| tailwind | 2287 |      57.5 |       1.26 |      64.1 |       5.3  |       62.5 |        9.85 |

### copper · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +4.8% 56.9%hit (n=364) [flat]; high >1.5: +6.2% 51.4%hit (n=285) [flat]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  364 |      58.5 |       0.21 |      60.7 |       2.08 |       56.9 |        4.82 |
| -1.5..-.5 |  947 |      53.7 |      -0.08 |      52.9 |       0.88 |       50.9 |        2.39 |
| -.5..5    | 2052 |      59.3 |       1.44 |      58.1 |       2.62 |       57.1 |        4.64 |
| .5..1.5   |  998 |      45.6 |      -0.18 |      50   |       0.59 |       48   |        2.76 |
| >1.5      |  285 |      47   |      -1.13 |      54.7 |       1.95 |       51.4 |        6.25 |

### copper · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   | 1276 |      58.9 |       1.91 |      62   |       6.34 |       60.7 |       11.89 |
| 15-50  | 1886 |      52   |       0.26 |      58.2 |       2.41 |       56.8 |        6.27 |
| 50-85  | 1747 |      55.5 |       1.1  |      53.7 |       0.83 |       57.8 |        2.19 |
| 85-100 | 1455 |      58.2 |       1.19 |      65   |       4.81 |       65.7 |        9.1  |

### copper · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1544 |      61.3 |       1.94 |      63   |       5.2  |       59.6 |        6.5  |
| Stagflation     | 1662 |      51.3 |       0.83 |      55.9 |       4.15 |       62.8 |        6.9  |
| Goldilocks      | 1552 |      51   |       0.12 |      50.7 |      -0.12 |       48.2 |        4.62 |
| Deflation-scare | 1718 |      56.9 |       0.99 |      63   |       3.03 |       63.3 |        7.65 |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    4.3 |          5   |            0.7 |         8.5 |     0.4  |          0.44 |      0.31 |            0.6 |   -40.4 |        -69.4 |             31   |               8.3 |            0.36 |
| moderate     |    3.8 |          4.6 |            0.9 |         8.5 |     0.31 |          0.44 |      0.3  |            0.6 |   -59.9 |        -69.4 |             52.8 |              10.3 |            0.32 |
| aggressive   |    3.8 |          4.7 |            0.9 |         8.5 |     0.3  |          0.44 |      0.32 |            0.6 |   -61.8 |        -69.4 |             63.9 |              10.5 |            0.32 |
| optimal      |    4.2 |          5   |            0.8 |         8.5 |     0.33 |          0.44 |      0.33 |            0.6 |   -57   |        -69.4 |             55.8 |               9.9 |            0.35 |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.2949**; observed SR 0.33 ann vs haircut SR0 0.44 ann (N=40 trials, T=6476d, skew=-1.277, kurt=47.532).

## OIL — 2001-01-02..2026-09-25 (6475 days)

| Signal | Verdict | full | pre | post | want |
|---|---|--:|--:|--:|--:|
| momentum | **CONTEXT-ONLY** | 0 | 0 | 1 | 1 |
| ts_momentum | **INVERTED** | -1 | -1 | -1 | 1 |
| structure | **CONTEXT-ONLY** | 0 | 0 | 1 | 1 |
| bw_change | **CONFIRMED** | 1 | 1 | 1 | 1 |
| driver_score | **CONFIRMED** | 1 | 1 | 1 | 1 |
| shock_z | **INVERTED** | -1 | -1 | -1 | 1 |
| pos_pctile | **CONTEXT-ONLY** | 0 | -1 | 0 | -1 |
| risk_index (drawdown) | **CONFIRMED near-term risk gauge** | -1 | -1 | -1 | -1 |

### oil · momentum — forward returns by band (full)

| band    |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:--------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-0.5   | 1733 |      52.7 |      -0.05 |      57.7 |       4.45 |       60.9 |        7.57 |
| -0.5..0 | 1108 |      57.2 |       1.82 |      63.2 |       5.1  |       59   |        6.92 |
| 0..0.5  | 1157 |      58.4 |       1.79 |      54.3 |       3.07 |       59.6 |        6.87 |
| >0.5    | 2477 |      52.7 |       1    |      55.9 |       1.53 |       54.4 |        3.61 |

### oil · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down | 1926 |      55.9 |       1.73 |      63.9 |       8.84 |       66.6 |       13.45 |
| down        |  755 |      55.5 |       1.08 |      56.7 |       2.06 |       62.6 |        6.83 |
| up          |  767 |      56.2 |       1.04 |      60.2 |       2.53 |       58.9 |        5.44 |
| strong-up   | 2864 |      53.4 |       0.6  |      54.7 |       0.48 |       53.3 |        1.77 |

### oil · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 1936 |      53.5 |       0.14 |      58   |       4.43 |       62.8 |        7.85 |
| neutral      | 1842 |      59.4 |       2.06 |      61.7 |       5.09 |       57.9 |        7.14 |
| constructive | 2697 |      51.9 |       0.89 |      53.9 |       1.02 |       54.3 |        3.47 |

### oil · bw_change — forward returns by band (full)

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     | 1211 |      46.7 |      -2.11 |      52.9 |      -1.75 |       45.8 |       -2.05 |
| -1.5..-.3 |  917 |      49.3 |      -0.27 |      49.3 |       1.54 |       45.4 |        0.59 |
| -.3..3    |  533 |      56.4 |       1.2  |      61.7 |       5.06 |       57.3 |        7.04 |
| .3..1.5   |  851 |      59.2 |       2.55 |      56   |       4.49 |       57.6 |        6.72 |
| >1.5      | 1262 |      56   |       2.63 |      55.9 |       4.44 |       59.2 |        8.42 |

### oil · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 2016 |      44.8 |      -1.63 |      48.5 |      -0.5  |       45.6 |       -0.34 |
| neutral  | 1916 |      60.3 |       2.4  |      61.6 |       4.82 |       59.4 |        6.95 |
| tailwind | 2543 |      57.9 |       2.04 |      61.2 |       4.93 |       66.5 |        9.87 |

### oil · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +12.7% 61.5%hit (n=375) [STRONG]; high >1.5: -4.2% 35.1%hit (n=356) [FADE]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  375 |      44   |      -1.21 |      58.9 |       6.99 |       61.5 |       12.7  |
| -1.5..-.5 | 1050 |      53   |       0.16 |      55   |       3.62 |       54.2 |        3.49 |
| -.5..5    | 1843 |      54.3 |       0.79 |      54.4 |       1.2  |       55.6 |        5.55 |
| .5..1.5   | 1019 |      51.5 |       1.19 |      49.3 |      -0.24 |       45.4 |       -1.61 |
| >1.5      |  356 |      53.9 |       1.32 |      50.3 |       1.77 |       35.1 |       -4.16 |

### oil · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   |  785 |      48.4 |       0.26 |      48.4 |       1.89 |       47.6 |        4.43 |
| 15-50  | 2260 |      55.3 |       0.77 |      60.6 |       4.7  |       62.3 |        6.55 |
| 50-85  | 1938 |      56.6 |       1.45 |      56.1 |       1.75 |       58.8 |        7.36 |
| 85-100 | 1385 |      54.4 |       1.31 |      61.2 |       4    |       58.5 |        4.68 |

### oil · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1544 |      61.2 |       2.59 |      67.6 |       5.4  |       70.6 |       11.26 |
| Stagflation     | 1660 |      53.2 |       0.81 |      53.8 |       2.85 |       61.7 |        6.84 |
| Goldilocks      | 1553 |      53.1 |       0.52 |      54.8 |       1.72 |       50.4 |        1.4  |
| Deflation-scare | 1718 |      51   |       0.19 |      53.9 |       2.89 |       49.2 |        3.73 |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    0.3 |          1.1 |            0.8 |         4.9 |     0.1  |         -0.01 |      0.08 |          -0.01 |   -64.1 |       -125.9 |             34   |               9.7 |            0.32 |
| moderate     |    0.8 |          1.6 |            0.8 |         4.9 |     0.14 |         -0.01 |      0.14 |          -0.01 |   -64.6 |       -125.9 |             52.2 |              10.1 |            0.36 |
| aggressive   |    2.9 |          3.6 |            0.8 |         4.9 |     0.24 |         -0.01 |      0.25 |          -0.01 |   -52.1 |       -125.9 |             62.2 |               9.6 |            0.61 |
| optimal      |    2.1 |          3   |            0.8 |         4.9 |     0.21 |         -0.01 |      0.21 |          -0.01 |   -63.5 |       -125.9 |             54.7 |              10   |            0.51 |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.1262**; observed SR 0.21 ann vs haircut SR0 0.43 ann (N=40 trials, T=6475d, skew=-0.484, kurt=16.868).

## Trial log

As-of 2026-09-25: **40** declared independent trials per asset (upper-bound); 8 signal families screened across 4 assets; allocation variants: conservative, moderate, aggressive, optimal; transaction cost 8.0bps one-way.