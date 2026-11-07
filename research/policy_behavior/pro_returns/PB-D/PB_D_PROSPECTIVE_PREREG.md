# PB-D prospective preregistration — v1.0

Operation `PB-D-T2-EVENT-QUALITY-20261007`. Status: **FROZEN_DESIGN_NOT_ENROLLED; ZERO SIGNAL AUTHORITY**. No prospective observations were collected by this commission. Freeze identity is this file's blob plus the containing final return commit and the label-spec blob. The owner must issue a future activation receipt before the first affected decision cut. This is a reproducible research design, not a registered clinical trial, accepted production contract or validated trading rule.

## 1. Question, hypothesis and estimand

The primary question is whether **fresh, verified material economic evidence with at least two independent originating roots** predicts a larger H5 SPY-relative return among first T2 episodes, conditional on raw attention and observable technical/calendar context.

Let `Q` be the gated issuer-level quality exposure defined in `PB_D_EVENT_QUALITY_LABEL_SPEC.md`: complete coverage and resolved materiality/fresh-root status first; then Q=1 if any focal event satisfies both predicates, Q=0 otherwise. Unresolved records are unknown. Primary inference compares Q=1 with known Q=0 within T2. Materiality without two roots, raw attention alone, old fundamental context and missing evidence are not interchangeable.

For each eligible matched date d, let g[d] be the mean within-pair difference in H5 SPY excess between Q=1 and Q=0 T2 issuers. The primary parameter is the **equal-date mean of g[d] over dates with eligible pairs**. H0: this incremental mean is zero; use a two-sided 95% interval and require a positive lower bound for a research-positive result. A +2 percentage-point increment is the prespecified planning effect of practical interest, not an estimate derived from a validated sample.

This is an observational, conditional prediction estimand. It does not identify the causal effect of news, prove superiority to all alternative technical definitions, or describe issuers omitted from the published board. It tests the joint quality definition beyond matched raw attention. The separate contribution of materiality and root count is secondary.

## 2. Population and technical definition

Use the existing **U.S. `us_prophet_v3`, buy-lane published board population**, without adding names, changing selection/caps or modifying runtime logic. Snapshot every admitted board receipt and its source/configuration versions. The effect is conditional on this population and its existing eligibility/ranking selection. A pre-cap or market-wide population would require a separately frozen study and must not be silently substituted.

