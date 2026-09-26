---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-entry-context-20260919-sol-006
model: sol
ended_because: complete
mission: >
  Add a pre-outcome, context-only rates join to the existing Live Entry Radar
  replay so already-selected leader-reset episodes can be conditioned on
  qualified dated nominal-rate evidence without changing candidates or outcomes.
state_before: >
  Nominal-rate origin was being repaired upstream, but Entry Radar had no pure
  rates-context adapter or frozen leader-like conditional experiment. Tactical
  R1-A/R1-B were separate price-first studies and could not be retrofitted.
changed:
  - path: engine/entry_radar/replay/rates_context.py
    what: Pure decision-date-compatible rates context projection and episode-row attachment; all authority false.
  - path: tests/test_entry_radar_w5_data.py
    what: Test-first chronology, identity preservation, multi-horizon, no-score, and prereg freeze cases in the existing CI-owned suite.
  - path: research/rates_aware_opportunity/leader_reset_rates_context_v1.json
    what: Machine-readable H10 leader-reset x 2y/10y rates-state preregistration frozen before outcomes.
  - path: research/rates_aware_opportunity/LEADER_RESET_RATES_CONTEXT_PREREG_2026-09-19.md
    what: Human-readable population, clock, estimand, multiplicity, authority and owner boundaries.
  - path: research/rates_aware_opportunity/FREEZE_RECEIPT.json
    what: Exact source/config hashes and untouched existing TrialLedger identity at the pre-outcome boundary.
verified:
  - claim: The pure rates-context cases pass after red-first implementation.
    command: python -m pytest -q tests/test_entry_radar_w5_data.py -k rates_context
    result: 11 passed, 75 deselected; target prereg test included; no target outcomes opened.
  - claim: The complete existing W5 data contract remains green.
    command: python -m pytest -q tests/test_entry_radar_w5_data.py
    result: 84 passed, 2 skipped.
  - claim: Wider W5 data/gates/battery contracts remain green.
    command: python -m pytest -q tests/test_entry_radar_w5_data.py tests/test_entry_radar_w5_gates.py tests/test_entry_radar_w5_battery.py
    result: 200 passed, 2 skipped.
  - claim: Existing TrialLedger was not changed before outcome access.
    command: git show af6fda723c1f5e5997748bb0992bb2ddcce51f93:data/trial_ledger.jsonl | sha256; row count
    result: SHA256 beb20607f5757d3a7dd169f0e88e274e8fa3e2dd952dd9bfad76c02edde6d03d; 1676 rows.
  - claim: Current-main movement is material-path disjoint from the frozen study.
    command: git diff --name-status af6fda723c1f5e5997748bb0992bb2ddcce51f93..origin/main over guides, replay owners, workstreams and TrialLedger
    result: Current main 53efe6f47e9efcdde45a12bce483d7ec33f0bb8d; zero listed material paths changed.
unverified:
  - claim: Historical same-session rate availability for replay episodes.
    what_would_verify: Existing source-receipt owner supplies observation availability instants bound to historical episodes.
  - claim: The leader-reset rates contrast improves entry economics.
    what_would_verify: Register the exact frozen study before outcomes, then run it through the existing replay/outcome/Evaluation owners.
  - claim: Sector/industry leadership and within-sector leader selection.
    what_would_verify: Separate owner-bound sector/stock leadership model and PIT evaluation; leader_reset is only an existing proxy.
unresolved:
  - Upstream nominal-rate source repair #7291 remains Draft/HOLD and is not production-proven.
  - Real-rate and meeting-specific policy-expectation evidence are not part of this v1 context.
  - Prospective Radar W5 evidence remains dependent on its existing private-spool/reconnect program.
next_actions:
  - Publish this pre-outcome research carrier as Draft/HOLD and obtain bounded source review.
  - Before any outcome read, register the exact config/hash through the existing TrialLedger/scientific owner with prefix preservation.
  - Then run only the frozen leader-reset comparison using the existing episode and H10 outcome owners; no new evaluator.
do_not_redo:
  - Do not reopen A V4, B Round2, C HardenedV2 or Tactical R1-A results without a material invalidator.
  - Do not modify frozen Tactical R1-B v4 to add rates; it is a separate H60 experiment.
  - Do not create a rates-specific episode store, candidate engine, outcome ledger, score or trade gate.
danger_areas:
  - Corrected-history source dates are not historical availability receipts.
  - Same-session joins require an actual pre-decision availability instant; date-only equality is insufficient.
  - Leader-reset is a leader-like proxy, not sector leadership proof and not semiconductor-specific.
---

This bounded slice freezes the join and scientific question only. It does not
register or execute the target study, strengthen authority, or complete the
parent rates-aware opportunity suite.
