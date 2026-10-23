# Matched controls and dependence: fixed analysis design

Recorded: 2026-10-09 23:34 UTC, before calculating new matched-control, dependence or power results. This is a transparent retrospective design freeze, **not a prospective preregistration**: the accepted historical findings and input outcomes already existed. Changes after computation must be recorded as amendments and may not silently replace this record.

## Purpose and scope

Resolve whether the original featured selections or the five already specified simple orderings outperform distinct-name controls with the same recorded sector and approximately the same recorded liquidity. Determine how little independent temporal evidence the H10 archive supplies and what that means for implementation acceptance. No factor search, new prices, new trading rules, production edit, original-result edit or claimed point-in-time repair.

Study source remains `3d90aad6d83152dfeeaf8345bc995826ac9d3139`. Inputs are the accepted qualified V4 H10 pool (all 1,488 rows, including unavailable and immature outcomes), accepted V4 episode/baseline records, accepted rank-metrics addendum, and accepted historical evidence. The only new source extraction is the benchmark's index from June 2026 onward, from the same pinned Git blob. All input bytes are hash checked. The analysis reads no external services after qualification.

## 1. Matching population and estimands

The primary candidate population is the existing cap-qualified cohort: `featured`, or `more_actionable` with `featured_cap`/`sector_cap`. Preserve the accepted five vintage-discordant date exclusions. One excluded date has no qualified rows, and must remain visible as such. Freeze source population and selected membership without reading outcome status or return values.

Two scopes are reported separately:

1. **Recorded featured and score, broad qualified pool.** Freeze the first six recorded featured names by lane rank/ticker; separately freeze the top six by V3 score/ticker under sector cap four. Evaluate every coherent date with enough pre-outcome names, including dates not yet matured. This scope resolves the old 17-date/102-slot feasibility audit. It is not an episode-based strategy.
2. **The accepted eleven-date common-feature comparison.** Preserve the same dates and same common-feature pool (`prophet_score`, `intel_score`, `ret_3m`, `quality_z` available). Reconstruct score, stored intelligence, momentum, reversal and quality top six with sector cap four. Also reconstruct intended intelligence → V3 score → ticker as a distinct, explicitly named arm; an unchanged tie-break is still reported. No new arm or thresholds are chosen after viewing these results.

For each date/arm, remove all six original selected names from the alternative population. An alternative may fill a selected slot only when recorded sectors match exactly and its recorded positive ADV lies in **[0.5, 2.0] times** the original slot's recorded positive ADV. A name may fill at most one slot; every slot must be filled. Missing sector or nonpositive/unavailable ADV cannot create an edge. Do not match on subsequent returns, outcome availability, quality, other latent exposure or future status.

One declared sensitivity removes the ADV band but retains exact recorded sector and all other restrictions. This measures the cost of the liquidity restriction; it is a different matching specification and cannot replace the primary result. No progressively loosened threshold search.

**Random policy:** sample uniformly from all complete injective slot-to-name assignments. A distinct portfolio may have more than one admissible slot assignment; consequently this is uniform over assignments, not uniform over unique unordered portfolios. Every draw is a full, without-replacement six-name control. Count assignments exactly with a candidate-by-slot-mask dynamic program, test against exhaustive small graphs, and compute exact inclusion probabilities and expected returns/precision. Use those exact moments as the central estimates. Ten thousand seeded draws quantify only the policy's conditional random-selection variability. Their tail fractions are descriptive, not causal or exchangeability-valid p-values.

Before outcomes, retain all edge counts, maximum matching sizes, unmatched slots, full-assignment counts and selected/alternative identities. Report the distinction between per-slot nonempty edges and genuine full matching. An infeasible six-slot graph has no matched six-name return. Partial assignments are not promoted to full controls.

## 2. Unresolved outcomes, unequal support and bounds

Outcome checks happen only after constructing each graph and freezing selected names. Do not replace a selected or matched name with an observed alternative. Count the fraction of complete assignments with fully observed labels exactly. The complete-outcome primary return comparison requires the original six labels and the entire support of the matching policy to be observed. If either fails, the original comparison is unresolved; any observed-assignment diagnostic is clearly conditional and cannot stand in for the full policy.

For unresolved returns, do not claim finite distribution-free two-sided bounds: stock upside and benchmark-relative returns are not bounded by a convenient symmetric number. Report unknown-name inclusion probability and sensitivity to the explicitly assumed missing excess values **−20, 0, +20 percentage points**. These are scenarios, not market/legal bounds. For positive-excess precision, missing outcomes have true finite bounds of zero or one. Preserve those bounds at the portfolio and original-cohort level.

