# US stocks S2 compression — evidence matrix (round 2)

Four L1 subjects × dark/light × EN/ZH × 1440/390, plus one sector_central
action-board control crop proving the megacap strip does not leak.
REST cells captured: 32/32.

## Fixture

- Source: `templates/dashboard.html.j2` (`mode="stocks"`) + page-scoped `<style>`.
- VM: `scripts/capture_us_stocks_compression_evidence.fixture_vm` (same shape the page tests use).
- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell.
- Control: `templates/_us_act_now_board.html.j2` rendered **without** `mode='stocks'`.

## Honest differences from live `site/us_stocks.html`

- Synthetic numbers (holdings N=12, sectors A–D band rows, Mag7 tape from the 2026-07-31 postmortem fixture), not that night's bake.
- No live quote hydration — `#dash-tape-band` stays on the loading chip; `#dash-mtf-body` stays at skeleton geometry (C5 wants this).
- Scratch dir copies `templates/*.css` + `templates/*.js`; nav chrome may 404 paired assets. Crops are element screenshots, so nav is out of frame.
- Sparse checkout has no `data/`; this is why the page is fixture-rendered.

## Cells

| Subject | Theme | Lang | Viewport | Alias | Captured |
|---|---|---|---|---|---|
| action-board | dark | en | desktop | `action-board-dark-en-desktop.png` | yes |
| action-board | light | en | desktop | `action-board-light-en-desktop.png` | yes |
| action-board | dark | zh | desktop | `action-board-dark-zh-desktop.png` | yes |
| action-board | light | zh | desktop | `action-board-light-zh-desktop.png` | yes |
| action-board | dark | en | mobile | `action-board-dark-en-mobile.png` | yes |
| action-board | light | en | mobile | `action-board-light-en-mobile.png` | yes |
| action-board | dark | zh | mobile | `action-board-dark-zh-mobile.png` | yes |
| action-board | light | zh | mobile | `action-board-light-zh-mobile.png` | yes |
| sectors | dark | en | desktop | `sectors-dark-en-desktop.png` | yes |
| sectors | light | en | desktop | `sectors-light-en-desktop.png` | yes |
| sectors | dark | zh | desktop | `sectors-dark-zh-desktop.png` | yes |
| sectors | light | zh | desktop | `sectors-light-zh-desktop.png` | yes |
| sectors | dark | en | mobile | `sectors-dark-en-mobile.png` | yes |
| sectors | light | en | mobile | `sectors-light-en-mobile.png` | yes |
| sectors | dark | zh | mobile | `sectors-dark-zh-mobile.png` | yes |
| sectors | light | zh | mobile | `sectors-light-zh-mobile.png` | yes |
| holdings | dark | en | desktop | `holdings-dark-en-desktop.png` | yes |
| holdings | light | en | desktop | `holdings-light-en-desktop.png` | yes |
| holdings | dark | zh | desktop | `holdings-dark-zh-desktop.png` | yes |
| holdings | light | zh | desktop | `holdings-light-zh-desktop.png` | yes |
| holdings | dark | en | mobile | `holdings-dark-en-mobile.png` | yes |
| holdings | light | en | mobile | `holdings-light-en-mobile.png` | yes |
| holdings | dark | zh | mobile | `holdings-dark-zh-mobile.png` | yes |
| holdings | light | zh | mobile | `holdings-light-zh-mobile.png` | yes |
| dash-mtf | dark | en | desktop | `dash-mtf-dark-en-desktop.png` | yes |
| dash-mtf | light | en | desktop | `dash-mtf-light-en-desktop.png` | yes |
| dash-mtf | dark | zh | desktop | `dash-mtf-dark-zh-desktop.png` | yes |
| dash-mtf | light | zh | desktop | `dash-mtf-light-zh-desktop.png` | yes |
| dash-mtf | dark | en | mobile | `dash-mtf-dark-en-mobile.png` | yes |
| dash-mtf | light | en | mobile | `dash-mtf-light-en-mobile.png` | yes |
| dash-mtf | dark | zh | mobile | `dash-mtf-dark-zh-mobile.png` | yes |
| dash-mtf | light | zh | mobile | `dash-mtf-light-zh-mobile.png` | yes |
| sector-central-action | dark | en | desktop | `sector-central-action-dark-en-desktop.png` | yes (leaked=False) |

## Floor (390 / 768 / 1440)

See `g8.json`. Checks: page horizontal scroll, focus-visible ring, `?` tap at 390, reduced-motion skeleton, chip wrap, in-container table scroll.

| Width | Page h-scroll | Focus ring | `?` tap | Reduced-motion skeleton | Chip wrap | Table in-container |
|---|---|---|---|---|---|---|
| 390 | none | visible | open (LENS or `.tip-open`) | `animation-name: none`, header bar 30px | wrap (`.acb-tape`) | `.tbl-scroll` overflow-x auto |
| 768 | none | visible | n/a | n/a | wrap | no overflow |
| 1440 | none | visible | n/a | n/a | wrap | no overflow |

## G-gate per-subject verdicts (judged from the crops)

Spec §0.3's 16-crop floor is `{dark,light}×{EN,ZH}` at 1440 plus the same four subjects at 390 = **32 REST cells**. The sector_central control is one extra 1440 dark EN crop (force_state, not a REST cell).

| Subject | Cells | Verdict | Notes |
|---|---|---|---|
| action-board (C1 + C4 theme link) | 8 | **PASS** | Header + megacap strip read as one block; one as-of stamp; figure is the only saturated ink; light crop shows the `--panel2` inset band (not a token-swap of the dark hairline); 390 wraps and the figure stays on the symbol's line; theme link is `Theme heat & reasons → Sector Intelligence` / `主题热度与详情 → 行业情报页`. |
| sectors (C2) | 8 | **PASS** | Band words (`washed out`/`超卖`, `mid-range`/`中位`, `stretched`/`拉伸`, `even odds`/`胜率接近五五`, `rolling over`/`正在回落`); seasonality is magnitude only; footer is the frozen rewrite; table scrolls inside `.tbl-scroll` at 390; page does not h-scroll. `MACD ↑` remains on non-down-cross rows (round-1 sweep named `MACD ↓` only). |
| holdings (C3 + C4 accumulation link + nulls) | 8 | **PASS** | Exactly 8 data rows; `See all 12 →` / `查看全部 12 项 →`; technical `no signal yet` / `暂无信号`; accumulation landing link in the header; combined Neocloud key renders `新型 GPU 云服务商 / AI 数据中心` in ZH. |
| dash-mtf (C5) | 8 | **PASS** | Skeleton at true geometry (30px header + 38px rows), no words; dark shimmer reads as a lift; light shimmer reads as a grey wash (color-mix off `--text`). Reduced-motion kills the animation. |
| sector-central-action (control) | 1 | **PASS** | 1440 dark EN: action board present, **no** `.acb-tape` / megacap strip. |

## Composition fixes this round

- Unhid the surviving L1 panels (`#dash-tape-band`, `#equity-scoreboard`, `#sectors`, `#dash-mtf-section`, `#holdings`) that the old declutter CSS still set to `display:none`. Leftover research boards stay hidden.
- Hide unscoped `.mx5-aurora` on `body.page-stocks` (aurora CSS is macro-only).
- `.acb-tape-line` keeps symbol + figure on one nowrap pair at 390.
- Holdings / accumulation tables wrap in `.tbl-scroll`.
- Help `?`: `tabindex=0`, `:focus-visible` ring, hover gated to `(hover:hover) and (pointer:fine)`, pointerdown toggle (S1 flash-and-vanish).
- Holdings header links stop floating at 390 so they don't cover the table.

