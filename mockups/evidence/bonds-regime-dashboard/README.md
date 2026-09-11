# Bonds regime-dashboard S3 — evidence matrix (round 2)

Six L1 subjects × dark/light × EN/ZH × 1440/390.
Spec G4 names a 4-subject 32-crop matrix; the seat and the round-2 brief expand that to the six L1 blocks, so the product of those axes is 48 cells, plus a stale-date gate pair.

## Fixture

- Source: `templates/bonds.html.j2` L1 wrap + page-scoped `<style>` (site-nav / seo / vector-polish stripped).
- VM: `scripts/capture_bonds_regime_dashboard_evidence.fixture_vm` (starts from `tests.test_bonds_divergence_gate._base_ctx`, the page-test idiom).
- Theme/lang: Playwright seeds localStorage then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell.

## Honest differences from live `site/bonds.html`

- No `_site_nav` chrome (two global nav families; this crop is the glance wrap).
- No live chart SVGs — health spark and the yield-curve figure stay at `.mx-skel` true geometry (58px / 120px).
- Numbers are representative (health 88, 10y 4.18%, HY OAS 2.67%, date 2026-09-10), not that night's bake.
- Sparse checkout has no `data/`; this is why the wrap is fixture-rendered.
- The Mastermind boot launcher (`#mmb-boot`) is hidden so it does not overlay the crops.

## Stale-date gate fixture

r3 production-reachable DELAYED: producer derives `last_obs` from `theme_daily.parquet` (the series it already loads). Fixture `last_obs='2026-08-01'` stands in for that dated branch so the crop shows `Data delayed since 01 Aug 2026`. The last_obs-missing copy is now `Data delayed — awaiting the daily series` (no manufactured 'feed started' claim) and is the empty-series fallback.
Captured as `stale-gate-dark-en-desktop.png` and `stale-gate-light-en-desktop.png` (`force_state: stale-delayed`).
Refusal copy must be visible; no scored verdict painted.

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
| world | dark | en | desktop | `world-dark-en-desktop.png` | yes |
| world | light | en | desktop | `world-light-en-desktop.png` | yes |
| world | dark | zh | desktop | `world-dark-zh-desktop.png` | yes |
| world | light | zh | desktop | `world-light-zh-desktop.png` | yes |
| world | dark | en | mobile | `world-dark-en-mobile.png` | yes |
| world | light | en | mobile | `world-light-en-mobile.png` | yes |
| world | dark | zh | mobile | `world-dark-zh-mobile.png` | yes |
| world | light | zh | mobile | `world-light-zh-mobile.png` | yes |
| watching | dark | en | desktop | `watching-dark-en-desktop.png` | yes |
| watching | light | en | desktop | `watching-light-en-desktop.png` | yes |
| watching | dark | zh | desktop | `watching-dark-zh-desktop.png` | yes |
| watching | light | zh | desktop | `watching-light-zh-desktop.png` | yes |
| watching | dark | en | mobile | `watching-dark-en-mobile.png` | yes |
| watching | light | en | mobile | `watching-light-en-mobile.png` | yes |
| watching | dark | zh | mobile | `watching-dark-zh-mobile.png` | yes |
| watching | light | zh | mobile | `watching-light-zh-mobile.png` | yes |
| deeper | dark | en | desktop | `deeper-dark-en-desktop.png` | yes |
| deeper | light | en | desktop | `deeper-light-en-desktop.png` | yes |
| deeper | dark | zh | desktop | `deeper-dark-zh-desktop.png` | yes |
| deeper | light | zh | desktop | `deeper-light-zh-desktop.png` | yes |
| deeper | dark | en | mobile | `deeper-dark-en-mobile.png` | yes |
| deeper | light | en | mobile | `deeper-light-en-mobile.png` | yes |
| deeper | dark | zh | mobile | `deeper-dark-zh-mobile.png` | yes |
| deeper | light | zh | mobile | `deeper-light-zh-mobile.png` | yes |
| stale-gate | dark | en | desktop | `stale-gate-dark-en-desktop.png` | yes |
| stale-gate | light | en | desktop | `stale-gate-light-en-desktop.png` | yes |

## G8 floor

See `g8.json`. Checks at 390 / 768 / 1440: page horizontal scroll, focus-visible ring, LENS tap at 390, reduced-motion skeleton, chip wrap, wide table scrolls inside `.sc-wrap`.

