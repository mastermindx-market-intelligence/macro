# Rate & inflation transmission — calibration report

As-of **2026-09-25**. Forward horizon **63 days**; split-half boundary **2015-01-01**. Transmission = signed Spearman IC(driver_t, asset forward 63d return); display-only coefficients. Scored gate = driver as STRESS vs forward 63d S&P drawdown (calibrate_bonds discipline) + purged-CV sign robustness + bootstrap-CI tercile edge + Clark-West return-forecast bar. No look-ahead.

Verdicts (cells & legs): **CONFIRMED** = sign-stable in full + both purged halves with |IC|≥0.10 (scored legs also need the high-stress tercile drawdown edge with a bootstrap-CI lower bound above the base rate, and purged-CV sign robustness); **DIRECTIONAL** = full + both halves but weaker; **CONTEXT** = weak/unstable; **INVERTED** = predicts the wrong way.

## Scored-leg gate — does any rate/inflation leg earn a SCORED tier?

Each driver, expressed as STRESS (higher = more risk-off), vs the forward 63-day S&P drawdown — the same discriminative bar the bond-health legs pass. The return-forecast columns (Clark-West t, OOS-R²) test whether it predicts the LEVEL of returns; a leg can flag RISK without forecasting return.

| leg | verdict | IC dd (full/pre/post) | CV robust | hi-tercile edge | boot CI | CW t | OOS-R² | scored? |
|---|---|---|:--:|--:|---|--:|--:|:--:|
| real10y_chg63 (Real-rate SPEED (63d rise) — 'speed breaks equities') | **DIRECTIONAL** | 0.134/0.052/0.213 | True | 6.8pp | [0.1, 0.193, 0.301] | -0.929 | -0.10224 | — |
| real10y (Real-rate LEVEL (high real yields)) | **CONTEXT** | 0.037/0.053/-0.018 | False | -1.2pp | [0.035, 0.111, 0.212] | -0.795 | -0.16771 | — |
| corepce_gap (Core-PCE-vs-target gap (sticky inflation)) | **DIRECTIONAL** | 0.072/0.058/0.115 | False | 0.6pp | [0.077, 0.121, 0.172] | 1.722 | -0.30812 | — |
| infl_accel (Inflation re-acceleration (3m>12m)) | **DIRECTIONAL** | 0.065/0.066/0.061 | False | 4.3pp | [0.107, 0.158, 0.215] | -1.054 | -0.12598 | — |
| exp_wedge (Expectations unanchoring (market>model)) | **CONTEXT** | -0.038/-0.05/-0.075 | False | -5.9pp | [0.016, 0.066, 0.136] | 2.333 | -0.096 | — |
| curve_tp_adj (TP-adjusted curve inversion (flip: low=stress)) | **CONTEXT** | 0.005/0.01/0.047 | False | -0.6pp | [0.063, 0.11, 0.165] | -0.982 | -0.25734 | — |
| nom10y_chg63 (Nominal-rate SPEED (63d rise)) | **DIRECTIONAL** | 0.115/0.097/0.197 | False | -0.2pp | [0.075, 0.117, 0.165] | 0.728 | -0.11332 | — |
| ntfs (Near-term forward spread inversion (flip: low=stress; Engstrom-Sharpe beats 2s10s)) | **CONTEXT** | -0.043/0.026/-0.196 | False | -1.5pp | [0.053, 0.103, 0.162] | -0.804 | -0.28004 | — |
| curvature (Curve curvature (2s5s10s butterfly — humped = late-cycle)) | **CONTEXT** | 0.037/-0.013/0.184 | False | -0.1pp | [0.06, 0.115, 0.178] | -1.335 | -0.30711 | — |
| real_speed_abs (Real-rate move VIOLENCE (|63d speed|, either direction)) | **DIRECTIONAL** | 0.118/0.161/0.071 | False | 3.0pp | [0.083, 0.156, 0.249] | -1.055 | -0.11006 | — |
| slope_chg63 (Curve flattening impulse (flip: − = flattening = stress; INVERTED if post-inversion steepening is the tell)) | **CONTEXT** | -0.035/-0.085/0.153 | False | -2.1pp | [0.052, 0.095, 0.145] | 0.727 | -0.12283 | — |
| trend_spread (3m10y TREND inversion (flip: low trend = stress) — Faria-Verona OOS equity-premium claim, tested on the return-forecast bar) | **CONTEXT** | 0.15/0.241/-0.047 | False | 6.4pp | [0.11, 0.179, 0.258] | 3.659 | -0.2701 | — |

