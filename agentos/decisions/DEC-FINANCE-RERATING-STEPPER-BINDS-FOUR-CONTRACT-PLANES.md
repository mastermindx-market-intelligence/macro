---
key: FINANCE-RERATING-STEPPER-BINDS-FOUR-CONTRACT-PLANES
question: The Finance dossier's primary visual was commissioned (seat D1 packet, 2026-09-24) as a seven-step stepper (driver → operating → earnings/book/FCF/capital → expectations → valuation anchor → price recognition → what we're watching), but the merged read-model contract's `rerating` object is `additionalProperties:false` over operating/expectations/valuation/price/bridge/falsifier_ids. Which governs the design spec?
answer: The contract governs (R-FIN-9). The stepper has exactly four data-bound nodes — operating, expectations, valuation, price — with the R11 chain questions as static captions, `rerating.bridge` as the connective sentence, `valuation_anchor` inside the valuation node, and `slices[].falsifiers[]` as a separate "what we're watching" list. Driver context lives in the macro matrix; earnings/book/FCF/capital are the operating plane's metric families, not a node.
rationale: The T1 contract (#7896) is merged and frozen with a closed shape; a spec that binds fields the composer may not emit either renders undefined nodes or forces a contract widening for a visual preference. The four planes already carry the thesis (operating → expectations → valuation anchor → price recognition); the seven-step reading order is preserved as captions and adjacent lists without inventing data.
alternatives:
  - option: Widen the contract with driver/earnings/watch node objects
    why_not: Re-opens a merged contract for presentation, duplicates the macro matrix and falsifier lists inside `rerating`, and delays every downstream lane on a schema round-trip.
  - option: Keep the seven nodes and let the shell synthesise driver/earnings from other sections
    why_not: Synthesis in the shell is an unowned derivation the LLM/UI may not originate (A7); it also blurs the four-plane thesis the Chairman fixed.
evidence:
  - PR #7903 comment 5810133462 (read-only Opus audit: FAIL, finding 2)
  - contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json `$defs.rerating` (b4c6e4bd)
  - scratchpad packet fin_d1_design_spec.md frozen constraint (b) — the seat's own seven-step instruction
affects:
  - research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md
  - the Finance T8 page shell
confidence: high
reversibility: easy
review_by: 2026-10-24
decided_by: Fable CEO seat 938d17d6 (claude8), operation gmi-finance-fable-ceo-e2e-20260924-chairman-001
decided_at: 2026-09-24T08:05:00Z
---

The seat's D1 packet, not the contract, carried the error; the repair lane `fin_d1a_repair` rewrites the spec to R-FIN-9 and a second read-only audit gates the mockup.
