# China Market State P3 — Results and Adjudication

**Operation:** `cn-risk-p3-market-state-validation-20260923-solpro-001`  
**Evidence class:** A — reconstructed historical evidence only  
**Frozen prereg payload:** `0533cb7add838e65553756e9f21b59b9ff1ae058f347dac0d946da4e977671d8`  
**Frozen study base:** `d5eb16f3b3a093afb053efe275be62778729dcf4`  
**Sample end:** 2026-09-24  
**Production behavior changed:** none

## Executive result

The current China Market State score does **not** earn forecast authority from P3.

On the preregistered, conservative release-lagged reconstruction, the current hand-weight model has essentially no full-sample discrimination for either target:

- 21-session >=5% drawdown: AUC **0.509**, 95% moving-block CI **[0.437, 0.579]**.
- 42-session >=10% drawdown: AUC **0.495**, 95% moving-block CI **[0.350, 0.642]**.
- Score vs 21-session return: Spearman **0.003**, CI **[-0.105, 0.116]**.
- Score vs 42-session return: Spearman **-0.027**, CI **[-0.184, 0.125]**.

The nominal daily sample is large, but it is highly overlapping. The dependence-aware effective sample is only about **163** observations at 21 sessions and **81** at 42 sessions; the event-run view contains **106** and **30** event episodes respectively.

The product therefore remains what its source doctrine says it is: a synthesis of signals that have already turned. P3 classifies the 0–100 score **DESCRIPTIVE_ONLY**.

## Frozen enum rulings

| Question | P3 ruling |
|---|---|
| CURRENT_WEIGHTS | **INSUFFICIENT** |
| CUT_42 | **PRODUCT_ONLY** |
| CUT_60 | **PRODUCT_ONLY** |
| SCORE_0_100 | **DESCRIPTIVE_ONLY** |
| trend | **NEED_MORE_DATA** |
| risk | **KEEP** |
| vol | **DISPLAY_ONLY** |
| breadth | **DISPLAY_ONLY** |
| liquidity | **NEED_MORE_DATA** |
| stress | **DISPLAY_ONLY** |

No ruling authorizes a production weight, cut, mapping, UI, sizing, Portfolio, Prophet, or Risk Radar change.

## What the current score means

The frozen production artifact for **2026-09-24** is reproduced exactly:

| Component | Score |
|---|---:|
| Trend | 32 |
| Risk appetite | 51 |
| Volatility/froth | 58 |
| Breadth | 11 |
| Liquidity | 16 |
| Stress | 63 |
| **Raw blend** | **38** |

The commission packet's earlier 39 was orientation only; the exact frozen artifact is **38**.

A 38 means that the current weighted blend of the already-turned inputs sits in the product's Risk-off band. It does **not** mean a 62% probability of a drawdown, a 62% risk level, an expected return, or any calibrated forecast.

The conservative release-lag reconstruction changes risk appetite 51 -> 49 and the raw blend 38 -> **37**, but leaves the product band Risk-off. The score is only 4–5 points below the 42 boundary. Under the frozen component-omission sensitivity, removing breadth moves the release-lagged score to **42** (Mixed); removing liquidity moves it to **41**. So today's label is directionally defensive but not far from its product boundary.

## Cut 42: Risk-off

At the current 42 cut:

- 21-session >=5% drawdown base rate: **20.46%**.
- Risk-off event rate: **22.47%**, point lift **1.10x**.
- Dependence-aware Risk-off minus non-Risk-off difference: **+2.7 pp**, CI **[-5.0 pp, +10.7 pp]**.
- 42-session >=10% drawdown base rate: **9.96%**.
- Risk-off event rate: **10.97%**, point lift **1.10x**.
- Dependence-aware difference: **+1.4 pp**, CI **[-5.7 pp, +9.5 pp]**.

None of the preregistered neighboring lower cuts **34 / 38 / 42 / 46 / 50** produces a dependence-aware difference whose 95% interval excludes zero.

**Ruling: PRODUCT_ONLY.** The cut remains coherent as the existing red/yellow product boundary, but P3 does not support calling 42 an empirically validated drawdown threshold.

## Cut 60: Risk-on

Risk-on versus Mixed at 60 shows no reliable separation:

- 21-session drawdown-rate difference: **+0.35 pp**, CI **[-8.15 pp, +7.72 pp]**.
- 42-session drawdown-rate difference: **+2.03 pp**, CI **[-6.04 pp, +10.35 pp]**.
- 21-session return difference: **-0.09 pp**, CI **[-1.44 pp, +1.23 pp]**.
- 42-session return difference: **-0.72 pp**, CI **[-2.67 pp, +1.29 pp]**.

None of the preregistered upper cuts **52 / 56 / 60 / 64 / 68** clears zero on tail or return separation.

**Ruling: PRODUCT_ONLY.** Sixty may remain a green/product-state boundary; it is not a demonstrated forecast threshold.

## Weights and simple baselines

Equal weights do not beat the current hand weights:

- 21d AUC delta vs current: **+0.0068**, CI **[-0.0036, +0.0180]**.
- 42d AUC delta: **-0.0054**, CI **[-0.0232, +0.0154]**.

The simple trend+breadth+liquidity baseline is actually worse than the current model on both preregistered event targets, with paired intervals excluding zero:

- 21d AUC delta: **-0.0329**, CI **[-0.0612, -0.0071]**.
- 42d AUC delta: **-0.0519**, CI **[-0.1028, -0.0080]**.

