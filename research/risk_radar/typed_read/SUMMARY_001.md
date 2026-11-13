# Typed read rr-typed-read-flags-001 — catch and false calls by channel-flag state (DESCRIPTION)

Ledger row `rr-typed-read-flags-001` (RD-signed; spec sha `72eeafb6a07e…`); chance account 14; nomination_possible false. Types `type_history_v1.parquet` d6e77b7c…; bm_ref rev1 f7350e6e…; adapter 50425797…; harness sha `9b18611e537a…`; runner `run_typed_001.py`. Raw output `out_001/result.json`.

> An idea first seen in a D cell is forward-only.

> The plain type table found flag-present days do not concentrate turns strongly (rate ratio 1.17–1.38 PRE, 0.88–1.11 D); this read asks a different question (catch and false calls by flag) and is description.

**How to read a cell.** `caught/clusters`, catch share, false calls per asset-year of sessions in that state, the object's alert share in that state, and the share of era sessions in that state. A cluster takes the flag state of its earliest turn's session; a false call takes the state of its alert-start session. Under 8 clusters: counts only (caught/clusters, false calls). Catch in a state partly follows how often the object is on in that state (the alert-share column); no cell is tested against a placebo or reference and nothing is declared from one. Every partition sums back to the bm_ref totals (asserted).


## PRE 2006-01-03..2019-12-31 — 21 series, 472 turns

Sensitivity: SA-1 2c PRE-differing turns removed: PENDING (SA-1 2c not landed).

Totals (bm_ref):

| object | clusters | caught | catch | false/asset-yr | alert share |
|---|---|---|---|---|---|
| credit_oas_roc | 127 | 35 | 0.276 | 1.39 | 0.135 |
| credit_hyg_tlt | 127 | 36 | 0.283 | 1.84 | 0.095 |
| rates_move | 127 | 26 | 0.205 | 1.21 | 0.115 |
| rates_realrate | 127 | 101 | 0.795 | 4.97 | 0.097 |
| bubble_ext | 127 | 30 | 0.236 | 2.56 | 0.127 |
| bubble_leadership | 127 | 42 | 0.331 | 2.92 | 0.127 |
| growth_defensives | 127 | 40 | 0.315 | 1.91 | 0.109 |
| growth_cyc_def | 127 | 47 | 0.370 | 2.07 | 0.108 |
| vol_term | 127 | 38 | 0.299 | 1.81 | 0.060 |
| global_breadth | 127 | 27 | 0.213 | 1.40 | 0.357 |
| jpy_carry | 127 | 67 | 0.528 | 3.47 | 0.112 |
| corr_floor_break | 127 | 11 | 0.087 | 0.57 | 0.018 |
| incumbent (object scored, not a feature) | 127 | 24 | 0.189 | 1.09 | 0.152 |

### flag_rate — conditioning

| object | multi-state clusters | absent (days 84.7%) | present (days 15.3%) |
|---|---|---|---|
| credit_oas_roc | 12 | 32/106 = 0.302; 1.21/yr; on 0.144 | 3/21 = 0.143; 2.36/yr; on 0.089 |
| credit_hyg_tlt | 12 | 34/106 = 0.321; 1.98/yr; on 0.107 | 2/21 = 0.095; 1.07/yr; on 0.026 |
| rates_move | 12 | 20/106 = 0.189; 0.96/yr; on 0.128 | 6/21 = 0.286; 2.56/yr; on 0.044 |
| rates_realrate | 12 | 81/106 = 0.764; 4.50/yr; on 0.086 | 20/21 = 0.952; 7.59/yr; on 0.157 |
| bubble_ext | 12 | 22/106 = 0.208; 2.21/yr; on 0.120 | 8/21 = 0.381; 4.49/yr; on 0.167 |
| bubble_leadership | 12 | 35/106 = 0.330; 3.02/yr; on 0.121 | 7/21 = 0.333; 2.36/yr; on 0.157 |
| growth_defensives | 12 | 36/106 = 0.340; 2.13/yr; on 0.120 | 4/21 = 0.190; 0.68/yr; on 0.049 |
| growth_cyc_def | 12 | 42/106 = 0.396; 2.27/yr; on 0.120 | 5/21 = 0.238; 0.97/yr; on 0.037 |
| vol_term | 12 | 32/106 = 0.302; 1.88/yr; on 0.055 | 6/21 = 0.286; 1.41/yr; on 0.085 |
| global_breadth | 12 | 22/106 = 0.208; 1.33/yr; on 0.394 | 5/21 = 0.238; 1.79/yr; on 0.154 |
| jpy_carry | 12 | 59/106 = 0.557; 3.52/yr; on 0.118 | 8/21 = 0.381; 3.24/yr; on 0.079 |
| corr_floor_break | 12 | 7/106 = 0.066; 0.57/yr; on 0.018 | 4/21 = 0.190; 0.59/yr; on 0.013 |
| incumbent (object scored, not a feature) | 12 | 22/106 = 0.208; 1.27/yr; on 0.170 | 2/21 = 0.095; 0.07/yr; on 0.057 |

### flag_easing — conditioning

