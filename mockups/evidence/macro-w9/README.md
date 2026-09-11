# macro.html W9 r3 — evidence matrix

S1 rig: fixture-rendered `templates/dashboard.html.j2` (`mode=macro`) with real `body.page-macro mx4-grid` classes. Playwright seeds `window.__skyDeck`, applies theme/lang via `setTheme`/`setLang`, refuses a cell on attribute mismatch, hides decorative layers, and records a per-crop overlay column from a post-shot computed-style probe. Screenshots are content-addressed (`cells/<sha16>.png`) plus human aliases. Capture: `python3 -m scripts.capture_macro_w9_evidence`.

## Dark treatment vs light treatment

These are two art directions of one semantic system, not a token swap.

**DARK** is a command center: graphite field, luminance depth, instrument-calm cards, restrained amber on need-action only. Empty/cautious lanes stay dim ink on the same dark plate — no glow, no jewel.

**LIGHT** is a research workspace: cool canvas, white card material, hairline borders, shadow instead of glow. The same stance lines and labelled slices sit on white plates; warn amber is ink-on-paper, not a lit chip. Token substitution is not the proof — the light full-page (`fullpage-light-en-desktop.png`) uses white material and hairline discipline the dark page does not.

Mechanisms that intentionally differ: dark keeps restrained field glow on score numerals; light kills text-shadow (page CSS already). Degraded states (null tape, cautious Events, No alerts today) use the same DOM in both themes; the material (field vs paper) is what changes.

## Fixture

- VM: `scripts.capture_macro_w9_evidence.fixture_vm` (page-test idiom; sparse tree has no `data/`).
- Live quotes are painted at capture time inside `#sx-markets-v2` only.
- Decorative hide (disclosed): `#mmb-root`, `#mmb-boot`, `#mmb-launch`, `.sky-fx`, `.mx5-aurora`, `.theme-fab`. Overlay probe after every shot; **56/56 = clean**.
- Honest vs live `site/macro.html`: numbers are representative (CPI/FOMC week of 2026-09, Fear 32, Energy heating); Fed Path accrues (`Forward path data — accruing from nightly log`) because the fixture does not ship a full `rates_command` board; nav ticker in the null shot is a planted `#nb-tape` chip used to prove the no-op.

DO-NOT-TOUCH surfaces (`#release-radar`, `#sx-risk-v2`, `details#health`) were not edited this round.

## Cells (overlay column)

| Alias | Theme | Lang | Viewport | Overlay | What it shows |
|---|---|---|---|---|---|
| `fullpage-dark-en-desktop.png` | dark | en | 1440 | clean | Full page, command-center |
| `fullpage-light-en-desktop.png` | light | en | 1440 | clean | Full page, research workspace |
| `fullpage-dark-zh-desktop.png` | dark | zh | 1440 | clean | Full page ZH |
| `fullpage-light-zh-desktop.png` | light | zh | 1440 | clean | Full page ZH |
| `fullpage-dark-en-mobile.png` | dark | en | 390 | clean | Mobile |
| `fullpage-light-en-mobile.png` | light | en | 390 | clean | Mobile |
| `fullpage-dark-zh-mobile.png` | dark | zh | 390 | clean | Mobile ZH |
| `fullpage-light-zh-mobile.png` | light | zh | 390 | clean | Mobile ZH |
| `gde-policy-*-en-desktop.png` | dark+light | en | 1440 | clean | `.gde-policy` plain words |
| `alerts-face-*-en-desktop.png` | dark+light | en | 1440 | clean | Alerts Centre: warn badge + rows + Headline |
| `markets-live-*-en-desktop.png` | dark+light | en | 1440 | clean | `#sx-markets-v2` live fixture |
| `fed-policy-*-en-desktop.png` | dark+light | en | 1440 | clean | Fed Path + Policy Monitor in one frame |
| `hottest-desk-*-en-desktop.png` | dark+light | en | 1440 | clean | `#sx-deep-context` Hottest desk |
| `regime-tip-*-en-desktop.png` | dark+light | en | 1440 | clean | Regime `?` tip open (populated `_fc`) |
| `stance-sentiment-*-en-desktop.png` | dark+light | en | 1440 | clean | Sentiment stance line |
| `stance-sector-*-en-desktop.png` | dark+light | en | 1440 | clean | Sector stance line |
| `stance-aibrief-*-en-desktop.png` | dark+light | en | 1440 | clean | AI Brief stance line |
| `stance-events-*-en-desktop.png` | dark+light | en | 1440 | clean | Events stance line |
| `markets-null-*-*-desktop.png` | dark+light | en+zh | 1440 | clean | Null tape: skeleton + dtp behind + bilingual why |
| `nav-noop-*-*-desktop.png` | dark+light | en+zh | 1440 | clean | Nav ticker `6,712.25` unchanged on null quote |
| `regime-fc-null-*-*-desktop.png` | dark+light | en+zh | 1440 | clean | `_fc.z` null: “One input didn't settle…” |
| `alerts-zero-*-*-desktop.png` | dark+light | en+zh | 1440 | clean | need=0/total=0 neutral “No alerts today” |
| `events-none-*-*-desktop.png` | dark+light | en+zh | 1440 | clean | Events None: cautious, **no** denial string |
| `events-empty-*-*-desktop.png` | dark+light | en+zh | 1440 | clean | Events []: denial “No top-tier prints…” |
| `count-hero-badge-*-en-desktop.png` | dark+light | en | 1440 | clean | Hero Fired alerts N + Alerts badge, agreeing |
| `count-dislocation-dlg-*-en-desktop.png` | dark+light | en | 1440 | clean | Dislocation row in dialog; N rows = of N |

Manifest: `mockups/evidence/macro-w9/manifest.json` (`mastermind.p0_evidence.v2`, outcome=`captured`, 56/56). Receipt: `EVIDENCE.yml`.
