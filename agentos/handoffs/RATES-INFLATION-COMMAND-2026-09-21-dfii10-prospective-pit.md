---
workstream: WS:RATES-INFLATION-COMMAND
session: sol/rates-dfii10-prospective-pit-20260921
model: sol
prs: [7593]
ended_because: ci_handoff
mission: >
  Add the smallest prospective five-completed-session DFII10 point-in-time
  receipt through the existing Rates & Inflation / Transmission owner and
  preserve it with the existing Live Entry Radar W5 observation without
  creating a second store, evaluator, event plane or trading authority.
state_before: >
  Phase22 Q2 required a decision-time DFII10 endpoint pair, but existing
  Transmission exposed only current level and longer changes and GLT's weekly
  snapshot identity did not bind the raw daily five-session vintage.
changed:
  - path: engine/rate_inflation_receipt.py
    what: >
      New measurement-only pure receipt owner: exact source-content identity,
      NYSE five-completed-session endpoints, bp delta, conservative capture
      clock, explicit stale/missing/correction states and hard-false authority.
  - path: scripts/build_transmission.py
    what: >
      Publish the receipt bundle inside the existing transmission latest.json
      contract and retain the prior valid bundle across a transient additive failure.
  - path: scripts/reconcile_entry_radar.py
    what: >
      Select only a receipt known by signal_known_ts and persist its bound
      endpoints, source hashes and clocks into the existing append-only W5
      forward row; event identity and QLedger authority remain unchanged.
  - path: tests/test_entry_radar_w5_reconciler.py
    what: >
      Add the prospective receipt, correction/retry, holiday, stale, tamper,
      non-finite and W5 consumer regressions to the existing CI-enrolled suite.
verified:
  - claim: Exact integrated candidate composes with current main and owning consumers.
    command: >
      python3 -m pytest -q --disable-warnings
      tests/test_entry_radar_w41_transport.py tests/test_entry_radar_w5_gates.py
      tests/test_entry_radar_w5_data.py tests/test_rates_command.py
      tests/test_yield_momentum.py tests/test_rate_inflation_transmission.py
      tests/test_entry_radar_w5_reconciler.py
    result: 300 passed, 290 warnings, exit 0 on integrated head 1fcc1fa4c69862fc6c21bf370f5dc6845f768017.
  - claim: Python syntax and diff hygiene pass.
    command: >
      python3 -m py_compile engine/rate_inflation_receipt.py
      scripts/build_transmission.py scripts/reconcile_entry_radar.py
      tests/test_entry_radar_w5_reconciler.py && git diff --check origin/main...HEAD
    result: exit 0.
  - claim: Current checkout input fails closed instead of fabricating fresh Phase22 context.
    command: >
      Build build_dfii10_owner_bundle() from canonical data/fred/DFII10.parquet
      at a fresh timezone-aware capture instant.
    result: >
      5932 rows; 2003-01-02 through 2026-09-17; source SHA256
      99984d0539e17de3e07aac6b7db7b80913ca43352084cfb701ff6ad9d2c7e2c2;
      latest 2026-09-17 2.61%, prior-five-session 2026-09-10 2.55%,
      delta +6bp; status STALE / STALE_AT_CAPTURE; all authority false.
unverified:
  - claim: Hosted exact-head CI and independent non-author review.
    what_would_verify: >
      Normal repository checks and substantive review on the final PR #7593 head.
  - claim: Natural production owner receipt and prospective Phase22 accrual.
    what_would_verify: >
      A live Transmission build with current source data followed by a real
      W5 event whose decision cut binds a QUALIFIED receipt before outcome.
unresolved:
  - >
    Phase22 still needs the existing owner-native same-cut C4_MTF_TURN@1.d2.turn
    snapshot durably bound to the immutable primary C2 event; current live payload
    has C4 context but W5 does not yet persist it.
  - >
    TrialLedger registration remains with Tactical R1-B PR #7274; this carrier
    does not edit data/trial_ledger.jsonl.
next_actions:
  - >
    Continue on a separate carrier with same-cut C4 context preservation through
    the existing C2 event -> spool -> W5 path, proving event_id stays identical
    and C4 remains stratification-only / never registered.
  - >
    After the Phase22 start-boundary inputs qualify, advance the pre-nominated
    multi-day leader-pullback baseline-versus-rates challenger on the same
    opportunities and common evaluation deadline.
do_not_redo:
  - "Do not redo merged nominal observation-origin PR #7291."
  - "Do not recreate policy/RIC/stance PR #7521 or overwrite Risk Radar PR #7029."
  - "Do not modify separate nominal-rate leader-reset PR #7418 from this lane."
  - "Do not rerun Research A V4, B Round2 or C Hardened V2 without an invalidator."
  - "Do not create a second rates store, receipt database, W5 ledger or evaluator."
danger_areas:
  - >
    Observation date is not provider release/first-known time; only the recorded
    owner capture clock is claimed prospectively.
  - >
    A stale receipt may preserve truthful endpoints but must remain unavailable
    for affirmative Phase22 regime assignment.
  - >
    C4 must be copied from the exact same-cut owner snapshot; recomputing it from
    later bars would leak future information into the experiment.
---

PR #7593 is the source carrier for this capability. It is Draft/HOLD-FOR-SOL:
source implementation and local proof exist, while merge, production deployment,
live source freshness, alpha and Phase22 experiment start remain separate gates.