| object | multi-state clusters | absent (days 99.4%) | present (days 0.6%) |
|---|---|---|---|
| credit_oas_roc | 1 | 35/125 = 0.280; 1.40/yr; on 0.135 | 0/2; fc 0 (counts only) |
| credit_hyg_tlt | 1 | 36/125 = 0.288; 1.85/yr; on 0.095 | 0/2; fc 0 (counts only) |
| rates_move | 1 | 24/125 = 0.192; 1.22/yr; on 0.115 | 2/2; fc 0 (counts only) |
| rates_realrate | 1 | 99/125 = 0.792; 5.00/yr; on 0.097 | 2/2; fc 0 (counts only) |
| bubble_ext | 1 | 30/125 = 0.240; 2.58/yr; on 0.128 | 0/2; fc 0 (counts only) |
| bubble_leadership | 1 | 41/125 = 0.328; 2.88/yr; on 0.126 | 1/2; fc 16 (counts only) |
| growth_defensives | 1 | 40/125 = 0.320; 1.90/yr; on 0.109 | 0/2; fc 4 (counts only) |
| growth_cyc_def | 1 | 47/125 = 0.376; 2.08/yr; on 0.108 | 0/2; fc 0 (counts only) |
| vol_term | 1 | 38/125 = 0.304; 1.82/yr; on 0.059 | 0/2; fc 0 (counts only) |
| global_breadth | 1 | 26/125 = 0.208; 1.41/yr; on 0.355 | 1/2; fc 0 (counts only) |
| jpy_carry | 1 | 66/125 = 0.528; 3.45/yr; on 0.111 | 1/2; fc 14 (counts only) |
| corr_floor_break | 1 | 11/125 = 0.088; 0.57/yr; on 0.018 | 0/2; fc 0 (counts only) |
| incumbent (object scored, not a feature) | 1 | 23/125 = 0.184; 1.10/yr; on 0.151 | 1/2; fc 0 (counts only) |

### flag_real_rate — description; fails the coverage line in PRE (Addendum A §2)

| object | multi-state clusters | absent (days 84.6%) | present (days 15.4%) |
|---|---|---|---|
| credit_oas_roc | 9 | 29/106 = 0.274; 1.22/yr; on 0.121 | 6/21 = 0.286; 2.28/yr; on 0.211 |
| credit_hyg_tlt | 9 | 31/106 = 0.292; 1.97/yr; on 0.096 | 5/21 = 0.238; 1.16/yr; on 0.088 |
| rates_move | 9 | 19/106 = 0.179; 1.00/yr; on 0.112 | 7/21 = 0.333; 2.32/yr; on 0.131 |
| rates_realrate | 9 | 80/106 = 0.755; 4.34/yr; on 0.079 | 21/21 = 1.000; 8.36/yr; on 0.194 |
| bubble_ext | 9 | 23/106 = 0.217; 2.22/yr; on 0.126 | 7/21 = 0.333; 4.40/yr; on 0.134 |
| bubble_leadership | 9 | 37/106 = 0.349; 3.12/yr; on 0.127 | 5/21 = 0.238; 1.84/yr; on 0.124 |
| growth_defensives | 9 | 35/106 = 0.330; 2.17/yr; on 0.110 | 5/21 = 0.238; 0.50/yr; on 0.102 |
| growth_cyc_def | 9 | 38/106 = 0.358; 2.29/yr; on 0.105 | 9/21 = 0.429; 0.92/yr; on 0.119 |
| vol_term | 9 | 30/106 = 0.283; 1.87/yr; on 0.054 | 8/21 = 0.381; 1.47/yr; on 0.091 |
| global_breadth | 9 | 23/106 = 0.217; 1.39/yr; on 0.369 | 4/21 = 0.190; 1.47/yr; on 0.293 |
| jpy_carry | 9 | 59/106 = 0.557; 3.63/yr; on 0.111 | 8/21 = 0.381; 2.67/yr; on 0.117 |
| corr_floor_break | 9 | 9/106 = 0.085; 0.68/yr; on 0.020 | 2/21 = 0.095; 0.00/yr; on 0.004 |
| incumbent (object scored, not a feature) | 9 | 21/106 = 0.198; 1.25/yr; on 0.152 | 3/21 = 0.143; 0.26/yr; on 0.157 |

### flag_credit_pressure — description; fails the coverage line in PRE (Addendum A §2)

