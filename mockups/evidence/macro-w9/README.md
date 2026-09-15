# macro.html W9 r4 — evidence matrix

S1 rig: fixture-rendered `templates/dashboard.html.j2` (`mode=macro`) with real `body.page-macro mx4-grid` classes. Playwright seeds `window.__skyDeck`, applies theme/lang via `setTheme`/`setLang`, refuses a cell on attribute mismatch, hides decorative layers, and records a per-crop overlay column from a post-shot computed-style probe. Screenshots are content-addressed (`cells/<sha16>.png`) plus human aliases. Capture: `python3 -m scripts.capture_macro_w9_evidence` **at a clean committed HEAD** (r4 code sha `795fda103318def45393e147c638892c6765a096`).

## Axis coverage (per subject family — not a uniform 8-cell REST)

The standing matrix is dark/light × EN/ZH × 1440/390, but that full product only applies to `fullpage`. Other families are seat-frozen additions on top of the r3 set:

| Family | Subjects | Axes this round | N |
|---|---|---|---|
| **fullpage** | `fullpage` | dark/light × EN/ZH × 1440/390 (all 8) | 8 |
| **close** (stance/component) | `gde-policy`, `alerts-face`, `markets-live`, `fed-policy`, `hottest-desk`, `regime-tip`, `stance-sentiment`, `stance-sector`, `stance-aibrief`, `stance-events` | dark+light EN desktop **+ dark ZH desktop** | 10 × 3 = 30 |
| **degraded** | `markets-null`, `nav-noop`, `regime-fc-null`, `alerts-zero`, `events-none`, `events-empty` | dark+light × EN/ZH desktop **+ dark EN 390w** | 6 × 5 = 30 |
| **count** | `count-hero-badge`, `count-dislocation-dlg` | dark+light EN desktop **+ dark ZH desktop** | 2 × 3 = 6 |

**74/74 captured, overlay clean.** "N/N" alone is not the coverage claim — the table above is.

r4 additions vs r3: each degraded state gained `*-dark-en-mobile.png`; each close/count cell gained `*-dark-zh-desktop.png`. Existing bilingual-desktop degraded cells and EN-desktop close cells were recaptured, not dropped.

## Dark treatment vs light treatment

These are two art directions of one semantic system, not a token swap.

**DARK** is a command center: graphite field, luminance depth, instrument-calm cards, restrained amber on need-action only. Empty/cautious lanes stay dim ink on the same dark plate — no glow, no jewel.

**LIGHT** is a research workspace: cool canvas, white card material, hairline borders, shadow instead of glow. The same stance lines and labelled slices sit on white plates; warn amber is ink-on-paper, not a lit chip. Token substitution is not the proof — the light full-page (`fullpage-light-en-desktop.png`) uses white material and hairline discipline the dark page does not.

Mechanisms that intentionally differ: dark keeps restrained field glow on score numerals; light kills text-shadow (page CSS already). Degraded states (null tape, cautious Events, No alerts today) use the same DOM in both themes; the material (field vs paper) is what changes.

## Fixture honesty (named gaps)

- VM: `scripts.capture_macro_w9_evidence.fixture_vm` (page-test idiom; sparse tree has no `data/`).
- Live quotes are painted at capture time inside `#sx-markets-v2` only.
- Decorative hide (disclosed): `#mmb-root`, `#mmb-boot`, `#mmb-launch`, `.sky-fx`, `.mx5-aurora`, `.theme-fab`. Overlay probe after every shot; **74/74 = clean**.
- Honest vs live `site/macro.html`: numbers are representative (CPI/FOMC week of 2026-09, Fear 32, Energy heating).
- **Fed Path accrues** (`Forward path data — accruing from nightly log`) because the fixture does not ship a full `rates_command` board.
- **60-SESSION PATH accrues** (`Path chart — accruing from nightly log.`) across ~40% of the hero row in every fullpage cell — the fixture has no `ms_history` series. Same class of fixture gap as Fed Path.
- **Empty `mx5-ai-ticker-pill` under "AI Brief"** (both themes, fullpage + `stance-aibrief-*`): fixture `macro_news.synthesis.top_tickers` is a list of **strings** (`["XLE"]`); the face reads `tk.ticker` (live producer emits `[{"ticker": k, "count": v}, …]` per `engine/macro_news.py`). The ~40×12px mint/dim-green capsule is that empty pill — fixture-VM, not a live empty-chip defect. Named so the recapture is not mistaken for a product chip with no label.
- Nav ticker in the null shot is a planted `#nb-tape` chip used to prove the no-op.
- **Stocks week-ahead band** (`test_stocks_band_tristate_source_pin_unreachable_code`): source-string pin on unreachable code inside the macro-only wrapper. **Source-verified, never render-verified.**

