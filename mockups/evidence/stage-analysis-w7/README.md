# Stage Analysis W7 — evidence matrix (round 4)

Packet REQUIRED EVIDENCE MATRIX: dark × light × EN × ZH × 1440/390 (8 shots per state). Fixture-only extras use dark-EN-1440 + light-ZH-390.

Captured at HEAD `4e6b0f739681c8b50c321c3548f806d3999702d7`.

## Fixture

- Source: `templates/stage_analysis.html.j2` + page-scoped `<style>` + `theme.css` / `theme.js`.
- Hero VM: 8 current (stations **2 / 3 / 1 / 2**) + 1 stale + 2 unresolved, matching the screener JSON.
- Feeds: fixture JSONs in the scratch `stagedata/` (round-2 shapes). Not the live bake.
- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell.
- `window.__skyDeck = true` in the init script (skyToggleFx bow-out) and any leftover `.sky-fx` is removed after apply.

## Honest differences from live `site/stage_analysis.html`

- No `_site_nav` chrome (two global nav families; this crop is the page wrap).
- No live.js hydration.
- Inter webfonts are not copied; system UI fonts render.
- Counts are a representative 8-name universe, not that night's 2,700-name bake — the M1 proof is that the **integers agree with each other**, not that they match production.
- Sparse checkout has no `data/` or `site/`; this is why the page is fixture-rendered.
- `#mmb-boot` and `.sky-fx` are stripped for capture; live still shows both on toggle.
- `.rise` animation is disabled so ATF opacity is 1 at shot time.
- Mobile viewport height is 1400 (width remains 390) so hero + filterbar + first rows fit one frame.
- Light `.aura` is `display:none` (cool canvas is the atmosphere; not a dimmed dark aurora).

## S1 / S5 agreement receipts

| Proof | Evidence |
|---|---|
| S1 population | Hero stations `2 + 3 + 1 + 2 = 8`. Screener showing **Showing 8 of 8 current · 1 stale shown for context · 2 unresolved**. Hero popreceipt **8 current · 1 stale · 2 unresolved**. One population, one word for the third bucket. |
| S5 tone/result | Earnings NVDA **72.2 / 8** + Read **Upbeat** (ZH **偏乐观**). Screener NVDA chip **72** (page `Math.round` of 72.2) + same Upbeat band. COST **47.2 / Balanced**. One 0–100 / 0–10 vocabulary. |

## Non-visual proofs

- **CSV header (list):** `['Ticker', 'Name', 'Industry', 'Industry rank', 'Trend quality', 'Trend change', 'Stage', 'Stage label', 'Weeks', 'Stretch', 'Volatility', 'Tags', 'Call tone', 'Earnings result', 'Rating']`
- **ZH tags:** `['上调指引', '需求加速', '上调指引', '新品', '利润率扩张', '下调指引', '供给受限', '需求放缓', '监管逆风', '上调指引', '人工智能', '需求加速', '利润率扩张', '业绩指引']`
- **Horizontal scroll at 390:** `[{"scrollWidth": 390, "clientWidth": 390, "tab": "screener", "ok": true}, {"scrollWidth": 390, "clientWidth": 390, "tab": "board", "ok": true}, {"scrollWidth": 390, "clientWidth": 390, "tab": "industries", "ok": true}, {"scrollWidth": 390, "clientWidth": 390, "tab": "earnings", "ok": true}, {"scrollWidth": 390, "clientWidth": 390, "tab": "altdata", "ok": true}, {"scrollWidth": 390, "clientWidth": 390, "tab": "research", "ok": true}]`
- **Keyboard:** `.tip-q` Enter opens the Trend quality tip (`tip_open: true`). Crop `s1-screener-dark-en-desktop-keyboard-tip.png`.
- **Tap:** `.tip-q` click on 390 opens the same tip (`tip_open: true`). Crop `s1-screener-dark-en-mobile-tap-tip.png`.

## State verdicts

