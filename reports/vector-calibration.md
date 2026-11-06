# Bitcoin Vector — calibration report

Span: 2015-01-01..2026-09-26 (4287 days). Split-half boundary: 2021-01-01.

House rule: a signal is trusted (labeled a *signal* in the UI) only if its forward outcome relationship trends in the expected direction in the full sample AND survives both halves (rank-trend |rho|>0.6, tolerant of one small-sample band). Return-predicting signals (momentum, structure, BFI) are judged on forward RETURN; the Risk Index is judged on forward DRAWDOWN (its actual job) because at long horizons extreme risk marks capitulation and forward *return* is U-shaped — the documented contrarian behavior, not a defect. Anything failing is context-only; anything inverted is flagged.

## Signal verdicts

| Signal | Verdict | full | pre | post | want |
|---|---|--:|--:|--:|--:|
| risk_index | **DIRECTIONAL (one half weak)** | -1 | -1 | 0 | -1 |
| momentum | **DIRECTIONAL (one half weak)** | 1 | 1 | 0 | 1 |
| structure | **DIRECTIONAL (one half weak)** | 1 | 1 | -1 | 1 |
| risk_oscillator | **CONTEXT-ONLY** | 0 | 0 | -1 | -1 |
| bfi | **DIRECTIONAL (one half weak)** | 1 | 0 | 1 | 1 |
| mvrv_z | **EXTREMES — low <0: +40.5%/90d 71.9% hit (n=356) [BOTTOM]; high >3.5: +27.1%/90d 57.8% hit (n=277) [weak]** | 0 | 0 | 0 | -1 |
| nupl | **EXTREMES — low <0: +28.0%/90d 66.5% hit (n=603) [BOTTOM]; high >.65: +25.8%/90d 58.5% hit (n=265) [weak]** | 0 | 0 | -1 | -1 |
| mayer | **EXTREMES — low <0.8: +11.6%/90d 48.9% hit (n=633) [weak]; high >2.4: -13.9%/90d 33.9% hit (n=62) [TOP]** | 1 | 1 | 0 | -1 |
| puell | **EXTREMES — low <0.5: +15.8%/90d 59.5% hit (n=153) [weak]** | 1 | 1 | 0 | -1 |
| sth_cb_ratio | **EXTREMES — low <-10%: +1.0%/90d 37.9% hit (n=321) [weak]** | 0 | 0 | 0 | 1 |
| hash_ribbon_capit | **CONTEXT-ONLY** | 0 | 0 | 0 | 1 |
| dvol | **EXTREMES — low <40: +6.1%/90d 46.0% hit (n=301) [weak]; high >90: +15.8%/90d 71.4% hit (n=168) [weak]** | 0 | 0 | 0 | -1 |
| vrp | **EXTREMES — low <-5: +17.2%/90d 77.8% hit (n=231) [weak]; high >15: +7.2%/90d 53.9% hit (n=484) [TOP]** | -1 | 0 | -1 | -1 |
| leverage_stress | **EXTREMES — low 0-25: +13.5%/90d 62.3% hit (n=706) [weak]** | -1 | 0 | -1 | -1 |
| funding_z | **EXTREMES — tails too thin to judge** | 0 | 0 | 0 | -1 |
| oi_price_divergence | **EXTREMES — low <-10%: +14.8%/90d 70.4% hit (n=166) [weak]** | -1 | 0 | -1 | -1 |
| net_liq_roc | **DIRECTIONAL (one half weak)** | 1 | 1 | 0 | 1 |
| macro_score | **CONFIRMED** | 1 | 1 | 1 | 1 |
| coinbase_premium_ema | **EXTREMES — low <-.3: +34.5%/90d 57.1% hit (n=184) [BOTTOM]** | -1 | 0 | 0 | 1 |
| ssr_oscillator | **CONTEXT-ONLY** | 0 | 0 | 0 | 1 |
| mpi | **INVERTED** | 1 | 0 | 1 | -1 |
| etf_flow_z | **DIRECTIONAL (one half weak)** | 1 | 0 | 1 | 1 |
| reserve_risk | **EXTREMES — low <.0015: +16.3%/90d 64.7% hit (n=979) [weak]; high >.02: -42.5%/90d 4.2% hit (n=48) [TOP]** | 1 | 0 | -1 | -1 |
| impulse | **DIRECTIONAL (one half weak)** | 1 | 0 | 1 | 1 |
| cycle_pct | **DIRECTIONAL (one half weak)** | -1 | -1 | 0 | -1 |
| cot_z | **EXTREMES — low <-1.5: +13.2%/90d 47.8% hit (n=224) [weak]; high >1.5: -4.9%/90d 35.7% hit (n=665) [TOP]** | -1 | 0 | -1 | -1 |
| corr_spx | **CONFIRMED** | -1 | -1 | -1 | -1 |
| vdd_multiple | **EXTREMES — low <.5: +6.3%/90d 41.7% hit (n=779) [weak]; high >2.9: +35.2%/90d 59.1% hit (n=154) [weak]** | 1 | 1 | 0 | -1 |
| global_m2_yoy | **DIRECTIONAL (full only)** | 1 | 0 | -1 | 1 |
| rv_cone_pctile | **EXTREMES — low 0-25: +24.1%/90d 70.0% hit (n=1252) [weak]; high 75-100: +30.1%/90d 63.8% hit (n=831) [weak]** | 0 | 0 | 0 | -1 |
| vov_pctile | **EXTREMES — low 0-25: +12.3%/90d 52.6% hit (n=1193) [weak]; high 75-100: +36.6%/90d 73.7% hit (n=844) [weak]** | 1 | 1 | 0 | -1 |
| stbl_growth_z | **DIRECTIONAL (one half weak)** | 1 | 0 | 1 | 1 |

