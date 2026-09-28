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
  (`_refs_outside_their_slice`) found nothing outside its slice. Two sibling defects sat on
  the same line. Constraints followed a slice_id extra outside the source record schema
  instead of business_scope: a foreign extra published a constraint under a slice its record
  is not filed under, and a record carrying no extra had its constraints dropped. And the
  conflict detector gathered each plane's observations again and chose by its own rule: the
  freshest one carrying a direction, dated by as_of alone, an undated one counted as the
  freshest, and no price-basis filter on market rows. So a conflict could judge a direction
  from an observation its plane never published.
falsifier: >-
  `python3 -m pytest tests/test_finance_intelligence_projection.py -q -k "conflict_reads_the_direction or absent_or_null_slice_tag or slice_tagged_valuation or after_the_knowledge_cutoff or anchors_only_the_slice or freshest_anchor or undated_valuation or constraint_is_published"`
  passes (9). Swap in engine/sector_intelligence/finance_projection.py from f6dae649ee6d and
  all 9 must fail. Put back only the constraints scope (business_scope reverted to the
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
    Only an absent or null tag is untagged. Any other value that is not the slice's id,
    an empty string or a malformed non-string included, files the observation elsewhere.
    An untagged observation reaches every slice, from whichever packet it sits in, so a
    composition that carries several companies' packets would need a company scope too.
  When a per-slice builder reads an input list, check that it applies the rule for that kind.
  (3) Select each reading once. A plane selects the observation it publishes, and anything
  that judges that plane (the conflict detector) reads that same observation. A second
  selection over the same list drifts from the first as soon as either rule changes, and
  the drift is invisible in the document: the conflict names a direction the plane does not
  show. Tests pin it by planting a second observation that the plane passes over, with the
  opposite direction, in both orders.
  (4) The structural fix is per-reading evidence, where each published value names its
  own observation. That grammar is the shared base's evidence_claim.v1 (#7870), and Finance
  adopts it in the later integration wave (DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF).
kind: landmine
verified_at: 2026-09-28
verified_by: "tests/test_finance_intelligence_projection.py::test_a_valuation_observation_anchors_only_the_slice_it_is_filed_under, ::test_the_valuation_plane_reads_its_slices_freshest_anchor, ::test_an_undated_valuation_observation_never_anchors, ::test_only_an_absent_or_null_slice_tag_means_company_data, ::test_on_one_date_the_slice_tagged_valuation_observation_anchors, ::test_a_valuation_observation_dated_after_the_knowledge_cutoff_never_anchors, ::test_a_conflict_reads_the_direction_of_the_valuation_reading_the_plane_publishes, ::test_a_conflict_reads_the_direction_of_the_price_reading_the_plane_publishes and ::test_a_constraint_is_published_under_the_slice_its_record_is_filed_under (all 9 fail with the composer from f6dae649ee6d; reverting only the constraints scope fails only the last); probe on #8134's head d275a9e72654: the borrowed-P/E document validates and _refs_outside_their_slice returns []; probe on f6dae649ee6d: a constraint on the card_networks record is dropped with no extra, and is published under issuer_processing, citing the card_networks record, with a slice_id extra of issuer_processing"
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - tests/test_finance_intelligence_projection.py
confidence: verified
---

## How it was found

The round-1 review of #8134 flagged the constraints scope. The valuation anchor turned up
next, in a census of the anchor each slice's valuation plane publishes and whether that
anchor is the slice's own. The round-1 review of #8135 then found that the conflict
detector still chose its own valuation observation, so it could judge a direction the
anchored plane did not publish. It also found three narrower gaps in the new anchor rule:
a falsy tag counted as untagged, a same-date tie fell to the owner's order, and an
observation dated after the knowledge cutoff could anchor.

## The fixes

- **Anchor.** The anchor is now the slice's freshest dated valuation observation: one
  tagged with the slice, or an untagged one. An observation tagged with another slice never
  anchors it, however fresh.
- **Undated observations.** An observation with no date never anchors. The anchor's date
  is published as the slice's information clock, which the contract requires. The first
  version of this fix sorted an undated observation as the freshest. That refused the
  whole document in either order, where main refused it only when the undated observation
  came first.
- **Anchor order.** The old code also published whichever of a slice's observations came
  first. A test now reads both orders.
- **Untagged.** Only an absent or null slice tag means company data.
- **Same date.** On one date, the observation tagged with the slice anchors over an
  untagged one. Between two at the same specificity, the later in the owner's order anchors.
- **Cutoff.** An observation dated after the knowledge cutoff never anchors.
- **Conflicts.** Each plane selects its reading once. The conflict detector reads the
  direction of the operating reading, the valuation anchor and the qualified price reading
  that the planes publish. Against this PR's previous head, a differential over 400 random
  compositions found every operating and valuation plane identical, every other conflict
  identical, and no P/E conflict set moved. Its operating observations took any date,
  direction and valid tag. Its valuation observations were tagged, on distinct dates up to
  the cutoff, so it does not exercise the new tie and cutoff rules; the tests above do.
- **Constraints.** A constraint is published under its record's business_scope.

Related: [[DSC:A-MINTED-REF-SATISFIES-A-MIN-ITEMS-RULE-THE-EVIDENCE-DOES-NOT]] (so_what 2:
the pooled and per-slice ref oracles; this record is where the per-slice one stops).
