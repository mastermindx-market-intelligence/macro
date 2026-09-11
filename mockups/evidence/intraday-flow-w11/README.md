# Intraday Flow W11 r3 — 16-cell evidence matrix

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

Captured 2026-09-11T07:52:23Z. 64 cells, 64 overlay-clean.

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
shadow. Tape chips (`大单` / `新建仓`) are the same filled info pills on the
white sheet and stay readable. Skeleton shimmer is a low-contrast ink wash
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
`行情数据未送达`. No `live` / `实时` in `#ift-stamp`. The labelled slice
`setups live` / `活跃布局` is DO-NOT-TOUCH #8 and does not assert real-time
pricing.

**Scope note:** Tape and Dealer-map columns are `hide-narrow` and do not
render ≤820px. C1 chip proofs are desktop-only. 390w shots prove the mobile
reduction and See-all behavior, not the chips.

Daily-ness of expected move lives on the existing Tier-2 dealer-map help and
the detail row `Expected move (day)` / `预期波动（日）`. No new popover.

## P0 DOM-grep receipt (state d, computed styles)

Quotes forced unavailable during RTH. Visible-text grep for `live`/`实时`:

| Cell | `#ift-stamp` | visible `live`/`实时` hits |
|---|---|---|
| `d-quotes-outage-dark-en-1440` | `Board built 10 Sep 11:34pm UTC · prices not coming through` | `setups live` only (DNT #8, not in stamp) |
| `d-quotes-outage-light-en-1440` | same | `setups live` only |
| `d-quotes-outage-dark-zh-1440` | `看板构建于9月10日 23:34 UTC · 行情数据未送达` | none (`活跃布局`, no `实时`) |
| `d-quotes-outage-light-zh-1440` | same | none |

No-read stance is in frame on every (d) cell. Overlay-clean true.

## Cell table (16 baselines + states)

overlay-clean is per-crop (viewport frame after overlay removal).

| Cell | File | Theme | Lang | Viewport | overlay-clean | In frame |
|---|---|---|---|---|---|---|
| `baseline-hero-dark-en-1440` | `5dc839795b9caa4d.png` | dark | en | 1440×900 | true | LENS tip; stamp all-feeds-carrying |
| `baseline-hero-light-en-1440` | `7b494906dffbf389.png` | light | en | 1440×900 | true | LENS tip on white; act name in spotlight |
| `baseline-hero-dark-zh-1440` | `7d50d3d9d2e21dee.png` | dark | zh | 1440×900 | true | LENS tip; 各路数据已送达 |
| `baseline-hero-light-zh-1440` | `7562f4b09be64e5a.png` | light | zh | 1440×900 | true | LENS tip on white |
| `baseline-hero-dark-en-390` | `30802381dd2428c9.png` | dark | en | 390×844 | true | mobile reduction |
| `baseline-hero-light-en-390` | `887348238580f804.png` | light | en | 390×844 | true | mobile reduction |
| `baseline-hero-dark-zh-390` | `9accce784e6ee462.png` | dark | zh | 390×844 | true | mobile reduction |
| `baseline-hero-light-zh-390` | `7593a0766968ed43.png` | light | zh | 390×844 | true | mobile reduction |
| `baseline-board-dark-en-1440` | `f4413ff63f3ceca8.png` | dark | en | 1440×900 | true | chips `big block`/`new position`; `~2.4% expected move`; See all 12 |
| `baseline-board-light-en-1440` | `a70b9d8f2118760c.png` | light | en | 1440×900 | true | chips on white; See-all ink-link |
| `baseline-board-dark-zh-1440` | `f1b599fe3349af6a.png` | dark | zh | 1440×900 | true | chips `大单`/`新建仓`; `~预期波动约2.4%`; 查看全部 12 只 |
| `baseline-board-light-zh-1440` | `efb692ae0dbd92b1.png` | light | zh | 1440×900 | true | translated chips on white |
| `baseline-board-dark-en-390` | `8467eb299b5ff56d.png` | dark | en | 390×844 | true | See-all; chips hidden (≤820) |
| `baseline-board-light-en-390` | `9db8d8554732e083.png` | light | en | 390×844 | true | See-all; chips hidden |
| `baseline-board-dark-zh-390` | `75ca84800d6ac9e7.png` | dark | zh | 390×844 | true | 查看全部 12 只 |
| `baseline-board-light-zh-390` | `95f85b6a7ce7b1df.png` | light | zh | 390×844 | true | 查看全部 12 只 |
| `a-market-open-dark-en-1440` | `6a5e1031a3f5ea35.png` | dark | en | 1440×900 | true | ≥1 act (NVDA Buy now) |
| `a-market-open-light-en-1440` | `6196917b86eba8b6.png` | light | en | 1440×900 | true | ≥1 act on white |
| `a-market-open-dark-zh-1440` | `019d09c6167fc8d6.png` | dark | zh | 1440×900 | true | 现在买入 |
| `a-market-open-light-zh-1440` | `b941a6100b03426f.png` | light | zh | 1440×900 | true | 现在买入 |
| `b-skeleton-dark-en-1440` | `de6c3994eb187e92.png` | dark | en | 1440×900 | true | r2 wordless skels in hero/spot/board |
| `b-skeleton-light-en-1440` | `03676edbedcf6910.png` | light | en | 1440×900 | true | skels on white, no glow |
| `b-skeleton-dark-zh-1440` | `430480fb4e25aac6.png` | dark | zh | 1440×900 | true | wordless (bilingual CSS) |
| `b-skeleton-light-zh-1440` | `10b1223643ff0e99.png` | light | zh | 1440×900 | true | wordless |
| `b-skeleton-dark-en-390` | `fb0978990af9a9e8.png` | dark | en | 390×844 | true | mobile skels |
| `b-skeleton-dark-zh-390` | `18711a2da60bb9eb.png` | dark | zh | 390×844 | true | mobile skels |
| `c-spotlight-empty-dark-en-1440` | `42e6da651af4a719.png` | dark | en | 1440×900 | true | live empty: No fresh setups (r1 DNT #2) |
| `c-spotlight-empty-light-en-1440` | `e12016f3d9978cf7.png` | light | en | 1440×900 | true | same empty on white |
| `c-spotlight-empty-dark-zh-1440` | `e98f3a67b5e0fe29.png` | dark | zh | 1440×900 | true | 当前无新布局 |
| `c-spotlight-empty-light-zh-1440` | `40b9790b7dc71efa.png` | light | zh | 1440×900 | true | 当前无新布局 |
| `d-quotes-outage-dark-en-1440` | `f18f871d70a26b7d.png` | dark | en | 1440×900 | true | P0: No read rows; stamp prices not coming through |
| `d-quotes-outage-light-en-1440` | `dba64794252f1398.png` | light | en | 1440×900 | true | No read on white |
| `d-quotes-outage-dark-zh-1440` | `48f1384b26a057cd.png` | dark | zh | 1440×900 | true | 暂无判断; 行情数据未送达 |
| `d-quotes-outage-light-zh-1440` | `cf2e3181ebe01cac.png` | light | zh | 1440×900 | true | 暂无判断 |
| `e-options-outage-dark-en-1440` | `00d24df3ac2de8cc.png` | dark | en | 1440×900 | true | stamp `options flow not coming through` |
| `e-options-outage-light-en-1440` | `36e5ff6a8ed30d42.png` | light | en | 1440×900 | true | same headline on white |
| `e-options-outage-dark-zh-1440` | `1c2a7437c1412b83.png` | dark | zh | 1440×900 | true | 期权流数据未送达 |
| `e-options-outage-light-zh-1440` | `5f5d871604700fe5.png` | light | zh | 1440×900 | true | 期权流数据未送达 |
| `f-board-default-dark-en-1440` | `f4413ff63f3ceca8.png` | dark | en | 1440×900 | true | Showing 8 of 12 · See all 12 |
| `f-board-default-light-en-1440` | `a70b9d8f2118760c.png` | light | en | 1440×900 | true | See all 12 ink-link |
| `f-board-default-dark-zh-1440` | `f1b599fe3349af6a.png` | dark | zh | 1440×900 | true | 显示 8 / 12 只 · 查看全部 12 只 |
| `f-board-default-light-zh-1440` | `efb692ae0dbd92b1.png` | light | zh | 1440×900 | true | 查看全部 12 只 |
| `f-board-default-dark-en-390` | `8467eb299b5ff56d.png` | dark | en | 390×844 | true | See-all, chips hidden |
| `f-board-default-dark-zh-390` | `75ca84800d6ac9e7.png` | dark | zh | 390×844 | true | 查看全部 12 只 |
| `g-board-expanded-dark-en-1440` | `391aa90fc6d5d3c9.png` | dark | en | 1440×900 | true | Showing 12 of 12 · Show top 8 ↑ |
| `g-board-expanded-light-en-1440` | `fe50af69f8158213.png` | light | en | 1440×900 | true | Show top 8 ↑ |
| `g-board-expanded-dark-zh-1440` | `81a48465f5a4f129.png` | dark | zh | 1440×900 | true | 显示 12 / 12 只 · 只看前 8 只 |
| `g-board-expanded-light-zh-1440` | `45374d959555cff9.png` | light | zh | 1440×900 | true | 只看前 8 只 |
| `g-board-expanded-dark-en-390` | `ebead736fe59dfb4.png` | dark | en | 390×844 | true | Show top 8 ↑ |
| `g-board-expanded-dark-zh-390` | `b095f980549195bd.png` | dark | zh | 390×844 | true | 只看前 8 只 |
| `h-basket-grid-dark-en-1440` | `f6d03a2a0ab02843.png` | dark | en | 1440×900 | true | Power Grid chip; 4 leaders; Power Grid sub-labels |
| `h-basket-grid-light-en-1440` | `9935d815cf67732a.png` | light | en | 1440×900 | true | same on white |
| `h-basket-grid-dark-zh-1440` | `7f8d544a9da8c18f.png` | dark | zh | 1440×900 | true | M2: 电网 chip active; row sub-labels 电网; 共 4 只 |
| `h-basket-grid-light-zh-1440` | `ef5a39cac0964e00.png` | light | zh | 1440×900 | true | 电网 on white |
| `i-search-narrow-dark-en-1440` | `35946d3aae3a49af.png` | dark | en | 1440×900 | true | `1 leader`; no See-all |
| `i-search-narrow-light-en-1440` | `590598526aa573f5.png` | light | en | 1440×900 | true | `1 leader` |
| `i-search-narrow-dark-zh-1440` | `845c3549082e1183.png` | dark | zh | 1440×900 | true | `共 1 只`; no 查看全部 |
| `i-search-narrow-light-zh-1440` | `6f5f33098128a4a5.png` | light | zh | 1440×900 | true | `共 1 只` |
| `i-search-narrow-dark-en-390` | `aa57a8379db1845c.png` | dark | en | 390×844 | true | `1 leader` |
| `i-search-narrow-dark-zh-390` | `c58ff69fe9f5c878.png` | dark | zh | 390×844 | true | `共 1 只` |
| `j-row-expanded-dark-en-1440` | `daf594d0abea0293.png` | dark | en | 1440×900 | true | Tier-2 detail: VWAP, expected move (day), receipts |
| `j-row-expanded-light-en-1440` | `e12973a753299b53.png` | light | en | 1440×900 | true | detail on white |
| `j-row-expanded-dark-zh-1440` | `5cfe6b1c92c901d6.png` | dark | zh | 1440×900 | true | 当日VWAP / 预期波动（日） |
| `j-row-expanded-light-zh-1440` | `c6dc8fe37ed87798.png` | light | zh | 1440×900 | true | detail on white |

Every r2-changed subject (stamp, tip, control, skeletons, outage stance)
appears in a fresh full-frame cell. No r2 crop is reused.
