---
workstream: WS:MARKET-OS
operation: marketontology-f01f13-market-orientation-projection-20260830-sol-001
packet: A-F01-MOR-2a
chairman_override: 2026-09-06 (Meta-CEO A seat owns F01/F13 Market Orientation per research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md:112)
frozen_authority: DEC:MARKET-ONTOLOGY-MARKET-ORIENTATION-PROJECTION-2026-08-30
handoff_unresolved: "The exact lawful premarket schedule and minimum source-currentness set require Project-Sol archaeology." (agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:93)
recorded_by: claude/mo-a-3-a-f01-mor2-premarket-archaeology-20260924
recorded_at: 2026-09-24
scope: RECORDS ONLY — no code, no template, no workflow, no data, no site, no config, no agentos edit
---

# MOR-2 premarket archaeology — facts the MOR-2b build packet needs

## §0 Verdict (≤8 lines)

Three weekday workflows fire 09:00–13:30Z AND already execute the full shim/externalize/stamp sweep on a render-path runner: `.github/workflows/asia-close.yml:26-28` (crons `30 9`, `30 10`, `15 11 * * *`; `runs-on: [self-hosted, macstudio]` at line 46; sweep at lines 827–833; `git add data/ site/` at line 879), `.github/workflows/sector-intelligence.yml:12` (cron `15 3,12,17,22 * * 1-5`; `runs-on: render-linux` at line 53; sweep at lines 134–136), and `.github/workflows/sentinel.yml:4` (cron `*/30 * * * *`; `runs-on: [self-hosted, macstudio-light]` at line 16; sweep at lines 56–58; commits site/vector.html + site/index.html at line 59). NO single one is unique; sector-intelligence is the cleanest fit because its sweep publishes to main unconditionally. The minimum current source set at 11:30Z (07:30 ET) is `site/live/quotes.json` ON THE `live-data` ORPHAN BRANCH (live-quotes.yml:131 builds root `quotes.json`, force-pushes to `live-data` at line 155) — the in-tree `site/live/quotes.json` is 58+ days stale because both VPS-gated scheduled writers are turned off (live-quotes.yml:53, intraday-fastpath.yml:54, btc-live.yml:44). Everything else is STALE_WITH_LAST_KNOWN (nightly writes data/regime + data/neuralweb/* at 22:30/23:30Z via daily.yml:638) or NOT_YET_OPEN (US RTH opens 13:30Z). MOR-2b's lawful insertion point is one new step inside sector-intelligence's existing rebuild job AFTER the preflight (line 95) and BEFORE the publish (line 117), gated on `github.event.schedule == '12 * * 1-5'` for the 12:15Z weekday slot. Bounded dependency: `scripts/build_am_edition.py:715-748` already produces `site/am_edition.{html,json}` from committed artifacts only; its `_feasibility()` at line 716 has THREE outcomes — `BLOCKED` (no committed source_as_of, line 722–728), `BLOCKED` (parse failure, line 733–739), `AVAILABLE` (fresh tape, line 743) or `DEGRADED` (stale but readable, line 744–748) — never broken, always returns 0 (line 848). No new workflow family; no new LLM call; no rank/score/size.

## §1 Workflow census (every weekday cron firing 09:00–13:30Z)

Three workflows fire 09:00–13:30Z on a render-path runner and run the full shim/externalize/stamp sweep:

- `.github/workflows/asia-close.yml:26-28` — crons `30 9`, `30 10`, `15 11 * * *`; `runs-on: [self-hosted, macstudio]` (line 46); sweep at lines 827–833; `git add data/ site/` (line 879); 60m collect / 165m builds (lines 47, 191); concurrency `pipeline-asia` (gate decides run=true).
- `.github/workflows/sector-intelligence.yml:12` — cron `15 3,12,17,22 * * 1-5`; `runs-on: render-linux` default / `macstudio` recovery (line 53); sweep at lines 134–136; `git add site/basketdata site/basket site/sectors site/sector_central.html ...` (line 141–148); 90m (line 54); concurrency `pipeline-sector-intelligence` cancel-in-progress false (line 38–39).
- `.github/workflows/sentinel.yml:4` — cron `*/30 * * * *`; `runs-on: [self-hosted, macstudio-light]` (line 16); sweep at lines 56–58; `git add data/vector data/coinbase/btc_hourly.parquet site/vector.html site/index.html` (line 59); 8m (line 17); concurrency `sentinel` cancel-in-progress false (line 11).

The remaining weekday crons firing inside the window — each verified via `git show origin/main:.github/workflows/<file>` — listed in priority order (largest artifact-producing impact first):

- `.github/workflows/intraday-fastpath.yml:21` — cron `*/30 11-21 * * 1-5` (US premarket: 11:00–13:30Z); `runs-on: [self-hosted, macstudio-light]` (line 47); VPS-gated OFF (line 54); 15m (line 56); concurrency `intraday-fastpath` cancel-in-progress true (line 31–32).
- `.github/workflows/intraday.yml:15` — cron `35 13-21 * * 1-5`; first fire 13:35Z; writes site/.
- `.github/workflows/live-breadth.yml:31-33` — crons `5,35 13-20`, `*/5 14-20`, `0,5,10,15 21`; first fire 13:05Z.
- `.github/workflows/codex-research.yml:31` — crons `5,35 13-20 * * 1-5`; first fire 13:05Z.
- `.github/workflows/entry-radar-live.yml:71-73` — crons `25,30,35,40,45,50,55 13`, `*/5 14-20`, `0,5,10,15 21`; first fire 13:25Z.
- `.github/workflows/prophet-live.yml:65-67` — same cron pattern as entry-radar-live.
- `.github/workflows/prophet-rescue.yml:43` — cron `40 * * * *`; fires 09:40, 10:40, 11:40, 12:40.
- `.github/workflows/merge-on-green.yml:35` — cron `*/10 * * * *`; sweeper.
- `.github/workflows/research-triage.yml:59` — cron `40 12 * * *`; `ubuntu-latest` (line 103, OFF render path); 20m (line 104).
- `.github/workflows/press-publish.yml:63` — cron `20 13 * * 1-5`; `ubuntu-latest` (line 112, OFF render path); 30m (line 113).
- `.github/workflows/smart-money-13f-census.yml:53-91` — crons `10 12-20 * * 1-5`, `17 6 * * 2-6`; `runs-on: [self-hosted, macstudio]` (line 80); 60m/180m (line 91).
- `.github/workflows/marketing-earnings-wire.yml:70-94` — cron `*/10 11-13,20-22 * * 1-5`; `ubuntu-latest` (line 93, OFF render path); 10m (line 94).
- `.github/workflows/marketing-press-wire.yml:60-62` — cron `25,30,35,40,45,50,55 13`, `*/5 14-20`, `0,5 21`.
- `.github/workflows/marketing-hot-tape.yml:33` — cron `7,37 * * * *` (fires every hour).
- `.github/workflows/marketing-publish.yml:42` — cron `10 1,12,17 * * *`; fires 12:10Z.
- `.github/workflows/marketing-media-backfill.yml:69` — cron `17 1,5,9,13,17,21 * * *`; fires 09:13Z.
- `.github/workflows/smart-money-13f-bulk-reconcile.yml:55` — cron `0 * * * *`; fires 09:00–13:00Z hourly.
- `.github/workflows/smart-money-filings.yml:17` — cron `0 10 * * 3` (Wed 10:00Z).
- `.github/workflows/company-intelligence.yml:23` — cron `20 */2 * * *`; fires 10:20, 12:20Z.
- `.github/workflows/earnings-evidence-graph.yml:10` — cron `17 */3 * * *`; fires 12:17Z.
- `.github/workflows/earnings-public-wire.yml:10` — cron `43 * * * *`.
- `.github/workflows/earnings-story-packets.yml:23` — cron `47 * * * *`.
- `.github/workflows/geo-enrich.yml:7` — cron `17 * * * *`.
- `.github/workflows/integration-baseline.yml:10` — cron `*/30 * * * *`.
- `.github/workflows/research-ingest.yml:47` — cron `*/5 * * * *`.
- `.github/workflows/signal-foundry.yml:57` — cron `0,30 0,1,11-23 * * *`; fires 11:00, 11:30, 12:00, 12:30, 13:00, 13:30Z.
- `.github/workflows/vps-live-heartbeat.yml:8` — cron `17 10 1-5 3,6,9,12 *`.
- `.github/workflows/whitehouse-sentinel.yml:7` — cron `17 13-23/2 * * 1-5`; first fire 13:17Z.
- `.github/workflows/heartbeat.yml:11` — cron `30 14 * * 1-5` (14:30Z, JUST outside the 09:00–13:30Z window — listed only to record its boundary).
- `.github/workflows/data-health.yml:35` — cron `30 13 * * 1-5`; `ubuntu-latest` (line 75, OFF render path); 180m (line 76).
- `.github/workflows/live-quotes.yml:35` — cron `*/5 * * * 1-5`; `ubuntu-latest` (line 61); builds root `quotes.json` (line 131); orphan-branch push to `live-data` (line 155 `git push -f origin HEAD:live-data`); NEVER touches main tree; 15m (line 67); concurrency `live-quotes` cancel-in-progress true (line 31).
- `.github/workflows/btc-live.yml:30` — cron `0 * * * *`; `ubuntu-latest`; VPS-gated OFF (line 44); `git add -f site/live/quotes.json` (line 46) is DISABLED while VPS_LIVE_PRIMARY=true; 8m (line 35); concurrency `btc-live` cancel-in-progress true (line 22).
- `.github/workflows/commodity-sentinel.yml:4` — cron `*/30 * * * *`; `runs-on: [self-hosted, macstudio-light]` (line 16); sweep at lines 56–58; `git add data/commodity data/reflexes/ site/commodities.html` (line 62); commit at line 72.
- `.github/workflows/nightly-liveness.yml:35-37` — crons `0 8`, `0 14`, `0 20 * * *`; watchdog.
- `.github/workflows/nightly-backstop.yml:26-28` — crons `0 1`, `30 3`, `0 6 * * *` (all OUTSIDE the 09:00–13:30Z window — listed only for completeness).
- `.github/workflows/weekly.yml:4` — cron `0 14 * * 6` (OUTSIDE window).
- `.github/workflows/metabolism-dream.yml:24` — cron `0 6 * * 0` (OUTSIDE window).
- `.github/workflows/ci-main-heartbeat.yml:45` — cron `17 */6 * * *`; `ubuntu-latest`; 10m timeouts.
- `.github/workflows/metabolism-*.yml` — 11 cron lines spanning 09:00–12:45Z: agenda :19 `15 9`, build :34 `45 10`, adjudicate :24 `15 10`, verify :27 `15 11`, audit :20 `45 11`, merge :44 `15 12`, cycle :29 `35 *`, heartbeat :28 `45 *`, immune :23 `15 */2`, propose :21 `45 9`, gc :15 `20 7` (OUTSIDE). Research-only, no site/ or data/ writes.
- `.github/workflows/government-revenue-live.yml:11` — cron `37 6 * * *` (OUTSIDE window).

Render lane itself (no scheduled cron; push-triggered only):

- .github/workflows/render.yml:34-50 — `on:` is `workflow_dispatch` + `push.branches: [main]`.
- .github/workflows/render.yml:62-91 — path includes `templates/**`, `scripts/build_aibrief.py` (line 88), `scripts/build_am_edition.py` (line 91).
- .github/workflows/render.yml:823 — `run_py "AI daily brief page (build_aibrief)" scripts.build_aibrief`.
- .github/workflows/render.yml:824 — `run_py "AM edition producer (build_am_edition)" scripts.build_am_edition`.
- .github/workflows/render.yml:936 — `brun reference "market reference page (build_market_reference)" scripts.build_market_reference`.
- .github/workflows/closing-bell.yml:242-247 — standard `run_py` wrapper idiom (label + module + tee to e.log + rc-tagged ::error).
- .github/workflows/closing-bell.yml:303 — closing-bell's `run_py` list.
- .github/workflows/earlyclose.yml:187, 223, 249 — earlyclose's `run_py()` definitions + list.

Existing AM Edition producer invocation in the canonical nightly:

- .github/workflows/daily.yml:4048-4056 — `- name: AI Daily Brief page (build_aibrief)` (line 4048); `python -m scripts.build_aibrief` (line 4051); `- name: AM Edition producer (build_am_edition)` (line 4053); `python -m scripts.build_am_edition` (line 4056).
- .github/workflows/daily.yml:638 — nightly data commit step `git add data/ site/qledger/` (stages data/regime, data/neuralweb/*, data/release_forecast/* onto main).
- scripts/build_am_edition.py:715-748 — `_feasibility()` returns three outcomes: BLOCKED (no source_as_of, line 722–728), BLOCKED (parse error, line 733–739), AVAILABLE (line 743), or DEGRADED (line 744–748); NEVER broken, always returns 0 (line 848).
- scripts/build_am_edition.py:751 — `def build_payload(site: Path, data_dir: Path, *, now: datetime | None = None) -> dict`.
- scripts/build_am_edition.py:71 — `_RELEASE_TITLES = {...}` opens here.
- scripts/build_am_edition.py:367-470 — `_tape_block` reads `site/live/quotes.json`.
- scripts/build_am_edition.py:471-506 — `_owner_state_block` reads `data/market_state/latest.json`.
- scripts/build_am_edition.py:507-557 — `_regime_block` reads `data/regime/latest.json`.
- scripts/build_am_edition.py:558-633 — `_plane_block` reads `data/neuralweb/market_plane.json`.
- scripts/build_am_edition.py:634-680 — `_calendar_block` reads `data/release_forecast/latest.json`; `release_date` filter at lines 656–660.
- scripts/build_am_edition.py:681-748 — `_prior_brief_ref_block` reads `site/master_brief.json`; title_en="Yesterday's brief" / title_zh="昨日简报" hard-coded at line 681.

## §2 Owner-artifact census (DEC §3.1 block list)

Each row: block | artifact path | producer script:line | writer lane + cron | timestamp key (verified via `git show origin/main:<path>`) | expected currentness at 11:30Z on a weekday (derived from the writer's cron) | typed state at 11:30Z today.

- Block 1 (clock) — artifact: payload `generated_at` (in-script stamp at build time, scripts/build_am_edition.py:763); producer scripts/build_am_edition.py:328-365 (`_session_clock_block`) + scripts/build_am_edition.py:751 (`build_payload`); writer .github/workflows/daily.yml:4056 at 22:30/23:30Z (post-RTH only); timestamp `generated_at` (no top-level artifact — derived in-script); expected currentness at 11:30Z weekday = ~13h stale (last fired 22:30Z prior day); typed state STALE_WITH_LAST_KNOWN.
- Block 2 (tape) — artifact: `site/live/quotes.json` (in-tree) OR `quotes.json` on the `live-data` orphan branch; producer scripts/build_am_edition.py:367-470 (`_tape_block`) + scripts/build_live_quotes.py:1; writers .github/workflows/intraday-fastpath.yml:21 (*/30 11-21, VPS-gated OFF, line 54), .github/workflows/btc-live.yml:30 (hourly, VPS-gated OFF, line 44), .github/workflows/live-quotes.yml:35 (*/5 weekdays, NO gate, builds root `quotes.json` at line 131, force-pushes to `live-data` orphan branch at line 155); timestamp `asof` (top-level on `live-data`'s `quotes.json`); expected currentness at 11:30Z weekday from `live-data` ≤ ~5 min if live-quotes runs, else UNAVAILABLE; in-tree `site/live/quotes.json` is 58+ days stale per `git log -1 origin/main -- site/live/quotes.json` (last commit `9aae769b3e9 Fri Sep 18 23:55:19 2026`); typed state STALE_WITH_LAST_KNOWN if reading in-tree, CURRENT if reading from `live-data` branch.
- Block 3 (rates/dollar/credit/commodity/intl) — four artifacts, each its own row:
  - `data/regime/latest.json` — timestamp `asof` (top-level); producer scripts/build_am_edition.py:507-557 (`_regime_block`); writer daily.yml:638 at 22:30/23:30Z; expected currentness at 11:30Z = ~13h stale; state STALE_WITH_LAST_KNOWN.
  - `data/neuralweb/market_plane.json` — timestamp `asof`; producer scripts/build_am_edition.py:558-633 (`_plane_block`); writer daily.yml:638; expected currentness at 11:30Z = ~13h stale; state STALE_WITH_LAST_KNOWN.
  - `data/neuralweb/liquidity_plumbing.json` — timestamp `asof`; producer scripts/build_liquidity_plumbing (run at .github/workflows/daily.yml:4212); writer daily.yml:638; expected currentness at 11:30Z = ~38h stale (last fired on prior calendar day); state STALE_WITH_LAST_KNOWN.
  - `data/neuralweb/world_state.json` — NO top-level `asof` (verified via `git show origin/main:data/neuralweb/world_state.json`); nested `verdict.asof`, `alerts.asof`, `rotation_events.as_of`; producer engine.world_state; writer daily.yml:638; expected currentness at 11:30Z = ~13h stale; state STALE_WITH_LAST_KNOWN.
- Block 4 (calendar) — `data/release_forecast/latest.json` + `data/release_forecast/scoreboard.json`; producer scripts/build_am_edition.py:634-680 (`_calendar_block`) reading `upcoming[]`; `release_date` filter at lines 656–660; writer daily.yml:638 at 22:30/23:30Z; timestamp `asof` (top-level on both); expected currentness at 11:30Z weekday = ~13h stale BUT content is date-keyed so today's rows are CURRENT once the calendar advances; typed state CURRENT for `release_date == today` rows, otherwise STALE_WITH_LAST_KNOWN.
- Block 5 (disagreement/attention) — reuses `data/neuralweb/world_state.json` (Block 3 row 4); reads `verdict.asof` (nested); `contradiction_count` + `stale` machine fields not shipped; expected currentness at 11:30Z weekday = ~13h stale; state STALE_WITH_LAST_KNOWN.
- Block 6 (research watch) — `data/master_brain/track_record.json` (top-level `scored_total`, `calibration_note`, `calibration_note_zh` per scripts/build_aibrief.py:373-405) + `data/master_brain/theses.jsonl` (per-row `logged_at`, `state_asof`, `subject`, `lean`, `horizon_d`, `falsifier`, `check_by` per scripts/build_aibrief.py:405-440); readers scripts/build_aibrief.py:347 (`_gather_record_panel`), :373 (`track_record`), :405 (`theses.jsonl`); writers engine.master_brain_scorer (.github/workflows/daily.yml:3528-3536) + engine.master_brain (.github/workflows/daily.yml:3541-3571); NO pre-open update lane; AM producer does NOT currently read theses/track_record; expected currentness at 11:30Z weekday = ~13h stale; state STALE_WITH_LAST_KNOWN.
- Block 7 (prior-close brief) — `site/master_brief.json`; reader scripts/build_aibrief.py:90-99 (`_load_briefs`); producer engine.master_brain (.github/workflows/daily.yml:3541-3571, post-RTH); timestamp `generated_at` (top-level), `state_asof` (top-level), `refresh_days` (top-level), nested `zh` dict with `tldr`/`summary`/`regime_read`/`conflicts`/`rotation_check`/`transmission`/`watch_items` (NO top-level `en`, NO top-level `as_of`); expected currentness at 11:30Z weekday = ~13h stale (last fired 22:30Z prior day, `refresh_days=1`); state STALE_WITH_LAST_KNOWN; `_prior_brief_ref_block` at scripts/build_am_edition.py:681 hard-codes title_en="Yesterday's brief" / title_zh="昨日简报". The handoff danger-area at agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:146 states the principle: "The prior-close LLM brief can be mistaken for live morning analysis unless visually and semantically separated."
- Block 8 (links/Reference) — `site/reference.html`; producer scripts.build_market_reference; writer .github/workflows/render.yml:936 (`brun reference`); nav `templates/_navlinks.html.j2:276` (`reference.html` only — aibrief.html has NO nav entry, verified via `grep -in "aibrief" templates/_navlinks.html.j2` = 0); stable anchor `templates/reference.html.j2:468` (`<article class="rf-e" id="{{ e.id }}">`); deep-link `templates/reference.html.j2:474`; timestamp NONE; expected currentness at 11:30Z weekday = CURRENT whenever a render.yml sweep lands; state CURRENT.

Served side artifacts the morning reader needs but §0/§5 do not name (verified via `git ls-tree -r --name-only origin/main site`):

- `site/china_brief.json` (schema = master_brief, lens china) — `generated_at` (top-level), `state_asof`, nested `zh`; writer .github/workflows/daily.yml:3541-3571 at 22:30/23:30Z; state STALE_WITH_LAST_KNOWN.
- `site/btc_brief.json` (schema = master_brief, lens btc) — last `generated_at: 2026-09-23T09:24:17Z` (~26h stale); writer daily.yml:3541-3571; state STALE_WITH_LAST_KNOWN.
- `site/options_intel_brief.json` — DIFFERENT timestamp family: `built_at_utc` (top-level), `as_of_session`, `oi_counted_date`, `pending_session`; producer scripts.build_options_intel_brief; options lane not measured in this packet; state NOT_COVERED (flag for MOR-2b).
- `site/neuralwebdata/market_plane.json` + `site/neuralwebdata/liquidity_plumbing.json` — served mirrors of `data/neuralweb/*`; timestamp `asof` (mirrors data-side); state CURRENT only if a render swept within freshness budget.
- `templates/_aibrief_body.html.j2` — server-side rendered lens-brief body (templates/aibrief.js:3-4 comment "SERVER-rendered into the page by the shared Jinja macro"); producer scripts/build_aibrief.py reads the three `*_brief.json` files; timestamp NONE (build-time snapshot).

Track-record reads used by `scripts/build_aibrief.py`:

- scripts/build_aibrief.py:101 `_gather_context_strip` (Panel A) reads data/regime/latest.json + data/neuralweb/{market_plane,liquidity_plumbing,world_state}.json.
- scripts/build_aibrief.py:209 `_gather_forward_panel` (Panel B) reads data/release_forecast/latest.json + data/master_brain/track_record.json.
- scripts/build_aibrief.py:347 `_gather_record_panel` (Panel C) reads data/master_brain/track_record.json + data/master_brain/theses.jsonl.
- scripts/build_aibrief.py:466 `main()` entrypoint; :373 opens `track_record.json`; :405 opens `theses.jsonl`.

Release radar `data/release_forecast/latest.json` `upcoming[]`:

- scripts/build_am_edition.py:656-660 reads `release_date` (NEVER raw `date` slug); :71-94 `_RELEASE_TITLES` whitelist.

## §3 The aibrief surface today

Section inventory by h1/h2 (line numbers verified via `git show origin/main:templates/aibrief.html.j2`):

- templates/aibrief.html.j2:99 — `AI Daily Brief` h1.
- templates/aibrief.html.j2:111 — `Right now` h2 (context strip).
- templates/aibrief.html.j2:122-151 — context-strip rows: Regime / Signals / Money / AI review.
- templates/aibrief.html.j2:165 — `What's ahead` h2.
- templates/aibrief.html.j2:178-181 — fwd-list of dated events.
- templates/aibrief.html.j2:194-197 — three toggle tabs Macro / China & Hong Kong / Bitcoin.
- templates/aibrief.html.j2:207 — `Macro · cross-asset synthesis` h2.
- templates/aibrief.html.j2:218 — `China & Hong Kong synthesis` h2.
- templates/aibrief.html.j2:229 — `Bitcoin synthesis` h2.
- templates/aibrief.html.j2:243 — `The brief's own record` h2.
- templates/aibrief.html.j2:286 — `Overnight deliberation` h2 (Panel D, client-side).
- templates/aibrief.js:3-4 — comment notes lens-brief bodies are SERVER-rendered via `templates/_aibrief_body.html.j2`.
- templates/aibrief.js:23 — `fetch("neuralweb/cortex_memo.json?_=" + Date.now())` is the only fetch target.

Build step + nav entry + asset stamps:

- .github/workflows/daily.yml:4048-4056 — `AI Daily Brief page (build_aibrief)` (4048–4052) + `AM Edition producer (build_am_edition)` (4053–4056).
- templates/_navlinks.html.j2:276 — `reference.html` nav entry (verified via `git show origin/main:templates/_navlinks.html.j2 | sed -n '276p'` → `Market Reference` / `市场参考` link).
- templates/_navlinks.html.j2 — there is NO `aibrief.html` / `AI Daily Brief` / `AI每日简报` nav entry — `grep -in "aibrief\|AI Daily Brief\|AI每日简报" templates/_navlinks.html.j2` returns 0 matches. This absence is a material MOR-2b fact: a new morning surface reachable only via direct URL is not a lawful morning orientation, and MOR-2b must either add a nav entry or anchor the morning page off an existing nav-reachable surface (e.g. macro.html → "Today's brief").
- templates/aibrief.html.j2 — NO inline `?v=` stamps; stamps applied by `scripts.optimize_assets` (render.yml:823 sweep, sector-intelligence.yml:134-136 sweep, asia-close.yml:827-833 sweep, sentinel.yml:56-58 sweep).

Existing CSS class families the page composes (so MOR-2b can extend, not fork):

- templates/aibrief.html.j2:97-286 — `panel` (top-level container).
- templates/aibrief.html.j2:120-151 — `ctx-strip` / `ctx-row` / `ctx-label` / `ctx-chip`.
- templates/aibrief.html.j2:151 — `cortex-ok` / `cortex-deg` modifiers.
- templates/aibrief.html.j2:178-181 — `fwd-list` / `fwd-date`.
- templates/aibrief.html.j2:194-197 — `brief-tabs` / `brief-tab-btn`.
- templates/aibrief.html.j2:206-228 — `ai-brief` / `brief-tab`.
- templates/aibrief.html.j2:252 — `record-cal`.
- templates/aibrief.html.j2:266 — `open-lean`.
- templates/aibrief.html.j2:5,124-126 — `l-en` / `l-zh` bilingual pair wrappers.
- templates/aibrief.html.j2 — there is NO `mq-` / `mx-` family in this template; those tokens belong to market-board surfaces.

## §4 Reference continuation

Stable id/anchor pattern:

- templates/reference.html.j2:468 — `<article class="rf-e" id="{{ e.id }}" data-kind data-family data-initial data-search>`.
- templates/reference.html.j2:474 — `<a class="rf-sum" href="#{{ e.id }}">` (deep-link).
- config/market_reference.yml — schema `mastermind.market_reference/v1`, 46 entries (24 indicator / 22 glossary).
- config/market_reference.yml:1813 — `coverage_exceptions` key opens here (file ends at 1843).

DEC §3.1 block → existing / missing reference ids:

- block 1 (clock): `market-regime` (existing), `market-state-score` (existing).
- block 2 (since-prior-close): `multi-timeframe-tape` (existing); SPY/QQQ/^RUT coverage lives in templates/reference.html.j2:468 stable anchors.
- block 3 (rates/dollar/credit/commodity/intl): `liquidity-state`, `real-rates`, `breakevens`, `yield-curve`, `credit-spread`, `high-yield-spread`, `dollar-index` (all existing); `commodity-sentinel` is NOT yet in the registry (a MOR-2b missing row).
- block 4 (calendar): `high-impact-event`, `surprise-skew`, `rebalance-flow`, `sue-earnings-surprise` (all existing).
- block 5 (disagreement/attention): `signal-divergence`, `risk-radar` (existing).
- block 6 (research watch): `stance-ladder`, `confidence-tier`, `buy-readiness` (existing); `watch-conditions` is NOT yet in the registry (missing).
- block 7 (prior-close brief): `market-regime`, `evidence-trend`, `evidence-risk-appetite` (all existing).
- block 8 (links): every entry above plus templates/_navlinks.html.j2:276.

Existing `coverage_exceptions` declarations (config/market_reference.yml:1813-end):

- Prophet Stock Signals Board — see_ids: alpha-chip, buy-readiness, entry-timing, insider-buy.
- Sector Act-Now Board — see_ids: sector-heat, leadership-rotation.
- Regime Badge — covered_by market-regime.
- Posture Chip — covered_by posture-dial.

## §5 Recommended MOR-2b decomposition

```
SCHEDULE OWNER: .github/workflows/sector-intelligence.yml (cite: lines 12, 53, 134-136)

INSERTION POINT: new step inside the rebuild job AFTER preflight (line 95) and BEFORE publish (line 117),
  gated on `github.event.schedule == '12 * * 1-5'`; preflight (lines 97-105) left untouched.
  cite: .github/workflows/closing-bell.yml:242-247, 303 ; .github/workflows/earlyclose.yml:187, 223, 249
  cite: .github/workflows/sector-intelligence.yml:95, 117

MINIMUM SOURCE SET + TYPED-STATE MAP (per block, per §2):
  b1 clock:        generated_at                              STALE_WITH_LAST_KNOWN
  b2 tape:         live-data/quotes.json (CURRENT) vs site/live/quotes.json (STALE 58+d)
  b3 context:      data/regime + data/neuralweb/*            STALE_WITH_LAST_KNOWN
  b4 calendar:     data/release_forecast/latest.json        CURRENT (date-keyed rows)
  b5 disagreement: data/neuralweb/world_state.json           STALE_WITH_LAST_KNOWN
  b6 watch:        NEW display over data/master_brain/* unchanged
  b7 prior brief:  site/master_brief.json                    STALE (visibly older)
  b8 links:        templates/reference.html + templates/_navlinks.html.j2:276

FILES MOR-2b MAY TOUCH (DEC §6, verbatim):
  scripts/build_aibrief.py · templates/aibrief.html.j2 · aibrief.js + paired site asset ·
  .github/workflows/sector-intelligence.yml · focused tests (per DEC §6)

EVIDENCE MATRIX (DEC §10.5) — 8 screenshots minimum:
  desktop 1440 × {dark, light} × {EN, ZH} ; mobile 390 × {dark, light} × {EN, ZH}

PRIOR-CLOSE BRIEF VISIBLY OLDER (handoff:146) — cite: agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:146
  Block 7 surfaces site/master_brief.json under a separate h2 with its own timestamp pill;
  never share visual chrome with the live current blocks. The "Yesterday's brief / 昨日简报"
  copy lives at scripts/build_am_edition.py:681 (NOT in the handoff).

DO-NOT LIST (handoff:130-138, verbatim) — cite: agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:130-138
  - "Do not create a second AI brief engine, LLM prompt family, model quota lane, brief JSON store, or general morning truth plane."
  - "Do not publish docs/site_semantics raw or expose internal repository paths, model/provider names, DNR labels, scoring keys, or operator instructions."
  - "Do not turn config/market_reference.yml into live value storage, a semantic database, an embedding index, or an authority source."
  - "Do not combine MOR-1, MOR-2, and MOR-3 into one mega-PR merely to claim three coarse rows at once."
  - "Do not call a rebuilt prior-close page a current AM Edition without source-currentness proof."
  - "Do not let definitions, AI prose, or reference links originate rank, score, gate, sizing, ENTRY_OPEN, Prophet, portfolio, or trade authority."
  - "Do not create a new workflow family when an existing scheduler/build owner can lawfully host the morning projection."
  - "Do not infer Project-Sol assignment from an idle browser, account label, GitHub packet, Slack delivery, or Linear state."
  - "Do not auto-start a worker, successor wave, or production mutation from this records carrier."
```

— end of MOR-2a packet. Authority ceiling: `display_only`. No code, template, workflow, data, site, config, or agentos file modified by this commit. Cross-session pointers: research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md:112 (chairman override 2026-09-06); agentos/decisions/DEC-MARKET-ONTOLOGY-MARKET-ORIENTATION-PROJECTION-2026-08-30.md (frozen authority); agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:93 (the load-bearing open question this packet closes).
