---
workstream: WS:PROPHET-US-AVAILABILITY
session: claude/turn-watch-runtime-20260917
model: sol
ended_because: ci_handoff
mission: >
  Reduce the full TURN WATCH computation without changing its discovery universe,
  observation semantics, history inputs, rules or output; restore a viable
  current-data-to-history path as part of the existing Prophet recovery.
state_before: >
  The real full-universe recovery produced current September-16 TURN WATCH data
  but took 1047.25 computation seconds and exceeded the 600-second builder budget.
  Source/identity recovery existed in separate unmerged held carriers.
changed:
  - path: engine/confluence_tiers.py
    what: Native calendar aggregation replaces per-bucket Python known-date callbacks.
  - path: engine/us_turn_watch.py
    what: >
      The bulk consumer skips explanatory details only after an empty trigger union;
      standalone evaluation, every trigger, every RS participant and all triggered
      private observations remain complete.
  - path: engine/us_leader_pullback.py
    what: >
      Vectorized warm-input validity retains the existing state machine and its
      exact per-leg null diagnostics while avoiding repeated scalar checks.
  - path: .github/ci/legacy-jobs.yml
    what: >
      Add the new resampling regression to the existing session-anchor code owner;
      keep TURN WATCH/leader tests in their sole existing washout-turn-organ owner.
verified:
  - claim: The actual full-universe output is unchanged except its measured runtime.
    command: >
      python -c "import json; r=json.load(open('research/us_prophet_availability/2026-09-17-runtime/full-universe-runtime.json')); print(r['elapsed_seconds'],r['identical_public_except_runtime'],r['identical_all_uncapped_rows'])"
    result: >
      Exact engine head 788462d59e60f6ec311b46c0ff23a45f0c186793 completed in
      556.560 wall seconds / 513.936 CPU seconds. All 6102 names were retained,
      5635 graded, and all 2901 uncapped observation rows compared exactly equal.
      Inputs and previous artifacts remained byte-unchanged; no provider request.
  - claim: The existing warning thresholds are not silently changed or conflated.
    command: >
      python -c "import json; r=json.load(open('research/us_prophet_availability/2026-09-17-runtime/measured-stages.json')); print(r['warning_600_seconds_met'],r['early_warning_480_seconds_met'])"
    result: 600-second comparison met in the measured run; 480-second early warning remains.
  - claim: Cold/null/calendar and full-state behavior remain identical.
    command: >
      python -m pytest -q tests/test_confluence_resample_runtime.py
      tests/test_us_turn_watch.py tests/test_us_leader_pullback.py
      tests/test_session_anchor_invariance.py tests/test_sq_anchor_invariance.py
    result: >
      410 passed on the final engine source. Additional 160 calendar reference
      cases and 48 leader full-state-frame cases are exact. Forbidden discarded-work
      and scalar-check mutations are detected. See bound evidence receipts.
unverified:
  - claim: These sources are deployed and the actual public candidate/plan journey is recovered.
    what_would_verify: >
      Concluded exact-head hosted CI/security, independent source review, accepted
      integrated source and prospective protocol adoption, one canonical publication,
      authorized actual candidate/plan/premium payload and browser verification.
unresolved:
  - 480-second early warning remains; one measured 600-second pass is not a future latency guarantee.
  - Existing peer fixes and source-custody/review gates are not waived by numerical compatibility.
  - The deployment must exercise actual current data and B1 history, not substitute this frozen benchmark.
next_actions:
  - >
    Conclude the runtime carrier's exact-head checks and independent review, then
    the existing single integration/publication owner incorporates the accepted
    source alongside 7180/7187/7200/7206/7227/7235 and proves the actual served journey.
do_not_redo:
  - Do not rerun provider acquisition or rewrite the preserved benchmark/history inputs.
  - Do not duplicate the incumbent price, copy, identity, capacity or publication lanes.
  - Do not shrink the universe, raise runtime warnings, or change signal/entry rules for performance.
  - Do not put TURN WATCH tests into a second CI owner or accept a private omitted asset as a source failure.
