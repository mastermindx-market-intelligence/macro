# Intraday Flow W11 r2 — forward crops (overlay column)

S1 rig: Playwright, `data-theme`/`data-lang` applied via `setTheme`/`setLang` (mismatch refuses), overlay selectors removed (`.ift-aurora`, `.mx5-aurora`, `.sky-fx`, `#mmb-boot`), `window.__skyDeck = true`, reduced-motion. Fixture is a page-CSS overlay column, not the live bake (sparse tree has no `data/`/`site/`).

Full 16-cell matrix stays r3.

| Cell | File | Judged as |
|---|---|---|
| stamp + tip open, dark EN | `cells/stamp-tip-dark-en.png` | Command-center: graphite panel, restrained `?` ring, opaque instrument tip. Absolute date. Tip = label · bare phrase, no noun stutter. |
| stamp + tip open, light EN | `cells/stamp-tip-light-en.png` | Research workspace: white card, hairline, ink-link `?`, shadow instead of glow. Same IA as dark, different material. |
| counted control, dark EN | `cells/control-dark-en.png` | Quiet underline control in muted, `Showing 8 of 116 leaders · See all 116`. |
| counted control, light EN | `cells/control-light-en.png` | Same copy; `See all 116` is an ink-link on white — an action, not a glow. |
| ZH tip row | `cells/tip-row-zh.png` | `行情 · 已送达 · 资金带 · 已送达 · 期权流 · 已送达` — same mechanism as EN, no `行情 行情`. |
| forced-outage stance | `cells/outage-stance-en.png` | Distinct from stand-aside: pill `No read`, reason `Prices aren't coming through — no read on this name right now`. |

Recapture: `python3 mockups/evidence/intraday-flow-w11-r2/capture.py`