DO-NOT-TOUCH surfaces (`#release-radar`, `#sx-risk-v2`, `details#health`) were not edited this round.

## Cells (overlay column)

### fullpage — dark/light × EN/ZH × 1440/390

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

### close / count — dark+light EN desktop + dark ZH desktop

| Alias | Theme | Lang | Viewport | Overlay | What it shows |
|---|---|---|---|---|---|
| `gde-policy-*-en-desktop.png` + `gde-policy-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | `.gde-policy` plain words |
| `alerts-face-*-en-desktop.png` + `alerts-face-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Alerts Centre: warn badge + rows + Headline |
| `markets-live-*-en-desktop.png` + `markets-live-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | `#sx-markets-v2` live fixture |
| `fed-policy-*-en-desktop.png` + `fed-policy-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Fed Path + Policy Monitor in one frame |
| `hottest-desk-*-en-desktop.png` + `hottest-desk-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | `#sx-deep-context` Hottest desk |
| `regime-tip-*-en-desktop.png` + `regime-tip-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Regime `?` tip open (populated `_fc`) |
| `stance-sentiment-*-en-desktop.png` + `stance-sentiment-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Sentiment stance line |
| `stance-sector-*-en-desktop.png` + `stance-sector-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Sector stance line |
| `stance-aibrief-*-en-desktop.png` + `stance-aibrief-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | AI Brief stance line (empty ticker pill: fixture, see honesty) |
| `stance-events-*-en-desktop.png` + `stance-events-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Events stance line (populated calendar) |
| `count-hero-badge-*-en-desktop.png` + `count-hero-badge-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Hero Fired alerts N + Alerts badge, agreeing |
| `count-dislocation-dlg-*-en-desktop.png` + `count-dislocation-dlg-dark-zh-desktop.png` | dark+light EN; dark ZH | en / zh | 1440 | clean | Dislocation row in dialog; N rows = of N |

### degraded — dark+light × EN/ZH desktop + dark EN 390w

| Alias | Theme | Lang | Viewport | Overlay | What it shows |
|---|---|---|---|---|---|
| `markets-null-*-*-desktop.png` + `markets-null-dark-en-mobile.png` | dark+light × en+zh desktop; dark EN 390 | en / zh | 1440 / 390 | clean | Null tape: skeleton + dtp behind + bilingual why |
| `nav-noop-*-*-desktop.png` + `nav-noop-dark-en-mobile.png` | dark+light × en+zh desktop; dark EN 390 | en / zh | 1440 / 390 | clean | Nav ticker `6,712.25` unchanged on null quote |
| `regime-fc-null-*-*-desktop.png` + `regime-fc-null-dark-en-mobile.png` | dark+light × en+zh desktop; dark EN 390 | en / zh | 1440 / 390 | clean | `_fc.z` null: “One input didn't settle…” |
| `alerts-zero-*-*-desktop.png` + `alerts-zero-dark-en-mobile.png` | dark+light × en+zh desktop; dark EN 390 | en / zh | 1440 / 390 | clean | need=0/total=0 neutral “No alerts today” |
| `events-none-*-*-desktop.png` + `events-none-dark-en-mobile.png` | dark+light × en+zh desktop; dark EN 390 | en / zh | 1440 / 390 | clean | Events None: cautious + reconnecting line, **no** denial, **content height** (both themes) |
| `events-empty-*-*-desktop.png` + `events-empty-dark-en-mobile.png` | dark+light × en+zh desktop; dark EN 390 | en / zh | 1440 / 390 | clean | Events []: denial “No top-tier prints…” |

m1 recapture (both themes, content-height card): `events-none-dark-en-desktop.png`, `events-none-light-en-desktop.png` (ZH twins and `events-none-dark-en-mobile.png` also recaptured).

Manifest: `mockups/evidence/macro-w9/manifest.json` (`mastermind.p0_evidence.v2`, outcome=`captured`, 74/74, `target.resolved_sha_or_none` = `795fda103318def45393e147c638892c6765a096`). Receipt: `EVIDENCE.yml`.
