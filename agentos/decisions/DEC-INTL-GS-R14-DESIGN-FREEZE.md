---
key: INTL-GS-R14-DESIGN-FREEZE
question: >
  Is the Paper R14 "Global Surveillance · Masterpiece" page (14 boards) plus its written
  spec the frozen design for International Markets Global Surveillance Waves 2–5
  (IM13–IM18), and how are the six open decisions ORCH-D left for the seat ruled?
answer: >
  Yes, frozen at research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md
  (blob 5d9c51dc25005935a6be5846a01baa48246f9375) with reference PNGs under mockups/refs/intl-gs-r14/.
  Rulings: (1) spec §5.3 additive tokens live scoped under .intl-gs in a new
  templates/intl_workspace_surveillance.css, nothing added to theme.css; (2) the §14
  file plan is ratified (new view templates, both view lists in shell.html.j2, the asset
  tuple in build_intl.py, the stylesheet link in intl.html.j2); (3) the IM16
  market-by-capability acceptance matrix is adopted as mandatory, as the masterplan
  already requires; (4) G1: the specified-but-undrawn theme/locale variants in §13 are
  accepted as specification — no further Paper pass; the 8 evidence crops are produced
  on the real build; (5) G7: PNGs copied into the repo under mockups/refs/intl-gs-r14/;
  (6) every Wave 2+ packet owes the 8 evidence screenshots plus focus-state captures in
  both themes (§16.1) and a green evidence gate is not acceptance — the seat reviews
  the crops.
rationale: >
  The seat inspected the scanner (dark/EN/1440) and Brazil dossier boards directly:
  the six-question scaffold, the four clocks, the return identity, rights tiers,
  attention stances, selected/featured states carried by 1.5px rings, neutral surface
  hierarchy and the existing site-nav family are all present; no accent stripe or
  colored edge appears. The spec reads column widths from Paper, carries a contrast
  table with three forbidden combinations, and separates selected/focus/hover states
  that the drawing merged. Where Paper and production disagree (Inter vs system font,
  light ink-ok hex, focus offset 2px vs 3px, the scanner Q6 footer's "2px offset" copy)
  production tokens and the spec are authoritative, never the PNG glyphs.
alternatives:
  - option: Commission a second Paper pass to draw every theme/locale variant of all six boards.
    why_not: >
      The scanner already proves all eight combinations; the remaining variants are
      mechanical applications of §13 and are verified on the real build anyway.
  - option: Add the new tokens to theme.css.
    why_not: >
      theme.css carries a same-diff receipt (ci-pack-9) and is shared by every page;
      a scoped stylesheet keeps the blast radius to the surveillance views.
evidence:
  - "Seat look at mockups/refs/intl-gs-r14/scanner__dark__en__1440.png and dossier__dark__en__1440.png (2026-10-21 04:2xZ)"
  - "research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md §1 design bar, §5 token diff, §13 matrices, §14 homes, §15 contrast, §17 gaps"
  - "ORCH-D return (Opus orchestrator abd45165af1bdea65): 14 artboards, 540 Paper tool calls, PNGs exported from Paper, no git acts"
  - "docs/DESIGN_DOCTRINE.md — no accent stripe rule (Chairman 2026-10-18)"
affects:
  - "research/INTL_GLOBAL_SURVEILLANCE_DESIGN_SPEC_R14_2026-10-21.md"
  - "mockups/refs/intl-gs-r14/*"
  - "templates/intl_workspace_surveillance.css (to be created by Wave 2)"
  - "templates/intl/shell.html.j2, scripts/build_intl.py, templates/intl.html.j2 (Wave 2 file plan)"
confidence: high
reversibility: costly
decided_by: fable-meta-ceo-seat-d7c4f490
decided_at: 2026-10-21
review_by: 2026-11-21
---

## Scope

This freezes the design reference for Waves 2–5 of WS:INTL-GLOBAL-SURVEILLANCE. It does
not build, merge or publish anything, and it does not reopen the Wave 0 or Wave 1
contracts. A later material invalidator (a §14 hard acceptance test that the design
cannot satisfy, or a Chairman design ruling) reopens it; a new session does not.