**Scored-eligible legs: NONE — every rate/inflation leg here is display-only context.** Eligible legs are PROPOSED for a config-gated MRS/drawdown leg, adopted only if they hold on the next refresh (the bonds restraint).

## Transmission matrix — per-asset forward pass-through

Signed Spearman IC of each rate/inflation driver vs each asset's forward 63-day return. Positive = tailwind, negative = headwind. These are the DISPLAY-ONLY coefficients the transmission engine reads; **CONFIRMED** cells are sign-stable across both halves.

### real10y — Real 10y yield (level)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | 0.345 | 0.374 | 0.313 | tailwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | -0.269 | -0.31 | -0.174 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | 0.176 | 0.266 | 0.084 | tailwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.165 | 0.122 | 0.182 | tailwind | CONFIRMED |
| XLV (Health Care (defensive)) | -0.146 | -0.271 | -0.046 | headwind | CONFIRMED |
| HG=F (Copper) | 0.133 | 0.19 | -0.03 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.122 | -0.18 | -0.04 | headwind | DIRECTIONAL |
| XLU (Utilities (bond proxy)) | 0.119 | 0.13 | 0.077 | tailwind | CONFIRMED |
| XLP (Staples (defensive)) | -0.06 | -0.159 | -0.005 | headwind | DIRECTIONAL |
| BTC-USD (Bitcoin (long-duration)) | -0.055 | None | -0.07 | headwind | CONTEXT |
| SPY (S&P 500) | -0.053 | -0.139 | 0.057 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.044 | 0.119 | -0.273 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.024 | 0.058 | -0.084 | neutral | CONTEXT |
| XLK (Technology) | -0.022 | -0.039 | 0.069 | neutral | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.021 | None | 0.021 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.015 | -0.069 | 0.067 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.015 | 0.075 | -0.125 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.009 | -0.1 | 0.047 | neutral | CONTEXT |

### real10y_chg63 — Real 10y — 63d change (speed)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.308 | None | -0.297 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.215 | -0.198 | -0.22 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.197 | -0.197 | -0.201 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.191 | -0.167 | -0.218 | headwind | CONFIRMED |
| XLK (Technology) | -0.191 | -0.209 | -0.192 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | -0.183 | -0.17 | -0.18 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.171 | -0.131 | -0.211 | headwind | CONFIRMED |
| HG=F (Copper) | -0.164 | -0.162 | -0.138 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.15 | -0.109 | -0.203 | headwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.14 | 0.225 | 0.072 | tailwind | CONFIRMED |
| XLP (Staples (defensive)) | -0.129 | -0.116 | -0.127 | headwind | CONFIRMED |
| XLE (Energy (inflation beneficiary)) | -0.107 | -0.142 | -0.052 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.081 | 0.018 | -0.172 | headwind | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.031 | 0.004 | -0.05 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | -0.028 | -0.0 | -0.053 | neutral | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.021 | None | 0.021 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.006 | 0.005 | -0.003 | neutral | CONTEXT |
| GC=F (Gold) | -0.003 | 0.052 | -0.055 | neutral | CONTEXT |

### nom10y_chg63 — Nominal 10y — 63d change

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.243 | None | -0.274 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.14 | -0.086 | -0.226 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.121 | -0.092 | -0.185 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.103 | -0.052 | -0.199 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.101 | 0.047 | -0.223 | headwind | CONTEXT |
| XLK (Technology) | -0.096 | -0.053 | -0.191 | headwind | DIRECTIONAL |
| IWM (Russell 2000 (small caps)) | -0.083 | 0.004 | -0.2 | headwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.071 | 0.137 | 0.034 | tailwind | DIRECTIONAL |
| GC=F (Gold) | -0.064 | -0.04 | -0.102 | headwind | DIRECTIONAL |
| CL=F (Oil (WTI)) | -0.045 | 0.052 | -0.186 | headwind | CONTEXT |
| XLP (Staples (defensive)) | -0.043 | -0.004 | -0.098 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | 0.038 | None | 0.038 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.036 | -0.041 | 0.015 | neutral | CONTEXT |
| HG=F (Copper) | -0.031 | 0.014 | -0.114 | neutral | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.029 | 0.054 | -0.169 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.026 | 0.049 | -0.011 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.024 | 0.029 | -0.103 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.021 | 0.064 | -0.029 | neutral | CONTEXT |