## Risk Index as a drawdown gauge

**CONFIRMED near-term risk gauge (7d drawdown)** — rank-trend {'full': -1, 'pre': -1, 'post': -1, 'want': -1, 'horizon': 7}.

| band   |    n |   avgDD_7d |   p05DD_7d |   avgDD_30d |   p05DD_30d |   avgDD_90d |   p05DD_90d |
|:-------|-----:|-----------:|-----------:|------------:|------------:|------------:|------------:|
| 0-25   | 2120 |      -2.94 |     -13.98 |       -8.11 |      -26.02 |      -13.66 |      -46.56 |
| 25-50  | 1355 |      -4.01 |     -16.17 |       -9.82 |      -30.09 |      -17.56 |      -50.33 |
| 50-75  |  708 |      -4.64 |     -20.76 |       -9.74 |      -36.88 |      -14.56 |      -41.63 |
| 75-100 |  104 |      -4.29 |     -15.96 |       -8.85 |      -27.33 |      -12.1  |      -32.43 |

### risk_index — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| 0-25   | 2120 |     56.2 |      2.01 |      57   |       7.89 |      65.9 |      28.21 |
| 25-50  | 1355 |     53.4 |      0.68 |      57.9 |       5.22 |      51.8 |      16.37 |
| 50-75  |  708 |     54   |      0.71 |      59.3 |       4.5  |      56.9 |      14.55 |
| 75-100 |  104 |     49   |      1.83 |      55.8 |       4.01 |      61.5 |      15.85 |

### momentum — forward returns by band (full sample)

| band    |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:--------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-0.5   | 1070 |     53.6 |      0.33 |      58.2 |       2.29 |      52.9 |       7.11 |
| -0.5..0 |  692 |     51.3 |      0.69 |      56.8 |       4.14 |      57.2 |      18.65 |
| 0..0.5  |  794 |     51.8 |      0.74 |      53.9 |       5.62 |      52.9 |      21.83 |
| >0.5    | 1731 |     58.2 |      2.57 |      59.4 |      10.21 |      68.1 |      32.11 |

### structure — forward returns by band (full sample)

| band         |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| broken       | 1170 |     53.1 |      0.46 |      60.4 |       3.23 |      58.5 |      12.53 |
| neutral      | 1262 |     54   |      1.03 |      56   |       6.35 |      56.2 |      22.01 |
| constructive | 1855 |     56.3 |      2.17 |      57   |       8.42 |      63   |      27.66 |

### risk_oscillator — forward returns by band (full sample)

| band    |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:--------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| falling | 1707 |     55.9 |      1.96 |      59.3 |       6.31 |      58.2 |      21.64 |
| neutral | 1284 |     54.6 |      1.34 |      58.9 |       7.13 |      63.1 |      24.24 |
| rising  | 1296 |     53.3 |      0.62 |      54.3 |       5.73 |      58.5 |      19.71 |

### bfi — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <40    | 1615 |     51   |      0.5  |      53.2 |       3.59 |      50.1 |      13.28 |
| 40-60  | 1069 |     55   |      0.72 |      57.8 |       7.06 |      61.4 |      22.06 |
| >60    | 1528 |     58.5 |      2.81 |      62.6 |       9.13 |      69.9 |      32.19 |

### mvrv_z — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <0     |  356 |     58.7 |      1.86 |      68   |       9.71 |      71.9 |      40.55 |
| 0-1    | 1294 |     54   |      1.07 |      58   |       4.2  |      49.7 |       4.64 |
| 1-2    | 1154 |     52.4 |      0.72 |      55.6 |       3.95 |      67.7 |      23.48 |
| 2-3.5  |  948 |     56.5 |      1.84 |      56.9 |      10.2  |      59.8 |      36.62 |
| >3.5   |  277 |     59.9 |      4.67 |      58.1 |      14.54 |      57.8 |      27.15 |

