# Commodities W6 — evidence matrix (round 3)

Packet REQUIRED EVIDENCE MATRIX: dark × light × EN × ZH × 1440/390
(8 base shots) plus named proof crops (a)–(g). 30/30 cells captured.

Judged from the PNG files after capture. Dark and light are two art
directions (command-center luminance vs research-workspace white cards /
hairline / no bloom). Overlay column is a probe for `.sky-fx` / `#mmb-boot`
sitting on content.

## Fixture

- Source: `templates/commodities.html.j2` + page-scoped `<style>` +
  `_state_inks.html.j2` + `_vector_polish.html.j2`.
- VM: `scripts/capture_commodities_w6_evidence.fixture_vm`
  (current-shaped board from `tests/test_commodities_w6_truth.py::
  test_hero_current_shaped_board_is_selective`: heating oil / corn /
  soybeans stretched → hero **In favour — 3 of 17 stretched**).
- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` /
  `window.setLang`; a mismatch refuses the cell.
- `window.__skyDeck = true` in the init script (skyToggleFx bow-out) and
  any leftover `.sky-fx` is removed after apply.

## Honest differences from live `site/commodities.html`

- No `_site_nav` chrome (two global nav families; this crop is the page wrap).
- No live.js hydration — live tiles keep the SSR 1-day change.
- No oil-episode cross-asset banner (so the hero is the first content element).
- No coverage-matrix rows (fixture `coverage=None`).
- Inter webfonts are not copied into the scratch; system UI fonts render.
- Numbers are representative (as of Sep 10, 2026), not that night's bake.
- Sparse checkout has no `data/`; this is why the page is fixture-rendered.
- `#mmb-boot` (brain FAB) and `.sky-fx` are stripped for capture; live still shows both on toggle.
- Fixture CSS forces `.dot{opacity:1}` so the staggered fade-in is not photographed mid-flight.

Commodities is a vector-family page: it does **not** link `theme.css`.
Material is page `<style>` + `_state_inks` + `_vector_polish`. Loading
`theme.css` in the fixture would be a second art direction, so it is not loaded.

## Cells

| Subject | Theme | Lang | Viewport | Alias | Captured | Overlay clean |
|---|---|---|---|---|---|---|
| atf | dark | en | desktop | `atf-dark-en-desktop.png` | yes | yes |
| atf | light | en | desktop | `atf-light-en-desktop.png` | yes | yes |
| atf | dark | zh | desktop | `atf-dark-zh-desktop.png` | yes | yes |
| atf | light | zh | desktop | `atf-light-zh-desktop.png` | yes | yes |
| atf | dark | en | mobile | `atf-dark-en-mobile.png` | yes | yes |
| atf | light | en | mobile | `atf-light-en-mobile.png` | yes | yes |
| atf | dark | zh | mobile | `atf-dark-zh-mobile.png` | yes | yes |
| atf | light | zh | mobile | `atf-light-zh-mobile.png` | yes | yes |
| a-heat-blowoff | dark | en | desktop | `a-heat-blowoff-dark-en-desktop.png` | yes | yes |
| a-heat-blowoff | light | en | desktop | `a-heat-blowoff-light-en-desktop.png` | yes | yes |
| a-heat-blowoff | dark | zh | desktop | `a-heat-blowoff-dark-zh-desktop.png` | yes | yes |
| a-heat-blowoff | light | zh | desktop | `a-heat-blowoff-light-zh-desktop.png` | yes | yes |
| a-heat-blowoff | dark | en | mobile | `a-heat-blowoff-dark-en-mobile.png` | yes | yes |
| a-heat-blowoff | light | en | mobile | `a-heat-blowoff-light-en-mobile.png` | yes | yes |
| a-heat-blowoff | dark | zh | mobile | `a-heat-blowoff-dark-zh-mobile.png` | yes | yes |
| a-heat-blowoff | light | zh | mobile | `a-heat-blowoff-light-zh-mobile.png` | yes | yes |
| b-live-oil | dark | en | desktop | `b-live-oil-dark-en-desktop.png` | yes | yes |
| b-live-oil | light | en | desktop | `b-live-oil-light-en-desktop.png` | yes | yes |
| d-cycle-missing | dark | en | desktop | `d-cycle-missing-dark-en-desktop.png` | yes | yes |
| d-cycle-missing | dark | zh | desktop | `d-cycle-missing-dark-zh-desktop.png` | yes | yes |
| d-cycle-missing | light | en | desktop | `d-cycle-missing-light-en-desktop.png` | yes | yes |
| d-cycle-missing | light | zh | desktop | `d-cycle-missing-light-zh-desktop.png` | yes | yes |
| e-dollar-value | dark | en | desktop | `e-dollar-value-dark-en-desktop.png` | yes | yes |
| e-dollar-omitted | dark | en | desktop | `e-dollar-omitted-dark-en-desktop.png` | yes | yes |
| f-catalysts-zh | dark | zh | desktop | `f-catalysts-zh-dark-zh-desktop.png` | yes | yes |
| f-timeline-zh | dark | zh | desktop | `f-timeline-zh-dark-zh-desktop.png` | yes | yes |
| f-catalysts-zh | light | zh | desktop | `f-catalysts-zh-light-zh-desktop.png` | yes | yes |
| f-timeline-zh | light | zh | desktop | `f-timeline-zh-light-zh-desktop.png` | yes | yes |
| g-lens-keyboard | dark | en | desktop | `g-lens-keyboard-dark-en-desktop.png` | yes | yes |
| g-lens-tap | dark | en | mobile | `g-lens-tap-dark-en-mobile.png` | yes | yes |