| State | What it must show | Overlay | Verdict |
|---|---|---|---|
| S1 Screener default | Hero stations + showing line agree (8 current); unresolved in hero and showing | yes | **PASS** |
| S2 Region=China | Disabled China + true-reason tip (“US coverage only…”) + US-scope hero. Board/Ind extras too | yes | **PASS** |
| S3 Research items:0 | “Company primers are being written” / 公司简介正在撰写中 — not Earnings | yes | **PASS** |
| S4 Alt-Data empty topics | Observable empty copy; no live/实时 over empty; outage chip when source/asof absent; TikTok seed only | yes | **PASS** |
| S5 Tone/result + Ranking | 72.2 + Upbeat; Ranking headers Trend strength / Still speeding up (no RS jargon) | yes | **PASS** |
| S6 Setup column | Cleanest / 最干净 at rest (T1/T2 in the tip) | yes | **PASS** |
| S7 Forced failures | Screener/board 404 plain-word; earnings degraded + stale banners; heatmap unavailable | yes | **PASS** |
| S8 Loading skeleton | Wordless `.sk-load` bars at table geometry | yes | **PASS** |

Light is a research workspace (cool canvas `#eef1f4`, white material, hairline, short shadow, `.aura{display:none}`) — marker `w7-r3-light`. Dark remains the command-center. Token swap alone is not this pass.

## Cells

