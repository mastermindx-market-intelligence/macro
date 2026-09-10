# start.html Tier-1 plain-language pass — 8-cell composition evidence

PR #7048 r2. The signed-in hub's Other Features chips, hero clock skeleton,
and What-changed first card now speak in plain words. These crops show that
presentation on the real theme/lang mechanism.

## Cells

| file | theme | lang | viewport | PNG (clip) | toggle |
|---|---|---|---|---|---|
| `start-tier1-dark-en-1440.png` | dark | en | 1440×900 | 1216×464 | data-theme=dark data-lang=en |
| `start-tier1-dark-en-390.png` | dark | en | 390×844 | 382×682 | data-theme=dark data-lang=en |
| `start-tier1-dark-zh-1440.png` | dark | zh | 1440×900 | 1216×472 | data-theme=dark data-lang=zh |
| `start-tier1-dark-zh-390.png` | dark | zh | 390×844 | 382×682 | data-theme=dark data-lang=zh |
| `start-tier1-light-en-1440.png` | light | en | 1440×900 | 1216×464 | data-theme=light data-lang=en |
| `start-tier1-light-en-390.png` | light | en | 390×844 | 382×682 | data-theme=light data-lang=en |
| `start-tier1-light-zh-1440.png` | light | zh | 1440×900 | 1216×472 | data-theme=light data-lang=zh |
| `start-tier1-light-zh-390.png` | light | zh | 390×844 | 382×682 | data-theme=light data-lang=zh |

Each cell was refused unless the observed `html[data-theme]` and
`html[data-lang]` matched the requested pair after the stamp.

## What each crop frames

- **(a) Other Features chip row** — Bitcoin Vector pills
  ("Low risk" / "Strong down-momentum" · 「低风险」/「动量偏强向下」) and
  Bonds ("Healthy · late-cycle" / 「健康 · 周期晚段」).
- **(b) Hero clock skeleton** — `.hub-clock-wrap` is **not** `is-live`
  (clock IIFE short-circuited in the capture HTML only). The static
  "Live" / 「实时」 word is visible beside the shimmer bar — the no-JS
  fallback. JS-on would hide the static word and the skeleton together
  once it stamps `is-live`.
- **(c) What-changed first card** — plain EN
  "The regime's footing went from a new regime to shifting (4 warning
  flags active)" and plain ZH
  「周期状态由「新周期」转为「转换中」（4 个预警激活）」. No ` -> ` arrow.

`start-tier1-dark-en-1440.png` also shows the LENS hover tip on the
momentum pill (vote roster: EMA trend, EMA cross, MACD, 200-day SMA,
20-day ROC, RSI, SOPR, short-term holder cost).

## 390 wrap verdict

Product CSS at `max-width:560px` hides `.nav.vc .chips` and `.h .eyebrow`
(compact vector cards). Capture injects a documented override so the
new chip strings can be measured at 390 rather than vanishing.

Measured on the Bitcoin Vector `.chips` after the override
(`flex-wrap: wrap`):

| cell | cardWidth | chipsClient | pill widths | overflowX | wrapped |
|---|---|---|---|---|---|
| dark-en-390 | 350 | 316 | 68 + 164 | **false** | false |
| dark-zh-390 | 350 | 316 | 54 + 89 | **false** | false |
| light-en-390 | 350 | 316 | 68 + 164 | **false** | false |
| light-zh-390 | 350 | 316 | 54 + 89 | **false** | false |

ZH twins are **shorter** than the EN pills (ideographs pack tighter than
"Strong down-momentum"). Both languages fit on one row at 390 with
`overflowX=false` and `overflowCard=false`. Wrap is armed (`flex-wrap:
wrap`) and would catch a future longer string; it does not fire on
these pills.

## Fixture

`scripts.build_vector._hub_html` with:

- Bitcoin Vector: `risk_on=True`, `risk_index=2`, `momentum=-0.8`
- Bonds: `score=88`, `phase=late`, `label=healthy`
- One What-changed row: the plain transition receipt (EN + ZH)
- Globe markets stubbed to US/CN/HK/CA (no `data/` reads)

Capture script (not committed):
`scratchpad/capture_start_tier1_pass.py` next to the r1 review.

## How dark / light / EN / ZH were toggled

The live page mechanism, not a hand-painted palette:

- Hub boot script (and `templates/theme.js`) key off `html[data-theme]`
  and `html[data-lang]`.
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
   `prefers-color-scheme` agrees. This page's material keys off
   `data-theme`, not that media query.

`window.setTheme()` is **not** called after load. Calling it fires the
`.sky-fx` sun/moon flourish, which is a capture artifact over the cards.
The attribute stamp is the same DOM state `setTheme` would leave.

## What differs from a live `site/start.html` visit

- Feed is one fixture transition card, not the nightly board. Globe
  markets are a four-row stub (`_globe_markets` patched for the
  capture). Backdrop JSON is absent in this sparse tree.
- Page chrome was hidden for the crop so chips + clock + first card sit
  fully in frame: `.site-nav`, `#sky`, `.globe-deck`, `.mk-sec`, footer,
  `#mmb-boot`. Vector cards other than Bitcoin Vector and Bonds were
  `display:none` so the 4-col desktop grid packs those two to the start.
- At 390, a capture-only stylesheet un-hides `.nav.vc .chips` and
  `.h .eyebrow` and restores column card geometry so wrap/skeleton can
  be seen. Live product still compact-hides those at `max-width:560px`.
- The clock IIFE is short-circuited (`return` as the first statement)
  so `.hub-clock-wrap` never gains `is-live` — the crop is the skeleton
  + static "Live" word, not a ticking clock.
- Theme CSS is the repo file (`templates/theme.css` +
  `product-nav-icons.css` + self-hosted `templates/fonts/Inter-*.woff2`),
  served next to the rendered HTML. Inter loads; no Google Fonts.
- `theme.js` is present for the boot path and the LENS hover; the crop
  does not exercise the settings popover click.

Nothing was hand-painted. Dark and light are the CSS token sets keyed by
`data-theme`. EN and ZH are the dual `l-en` / `l-zh` spans keyed by
`data-lang`.
