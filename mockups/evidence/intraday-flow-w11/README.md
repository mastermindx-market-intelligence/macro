# Intraday Flow W11 r5 — 16-cell evidence matrix

S1 rig: Playwright against fixture feeds on the real `body.page-intraday-flow` page
(not an overlay-column crop). `data-theme` / `data-lang` applied via `setTheme` /
`setLang` (mismatch refuses). Overlays `.ift-aurora`, `.mx5-aurora`, `.sky-fx`,
`#mmb-root`, `#mmb-boot` are removed before each shot. `window.__skyDeck = true`.
`prefers-reduced-motion: reduce`. At-rest text is read from computed styles
(display/visibility/opacity + inactive `.l-en`/`.l-zh` spans skipped), never
from HTML source. PNGs are content-addressed `sha256[:16].png`.

Recapture: `python3 mockups/evidence/intraday-flow-w11/capture.py`

**fixture N = 12.** The fixture holds 12 leaders. Default board shows 8 of 12
with `See all 12` / `查看全部 12 只`; expansion renders exactly 12 rows. It is
count-true. It is not 116; 12 is what the fixture actually holds.

Captured 2026-09-11T08:50:00Z at committed head `c47117579e66ff820dd5c19cb67958896be2926d`
with empty `git status --porcelain` (rig-enforced). 64 cells, 64 overlay-clean.
58 PNGs on disk; the 6-file delta is content-addressed reuse (`f-board-default-*`
byte-identical to `baseline-board-*`). README cells↔PNGs reconcile 64/64, no orphans.

## DARK TREATMENT

Command center. Page canvas `--bg:#0a0c11`, panels `--panel:#14171e` with glass
line and restrained inset highlight. Stamp is muted graphite instrument type.
The `?` LENS control is a small ring; the feed-status tip is an opaque
`--panel` card (`body.page-intraday-flow .lens-pop` kills backdrop-filter so
the desk does not wash through). Tape chips are filled `--info` pills on the
dark sheet. See-all inherits muted and underlines. Degraded `No read` sits in
the aside lane with no glow. Skeletons shimmer on the dark panel.

## LIGHT TREATMENT

Research workspace. Forced `data-theme="light"` on `<html>`. Page canvas
`--bg:#e8ebf1`, panels white `--panel:#ffffff`, hairline `--line`, elevation
from shadow instead of glow (`--glass-sh` becomes a cool drop shadow + white
inset). See-all is an ink-link (`--ink-link`) with a 2px hover underline — an
action on white, not a glow. Stamp type is mixed toward `--text` so it does
not wash out. The LENS `?` is a white chip with a hairline and a 1px rest
shadow. Tape chips ghost/hairline in light — recessive by design (`大单` /
`新建仓` are transparent ground, hairline border, muted ink — not filled
pills). Skeleton shimmer is a low-contrast ink wash
on white, no glow. The rebuilt stamp + LENS tip is a white card with
`0 10px 28px` cool shadow.

## Which mechanisms intentionally differ

Shared: information architecture, bilingual `.l-en`/`.l-zh` spans, See-all
control, LENS tip (theme.js open/close), Tape-chip lexicon, dealer-line
geometry, skeleton geometry, stance lanes.

Intentionally different material: dark depth is luminance + restrained glass
glow; light depth is white plane + hairline + drop shadow. See-all color
inherits muted on dark and becomes an ink-link on light. Stamp LENS `?` is a
ring on graphite and a white chip with hairline on the research canvas.
Skeleton shimmer is a bright sweep on dark and a low-ink wash on light.
Token substitution alone is not the light design — the three new surfaces
(See-all, stamp+LENS, Tape chips) have dedicated `html[data-theme="light"]`
rules.

**Degraded (light and dark):** quotes outage during RTH paints `No read` /
`暂无判断` with `Prices aren't coming through — no read on this name right now`
/ `行情未送达——该标的暂无判断`. Stamp headline `prices not coming through` /
`行情数据未送达`. no freshness-claiming live/实时 string; the labelled signal-count 'setups live' is present and seat-ratified 2026-09-11.

