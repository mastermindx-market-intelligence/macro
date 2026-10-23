# China Risk Radar Capital-Policy Validation

**Operation:** `cn-risk-p4-capital-policy-20260923-solpro-001`<br>
**Status:** `DRAFT_HOLD_RESEARCH_ONLY`<br>
**Policy verdict:** **INSUFFICIENT_INDEPENDENT_EPISODES**<br>
**Source base:** `49ceebf8d1a14c044684abdbeeb5779875cf20fc`<br>
**Preregistration commit:** `6caaf30b68b6b327dd7255f8610f8ea613a363ed`

> Historical policy results are a causal/date-aligned, definition-current reconstruction. They are not membership-PIT, are not source-vintage verified, and are diagnostic only. Authority is adjudicated from the issued-forward ledger.

## Executive ruling

Authority-bearing effective episode N is **1**: 1 risk-off-containing and 0 elevated-only. This is insufficient to estimate either a five-step ladder or the exact ×0.62 risk-off coefficient.

The exact current ladder passed the frozen exact-policy gate: **False**. The preregistered binary loud-state policy passed its separate gate: **False**.

Exact-gate failures: `historical_authority_eligible, episode_floor, riskoff_episode_floor, elevated_only_episode_floor, all_loco`.<br>
Simple-policy gate failures: `historical_authority_eligible, episode_floor, riskoff_episode_floor, mdd_protection, certainty_equivalent_ci, positive_episode_fraction, era_stability, loco`.

No source mapping, UI, `can_force`, Market State, ranking, execution, Prophet, or live allocation consumer changed in this wave.

## Historical source qualification

Classification: **CAUSAL_DEFINITION_CURRENT_NOT_AUTHORITY_GRADE_PIT**. Construction is causal: **True**. Historical authority eligible: **False**.

The exact CN state uses the breadth leg: **True**. The breadth history is rebuilt from the current hand-curated membership over maximum available history: **True**. Date-effective membership fields are present: **False**; observed membership columns are `['name', 'sector']`.

Source-vintage metadata is present across the reconstructed macro inputs: **False**. Therefore the long history is retained for diagnostic counterfactuals but is barred from promotion gates.

## Frozen benchmark and execution contract

The state reconstruction begins 2003-03-03; the first aligned benchmark return is 2003-03-04 because close-to-close returns consume one prior close. The lane runs through 2026-09-23 with 5721 aligned returns and 5720 executed primary-policy observations after the one-session lag.

State is observed at close *t* and gross is applied to the next close-to-close return. The primary scenario charges 10 bps per unit of gross change, earns zero on unused gross, and does not charge the initial allocation. Lag-two and 25-bps variants are frozen sensitivities.

The investable robustness lane uses CSI 300 ETF `510300.SS` from 2012-05-11 through 2026-09-23.

## Diagnostic reconstructed results — not authority-bearing

| Policy | CAGR | Max DD | CVaR 95 | Vol | Sharpe | Sortino | Calmar | Avg gross | Reduced time | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `current_ladder` | 5.28% | -64.15% | -3.30% | 21.16% | 0.350 | 0.485 | 0.082 | 0.939 | 41.08% | 93.400 |
| `constant_100` | 4.27% | -71.98% | -3.60% | 22.94% | 0.297 | 0.412 | 0.059 | 1.000 | 0.00% | 0.000 |
| `constant_075` | 3.70% | -60.77% | -2.70% | 17.20% | 0.297 | 0.412 | 0.061 | 0.750 | 100.00% | 0.000 |
| `matched_constant` | 4.16% | -69.54% | -3.38% | 21.53% | 0.297 | 0.412 | 0.060 | 0.939 | 100.00% | 0.000 |
| `binary_loud_075` | 4.99% | -66.48% | -3.41% | 21.86% | 0.333 | 0.461 | 0.075 | 0.968 | 12.69% | 55.250 |
| `current_riskoff_075` | 5.05% | -66.11% | -3.35% | 21.49% | 0.337 | 0.468 | 0.076 | 0.950 | 41.08% | 73.250 |
| `vol_target_15` | 3.03% | -52.39% | -2.38% | 15.96% | 0.267 | 0.371 | 0.058 | 0.814 | 60.87% | 80.535 |

## Diagnostic protection versus merely holding less

The current ladder's mean executed gross is **0.939**; the one canonical exposure-matched constant holds exactly **0.939**, derived from executed post-lag current-ladder gross without return optimization.

Current minus matched constant: CAGR 1.12%, max-drawdown difference 5.39%, CVaR difference 0.08%, Calmar difference 0.023, and certainty-equivalent difference 1.23%.

Exact risk-off ×0.62 minus the same ladder with ×0.75: CAGR 0.23%, max drawdown 1.96%, CVaR 0.05%, and Calmar 0.006.

On the investable CSI-300 proxy, ×0.62 minus ×0.75 is: CAGR -0.06%, max drawdown -0.49%, CVaR 0.04%, and Calmar -0.003; negative values favor ×0.75.

Diagnostic bootstrap 90% intervals (current minus matched):

