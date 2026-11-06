---
key: A-MINTED-REF-SATISFIES-A-MIN-ITEMS-RULE-THE-EVIDENCE-DOES-NOT
claim: >-
  The Finance read model's contract rules that an OBSERVED plane cites evidence
  (`evidence_refs` minItems 1). The composer met that rule by minting. Every slice's
  evidence list got a synthetic `slice:<slice_id>` ref that named no source record, so the
  rule could never fail. In the default fixture, 220 of 263 published evidence refs were
  such mints: 44 of 52 slices cited nothing else, on the slice and on all four planes. A
  probe dropped one slice's owner records (card_networks) in each of the five conflict
  fixtures. In all five, the slice still published a reading that cited only the mint, and
  the contract accepted every document. In four of the five, a conflict was still drawn
  from those readings. No committed test could see it. In all twelve fixture variants
  (six fixtures, with and without the extended owner inputs), every OBSERVED plane also
  cited a real record, so no fixture carried a reading that rested on the mint alone.
falsifier: >-
  `python3 -m pytest tests/test_finance_intelligence_projection.py -q -k "owner_ref or minted_ref or no_owner_ref or reading_only"`
  passes (14). Swap in engine/sector_intelligence/finance_projection.py from e4dd84d1c535
  and append an inert `_withhold_unevidenced` that returns the plane unchanged. 12 of the 14
  must then fail. The 2 that pass are the oracle's positive controls, which monkeypatch a
  mint of their own. If none fail, the mint was not the path.
so_what: >-
  (1) A presence rule (minItems, required, non-null) is only as strong as the producer's
  inability to fabricate the value. A composer that can mint a value satisfies the rule
  vacuously, so audit every default or fallback that fills a field a contract rule
  requires. The Finance composer now never mints a ref
  (DEC:FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF).
  (2) Ask the oracle where a value CAME FROM, not what it LOOKS LIKE. The test collects
  every ref the owner inputs carry (record_id, evidence_ref, evidence_refs, source) and
  requires every published ref to be one of them. A prefix oracle (no ref starts with
  `slice:`) calls a mint of the bare slice id clean. The owner-carried oracle catches both
  shapes (positive controls [prefixed, bare]). Pooled across the document, it still passes
  a composer that stops scoping refs by slice, so a second oracle asks which slice the
  owner files each ref under. An unscoped composer publishes 2040 refs outside their slice
  on the default fixture, and only the per-slice oracle sees them.
  (3) Test the rule's failure path by removing the evidence, not by reading fixtures that
  carry it. Only the dropped-record probe showed a reading outliving its evidence.
  (4) Withhold the reading, not the document. A contract refusal would take the other 51
  slices down with one. An OBSERVED plane without an owner ref is published as MISSING,
  in words, with its reading withheld. Any other state keeps its state and words and loses
  only the reading. Conflicts are drawn from the planes, so a withheld reading draws none.
  Withhold the reading's DATE too: freshness and common_as_of were computed from the raw
  inputs, so a slice with every plane withheld still read FRESH, and one withheld price
  row dated 2019 made the whole document SOURCE_STALE. Every field derived from a
  reading has to be traced, not only the reading.
  The page opens an empty evidence list as "No evidence on file." (the spec's NO_EVIDENCE
  words), never as the contents link's prompt to choose an evidence action.
  (5) Owner refs are still not checked to resolve. The committed PRICE_UP conflict fixture
  publishes 2 exposure-cell refs that name records its trimmed ledger does not carry. The
  extended owner inputs publish 10 to 14 per fixture, from observation `source` fields. The
  page opens each as "This evidence record is not on file." Plane evidence is the union of
  the slice's owner refs, so a check that a ref resolves would not prove that a reading's
  own evidence can be opened. Per-reading resolution waits for the evidence grammar of the
  shared base (#7870, evidence_claim.v1).
kind: landmine
verified_at: 2026-09-28
verified_by: "tests/test_finance_intelligence_projection.py::test_every_published_evidence_ref_is_an_owner_ref[six fixtures], ::test_the_evidence_ref_oracle_fires_on_a_minted_ref[prefixed,bare], ::test_a_reading_no_owner_ref_backs_is_withheld[five conflict fixtures] and ::test_a_plane_publishes_a_reading_only_with_an_owner_ref (12 of 14 fail with the minting composer from e4dd84d1c535 swapped in); ::test_a_slice_cites_only_evidence_its_owner_files_under_it[six fixtures] and ::test_the_slice_evidence_oracle_fires_on_an_unscoped_composer (the pooled oracle passes an unscoped composer; the per-slice one finds 2040 refs outside their slice); ::test_a_withheld_reading_publishes_no_date (fails on the round-1 composer, which dated the document from a withheld row); tests/test_finance_intelligence_hydration.py::test_an_evidence_trigger_opens_words_for_what_it_cites (the empty-list button opened the bare prompt under the old page JS); census of every published evidence_refs list: 220 minted of 263 on the default fixture before, 0 minted after"
scope:
  - macro
  - engine/sector_intelligence/finance_projection.py
  - tests/test_finance_intelligence_projection.py
  - contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json
  - templates/finance_intelligence.js
confidence: verified
---

Found while planning the page's evidence drawer, not by a test. The page opens the first
ref of an evidence button and looks it up by `source_records[].record_id`. A census of
every published ref by class showed that most buttons would open a record that does not
exist. The minted ref sat in `_slice_evidence_refs`. The `_plane_evidence_refs` helper
beside it, which derived refs from `record_id`, had no call site and is deleted, together
with two other dead helpers.

The dropped-record probe on the fixed composer: all five conflict fixtures compose a
valid document. The card_networks planes carry no reading and no refs, OBSERVED planes read
MISSING, the REGIME_BREAK plane keeps its state without a reading, and no conflict is drawn
for the slice.

Related: [[DSC:TWO-ENDS-OF-ONE-POINTER-VALIDATED-IN-ISOLATION-BOTH-PASS-WHILE-IT-DANGLES]]
(its Finance scope note cited the dead helper and is corrected to match this record),
[[DSC:A-MINTING-DEFAULT-IS-INVISIBLE-TO-AN-EMPTINESS-GATE]] (the same mechanism on another
vertical) and [[DSC:A-GUARD-NAMED-IN-THE-DOCSTRING-CAN-HAVE-ZERO-CALL-SITES]].
