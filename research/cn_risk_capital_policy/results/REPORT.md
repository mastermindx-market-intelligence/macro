# China Risk Radar Capital-Policy Validation

**Operation:** `cn-risk-p4-capital-policy-20260923-solpro-001`<br>
**Status:** `DRAFT_HOLD_RESEARCH_ONLY`<br>
**Policy verdict:** **HAZARD_VALID_BUT_EXACT_GROSS_UNVALIDATED**<br>
**Source base:** `49ceebf8d1a14c044684abdbeeb5779875cf20fc`<br>
**Preregistration commit:** `6caaf30b68b6b327dd7255f8610f8ea613a363ed`

> Historical results below are PIT-honest reconstructed history, not issued-forward policy performance. The detector question and the capital-policy question are adjudicated separately.

## Executive ruling

The exact current ladder passed the frozen exact-policy gate: **False**. The preregistered binary loud-state policy passed its separate gate: **False**.

Exact-gate failures: `episode_floor, elevated_only_episode_floor, all_loco`.<br>
Simple-policy gate failures: `mdd_protection, certainty_equivalent_ci, positive_episode_fraction, era_stability, loco`.

No source mapping, UI, `can_force`, Market State, ranking, execution, or live allocation consumer changed in this wave.

## Frozen benchmark and execution contract

Primary benchmark: Shanghai Composite `['china', '000001.SS']` from 2003-03-04 through 2026-09-23 (5721 sessions).

Primary timing: observe state at close *t*, apply gross to the next close-to-close return, charge 10 bps per unit of gross change, earn zero on unused gross, and do not charge the initial allocation. Lag-two and 25-bps scenarios are frozen sensitivities.

Investable robustness lane: CSI 300 ETF `510300.SS` from 2012-05-11 through 2026-09-23.

## Primary reconstructed results

| Policy | CAGR | Max DD | CVaR 95 | Vol | Sharpe | Sortino | Calmar | Avg gross | Reduced time | Turnover |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `current_ladder` | 5.28% | -64.15% | -3.30% | 21.16% | 0.350 | 0.485 | 0.082 | 0.939 | 41.08% | 93.400 |
| `constant_100` | 4.27% | -71.98% | -3.60% | 22.94% | 0.297 | 0.412 | 0.059 | 1.000 | 0.00% | 0.000 |
| `constant_075` | 3.70% | -60.77% | -2.70% | 17.20% | 0.297 | 0.412 | 0.061 | 0.750 | 100.00% | 0.000 |
| `matched_constant` | 4.16% | -69.54% | -3.38% | 21.53% | 0.297 | 0.412 | 0.060 | 0.939 | 100.00% | 0.000 |
| `binary_loud_075` | 4.99% | -66.48% | -3.41% | 21.86% | 0.333 | 0.461 | 0.075 | 0.968 | 12.69% | 55.250 |
| `current_riskoff_075` | 5.05% | -66.11% | -3.35% | 21.49% | 0.337 | 0.468 | 0.076 | 0.950 | 41.08% | 73.250 |
| `vol_target_15` | 3.03% | -52.39% | -2.38% | 15.96% | 0.267 | 0.371 | 0.058 | 0.814 | 60.87% | 80.535 |

## Protection versus merely holding less

The current ladder's mean executed gross was **0.939**; the exposure-matched constant held exactly **0.939** without timing.

Current minus matched constant: CAGR 1.12%, max-drawdown difference 5.39%, CVaR difference 0.08%, Calmar difference 0.023, and certainty-equivalent difference 1.23%.

Exact risk-off ×0.62 versus the same ladder with ×0.75: CAGR difference 0.23%, max-drawdown difference 1.96%, CVaR difference 0.05%, and Calmar difference 0.006.

On the investable CSI-300 proxy, the same ×0.62-minus-×0.75 comparison is: CAGR -0.06%, max drawdown -0.49%, CVaR 0.04%, and Calmar -0.003; negative values favor ×0.75.

Bootstrap 90% intervals (current minus matched):

- CAGR: [0.10%, 1.13%, 2.19%]
- Max drawdown: [-2.04%, 1.93%, 7.43%]
- CVaR 95: [0.00%, 0.08%, 0.17%]
- Calmar: [0.001, 0.020, 0.054]
- Certainty equivalent: [0.18%, 1.24%, 2.36%]

Bootstrap 90% intervals (×0.62 minus ×0.75):

- CAGR: [-0.12%, 0.23%, 0.60%]
- Max drawdown: [-0.51%, 0.79%, 2.63%]
- CVaR 95: [0.03%, 0.05%, 0.08%]
- Calmar: [-0.002, 0.005, 0.016]
- Certainty equivalent: [0.00%, 0.36%, 0.75%]

## Opportunity cost and churn

Across the full sample, the arithmetic contribution sums were: missed positive returns **195.68%**, avoided negative returns **218.10%**, transaction-cost drag **9.34%**, and net excess versus full gross **13.08%**.

Annualized contribution equivalents were: missed upside **8.62%**, avoided downside **9.61%**, cost drag **0.41%**, and net arithmetic timing contribution **0.58%**.

It made **1064** executed gross changes, with total turnover **93.400** and annualized turnover **4.115**.

Binary loud-state policy: missed upside **108.65%**, avoided downside **124.39%**, and 221 exposure changes.

## Independent episodes

Eligible complete episode N: **26**; risk-off-containing: **24**; elevated-only: **2**. Open/censored clusters excluded from authority N: **1**.

Downside episodes: **21**; false-positive/non-5%-drawdown episodes: **5**.

All false-positive episodes produced positive timing value in **0 / 5** cases; their aggregate arithmetic policy excess was **-4.84%**, with **3.02%** of recovery upside missed.

Across true downside episodes, aggregate arithmetic policy excess was **25.17%**, positive in **11 / 21** episodes.

Risk-off-containing episode downside rate: **87.50%**, median path loss **-7.87%**. Elevated-only downside rate: **0.00%**, median path loss **-0.78%**.

Current policy positive-timing fraction: **42.31%**; binary policy: **34.62%**.

## Crisis concentration, recovery, and leave-one-crisis-out

Current-ladder protection concentration: top crisis **45.92%**; top two crises **66.29%** of all positive crisis protection.

LOCO runs beating the matched constant on both Calmar and CVaR: current **8 / 9**; binary **0 / 9**.

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

## Stability

Lag/cost sensitivity pass — current: **True**; binary: **True**.<br>
Split-era pass — current: **True**; binary: **False**.

The full scenario, era, episode, crisis, recovery, and LOCO rows are in the compact CSV artifacts; no post-outcome mapping or threshold search was performed.

## Product-language adjudication

- May say **suggested size**: **False**.
- May say **risk-budget reference**: **False**.
- May show **×0.62 as advice**: **False**.
- May show **×0.62 in research/debug disclosure**: **True**.
- Should round to a plain-English fraction such as “half of normal”: **False**.
- Supported authority today: **DISPLAY_CONTEXT_ONLY**.

No ruling in this wave authorizes automatic sizing, trade origination, exits, name vetoes, `can_force`, or a live control-plane consumer.

## Forward evidence limit

The issued ledger has 34 rows and only 16 matured rows. Its matured state counts are `{'caution': 9, 'elevated': 1, 'risk-off': 4, 'watch': 2}`. It is monitoring evidence, not enough information to optimize five gross coefficients.

## Shadow candidate

No shadow policy candidate was earned under the frozen gates.

## Hold boundary

This evidence carrier is intentionally Draft/HOLD. The Astra integrator must make any later source or product-language decision in a separate wave. Do not merge this PR and do not re-run a ladder search around these outcomes.
