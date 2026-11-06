---
key: FINANCE-COMPOSER-NEVER-MINTS-AN-EVIDENCE-REF
question: >-
  The Finance read model's contract requires an OBSERVED plane to cite evidence. When no
  owner evidence backs a slice, what may the composer publish: a ref of its own that
  satisfies the rule, a refusal, or something else?
answer: >-
  The composer never mints an evidence ref. Every published ref is one that an owner input
  carries: a source record's record_id or evidence_ref, or an observation's source or
  evidence_ref. A plane publishes a reading only when such a ref backs it. An OBSERVED
  plane without one is published as MISSING, with its reading and clock withheld and a
  plain-word note ("Operating evidence is not available for this slice."). A plane in any
  other state keeps its state and words and loses only the reading. The reading's date is
  withheld with it: such a slice's freshness reads NO_EVIDENCE, and none of its inputs'
  dates reaches the document's freshness or common_as_of. The document stays valid, and
  no conflict is drawn from a withheld reading. Owner refs are published as
  given, and none is filtered out. On the page, a section whose evidence list is empty opens
  the drawer with the words "No evidence on file." / "暂无证据。" (the spec's NO_EVIDENCE words,
  D.12/D.15). It never shows the prompt to choose an evidence action: only the contents
  link, which cites nothing, opens that. A cited record the document does not carry opens
  "This evidence record is not on file."
rationale: >-
  The minted `slice:<slice_id>` ref satisfied the contract's rule vacuously. It named no
  record, so the rule could never fail. With a slice's owner records removed, its readings
  stayed published and a conflict was still drawn from them, in documents the contract
  accepted (DSC:A-MINTED-REF-SATISFIES-A-MIN-ITEMS-RULE-THE-EVIDENCE-DOES-NOT). Withholding
  the reading keeps the rule honest: the contract's OBSERVED rule holds because owner
  evidence exists. It also keeps the thesis rule that a missing state is rendered as words,
  and a slice's gap stays that slice's gap. The page must not answer a reader who just
  chose an evidence action by asking them to choose one.
alternatives:
  - option: >-
      fail closed, so the contract refuses the document when an OBSERVED plane has no owner ref
    why_not: >-
      one slice's gap would take the other 51 slices down with it; the same trade was rejected for malformed owner values (DSC:A-SEALED-CONTRACT-CANNOT-SEE-A-STRUCTURE-STRINGIFIED-INTO-FREE-TEXT so_what 4)
  - option: >-
      keep minting, and hide the mint on the page
    why_not: >-
      the contract rule stays vacuous for every other reader of the read model, and the page becomes the only guard
  - option: >-
      publish the unbacked reading as INFERRED
    why_not: >-
      it misstates provenance, since nothing was inferred; the evidence is absent
  - option: >-
      count a ref as backing only when it resolves to a published source record
    why_not: >-
      plane evidence is the union of the slice's owner refs, so a resolving ref would still not prove that the reading's own evidence can be opened. It would also withhold a market-sourced price reading whose evidence is an observation source rather than a research record. Measured: every reading in all twelve fixture variants already carries a resolving ref, so the rule would change nothing today and protect nothing it claims to
  - option: >-
      per-observation evidence refs now
    why_not: >-
      that ref grammar is the shared base's evidence_claim.v1 (#7870). Under the Chairman directive, sector verticals mint no evidence vocabularies and Finance integrates in the later wave
evidence:
  - "dropped-record probe (card_networks records removed, five conflict fixtures): minting composer — a reading citing only the mint survives in all five and a conflict is still drawn in four, every document valid; this decision — no reading, no refs and no conflict for the slice, every document valid"
  - "census of every published evidence_refs list, default fixture: 220 of 263 refs minted before, 0 after; readings with no resolving ref: 0 in all twelve fixture variants"
  - "tests/test_finance_intelligence_projection.py: 14 new tests; 12 fail with the composer from e4dd84d1c535 and an inert _withhold_unevidenced (the 2 oracle positive controls pass either way). 7 more pin that a slice cites only refs its owner files under it; their positive control's unscoped composer passes the pooled oracle and publishes 2040 refs outside their slice"
  - "tests/test_finance_intelligence_hydration.py::test_an_evidence_trigger_opens_words_for_what_it_cites: fails under the old page JS (the empty-list button showed the choose-an-action prompt); tests/test_finance_intelligence_page.py::test_the_drawer_says_when_a_section_cites_no_evidence fails under the old template"
  - "tests/test_finance_intelligence_projection.py::test_a_withheld_reading_publishes_no_date and the freshness assertion in ::test_a_reading_no_owner_ref_backs_is_withheld: under the first version of this change a withheld price row dated 2019-01-02 still became the document's common_as_of and turned its freshness SOURCE_STALE, and a slice with every plane withheld still read FRESH (independent review, round 1)"
  - "git grep on origin/main: _plane_evidence_refs, _source_record_evidence_ref and _observation_unit are referenced nowhere but their own def lines (and one DSC scope note); the mint was refs.add('slice:' + slice_id) in _slice_evidence_refs"
affects:
  - WS:GMI-FINANCE-INTELLIGENCE
  - engine/sector_intelligence/finance_projection.py
  - templates/finance_intelligence.js
  - templates/finance_intelligence.html.j2
confidence: high
reversibility: easy
decided_by: "seat 938d17d6 (Finance Intelligence CEO seat, operation gmi-finance-fable-ceo-e2e-20260924-chairman-001)"
decided_at: 2026-09-28
---

The ruling covers the Finance composer and page only. When the integration wave brings the
shared base's evidence claims, the per-reading evidence grammar is theirs. Until then, a
Finance plane's evidence is the union of its slice's owner refs.
