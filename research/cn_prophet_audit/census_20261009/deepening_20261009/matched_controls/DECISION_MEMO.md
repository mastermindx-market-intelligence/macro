# Matched controls, dependence and a feasible acceptance design

## Decision

**The previously unexecuted matched-random comparison is now complete for its identifiable historical support.** The original featured top six do not outperform the exact expected sector/liquidity-matched random control in the nine fully supported dates: selected minus control is **−0.1081 percentage points** of gross H10 benchmark excess. Eight further matured dates cannot support a distinct six-name matching. This resolves a factual gap in the first commission; it does not repair the original point-in-time or execution limitations.

The most useful implementation conclusion is to separate a correctness release from a claim of better investment selection. The current archive can verify publication identity, eligibility, execution labeling and real ledger integration. Its temporal span and matching support cannot certify a small expected-return improvement. A final handoff should contain a working prospective evaluation contract and a frozen challenger test, rather than requiring a short implementation pilot to manufacture an alpha result.

All numbers below come from [MATCHED_CONTROLS_RESULTS.json](MATCHED_CONTROLS_RESULTS.json), whose exact matching arithmetic is checked independently in [VALIDATION.json](VALIDATION.json). The [fixed design](DESIGN.md) was written before these new calculations. It is a retrospective design freeze, not a claim that the already-examined historical data were an untouched preregistered trial. Two calculation-reporting refinements are disclosed in [AMENDMENTS.md](AMENDMENTS.md).

## 1. The matched control that was missing

For each original selected slot, alternatives had to have the **same recorded sector** and **0.5–2.0 times the selected name's positive recorded ADV**. All six originally selected names were excluded. Every draw uses six distinct alternatives and fills every slot. Membership, edges, full-assignment counts and feasibility were frozen before inspecting labels; all receipts are retained in [FROZEN_MATCHING_RECEIPT.json](FROZEN_MATCHING_RECEIPT.json).

The random policy is uniform over valid complete slot assignments. Several assignments may correspond to the same unordered portfolio, so the policy is not uniform over unique unordered portfolios. Exact inclusion counts provide the main expectation; 10,000 seeded draws provide the conditional selection distribution. Their tail fractions are not causal or exchangeability-valid p-values.

| Original featured comparison | Same sector and 0.5–2× ADV | Same sector only, declared sensitivity |
|---|---:|---:|
| Matured original dates attempted | 17 | 17 |
| Dates with every slot individually matchable | 9 | 14 |
| Dates with a genuine complete matching | 9 | 13 |
| Dates with all original and matching-policy labels observed | **9** | **12** |
| Mean selected excess | −1.0295 pp | −0.4021 pp |
| Mean expected control excess | −0.9214 pp | +0.2847 pp |
| Mean selected minus control | **−0.1081 pp** | **−0.6868 pp** |
| IID-date descriptive 95% range | [−1.9497, +1.9104] pp | [−2.3761, +0.9873] pp |
| Five-session calendar-block range | [−1.6456, +2.5159] pp | [−2.3788, +1.1483] pp |
| Ten-session calendar-block range | [−1.5761, +1.4942] pp | [−1.5740, +0.2089] pp |

The original featured and broad-pool score top six are identical on these comparisons. Under the primary random policy, a random control's aggregate realized return is at least the selected return in **53.85%** of the sampled matching draws. This describes random selection on fixed outcomes; it is not an investment-success probability.

The nine primary complete dates all lie between August 18 and September 3, spanning only **13 benchmark admission sessions**. The wider seventeen-date population cannot be represented by extrapolating those nine means. With the eight infeasible comparisons retained, the full matured cohort's conservative precision-difference bounds are **−43.98 to +50.14 percentage points**. Unrestricted excess returns do not have a finite symmetric missing-support bound. The eight missing full matches are selection-support failures, not subsequently losing observations removed from the sample.

## 2. Complete matching changes what a baseline can claim

All nine dates identified as potentially feasible in the original 82-of-102-slot audit do have full matchings. That favorable result does not make per-slot checks sufficient. Other tested populations contain actual collisions. On August 20, the common-feature score selection gives every slot at least one alternative, but slots for **002240.SZ and 002466.SZ share only one distinct alternative**. One name cannot fill both. On August 21, three intelligence slots share only two distinct alternatives. The output records each exact deficient slot group.

Matching within the accepted eleven-date common-feature comparison has very little common support:

| Arm | Primary full-matching dates | Primary fully observed dates | Selected minus expected control on that limited support |
|---|---:|---:|---:|
| Score | 2 | 2 | −1.7296 pp |
| Stored intelligence | 2 | 1 | −0.2376 pp |
| Intended intelligence → V3 → ticker | 2 | 1 | −0.2376 pp |
| Momentum | 1 | 1 | −8.5207 pp |
| Reversal | 1 | 1 | +3.1479 pp |
| Quality | 2 | 2 | −2.1535 pp |

