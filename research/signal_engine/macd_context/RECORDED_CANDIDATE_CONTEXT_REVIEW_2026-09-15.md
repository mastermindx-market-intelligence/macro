# Recorded Prophet candidate context — measured join and historical lineage

Date: 2026-09-15 America/New_York; tool receipts continue into September 16 UTC.
State: PARTIAL research, zero production authority. No new profitability estimate, fitted selector, calibrated probability or trade change.

## Capability delta

Before: one snapshot example and a readable outcome frame, but the coverage of exact candidate-context joins was unknown.
After: the existing canonical board parser joined all 8,664 post-cutoff graded rows across 32 board dates to their recorded snapshot candidates. A historical full-board artifact was matched exactly to the June 30 snapshot after applying the existing snapshot projection. Five synthetic join-core tests pass. The reusable full extraction/export runner remains incomplete after a platform refusal; there is no saved complete joined dataset or new benchmark-context outcome run.

## Sources and custody

Protected Skillpack: Mastermind@7642aea155d2817219135b24246b55c1d7611c66; INDEX, COLD_START, ACTIVE_EXECUTION, RECONCILE_STATE, CLOSEOUT loaded atomically; schema1/version1.0.1/bootstrap1.
Macro source pin: 9579caf3f950f1a2e7b959a9b3b68d26e42e5d06.
Research operation/carrier unchanged: macd-context-cycle-attribution-20260915-c3; Remote Desktop Commander; Mac Studio 3f5ce987-e3eb-40a3-af9f-4b0ae54919cc.
Separate publication operation remains macd-cycle-research-publication-20260915-c3 on draft PR7177 / sol/macd-cycle-research-20260915-c3. No new workstream, Job, worker, watcher, event identity, outcome grader or ledger was created.
Direct work rationale: PRINCIPAL_JUDGMENT for source/estimand admission and bounded existing-owner checks. An Executive OS plugin search returned no usable existing Executive submission route; no review worker was dispatched or independently accepted this research.

Read-only source objects, verified by Git blob hash:
- data/us_board_ledger/retro_grades.parquet: 67e2541add91fa335918c95e098d9aec0fcf7030, 778145 bytes; 9614 rows.
- data/us_board_ledger/snapshots.jsonl: 8e39dcc977931a3900c1a63e81a31eddd039fb05, 57157509 bytes.
- scripts/grade_us_board.py: 68ef9eb7620f0592e3cd02d66a3eae2ab0998dce, verified against the local parser before import.
No current checkout, original graded outcome, original crossover study or canonical TrialLedger was modified.

## 1. The existing product-era cutoff resolves the missing-date question

The canonical grader defines LEDGER_HISTORY_FROM = 2026-06-25. Its documented reason is that earlier buy-key lists were broad screens, including names labelled DOWNTREND/TOPPING, rather than the later narrower selection. This is an existing product-definition rule, not a cutoff chosen from this study's returns.

The exact snapshot object has 38 records on 38 distinct dates, June 30 through September 11, 2026; no duplicate snapshot dates. The outcome frame has 39 graded board dates. Exactly 32 of those dates have snapshots. The seven unmatched dates are June 15, 16, 17, 18, 22, 23 and 24: all precede the existing selection-era cutoff.

Using the unchanged owner's _board_to_record parser and exact (as_of, lane, ticker) keys:
- 4590 snapshot candidate keys; zero duplicate snapshot candidate keys.
- 8664 graded rows match a snapshot candidate.
- 950 graded rows are unmatched; all are pre-cutoff history.
- Zero post-cutoff graded rows are unmatched.
- The join preserves horizons and original outcome rows. Graded rows and repeated observations are not independent trades.

This establishes recorded-context availability, not fully point-in-time scientific admission. Missing pre-cutoff snapshots are not filled from today's engine, and pre-cutoff screens are not relabelled as current recommendations.

## 2. Five recorded ranker labels must remain separate

The 38 snapshots carry these ranker labels: bottoming-alignment (8 snapshots), confluence (9), us_prophet_v1 (1), us_prophet_v2 (3), us_prophet_v3 (17). These counts cover all 38 snapshots, including dates not represented in the graded frame.

