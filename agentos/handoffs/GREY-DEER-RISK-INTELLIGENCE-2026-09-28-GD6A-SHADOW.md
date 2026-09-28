---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/gd6a-us-shadow-intake-20260928
model: sol
prs:
- 8141
ended_because: ci_handoff
mission: Qualify published GD-6A through its existing read/acceptance path and resolve
  the actual CI scope defect. MISSION_COMPLETE:false.
state_before: R5 builder/checkpoint were connected; the native acceptance alarm did
  not bind the new publication, and declared CI import coverage was incomplete.
changed:
- path: scripts/build_prophet_market_eligibility.py
  what: Shared native window and receipt helpers; read-only published-result consumer.
- path: scripts/prophet_board_acceptance.py
  what: Consume the receipt in the existing alarm, never a new policy or gate.
- path: tests/test_prophet_market_eligibility_publication.py
  what: 23 reader and native-alarm tests.
- path: .github/ci/legacy-jobs.yml
  what: Add exactly two missing import paths to the existing job.
- path: research/grey_deer/GD6A_ZERO_POLICY_SHADOW_INTAKE_2026-09-28.md
  what: Current source, CI evidence and remaining policy boundary.
verified:
- claim: Whole bridge file and all GD6A suites pass with new reader tests.
  command: python3.12 -m pytest tests/test_prophet_market_eligibility.py tests/test_prophet_market_eligibility_native.py
    tests/test_prophet_market_eligibility_publication.py tests/test_prophet_bridge.py
    -q
  result: 212 passed, 67 subtests passed; isolated native-source fixture; log 5d021a2345dc2e7ae358eb0d509f12ed9985cf47d4d78897aa6d51e03d9b4d98.
- claim: Real committed input survives actual producer and reader.
  command: python3.12 release-r6/real_reader_probe.py
  result: 69/69 original rows, exact order/content, zero action flags and no reader
    writes; not served production.
- claim: The tests discriminate disconnecting the alarm and omitting receipt comparison.
  command: python3 release-r6/reader_fault_controls.py
  result: Intended assertion failures; originals restored.
unverified:
- claim: Exact R6 hosted/current-base release acceptance.
  what_would_verify: Required concluded checks on the new head, including differential
    scope validation.
- claim: Ordinary served publication or active risk enforcement.
  what_would_verify: Accepted normal checkpoint plus entitled bound reader/refresh,
    and separately adopted per-policy source/authority.
unresolved:
- R5 scope gate reported two omitted paths; R6 repair still requires hosted confirmation.
- Two unrelated jobs failed installing dependencies; no bypass or global dependency
  edit.
- The inspected registry/envelope has no active GD6A policy.
- Separate compound app/deploy-source inspection was refused; no retry or proxy.
next_actions:
- Consume new-head CI and resolve actual remaining release blockers.
- Accept source under concluded checks, then witness normal publication/read/refresh.
- Advance a separately registered native risk policy, preserving research and all
  scope/expiry gates.
do_not_redo:
- Do not recreate GD-6A or add a second risk policy, identity, registry, collector,
  ledger or publisher.
- Do not repeat CI registration; it landed in69601edd13829d6a32a5a51ffa07e781ff314ef3.
- Reuse unchanged source tests appropriately; preserve GD-2/GD-3 and merged B4 source-session
  proofs.
- Preserve H1/Cycle, Seat B's source custody and the original CEO's UI release.
danger_areas:
- ELIGIBLE remains a zero-policy shadow observation, not buy permission; all eight
  action flags stay false.
- A fresh summary does not qualify an undated optional contributor. Missing evidence
  cannot erase research or invent liquidation.
- Descriptor checks cover the opened regular file; independent owner hashes, source
  scope and validity remain mandatory.
- No status-read denial, readonly ingress or new chat transfers custody or authorizes
  a proxy retry.
---

# GD-6A R6 continuation

MISSION_COMPLETE:false. Same operation, source branch and PR. No source-writer release or automatic wake.