**There are zero dates on which all these primary comparisons are simultaneously feasible and fully observed.** The entries in this table must not be used as a ranker leaderboard. Sector-only matching creates only one date common to every arm. Even the direction of a large one-date result is an inadequate promotion criterion.

One positive finding is retained: in the declared sector-only sensitivity, reversal exceeds its matched random control by **+2.5423 pp across six supported dates**. Its IID-date range is [**+1.9623, +3.1873**] pp. The five- and ten-session resampling ranges also remain positive. This supports retaining reversal as a prespecified research challenger. It does not show liquidity-matched advantage, does not use the same support as the other arms, and spans only fifteen admission sessions. The five-session calculation has **168/10,000 zero-observation resamples**, explicitly retained in the receipt; its finite range is conditional on the other 9,832 draws. The original eleven-date reversal-minus-score comparison remains inconclusive under all fixed dependence checks.

The adverse quality result also remains visible. Sector-only quality minus matched control is **−0.9367 pp across seven supported dates**, while the primary liquidity-matched support has just two dates. Neither that conditional negative result nor reversal's conditional positive result resolves a universal comparison.

## 3. Missing labels cannot be fixed by resampling until something grades

On September 1, `601059.SS` lacks the required exact-session outcome. In the common-feature intelligence matching graph:

- There are **308** complete assignments.
- **170**, or **55.19%**, include that unresolved name.
- Only **138**, or **44.81%**, have all six control labels observed.
- The unresolved name's expected share of the six-name control is **9.20%**.

Drawing until six observed names appear would silently condition away more than half the intended matching policy. The full return comparison is therefore unresolved. Exact precision bounds remain possible; return scenarios at assumed missing excess values −20, 0 and +20 pp are labeled assumptions. Moving that one assumed excess from −20 to +20 pp moves the date's expected selected-minus-control comparison by **3.68 pp**. That sensitivity is materially larger than the proposed +0.25 pp hurdle.

The broad primary nine-date comparison does not contain this missing-policy outcome. The broader sector-only control does, with a smaller but nonzero inclusion probability. The records preserve both cases rather than applying one blanket label-completeness rule after drawing.

## 4. The archive contains few distinct return periods

The accepted V4 H10 close/close cohort reproduces exactly: **288 episodes, 21 admission dates, mean excess +0.1637383 pp**. It contains **249 distinct issuers**, 39 observations beyond the first issuer occurrence, and 35 issuers with repeated observations. Thirty-six same-issuer observation pairs overlap in their H10 return interval.

The 21 dates occupy **22 benchmark admission sessions**. Of 210 distinct date-window pairs, **135 overlap** in at least one return session. At most **three** date windows can be mutually nonoverlapping. This is a structural coverage result, not an estimate that statistical effective sample size is literally three.

| Descriptive resampling assumption | H10 mean 95% range |
|---|---:|
| IID admission-date clusters | [−0.4742, +0.8490] pp |
| Five-session calendar blocks, gaps preserved | [−0.5517, +0.8290] pp |
| Ten-session calendar blocks, gaps preserved | [−0.4565, +0.7205] pp |
| Entire issuer clusters | [−0.6654, +1.0332] pp |
| Ten-session calendar blocks × independent issuer multiplicities | **[−0.9951, +1.4154] pp** |

The crossed sensitivity standard error is about **1.82 times** the IID-date reference. The ten-session-only range is narrower than the IID-date range because this extremely short realized series does not identify long-run dependence reliably. That narrowing does not justify a shorter future trial. The crossed method is a sensitivity calculation, not a small-sample-valid two-way confidence certificate.

All ten disjoint entry-session phases were retained. Their means range from **−0.9838 to +1.5327 pp**, with five positive and five negative phase means; each phase contains only two or three date windows. Dropping the single most influential issuer, **301216.SZ**, reduces the original mean from +0.1637 to **+0.0118 pp**. Dropping the most influential date, September 9, reduces it to **+0.0279 pp**. No observation was removed from the headline result.

For the original common-feature daily challenger-minus-score comparison, fixed ten-session calendar-block ranges are:

| Challenger | Original mean difference | Ten-session sensitivity range |
|---|---:|---:|
| Intelligence, including exact intended tie-break | −0.2469 pp | [−3.0216, +2.0311] pp |
| Momentum | +0.3132 pp | [−3.7147, +3.9536] pp |
| Reversal | +0.8339 pp | [−0.1170, +1.6674] pp |
| Quality | −0.2689 pp | [−3.7966, +2.6047] pp |

All cross zero. Matching diagnostics with only one date have no estimated date uncertainty. Where a chosen circular block is at least as long as the entire available span, the output explicitly marks the resulting range as degenerate. A zero-width range from rotating the whole observed span is not evidence of certainty.

## 5. A +0.25 pp hurdle is not a ten-session release test

An acceptance hurdle of +0.25 pp means the uncertainty-qualified improvement must exceed +0.25 pp. Detecting +0.25 pp relative to zero is a different question. If the true improvement equals the hurdle, no finite sample provides 80% or 90% power to demonstrate a positive margin above it.

