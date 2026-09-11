# China Archetype-D S1 — evidence matrix (round 3)

Five L1 subjects × dark/light × EN/ZH × 1440/390.
Spec G7 names this the 20-crop matrix; the product of those axes is 40 cells.

## Fixture

- Source: `templates/china.html.j2` macro-mode `.cnx-wrap` + page-scoped `<style>`.
- VM: `scripts/capture_china_archetype_d_evidence.fixture_vm` (same shape the page tests use).
- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell.

## Honest differences from live `site/china.html`

- No `_site_nav` chrome (two global nav families; this crop is the glance wrap).
- No dialogs, heatmap, or stocks-mode board.
- No live quote hydration — CSI 300 / ChiNext stay at skeleton geometry.
- Numbers are representative (southbound +¥4.6bn / +¥46亿, events 4 of 5, pullback 87, date 2026-09-10), not that night's bake.
- Sparse checkout has no `data/`; this is why the wrap is fixture-rendered.

## Cells

| Subject | Theme | Lang | Viewport | Alias | Captured |
|---|---|---|---|---|---|
| hero | dark | en | desktop | `hero-dark-en-desktop.png` | yes |
| hero | light | en | desktop | `hero-light-en-desktop.png` | yes |
| hero | dark | zh | desktop | `hero-dark-zh-desktop.png` | yes |
| hero | light | zh | desktop | `hero-light-zh-desktop.png` | yes |
| hero | dark | en | mobile | `hero-dark-en-mobile.png` | yes |
| hero | light | en | mobile | `hero-light-en-mobile.png` | yes |
| hero | dark | zh | mobile | `hero-dark-zh-mobile.png` | yes |
| hero | light | zh | mobile | `hero-light-zh-mobile.png` | yes |
| todo | dark | en | desktop | `todo-dark-en-desktop.png` | yes |
| todo | light | en | desktop | `todo-light-en-desktop.png` | yes |
| todo | dark | zh | desktop | `todo-dark-zh-desktop.png` | yes |
| todo | light | zh | desktop | `todo-light-zh-desktop.png` | yes |
| todo | dark | en | mobile | `todo-dark-en-mobile.png` | yes |
| todo | light | en | mobile | `todo-light-en-mobile.png` | yes |
| todo | dark | zh | mobile | `todo-dark-zh-mobile.png` | yes |
| todo | light | zh | mobile | `todo-light-zh-mobile.png` | yes |
| changed | dark | en | desktop | `changed-dark-en-desktop.png` | yes |
| changed | light | en | desktop | `changed-light-en-desktop.png` | yes |
| changed | dark | zh | desktop | `changed-dark-zh-desktop.png` | yes |
| changed | light | zh | desktop | `changed-light-zh-desktop.png` | yes |
| changed | dark | en | mobile | `changed-dark-en-mobile.png` | yes |
| changed | light | en | mobile | `changed-light-en-mobile.png` | yes |
| changed | dark | zh | mobile | `changed-dark-zh-mobile.png` | yes |
| changed | light | zh | mobile | `changed-light-zh-mobile.png` | yes |
| drivers | dark | en | desktop | `drivers-dark-en-desktop.png` | yes |
| drivers | light | en | desktop | `drivers-light-en-desktop.png` | yes |
| drivers | dark | zh | desktop | `drivers-dark-zh-desktop.png` | yes |
| drivers | light | zh | desktop | `drivers-light-zh-desktop.png` | yes |
| drivers | dark | en | mobile | `drivers-dark-en-mobile.png` | yes |
| drivers | light | en | mobile | `drivers-light-en-mobile.png` | yes |
| drivers | dark | zh | mobile | `drivers-dark-zh-mobile.png` | yes |
| drivers | light | zh | mobile | `drivers-light-zh-mobile.png` | yes |
| watching-deeper | dark | en | desktop | `watching-deeper-dark-en-desktop.png` | yes |
| watching-deeper | light | en | desktop | `watching-deeper-light-en-desktop.png` | yes |
| watching-deeper | dark | zh | desktop | `watching-deeper-dark-zh-desktop.png` | yes |
| watching-deeper | light | zh | desktop | `watching-deeper-light-zh-desktop.png` | yes |
| watching-deeper | dark | en | mobile | `watching-deeper-dark-en-mobile.png` | yes |
| watching-deeper | light | en | mobile | `watching-deeper-light-en-mobile.png` | yes |
| watching-deeper | dark | zh | mobile | `watching-deeper-dark-zh-mobile.png` | yes |
| watching-deeper | light | zh | mobile | `watching-deeper-light-zh-mobile.png` | yes |

