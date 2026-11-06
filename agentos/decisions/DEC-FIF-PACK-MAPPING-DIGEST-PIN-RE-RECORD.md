---
key: FIF-PACK-MAPPING-DIGEST-PIN-RE-RECORD
question: >
  When a specialist pack's dev-corpus repair changes only how a field is mapped
  (an alias tuple or a section selector) and not what the field resolves to on
  AAPL, may that repair lane re-record the pack's own AAPL envelope pin literals,
  which embed mapping and pack-content digests?
answer: >
  Yes, under four conditions, and only for the pack under repair. Base ruling (PK02
  sbc_expense_total): (1) the only producer change is an alias-tuple change inside
  that pack's module; (2) the pack's AAPL envelope before and after is
  byte-identical once mapping_rule_digest is masked in every row and the concept /
  source-fact provenance fields are masked in the repaired field's row only, proven
  by equal sha256 of the two masked serialisations; (3) the repaired field's AAPL
  value, unit, period and quality_state are identical; (4) no other pack's pin, no
  golden fixture and no GOLDEN_AAPL_QUERY_ACCESSIONS entry changes. PK09 extension
  (section-selector repair, this repair only): only PK09's entries in
  BASE_AAPL_ENVELOPE_SHA256, BASE_PACK_ENVELOPE_SHA256 and
  PK05_/PK07_/PK08_BASE_PACK_ENVELOPE_SHA256 may change; every changed fixture is
  byte-identical once mapping_rule_digest, pack_content_sha256 and the single
  limitations entry embedding the section regex are masked; no field value, unit,
  period, quality_state or evidence (span, quote, accession) changes; no golden
  fixture, GOLDEN_AAPL entry or other pack's pin changes. If any condition fails,
  the pins stay frozen and the lane returns BLOCKED with the diff.
rationale: >
  The pins exist to catch a change in what the product says about AAPL. A mapping
  repair that leaves every AAPL value and its evidence untouched still moves the
  embedded digests, so a frozen pin would block every dev-corpus repair even when
  the AAPL product is unchanged. The masked-equality proof keeps the pin's purpose
  (no silent AAPL drift) while letting the digest literals follow the code. The
  ruling is scoped per pack and per repair so it cannot become a general licence
  to re-record pins.
alternatives:
  - option: Keep every pin frozen and refuse any mapping repair that moves a digest.
    why_not: >
      Blocks every dev-corpus generalization repair (DEC-FIF-PACK-GENERALIZATION-DEV-CORPUS)
      for a digest change that carries no product change.
  - option: Let any lane re-record pins whenever its tests pass.
    why_not: >
      Removes the pin's guarantee; an AAPL value drift would be re-recorded as the new
      truth with no proof that the product is unchanged.
evidence:
  - "PK02 dev2 repair packet fif-pk02dev2-20261101 (base ruling, four conditions); shipped in PR #10467 with the masked envelope equal on all five pinned paths"
  - "PK09 dev2 review packet fif-pk09dev2rev-20261101 (PK09 extension, four conditions)"
  - "agentos/decisions/DEC-FIF-PACK-GENERALIZATION-DEV-CORPUS.md (repairs are developed against dev corpora)"
affects:
  - tests/test_fif_specialist_packs.py (pinned envelope literals)
  - engine/fundamental_forensics/specialist_packs/pk02_*.py
  - engine/fundamental_forensics/specialist_packs/pk09_*.py
confidence: high
reversibility: easy
decided_by: "FIF Meta-CEO seat 96dc937a (Fable)"
decided_at: 2026-11-01
---

A pack's own dev-corpus repair may re-record that pack's AAPL envelope pin literals only when a masked-envelope sha256 proves the AAPL product is unchanged (base ruling for PK02 alias-tuple repairs; one-repair extension for the PK09 section-selector repair).