| Subject | Theme | Lang | Viewport | Force | Alias | Captured | Overlay clean |
|---|---|---|---|---|---|---|---|
| s1-screener | dark | en | desktop | rest | `s1-screener-dark-en-desktop-rest.png` | yes | yes |
| s1-screener | light | en | desktop | rest | `s1-screener-light-en-desktop-rest.png` | yes | yes |
| s1-screener | dark | zh | desktop | rest | `s1-screener-dark-zh-desktop-rest.png` | yes | yes |
| s1-screener | light | zh | desktop | rest | `s1-screener-light-zh-desktop-rest.png` | yes | yes |
| s1-screener | dark | en | mobile | rest | `s1-screener-dark-en-mobile-rest.png` | yes | yes |
| s1-screener | light | en | mobile | rest | `s1-screener-light-en-mobile-rest.png` | yes | yes |
| s1-screener | dark | zh | mobile | rest | `s1-screener-dark-zh-mobile-rest.png` | yes | yes |
| s1-screener | light | zh | mobile | rest | `s1-screener-light-zh-mobile-rest.png` | yes | yes |
| s1-screener | dark | en | desktop | keyboard-tip | `s1-screener-dark-en-desktop-keyboard-tip.png` | yes | yes |
| s1-screener | dark | en | mobile | tap-tip | `s1-screener-dark-en-mobile-tap-tip.png` | yes | yes |
| s2-china | dark | en | desktop | rest | `s2-china-dark-en-desktop-rest.png` | yes | yes |
| s2-china | light | en | desktop | rest | `s2-china-light-en-desktop-rest.png` | yes | yes |
| s2-china | dark | zh | desktop | rest | `s2-china-dark-zh-desktop-rest.png` | yes | yes |
| s2-china | light | zh | desktop | rest | `s2-china-light-zh-desktop-rest.png` | yes | yes |
| s2-china | dark | en | mobile | rest | `s2-china-dark-en-mobile-rest.png` | yes | yes |
| s2-china | light | en | mobile | rest | `s2-china-light-en-mobile-rest.png` | yes | yes |
| s2-china | dark | zh | mobile | rest | `s2-china-dark-zh-mobile-rest.png` | yes | yes |
| s2-china | light | zh | mobile | rest | `s2-china-light-zh-mobile-rest.png` | yes | yes |
| s2-china | dark | en | desktop | board | `s2-china-dark-en-desktop-board.png` | yes | yes |
| s2-china | light | zh | mobile | board | `s2-china-light-zh-mobile-board.png` | yes | yes |
| s2-china | dark | en | desktop | ind | `s2-china-dark-en-desktop-ind.png` | yes | yes |
| s2-china | light | zh | mobile | ind | `s2-china-light-zh-mobile-ind.png` | yes | yes |
| s3-research | dark | en | desktop | rest | `s3-research-dark-en-desktop-rest.png` | yes | yes |
| s3-research | light | en | desktop | rest | `s3-research-light-en-desktop-rest.png` | yes | yes |
| s3-research | dark | zh | desktop | rest | `s3-research-dark-zh-desktop-rest.png` | yes | yes |
| s3-research | light | zh | desktop | rest | `s3-research-light-zh-desktop-rest.png` | yes | yes |
| s3-research | dark | en | mobile | rest | `s3-research-dark-en-mobile-rest.png` | yes | yes |
| s3-research | light | en | mobile | rest | `s3-research-light-en-mobile-rest.png` | yes | yes |
| s3-research | dark | zh | mobile | rest | `s3-research-dark-zh-mobile-rest.png` | yes | yes |
| s3-research | light | zh | mobile | rest | `s3-research-light-zh-mobile-rest.png` | yes | yes |
| s4-altdata | dark | en | desktop | rest | `s4-altdata-dark-en-desktop-rest.png` | yes | yes |
| s4-altdata | light | en | desktop | rest | `s4-altdata-light-en-desktop-rest.png` | yes | yes |
| s4-altdata | dark | zh | desktop | rest | `s4-altdata-dark-zh-desktop-rest.png` | yes | yes |
| s4-altdata | light | zh | desktop | rest | `s4-altdata-light-zh-desktop-rest.png` | yes | yes |
| s4-altdata | dark | en | mobile | rest | `s4-altdata-dark-en-mobile-rest.png` | yes | yes |
| s4-altdata | light | en | mobile | rest | `s4-altdata-light-en-mobile-rest.png` | yes | yes |
| s4-altdata | dark | zh | mobile | rest | `s4-altdata-dark-zh-mobile-rest.png` | yes | yes |
| s4-altdata | light | zh | mobile | rest | `s4-altdata-light-zh-mobile-rest.png` | yes | yes |
| s5-earnings | dark | en | desktop | rest | `s5-earnings-dark-en-desktop-rest.png` | yes | yes |
| s5-earnings | light | en | desktop | rest | `s5-earnings-light-en-desktop-rest.png` | yes | yes |
| s5-earnings | dark | zh | desktop | rest | `s5-earnings-dark-zh-desktop-rest.png` | yes | yes |
| s5-earnings | light | zh | desktop | rest | `s5-earnings-light-zh-desktop-rest.png` | yes | yes |
| s5-earnings | dark | en | mobile | rest | `s5-earnings-dark-en-mobile-rest.png` | yes | yes |
| s5-earnings | light | en | mobile | rest | `s5-earnings-light-en-mobile-rest.png` | yes | yes |
| s5-earnings | dark | zh | mobile | rest | `s5-earnings-dark-zh-mobile-rest.png` | yes | yes |
| s5-earnings | light | zh | mobile | rest | `s5-earnings-light-zh-mobile-rest.png` | yes | yes |
| s5-industries | dark | en | desktop | rest | `s5-industries-dark-en-desktop-rest.png` | yes | yes |
| s5-industries | light | en | desktop | rest | `s5-industries-light-en-desktop-rest.png` | yes | yes |
| s5-industries | dark | zh | desktop | rest | `s5-industries-dark-zh-desktop-rest.png` | yes | yes |
| s5-industries | light | zh | desktop | rest | `s5-industries-light-zh-desktop-rest.png` | yes | yes |
| s5-industries | dark | en | mobile | rest | `s5-industries-dark-en-mobile-rest.png` | yes | yes |
| s5-industries | light | en | mobile | rest | `s5-industries-light-en-mobile-rest.png` | yes | yes |
| s5-industries | dark | zh | mobile | rest | `s5-industries-dark-zh-mobile-rest.png` | yes | yes |
| s5-industries | light | zh | mobile | rest | `s5-industries-light-zh-mobile-rest.png` | yes | yes |
| s6-board | dark | en | desktop | rest | `s6-board-dark-en-desktop-rest.png` | yes | yes |
| s6-board | light | en | desktop | rest | `s6-board-light-en-desktop-rest.png` | yes | yes |
| s6-board | dark | zh | desktop | rest | `s6-board-dark-zh-desktop-rest.png` | yes | yes |
| s6-board | light | zh | desktop | rest | `s6-board-light-zh-desktop-rest.png` | yes | yes |
| s6-board | dark | en | mobile | rest | `s6-board-dark-en-mobile-rest.png` | yes | yes |
| s6-board | light | en | mobile | rest | `s6-board-light-en-mobile-rest.png` | yes | yes |
| s6-board | dark | zh | mobile | rest | `s6-board-dark-zh-mobile-rest.png` | yes | yes |
| s6-board | light | zh | mobile | rest | `s6-board-light-zh-mobile-rest.png` | yes | yes |
| s7-screener-404 | dark | en | desktop | rest | `s7-screener-404-dark-en-desktop-rest.png` | yes | yes |
| s7-screener-404 | light | en | desktop | rest | `s7-screener-404-light-en-desktop-rest.png` | yes | yes |
| s7-screener-404 | dark | zh | desktop | rest | `s7-screener-404-dark-zh-desktop-rest.png` | yes | yes |
| s7-screener-404 | light | zh | desktop | rest | `s7-screener-404-light-zh-desktop-rest.png` | yes | yes |
| s7-screener-404 | dark | en | mobile | rest | `s7-screener-404-dark-en-mobile-rest.png` | yes | yes |
| s7-screener-404 | light | en | mobile | rest | `s7-screener-404-light-en-mobile-rest.png` | yes | yes |
| s7-screener-404 | dark | zh | mobile | rest | `s7-screener-404-dark-zh-mobile-rest.png` | yes | yes |
| s7-screener-404 | light | zh | mobile | rest | `s7-screener-404-light-zh-mobile-rest.png` | yes | yes |
| s7-screener-404 | dark | en | desktop | board-404 | `s7-screener-404-dark-en-desktop-board-404.png` | yes | yes |
| s7-screener-404 | light | zh | mobile | board-404 | `s7-screener-404-light-zh-mobile-board-404.png` | yes | yes |
| s7-screener-404 | dark | en | desktop | ern-degraded | `s7-screener-404-dark-en-desktop-ern-degraded.png` | yes | yes |
| s7-screener-404 | light | zh | mobile | ern-degraded | `s7-screener-404-light-zh-mobile-ern-degraded.png` | yes | yes |
| s7-screener-404 | dark | en | desktop | ern-stale | `s7-screener-404-dark-en-desktop-ern-stale.png` | yes | yes |
| s7-screener-404 | light | zh | mobile | ern-stale | `s7-screener-404-light-zh-mobile-ern-stale.png` | yes | yes |
| s7-screener-404 | dark | en | desktop | heat-unavail | `s7-screener-404-dark-en-desktop-heat-unavail.png` | yes | yes |
| s7-screener-404 | light | zh | mobile | heat-unavail | `s7-screener-404-light-zh-mobile-heat-unavail.png` | yes | yes |
| s8-loading | dark | en | desktop | rest | `s8-loading-dark-en-desktop-rest.png` | yes | yes |
| s8-loading | light | en | desktop | rest | `s8-loading-light-en-desktop-rest.png` | yes | yes |
| s8-loading | dark | zh | desktop | rest | `s8-loading-dark-zh-desktop-rest.png` | yes | yes |
| s8-loading | light | zh | desktop | rest | `s8-loading-light-zh-desktop-rest.png` | yes | yes |
| s8-loading | dark | en | mobile | rest | `s8-loading-dark-en-mobile-rest.png` | yes | yes |
| s8-loading | light | en | mobile | rest | `s8-loading-light-en-mobile-rest.png` | yes | yes |
| s8-loading | dark | zh | mobile | rest | `s8-loading-dark-zh-mobile-rest.png` | yes | yes |
| s8-loading | light | zh | mobile | rest | `s8-loading-light-zh-mobile-rest.png` | yes | yes |

## Capture-harness disclosure

`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms after every `setTheme`. This harness seeds `window.__skyDeck = true` and removes any leftover `.sky-fx` after apply. The brain FAB (`#mmb-boot`) is stripped so it cannot sit on a crop. Live toggles still play the flourish. Per-crop overlay column is in `pages[].states[]` (`overlay_clean`). Capture aborts if the worktree is dirty (M1 provenance).

Rig: `python3 -m scripts.capture_stage_analysis_w7_evidence`