## G8 floor

See `g8.json`. Checks at 390 / 768 / 1440: page horizontal scroll, focus-visible ring, LENS tap at 390, reduced-motion skeleton, chip wrap.

| Width | Page h-scroll | Focus ring | LENS tap | Reduced-motion skeleton | Chip wrap |
|---|---|---|---|---|---|
| 390 | none (`scrollWidth=clientWidth=390`) | visible | open | `animation-name: none`, plate ~58.296875px | wrap |
| 768 | none | visible | n/a (390 only) | n/a | wrap |
| 1440 | none | visible | n/a | n/a | wrap |

## G7 per-subject verdicts (judged from the crops)

Spec G7's "20 crops" is `{dark,light}×{EN,ZH}×{1440,390}` × 5 subjects = **40 cells**. Each subject is one G7 surface; the eight cells share the composition verdict unless a criterion is axis-specific.

| Subject | Cells | G7 verdict | Notes |
|---|---|---|---|
| hero | 8 | **PASS** | One regime word (`GROWTH SCARE` / `增长恐慌`) from `_ms_label`; one producer clause; exactly one date `2026-09-10`; index strip SSE/CSI/ChiNext/HSI; dark = luminance field + dial arc; light = white card on deeper canvas, no full-bleed field, no bloom; ZH has no Latin state enum; 390 stacks with no page h-scroll. CSI/ChiNext skeletons at true geometry. Dial is a thin arc at 390 (no white disc). |
| todo | 8 | **PASS** | Three producer-bound stance sentences within word budgets; LENS `?` on each row; next-print date is the only digits-with-units at rest; ZH has no `3/3` / `90` / `70%`. |
| changed | 8 | **PASS** (mapped from G7 Macro News) | Two headlines + two alerts; EN crop is not blank (Chinese source text in both slots — spec §4.1 frozen fallback); ZH matches; no EN/ZH mix inside a crop. |
| drivers | 8 | **PASS** (mapped from G7 Connect Flows + four-driver band) | EN `+¥4.6bn` + Latin names; ZH `+¥46亿` + 中文 names; no mix; dark accent-tinted value; light uses light-rung ink. Four panels, 2-col desktop / swipe at 390. |
| watching-deeper | 8 | **PASS** (mapped from G7 Upcoming Events + Go deeper) | Slice label `4 of 5 shown · full calendar →` (ZH `4/5 项已显示 · 完整日历 →`) in the same crop as the strip; population `5` once; 390 strip scrolls inside `.cnx-estrip`; Go-deeper links wrap and include the playbook landing; light hover is ring-not-glow. |

## Capture-harness disclosure (B2)

Round-2 light bloom and the 390 white disc were **not** the page aurora. They were `theme.js` `skyToggleFx`: a 1.05s sun (light) / crescent-moon (dark) flourish at `z-index: 2147483600` that `setTheme()` appends for 1100ms (`templates/theme.css` `.sky-fx` / `.sky-fx .disc`; `theme.js` `skyToggleFx`, timeout 1100). The r2 harness called `window.setTheme` then screenshotted at ~150ms, so every cell photographed the in-flight disc. Receipt: computed style on the orange blob was `span.disc` inside `.sky-fx.sun` (`radial-gradient(circle at 50% 46%, #fffdf7 … #ffc35a …)`); the dark 390 disc was `.sky-fx.moon .disc` with the crescent mask. This round sets `window.__skyDeck = true` in the init script (the same bow-out the landing hub uses) and removes any leftover `.sky-fx` after apply. Live theme toggles still play the flourish; it is not a page-china CSS hide. Light page-aurora remains CSS-gated `display:none` (spec §5.5).

## CNH inverted-tile ruling

L1 index strip is SSE / CSI 300 / ChiNext / HSI — **no inverted-quote tile renders**. `MARKET_TILE_SPEC` still has `CNH_F` `invert=True`; orientation copy now also renders on the Tier-2 USD/CNH card inside `cnx-dlg-markets` (`quoted as yuan per US dollar — higher = a weaker yuan` / `以美元兑人民币报价 — 数值升高 = 人民币走弱`).