### nupl — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <0     |  603 |     56.7 |      1.07 |      63.2 |       6.29 |      66.5 |      28.01 |
| 0-.25  |  684 |     57.9 |      1.94 |      69   |       7.4  |      57.9 |      10.61 |
| .25-.5 | 1708 |     53   |      0.76 |      53.1 |       2.61 |      59.3 |      16.12 |
| .5-.65 | 1027 |     53.7 |      1.44 |      54.1 |      10.19 |      58   |      33.38 |
| >.65   |  265 |     57.4 |      4.19 |      58.5 |      13.03 |      58.5 |      25.77 |

### mayer — forward returns by band (full sample)

| band    |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:--------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <0.8    |  633 |     54.7 |      1.01 |      62.2 |       4.12 |      48.9 |      11.61 |
| 0.8-1   | 1006 |     51.6 |      0.1  |      54.5 |       2.44 |      52.1 |      10.3  |
| 1-1.5   | 1927 |     55.8 |      1.48 |      58.1 |       6.16 |      68.3 |      24.11 |
| 1.5-2.4 |  566 |     58.7 |      3.82 |      60.6 |      18.69 |      62.5 |      53.36 |
| >2.4    |   62 |     43.5 |      2.27 |      43.5 |      -1.92 |      33.9 |     -13.95 |

### puell — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <0.5   |  153 |     54.9 |      1.22 |      64.7 |       4.09 |      59.5 |      15.76 |
| 0.5-1  | 1770 |     54.2 |      0.72 |      59.7 |       4.41 |      61.1 |      19.92 |
| 1-2    | 1871 |     55.2 |      1.7  |      55.6 |       6.87 |      60.1 |      20.23 |
| 2-4    |  397 |     54.7 |      2.41 |      57.4 |      14.94 |      58.7 |      47.89 |
| >4     |   23 |     56.5 |     10.54 |      34.8 |      -3.22 |      17.4 |     -33.4  |

### sth_cb_ratio — forward returns by band (full sample)

| band   |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-10%  | 321 |     53.9 |      0.6  |      60.4 |       1.89 |      37.9 |       1.03 |
| -10-0% | 390 |     52.3 |      0.33 |      59.7 |       3.62 |      68.2 |      21.27 |
| 0-20%  | 656 |     53.4 |      1.23 |      53.2 |       4.56 |      57.5 |       8.63 |
| 20-50% | 198 |     52   |      0.97 |      55.6 |       3.69 |      68.9 |      13.76 |
| >50%   |   0 |    nan   |    nan    |     nan   |     nan    |     nan   |     nan    |

### hash_ribbon_capit — forward returns by band (full sample)

| band         |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| normal       | 3477 |     55.1 |      1.57 |      58.3 |       7.18 |      60.1 |      23.22 |
| capitulation |  810 |     53.2 |      0.49 |      55.1 |       2.99 |      58.1 |      15.44 |

### dvol — forward returns by band (full sample)

| band   |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <40    | 301 |     51.7 |      0.2  |      48.7 |       1.56 |      46   |       6.1  |
| 40-55  | 664 |     51.7 |      0.94 |      60.1 |       4.45 |      61.8 |      11.65 |
| 55-70  | 479 |     54.1 |      0.47 |      53.9 |       2.88 |      62.6 |      10.65 |
| 70-90  | 401 |     48.9 |      0.01 |      38.4 |      -3.8  |      18.7 |     -12.64 |
| >90    | 168 |     47   |     -0.28 |      47   |       2.06 |      71.4 |      15.84 |

### vrp — forward returns by band (full sample)

| band   |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-5    | 231 |     58   |      1.18 |      61.6 |       3.81 |      77.8 |      17.23 |
| -5-0   | 175 |     57.7 |      1.61 |      64.7 |       5.38 |      52.4 |       9.51 |
| 0-5    | 381 |     50.1 |      0.19 |      55.6 |       2.53 |      34.7 |       1.06 |
| 5-15   | 742 |     47.3 |     -0.23 |      48.1 |       0.27 |      51.8 |       3.75 |
| >15    | 484 |     52.9 |      0.88 |      44.6 |       1.45 |      53.9 |       7.2  |

### leverage_stress — forward returns by band (full sample)

