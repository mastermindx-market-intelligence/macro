---
key: REGIME-TESTS-WERE-GRANDFATHERED-CI-DARK
claim: >
  At macro e4d6bf36da7a8960ea46010a085fc46db854bdc1, all four W0 regime test files
  were grandfathered unrun suites, so local82-test success was not normal CI coverage.
falsifier: >
  Resolve workflow run bodies with scripts.audit_unrun_tests._workflow_blob at that
  immutable head; finding an actual run reference to all four suites disproves the claim.
so_what: >
  Preserve the same-PR repair registering these suites in code-gated unrun-scoring-engine and removing
  only their four baseline entries; never infer executed regression coverage from green
  packs before this registration, and verify actual test execution separately from planning.
kind: landmine
verified_at: 2026-09-09
verified_by: >
  python3 -B -m pytest tests/test_regime_one.py::test_hmm_history_suites_are_named_by_real_ci_run_steps -q
  failed on e4 source and passed after one existing-job command/dependency amendment;
  the final four-file focused command passed88 tests and the amended real job step
  passed105 (PR #7015); the added gate=code regression failed before lane repair.
scope: [macro, WS:REGIME-HISTORY-HONESTY]
confidence: verified
---

The correction adds no workflow, runner, job, gate bypass or baseline exemption. It extends
one existing code-gated scoring-engine pytest command and declares the tested hmmlearn0.3.3 dependency.
The current candidate needs fresh exact-delta review and hosted checks; a local planner
validation is not evidence that the remote pack actually executed these tests.

The intermediate1269 candidate registered them only in gate:data, which runs after the nightly, not
as a PR merge condition. R3 correctly identified that distinction. The final correction restores
unrun-macro-panels and moves registration to gate:code; no entire data-health job is promoted.