| object | multi-state clusters | absent (days 78.8%) | present (days 21.1%) |
|---|---|---|---|
| credit_oas_roc | 5 | 20/103 = 0.194; 1.13/yr; on 0.049 | 15/24 = 0.625; 2.36/yr; on 0.461 |
| credit_hyg_tlt | 5 | 24/103 = 0.233; 1.38/yr; on 0.039 | 12/24 = 0.500; 3.57/yr; on 0.303 |
| rates_move | 5 | 14/103 = 0.136; 0.64/yr; on 0.041 | 12/24 = 0.500; 3.36/yr; on 0.394 |
| rates_realrate | 5 | 79/103 = 0.767; 5.22/yr; on 0.091 | 22/24 = 0.917; 4.03/yr; on 0.122 |
| bubble_ext | 5 | 29/103 = 0.282; 3.23/yr; on 0.158 | 1/24 = 0.042; 0.07/yr; on 0.010 |
| bubble_leadership | 5 | 39/103 = 0.379; 3.02/yr; on 0.142 | 3/24 = 0.125; 2.53/yr; on 0.069 |
| growth_defensives | 5 | 23/103 = 0.223; 1.39/yr; on 0.071 | 17/24 = 0.708; 3.85/yr; on 0.251 |
| growth_cyc_def | 5 | 33/103 = 0.320; 1.62/yr; on 0.063 | 14/24 = 0.583; 3.79/yr; on 0.277 |
| vol_term | 5 | 31/103 = 0.301; 1.75/yr; on 0.050 | 7/24 = 0.292; 2.00/yr; on 0.095 |
| global_breadth | 5 | 22/103 = 0.214; 1.33/yr; on 0.217 | 5/24 = 0.208; 1.69/yr; on 0.884 |
| jpy_carry | 5 | 51/103 = 0.495; 2.97/yr; on 0.086 | 16/24 = 0.667; 5.36/yr; on 0.212 |
| corr_floor_break | 5 | 11/103 = 0.107; 0.72/yr; on 0.021 | 0/24 = 0.000; 0.00/yr; on 0.004 |
| incumbent (object scored, not a feature) | 5 | 10/103 = 0.097; 0.71/yr; on 0.059 | 14/24 = 0.583; 2.53/yr; on 0.505 |

### flag_credit_level — description; fails the coverage line in PRE (Addendum A §2)

| object | multi-state clusters | absent (days 80.8%) | present (days 19.2%) |
|---|---|---|---|
| credit_oas_roc | 2 | 24/101 = 0.238; 1.17/yr; on 0.092 | 11/26 = 0.423; 2.33/yr; on 0.321 |
| credit_hyg_tlt | 2 | 28/101 = 0.277; 1.74/yr; on 0.078 | 8/26 = 0.308; 2.29/yr; on 0.165 |
| rates_move | 2 | 15/101 = 0.149; 1.03/yr; on 0.053 | 11/26 = 0.423; 1.98/yr; on 0.380 |
| rates_realrate | 2 | 75/101 = 0.743; 4.96/yr; on 0.084 | 26/26 = 1.000; 5.04/yr; on 0.154 |
| bubble_ext | 2 | 30/101 = 0.297; 3.16/yr; on 0.157 | 0/26 = 0.000; 0.00/yr; on 0.000 |
| bubble_leadership | 2 | 30/101 = 0.297; 2.94/yr; on 0.112 | 12/26 = 0.462; 2.80/yr; on 0.188 |
| growth_defensives | 2 | 27/101 = 0.267; 1.85/yr; on 0.087 | 13/26 = 0.500; 2.16/yr; on 0.201 |
| growth_cyc_def | 2 | 34/101 = 0.337; 1.73/yr; on 0.078 | 13/26 = 0.500; 3.55/yr; on 0.235 |
| vol_term | 2 | 34/101 = 0.337; 1.97/yr; on 0.064 | 4/26 = 0.154; 1.08/yr; on 0.041 |
| global_breadth | 2 | 20/101 = 0.198; 1.50/yr; on 0.251 | 7/26 = 0.269; 0.97/yr; on 0.810 |
| jpy_carry | 2 | 47/101 = 0.465; 3.22/yr; on 0.081 | 20/26 = 0.769; 4.58/yr; on 0.244 |
| corr_floor_break | 2 | 11/101 = 0.109; 0.70/yr; on 0.022 | 0/26 = 0.000; 0.00/yr; on 0.000 |
| incumbent (object scored, not a feature) | 2 | 11/101 = 0.109; 0.73/yr; on 0.061 | 13/26 = 0.500; 2.64/yr; on 0.545 |

### flag_dollar — description; fails the coverage line in PRE (Addendum A §2)

| object | multi-state clusters | absent (days 76.6%) | present (days 16.2%) | unavailable (days 7.1%) |
|---|---|---|---|---|
| credit_oas_roc | 1 | 24/101 = 0.238; 1.23/yr; on 0.116 | 10/17 = 0.588; 2.38/yr; on 0.266 | 1/9 = 0.111; 0.65/yr; on 0.020 |
| credit_hyg_tlt | 1 | 24/101 = 0.238; 1.36/yr; on 0.069 | 12/17 = 0.706; 4.74/yr; on 0.248 | 0/9 = 0.000; 0.00/yr; on 0.000 |
| rates_move | 1 | 18/101 = 0.178; 0.93/yr; on 0.102 | 8/17 = 0.471; 2.96/yr; on 0.220 | 0/9 = 0.000; 0.00/yr; on 0.000 |
| rates_realrate | 1 | 81/101 = 0.802; 5.02/yr; on 0.098 | 15/17 = 0.882; 5.01/yr; on 0.112 | 5/9 = 0.556; 4.33/yr; on 0.052 |
| bubble_ext | 1 | 23/101 = 0.228; 2.84/yr; on 0.127 | 1/17 = 0.059; 1.24/yr; on 0.038 | 6/9 = 0.667; 2.65/yr; on 0.364 |
| bubble_leadership | 1 | 39/101 = 0.386; 3.10/yr; on 0.143 | 1/17 = 0.059; 2.90/yr; on 0.099 | 2/9 = 0.222; 0.70/yr; on 0.004 |
| growth_defensives | 1 | 26/101 = 0.257; 1.49/yr; on 0.081 | 10/17 = 0.588; 3.25/yr; on 0.225 | 4/9 = 0.444; 3.41/yr; on 0.139 |
| growth_cyc_def | 1 | 38/101 = 0.376; 1.97/yr; on 0.103 | 8/17 = 0.471; 3.09/yr; on 0.134 | 1/9 = 0.111; 0.70/yr; on 0.093 |
| vol_term | 1 | 32/101 = 0.317; 1.90/yr; on 0.064 | 6/17 = 0.353; 2.07/yr; on 0.064 | 0/9 = 0.000; 0.00/yr; on 0.000 |
| global_breadth | 1 | 21/101 = 0.208; 1.03/yr; on 0.263 | 2/17 = 0.118; 1.39/yr; on 0.798 | 4/9 = 0.444; 5.95/yr; on 0.329 |
| jpy_carry | 1 | 51/101 = 0.505; 3.43/yr; on 0.110 | 9/17 = 0.529; 3.75/yr; on 0.115 | 7/9 = 0.778; 3.25/yr; on 0.127 |
| corr_floor_break | 1 | 11/101 = 0.109; 0.74/yr; on 0.021 | 0/17 = 0.000; 0.00/yr; on 0.010 | 0/9 = 0.000; 0.00/yr; on 0.000 |
| incumbent (object scored, not a feature) | 1 | 17/101 = 0.168; 0.88/yr; on 0.113 | 5/17 = 0.294; 2.09/yr; on 0.368 | 2/9 = 0.222; 1.03/yr; on 0.073 |

