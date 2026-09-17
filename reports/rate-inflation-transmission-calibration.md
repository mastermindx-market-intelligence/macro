# Rate & inflation transmission — calibration report

As-of **2026-09-11**. Forward horizon **63 days**; split-half boundary **2015-01-01**. Transmission = signed Spearman IC(driver_t, asset forward 63d return); display-only coefficients. Scored gate = driver as STRESS vs forward 63d S&P drawdown (calibrate_bonds discipline) + purged-CV sign robustness + bootstrap-CI tercile edge + Clark-West return-forecast bar. No look-ahead.

Verdicts (cells & legs): **CONFIRMED** = sign-stable in full + both purged halves with |IC|≥0.10 (scored legs also need the high-stress tercile drawdown edge with a bootstrap-CI lower bound above the base rate, and purged-CV sign robustness); **DIRECTIONAL** = full + both halves but weaker; **CONTEXT** = weak/unstable; **INVERTED** = predicts the wrong way.

## Scored-leg gate — does any rate/inflation leg earn a SCORED tier?

Each driver, expressed as STRESS (higher = more risk-off), vs the forward 63-day S&P drawdown — the same discriminative bar the bond-health legs pass. The return-forecast columns (Clark-West t, OOS-R²) test whether it predicts the LEVEL of returns; a leg can flag RISK without forecasting return.

| leg | verdict | IC dd (full/pre/post) | CV robust | hi-tercile edge | boot CI | CW t | OOS-R² | scored? |
|---|---|---|:--:|--:|---|--:|--:|:--:|
| real10y_chg63 (Real-rate SPEED (63d rise) — 'speed breaks equities') | **DIRECTIONAL** | 0.135/0.052/0.215 | True | 7.0pp | [0.101, 0.195, 0.304] | -0.95 | -0.10259 | — |
| real10y (Real-rate LEVEL (high real yields)) | **CONTEXT** | 0.038/0.053/-0.015 | False | -1.2pp | [0.034, 0.112, 0.212] | -0.812 | -0.16797 | — |
| corepce_gap (Core-PCE-vs-target gap (sticky inflation)) | **DIRECTIONAL** | 0.072/0.058/0.117 | False | 0.6pp | [0.077, 0.121, 0.172] | 1.716 | -0.30845 | — |
| infl_accel (Inflation re-acceleration (3m>12m)) | **DIRECTIONAL** | 0.064/0.066/0.06 | False | 4.3pp | [0.107, 0.158, 0.215] | -1.069 | -0.12622 | — |
| exp_wedge (Expectations unanchoring (market>model)) | **INVERTED** | -0.04/-0.05/-0.078 | False | -6.0pp | [0.016, 0.066, 0.136] | 2.311 | -0.09627 | — |
| curve_tp_adj (TP-adjusted curve inversion (flip: low=stress)) | **CONTEXT** | 0.005/0.01/0.046 | False | -0.6pp | [0.063, 0.11, 0.165] | -0.988 | -0.25758 | — |
| nom10y_chg63 (Nominal-rate SPEED (63d rise)) | **DIRECTIONAL** | 0.115/0.097/0.198 | False | -0.2pp | [0.076, 0.117, 0.165] | 0.716 | -0.11351 | — |
| ntfs (Near-term forward spread inversion (flip: low=stress; Engstrom-Sharpe beats 2s10s)) | **CONTEXT** | -0.042/0.026/-0.197 | False | -1.6pp | [0.054, 0.103, 0.162] | -0.795 | -0.27982 | — |
| curvature (Curve curvature (2s5s10s butterfly — humped = late-cycle)) | **CONTEXT** | 0.037/-0.013/0.183 | False | -0.1pp | [0.06, 0.115, 0.178] | -1.337 | -0.30733 | — |
| real_speed_abs (Real-rate move VIOLENCE (|63d speed|, either direction)) | **DIRECTIONAL** | 0.118/0.161/0.071 | False | 3.0pp | [0.083, 0.156, 0.248] | -1.072 | -0.11035 | — |
| slope_chg63 (Curve flattening impulse (flip: − = flattening = stress; INVERTED if post-inversion steepening is the tell)) | **CONTEXT** | -0.034/-0.085/0.155 | False | -2.1pp | [0.052, 0.095, 0.145] | 0.729 | -0.12285 | — |
| trend_spread (3m10y TREND inversion (flip: low trend = stress) — Faria-Verona OOS equity-premium claim, tested on the return-forecast bar) | **CONTEXT** | 0.151/0.241/-0.045 | False | 6.5pp | [0.109, 0.179, 0.258] | 3.648 | -0.27038 | — |

