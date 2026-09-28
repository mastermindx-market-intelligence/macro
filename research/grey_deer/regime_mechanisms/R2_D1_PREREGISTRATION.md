# R2-D1 — vintage-native conditional diagnostic

Operation: `risk-regime-mechanism-research-20260927-sol-001`. Parent #8128; same research carrier PR #8133. Frozen before any R2-D1 outcome construction or fitted-model result inspection. R1 and the original R2 protocol remain unchanged. This is an explicitly named supplementary diagnostic, NOT the original B1/B2/C1 comparison, not a new production regime owner, and not predictive or capital-policy promotion.

## Why this supplementary construction is needed

Pinned Macro source/data: `f6dae649ee6d32ec65a95ccea411b205d0b0bc45`.

The actual `regime_one._causal_filtered_pquad` estimates means, covariances, transition matrix and initial distribution on its entire supplied input before filtering. A source-isolated replay using the actual function and scipy Gaussian log-density in place of the unavailable hmmlearn dependency compared an input ending 2026-06-30 with one ending 2026-09-25: 172 of 189 common published-history dates changed, one modal regime changed, and the maximum probability change was 0.0282. This is a historical-parameter leakage result, not proof that every current endpoint is wrong. The source file SHA-256 is `7671e86ae2cce28f83a83054ad76c4920638f68a28a92af074dbf28c054d95eb`; actual history input SHA-256 is `5003f8c9a75fe3a9ae47a50384d72377ef187c4d6fc69eeb8ff7246de25558d3`.

The separate release-axis row is used for the macro display; `_forward_read` still receives the original full regime frame. Therefore calling the history filtered, or constructing a release-aware display row, does not qualify the historical posterior for R2. Original incumbent/conditional reconstruction remains open.

A bounded census found separate, already-collected full-vintage stores for PAYEMS and CPIAUCSL, rather than only the first-release table read by the generic accessor. They permit a more limited transparent experiment with actually archived economic releases. R2-D1 uses them explicitly; it does not relabel that construction as the existing production regime.

## Frozen input identity and scope

US only. Historical decision dates 2007-01-01 through 2026-09-25, plus prehistory for trailing transforms. Fixed current-snapshot daily market stores; archived ALFRED macro vintages. No new collector or provider call. All reads use immutable git blobs from the pin, not changing working-tree bytes. No source/data/ledger/UI/policy modification.

- SPY total-return `close`: SHA256 `70e78d38834e129ddf48e782b4c633c388479e86484eecb2f4046cc2acd1a4af`.
- `_MOVE` close: `93c4e4aaa87451646312f2643afa07e69d1bdeb56b467924f75c515feb6e2a97`.
- `_VIX` close: `31a88a0113eb837108ac6c2cf1d2ccb0b9b2a0fa3131a09b42a5a7018dcd5a04`.
- TLT total-return close, secondary joint-loss target only: `d69d3f8c54f7e00d305ec358f906f836a458728f8bdd0ee86ea7921811519d38`.
- DGS2 `us2y`: `aac49f450bb2d70377d2f3f62112f2d5fd38700b83c7ad3dc52e8f7dcf4d2102`.
- DGS10 `us10y`: `86ff480555fc3de845ff576325d2b96de039034a19a6ffc508829f5efda119cd`.
- DFII10 `us10y_real`: `8714929802efe9ee634c6d8a3251845aca4e26bada7062d7ef74a5c4dec151fc`.
- BAMLH0A0HYM2 `hy_oas`: `5a50c7daa61f0ecc6961a84c97b29d227972839e0fe085fad9c5a1b4b41d6168`.
- `data/fred_vintage/release_targets/PAYEMS_all_vintages.parquet`: 314191 rows, 360 distinct vintage dates, SHA256 `5fe02dde232efad7799d14b5331bd83d4ba2f849dc82e687bd49ade357debaee`.
- `data/fred_vintage/release_targets/CPIAUCSL_all_vintages.parquet`: 292553 rows, 376 distinct vintage dates, SHA256 `abc6b65a873a3d6de63d85379c86b61f71f99480354f46915c391d506970718b`.

Both full-vintage tables have zero duplicate period/vintage pairs and zero missing schema fields in the inspected pin. Manifest hashes match. Vendor observation/publication timestamps and market-data vintages are not present in daily stores; historical market-data release and adjustment uncertainty remains explicit. No claim of wholly vendor-vintage PIT is made.

## Clocks and macro construction

Daily assessment is conceptualized after US close at 17:00 New York time. All rates/credit/MOVE/VIX inputs use strictly earlier observation dates, not same-day closes; raw source age must be at most three elapsed SPY sessions. This is a conservative date-availability approximation, not observed vendor publication telemetry. No trade is assumed executable at the already-passed assessment close.

