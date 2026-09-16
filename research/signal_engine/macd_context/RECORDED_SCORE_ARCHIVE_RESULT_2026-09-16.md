# Recorded swing-entry quality: recovered archive result

Date: 2026-09-16. State: completed descriptive audit; predictive/product program PARTIAL.

## What this measures

This is the previously declared fixed audit of archived `recorded_horizon_d21` against the existing H21 `ret`, not a new policy backtest. The pre-outcome scope ruling was published at `903f9b56b0a39a5d88892a3cbef7daf2da2e37cd`. Its source and complete results were generated before this recovery, but had not been committed or delivered in a successful final reply. This recovery verifies and publishes them without rerunning or optimizing the result.

Within each recorded-ranker/price-basis group, average-rank Spearman correlation is computed separately for each date. Defined date correlations are then equally weighted. Undefined dates remain explicitly recorded. A negative correlation means higher recorded quality tended to accompany lower subsequent returns within the observed dates; it does not mean all high-scored stocks lost money, nor is it a win rate.

## All six declared groups

| Recorded ranker | Price basis | Rows | Dates / defined dates | Mean within-date rank correlation |
|---|---|---:|---:|---:|
| bottoming-alignment | adjusted | 166 | 7 / 7 | -0.082253 |
| bottoming-alignment | unadjusted | 27 | 7 / 6 | -0.192674 |
| bottoming-alignment | unverified_pre_20260806 | 34 | 1 / 1 | -0.340240 |
| confluence | adjusted | 512 | 9 / 9 | -0.218077 |
| confluence | unadjusted | 10 | 4 / 2 | -0.171429 |
| us_prophet_v1 | adjusted | 74 | 1 / 1 | -0.175747 |

All 823 target rows have finite score/outcome pairs. There are 18 distinct board dates across the target, not the sum of the table's overlapping basis-group dates. The 26 defined date/stratum correlations are retained in `recorded_score_description_20260916_r1/date_associations.csv`. All six aggregate directions are negative; they are not six independent confirmations of an effect.

## Interpretation and explicit non-conclusions

The recorded scores do not display the intended positive return-ranking relationship in these particular archive groups. The adjusted confluence group is the largest and warrants investigation, but no p-value, confidence interval or statistical-superiority claim was commissioned or computed. These data do not justify mechanically reversing the score, optimizing thresholds, changing a live gate, or claiming the current Prophet engine is proven defective.

The archive is selected, the outcome windows overlap, ranking labels are not complete runtime versions, and publication/input vintages remain unverified. There is no current-v3 H21 cohort and no example of the specified SPY-up/RSP-down or SPY-below-200 repair state. Those questions remain unsupported here. Score quality, absolute profit, target-before-stop success, and holding durability remain different objectives.

## Reproducibility and accounting

Input joined dataset SHA256: `366d94709ea8fef4ac91cc30cf4efd975b26e68a65766082e5ca8feb99aca6db`.
Measured audit source SHA256: `61fe01a33e5dbac5ccf972b458f86bc68d4cdc59e8abcb147f12d000720aca84`.
Aggregate CSV SHA256: `84c02e4cea9afcb3f41b9dc3810f81f543a38af72f24180ffb8259cc85aee279`.
Date CSV SHA256: `c36ed8a0a7b5ab143f6893aef6834702471191ba1dff58bce874dc529ce46c11`.
The source, five synthetic tests, both complete CSVs, original receipt and verification receipt are published together. The stored arithmetic cross-check used scipy.rankdata and numpy.corrcoef and matched all 26 defined date correlations within 1.12e-16. That is a mechanical check, not independent scientific review.

The six planned configurations were recorded through the existing TrialLedger owner on this PR branch before the audit. Its conservative 6502 floor is retrospective exposure accounting, not an independent-test count or corrected statistical significance. Default-main application remains false until reviewed merge. Original grade/price stores and completed crossover studies are unchanged.

## Decision

Do not treat the archived score as a calibrated probability or presume it adds positive selection value. Do not invert it based on this diagnostic. The next scientific test must use a frozen opportunity and execution contract, preserve current-version/chronology/coverage limits, and distinguish timing geometry from larger holding quality. Decomposition of the existing score is a hypothesis for later declared testing, not an already-proven cause of the negative association.

Historical replay source readiness remains a separate dependency. During this recovery the retained historical worktree was confirmed to omit the tracked SPY file via sparse checkout; the actual upstream diagnostic was `residual_alpha: no SPY market series`. Restoring historical input visibility is not replacing a price series with current data, changing signal logic, or waiving fidelity. Its proof and any remaining replay failure belong to the recovery continuation, not this archive statistic.

No trade, ranking, sizing, plan, forecast probability or customer-facing indicator was changed. This result is delivered as adverse descriptive evidence with all declared groups retained; success of this audit means a reproducible honest answer, not a favorable sign.
