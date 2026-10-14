---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/prophet-reflex-record-integrity-20260928
model: sol
prs:
- 8154
ended_because: ci_handoff
mission: Preserve Reflex writer metadata and bind cached registry rules to the requested
  source root before future risk-policy use. MISSION_COMPLETE:false.
state_before: The firing metadata repair was tested and CI-green, but the same module
  could return cached rules from a different registry root.
changed:
- path: engine/neuralweb/reflexes.py
  what: Bind the existing single-entry cache to resolved source path atomically; preserve
    metadata repair and explicit refresh contract.
- path: tests/test_reflexes.py
  what: Eleven registry-root tests plus unchanged selected writer/load cases.
- path: .github/ci/legacy-jobs.yml
  what: Append the new test class to the existing neural-web-core command.
- path: research/grey_deer/REFLEX_FIRING_METADATA_INTEGRITY_2026-09-28.md
  what: Record causal witness, proof, current CI limits and original policy gates.
verified:
- claim: The final tests distinguish wrong-root rule reuse and preserve prior writer
    semantics.
  command: python3.12 -m pytest tests/test_reflexes.py::TestRecordFiring tests/test_reflexes.py::TestLoadFirings
    tests/test_reflexes.py::TestRegistryRootIsolation -q
  result: Original 8 failures/23 passes; repaired31 passes. Synthetic isolated native
    module. Green log 61f0d6ff93d29e24d178e1c17bc116ace18799f56554829040a2426d15136468.
- claim: The earlier immutable R7 candidate completed its hosted CI.
  command: gh api repos/mastermindx-market-intelligence/macro/actions/runs/36430924429
  result: Run completed success for98b2fa535551eecd407aa7ea54afc0070d94d179; not new
    R8 acceptance.
unverified:
- claim: New-head source release and ordinary production behavior.
  what_would_verify: Concluded current integration/CI, accepted self-audit and ordinary
    native producer/reader evidence.
unresolved:
- No live risk-policy authority or predictive performance follows from evidence metadata
  or source-root isolation.
- Same-path registry content refresh remains explicit force/invalidate, not a new
  hot-reload capability.
- Current-base CI source/artifact/manifest inspection refusals remain; no retry or
  proxy.
- GD6A#8141 stays separately frozen and unmerged.
next_actions:
- Consume actual new-head CI and named findings without source churn for ancestry
  alone.
- Qualify the same source for release, then ordinary producer/reader behavior.
- Bind first nonzero policy through the existing grant/scope/evidence/expiry owners;
  do not infer a grant from the cache.
do_not_redo:
- Do not rewrite historic firing records or alter the claim ID algorithm.
- Do not change rankings, policy thresholds, portfolios, source collectors or schedulers.
- Do not repeat accepted GD6A tests or seize other research seats.
danger_areas:
- A context-only marker is not financial authority or proof of single-writer admission.
---

# R8 same-PR source-integrity continuation

MISSION_COMPLETE:false. No source-writer release, live policy or background execution is claimed.