**Scored-eligible legs: NONE — every rate/inflation leg here is display-only context.** Eligible legs are PROPOSED for a config-gated MRS/drawdown leg, adopted only if they hold on the next refresh (the bonds restraint).

## Transmission matrix — per-asset forward pass-through

Signed Spearman IC of each rate/inflation driver vs each asset's forward 63-day return. Positive = tailwind, negative = headwind. These are the DISPLAY-ONLY coefficients the transmission engine reads; **CONFIRMED** cells are sign-stable across both halves.

### real10y — Real 10y yield (level)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | 0.344 | 0.374 | 0.309 | tailwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | -0.268 | -0.31 | -0.172 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | 0.175 | 0.266 | 0.081 | tailwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.168 | 0.122 | 0.189 | tailwind | CONFIRMED |
| XLV (Health Care (defensive)) | -0.15 | -0.271 | -0.054 | headwind | CONFIRMED |
| HG=F (Copper) | 0.132 | 0.19 | -0.033 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.123 | 0.13 | 0.087 | tailwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.123 | -0.18 | -0.04 | headwind | CONFIRMED |
| BTC-USD (Bitcoin (long-duration)) | -0.059 | None | -0.074 | headwind | CONTEXT |
| XLP (Staples (defensive)) | -0.058 | -0.159 | -0.001 | headwind | DIRECTIONAL |
| SPY (S&P 500) | -0.053 | -0.139 | 0.057 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.047 | 0.119 | -0.284 | headwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.027 | None | 0.027 | neutral | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.026 | 0.058 | -0.08 | neutral | CONTEXT |
| XLK (Technology) | -0.021 | -0.039 | 0.073 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.013 | -0.069 | 0.071 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.012 | 0.075 | -0.133 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.006 | -0.1 | 0.053 | neutral | CONTEXT |

### real10y_chg63 — Real 10y — 63d change (speed)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.31 | None | -0.299 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.214 | -0.198 | -0.218 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.196 | -0.197 | -0.2 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.191 | -0.167 | -0.219 | headwind | CONFIRMED |
| XLK (Technology) | -0.19 | -0.209 | -0.191 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | -0.186 | -0.17 | -0.185 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.169 | -0.131 | -0.208 | headwind | CONFIRMED |
| HG=F (Copper) | -0.165 | -0.162 | -0.14 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.15 | -0.109 | -0.204 | headwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.142 | 0.225 | 0.075 | tailwind | CONFIRMED |
| XLP (Staples (defensive)) | -0.128 | -0.116 | -0.125 | headwind | CONFIRMED |
| XLE (Energy (inflation beneficiary)) | -0.11 | -0.142 | -0.055 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.082 | 0.018 | -0.174 | headwind | CONTEXT |
| XLV (Health Care (defensive)) | -0.03 | -0.0 | -0.057 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.028 | 0.004 | -0.047 | neutral | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.024 | None | 0.024 | neutral | CONTEXT |
| GC=F (Gold) | -0.006 | 0.052 | -0.063 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.006 | 0.005 | -0.001 | neutral | CONTEXT |

