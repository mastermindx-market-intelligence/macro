# Bonds regime-dashboard S3 — evidence matrix (round 4)

Six L1 subjects × dark/light × EN/ZH × 1440/390.
Spec G4 names a 4-subject 32-crop matrix; the seat and the round-2 brief expand that to the six L1 blocks, so the product of those axes is 48 cells, plus DELAYED-card force_state pairs (stale + unbuilt).

## Fixture

- Source: `templates/bonds.html.j2` L1 wrap + page-scoped `<style>` (site-nav / seo / vector-polish stripped).
- VM: `scripts/capture_bonds_regime_dashboard_evidence.fixture_vm` (starts from `tests.test_bonds_divergence_gate._base_ctx`, the page-test idiom). Watching is `_watching(vm)` — un-inverted fixture no longer presupposes inversion.
- Theme/lang: Playwright seeds `window.__skyDeck = true` then localStorage, then calls `window.setTheme` / `window.setLang`; a mismatch refuses the cell. `__skyDeck` bows out of `theme.js` `skyToggleFx` (the ~1100ms sun/moon disc).
- Decorative hide (disclosed): `#mmb-boot`, `#mmb-launch`, `#mmb-root`, `.sky-fx`, `.mx5-aurora`, `.theme-fab`. This page does not ship an aurora or theme FAB; the hide is belt-and-suspenders. Overlay probe runs after every recaptured shot. Only the 24 recaptured cells carry the overlay column; the other 28 predate the probe.

## Honest differences from live `site/bonds.html`

- No `_site_nav` chrome (two global nav families; this crop is the glance wrap).
- No live chart SVGs — health spark and the yield-curve figure stay at `.mx-skel` true geometry (58px / 120px).
- Numbers are representative (health 88, 10y 4.18%, HY OAS 2.67%, date 2026-09-10), not that night's bake.
- Sparse checkout has no `data/`; this is why the wrap is fixture-rendered.
- The Mastermind boot launcher (`#mmb-boot`) is hidden so it does not overlay the crops.

## Delayed-card fixtures (r4 + W7-A true-cause)

Four DELAYED causes per `scripts/build_bonds.py:158-205`; only branches 1, 2, and (this round) 4 are cropped. Branch 3 is test-pinned, not cropped this round.

1. **stale** (`last_obs < as_of`): `divergence_card_state(False, '2026-08-14', '2026-08-01', '2026-09-10')` → `Data delayed since 01 Aug 2026` + series-not-updated why. Aliases `stale-gate-*-en-desktop.png` (`force_state: stale-delayed`).
2. **unbuilt** (`last_obs >= as_of`): `divergence_card_state(False, None, '2026-09-10', '2026-09-10')` → `This read isn't live yet — the comparison engine hasn't produced it`. No date, no feed-delay. Aliases `unbuilt-gate-*-en-desktop.png` (`force_state: unbuilt-delayed`).
3. **unknown** (`last_obs` real, `as_of` unparseable): cause-neutral copy, no date — see `scripts/build_bonds.py:196-201`. Not cropped this round (test-pinned only).
4. **awaiting** (series missing): `Data delayed — awaiting the daily series`. Not cropped this round.

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
| unbuilt-gate | dark | en | desktop | `unbuilt-gate-dark-en-desktop.png` | yes |
| unbuilt-gate | light | en | desktop | `unbuilt-gate-light-en-desktop.png` | yes |

## Capture round (per-cell provenance)

The 52-cell matrix is mixed-generation; per-cell `capture_tree` + `captured_at` in `manifest.json` describe each committed cell. Summary:

- **Round 2 (2026-09-11T01:58:37Z, scratch `bonds_s3_evidence_jipsev5n`)** — 20 cells: changed × 8, drivers×1440 × 4, deeper × 8.
- **Round 4 (2026-09-11T02:54:55Z, scratch `bonds_s3_r4_<uuid>`)** — 24 cells: world × 8, watching × 8, drivers×390 × 4, stale-gate × 2, unbuilt-gate × 2.
- **W7-A heal (this commit, scratch `bonds_s3_hero_<uuid>`)** — 8 cells: hero × 8 (recaptured to depict the head's shipped ZH date form `截至 2026年9月10日`).

Manifest's `generated_at` is the time the manifest was last rewritten; per-cell fields are the source of truth.

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
| hero | 8 | **PASS** | W7-A recapture (8 hero crops re-shot at this heal's committed tree, `capture_tree: bonds_s3_hero_<uuid>` in the manifest). One regime word (`HEALTHY, LATE-CYCLE` / `健康 · 周期晚段`) is the largest, highest-contrast element; one clause; stance chip (`Watch — don't chase` / `观察，勿追`); caveat sits under the headline, never behind a hover; exactly one `.dtp-asof`; dark = luminance field, no drop shadow; light = white card on cool canvas, 1px hairline + soft shadow, no glow bleed; ZH has no Latin state enum; 390 stacks with no page h-scroll. Gauge + `.mx-skel` at true geometry. ZH hero as-of renders the shipped ZH date form `截至 2026年9月10日` (visually confirmed in `hero-light-zh-desktop.png`, `hero-dark-zh-desktop.png`); EN is `As of Sep 10, 2026`. |
| changed | 8 | **PASS** | r2 pixels (changed copy unchanged this round). ≤4 DecisionRows; EN/ZH each one language; stance chips; 390 wraps the clause onto a second line (spec DecisionRow stack); dark = luminance panel, light = white card + hairline. |
| drivers | 8 | **PASS** (390 recaptured; 1440 still r2) | Exactly four panels; each first line is a plain-word read; one as-of per panel; no bare `r` / `Betas` / `2s10s` / `TP-adjusted` / `1y z` / `Recession-IC` at rest (receipts live on `.lens-q`); 1440 is 2-col (r2 pixels — `align-items:start` is a 390 rule, so 1440 composition is unchanged). r4 390: swipe strip, never stacked full-width cards; the second card peeks and top-aligns rather than stretching (m4). Dark = luminance panels, no shadow; light = white cards, hairline, ring-not-glow. ZH uses 曲线与增长/正常/偏紧, not HEALTHY/TIGHT. Overlay=clean. |
| world | 8 | **PASS** | r4 recapture. Subtitle binds `g.direction` (`the world is tightening` / `全球融资成本在收紧` on the rising fixture). 8-row sovereign table + tailwind/headwind list; `.world-list{max-width:36rem}` is visible at 1440 (list does not span the crop). 390 table scrolls inside `.sc-wrap` (left four columns in the crop). EN 390 dark/light and ZH 390 dark are byte-identical to r2 (`36rem` does not bind at 364px); recaptured anyway, overlay=clean. ZH names 美国/德国/日本…; `EMB` is the fund ticker, not a state enum. Light = white material + hairline; dark = luminance. |
| watching | 8 | **PASS** | r4 recapture. 3 `.watch-cond`; VM-derived copy (`The curve inverts again while growth still holds` / `增长仍在时曲线再次倒挂`) — the r2 "un-inverts" premise is gone. Each is condition → what it would change; no 证伪/falsifier; `.watch-foot` in the crop's language. 390 stacks. Dark luminance panels; light white cards + hairline. Overlay=clean. |
| deeper | 8 | **PASS** | r2 pixels (deeper copy unchanged this round). Named landings wrap; light hover is ring-not-glow (CSS); ZH labels are 中文; 390 wraps, no page h-scroll. |
| stale-gate | 2 | **PASS** | r4 recapture, DELAYED cause=stale. Dark+light EN 1440. Lead `Data delayed since 01 Aug 2026`; why `The daily series has not updated…`; no scored verdict, no "price feed" claim. Dark: panel drops one luminance stop (`.cc-delayed`, no alarm fill). Light: white card, hairline only, no shadow. Overlay=clean. |
| unbuilt-gate | 2 | **PASS** | r4 new, DELAYED cause=unbuilt (`last_obs == as_of`). Dark+light EN 1440. Lead `This read isn't live yet — the comparison engine hasn't produced it`; why names the missing engine run; **no date, no feed-delay**. Same delayed material as stale-gate (luminance drop / white hairline card), not an alarm. Overlay=clean. |

## r4 recapture overlay column

`window.__skyDeck=true` before `setTheme`. Probe selectors: `.sky-fx`, `.mx5-aurora`, `#mmb-boot`, `#mmb-launch`, `#mmb-root`, `.theme-fab`. `clean` = none of those were visible in the shot.

| Alias | Overlay | Judgment |
|---|---|---|
| `watching-dark-en-desktop.png` | clean | PASS — "inverts again while growth still holds"; 3 luminance panels |
| `watching-light-en-desktop.png` | clean | PASS — same copy; white cards + hairline |
| `watching-dark-zh-desktop.png` | clean | PASS — `增长仍在时曲线再次倒挂`; no Latin enum |
| `watching-light-zh-desktop.png` | clean | PASS — same ZH; white cards |
| `watching-dark-en-mobile.png` | clean | PASS — 390 stacks 3 cards |
| `watching-light-en-mobile.png` | clean | PASS — 390 stacks; white cards |
| `watching-dark-zh-mobile.png` | clean | PASS — 390 ZH stack |
| `watching-light-zh-mobile.png` | clean | PASS — 390 ZH stack; white cards |
| `world-dark-en-desktop.png` | clean | PASS — tightening bound to rising; list capped 36rem |
| `world-light-en-desktop.png` | clean | PASS — white material + hairline; same IA |
| `world-dark-zh-desktop.png` | clean | PASS — `全球融资成本在收紧`; 美国/德国/日本 |
| `world-light-zh-desktop.png` | clean | PASS — ZH light; white + hairline |
| `world-dark-en-mobile.png` | clean | PASS — byte-identical to r2 (36rem inert at 364px); table in `.sc-wrap` |
| `world-light-en-mobile.png` | clean | PASS — byte-identical to r2; light hairline |
| `world-dark-zh-mobile.png` | clean | PASS — byte-identical to r2; ZH names |
| `world-light-zh-mobile.png` | clean | PASS — ZH 390 light (new hash); table scroller |
| `drivers-dark-en-mobile.png` | clean | PASS — swipe strip, next card peeks, top-aligned |
| `drivers-light-en-mobile.png` | clean | PASS — white swipe cards, top-aligned |
| `drivers-dark-zh-mobile.png` | clean | PASS — `曲线与增长` / `正常`; swipe |
| `drivers-light-zh-mobile.png` | clean | PASS — ZH light swipe |
| `stale-gate-dark-en-desktop.png` | clean | PASS — dated delay, series-not-updated why |
| `stale-gate-light-en-desktop.png` | clean | PASS — white hairline card; same copy |
| `unbuilt-gate-dark-en-desktop.png` | clean | PASS — not-live copy; no date |
| `unbuilt-gate-light-en-desktop.png` | clean | PASS — white hairline; not-live copy |

## Composition / floor fixes made this round

- Ported `.mx-chg-row` flex (theme.css has it; this vector page does not load that sheet).
- `.lens-q` `?` buttons on L1 `data-tip` hosts + pointerdown toggle + `::after` receipt (S1 flash-and-vanish).
- Focus-visible rings on `.mx-chg-row`, `.depth a`, `.jump-nav a`, `.lens-q`.
- `.mx-skel` plates at true geometry; `animation-name: none` under `prefers-reduced-motion`.
- Inner `.sc-scroll` so the sovereign table is a real scrollport at 390 (Chromium does not let a CSS table's `min-width` expand a block's `scrollWidth`).