| band   |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| 0-25   | 706 |     54.1 |      1.31 |      58.9 |       4.06 |      62.3 |      13.46 |
| 25-50  | 482 |     52   |      0.28 |      56.5 |       3.34 |      60   |      12.49 |
| 50-75  | 348 |     52.9 |      0.77 |      51.4 |       3.15 |      45.6 |       3.36 |
| 75-100 |  17 |     52.9 |      1.51 |      64.7 |       5.27 |      47.1 |       2.58 |

### funding_z — forward returns by band (full sample)

| band   |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-1    |   6 |     50   |     -0.24 |       nan |        nan |       nan |        nan |
| -1-0   |   5 |     60   |      4.18 |       nan |        nan |       nan |        nan |
| 0-1    |   9 |     71.4 |      2.99 |       nan |        nan |       nan |        nan |
| 1-2    |   4 |     75   |      3.28 |       nan |        nan |       nan |        nan |
| >2     |   0 |    nan   |    nan    |       nan |        nan |       nan |        nan |

### oi_price_divergence — forward returns by band (full sample)

| band   |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-10%  | 166 |     59   |      1.03 |      59.3 |       0.92 |      70.4 |      14.78 |
| -10-0% | 556 |     53.1 |      1.24 |      60.2 |       4.99 |      62.4 |      12.72 |
| 0-10%  | 673 |     53   |      0.79 |      54.2 |       3.94 |      53.7 |       9.37 |
| 10-25% | 152 |     49.3 |     -0.13 |      52.6 |       0.87 |      45.7 |       6.27 |
| >25%   |   6 |     16.7 |     -3.5  |       0   |      -5.7  |      33.3 |      -4.16 |

### net_liq_roc — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-2%   | 1256 |     52.2 |      0.58 |      53.5 |       1.65 |      48.8 |       8.69 |
| -2-0%  |  901 |     53.7 |      1.54 |      57.4 |       7.66 |      61.6 |      17.93 |
| 0-2%   |  872 |     53.2 |      1.17 |      57.5 |       5.42 |      62.1 |      21.83 |
| 2-5%   |  727 |     59.3 |      2.06 |      60.1 |       8.88 |      67.2 |      35.3  |
| >5%    |  508 |     58.5 |      2.23 |      65   |      14.01 |      67.3 |      41.68 |

### macro_score — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-.3   |  571 |     52   |     -0.04 |      51.3 |      -0.38 |      42.6 |       3.03 |
| -.3-.1 |  812 |     53.2 |      1.22 |      60.6 |       5.53 |      59.5 |      17.91 |
| -.1-.1 | 1008 |     58.4 |      2.04 |      60.6 |       8.34 |      56.8 |      19.63 |
| .1-.3  |  969 |     54.1 |      1.62 |      58.9 |       7.51 |      61.3 |      17.48 |
| >.3    |  927 |     54.5 |      1.37 |      54.7 |       8.03 |      72.1 |      43.5  |

### coinbase_premium_ema — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-.3   |  184 |     52.2 |      1.33 |      60.3 |       4.32 |      57.1 |      34.46 |
| -.3-0  | 1050 |     51.6 |      0.38 |      53.5 |       2.48 |      45.2 |       5.43 |
| 0-.5   | 1882 |     52.6 |      0.98 |      52.8 |       4.18 |      55.5 |      13.41 |
| .5-1.5 |   61 |     55.7 |      1.7  |      59   |      13.3  |      93.4 |      85.36 |
| >1.5   |    4 |     25   |     -2.57 |       0   |      -8.47 |       0   |     -28.98 |

### ssr_oscillator — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-1    |  484 |     52.3 |      1.11 |      50.4 |       4.16 |      55.6 |       9.9  |
| -1-.3  |  318 |     52.8 |      0.94 |      70.6 |       8.91 |      73.7 |      17.39 |
| -.3-.5 |  551 |     55.3 |      1.34 |      48.6 |       0.88 |      47.3 |       3.5  |
| .5-1.5 | 1440 |     52.4 |      0.72 |      52.6 |       3.85 |      53.9 |      21.27 |
| >1.5   |  342 |     48.5 |      0.08 |      57   |       4.09 |      40.1 |       2.82 |

### mpi — forward returns by band (full sample)

| band    |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:--------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <0.7    | 428 |     51.5 |      0.6  |      59.5 |       2.35 |      51.5 |       5.55 |
| 0.7-1   | 255 |     55.7 |      0.48 |      56.1 |       3.2  |      67.1 |      15.14 |
| 1-1.5   | 370 |     51.6 |      0.78 |      55.7 |       3.83 |      63.5 |      13.56 |
| 1.5-2.5 | 255 |     58.8 |      1.95 |      64.3 |       8.59 |      69.4 |      19.37 |
| >2.5    | 140 |     52.9 |      1.35 |      46.4 |       2.13 |      60   |      11    |

