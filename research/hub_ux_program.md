# Hub UX Program — front-page UI/UX overhaul (2026-07-10)

Operator ask: full UI/UX sweep of mastermind-x.com (the hub / `site/index.html`), fix bugs,
improve responsiveness, enhance the settings pane, add features, add wow factor.
Method: 6-lane multi-agent review (visual / UX+features / responsive / a11y+i18n / bugs /
settings pane) over a 28-shot matrix (5 viewports × dark/light × EN/ZH × key states),
then waved build. Perf substrate: PR #2079 (pause-aware globe, quality governor, `__gdPerf`).

## Shipped waves (this PR)

- **W0 bugs/a11y/i18n** — honest alerts chip ("5 of 12 signals") + in-place expander +
  visible-cut dedupe; hero tagline "backtested" → "disciplined" (house epistemics; note
  `check_validated_claims` tokens don't cover "backtested" — candidate follow-up, mind
  legitimate negations on methodology pages); pebbles `tabindex=-1` (were focusable inside
  `aria-hidden`); `<html lang>` synced on language switch (+ MutationObserver fallback);
  `#gd-live` announces in the active language; lang toggle keyboard-operable; light-theme
  `.pill` WCAG contrast override (48% mix ≈ 5.08:1); ZH statics (中国行业, 美元增长溢价 ·
  风险偏好, 截至 date); `viewport-fit=cover` + safe-area insets (bottom-sheet tooltip,
  `.af` toast, body padding); ≥44px pebble hit areas (≤560 `::after` inset −10px — note:
  this consumes the accent-underline pseudo on mobile); dead `.gd-cluster`/`buildCluster`
  removed.
- **W1 responsive** — ≥1600px: `.wrap` 1180→1360, globe stage cap 640→740; 769–1024
  tablet band: features grid 3-col, globe `min(80vw,560px)`.
- **W2 UX/features** — globe hint chip (first visit, `gdHintSeen`); eyebrow next-bell
  countdown + data-vintage chip (freshness honesty vs the ticking "Live" clock); sign-in
  affordance `#hub-signin` (MDXAuth-gated); rotation snapshot strip
  (`data/sector_central/calls.parquet`, omit-if-stale>7d); latest-report teaser on the
  Reports card (`build_reports` front-matter); regime-changed badges (US-only detectable
  from the home alert feed today); standout ticker chips (US/CN/HK from committed
  `site/factordata/*_standouts.json`). Data-driven sections materialize with the next
  nightly render — the committed page only carries static-safe transplants.
- **W4 settings pane** — 3-way **Auto/Light/Dark** with auto-theme lifted site-wide into
  theme.js (was index-only; re-derives on boot when `themeAuto=1`, rewrites `theme` so
  head pre-paint scripts agree); **Reduced effects** (`fx=min` → `html.fx-min` +
  `__gdSetTier(0)`/`__gdSetMotion(false)` globe API, governor pinned); **Live prices**
  on/off (`liveOff` → `LiveQuotes.pause/resume`, row hidden where LiveQuotes absent);
  **Default view** Markets/Features (hub-only row, `hubView`); pane aria/focus fixes +
  attribute-driven i18n. theme.js/theme.css/live.js are PAIRED templates — token-preserving
  sync (`check_template_site_sync --fix` keeps the baked `SUPABASE_CFG`).

## Gated / follow-ups

- **W3 wow — OPERATOR PICKED 2026-07-10: A+B blend, AMENDED.** Binding design rulings
  from the mockup review: light mode keeps the current palette (**NO light-blue / blue-marble
  recolor**), **NO stars and NO moon in daylight** — sun only, **dimmed** so text never
  washes out; **dark mode unchanged** (plus moon fading out on scroll — fixes the
  moon-bleed-behind-cards bug); **REJECTED: regime/movers side rails** (do not re-propose).
  SHIPPED same day: globe auto-tour (focus-safe, AT-quiet, pauses 15s on any interaction incl.
  pebbles/deselect, holds rotation + restores zoom per step, reduced-motion-skipped), dimmed
  light-mode sun (~45%), dark-mode moon-set on scroll (composes with the -50% centering
  transform — inline transform stomping was a review catch), graded alert timeline
  (per-row positioning context + reduced-motion-safe pulse cascade were review catches),
  three-part footer, document-level Escape for the pinned tooltip. Variant-C numbered
  sections not picked.
- **W2b live quotes**: the hub's 9 index symbols (^GSPC, ^HSI, …) are served by NO feed —
  live.js is a no-op on the front page. Wire into `build_live_overlay` (+ sessions for
  jp/kr/tw/gb/eu; client `regionOf` already mapped, absent sessions are safe-unknown).
- **W2c ZH engine strings**: alert detail bodies leak English into `.l-zh` — needs a
  paired `{text_en, text_zh}` contract at the emitters, not template patches.
- **W5 guards**: landing a11y check (aria-hidden-focusable, `lang` sync, light `.pill`
  contrast) in dark/light × EN/ZH; also the inline-`onclick` gap: `check_inline_js` parses
  `<script>` bodies in `site/*.html` only — a broken onclick in a `build_vector.py`-rendered
  section ships green until rendered (bit us: expander blocker caught in review).
