# Commodity Vector — calibration report

Split-half boundary: 2013-01-01. Forward horizons: [21, 63, 126] days.

House rule: a relationship is trusted (labeled a *signal* in the UI) only if its forward-return rank-trend holds in the expected direction in the full sample AND survives both halves. The Risk Index is judged on forward DRAWDOWN (its real job). **shock_z** (the residual exogenous-bid detector) is judged directionally: CONFIRMED = bids persist (momentum), INVERTED = bids fade (mean-reversion) — both honest. Anything failing is context-only.


## GOLD — 2001-01-02..2026-09-18 (6466 days)

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
| <-0.5   | 1342 |      60.2 |       1    |      62.4 |       2.35 |       68.4 |        4.96 |
| -0.5..0 | 1120 |      59.7 |       1.34 |      65.4 |       2.62 |       70.4 |        6.06 |
| 0..0.5  | 1178 |      55.7 |       0.88 |      67.4 |       4.09 |       73.8 |        7.26 |
| >0.5    | 2826 |      55.6 |       1.01 |      63.5 |       3.22 |       71.7 |        6.79 |

### gold · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down |  477 |      56.2 |       0.71 |      57   |       1.47 |       45.7 |        1.17 |
| down        | 1077 |      53.5 |       0.77 |      59.7 |       1.75 |       67.2 |        4.22 |
| up          | 1257 |      54.6 |       0.73 |      60.2 |       2.69 |       71.6 |        5.66 |
| strong-up   | 3487 |      59.5 |       1.29 |      67.6 |       3.92 |       74.9 |        8.15 |

### gold · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 1716 |      60   |       1.3  |      62.1 |       2.28 |       68.9 |        5.44 |
| neutral      | 1993 |      55.4 |       0.75 |      67.7 |       3.63 |       72.2 |        6.94 |
| constructive | 2757 |      57   |       1.09 |      63.2 |       3.21 |       71.8 |        6.54 |

### gold · gsr_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-20   | 1287 |      53.9 |       0.75 |      56.2 |       2.02 |       68.5 |        4.33 |
| 20-40  |  873 |      52.3 |       0.54 |      55.2 |       2.07 |       61.9 |        5.68 |
| 40-60  |  791 |      59.2 |       1.33 |      65.1 |       3.54 |       65   |        4.7  |
| 60-80  |  997 |      54.7 |       0.78 |      68.3 |       3.48 |       79.7 |        8.8  |
| 80-100 | 2414 |      61.5 |       1.41 |      69.4 |       3.76 |       73.6 |        7.26 |

### gold · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 1696 |      61.7 |       1.53 |      74   |       4.62 |       79.7 |        8.78 |
| neutral  | 2728 |      55   |       0.75 |      62   |       2.2  |       67.5 |        5.25 |
| tailwind | 2042 |      56.6 |       1.02 |      59.5 |       3.02 |       69.1 |        5.92 |

### gold · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +3.4% 67.4%hit (n=336) [flat]; high >1.5: +7.1% 69.4%hit (n=586) [flat]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  336 |      66.1 |       1.93 |      51.8 |       0.93 |       67.4 |        3.4  |
| -1.5..-.5 | 1282 |      57.3 |       0.91 |      65.5 |       3.23 |       68.5 |        6.17 |
| -.5..5    | 2057 |      58.1 |       1.37 |      65.3 |       3.71 |       70.8 |        6.91 |
| .5..1.5   | 1124 |      54.1 |       0.85 |      60.2 |       2.92 |       65.9 |        6.27 |
| >1.5      |  586 |      51.2 |       0.16 |      62.1 |       2.45 |       69.4 |        7.07 |

### gold · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   |  951 |      63   |       1.33 |      67.1 |       2.99 |       69.3 |        5.23 |
| 15-50  | 1814 |      54.4 |       0.58 |      58.7 |       1.88 |       70   |        5.77 |
| 50-85  | 2158 |      56.6 |       1.25 |      65.7 |       3.73 |       70.3 |        6.67 |
| 85-100 | 1431 |      58.4 |       1.16 |      66.8 |       3.87 |       74.1 |        7.63 |