### nom10y_chg63 — Nominal 10y — 63d change

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.244 | None | -0.274 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.14 | -0.086 | -0.226 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.121 | -0.092 | -0.186 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.103 | -0.052 | -0.199 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.101 | 0.047 | -0.224 | headwind | CONTEXT |
| XLK (Technology) | -0.096 | -0.053 | -0.191 | headwind | DIRECTIONAL |
| IWM (Russell 2000 (small caps)) | -0.082 | 0.004 | -0.2 | headwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.071 | 0.137 | 0.036 | tailwind | DIRECTIONAL |
| GC=F (Gold) | -0.065 | -0.04 | -0.105 | headwind | DIRECTIONAL |
| CL=F (Oil (WTI)) | -0.046 | 0.052 | -0.187 | headwind | CONTEXT |
| XLP (Staples (defensive)) | -0.043 | -0.004 | -0.098 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | 0.039 | None | 0.039 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.036 | -0.041 | 0.016 | neutral | CONTEXT |
| HG=F (Copper) | -0.031 | 0.014 | -0.114 | neutral | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.029 | 0.054 | -0.169 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.027 | 0.049 | -0.01 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.025 | 0.029 | -0.105 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.021 | 0.064 | -0.03 | neutral | CONTEXT |

### be10y — 10y breakeven (inflation comp.)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.319 | None | -0.347 | headwind | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.277 | -0.38 | -0.163 | headwind | CONFIRMED |
| XLK (Technology) | -0.277 | -0.37 | -0.138 | headwind | CONFIRMED |
| XLB (Materials (inflation beneficiary)) | -0.225 | -0.281 | -0.26 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.217 | -0.281 | -0.143 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.215 | -0.243 | -0.23 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.186 | -0.174 | -0.182 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.164 | -0.1 | -0.27 | headwind | CONFIRMED |
| HG=F (Copper) | -0.119 | -0.176 | -0.109 | headwind | CONFIRMED |
| XLP (Staples (defensive)) | -0.108 | -0.193 | -0.099 | headwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | 0.104 | 0.143 | 0.168 | tailwind | CONFIRMED |
| XLV (Health Care (defensive)) | -0.096 | -0.177 | -0.049 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | -0.089 | None | -0.089 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.074 | -0.027 | -0.18 | headwind | DIRECTIONAL |
| GC=F (Gold) | -0.062 | -0.165 | 0.038 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.06 | -0.045 | 0.081 | tailwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.048 | 0.152 | -0.122 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.036 | 0.048 | -0.016 | neutral | CONTEXT |

### be10y_chg63 — 10y breakeven — 63d change

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | -0.122 | -0.156 | -0.09 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.121 | -0.075 | -0.144 | headwind | CONFIRMED |
| HG=F (Copper) | 0.098 | 0.189 | -0.053 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | 0.087 | 0.228 | -0.068 | tailwind | CONTEXT |
| XLV (Health Care (defensive)) | 0.071 | 0.121 | 0.039 | tailwind | DIRECTIONAL |
| XLP (Staples (defensive)) | 0.069 | 0.151 | -0.015 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.056 | 0.082 | 0.027 | tailwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.048 | -0.028 | -0.071 | headwind | DIRECTIONAL |
| XLB (Materials (inflation beneficiary)) | -0.044 | 0.036 | -0.141 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | 0.039 | 0.113 | -0.086 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.038 | -0.062 | 0.037 | neutral | CONTEXT |
| XLK (Technology) | -0.037 | -0.012 | -0.073 | neutral | CONTEXT |
| SPY (S&P 500) | 0.029 | 0.107 | -0.053 | neutral | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.029 | None | 0.029 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.019 | 0.075 | -0.163 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.015 | None | -0.064 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.005 | 0.092 | -0.095 | neutral | CONTEXT |
| TLT (Long Treasuries (20y+)) | -0.003 | -0.014 | 0.026 | neutral | CONTEXT |

