# Existing reader integration: exact reuse boundary

Continuation of Macro PR #9507. This is a source-grounded integration design, not activation, implementation, an amendment to the incumbent research protocol or permission to run its candidate/evaluator. It refines the source-readiness next action after the R2 package was initially verified.

## 1. An input preparer already exists

At Macro `3ab3382af89242c7b7fe8c65360bd883a7dd3504`, `engine/research_codegen/bridge.py` (Git blob `c23394e1436e136fd7f728a7d4c608b1a40e3bc5`) implements a narrow per-decision preparation interface:

- `PreparedIdentity`, lines 151–162, binds nine immutable research identities, including source/config/protocol/input-policy/runtime/evaluator hashes and original root.
- `PreparedDecisionInput`, lines 165–178, carries request/input bytes, cutoff, trailing session dates and completeness. It does not carry labels, file paths or raw capture images.
- `PreparedSyntheticInputs`, lines 190–202, binds prepared decisions and the owner's fixed schedules. Its documentation explicitly says structural admission is not authentication or generation/execution/evaluation authority.
- `_capture_input`, lines 296–381, validates receipt/image identities and clocks, requires chronological session bindings, and only emits eligible observations available by the decision cutoff.
- `prepare_synthetic_inputs`, lines 540–585, reuses the incumbent manifest, owner, accounting, source-exclusion and schedule checks without executing candidates or releasing labels.

The bridge is explicitly **synthetic engineering only**. Its `_FLAGS`, lines 40–44, keep generation, execution, evaluation and authority disabled and scientific acceptance unqualified. The existence of this useful interface is not a live-reader or scientific-admission receipt.

Do not build a second input service, snapshot store, experiment queue or identity scheme to solve the allocation study. Preserve this boundary and qualify the exact new study adapter through its owner.

## 2. Direct reuse would test a different experiment

| Dimension | Inspected incumbent contract | Proposed sector-allocation baseline | Required treatment |
|---|---|---|---|
| Cohort | Nine fixed nodes and exactly nine source dispositions, `_positions` lines 384–397 | Eleven sector instruments plus SPY and BIL | Distinguish selected assets from benchmarks; preserve complete source dispositions for all thirteen inputs rather than relabelling nine inputs as the full study |
| Schedule spacing | Anchor plus `26 * calendar_index`, lines 414–417 | Twenty-session sequential holding blocks | A new protocol-specific schedule adapter; do not change the incumbent experiment's fixed cadence |
| Decision cutoff | Next session at 09:00 America/New_York, lines 485–489 | Next session at 08:00, as selected in TARGET_SCOPE_AND_BASELINES_R1 | Retain the study's own exact clock and reject a foreign cutoff; an hour shift is a material information-set change |
| Price prefix | `trigger_index-62` through trigger inclusive; exactly 63 observations, lines 493–498 | A 63-session return from t-63 to t, requiring 64 prices | Preserve the distinction between observation count and elapsed return intervals; no silent lookback substitution |
| Availability meaning | Durable/current capture and completed receipt read, not original historical vendor publication, lines 326–375 | As-known current decision, or explicitly reconstructed historical development | Retain original evidence meaning; a newly captured history cannot establish historical publication times |
| Runtime permission | Structurally complete but disabled synthetic preparation | A future qualified reader and separately admitted study | Do not set an enable flag simply because the types line up |

This is **not a bug finding against the old experiment**. Its nine-node, 26-session, 9 a.m., 63-price specification may be correct for its own target. The defect would be transplanting that contract into a different target without an explicit adapter and validation.

The source corpus also has a different `ResearchEstimate` identity with eleven fields. Its field count must not be confused with this bridge's nine identity fields or the nine-sector input population; those are three unrelated contracts.

## 3. A concrete observation-count witness

A pure arithmetic check used session-index t=100. The existing prefix `range(t-62, t+1)` has 63 prices and spans 62 return intervals. The required 63-session return uses `range(t-63, t+1)`, 64 prices. With invented prices `price[i]=i+100`, the former computes 0.4492753623188406 and the latter 0.45985401459854014. Both counts and the unequal returns were asserted in the active turn.

No market prices, production imports or candidate execution were used. This check establishes the off-by-one integration risk, not empirical performance. Do not publish a 62-interval result under a 63-session label.