### core_label — description only (core label fails the coverage line in every era)

Published-U share over this read window: 69.74% (breadth source: {'dated': 3523}). Printed as required beside a core-label table; the coverage verdict is the RD's (Addendum A §2, applied once), not re-run here.

| object | multi-state clusters | B (days 15.3%) | D (days 3.7%) | N (days 3.1%) | S (days 8.1%) | U (days 69.7%) |
|---|---|---|---|---|---|---|
| credit_oas_roc | 18 | 0/25 = 0.000; 0.00/yr; on 0.000 | 2/4; fc 6 (counts only) | 0/2; fc 43 (counts only) | 5/10 = 0.500; 2.10/yr; on 0.451 | 28/86 = 0.326; 1.51/yr; on 0.107 |
| credit_hyg_tlt | 18 | 3/25 = 0.120; 0.32/yr; on 0.002 | 3/4; fc 19 (counts only) | 0/2; fc 28 (counts only) | 4/10 = 0.400; 2.93/yr; on 0.278 | 26/86 = 0.302; 2.00/yr; on 0.069 |
| rates_move | 18 | 2/25 = 0.080; 0.00/yr; on 0.013 | 3/4; fc 27 (counts only) | 0/2; fc 12 (counts only) | 1/10 = 0.100; 2.58/yr; on 0.484 | 20/86 = 0.233; 1.24/yr; on 0.094 |
| rates_realrate | 18 | 19/25 = 0.760; 5.84/yr; on 0.093 | 4/4; fc 29 (counts only) | 1/2; fc 14 (counts only) | 10/10 = 1.000; 6.48/yr; on 0.188 | 67/86 = 0.779; 4.89/yr; on 0.090 |
| bubble_ext | 18 | 10/25 = 0.400; 3.46/yr; on 0.313 | 0/4; fc 0 (counts only) | 0/2; fc 0 (counts only) | 0/10 = 0.000; 0.00/yr; on 0.000 | 20/86 = 0.233; 2.91/yr; on 0.113 |
| bubble_leadership | 18 | 6/25 = 0.240; 5.00/yr; on 0.166 | 0/4; fc 6 (counts only) | 0/2; fc 7 (counts only) | 3/10 = 0.300; 2.54/yr; on 0.153 | 33/86 = 0.384; 2.72/yr; on 0.124 |
| growth_defensives | 18 | 7/25 = 0.280; 0.20/yr; on 0.005 | 3/4; fc 68 (counts only) | 1/2; fc 18 (counts only) | 8/10 = 0.800; 1.53/yr; on 0.298 | 21/86 = 0.244; 2.08/yr; on 0.094 |
| growth_cyc_def | 18 | 5/25 = 0.200; 0.86/yr; on 0.015 | 3/4; fc 3 (counts only) | 1/2; fc 52 (counts only) | 6/10 = 0.600; 5.73/yr; on 0.304 | 32/86 = 0.372; 1.85/yr; on 0.094 |
| vol_term | 18 | 4/25 = 0.160; 0.43/yr; on 0.009 | 2/4; fc 50 (counts only) | 1/2; fc 4 (counts only) | 1/10 = 0.100; 0.26/yr; on 0.044 | 30/86 = 0.349; 2.19/yr; on 0.069 |
| global_breadth | 18 | 0/25 = 0.000; 0.57/yr; on 0.049 | 0/4; fc 4 (counts only) | 0/2; fc 21 (counts only) | 0/10 = 0.000; 0.00/yr; on 0.989 | 27/86 = 0.314; 1.76/yr; on 0.326 |
| jpy_carry | 18 | 12/25 = 0.480; 3.98/yr; on 0.110 | 3/4; fc 70 (counts only) | 0/2; fc 9 (counts only) | 8/10 = 0.800; 3.28/yr; on 0.243 | 44/86 = 0.512; 3.34/yr; on 0.091 |
| corr_floor_break | 18 | 3/25 = 0.120; 0.14/yr; on 0.002 | 0/4; fc 0 (counts only) | 1/2; fc 0 (counts only) | 0/10 = 0.000; 0.00/yr; on 0.000 | 7/86 = 0.081; 0.79/yr; on 0.022 |
| incumbent (object scored, not a feature) | 18 | 0/25 = 0.000; 0.00/yr; on 0.000 | 4/4; fc 42 (counts only) | 0/2; fc 0 (counts only) | 5/10 = 0.500; 1.23/yr; on 0.860 | 15/86 = 0.174; 1.21/yr; on 0.082 |