An eligible technical observation is an actually emitted, valid T2 classification from the existing owner, not a historical reconstruction using future bars. Lock the reference implementation to `engine/confluence_tiers.py` blob `004eda921766922e146d35acc6ee2bc646e96854` and `engine/signal_gate.py` blob `cccf77910f875925910e5adda14bbb33d6dc942d`, as inspected at [the frozen source](https://github.com/mastermindx-market-intelligence/macro/tree/2f2feec4851b45636f63a48ec61e6f0b02b8118a/engine). The behavior includes:

- `abs-session-2026-08-06` anchors; RSI14; MACD14/60/5; StochRSI14/3/3; 80/20 bounds; confirmation window eight native bars; RSI below 65; freshness of two native 2D ticks.
- A 2D MACD-up-cross event plus recent 3D Stoch-up within eight native 3D bars; confirmation from a prior completed weekly RSI/MACD bull state or a 3D stochastic-D visit below 20 within the relevant eight-bar window.
- T2 active age at most two **native 2D ticks**, with long-bias and existing topped veto; T1 takes cascade precedence. Preserve provisional trailing 2D/3D buckets and disclosed young-history null/fail-open behavior. Preserve the U.S. gate's existing unlatch behavior.

The exact implementation and observed inputs govern where prose is incomplete. No new closed-bucket requirement, alternative T2 threshold, future full-tape replay, event latch or entry permission is introduced. Record the native event ID/date, active age and all required state. If the actual emitter cannot supply or attest those inputs and version, quarantine it; do not run an unapproved surrogate. If technical semantics or board-population version change during enrollment, end that version's cohort before the affected observation and issue a prospective amendment for a separate era.

## 3. Observation clock, first episode and entry

Decision cut is **09:15 America/New_York on each U.S. exchange trading day**. Use the exchange calendar, including holidays and early closes, and store the UTC equivalent. The board receipt and prices used for T2 must correspond to the immediately preceding completed U.S. regular session and must have been observed by the cut. Store board as-of time, generation time, ingestion time, config digest and price-source vintage separately. A date-only label is not an intraday receipt.

Admit the first eligible emitted T2 observation for each canonical issuer in this cohort, irrespective of whether its event-quality classification is positive, negative or unknown. This is **filter to T2, then take the first observation per issuer**. Do not take first-any-tier and filter afterward; do not wait for the issuer's first favorable news or first complete-quality observation. Once the first technical observation is admitted, later daily echoes cannot supply a second primary observation, even if evidence arrives later. Keep later episodes only in the designated repeated-episode sensitivity ledger.

All event sources, root/publication clocks, reviews and adjudication must be available by the cut. Material information and both independent supporting roots must contain genuinely new publicly available information within `(cut[d−3], cut[d]]` and must also have been locally observed by cut[d]. Late ingestion of older public information is not a fresh root. Both exposure groups use the same coverage gate. Labels completed after the cut are unknown for the original primary record; later correction cannot backfill them.

Hypothetical entry is the **first scheduled regular-session close after the cut**, normally that day's close. H1 exit is the next regular-session close after entry; H5, H10 and H21 are 5, 10 and 21 completed trading sessions after entry. This matches the discovery's next-as-of-session close convention only when the preceding-session board receipt satisfies this prospective cut. Do not assume a same-day open or signal-date close fill. A halted or unpriceable entry is marked unfilled and retained in the enrollment accounting, with no delayed discretionary replacement. This convention is a measurement assumption, not an executable fill or entry-authority claim.

Primary entry and exit use a single declared corporate-action-consistent adjusted-price convention across issuer, SPY and mapped sector benchmark. Freeze the benchmark mapping at cut. Record splits, dividends, symbol changes, delistings, price-provider revisions and missing data explicitly. Historical use of an `adjusted` flag is not sufficient certification of future prices. Any vendor or corporate-action convention change requires a versioned prospective amendment before affected observations.

## 4. Exposure cells and aggregation

Freeze the nine requested reports below. They are overlapping descriptive views, not nine independent experiments. Publish their overlaps and unknown counts. One issuer contributes once to the primary cohort; one event carrying several tags is not multiplied.

| Report | Definition within first T2 observations |
|---|---|
| T2 alone | Complete coverage; raw attention false; materiality false for all reviewed events |
| T2 + raw attention | Legacy-compatible retained-item burst A=true, independent of sentiment or quality |
| T2 + material event | Any adjudicated `VERIFIED_MATERIAL_EVENT=true` |
| T2 + independent fresh evidence | Primary Q=1: material event and two fresh independent admissible roots in that focal scope |
| T2 + expectation change | Any `EXPECTATION_CHANGE=true`; report baseline type and direction |
| T2 + strategic option | Any `STRATEGIC_OPTION=true`; retain funding, milestone and falsifier |
| T2 + government link | Any `GOVERNMENT_LINKED=true`; retain legal/action status and direction |
| T2 + financing link | Any `FINANCING_LINKED=true`; retain conditionality and dilution/liquidity mechanism |
| T2 + syndicated burst | A=true and a reviewed `SYNDICATED_SINGLE_ROOT=true` focal event |

For A, preserve the existing compact-feature meaning `n_recent >= 3` after its existing filtering/deduplication/top-item retention, and record its input version and coverage status. Do not silently replace it with novelty-z, a new window or root count. Missing provider/ticker coverage gives A=unknown prospectively, even if the legacy runtime represents absence as false. A is not a positive-sentiment requirement. Do not impose an unregistered favorable-event-direction filter: the primary definition is direction-agnostic, with direction recorded for descriptive interpretation.

Secondary Q comparisons use the same reviewed label gates. Report materiality versus attention-only, and independent roots versus single-root material events. Do not pool government, financing and strategic tags into an after-the-fact preferred score. A sparse cell receives counts, effect estimates and uncertainty, not a new threshold or an automatic merger with a better-performing cell.

## 5. Matching and comparison populations

Primary matching is one Q=0 control per Q=1 treated issuer, without replacement, requiring exact equality of decision date, frozen sector, A state (true/false), and native T2 age (0, 1 or 2). Both must be first T2 observations admitted on that cut, have complete primary quality/attention/technical coverage and a valid common benchmark mapping. Unknown tiers or ages are not certified controls.

Perform matching before outcomes, using SHA256 of `operation_key|cohort_id|canonical_issuer_id` to order both treated and controls within each stratum; pair first with first, second with second, and so on. Freeze pairs in the decision receipt. More treated than controls leaves unmatched treated records; excess controls remain unused. No reuse across dates or issuers, no future widening of strata, no search for closer returns. The primary matched-support fraction is matched Q=1 divided by all otherwise eligible, fully covered Q=1 records; publish reasons for unmatched exposure. Primary estimates apply to this common-support subset.

Use equal-date g[d] weighting as specified above. Also report the equal-pair mean, clearly labeled as a different weighting. Entry status is recorded but not an eligibility condition. Matching on existing `entry_status` is a prespecified sensitivity, with an explicit warning that it may be downstream of technical/market variables. Never relabel the whole cohort as actionable trades.

Only original pairs with both valid H5 outcomes enter the primary point estimate. Exclude an incomplete pair as a whole; never rematch it after observing outcome availability or returns. Dates with no complete pairs are inactive in that estimate. Preserve all original pairs for missing-outcome scenarios. Outcome completeness is the number of original pairs with both valid H5 legs divided by all original frozen pairs, including unfilled pairs.

Required comparisons/sensitivities are:

- First-T2, no-news/attention-false T2, same-date T2 controls and same-date/sector controls, alongside the stricter primary matching. Relaxed matching is descriptive, not a replacement for a failed primary analysis.
- Leave one issuer out of **both** treated and control pools; leave INTC out; leave one matched date and one sector out; report the largest concentration and support loss. Recompute matching deterministically after each omission and label the changed support.
- Event-root deduplication and common-root sensitivity. If one originating event affects several issuers, retain the common root ID; report a secondary estimate selecting the lowest-hash issuer per root-connected component without future-outcome choice.
- Repeated T2 episodes as a secondary ledger only. One episode starts at a new native event identity; daily repeats are not new episodes. Do not count another issuer episode until the prior 21-session outcome window is complete. This sensitivity clusters by issuer and calendar blocks.
- Calendar-quarter and technical-version era reports; no pooling with the July confluence era or this discovery cohort. Historical era comparisons remain separate diagnostics.
- A **valid first-T1 comparator**, with the same receipt clock, Q labels and first-within-T1 rule. Missing tiers are excluded from certified comparisons and remain in the quality ledger. Report T1 Q effects and the difference in Q effects between T2 and T1; do not call all unclassified/not-T2 rows T1.

The formal interaction is `(mean T2,Q1 − mean T2,Q0) − (mean T1,Q1 − mean T1,Q0)` on dates/sector/attention support common to all four cells. It is a secondary estimand. It is not the primary within-T2 contrast, and it does not prove causal specificity. An issuer appearing once in each tier is linked across the four-cell analysis for dependence accounting.

## 6. Outcomes and path definitions

Let E be entry close and C[h] the adjusted close h sessions later. Absolute simple return is C[h]/E−1. SPY and sector excess subtract the benchmark simple return over the identical entry/exit timestamps; they are arithmetic differences, not separately independent wins. A positive outcome is strictly greater than zero. Report absolute, SPY-relative and sector-relative results at H1/H5/H10/H21, including means, medians, positive counts, uncertainty and maturity denominators.

Primary endpoint is the matched **H5 mean SPY excess increment**. On identical complete pairs with the same entry/exit timestamps, SPY subtraction cancels between issuers. Exact sector matching also makes sector subtraction cancel. The primary mean absolute, SPY-relative and sector-relative increments are therefore algebraically identical; report them for interpretation, never as three corroborating tests. Individual cell means and positive-rate outcomes need not coincide.

Fixed secondary endpoint order is H5 SPY-positive rate difference; H10 SPY mean increment; H21 SPY mean increment; H5 clean-liftoff rate difference. Use Holm adjustment across these four secondary endpoint tests if tested inferentially. All other paths, tags, directions, T1 specificity and subgroup results are descriptive unless a later independent preregistration allocates confirmatory error to them. Do not promote a significant unplanned cell after a null primary.

For each horizon h, using aligned corporate-action-consistent OHLC only in sessions strictly **after the entry close**:

- MFE[h] = max(0, max(high[j]/E−1)), j=1..h. MAE[h] = min(0, min(low[j]/E−1)), j=1..h. No pre-fill intraday high/low is included. Preserve close-only analogues under separate names.
- Close peak-to-trough drawdown[h] = minimum of C[j]/max(E,C[1],...,C[j])−1. This is different from minimum return from entry. Report both where available.
- Freeze ATR20 at the cut as the arithmetic mean of the last 20 completed-session true ranges, each `max(high−low, abs(high−prior_close), abs(low−prior_close))`. This is a research scale; it does not alter T2.
- Clean liftoff at H5 is true when the path first reaches E+ATR20 before E−ATR20 and H5 closes above E. It is false when an unambiguous path fails that definition. If both barriers first cross within the same daily bar and intraday ordering is unavailable, label unknown; do not infer ordering from the close. Missing ATR/path data is unknown.
- Freeze B20 as the maximum high of those 20 completed sessions. The failed-breakout subset is defined at entry by E>B20. Failure is any subsequent close through H5 below B20−0.5×ATR20. Other observations are not applicable, rather than nonfailures. This auxiliary breakout definition is separate from technical T2 eligibility.
- An H5 responder has H5 SPY excess >0. Persistence is the fraction of those responders still SPY-positive at H10 and H21, with fully matured denominators. Report the later mean and change in cumulative return, plus reversal fraction (later SPY excess <=0) and post-H5 drawdown.

Gross returns are primary to preserve a clear measurement estimand. Report fixed round-trip cost deductions of 10, 25 and 50 basis points as scenarios, never as measured execution costs. Real capacity, spreads, slippage, borrow, market impact and achievable fills are outside this study. A positive gross result does not establish positive executable returns.

Equal fixed cost deductions cancel in a paired mean increment just as shared benchmarks do. These scenarios show individual cell net-return and hit-rate sensitivity; they do not identify differential trading costs between exposure groups.

## 7. Enrollment length, n-floor and missingness

Activation must record an immutable cohort ID, first cut, board/config/price/label versions, authorized owner, available source/annotation coverage and the exact files' hashes. Begin only after a prospective source/clock dry run passes; dry-run observations are excluded from this confirmatory cohort and cannot be selected by their returns. The dry run is an implementation acceptance check, not authorization granted by this document.

Enroll for **252 consecutive U.S. trading sessions**, then wait 21 additional sessions for the last outcome to mature. Do not stop early for favorable performance, extend until significant or inspect return-by-cell dashboards during enrollment. Coverage, label disagreement and count dashboards may be examined without cell outcomes.

The research advancement floor is **at least 200 Q=1 first-T2 issuers paired with 200 distinct Q=0 control issuers, with both H5 outcomes valid in every counted pair**, at least 50 complete-pair decision dates, representation in all four successive enrollment quarters (four fixed 63-session blocks), and at least 70% primary matched support. These are minimum breadth/support conditions, not a declaration of 80% power. The strict quality definition may not produce that many events in one year. If the fixed cohort misses a floor, publish an underpowered result and do not widen the definition. A future additional cohort requires a new prospective receipt and must preserve the first cohort as a completed result.

For a future inferential four-cell specificity claim, require at least 200 observed issuers in **each** T2/T1 × Q cell on common support and a separate design-adequacy review; the approximate 5-pp-SD interaction calculation is about 197 per cell before dependence. These are necessary conditions only. This protocol's interaction remains descriptive even if those counts are reached: inferential status still requires a separately frozen, prospective error allocation, matching/weighting and issuer-linked dependence plan before the affected cohort, as specified in Section 6. A review after its outcomes cannot make it confirmatory.

Record every technical first observation before quality/matching/outcome exclusions. Publish the flow from observed board to first T2, coverage known/unknown, Q0/Q1, matched/unmatched, filled/unfilled, mature/pending and price-valid/missing. At cohort close require at least 80% complete primary exposure coverage among first T2 records and at least 95% mature valid H5 outcomes among matched pairs; otherwise no research-positive classification. These are prespecified operational gates and do not prove missingness is ignorable. Report coverage by date, sector and A/Q where ascertainable, and show unfilled/missing-outcome counts separately by exposure.

Pending horizons are right-censored, never failures. Halts, delistings and missing benchmark prices are never silently dropped as winners or treated as zero return. Seek the prespecified price/corporate-action owner resolution; if unresolved, report missingness and prespecified adverse observed-range imputation scenarios (missing treated H5 SPY excess assigned the worst observed cohort H5 SPY excess and missing controls the best, then vice versa; retain known legs and original pairs). These are sensitivity scenarios, not identification bounds or recovered actual returns: outcomes beyond the observed range remain possible. A missingness-sensitive conclusion cannot advance.

## 8. Uncertainty, multiplicity and decision rule

Historical IID binomial and Fisher calculations are discovery illustrations. For the future primary mean, form a full 252-session vector of date-level g[d] and an active-date indicator, preserving each date's entire matched cross-section. Use a circular moving-block bootstrap with block length 21 sessions, 10,000 draws, and NumPy `Generator(PCG64(2601007))`. In each draw sample `ceil(252/L)` start indices uniformly with replacement from 0..251, append each contiguous L-session block with indices modulo 252, then truncate to 252 sessions. Repeated sampled dates contribute with their sampled multiplicity. Estimate each draw as the mean over its active dates, not with no-pair days counted as zero returns. A draw with no active date is invalid, never zero.

Report the two-sided percentile 95% interval using NumPy's `quantile(method="linear")` at .025 and .975. Also run L=10 and L=42, restarting the same declared generator/seed for each L; they cannot replace the primary choice. Each calculation must have at least 9,900 valid draws out of the fixed 10,000 and finite interval endpoints; otherwise mark inference inconclusive. The research-positive classification additionally requires lower interval bounds above zero for all three lengths. These fixed diagnostics replace discretionary judgments about a favorable interval. Publish the analysis implementation, dependency versions and a synthetic known-result dry-run receipt before enrollment, and publish actual valid-draw counts with the final analysis. These gates do not certify true 95% coverage.

Each tested secondary endpoint uses the same equal-date statistic on original frozen pairs with both endpoint values known; no outcome-driven rematching. H10/H21 use complete later-return pairs. Clean-liftoff uses pairs whose two labels are true/false, excluding unknowns as whole pairs. If a secondary endpoint has fewer than 200 complete pairs, fewer than 50 active dates, under 95% endpoint completeness or fewer than 9,900 valid primary-L bootstrap draws, report it descriptively and assign p=1 for the fixed four-member Holm family. Missing/unavailable endpoints stay in that family rather than reducing its size.

For eligible secondary tests, reuse the L=21 sampled calendar blocks and compute the endpoint's estimate theta and bootstrap replicates theta*. The approximate two-sided centered-bootstrap p-value is `(1 + count(abs(theta*−theta) >= abs(theta))) / (1 + valid_draw_count)`. Apply Holm's step-down adjustment to the four p-values at family alpha .05. This is an approximate null-centered bootstrap test, not an exact randomization p-value and not an inversion of the primary percentile interval. The primary interval and research classification remain the rules above. All unallocated comparisons remain descriptive.

This procedure assumes enough approximately stable calendar blocks; it is not exact randomization inference. Related issuers/roots, persistent sector shocks and nonstationarity can defeat that approximation. Primary issuer uniqueness and within-date pairing reduce some dependence but do not remove it. Show issuer/root concentration and omission sensitivity; for repeated/four-cell data preserve issuer links as well. Do not permute observational exposure labels and claim randomized exactness. Cluster limitations follow [Cameron and Miller](https://cameron.econ.ucdavis.edu/research/Cameron_Miller_JHR_2015_February.pdf); permutation qualifications follow [Chung and Romano](https://arxiv.org/abs/1304.5939).

A **research-positive H5 result** requires all coverage/n/support/bootstrap gates; the primary and both fixed sensitivity intervals wholly above zero; point increment at least +2 pp; no sign reversal of the estimated increment after any one issuer or INTC omission; no conclusion dependent on missing-outcome sensitivity; and no material unresolved timing, root, price or version audit failure. Failure of an adequacy gate gives `INCONCLUSIVE_UNDERPOWERED_OR_INVALID`, not proof of no effect. An adequately measured primary estimate whose interval includes zero gives `PRIMARY_NOT_CONFIRMED`; a negative interval is adverse evidence. A positive primary interval failing a sensitivity requirement gives `PRIMARY_POSITIVE_NOT_ROBUST`. Report the entire interval, not just a category. A +2-pp point estimate with a positive interval does not establish that the true increment is at least +2 pp.

These conditions permit a subsequent research review only. They grant **zero automatic promotion**, including when all pass. The +2-pp target, matching bins, primary definition, path thresholds, cell aggregations and stopping horizon cannot be tuned against accumulated outcomes. Other fresh-acceptance definitions require a new independently frozen comparison; this trial does not select the best T2 variant.

## 9. Correction, amendments and no-go conditions

Preserve original as-known receipts and append source corrections with first-known timestamps. The primary exposure remains the original decision-time label; corrected-truth analysis is separate. A clock violation or invalid mapping is quarantined with its audit trail and sensitivity, not silently relabeled. Data errors affecting the planned inference require an integrity ruling with the original result retained.

Log amendments by commit, reason, old/new rule, author, timestamp and the first affected future observation. An amendment is prospective only if committed before that observation and without access to affected outcomes. An amendment after outcome access creates a new exploratory analysis or a new cohort, not a rewritten preregistration. The confirmatory/exploratory separation follows [Nosek et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC5856500/).

No promotion discussion is supported by retrospective relabeling, substituted synthetic earnings clocks, unversioned manager grades, missing root lineage, date-only freshness, silently changed board/T2 logic, outcome-selected cells, independent-trials claims from repeated rows, a failed primary rescued by an unplanned horizon, inadequate support or unstable prices. Even a clean positive trial would still require independent replication, execution/cost assessment and explicit owner authorization before a production proposal. This commission neither starts enrollment nor creates an automated collector, event store, runtime consumer or signal.