- CAGR: [0.10%, 1.13%, 2.19%]
- Max drawdown: [-2.04%, 1.93%, 7.43%]
- CVaR 95: [0.00%, 0.08%, 0.17%]
- Calmar: [0.001, 0.020, 0.054]
- Certainty equivalent: [0.18%, 1.24%, 2.36%]

Diagnostic bootstrap 90% intervals (×0.62 minus ×0.75):

- CAGR: [-0.12%, 0.23%, 0.60%]
- Max drawdown: [-0.51%, 0.79%, 2.63%]
- CVaR 95: [0.03%, 0.05%, 0.08%]
- Calmar: [-0.002, 0.005, 0.016]
- Certainty equivalent: [0.00%, 0.36%, 0.75%]

## Diagnostic opportunity cost and churn

Annualized arithmetic contribution equivalents are: missed upside **8.62%**, avoided downside **9.61%**, cost drag **0.41%**, and net timing contribution **0.58%**.

The current ladder makes **1064** executed gross changes, with total turnover **93.400** and annualized turnover **4.115**.

## Episode accounting

Issued-forward authority N is **1**. The diagnostic reconstruction contains 26 complete clusters, of which 6 have 21-session outcome windows that reach the next alert and are excluded from independent N. That leaves **20** non-overlapping diagnostic episodes; 1 open cluster is censored.

Within the non-overlapping diagnostic set, downside episodes are **16** and non-5%-drawdown/false-positive episodes are **4**.

False-positive aggregate arithmetic policy excess is **-3.42%**, positive in **0 / 4** cases, with **2.51%** of recovery upside missed.

True-downside aggregate arithmetic policy excess is **24.56%**, positive in **9 / 16** cases.

Diagnostic risk-off-containing downside rate: **88.89%**, median path loss **-7.87%**. Elevated-only downside rate: **0.00%**, median path loss **-0.78%**.

Diagnostic positive-timing fraction: current **45.00%**; binary **35.00%**.

## Diagnostic crisis, recovery, and leave-one-crisis-out

Current-ladder protection concentration: top crisis **45.92%**; top two **66.29%** of all positive crisis protection.

LOCO runs beating the matched constant on both Calmar and CVaR: current **8 / 9**; binary **0 / 9**.

Recovery capture is undefined when benchmark recovery is non-positive.

| Crisis | Policy return | Full return | Protection | Policy max DD | Full max DD | Recovery capture | Recovery avg gross |
|---|---:|---:|---:|---:|---:|---:|---:|
| `bear_2004_05` | -39.79% | -42.74% | 2.95% | -40.70% | -43.09% | 82.80% | 0.953 |
| `gfc_2007_08` | -63.82% | -71.70% | 7.88% | -64.15% | -71.98% | 89.45% | 0.959 |
| `tightening_2009_10` | -32.14% | -31.73% | -0.41% | -32.31% | -31.90% | 99.32% | 0.998 |
| `slowdown_2011_12` | -35.89% | -35.76% | -0.13% | -36.03% | -35.90% | 97.04% | 0.995 |
| `bubble_2015_16` | -45.92% | -48.15% | 2.23% | -46.39% | -48.60% | 97.44% | 0.979 |
| `trade_deleveraging_2018` | -30.03% | -30.51% | 0.48% | -30.28% | -30.77% | 99.81% | 0.998 |
| `covid_2020` | -13.97% | -13.97% | 0.00% | -14.62% | -14.62% | 96.34% | 0.976 |
| `property_2021_22` | -18.56% | -22.05% | 3.50% | -18.80% | -22.31% | 72.99% | 0.896 |
| `confidence_2023_24` | -18.84% | -18.96% | 0.12% | -20.29% | -20.41% | 99.28% | 0.996 |

## Diagnostic stability

Lag/cost direction — current: **True**; binary: **True**.<br>
Split-era direction — current: **True**; binary: **False**.

These diagnostic checks cannot override the non-PIT source qualification or the issued-forward episode floor.

## Product-language adjudication

- May say **suggested size**: **False**.
- May say **risk-budget reference**: **False**.
- May show **×0.62 as advice**: **False**.
- May show **×0.62 in research/debug disclosure**: **True**.
- Should round to “half of normal”: **False**.
- Supported authority today: **DISPLAY_CONTEXT_ONLY**.

No ruling in this wave authorizes automatic sizing, trade origination, exits, name vetoes, `can_force`, or a live control-plane consumer.

## Forward evidence limit

The issued ledger has 34 rows, 16 matured rows, and 5 matured loud rows. Its matured state counts are `{'caution': 9, 'elevated': 1, 'risk-off': 4, 'watch': 2}`. Those matured loud rows form only **1** completed independent episode; 1 open loud episode remains ungraded. Therefore neither five coefficients nor a simpler promoted policy can be estimated honestly.

## Shadow candidate

No shadow policy candidate was earned under the frozen gates.

## Hold boundary

This evidence carrier is intentionally Draft/HOLD. The Astra integrator may consume the fail-closed ruling, but any PIT-data repair or later source/UI policy change requires a separately authorized wave. Do not merge this PR and do not search alternative ladders around these outcomes.
