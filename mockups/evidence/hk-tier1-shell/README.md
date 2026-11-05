# HK Tier-1 shell — visual evidence (H2)

Outcome: **captured** (28/28 cells).

Crops are Playwright element screenshots of a `templates/hk.html.j2` render with the packet's fixture VM (Growth-scare, VHSI 32nd / mid-range, A/H 28.4% about average, DISTINCT per-tile strip values: peg negative / yuan-quote negative / overnight rate as points-only). Not a live `site/hk.html` bake — this worktree is sparse (`data/` and `site/` omitted).

Matrix: dark + light × EN + ZH × desktop 1440 × mobile 390, for the hero (`#hkx-hero-card`), the cross-market strip (`.hkx-cas-strip`), and one What To Do signal row (`.hkx-rack2 .hkx-row`) showing the monoline icons. Hero also captures `--force-state` hover(`.hkx-hbtn`) and focus(`.hkx-hbtn`) on desktop/en dark and light — REST shots cannot prove those presentations.

Harness note (M3): `window.setTheme()` fires `skyToggleFx()` — a ~1100ms crescent-moon (dark) / sun (light) overlay at z-index 2147483600. That flourish is toggle chrome, not page content. The r1 390-dark strip crop caught it mid-animation. Capture now sets `prefers-reduced-motion: reduce` (the flourish's own skip) and strips leftover `.sky-fx` nodes before shooting. Page CSS z-index is unchanged.

## Crops

- `hero/desktop/en/dark -> 6ea5207a758aa864.png`
- `hero/desktop/en/light -> 1c62268d6afe3f4c.png`
- `hero/desktop/zh/dark -> 75a7dde96d1484d3.png`
- `hero/desktop/zh/light -> ce0d45e2dcc33681.png`
- `hero/mobile/en/dark -> 93b78189233e5299.png`
- `hero/mobile/en/light -> 12abaadad6175ab3.png`
- `hero/mobile/zh/dark -> f4e9bb8b986ee49c.png`
- `hero/mobile/zh/light -> 70a5764e3d28db2a.png`
- `hero/desktop/en/dark/btn-hover -> b1d4c9575a8b85e4.png`
- `hero/desktop/en/light/btn-hover -> 5fd224794be5a577.png`
- `hero/desktop/en/dark/btn-focus -> d1d712b2b2a1cede.png`
- `hero/desktop/en/light/btn-focus -> 895781b288eee328.png`
- `strip/desktop/en/dark -> 68c4144c9e291a96.png`
- `strip/desktop/en/light -> 1b53e3e8314bed4a.png`
- `strip/desktop/zh/dark -> af8f368e4b95f939.png`
- `strip/desktop/zh/light -> 52e0df44139f91d4.png`
- `strip/mobile/en/dark -> d5c9292073378728.png`
- `strip/mobile/en/light -> 5714efcc89ebfdb0.png`
- `strip/mobile/zh/dark -> 9d3a8cb1a058a7ca.png`
- `strip/mobile/zh/light -> ed65e7cb0ac99918.png`
- `signal-row/desktop/en/dark -> 1c5c282b5ef2b74b.png`
- `signal-row/desktop/en/light -> 5bd08199db4a8671.png`
- `signal-row/desktop/zh/dark -> 27862cb893ecf626.png`
- `signal-row/desktop/zh/light -> 6cd5d92933920eab.png`
- `signal-row/mobile/en/dark -> 06929a82695d9e3e.png`
- `signal-row/mobile/en/light -> ba65e9061301c7c7.png`
- `signal-row/mobile/zh/dark -> ed5ce02ee1c2eb2b.png`
- `signal-row/mobile/zh/light -> d222ffae4348fc50.png`