### be5y5y — 5y5y forward breakeven (anchor)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.31 | None | -0.291 | headwind | CONTEXT |
| XLK (Technology) | -0.263 | -0.272 | -0.142 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.215 | -0.272 | -0.14 | headwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.206 | 0.261 | -0.046 | tailwind | CONTEXT |
| HG=F (Copper) | -0.199 | -0.409 | -0.183 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.169 | -0.167 | -0.132 | headwind | CONFIRMED |
| XLB (Materials (inflation beneficiary)) | -0.162 | -0.302 | -0.275 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.153 | -0.085 | -0.162 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.138 | -0.195 | -0.198 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | -0.124 | -0.165 | -0.26 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.105 | -0.306 | -0.175 | headwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | 0.07 | 0.205 | 0.132 | tailwind | DIRECTIONAL |
| GC=F (Gold) | -0.069 | -0.243 | 0.068 | headwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | -0.068 | None | -0.068 | headwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.056 | 0.045 | -0.026 | tailwind | CONTEXT |
| XLP (Staples (defensive)) | -0.023 | -0.073 | -0.12 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.009 | -0.13 | -0.031 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.003 | 0.017 | -0.062 | neutral | CONTEXT |

### curve_tp_adj — TP-adjusted 2s10s curve

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| TLT (Long Treasuries (20y+)) | 0.238 | 0.246 | 0.156 | tailwind | CONFIRMED |
| XLRE (Real Estate (rate-sensitive)) | 0.162 | None | 0.162 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.146 | -0.08 | -0.15 | headwind | CONFIRMED |
| XLK (Technology) | -0.117 | 0.009 | -0.11 | headwind | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.107 | None | -0.055 | headwind | CONTEXT |
| SPY (S&P 500) | -0.098 | -0.067 | -0.135 | headwind | DIRECTIONAL |
| FXI (China large-cap (EM proxy)) | -0.082 | -0.266 | -0.072 | headwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.063 | 0.036 | -0.128 | headwind | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.056 | -0.065 | 0.026 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.043 | -0.046 | -0.087 | headwind | DIRECTIONAL |
| XLV (Health Care (defensive)) | 0.042 | 0.049 | 0.052 | tailwind | DIRECTIONAL |
| XLE (Energy (inflation beneficiary)) | -0.036 | -0.086 | -0.011 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | 0.031 | 0.048 | 0.007 | neutral | CONTEXT |
| XLP (Staples (defensive)) | -0.023 | -0.023 | 0.012 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.018 | 0.033 | -0.077 | neutral | CONTEXT |
| GC=F (Gold) | -0.018 | 0.112 | -0.128 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.015 | -0.041 | 0.103 | neutral | CONTEXT |
| HG=F (Copper) | 0.001 | 0.07 | -0.062 | neutral | CONTEXT |

### policy_gap — us2y − funds (cut/hike pricing)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.193 | None | -0.172 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.176 | -0.171 | -0.18 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.166 | -0.059 | -0.349 | headwind | CONFIRMED |
| XLK (Technology) | -0.166 | -0.028 | -0.307 | headwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.155 | -0.016 | -0.325 | headwind | DIRECTIONAL |
| XLF (Financials (rate beneficiary)) | -0.139 | -0.031 | -0.282 | headwind | DIRECTIONAL |
| FXI (China large-cap (EM proxy)) | -0.097 | -0.085 | -0.155 | headwind | DIRECTIONAL |
| IWM (Russell 2000 (small caps)) | -0.096 | -0.0 | -0.236 | headwind | DIRECTIONAL |
| XLP (Staples (defensive)) | -0.072 | -0.087 | -0.055 | headwind | DIRECTIONAL |
| TLT (Long Treasuries (20y+)) | 0.071 | 0.189 | -0.047 | tailwind | CONTEXT |
| GC=F (Gold) | -0.07 | 0.125 | -0.298 | headwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | -0.063 | None | -0.063 | headwind | CONTEXT |
| HG=F (Copper) | 0.058 | 0.224 | -0.154 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.033 | -0.014 | -0.058 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | 0.027 | 0.111 | -0.042 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.02 | -0.05 | 0.099 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | -0.019 | -0.005 | -0.053 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.014 | -0.004 | -0.037 | neutral | CONTEXT |