## 4. Capture activation alone is insufficient

At the same pin, `collectors/yahoo.py::YahooAdapter.fetch`, lines 128–155 (blob `ac53401672ab0bddc5507bc5aabc52d74967332f`), chooses `period="max"` only with `full_history=True`; normal collection requests `period="1mo"`. The bridge's usable observations come from the **provider-return image**, not a substitution of the entire merged cache.

A normal one-month provider window cannot supply the required 63-price incumbent prefix, much less the allocation study's 64-price return prefix. Capturing that normal window faithfully and enabling a reader would therefore still produce insufficient history. Quietly taking older merged-cache rows would change the provenance that the capture contract explicitly protects.

Do not solve this by running `full_history=True` across the collector's entire ticker configuration: the inspected source obtains all configured tickers and then batches them. That would be a broader acquisition with its own costs and effects, not the bounded thirteen-series input qualification.

### Selected integration approach

Prepare a bounded source-owner acquisition/capture contract for the thirteen named series, with the exact price-basis and sufficient complete prior-session coverage. For the proposed 252-prior-session warmup, a full price-grid witness includes those 252 prior observations plus the current anchor; the 63-session return then selects its correct 64-price endpoints. The amount of history actually required by each feature remains explicit rather than inferred from a generic period string.

A present-day capture of older prices may support a **future** decision that genuinely receives it before cutoff, subject to source/rights/calendar/basis qualification. It does not retroactively authorize forecasts at dates before that capture. This distinction allows a bounded initial warmup without either waiting unnecessarily for months of new price observations or fabricating original historical availability.

If the incumbent source owner instead composes separately captured slices, it must qualify revision consistency, missing sessions, and the as-known merge rule. Never splice incompatible adjustment vintages merely because every slice has a hash. Retaining an immutable merged image alone does not prove each inherited row's provider lineage.

No acquisition, capture activation, `full_history` run or source-cohort expansion occurred in this continuation. These are the exact acceptance requirements for the subsequent source integration—not a background task or an admission receipt.

## 5. Minimal future adaptation and acceptance

The future source/reader work stays within the existing owners and carries one immutable study specification containing cohort, schedule, cutoff, lookback and source-use identity. A protocol-specific adapter may compose the existing envelope validators and immutable identity types; it must not mutate the incumbent experiment's parameters or create a new evaluator/registry.

It must demonstrate all of the following with invented inputs before any admitted live study:

1. The current nine-node/26-session/9 a.m./63-price experiment is unchanged.
2. The proposed eleven-asset/thirteen-input study cannot run with a missing benchmark or silently reduced universe.
3. Sixty-three prices are refused for a 63-session return; sixty-four correctly aligned prices yield the intended endpoints.
4. A receipt read after the 8 a.m. information cutoff is not made eligible by an earlier observation date or later publication timestamp.
5. One-month capture does not inherit unproven older rows from the mutable cache.
6. Bounded warmup captures known today can serve a later decision but never a historical decision preceding their availability.
7. No prepared input contains outcome labels, runtime filesystem paths, or a grant to execute candidates; separate owner admission remains intact.
8. Every expected decision remains in the source-disposition schedule, including unavailable decisions; no selective dropping manufactures a better backtest.

The code-level input interface and the required semantic changes are now identified. The remaining boundary is **qualification and implementation of that exact source/reader adaptation plus genuine independent review**, not discovery of a new system or another generic architecture exercise. Product implementation and live source effects remain deferred under the current research-first phase.

## 6. Evidence and compatibility

The bridge and its test-source file were downloaded at the exact source pin into the existing bounded M2 research-evidence directory. `tests/test_research_codegen_prefix_driver.py`, blob `25c93a70f5d93fc4f570318f72f739e9b3f3451b`, describes invented fixtures and fake transport. Its source was inspected; its test suite was **not run** in this continuation, and its presence does not constitute a fresh pass.

No active worker, denied review retry, source-writer displacement or unresolved modifying effect was created. The prior source-readiness and policy-accounting proofs remain valid on their unchanged bytes. This appendix supplies an actionable consumer-integration boundary for the next phase rather than claiming that the adaptation is already built.
