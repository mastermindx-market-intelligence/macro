# Market Structure — W10 r3 evidence matrix

Fixture-rendered `templates/market_structure.html.j2` (no live `data/` bake).
Playwright seeds `localStorage` (`theme`, `lang`, clears `themeAuto`), sets
`window.__skyDeck = true` (bows out of theme.js `skyToggleFx` sun/moon
flourish), calls `setTheme`/`setLang`, re-reads `html[data-theme]` /
`html[data-lang]`, and refuses a cell on mismatch. Fixture HTML carries the
real `body.page-msp` class. Any leftover `.sky-fx` node is removed before
the shot; `.aurora` and the theme FAB are hidden (disclosed below).
At-rest text is recorded via `getComputedStyle` (color / display / visibility)
so a crop cannot pass on a `display:none` node.

## DARK TREATMENT

Command center: luminance depth, instrument glass, restrained colour wash.
The watching band is an inset plate — 7% blue wash on graphite, hairline
border, no glow — so the two conditions read as instrument notes under the
hero, not a second hero. The 390 swipe strip is composition only: cards sit
on graphite, next-card peek is the 86% flex basis, no extra bloom on the
track. Stance chips keep their existing wash.

## LIGHT TREATMENT

Research workspace: cool canvas, white material, hairline discipline, shadow
instead of glow. The watching band is a recessed well inside the white
`.glass` card (`background: var(--bg)` against the hero's white glass, plus
an 8% ink shadow) — not a paper plate raised on the page canvas. Never the
dark 7% blue wash transplanted onto white. Swipe-strip cards pick up the
same 8% ink shadow so a peeked next card reads as a stacked sheet, not a
glowing tile. Token substitution alone is not this design: the band's
ground and the strip's card shadow are light-only mechanisms.

## Intentional differences

| Mechanism | Dark | Light |
|---|---|---|
| Watching-band ground | 7% blue wash on graphite | recessed `--bg` well inside the white `.glass` + 8% ink shadow |
| Watching-band border | hairline `--line` | same hairline, no glow |
| Swipe-strip cards | graphite panels, no extra shadow | 8% ink shadow on the panel |
| Hero / chips | unchanged r2 treatments | unchanged r2 treatments |

## Theme-specific degraded states

- Dark, missing gamma: hero warmup (market-facing sentence + `.empty-why`);
  watching band is absent (nothing to watch).
- Light, missing gamma: same structure on canvas; dashed warmup, no glow.
- Dark/light, missing dispersion thresholds: band still renders the flip
  condition alone.

## A — 8 rest baselines (dark/light × EN/ZH × 1440×900 / 390)

| File | Subject | Theme | Lang | Captured | Overlay |
|---|---|---|---|---|---|
| `A-desktop-dark-en.png` | 8-cell rest baseline | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `A-desktop-dark-zh.png` | 8-cell rest baseline | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `A-desktop-light-en.png` | 8-cell rest baseline | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `A-desktop-light-zh.png` | 8-cell rest baseline | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `A-mobile-dark-en.png` | 8-cell rest baseline | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `A-mobile-dark-zh.png` | 8-cell rest baseline | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `A-mobile-light-en.png` | 8-cell rest baseline | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `A-mobile-light-zh.png` | 8-cell rest baseline | light | zh | yes | none (aurora/sky-fx/FAB hidden) |

## B — crops (dark+light+ZH)

