# MastermindX Public-Site Figma Baseline — Deviation Ledger

This ledger records differences and edge conditions rather than silently cleaning them up in **Current / 1:1**. None authorizes a redesign or production fix before baseline acceptance.

## CURRENT-001 — English 390px footer exceeds the viewport

**State:** observed in frozen source; preserve and annotate in Current  
**Surfaces:** Homepage, Market Terminal, Mastermind AI, Market Dashboards  
**Evidence:** at a 390px English viewport, `.f-cols` begins at x=20 and ends at x=405.6; the root document width is 406px on the first three pages.  
**Visible behavior:** the exact-width reference is clipped to the user viewport; the right edge of the Legal column exceeds it.  
**Figma contract:** Current frames remain 390px wide and reproduce the visible clipped state. Add an annotation showing the authored document width.  
**Revamp candidate:** reflow the footer columns only after the baseline is accepted.

## CURRENT-002 — Dashboard mobile artifact reaches 425px

**State:** observed in frozen source; preserve and annotate in Current  
**Surface:** Market Dashboards, English and Chinese 390px states  
**Evidence:** root document width is 425px. The theme-lane artifact and a 300px SVG extend beyond the viewport; individual lane content reaches farther, but clipping limits root width to 425px.  
**Visible behavior:** the exact-width reference intentionally captures the 390px user viewport rather than widening the screenshot to the hidden document width.  
**Figma contract:** keep the Current frame at 390px, reproduce the visible clipping, and record `document_width=425`.  
**Revamp candidate:** recompose the lane/SVG artifact after baseline acceptance.

## CURRENT-003 — Homepage market-card rail is intentionally off-canvas

**State:** expected motion construction, not a width-fix target  
**Surface:** Homepage  
**Evidence:** the duplicated Prophet card track spans several thousand CSS pixels while its containing stage clips the rail.  
**Figma contract:** model the rail as a clipped motion group; do not widen the page frame or treat every off-canvas card as visible page content.

## CAPTURE-001 — Founding-offer API is deterministic in local evidence

**State:** capture-environment substitution with source-equivalent output  
**Reason:** the frozen static tree has no `/api/billing/offers/founding_pro` endpoint.  
**Substitution:** `{"active":true,"claimed":null,"cap":2000}`, exactly matching the source defaults used when the request is absent.  
**Effect:** removes local 404 console noise without changing the rendered founding rate, total-cap copy or progress visibility.

## CAPTURE-002 — System Chrome channel replaces a stale bundled revision

**State:** capture tooling only  
**Reason:** Playwright CLI 1.47 requested removed Chromium revision 1134 while the host had newer cached revisions. The repository's established system-Chrome launch pattern succeeded.  
**Contract:** captures use Google Chrome through Playwright at DPR 1; source and visual behavior remain unchanged.

## RUNTIME-001 — Optional injected chrome is not permanent page anatomy

The Ask Mastermind launcher is loaded by the page runtime and is present in current product references. Market-alert/White-House banners are conditional runtime overlays and are not baked into every canonical static frame. They should be represented as optional variants, not permanent content.
