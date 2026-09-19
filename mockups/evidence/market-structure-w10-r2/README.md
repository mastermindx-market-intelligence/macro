# Market Structure — W10 r2 evidence (6 crops)

SUPERSEDED by the r3/r4 matrix; manifest head predates its own features (capture-from-dirty-tree, disclosed 2026-09-11)

Fixture-rendered `templates/market_structure.html.j2` (no live `data/` bake).
Playwright seeds `localStorage` (`theme`, `lang`, clears `themeAuto`), sets
`window.__skyDeck = true` (bows out of theme.js `skyToggleFx` sun/moon
flourish), calls `setTheme`/`setLang`, re-reads `html[data-theme]` /
`html[data-lang]`, and refuses a cell on mismatch. Fixture HTML carries the
real `body.page-msp` class. Any leftover `.sky-fx` node is removed before
the shot; `.aurora` and the theme FAB are hidden (disclosed below).

Full 16-cell matrix (dark/light × EN/ZH × 1440/390) stays r4.

## DARK TREATMENT

Command center: luminance depth, instrument glass, restrained colour wash.
`.sc-chip.changed` sits on a 12% blue wash against graphite; `.sc-chip.empty`
is a dashed hairline on transparent graphite, no blue, no glow — a designed
hole, not a highlighted blank. `.rc.adding.near-flat` drops the full green
to a 5% wash and muted ink so a grazing CTA add cannot impersonate VC's
real +$11.8B move.

## LIGHT TREATMENT

Research workspace: cool canvas, white material, hairline discipline, shadow
instead of glow. `.sc-chip.empty` uses `--bg` (the canvas, not the white
card `--panel`) so the dashed hole reads as paper-on-desk, not a second
card nested on a card. `.near-flat` in light is a paper chip: canvas fill,
cool up/dn hairline mix, 8% ink shadow, muted ink — never the dark bloom
transplanted onto white, and never "tokens already split the two art
directions."

## Intentional differences

| Mechanism | Dark | Light |
|---|---|---|
| Empty chip ground | transparent on graphite | `--bg` canvas, no card wash |
| Near-flat fill | 5% up/dn wash | canvas `--bg` + 8% ink shadow |
| Near-flat border | faded up/dn mix on graphite | same mix against light hairline |
| Changed chip | 12% blue wash (unchanged) | token `--blue` on white (unchanged) |

## Crops

| File | Subject | Theme | Lang | Captured | Overlay |
|---|---|---|---|---|---|
| `crop-changed-dark-en.png` | revived change strip with a real labelled chip | dark | EN | yes | none (aurora/sky-fx/FAB hidden) |
| `crop-changed-light-en.png` | revived change strip with a real labelled chip | light | EN | yes | none (aurora/sky-fx/FAB hidden) |
| `crop-empty-dark-en.png` | .sc-chip.empty designed hole | dark | EN | yes | none (aurora/sky-fx/FAB hidden) |
| `crop-empty-light-en.png` | .sc-chip.empty designed hole | light | EN | yes | none (aurora/sky-fx/FAB hidden) |
| `crop-near-flat-dark-en.png` | CTA .near-flat chip | dark | EN | yes | none (aurora/sky-fx/FAB hidden) |
| `crop-near-flat-light-en.png` | CTA .near-flat chip | light | EN | yes | none (aurora/sky-fx/FAB hidden) |

## Disclosed hides

- `window.__skyDeck = true` before `setTheme` so the ~1100ms sun/moon disc
  is never photographed.
- `.sky-fx` nodes removed if any survived.
- `.aurora` (page bloom) and the theme FAB set `display:none` for these
  crops so the chip is the subject. Live visitors still see both.

## Honest differences vs live

- Fixture VM, not the VPS bake.
- Shared site nav renders; some nav JS 404s are expected.
- Three synthetic overlays on the committed fixture (producer long→short
  note, empty-note hole, `cta_near_flat=true`).
