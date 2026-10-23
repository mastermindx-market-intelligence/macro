# Independent matched-controls review

**Disposition: accepted for the stated retrospective research purpose, with one interpretation qualification.** I found no answer-changing arithmetic error in the matching, missing-label accounting, reported central effects, structural dependence counts, or illustrative power calculations. The full-cohort precision envelope must not be presented as an identified bound for a strict matching policy that has no valid assignment on eight of its seventeen matured dates.

This review was completed on 2026-10-10 UTC against the unchanged study pin `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. The matched-controls design, memo, amendments, analysis, validator and result arrays were read. Neither completed lab was edited. This directory contains independently authored executable evidence; it does not import or execute the producer's analysis or validator.

## Accepted findings

### 1. The assignment policy is coherent and its weighting matters

The declared distribution is uniform over complete **slot-ordered assignments of distinct alternative issuers**. A portfolio can receive several assignments and therefore more probability. The analysis's candidate-by-slot-mask dynamic program counts these assignments correctly: a candidate is either skipped or used in one permitted, currently unfilled slot. The conditional sampler selects those branches in proportion to their remaining completion counts. That yields uniform complete assignments.

The separate producer validator uses a genuinely different counting implementation: set-partition inclusion–exclusion plus sector factorization, and direct recursive enumeration for ten real graphs. Its `used` set prevents duplicate issuers within a draw; it does not deduplicate different slot assignments of the same portfolio. Its 109,344 assignments are an implementation-independent arithmetic check authored by the producer, not a separate human or agent review. This review supplies the latter without claiming to re-enumerate all 109,344 assignments.

The independent counterexample has two slots with neighbors `{x,y}` and `{x,y,z}`. Four valid assignments represent three portfolios with multiplicities 2, 1 and 1. With returns `x=0`, `y=0`, `z=10` pp, the uniform assignment mean is **2.5 pp**; the uniform unique-portfolio mean is **3.333333 pp**. Treating the policies as equivalent fails this executable case.

Sector factorization is valid because exact sector matching creates disjoint candidate sets. The full assignment set is a Cartesian product of sector assignment sets; multiplying the counts and drawing independent uniform component assignments preserves the declared distribution. A two-sector synthetic product and two real graphs verify this directly. For the September 3 featured primary graph, the component counts are **6 × 1 × 6 = 36**, despite 96 unconstrained slot combinations. The archive's six-slot arithmetic does not itself establish production performance for a larger board.

### 2. Missing assignment mass and missing portfolio weight are different

The independent oracle reconstructs neighbors from the original feature matrix, enumerates a Cartesian product and then rejects repeated names. It uses neither stored masks as the source of edges nor either producer counting algorithm.

For `accepted_common_features/intel_top6/sector_adv_0.5_to_2/2026-09-01`, this produces exactly **308 assignments** and **54 unique unordered portfolios**. The missing-outcome issuer `601059.SS` appears in **170 assignments**. Thus:

| Quantity | Independent result |
|---|---:|
| Probability a control assignment touches the missing issuer | 170/308 = 55.194805% |
| Assignments with all six labels observed | 138/308 = 44.805195% |
| Expected missing share of the six-name control | 170/(308 × 6) = 9.199134% |
| Full-policy expected return | Unavailable |
| Mean conditional on a fully observed assignment | −1.462509 pp |

The conditional mean cannot replace the unavailable full-policy mean. Drawing again until outcomes are observed would change the intended distribution. The result correctly leaves the full-policy return null, keeps the unknown probability mass, and labels finite-only summaries as conditional.

Assuming the one missing return equals −20, 0 or +20 pp gives selected-minus-control differences **+1.003439, −0.836388 and −2.676215 pp**. Raising the missing control return by 40 pp lowers the difference by **3.679654 pp**. The sign, six-name divisor, missing-label precision bounds and all per-slot inclusion counts match the frozen results. The separate 36-assignment complete case also reproduces the exact mean and population standard deviation.

### 3. The primary effect and all reported aggregate means reproduce

All sixteen aggregate rows were reconstructed from original return labels and fixed inclusion counts, with complete dates retained exactly as recorded. This is independent aggregation; it is not an independent re-estimation of every stored inclusion count.

The primary featured result has **17 matured opportunity dates, 9 fully feasible and observed comparison dates, and 8 infeasible dates**. Across the nine supported dates:

| Measure | Reconstructed value |
|---|---:|
| Selected mean H10 excess | −1.029524 pp |
| Expected random-control mean H10 excess | −0.921376 pp |
| Selected minus expected control | **−0.108148 pp** |
| Selected minus expected-control precision | +0.058160 in fraction units = +5.815983 percentage points |

Positive return differences favor the selected policy. Return effects are percentage points of H10 stock-minus-benchmark return, not raw decimal returns. Precision fractions must be multiplied by 100 when displayed as percentage points; the memo does that correctly. The different signs of return and precision are not contradictory because one measures magnitudes and the other only counts positive excess outcomes.

The six arms share **zero** complete common dates under sector-plus-ADV matching and **one** under sector-only matching. Their separate support means cannot be used to rank the arms on a common opportunity set. The positive sector-only reversal result and the original eleven-date reversal-minus-score result have different comparators and different date supports; they must remain separate findings.

### 4. Dependence and power warnings are proportionate to the evidence

The original H10 row matrix independently yields **288 observed episodes, 21 dates, 249 issuers, 39 observations beyond each issuer's first occurrence, and 35 repeated issuers**. There are **135 overlapping date-window pairs out of 210**, and **36 same-issuer overlapping pairs**. Exhaustive subsets find two nonoverlapping triples and no nonoverlapping quadruple, proving the maximum is three for these realized windows. That structural maximum is not a statistical effective sample size.

All ten phase memberships, their means, and leave-one-date/issuer means reproduce. The phases contain only two or three dates each. Different nonoverlapping phases still share a market period and may share issuers; nonoverlap does not certify independence.

A separately implemented direct calendar-index resample reproduces the sector-only reversal five-session case: **15 calendar sessions, six observed dates, 168 empty draws, 9,832 finite draws**, and finite-only percentiles **[1.594136, 2.805484] pp**. Preserving the nine gaps is material. Those percentiles condition on nonempty resamples and are appropriately described as sensitivity, not a calibrated confidence guarantee. The crossed calendar/issuer method was inspected rather than rerun in full; its multiplicity product is a descriptive sensitivity with too little temporal breadth to justify a general coverage claim.

All **90 power-grid rows**, their dependence multipliers and the separate +0.25-versus-zero examples reproduce from the original eleven paired-date memberships and outcome labels. The formula is:

`ceil(((1.9599639845 + z_power) × paired_sample_SD × SD_multiplier / (true_effect_pp − 0.25))²)`

For 80% power and the observed SD, true effects +0.50/+0.75/+1.00 pp require the reported independent-date equivalents: intelligence **2,908/727/324**, momentum **2,911/728/324**, reversal **1,454/364/162**, quality **3,226/807/359**. These are internally consistent normal-approximation illustrations using an unstable eleven-date SD. The memo explicitly declines to turn them into a release schedule, a forecast of actual calendar duration, or a calibrated target for a 24-name executable strategy. No correction is required to the formula or units.

## One qualification to carry into synthesis

**R1 — reporting semantics, not an arithmetic failure.** On eight primary matured dates there is no complete assignment. A uniform probability distribution over an empty assignment set does not exist. Therefore the strict matching policy's seventeen-date performance and precision comparison are unavailable; they are not merely missing labels of an otherwise defined policy.

`grade_case` inserts `[-1,+1]` for each infeasible date and the aggregate averages these with the nine defined comparisons. That arithmetic correctly produces **[−43.979774, +50.137873] precision percentage points**. Its interpretation is an intentionally loose envelope over arbitrary **hypothetical completions** on unsupported dates. It is not an identified bound for the strict full-cohort policy. The design disclosed the convention and the memo already distinguishes selection-support failure from missing losing observations, so this does not invalidate the nine-date result or block using the research package.

For downstream implementation or final synthesis, retain two distinct fields or their equivalent:

- `strict_full_cohort_status = UNAVAILABLE_NO_FULL_ASSIGNMENT_ON_EIGHT_DATES`, with the strict full-cohort estimate null.
- `hypothetical_completion_precision_envelope`, with the numbers above and the completion assumption explicit.

The review evidence includes this exact distinction and a Hall-failure fixture in which every slot has a neighbor but no full assignment exists. **Blocked interpretation:** describing this envelope as an identified performance bound for a defined strict seventeen-date matching policy. **Accepted interpretation:** using it as a conservative missing-support scenario while retaining the unavailable policy status and supported-cohort estimand.

## Executable evidence and integrity

Run from any working directory:

```bash
python /workspace/scratch/cb265ed3ed34/deliverable/research/cn_prophet_audit/census_20261009/deepening_20261009/reviews/matched_controls_review/independent_checks.py
```

The script requires the same NumPy already available to the producer; the verified runtime was Python 3.12.14 and NumPy 2.3.5. It writes only `REVIEW_EVIDENCE.json` beside itself. The terminal run passed **1,469 checks**, enumerated **344 real assignments** independently, and confirmed all reviewed original files and four accepted input matrices were unchanged before and after the calculation. `MANIFEST.json` records every input hash and the review artifact hashes. No production, vendor, cache, source-repository or completed-lab mutation occurred.

These checks evaluate the stated conditional retrospective comparison. They do not certify first-publication point-in-time availability, original price-vintage identity, execution, net costs, long-run statistical power, or new investment alpha. Those limitations remain the findings of the broader commission rather than claims resolved by this review.
