---
key: A-LANE-SIDE-SUITE-PAGE-REBUILD-IS-UNSTAMPED
claim: "scripts/build_macro_suite_pages.py emits pages with no ?v= cache stamps and no defer attributes; the stamps are applied by scripts.optimize_assets at the end of render.yml (:1281), so any page rebuilt outside the render lane differs from main (seat measurement: 374 diff lines, 0 ?v=)."
falsifier: "`python3 scripts/build_macro_suite_pages.py && grep -c '?v=' site/macro_national_debt_liabilities.html` returning a non-zero count identical to the committed page's."
so_what: "Never commit a lane- or seat-rebuilt suite page; it would ship an unstamped page that busts no caches and is overwritten by the next render anyway."
kind: landmine
verified_at: 2026-10-02
verified_by: "seat: python3 scripts/build_macro_suite_pages.py output diffed against origin/main:site/macro_national_debt_liabilities.html (374 lines, grep -c '?v=' = 0); render.yml:1281"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "scripts/build_macro_suite_pages.py"
  - ".github/workflows/render.yml"
confidence: verified
---

The render lane is the only stamper. This is why `DEC:SUITE-PAGE-HEALS-SHIP-LIB-PLUS-RENDER` forbids committing the rebuilt page even when it would green the copy-law test immediately.
