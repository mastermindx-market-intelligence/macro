# R7 design return — Prophet Opportunity workspace (§7.4)

Date: 2026-10-21. Child: orchestration (Opus, fable-mode) under Prophet end-to-end seat 69eb9a1c.

## Outcome
DONE for the design deliverable, which is reference only.

New Paper page `08 · R7 award-grade · Opportunity workspace · DRAFT` in the file PROPHET, with 27 artboards:
- Today at 1440 in light/dark × EN/ZH, at 390 in light/dark × EN/ZH, at 768, and the 320 stress reflow.
- Setup detail at 1440/390 in light/dark.
- Three lens boards and Compare at 1440/390.
- Saved list, Save to list at 390/1440, and Save outcomes.
- Three truthful-state boards: decision unavailable; stale quote with revoked entry and reconstructed plan; refusal receipt.
- Board states: loading, healthy empty, outage.

Every artboard was screenshot-reviewed and exported to `proofs/` (27 PNGs). The implementation spec, with the full EN/ZH register, is `R7_DESIGN_SPEC_2026-10-21.md`.

Nothing is implemented, nothing is browser-proven, and production tokens are unchanged.

## Source
- Commission: ROUTE orchestration, Opus with WHY OPUS stated.
- Masterplan: `/Users/chriswong/Downloads/Prophet_End_to_End_Masterplan_Fable_2026-10-20.md`, §6.2–6.5, §7.4 and §13.
- Doctrine: `docs/DESIGN_DOCTRINE.md` and the Chairman no-edge-accent rule of 2026-10-18.
- Vocabulary: `templates/theme.css` and the Prophet templates, read only.
- Base page p-A-0, read only and never duplicated or edited.
- Merged PR #9566 (4f52d225), read once.

## Evidence
- Proofs: `research/prophet_v4/r7_design/proofs/01..27_*.png`. The artboard-to-proof table is spec §2.
- Node counts after the work, from `get_basic_info` on every page. All 11 pre-existing pages are identical to before:

  | Page | Nodes / artboards |
  |---|---|
  | p-1-0 | 3850/19 |
  | p-B-0 | 2631/23 |
  | p-A-0 | 10121/36 |
  | p-9-0 | 497/8 |
  | p-8-0 | 3291/10 |
  | p-7-0 | 3156/23 |
  | p-6-0 | 1549/1 |
  | p-5-0 | 1568/8 |
  | p-4-0 | 2666/8 |
  | p-3-0 | 3972/21 |
  | p-2-1 | 2623/19 |
  | New page | 6687/27 |

  The user's active page is still p-1-0.
- Token set: 4 add-only tokens (`line-quiet` and `focus`, each in light and dark). The hash moved from b80d0392 to 640746f9. No existing token changed.
- Audits of the new page found 0 container edge accents, 0 middots, 0 "→", 0 ALL-CAPS, 0 Menlo, 0 straight apostrophes, and every fill token-bound.
- AA contrast is computed per theme in spec §9. All text is ≥4.5:1 and all information-bearing marks are ≥3:1.
- Copy register: 457 EN rows. All 99 ZH strings drawn on ZH boards match a register ZH, with 0 unmatched. Spec Appendix A.
- Variants: `variants/` holds 5 HTML sketches, and `check_variants.py` reports OK.

## Interpretation
- The signature is the five-slot decision line: Company, Current decision, Timing, What ends it, Lens.
- It appears as the ledger spine at 1440, as card slots at 390/768, as sections in Setup, and transposed in Compare.
- Truth states replace content inside fixed slots, so state-driven layout shift is 0 by construction.
- Lenses act as filters and never as scores. Unavailable, not assessed and older signal only stay distinct from Wait.

## Integration
- **Blocking:** read spec §14 OQ1 before any build. #9566 binds #9495 to the compact chart-first card.
- The recommended default is to carry the R7 semantics, copy, tokens and states into that compact card, and to confine the 1440 ledger to the All candidates landing unless the seat or the Chairman rules otherwise.
- Spec §13 lists the template-by-template changes for a routed builder.
- The `REFUSAL_COPY` change must land together with its pinned test.

## Custody
- No commit, push or PR.
- Files were written only under `research/prophet_v4/r7_design/`.
- No Paper write is pending; finish_working_on_nodes was called after each write group.
- No fabric lane is live. pro-design-variants-20261021-r1 is DONE and was consumed.

## Review
Self-review only, with screenshot critique per artboard and scripted audits. This is **not** an independent review. An independent design and accessibility review is recommended before the build is accepted.

## Continuation
- **Next owner:** the parent seat.
  1. Rule on OQ1 (ledger vs the #9566 compact card).
  2. Commission a build lane against spec §13.
  3. Commission browser proof (mastermind-product-path-proof) at 1440/768/390/320 in light/dark × EN/ZH.
- **Undrawn cells, specified but not drawn:** dark and ZH for the non-Today surfaces, and 768 beyond Today. Rules are in spec §8 and §11.
- **Spec-only §13 rows:** quote/basis mismatch, retracted source, selection and back, related Plan, holding vs new entry, and track record.