### corepce_gap — Core PCE YoY − 2% target

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| BTC-USD (Bitcoin (long-duration)) | -0.259 | None | -0.312 | headwind | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.176 | -0.229 | -0.173 | headwind | CONFIRMED |
| XLV (Health Care (defensive)) | -0.17 | -0.272 | -0.076 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.162 | -0.307 | -0.087 | headwind | CONFIRMED |
| XLRE (Real Estate (rate-sensitive)) | -0.15 | None | -0.15 | headwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | -0.144 | -0.13 | -0.173 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.138 | 0.024 | -0.23 | headwind | CONTEXT |
| XLK (Technology) | -0.128 | -0.287 | -0.065 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.103 | -0.172 | -0.082 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.101 | -0.184 | -0.113 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | -0.099 | -0.097 | -0.096 | headwind | DIRECTIONAL |
| XLP (Staples (defensive)) | -0.087 | -0.091 | -0.108 | headwind | DIRECTIONAL |
| HG=F (Copper) | -0.084 | -0.14 | -0.059 | headwind | DIRECTIONAL |
| TLT (Long Treasuries (20y+)) | -0.067 | 0.125 | -0.205 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.043 | -0.065 | 0.179 | tailwind | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.041 | 0.034 | 0.244 | tailwind | DIRECTIONAL |
| XLU (Utilities (bond proxy)) | 0.02 | 0.049 | -0.063 | neutral | CONTEXT |
| GC=F (Gold) | 0.019 | -0.044 | 0.016 | neutral | CONTEXT |

### infl_accel — Inflation re-acceleration (3m−12m)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| FXI (China large-cap (EM proxy)) | -0.198 | -0.191 | -0.19 | headwind | CONFIRMED |
| CL=F (Oil (WTI)) | 0.115 | 0.056 | 0.141 | tailwind | CONFIRMED |
| XLU (Utilities (bond proxy)) | 0.097 | 0.081 | 0.118 | tailwind | DIRECTIONAL |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.089 | -0.136 | -0.035 | headwind | DIRECTIONAL |
| XLE (Energy (inflation beneficiary)) | 0.079 | -0.027 | 0.16 | tailwind | CONTEXT |
| GC=F (Gold) | -0.079 | -0.009 | -0.16 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | 0.077 | None | 0.077 | tailwind | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.07 | -0.136 | 0.003 | headwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.07 | -0.095 | -0.039 | headwind | DIRECTIONAL |
| XLB (Materials (inflation beneficiary)) | -0.067 | -0.09 | -0.047 | headwind | DIRECTIONAL |
| XLK (Technology) | -0.064 | -0.101 | -0.031 | headwind | DIRECTIONAL |
| DX-Y.NYB (US Dollar (DXY)) | -0.033 | -0.069 | 0.151 | neutral | CONTEXT |
| HG=F (Copper) | 0.025 | 0.044 | -0.02 | neutral | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.022 | 0.079 | -0.011 | neutral | CONTEXT |
| SPY (S&P 500) | -0.018 | -0.019 | -0.021 | neutral | CONTEXT |
| XLP (Staples (defensive)) | 0.015 | 0.064 | -0.042 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.015 | 0.09 | -0.066 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.012 | None | -0.038 | neutral | CONTEXT |