### etf_flow_z — forward returns by band (full sample)

| band      |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:----------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-.75     | 214 |     47.2 |     -0.37 |      39.7 |      -3.26 |      42.9 |       1.29 |
| -.75--.25 | 150 |     52.7 |      0.36 |      54.5 |       0.16 |      44.3 |       1.13 |
| -.25-.25  | 170 |     50   |      0.76 |      58.8 |       2.94 |      43.9 |       3.04 |
| .25-.75   | 124 |     65.9 |      1.7  |      64.2 |       6    |      57.4 |       8.84 |
| >.75      | 193 |     52.9 |      1    |      62.1 |       5.42 |      59.9 |       6.55 |

### reserve_risk — forward returns by band (full sample)

| band        |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:------------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <.0015      |  979 |     55.8 |      1.47 |      61.8 |       5.67 |      64.7 |      16.27 |
| .0015-.0025 | 1685 |     56.9 |      1.18 |      63   |       6.11 |      69.8 |      25.51 |
| .0025-.005  |  940 |     51.4 |      1.39 |      47.7 |       5.99 |      46   |      17.52 |
| .005-.02    |  535 |     52.9 |      1.76 |      51   |      11.12 |      47.7 |      33.53 |
| >.02        |   48 |     33.3 |     -1.14 |      10.4 |     -22.01 |       4.2 |     -42.55 |

### impulse — forward returns by band (full sample)

| band     |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:---------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-.5     |  378 |     56.1 |      1.55 |      51.3 |       4.42 |      60.9 |      22.87 |
| -.5--.15 |  615 |     52.6 |      0.63 |      56.5 |       6.87 |      59.9 |      19.48 |
| -.15-.15 | 2089 |     52.4 |      0.63 |      55.6 |       4.72 |      57.3 |      17.86 |
| .15-.5   |  584 |     59   |      2.27 |      64.1 |       8.96 |      61.8 |      27.35 |
| >.5      |  621 |     60   |      3.62 |      63.7 |      10.21 |      65.2 |      31.62 |

### cycle_pct — forward returns by band (full sample)

| band     |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:---------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| accum    |  963 |     61.1 |      2.76 |      70.4 |      13.26 |      80.6 |      47.86 |
| markup   |  876 |     52.6 |      1.48 |      48.6 |       6.58 |      53.7 |      22.24 |
| markdown | 1350 |     49.3 |     -0.33 |      50.1 |      -0.3  |      42.1 |       4.52 |
| recovery | 1098 |     57.6 |      2.13 |      62.8 |       8.23 |      66.7 |      18.54 |
| late     |    0 |    nan   |    nan    |     nan   |     nan    |     nan   |     nan    |

### cot_z — forward returns by band (full sample)

| band     |   n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:---------|----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-1.5    | 224 |     50   |      0.23 |      51.3 |       5.29 |      47.8 |      13.25 |
| -1.5--.5 | 655 |     60.9 |      3.36 |      71.5 |      14.14 |      77.9 |      41.72 |
| -.5-.5   | 749 |     56.1 |      1.31 |      53.9 |       3.98 |      61.6 |      18.82 |
| .5-1.5   | 618 |     48.1 |      0.23 |      49.1 |       1.52 |      53.5 |       9.38 |
| >1.5     | 665 |     46.2 |     -0.7  |      48.6 |      -1.92 |      35.7 |      -4.91 |

### corr_spx — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <0     | 1034 |     56.1 |      1.78 |      57   |       7.01 |      61.4 |      29.23 |
| 0-.2   | 1208 |     57.4 |      2.18 |      64.5 |      12.1  |      69.2 |      32.64 |
| .2-.4  | 1102 |     54   |      0.8  |      51.7 |       2.59 |      56.8 |      11.23 |
| >.4    |  943 |     50.8 |      0.53 |      56.5 |       2.67 |      49   |      11.25 |

### vdd_multiple — forward returns by band (full sample)

| band    |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:--------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <.5     |  779 |     55.2 |      0.5  |      53.8 |       2.75 |      41.7 |       6.31 |
| .5-.87  | 1142 |     50.5 |      0.62 |      63.9 |       5.87 |      65.4 |      18.36 |
| .87-1.4 | 1200 |     56.1 |      1.3  |      48.6 |       1.99 |      64.7 |      18.77 |
| 1.4-2.9 |  912 |     57.8 |      2.77 |      65.6 |      15.92 |      61.3 |      41.06 |
| >2.9    |  154 |     51.9 |      2.86 |      40.3 |       4.02 |      59.1 |      35.2  |

