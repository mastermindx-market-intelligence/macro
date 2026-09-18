# china_intel W12 r2 — forward crops (overlay column)

S1 rig: Playwright, `data-theme`/`data-lang` applied via `setTheme`/`setLang` (mismatch refuses), overlay selectors removed (`.ift-aurora`, `.mx5-aurora`, `.sky-fx`, `#mmb-boot`), `window.__skyDeck = true`, reduced-motion. Fixture is a page-CSS overlay column, not the live bake (sparse tree has no `data/`/`site/`).

Capture AFTER the code commit, on a clean tree. `manifest.json` `sha` is `git rev-parse HEAD` at capture time.

Full 8-cell matrix stays the closing round.

| Cell | File | Judged as |
|---|---|---|
| B1 state-3 chip, dark EN | `cells/b1-state3-dark-en.png` | Command-center warn pill: `No feed is current — oldest 70d.` Failure named; no live/fresh word. |
| B1 state-4 chip, dark EN | `cells/b1-state4-dark-en.png` | Outage style, never suppressed: `Feed timestamps unavailable.` Not an all-clear. |
| Dated brief card, dark EN | `cells/brief-card-dark-en.png` | Graphite card, as-of + Policy language source chip. Identity device. |
| Dated brief card, light EN | `cells/brief-card-light-en.png` | Research workspace: white card, hairline, shadow not glow. Same IA. |
| Regime colour, EN | `cells/regime-en.png` | Risk-on hex `#1f9a55` / `rgb(31, 154, 85)` on `.cmdbar .regime b.on`. |
| Regime colour, ZH | `cells/regime-zh.png` | ZH flip `#d23f3f` / `rgb(210, 63, 63)` — same instrument, flipped for 红涨绿跌. |

Recapture: `python3 mockups/evidence/china-intel-w12-r2/capture.py`