However, the current model itself does not clear forecast-null uncertainty, and component effects conflict by horizon/era. Therefore P3 does not call the incumbent weights optimized, does not declare equal weight superior, and does not nominate a production reweight.

**CURRENT_WEIGHTS: INSUFFICIENT.**

## Component ablations

### Risk appetite — KEEP

Removing risk appetite worsens the 21d tail discrimination by **-0.0224 AUC**, CI **[-0.0376, -0.0082]**. The sign is stable in both chronological halves, post-2016, the near-current slice, every frozen crisis exclusion, the production-reference sensitivity, and the CN-session-anchor sensitivity.

The 42d delta is also negative at -0.0309, although its CI reaches approximately zero.

Risk is the only component with clear incremental 21d evidence under the preregistered paired test.

### Trend — NEED_MORE_DATA

Removing trend improves 21d AUC by **+0.0340**, CI **[+0.0069, +0.0625]**. That improvement is directionally stable across both halves and all crisis exclusions.

But the 42d result is not robust, and its sign reverses in the recent half, near-current slice, and production-reference sensitivity. Trend-only is itself worse than the full model at 21d.

This is a real interaction/falsifier worth follow-up, but not a clean removal result.

### Liquidity — NEED_MORE_DATA

Removing liquidity improves the point estimate at both horizons (+0.0073 / +0.0203 AUC), and the improvement grows in later 42d samples, but both paired intervals include zero. The historical macro leg also depends on conservative release-lagged **current-vintage** reconstruction rather than genuine historical vintages.

That combination is insufficient for either KEEP or REMOVE_CANDIDATE as a predictive component.

### Volatility/froth — DISPLAY_ONLY

Removing vol changes AUC by only -0.0059 at 21d and -0.0089 at 42d; both intervals include zero. It remains coherent as descriptive options/crowding context, not forecast authority.

### Breadth — DISPLAY_ONLY

Removing breadth changes neither target robustly. Historical breadth is reconstructed from today's curated 82-name large-cap roster rather than point-in-time membership, which prevents a stronger predictive claim. Breadth remains useful as participation context.

### Stress — DISPLAY_ONLY

The preregistered falsifier does **not** support downweighting or removing stress:

- Stress-half 21d delta: -0.0024; CI crosses zero.
- Stress-half 42d delta: essentially zero; CI crosses zero.
- Stress-zero / LOCO-stress 21d delta: -0.0045; CI **[-0.0151, +0.0049]**.
- Stress-zero 42d delta: +0.0003; CI **[-0.0136, +0.0135]**.

The leg therefore has no demonstrated incremental forecast edge, but it also has no OOS case for removal. Keep it as descriptive downturn context only.

## Era and robustness result

The apparent forecast relationship is strongly era-sensitive.

Current model AUCs:

| Slice | 21d | 42d |
|---|---:|---:|
| 2012-08-14 to 2019-09-02 | 0.482 | 0.451 |
| 2019-09-03 to 2026-09-24 | 0.547 | 0.619 |
| Post-2016 | 0.547 | 0.598 |
| Near-current / QVIX era | 0.576 | 0.780 |
| Full primary | 0.509 | 0.495 |

The full-sample dependence-aware intervals remain non-significant, and frozen crisis exclusions move the point estimates materially. In particular, excluding the 2021–2022 grinding bear moves current 42d AUC down to about **0.433**, while excluding the 2023–2024 grind moves it to about **0.522**.

This is not stable long-horizon evidence.

## Temporal and source sensitivity

The conservative release-lagged reconstruction produces current-model AUCs of **0.509 / 0.495** at 21d/42d.

The production reference-stamped reconstruction gives **0.489 / 0.457**.

That material difference is itself evidence that China macro publication timing matters. Since the repository does not hold complete genuine historical release vintages for this model closure, P3 cannot promote reconstructed results to true PIT authority.

The current US-default versus CN-session 3-session trend anchor barely changes aggregate P3 results (**0.509/0.495** vs **0.510/0.496**), despite the underlying bucket geometry defect. That defect should still be fixed separately if product correctness requires it, but P3 does not use it to explain the forecast result and does not modify production.

## What may and may not be claimed

P3 supports these claims:

- Current Market State is useful as a compact descriptive synthesis of market state.
- The 42/60 bands can remain product semantics.
- The current Risk-off band has a modest historical point lift, but the dependence-aware uncertainty is too wide to call it reliable.
- Equal weights are not demonstrably better.
- Risk appetite adds some incremental 21d tail information.
- Trend interaction and liquidity timing deserve targeted follow-up.
- Stress does not earn forecast authority and does not earn removal.

P3 **does not** support saying:

- 42 is a validated drawdown threshold.
- 60 identifies a reliably safer or higher-return Risk-on state.
- 38 is a probability or calibrated risk forecast.
- the current weights are optimized or forecast-validated.
- equal weights are superior.
- stress should be downweighted or removed.
- reconstructed history authorizes capital sizing or policy.

## Exact next evidence

No production change follows from P3.

If predictive authority remains a product goal, the next evidence should be a genuinely issued **same-model prospective cohort**, using the existing forward-log / exact-model issue-receipt discipline rather than creating a second ledger. China macro publication/vintage provenance and breadth membership PIT should be improved before any promotion decision.

Trend interaction and liquidity timing can be investigated as bounded follow-up research candidates, but this P3 result does not authorize reweighting or removal.
