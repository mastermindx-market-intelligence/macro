---
key: AIBRIEF-SERVER-RENDERED-TABS-NEED-SAME-SURFACE-FRESHNESS
claim: >
  The Macro, China, Hong Kong and consolidated AI Brief surfaces render the shared
  `.aib2` brief body into HTML at build time. `templates/aibrief.js` intentionally
  stopped fetching or rendering those lens bodies when ABX v2 made the shared Jinja
  macro authoritative. Therefore a browser tab that remains mounted across a later
  render can keep showing the prior brief indefinitely even though main, the VPS
  origin and a newly loaded page have advanced. The September 11 incident proved
  this split: the screenshot still showed the September 9 Macro brief while main had
  published September 10 state through both September 10 and September 11 builds.
  This is not evidence that the producer stopped. The safe browser repair is a
  content-hashed, display-only client attached by the existing post-render optimizer:
  on brief intent, tab visibility return or BFCache restore it fetches the SAME page
  path with cache bypass, parses that page's server-rendered `.aib2` body and replaces
  only a matching lens whose ISO state date is strictly newer. Fetching the
  consolidated `aibrief.html` as the source for every page is unsafe because the
  wrapper may carry caller-specific receipt/footer markup on Macro, China or Hong
  Kong. Equal dates must not be swapped for the same reason.
falsifier: >
  `rg -n "fetch|render" templates/aibrief.js templates/_aibrief_body.html.j2`,
  followed by browser proof that all brief surfaces now use one reviewed
  client-rendered canonical payload or that every mounted page force-reloads whenever
  its deployed HTML changes, would falsify the need for this same-surface freshness
  client. A future immutable revision identifier inside the shared body could safely
  supersede the strict state-date comparison, but only if it is common to every
  surface and excludes caller-specific markup.
so_what: >
  Do not diagnose an old date in an already-open AI Brief modal as a failed nightly
  until the committed artifact and a fresh page load are checked separately. Do not
  add a second JSON-to-DOM brief renderer or a second scheduler. Keep the shared
  server renderer authoritative, use the existing optimize-assets publication path,
  preserve each surface's own receipt/footer, and respect each lens's configured
  cadence (including Bitcoin's intentional three-day cadence). Any lane that emits
  these pages must continue running `scripts.optimize_assets`; daily, render,
  engine-render, closing-bell and asia-close already do.
kind: constraint
verified_at: 2026-09-11
verified_by: >
  Repository history for site/master_brief.json and site/macro.html; direct inspection
  of templates/aibrief.js, templates/_aibrief_body.html.j2 and the rendered China
  receipt; regression tests in PR #7080 covering strictly-newer lens replacement,
  same-surface cache-bypassed fetch, equal-date preservation, event triggers, failure
  fallback, depth-correct injection, idempotence and all four shipped surfaces.
scope: [macro, AI Brief, scripts/optimize_assets.py, site/assets/js/aibrief-freshness.js]
confidence: verified
metadata:
  type: discovery
---

Related: [[MARKET-OS]]