### be10y — 10y breakeven (inflation comp.)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.318 | None | -0.346 | headwind | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.277 | -0.38 | -0.164 | headwind | CONFIRMED |
| XLK (Technology) | -0.277 | -0.37 | -0.138 | headwind | CONFIRMED |
| XLB (Materials (inflation beneficiary)) | -0.225 | -0.281 | -0.26 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.216 | -0.281 | -0.141 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.214 | -0.243 | -0.231 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.186 | -0.174 | -0.181 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.164 | -0.1 | -0.269 | headwind | CONFIRMED |
| HG=F (Copper) | -0.118 | -0.176 | -0.108 | headwind | CONFIRMED |
| XLP (Staples (defensive)) | -0.108 | -0.193 | -0.099 | headwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | 0.103 | 0.143 | 0.167 | tailwind | CONFIRMED |
| XLV (Health Care (defensive)) | -0.096 | -0.177 | -0.047 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | -0.09 | None | -0.09 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.073 | -0.027 | -0.178 | headwind | DIRECTIONAL |
| GC=F (Gold) | -0.061 | -0.165 | 0.042 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.06 | -0.045 | 0.083 | tailwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.048 | 0.152 | -0.123 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.035 | 0.048 | -0.017 | neutral | CONTEXT |

### be10y_chg63 — 10y breakeven — 63d change

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | -0.125 | -0.156 | -0.095 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.122 | -0.075 | -0.146 | headwind | CONFIRMED |
| HG=F (Copper) | 0.097 | 0.189 | -0.054 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | 0.086 | 0.228 | -0.069 | tailwind | CONTEXT |
| XLP (Staples (defensive)) | 0.07 | 0.151 | -0.013 | tailwind | CONTEXT |
| XLV (Health Care (defensive)) | 0.069 | 0.121 | 0.036 | tailwind | DIRECTIONAL |
| XLU (Utilities (bond proxy)) | 0.058 | 0.082 | 0.03 | tailwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.048 | -0.028 | -0.069 | headwind | DIRECTIONAL |
| XLB (Materials (inflation beneficiary)) | -0.043 | 0.036 | -0.139 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | 0.037 | 0.113 | -0.09 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.037 | -0.062 | 0.038 | neutral | CONTEXT |
| XLK (Technology) | -0.036 | -0.012 | -0.072 | neutral | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.031 | None | 0.031 | neutral | CONTEXT |
| SPY (S&P 500) | 0.029 | 0.107 | -0.052 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.021 | 0.075 | -0.166 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.017 | None | -0.066 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.004 | 0.092 | -0.093 | neutral | CONTEXT |
| TLT (Long Treasuries (20y+)) | -0.001 | -0.014 | 0.029 | neutral | CONTEXT |

### be5y5y — 5y5y forward breakeven (anchor)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.309 | None | -0.29 | headwind | CONTEXT |
| XLK (Technology) | -0.263 | -0.272 | -0.143 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.215 | -0.272 | -0.141 | headwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.206 | 0.261 | -0.047 | tailwind | CONTEXT |
| HG=F (Copper) | -0.199 | -0.409 | -0.182 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.169 | -0.167 | -0.131 | headwind | CONFIRMED |
| XLB (Materials (inflation beneficiary)) | -0.161 | -0.302 | -0.275 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.153 | -0.085 | -0.162 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.137 | -0.195 | -0.199 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | -0.125 | -0.165 | -0.257 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.105 | -0.306 | -0.174 | headwind | CONFIRMED |
| GC=F (Gold) | -0.07 | -0.243 | 0.07 | headwind | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.07 | 0.205 | 0.131 | tailwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | -0.069 | None | -0.069 | headwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.057 | 0.045 | -0.027 | tailwind | CONTEXT |
| XLP (Staples (defensive)) | -0.023 | -0.073 | -0.121 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.01 | -0.13 | -0.029 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.002 | 0.017 | -0.059 | neutral | CONTEXT |

