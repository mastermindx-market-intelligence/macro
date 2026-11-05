---
key: TERMINAL-N-BUBBLE-IN-390-CROPS-IS-THE-NEXTJS-DEV-INDICATOR
claim: >
  the dark pill with the letter N that occludes content in dev-server-driven Playwright
  crops (terminal#490, #524 at 390) is Next.js's dev-tools indicator, not a product
  launcher; no floating assistant launcher exists on Terminal shell routes.
falsifier: >
  a production build (next build && next start) crop at 390 that still shows the bubble,
  or a grep of the built HTML for a launcher element.
so_what: >
  reviewers must not file it as a product occlusion defect and builders must not invent
  a launcher to 'fix' it (terminal#532 did exactly that and was re-scoped); evidence
  captures run with devIndicators disabled under the capture flag.
kind: landmine
verified_at: 2026-09-07
verified_by: >
  Meta-CEO B session 7cd4fae1 2026-09-07, wave B5 review of terminal#532 (opus reviewer)
  + code reads: terminal/next.config.ts has no devIndicators key; AppShell mounts no
  BrainWidget; mm_brain.js renders #mmb-launch only for anchor 'br' while BrainWidget
  anchors 'top'.
scope:
  - terminal
  - "terminal/next.config.ts"
  - "charting-app/templates/mm_brain.js"
  - WS:MARKET-OS
confidence: probable
related:
  - "DEC:TERMINAL-SHELL-IS-DARK-ONLY-EVIDENCE-MATRIX-2026-09-06"
  - "WS:MARKET-OS"
---

The dark "N" pill in 390 Playwright crops from the Terminal dev server is Next.js
dev-tools chrome, not a product launcher. Do not file it as an occlusion defect and
do not invent a launcher to hide it; capture with the indicator disabled.
