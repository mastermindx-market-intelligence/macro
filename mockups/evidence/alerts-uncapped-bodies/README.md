# Alerts un-capped bodies — 8-cell composition evidence

PR #7046 r3. Card bodies (`a.detail`, `v.note`) are unbounded on the page;
Telegram still caps at 200/120. Un-capped prose uses the page's own measure
(`max-width:62ch` on `.ac .dt` and `.muted`, same idiom as `.read-line`).
These crops show the un-capped composition on the alerts feed with the
story strip visible (so `truncate(70, false, '…', 0)` is in frame) plus
one long-detail card and one long-note vector card.

## Cells

| file | theme | lang | viewport | PNG |
|---|---|---|---|---|
| `alerts-feed-dark-en-1440.png` | dark | en | 1440×900 | 1360×663 |
| `alerts-feed-dark-en-390.png` | dark | en | 390×844 | 354×1082 |
| `alerts-feed-dark-zh-1440.png` | dark | zh | 1440×900 | 1360×627 |
| `alerts-feed-dark-zh-390.png` | dark | zh | 390×844 | 354×983 |
| `alerts-feed-light-en-1440.png` | light | en | 1440×900 | 1360×663 |
| `alerts-feed-light-en-390.png` | light | en | 390×844 | 354×1082 |
| `alerts-feed-light-zh-1440.png` | light | zh | 1440×900 | 1360×627 |
| `alerts-feed-light-zh-390.png` | light | zh | 390×844 | 354×983 |

PNG width is the capture-target box, not the viewport: 1440 crops sit
inside the page's `max(40px, calc((100vw - 1360px)/2))` padding; 390
crops sit inside the 18px body padding. 390 height exceeds the 844
viewport because Playwright screenshots the full element (story strip +
two wrapped cards).

## Fixture

Rendered `templates/alerts.html.j2` via the same Jinja path as
`tests/test_alert_triage.py:_render`. Two synthetic cards, producer copy,
plus lengthened story-strip headlines so the 70-char ellipsis is visible:

1. **Long-detail theme card** (`theme_emerging`) — body from
   `engine.theme_alerts._confirmed_emerging_event` for
   "Utilities (Equal-Weight)" / 公用事业（等权）, score 38, held 2.
   EN 238 chars (the "wait for a second session" clause). ZH is the
   producer sibling (`进取方向需连续确认`).
2. **Long-note vector card** (`impulse_warn_down`) — validation note from
   `engine.btc_alerts._conviction("impulse_warn_down")["edge"]` /
   `["edge_zh"]`. EN 233 chars including
   `BLIND to slow/options-calm flushes (e.g. it did NOT lead the 2026-06-24 cascade).`
   ZH is the producer sibling
   `对缓慢/期权平静式下跌无效（例如未能领先 2026-06-24 的下跌）。`
3. **Story strip** — `top_headline` forced past 70 chars (same EN string
   as `test_story_strip_ellipsizes_long_headlines_word_safe`). Word-safe
   EN cut lands on "continues…"; CJK cut is `s[:69] + '…'`.

Capture script (not committed):
`scratchpad/capture_alerts_uncapped_bodies.py` next to the r1 review.

## How dark / light / EN / ZH were toggled

The live page mechanism, not a hand-painted palette:

- `templates/alerts.html.j2` boot script (and `templates/theme.js`) key
  off `html[data-theme]` and `html[data-lang]`.
- `templates/theme.css` `:root` is the dark command-center tokens;
  `html[data-theme="light"]` is the light research-workspace override.
- `html:not([data-lang="zh"]) .l-zh { display: none }` and
  `html[data-lang="zh"] .l-en { display: none }` pick the dual spans.

Each cell:

1. Playwright `add_init_script` seeds `localStorage.theme` / `.lang` and
   clears `themeAuto` (same seed as `scripts/capture_page_evidence.py`).
2. After load, stamps `document.documentElement` `data-theme` and
   `data-lang` (and `documentElement.lang`). The cell is refused if the
   observed attributes do not match the requested theme/lang.
3. `color_scheme` on the browser context matches the requested theme so
   `prefers-color-scheme` agrees. This page's material does not key off
   that media query; `data-theme` is the load-bearing switch.

`window.setTheme()` is **not** called after load. Calling it fires the
`.sky-fx` sun/moon flourish, which is a capture artifact over the cards.
The attribute stamp is the same DOM state `setTheme` would leave.

## What differs from a live `site/alerts.html` visit

- Feed is the two fixture cards, not the nightly board. Backdrop / regime
  JSON is absent in this sparse tree (`PARTIAL` coverage in the assembler).
- Page chrome was hidden for the crop so the strip + both un-capped
  bodies sit fully in frame: `.site-nav`, `.hero`, sticky `.filterbar`
  (otherwise overlays `#feed` when Playwright scrolls it into view),
  `#mmb-boot` (Ask Mastermind fab covered the BLIND clause on 1440),
  `.sky-fx`. Other `.panel` blocks (backdrop, methodology, empty states)
  are hidden; the story-strip `.panel` is kept. Those overlays are
  pre-existing and not the subject of this matrix.
- r3 vs r2: the story strip is now IN the crop (r2 hid all `.panel`, so
  `truncate(70, …)` had zero visual cells). Un-capped bodies wrap at
  `max-width:62ch` instead of running the full card width at 1440.
- Theme CSS is the repo file (`templates/theme.css` +
  `product-nav-icons.css` + self-hosted `templates/fonts/Inter-*.woff2`),
  served next to the rendered HTML. Inter loads; no Google Fonts.
- `theme.js` is present for the boot path; the crop does not exercise the
  settings popover click.

Nothing was hand-painted. Dark and light are the CSS token sets keyed by
`data-theme`. EN and ZH are the dual `l-en` / `l-zh` spans keyed by
`data-lang`.
