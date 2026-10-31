# Nav pre-hydration barrier — slow-chain immediate-hover evidence (2026-10-30)

Real-browser proof for the mega-menu flash fix (`mdx-nav-boot` barrier in
`templates/_navlinks.html.j2` + the withholding rule in
`templates/navigation-refresh.css`, lifted by `nav_market.js` boot).

## Harness

`capture.py` (committed here, runnable: `python3 capture.py`) serves this
branch's `site/` over loopback and stalls `nav_market.js` by 4 s in a threaded
handler (the real chain is theme.js → account.js → nav_market.js; this
simulates its cold-cache tail). Chromium via Playwright, headless.

Pages captured:

- `chat.html` — a COMMITTED page of this branch (generated header synced by
  `scripts/sync_chat_nav --fix`), so it ships the barrier script as-is.
- `macro.html.treated` — the committed `macro.html` with the barrier script
  from the changed partial spliced in above the nav stylesheet link: exactly
  what the nightly estate render emits from the new partial. (The committed
  `macro.html` predates the render; its nav header is refreshed by the render
  lane like every page, as with prior shared-nav changes.)
- `macro.html` (as committed, no barrier script) — the CONTROL below.

## Measurements (RESULTS.json — all 14 checks pass)

- **CONTROL** (pre-render page, no barrier): during the 4 s stall with the
  trigger already hovered, **71/71 rAF frames show the legacy compact panel
  visible** (`display: block`, un-enhanced) — the reported flash, reproduced.
- **TREATED** (barrier armed): desktop 1440 dark EN / light EN / dark ZH —
  **92/92 frames `display: none`** across the whole stall; `barrier=True`
  the entire window; zero legacy frames.
- **Keyboard**: immediate trigger focus during the stall — zero legacy
  frames; after boot, focus opens the mega menu (`display: grid`).
- **Mobile 390**: hamburger open + immediate US accordion tap during the
  stall — zero legacy frames; after boot the mega accordion opens.
- **Fallbacks**: `nav_market.js` request aborted → the loader's `onerror`
  lifts the barrier, hover shows the usable legacy menu;
  `account.js` aborted → `theme.js`'s `onerror` lifts it; JS fully disabled →
  `html` carries no `mdx-nav-boot` class and the legacy menu renders on hover.
- Boot promptness: with the 4 s stall the mega menu is live immediately at
  boot completion; with a warm cache the whole window is sub-second.

## Screens

| file | meaning |
| --- | --- |
| `control_pre_fix_legacy_flash.png` | the bug: legacy US dropdown open during the stall |
| `desktop_{dark,light}_{en,zh}_preboot.png` | stall with hover active: no dropdown paints |
| `desktop_*_postboot.png` | boot complete: full-width mega menu |
| `kb_preboot.png` / `kb_postboot.png` | same via keyboard focus |
| `mobile_preboot.png` / `mobile_postboot.png` | 390 px accordion, stall vs boot |
| `fallback_*.png`, `no_js_legacy_usable.png` | degraded paths keep the legacy nav usable |