### gold · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1540 |      58.6 |       1.08 |      61.8 |       2.83 |       68.9 |        6.13 |
| Stagflation     | 1657 |      53.1 |       0.97 |      62.2 |       3.25 |       72.3 |        6.87 |
| Goldilocks      | 1551 |      60.9 |       1.28 |      67.4 |       2.77 |       70.2 |        6.02 |
| Deflation-scare | 1718 |      56.8 |       0.86 |      65.9 |       3.47 |       73   |        6.45 |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    5.2 |          6   |            0.7 |        11.5 |     0.62 |           0.7 |      0.48 |           0.93 |   -14.3 |        -44.4 |             35.3 |               8.8 |            0.23 |
| moderate     |    4.4 |          5.3 |            0.9 |        11.5 |     0.44 |           0.7 |      0.44 |           0.93 |   -33.3 |        -44.4 |             58.1 |              10.3 |            0.18 |
| aggressive   |    5.3 |          6.2 |            0.9 |        11.5 |     0.46 |           0.7 |      0.49 |           0.93 |   -32.2 |        -44.4 |             68.5 |              10.1 |            0.23 |
| optimal      |    4.9 |          5.8 |            0.8 |        11.5 |     0.48 |           0.7 |      0.48 |           0.93 |   -33.7 |        -44.4 |             60.8 |               9.9 |            0.21 |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.5805**; observed SR 0.48 ann vs haircut SR0 0.44 ann (N=40 trials, T=6466d, skew=-0.822, kurt=18.696).

## SILVER — 2001-01-02..2026-09-18 (6467 days)

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
| <-0.5   | 1847 |      56.2 |       1.29 |      64.2 |       3.59 |       62.9 |        6.93 |
| -0.5..0 | 1161 |      57.5 |       2.17 |      60   |       4.47 |       61.2 |        6.67 |
| 0..0.5  | 1051 |      53.5 |       1.29 |      56.3 |       3.98 |       58.2 |        9    |
| >0.5    | 2408 |      49.4 |       0.85 |      50   |       3.61 |       56.1 |        9.08 |

### silver · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down | 1552 |      52.4 |       1.35 |      60.8 |       3.48 |       59.6 |        5.83 |
| down        |  786 |      47.8 |      -0.04 |      52   |       1.16 |       58.4 |        4.75 |
| up          |  791 |      51.3 |       1.22 |      58.5 |       4.82 |       58.2 |        7.72 |
| strong-up   | 3170 |      56.8 |       1.7  |      57.4 |       4.71 |       60.5 |       10.59 |

### silver · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 2007 |      56.5 |       1.47 |      63.4 |       3.42 |       64.5 |        6.41 |
| neutral      | 1991 |      54.4 |       1.1  |      59.1 |       3.34 |       55.4 |        7    |
| constructive | 2469 |      50.3 |       1.28 |      49.6 |       4.53 |       58.1 |       10.15 |

### silver · gsr_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-20   | 1288 |      51.5 |       0.87 |      47.9 |       1.32 |       47.7 |        1.49 |
| 20-40  |  873 |      48   |       0.74 |      51.6 |       2.5  |       52.7 |        7.08 |
| 40-60  |  791 |      56.8 |       1.58 |      55.8 |       4.91 |       55.6 |        4.93 |
| 60-80  |  996 |      47.6 |       0.44 |      59   |       3.6  |       66   |       11.91 |
| 80-100 | 2415 |      58.4 |       2.06 |      64.6 |       5.62 |       67.4 |       11.53 |

### silver · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 1584 |      55.3 |       1.6  |      61.7 |       4.04 |       69.1 |        9.57 |
| neutral  | 2786 |      50   |       0.67 |      55.4 |       2.94 |       55.5 |        6.14 |
| tailwind | 2097 |      56.7 |       1.86 |      55.1 |       4.8  |       56.9 |        9.36 |

### silver · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +13.7% 65.0%hit (n=361) [STRONG]; high >1.5: +6.6% 54.1%hit (n=482) [flat]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  361 |      63.4 |       2.33 |      65.4 |       5.44 |       65   |       13.72 |
| -1.5..-.5 | 1390 |      55.5 |       1.3  |      62.7 |       4.21 |       61.3 |        7.11 |
| -.5..5    | 1999 |      50   |       0.99 |      55   |       2.9  |       55.7 |        7    |
| .5..1.5   | 1153 |      52   |       1.19 |      49.7 |       4.28 |       57.3 |       11.1  |
| >1.5      |  482 |      51.2 |       2.29 |      50.2 |       5.46 |       54.1 |        6.61 |

