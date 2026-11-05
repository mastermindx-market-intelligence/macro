# Cycle W8 r2 — unavailable-why crops (partial)

New user-visible surface on 17/19 measured cards: the worded unavailable
block now carries a plain-word why. Full dual-theme matrix (dark/light ×
EN/ZH × 1440/390) stays r3. These 4 cells are 1440-only.

## Rig (S1 pattern)

- Fixture feeds the real `hazardLine` markup (non_monotone_cdf why — the
  live 17/19 case) plus a compact MEASURED card with the projection fallback.
- Real page identity: `html.cyc-page.cyc-main`, bare `<body>` (matches
  `site/cycle.html`).
- `window.__skyDeck = true` before paint so theme.js would bow out of
  `skyToggleFx`.
- theme.js / sky.js are **not loaded**. Decorative layers (`.mx5-aurora`,
  `.sky-fx`, theme FAB, `span.disc`) are therefore not mounted, and a
  disclosed CSS hide (`display:none !important`) is also applied.
- Overlay probe (selectors `.sky-fx`, `.mx5-aurora`, `.theme-fab`,
  `span.disc`, `.aurora`) recorded in `overlay_probe.json`.

## Cells

| file | theme | lang | viewport | overlay over content | why visible |
|---|---|---|---|---|---|
| unavailable_1440_dark_en.png | dark (applied) | en (applied) | 1440 | none | TURN HAZARD + Unavailable today — the model's short- and long-window reads disagreed… |
| unavailable_1440_dark_zh.png | dark (applied) | zh (applied) | 1440 | none | 转折风险 + 今日暂不可用——模型的短窗与长窗读数不一致… |
| unavailable_1440_light_en.png | light (applied) | en (applied) | 1440 | none | same EN why; white panel / hairline / shadow (not glow) |
| unavailable_1440_light_zh.png | light (applied) | zh (applied) | 1440 | none | same ZH why; white panel / hairline / shadow (not glow) |

Self-judgment: no stutter ("Turn hazard Turn hazard unavailable" /
「转折风险 转折风险暂不可用」 absent). No sun/moon disc, aurora bloom, or
FAB over the copy. Dark = command-center panel; light = research-workspace
white material. 390 cells and the remaining state-coverage cases are r3.
