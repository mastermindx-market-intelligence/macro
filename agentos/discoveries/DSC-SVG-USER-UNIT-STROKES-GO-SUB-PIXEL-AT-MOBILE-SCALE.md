---
key: SVG-USER-UNIT-STROKES-GO-SUB-PIXEL-AT-MOBILE-SCALE
claim: "A viewBox-scaled SVG stroke set in user units without vector-effect:non-scaling-stroke renders at width x scale; at 390 px the 1000-unit sanctions map is about 0.31 scale, so a 1.8-unit 'mobile override' painted about 0.56 px (1 blue pixel in 441 in the dark mobile cell)."
falsifier: "`python3 scripts/capture_page_evidence.py --route /sanctions_map.html --viewport 390` producing a cell with at least 20 blue pixels inside the UK box WITHOUT vector-effect:non-scaling-stroke in templates/sanctions_map.html.j2."
so_what: "Computed CSS values are not rendered widths: judge map marks in the 390 cells (pixel counts), never from the stylesheet; mobile marks need non-scaling strokes."
kind: constraint
verified_at: 2026-10-02
verified_by: "Opus RO review of PR #8290 / #8292 cells (pixel census 1/441); #8292 fix = vector-effect:non-scaling-stroke 1.5 px in templates/sanctions_map.html.j2, 16-cell receipt viewed"
scope:
  - "macro"
  - "WS:MARKET-OS"
  - "templates/sanctions_map.html.j2"
  - "templates/_worldmap_base.html.j2"
  - "mockups/evidence/sanctions-map-*/"
confidence: verified
---

The D4-mobile/D8 follow-ups (mark out-ranking the row highlight at 390; dashes closing into a solid over an 8 px UK) are a DESIGN question for the designer lane, not a builder fix.