Arm-specific complete matching supports may differ. Show each date set and intersection before comparing arms. Evaluate every feasible date in its original scope; compare orderings directly only on the intersection with complete outcomes under both policies. Full-cohort precision-difference bounds treat an infeasible or ungraded comparison as [−1,+1], retain its weight and expose how wide the missing-support bound becomes. Immature cohorts are displayed separately, never presented as observed losses or removed without a denominator.

## 3. Overlap, repeated issuers and influence

Reproduce the accepted 288-observation/21-date V4 H10 close/close episode mean before applying sensitivity estimators. Preserve all original episode outcomes and all existing economic limitations. The primary descriptive estimand is the original row-weighted mean; a separately labeled date-weighted mean is also provided. Use the pinned benchmark session index to place admission and entry/exit dates exactly.

1. Count same-issuer repetitions, overlapping date-label intervals, and the maximum number of mutually nonoverlapping ten-session date windows available by earliest-finish interval scheduling. A count of nonoverlapping windows is a structural coverage fact, not a literal statistical effective sample size.
2. Reproduce an IID-date resampling reference. Then resample **circular calendar blocks of 5 and 10 benchmark sessions**, retaining no-issuance sessions as zero-count dates. Concatenate enough blocks, truncate to the original calendar span, and calculate the ratio of total sampled return to total sampled observation count. Ten thousand draws, with fixed seeds; no block-length search based on favorable results.
3. Resample entire issuer clusters. As a deliberately conservative sensitivity, independently combine issuer multiplicities with the 10-session calendar block weights. Call these descriptive sensitivity distributions, not a small-sample-valid two-way-cluster confidence certificate. Report invalid zero-denominator replicates explicitly if any; do not hide their rejection rate.
4. Remove each issuance date and each issuer in turn; retain all leave-one-out means, sample losses and maximum influence. Do not remove an influential name from the headline estimate.
5. Divide dates into all ten phases of entry-session index modulo ten. Each phase's intervals share no positive-length return segment. Show every phase, names and dates; never choose the best phase. Nonoverlap still does not establish regime independence or remove issuer dependence.

Apply IID-date and calendar-block sensitivity to the four accepted challenger-minus-score daily differences on the same eleven dates, plus the separate intended-intelligence tie-break. Apply the same machinery to fully observed primary matching daily differences where enough dates exist. No cross-definition era pooling, current-price repair or portfolio-performance claim.

## 4. Prospective precision and power planning

Use each accepted paired daily-difference standard deviation as an **illustrative unstable planning input**, not a consistent long-run variance estimate. Present normal-approximation independent-unit requirements with a 95% two-sided lower-bound convention (`z=.975`) and 80%/90% power. Distinguish detecting +0.25 pp relative to zero from demonstrating an improvement **above** a +0.25 pp acceptance hurdle. A true effect equal to the hurdle has no positive margin and no finite sample size yielding the specified power.

For hurdle 0.25 pp, illustrate true effects 0.50, 0.75 and 1.00 pp. Formula: `n = ceil(((z_0.975 + z_power) * sigma / (true_effect - hurdle)) ** 2)`. These are independent date-unit equivalents, not independent-name counts. Show variance assumptions at 0.5×, 1× and 2× observed standard deviation, and illustrative calendar dependence multipliers 1, 2, 5 and 10. The latter are scenarios, not measured design effects or guaranteed calendar durations. Report observed block/IID standard-error ratios, but never use an unstable ratio below one to promise a shorter trial.

The implementation decision should distinguish: (a) correctness evidence that can be obtained with exact fixtures and a natural process cycle; (b) an instrumented prospective shadow pilot used to estimate variance and coverage; and (c) a frozen confirmatory comparison with sufficient new chronological evidence. The whole examined archive is research data and cannot become a holdout. One predeclared challenger and primary horizon, controlled repeated looks/multiplicity, original selection records, explicit abstention/coverage cost and net execution assumptions are required. No arbitrary 60-name count is a power certificate.

## Reproducibility and refusal conditions

All outputs go only to `deepening_20261009/matched_controls/`. Preserve input hashes, design hash, script hash, random seeds, full matching receipts, complete date gates and reconstruction assertions. The independent reviewer must reproduce graph counts/moments on exhaustive examples, original arm/date memberships, missingness treatment, intervals and planning formula. Any failed accepted-result control stops grading. Findings may be negative or unidentifiable; the final memo must retain those results and tell the implementation owner exactly which decisions they support.

All prior limits remain: non-certified historical first-publication timestamps, current adjusted price vintage, incomplete security status, gross close/close outcomes, overlapping returns, repeated issuers, short period, incomplete market regimes and no executable portfolio accounting. No causal attribution or strategy promotion follows from this exercise alone.
