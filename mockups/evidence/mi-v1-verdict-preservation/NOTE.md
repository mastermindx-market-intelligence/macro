# Preserved Research Verdicts — visual evidence (V1)

## DARK TREATMENT

Command center: card material uses `--panel` on the page `--bg`, badges sit on `--panel2`, separation is a 1px `--line` hairline only. No box shadow and no glow on cards or badges; badges use a flat 6px state dot.

## LIGHT TREATMENT

Research workspace: cards are white `--panel` on the cool canvas, hairlines via `--line`, depth from `--card-shadow` (shadow only, never glow). Counterfactual cards drop shadow so they read subordinate.

## Mechanisms that intentionally differ

- Card elevation: dark uses luminance steps (`--bg` → `--panel` → `--panel2`); light uses `--card-shadow`.
- Counterfactual row: dashed border, transparent fill, muted ink, and extra indent in both themes; light also omits shadow on `.vp-cf`.

## Theme-specific degraded states

- **pin_ok false:** dashed muted re-check chip replaces the status badge (no `vp-s-*` class); recorded literal withheld in both themes.
- **Registry absent/invalid:** entire `#vp-section` omitted from the page (no placeholder shell).

## Section crops (8)

- `crops/vp-dark-en-desktop.png`
- `crops/vp-dark-en-mobile.png`
- `crops/vp-dark-zh-desktop.png`
- `crops/vp-dark-zh-mobile.png`
- `crops/vp-light-en-desktop.png`
- `crops/vp-light-en-mobile.png`
- `crops/vp-light-zh-desktop.png`
- `crops/vp-light-zh-mobile.png`
