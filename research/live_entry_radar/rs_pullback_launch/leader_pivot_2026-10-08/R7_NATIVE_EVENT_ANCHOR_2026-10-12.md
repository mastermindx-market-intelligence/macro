# R7 — native event-anchor / actual-decision compatibility

Date: 2026-10-12. Workstream: WS:LIVE-ENTRY-RADAR / RS Pullback Launch. Sole existing PR: #8649, branch `sol/leader-pivot-publication-p0b30m-20261008-c1`. Source parent: `d0beadc4043624f2e3e7cc9fd6450db1c754f9a0`. Protected procedure pin reused: Mastermind `25c4b7923734392b1013afae179966985819d847`.

**Capability: BUILT_NOT_PROVEN. Engineering-only native implementation; no new market backtest, data admission, detector registration, live alert, trade, sizing, calibrated probability or deployment.** The exact stock-level pivot hypothesis remains unvalidated. This is not a second source owner, collector, experiment ledger or scheduler.

## Before and after

Before: the Phase-1 adapter selected the newest completed 15m and 30m windows from the actual decision clock. A feed whose final constituent minute is unavailable until at least 15 minutes after its end cannot satisfy the newest-15m requirement at any current decision time. At 12:30, a window ending 12:15 might finally be known, but the adapter requests the one ending 12:30. At 12:45 it advances again. This is a contract incompatibility, not a statistical result.

The preceding R6 conversation package reproduced that with synthetic native inputs and explored an in-memory prototype; it was not a source commit. R7 replaces that prototype technique with a normal explicit version branch in the incumbent input module. There is no dynamic source rewriting, monkey-patching or execution of an AST-generated replacement in native code.

After: callers can explicitly choose input schema `mastermind.rs_pullback_launch.phase1_input.v2`. Every candidate declares:

```json
{
  "candidate_id": "illustrative-only",
  "session": "2026-10-06",
  "event_anchor_at": "2026-10-06T16:30:00Z",
  "decision_at": "2026-10-06T16:45:00Z",
  "max_feature_age_seconds": 900
}
```

The example omits the unchanged mandatory streams and other owner receipts. It is not a complete admitted bundle. The age limit is an explicit caller research parameter, not an adopted production value.

Both feature windows end at the declared earlier complete 30m boundary. All source revisions, calendar visibility, identity, basis, latest daily context, current incumbent assessment and news coverage are still evaluated at **actual `decision_at`**. The result is `phase1_panel.v2`, with normalized event anchor, observed feature age and declared maximum age on its frames.

## Version and refusal contract

V1 remains the original schema, behavior and frame shape. V1 never infers v2 from extra candidate keys. Unknown schema versions fail explicitly. There is no silent selection of a more favorable earlier bar.

Each v2 candidate requires an aware timestamp, same-session endpoint after the open, exact 30-minute alignment, no future endpoint and a nonnegative integer maximum age (booleans, floats and strings are not integers for this contract). Exact age equality is allowed; one microsecond beyond the limit is not. Invalid or old candidates remain in the population with `UNAVAILABLE` and a specific refusal. Whole-day future completeness is not a prerequisite for a valid earlier feature.

`_aggregate`, `_metadata_errors`, `_latest_context`, calendar binding, source census and all original helper functions/classes remain AST-identical. In particular, `TERMINAL_BASIS_UNPROVEN` is unchanged. Current Terminal occurrence provenance cannot be laundered into admitted data by supplying matching scalar labels or choosing an older endpoint. All authority fields remain false, and an `OBSERVED_MARKET` input label remains `INPUT_PANEL_BUILT_NOT_ADMITTED`.

The original diagnostic 120-minute label endpoint is unchanged and still based on actual decision time. It is not a newly registered economic-policy exit. Full policy evaluation must use the separately frozen R5 common-horizon protocol.

## Both incumbent pivot consumers verified

Neither `leader_pivot_descriptor.py` nor `first_green_reversal_descriptor.py` was edited. Their definitions and unequal warmups are preserved: undercut/reclaim requires four prior full same-session half-hours; immediate red-to-green is a separate construction.

