# Commodities W6 — evidence matrix (round 6, #7055 cure round 1)

Packet REQUIRED EVIDENCE MATRIX: dark × light × EN × ZH × 1440/390 (8 base
shots) plus named proof crops (a)–(g) — every subject now carries the full
8-cell matrix (was partial-subset in r5; #7055 round 1 cure expanded every
subject's job generator via a shared `_matrix` helper so the corpus test
has 61 fewer MISSING-rest-cell findings).

Capture head: `3796cd819b54` (the C1 capture-script patch commit — every PNG
in this corpus was rendered at that commit; `manifest.json`'s
`target.resolved_sha_or_none` matches it byte-for-byte).

Estate shape: every PNG lives at the corpus ROOT, NEVER under a cells/
subdir. The r5 corpus carried PNGs under `cells/` but referenced them as
bare `<hash>.png`, which the TP-0 visual-evidence gate resolves against
`manifest_path.parent / file_rel` (= OUT_DIR) — so a `cells/` subdir
silently orphaned every reference and produced 35 SHAPE 'screenshot does
not exist' findings. The r6 cure removed the `cells/` subdir (PNGs at
root) and patched the capture script (`scripts/
capture_commodities_w6_evidence.py` `CELLS_DIR = OUT_DIR`); see the
script's CELLS_DIR comment for the source of the cure.

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
| a-heat-extended | dark | en | mobile | `a-heat-extended-dark-en-mobile.png` | yes | yes |
| a-heat-extended | light | en | mobile | `a-heat-extended-light-en-mobile.png` | yes | yes |
| a-heat-extended | dark | zh | mobile | `a-heat-extended-dark-zh-mobile.png` | yes | yes |
| a-heat-extended | light | zh | mobile | `a-heat-extended-light-zh-mobile.png` | yes | yes |
| b-live-oil | dark | en | desktop | `b-live-oil-dark-en-desktop.png` | yes | yes |
| b-live-oil | light | en | desktop | `b-live-oil-light-en-desktop.png` | yes | yes |
| b-live-oil | dark | zh | desktop | `b-live-oil-dark-zh-desktop.png` | yes | yes |
| b-live-oil | light | zh | desktop | `b-live-oil-light-zh-desktop.png` | yes | yes |
| b-live-oil | dark | en | mobile | `b-live-oil-dark-en-mobile.png` | yes | yes |
| b-live-oil | light | en | mobile | `b-live-oil-light-en-mobile.png` | yes | yes |
| b-live-oil | dark | zh | mobile | `b-live-oil-dark-zh-mobile.png` | yes | yes |
| b-live-oil | light | zh | mobile | `b-live-oil-light-zh-mobile.png` | yes | yes |
| d-cycle-missing | dark | en | desktop | `d-cycle-missing-dark-en-desktop.png` | yes | yes |
| d-cycle-missing | light | en | desktop | `d-cycle-missing-light-en-desktop.png` | yes | yes |
| d-cycle-missing | dark | zh | desktop | `d-cycle-missing-dark-zh-desktop.png` | yes | yes |
| d-cycle-missing | light | zh | desktop | `d-cycle-missing-light-zh-desktop.png` | yes | yes |
| d-cycle-missing | dark | en | mobile | `d-cycle-missing-dark-en-mobile.png` | yes | yes |
| d-cycle-missing | light | en | mobile | `d-cycle-missing-light-en-mobile.png` | yes | yes |
| d-cycle-missing | dark | zh | mobile | `d-cycle-missing-dark-zh-mobile.png` | yes | yes |
| d-cycle-missing | light | zh | mobile | `d-cycle-missing-light-zh-mobile.png` | yes | yes |
| e-dollar-value | dark | en | desktop | `e-dollar-value-dark-en-desktop.png` | yes | yes |
| e-dollar-value | light | en | desktop | `e-dollar-value-light-en-desktop.png` | yes | yes |
| e-dollar-value | dark | zh | desktop | `e-dollar-value-dark-zh-desktop.png` | yes | yes |
| e-dollar-value | light | zh | desktop | `e-dollar-value-light-zh-desktop.png` | yes | yes |
| e-dollar-value | dark | en | mobile | `e-dollar-value-dark-en-mobile.png` | yes | yes |
| e-dollar-value | light | en | mobile | `e-dollar-value-light-en-mobile.png` | yes | yes |
| e-dollar-value | dark | zh | mobile | `e-dollar-value-dark-zh-mobile.png` | yes | yes |
| e-dollar-value | light | zh | mobile | `e-dollar-value-light-zh-mobile.png` | yes | yes |
| e-dollar-omitted | dark | en | desktop | `e-dollar-omitted-dark-en-desktop.png` | yes | yes |
| e-dollar-omitted | light | en | desktop | `e-dollar-omitted-light-en-desktop.png` | yes | yes |
| e-dollar-omitted | dark | zh | desktop | `e-dollar-omitted-dark-zh-desktop.png` | yes | yes |
| e-dollar-omitted | light | zh | desktop | `e-dollar-omitted-light-zh-desktop.png` | yes | yes |
| e-dollar-omitted | dark | en | mobile | `e-dollar-omitted-dark-en-mobile.png` | yes | yes |
| e-dollar-omitted | light | en | mobile | `e-dollar-omitted-light-en-mobile.png` | yes | yes |
| e-dollar-omitted | dark | zh | mobile | `e-dollar-omitted-dark-zh-mobile.png` | yes | yes |
| e-dollar-omitted | light | zh | mobile | `e-dollar-omitted-light-zh-mobile.png` | yes | yes |
| f-catalysts-zh | dark | en | desktop | `f-catalysts-zh-dark-en-desktop.png` | yes | yes |
| f-catalysts-zh | light | en | desktop | `f-catalysts-zh-light-en-desktop.png` | yes | yes |
| f-catalysts-zh | dark | zh | desktop | `f-catalysts-zh-dark-zh-desktop.png` | yes | yes |
| f-catalysts-zh | light | zh | desktop | `f-catalysts-zh-light-zh-desktop.png` | yes | yes |
| f-catalysts-zh | dark | en | mobile | `f-catalysts-zh-dark-en-mobile.png` | yes | yes |
| f-catalysts-zh | light | en | mobile | `f-catalysts-zh-light-en-mobile.png` | yes | yes |
| f-catalysts-zh | dark | zh | mobile | `f-catalysts-zh-dark-zh-mobile.png` | yes | yes |
| f-catalysts-zh | light | zh | mobile | `f-catalysts-zh-light-zh-mobile.png` | yes | yes |
| f-timeline-zh | dark | en | desktop | `f-timeline-zh-dark-en-desktop.png` | yes | yes |
| f-timeline-zh | light | en | desktop | `f-timeline-zh-light-en-desktop.png` | yes | yes |
| f-timeline-zh | dark | zh | desktop | `f-timeline-zh-dark-zh-desktop.png` | yes | yes |
| f-timeline-zh | light | zh | desktop | `f-timeline-zh-light-zh-desktop.png` | yes | yes |
| f-timeline-zh | dark | en | mobile | `f-timeline-zh-dark-en-mobile.png` | yes | yes |
| f-timeline-zh | light | en | mobile | `f-timeline-zh-light-en-mobile.png` | yes | yes |
| f-timeline-zh | dark | zh | mobile | `f-timeline-zh-dark-zh-mobile.png` | yes | yes |
| f-timeline-zh | light | zh | mobile | `f-timeline-zh-light-zh-mobile.png` | yes | yes |
| g-lens-keyboard | dark | en | desktop | `g-lens-keyboard-dark-en-desktop.png` | yes | yes |
| g-lens-keyboard | light | en | desktop | `g-lens-keyboard-light-en-desktop.png` | yes | yes |
| g-lens-keyboard | dark | zh | desktop | `g-lens-keyboard-dark-zh-desktop.png` | yes | yes |
| g-lens-keyboard | light | zh | desktop | `g-lens-keyboard-light-zh-desktop.png` | yes | yes |
| g-lens-keyboard | dark | en | mobile | `g-lens-keyboard-dark-en-mobile.png` | yes | yes |
| g-lens-keyboard | light | en | mobile | `g-lens-keyboard-light-en-mobile.png` | yes | yes |
| g-lens-keyboard | dark | zh | mobile | `g-lens-keyboard-dark-zh-mobile.png` | yes | yes |
| g-lens-keyboard | light | zh | mobile | `g-lens-keyboard-light-zh-mobile.png` | yes | yes |
| g-lens-tap | dark | en | desktop | `g-lens-tap-dark-en-desktop.png` | yes | yes |
| g-lens-tap | light | en | desktop | `g-lens-tap-light-en-desktop.png` | yes | yes |
| g-lens-tap | dark | zh | desktop | `g-lens-tap-dark-zh-desktop.png` | yes | yes |
| g-lens-tap | light | zh | desktop | `g-lens-tap-light-zh-desktop.png` | yes | yes |
| g-lens-tap | dark | en | mobile | `g-lens-tap-dark-en-mobile.png` | yes | yes |
| g-lens-tap | light | en | mobile | `g-lens-tap-light-en-mobile.png` | yes | yes |
| g-lens-tap | dark | zh | mobile | `g-lens-tap-dark-zh-mobile.png` | yes | yes |
| g-lens-tap | light | zh | mobile | `g-lens-tap-light-zh-mobile.png` | yes | yes |
| h-hero-ntop9-tip | dark | en | desktop | `h-hero-ntop9-tip-dark-en-desktop.png` | yes | yes |
| h-hero-ntop9-tip | light | en | desktop | `h-hero-ntop9-tip-light-en-desktop.png` | yes | yes |
| h-hero-ntop9-tip | dark | zh | desktop | `h-hero-ntop9-tip-dark-zh-desktop.png` | yes | yes |
| h-hero-ntop9-tip | light | zh | desktop | `h-hero-ntop9-tip-light-zh-desktop.png` | yes | yes |
| h-hero-ntop9-tip | dark | en | mobile | `h-hero-ntop9-tip-dark-en-mobile.png` | yes | yes |
| h-hero-ntop9-tip | light | en | mobile | `h-hero-ntop9-tip-light-en-mobile.png` | yes | yes |
| h-hero-ntop9-tip | dark | zh | mobile | `h-hero-ntop9-tip-dark-zh-mobile.png` | yes | yes |
| h-hero-ntop9-tip | light | zh | mobile | `h-hero-ntop9-tip-light-zh-mobile.png` | yes | yes |

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

