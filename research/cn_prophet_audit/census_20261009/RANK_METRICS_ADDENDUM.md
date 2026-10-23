# Ranking metrics addendum

## Finding

**The accepted five-arm comparison has precision@6 of 42.4242% for score, 43.9394% for stored intel, 50.0000% for momentum, 50.0000% for reversal, and 46.9697% for quality.** These are 28, 29, 33, 33 and 31 positive H10 excess outcomes, respectively, from 66 selected observations per arm over the same 11 dates.

The existing analytical candidate archive was sufficient to complete the requested **frozen top-decile lift** and the **single intended intel tie-break check** without recalculating prices or outcomes. All 55 original arm/date counts, precisions and mean returns were first reproduced from the original frozen features. The accepted historical files remain unchanged. This addendum adds separate conditional ranking diagnostics; it does not change the original performance definitions or establish executable alpha.

## Source, selection rules and precision definition

All data remain pinned to Macro `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The additional input is a lossless subset of the existing `eligible_candidate_horizon_returns.csv`: `cn_prophet_v4`, horizon 10, and recorded featured candidates plus more-actionable candidates whose sole exclusion reason is `featured_cap` or `sector_cap`. Extraction retained missing features and all outcome statuses. It contains **1,488 qualified rows over 29 dates: 949 observed, 537 immature and two missing-exact-session outcomes**. The full source CSV has 30,582 rows; its V4 H10 slice has 2,917 rows. Extraction details and the original manifest are embedded in `rank_metrics_pool_input.json`.

The comparison then preserves the accepted `rankable_common_features` pool: all of `prophet_score`, `intel_score`, `ret_3m` and `quality_z` must be present, and the existing board/candidate vintage exclusions remain. This is a cap-qualified common-feature cohort, not the entire raw-eligible universe. Membership is sorted using frozen features and ticker before inspecting outcome status. Unknown outcomes never trigger replacement.

A hit means **strictly positive `excess_cc`** under the unchanged diagnostic: entry is the first benchmark-session close after the recorded board date, and exit is ten benchmark sessions later, with identical dates for stock and **CSI300 ETF proxy `510300.SS`**. This current-vintage close/close outcome differs from the separately reconciled production H10 open/HL2 and latched-fill conventions.

The original six-name arms use a maximum of four names per sector. Their primary orders are score descending, intel descending, three-month momentum descending, three-month reversal ascending, and quality descending; each uses ticker ascending for ties. The separate intended intel arm adds v3 score descending ahead of ticker. Top-decile selections use the same five original feature orders with **no sector cap**, as explicitly specified below.

## Accepted precision@6, independently reaggregated

Each date contributes equally to precision. Because every original selection has six names, mean daily precision also equals total positive outcomes divided by 66. The source field `average_precision` is a mean of daily precision@6; it is not average precision over a retrieval curve.

| Accepted arm | Positive H10 excess outcomes | Precision@6 | Same dates | K per date |
|---|---:|---:|---:|---:|
| Score | 28/66 | 42.4242% | 11 | 6 |
| Stored intel; ticker tie-break | 29/66 | 43.9394% | 11 | 6 |
| Momentum | 33/66 | 50.0000% | 11 | 6 |
| Reversal | 33/66 | 50.0000% | 11 | 6 |
| Quality | 31/66 | 46.9697% | 11 | 6 |

All five arms use these dates: 2026-08-20, 2026-08-21, 2026-08-24, 2026-08-25, 2026-08-28, 2026-09-01, 2026-09-03, 2026-09-07, 2026-09-08, 2026-09-09, 2026-09-16. Sources are `v4_review_rows.json` → `baseline_dates`, `historical_evidence.json` → `autopsy.baseline_comparison`, and the independently reconstructed memberships in `rank_metrics_addendum.json` → `accepted_daily_reconstruction`.

Every arm-count cell below is hits out of six. Pool counts include unobserved original members; decile K is fixed from that original pool size before outcomes.

| Date | Observed pool / original pool | Decile K | Score hits | Stored-intel hits | Momentum hits | Reversal hits | Quality hits |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026-08-20 | 35/35 | 4 | 1 | 5 | 4 | 3 | 6 |
| 2026-08-21 | 29/29 | 3 | 1 | 3 | 5 | 2 | 4 |
| 2026-08-24 | 26/26 | 3 | 3 | 5 | 5 | 4 | 5 |
| 2026-08-25 | 35/35 | 4 | 2 | 2 | 6 | 3 | 2 |
| 2026-08-28 | 49/49 | 5 | 2 | 4 | 2 | 3 | 3 |
| 2026-09-01 | 45/46 | 5 | 2 | 1 | 0 | 3 | 3 |
| 2026-09-03 | 24/24 | 3 | 4 | 0 | 2 | 5 | 1 |
| 2026-09-07 | 40/40 | 4 | 6 | 2 | 2 | 4 | 1 |
| 2026-09-08 | 34/34 | 4 | 2 | 2 | 0 | 2 | 0 |
| 2026-09-09 | 30/30 | 3 | 1 | 2 | 2 | 3 | 2 |
| 2026-09-16 | 18/18 | 2 | 4 | 3 | 5 | 1 | 4 |

## Frozen top-decile excess-return lift on identical complete pools

**K = ceil(0.1 × original common-feature pool size)**, with ticker ascending as the final tie-break and **no sector cap**. Selection is frozen before joining outcomes. Every reported arm uses exactly the same **10 dates**, and both the entire original pool and every frozen selected name have observed outcomes on those dates. K ranges from two to five, yielding **35 selected name/date observations per arm** and **320 full-pool name/date observations**. Six-name results are not relabeled as decile results.

The commission's primary **top-decile lift** is the equal-date-weighted mean of **decile mean excess minus the mean excess of the same full eligible pool**. Both sides use identical dates and the original unchanged H10 outcomes. Full-pool mean excess is **+0.2012 pp**. The selected and full-pool means below use equal date weights; their difference equals the mean of the paired daily differences.

| Frozen ordering | Decile mean gross excess | Same-pool mean gross excess | Mean excess lift | Descriptive paired date-cluster 95% interval for lift |
|---|---:|---:|---:|---:|
| Score | -0.1273 pp | +0.2012 pp | -0.3285 pp | [-2.8919, +2.1094] pp |
| Stored intel; ticker tie-break | +0.3263 pp | +0.2012 pp | +0.1251 pp | [-1.9153, +2.2050] pp |
| Momentum | +0.7389 pp | +0.2012 pp | +0.5377 pp | [-2.1966, +3.5272] pp |
| Reversal | +0.5087 pp | +0.2012 pp | +0.3075 pp | [-3.5201, +3.1882] pp |
| Quality | -1.1115 pp | +0.2012 pp | -1.3127 pp | [-2.2262, -0.2421] pp |

The intervals use **10,000 bootstrap resamples of the ten dates, with replacement, seed 20261009**. Each draw retains the complete selected-minus-pool date pair, and the same date-index draws are used for all five arms. Endpoints are the 2.5th and 97.5th percentiles with linear interpolation. These are **descriptive paired date-cluster intervals**: resampling individual dates does not fully address serially overlapping holding periods or recurring issuers, and the intervals are **not adjusted for the five-arm comparison**. They do not constitute a promotion or net-alpha test.

### Additional precision lift

Full-pool precision, weighted equally by date, is **47.1802%**. This supplementary precision-lift ratio divides selected precision by full-pool precision; the adjacent column gives their percentage-point difference. It is distinct from the commission's mean-excess lift above. Because decile K varies, the positive-count fraction is a pooled count and can differ from the reported date-weighted precision.

| Frozen ordering | Positive outcomes / selected observations | Date-weighted top-decile precision | Difference from same pool | Precision lift ratio |
|---|---:|---:|---:|---:|
| Score | 17/35 | 49.0000% | +1.8198 pp | 1.0386× |
| Stored intel; ticker tie-break | 18/35 | 51.0000% | +3.8198 pp | 1.0810× |
| Momentum | 18/35 | 55.3333% | +8.1531 pp | 1.1728× |
| Reversal | 21/35 | 56.8333% | +9.6531 pp | 1.2046× |
| Quality | 14/35 | 41.5000% | -5.6802 pp | 0.8796× |

The ten complete-pool dates are the accepted 11-date set with **2026-09-01 excluded**. That date has 45/46 common-feature pool outcomes; `601059.SS` is `missing_exact_session`. Its five top-six selections are complete, which is why it remains in precision@6, but it cannot supply a complete-pool comparison. The already excluded **2026-08-31** remains excluded: its original score top-six contains unresolved `601059.SS`. The rejected outcome-first method would have substituted `601360.SS`. No such substitution occurs here.

Per-date original pool sizes, frozen decile memberships, unresolved rows, and outcomes are stored under `frozen_top_decile.daily`; each arm summary also contains its ten paired return-lift observations and interval. The stored-intel decile retains the original ticker-only tie-break; the intended intel policy is assessed only in the single separately labeled top-six check below. No additional feature or parameter search was performed.

## Intended intel tie-break: one separate completeness check

Integrated source review clarifies the intended ordering as **intel descending, v3 score (`prophet_score`) descending, then ticker ascending**. The accepted stored-intel baseline uses **intel descending, then ticker ascending**. They must remain distinct labels.

Applying the intended tie-break to the same original common-feature pools changes membership on **0 of 11 dates**, replacing **0 selected name/date slots**; the ordered six-name list changes on **0 dates**. Both versions keep K=6 and the sector cap of four. There are **11 paired complete dates**. Newly excluded dates: **None**.

| Ordering on paired complete dates | Positive outcomes | Date-weighted precision@6 | Mean gross H10 excess |
|---|---:|---:|---:|
| Accepted stored intel → ticker | 29/66 | 43.9394% | -0.5631 pp |
| Intended intel → v3 score → ticker | 29/66 | 43.9394% | -0.5631 pp |

The paired change is **+0.0000 percentage points in precision**, and **+0.0000 pp in mean gross excess**. These are deterministic effects within this frozen historical cohort; they do not establish an expected future advantage or net trading return.

| Changed date | Removed from accepted selection | Added by intended tie-break | Positive outcomes, old → new | Mean excess change |
|---|---|---|---:|---:|
| No changed dates | — | — | — | — |

The full original and intended ticker orders, selected outcome receipts, and exclusion checks appear under `intended_intel_tiebreak_top6.daily`. This comparison neither rewrites the accepted stored-intel history nor claims to reconstruct the actual 24-name published board.

## Preserved cohort gates and limitations

The 29-date input is classified below using the existing vintage, common-feature, maturity and frozen-selection rules. Original rows are retained in the input even when their dates cannot enter a comparison. Full per-date counts, missing features and unresolved memberships are in `all_qualified_date_gates`.

| Gate | Qualified input dates |
|---|---:|
| `accepted_common_date` | 11 |
| `existing_vintage_exclusion` | 4 |
| `fewer_than_six_common_feature_names` | 5 |
| `incomplete_frozen_selection` | 1 |
| `no_observed_h10_outcomes` | 8 |

The existing evidence quarantines five vintage-discordant dates. Only four appear among these 29 qualified input dates; the already quarantined date with no qualified input rows is **2026-09-04**. The source quarantine is preserved in full, rather than inferred from only the dates present in the subset.

These statistics use current adjusted-price outcomes and date-only candidate records. Original publication-time snapshots and original price vintages have not been recovered; intraday execution, suspensions and terminal outcomes remain incompletely certified. Date and issuer overlap mean selected observations are not independent trades. Top-six and top-decile are separate ranking diagnostics with explicitly different K/cap rules. There is no portfolio weighting, financing, transaction-cost model, executable fill proof, accepted point-in-time backtest, net-alpha claim, or recommendation to promote an ordering. Small conditional-cohort differences do not alter the accepted report's conclusion about the lack of a demonstrated stable ranking advantage.

## Reproduction and hashes

Run the standard-library script beside its three pinned JSON inputs:

```bash
python3 rank_metrics_addendum.py
```

It verifies input hashes and the archive manifest chain, reconstructs all 55 original arm/date metrics and ten full-pool controls, then computes only the five prespecified top-decile arms, their fixed paired date-bootstrap intervals, and the single intended intel tie-break. It never reads prices or reruns the original grader. It writes only `rank_metrics_addendum.json` and this addendum. Accepted inputs are checked again after output generation.

| Input | SHA256 |
|---|---|
| `v4_review_rows.json` | `626aacda09bdef9ba6cd8bb01a3688e445228b48ce63d5496defb07ce0482830` |
| `historical_evidence.json` | `8b651cf4df19736f66a3cf184c5a47478ffe0bf2fc62a24bb5452c01b836e54d` |
| `rank_metrics_pool_input.json` | `1f6708ca0e8ec12d2983900f5d5d0313a9272e726730d7a91a220b4165bb6976` |

Original existing analytical CSV SHA256: `2db25adc73e9e5e5a934898edb4da6ae6852b43b096613acbe5724b8f622a1b3`. Original results manifest SHA256: `80f38bdd75cff63d87190081c4edf027bdce5d564dc23740f9203750b70209c4`. Addendum script SHA256: `da214bd49e4e7f37975463d6cf891696ae95e767ef112562f08826295f42ce39`. The extraction predicate, original CSV strings, source file sizes, full original manifest and all selection receipts make the new calculation reproducible without another host or vendor query. The accepted `HISTORICAL_EVALUATION.md`, `historical_evidence.json`, `v4_review_rows.json`, `autopsy.py` and `extend_audit.py` were not modified.