### silver · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   | 1146 |      60.2 |       2.13 |      68.7 |       5.98 |       63.4 |        7.32 |
| 15-50  | 2044 |      53.5 |       1.52 |      51.7 |       2.51 |       61.5 |        5.69 |
| 50-85  | 2040 |      51.2 |       1.12 |      57   |       4.82 |       57   |       10.91 |
| 85-100 | 1125 |      52   |       0.58 |      57.6 |       2.77 |       59   |        8.66 |

### silver · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1541 |      56.7 |       2.04 |      61.8 |       4.5  |       67   |        9.95 |
| Stagflation     | 1658 |      53.9 |       1.53 |      55   |       3.94 |       53.8 |        7.41 |
| Goldilocks      | 1551 |      50.1 |       0.75 |      52.7 |       1.02 |       53.4 |        4.86 |
| Deflation-scare | 1717 |      53.3 |       0.86 |      57.7 |       5.54 |       62.5 |        9.59 |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    1.3 |          2   |            0.7 |          11 |     0.16 |          0.48 |      0.11 |            0.6 |   -50.5 |        -75.8 |             28.3 |               8.6 |            0.1  |
| moderate     |    1.4 |          2.2 |            0.8 |          11 |     0.17 |          0.48 |      0.14 |            0.6 |   -59.4 |        -75.8 |             47.3 |               9.9 |            0.1  |
| aggressive   |    2.3 |          3.2 |            0.8 |          11 |     0.22 |          0.48 |      0.2  |            0.6 |   -73   |        -75.8 |             59   |              10.1 |            0.12 |
| optimal      |    1.5 |          2.3 |            0.8 |          11 |     0.18 |          0.48 |      0.15 |            0.6 |   -61.7 |        -75.8 |             51.1 |              10   |            0.1  |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.0946**; observed SR 0.18 ann vs haircut SR0 0.44 ann (N=40 trials, T=6467d, skew=-2.739, kurt=74.506).

## COPPER — 2001-01-02..2026-09-18 (6470 days)

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
| -0.5..0 | 1088 |      56.1 |       1.45 |      61.6 |       3.48 |       58.2 |        5.19 |
| 0..0.5  | 1203 |      57.5 |       1.68 |      57.3 |       3.98 |       56.2 |        6.2  |
| >0.5    | 2472 |      54.2 |       1.19 |      58.6 |       3.85 |       60.2 |        8.59 |

### copper · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down | 1597 |      59   |       1.14 |      63.1 |       4.45 |       58.6 |        8.44 |
| down        | 1030 |      45.4 |      -0.38 |      42.7 |      -1.13 |       39.1 |       -0.48 |
| up          |  764 |      51.2 |       0.09 |      55.7 |      -0.37 |       65.9 |        2.75 |
| strong-up   | 2911 |      59.7 |       1.81 |      64.8 |       5.43 |       66.4 |        9.93 |

### copper · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 1893 |      54   |      -0.09 |      55.3 |       1.44 |       59.8 |        4.62 |
| neutral      | 1935 |      55.8 |       1.09 |      58.2 |       2.3  |       54.4 |        3.27 |
| constructive | 2642 |      55.3 |       1.63 |      60.3 |       4.86 |       61.2 |       10.22 |

### copper · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 1337 |      53.3 |       0.05 |      57.7 |       1.02 |       63.2 |        5.37 |
| neutral  | 2846 |      53.9 |       1.16 |      53.7 |       2.28 |       53.6 |        4.27 |
| tailwind | 2287 |      57.5 |       1.26 |      64.1 |       5.3  |       62.5 |        9.85 |

### copper · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +4.8% 56.9%hit (n=364) [flat]; high >1.5: +6.2% 51.4%hit (n=285) [flat]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  364 |      58.5 |       0.21 |      60.7 |       2.08 |       56.9 |        4.82 |
| -1.5..-.5 |  950 |      53.5 |      -0.08 |      52.9 |       0.88 |       50.9 |        2.39 |
| -.5..5    | 2048 |      59.2 |       1.44 |      58   |       2.6  |       57   |        4.62 |
| .5..1.5   |  993 |      45.6 |      -0.18 |      50   |       0.59 |       48   |        2.76 |
| >1.5      |  285 |      47   |      -1.13 |      54.7 |       1.95 |       51.4 |        6.25 |