danger_areas:
  - Full-universe identical computation is not a full nightly or production deployment proof.
  - The code still has pending source-review and release gates even where isolated tests pass.
  - Latest remote head and source custody must be reconciled before any source or publication effect.
prs: [7180, 7187, 7200, 7206, 7227, 7235]
---

## Authority and source identity

Current Chairman direction continues the approved recovery and complementary runtime phase.
Procedure pin: Mastermind `eec5324c5205e8bad206512e0a936898e50b2408`, Skillpack 1.0.1.
Own source carrier: `claude/turn-watch-runtime-20260917`, isolated worktree
`/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/turn-watch-runtime-20260917-sol-001`.
Initial base: `3daf739affa12a43a6b3a0feb3b4c57154587756`.
The measured engine source is `788462d59e60f6ec311b46c0ff23a45f0c186793`.
Later `81c28903c7f18132b43d5819d2e3c5e6330d0ec1` corrects CI ownership only.
Evidence-only commits must not be relabeled as newly benchmarked engine implementations.

## User and machine journey preserved

All names retain price reads, history-floor accounting, cross-sectional participation and trigger
computation. All triggered observations retain full explanation, private history input and public
ordering. Only the already-discarded empty-trigger rows skip unused details. Standalone callers
still receive their complete result. Empty/all-null/timezone/duplicate observations keep the
original semantics; no value or date is fabricated. The B1 identity/correction core is untouched.

## Method, failures and boundaries

Native calendar aggregation alone measured 889.146 seconds; adding discarded-detail deferral
measured 629.373 seconds. Both had exact full-output parity but missed 600 seconds. The final
warm-mask optimization brought the full path to 556.560 seconds. Each failure and fix is retained
in evidence, not rounded into a pass. The prior full baseline was from the preceding real-input
phase; source input hashes and the prior complete output were preserved throughout.

The first broad integration run identified our duplicate TURN WATCH test registration plus an
omitted private `site/theme.js` snapshot asset. The original ownership assertion was preserved;
only our duplicate declaration was removed. The exact integrated asset was materialized without
editing templates, site source or tests. The targeted two-suite rerun passed 38 tests. Consume
the final broad-run receipt before claiming the whole composition passed.

## Continuation and material side channel

The #7200 CI gate is now fully green (12 trusted packs, selected contract/security gates) at the
03:08 UTC Sep-17 observation, but no independent review was submitted. A material update was
sent to its existing placement root `C0BSBM78V1N/1789587618.242409`, message
`1789614555.307319`. This is not reviewer placement, ACK, START or acceptance. No receiver-specific
watcher is asserted or new runtime job created. Source-author self-review remains disallowed.

The parent recovery remains active. This source is draft/HOLD-FOR-SOL until independent review
and concluded exact-head checks; one acknowledged integration owner controls actual publication.
The same held peer implementations and their outstanding defects retain their owners. On any
ambiguous mutation, reconcile its original carrier before repeating. No production/provider/
workflow mutation was made in this runtime phase. The next major phase is reviewed adoption
and live proof, not another broad reconstruction of these already-bound experiments.

## Concluded exact integration proof

After the targeted correction, the full 24-suite battery passed **996 tests**, with no skips,
no source changes, and 38 pre-existing pandas deprecation warnings. Exact private integration
commit: `3f41c92e98eb6d536ae20534c70aedb626996baf`; tree:
`d6e4de9ef917dff7d1bebbc1e239a934a66cf4b7`. All seven source carriers composed without
manual conflict resolution; published branch references were not changed by this proof.
See the exact source-composition and integrated-tests receipts. This removes the introduced
CI-owner duplication without waiving the original contract; it does not waive any peer finding
or replace hosted CI, independent review, or actual deployment proof.
