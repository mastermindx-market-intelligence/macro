# US stocks S2 compression — evidence matrix (round 3)

Four L1 subjects × dark/light × EN/ZH × 1440/390, plus two demotion
landings on the real `sector_central.html.j2` path (same 8-cell matrix),
plus one sector_central action-board control crop proving the megacap
strip does not leak.
REST cells captured: 48/48.

## Fixture

- Stocks: `templates/dashboard.html.j2` (`mode="stocks"`, `body.page-stocks`) + page-scoped `<style>`.
- Landings + control: `templates/sector_central.html.j2` via the builder context shape (`body.macro-desk.page-baskets`, no `mode`). Landing views are forced `.on` (`moving` for `#accumulation`, `explore` for `#theme-tape`).
- VM: `scripts/capture_us_stocks_compression_evidence.fixture_vm` (same shape the page tests use). Holdings label uses `holdings_universe_n=24` (destination-true count in the fixture; noun is 'accumulating' / '项增持').
- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell.

## Overlays hidden for capture (disclosed)

Round-2 crops were contaminated because `window.setTheme` mints `.sky-fx` (sun on light, moon on dark) and the chat FAB (`#mmb-boot`) sits over rows. The fixture now:

1. Sets `window.__skyDeck = true` in the init script so `theme.js` `skyToggleFx` bows out (same gate the landing page uses).
2. Removes `.mx5-aurora`, `.rvx-aurora`, `.sky-fx`, `#mmb-root`, `#mmb-boot`, `.mx-tier-gate` before the screenshot.
3. Records `overlay_dom_clean` per cell (those selectors absent).

Stocks aurora markup is already gated `mode != 'stocks'`; the hide is defence in depth. Sector_central's `.rvx-aurora` is hidden the same way.

## Honest differences from live

- Synthetic numbers (holdings universe N=24 / 8 rows shown, sectors A–D band rows, Mag7 tape from the 2026-07-31 postmortem fixture), not that night's bake.
- No live quote hydration — `#dash-tape-band` stays on the loading chip; `#dash-mtf-body` stays at skeleton geometry (C5 wants this).
- Scratch dir copies `templates/*.css` + `templates/*.js`; nav chrome may 404 paired assets. Crops are element screenshots, so nav is out of frame.
- Sparse checkout has no `data/`; this is why the page is fixture-rendered.

## Cells

| Subject | Theme | Lang | Viewport | Alias | Captured | Overlay DOM clean |
|---|---|---|---|---|---|---|
| action-board | dark | en | desktop | `action-board-dark-en-desktop.png` | yes | yes |
| action-board | light | en | desktop | `action-board-light-en-desktop.png` | yes | yes |
| action-board | dark | zh | desktop | `action-board-dark-zh-desktop.png` | yes | yes |
| action-board | light | zh | desktop | `action-board-light-zh-desktop.png` | yes | yes |
| action-board | dark | en | mobile | `action-board-dark-en-mobile.png` | yes | yes |
| action-board | light | en | mobile | `action-board-light-en-mobile.png` | yes | yes |
| action-board | dark | zh | mobile | `action-board-dark-zh-mobile.png` | yes | yes |
| action-board | light | zh | mobile | `action-board-light-zh-mobile.png` | yes | yes |
| sectors | dark | en | desktop | `sectors-dark-en-desktop.png` | yes | yes |
| sectors | light | en | desktop | `sectors-light-en-desktop.png` | yes | yes |
| sectors | dark | zh | desktop | `sectors-dark-zh-desktop.png` | yes | yes |
| sectors | light | zh | desktop | `sectors-light-zh-desktop.png` | yes | yes |
| sectors | dark | en | mobile | `sectors-dark-en-mobile.png` | yes | yes |
| sectors | light | en | mobile | `sectors-light-en-mobile.png` | yes | yes |
| sectors | dark | zh | mobile | `sectors-dark-zh-mobile.png` | yes | yes |
| sectors | light | zh | mobile | `sectors-light-zh-mobile.png` | yes | yes |
| holdings | dark | en | desktop | `holdings-dark-en-desktop.png` | yes | yes |
| holdings | light | en | desktop | `holdings-light-en-desktop.png` | yes | yes |
| holdings | dark | zh | desktop | `holdings-dark-zh-desktop.png` | yes | yes |
| holdings | light | zh | desktop | `holdings-light-zh-desktop.png` | yes | yes |
| holdings | dark | en | mobile | `holdings-dark-en-mobile.png` | yes | yes |
| holdings | light | en | mobile | `holdings-light-en-mobile.png` | yes | yes |
| holdings | dark | zh | mobile | `holdings-dark-zh-mobile.png` | yes | yes |
| holdings | light | zh | mobile | `holdings-light-zh-mobile.png` | yes | yes |
| dash-mtf | dark | en | desktop | `dash-mtf-dark-en-desktop.png` | yes | yes |
| dash-mtf | light | en | desktop | `dash-mtf-light-en-desktop.png` | yes | yes |
| dash-mtf | dark | zh | desktop | `dash-mtf-dark-zh-desktop.png` | yes | yes |
| dash-mtf | light | zh | desktop | `dash-mtf-light-zh-desktop.png` | yes | yes |
| dash-mtf | dark | en | mobile | `dash-mtf-dark-en-mobile.png` | yes | yes |
| dash-mtf | light | en | mobile | `dash-mtf-light-en-mobile.png` | yes | yes |
| dash-mtf | dark | zh | mobile | `dash-mtf-dark-zh-mobile.png` | yes | yes |
| dash-mtf | light | zh | mobile | `dash-mtf-light-zh-mobile.png` | yes | yes |
| accumulation-landing | dark | en | desktop | `accumulation-landing-dark-en-desktop.png` | yes | yes |
| accumulation-landing | light | en | desktop | `accumulation-landing-light-en-desktop.png` | yes | yes |
| accumulation-landing | dark | zh | desktop | `accumulation-landing-dark-zh-desktop.png` | yes | yes |
| accumulation-landing | light | zh | desktop | `accumulation-landing-light-zh-desktop.png` | yes | yes |
| accumulation-landing | dark | en | mobile | `accumulation-landing-dark-en-mobile.png` | yes | yes |
| accumulation-landing | light | en | mobile | `accumulation-landing-light-en-mobile.png` | yes | yes |
| accumulation-landing | dark | zh | mobile | `accumulation-landing-dark-zh-mobile.png` | yes | yes |
| accumulation-landing | light | zh | mobile | `accumulation-landing-light-zh-mobile.png` | yes | yes |
| theme-tape-landing | dark | en | desktop | `theme-tape-landing-dark-en-desktop.png` | yes | yes |
| theme-tape-landing | light | en | desktop | `theme-tape-landing-light-en-desktop.png` | yes | yes |
| theme-tape-landing | dark | zh | desktop | `theme-tape-landing-dark-zh-desktop.png` | yes | yes |
| theme-tape-landing | light | zh | desktop | `theme-tape-landing-light-zh-desktop.png` | yes | yes |
| theme-tape-landing | dark | en | mobile | `theme-tape-landing-dark-en-mobile.png` | yes | yes |
| theme-tape-landing | light | en | mobile | `theme-tape-landing-light-en-mobile.png` | yes | yes |
| theme-tape-landing | dark | zh | mobile | `theme-tape-landing-dark-zh-mobile.png` | yes | yes |
| theme-tape-landing | light | zh | mobile | `theme-tape-landing-light-zh-mobile.png` | yes | yes |
| sector-central-action | dark | en | desktop | `sector-central-action-dark-en-desktop.png` | yes leaked=False | yes |

