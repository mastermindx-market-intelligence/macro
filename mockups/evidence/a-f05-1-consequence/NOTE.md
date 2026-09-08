# A-F05-1 News consequence panel — dual-theme evidence

Recaptured 2026-09-08 after the selector commit `576a2fc3e327d31d5d63c952cd4693dfdacbe087`
with `scripts/capture_page_evidence.py` (`--site-dir site --routes
news.html#nxConsequence --as-of 2026-09-08T08:00:00Z`, generated_at
2026-09-08T08:00:00Z) then cropped to `#nxConsequence` so the eight glance
cards are the review surface. Manifest `target.resolved_sha_or_none` is that
code commit. `git diff 576a2fc3e327 HEAD -- templates/news.html.j2` is empty
on the evidence commit — the template bytes did not change between capture
and the frames landing. Host page is a local render of this branch's
`templates/news.html.j2` over `origin/main:data/chronicle/events.jsonl`
(`git show` into a temp file; no `data/` write). `site/news.html` was
restored after capture and is not in this PR.

**Selector (shipped).** `glance_consequence_surface` takes events dated
within 7 days of the newest parseable ledger date (here 2026-09-07, so
2026-08-31–2026-09-07; `window_mode=last_7_days`; the newest-200 fallback
does not fire on this corpus) and keeps the newest 8 rows that carry a
direct ticker or a second-order ticker. Research notes with no named
exposure stay in the feed/vault. This window yields eight `prophet_ledger`
closes, newest first: FBRT, DVA, ROST, NXST, TEL, SGI, GLXY, IART. Every
card prints a Named ticker and a plain date (EN `4 Sep 2026` / ZH
`2026年9月4日`). No card says "No named ticker".

**Also-watching on the real window.** Second-order stays empty on these
eight rows (Prophet closes carry no theme, so co-theme never fires). The
three template branches are evidenced by fixture-route frames
(`fixture: true`) shot from committed HTML under
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

**Degraded states:** fewer than 3 named-exposure events in the window prints
only “No event with a named market exposure in the last 7 days.” /
“近7天没有带明确市场敞口的事件。” — no cards, no stance, no disclaimer.
An empty input still prints “Not available yet” / “暂不可用” with a typed
reason. Intelligence Desk and Live Wire stay `hidden` when those payloads
404 (anonymous capture).

**Layout:** `#nxConsequence` is a single-column `.nx-consequence` wrapper
(not `nx-cols`, no `<main>`). Cards use the news sheet’s full inner width
(desktop crop 1007px at 1440 after report-base + `.nxx` padding). Specified
grid is `repeat(auto-fill,minmax(280px,1fr))` / `gap:14px` — that is 3
across at this sheet width, 1 across at 390. Four columns would need
≥1162px; the page chrome was not widened. 3 columns is the accepted reading
of r1 R1.

**Rest-cell frames (shipped selector, real corpus):**

| file | theme | locale | viewport | crop |
|---|---|---|---|---|
| `5c2ad8b60ce771e4.png` | light | en | desktop 1440 | 1007×422 |
| `4626ebe4a24936e4.png` | dark | en | desktop 1440 | 1007×422 |
| `59dc5e337383145e.png` | light | zh | desktop 1440 | 1007×422 |
| `f91968d40cb46fbf.png` | dark | zh | desktop 1440 | 1007×422 |
| `d15c1636d9af3c1d.png` | light | en | mobile 390 | 320×1014 |
| `7472b2e033aec06b.png` | dark | en | mobile 390 | 320×1014 |
| `6f0c49319ed4ff59.png` | light | zh | mobile 390 | 320×952 |
| `f58c89becc17b432.png` | dark | zh | mobile 390 | 320×952 |

Each rest cell shows the same eight Named prophet-close cards in the order
above. Mobile is one column. The site chat FAB is pre-existing chrome and
may overlap the last mobile card; it is not this panel's.

Matrix: dark/light × en/zh × desktop(1440)/mobile(390) = 8 rest cells,
plus 3 fixture frames.