### exp_wedge — Expectations wedge (mkt − model)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | -0.257 | -0.302 | -0.257 | headwind | CONFIRMED |
| XLV (Health Care (defensive)) | 0.188 | 0.282 | 0.057 | tailwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.163 | -0.297 | -0.135 | headwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | 0.139 | 0.17 | 0.13 | tailwind | CONFIRMED |
| HG=F (Copper) | -0.138 | -0.249 | -0.043 | headwind | CONFIRMED |
| XLP (Staples (defensive)) | 0.128 | 0.165 | 0.023 | tailwind | DIRECTIONAL |
| BTC-USD (Bitcoin (long-duration)) | 0.125 | None | 0.178 | tailwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | 0.084 | None | 0.084 | tailwind | CONTEXT |
| CL=F (Oil (WTI)) | 0.068 | -0.102 | 0.262 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | 0.063 | 0.166 | 0.006 | tailwind | DIRECTIONAL |
| XLK (Technology) | -0.048 | 0.014 | -0.068 | headwind | CONTEXT |
| SPY (S&P 500) | 0.043 | 0.138 | -0.042 | tailwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.028 | -0.005 | -0.078 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.007 | -0.041 | -0.028 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | 0.006 | 0.08 | -0.123 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.005 | 0.038 | -0.047 | neutral | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.004 | -0.059 | 0.021 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.003 | -0.046 | 0.016 | neutral | CONTEXT |

### curvature — 2s5s10s curvature (butterfly)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| SPY (S&P 500) | -0.232 | -0.131 | -0.384 | headwind | CONFIRMED |
| XLK (Technology) | -0.221 | -0.121 | -0.327 | headwind | CONFIRMED |
| BTC-USD (Bitcoin (long-duration)) | -0.221 | None | -0.175 | headwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.207 | -0.098 | -0.31 | headwind | CONFIRMED |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.203 | -0.109 | -0.325 | headwind | CONFIRMED |
| IWM (Russell 2000 (small caps)) | -0.194 | -0.116 | -0.31 | headwind | CONFIRMED |
| XLB (Materials (inflation beneficiary)) | -0.176 | -0.156 | -0.231 | headwind | CONFIRMED |
| TLT (Long Treasuries (20y+)) | 0.168 | 0.305 | -0.017 | tailwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.103 | -0.136 | -0.073 | headwind | CONFIRMED |
| XLRE (Real Estate (rate-sensitive)) | -0.098 | None | -0.098 | headwind | CONTEXT |
| XLV (Health Care (defensive)) | -0.081 | -0.072 | -0.085 | headwind | DIRECTIONAL |
| XLP (Staples (defensive)) | -0.076 | -0.085 | -0.048 | headwind | DIRECTIONAL |
| HG=F (Copper) | -0.054 | 0.068 | -0.212 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.039 | -0.045 | 0.005 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.028 | -0.033 | -0.027 | neutral | CONTEXT |
| GC=F (Gold) | -0.024 | 0.129 | -0.251 | neutral | CONTEXT |
| FXI (China large-cap (EM proxy)) | -0.022 | 0.014 | -0.123 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.0 | -0.028 | 0.111 | neutral | CONTEXT |

### slope_chg63 — 2s10s 63d change (steepening)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| XLRE (Real Estate (rate-sensitive)) | 0.319 | None | 0.319 | tailwind | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | 0.166 | None | 0.144 | tailwind | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.114 | 0.028 | 0.217 | tailwind | DIRECTIONAL |
| XLE (Energy (inflation beneficiary)) | -0.1 | -0.121 | -0.102 | headwind | DIRECTIONAL |
| GC=F (Gold) | 0.096 | 0.014 | 0.206 | tailwind | DIRECTIONAL |
| HG=F (Copper) | -0.073 | -0.199 | 0.106 | headwind | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | 0.061 | -0.068 | 0.294 | tailwind | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.059 | 0.009 | 0.149 | tailwind | DIRECTIONAL |
| DX-Y.NYB (US Dollar (DXY)) | -0.054 | -0.029 | -0.124 | headwind | DIRECTIONAL |
| SPY (S&P 500) | 0.047 | -0.083 | 0.318 | tailwind | CONTEXT |
| IWM (Russell 2000 (small caps)) | 0.041 | -0.061 | 0.206 | tailwind | CONTEXT |
| CL=F (Oil (WTI)) | -0.034 | -0.045 | -0.052 | neutral | CONTEXT |
| XLK (Technology) | 0.026 | -0.105 | 0.259 | neutral | CONTEXT |
| FXI (China large-cap (EM proxy)) | -0.015 | -0.036 | 0.03 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.014 | -0.099 | 0.205 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | 0.008 | -0.009 | 0.047 | neutral | CONTEXT |
| XLP (Staples (defensive)) | 0.007 | -0.078 | 0.149 | neutral | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.006 | -0.139 | 0.217 | neutral | CONTEXT |

