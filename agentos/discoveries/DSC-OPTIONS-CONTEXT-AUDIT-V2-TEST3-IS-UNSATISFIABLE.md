---
key: OPTIONS-CONTEXT-AUDIT-V2-TEST3-IS-UNSATISFIABLE
claim: >
  At Macro main 01f86f7d7431 (charter blob 4f321e614a6adf48), acceptance test 3
  of the v2 charter cannot pass on a correct implementation. The receipt must
  bind the run manifest (run digests, run count; l.130) and the observed peak
  RSS, CPU seconds and wall seconds (l.131). Yet test 3 (l.208) and l.143
  require identical receipt bytes across chunk-size changes, run-partition
  changes and replays. Test 3 also requires input reorder to give identical
  output, while l.110, l.141, l.167 and test 4 (l.209) require reorder to refuse.
falsifier: >
  A charter revision (a new blob) whose determinism test is stated over a defined
  canonical projection that excludes run-observed fields (run manifest, resource
  observations), and whose reorder rule agrees with test 4. Or a re-read of blob
  4f321e614a6adf48 showing that l.130-131 do not place run-observed values inside
  the receipt bytes test 3 compares.
so_what: >
  No implementation child can honestly report test 3 green against this blob. A
  "pass" means the child reinterpreted the preregistration in place, which the
  2026-08-13 adjudication (l.189-193) forbids, and any correct replay trips
  REPLAY_MISMATCH (charter l.176). Repair the test text before acceptance; it is
  a must-close gate. More generally, any receipt that records observed resources
  or run identity must state determinism over a named canonical projection, not
  over whole-receipt bytes.
kind: landmine
verified_at: 2026-10-22
verified_by: >
  Independent READ_ONLY Claude Opus audit of the v2 charter staged at Macro main
  01f86f7d7431 (finding 4; check C row 3 "Unsatisfiable as written"; check F
  must-close gate "Test 3 repair"). Seat ruling D89. Review record:
  research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_REVIEW_2026-10-22.md.
scope:
  - macro
  - "WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2"
  - research/options_estate/OPTIONS_CONTEXT_AUDIT_PREREG_V2_CHARTER_2026-09-22.md
confidence: verified
expires: 2026-11-22
---

## Evidence qualification

This verifies the charter text at blob 4f321e614a6adf48. It does not cover any
implementation, benchmark or later charter revision. It says nothing about
whether the other acceptance tests can fail on a wrong implementation; the review
record covers that per test (check C). The "interrupted writes" case named at
charter l.221 is part of the same test-3 repair.

## Continuation

Repair owner: the WS owner coo-fable, under
DSC:OPTIONS-CONTEXT-AUDIT-V2-ACCEPTOR-IS-SOL-NOT-SEAT. Acceptance of the repaired
text belongs to Sol or a recorded delegation. This discovery authorizes no
charter edit and no implementation-child admission.
