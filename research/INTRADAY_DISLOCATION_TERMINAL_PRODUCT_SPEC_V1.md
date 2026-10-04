# Intraday Dislocation + Reclaim — Terminal product spec V1

Program: Intraday Dislocation + Reclaim (Chairman handoff, mastermind-terminal#784).
Owner of this document: the Fable CEO seat for that program. Status: FROZEN for wave 1
of the product build (changes need a new version, not an edit).
Related: `WS:LIVE-ENTRY-RADAR` (tactical 5-minute detector/evaluator truth),
`research/LIVE_ENTRY_RADAR_*` (live lane), `DEC:LER-LIVE-LANE-VPS-5MIN-REST`,
Terminal #782 (ownership contract: the Terminal is the product consumer, never a second
detector plane), R1-A (accepted) and R1-B (registered, unrun) under `research/species/tti_r1b/`.

## §0 Acceptance gates (not done unless)

A wave of this program is not done unless every line below that names it is true and
evidenced in the PR body by command output or committed crops.

- G1 (producer) The served Radar artifact carries dislocation episodes in the owner schema
  `mastermind.live_entry_episode.v1` with `detector_id` of the dislocation family, built by the
  existing 5-minute Radar pass and NO new timer, process, WebSocket, queue, or quote owner.
  Evidence: `jq '.episodes[] | select(.detector_id|startswith("tactical_dislocation"))'` on the
  VPS file plus the pass receipt showing REST/snapshot reads only.
- G2 (producer) The pack behind the pass is FRESH (`pack.as_of` equals the last completed
  session) on the VPS at pre-open. Today it is not (see §3.1); G2 is a precondition, not a
  side effect, and a wave that ships a detector against a stale pack has shipped nothing.
- G3 (producer) Every non-terminal episode has exactly one producer path to each terminal
  state. INVALIDATED has a producer (today none exists anywhere in the Radar).
- G4 (consumer) `GET /api/v1/dislocations?view=my` answers 401 `{state:"unauthenticated"}`
  without a session, `Cache-Control: private, no-store` always, and one of the honest data
  states in §4.4 when the Macro file is missing, stale, or malformed; it never fabricates an
  empty-but-healthy answer.
- G5 (consumer) The screen renders from committed fixtures in the owner schema with no network,
  dark theme, EN and ZH, desktop 1440 and mobile 390; four crops (forming, confirmed, invalidated
  tail, source-unavailable) are committed under `mockups/refs/dislocations/` in the Terminal repo
  and linked in the PR body.
- G6 (consumer) Every row answers "so what do I do" in plain words under the glance budget; no
  internal state names, study names, raw slugs, or untranslated statistics are visible at glance
  tier; nothing on the surface says or implies a trading edge, win rate, or return.
- G7 (both) No duplicate planes: no second detector, residual engine, episode lifecycle,
  evidence ledger, quote owner, catalyst clock, or materiality model. The PR body names the
  incumbent each piece reads from.
- G8 (both) Fresh end-to-end happy path with zero manual workarounds on the real deploy
  (route answers from the real VPS file for a seeded test user with one watchlist symbol that
  currently has an episode, or the honest "no episodes for your symbols" state).

## §1 Purpose and non-claims

The user job: "which of MY names (and which names in the market) are in an intraday
dislocation right now, is a reclaim forming or confirmed, when did we know it, how fresh is
that, and does a known catalyst explain it". The product is decision SUPPORT: it shows a
causal reclaim recognition (dislocation → exhaustion → reclaim) with honest invalidation,
freshness, and catalyst uncertainty, and it accrues prospective evidence. It does not claim a
trading edge; R1-B is registered and unrun, and nothing here is promoted to rank, size, or
gate authority. The gauntlet remains the promotion gate (`DNR:KILL-WASHOUT-TURN` is confronted
by name in §3.2: this family is display-tier context and does not re-propose the killed
standalone construction).

## §2 Owner map (who computes what; nothing new is minted)

