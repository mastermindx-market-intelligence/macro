# Commodities W6 — evidence matrix (round 5)

Packet REQUIRED EVIDENCE MATRIX: dark × light × EN × ZH × 1440/390 (8 base shots) plus named proof crops (a)–(g).

## Fixture

- Source: `templates/commodities.html.j2` + page-scoped `<style>` + `_state_inks.html.j2` + `_vector_polish.html.j2`.
- VM: `scripts/capture_commodities_w6_evidence.fixture_vm` (current-shaped board from `tests/test_commodities_w6_truth.py::test_hero_current_shaped_board_is_selective`: heating oil / corn / soybeans stretched → hero **In favour — 3 of 17 stretched**; names on the hero LENS tip). n_top=9 crop is a second fixture.
- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell.
- `window.__skyDeck = true` in the init script (skyToggleFx bow-out) and any leftover `.sky-fx` is removed after apply.

## Honest differences from live `site/commodities.html`

- No `_site_nav` chrome (two global nav families; this crop is the page wrap).
- No live.js hydration — live tiles keep the SSR 1-day change.
- No oil-episode cross-asset banner (so the hero is the first content element).
- No coverage-matrix rows (fixture `coverage=None`).
- Inter webfonts are not copied into the scratch; system UI fonts render.
- Numbers are representative (as of Sep 10, 2026), not that night's bake.
- Sparse checkout has no `data/`; this is why the page is fixture-rendered.
- `#mmb-boot` (brain FAB) and `.sky-fx` are stripped for capture; live still shows both on toggle.

## Cells

| Subject | Theme | Lang | Viewport | Alias | Captured | Overlay clean |
|---|---|---|---|---|---|---|
| b-live-oil | dark | en | desktop | `b-live-oil-dark-en-desktop.png` | yes | yes |
| b-live-oil | light | en | desktop | `b-live-oil-light-en-desktop.png` | yes | yes |
| d-cycle-missing | dark | en | desktop | `d-cycle-missing-dark-en-desktop.png` | yes | yes |
| d-cycle-missing | dark | zh | desktop | `d-cycle-missing-dark-zh-desktop.png` | yes | yes |
| d-cycle-missing | light | en | desktop | `d-cycle-missing-light-en-desktop.png` | yes | yes |
| d-cycle-missing | light | zh | desktop | `d-cycle-missing-light-zh-desktop.png` | yes | yes |
| e-dollar-value | dark | en | desktop | `e-dollar-value-dark-en-desktop.png` | yes | yes |
| e-dollar-omitted | dark | en | desktop | `e-dollar-omitted-dark-en-desktop.png` | yes | yes |
| f-timeline-zh | dark | zh | desktop | `f-timeline-zh-dark-zh-desktop.png` | yes | yes |
| f-timeline-zh | light | zh | desktop | `f-timeline-zh-light-zh-desktop.png` | yes | yes |
| f-catalysts-zh | dark | zh | desktop | `f-catalysts-zh-dark-zh-desktop.png` | yes | yes |
| f-catalysts-zh | light | zh | desktop | `f-catalysts-zh-light-zh-desktop.png` | yes | yes |
| g-lens-keyboard | dark | en | desktop | `g-lens-keyboard-dark-en-desktop.png` | yes | yes |
| g-lens-tap | dark | en | mobile | `g-lens-tap-dark-en-mobile.png` | yes | yes |
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
| a-heat-extended | dark | en | desktop | `a-heat-extended-dark-en-desktop.png` | yes | yes |
| a-heat-extended | light | en | desktop | `a-heat-extended-light-en-desktop.png` | yes | yes |
| a-heat-extended | dark | zh | desktop | `a-heat-extended-dark-zh-desktop.png` | yes | yes |
| a-heat-extended | light | zh | desktop | `a-heat-extended-light-zh-desktop.png` | yes | yes |
| h-hero-ntop9-tip | dark | en | desktop | `h-hero-ntop9-tip-dark-en-desktop.png` | yes | yes |

## Proof crops (a)–(g)

Judged from the files after capture. Dark and light are two art directions.

| Proof | What it must show | Aliases | Overlay | Verdict |
|---|---|---|---|---|
| (a) heat-grid blow-off | Legend (incl. Extended) beside Sugar/Corn/Soybeans; blow-off ≠ green | `a-heat-blowoff-*` | see table | PENDING-JUDGE |
| (a2) Extended member | Heating oil amber-edge Extended, not green Momentum up | `a-heat-extended-*` | see table | PENDING-JUDGE |
| (b) one number per window | Live oil 1-day beside oil grid 1-month | `b-live-oil-*` | see table | PENDING-JUDGE |
| (c) ATF 1440 hero = board | Hero sub is count+stance only; names in LENS tip | `atf-*-desktop` | see table | PENDING-JUDGE |
| (h) n_top=9 LENS tip | Tip lists all 9 counted members; sub has none | `h-hero-ntop9-tip-*` | see table | PENDING-JUDGE |
| (d) missing cycle | Cotton detail shows the sentence, not a dash | `d-cycle-missing-*` | see table | PENDING-JUDGE |
| (e) Dollar row | Oil: value; cotton: omitted (never `Dollar: ·`) | `e-dollar-*` | see table | PENDING-JUDGE |
| (f) ZH catalysts + timeline | Production-shaped label_zh; no EN leaks | `f-catalysts-zh-*`, `f-timeline-zh-*` | see table | PENDING-JUDGE |
| (g) canonical LENS | `.lens-q` tap/focus; machine-term rc visible in `.lens-pop` | `g-lens-*` | see table | PENDING-JUDGE |

## Capture-harness disclosure

`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms after every `setTheme`. This harness seeds `window.__skyDeck = true` (landing-hub bow-out) and removes any leftover `.sky-fx` after apply. The brain FAB (`#mmb-boot`) is stripped so it cannot sit on a crop. Live toggles still play the flourish. Per-crop overlay column is above.

Commodities is a vector-family page: it does **not** link `theme.css`. Material is page `<style>` + `_state_inks` + `_vector_polish`. Loading `theme.css` in the fixture would be a second art direction, so it is not loaded.

