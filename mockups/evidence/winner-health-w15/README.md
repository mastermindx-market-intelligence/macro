# Winner Health W15 r3 — evidence matrix

S1 rig: Playwright against scratch-rendered `winner_health.html.j2` on the real page skeleton (`_site_nav` included; live `<body>` has no `page-*` class, and the fixture matches that). `data-theme` / `data-lang` applied via `setTheme` / `setLang` (mismatch refuses). Overlays `.mx5-aurora`, `.sky-fx`, `#mmb-root`, `#mmb-boot` are removed before each shot. `window.__skyDeck = true`. `prefers-reduced-motion: reduce`. At-rest text is read from computed styles (display/visibility/opacity + inactive `.l-en`/`.l-zh` spans skipped), never from HTML source. PNGs are content-addressed `sha256[:16].png` plus an alias twin.

Recapture: `python3 -m scripts.capture_winner_health_w15_evidence`

Captured 2026-09-11T09:17:45Z at committed head `d8a181e87a4a4ed5ca993366b2c462068f8f4e2e` with empty `git status --porcelain` (rig-enforced). Porcelain receipt: `(empty)`. 68/68 cells captured, 68 overlay-clean.

## TWO DATA SHAPES (never blended in one cell)

**Production shape** (the committed artifact verbatim): `git show origin/main:data/top_maturation/latest.json`. Today's committed artifact has **no `members` key**, so the production-shaped render exercises the r2 M1 degrade — barless count-only theme rows, no width note. Theme bars absent by design until the nightly emits `members` (M1 degrade). The 8 full-page baselines and every `shape=production` cell run on this.