| Concern | Owner today | This spec |
|---|---|---|
| Intraday event truth, episode lifecycle, states, evidence refs | Macro Radar (`engine/entry_radar/live_eval.py`, 5-min VPS timer, REST only) | adds one detector family inside the same pass |
| Nightly thresholds / pack / substrate | Macro Radar pack builder (`scripts/entry_radar_live_pack.py`) | must become fresh (§3.1); no new builder |
| Delayed/live quotes, per-name intraday aggregates | Macro live files + the injectable `intraday_reader` seam (REST, bounded windows) | consumed through the seam only |
| Durable evidence ledger, resolution at horizon | Radar ledger + nightly reconciler (sole durable writer) | episodes resolve through it; Terminal reads counts |
| Catalyst envelope (freshness/relevance clocks, `radar_episode_id`) | Catalyst context (#8305 lane) | joined by `radar_episode_id`; never copied into `evidence_refs` |
| Desirability / Prophet | Prophet (untouchable) | not referenced on this surface |
| User watchlists / portfolio | Terminal Supabase (`watchlists`, `watchlist_symbols`, `portfolio_positions`) | joined server-side per user |
| Product surface, chart, alerts | Terminal (`terminal/app`, chart engine) | new route + screen + chart plumbing |
| Served file | `/var/lib/macro-live/public/live/entry_radar.json` (Caddy default-deny; root-owned 0644) | read from disk by the Terminal server on the same host via `MACRO_LIVE_DIR` |

Observed 2026-10-04: `terminal.service` runs `npm run start` as root in `/opt/terminal/terminal`
on the same host as the Macro live directory, so a disk read needs no Caddy allowlist change.
If the service is ever de-privileged, the route needs group read on that directory, not an
HTTP hop.

## §3 Producer (Macro Radar side)

### §3.1 Precondition — the pack is six weeks stale and the builder cannot finish on the VPS

Measured on the VPS 2026-10-04 00:50Z: `pack/current.json` reads `as_of 2026-08-19`;
`macro-entry-radar-pack.service` is killed by its start timeout on every pre-open attempt
(timer `Mon..Fri 10..13:20 UTC`; four attempts per day; each consumed ~15 min CPU, 256 MB
memory peak against `MemoryHigh=256M`, `MemoryMax=512M`, ~950 MB swap peak, `CPUQuota=60%`;
the box has 2 cores and 3.9 GB with ~120 MB free). The served `entry_radar.json` therefore
carries a stale `pack` block. PR macro#8353 (streamed substrate sink + compact per-name state)
is the first half of the pack scale plan and is explicitly additive ("neither changes what the
builder writes today"). The producer critical path is therefore:

- P-SCALE-2: a disk-backed `SubstrateSink` (per-name parquet append under the pack staging
  dir) plus `save_pack`/`load_pack` reading the streamed substrate, wired into
  `scripts/entry_radar_live_pack.py` behind a flag, with ONE measured full-universe build
  (peak RSS, wall time) recorded in the PR body. Gate: peak RSS under 256 MB or the unit's
  limits are raised by a DEC that cites the measurement — never by guessing (Sol ruling,
  WS record: "Do NOT solve by arbitrary timeout/memory inflation — measure the cold-start
  phases, establish the actual bottleneck").
- P-SCALE-3: switch the VPS unit to the streamed path; first fresh pack on the VPS; G2 holds.
- Alternative kept open, not chosen yet: build the pack off-box on the nightly runner and ship
  the artifact to R2 for the VPS to pull (house law: heavy compute off the render path,
  artifacts to R2). Choose by the P-SCALE-2 measurement: if a streamed build still cannot fit
  the unit, the pack moves off-box.

### §3.2 Detector family `tactical_dislocation` (display tier)

- Lives in the existing 5-minute pass (`run_pass`), evaluates only names the pass already
  admits, and reads intraday aggregates only through the injected `intraday_reader`
  (adjusted, ascending, bounded window; no bulk minute crawl; no permanent minute store;
  nothing is recomputed from 1-minute bars — `DEC:LER-LIVE-LANE-VPS-5MIN-REST`).
- Cheap gate before any reader call: the delayed snapshot's drawdown from the session open or
  prior close against the pack's nightly-inverted ATR threshold (the armed-pack pattern). Names
  below the gate cost nothing.
- Constructs reused, not re-derived: `engine/entry_radar/tactical_research.py` (`BAR_SECONDS=300`,
  `closed_prefix`, `segment_features`, `select_arms`, `first_touch`, `fixed_outcome`) and the
  exhaustion geometry from `engine/entry_radar/tactical_exhaustion.py` once #7274 lands. The
  detector cannot ship before #7274 merges; building a second exhaustion module to go faster
  is forbidden (G7).
- State mapping (owner `DetectorState`, unchanged enum): PROBING = gate crossed on the delayed
  snapshot; ARMED = exhaustion geometry present on closed 5-minute bars; TURNING = reclaim in
  progress (price back through the first reclaim level, not yet held); CANDIDATE = reclaim held
  for the registered confirmation window; INVALIDATED = a new session low beyond the invalidation
  band or the time budget exceeded while ARMED/TURNING (first INVALIDATED producer in the Radar);
  EXPIRED = session ended while PROBING/ARMED/TURNING; RESOLVED = fixed-outcome horizon reached
  through the existing reconciler (`RESOLVE_HORIZON_SESSIONS=10`).
- Every episode carries the owner contract fields; `detector_version` and `detector_spec_hash`
  pin the parameters; `knowable_at` is the bar close that produced the transition plus the
  delayed-feed lag, never the pass wall clock; `data_quality`/`freshness` are filled from the
  pass's own quote-age receipts.
- Confronting `DNR:KILL-WASHOUT-TURN` by name: the killed row closed a specific standalone
  washout-turn construction as an authority signal. This family makes no standalone claim,
  carries no rank/size/gate authority, and is published as context with its nulls printed;
  promotion of anything here requires a pre-registered gauntlet pass. The implementing lane
  quotes the registry row verbatim in its PR body.

### §3.3 Publication (one pack, additive)

- `entry_radar.json` keeps schema `entry_radar.live/v1`; an additive top-level `episodes` array
  is added (owner schema rows; non-terminal episodes plus terminal ones from the current and
  previous session). Existing consumers are untouched. `health` gains `episodes_count` and
  `episodes_schema`.
- Catalyst coverage is attached by the catalyst owner as `episode.catalyst =
  {radar_episode_schema, radar_episode_id, fresh_until, relevant_until, coverage}` when the
  #8305 envelope binds to that episode id; absent means "coverage unknown", never "no catalyst".

## §4 Consumer (Terminal side)

### §4.1 Route `GET /api/v1/dislocations`

- Query `view=my|market` (default `my`), optional `sym` filter.
- Auth: `supabase.auth.getUser` via `@/lib/supabase/server`; 401 `{state:"unauthenticated"}`.
  Market view gated by `isPaidTier` (ASSUMED; cheap to flip).
- Reads `${MACRO_LIVE_DIR}/entry_radar.json` (default `/var/lib/macro-live/public/live`), parses
  once per process per mtime, caps age with the same bounded cache pattern as
  `event-impact/route.ts` (MAX_STALE_MS, `stale` flag).
- Joins `watchlist_symbols` and `portfolio_positions` for the user; `my` returns only episodes on
  those symbols; `market` returns all, newest transition first, capped at 200.
- Response: `{state, generated_at, knowable_at_max, source:{asof, pack_as_of, pack_fresh,
  quote_age_s, delayed:true}, episodes:[...owner rows + display fields...]}`. Headers always
  `Cache-Control: private, no-store`.

### §4.2 Screen `/dislocations` ("My Dislocations")

- Nav: added to `AppNav.tsx` `TOP` after `discover`. Dark-only, EN/ZH via the existing i18n
  path; no translated text in `title=` attributes.
- Groups: Forming (PROBING/ARMED/TURNING) — Confirmed (CANDIDATE) — a quiet tail of Ended
  (INVALIDATED/EXPIRED, this and previous session). Each row: symbol, plain-word stance
  ("washout, no turn yet" / "turn forming, not held" / "reclaim held" / "turn failed" /
  "ran out of session"), the knowable-at clock in the user's timezone with the delay badge
  ("as of 10:35, 15-min delayed data"), a freshness chip, a catalyst chip (known / unknown
  coverage), and a "what we're watching" line (the invalidation level and the time budget).
- Technicals (ATR multiple, exhaustion geometry, score fields) live in a popover, never at
  glance. Banned at glance: state enum names, `detector_id`, study names, raw slugs, raw
  statistics.
- Empty and degraded states are first-class (§4.4), designed, and in the fixtures.

### §4.3 Chart deep link

- Row click → `/terminal?sym=<sym>&episode=<id>`; `terminal/app/terminal/page.tsx` already reads
  `sym`; new `episode` param plumbs the episode's levels into `MarkerSpec` / `PriceLineSpec`
  (`terminal/lib/chart-engine/api.ts`): dislocation low, first reclaim level, invalidation
  level, and one marker per transition at its knowable-at time. No new indicator math in the
  Terminal (`intradayMath.ts` is not extended for this).

### §4.4 Honest data states (route `state`)

`ok` · `ok_empty` (file fresh, no episodes on the user's symbols) · `data_delayed` (always true
on the delayed cluster; a badge, not an error) · `stale` (file older than the pass cadence plus
grace, or `pack.fresh=false`) · `source_unavailable` (file missing/unreadable/malformed) ·
`unauthenticated`. The screen renders each distinctly; `stale` and `source_unavailable` show
the last good `asof` and say so in plain words. "OK-empty" is never shown as healthy when the
source is stale.

### §4.5 Fixtures, tests, entitlement

- Fixtures in the owner schema, committed under `terminal/fixtures/dislocations/`; served only
  through the existing fixture-cookie mechanism (`FIXTURE_STORE_COOKIE`), never in production.
- Route tests: 401, no-store header, each §4.4 state, `my` vs `market` join, cap.
- e2e: one spec under `terminal/e2e/` rendering the four crops from fixtures.
- Alerts ("tell me when a reclaim on my names is confirmed") are a LATER wave: a new
  `alerts.condition` kind evaluated server-side from the same file; no per-browser fan-out.

## §5 Evidence accrual (prospective, honest)

Episodes resolve through the Radar's own ledger at the fixed horizon; the Terminal shows only
counts with honest-N ("12 confirmed reclaims on your names this quarter, 9 resolved") and never
a return, hit rate, or ranking until a gauntlet pass promotes the family. Falsifier language is
never front-facing; the Calibration Lab remains the home of verdicts.

## §6 Waves, lanes, owned files

| Wave | Lane | Repo / owned files | Depends on | Gate |
|---|---|---|---|---|
| W0 | P-SCALE-2 streamed sink + wiring + measurement | macro `engine/entry_radar/live_pack.py`, `scripts/entry_radar_live_pack.py`, tests | #8353 merged | measured peak RSS in PR body |
| W0 | P-SCALE-3 VPS switch, first fresh pack | VPS unit + DEC | P-SCALE-2 | G2 on the VPS |
| W1 | T-ROUTE route + fixtures + types + tests | terminal `app/api/v1/dislocations/route.ts`, `lib/dislocations/*`, `fixtures/dislocations/*`, tests | spec only | G4, G7 |
| W1 | T-SCREEN screen + nav + i18n (design via `designer`) | terminal `app/(shell)/dislocations/*`, `AppNav.tsx`, i18n files | T-ROUTE types | G5, G6 |
| W2 | T-CHART deep link + markers | terminal `app/terminal/page.tsx`, chart plumbing | T-ROUTE | crops of markers |
| W2 | D-DETECTOR dislocation family in the pass + INVALIDATED producer + `episodes` publication | macro `engine/entry_radar/live_eval.py`, detector module, tests | #7274 merged, W0 | G1, G3 |
| W3 | ACCEPT real-path acceptance (G8) + alerts wave decision | both | W1, W2 | G8 |

W1 proceeds against fixtures immediately; nothing in W1 waits on the producer.

## §7 Assumptions (labelled)

- ASSUMED: Market view is paid-tier. STATED: Terminal is dark-only + EN/ZH; one market-wide pack
  joined server-side (architecture A). PHYSICS: the delayed cluster is ~15 minutes behind; the
  pass is 5-minute REST. INHERITED: Radar episode schema, state enum, horizons, DNR kills,
  catalyst clocks are owner-declared absolutes.
- Open: whether `episodes` publication should be a separate served file rather than an
  additive key (chosen: additive key, to keep ONE pack and ONE reader); whether W2 D-DETECTOR
  starts before R1-B runs (chosen: yes — display tier ships freely; R1-B governs promotion only).
