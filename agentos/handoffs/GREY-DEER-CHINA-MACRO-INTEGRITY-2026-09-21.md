---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/china-breadth-current-coverage-20260921-sol
model: sol
ended_because: context_budget
mission: Repair China macro input integrity and interpretation without manufacturing risk probabilities or duplicating
  the existing radar programme.
state_before: China breadth accepted historical-only coverage and could publish an older computed row after accepting
  a newer partial batch.
changed:
- path: collectors/china_breadth.py
  what: Bind coverage to configured names, valid latest prices and sufficient moving-average history; reject dropped
    latest rows before cache writes.
- path: tests/test_china_breadth_coverage.py
  what: Exercise the real fetch, inherited calculation, runner, stored output and existing regional summary reader.
- path: .github/ci/legacy-jobs.yml
  what: Include the new suite and its existing yfinance dependency in the existing China breadth CI job.
- path: engine/china_tier1.py
  what: Separate washed-out margin receipts and reuse the producer slowdown label with strict unavailable semantics.
- path: scripts/build_china.py
  what: Use one slowdown interpretation for the existing dialog and risk-card projection.
- path: templates/china.html.j2
  what: Name Economic slowdown truthfully and remove missing-input calm/high-risk sizing fallbacks.
- path: mockups/evidence/china-integrity-7592/
  what: Eight dual-theme/language/viewport screenshots and eight actual live-patcher interaction cases, explicitly
    synthetic.
verified:
- claim: The original implementation failed the nine initial negative cases while two valid controls passed.
  command: python -m pytest tests/test_china_breadth_coverage.py -q --tb=short
  result: Initial RED 9 failed / 2 passed; expanded edge RED 2 failed / 13 passed.
- claim: The repaired producer and adjacent collector/heatmap suites pass.
  command: python -m pytest tests/test_china_breadth_coverage.py tests/test_china_board_breadth.py tests/test_market_heatmap.py
    tests/test_breadth_constituents_repair.py tests/test_breadth_split_seam.py -q
  result: Original integrated candidate 84 passed; after native review repair, 94 passed without warnings in isolated
    Python3.12.13/pandas3.0.6/NumPy2.5.3.
- claim: An existing stored close matrix retains identical breadth math on valid inputs.
  command: python research/grey_deer/china_breadth_coverage_20260921/real_input_probe.py --source /Users/chriswong/Documents/Cluade/macro-main/data/china_search/closes.parquet
  result: 1270 rows; 76 of 82 configured names present; 75 latest and MA-eligible names; exact output equality.
    Artifact ends 2026-09-04, not a current-production proof.
- claim: Affected-area producer, page, dialog and live-state regressions pass in a full checkout.
  command: The complete eleven-suite pytest command in research/grey_deer/china_breadth_coverage_20260921/UI_TRUTH_REPAIR.md.
  result: 309 passed. New publication cases RED 19 failed / 25 passed, then 44 passed; sparse data/site failures
    resolved rather than omitted.
- claim: The real current-template synthetic browser matrix preserves unavailable states and live headline ownership.
  command: python research/grey_deer/china_breadth_coverage_20260921/capture_truth_cases.py --work-dir <unique evidence
    directory> --browser <installed Chrome executable>
  result: 8/8 screenshots plus 8/8 interaction cases, no document horizontal overflow; no capture console errors
    or failed responses; local server closed.
- claim: Stored September18 economic reading uses the same label in glance and dialog.
  command: slowdown_face(record) == _radar_dlg_vm({}, latest)["slowdown"] on the hash-bound data/china_regime/latest.json;
    see real_slowdown_receipt.json.
  result: 58.5 / high stays numerically unchanged; weak / 疲弱 in both consumers. Not a deployment proof.
unverified:
- claim: Exact-new-head hosted CI, merge, publication and real production collector/page proof.
  what_would_verify: Concluded exact-head checks on PR7592, current-base integration, normal release and actual production
    run/status/output/browser receipts. Remaining independent review is Chairman-waived, never approved.
- claim: The 94 screenshot value or its predictive calibration is corrected.
  what_would_verify: Reconcile PR 6989, its original custody, same-input source clocks, current consumer compatibility
    and independently reviewed calibration/authority evidence.
unresolved:
- Whole-frame session age remains with the existing runner/freshness owner; this change does not invent a venue
  calendar or certify current data from a build timestamp.
- Shared radar arithmetic/calibration repairs remain on PR 6989 at d775a6c40c9f12c8411cd87100ac7dbfcd664870, Draft/HOLD;
  this branch is not a replacement.