| Width | Page h-scroll | Focus ring | LENS tap | Reduced-motion skeleton | Chip wrap | Table in own scroller |
|---|---|---|---|---|---|---|
| 390 | none (`scrollWidth=clientWidth=390`) | visible | open (`::after` receipt on `.lens-q.cnx-tip-open`) | `animation-name: none`, plate ~114px | wrap | yes (`scrollWidth=640` > `clientWidth=364`) |
| 768 | none | visible | n/a (390 only) | n/a | wrap | n/a (table fits) |
| 1440 | none | visible | n/a | n/a | wrap | n/a (table fits) |

## G4 per-subject verdicts (judged from the crops)

Spec G4's original 32-crop matrix is 4 subjects; the round-2 brief expands it to the six L1 blocks, so `{dark,light}×{EN,ZH}×{1440,390}` × 6 = **48 REST cells**. Each subject is one G4 surface; the eight cells share the composition verdict unless a criterion is axis-specific.

| Subject | Cells | G4 verdict | Notes |
|---|---|---|---|
| hero | 8 | **PASS** | One regime word (`HEALTHY, LATE-CYCLE` / `健康 · 周期晚段`) is the largest, highest-contrast element; one clause; stance chip (`Watch — don't chase` / `观察，勿追`); caveat sits under the headline, never behind a hover; exactly one `.dtp-asof`; dark = luminance field, no drop shadow; light = white card on cool canvas, 1px hairline + soft shadow, no glow bleed; ZH has no Latin state enum; 390 stacks with no page h-scroll. Gauge + `.mx-skel` at true geometry. Residual: as-of date stays `Sep 10, 2026` in ZH. |
| changed | 8 | **PASS** | ≤4 DecisionRows; EN/ZH each one language; stance chips; 390 wraps the clause onto a second line (spec DecisionRow stack); dark = luminance panel, light = white card + hairline. |
| drivers | 8 | **PASS** | Exactly four panels; each first line is a plain-word read; one as-of per panel; no bare `r` / `Betas` / `2s10s` / `TP-adjusted` / `1y z` / `Recession-IC` at rest (receipts live on `.lens-q`); 1440 is 2-col; 390 is a swipe strip, never stacked full-width cards. Dark = luminance panels, no shadow; light = white cards, hairline, ring-not-glow. ZH uses 正常/偏紧/平静, not HEALTHY/TIGHT. |
| world | 8 | **PASS** | 8-row sovereign table + tailwind/headwind list; 390 table scrolls inside `.sc-wrap` (left four columns in the crop, remaining columns reachable by the wrap's own scroller — not page h-scroll). ZH names 美国/德国/日本…; `EMB` is the fund ticker, not a state enum. Light = white material + hairline; dark = luminance. |
| watching | 8 | **PASS** | 3 `.watch-cond` (inside ≥2 ≤4); each is condition → what it would change; no 证伪/falsifier; `.watch-foot` in the crop's language. Dark luminance panels; light white cards. r3: producer watching copy is now VM-derived (un-inverted fixture no longer presupposes inversion); these 8 cells are r2 pixels and were not recaptured. |
| deeper | 8 | **PASS** | Named landings wrap; light hover is ring-not-glow (CSS); ZH labels are 中文; 390 wraps, no page h-scroll. |
| stale-gate | 2 | **PASS** | r3 recapture, production-reachable DELAYED+dated last_obs. `force_state: stale-delayed`. Dark+light EN 1440. Refusal copy `Data delayed since 01 Aug 2026` + `.empty-why` visible; no scored verdict. Dark: panel drops one luminance stop (`.cc-delayed`, no alarm fill). Light: white card, hairline only, no shadow. |

## Composition / floor fixes made this round

- Ported `.mx-chg-row` flex (theme.css has it; this vector page does not load that sheet).
- `.lens-q` `?` buttons on L1 `data-tip` hosts + pointerdown toggle + `::after` receipt (S1 flash-and-vanish).
- Focus-visible rings on `.mx-chg-row`, `.depth a`, `.jump-nav a`, `.lens-q`.
- `.mx-skel` plates at true geometry; `animation-name: none` under `prefers-reduced-motion`.
- Inner `.sc-scroll` so the sovereign table is a real scrollport at 390 (Chromium does not let a CSS table's `min-width` expand a block's `scrollWidth`).

