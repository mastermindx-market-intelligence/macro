---
key: A-DISTINCTION-IN-AN-UNRENDERED-FIELD-IS-NOT-A-DISTINCTION
claim: >
  A composition can return two different status values for two cases whose USER-VISIBLE
  consequence is identical, and a test asserting the status field will pass while the
  obligation it claims to enforce is unmet. Measured twice inside one function: a
  `limited` section and a `refused` section carried different statuses and withheld the
  SAME dependent prose, so "distinct required refusal versus optional limitation"
  (IND-R215) held only in a field no renderer reads; and a correctly-refused
  physical-production field degraded the page verdict to `qualified`, making every
  correctly-scoped service company report itself partially evidenced.
falsifier: >
  Revert engine/company_intelligence/financial_dossier.py's three-state prose (make a
  `limited` dependency blocking, as `status != "ready"` rather than `== "refused"`) and
  observe tests/test_industrials_financial_dossier.py::
  test_ind_r215_dossier_view_distinctness FAIL on the prose comparison while every
  section-status assertion in the file still passes. Then remove
  _NON_EVIDENCE_LIMITATION_PREFIXES from the page-verdict computation and observe
  test_ind_sf04 fail on `status == "ready"` while its refused_fields assertion passes.
so_what: >
  Before writing a test for an absence/refusal obligation, run the compliant and
  violating inputs through the real code and print what a CONSUMER would get - is the
  text readable, is the number present, does the page claim success - not the status
  field you just wrote. If the two rows differ only in a label, the distinction is not
  made yet and a test asserting the label guards nothing. Two corollaries: not every
  limitation is an evidence limitation, so a page-level verdict must be computed from
  the subset that actually means something is missing; and when you exclude a class from
  a verdict, assert BOTH that the excluded thing is still DISCLOSED and that the verdict
  is not degraded, or the exclusion silently widens.
kind: landmine
verified_at: 2026-09-29
verified_by: >
  PR #8213 (squash 28a3ab1e7cb2), which delivered assemble_evidence_view for IND-D23, IND-R201,
  IND-R215, IND-R218 and IND-SF04. Both defects were found by a side-by-side probe with
  the all-present control asserted first, BEFORE any test existed. 11/11 mutants caught
  afterwards; the eleventh survived its first attempt for a related reason - the
  page-verdict assertion was reached by the withheld-prose route rather than the
  refused-section route, so a view ignoring refused sections entirely still passed.
scope:
  - engine/company_intelligence/financial_dossier.py
  - tests/test_industrials_financial_dossier.py
  - WS:GMI-INDUSTRIALS-FIRST-VERTICAL
confidence: verified
---

The two defects are the same error at two altitudes, and both are cheap to catch and
expensive to leave: writing the producer and its test in one sitting makes the test
assert the field just added rather than the outcome the obligation is about.
`status == "limited"` is trivially true because you wrote the string. "The reader can
still see the cash story" is the actual claim, and it is a different one.

The third clause of IND-D23 ("no all-page false success") and IND-R201's
("no full-vertical acceptance") are both claims about the PAGE rather than a section, so
a section-level view cannot express them at all - which is why the composition needed a
page-level `status` before either row could be more than an anchor over nothing. That is
the same scope error as
[[DSC:A-VENDORED-TRACEABILITY-MAP-STILL-HAS-NO-REQUIREMENT-TEXT]] one level down:
an instrument's reach silently deciding a conclusion's reach.
