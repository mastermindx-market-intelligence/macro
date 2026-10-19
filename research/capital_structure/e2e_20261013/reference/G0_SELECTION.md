# G0-S selection record — the three E0 reference gaps (pack 1.1.0)

Lane G0-S (SPEC_G0 Rev 2 §3): select `whk_replacement_issuer`,
`foreign_issuer_f3_witness` and `held_out_pattern_witness` from the served
universe, requalify the six archetypes, and seal the held-out answer. Base
`e568e13820a9d88daca57bb4bf0058038d7a659e`. Candidate lists are built exactly
per §3: issuers with a filing of the named form with `filing_date` inside
2025-10-01..2026-10-15 in `data/capital_structure/source_manifest.jsonl` +
`source_manifest.part-0002.jsonl` (read via `git show`, never materialized),
one entry per CIK at its first qualifying accession, ordered by accession
ascending, excluding the six archetype CIKs (AIR 0000001750, CLNN 0001822791,
QNCX 0001662774, WHK 0001921603, LPTH 0000889971, EDBL 0001809750) and every
CIK already chosen for another gap. Candidates are tested in list order
against SEC primary documents only (submissions JSON + the named filing's
primary documents); the first candidate passing every criterion of its row is
chosen; taste is not a criterion.

- Window: 2025-10-01..2026-10-15 (filing_date).
- Candidate counts: whk_replacement_issuer 293 (S-3 | S-3/A), foreign_issuer_f3_witness 114 (F-3, exact form string),
  held_out_pattern_witness 458 (424B5).
- Budget: at most 60 candidates tested per gap; pacing 1 req/s; user agent
  `MastermindMarketIntelligence-ResearchSeat/1.0 (+https://www.mastermind-x.com)`.

## Gap: whk_replacement_issuer

STATUS: (in progress)

## Gap: foreign_issuer_f3_witness

STATUS: (pending)

## Gap: held_out_pattern_witness

STATUS: (pending)

## Requalification of the six archetypes

STATUS: (in progress)

## Request ledger

(pending)