### ntfs — Near-term forward spread

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| XLB (Materials (inflation beneficiary)) | -0.213 | -0.237 | -0.188 | headwind | CONFIRMED |
| XLK (Technology) | -0.208 | -0.063 | -0.323 | headwind | CONFIRMED |
| SPY (S&P 500) | -0.201 | -0.106 | -0.352 | headwind | CONFIRMED |
| XLF (Financials (rate beneficiary)) | -0.195 | -0.099 | -0.273 | headwind | CONFIRMED |
| BTC-USD (Bitcoin (long-duration)) | -0.18 | None | -0.145 | headwind | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.172 | -0.036 | -0.333 | headwind | DIRECTIONAL |
| IWM (Russell 2000 (small caps)) | -0.127 | -0.046 | -0.24 | headwind | CONFIRMED |
| FXI (China large-cap (EM proxy)) | -0.113 | -0.17 | -0.15 | headwind | CONFIRMED |
| XLP (Staples (defensive)) | -0.106 | -0.156 | -0.037 | headwind | DIRECTIONAL |
| TLT (Long Treasuries (20y+)) | 0.105 | 0.203 | -0.044 | tailwind | CONTEXT |
| GC=F (Gold) | -0.092 | 0.103 | -0.323 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.058 | -0.09 | -0.038 | headwind | DIRECTIONAL |
| XLV (Health Care (defensive)) | -0.053 | -0.064 | -0.034 | headwind | DIRECTIONAL |
| XLU (Utilities (bond proxy)) | -0.051 | -0.083 | -0.012 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | -0.048 | None | -0.048 | headwind | CONTEXT |
| CL=F (Oil (WTI)) | 0.032 | 0.089 | -0.005 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | 0.024 | -0.013 | 0.146 | neutral | CONTEXT |
| HG=F (Copper) | -0.012 | 0.141 | -0.18 | neutral | CONTEXT |

### real_speed_abs — |Real 10y 63d speed| (violence)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| GC=F (Gold) | 0.12 | 0.067 | 0.171 | tailwind | CONFIRMED |
| DX-Y.NYB (US Dollar (DXY)) | -0.099 | -0.156 | -0.01 | headwind | DIRECTIONAL |
| XLRE (Real Estate (rate-sensitive)) | 0.049 | None | 0.049 | tailwind | CONTEXT |
| XLF (Financials (rate beneficiary)) | -0.048 | -0.111 | 0.022 | headwind | CONTEXT |
| FXI (China large-cap (EM proxy)) | 0.032 | -0.008 | 0.078 | neutral | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.026 | -0.0 | 0.05 | neutral | CONTEXT |
| TLT (Long Treasuries (20y+)) | 0.026 | -0.006 | 0.055 | neutral | CONTEXT |
| SPY (S&P 500) | -0.022 | -0.05 | 0.01 | neutral | CONTEXT |
| IWM (Russell 2000 (small caps)) | -0.018 | -0.028 | -0.005 | neutral | CONTEXT |
| XLK (Technology) | -0.015 | -0.022 | -0.001 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | -0.015 | None | -0.028 | neutral | CONTEXT |
| XLV (Health Care (defensive)) | -0.012 | -0.051 | 0.037 | neutral | CONTEXT |
| XLP (Staples (defensive)) | 0.009 | -0.037 | 0.05 | neutral | CONTEXT |
| HG=F (Copper) | 0.008 | 0.003 | -0.011 | neutral | CONTEXT |
| XLU (Utilities (bond proxy)) | -0.006 | -0.091 | 0.077 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | -0.003 | 0.073 | -0.088 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.001 | 0.001 | 0.004 | neutral | CONTEXT |
| XLE (Energy (inflation beneficiary)) | -0.0 | 0.021 | -0.037 | neutral | CONTEXT |