### copper · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   | 1276 |      58.9 |       1.91 |      62   |       6.34 |       60.7 |       11.89 |
| 15-50  | 1886 |      52   |       0.26 |      58.2 |       2.41 |       56.8 |        6.27 |
| 50-85  | 1747 |      55.5 |       1.1  |      53.7 |       0.83 |       57.6 |        2.15 |
| 85-100 | 1449 |      58.1 |       1.19 |      64.9 |       4.79 |       65.7 |        9.1  |

### copper · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1540 |      61.3 |       1.94 |      63   |       5.2  |       59.6 |        6.5  |
| Stagflation     | 1660 |      51.1 |       0.83 |      55.9 |       4.15 |       62.7 |        6.9  |
| Goldilocks      | 1552 |      51   |       0.12 |      50.5 |      -0.15 |       48.2 |        4.62 |
| Deflation-scare | 1718 |      56.9 |       0.99 |      63   |       3.03 |       63.2 |        7.63 |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    4.3 |          5   |            0.7 |         8.5 |     0.4  |          0.44 |      0.31 |            0.6 |   -40.4 |        -69.4 |             31.1 |               8.3 |            0.36 |
| moderate     |    3.8 |          4.6 |            0.9 |         8.5 |     0.31 |          0.44 |      0.3  |            0.6 |   -59.9 |        -69.4 |             52.8 |              10.3 |            0.32 |
| aggressive   |    3.8 |          4.7 |            0.9 |         8.5 |     0.3  |          0.44 |      0.32 |            0.6 |   -61.8 |        -69.4 |             63.9 |              10.5 |            0.32 |
| optimal      |    4.2 |          5   |            0.8 |         8.5 |     0.33 |          0.44 |      0.33 |            0.6 |   -57   |        -69.4 |             55.8 |               9.9 |            0.35 |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.2958**; observed SR 0.33 ann vs haircut SR0 0.44 ann (N=40 trials, T=6470d, skew=-1.277, kurt=47.501).

## OIL — 2001-01-02..2026-09-18 (6469 days)

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
| <-0.5   | 1733 |      52.7 |      -0.05 |      57.6 |       4.35 |       60.9 |        7.57 |
| -0.5..0 | 1108 |      57.2 |       1.82 |      63.2 |       5.1  |       59   |        6.92 |
| 0..0.5  | 1157 |      58.3 |       1.75 |      54.3 |       3.07 |       59.6 |        6.88 |
| >0.5    | 2471 |      52.6 |       1    |      55.9 |       1.53 |       54.5 |        3.62 |

### oil · ts_momentum — forward returns by band (full)

| band        |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| strong-down | 1926 |      55.9 |       1.73 |      63.9 |       8.84 |       66.6 |       13.45 |
| down        |  755 |      55.5 |       1.08 |      56.7 |       2.06 |       62.6 |        6.83 |
| up          |  767 |      56.2 |       1.04 |      59.9 |       2.29 |       58.9 |        5.44 |
| strong-up   | 2858 |      53.3 |       0.58 |      54.7 |       0.48 |       53.3 |        1.78 |

### oil · structure — forward returns by band (full)

| band         |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| broken       | 1936 |      53.5 |       0.14 |      57.9 |       4.35 |       62.8 |        7.85 |
| neutral      | 1842 |      59.4 |       2.06 |      61.7 |       5.09 |       57.9 |        7.14 |
| constructive | 2691 |      51.8 |       0.87 |      53.9 |       1.02 |       54.3 |        3.48 |

### oil · bw_change — forward returns by band (full)

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     | 1211 |      46.7 |      -2.11 |      52.9 |      -1.77 |       45.8 |       -2.04 |
| -1.5..-.3 |  916 |      49.3 |      -0.27 |      49.2 |       1.51 |       45.3 |        0.58 |
| -.3..3    |  532 |      56.4 |       1.2  |      61.5 |       4.9  |       57.3 |        7.04 |
| .3..1.5   |  850 |      59.2 |       2.55 |      56   |       4.49 |       57.6 |        6.72 |
| >1.5      | 1259 |      55.8 |       2.59 |      55.9 |       4.41 |       59.2 |        8.42 |

### oil · driver_score — forward returns by band (full)

