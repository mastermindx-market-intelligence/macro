---
key: FIF-PACK-PATTERN-REPINS-ARE-DIGEST-ONLY
question: >
  When a specialist-pack narrative pattern is repaired after review, may the
  envelope pins in tests/test_fif_specialist_packs.py move, and on what proof?
answer: >
  Yes, by seat ruling per repair, and only as a digest-only re-pin: the masked
  diff of every affected envelope context — with `mapping_rule_digest` and
  `pack_content_sha256` masked — must be EMPTY, so that only the rule-digest
  provenance moved and no emitted value, span, reason code or field changed. The
  independent reviewer audits that only the repaired pack's own pin literals moved
  and that every other pin is byte-identical to the parent.
rationale: >
  `mapping_rule_digest` hashes the pattern bytes, so any legitimate pattern repair
  moves the pack's pins; freezing them would make every reviewed repair
  unmergeable, while re-pinning without the masked proof would let content drift
  hide behind a provenance change.
alternatives:
  - option: Freeze every pin literal after the first acceptance
    why_not: The digest is a function of the pattern bytes; a frozen pin forbids all pattern repairs, including reviewer-mandated ones.
  - option: Regenerate pins from the candidate output without a masked diff
    why_not: Generating expected output from the candidate renderer is the T11 anti-pattern; it cannot distinguish provenance movement from content drift.
evidence:
  - "PK09 B.3 v2–v5 (#9907 head db073db6): five PK09 pins moved, masked diffs EMPTY for all five contexts; review fif-pk09fix4rev-20261020-r2 PASS_WITH_NOTES, 364 passed"
  - "PK08 fix2 (#9903 merged 18572291) and F3-1 (#10246, lane fif-pk08f31-20261021-r1): PK08-only pins, masked diffs EMPTY, 358 passed"
  - "#9911 (census re-pin) was a line-number-only re-pin under the same rule"
affects:
  - WS:FINANCIAL-INTELLIGENCE-FABRIC
  - tests/test_fif_specialist_packs.py
  - engine/fundamental_forensics/specialist_packs/
confidence: high
reversibility: easy
decided_by: FIF Meta-CEO seat 96dc937a (Fable)
decided_at: 2026-10-20
---

Applied to every PK08/PK09/PK10 repair in the 2026-10-20/31 review rounds.