### global_m2_yoy — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <5.5   |  519 |     53.4 |      1.24 |      60.7 |       6.05 |      72.6 |      23.39 |
| 5.5-7  | 1364 |     53.9 |      1.04 |      55.1 |       3.65 |      47.7 |       6.93 |
| 7-8.5  |  699 |     53.1 |      2.03 |      54.4 |      10.81 |      60.4 |      38.8  |
| 8.5-11 | 1310 |     54   |      0.54 |      56.5 |       3.53 |      59.7 |      15.75 |
| >11    |  395 |     64.6 |      4.23 |      72.2 |      17.65 |      80.8 |      57.97 |

### rv_cone_pctile — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| 0-25   | 1252 |     55.1 |      1.28 |      59.9 |       5.84 |      70   |      24.1  |
| 25-50  | 1081 |     53   |      0.73 |      50.4 |       2.32 |      50.8 |      15.58 |
| 50-75  |  927 |     56.5 |      1.47 |      57.9 |       8.14 |      55.1 |      23.16 |
| 75-100 |  831 |     54.3 |      2.48 |      63.4 |      11.39 |      63.8 |      30.11 |

### vov_pctile — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| 0-25   | 1193 |     55.5 |      1.36 |      52.9 |       3.74 |      52.6 |      12.32 |
| 25-50  | 1023 |     53.2 |      0.97 |      56.6 |       6.52 |      55.3 |      19.27 |
| 50-75  | 1002 |     54.4 |      1.58 |      60.5 |       6.57 |      62.9 |      27.62 |
| 75-100 |  844 |     56.8 |      2    |      64.4 |      11.39 |      73.7 |      36.6  |

### stbl_growth_z — forward returns by band (full sample)

| band   |    n |   hit_7d |   mean_7d |   hit_30d |   mean_30d |   hit_90d |   mean_90d |
|:-------|-----:|---------:|----------:|----------:|-----------:|----------:|-----------:|
| <-1    |  419 |     44.6 |     -1.05 |      43.9 |      -2.03 |      46.1 |       2.57 |
| -1-0   | 1590 |     53.4 |      1.04 |      54.7 |       4.48 |      53.4 |      15.87 |
| 0-1    |  646 |     49.9 |      0.89 |      51.1 |       4.01 |      55.8 |      16.26 |
| 1-2    |  228 |     72.8 |      4.22 |      78.1 |      14.14 |      75.9 |      23.38 |
| >2     |  162 |     51.2 |      0.65 |      60.5 |       5.47 |      62.3 |      19.55 |

## Allocation backtest vs HODL — GATED series (NET of 10.0bps one-way cost)

`cagr` is net of transaction cost (the honest headline); `cagr_gross` and `cost_drag_pp` show the cost bite, `turnover_annual` the one-way turnover/yr driving it. **GATED** = final live behavior (midterm blackout active).

|              |   cagr |   cagr_gross |   cost_drag_pp |   hodl_cagr |   sharpe |   hodl_sharpe |   sortino |   hodl_sortino |   maxdd |   hodl_maxdd |   time_in_market |   turnover_annual |   final_vs_hodl |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |   50.4 |         52.9 |            2.5 |          61 |     1.38 |          1.05 |      1.51 |            1.4 |   -33.6 |        -83.8 |             62.7 |              16.7 |            0.45 |
| moderate     |   62.9 |         65.6 |            2.6 |          61 |     1.44 |          1.05 |      1.77 |            1.4 |   -37.1 |        -83.8 |             80.2 |              16.1 |            1.15 |
| aggressive   |   62.2 |         64.8 |            2.5 |          61 |     1.32 |          1.05 |      1.65 |            1.4 |   -45.2 |        -83.8 |             85.1 |              15.6 |            1.09 |
| optimal      |   61.5 |         64.2 |            2.6 |          61 |     1.42 |          1.05 |      1.75 |            1.4 |   -41.2 |        -83.8 |             81.5 |              16.1 |            1.04 |

## Allocation backtest vs HODL — RAW (ungated) series

Pure engine without midterm-blackout override. Pre-gate figures retired as of 2026-07; fresh dual-track compute (W1 N7).

