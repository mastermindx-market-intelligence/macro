# Stage Analysis W7 — evidence matrix (round 3)

Packet REQUIRED EVIDENCE MATRIX: dark × light × EN × ZH × 1440/390
(8 shots per state). Fixture-only extras use dark-EN-1440 + light-ZH-390.

Judged 2026-09-11 against the files in `cells/`. Dark and light are two art
directions (command-center vs research workspace). Overlay column is per crop.

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
- **S4 live chip:** round-1 scope creep not done. Empty topics still print a `live` / `实时` chip on Google/Reddit/Wikipedia; TikTok is `seed only` / `仅种子`. Captured honestly.

## S1 / S5 agreement receipts

| Proof | Evidence |
|---|---|
| S1 population | Hero stations `2 + 3 + 1 + 2 = 8`. Screener showing **Showing 8 of 8 current · 1 stale shown for context · 2 unresolved**. Hero popreceipt **8 current · 1 stale · 2 unknown**. One population. |
| S5 tone/result | Earnings NVDA **72.2 / 8** + Read **Upbeat** (ZH **偏乐观**). Screener NVDA chip **72** (page `Math.round` of 72.2) + same Upbeat band. COST **47.2 / Balanced**. One 0–100 / 0–10 vocabulary. |

## Non-visual proofs

- **CSV header (EN):** `Ticker,Name,Industry,Industry rank,Trend quality,Trend change,Stage,Stage label,Weeks,Stretch,Volatility,Tags,Call tone,Earnings result,Rating`
- **ZH tags in Themes/Tags:** `上调指引, 需求加速, 新品, 利润率扩张, 下调指引, 供给受限, 需求放缓, 监管逆风, 人工智能, 业绩指引` — no title-cased English slug survived.
- **Horizontal scroll at 390:** every tab `scrollWidth == clientWidth == 390`.
- **Keyboard:** `.tip-q` Enter opens the Trend quality tip (`tip_open: true`). Crop `s1-screener-dark-en-desktop-keyboard-tip.png`.
- **Tap:** `.tip-q` click on 390 opens the same tip (`tip_open: true`). Crop `s1-screener-dark-en-mobile-tap-tip.png`.

## State verdicts

| State | What it must show | Overlay | Verdict |
|---|---|---|---|
| S1 Screener default | Hero stations + showing line agree (8 current); unresolved >0; first rows in frame | yes | **PASS** |
| S2 Region=China | Disabled China + true-reason tip (“US coverage only…”) + US-scope hero. Board/Ind extras too | yes | **PASS** |
| S3 Research items:0 | “Company primers are being written” / 公司简介正在撰写中 — not Earnings | yes | **PASS** |
| S4 Alt-Data empty topics | Empty-topic sentence + “Screener and Stage Board are unaffected”. **Live chip still present (3)** — disclosed, not a chip-fix | yes | **PASS (chip disclosed)** |
| S5 Tone/result + Ranking | 72.2 + Upbeat; Ranking headers Trend strength / Still speeding up (no RS jargon) | yes | **PASS** |
| S6 Setup column | Cleanest / 最干净 at rest (T1/T2 in the tip) | yes | **PASS** |
| S7 Forced failures | Screener/board 404 plain-word; earnings degraded + stale banners; heatmap unavailable | yes | **PASS** |
| S8 Loading skeleton | Wordless `.sk-load` bars at table geometry | yes | **PASS** |

Light is a research workspace (cool canvas `#eef1f4`, white material, hairline, short shadow) — marker `w7-r3-light`. Dark remains the command-center. Token swap alone is not this pass.

## Cells

See `manifest.json` `pages[].states[]` for the per-crop overlay column (`overlay_clean`). All 86 captured states in this run are `overlay_clean: true` (no `.sky-fx` / `#mmb-boot` / high-z aurora).

## Capture-harness disclosure

`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms
after every `setTheme`. This harness seeds `window.__skyDeck = true`
and removes any leftover `.sky-fx` after apply. The brain FAB
(`#mmb-boot`) is stripped so it cannot sit on a crop. Live toggles
still play the flourish.

Rig: `python3 -m scripts.capture_stage_analysis_w7_evidence`
