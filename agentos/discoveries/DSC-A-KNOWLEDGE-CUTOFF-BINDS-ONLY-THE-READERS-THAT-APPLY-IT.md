---
key: A-KNOWLEDGE-CUTOFF-BINDS-ONLY-THE-READERS-THAT-APPLY-IT
claim: >-
  The Finance read-model contract compares no date with the document's knowledge_cutoff, so a
  reading dated after the cutoff validates. Only the readers that apply the cutoff themselves
  are bound by it. After #8135, only the valuation anchor did. Every other reader of a dated
  owner row published rows dated after the cutoff: the operating reading, the expectations
  reading, the qualified price reading, the company cells, the source records, and the
  freshness drawn from them, and a conflict read the late readings it was given. The anchor
  also admitted an observation dated on the cutoff by as_of but observed or published after
  it, because it read as_of first. The shared rule that states this, feature.point_in_time
  in engine/sector_intelligence/contracts.py, belongs to feature_snapshot.v1, not to the
  Finance read model.
falsifier: >-
  `python3 -m pytest tests/test_finance_intelligence_projection.py -q -k "knowledge_cutoff or however_far_ahead"`
  passes (31). Swap in engine/sector_intelligence/finance_projection.py from 2a93791563bb
  (#8135's squash) and 28 must fail, each on an assertion after validate_contract accepted
  the document. The 3 that still pass are the valuation-observation as_of case, the
  world-valid test and the anchor's own cutoff test. If the swap passes, the readers already
  applied the cutoff and this record is wrong.
so_what: >-
  (1) Apply a knowledge cutoff once, at the input boundary, before any reader runs. The
  composer now reads its inputs through _known_at_cutoff, so a reader added later inherits
  the cutoff. A cutoff check inside one reader covers that reader only, and the contract
  will not catch the others.
  (2) Gate only the clocks that say when a row became knowable:
  - observations: as_of, observed_at and published_at;
  - company cells: those three and evidence_date;
  - source records: their source's published_at, observed_at and retained_at.
  Never gate the clocks that say when a row holds in the world: a report period,
  effective_at, business validity. A row can be known before the time it describes, such as
  a rate change announced today and effective next month.
  (3) The input digest still covers the owner's whole snapshot, so it still identifies which
  snapshot produced the document. A late row changes the digest and nothing else.
  (4) A sweep test that moves every clock past the cutoff is not enough. With every source
  record gone, every plane is withheld as unevidenced, so a leak through one input kind
  publishes nothing. A mutant that stopped gating market rows passed the sweep. Only a
  per-row differential caught it. That test adds one late row beside the base and asserts
  the document changes only in its digest. It then puts the same row on the cutoff and
  asserts the document changes, which proves the row is one a reader publishes.
  (5) Enforcing the rule in the Finance read-model contract, or in the shared base's
  evidence grammar (#7870), would refuse a composer regression at validation time. That is
  a contract change and is not made here.
kind: landmine
verified_at: 2026-09-28
verified_by: "tests/test_finance_intelligence_projection.py::test_nothing_dated_after_the_knowledge_cutoff_reaches_the_document (6 fixtures), ::test_a_row_dated_after_the_knowledge_cutoff_changes_nothing_but_the_digest (23 row and clock cases) and ::test_a_row_known_by_the_cutoff_is_read_however_far_ahead_it_holds. With the composer from 2a93791563bb, 28 fail after validate_contract accepts each document: all 6 sweeps (the walk finds the moved dates in the document) and 22 row cases (the late row changes the document). 17 mutants of the gate each fail only the tests that pin their piece: removing retained_at fails only the retained_at case, gating effective_at fails only the world-valid test, and an off-by-one fails every positive control."
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - tests/test_finance_intelligence_projection.py
confidence: verified
---

## How it was found

#8135 made the valuation anchor pass over an observation dated after the knowledge cutoff.
A census then asked every other reader of a dated owner row whether it applied the cutoff.
None did, and the contract accepted every document that published a late date.

## The fix

- `_known_at_cutoff` removes every owner row that any of its knowledge clocks dates after
  the cutoff, once, before any reader runs. A clock that is absent or does not parse says
  nothing, so how an undated row is read stays each reader's rule.
- The valuation anchor no longer applies its own cutoff. Nothing dated after the cutoff
  reaches it.
- The digest is computed over the owner's inputs, not the gated ones.

Related: [[DSC:A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE]] (the
same pattern for slice scope: one rule per input kind, applied where the input enters).