## D 2020-01-02..2023-12-29 — 21 series, 191 turns

Sensitivity: edge-turns line: PENDING (SA-1 2c not landed).

Totals (bm_ref):

| object | clusters | caught | catch | false/asset-yr | alert share |
|---|---|---|---|---|---|
| credit_oas_roc | 45 | 14 | 0.311 | 1.52 | 0.117 |
| credit_hyg_tlt | 45 | 15 | 0.333 | 2.40 | 0.108 |
| rates_move | 45 | 19 | 0.422 | 1.72 | 0.250 |
| rates_realrate | 45 | 37 | 0.822 | 4.71 | 0.139 |
| bubble_ext | 45 | 12 | 0.267 | 2.46 | 0.188 |
| bubble_leadership | 45 | 17 | 0.378 | 3.20 | 0.148 |
| growth_defensives | 45 | 19 | 0.422 | 2.32 | 0.094 |
| growth_cyc_def | 45 | 16 | 0.356 | 1.89 | 0.124 |
| vol_term | 45 | 22 | 0.489 | 1.90 | 0.105 |
| global_breadth | 45 | 10 | 0.222 | 0.95 | 0.329 |
| jpy_carry | 45 | 30 | 0.667 | 3.36 | 0.145 |
| corr_floor_break | 45 | 5 | 0.111 | 0.64 | 0.021 |
| incumbent (object scored, not a feature) | 45 | 15 | 0.333 | 1.00 | 0.224 |

### flag_rate — conditioning

| object | multi-state clusters | absent (days 72.8%) | present (days 27.2%) |
|---|---|---|---|
| credit_oas_roc | 4 | 10/37 = 0.270; 1.45/yr; on 0.093 | 4/8 = 0.500; 1.70/yr; on 0.182 |
| credit_hyg_tlt | 4 | 14/37 = 0.378; 3.03/yr; on 0.133 | 1/8 = 0.125; 0.70/yr; on 0.040 |
| rates_move | 4 | 15/37 = 0.405; 1.78/yr; on 0.171 | 4/8 = 0.500; 1.53/yr; on 0.466 |
| rates_realrate | 4 | 29/37 = 0.784; 4.99/yr; on 0.112 | 8/8 = 1.000; 3.97/yr; on 0.215 |
| bubble_ext | 4 | 11/37 = 0.297; 2.29/yr; on 0.206 | 1/8 = 0.125; 2.92/yr; on 0.138 |
| bubble_leadership | 4 | 16/37 = 0.432; 3.51/yr; on 0.176 | 1/8 = 0.125; 2.35/yr; on 0.073 |
| growth_defensives | 4 | 12/37 = 0.324; 2.04/yr; on 0.075 | 7/8 = 0.875; 3.09/yr; on 0.146 |
| growth_cyc_def | 4 | 11/37 = 0.297; 1.47/yr; on 0.085 | 5/8 = 0.625; 3.05/yr; on 0.229 |
| vol_term | 4 | 16/37 = 0.432; 1.71/yr; on 0.088 | 6/8 = 0.750; 2.44/yr; on 0.153 |
| global_breadth | 4 | 9/37 = 0.243; 0.92/yr; on 0.249 | 1/8 = 0.125; 1.00/yr; on 0.549 |
| jpy_carry | 4 | 27/37 = 0.730; 4.05/yr; on 0.177 | 3/8 = 0.375; 1.48/yr; on 0.058 |
| corr_floor_break | 4 | 5/37 = 0.135; 0.75/yr; on 0.023 | 0/8 = 0.000; 0.35/yr; on 0.018 |
| incumbent (object scored, not a feature) | 4 | 11/37 = 0.297; 1.07/yr; on 0.152 | 4/8 = 0.500; 0.83/yr; on 0.422 |

### flag_easing — conditioning