### curve_tp_adj — TP-adjusted 2s10s curve

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| TLT (Long Treasuries (20y+)) | 0.239 | 0.246 | 0.154 | tailwind | CONFIRMED |
| XLRE (Real Estate (rate-sensitive)) | 0.159 | None | 0.159 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.146 | -0.08 | -0.15 | headwind | CONFIRMED |
| XLK (Technology) | -0.116 | 0.009 | -0.111 | headwind | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.106 | None | -0.053 | headwind | CONTEXT |
| SPY (S&P 500) | -0.098 | -0.067 | -0.134 | headwind | DIRECTIONAL |
| FXI (China large-cap (EM proxy)) | -0.082 | -0.266 | -0.071 | headwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.062 | 0.036 | -0.129 | headwind | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.055 | -0.065 | 0.025 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.042 | -0.046 | -0.088 | headwind | DIRECTIONAL |
| XLV (Health Care (defensive)) | 0.042 | 0.049 | 0.055 | tailwind | DIRECTIONAL |
| XLE (Energy (inflation beneficiary)) | -0.036 | -0.086 | -0.009 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | 0.03 | 0.048 | 0.011 | neutral | CONTEXT |
| XLP (Staples (defensive)) | -0.022 | -0.023 | 0.011 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.018 | 0.033 | -0.079 | neutral | CONTEXT |
| GC=F (Gold) | -0.018 | 0.112 | -0.124 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.014 | -0.041 | 0.099 | neutral | CONTEXT |
| HG=F (Copper) | 0.001 | 0.07 | -0.061 | neutral | CONTEXT |

### policy_gap — us2y − funds (cut/hike pricing)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.192 | None | -0.171 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.176 | -0.171 | -0.182 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.167 | -0.059 | -0.349 | headwind | CONFIRMED |
| XLK (Technology) | -0.166 | -0.028 | -0.308 | headwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.156 | -0.016 | -0.327 | headwind | DIRECTIONAL |
| XLF (Financials (rate beneficiary)) | -0.138 | -0.031 | -0.282 | headwind | DIRECTIONAL |
| IWM (Russell 2000 (small caps)) | -0.098 | -0.0 | -0.239 | headwind | DIRECTIONAL |
| FXI (China large-cap (EM proxy)) | -0.096 | -0.085 | -0.153 | headwind | DIRECTIONAL |
| XLP (Staples (defensive)) | -0.073 | -0.087 | -0.057 | headwind | DIRECTIONAL |
| TLT (Long Treasuries (20y+)) | 0.069 | 0.189 | -0.05 | tailwind | CONTEXT |
| GC=F (Gold) | -0.068 | 0.125 | -0.293 | headwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | -0.067 | None | -0.067 | headwind | CONTEXT |
| HG=F (Copper) | 0.058 | 0.224 | -0.153 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.034 | -0.014 | -0.062 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | 0.028 | 0.111 | -0.038 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.02 | -0.05 | 0.097 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | -0.018 | -0.005 | -0.05 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.013 | -0.004 | -0.033 | neutral | CONTEXT |

### corepce_gap — Core PCE YoY − 2% target

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.256 | None | -0.308 | headwind | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.178 | -0.229 | -0.176 | headwind | CONFIRMED |
| XLV (Health Care (defensive)) | -0.167 | -0.272 | -0.071 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.163 | -0.307 | -0.089 | headwind | CONFIRMED |
| XLRE (Real Estate (rate-sensitive)) | -0.154 | None | -0.154 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.145 | -0.13 | -0.175 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.137 | 0.024 | -0.229 | headwind | CONTEXT |
| XLK (Technology) | -0.128 | -0.287 | -0.067 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.102 | -0.172 | -0.082 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.101 | -0.184 | -0.113 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | -0.096 | -0.097 | -0.091 | headwind | DIRECTIONAL |
| XLP (Staples (defensive)) | -0.088 | -0.091 | -0.11 | headwind | DIRECTIONAL |
| HG=F (Copper) | -0.083 | -0.14 | -0.058 | headwind | DIRECTIONAL |
| TLT (Long Treasuries (20y+)) | -0.069 | 0.125 | -0.208 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.046 | -0.065 | 0.182 | tailwind | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.041 | 0.034 | 0.242 | tailwind | DIRECTIONAL |
| GC=F (Gold) | 0.021 | -0.044 | 0.019 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.017 | 0.049 | -0.068 | neutral | CONTEXT |