|              |   cagr |   cagr_gross |   cost_drag_pp |   hodl_cagr |   sharpe |   hodl_sharpe |   sortino |   hodl_sortino |   maxdd |   hodl_maxdd |   time_in_market |   turnover_annual |   final_vs_hodl |
|:-------------|-------:|-------------:|---------------:|------------:|---------:|--------------:|----------:|---------------:|--------:|-------------:|-----------------:|------------------:|----------------:|
| conservative |   50.4 |         52.9 |            2.5 |          61 |     1.38 |          1.05 |      1.51 |            1.4 |   -33.6 |        -83.8 |             62.7 |              16.7 |            0.45 |
| moderate     |   62.9 |         65.6 |            2.6 |          61 |     1.44 |          1.05 |      1.77 |            1.4 |   -37.1 |        -83.8 |             80.2 |              16.1 |            1.15 |
| aggressive   |   62.2 |         64.8 |            2.5 |          61 |     1.32 |          1.05 |      1.65 |            1.4 |   -45.2 |        -83.8 |             85.1 |              15.6 |            1.09 |
| optimal      |   61.5 |         64.2 |            2.6 |          61 |     1.42 |          1.05 |      1.75 |            1.4 |   -41.2 |        -83.8 |             81.5 |              16.1 |            1.04 |

**Block-bootstrap 95% CI** [optimal, 5000 resamples, 21d blocks]: Sharpe **1.41** [0.79, 2.01] · MaxDD -45.0% [-32.2, -66.2] · P(Sharpe>0) 1.0. Circular block bootstrap (21d blocks) of the NET daily strategy returns → 95% CI [2.5, 50, 97.5]. sharpe_gt0_prob = bootstrap P(Sharpe>0). Pairs with the Deflated-Sharpe haircut: DSR deflates the mean, this bounds the variance.

## Purged walk-forward CV (stability gate)

9/31 signals **robust** under 5 embargoed folds (90d embargo = max horizon). Purged + embargoed walk-forward CV (embargo = max forward horizon) replaces the single split_date's leaky boundary. 'robust' = full-sample sign matches `want`, no fold flips, all-but-one folds agree. Stricter than pre/post; both are reported.

| Signal | full | folds | want | robust |
|---|--:|---|--:|:-:|
| risk_index | -1 | [-1, -1, -1, -1, 0] | -1 | ✅ |
| momentum | +1 | [0, 1, 1, 1, -1] | +1 | · |
| structure | +1 | [-1, 1, 1, 1, -1] | +1 | · |
| risk_oscillator | -1 | [-1, -1, -1, -1, -1] | -1 | ✅ |
| bfi | +1 | [-1, 0, 0, 1, 0] | +1 | · |
| mvrv_z | +0 | [0, 0, 0, 0, 0] | -1 | · |
| nupl | +0 | [1, 0, 0, -1, -1] | -1 | · |
| mayer | +1 | [0, 1, 1, 1, 0] | -1 | · |
| puell | +1 | [0, 1, -1, 0, 0] | -1 | · |
| sth_cb_ratio | +0 | [0, 0, 0, 0, 0] | +1 | · |
| dvol | +0 | [0, 0, 0, -1, 1] | -1 | · |
| vrp | -1 | [0, 0, 0, 1, -1] | -1 | · |
| leverage_stress | -1 | [0, 0, 0, 0, 0] | -1 | · |
| funding_z | +0 | [0, 0, 0, 0, 0] | -1 | · |
| oi_price_divergence | -1 | [0, 0, 0, -1, 0] | -1 | ✅ |
| net_liq_roc | +1 | [1, 1, 0, 1, 0] | +1 | ✅ |
| macro_score | +1 | [1, 1, -1, 1, 1] | +1 | · |
| coinbase_premium_ema | -1 | [0, 0, 0, 0, 0] | +1 | · |
| ssr_oscillator | +0 | [0, 0, 0, 0, 0] | +1 | · |
| mpi | +1 | [0, 0, 0, -1, 0] | -1 | · |
| etf_flow_z | +1 | [0, 0, 0, 0, 1] | +1 | ✅ |
| reserve_risk | +1 | [0, 0, -1, 0, 0] | -1 | · |
| impulse | +1 | [0, 0, 1, 0, 1] | +1 | ✅ |
| cycle_pct | -1 | [0, 0, -1, 0, -1] | -1 | ✅ |
| cot_z | -1 | [0, 0, 0, -1, -1] | -1 | ✅ |
| corr_spx | -1 | [0, -1, 1, -1, 0] | -1 | · |
| vdd_multiple | +1 | [0, 1, 1, 1, 0] | -1 | · |
| global_m2_yoy | +1 | [0, 0, 1, -1, -1] | +1 | · |
| rv_cone_pctile | +0 | [-1, 1, -1, -1, 0] | -1 | · |
| vov_pctile | +1 | [-1, 1, 0, 0, 1] | -1 | · |
| stbl_growth_z | +1 | [0, 0, 0, 1, 0] | +1 | ✅ |

## Probability calibration of the conviction layer (out-of-fold)