| object | multi-state clusters | absent (days 98.8%) | present (days 1.2%) |
|---|---|---|---|
| credit_oas_roc | 1 | 14/45 = 0.311; 1.53/yr; on 0.117 | 0/0; fc 0 (counts only) |
| credit_hyg_tlt | 1 | 15/45 = 0.333; 2.43/yr; on 0.109 | 0/0; fc 0 (counts only) |
| rates_move | 1 | 19/45 = 0.422; 1.74/yr; on 0.250 | 0/0; fc 0 (counts only) |
| rates_realrate | 1 | 37/45 = 0.822; 4.77/yr; on 0.140 | 0/0; fc 0 (counts only) |
| bubble_ext | 1 | 12/45 = 0.267; 2.49/yr; on 0.190 | 0/0; fc 0 (counts only) |
| bubble_leadership | 1 | 17/45 = 0.378; 3.24/yr; on 0.150 | 0/0; fc 0 (counts only) |
| growth_defensives | 1 | 19/45 = 0.422; 2.35/yr; on 0.093 | 0/0; fc 0 (counts only) |
| growth_cyc_def | 1 | 16/45 = 0.356; 1.91/yr; on 0.125 | 0/0; fc 0 (counts only) |
| vol_term | 1 | 22/45 = 0.489; 1.92/yr; on 0.106 | 0/0; fc 0 (counts only) |
| global_breadth | 1 | 10/45 = 0.222; 0.96/yr; on 0.324 | 0/0; fc 0 (counts only) |
| jpy_carry | 1 | 30/45 = 0.667; 3.40/yr; on 0.147 | 0/0; fc 0 (counts only) |
| corr_floor_break | 1 | 5/45 = 0.111; 0.65/yr; on 0.022 | 0/0; fc 0 (counts only) |
| incumbent (object scored, not a feature) | 1 | 15/45 = 0.333; 1.02/yr; on 0.225 | 0/0; fc 0 (counts only) |

### flag_real_rate — conditioning

| object | multi-state clusters | absent (days 73.4%) | present (days 26.6%) |
|---|---|---|---|
| credit_oas_roc | 4 | 8/35 = 0.229; 0.90/yr; on 0.080 | 6/10 = 0.600; 3.25/yr; on 0.220 |
| credit_hyg_tlt | 4 | 14/35 = 0.400; 2.62/yr; on 0.123 | 1/10 = 0.100; 1.78/yr; on 0.067 |
| rates_move | 4 | 13/35 = 0.371; 1.82/yr; on 0.142 | 6/10 = 0.600; 1.43/yr; on 0.554 |
| rates_realrate | 4 | 27/35 = 0.771; 4.99/yr; on 0.103 | 10/10 = 1.000; 3.92/yr; on 0.242 |
| bubble_ext | 4 | 11/35 = 0.314; 2.37/yr; on 0.235 | 1/10 = 0.100; 2.72/yr; on 0.056 |
| bubble_leadership | 4 | 17/35 = 0.486; 4.06/yr; on 0.199 | 0/10 = 0.000; 0.76/yr; on 0.004 |
| growth_defensives | 4 | 10/35 = 0.286; 1.80/yr; on 0.069 | 9/10 = 0.900; 3.79/yr; on 0.164 |
| growth_cyc_def | 4 | 11/35 = 0.314; 1.50/yr; on 0.078 | 5/10 = 0.500; 2.99/yr; on 0.253 |
| vol_term | 4 | 13/35 = 0.371; 1.50/yr; on 0.078 | 9/10 = 0.900; 3.03/yr; on 0.182 |
| global_breadth | 4 | 8/35 = 0.229; 0.96/yr; on 0.195 | 2/10 = 0.200; 0.89/yr; on 0.706 |
| jpy_carry | 4 | 26/35 = 0.743; 3.97/yr; on 0.167 | 4/10 = 0.400; 1.65/yr; on 0.082 |
| corr_floor_break | 4 | 4/35 = 0.114; 0.79/yr; on 0.016 | 1/10 = 0.100; 0.22/yr; on 0.037 |
| incumbent (object scored, not a feature) | 4 | 10/35 = 0.286; 0.90/yr; on 0.115 | 5/10 = 0.500; 1.29/yr; on 0.532 |

### flag_credit_pressure — conditioning

| object | multi-state clusters | absent (days 81.2%) | present (days 18.8%) |
|---|---|---|---|
| credit_oas_roc | 3 | 10/37 = 0.270; 1.32/yr; on 0.042 | 4/8 = 0.500; 2.41/yr; on 0.450 |
| credit_hyg_tlt | 3 | 12/37 = 0.324; 2.27/yr; on 0.088 | 3/8 = 0.375; 2.98/yr; on 0.196 |
| rates_move | 3 | 15/37 = 0.405; 1.89/yr; on 0.166 | 4/8 = 0.500; 0.95/yr; on 0.624 |
| rates_realrate | 3 | 29/37 = 0.784; 5.06/yr; on 0.116 | 8/8 = 1.000; 3.17/yr; on 0.243 |
| bubble_ext | 3 | 12/37 = 0.324; 3.02/yr; on 0.230 | 0/8 = 0.000; 0.00/yr; on 0.000 |
| bubble_leadership | 3 | 17/37 = 0.459; 3.92/yr; on 0.181 | 0/8 = 0.000; 0.00/yr; on 0.000 |
| growth_defensives | 3 | 13/37 = 0.351; 2.23/yr; on 0.066 | 6/8 = 0.750; 2.72/yr; on 0.217 |
| growth_cyc_def | 3 | 11/37 = 0.297; 1.86/yr; on 0.087 | 5/8 = 0.625; 2.03/yr; on 0.286 |
| vol_term | 3 | 17/37 = 0.459; 2.13/yr; on 0.081 | 5/8 = 0.625; 0.89/yr; on 0.212 |
| global_breadth | 3 | 8/37 = 0.216; 1.02/yr; on 0.198 | 2/8 = 0.250; 0.63/yr; on 0.910 |
| jpy_carry | 3 | 25/37 = 0.676; 3.59/yr; on 0.152 | 5/8 = 0.625; 2.34/yr; on 0.116 |
| corr_floor_break | 3 | 4/37 = 0.108; 0.79/yr; on 0.026 | 1/8 = 0.125; 0.00/yr; on 0.000 |
| incumbent (object scored, not a feature) | 3 | 8/37 = 0.216; 0.70/yr; on 0.126 | 7/8 = 0.875; 2.34/yr; on 0.656 |