### infl_accel — Inflation re-acceleration (3m−12m)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| FXI (China large-cap (EM proxy)) | -0.198 | -0.191 | -0.191 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | 0.114 | 0.056 | 0.137 | tailwind | CONFIRMED |
| XLU (Utilities (bond proxy)) | 0.098 | 0.081 | 0.121 | tailwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.089 | -0.136 | -0.033 | headwind | DIRECTIONAL |
| GC=F (Gold) | -0.081 | -0.009 | -0.164 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | 0.078 | None | 0.078 | tailwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.078 | -0.027 | 0.158 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.071 | -0.095 | -0.039 | headwind | DIRECTIONAL |
| IWM (Russell 2000 (small caps)) | -0.069 | -0.136 | 0.005 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.066 | -0.09 | -0.045 | headwind | DIRECTIONAL |
| XLK (Technology) | -0.064 | -0.101 | -0.03 | headwind | DIRECTIONAL |
| DX-Y.NYB (US Dollar (DXY)) | -0.033 | -0.069 | 0.153 | neutral | CONTEXT |
| HG=F (Copper) | 0.025 | 0.044 | -0.021 | neutral | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.023 | 0.079 | -0.009 | neutral | CONTEXT |
| SPY (S&P 500) | -0.017 | -0.019 | -0.02 | neutral | CONTEXT |
| XLP (Staples (defensive)) | 0.016 | 0.064 | -0.041 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.014 | 0.09 | -0.068 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.013 | None | -0.039 | neutral | CONTEXT |

### exp_wedge — Expectations wedge (mkt − model)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | -0.261 | -0.302 | -0.266 | headwind | CONFIRMED |
| XLV (Health Care (defensive)) | 0.183 | 0.282 | 0.049 | tailwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.164 | -0.297 | -0.138 | headwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | 0.14 | 0.17 | 0.132 | tailwind | CONFIRMED |
| HG=F (Copper) | -0.139 | -0.249 | -0.046 | headwind | CONFIRMED |
| XLP (Staples (defensive)) | 0.129 | 0.165 | 0.026 | tailwind | DIRECTIONAL |
| BTC-USD (Bitcoin (long-duration)) | 0.121 | None | 0.174 | tailwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.089 | None | 0.089 | tailwind | CONTEXT |
| CL=F (Oil (WTI)) | 0.063 | -0.102 | 0.251 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | 0.062 | 0.166 | 0.006 | tailwind | DIRECTIONAL |
| XLK (Technology) | -0.047 | 0.014 | -0.065 | headwind | CONTEXT |
| SPY (S&P 500) | 0.043 | 0.138 | -0.042 | tailwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.031 | -0.005 | -0.072 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | 0.009 | 0.08 | -0.117 | neutral | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.006 | -0.059 | 0.026 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.003 | 0.038 | -0.043 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.002 | -0.041 | -0.018 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.0 | -0.046 | 0.008 | neutral | CONTEXT |

### curvature — 2s5s10s curvature (butterfly)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| SPY (S&P 500) | -0.232 | -0.131 | -0.384 | headwind | CONFIRMED |
| BTC-USD (Bitcoin (long-duration)) | -0.221 | None | -0.175 | headwind | CONTEXT |
| XLK (Technology) | -0.22 | -0.121 | -0.326 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.208 | -0.098 | -0.31 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.202 | -0.109 | -0.324 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.193 | -0.116 | -0.308 | headwind | CONFIRMED |
| XLB (Materials (inflation beneficiary)) | -0.175 | -0.156 | -0.23 | headwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.169 | 0.305 | -0.016 | tailwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.104 | -0.136 | -0.074 | headwind | CONFIRMED |
| XLRE (Real Estate (rate-sensitive)) | -0.098 | None | -0.098 | headwind | CONTEXT |
| XLV (Health Care (defensive)) | -0.082 | -0.072 | -0.086 | headwind | DIRECTIONAL |
| XLP (Staples (defensive)) | -0.076 | -0.085 | -0.047 | headwind | DIRECTIONAL |
| HG=F (Copper) | -0.054 | 0.068 | -0.212 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.04 | -0.045 | 0.003 | headwind | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.027 | -0.033 | -0.026 | neutral | CONTEXT |
| GC=F (Gold) | -0.024 | 0.129 | -0.25 | neutral | CONTEXT |
| FXI (China large-cap (EM proxy)) | -0.022 | 0.014 | -0.123 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.0 | -0.028 | 0.111 | neutral | CONTEXT |

