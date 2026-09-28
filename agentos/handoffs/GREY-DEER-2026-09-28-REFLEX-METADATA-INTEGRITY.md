---
workstream: WS:GREY-DEER-RISK-INTELLIGENCE
session: claude/prophet-reflex-record-integrity-20260928
model: sol
prs: []
ended_because: ci_handoff
mission: Fix the existing Reflex firing metadata contract before future risk-policy
  evidence reuses it. MISSION_COMPLETE:false.
state_before: Caller payload could overwrite five documented writer-owned metadata
  fields in the actual append function.
changed:
- path: engine/neuralweb/reflexes.py
  what: Preserve canonical metadata after merging the caller payload without changing
    ordinary bytes.
- path: tests/test_reflexes.py
  what: Five methods / twelve additional cases for reserved fields and compatibility.
- path: .github/ci/legacy-jobs.yml
  what: Register only writer/reader classes in existing neural-web-core job.
verified:
- claim: Reserved-field regression and ordinary byte compatibility are discriminated.
  command: python3.12 -m pytest tests/test_reflexes.py::TestRecordFiring tests/test_reflexes.py::TestLoadFirings
    -q
  result: Original 10 failures/10 passes; repaired 20 passes, synthetic isolated source
    module.
unverified:
- claim: Source release and production behavior.
  what_would_verify: Real hosted/current-base acceptance and normal release with original
    telemetry behavior preserved.
unresolved:
- No active policy grant or predictive claim is conferred by this metadata repair.
- 'GD6A #8141 remains separately frozen pending its actual compatibility qualification.'
next_actions:
- Read exact branch/PR results and resolve actual CI findings.
- Do not use this operation to retry the separately refused GD6A compatibility read.
do_not_redo:
- Do not rewrite historic firing records or alter the claim ID algorithm.
- Do not change rankings, policy thresholds, portfolios, source collectors or schedulers.
- Do not repeat accepted GD6A tests or seize other research seats.
danger_areas:
- A context-only marker is not financial authority or proof of single-writer admission.
---

# Same Grey Deer program, bounded prerequisite repair

MISSION_COMPLETE:false. Existing parent #6817 retains integration responsibility. No production effect or background worker is claimed.
