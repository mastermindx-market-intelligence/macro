---
key: MAS28-MISSING-INVALID-WIRE
claim: >
  At Macro f9ed175800257b228166dabe8b3ac9a55e74e237, a real header missing Linear
  but containing invalid Authority and Completion values makes the validator reject
  its own semantic report as TYPE_MISMATCH. Null normalization conflates invalid
  present values with literal omissions in the R001 consistency check.
falsifier: >
  Run pytest tests/test_pr_linkage_hostile_regressions.py::test_missing_field_and_present_invalid_values_remain_distinct_on_report_wire against
  the frozen pre-repair validator: the claim is disproved if it returns a valid
  report with R001 missing_fields exactly Linear and retains R011 and R012.
so_what: >
  Keep source presence distinct from normalized value validity. Preserve the full
  null set for canonical-state checks, while subtracting validated present-invalid
  field evidence only for the exact R001 literal-omission comparison.
kind: landmine
verified_at: 2026-10-04
verified_by: >
  Frozen macro #7039 body SHA256 8ea8b94b161547c5ee4cfe452faa204c92ce258104e745017cbcf96d0282970a;
  discriminating RED regression, b09fea5f6d3fb8c1c3cc686dc2247fd15ba8f5d0 repair,
  456 passing PR-linkage tests, and immutable before/after calibration artifacts.
scope:
  - macro
  - MAS-28
  - lib/pr_linkage_validator.py
confidence: verified
---

The repair does not validate the invalid values. The same input now returns an
incomplete `REFUSE_METADATA` report with R001, R011 and R012 intact. The five independent
oversized-body refusals remain unchanged; their inputs must not be truncated to obtain
more favorable calibration counts.
