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

Captured 2026-09-21T12:03:10Z at committed head `ff81d9bbb2a9a8b587644c75ee936a99ce6c490c`
with empty `git status --porcelain` (rig-enforced). 68 cells, 68 overlay-clean (64 rest/named + 4 See-all hover/focus).
62 PNGs on disk; content-addressed reuse is honest (`f-board-default-*` byte-identical to
`baseline-board-*`; board/outage/see-all cells whose pixels did not move kept their hashes). README cells↔PNGs reconcile 64/64, no orphans.

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
action on white, not a glow. Stamp type is `--muted`. The LENS `?` is a white
`--panel` chip with `--line` hairline and `--card-shadow`. Tape chips ghost/hairline in light — recessive by design (`大单` /
`新建仓` are transparent ground, `--line` hairline, `--muted` ink — not filled
pills). Skeleton shimmer is the design-system `.skel` wash
on `--panel2`, no glow. The rebuilt stamp + LENS tip is a white card with
`--popover-shadow`.

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
| `baseline-hero-dark-en-1440` | `3bee645a66b14863.png` | dark | en | 1440×900 | true | LENS tip 3 rows: quotes · carrying prices / tape · carrying trades / options · carrying flow; stamp all feeds carrying |
| `baseline-hero-light-en-1440` | `684ef97e06dd1580.png` | light | en | 1440×900 | true | LENS tip 3 rows on white; act name in spotlight |
| `baseline-hero-dark-zh-1440` | `3d34da2658bd61e6.png` | dark | zh | 1440×900 | true | LENS tip 3 rows: 行情 · 报价已送达 / 资金带 · 成交已送达 / 期权流 · 流数据已送达; 各路数据已送达 |
| `baseline-hero-light-zh-1440` | `c66d07c9aa3f5de8.png` | light | zh | 1440×900 | true | LENS tip 3 rows on white |
| `baseline-hero-dark-en-390` | `270d73b170815b83.png` | dark | en | 390×844 | true | mobile reduction |
| `baseline-hero-light-en-390` | `d999d12465c1a408.png` | light | en | 390×844 | true | mobile reduction |
| `baseline-hero-dark-zh-390` | `e30373d78f4d964f.png` | dark | zh | 390×844 | true | mobile reduction |
| `baseline-hero-light-zh-390` | `51be30858758a0eb.png` | light | zh | 390×844 | true | mobile reduction |
| `baseline-board-dark-en-1440` | `8d74e8e2ac71b0f3.png` | dark | en | 1440×900 | true | chips `big block`/`new position`; `~2.4% expected move`; See all 12 |
| `baseline-board-light-en-1440` | `fbfb041b197c36b7.png` | light | en | 1440×900 | true | ghost/hairline chips `big block`/`new position` (recessive); See-all ink-link |
| `baseline-board-dark-zh-1440` | `9a47d810b76b85ab.png` | dark | zh | 1440×900 | true | chips `大单`/`新建仓`; `~预期波动约2.4%`; 查看全部 12 只 |
| `baseline-board-light-zh-1440` | `80eac7e7ce77ee6e.png` | light | zh | 1440×900 | true | ghost/hairline chips `大单`/`新建仓` on white |
| `baseline-board-dark-en-390` | `fe59630111dc6eea.png` | dark | en | 390×844 | true | See-all; chips hidden (≤820) |
| `baseline-board-light-en-390` | `8ad8d7bbf4666d27.png` | light | en | 390×844 | true | See-all; chips hidden |
| `baseline-board-dark-zh-390` | `7e6b8e6e1c24cb3e.png` | dark | zh | 390×844 | true | 查看全部 12 只 |
| `baseline-board-light-zh-390` | `86226ae3dc61db54.png` | light | zh | 390×844 | true | 查看全部 12 只 |
| `a-market-open-dark-en-1440` | `c88db184f367982b.png` | dark | en | 1440×900 | true | ≥1 act (NVDA Buy now); LENS tip 3 rows |
| `a-market-open-light-en-1440` | `057be3abcab3a73a.png` | light | en | 1440×900 | true | ≥1 act on white |
| `a-market-open-dark-zh-1440` | `3ae33975c07773a1.png` | dark | zh | 1440×900 | true | 现在买入 |
| `a-market-open-light-zh-1440` | `eca7c50b53262274.png` | light | zh | 1440×900 | true | 现在买入 |
| `b-skeleton-dark-en-1440` | `d281a253cbd76048.png` | dark | en | 1440×900 | true | r2 wordless skels in hero/spot/board |
| `b-skeleton-light-en-1440` | `7ad9568c9fab6b3d.png` | light | en | 1440×900 | true | skels on white, no glow |
| `b-skeleton-dark-zh-1440` | `292f1fd65a65b811.png` | dark | zh | 1440×900 | true | wordless (bilingual CSS) |
| `b-skeleton-light-zh-1440` | `11754460b317aff0.png` | light | zh | 1440×900 | true | wordless |
| `b-skeleton-dark-en-390` | `1f72d42a74a302dd.png` | dark | en | 390×844 | true | mobile skels |
| `b-skeleton-dark-zh-390` | `345e66bfe3420b44.png` | dark | zh | 390×844 | true | mobile skels |
| `c-spotlight-empty-dark-en-1440` | `a75d0da83e882af8.png` | dark | en | 1440×900 | true | live empty: No fresh setups (r1 DNT #2) |
| `c-spotlight-empty-light-en-1440` | `aaf128e8bf83b3fc.png` | light | en | 1440×900 | true | same empty on white |
| `c-spotlight-empty-dark-zh-1440` | `994e9d509e16e568.png` | dark | zh | 1440×900 | true | 当前无新布局 |
| `c-spotlight-empty-light-zh-1440` | `a6172f15fac45d17.png` | light | zh | 1440×900 | true | 当前无新布局 |
| `d-quotes-outage-dark-en-1440` | `5d15ad9148101e0f.png` | dark | en | 1440×900 | true | P0: No read leads; aux cells subordinated (2.4× holding / ceiling-floor / ~call buying stay); stamp prices not coming through; no freshness-claiming live/实时 string; the labelled signal-count 'setups live' is present and seat-ratified 2026-09-11 |
| `d-quotes-outage-light-en-1440` | `bbd53def78b23acf.png` | light | en | 1440×900 | true | No read leads on white; aux cells muted; ghost/hairline chips; setups live seat-ratified |
| `d-quotes-outage-dark-zh-1440` | `e46c408a4fa12265.png` | dark | zh | 1440×900 | true | 暂无判断 leads; aux subordinated; 行情数据未送达 |
| `d-quotes-outage-light-zh-1440` | `f0736b40f6a4b00a.png` | light | zh | 1440×900 | true | 暂无判断 leads; aux muted on white |
| `e-options-outage-dark-en-1440` | `629661331cf6170c.png` | dark | en | 1440×900 | true | stamp `options flow not coming through`; tip rows tape · carrying trades / options · flow not coming through |
| `e-options-outage-light-en-1440` | `eb1cbc16af59aece.png` | light | en | 1440×900 | true | same headline on white; tip 3 rows |
| `e-options-outage-dark-zh-1440` | `728b6979f001e4a7.png` | dark | zh | 1440×900 | true | 期权流数据未送达 |
| `e-options-outage-light-zh-1440` | `ecaf6c7f7ffceae0.png` | light | zh | 1440×900 | true | 期权流数据未送达 |
| `f-board-default-dark-en-1440` | `8d74e8e2ac71b0f3.png` | dark | en | 1440×900 | true | Showing 8 of 12 · See all 12 |
| `f-board-default-light-en-1440` | `fbfb041b197c36b7.png` | light | en | 1440×900 | true | ghost/hairline chips; See all 12 ink-link (reuse of baseline-board-light-en-1440) |
| `f-board-default-dark-zh-1440` | `9a47d810b76b85ab.png` | dark | zh | 1440×900 | true | 显示 8 / 12 只 · 查看全部 12 只 |
| `f-board-default-light-zh-1440` | `80eac7e7ce77ee6e.png` | light | zh | 1440×900 | true | ghost/hairline chips; 查看全部 12 只 (reuse of baseline-board-light-zh-1440) |
| `f-board-default-dark-en-390` | `fe59630111dc6eea.png` | dark | en | 390×844 | true | See-all, chips hidden |
| `f-board-default-dark-zh-390` | `7e6b8e6e1c24cb3e.png` | dark | zh | 390×844 | true | 查看全部 12 只 |
| `g-board-expanded-dark-en-1440` | `4bcf370074c997e6.png` | dark | en | 1440×900 | true | Showing 12 of 12 · Show top 8 |
| `g-board-expanded-light-en-1440` | `9077bf37c76f04d5.png` | light | en | 1440×900 | true | Show top 8 |
| `g-board-expanded-dark-zh-1440` | `ba16777a723bbc5c.png` | dark | zh | 1440×900 | true | 显示 12 / 12 只 · 只看前 8 只 |
| `g-board-expanded-light-zh-1440` | `77b2a274e2f3260b.png` | light | zh | 1440×900 | true | 只看前 8 只 |
| `g-board-expanded-dark-en-390` | `c708cceb1a9eafb8.png` | dark | en | 390×844 | true | Show top 8 |
| `g-board-expanded-dark-zh-390` | `64d593f513ddb0d7.png` | dark | zh | 390×844 | true | 只看前 8 只 |
| `h-basket-grid-dark-en-1440` | `d7d8c978582fbcdd.png` | dark | en | 1440×900 | true | Power Grid chip; 4 leaders; Power Grid sub-labels |
| `h-basket-grid-light-en-1440` | `9e800befa26e5a6b.png` | light | en | 1440×900 | true | same on white |
| `h-basket-grid-dark-zh-1440` | `08b0277930047eb7.png` | dark | zh | 1440×900 | true | M2: 电网 chip active; row sub-labels 电网; 共 4 只 |
| `h-basket-grid-light-zh-1440` | `3b031535d9f30ff9.png` | light | zh | 1440×900 | true | 电网 on white |
| `i-search-narrow-dark-en-1440` | `d3c5937e45910493.png` | dark | en | 1440×900 | true | `1 leader`; no See-all |
| `i-search-narrow-light-en-1440` | `82b8cf19f70c4e93.png` | light | en | 1440×900 | true | `1 leader` |
| `i-search-narrow-dark-zh-1440` | `f9ffa9c2fed5a5ad.png` | dark | zh | 1440×900 | true | `共 1 只`; no 查看全部 |
| `i-search-narrow-light-zh-1440` | `0e15666322ccd76d.png` | light | zh | 1440×900 | true | `共 1 只` |
| `i-search-narrow-dark-en-390` | `e2fe3e9ea3f2556d.png` | dark | en | 390×844 | true | `1 leader` |
| `i-search-narrow-dark-zh-390` | `19abc900719f4878.png` | dark | zh | 390×844 | true | `共 1 只` |
| `j-row-expanded-dark-en-1440` | `90012cf6e8e9a0d9.png` | dark | en | 1440×900 | true | Tier-2 detail: VWAP, expected move (day), receipts |
| `j-row-expanded-light-en-1440` | `58ce3450a58dc129.png` | light | en | 1440×900 | true | detail on white |
| `j-row-expanded-dark-zh-1440` | `ffec7dac4d222ced.png` | dark | zh | 1440×900 | true | 当日VWAP / 预期波动（日） |
| `j-row-expanded-light-zh-1440` | `802da282fd89f819.png` | light | zh | 1440×900 | true | detail on white |

Volume-column session-anchored tip (`This session's volume vs a normal day at this exact time` / `本时段成交量与同一时段正常水平之比`) lives on the header `help()`; the matrix does not hover that control, so the string is source-proven (r4 whole-template sweep) rather than in-frame. Feed-status tip rows and headlines are in-frame on the hero/outage cells above.

TOKENIZE-7070-R2 recapture at committed head `ff81d9bbb2a9a8b587644c75ee936a99ce6c490c`; porcelain empty at capture. Compass removed from the hero ctx row so hero/open/skeleton/search cells reminted; board/dealer/see-all hashes reused where pixels were unchanged. Content-addressed reuse is honest (cells.json 68 rows, 62 PNGs, no orphans).