| File | Subject | Theme | Lang | Captured | Overlay |
|---|---|---|---|---|---|
| `B-changed-dark-en.png` | revived change strip with a real labelled long→short chip | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-changed-light-en.png` | revived change strip with a real labelled long→short chip | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-changed-dark-zh.png` | revived change strip with a real labelled long→short chip | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-changed-light-zh.png` | revived change strip with a real labelled long→short chip | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-hero-meta-dark-en.png` | hero-meta headline-vs-receipt (0.4 below flip beside SPX 7636 · flip 7663) | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-hero-meta-light-en.png` | hero-meta headline-vs-receipt (0.4 below flip beside SPX 7636 · flip 7663) | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-hero-meta-dark-zh.png` | hero-meta headline-vs-receipt (0.4 below flip beside SPX 7636 · flip 7663) | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-hero-meta-light-zh.png` | hero-meta headline-vs-receipt (0.4 below flip beside SPX 7636 · flip 7663) | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-footnote-dark-en.png` | merged single hero footnote | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-footnote-light-en.png` | merged single hero footnote | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-footnote-dark-zh.png` | merged single hero footnote | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-footnote-light-zh.png` | merged single hero footnote | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-hero-dark-en.png` | hero stance line | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-hero-light-en.png` | hero stance line | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-hero-dark-zh.png` | hero stance line | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-hero-light-zh.png` | hero stance line | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-flows-dark-en.png` | machine-money stance line | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-flows-light-en.png` | machine-money stance line | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-flows-dark-zh.png` | machine-money stance line | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-flows-light-zh.png` | machine-money stance line | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-disp-dark-en.png` | stock-picker stance line | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-disp-light-en.png` | stock-picker stance line | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-disp-dark-zh.png` | stock-picker stance line | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-disp-light-zh.png` | stock-picker stance line | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-vol-dark-en.png` | vol-weather stance line | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-vol-light-en.png` | vol-weather stance line | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-vol-dark-zh.png` | vol-weather stance line | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-vol-light-zh.png` | vol-weather stance line | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-week-dark-en.png` | weekly-range stance line | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-week-light-en.png` | weekly-range stance line | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-week-dark-zh.png` | weekly-range stance line | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-stance-week-light-zh.png` | weekly-range stance line | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-watch-band-dark-en.png` | P8 watching band folded into the hero | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-watch-band-light-en.png` | P8 watching band folded into the hero | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-watch-band-dark-zh.png` | P8 watching band folded into the hero | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-watch-band-light-zh.png` | P8 watching band folded into the hero | light | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-swipe-390-dark-en.png` | P9 swipe strip at 390 (next-card peek, equal-height cards, content top-anchored) | dark | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-swipe-390-light-en.png` | P9 swipe strip at 390 (next-card peek, equal-height cards, content top-anchored) | light | en | yes | none (aurora/sky-fx/FAB hidden) |
| `B-swipe-390-dark-zh.png` | P9 swipe strip at 390 (next-card peek, equal-height cards, content top-anchored) | dark | zh | yes | none (aurora/sky-fx/FAB hidden) |
| `B-swipe-390-light-zh.png` | P9 swipe strip at 390 (next-card peek, equal-height cards, content top-anchored) | light | zh | yes | none (aurora/sky-fx/FAB hidden) |

## C — synthetic proofs

- `net_gex_pctile` ∈ {1, 2, 3, 21} forced; tip forced visible; files
  `C-ord{1,2,3,21}-dark-en.png` / light-en.
- All six `.warmup` branches forced, dark+light+EN+ZH, each showing the
  market-facing sentence + `.empty-why` (same-subject ZH). Files
  `C-warmup{0-5}-{theme}-{locale}.png`.

## D — 390w composition + no page-level h-scroll

- en/dark: doc 390 / 390 — no page h-scroll; strip 1553 / 350 (strip may exceed)
- zh/dark: doc 390 / 390 — no page h-scroll; strip 1553 / 350 (strip may exceed)
- en/light: doc 390 / 390 — no page h-scroll; strip 1553 / 350 (strip may exceed)
- zh/light: doc 390 / 390 — no page h-scroll; strip 1553 / 350 (strip may exceed)

Page `overflow-x` is hidden; the driver strip is allowed to scroll
horizontally (that is the reduction). `.kpi-row` / `.vix-row` wrap.

## E — producer-regression tests

Re-run at head `03eebd10e7d343c955fe960cdeebb411ed916c7d` (pipe-free):

```
tests/test_build_market_structure_page.py::test_p0_template_consumes_note_en PASSED
tests/test_build_market_structure_page.py::test_p0_gamma_long_to_short_chip_renders_producer_note PASSED
tests/test_build_market_structure_page.py::test_p1_hero_distance_round_trips_from_emitted_spot_flip PASSED
tests/test_build_market_structure_page.py::test_p8_watch_band_binds_stubbed_flip_not_fixture_default PASSED
============================== 4 passed in 2.35s ===============================
```

## F — design-system gates

Re-run at the same head against `git diff f6d512195596 HEAD`:

```
python3 scripts/check_design_system.py --mode enforce-added --diff-file /tmp/mstruct-w10-r4-code.diff
::notice title=design-system::R0 enforce-added: 0 blocking finding(s) (19037 further pre-existing, non-blocking finding(s) in the estate — run --mode report for the full census)
design-system ratchet — mode=enforce-added blocking=0 (estate pre-existing, non-blocking: 19037)
EXIT_DS=0

python3 scripts/check_runtime_style_injection.py
runtime style injection guard REFUSED: sparse worktree — site not checked out; opt into a full checkout with: python3 scripts/worktree_sparse.py full
EXIT_RSI=1

python3 scripts/check_ui_visual_evidence.py --diff-file /tmp/mstruct-w10-r4-code.diff
EXIT_UVE=0
```

REFUSED-on-sparse for `check_runtime_style_injection.py` is lawful on this tree (`data/`, `site/`, `verify_shots` omitted). Direct inspection: zero `style.textContent` / `createElement('style')` / `insertRule` in the template; new rules sit in the governed `<style>` block.

## Disclosed hides

- `window.__skyDeck = true` before `setTheme` so the ~1100ms sun/moon disc
  is never photographed.
- `.sky-fx` nodes removed if any survived.
- `.aurora` (page bloom), the theme FAB, and `#mmb-boot` (brain launcher)
  set `display:none` so the crop is the subject. Live visitors still see them.

## Honest differences vs live

- Fixture VM, not the VPS bake.
- Shared site nav renders; some nav JS 404s are expected.
- Synthetic overlays listed above.