| band     |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:---------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| headwind | 2016 |      44.8 |      -1.63 |      48.3 |      -0.6  |       45.6 |       -0.34 |
| neutral  | 1913 |      60.3 |       2.4  |      61.6 |       4.82 |       59.4 |        6.97 |
| tailwind | 2540 |      57.8 |       2.02 |      61.2 |       4.93 |       66.5 |        9.87 |

### oil · shock_z — forward returns by band (full)  
_EXTREMES — low <-1.5: +12.7% 61.5%hit (n=375) [STRONG]; high >1.5: -4.2% 35.1%hit (n=356) [FADE]_

| band      |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| <-1.5     |  375 |      44   |      -1.21 |      58.9 |       6.99 |       61.5 |       12.7  |
| -1.5..-.5 | 1050 |      53   |       0.16 |      54.7 |       3.45 |       54.1 |        3.49 |
| -.5..5    | 1842 |      54.2 |       0.76 |      54.4 |       1.2  |       55.6 |        5.56 |
| .5..1.5   | 1014 |      51.4 |       1.18 |      49.3 |      -0.24 |       45.5 |       -1.61 |
| >1.5      |  356 |      53.9 |       1.32 |      50.3 |       1.77 |       35.1 |       -4.16 |

### oil · pos_pctile — forward returns by band (full)

| band   |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:-------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| 0-15   |  785 |      48.4 |       0.26 |      48.4 |       1.89 |       47.5 |        4.47 |
| 15-50  | 2254 |      55.2 |       0.75 |      60.5 |       4.62 |       62.3 |        6.55 |
| 50-85  | 1938 |      56.6 |       1.45 |      56.1 |       1.75 |       58.8 |        7.36 |
| 85-100 | 1385 |      54.4 |       1.31 |      61.2 |       4    |       58.5 |        4.68 |

### oil · forward returns by complex regime

| band            |    n |   hit_21d |   mean_21d |   hit_63d |   mean_63d |   hit_126d |   mean_126d |
|:----------------|-----:|----------:|-----------:|----------:|-----------:|-----------:|------------:|
| Reflation       | 1540 |      61.2 |       2.59 |      67.6 |       5.4  |       70.6 |       11.26 |
| Stagflation     | 1658 |      53   |       0.77 |      53.8 |       2.85 |       61.6 |        6.85 |
| Goldilocks      | 1553 |      53.1 |       0.52 |      54.6 |       1.6  |       50.4 |        1.4  |
| Deflation-scare | 1718 |      51   |       0.19 |      53.9 |       2.89 |       49.3 |        3.75 |
| Neutral         |    0 |     nan   |     nan    |     nan   |     nan    |      nan   |      nan    |

### allocation vs buy-and-hold (NET of 8.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it.

|              |   cagr |   cagr_gross |   cost_drag_pp |   hold_cagr |   sharpe |   hold_sharpe |   sortino |   hold_sortino |   maxdd |   hold_maxdd |   time_in_market |   turnover_annual |   final_vs_hold |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |    0.6 |          1.4 |            0.8 |         5.2 |     0.12 |         -0.01 |      0.1  |          -0.01 |   -64.1 |       -125.9 |             34   |               9.6 |            0.32 |
| moderate     |    1.1 |          2   |            0.8 |         5.2 |     0.16 |         -0.01 |      0.15 |          -0.01 |   -64.6 |       -125.9 |             52.2 |              10.1 |            0.36 |
| aggressive   |    3.2 |          4   |            0.8 |         5.2 |     0.25 |         -0.01 |      0.27 |          -0.01 |   -52.1 |       -125.9 |             62.2 |               9.6 |            0.61 |
| optimal      |    2.5 |          3.3 |            0.8 |         5.2 |     0.22 |         -0.01 |      0.22 |          -0.01 |   -63.5 |       -125.9 |             54.6 |              10   |            0.51 |

**Deflated Sharpe (multiple-testing haircut)** — shipped variant `optimal`: **FAILS multiple-testing haircut (DSR<0.90)**. DSR (P true Sharpe>0) = **0.1433**; observed SR 0.22 ann vs haircut SR0 0.43 ann (N=40 trials, T=6469d, skew=-0.479, kurt=16.958).

## Trial log

As-of 2026-09-18: **40** declared independent trials per asset (upper-bound); 8 signal families screened across 4 assets; allocation variants: conservative, moderate, aggressive, optimal; transaction cost 8.0bps one-way.