### trend_spread — 3m10y trend (2y smooth, Faria-Verona)

| asset | IC (full) | pre | post | effect | verdict |
|---|--:|--:|--:|---|---|
| TLT (Long Treasuries (20y+)) | 0.128 | 0.123 | 0.036 | tailwind | DIRECTIONAL |
| XLP (Staples (defensive)) | 0.113 | 0.239 | -0.072 | tailwind | CONTEXT |
| XLU (Utilities (bond proxy)) | 0.101 | 0.253 | -0.12 | tailwind | CONTEXT |
| GC=F (Gold) | -0.099 | 0.043 | -0.323 | headwind | CONTEXT |
| XLV (Health Care (defensive)) | 0.081 | 0.174 | -0.065 | tailwind | CONTEXT |
| IWM (Russell 2000 (small caps)) | 0.071 | 0.237 | -0.173 | tailwind | CONTEXT |
| XLRE (Real Estate (rate-sensitive)) | -0.065 | None | -0.065 | headwind | CONTEXT |
| XLE (Energy (inflation beneficiary)) | 0.052 | 0.161 | -0.105 | tailwind | CONTEXT |
| HG=F (Copper) | 0.045 | 0.204 | -0.219 | tailwind | CONTEXT |
| XLK (Technology) | -0.04 | 0.149 | -0.177 | neutral | CONTEXT |
| DX-Y.NYB (US Dollar (DXY)) | -0.032 | -0.051 | 0.08 | neutral | CONTEXT |
| CL=F (Oil (WTI)) | 0.027 | 0.038 | 0.007 | neutral | CONTEXT |
| XLF (Financials (rate beneficiary)) | 0.025 | 0.21 | -0.189 | neutral | CONTEXT |
| XLB (Materials (inflation beneficiary)) | 0.025 | 0.093 | -0.109 | neutral | CONTEXT |
| FXI (China large-cap (EM proxy)) | -0.021 | -0.152 | -0.092 | neutral | CONTEXT |
| QQQ (Nasdaq 100 (long-duration growth)) | -0.014 | 0.144 | -0.183 | neutral | CONTEXT |
| BTC-USD (Bitcoin (long-duration)) | 0.014 | None | 0.068 | neutral | CONTEXT |
| SPY (S&P 500) | -0.005 | 0.144 | -0.259 | neutral | CONTEXT |

## Collinearity vs already-scored legs

VIF (>5 redundant) and the top correlated pairs — a 'new' leg that merely restates the breakeven-direction / TIPS-nominal / sticky-CPI legs already in the inflation axis is caught here and NOT double-counted.

| driver | VIF |
|---|--:|
| be10y | 189251.57 |
| _scored_tips_nominal | 189246.7 |
| nom10y_chg63 | 135094.09 |
| real10y_chg63 | 94892.76 |
| be10y_chg63 | 61459.09 |
| be5y5y | 16.62 |
| exp_wedge | 15.79 |
| ntfs | 14.3 |
| policy_gap | 11.49 |
| real10y | 10.82 |
| curve_tp_adj | 7.84 |
| trend_spread | 3.76 |
| corepce_gap | 3.62 |
| slope_chg63 | 2.9 |
| curvature | 2.85 |
| infl_accel | 1.97 |
| _scored_be10y_chg | 1.77 |
| _scored_sticky_dir | 1.55 |
| real_speed_abs | 1.36 |

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
- `policy_gap` ↔ `trend_spread`: 0.62
- `policy_gap` ↔ `curvature`: 0.6