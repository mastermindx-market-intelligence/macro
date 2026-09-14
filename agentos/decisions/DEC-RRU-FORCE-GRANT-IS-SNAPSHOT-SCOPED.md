---
key: RRU-FORCE-GRANT-IS-SNAPSHOT-SCOPED
question: Can corrected Risk Radar arithmetic inherit an earlier construction's force grant?
answer: >
  No. Qualify effective snapshot permission through one pure predicate in the existing
  audit owner, at both grant attachment and market-state consumption. No composition-
  bearing construction is promoted by this integrity release. Preserve reported old
  evidence as provenance and preserve legacy snapshots, named policies and independent
  restrictions. An inapplicable current grant is not a policy-release event.
rationale: >
  The reproduced error is a stateless per-snapshot ceiling, not a policy lifecycle.
  Its consumer has no policy ID, expiry or previous-policy input. Requiring a new
  restriction store to repair that error would duplicate authority; silently carrying
  the old grant into a new method would manufacture validation. Real installed policy
  transition/cutover evidence remains required before production release.
alternatives:
  - option: Copy the old grant because the method retains the same market key.
    why_not: Market identity does not establish construction-compatible validation.
  - option: Clear every grant or existing restriction globally.
    why_not: That changes proven legacy behavior and can release independently owned protection.
  - option: Create a Risk Radar restriction store to retain every past ceiling.
    why_not: A new policy lifecycle is neither required by the stateless defect nor authorized here.
evidence:
  - research/grey_deer/RRU_FORCE_APPLICABILITY_SCOPE_2026_09_09.md
  - python3 research/grey_deer/RRU_FORCE_VERIFY_2026_09_09.py --full-modules
  - python3 research/grey_deer/RRU_FORCE_BLOCK_TESTS_2026_09_09.py --baseline-blocks
  - python3 research/grey_deer/RRU_FORCE_BLOCK_TESTS_2026_09_09.py
affects:
  - "WS:GREY-DEER-RISK-INTELLIGENCE"
  - engine/risk_radar_intl_audit.py
  - engine/market_state.py
  - engine/intl_run.py
  - research/grey_deer/RRU_COMPOSITION_EDGE_TESTS_2026_09_08.py
confidence: high
reversibility: easy
decided_by: ceo-sol
decided_at: 2026-09-09
---

This amends only the old candidate edge test's expectation that a modern reading
retains effective legacy authority. Raw-input immutability remains required. The
original release-counterexample test is preserved and now must pass; it is not waived.
No production policy object, grant, history row or deployed source changes here.
The frozen Risk Envelope v0 source emits no policies; that is NOT a live policy census.
The predicate's future expansion requires reviewed construction-specific promotion;
a caller-supplied method name, 'reviewed' label or scorecard boolean cannot enable it.