- PR7597 merged as 4183c5d564853d4796798bf19270f906adb5c9b5 and now owns the accepted HK/Canada P0B
  evidence heal (two receipt bindings plus sixteen screenshots). The earlier PR7578 18-binding rebind instruction is
  superseded / DO_NOT_REDO; PR7578 may retain only its still-unique render/dead-route delta.
- PR7485 merged via c4267cdc18d995f4b4d5a2f0c868fd520ba5481d; this candidate repairs its remaining interpretation/null
  findings on current main.
- The blocked revised native review result remains unread. The Chairman waived it rather than granting alternate
  inspection or duplicate review.
next_actions:
- >-
  Consume current exact PR7592 CI; PR7597 already closed the inherited P0B evidence drift.
  Refresh integration only on material protected-main movement, then complete the existing
  release/publication path.
- Verify the real production collection status, saved breadth and China page, including unavailable-state wording
  and headline refresh.
- Continue the original PR6989 custody/calibration and participation/dispersion programme without repeating its
  blocked materialization or denied result read.
do_not_redo:
- Do not lower the displayed risk score by judgment or replace old calibration with the tiny live sample.
- Do not rebuild PR 6989's already tested composition/reference/cohort/authority/adapter repairs.
- Preserve merged China freshness 7156 and renderer 7463; do not claim merge alone is live proof.
- Never interpret the stored-input canary's 2026-09-04 endpoint as the current market session.
- Never modify the shared macro-main checkout, foreign worktrees, production data or historical risk ledgers in
  this repair.
- 'Preserve the merged #7485 deep composition and neutral/headline repairs; older #7481 is held/disarmed, #7383
  remains a held historical restoration.'
- Do not repeat the blocked test append to test_china_delayed_board_disclosure.py. No change to that file is part
  of this candidate.
- Do not reopen the exceptional waived reviewer gate or claim an unread result passed.
danger_areas:
- The inherited breadth calculation can drop partial newest rows; checking fetch coverage alone is insufficient.
- Current quotes without enough valid history cannot support a representative moving-average breadth denominator.
- This is curated large-cap breadth, not all A-shares; no all-boats inference follows.
- The earlier 403-PR census identified PR7578 as the P0B evidence writer, but protected main later merged PR7597
  with the complete self-binding heal; that later accepted source supersedes the old repair instruction.
prs:
- 7592
decisions:
- DEC:CHINA-INTEGRITY-EXCEPTIONAL-REVIEW-WAIVER-20260921
---

## Current cumulative boundary
MISSION_COMPLETE: false
FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION

The cumulative implementation and evidence reached a safe phase boundary after
substantial source, test and browser work. No writer transfer, daemon, worker
liveness, merge or deployment is implied. Parent Sol retains custody on PR7592.

Procedure: Mastermind@6a24ed038774afff0bbab2982f420ef0e66e5b5f,
Skillpack1.0.1/bootstrap1. Current integrated local base is
29f68a5d0d5c810b96f3d81db9c94d26d8a05b81, joining the original repaired
6328aebe521ef18ad61ac0d5e36a6148b637dbd2 with main
1dc11fb3eb326393c803bc2eff408db89bb91bc1. The PR's latest commit/comment binds
this cumulative source/evidence checkpoint to its final pushed head.

Details and commands: research/grey_deer/china_breadth_coverage_20260921/UI_TRUTH_REPAIR.md.
Prior producer receipts in README/REVIEW_REPAIR remain dated evidence, not current
release claims. The stored legacy radar reproduction of94.4444 remains numerical
reproduction only, not proof of calibration, broad-market coverage or production.

The one-off Chairman waiver is recorded in the cited DEC and PR comment5757931717.
The revised native review378bcdac-632f-4cf2-a777-a69236b6e3c4 exited, but its
result-access call was platform-blocked. Do not inspect it by another route,
forward it unread, or create a duplicate reviewer. No review/watch remains running.

Next resume: minimum fresh procedure + exact PR7592 and PR7578 state, consume
new CI/owner evidence, then lawful release and real production-path proof. Do not
rehydrate old tool history or repeat the already proven tests without an invalidator.

Pre-publication note: an additional combined latest-ref/evidence-validation call
was platform-refused before returning a process handle. It was not retried or
repackaged. The completed tests and browser proofs above bind the already-verified
integrated source, not an unobserved later main tip. Current-base release proof
remains a separate obligation; this checkpoint does not claim it is satisfied.