For each archived PAYEMS/CPI vintage, derive YoY percent change at its latest observation period and acceleration as that YoY rate minus the YoY rate three months earlier, all from the SAME vintage's period history. Never subtract independently first-published levels with differing revisions. Date-only macro releases are eligible strictly after their vintage date (next observed SPY session), never on the same date. A macro release older than 60 calendar days, or its latest observation period older than 95 calendar days, is unavailable. No modelled macro release-date substitution.

For market levels/changes, use the source-aware prior-date projection onto the SPY session calendar, preserving availability ages. Rates/OAS changes are 5/21 SPY sessions as specified below. MOVE/VIX percentile uses actual source observations, 504 trailing observations including current, minimum252; midrank ties. MOVE acceleration retains the earlier descriptive rule: >=20% and >=10 points over five source observations, OR >=30% and >=15 points over twenty source observations. No new threshold search.

## Targets

Primary Y21: any of the next21 SPY total-return closes <=0.95 times the decision-date close; exclude today's loss, require all21 future closes; otherwise null until mature. Secondary Y63: <=0.90 within63 sessions. Secondary hedge-failure descriptor: both SPY and TLT total returns negative over the next21 sessions. TLT is a long-duration US Treasury ETF, not a generic world bond hedge. No cash/trading P&L is computed. Each target's models compare identical eligible rows.

## Models and fixed features

D0 = expanding training base rate with Jeffreys smoothing. D1 = ridge logistic additive baseline. D2 = identical baseline plus four prespecified interactions. None is a replacement for original B1/B2/C1, which remains unrun.

Seventeen baseline fields: 2y nominal level; 10y nominal level; 10y real level; real5 change; real21 change; nominal2y21 change; OAS level; OAS21 change; MOVE percentile; MOVE acceleration flag; VIX percentile; PAYEMS YoY; PAYEMS three-month YoY acceleration; CPI YoY; CPI three-month YoY acceleration; current SPY drawdown from trailing252-session high; current SPY21 return. Units are percentage points for yields/OAS/macro rates, percentage returns for SPY, percentile0–100 for volatility ranks, binary for MOVE acceleration.

Four interactions: real21 change × CPI acceleration; OAS21 change × negative PAYEMS acceleration; MOVE acceleration × OAS21 change; real21 change × positive magnitude of current SPY drawdown. No coefficient signs are imposed. No extra feature search. Descriptive backdrop cells are the signs of payroll and CPI acceleration; zeros are separately labelled flat, not forced into a quadrant.

Training-only mean/standard-deviation scaling of each model's own columns; no global scaling, clipping or test-aware feature selection. Constant training columns use scale1. Ridge penalty convention: summed logistic negative log likelihood + ||nonintercept coefficients||²/(2C); intercept unpenalized. C in {0.1,1,10}, selected by average Brier score in the two prior annual inner folds; use C1 only when no inner fold is eligible. Chronological ties choose the smaller C.

## Validation

Annual expanding test years2015–2026. Training begins2007 and ends at least63 observed SPY sessions before the first test session; all labels must have matured before the test cut. Same63-session purge for inner folds. Minimum300 training rows and both outcome classes; a refused fit stays refused, not constant-prediction success. Numerical convergence and gradient norm reported; no silently accepted optimizer failure.

Report pooled/annual and descriptive-backdrop-cell Brier/log loss/AP/AUC, calibration bins, and common sample counts. Compare warning burdens5/10/20% using training-prediction quantiles only, ties unbroken by outcomes. Disclose realized test warning burden (training quantiles do not guarantee matched test rates); do not claim matched realized burden if it differs.

First-warning episode view requires21 eligible observed quiet sessions to rearm; missing dates reset quiet streak, never rearm. Report first-warning hits/N separately from daily overlap. One global event is one dependent family; the US-only result grants no country replication claim.

Paired D2−D1 Brier uncertainty uses moving calendar blocks of21/63/126 SPY sessions, 2000 bootstrap draws each, seed20260927. Preserve ineligible-date gaps in the resampling calendar. Leave-era stress windows out of AGGREGATION for sensitivity:2007–09,2011,2015–16,2018,2020,2022,March–May2023,August2024,April2025. This is not a leave-one-crisis-out REFIT; report that distinction. True model-refit crisis exclusion and original incumbent comparison remain owed.

## Evidence ceiling and next decision

This diagnostic may support or refute the specific four-interaction construction under two archived macro measures. It cannot certify the exact full production regime, structural causality, unseen-crisis reliability, warning-policy optimality, country effects or automatic sizing. Historical episodes are design-exposed. Independent scientific review and the original R2 incumbent comparison remain mandatory before promotion.

The research code/tests/results will live under this existing research path. No production module is edited; the earlier denied MOVE integration is not retried, delegated or rerouted. A failed conditional construction is reported without retuning. A useful result advances the next investigation; it does not close the wider bank/funding/energy/propagation/repair program.