A synthetic feature ending 12:30 ET, observed at 12:45 ET, now forms through both actual native consumers. The reference starts after the true 12:45 formation decision. A later minute closing above the reference at 12:46 is first known at 13:01 under the same modeled 15-minute delay. Both native consumers retain those distinct clocks. An earlier query cannot see that confirmation.

At 13:01 the historical break can be retained while the current progress state is `UNAVAILABLE` because the newer suffix is unknown. R7 does not hide this or promote historical confirmation to current buyability. Same-minute low-breach precedence, later failure with retained prior confirmation, zero-delay confirmation, invalidation and source-basis refusal are tested without altering the descriptor files.

Consequently, R7 fixes **feature-window readability**, not real-time market knowledge. It does not eliminate source delay, prove entitlement, fill an order or establish predictive value.

## CI dependency repair

The existing `entry-radar-rs-pullback-calendar` job's paths list omitted the two descriptor modules and four tests imported through its existing fixture chain. Exactly those six declarations are added. All 249 parsed job definitions, commands, steps, thresholds and other fields are otherwise unchanged. The original manifest is recovered byte-for-byte by removing the six new lines.

The incumbent manifest parser validates 177 code jobs. The incumbent scope-inference function derives 24 literal dependencies for the affected job: before the repair exactly six were uncovered, afterward zero are uncovered with 24 declared paths. This is a focused native checker result, **not the full differential contract gate or concluded hosted CI**.

## Executed evidence

- Unchanged-source baseline: 198 passed and two CLI failures because the isolated sparse acquisition initially omitted the committed CLI launcher. Restoring that exact committed file resolved those two unchanged checks (2 passed). No assertion was relaxed.
- New v2 tests first failed against the original unsupported schema. Pytest's subtest-inclusive red summary was 50 failed / 9 passed / 32 deselected; this is not a claim of 50 distinct new test functions.
- New suite: 39 test functions and 20 subtests pass, covering native input and both native consumers.
- Full seven-file ordinary repository-import suite on Python 3.14: **292 passed, 113 subtests passed**, exit 0.
- Same suite on Python 3.12.13: **292 passed, 113 subtests passed**, exit 0. These are repeated environment validations, not additive independent test counts.
- Exact-source differential: **44 complete v1 panels byte-identical**, including unavailable, delayed, old-context, revision and multi-candidate cases. Original test-file prefix is byte-exact.
- Actual unchanged native CLI on Python 3.12: v2 synthetic two-candidate JSON input; exit 0; population 2, retained 2, available 1. The malformed anchor is retained unavailable, actual decision clock survives and all authority remains false.
- Native source diff checked; source/test parse and output hashes verified. Review is author verification, not a claimed independent review. Prior Chairman-waiver classification stays explicit.

See [machine-readable receipt](verification/R7_NATIVE_EVENT_ANCHOR_2026-10-12.json) for hashes, test commands and evidence scope.

## Recovery and remaining delivery

The Studio connection terminated before a Python 3.12 launch returned a PID. Read-only reconciliation on the same actual M2 via authorized Desktop Commander found no matching active process and neither the redirect log nor JUnit target; the source remained exact. One bounded technical recovery ran the test successfully on that same source. This was a transport termination, not a safety/permission refusal. None of the older explicitly refused R1/R2 operations was repeated.

Native source, tests and focused CI repair are complete locally. At this document's creation the source commit/push and hosted CI are still separate next effects; subsequent same-PR receipts bind the published head and actual CI conclusions. Do not relabel local tests as hosted success.

Keep the PR DRAFT, no auto-merge, no trading activation. Source/rights/identity/action-basis/first-seen admission remains distinct; Macro #8623/#8637 and Terminal #844 are untouched. A real admitted four-stream minute witness, full controlled stock-level experiment, prospective outcomes and production/browser consumer proof remain outstanding. R6/R7 engineering does not retrospectively change the earlier market-backtest results or turn the reused sector cohort into independent validation.