## Proof crops (a)–(g)

| Proof | What it must show | Aliases | Overlay | Verdict |
|---|---|---|---|---|
| (a) heat-grid blow-off | Legend beside Sugar/Corn/Soybeans; blow-off ≠ green; M-A3 digit amber | `a-heat-blowoff-*` | clean | **PASS** — Corn +14.2% / Soybeans +8.1% / Sugar +11.0% paint `Blow-off` / `喷发` with amber left-edge + amber digit, not green `Momentum up`. Legend swatch for Blow-off is amber, distinct from green Momentum up. Light uses brown/amber ink on white cards (not a token-swap of the dark glow). Cotton empty cycle is `no cycle` / `无周期`, not `—`. |
| (b) one number per window | Live oil 1-day beside oil grid 1-month | `b-live-oil-*` | clean | **PASS** — live CL tile `68.40` / `−0.6%` with LIVE pill (1-day SSR); energy-grid Oil · WTI `+4.2%` (1-month). Two windows, one number each. Layout does not place the live strip adjacent to the heat grid (index + board sit between them); both numbers are in the crop. |
| (c) ATF 1440 hero = board | Hero is first content; **In favour — 3 of 17 stretched** | `atf-*-desktop` | clean | **PASS** — hero is the first content element (oil-episode banner omitted in the fixture, as live would put it above). Stance `In favour` / `倾向做多` + `3 of 17 stretched; trim those, don't add`. Hero does not say "in sync" / "Act". Board header "Early warnings forming" is at the fold with Heating Oil / Corn / Soybeans as the three stretched names. Dark = green-luminance field; light = white cards on cool canvas, no bloom, dark-green ink. ZH sparkline is red (红涨绿跌). 390 stacks, no page h-scroll. |
| (d) missing cycle | Cotton detail shows the sentence, not a dash | `d-cycle-missing-*` | clean | **PASS** — `No long-cycle data for this commodity.` / `此品种无长周期数据。` |
| (e) Dollar row | Oil: value; cotton: omitted (never `Dollar: ·`) | `e-dollar-*` | clean | **PASS** — oil: `Dollar: rising · headwind for this commodity`. Cotton: no Dollar row at all. |
| (f) ZH catalysts + timeline | No EN leaks | `f-catalysts-zh-*`, `f-timeline-zh-*` | clean | **PASS** — catalysts: `美联储会议` / `美联储议息决议` / `EIA油品报告` / `周度石油库存` / `黄金, 原油` / `5天后` / disclaimer `日期为日程，并非预测。`. Timeline: `全部/冲击/风险/驱动/配置/其他`, `配置` `原油` `模型原油敞口已调至满仓`, daylabel `2026-09-10` (ISO, language-neutral). `ET` / `UTC` are timezone abbreviations. |
| (g) LENS keyboard/tap | `?` button focus-visible + 390 tap stays open | `g-lens-*` | clean | **PASS** — dedicated `<button class="cmdty-lens">`, not a tabindex row. Desktop: focus-visible ring + full tip to the right of `?` (`Early-warning list: … A heads-up, not a buy signal.`). 390 tap: `tap_opened: true` in the manifest; tip stays open as a fixed sheet at the bottom (not flash-and-vanish). Receipt chips also carry `?` buttons. |

## Capture-harness disclosure

`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms
after every `setTheme`. This harness seeds `window.__skyDeck = true`
(landing-hub bow-out) and removes any leftover `.sky-fx` after apply.
The brain FAB (`#mmb-boot`) is stripped so it cannot sit on a crop.
Live toggles still play the flourish. Per-crop overlay column is above:
all 30 cells probed clean (no `.sky-fx`, no `#mmb-boot`).

## Fixes made this round (composition, not producer truth)

- Early-warning `?` is a `<button class="cmdty-lens">` with pointerdown
  toggle (S1 pattern) so 390 tap does not flash-and-vanish.
- Receipt chips lost `data-tip-en` on the `.l-en` span (hidden in ZH and
  not keyboard-reachable); each chip now has a `?` button. Machine terms
  stay on `data-tip-rc-en`.
- Catalyst labels `td(c.label)` → `t(c.label, c.label_zh)`.
- Disclaimer cut to the one true sentence, bilingual.
- Timeline asset uses `t(e.asset_label, e.asset_label_zh)`; producer
  writes `asset_label_zh` from META.
- Timeline `daylabel` is ISO `YYYY-MM-DD` (was `%a %b %d`, an EN leak in ZH).
- Heat-grid empty cycle is `no cycle` / `无周期`, not `—`.
