# A-F05-1 News consequence panel — dual-theme evidence

Recaptured 2026-09-08 with `scripts/capture_page_evidence.py` (`--site-dir site
--routes news.html#nxConsequence`, generated_at 2026-09-08T07:01:38Z, HEAD
`b44948fb95be0265bace4201cd70e1d183bf110e`) then cropped to `#nxConsequence`
so the eight glance cards are the review surface (not the full News page).
Host page is a local render of this branch's `templates/news.html.j2` over
real `data/chronicle/events.jsonl` (no fabricated signals). `site/news.html`
was restored after capture and is not in this PR.

Window (real events, mixed families the date-sorted last-24 vault-only window
cannot show): research_vault (UBS 2026-09-07), regime_flip (Canada / Hong Kong),
macro_release (payrolls +162k), risk_band (calm → watch), prophet_ledger (FBRT),
earnings_call (FINV mixed), earnings (AAP). Search inputs were cleared
(no leftover ticker in the nav field). Also-watching stays empty on these
eight rows: FINV/AAP themes are corpus-dominant and fail closed, so this
window does not print a truncated also-watching list.

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

**Degraded states:** empty window still prints “Not available yet” /
“暂不可用” with a typed reason. Intelligence Desk and Live Wire stay
`hidden` when those payloads 404 (anonymous capture).

**Layout:** `#nxConsequence` is a single-column `.nx-consequence` wrapper
(not `nx-cols`, no `<main>`). Cards use the news sheet’s full inner width
(~1008px at 1440 after report-base + `.nxx` padding). Specified grid is
`repeat(auto-fill,minmax(280px,1fr))` / `gap:14px` — that is 3 across at
this sheet width, 1 across at 390. Four columns would need ≥1162px; the
page chrome was not widened.

Matrix: dark/light × en/zh × desktop(1440)/mobile(390) = 8 rest cells.
