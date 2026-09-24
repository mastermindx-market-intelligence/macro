---
workstream: WS:RATES-INFLATION-COMMAND
session: claude/rates-policy-constituents-20260924-sol-002
model: sol
ended_because: ci_handoff
mission: >
  Preserve rate-futures contract evidence through the existing collector/store
  and RIC consumer, separating matched-contract changes from rolling-horizon
  reweighting without granting forecast or trading authority.
state_before: >
  RD1 failed its directional benchmark. Existing policy curves retained only
  interpolated values; a moving horizon could be misread as pure repricing.
changed:
  - path: collectors/rate_futures.py
    what: Preserve same-download contract identity, weights and paired evidence; refuse unidentified batch quotes.
  - path: engine/rate_futures_repricing.py
    what: Validate generations, dates, contract semantics and exact symmetric repricing/roll attribution.
  - path: engine/rates_inflation_command.py
    what: Add policy_path_repricing after existing stance construction without changing scoring inputs.
  - path: tests/test_rates_command.py
    what: Test arithmetic, nulls, clocks, torn generations and actual collector/store/RIC integration in the existing suite.
  - path: research/RATES_POLICY_CONSTITUENTS_2026-09-24.md
    what: Record exchange conventions, scope, source identities, evidence limits and continuation.
verified:
  - claim: Targeted regression suite passes after discriminating RED cases.
    command: python3 -m pytest tests/test_rates_command.py tests/test_fed_path.py tests/test_yield_momentum.py -q --disable-warnings --tb=short
    result: 137 passed, 301 warnings; synthetic/no-network source and consumer proof.
  - claim: Existing numeric curve values and legacy reader remain compatible.
    command: test_rd2_native_collector_and_store_roundtrip in tests/test_rates_command.py
    result: Original m1/m3/m6/m12 columns equal exactly; native validate/upsert/read and attribution pass.
  - claim: RIC actually consumes the new measurement without changing its stance.
    command: test_rd2_ric_real_consumer_preserves_stance in tests/test_rates_command.py
    result: Synthetic month roll plus repricing reaches the RIC artifact; stance equality passes.
unverified:
  - claim: Current production data reaches the candidate consumer.
    what_would_verify: Captured native raw quote input, source identity and non-mocked candidate read; later deployed proof remains separate.
  - claim: Independent review, concluded CI, merge and browser proof.
    what_would_verify: Exact-head non-author review, concluded repository checks and lawful release with production/browser receipts.
  - claim: Historical first-known policy curves or a forecasting edge.
    what_would_verify: Qualified source-owner knowledge clocks and separately registered prospective forecasting experiments.
unresolved:
  - Native current-input qualification and held-7521 composition proof are next; no live source result is claimed yet.
  - Upstream quote completion and exchange-settlement authentication remain unknown.
  - Parent predictive model remains rejected; RD2 is measured context, not a replacement positive backtest.
next_actions:
  - Freeze and publish this exact candidate; preserve the original RD1 study and current repair carrier.
  - Test non-mocked current raw quotes and private exact-source composition with held 7521 without mutating that carrier.
  - Obtain independent review and exact-head CI before any source release or production claim.
do_not_redo:
  - Preserve RD1 freeze 8796829eea9fe8792a73155f64d5c1dbe83ae3b6 and all 48 original trials and negative results.
  - RD1 maintenance head 748067a3631959e2dd6ffe25ebc7675ed82395ee only repairs import pinning; no experiment rerun.
  - Do not overwrite or release held 7521, 7593, 7418, 7400, 7320, 7877 or Mastermind 769.
  - No new collector, source archive, calendar, trial ledger, forecast service or control plane.
danger_areas:
  - Matched-contract movement includes fixings and risk premia; it is not pure future-policy repricing or a causal shock.
  - Captures and hashes do not authenticate exchange settlement or historical information availability.
  - The canonical parquet store holds latest vintages; no immutable prospective archive is claimed.
  - Whole-month interpolation centres remain legacy approximations, not exact reference-period midpoint estimates.
  - Same-day captures never become qualified merely because wall time advances; recapture is needed.
---

# Cumulative working checkpoint

MISSION_COMPLETE: false. Capability state: BUILT_NOT_PROVEN.
This is source custody/evidence continuity, not a worker lifecycle or release.

Authority: Chairman's standing end-to-end delegation and current continuation.
Procedure pin: Mastermind 1a7d400294b0d37c460b963b8865b40a23173b58,
compatible Skillpack 1.0.1/bootstrap1.
Base: b7d6914db7d8ef6e810500926764e18b85f01348.
Operation: rates-policy-constituents-20260924-sol-002.
Branch: claude/rates-policy-constituents-20260924-sol-002.
Workspace: /Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/rates-policy-constituents-20260924-sol-002.

This is an independently reviewable source slice under the existing parent PR7909,
not a replacement for its frozen research carrier. The Macro native sparse owner
created this workspace from fresh origin/main using committed hook blob
42119c614330a04fedcbf00a299d34c68a69e327; the occupied primary checkout was not edited.

No external child/reviewer has STARTed, no watcher or automatic wake exists, and
no unresolved modifying effect remains at this checkpoint. No model trial, trade,
forecast publication, vendor purchase or existing production data mutation ran.
Source tests use explicitly synthetic quotes and isolated temporary stores.

The added source field is outside held7521's normalization and before no scoring
or stance decision: the artifact is enriched only after the existing stance is built.
Held7521 retains its own exact source/review/release authority and remains untouched.