**Scope note:** Tape and Dealer-map columns are `hide-narrow` and do not
render ≤820px. C1 chip proofs are desktop-only. 390w shots prove the mobile
reduction and See-all behavior, not the chips.

Daily-ness of expected move lives on the existing Tier-2 dealer-map help and
the detail row `Expected move (day)` / `预期波动（日）`. No new popover.

## P0 DOM-grep receipt (state d, computed styles)

Quotes forced unavailable during RTH. Visible-text grep for `live`/`实时`:

| Cell | `#ift-stamp` | visible `live`/`实时` hits |
|---|---|---|
| `d-quotes-outage-dark-en-1440` | `Board built 10 Sep 11:34pm UTC · prices not coming through` | no freshness-claiming live/实时 string; the labelled signal-count 'setups live' is present and seat-ratified 2026-09-11 |
| `d-quotes-outage-light-en-1440` | same | same |
| `d-quotes-outage-dark-zh-1440` | `看板构建于9月10日 23:34 UTC · 行情数据未送达` | none (`活跃布局`, no `实时`) |
| `d-quotes-outage-light-zh-1440` | same | none |

No-read stance is in frame on every (d) cell. Overlay-clean true.

## Cell table (16 baselines + states)

overlay-clean is per-crop (viewport frame after overlay removal).

