---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-direction-20260924-sol-001
model: sol
ended_because: ci_handoff
mission: >
  Deliver Chairman-authorized short/medium-term Treasury direction and jump-risk
  intelligence end to end through the incumbent RIC sources, evaluation and consumers.
state_before: >
  The conversational September 23 explanation was an unvalidated hypothesis.
  RIC already had nominal-yield context, with separate active policy/real-rate
  qualification and entry-conditioned research carriers that must not be duplicated.
changed:
  - path: research/RATES_DIRECTION_AND_SHOCK_MASTERPLAN_2026-09-24.md
    what: Freeze program ownership, scientific thesis, staged delivery, falsifiers and production acceptance.
  - path: research/rates_direction/prereg_v1.json
    what: Predeclare 48 tenor/horizon/model configurations, primary period, baselines and fixed settings.
  - path: engine/rates_direction_research.py
    what: Add pure research-only purged fit/calibration/forecast and incumbent-HAC score consumer.
  - path: scripts/research/ric_rates_direction.py
    what: Consume existing FRED store only after canonical TrialLedger registration and frozen-byte checks.
  - path: tests/test_rates_direction_research.py
    what: Synthetic leakage, missingness, units, calibration, probability and preregistration tests.
verified:
  - claim: The synthetic suite passes after the expected missing-module RED and a repaired read-only-array failure.
    command: python3 -m pytest tests/test_rates_direction_research.py -q --disable-warnings --tb=short
    result: 15 passed, 16 warnings; no real target outcomes were opened by these tests.
  - claim: The program decision satisfies Agent OS schema.
    command: python3 scripts/agentos.py validate
    result: 1241 records, 0 errors, 94 existing warnings before this handoff was added.
unverified:
  - claim: Any model improves on historical or prospective benchmarks.
    what_would_verify: Frozen registered experiment, independent replication and accepted prospective evidence.
  - claim: Production or browser consumers are using this module.
    what_would_verify: Separate lawful integration/release and real input-to-consumer proof.
unresolved:
  - Historical evaluation, independent review, required CI and release remain unaccepted.
  - Proper PIT source clocks, macro consensus and policy/real-rate receipt integration remain separate dependencies.
next_actions:
  - Freeze exact source and test hashes before opening target outcomes.
  - Register all 48 generated configs in the existing TrialLedger, then run corrected-history diagnostics.
  - Publish all outcomes including failures, obtain independent review, and continue RD2-RD6 without claiming completion.
do_not_redo:
  - Preserve this original Studio worktree/branch and all verified edits; no other worker has started.
  - Do not duplicate or release held 7418, 7400, 7521, 7593, 7320, 7877 or Mastermind 769.
  - Do not create collectors, calendars, TrialLedgers, transmission engines or control planes.
danger_areas:
  - Historical source labels and hashes are not historical receipt timestamps; no PIT certification.
  - September 23 and all 2026 data are motivating-case audit, not the primary holdout.
  - Research outputs never imply trade, rank, gate or size authority.
decisions: [DEC:RIC-RATES-DIRECTION-PROGRAM]
---

# Cumulative working checkpoint

MISSION_COMPLETE: false. This is an interim durable source checkpoint, not a claim that the chat, program, ship attempt or research is complete.

Authority: live Chairman delegation on September 24; DEC:RIC-RATES-DIRECTION-PROGRAM. Protected procedure: Mastermind 294b4c00ed668b497edb834be8108f14bc1bee8a, compatible 1.0.1/bootstrap1.

Operation: rates-direction-20260924-sol-001. Macro base 19ba4a8f3147b487f78894d7090bd7e36080d9e4. Original Studio workspace: /Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/rates-direction-20260924-sol-001. Branch claude/rates-direction-20260924-sol-001.

Accepted scope: end-to-end research/build within existing RIC; no vendor purchase, trade authority, duplicate owners or held-sibling release. Synthetic functionality is built, not independently accepted. Active workers/children: none. Background execution/wake: none claimed. Pending modifying effects: none after same-carrier readback reconciled a transient Studio gateway restart; data materialization subsequently completed with exit 0 on PID 89650.

The existing Macro sparse owner materialized data before any ledger edit, preserving complete incumbent contents. New test enrollment only extends the existing rates CI job; no new runner or queue. Preserve source edits and freeze history; no empirical selection or outcome claim exists at this checkpoint.
