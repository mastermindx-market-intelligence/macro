# A-F05-1 News consequence panel — dual-theme evidence

Recaptured 2026-09-08 after the r4 ruling commit that lands with
these frames. Host page is a local render of this branch's
`templates/news.html.j2` over `origin/main:data/chronicle/events.jsonl`
(`git show` into `/tmp/r6896-capture/events.jsonl`; no `data/` write).
The eight rest cells are Playwright locator screenshots of
`#nxConsequence` after the page's own `setTheme` / `setLang` (same
dark/light × en/zh × 1440/390 matrix as `scripts/capture_page_evidence.py`;
1300ms settle so the theme flourish is gone). After this commit lands,
`git rev-parse HEAD` is the capture sha;
`git diff HEAD HEAD -- templates/news.html.j2 engine/chronicle/impact.py`
is empty because the frames and the selector landed together.
`site/news.html` was not written.

**Real window (shipped selector).** `glance_consequence_surface` on the
11,087-event spine (`git show origin/main:data/chronicle/events.jsonl`)
returns `window_mode=last_7_days`, as-of 2026-09-07 so the dated header
is EN `Events from 31 Aug to 7 Sep 2026` /
ZH `2026年8月31日至9月7日的事件`, `event_count=97`, **0 rows**,
`empty_kind=no_named_exposure`. The panel prints only
“No event with a named market exposure in the last 7 days.” /
“近7天没有带明确市场敞口的事件。” — no cards, no stance, no section
line. That is the honest product at this head. The r4 family exemption
(`GLANCE_NAMED_EXPOSURE_FAMILIES`) is withdrawn: every glance row must
carry a named exposure; `prophet_ledger` stays excluded; no asset map
was invented for macro/regime/risk events.

**Populated cards (fixture).** The real window has no named-exposure
row, so populated cards are evidenced by fixture-route frames
(`fixture: true`) from
`fixtures/named-exposure-earnings.html`, built from three real
`earnings` events on the same spine that carry tickers (FISV, HLX, KO).
Dark/light × EN/ZH at 1440. No size slot. No “Size not available yet”.

**Also-watching on the real window.** Second-order stays empty because
there are no rows. The three template branches stay evidenced by the
same fixture-route frames as r4 (`fixture: true`):

| file | state | what it shows |
|---|---|---|
| `31057e53c4f37407.png` | present | "Also watching" AMD + AVGO under a Named NVDA card |
| `52a4c4dde525103e.png` | truncated | "Also watching" AMD AVGO TSM ASML — the template `[:4]` cap |
| `4a7fccbf4ae2840c.png` | dropped | "Also-watching list not available yet · too many weak matches were dropped (12)" |

**DARK TREATMENT:** command center — deep charcoal sheet, restrained blue
accent bar on the section head, dark cards with the existing `.nx-rel`
hairline plus `box-shadow: var(--card-shadow)` (dark token is the 1px top
highlight `0 1px 0 rgba(255,255,255,.02)`) and an inset ring
`inset 0 0 0 1px color-mix(in srgb, var(--line) 55%, transparent)`. No drop
shadow. No glow.

**LIGHT TREATMENT:** research workspace — white `var(--panel)` card plane
(theme.css surface token; `--card` is not a root token), existing `.nx-rel`
hairline, elevation from the light `--card-shadow` token
(`0 1px 3px rgba(20,30,50,.07)`) plus one soft ambient layer
`0 8px 24px rgba(20,30,50,.06)`. Hover uses `var(--popover-shadow)`. Not a
token-swap of the dark ring; not a cool lavender canvas.

**Which mechanisms differ:** dark depth is highlight + inset `--line` ring;
light depth is a white plane + real drop shadow. Shared: `.nx-rel` card
markup, hairline border, section copy, 280px auto-fill grid.

**Degraded states:** ZERO named-exposure events in the window prints only
“No event with a named market exposure in the last 7 days.” /
“近7天没有带明确市场敞口的事件。” — no cards, no stance, no section
line. The dated window label still prints so a stale corpus is visibly
dated. An empty input still prints “Not available yet” / “暂不可用”
with a typed reason. The newest-200 fallback is labelled
“Latest 200 recorded events” / “最近记录的200个事件”. Intelligence Desk
and Live Wire stay `hidden` when those payloads 404 (anonymous capture).

**Layout:** `#nxConsequence` is a single-column `.nx-consequence` wrapper
(not `nx-cols`, no `<main>`). The empty-state crop is **1008×161** at 1440
and **320×182** (EN) / **320×161** (ZH) at 390 — PNG IHDR. Specified grid
is `repeat(auto-fill,minmax(280px,1fr))` / `gap:14px`.

**Rest-cell frames (shipped selector, real corpus — empty state). Crop
column is PNG IHDR (`struct.unpack('>II', data[16:24])`), not a CSS box:**

| file | theme | locale | viewport | crop (IHDR) |
|---|---|---|---|---|
| `6e564687716cf8fa.png` | light | en | desktop 1440 | 1008×161 |
| `88f826c217433395.png` | dark | en | desktop 1440 | 1008×161 |
| `f540d86c90e7b06b.png` | light | zh | desktop 1440 | 1008×161 |
| `6d340338b81cb3e5.png` | dark | zh | desktop 1440 | 1008×161 |
| `2713b2e3b02a84f2.png` | light | en | mobile 390 | 320×182 |
| `b3ec31e2b3b111bc.png` | dark | en | mobile 390 | 320×182 |
| `1468774f34c3a576.png` | light | zh | mobile 390 | 320×161 |
| `c73656afa945bb7e.png` | dark | zh | mobile 390 | 320×161 |

Each rest cell shows the dated header and the typed empty sentence. No
cards. Mobile is one column.

**Named-exposure earnings fixtures (dark/light × EN/ZH at 1440):**

| file | theme | locale | viewport | crop (IHDR) |
|---|---|---|---|---|
| `a78ba5764aebb856.png` | dark | en | desktop 1440 | 1404×219 |
| `9454c359edd4f426.png` | light | en | desktop 1440 | 1404×219 |
| `a73e8812eb5866c4.png` | dark | zh | desktop 1440 | 1404×199 |
| `2fad9c906d4a7b05.png` | light | zh | desktop 1440 | 1404×199 |

Matrix: dark/light × en/zh × desktop(1440)/mobile(390) = 8 rest cells,
plus 4 named-exposure fixture frames and 3 also-watching fixture frames.
