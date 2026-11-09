---
key: A-MUTATION-THAT-DOES-NOT-KILL-IS-USUALLY-MISTARGETED
claim: >
  When a mutation of repaired production code fails to kill any test, the first hypothesis must be
  that the mutation missed the path the tests actually drive - not that the tests are weak; and
  resolving which reveals coverage gaps that a fully green suite hides. Measured 2026-09-25 on
  Mastermind IAC-P1 C-A-4, where an UNCERTAIN carrier read must degrade to
  `CARRIER_RECONCILIATION_REQUIRED` with no body on two symmetric legs (question and answer).
  Replacing ONLY the question leg's assignment left the entire 1977-test suite green. Replacing BOTH
  killed both of the slice's named C-A-4 tests. So the mutation had been aimed at the leg no test
  drives: the behaviour was implemented correctly on both legs, but only the answer leg was pinned,
  and the question-leg line could have been deleted in a later refactor with the suite staying green.
  A per-leg gap of this kind is invisible to a suite-level pass/fail, to a failure-name differential,
  and to an exact-count reconciliation, because nothing is failing or missing - the coverage simply
  does not reach one branch of a symmetric pair.
falsifier: >
  For N symmetric guards, mutate them ONE AT A TIME rather than as a group, and record which named
  test dies for each. A guard whose solo mutation kills nothing is unpinned. To confirm the mutation
  was well-aimed rather than the test weak, mutate the remaining guards too: if the group mutation
  kills tests that no single mutation kills, the tests are carried by the other legs and the coverage
  gap is real. Guard the gap from OUTSIDE the tree under audit and control the new falsifier at three
  points - FAIL at the parent, PASS at the repaired head, FAIL under the one-leg mutation - since a
  falsifier that cannot tell one leg from two does not close the gap it was written for.
  Historical targets: integrations/company_consultation_dispatch.py and instrument_p1c.py, with the per-leg controls recorded in https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828478882.
so_what: >
  Group mutations systematically overstate coverage on any code with symmetric branches - both legs of
  a two-sided refusal, each field of a validated set, every arm of a fan-out. A reviewer who mutates
  in groups concludes the repair is well-tested when half of it is unpinned. Report such a gap as a
  coverage finding against correct behaviour, not as a defect, and close it with an instrument rather
  than by hand-editing the slice under review: editing the tree you are auditing destroys the
  independence that made the review worth anything.
kind: landmine
verified_at: 2026-09-25
verified_by: >
  Historical author-recorded verification dated 2026-09-25; supporting receipt: https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828478882.
  The C-A receipt records the surviving question-only mutation, failing both-leg mutation, and external f8 discriminator controlled at parent/current/one-leg-mutant. Production behavior was correct; the finding concerned coverage.
scope:
  - "Mastermind historical IAC-P1 C-A-4 donor evidence (2026-09-25)"
  - "integrations/company_consultation_dispatch.py"
  - "historical instrument_p1c.py"
confidence: verified
---

## Historical provenance — 2026-09-25

The measurements, confidence and verification date above describe the original September 25 observation. The November 6 record repair validates document structure and preserves source references; it does not rerun the historical experiment or establish current runtime behavior. The supporting [original receipt](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5828478882) records the historical evidence.

The [later canonical lineage ruling](https://github.com/mastermindx-market-intelligence/Mastermind/pull/600#issuecomment-5841164702) designated claude/iac1-p1-packet-carriage-20260925 as **DONOR_TEST_EVIDENCE / DO_NOT_PUBLISH_AS_P1**, with [Mastermind #986](https://github.com/mastermindx-market-intelligence/Mastermind/pull/986) the canonical P1 carrier. Its held C-D child remained STOP / DO_NOT_PUBLISH. These knowledge records grant no transplantation, installation, live-packet or replay authority; all original refused or uncertain effects retain their original target and reconciliation boundary.