**Members-present fixture** (production artifact + `members` injected from `data/baskets/membership.json` truths — the packet's own 9-row table): Cybersecurity 10, US Energy Complex 22, AI Software & Platforms 17, Non-AI Tech & Hardware 13, AI Infrastructure 24, Managed Care & Insurers 9, Non-AI Software 14, Semiconductor Equipment (WFE) 16, Robotics & Automation 12, plus `basket_id` so the WFE tip keys. Live `origin/main` membership.json now reports Cybersecurity=12 and Non-AI Tech=14; the fixture keeps the packet table so the inverted pair and the 5-of-10 hatch are the ones the packet named. P0-1 and P1-3 run on this.

Production-shape proof pins (still no `members` key): TPC analog 39/40 for the named nearly-all / n=1-survivor card; CXM/PFGC/RUSHA moved to the front of atrz breaking so the three lib-null rows share a frame.

## DARK TREATMENT

Command center. Page canvas is the estate `--bg` with the maturation ramp (`--m1` slate-teal → `--m2` brass → `--m3` ochre → `--m4` violet ash) as wear, not a siren. Hero/nullhero sit in luminance depth with restrained glass, no drop shadow. Unobserved tail (`.bar .b0`) is a muted hatch in the well. LENS is a glass card. Instrument calm: counts are tabular, stances are one clause.

## LIGHT TREATMENT

Research workspace. Forced `data-theme="light"` on `<html>` and judged as a design, not a tint. Canvas is the cool estate light `--bg`; panels are white material. Depth is shadow instead of glow: `html[data-theme="light"] .hero` / `.nullhero` carry `box-shadow: 0 1px 2px …, 0 10px 26px -18px …`. Hairline discipline: `.bar` and `.wear i` get inset 1px rings; `.leg` border is re-inked. Sparkline underlay opacity is raised to `.23` (`.sp-uw`). Unobserved tail is a hairline hatch plus inset ring — not a token-swapped well. Verified in r1 against those three mechanisms (shadow / hairline / underlay) and re-used here.

## Which mechanisms intentionally differ

Shared: information architecture, bilingual `.l-en`/`.l-zh`, theme panel, LENS, group cap + find, shelf vs backdrop population words, one-sentence footer.

Intentionally different material: dark depth is luminance + restrained glass; light depth is white plane + hairline + drop shadow. Hatch of the unobserved tail is a muted well on dark and a hairline hatch + inset ring on light. Token substitution alone is not the light design.

**Degraded (both themes):** when `members` is absent, theme rows are count-only (board-presence copy) and the width note is withheld. That is the honest current production state.

## Cells

| ID | Subject | Shape | Theme | Lang | Viewport | Overlay | Captured |
|---|---|---|---|---|---|---|---|
| `baseline-dark-en-1440` | baseline | production | dark | en | desktop | yes | yes |
| `baseline-light-en-1440` | baseline | production | light | en | desktop | yes | yes |
| `baseline-dark-zh-1440` | baseline | production | dark | zh | desktop | yes | yes |
| `baseline-light-zh-1440` | baseline | production | light | zh | desktop | yes | yes |
| `baseline-dark-en-390` | baseline | production | dark | en | mobile | yes | yes |
| `baseline-light-en-390` | baseline | production | light | en | mobile | yes | yes |
| `baseline-dark-zh-390` | baseline | production | dark | zh | mobile | yes | yes |
| `baseline-light-zh-390` | baseline | production | light | zh | mobile | yes | yes |
| `p0-1-pair-dark-en-1440` | p0-1-pair | members-present | dark | en | desktop | yes | yes |
| `p0-1-pair-light-en-1440` | p0-1-pair | members-present | light | en | desktop | yes | yes |
| `p0-1-pair-dark-zh-1440` | p0-1-pair | members-present | dark | zh | desktop | yes | yes |
| `p0-1-pair-light-zh-1440` | p0-1-pair | members-present | light | zh | desktop | yes | yes |
| `p0-1-partial-dark-en-1440` | p0-1-partial | members-present | dark | en | desktop | yes | yes |
| `p0-1-partial-light-en-1440` | p0-1-partial | members-present | light | en | desktop | yes | yes |
| `p0-1-partial-dark-zh-1440` | p0-1-partial | members-present | dark | zh | desktop | yes | yes |
| `p0-1-partial-light-zh-1440` | p0-1-partial | members-present | light | zh | desktop | yes | yes |
| `p0-2-nearly-all-dark-en-1440` | p0-2-nearly-all | production | dark | en | desktop | yes | yes |
| `p0-2-nearly-all-light-en-1440` | p0-2-nearly-all | production | light | en | desktop | yes | yes |
| `p0-2-nearly-all-dark-zh-1440` | p0-2-nearly-all | production | dark | zh | desktop | yes | yes |
| `p0-2-nearly-all-light-zh-1440` | p0-2-nearly-all | production | light | zh | desktop | yes | yes |
| `p0-2-8in10-dark-en-1440` | p0-2-8in10 | production | dark | en | desktop | yes | yes |
| `p0-2-8in10-light-en-1440` | p0-2-8in10 | production | light | en | desktop | yes | yes |
| `p0-2-8in10-dark-zh-1440` | p0-2-8in10 | production | dark | zh | desktop | yes | yes |
| `p0-2-8in10-light-zh-1440` | p0-2-8in10 | production | light | zh | desktop | yes | yes |
| `p1-1-n1-dark-en-1440` | p1-1-n1 | production | dark | en | desktop | yes | yes |
| `p1-1-n1-light-en-1440` | p1-1-n1 | production | light | en | desktop | yes | yes |
| `p1-1-n1-dark-zh-1440` | p1-1-n1 | production | dark | zh | desktop | yes | yes |
| `p1-1-n1-light-zh-1440` | p1-1-n1 | production | light | zh | desktop | yes | yes |
| `p1-1-nge5-dark-en-1440` | p1-1-nge5 | production | dark | en | desktop | yes | yes |
| `p1-1-nge5-light-en-1440` | p1-1-nge5 | production | light | en | desktop | yes | yes |
| `p1-1-nge5-dark-zh-1440` | p1-1-nge5 | production | dark | zh | desktop | yes | yes |
| `p1-1-nge5-light-zh-1440` | p1-1-nge5 | production | light | zh | desktop | yes | yes |
| `p1-2-libnull-dark-en-1440` | p1-2-libnull | production | dark | en | desktop | yes | yes |
| `p1-2-libnull-light-en-1440` | p1-2-libnull | production | light | en | desktop | yes | yes |
| `p1-2-libnull-dark-zh-1440` | p1-2-libnull | production | dark | zh | desktop | yes | yes |
| `p1-2-libnull-light-zh-1440` | p1-2-libnull | production | light | zh | desktop | yes | yes |
| `p1-3-wfe-dark-en-1440` | p1-3-wfe | members-present | dark | en | desktop | yes | yes |
| `p1-3-wfe-light-en-1440` | p1-3-wfe | members-present | light | en | desktop | yes | yes |
| `p1-3-wfe-dark-zh-1440` | p1-3-wfe | members-present | dark | zh | desktop | yes | yes |
| `p1-3-wfe-light-zh-1440` | p1-3-wfe | members-present | light | zh | desktop | yes | yes |
| `p1-4-footer-dark-en-1440` | p1-4-footer | production | dark | en | desktop | yes | yes |
| `p1-4-footer-light-en-1440` | p1-4-footer | production | light | en | desktop | yes | yes |
| `p1-4-footer-dark-zh-1440` | p1-4-footer | production | dark | zh | desktop | yes | yes |
| `p1-4-footer-light-zh-1440` | p1-4-footer | production | light | zh | desktop | yes | yes |
| `p1-5-209s-dark-en-1440` | p1-5-209s | production | dark | en | desktop | yes | yes |
| `p1-5-209s-light-en-1440` | p1-5-209s | production | light | en | desktop | yes | yes |
| `p1-5-209s-dark-zh-1440` | p1-5-209s | production | dark | zh | desktop | yes | yes |
| `p1-5-209s-light-zh-1440` | p1-5-209s | production | light | zh | desktop | yes | yes |
| `p1-6-capped-dark-en-1440` | p1-6-capped | production | dark | en | desktop | yes | yes |
| `p1-6-capped-light-en-1440` | p1-6-capped | production | light | en | desktop | yes | yes |
| `p1-6-capped-dark-zh-1440` | p1-6-capped | production | dark | zh | desktop | yes | yes |
| `p1-6-capped-light-zh-1440` | p1-6-capped | production | light | zh | desktop | yes | yes |
| `p1-6-expanded-dark-en-1440` | p1-6-expanded | production | dark | en | desktop | yes | yes |
| `p1-6-expanded-light-en-1440` | p1-6-expanded | production | light | en | desktop | yes | yes |
| `p1-6-expanded-dark-zh-1440` | p1-6-expanded | production | dark | zh | desktop | yes | yes |
| `p1-6-expanded-light-zh-1440` | p1-6-expanded | production | light | zh | desktop | yes | yes |
| `p1-6-find-dark-en-1440` | p1-6-find | production | dark | en | desktop | yes | yes |
| `p1-6-find-light-en-1440` | p1-6-find | production | light | en | desktop | yes | yes |
| `p1-6-find-dark-zh-1440` | p1-6-find | production | dark | zh | desktop | yes | yes |
| `p1-6-find-light-zh-1440` | p1-6-find | production | light | zh | desktop | yes | yes |
| `p1-6-find-dark-en-390` | p1-6-find | production | dark | en | mobile | yes | yes |
| `p1-6-find-light-en-390` | p1-6-find | production | light | en | mobile | yes | yes |
| `p1-6-find-dark-zh-390` | p1-6-find | production | dark | zh | mobile | yes | yes |
| `p1-6-find-light-zh-390` | p1-6-find | production | light | zh | mobile | yes | yes |
| `m1-degrade-dark-en-1440` | m1-degrade | production | dark | en | desktop | yes | yes |
| `m1-degrade-light-en-1440` | m1-degrade | production | light | en | desktop | yes | yes |
| `m1-degrade-dark-zh-1440` | m1-degrade | production | dark | zh | desktop | yes | yes |
| `m1-degrade-light-zh-1440` | m1-degrade | production | light | zh | desktop | yes | yes |

## P1-6 390w find receipt

Find query `SLS` (9th name in primary `extended_watch`, past the cap of 8). Cells `p1-6-find-*-390` type that needle; the group uncaps and the row is not `.is-miss`.

## No page h-scroll at 390

Probe `documentElement.scrollWidth > clientWidth+1` on every 390w cell: PASS (no overflow).

| Cell | Locale | Overflow |
|---|---|---|
| `baseline-dark-en-390` | en | no |
| `baseline-light-en-390` | en | no |
| `baseline-dark-zh-390` | zh | no |
| `baseline-light-zh-390` | zh | no |
| `p1-6-find-dark-en-390` | en | no |
| `p1-6-find-light-en-390` | en | no |
| `p1-6-find-dark-zh-390` | zh | no |
| `p1-6-find-light-zh-390` | zh | no |

## Scratch-render gates

| HTML | shape | `grep -c '<h1'` | `about 1 in 1` | `>—<` |
|---|---|---|---|---|
| `prod.html` | production | 1 | 0 | 0 |
| `members.html` | members-present | 1 | 0 | 0 |
| `rate39.html` | production (TPC 39/40 pin) | 1 | 0 | 0 |
| `libnull.html` | production (lib-null front pin) | 1 | 0 | 0 |

Packet assertion: `grep -c 'about 1 in 1[^0-9]'` == 0 on every scratch render.

## Capture-harness disclosure

`theme.js` `skyToggleFx` appends a `.sky-fx` sun/moon disc for ~1100ms after every `setTheme`. This harness seeds `window.__skyDeck = true` and removes leftover `.sky-fx` / `#mmb-boot` / `.mx5-aurora` after apply. Live toggles still play the flourish. Per-crop overlay column is above.

Find crops additionally hide the primary ladder and the theme panel (they sit between `#wh-find` and the groups) so the input and the matched row share a frame. Live page keeps both.

SEAT RULING 3: production JSON is copied via `git show origin/main:…` into a scratch dir; the builder's `render()` writes HTML there. This worktree never opts into `site/` or `data/`.

