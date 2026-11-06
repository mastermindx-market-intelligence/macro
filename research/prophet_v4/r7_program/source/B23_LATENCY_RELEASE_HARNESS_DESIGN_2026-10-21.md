# B23 — Prophet journey latency + release-proof measurement-harness DESIGN (2026-10-21)

BASE `e5dd30c6344e4b62a0beba054ac4da97e00bab36` (branch `lane/pro-source-b23harness-20261021-r1`, clean).
MODE: read-only inventory + design. No harness code was written, no browser/server/network was run, no
outcome data was opened. Program unit: B23 "Qualify reliability and operating budgets"
(`research/prophet_v4/r6_fable_meta_ceo_handoff/effective/BUILD_PROGRAM.json`, status
`SPECIFIED_NOT_DISPATCHED`, outputs "Source/quote/model health, bounded fanout and field metrics; exact
existing-owner rollback and ordinary refresh", decision_ids ["D11"]). Release shape: D11
(`DECISION_REGISTER.json` D11, `OPEN_TECHNICAL_DECISION_FABLE_AUTHORIZED_TO_RESOLVE`, required_output
"Accepted staged-release/rollback packet with declared freshness and field performance budgets; current
quote-state reevaluation after any rollback").

Field budgets (quoted from the commissioning packet; see "Absent / not found" item 1): **p75 LCP ≤ 2.5 s,
p75 INP ≤ 200 ms, p75 CLS ≤ 0.1, at widths 320/390/768/1440, EN and ZH, light and dark**. A historical
80.420-second / 197-object lookup and an observed production 524 are retained diagnostics, not
measurements. #9369 head `858e11a4d17f2d9387af720d01c6d84dcc80b49d` is present on host
(`git cat-file -e …^{commit}` ok); its committed diff changes `app/prophet_daily_brief.py` (63 lines) and
`scripts/build_stock_library.py` (173 lines) and **removes** `_READ_ADMISSION = BoundedSemaphore(1)`
(`git diff e5dd30c6344 858e11a4 -- app/prophet_daily_brief.py`: `-_READ_ADMISSION = …`); its synthetic
12-candidate / 192-episode timings (2.770 s → 1.552 s) are **not committed bytes** (Absent item 2). A
longer timeout is never the completion criterion; no new release, flag or telemetry plane may be built
(SEAT_RULING_R6-D11-01: "D11 is resolved by incumbent controls only").

Citation convention: `path:line` = read directly at BASE this run. `path:line @eeb6449d9dff` = quoted
through the committed census `research/prophet_v4/r6_program/wave0/D11_RELEASE_PATH_CENSUS_2026-09-23.md`
(read in full this run), whose citations were taken at that sha.

---

## Q1 — Inventory: browser/evidence tools, what each measures, matrix support, auth

**A. `scripts/capture_page_evidence.py`** — `TOOL_VERSION = "1.3.0"` (`:104`), `MANIFEST_SCHEMA
mastermind.p0_evidence.v2` (`:109`). Anonymous page census over the page registry
(`data/product_experience/page_registry.json`, `:113`); playwright is a lazily imported injected seam
(`:28-33`); screenshots content-addressed + local, only manifest/smell report committed (`:36-38`).
- Measures per page/state: screenshot bytes, `payload_bytes_total` ("sum of response body sizes reported
  by the driver", `:233`; counted from playwright `request.sizes().get("responseBodySize")`, `:1599`),
  request counters (`counters = {"requests": 0, "bytes": 0}`, `:1565`), attributed console errors and
  failed responses (`:39-46`), document layout facts (`document_height_px` `:1716`). **No timing metric of
  any kind is recorded** (grep `resource|transfer|duration|timing|performance|navigation` → only the
  bytes/requests fields above).
- Matrix: `VIEWPORTS = {desktop:(1440,900), tablet:(820,1180), mobile:(390,844)}` (`:122-126`);
  `SUPPORTED_LOCALES = ("en","zh")` (`:127`); `SUPPORTED_THEMES = ("light","dark")` (`:128`); locale/theme
  are applied through the site's own `setTheme`/`setLang` and written back from the observed `<html>`
  attributes (`:60-66`). CLI: `--base-url` live origin / `--site-dir` local serve (`:2121-2122`),
  `--viewports/--locales/--themes` (`:2128-2130`), `--timeout-s` default 30.0 (`:2145`), `--force-state`
  opt-in presentation forcing (`:101` block, `:133-140`), `--self-check` (`:2164`).
- Auth: **anonymous only, by law** — "No credential is ever entered, synthesized, or read" (`:16-19`);
  `GATED_ACCESS_REASON = "requires authenticated session; not automatable without approved fixtures"`
  (`:132`); gated states are recorded as gaps, never captures (`:130-131`). Off the render path, never
  wired into CI or the nightly (`:34-35`); confirmed: no `.github/workflows/` file runs it (grep over
  workflows finds only path-filter lists, e.g. the momoedge trigger list `ci.yml:249-256`, no run step).
  Test owner: `tests/test_capture_page_evidence.py` (driver-seam fake, no browser import `:32-33`).

**B. `ux-evidence/_tools/` collector family** (schema v1.0 frozen, `ux-evidence/README.md:1-12`).
- `collect_page.py`: `--page <page_id>`, `--width` (default 1440), `--height` (default 1000),
  `--cycle-only` (`:163-166`) — **arbitrary width is a first-class CLI input**, so 320/768 need no code
  change here. Captures extracts/sections/controls per config; `run_cycle_interaction(page, shots, w, h,
  cookies_used)` (`:48`) drives the interaction cycle. **No theme/locale handling exists** (grep over
  `collect_page.py`/`recapture_board_interactions.py` for theme/setTheme/data-lang/locale/dark → no hits),
  and no timing is recorded (see Q2).
- `pw_lib.py` — **the authenticated CDP route**: `load_aionui_cookies()` (`:61-63`) "Import session
  cookies into memory only. Never write values to disk", opens `ws://127.0.0.1:{AIONUI_CDP_ACTIVE_PORT}/
  aionui-cdp?token={AIONUI_CDP_BRIDGE_TOKEN}` (`:63-72`), `Network.getAllCookies` (`:74`), filters to
  mastermind-x.com (`:83`), injects via `new_page(browser, w, h, cookies)` (`:115-122`). No synthetic
  login exists anywhere in the family. Provenance fields `authenticated_session_used / cookie_count /
  cookies_injected` are recorded, never asserted (D11 census Q5, `collect_page.py:48-57 @eeb6449d9dff`).
- Page configs: `ux-evidence/_config/pages/us-stocks-prophet-board.json` — `url
  https://www.mastermind-x.com/us_stocks.html`, `requires_auth: false`, `local_html site/us_stocks.html`,
  sections `#us-standouts`, `#us-stage-filter`, `#trd-btn`, `#prophet-live`; `stock-detail.json` — `url
  https://www.mastermind-x.com/stock.html#ONTO`, **`requires_auth: True`**.
- Committed Prophet dossier `ux-evidence/pages/us-stocks-prophet-board/`: extracts at **390/768/1024/
  1280/1440** (`extract-390x844.json`, `extract-768x900.json`, `extract-1024x800.json`,
  `extract-1280x900.json`, `extract-1440x1000.json`), `interaction-manifest.json`, `capture-fidelity.json`,
  `run-manifest.json` (`authenticated_session_used: false`, run `20260816T171140Z-e5431db1` — an
  ANONYMOUS capture). Interaction records carry named interactions with pre/postconditions and
  `side_effect_class` (`ux-evidence/_schema/interaction.schema.json`) but **no duration field**.
- Matrix support: widths yes (arbitrary `--width`); locales/themes **no**; auth yes (real-session CDP
  cookies, config-gated).

**C. `scripts/biocatalyst_browser_verifier.py`** — product-acceptance verifier: playwright driver
(`playwright_page_driver(headless=not args.headed)` `:816`, `--headed` `:797`); "observes a rendered page…
authors no verdicts" (`:28-30`); receipts `non_authorizing: True` (`:636-637`). No timing capture (grep →
no hits). **D. `scripts/verify_commodity_workspace_browser.py`** — local-bytes + stub verifier; "It serves
local bytes and a destination stub; it is not a Terminal login or deployment proof" (`:258`). **E.
`scripts/momoedge_browser_receiver.py` + `browser/momoedge_capture/`** (MV3 extension + native
messaging): observe-only, targets `https://momoedge.ai/terminal`, "never logs in and never reads…
cookies… tokens" (`docs/runbooks/MOMOEDGE_BROWSER_COMPANION.md:12-17`) — an options-NBBO instrument, not a
mastermind-x.com page measurer. **F.** the wide `scripts/capture_*_evidence.py` family (bonds regime,
china archetype, us-stocks compression, macro command p3/p4/p5, …) — playwright page captures;
`capture_macro_command_p3.py:2493` uses CDP `Emulation.setDeviceMetricsOverride` "so 390/768" widths. **G.
Prior art only:** `research/defense_intelligence/e2e_20261011/combined_generation_v1{3,4,5}_proof/
diagnostic_timing.py` — "Ten fresh browser contexts; cache disabled" (`:4-5`), exact displayed-value
assertions, samples pinned to 10 (`:22`) — and its `diagnostic_server.py`/`serve_final_asgi*.py` which
journal per-request `elapsed_ms` into `REQUESTS.json`. This is research-folder code with a hardcoded
`/Volumes/Mastermind/...` path (`:1-2`), **not** a `scripts/` owner; usable as a pattern, not as an owner.

**Matrix truth:** no existing owner covers 4 widths × 2 locales × 2 themes. `capture_page_evidence.py`
covers en/zh × light/dark × {390, 820, 1440}; `ux-evidence` covers arbitrary widths incl. 768 but no
locale/theme; **320 px has no committed cell anywhere** (only 390+ widths appear in both owners).

## Q2 — Field (real-user) metrics today

**None.** Searches run (all at BASE): `git grep -n -E 'PerformanceObserver|largest-contentful-paint|
layout-shift|web-vitals|first-input|event-timing|performance\.mark|performance\.now|navigator\.sendBeacon'
-- templates app scripts` (plus the same against `site/*.js` in the BASE tree) → only: `templates/adtest.js:177-178`
(`navigator.sendBeacon('/api/collect', …)`), `templates/committee.html.j2` / `templates/index.html`
`performance.now()` canvas-paint loops, and vendor `templates/lightweight-charts.js` internals. Tree-wide
`git grep -l -E 'PerformanceObserver|largest-contentful-paint|layout-shift|event-timing' e5dd30c6344` →
only coincidental English ("an event-timing probability": `engine/seasonality/contracts.py:1668`;
"no authorized event-timing probability exists": `tests/test_mastermind_context.py:2108`) plus
`diagnostic_timing.py` research prior art. **No LCP/INP/CLS/Event-Timing API usage exists in any served
template or script.**

What DOES exist is the incumbent first-party beacon plane a field wire would ride: `templates/theme.js`
`loadMMAnalytics` — "page views + in-page navigation + dwell + scroll + clicks + committed searches to the
SAME-ORIGIN /api/collect" (`:113-118`), `track(type, extra)` enqueue (`:176-182`), sendBeacon/fetch-keepalive
flush; sink `POST /api/collect` (`app/main.py:520`), ≤16 KiB body (`:522-524`), per-IP throttle (`:525-527`),
batch ≤40 (`_MM_MAX_BATCH` `:260`); accepted wires are registry-derived — "the registry IS the whitelist"
(`app/main.py:261-269`, `config/growth_events.yml` + `lib/growth_registry`); rows land in the shared
Supabase `analytics_events` table via PostgREST as a BackgroundTask (`app/main.py:253-256`). That is where
field web-vitals rows would be stored — by extending this plane, not by building a new one (see Q5, BU3).

## Q3 — Fan-out: cold-load requests on the Prophet journey pages, and the serving routes

Journey surfaces at BASE: **Today** = `us_stocks.html` (built from `templates/dashboard.html.j2
mode=stocks`; `ux-evidence/_config/pages/us-stocks-prophet-board.json` source_hint) with the Prophet board
`#us-standouts`, plan cards `{% include "_us_prophet_plan_cards.html.j2" %}` (`dashboard.html.j2:17164`),
setup/evidence detail via `{% import '_prophet_setup_detail.html.j2' as psd %}` (`_us_board_cards.html.j2:1`,
`dashboard.html.j2:16826`), exact returns via `{% import "_prophet_receipts.html.j2" as pvr %}`
(`dashboard.html.j2:9`). **Candidate** = `stock.html` (`stock-detail.json`, `requires_auth: True`).

Cold-load requests as far as the templates show (file:line, URL pattern):
- `us_stocks.html` scripts: `theme.js`, `tier_preview.js`, `chart_i18n.js`, `timemachine.js`,
  `tablesort.js`, `charts.js` (stocks mode), `risk_state_live.js` (`dashboard.html.j2:18488-18501`),
  `stocktable.js` (`:20458`); font preload `InterDisplay-600.woff2` (`:317`).
- `us_stocks.html` fetches: `macrodata/release_forecast.json` (`:11545`), `basketdata/baskets.json`
  (`:19138`), **`live/prophet_live.json`** (`var PLV_URL` `:19196`; visibility-triggered refetch floor
  30 s — `PLV_FLOOR = 30000` `:19199`, refetch `:20441`), **`/api/prophet/daily-brief/v1`**
  (`:21176-21180`, `credentials:'same-origin', cache:'no-store'`), the gate payload `SRC` =
  `GATE.payload || PGATE.payload || LIFE_GATE.payload || us_today_native_emit` (`:20746-20752`) — the
  entitled board hydrates from **`/premiumdata/us_stocks.json`** ("paid rows hydrate through
  /premiumdata/us_stocks.json", `config/site_access.yml:735-737`); early-observations client
  `/api/prophet/observations/v1` (`templates/_us_early_observations_client.js:153`). CN twin polls
  `live/cn_prophet_live.json` with `?t=` cache-bust, `FLOOR = 30000` (`templates/cn_prophet_live.js:18,21,165`).
- `stock.html` scripts: `lightweight-charts-v5.js`, `chart.js`, `stockview.js`, `stockbrief.js`,
  `aidesk_lean.js` (`stock.html.j2:865-869`), `mtf.js`, `theme.js` (`:3493-3494`).
- `stock.html` fetches: `stockdata/calibration.json`, `stockdata/bc_calibration.json` (`:1917-1919`),
  **per-candidate `stockdata/<ticker>.json`** (`:2093`, `:3624`), **per-candidate
  `anticipationdata/<ticker>.json`** (`:3626`), `flowtracker/base.json` (`:2505`), `live/flow_pulse.json`
  (`:2525`), enrichment + ticker URLs (`:2573-2574`).
- Per-candidate fan-out is therefore concentrated on the candidate step (2 JSON per ticker), while the
  Today step's fan-out is a fixed set plus one gated live poll (30 s floor) and one entitled API call.
  The exact per-page request count and bytes are already machine-captured by owner A
  (`payload_bytes_total`, request counters, Q1) — the design reads them rather than re-deriving them.

Serving routes and their timeout/cache/batch settings (all handlers read this run):
- `GET /api/prophet/daily-brief/v1` — `app/prophet_daily_brief.py:137`; `Depends(require_site_full_user)`;
  **admission `BoundedSemaphore(1)`** (`:72`, "overlap fails privately instead of queueing" `:70-71`) →
  503 `DAILY_BRIEF_UNAVAILABLE` (`:123-125`) when busy; `_PRIVATE_HEADERS` = `Cache-Control: private,
  no-store` + `Vary: Authorization` imported from `app.prophet_lab` (`app/prophet_daily_brief.py:60`;
  `app/prophet_lab.py:73-78`). **No request timeout is set anywhere in the handler**; the work is
  `read_today_candidate_projection` (owner `scripts/build_stock_library.py`). #9369's head removes the
  semaphore (diff quoted above) — the post-merge concurrency shape must be re-measured, not assumed.
- `GET /api/prophet/lab/v1`, `…/episodes/{id}/intelligence`, `…/episodes/{id}/earnings` —
  `app/prophet_lab.py:233,254,326`; `require_site_full_user`; env kill switch → 503; private 503 errors;
  no-store via `_response` (`:119-120`). No page template consumes the Lab API at BASE
  (`git grep 'prophet/lab' templates` → no hits), so it is off the journey.
- `GET /api/hub/prophet` — `app/prophet_lab.py:387-403`; **internal-only** loopback + no-`X-MM-Peer` guard
  (`:358-384`); serves the raw plan book JSON with `Cache-Control: no-store` (`:402`).
- `GET /api/prophet/observations/v1` — `app/prophet_observations.py:98`; entitled; 503 private errors;
  no-store.
- `GET /api/portfolio/brief` — `app/main.py:2097`; Pro-only; **in-process cache TTL 300 s**
  (`:2102-2105`); `private, no-store`.
- Static Prophet planes: `site/prophet/{index.json,plans/*,states/*,showcase.json}` (nightly producer),
  gated premium-by-omission (`config/site_access.yml:735-737`, census Q2); **`/live/prophet_live.json` is
  deliberately undeclared → `premium.default_tier`**, pinned by test (`config/site_access.yml:347-355`);
  the intraday producer is `macro-live-prophet.timer` `Mon..Fri *-*-* 13..21:03/5:00 UTC` →
  `python -m scripts.prophet_live_evaluator`, `TimeoutStartSec=120`, resource-capped
  (`app/deploy/macro-live-prophet.service`), publishing by atomic rename (census Q1 item 14
  @eeb6449d9dff). Edge: `/api/*` is reverse-proxied to `127.0.0.1:8000` (`app/deploy/Caddyfile:121`);
  the serving edge is EdgeOne (32 mentions in the Caddyfile; e.g. the no-Cache-Control default-TTL trap,
  census Q4 @eeb6449d9dff).

## Q4 — Harness design (built only from the owners above)

**Principle.** One harness, two legs, three owners: owner A (`scripts/capture_page_evidence.py`) extended
for timing + the 320/768 viewport keys; owner B (`ux-evidence/_tools/collect_page.py` + `pw_lib.py`)
extended for timing + theme/locale; owner C (the incumbent release controls of Q7) read, never built. No
new scheduler, no CI wiring (render-budget law, `capture_page_evidence.py:34-35`), no synthetic login, no
timeout raised anywhere.

**Pages and journey steps** (steps as named by the masterplan journey, mapped to observed surfaces):
1. Today → `us_stocks.html` anonymous shell AND entitled full board (two capture classes, Q6).
2. Candidate → `stock.html#<TICKER>` (one fixed representative ticker per run, declared in the manifest;
the per-ticker fan-out is measured, not sampled across tickers).
3. Setup/evidence → the setup-detail panel inside the board card (`_us_board_cards.html.j2:1`) and the
dashboard table import (`dashboard.html.j2:16826`) — reached by the board interaction cycle
(`interaction-manifest.json` pattern).
4. Plan/none → the plan-card grid (`dashboard.html.j2:17164`) incl. the empty/"none" state as a recorded
gap-or-state (owner A's honest-gap law, `:20-27`).
5. Comparison/save → the in-page compare/watch surfaces reached from the board; the interaction cycle's
`side_effect_class` (READ_ONLY vs LOCAL_DISPLAY_PREFERENCE vs PERSISTENT_MUTATION,
`interaction.schema.json`) is the declared guard that a "save" in the harness touches only local display
preference, never a persistent mutation.
6. Exact return → the receipts block (`_prophet_receipts`, `dashboard.html.j2:9`).
7. Revisit → a second navigation to `us_stocks.html` in the same context (warm cache) after ≥ `PLV_FLOOR`
(30 s), so the live-poll path (`live/prophet_live.json`, entitled) is exercised as the ordinary-refresh
shape.

**Matrix.** 4 widths {320, 390, 768, 1440} × 2 locales {en, zh} × 2 themes {light, dark} = 16 cells per
page-step. Widths 390/768/1440 map to existing cells (owner B extracts 390/768/1440; owner A 390/1440);
**320 is a new cell for both owners** (owner B needs only a CLI value; owner A needs two `VIEWPORTS`
entries — a one-dict change behind `--viewports` validation, `:2189`). Locale/theme application is owned
by owner A's `setTheme`/`setLang` mechanism (`:60-66`) and must be ported into owner B's `new_page` flow
as the same calls (BU2) — the site's own toggle, never a URL hack.

**Runs per cell and why.** For each (page-step, cell): **N = 25 cold loads** for LCP/CLS and the
fan-out/bytes facts. Rationale: the p75 of a heavy-tailed load distribution is the 19th order statistic at
N = 25 — stable enough to distinguish a 2.5 s budget without pretending lab variance is field variance;
N < 15 makes the p75 order statistic move by whole seconds between runs; the defense-intelligence prior
art pinned 10 samples for a pass/fail display assertion (`diagnostic_timing.py:22`), which is too few for
a percentile budget. CLS is comparatively deterministic but shares the N because layout shifts are
network-jitter-driven. INP: **each named interaction is executed 30× per cell** (INP is a per-interaction
worst-ish statistic; 30 gives a p75-of-interactions per cell without masquerading as a session-wide p75).
Declared budget: total ≈ 16 cells × ~7 steps × 25 loads ≈ 2,800 page loads per full matrix run — the
harness manifest must record wall-clock and cap politeness delay (owner A `--delay-ms` default 500,
`:2132`); the matrix is divisible per page-step so a run can be split across sessions.

**Lab conditions to declare in every artifact** (owner A manifest fields extended): CPU/network throttling
— **none exists today in any owner** (grep for `setCPUThrottling|setNetworkConditions` over
`scripts/capture_*.py` → no hits); the design therefore declares the UNTHROTTLED condition as the lab
condition and records it as a field, and does not silently emulate "mid-tier mobile". Any throttling added
later is a declared condition change, a new artifact version, never a quiet re-baseline. Cache: cold =
fresh context per load (owner B prior art: "Ten fresh browser contexts; cache disabled"); warm = the
revisit step in the same context. `--as-of` pinning (owner A `:2146`) makes a run byte-reproducible; the
served `?v=` stamps (Q7) tie each load to exact asset bytes.

**How INP is exercised.** Named interactions per step, taken from the existing
`interaction-manifest.json` vocabulary (e.g. `I.board.table` grid→table toggle) plus the journey's own
acts: stage-filter change (`#us-stage-filter`), card→setup-detail expand, plan-card select, compare/save
toggle, receipts reveal, revisit reload. Each interaction is driven by the owner-B cycle
(`run_cycle_interaction`) with pre/postconditions asserted as today, PLUS (BU2) the Event-Timing read:
`PerformanceObserver` with `type: 'event'` (and `first-input` for the first interaction) injected by the
harness, reading `interactionId/processingStart/processingEnd/duration` per named interaction. The harness
reports per-interaction duration distributions per cell; it never reports a single page-level "INP" number
as if it were the field metric (see Q5).

**Request count, transferred bytes, server time.** Count + bytes ride owner A's existing counters
(`:1565`, `:1599`, `payload_bytes_total` `:233`) — no new capture mechanism. Server time per route is
captured two ways, both from existing shapes: (a) client-side resource timing via CDP/ playwright network
events per URL pattern (`responseEnd - requestStart`, and `waitingForResponse` as the server-held
fraction), attributed to the route table of Q3; (b) for the local-serve leg, a journaling serve wrapper
modeled on the defense-intelligence `diagnostic_server.py`/`REQUESTS.json` `elapsed_ms` pattern (prior
art, Q1-G) — a build unit (BU4), because no request-path server-timing owner exists at BASE (only
render-path `data/ops/nightly_timings/*.jsonl` via `scripts/nightly_timings.py`, and the API logs no
durations).

**The 524 path — reproduced or bounded, never accommodated.** The observed production 524 is an
edge-origin-timeout class; the harness never raises any timeout (owner A `--timeout-s` stays 30.0; the
systemd producer keeps `TimeoutStartSec=120`; nothing in the design touches any Caddy/EdgeOne limit).
Bounding evidence: (i) at BASE the daily-brief route admits ONE read per API process and fails fast 503
(`BoundedSemaphore(1)`, `app/prophet_daily_brief.py:72,123-125`) — the harness records that 503 as the
honest concurrency bound, and concurrent-journey loads are a declared failure class, not a retry; (ii) the
measured server-held time distribution per route (Q4 above) is compared against the incumbent tool
timeout (30 s) — any response whose server-held time exceeds a declared fraction of the incumbent edge
budget is reported as `EDGE_TIMEOUT_RISK` with its exact duration and count; (iii) reproduction of a
slow-origin shape uses the local-serve leg with an artificially cold/slow producer input declared in the
manifest (fault-injection per B23's discriminating cases "Optional source timeout; mandatory quote
stale"), never a production call. #9369's removal of the semaphore means the post-merge shape must be
re-measured before any bound is quoted as current — its synthetic timings are not proof (Absent item 2).

## Q5 — Lab p75 vs field p75

A lab p75 can prove: that the served bytes, under the declared browser/width/locale/theme and the declared
(no-)throttling condition, paint within budget in that environment; regressions between builds on the
same rig; the request/byte fan-out and the server-held time of each route; the presence/absence of error
classes (524-shaped hangs, 401/403 leaks, console errors). It cannot prove: the real-user p75 — field LCP/
INP/CLS mix devices, networks, cache states and interaction patterns the lab does not sample; a green lab
p75 is necessary evidence, never sufficient for the field budget. The two artifacts must therefore be
labeled differently (`lab_p75_*` vs `field_p75_*`) and never merged into one number.

Smallest existing-owner path to field data: the incumbent first-party beacon plane (Q2) —
`templates/theme.js` `track()` + `POST /api/collect` + the `config/growth_events.yml` registry + the
Supabase `analytics_events` table. A `web_vitals` wire (LCP/INP/CLS + width/locale/theme read from the
same `<html>` attributes owner A trusts) rides that plane: registry-declared, envelope-v1 typed, capped by
the existing ≤16 KiB/40-event batch. That is an EXTENSION of the existing plane (BU3), which is the only
lawful route under "no new telemetry plane may be built"; it still requires the D11 packet to accept the
wire declaration, so it is BLOCKED on D11, not READY. If D11 declines the wire, then no field path exists
and the release proof must say so in those words — a lab-only p75 labeled as field would be a false claim.

## Q6 — Auth: entitled pages through the ux-evidence/CDP route only

Entitled measurement uses owner B with `requires_auth` pages (`stock-detail.json`) and the board's
entitled state: `pw_lib.load_aionui_cookies()` imports the operator's real mastermind-x.com session
cookies from the live AionUI CDP bridge into the in-memory playwright context (`pw_lib.py:61-122`);
"no synthetic login is ever built" is the seat's own law — SEAT_RULING_R6-D11-01 consequence 5:
"Entitled-user proof is a real-session act. `ux-evidence` authenticates only through a live CDP session;
`capture_page_evidence.py` is anonymous-only by law." The run manifest records
`authenticated_session_used`/`cookies_injected` truthfully (owner B's provenance law); the committed
Prophet dossier is anonymous (`run-manifest.json`), so the entitled capture is a missing artifact this
design depends on (D11-a). Owner A stays anonymous always — it measures what an anonymous visitor gets:
the gated shell with `preview_rows: 3` (`config.yml:7448-7450`), public `showcase.json`, static assets,
and the honest gap rows for the gated planes (its `GATED_ACCESS_REASON` law, `:132`). Anonymous capture
still meaningfully measures: LCP/CLS of the public shell, the full static fan-out, the 401/403 posture of
gated URLs (recorded as failed responses with status, `:39-46`), and console errors. It must never be
reported as the entitled journey.

## Q7 — Release-proof rung mapping (incumbent control → observable artifact)

| Masterplan rung | Incumbent control (owner) | Observable artifact that proves it |
|---|---|---|
| Accepted source | PR review + merge to `main` (Fable main loop / operator) | merged PR + main sha; B23 packet |
| Merge → rendered | path-filtered `render`/`engine-render` on push (`render.yml:34,45,62-63 @eeb6449d9dff`); `build_site` never runs `build_prophet` (`scripts/build_site.py:4817-4818 @eeb6449d9dff`) | the `site/` render-receipt commit `render: site re-render <date> (scope=…, from=<sha>)` (`render.yml:1356-1365 @eeb6449d9dff`) |
| Installed (VPS) | `macro-update` cron `*/3` + flock + `git reset --hard` + rsync atomic publish (`app/deploy/setup.sh:68,74-75`; `update.sh:263-296 @eeb6449d9dff`) | `/api/health` `{commit, checkout}` (`app/main.py:202`); `/api/status` `checks.site.commit{,_time}` (`app/main.py:671`) |
| Producer generation | nightly "Prophet nightly" step → `scripts/build_prophet.py` writes `site/prophet/index.json`, `plans/*`, `states/*`, public `showcase.json` (`daily.yml:2319-2348`, `build_prophet.py:121,279,2790 @eeb6449d9dff`); intraday `macro-live-prophet.timer` 5-min RTH → atomic rename (`app/deploy/macro-live-prophet.service` ExecStart/`TimeoutStartSec=120`) | public R2 `prophet/health.json` `source_asof/published_at/checkpoint/index_sha256` (`build_prophet.py:216-247 @eeb6449d9dff`); render-path bands in `data/ops/nightly_timings/*.jsonl` (`scripts/nightly_timings.py`; `us_prophet_ledgers.jsonl` present at BASE) |
| Authenticated serving | Caddy `root /opt/macro/site.served`, `/api/*` → `127.0.0.1:8000` (`Caddyfile:88,121 @eeb6449d9dff`); paywall chain `paywall_check` fail-closed (`app/paywall.py:482-520 @eeb6449d9dff`); `us_board_gate` + `premium.enforced_early` | served `?v=<sha256[:8]>` stamps (`scripts/optimize_assets.py:4,59`); entitled journey capture (Q6) with zero unexpected 401/403 |
| User outcome | the B23 harness itself: entitled ux-evidence run + owner-A matrix | per-cell lab_p75 artifacts + interaction cycle receipts (Q8 table) |
| Next ordinary refresh | VPS pull ≤3 min; `/live/staleness.json` public freshness verdicts (`config/site_access.yml:358-363`); `PROPHET_MAX_SESSIONS_BEHIND = 1` (`freshness_sentinel.py:269 @eeb6449d9dff`); nightly-liveness watchdog 3×/day (`nightly-liveness.yml:1-38 @eeb6449d9dff`) | revisit-step capture (Q4) + staleness verdict at capture time recorded in the manifest |
| Rollback rehearsal | `app/deploy/live-rollback.sh:1-48` (root-only, non-destructive: stop timers, restore legacy cron, `mv` public → timestamped backup); gate flip `us_board_gate.gated:false` (`config.yml` block); `PROPHET_LIVE_NO_PUBLISH=1` (`engine/prophet_live/r2io.py:113-128 @eeb6449d9dff`); revert + re-render | the rollback script's own log lines (`[1/3]…[3/3]`, `DONE — legacy cron is primary`) + post-rollback re-capture showing the pre-cutover serving state; ledgers NOT un-advanced (seat ruling consequence 4) |

D11 open items and what each still needs (SEAT_RULING_R6-D11-01 "Open items carried"):
- **D11-a** anonymous-vs-entitled served-byte diff of `us_stocks.html`/`sector_central.html` — needs an
authenticated session capture (Q6) plus the byte diff; census NOT_ESTABLISHED 4/6.
- **D11-b** R2 bucket versioning/lifecycle policy — an operator question, not in-tree; forward-heal by
next publish is the current rollback.
- **D11-c** `/live/prophet_live.json` served status classification is source-derived — needs an
authorized origin probe receipt (production call; outside this read-only lane).

## Q8 — Acceptance table and failure classes

Who runs it: the seat host or operator, locally, off the render path (owner A law `:34-35`); never CI;
artifacts committed under `data/product_experience/…` (owner A defaults `:113-116`) and
`ux-evidence/pages/…` (owner B), with the acceptance report under
`research/prophet_v4/r7_program/source/` next to this design.

| Metric | Budget (mission text) | Statistic | Cells | Evidence artifact (path pattern) | Runner |
|---|---|---|---|---|---|
| LCP | ≤ 2.5 s | lab p75, N=25 cold loads/cell | 4 widths × {en,zh} × {light,dark} × journey steps | `data/product_experience/evidence/<sha>.png` + `p0_evidence_manifest.json` cells + `b23_latency_report.json` | seat host (owner A ext.) |
| INP | ≤ 200 ms | per-interaction p75, 30 reps/interaction/cell | same cells; named interactions per step (Q4) | `ux-evidence/pages/<page>/interaction-manifest.json` (duration-extended) + `b23_latency_report.json` | seat host/operator (owner B ext., real CDP session for entitled steps) |
| CLS | ≤ 0.1 | lab p75, N=25/cell | same cells | same as LCP row | seat host |
| Request count / transferred bytes (cold) | declared envelope per page-step (no number invented here; first run sets the baseline, later runs diff it) | per-load value + max | widths × locales × themes | `p0_evidence_manifest.json` `payload_bytes_total` + request counters | seat host (owner A, unchanged) |
| Server-held time per route | no budget minted; reported distribution + `EDGE_TIMEOUT_RISK` flag vs incumbent 30 s tool timeout | distribution, per route | entitled journey steps | `b23_server_timing.json` (CDP resource timing; local-serve journal `REQUESTS.json`-shaped) | seat host (BU1/BU4) |
| Error classes | zero | count | all | manifest `failed_responses`/console errors; 503 admission counts | seat host |
| Field metrics | the same three budgets, as `field_p75_*` | p75 over real users | real traffic | Supabase `analytics_events` (wire per Q5) | BLOCKED on D11 (BU3) |

Failure classes reported, never averaged away: (1) any 524/5xx or response exceeding the incumbent tool
timeout (`EDGE_TIMEOUT_RISK`, exact duration); (2) 401/403 on an entitled route inside an authenticated
run, or a 200 on a gated plane inside an anonymous run (entitlement leak); (3) console errors and failed
responses (owner A attribution law `:39-46`); (4) interactions that never settle (postcondition unmet
within the incumbent timeout); (5) capture-fidelity failures (owner B `capture-fidelity.json`); (6)
cache-control violations on gated assets (no-store absent); (7) request-count/bytes beyond the declared
envelope; (8) any cell recorded as a gap (gated/absent state) — gaps stay gaps, per owner A law `:20-27`.

## Q9 — Smallest build units this design implies

- **BU1** Timing + viewport extension of owner A: add LCP/CLS/INP observation and resource timing to
`scripts/capture_page_evidence.py` behind the existing `PageDriver` seam; add `VIEWPORTS` entries for
320 and 768 (`:122-126`, checked against the `--viewports` key list at `:2189`); new manifest fields
versioned by `TOOL_VERSION`.
Extends: `scripts/capture_page_evidence.py` + `tests/test_capture_page_evidence.py`. **READY** (local,
off render path, anonymous law untouched).
- **BU2** Timing + theme/locale extension of owner B: Event-Timing capture per named interaction and the
`setTheme`/`setLang` application in `ux-evidence/_tools/collect_page.py`/`pw_lib.py`; width 320/768 via
existing `--width`. Extends: `ux-evidence/_tools/*`, schemas `ux-evidence/_schema/interaction.schema.json`.
Code **READY**; the entitled RUN is **BLOCKED** on a live AionUI CDP session (operator/seat host) — this
is D11-a's missing artifact.
- **BU3** Field web-vitals wire on the incumbent beacon: `web_vitals` wire in `config/growth_events.yml`
(envelope-v1 typed) + `templates/theme.js` `track()` payload from `PerformanceObserver`. Extends:
`app/main.py` registry consumption (no collector change needed), `lib/growth_registry`,
`config/growth_events.yml`, `templates/theme.js`. **BLOCKED** on the D11 packet accepting the wire
declaration ("no new telemetry plane may be built" — this is an extension of the existing one, and only
D11 can accept it).
- **BU4** Local-serve request journal for the lab leg: a serve wrapper recording per-request
`elapsed_ms` + input digests, modeled on
`research/defense_intelligence/e2e_20261011/combined_generation_v1{3,4}_proof/diagnostic_server.py`
(prior art; not an owner). New small `scripts/` module + test. **READY** as a build; meaningful only
combined with BU1/BU2.
- **BU5** Journey manifest + acceptance report generator: a declarative journey/matrix spec consumed by
BU1/BU2 producing the Q8 report (`b23_latency_report.json` + markdown). Extends the
`scripts/nightly_timings.py` jsonl pattern for run bookkeeping. **READY**.
- No build unit touches any release control, timeout, Caddy/EdgeOne setting, systemd unit, or gate: Q7 is
read-only by design.

---

## Absent / not found

1. The 2026-10-20 Prophet masterplan file itself is not in-tree at BASE (`git ls-files research/prophet_v4
   | grep -iE '2026-10-20|MASTERPLAN'` → only 2026-08-17/2026-10-04/2026-10-06 documents). The field
   budgets are therefore quoted from the commissioning packet text, which is the mission's designated
   source; no budget number in this document is invented.
2. #9369's synthetic timings (12 candidates / 192 episodes, 2.770 s → 1.552 s): not committed bytes.
   Searched `git grep -n -E '2\.770|1\.552|192 episodes' 858e11a4 -- research scripts docs tests agentos`
   and whole-tree `git grep -n '2\.770' 858e11a4` → only coincidental timestamps/CSV floats. The
   committed #9369 facts are the diff to `app/prophet_daily_brief.py` + `scripts/build_stock_library.py`
   quoted in the header.
3. The historical 80.420-second / 197-object diagnostic: not found. `git grep -n -E '80\.42|197 objects|
   197-object' -- agentos research docs` → only unrelated data rows (e.g.
   `research/artifacts/july_2026_market_navigation/source_live_adjusted_closes.csv:156`) and
   `elapsed_ms: 80.424…` inside defense-intelligence REQUESTS logs.
4. No client web-vitals instrumentation anywhere (searches quoted in Q2); no field metric is collected or
   stored today.
5. No CPU/network throttling exists in any capture owner (grep quoted in Q4) — the lab condition is
   unthrottled and must be declared as such.
6. No 320 px cell exists in any committed evidence; 768 exists only in owner B extracts and a macro-command
   capture comment.
7. No `.github/workflows` job runs any browser capture tool (owner A's own law `:34-35`; workflow greps
   show only path-filter lists).
8. No request-path server-timing owner (API logs carry no durations; only render-path
   `data/ops/nightly_timings/*.jsonl` exists).
9. `data/product_experience/*` (page registry, P0 manifest, smell report) and all 81 `mockups/**/
   EVIDENCE.yml` receipts are sparse-omitted in this worktree (`config/sparse_worktree.json`
   `exclude_dirs`) — not read, per lane rule; shapes taken from owner A defaults and the census.
10. No page template consumes `/api/prophet/lab/v1` at BASE — the Operator Lab is off the journey.
11. An authenticated (entitled) capture of the Prophet board does not exist in-tree (D11 census Q5;
    committed dossier is anonymous).

## Outcome files avoided

No outcome data was opened this run. Paths seen only as names in listings/diffs and never read:
`data/prophet/ledger.jsonl`, `data/prophet/legacy_shadow/**`, `data/cn_prophet_audit/**`,
`data/cn_prophet_live/forward.parquet`, `data/china_prophet_rank/candidates.parquet`,
`data/neuralweb/prophet_{status,suggestions}.json` (all appeared in the #9369 `--name-only` diff),
`research/artifacts/july_2026_market_navigation/source_live_adjusted_closes.csv`,
`research/bottom_signal_backtest/results/all_base_events.csv`,
`research/oracle_asymmetry/W2_trades_in_ablation.csv` (grep hits only, lines not read beyond the matched
float), `data/ops/nightly_timings/*.jsonl` (existence checked, contents not read).

## Evidence base (primary reads this run)

`scripts/capture_page_evidence.py` (header/contract/CLI/counters), `ux-evidence/README.md`,
`ux-evidence/_tools/{collect_page.py,pw_lib.py}` (surface), `ux-evidence/_config/pages/*.json`,
`ux-evidence/pages/us-stocks-prophet-board/{run-manifest,capture-fidelity,interaction-manifest}.json`,
`ux-evidence/_schema/interaction.schema.json`, `app/prophet_lab.py`, `app/prophet_daily_brief.py`,
`app/prophet_observations.py`, `app/main.py` (collect + briefs + health/status),
`app/deploy/{Caddyfile,macro-live-prophet.service,macro-live-prophet.timer,live-rollback.sh}`,
`config/site_access.yml`, `config.yml` (`us_board_gate`), `config/growth_events.yml` (vocab),
`templates/{dashboard.html.j2,stock.html.j2,theme.js,adtest.js,cn_prophet_live.js,
_us_board_cards.html.j2,_us_early_observations_client.js}`, `.github/workflows/ci.yml` (structure),
`docs/runbooks/MOMOEDGE_BROWSER_COMPANION.md`,
`research/prophet_v4/r6_program/rulings/SEAT_RULING_R6-D11-01_2026-09-23.md`,
`research/prophet_v4/r6_program/wave0/D11_RELEASE_PATH_CENSUS_2026-09-23.md`,
`research/prophet_v4/r6_fable_meta_ceo_handoff/effective/{BUILD_PROGRAM,DECISION_REGISTER}.json`,
`research/defense_intelligence/e2e_20261011/combined_generation_v15_proof/diagnostic_timing.py` (header),
`agentos/handoffs/BIOCATALYST-CORE-PRODUCT-2026-08-22-P1-1-PROD.md` (proof section),
`agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-08-25-AD1T1-PRODUCTION-PROOF.md` (proof section),
`git diff e5dd30c6344 858e11a4d17f2d9387af720d01c6d84dcc80b49d` (stat + targeted hunks, read-only).