Within the matched graded rows, the stored rank_by and snapshot rank_by agree:

| Recorded label | Matched graded rows |
|---|---:|
| bottoming-alignment | 1545 |
| confluence | 2993 |
| us_prophet_v1 | 486 |
| us_prophet_v2 | 942 |
| us_prophet_v3 | 2698 |

These are graded rows across horizons, not five independent experiments. A ranker label is not a complete producer-version identity: code, configuration, inputs or acceptance rules can change while a string remains the same. The table must not be pooled into a claim that one unchanging Prophet champion produced the whole record.

## 3. Known context fields agree; unknowns remain unresolved

On matched graded rows, the current canonical parser reproduces the following recorded metadata wherever both sides are non-null:

| Field | Both sides known | Unequal values in the inspected comparison |
|---|---:|---:|
| entry_status | 8307 | 0 |
| sector | 8664 | 0 |
| align_tier | 1270 | 0 |
| state | 8331 | 0 |
| score | 8328 | 0 |
| act_level | 8307 | 0 |

This is not complete-field coverage: a both-known comparison does not certify rows whose values are missing on either side. Do not fill those gaps or infer confirmation state from a present-day label.

A preliminary position comparison converted values to strings and reported differences. Its numerical/type-aware follow-up was part of a compound tool call that was refused. Numeric rank-position parity is therefore UNRESOLVED. The string comparison is not a confirmed production data defect, and this report makes no claim that the stored ranks are corrupt or fully reconciled.

## 4. One historical board has a complete content match

A bounded local history query over the board path returned no June 29–July 1 revisions. This did not establish that the historical records were absent: the GitHub commit query found them. No local history rewrite/fetch or checkout mutation was used.

Historical artifact commit: ba0daeb4d4966bd79ccba9634ebdc705cf98030d, whose metadata records July 1, 2026, 11:19:43 UTC and the message engine-render: regime recompute + re-render 2026-07-01 (scope=all).
Board path: site/factordata/us_standouts.json.
Board blob: 6dcd3cf80fa32fdc2f2088f2fa5745a056ea0882; 640398 bytes.
Board as_of: 2026-06-30; rank_by: bottoming-alignment.

The full object was read and hash-verified. Applying the existing snapshot projection (as_of, rank_by, dispersion state, optional donor, and preserved lanes) yields exact object equality with the June 30 archived snapshot. This is a whole-record content match, not a match on ticker or headline alone.

The associated historical tree contains:
- engine/entry_signal.py: 1990820e3e8d612f053cfc210aac054a5247fd9b
- engine/cycles.py: 782abc843c177246c29494d2cae3ac1605060f11
- engine/confluence_tiers.py: 99fe807ecb1b6e73f51b841707ba0579eaa85813
- scripts/build_stock_library.py: 9cf6e6fe43d782579a0209094205d526e98ab284

This supplies an exact artifact-to-repository-tree association. It does NOT prove the original provider/job's execution revision, when a user saw the result, or historical price/configuration vintages. A Git commit timestamp is not automatically a runtime publication receipt. The local tree query did not show scripts/grade_us_board.py at that historical commit; do not claim the current snapshot machinery itself ran on June 30.

The full board includes gate_go=false while the snapshot projection omits that top-level field. This is a source-coverage observation, NOT a finding that every buy was forbidden: gate_go semantics must be recovered from the relevant intake/producer contract before any such conclusion. Existing research/prophet_us_audit/INTAKE_FILTER_PREREG.md already documents conditional admission when gate_go is false.

## 5. Historical horizon values are entry-quality scores, not probabilities

The historical entry_signal.py at the exact artifact-associated commit explicitly defines _horizon_read outputs in [-1,+1], as entry-QUALITY reads, NOT return forecasts. This strengthens the earlier current-source-only interpretation, while retaining the runtime-lineage limit above.

Its d3 component normalizes the entry-quality score. Its d21 component combines that value, price relative to a 50-session mean, and cycle freshness with weights 0.45/0.30/0.25. Its d63 component uses longer-trend location and extension adjustments. These formulas are source facts; comments about calibration do not establish empirical calibration in this study.