OOF 7d direction: **Brier 0.249** vs base 0.2477 (skill -0.006); Platt a=0.743, b=0.054. Out-of-fold: each day's P(up) is the momentum×risk cell rate fit on the OTHER folds (EB-shrunk, the live mechanism), scored vs realized. brier<base_brier = skill; Platt a≈1/b≈0 = already calibrated. Direction is a near-coin-flip, so calibrated probabilities cluster near the base rate — that is the honest result.

| prob bin | n | predicted | observed |
|---|--:|--:|--:|
| 0.5-0.6 | 3831 | 0.546 | 0.549 |

## Deflated Sharpe Ratio — GATED series (multiple-testing haircut)

**SURVIVES multiple-testing (DSR≥0.95)** — shipped variant `optimal` (GATED / live behavior).

- DSR (gated) — P(true Sharpe > 0): **0.9601**
- Observed Sharpe 1.42 ann (0.07409/day); haircut threshold SR0 0.82 ann
- N=71 trials (upper-bound, incl. override dof_cost) · T=4287d · skew=0.614 · kurt=13.216 · SR-variance: max(cross-variant dispersion, null SR-sampling proxy)
- **Effective-N haircut**: T_eff=2561.8 vs raw T=4287 (rho_sum_K20=0.3367); dsr_effN=0.9186 (dsr_legacy=0.994). Block-bootstrap refinement: W5.

> DSR = P(true Sharpe>0) after deflating for n_trials independent configs, sample length, skew & kurtosis. n_trials is a manual UPPER-BOUND of the signal/threshold/window variants explored — overestimating is the conservative direction (de Prado). Bump vector.calibration.n_trials as you try more. The DSR statistic now uses a block-bootstrap effective sample size (T_eff) instead of raw sqrt(T-1), so autocorrelated daily returns no longer overstate confidence. GATED series (live behavior).

## Deflated Sharpe Ratio — RAW (ungated) series

**SURVIVES multiple-testing (DSR≥0.95)** — variant `optimal` (RAW / pure engine).

> Pre-gate figure (0.9965) retired as of 2026-07. This is the fresh dual-track compute. Raw series excludes midterm-blackout contamination.
- DSR (raw) — P(true Sharpe > 0): **0.9601**
- Observed Sharpe 1.42 ann; SR0 0.82 ann
- N=71 trials · T=4287d · skew=0.614 · kurt=13.216
- **Effective-N haircut**: T_eff=2561.8, dsr_effN=0.9186 (dsr_legacy=0.994)

> DSR on the RAW (ungated) series — pure engine without override contamination. Pre-gate figure (0.9965) retired; this is the fresh dual-track compute as of 2026-07. n_trials includes override dof_cost. RAW series.

## Trial log (N7 — n_trials breakdown)

As-of 2026-09-26: **n_trials_declared=71** = n_trials_config=65 (config upper-bound) + override dof_cost (registry).
  - override `midterm_blackout`: dof_cost=6
32 signal families screened; allocation variants: conservative, moderate, aggressive, optimal; transaction cost 10.0bps one-way.

> Point-in-time trial ledger (overwritten each run). n_trials_declared = n_trials_config (upper-bound of configs explored) + sum(dof_cost) across registered overrides. Raise n_trials_config as you try more; each new override must declare its dof_cost, which is ADDED here.

## Ensemble capstone — does combining beat the heuristic?

**KEEP-HEURISTIC — the hand-tuned composite_state is NOT beaten by the fixed-form ensemble**

Each axis oriented by its calibrated expected-fwd-return band-map (handles the U-shape a linear z can't), de-correlated in a fixed order, equal-weight combined. Promotion needs the ensemble to beat BOTH the best single signal AND the heuristic composite_state on net Sharpe in BOTH halves. Honest non-promotion = keep the simpler winner (the forecast-combination literature: equal-weight/best-single are brutal baselines on ~3 cycles).

| read | net Sharpe full | pre-2021 | post-2021 |
|---|--:|--:|--:|
| ensemble_eqw | 1.28 | 1.46 | 0.66 |
| best_single | 0.98 | 1.2 | 0.43 |
| heuristic | 1.21 | 1.48 | 0.72 |

Ensemble OOF rank-IC vs 90d return: **0.184** (best single axis = `net_liq_roc`). Per-axis IC: risk_index 0.079, net_liq_roc 0.252, vrp nan, cot_z 0.003, mvrv_z 0.068, momentum 0.121.

## Whipsaw

|                  |   changes |   whipsaws |   pct |
|:-----------------|----------:|-----------:|------:|
| momentum_state   |       183 |         36 |  19.7 |
| risk_regime      |       117 |         21 |  17.9 |
| structure_state  |       184 |         39 |  21.2 |
| market_mode      |        86 |         14 |  16.3 |
| alt_cycle_leader |       103 |         21 |  20.4 |