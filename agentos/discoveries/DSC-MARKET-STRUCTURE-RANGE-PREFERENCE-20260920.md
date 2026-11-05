---
key: MARKET-STRUCTURE-RANGE-PREFERENCE-20260920
claim: >
  At macro da216f856dc4eacf42e71c6edc1b1fc27e1700ad, invalid or unsupported saved
  chart ranges could leave Market Structure with no selected range, while its
  20px mobile buttons and four SVG charts exposed no selected-state/chart names.
falsifier: >
  Serve that immutable page, seed msp-gex-range=broken and msp-sys-range=126,
  then inspect the native range groups: one supported button must already be
  aria-pressed=true in each group, with 40px mobile targets and named SVGs,
  to disprove the recorded counterexample in the #7437 evidence directory.
so_what: >
  Keep validation against the displayed choices, native pressed/group semantics,
  and observed date bounds in the existing page controller. Exercise real clicks,
  Enter/Space, reloads, storage denial and the language event; compare geometry,
  not merely button counts. Continue through #7437 rather than a replacement PR.
kind: landmine
verified_at: 2026-09-20
verified_by: 'PR #7437; research/evidence/uiux-market-structure-controls-20260920/'
scope:
  - 'mastermindx-market-intelligence/macro'
  - 'templates/market_structure.html.j2'
  - 'site/market_structure.html'
  - 'tests/test_build_market_structure_page.py'
confidence: verified
---

The repair is source-built and locally browser-proven. It is not yet production
accepted. The continuation README preserves current authority, exact base,
unchanged data/model/auth boundaries, validation commands and the VPS-only
release gate; publication and production receipts belong on the existing PR.