Therefore a historical value such as d3=0.58 is not a 58% cash-profit probability. The current verified grade frame carries horizons 5,10,21; these do not justify silently treating H5 as the d3 outcome or H21 as the d63 outcome. The first exact-horizon candidate is recorded d21 versus the existing H21 ruler, conditional on source/field coverage and the separate admission gates. New H3/H63 outcomes, where required, belong to the existing grading/entry owners and their maturity policy.

## 6. Two evaluation questions, different provenance requirements

Proposed scientific distinction, not a new control plane:

1. **Recorded-decision evaluation:** assess immutable, actually recorded candidate/score observations against their owner-defined outcomes. It does not require regenerating the candidate with today's engine. It does require source references, correct field meaning, admission/confirmation and observation/entry clocks, and appropriate era/price-basis treatment.
2. **Engine-policy replay:** regenerate candidates under a historical or challenger algorithm. It additionally requires executable source/configuration/input custody, causal as-of restrictions, and a control demonstrating fidelity. The existing scripts/prophet_pit_replay.py already owns the general replay route; this study does not create a replacement or execute its plan-writing mode.

Recovering recorded observations can move the first question forward without pretending to have solved the second. A single historical code match must not become a blanket certification of all 38 snapshots.

SPY opportunity cost, RSP participation and economically preassigned sector/peer comparisons remain separate. Context values must attach using exact observation dates and original benchmark/sector owners, not future values or the benchmark that makes a result look best. No actual 2026 breadth-context or new return calculation ran in this chunk.

## 7. Implementation proof and current platform boundary

Local root: /Volumes/Mastermind/Mastermind/artifacts/macd-context-first-look-20260915-c3/cycle_extension_v2/.
CONTEXT_JOIN_AMENDMENT_20260915.md SHA256 fcd030c756177e92e5c5a7219a9437110c0d8d23c5043ea39b530e0da5de42b0.
recorded_context_join.py SHA256 6b338031f0e16775096702371b5a6b3341a3205a76dc4bfae87b5bd83d105b44, 59 lines at the final read. attach_context and attach_market_context are implemented; snapshot extraction stops partway through its loop, with no complete runner/export path. Do NOT call the incomplete extractor or represent this file as a completed dataset build.
test_recorded_context_join.py SHA256 89e93a022fed326966434b6dff87323c2c0aa6ab619398cb0d3d3938f44500b7.

Five synthetic tests were observed failing while the module was absent (process5670, exit1). After the core was written, process34798 exited0 with all five passing: denominator/cutoff/unknown behavior, duplicate-context refusal, duplicate-grade-key refusal, unchanged existing columns, and exact-date/no-forward-fill market context.

The next source append, containing remaining extraction and runner code, was blocked. Native readback proved it absent. It was not retried, re-encoded, moved to another carrier or recreated via the REPL. The measured real-data join described earlier was performed before this source-write refusal using the already-existing canonical parser. No complete joined dataset was exported afterward.

The separate denied compound metadata inspection also remains held. Historical source retrieval/content matching and synthetic core tests did not compute its requested rank-position or per-ranker-date diagnostics.

## Current ruling and next action

The source-availability question has materially advanced: all post-cutoff graded candidates can be linked to saved snapshot candidates. Scientific admission remains PARTIAL because rank-position parity, observation/publication timing, historical producer/configuration linkage, field coverage and price-basis strata are not all closed.

No prior crossover, benchmark, contrast or repair study was rerun. No performance view was added to the old mechanically counted 6496-view inventory; the TrialLedger accounting proposal remains unapplied and requires the existing owner's adjudication. It is not an independent-test count or accepted preregistration. Independent scientific review remains absent.

Exact next primary action: after the specific native source-write/metadata gate clears, finish the declared snapshot extractor/exporter and outstanding position check, then attach source-qualified as-of breadth/sector context and assess the recorded d21/H21 opportunity under preassigned benchmark/era rules. Do not fit a stock selector, choose per-name winning timeframes, substitute forecast probabilities for quality scores, or move live rank/availability/size/trade authority. Existing TOI/Temporal Grain/Elliott holds remain unchanged.