### slope_chg63 — 2s10s 63d change (steepening)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| XLRE (Real Estate (rate-sensitive)) | 0.322 | None | 0.322 | tailwind | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | 0.163 | None | 0.142 | tailwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.115 | 0.028 | 0.221 | tailwind | DIRECTIONAL |
| XLE (Energy (inflation beneficiary)) | -0.102 | -0.121 | -0.107 | headwind | CONFIRMED |
| GC=F (Gold) | 0.094 | 0.014 | 0.202 | tailwind | DIRECTIONAL |
| HG=F (Copper) | -0.074 | -0.199 | 0.104 | headwind | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | 0.061 | -0.068 | 0.296 | tailwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.06 | 0.009 | 0.151 | tailwind | DIRECTIONAL |
| DX-Y.NYB (US Dollar (DXY)) | -0.054 | -0.029 | -0.122 | headwind | DIRECTIONAL |
| SPY (S&P 500) | 0.046 | -0.083 | 0.317 | tailwind | CONTEXT |
| IWM (Russell 2000 (small caps)) | 0.042 | -0.061 | 0.209 | tailwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.036 | -0.045 | -0.057 | neutral | CONTEXT |
| XLK (Technology) | 0.026 | -0.105 | 0.26 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.016 | -0.099 | 0.21 | neutral | CONTEXT |
| FXI (China large-cap (EM proxy)) | -0.015 | -0.036 | 0.028 | neutral | CONTEXT |
| XLP (Staples (defensive)) | 0.008 | -0.078 | 0.151 | neutral | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.007 | -0.139 | 0.216 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.006 | -0.009 | 0.043 | neutral | CONTEXT |

### ntfs — Near-term forward spread

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| XLB (Materials (inflation beneficiary)) | -0.213 | -0.237 | -0.189 | headwind | CONFIRMED |
| XLK (Technology) | -0.208 | -0.063 | -0.324 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.201 | -0.106 | -0.352 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.195 | -0.099 | -0.273 | headwind | CONFIRMED |
| BTC-USD (Bitcoin (long-duration)) | -0.18 | None | -0.144 | headwind | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.172 | -0.036 | -0.333 | headwind | DIRECTIONAL |
| IWM (Russell 2000 (small caps)) | -0.127 | -0.046 | -0.24 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.113 | -0.17 | -0.149 | headwind | CONFIRMED |
| XLP (Staples (defensive)) | -0.106 | -0.156 | -0.038 | headwind | DIRECTIONAL |
| TLT (Long Treasuries (20y+)) | 0.105 | 0.203 | -0.045 | tailwind | CONTEXT |
| GC=F (Gold) | -0.092 | 0.103 | -0.32 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.058 | -0.09 | -0.036 | headwind | DIRECTIONAL |
| XLV (Health Care (defensive)) | -0.053 | -0.064 | -0.033 | headwind | DIRECTIONAL |
| XLU (Utilities (bond proxy)) | -0.051 | -0.083 | -0.014 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | -0.05 | None | -0.05 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | 0.032 | 0.089 | -0.004 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.024 | -0.013 | 0.145 | neutral | CONTEXT |
| HG=F (Copper) | -0.013 | 0.141 | -0.18 | neutral | CONTEXT |