## Floor (390 / 768 / 1440)

See `g8.json`. Checks: page horizontal scroll, focus-visible ring, `?` tap at 390, reduced-motion skeleton, chip wrap, in-container table scroll.

| Width | Page h-scroll | Focus ring | `?` tap | Reduced-motion skeleton | Chip wrap | Table in-container |
|---|---|---|---|---|---|---|
| 390 | none | visible | open (LENS or `.tip-open`) | `animation-name: none`, header bar 30px | wrap (`.acb-tape`) | `.tbl-scroll` overflow-x auto |
| 768 | none | visible | n/a | n/a | wrap | no overflow |
| 1440 | none | visible | n/a | n/a | wrap | no overflow |

## G-gate per-subject verdicts (judged from the crops)

Spec §0.3's 16-crop floor is `{dark,light}×{EN,ZH}` at 1440 plus the same four subjects at 390 = **32 REST cells** on us_stocks. Round 3 adds 16 landing cells on sector_central + the control. Overlay re-judgment is the `Overlay DOM clean` column plus a visual pass for aurora / sky-fx / FAB over content.

| Subject | Cells | Verdict | Notes |
|---|---|---|---|
| action-board (C1 + C4 theme link) | 8 | **PASS** | Header + megacap strip read as one block; one as-of stamp; figure is the only saturated ink; light crop shows the `--panel2` inset band; 390 wraps; no aurora/sky-fx/FAB over the IN-FAVOUR lane. |
| sectors (C2) | 8 | **PASS** | Band words (`washed out`/`超卖`, `mid-range`/`中位`, `stretched`/`拉伸`, `even odds`/`胜率接近五五`, `more often up`/`多数时候上涨`, `rolling over`/`正在回落`, `turning up`/`正在转强`); no `usually up`; seasonality is magnitude only; table scrolls inside `.tbl-scroll` at 390. |
| holdings (C3 + C4 accumulation link + nulls) | 8 | **PASS** | Exactly 8 data rows; `See all 24 accumulating →` / `查看全部 24 项增持 →` (destination accumulate N, not the sliced 12); technical `no signal yet` / `暂无信号`; ZH 390 nowraps inside `.tbl-scroll` (min-width 640px) instead of crushing columns. No moon glyph / FAB over rows. |
| dash-mtf (C5) | 8 | **PASS** | Skeleton at true geometry (30px header + 38px rows), no words; dark shimmer = lift; light shimmer = grey wash. |
| accumulation-landing | 8 | **PASS** | `#accumulation` inside `#si-movement` on the real sector_central path; help/tip + tbl-scroll self-styled; `Top 8 · 24 tracked`. |
| theme-tape-landing | 8 | **PASS** | `#theme-tape` inside `#explore-section` on the real sector_central path; CSS retargeted off `body.page-stocks` onto `#theme-tape`. |
| sector-central-action (control) | 1 | **PASS** | Full page skeleton (`body.macro-desk.page-baskets`); action board present, **no** `.acb-tape` / megacap strip. |

## Composition / harness fixes this round

- Capture harness renders the real page body classes (`body.page-stocks`, `body.macro-desk.page-baskets`), not a standalone partial.
- Decorative layers hidden and disclosed (see Overlays section).
- Holdings / accumulation tables `min-width:640px` + `white-space:nowrap` so 390 ZH scrolls inside `.tbl-scroll` instead of wrapping one-char columns.
- Theme-tape CSS scoped to `#theme-tape` so it paints on sector_central.
- Accumulation watch ships its own help/tip + tbl-scroll CSS.