- CN standout chips show bare numeric codes (601326…) — artifact has no alias field.
- Regime-change badges for CN/HK/CA need their regime events surfaced into the home feed.

## Review verdicts folded in

Opus review (block → fixed): expander onclick was invalid JS (quote-nesting — rebuilt with
pre-rendered label spans + class toggle, e2e-tested 5→8→5); `#hub-signin` never unhid
([hidden] vs inline display); observer now syncs `documentElement.lang`; theme segment got
`aria-pressed`; chip counts deduped total; tickers added to `.l-zh` too.


## 2026-11-12 — Landing globe and shared-shell continuation

Current Chairman commission: enhance the earth globe and the entire start.html experience,
make the landing robust, and integrate its composition with the shared shell. This
extends the existing Hub UX Program; prior accepted work and data contracts remain inputs.

Source baseline: macro `e907472c31478649d0827b128da577dd05ee39c2`.
Procedure: Mastermind `0e1ca7a2d8aa95ac415191d64bd3a39212be39d0`, skillpack 1.0.1.
Carrier: GitHub-native branch `sol/web-landing-globe-shell-20261112-c2`; authenticated author
`mastermindxryan`. No pre-existing globe-titled open PR was found; three start.html
search hits concern independent intake, IPO date semantics, and Terminal fallback.
Changes must preserve those domains and the existing shared-shell owner.

DONE_WHEN: a visually coherent global Home, with an enhanced earth, understandable market
selection, keyboard/touch operation, controllable motion, honest data freshness and a
useful degraded state; the same content works standalone and within the existing shell.
The source must pass affected checks and required CI, enter the repository's permitted
release path, and receive actual browser proof. A design, PR or green CI alone is not
production acceptance.

### Execution sequence

1. Inspect the live globe and current renderer, content producer, shell contract and
   accepted design doctrine. Keep the existing d3 canvas and data/quote ownership unless
   a concrete incompatibility requires a change. Resolve the Home vs marketing distinction.
2. Freeze desktop/mobile and dark/light composition with EN/ZH parity. Preserve the
   existing rejection of regime/mover side rails. Paper may supply a mockup only when the
   intended Mastermind file is exactly bound; the observed active AERLOR file is unrelated.
3. Implement through the existing globe runtime and build_vector Home producer,
   retaining single runtime loads, shell routing, data provenance and page destinations.
   Add only focused regression coverage for real changed behavior.
4. Inspect actual screenshots and exercise market selection, motion controls,
   resize, keyboard, mobile scrolling, reduced motion, shell visibility and failure
   fallback. Save exact evidence with the source.
5. Publish one coherent candidate; self-check, consume required CI, repair scoped
   failures, qualify normal protected release and verify the resulting live journey.

### Design direction and constraints

Home is the global-overview Command Center, not another marketing header.
The globe remains the visual centre; concise purpose and next actions should read
immediately. Prefer a restrained atmospheric earth, legible market markers and
explicit controls to competing sun/moon ornament. Use accepted tokens and shared
navigation. Dark: calm luminous depth and restrained atmosphere. Light: clear research
canvas, hairlines and shadow, without the previously rejected blue-marble recolour.
Data timestamps and availability are facts, not decorative LIVE claims.

No changes to auth, subscription gates, market calculations, provider routing,
global shell protocol, or unrelated dashboards. No copied competitor assets.
No direct main push, self-approval/self-merge, native Macro auto-merge or invented
deployment proof.

### Current execution facts

- Live page inspected in the connected browser; no sampled console error, but globe
  ornament competes with hierarchy and market labels crowd. Existing motion and
  keyboard paths are present and must be preserved or improved.
- Fabric capability preflight reports adapter_available=false; no worker requested or
  started. Direct implementation is retained under LOWER_TOTAL_OVERHEAD and
  PRINCIPAL_JUDGMENT, with one native read-only architecture counsel role.
- Paper inspect succeeded, but its active document is AERLOR
  `01M6JNN71ZN4867VJZ83PPXQZ0`, not the Mastermind target. No Paper edit attempted.
- Implementation and product acceptance are not yet established.


### 2026-11-12 implementation checkpoint

GitHub-native carrier: `sol/web-landing-globe-shell-20261112-c2`. Initial implementation commit `35daf5a641de10e59b183a0c880cf471af6e3f21` was read back at exact blob content. The existing D3 canvas now has a globe-led Home layout, explicit controls and fallback dashboard anchors; the existing shared-shell visibility event owns suspension. No shell protocol, data math, auth, or provider changes.

Focused verification: syntax checks; seven executable Node lifecycle cases (shell/document suspension, reduced motion with interactive repaint, container resize/focus, failed fetch retry, missing canvas, quality-governor single-loop ownership, and timeout); five retained tooltip/mobile/source checks through pytest. The first actual dark desktop preview renders. Full theme/locale/viewport and hover/focus captures, final source self-check, required CI, qualified merge-on-green enrollment, and production proof remain owed. No PR is armed. Paper's artboard mutation contract is held in this connection; the current Paper file is unrelated, so no Paper content was edited. The working browser preview is the design surface.