### real_speed_abs — |Real 10y 63d speed| (violence)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | 0.118 | 0.067 | 0.168 | tailwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | -0.099 | -0.156 | -0.01 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | 0.049 | None | 0.049 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.048 | -0.111 | 0.022 | headwind | CONTEXT |
| FXI (China large-cap (EM proxy)) | 0.032 | -0.008 | 0.077 | neutral | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.027 | -0.006 | 0.055 | neutral | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.026 | -0.0 | 0.05 | neutral | CONTEXT |
| SPY (S&P 500) | -0.023 | -0.05 | 0.008 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.018 | -0.028 | -0.005 | neutral | CONTEXT |
| XLK (Technology) | -0.015 | -0.022 | -0.001 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.015 | None | -0.028 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | -0.012 | -0.051 | 0.036 | neutral | CONTEXT |
| XLP (Staples (defensive)) | 0.009 | -0.037 | 0.051 | neutral | CONTEXT |
| HG=F (Copper) | 0.008 | 0.003 | -0.011 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.005 | -0.091 | 0.078 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | -0.003 | 0.073 | -0.088 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.001 | 0.001 | 0.004 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.001 | 0.021 | -0.038 | neutral | CONTEXT |

### trend_spread — 3m10y trend (2y smooth, Faria-Verona)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| TLT (Long Treasuries (20y+)) | 0.13 | 0.123 | 0.039 | tailwind | DIRECTIONAL |
| XLP (Staples (defensive)) | 0.114 | 0.239 | -0.069 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.104 | 0.253 | -0.115 | tailwind | CONTEXT |
| GC=F (Gold) | -0.101 | 0.043 | -0.324 | headwind | CONTEXT |
| XLV (Health Care (defensive)) | 0.079 | 0.174 | -0.069 | tailwind | CONTEXT |
| IWM (Russell 2000 (small caps)) | 0.073 | 0.237 | -0.17 | tailwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | -0.062 | None | -0.062 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.049 | 0.161 | -0.109 | tailwind | CONTEXT |
| HG=F (Copper) | 0.044 | 0.204 | -0.22 | tailwind | CONTEXT |
| XLK (Technology) | -0.039 | 0.149 | -0.174 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.031 | -0.051 | 0.081 | neutral | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.026 | 0.093 | -0.106 | neutral | CONTEXT |
| XLF (Financials (rate beneficiary)) | 0.024 | 0.21 | -0.189 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | 0.024 | 0.038 | 0.002 | neutral | CONTEXT |
| FXI (China large-cap (EM proxy)) | -0.022 | -0.152 | -0.094 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.013 | 0.144 | -0.18 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | 0.012 | None | 0.066 | neutral | CONTEXT |
| SPY (S&P 500) | -0.006 | 0.144 | -0.259 | neutral | CONTEXT |

## Collinearity vs already-scored legs

VIF (>5 redundant) and the top correlated pairs — a 'new' leg that merely restates the breakeven-direction / TIPS-nominal / sticky-CPI legs already in the inflation axis is caught here and NOT double-counted.

| driver | VIF |
|---|--:|
| be5y5y | 16.62 |
| exp_wedge | 15.82 |
| ntfs | 14.29 |
| policy_gap | 11.49 |
| real10y | 10.84 |
| curve_tp_adj | 7.84 |
| trend_spread | 3.75 |
| corepce_gap | 3.63 |
| be10y | 3.03 |
| _scored_tips_nominal | 3.03 |
| slope_chg63 | 2.9 |
| curvature | 2.85 |
| infl_accel | 1.97 |
| _scored_be10y_chg | 1.77 |
| be10y_chg63 | 1.56 |
| _scored_sticky_dir | 1.55 |
| real_speed_abs | 1.36 |
| real10y_chg63 | 1.11 |
| nom10y_chg63 | 0.87 |

Top correlated pairs:

- `be10y` ↔ `_scored_tips_nominal`: 1.0
- `policy_gap` ↔ `ntfs`: 0.88
- `be10y` ↔ `be5y5y`: 0.78
- `be5y5y` ↔ `_scored_tips_nominal`: 0.78
- `real10y_chg63` ↔ `nom10y_chg63`: 0.74
- `curvature` ↔ `ntfs`: 0.71
- `ntfs` ↔ `trend_spread`: 0.68
- `curve_tp_adj` ↔ `ntfs`: 0.67
- `curve_tp_adj` ↔ `trend_spread`: 0.64
- `real10y` ↔ `exp_wedge`: 0.62
- `policy_gap` ↔ `trend_spread`: 0.61
- `policy_gap` ↔ `curvature`: 0.6