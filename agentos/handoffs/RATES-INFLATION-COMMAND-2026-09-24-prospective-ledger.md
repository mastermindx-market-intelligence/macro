---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-direction-prospective-ledger-20260924-sol-004
model: sol
prs: [7940]
ended_because: ci_handoff
mission: >
  Preserve #7923 policy-path matched-contract/roll measurements prospectively
  through the existing RIC nightly keep-FIRST ledger without creating a second
  ledger, forecast, score or trade authority.
state_before: >
  RIC forward_log.jsonl retained coarse flags and legacy implied-path fields but
  dropped policy_path_repricing, so the new measurement could not accrue as
  first-known prospective evidence.
changed:
  - path: scripts/build_rates_command.py
    what: >
      Additively copies the already-qualified policy_path_repricing block into
      the incumbent nightly keep-FIRST stamp with no recomputation.
  - path: tests/test_rates_command.py
    what: >
      RED/GREEN regression proves exact measurement retention, authority false,
      and same-night correction cannot rewrite the first row.
  - path: research/RATES_DIRECTION_PROSPECTIVE_LEDGER_2026-09-24.md
    what: >
      Records capability, evidence boundary, dependency and production proof law.
verified:
  - claim: The missing prospective measurement is now retained and immutable per asof night.
    command: >
      python3 -m pytest
      tests/test_rates_command.py::TestForwardLogLane::test_forward_log_freezes_policy_repricing_measurement_keep_first
      -q --disable-warnings --tb=short
    result: >
      RED before source repair with KeyError policy_path_repricing; GREEN after
      additive field copy, 1 passed.
  - claim: Existing rates/RIC behavior remains compatible on the stacked candidate.
    command: >
      python3 -m pytest tests/test_rates_command.py tests/test_fed_path.py
      tests/test_yield_momentum.py -q --disable-warnings --tb=short
    result: 148 passed, 301 warnings.
unverified:
  - claim: PR #7923 is independently accepted and released.
    what_would_verify: >
      Non-author source/financial-semantics PASS on its exact accepted head plus
      normal source release proof.
  - claim: A natural nightly has frozen the measurement in production.
    what_would_verify: >
      Real production readback of one nightly keep-FIRST row whose
      policy_path_repricing matches the same-run RIC artifact and source receipts.
unresolved:
  - This slice is dependency-held on #7923 and must not be released ahead of it.
  - GDPNow intra-quarter full-vintage sourcing remains a separate source-owner dependency.
next_actions:
  - Publish this as a Draft/HOLD stacked PR based on #7923 and obtain normal CI/review.
  - After #7923 acceptance, rebase/retarget without changing the keep-FIRST evidence law.
  - After lawful release, prove one natural nightly input-to-forward-row readback before calling prospective accrual live.
do_not_redo:
  - Do not create another rates-direction ledger or feature archive.
  - Do not rerun or tune RD1; its negative result and 48 registered trials remain final for that construction.
  - Do not install the superseded sandbox RD2 implementation.
  - Do not reinterpret policy_path_repricing as a causal policy shock or trading signal.
danger_areas:
  - Keep-FIRST is evidence law; same-night corrections must not mutate the row.
  - The copied block may truthfully be unavailable/partial and must remain so.
  - Stacked source does not imply #7923 review, merge, deployment or production proof.
---

FINALIZATION_CLASSIFICATION: CHECKPOINTED_CONTINUATION
MISSION_COMPLETE: false
CAPABILITY_STATE: BUILT_NOT_PROVEN

This bounded slice closes the prospective-retention implementation gap only.
Parent rates-direction intelligence remains incomplete. No external worker or
watcher was started, no production data was mutated, and no empirical model trial
was run. The exact dependency base is #7923 at
`dbf8d03ed4f2a29ea349bb37a23b9048f18bc2db`. Source carrier is Draft/HOLD Macro
PR #7940; first implementation commit `6791be6e01bfc608217a8ff3972d09ec6c50e422`.