### flag_credit_level — conditioning

| object | multi-state clusters | absent (days 82.7%) | present (days 17.3%) |
|---|---|---|---|
| credit_oas_roc | 0 | 13/36 = 0.361; 1.67/yr; on 0.088 | 1/9 = 0.111; 0.76/yr; on 0.259 |
| credit_hyg_tlt | 0 | 12/36 = 0.333; 2.09/yr; on 0.086 | 3/9 = 0.333; 3.93/yr; on 0.218 |
| rates_move | 0 | 18/36 = 0.500; 2.07/yr; on 0.252 | 1/9 = 0.111; 0.00/yr; on 0.241 |
| rates_realrate | 0 | 28/36 = 0.778; 4.64/yr; on 0.140 | 9/9 = 1.000; 5.10/yr; on 0.138 |
| bubble_ext | 0 | 8/36 = 0.222; 2.42/yr; on 0.191 | 4/9 = 0.444; 2.69/yr; on 0.172 |
| bubble_leadership | 0 | 14/36 = 0.389; 3.33/yr; on 0.168 | 3/9 = 0.333; 2.55/yr; on 0.052 |
| growth_defensives | 0 | 18/36 = 0.500; 1.88/yr; on 0.097 | 1/9 = 0.111; 4.48/yr; on 0.075 |
| growth_cyc_def | 0 | 14/36 = 0.389; 1.91/yr; on 0.122 | 2/9 = 0.222; 1.79/yr; on 0.132 |
| vol_term | 0 | 21/36 = 0.583; 2.29/yr; on 0.097 | 1/9 = 0.111; 0.00/yr; on 0.143 |
| global_breadth | 0 | 9/36 = 0.250; 1.14/yr; on 0.301 | 1/9 = 0.111; 0.00/yr; on 0.466 |
| jpy_carry | 0 | 22/36 = 0.611; 2.91/yr; on 0.133 | 8/9 = 0.889; 5.58/yr; on 0.207 |
| corr_floor_break | 0 | 5/36 = 0.139; 0.77/yr; on 0.026 | 0/9 = 0.000; 0.00/yr; on 0.000 |
| incumbent (object scored, not a feature) | 0 | 11/36 = 0.306; 0.83/yr; on 0.206 | 4/9 = 0.444; 1.86/yr; on 0.310 |

### flag_dollar — conditioning

| object | multi-state clusters | absent (days 79.2%) | present (days 20.8%) |
|---|---|---|---|
| credit_oas_roc | 4 | 9/35 = 0.257; 1.49/yr; on 0.081 | 5/10 = 0.500; 1.61/yr; on 0.259 |
| credit_hyg_tlt | 4 | 10/35 = 0.286; 2.33/yr; on 0.112 | 5/10 = 0.500; 2.70/yr; on 0.091 |
| rates_move | 4 | 13/35 = 0.371; 1.67/yr; on 0.207 | 6/10 = 0.600; 1.89/yr; on 0.421 |
| rates_realrate | 4 | 27/35 = 0.771; 4.53/yr; on 0.131 | 10/10 = 1.000; 5.45/yr; on 0.172 |
| bubble_ext | 4 | 12/35 = 0.343; 3.09/yr; on 0.236 | 0/10 = 0.000; 0.00/yr; on 0.000 |
| bubble_leadership | 4 | 15/35 = 0.429; 4.01/yr; on 0.186 | 2/10 = 0.200; 0.00/yr; on 0.000 |
| growth_defensives | 4 | 13/35 = 0.371; 2.21/yr; on 0.078 | 6/10 = 0.600; 2.75/yr; on 0.153 |
| growth_cyc_def | 4 | 12/35 = 0.343; 1.77/yr; on 0.095 | 4/10 = 0.400; 2.35/yr; on 0.235 |
| vol_term | 4 | 16/35 = 0.457; 1.64/yr; on 0.084 | 6/10 = 0.600; 2.92/yr; on 0.187 |
| global_breadth | 4 | 7/35 = 0.200; 1.13/yr; on 0.198 | 3/10 = 0.300; 0.23/yr; on 0.842 |
| jpy_carry | 4 | 23/35 = 0.657; 3.63/yr; on 0.155 | 7/10 = 0.700; 2.29/yr; on 0.105 |
| corr_floor_break | 4 | 4/35 = 0.114; 0.81/yr; on 0.027 | 1/10 = 0.100; 0.00/yr; on 0.000 |
| incumbent (object scored, not a feature) | 4 | 9/35 = 0.257; 0.83/yr; on 0.125 | 6/10 = 0.600; 1.66/yr; on 0.612 |

