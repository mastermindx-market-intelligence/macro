---
key: FINANCE-DOSSIER-SPEC-SURFACE-TIERS-STATE-SCOPED-FRESHNESS-AND-ANSWER-FIRST-COMPOSITION
question: Beyond the four-plane binding (DEC:FINANCE-RERATING-STEPPER-BINDS-FOUR-CONTRACT-PLANES), which composition and material rulings govern the Finance dossier design spec (research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md) so that the T8 shell and D1b mockup implement one design rather than re-deciding it?
answer: >
  The closed ruling set R-C..R-K, R1–R4 and D1–D3 (PR #7903 comments 5810133462, 5812280671, 5812943971).
  Composition: exactly seven L1 sections in the frozen R11 order — what-changed, rerating-map (conflicts nested inside it), system-map, subtheme-atlas, company-exposure, macro-matrix, constraint-map — plus one evidence dialog drawer; `<main class="fi-shell">` is the canvas (no panel class), L1 sections are `fi-panel`, nested blocks are `fi-panel2`; `#rerating-map` is the answer tier (h1 scale, full width directly under what-changed) and every other section is support; L1 tables show the first 8 rows sorted by issuer label with a "See all N / 查看全部 N 家" disclosure, the exposure table wrapper holds ONLY the table and the disclosure is a sibling, phone cards live outside both wrappers.
  Shell: data-free markup hydrated by one fetch from `[data-fi-read-url]`; every payload token has one EN+ZH label; the eleven missing states render as plain-word chips at named DOM locations; freshness is state-scoped (`data-state-freshness` mirrored from top-level `freshness.state` onto the what-changed head) and rendered as a real 8px `::before` pip coloured by `--fi-fresh-colour`, hidden in light.
  Material: two art directions (dark = command center with the pip glow, light = research workspace with hairlines and shadow); every colour is a theme.css token; materiality colours are `--ink-warn` for MATERIAL and `--muted` otherwise, never `--up`/`--down`; what-changed rows carry name, plane, evidence chip and freshness with NO stance verb because `material_changes[]` has no stance field.
  Interaction: tablist with roving tabindex and Arrow/Home/End keys; one breakpoint set (≤767 phone: vertical stepper, per-row cards listing only present cells, 16px gutter); the dialog drawer is the only overlay.
rationale: >
  Four repair rounds showed that every unpinned choice (surface tier, freshness rendering, table density, stance wording) was re-decided differently by each lane pass; pinning the set as one record lets the mockup and shell lanes be commissioned as implementation of a fixed spec and lets the audits attack drift rather than taste. Each ruling traces to an existing law — MASTER_PRODUCT_DESIGN_SYSTEM_V1 §5 items 3 and 10, §9, §10 archetype C, the two-art-directions theme law, the contract's closed enums — so none of them is a new design system.
alternatives:
  - option: Let the mockup lane (D1b) choose surface tiers and freshness treatment from the specimen
    why_not: The specimen has no state-scoped freshness idiom and no answer-tier rule for a dossier; three audits recorded the lane inventing halos, wrappers and stance verbs when the spec left the choice open.
  - option: Encode the rulings only in the T8 packet
    why_not: A packet is session scratch; the mockup, the shell, and any later vertical reusing the dossier archetype need the same set, and a DEC is the only cross-session home.
evidence:
  - PR #7903 comments 5810133462 (audit 1 + R-A..R-K), 5812280671 (audit 3 + R1–R4), 5812943971 (audit 4 + D1–D3)
  - research/MASTER_PRODUCT_DESIGN_SYSTEM_V1.md §5 items 3 and 10, §9, §10 archetype C
  - contracts/sector_intelligence/finance_intelligence_read_model.v1.schema.json (material_changes has no stance field; freshness.state enum)
affects:
  - research/finance/implementation/FINANCE_DOSSIER_DESIGN_SPEC_2026-09-24.md
  - mockups/finance_intelligence/ (D1b)
  - the Finance T8 page shell and its hydration module
confidence: high
reversibility: easy
review_by: 2026-10-24
decided_by: Fable CEO seat 938d17d6 (claude8), operation gmi-finance-fable-ceo-e2e-20260924-chairman-001
decided_at: 2026-09-24T11:20:00Z
---

Rulings are cumulative: a later ruling narrows an earlier one and never re-opens it (D1 narrows R4's table composition; D2 replaces R2's halo with a pip; D3 removes the stance verb R-F's chips never had). Minor residuals that survive the fifth audit ride the T8 packet appendix, not another spec round.