The following illustration uses the already-observed paired daily standard deviation, a 95% two-sided lower-bound convention, 80% power and the normal approximation. Numbers are **independent paired-date equivalents**, not independent stocks, guaranteed future market dates or fixed implementation schedules.

| Challenger | Observed daily paired SD | True effect +0.50 pp, margin +0.25 | True effect +0.75 pp, margin +0.50 | True effect +1.00 pp, margin +0.75 |
|---|---:|---:|---:|---:|
| Intelligence | 4.8118 pp | **2,908** | 727 | 324 |
| Momentum | 4.8141 pp | 2,911 | 728 | 324 |
| Reversal | 3.4026 pp | 1,454 | 364 | 162 |
| Quality | 5.0681 pp | 3,226 | 807 | 359 |

The full result includes 90% power, half/double SD scenarios and dependence multipliers of 1, 2, 5 and 10. These multipliers are scenarios; the eleven-date archive cannot estimate them reliably. Halving the true paired SD approximately quarters the requirement, which is why paired policies on identical opportunity sets and clear economic labels matter. Renaming hundreds of correlated stock rows as independent observations does not solve the problem.

These requirements are intentionally sobering. They do not mean correctness repairs should wait for years of returns. They mean a small alpha hurdle is a research objective whose evaluation design needs its own evidence budget. The calculation applies to the existing six-name gross close/close diagnostic; it is not a certified sample target for a 24-name executable policy.

## 6. Concrete instructions for the implementation owner

**Release correctness independently.** Exact publication/candidate/entry identities, correct stock/benchmark intervals, preserved original latches, lawful execution states and one real scheduled ledger roundtrip have deterministic acceptance conditions. Passing them earns a correctness release. It does not earn an expected-return claim.

**Keep one primary ranking experiment.** Freeze one challenger, its objective/horizon, eligibility, missing-source policy, concentration limits, abstention behavior, effect hurdle and net-cost assumptions before observing its prospective results. Use the same original candidate set and exact dates for champion and challenger. Preserve the other arms as labeled exploratory diagnostics. A primary direct paired policy comparison should not depend on a matched-random test that is unidentifiable for many original selections.

**Archive the random-control policy before outcomes.** Store the policy/version, original selected identity, candidate/feature generation, edge-graph identity, maximum matching size, complete-assignment count, seed, inclusion probabilities, unresolved-label mass and disposition. A graph that fills only five slots must not receive a six-name performance row. Do not drop an unresolved control from the sampling population or repeatedly draw until its result becomes observable.

**Use an instrumented pilot to learn variance and coverage.** Its purpose is to check real data flow, label completion, temporal/issuer concentration, support attrition and paired variance. Then fix a confirmatory chronological sample and decision procedure. Account for repeated looks and the number of evaluated challengers. The already-examined archive remains research data. A count such as sixty names is not a power guarantee; the number and variety of matured date blocks must be visible.

**Scale the offline matcher by sector.** The exact graph decomposes into disjoint sector components. The current sector cap limits each component to four selected slots. Count and sample each component, then multiply its count and combine its independent assignment draw. This produces the same uniform full-assignment policy without a monolithic `2^24` state space. The independent validator uses a different inclusion-exclusion formula to verify this factorization for **all 232 frozen cases**. Keep the matcher in existing offline evaluation ownership; no new runtime, service or production selection dependency is needed. Full-board extensions should serialize potentially large integer assignment counts without lossy JavaScript-number conversion.

**Retain the falsifiers.** The primary random-control result is unfavorable and inconclusive; the sector-only reversal result is positive but narrow; the adverse quality result remains adverse; exact intended intelligence tie-breaking changes nothing in the accepted historical six-name sample. The final implementation handoff should preserve all four findings. None supports treating an intelligence activation, a new formula or an attractive example as established investment improvement.

## Reproduction and evidence custody

From the repository root:

```bash
python research/cn_prophet_audit/census_20261009/deepening_20261009/matched_controls/analyze_matched_controls.py
python research/cn_prophet_audit/census_20261009/deepening_20261009/matched_controls/validate_matched_controls.py
```

The analysis requires NumPy; validation uses only the Python standard library. The actual runtime was Python 3.12 with NumPy 2.3.5. The default commands write only within this deepening subdirectory. To reproduce the analysis into a separate destination, copy `DESIGN.md` and `benchmark_sessions_input.json` there, pass that directory as `--out`, and pass the accepted docket directory as `--docket`.

The computation checks the unchanged hashes of all four accepted inputs, reconstructs all 55 original arm/date memberships plus the eleven intended-intelligence memberships, and reproduces the original 17-date/82-of-102-slot feasibility result. Forty small graphs were exhaustively checked inside the analysis. The separate oracle rebuilds all 232 edge/maximum-matching cases, checks sector-factorized counts independently, and enumerates **109,344 assignments** from ten important real graphs. No new price, outcome or vendor record was created. All historical publication, adjusted-basis, execution, regime-coverage and selection-support limitations continue to apply.
