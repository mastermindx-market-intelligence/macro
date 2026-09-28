---
key: A-SLICE-WIDE-REF-LIST-VOUCHES-FOR-A-VALUE-BORROWED-FROM-ANOTHER-SLICE
claim: >-
  In the Finance read model, a plane's evidence_refs is the union of its slice's owner refs,
  not the refs of the reading the plane publishes. So a check of where a slice's refs come
  from cannot see a VALUE that crossed slices. The valuation plane took its anchor from the
  first valuation observation of whichever financial packet iterated last, with no slice
  scope. A probe gave ach_instant_b2b a qualified price basis of its own: the
  EARNINGS_UP_P_E_DOWN fixture, with card_networks' market rows copied under an ach source.
  ach then published card_networks' P/E of 18.0 as its OBSERVED valuation, although that
  observation is tagged slice_id card_networks. The reading cited only ach's own ref. The
  contract accepted the document. The per-slice ref oracle of #8134
  (`_refs_outside_their_slice`) found nothing outside its slice. Constraints had a sibling
  defect. They followed a slice_id extra outside the source record schema instead of
  business_scope. A foreign extra published a constraint under a slice its record is not
  filed under, and a record carrying no extra had its constraints dropped.
falsifier: >-
  `python3 -m pytest tests/test_finance_intelligence_projection.py -q -k "anchors_only_the_slice or freshest_anchor or constraint_is_published"`
  passes (3). Swap in engine/sector_intelligence/finance_projection.py from f6dae649ee6d and
  all 3 must fail. Put back only the constraints scope (business_scope reverted to the
  slice_id extra) and only the constraint test must fail. If the swap passes, the reads
  were already scoped and this record is wrong.
so_what: >-
  (1) A ref oracle proves where a plane's CITATIONS come from, never where its VALUE comes
  from, whenever the ref list is wider than the reading. Every per-slice read path in a
  composer needs its own scope test. The test plants an input filed under another slice
  and asserts this slice does not publish it. A green per-slice ref oracle says nothing
  about values.
  (2) Use one scope rule per input kind, on every path:
  - Source records: by business_scope, the schema field, which is also the slice their
    refs are filed under.
  - Observations: by the slice they are tagged with, or untagged, which means company data.
  The operating plane and the conflict detector already applied the observation rule.
  The valuation anchor applied none, and constraints read a non-schema extra. When a
  per-slice builder reads an input list, check that it applies the rule for that kind.
  (3) The structural fix is per-reading evidence, where each published value names its
  own observation. That grammar is the shared base's evidence_claim.v1 (#7870), and Finance
  adopts it in the later integration wave (DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF).
kind: landmine
verified_at: 2026-09-28
verified_by: "tests/test_finance_intelligence_projection.py::test_a_valuation_observation_anchors_only_the_slice_it_is_filed_under, ::test_the_valuation_plane_reads_its_slices_freshest_anchor and ::test_a_constraint_is_published_under_the_slice_its_record_is_filed_under (all 3 fail with the composer from f6dae649ee6d; reverting only the constraints scope fails only the last); probe on #8134's head d275a9e72654: the borrowed-P/E document validates and _refs_outside_their_slice returns []; probe on f6dae649ee6d: a constraint on the card_networks record is dropped with no extra, and is published under issuer_processing, citing the card_networks record, with a slice_id extra of issuer_processing"
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - tests/test_finance_intelligence_projection.py
confidence: verified
---

## How it was found

The round-1 review of #8134 flagged the constraints scope. The valuation anchor turned up
next, in a census of the anchor each slice's valuation plane publishes and whether that
anchor is the slice's own.

## The fixes

- **Anchor.** The anchor is now the slice's freshest valuation observation: one tagged
  with the slice, or an untagged one. An observation tagged with another slice never
  anchors it, however fresh.
- **Anchor order.** The old code also published whichever of a slice's observations came
  first. A test now reads both orders.
- **Constraints.** A constraint is published under its record's business_scope.

Related: [[DSC:A-MINTED-REF-SATISFIES-A-MIN-ITEMS-RULE-THE-EVIDENCE-DOES-NOT]] (so_what 2:
the pooled and per-slice ref oracles; this record is where the per-slice one stops).