### core_label — description only (core label fails the coverage line in every era)

Published-U share over this read window: 71.07% (breadth source: {'dated': 1006}). Printed as required beside a core-label table; the coverage verdict is the RD's (Addendum A §2, applied once), not re-run here.

| object | multi-state clusters | B (days 8.6%) | D (days 9.0%) | N (days 5.8%) | S (days 5.6%) | U (days 71.1%) |
|---|---|---|---|---|---|---|
| credit_oas_roc | 5 | 0/4; fc 0 (counts only) | 0/1; fc 50 (counts only) | 0/2; fc 13 (counts only) | 2/3; fc 0 (counts only) | 12/35 = 0.343; 1.09/yr; on 0.078 |
| credit_hyg_tlt | 5 | 1/4; fc 8 (counts only) | 0/1; fc 40 (counts only) | 0/2; fc 6 (counts only) | 2/3; fc 12 (counts only) | 12/35 = 0.343; 2.28/yr; on 0.088 |
| rates_move | 5 | 0/4; fc 11 (counts only) | 0/1; fc 16 (counts only) | 0/2; fc 24 (counts only) | 2/3; fc 0 (counts only) | 17/35 = 0.486; 1.57/yr; on 0.199 |
| rates_realrate | 5 | 1/4; fc 6 (counts only) | 1/1; fc 19 (counts only) | 2/2; fc 8 (counts only) | 3/3; fc 36 (counts only) | 30/35 = 0.857; 5.46/yr; on 0.139 |
| bubble_ext | 5 | 2/4; fc 39 (counts only) | 0/1; fc 0 (counts only) | 1/2; fc 0 (counts only) | 0/3; fc 0 (counts only) | 9/35 = 0.257; 2.80/yr; on 0.204 |
| bubble_leadership | 5 | 2/4; fc 36 (counts only) | 0/1; fc 0 (counts only) | 1/2; fc 16 (counts only) | 0/3; fc 0 (counts only) | 14/35 = 0.400; 3.62/yr; on 0.143 |
| growth_defensives | 5 | 3/4; fc 9 (counts only) | 1/1; fc 35 (counts only) | 0/2; fc 33 (counts only) | 2/3; fc 4 (counts only) | 13/35 = 0.371; 1.92/yr; on 0.079 |
| growth_cyc_def | 5 | 1/4; fc 9 (counts only) | 1/1; fc 31 (counts only) | 0/2; fc 4 (counts only) | 3/3; fc 12 (counts only) | 11/35 = 0.314; 1.73/yr; on 0.103 |
| vol_term | 5 | 1/4; fc 8 (counts only) | 1/1; fc 38 (counts only) | 1/2; fc 6 (counts only) | 2/3; fc 2 (counts only) | 17/35 = 0.486; 1.78/yr; on 0.087 |
| global_breadth | 5 | 0/4; fc 0 (counts only) | 0/1; fc 0 (counts only) | 1/2; fc 0 (counts only) | 2/3; fc 0 (counts only) | 7/35 = 0.200; 1.32/yr; on 0.253 |
| jpy_carry | 5 | 3/4; fc 47 (counts only) | 0/1; fc 5 (counts only) | 1/2; fc 4 (counts only) | 3/3; fc 34 (counts only) | 23/35 = 0.657; 3.23/yr; on 0.140 |
| corr_floor_break | 5 | 0/4; fc 0 (counts only) | 0/1; fc 0 (counts only) | 1/2; fc 4 (counts only) | 0/3; fc 0 (counts only) | 4/35 = 0.114; 0.83/yr; on 0.023 |
| incumbent (object scored, not a feature) | 5 | 0/4; fc 0 (counts only) | 1/1; fc 5 (counts only) | 0/2; fc 0 (counts only) | 3/3; fc 21 (counts only) | 11/35 = 0.314; 0.98/yr; on 0.155 |

## What the tables show (description; no cell is tested, nothing is declared)

1. **The rate leg (`rates_realrate`) catches in every flag state.** On PRE with `flag_rate` present it catches
   20/21 at 7.59 false calls/asset-yr, against 81/106 at 4.50 when absent. On D with `flag_rate` present it
   catches 8/8 at 3.97, against 29/37 at 4.99 when absent. The false-call difference has opposite signs in the
   two eras, so no flag-conditioned cut to the rate leg's false calls is described here.
2. **The incumbent's catch follows how often it is on.** With credit pressure present on D (a conditioning flag
   there), the Radar loud state catches 7/8 (.875) at 2.34/yr, on 65.6% of those sessions. With it absent it
   catches 8/37 (.216) at 0.70/yr, on 12.6%. PRE shows the same direction (14/24 against 10/103), but
   credit_pressure fails the coverage line in PRE, so that is description only. A D-first observation is
   forward-only.
3. **Easing cannot be read.** Present cells hold 2 PRE clusters and 0 D clusters, so they are counts only.
4. **Few clusters straddle states.** Clusters whose turns carry more than one state number 12/127 PRE and
   4/45 D for `flag_rate`, and 1–9 for the other flags. Assignment by earliest turn moves few clusters.
5. **Totals reproduce the accepted single-leg reads.** `rates_realrate` gives PRE .795/4.97 and D .822/4.71;
   the incumbent gives D .333/1.00.
