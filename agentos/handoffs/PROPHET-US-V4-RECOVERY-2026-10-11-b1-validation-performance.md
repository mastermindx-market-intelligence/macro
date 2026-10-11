---
workstream: WS:PROPHET-US-V4-RECOVERY
session: 01a11e89-b35d-7a81-9404-5fce2c6170cb / claude/ssd-prophet-b1-validation-performance-1eddff8b2400293a
model: codex
ended_because: ci_handoff
mission: Complete authenticated B03 discovery and exact candidate return after preserving canonical source
  validation.
state_before: PR8832 merged normally as 3cb4bfcc49081515f415a10064f0f6882b9434ef. Exact B03 engine installed17:33:05
  and API PID3046105 started17:33:16. Entitled browser read17:41 still aborted at15.002466 seconds with
  no response. Isolated installed read completed25.569790 seconds, B1 semantics24.566727 seconds; actual
  browser request arrival remains unknown.
changed:
- path: engine/us_candidate_episode.py
  what: Validate partition envelopes once per request, retain cross-partition identity and source-ownership
    checks, replay through a private validated-data helper, and group final relations once after all replay/retractions.
    Public validation entry points remain full validators.
- path: tests/test_us_candidate_episode.py
  what: Add linear relation access and interleaved equal-clock late-retraction controls.
- path: tests/test_us_candidate_episode_reconciler.py
  what: Count fresh validation per request; exercise same-HEAD corruption, cross-month event/suppression
    collisions, malformed readdressed envelope and missing causal correction/retraction parents.
prs: []
verified:
- claim: Complexity tests distinguish the old repeated work while six semantic controls pass.
  command: Run current tests against git show HEAD:engine/us_candidate_episode.py loaded in an isolated
    Python process; b1-combined-red-20261011.txt.
  result: 2 failed,6 passed,94 deselected. Baseline envelopes event4/suppression3 instead of1/1; 48-event
    replay reads episode_id2496 times against linear upper bound384.
- claim: Affected B1 engine/intake/writer/wiring and B03/API suites pass.
  command: python3 -m pytest -q tests/test_us_candidate_episode.py tests/test_us_candidate_episode_reconciler.py
    tests/test_us_candidate_episode_intake.py tests/test_us_candidate_episode_wiring.py tests/test_prophet_early_observations.py
    tests/test_prophet_observations_api.py
  result: 190 passed,0 skipped,0 deselected. Existing deprecation and unrelated temporary-cleanup warnings
    retained.
- claim: Complete retained-input B03 result is byte-identical after repair.
  command: Read same retained October8 input/identity/B1 generation with reference2026-10-09 before and
    after; b1-validation-b03-before-timing-20261011.json and b1-validation-b03-final-timing-20261011.json.
  result: 371 rows, all relation fields and snapshot equal; canonical result SHA0185b1ed6cd74211697d07631ca92c3ae8766e828a651f149136ca6acd29eff2.
    One local whole-read11.621227s to4.880347s; not a production latency or causation claim.
- claim: Independent bounded reasoning review approves final source and tests.
  command: Exact-diff review /root/b03_runtime_read_reasoning against base5abdab24ca639e310e97ed0fef9e286a71e2fe43;
    parent git hash-object readback.
  result: APPROVE engine7dd5b5dea5d126fec3efee3f97dde8301168231d, core testsaa52f0c700d68c5d68b8f935f74651a8c0921e65,
    reconciler tests7325df9989accb94c7139406f3cd15c7e567a5e1. Reviewer did not execute tests; parent results
    separate.
unverified:
- claim: The repair resolves the authenticated production timeout.
  what_would_verify: Normal exact-head CI/release, current installed-source/runtime boundary and entitled
    browse/filter/pagination/relation journey below existing15s deadline.
unresolved:
- B03 browse8rows, exactAMZN-before-paging, snapshot consistency, missing history/counterevidence/exactB1
  relation and sign-out remain owed.
- 'Return to candidate requires coherent generated HTML: served theme includes8827 but last inline USProphetSource
  owner did not. Render38141694842 is still in progress at scheduled18:00 read.'
next_actions:
- Publish original fresh B1 repair branch, consume exact semantic CI and required gates once, reconcile
  current-main source/proof compatibility and normal expected-head squash.
- Verify normal API adoption then entitled B03; independently consume actual render source/generated commit
  and live candidate-return journey.
do_not_redo:
- PR8832 and8827 source/reviews/CI/release are closed; retain their merged worktrees and never reuse/reset.
- Do not replay Fabric log-reservation refusal or replace its ID; no pending Fabric operation.
- Do not repeat consumed runtime diagnostics, denied org403 or /api/health through another carrier.
- Do not cache validation by HEAD/mtime/size, weaken public APIs, skip integrity checks, extend client
  deadline or change stored data.
- Preserve P1a8444 integration refusal6029541334, DailyBrief8249 source refusal5924461491,7264/8333 foreign
  OLI custody and scientific holds.
danger_areas:
- Private validated-data helpers are safe only on fresh outputs of full partition validators during the
  current request.
- Post-replay relation grouping must preserve insertion order, equal-clock tie behavior and every late
  retraction.
- Isolated runtime timing identifies cost but does not establish actual browser request arrival or first
  fault.
---

Evidence: /Volumes/Mastermind/evidence/prophet-r6-local-20261008-01a11e89.