| Cell | File | Theme | Lang | Viewport | overlay-clean | In frame |
|---|---|---|---|---|---|---|
| `baseline-hero-dark-en-1440` | `70d7771c96904994.png` | dark | en | 1440×900 | true | LENS tip 3 rows: quotes · carrying prices / tape · carrying trades / options · carrying flow; stamp all feeds carrying |
| `baseline-hero-light-en-1440` | `fd0c9cb78d9083ed.png` | light | en | 1440×900 | true | LENS tip 3 rows on white; act name in spotlight |
| `baseline-hero-dark-zh-1440` | `be758c594d7e3eda.png` | dark | zh | 1440×900 | true | LENS tip 3 rows: 行情 · 报价已送达 / 资金带 · 成交已送达 / 期权流 · 流数据已送达; 各路数据已送达 |
| `baseline-hero-light-zh-1440` | `320568a6a9cdfb49.png` | light | zh | 1440×900 | true | LENS tip 3 rows on white |
| `baseline-hero-dark-en-390` | `6002e275ecccf0f9.png` | dark | en | 390×844 | true | mobile reduction |
| `baseline-hero-light-en-390` | `2dcbb2d5d3334ec5.png` | light | en | 390×844 | true | mobile reduction |
| `baseline-hero-dark-zh-390` | `fc5f150c16021fb3.png` | dark | zh | 390×844 | true | mobile reduction |
| `baseline-hero-light-zh-390` | `7593a0766968ed43.png` | light | zh | 390×844 | true | mobile reduction |
| `baseline-board-dark-en-1440` | `b30ca33299780236.png` | dark | en | 1440×900 | true | chips `big block`/`new position`; `~2.4% expected move`; See all 12 |
| `baseline-board-light-en-1440` | `18e1098829cede0f.png` | light | en | 1440×900 | true | ghost/hairline chips `big block`/`new position` (recessive); See-all ink-link |
| `baseline-board-dark-zh-1440` | `bf1b80452752cb84.png` | dark | zh | 1440×900 | true | chips `大单`/`新建仓`; `~预期波动约2.4%`; 查看全部 12 只 |
| `baseline-board-light-zh-1440` | `507b40ee6275f62d.png` | light | zh | 1440×900 | true | ghost/hairline chips `大单`/`新建仓` on white |
| `baseline-board-dark-en-390` | `17206c8aa2369c0b.png` | dark | en | 390×844 | true | See-all; chips hidden (≤820) |
| `baseline-board-light-en-390` | `56ddcc3c6a26fcc4.png` | light | en | 390×844 | true | See-all; chips hidden |
| `baseline-board-dark-zh-390` | `7af3c1d5bd492275.png` | dark | zh | 390×844 | true | 查看全部 12 只 |
| `baseline-board-light-zh-390` | `6e2401121cfbe28a.png` | light | zh | 390×844 | true | 查看全部 12 只 |
| `a-market-open-dark-en-1440` | `256fee67c9d75738.png` | dark | en | 1440×900 | true | ≥1 act (NVDA Buy now); LENS tip 3 rows |
| `a-market-open-light-en-1440` | `97c963878678bff6.png` | light | en | 1440×900 | true | ≥1 act on white |
| `a-market-open-dark-zh-1440` | `22a3919cdbacd14f.png` | dark | zh | 1440×900 | true | 现在买入 |
| `a-market-open-light-zh-1440` | `b941a6100b03426f.png` | light | zh | 1440×900 | true | 现在买入 |
| `b-skeleton-dark-en-1440` | `de6c3994eb187e92.png` | dark | en | 1440×900 | true | r2 wordless skels in hero/spot/board |
| `b-skeleton-light-en-1440` | `03676edbedcf6910.png` | light | en | 1440×900 | true | skels on white, no glow |
| `b-skeleton-dark-zh-1440` | `430480fb4e25aac6.png` | dark | zh | 1440×900 | true | wordless (bilingual CSS) |
| `b-skeleton-light-zh-1440` | `0f71d73205a225f2.png` | light | zh | 1440×900 | true | wordless |
| `b-skeleton-dark-en-390` | `fb0978990af9a9e8.png` | dark | en | 390×844 | true | mobile skels |
| `b-skeleton-dark-zh-390` | `18711a2da60bb9eb.png` | dark | zh | 390×844 | true | mobile skels |
| `c-spotlight-empty-dark-en-1440` | `d4841cbb1d6b5b20.png` | dark | en | 1440×900 | true | live empty: No fresh setups (r1 DNT #2) |
| `c-spotlight-empty-light-en-1440` | `67de3388dcc92198.png` | light | en | 1440×900 | true | same empty on white |
| `c-spotlight-empty-dark-zh-1440` | `5df46f334e09b9e1.png` | dark | zh | 1440×900 | true | 当前无新布局 |
| `c-spotlight-empty-light-zh-1440` | `5d392984e1da80c7.png` | light | zh | 1440×900 | true | 当前无新布局 |
| `d-quotes-outage-dark-en-1440` | `72e6a468536b5fac.png` | dark | en | 1440×900 | true | P0: No read leads; aux cells subordinated (2.4× holding / ceiling-floor / ~call buying stay); stamp prices not coming through; no freshness-claiming live/实时 string; the labelled signal-count 'setups live' is present and seat-ratified 2026-09-11 |
| `d-quotes-outage-light-en-1440` | `a4cb854e123fbb67.png` | light | en | 1440×900 | true | No read leads on white; aux cells muted; ghost/hairline chips; setups live seat-ratified |
| `d-quotes-outage-dark-zh-1440` | `5e945d499aea22f4.png` | dark | zh | 1440×900 | true | 暂无判断 leads; aux subordinated; 行情数据未送达 |
| `d-quotes-outage-light-zh-1440` | `05f94dc83f5f7338.png` | light | zh | 1440×900 | true | 暂无判断 leads; aux muted on white |
| `e-options-outage-dark-en-1440` | `b98e6bb4f6984bdc.png` | dark | en | 1440×900 | true | stamp `options flow not coming through`; tip rows tape · carrying trades / options · flow not coming through |
| `e-options-outage-light-en-1440` | `9ca1c3debeb74308.png` | light | en | 1440×900 | true | same headline on white; tip 3 rows |
| `e-options-outage-dark-zh-1440` | `6a92df518b6b2b80.png` | dark | zh | 1440×900 | true | 期权流数据未送达 |
| `e-options-outage-light-zh-1440` | `5f5d871604700fe5.png` | light | zh | 1440×900 | true | 期权流数据未送达 |
| `f-board-default-dark-en-1440` | `b30ca33299780236.png` | dark | en | 1440×900 | true | Showing 8 of 12 · See all 12 |
| `f-board-default-light-en-1440` | `18e1098829cede0f.png` | light | en | 1440×900 | true | ghost/hairline chips; See all 12 ink-link (reuse of baseline-board-light-en-1440) |
| `f-board-default-dark-zh-1440` | `bf1b80452752cb84.png` | dark | zh | 1440×900 | true | 显示 8 / 12 只 · 查看全部 12 只 |
| `f-board-default-light-zh-1440` | `507b40ee6275f62d.png` | light | zh | 1440×900 | true | ghost/hairline chips; 查看全部 12 只 (reuse of baseline-board-light-zh-1440) |
| `f-board-default-dark-en-390` | `17206c8aa2369c0b.png` | dark | en | 390×844 | true | See-all, chips hidden |
| `f-board-default-dark-zh-390` | `7af3c1d5bd492275.png` | dark | zh | 390×844 | true | 查看全部 12 只 |
| `g-board-expanded-dark-en-1440` | `a695694bac61affd.png` | dark | en | 1440×900 | true | Showing 12 of 12 · Show top 8 ↑ |
| `g-board-expanded-light-en-1440` | `18115eea479f6c02.png` | light | en | 1440×900 | true | Show top 8 ↑ |
| `g-board-expanded-dark-zh-1440` | `61d258221b3b048a.png` | dark | zh | 1440×900 | true | 显示 12 / 12 只 · 只看前 8 只 |
| `g-board-expanded-light-zh-1440` | `d938a938ccc18e10.png` | light | zh | 1440×900 | true | 只看前 8 只 |
| `g-board-expanded-dark-en-390` | `99fc63238969b22b.png` | dark | en | 390×844 | true | Show top 8 ↑ |
| `g-board-expanded-dark-zh-390` | `31fc1d667a5458e9.png` | dark | zh | 390×844 | true | 只看前 8 只 |
| `h-basket-grid-dark-en-1440` | `74018c2e988ce961.png` | dark | en | 1440×900 | true | Power Grid chip; 4 leaders; Power Grid sub-labels |
| `h-basket-grid-light-en-1440` | `898709752a20809e.png` | light | en | 1440×900 | true | same on white |
| `h-basket-grid-dark-zh-1440` | `cab030ee5cc2a3d3.png` | dark | zh | 1440×900 | true | M2: 电网 chip active; row sub-labels 电网; 共 4 只 |
| `h-basket-grid-light-zh-1440` | `f14624804ab3102a.png` | light | zh | 1440×900 | true | 电网 on white |
| `i-search-narrow-dark-en-1440` | `602eab7c2d3a61c7.png` | dark | en | 1440×900 | true | `1 leader`; no See-all |
| `i-search-narrow-light-en-1440` | `d391a2dff1d15ad3.png` | light | en | 1440×900 | true | `1 leader` |
| `i-search-narrow-dark-zh-1440` | `765d1ff460cb6b28.png` | dark | zh | 1440×900 | true | `共 1 只`; no 查看全部 |
| `i-search-narrow-light-zh-1440` | `45aedbad83eb099d.png` | light | zh | 1440×900 | true | `共 1 只` |
| `i-search-narrow-dark-en-390` | `7b05d30871661763.png` | dark | en | 390×844 | true | `1 leader` |
| `i-search-narrow-dark-zh-390` | `f70518d44e83c2fc.png` | dark | zh | 390×844 | true | `共 1 只` |
| `j-row-expanded-dark-en-1440` | `de3e6c9eda307eb2.png` | dark | en | 1440×900 | true | Tier-2 detail: VWAP, expected move (day), receipts |
| `j-row-expanded-light-en-1440` | `cf39b960f55897a0.png` | light | en | 1440×900 | true | detail on white |
| `j-row-expanded-dark-zh-1440` | `bf7528abbd47b992.png` | dark | zh | 1440×900 | true | 当日VWAP / 预期波动（日） |
| `j-row-expanded-light-zh-1440` | `102fcbe6509e222d.png` | light | zh | 1440×900 | true | detail on white |

Volume-column session-anchored tip (`This session's volume vs a normal day at this exact time` / `本时段成交量与同一时段正常水平之比`) lives on the header `help()`; the matrix does not hover that control, so the string is source-proven (r4 whole-template sweep) rather than in-frame. Feed-status tip rows and headlines are in-frame on the hero/outage cells above.

r5 recapture at committed head `c47117579e66`; porcelain empty at capture. Content-addressed reuse is honest (cells.json 64 rows, 58 PNGs, 6 shared files, no orphans).
