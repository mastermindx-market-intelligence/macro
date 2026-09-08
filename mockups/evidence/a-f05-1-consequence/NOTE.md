# A-F05-1 News consequence panel — dual-theme evidence

Recaptured 2026-09-08 after the selector/copy commit
`ba157e10d400475dd765c82f8f7b794c7fbc36f0`. Host page is a local render of
this branch's `templates/news.html.j2` over
`origin/main:data/chronicle/events.jsonl` (`git show` into a temp file; no
`data/` write). The eight rest cells are Playwright locator screenshots of
`#nxConsequence` after the page's own `setTheme` / `setLang` (same
dark/light × en/zh × 1440/390 matrix as `scripts/capture_page_evidence.py`;
1300ms settle so the theme flourish is gone). Manifest
`target.resolved_sha_or_none` is that code commit.
`git diff ba157e10d400 HEAD -- templates/news.html.j2 engine/chronicle/impact.py`
is empty on the evidence commit — those bytes did not change between
capture and the frames landing. `site/news.html` was restored after
capture and is not in this PR.

**Selector (shipped).** `glance_consequence_surface` takes events dated
within 7 days of the newest parseable ledger date (here 2026-09-07, so
2026-08-31–2026-09-07; `window_mode=last_7_days`; the newest-200 fallback
does not fire on this corpus). Eligible families: earnings, earnings_call,
macro_release, regime/risk shifts, and research_vault rows that carry a
named exposure. `prophet_ledger` is a typed exclusion (the product's own
trade ledger is not a market event). Earnings / calls / vault notes still
need a named ticker; macro prints and regime/risk shifts do not. Every
qualifying row up to 8 renders; the typed empty state appears only when
ZERO rows qualify. This window yields seven cards, newest first:
regime_flip ×4, macro_release ×2, risk_band ×1. Header:
EN `Events from 31 Aug to 7 Sep 2026` /
ZH `2026年8月31日至9月7日的事件`. Every card prints a plain date and
`Size not available yet` / `暂无幅度`. Zero prophet closes. Zero
"Also watching" on this real window.

**Also-watching on the real window.** Second-order stays empty on these
seven rows. The three template branches are evidenced by fixture-route
frames (`fixture: true`) shot from committed HTML under
`mockups/evidence/a-f05-1-consequence/fixtures/`:

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

**Degraded states:** ZERO named-exposure / eligible-family events in the
window prints only “No event with a named market exposure in the last 7
days.” / “近7天没有带明确市场敞口的事件。” — no cards, no stance, no
disclaimer. The dated window label still prints so a stale corpus is
visibly dated. An empty input still prints “Not available yet” /
“暂不可用” with a typed reason. The newest-200 fallback is labelled
“Latest 200 recorded events” / “最近记录的200个事件”. Intelligence Desk
and Live Wire stay `hidden` when those payloads 404 (anonymous capture).

**Layout:** `#nxConsequence` is a single-column `.nx-consequence` wrapper
(not `nx-cols`, no `<main>`). Cards use the news sheet’s full inner width
(desktop crop **1008px** at 1440 after report-base + `.nxx` padding —
PNG IHDR). Specified grid is `repeat(auto-fill,minmax(280px,1fr))` /
`gap:14px` — that is 3 across at this sheet width, 1 across at 390. Four
columns would need ≥1162px; the page chrome was not widened. 3 columns is
the accepted reading of r1 R1.

**Rest-cell frames (shipped selector, real corpus). Crop column is PNG
IHDR (`struct.unpack('>II', data[16:24])`), not a CSS box:**

| file | theme | locale | viewport | crop (IHDR) |
|---|---|---|---|---|
| `18545452a1fdb5a5.png` | light | en | desktop 1440 | 1008×553 |
| `c49afc56f76921ca.png` | dark | en | desktop 1440 | 1008×553 |
| `54f944f225e84d91.png` | light | zh | desktop 1440 | 1008×469 |
| `2d64d1bc5fcba156.png` | dark | zh | desktop 1440 | 1008×469 |
| `8db849567482055b.png` | light | en | mobile 390 | 320×1114 |
| `01b64f3cb232c717.png` | dark | en | mobile 390 | 320×1114 |
| `8a722ccb269e2036.png` | light | zh | mobile 390 | 320×948 |
| `7281162bc87a37ba.png` | dark | zh | mobile 390 | 320×948 |

Each rest cell shows the same seven cards in the order above. Mobile is
one column. The site chat FAB is pre-existing chrome and may overlap a
mobile card; it is not this panel's.

Matrix: dark/light × en/zh × desktop(1440)/mobile(390) = 8 rest cells,
plus 3 fixture frames.
