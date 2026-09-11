# HK Tier-1 shell — visual evidence (H2)

Outcome: **captured** (24/24 cells).

Crops are Playwright element screenshots of a `templates/hk.html.j2` render with the packet's fixture VM (Growth-scare, VHSI 32nd / mid-range, A/H 28.4% about average, DISTINCT per-tile strip values: peg negative / yuan-quote negative / overnight rate as points-only). Not a live `site/hk.html` bake — this worktree is sparse (`data/` and `site/` omitted).

Matrix: dark + light × EN + ZH × desktop 1440 × mobile 390, for the hero (`#hkx-hero-card`), the cross-market strip (`.hkx-cas-strip`), and one What To Do signal row (`.hkx-rack2 .hkx-row`) showing the monoline icons.

Harness note (M3): `window.setTheme()` fires `skyToggleFx()` — a ~1100ms crescent-moon (dark) / sun (light) overlay at z-index 2147483600. That flourish is toggle chrome, not page content. The r1 390-dark strip crop caught it mid-animation. Capture now sets `prefers-reduced-motion: reduce` (the flourish's own skip) and strips leftover `.sky-fx` nodes before shooting. Page CSS z-index is unchanged.

## Crops

- `hero/desktop/en/dark -> fb2eead9372fe6dd.png`
- `hero/desktop/en/light -> e0b8e77243389563.png`
- `hero/desktop/zh/dark -> 9c60f2a8606030ec.png`
- `hero/desktop/zh/light -> e1db611670a8f76a.png`
- `hero/mobile/en/dark -> ee4ec7104e7191cf.png`
- `hero/mobile/en/light -> 38530e6f31dfee08.png`
- `hero/mobile/zh/dark -> b7b76aa99d5d0264.png`
- `hero/mobile/zh/light -> a8f5a79059eaa84d.png`
- `strip/desktop/en/dark -> 41c573be41ada763.png`
- `strip/desktop/en/light -> ca01febcb4e8f00d.png`
- `strip/desktop/zh/dark -> a10ef463643dba5a.png`
- `strip/desktop/zh/light -> b46af0d43b98a126.png`
- `strip/mobile/en/dark -> 9682e3d8f75f73f6.png`
- `strip/mobile/en/light -> 1c2188f9612c8891.png`
- `strip/mobile/zh/dark -> b43a9f514d10eedf.png`
- `strip/mobile/zh/light -> d76ed58a3d555657.png`
- `signal-row/desktop/en/dark -> 8fffc928a12f5140.png`
- `signal-row/desktop/en/light -> 0a0bd75e5787515c.png`
- `signal-row/desktop/zh/dark -> be2a1b3e1539cbb3.png`
- `signal-row/desktop/zh/light -> 34498a6973672cb6.png`
- `signal-row/mobile/en/dark -> 01c9f2b95ee226c1.png`
- `signal-row/mobile/en/light -> 094abd40ccf9fea0.png`
- `signal-row/mobile/zh/dark -> 6c39aded2b3be6ef.png`
- `signal-row/mobile/zh/light -> f119ec1e6d4a3aec.png`
