---
workstream: WS:MARKET-OS
operation: marketontology-f01f13-market-orientation-projection-20260830-sol-001
packet: A-F01-MOR-2a
chairman_override: 2026-09-06 (Meta-CEO A seat owns F01/F13 Market Orientation per research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md:112)
frozen_authority: DEC:MARKET-ONTOLOGY-MARKET-ORIENTATION-PROJECTION-2026-08-30
handoff_unresolved: "The exact lawful premarket schedule and minimum source-currentness set require Project-Sol archaeology." (agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:91)
recorded_by: claude/mo-a-3-a-f01-mor2-premarket-archaeology-20260924
recorded_at: 2026-09-24
scope: RECORDS ONLY — no code, no template, no workflow, no data, no site, no config, no agentos edit
---

# MOR-2 premarket archaeology — facts the MOR-2b build packet needs

## §0 Verdict (≤8 lines)

The only weekday workflow that fires 09:00–13:30Z AND already executes the full render chain on a render-path runner is `.github/workflows/sector-intelligence.yml` (cron `15 3,12,17,22 * * 1-5` at line 12; `runs-on: render-linux` at line 53; runs the inject_data_base + externalize_css + optimize_assets sweep before pushing site/, lines 117–123).
The minimum current source set at 11:30Z (07:30 ET) is `site/live/quotes.json` (intraday-fastpath.yml */30 11-21, line 21) — everything else is either STALE_WITH_LAST_KNOWN (data/regime, data/neuralweb/*, data/release_forecast all commit at 22:30/23:30Z via daily.yml) or NOT_YET_OPEN (US RTH, opens 13:30Z = 09:30 ET).
MOR-2b's lawful insertion point is one `run_py "AM Edition producer (build_am_edition)" scripts.build_am_edition` call inside that job's rebuild step, gated on the weekday 12:15Z slot.
Bounded dependency: `scripts/build_am_edition.py:1-852` already runs in `daily.yml:4053-4056` at 22:30/23:30Z (post-US-close); the same producer can be invoked at 12:15Z without modification because its `_feasibility()` at scripts/build_am_edition.py:716-742 classifies a 12:15Z invocation as AVAILABLE (live tape `asof` ≥ prior close cut) or DEGRADED (older), never broken.
No new workflow family; no new LLM call; no rank/score/size.

## §1 Workflow census (every weekday cron firing 09:00–13:30Z)

Each line below is one `file:line` cite, verified via `git show origin/main:.github/workflows/<file>`.

- .github/workflows/intraday-fastpath.yml:21 — cron `*/30 11-21 * * 1-5` (extended to 11:00Z for US premarket per the file's own comment).
- .github/workflows/intraday-fastpath.yml:23 — cron `*/30 1-8 * * 1-5` HKEX window.
- .github/workflows/intraday-fastpath.yml:47-56 — runs-on `[self-hosted, macstudio-light]`; timeout 15m; concurrency `intraday-fastpath` cancel-in-progress true.
- .github/workflows/intraday-fastpath.yml:78-83 — regime self-heal is RTH-gated; UTC < 13 skips.
- .github/workflows/sector-intelligence.yml:12 — cron `15 3,12,17,22 * * 1-5` (the 12:15Z weekday slot is the only 09:00–13:30Z schedule on a render-path runner).
- .github/workflows/sector-intelligence.yml:40-54 — runs-on `render-linux`; timeout 90m; concurrency `pipeline-sector-intelligence` cancel-in-progress false.
- .github/workflows/sector-intelligence.yml:117-123 — full sweep inject_data_base + externalize_css + optimize_assets before publish.
- .github/workflows/research-triage.yml:59 — cron `40 12 * * *`; runs-on ubuntu-latest (line 103, OFF render path); timeout 20m (line 104).
- .github/workflows/press-publish.yml:63 — cron `20 13 * * 1-5`; runs-on ubuntu-latest (line 112, OFF render path); timeout 30m (line 113).
- .github/workflows/smart-money-13f-census.yml:53-91 — crons `10 12-20 * * 1-5` + `17 6 * * 2-6`; runs-on `[self-hosted, macstudio]` (line 80); timeout 60m/180m (line 91).
- .github/workflows/marketing-earnings-wire.yml:70-94 — cron `*/10 11-13,20-22 * * 1-5`; runs-on ubuntu-latest (line 93, OFF render path); timeout 10m (line 94).
- .github/workflows/metabolism-agenda.yml:19 — cron `15 9 * * *`.
- .github/workflows/metabolism-build.yml:34 — cron `45 10 * * *`.
- .github/workflows/metabolism-adjudicate.yml:24 — cron `15 10 * * *`.
- .github/workflows/metabolism-verify.yml:27 — cron `15 11 * * *`.
- .github/workflows/metabolism-audit.yml:20 — cron `45 11 * * *`.
- .github/workflows/metabolism-merge.yml:44 — cron `15 12 * * *`.
- .github/workflows/metabolism-cycle.yml:29 — cron `35 * * * *`.
- .github/workflows/metabolism-heartbeat.yml:28 — cron `45 * * * *`.
- .github/workflows/metabolism-immune.yml:23 — cron `15 */2 * * *`.
- .github/workflows/metabolism-propose.yml:21 — cron `45 9 * * *`.
- .github/workflows/metabolism-gc.yml:15 — cron `20 7 * * *`.
- .github/workflows/nightly-liveness.yml:35-37 — crons `0 8`, `0 14`, `0 20 * * *` watchdog.
- .github/workflows/live-quotes.yml:35 — cron `*/5 * * * 1-5`; ubuntu-latest (line 61); force-adds `site/live/quotes.json` (line 67) onto `live-data` branch.
- .github/workflows/btc-live.yml:30 — cron `0 * * * *`; force-adds `site/live/quotes.json` hourly (line 67).
- .github/workflows/commodity-sentinel.yml:4 — cron `*/30 * * * *`; `[self-hosted, macstudio-light]` (line 16); sweep on shock only (lines 67-70); stages `data/commodity + site/commodities.html` (line 73).
- .github/workflows/data-health.yml:35 — cron `30 13 * * *`; ubuntu-latest (line 75); timeout 180m (line 76).

Render lane itself (no scheduled cron; push-triggered only):

- .github/workflows/render.yml:34-50 — `on:` is `workflow_dispatch` + `push.branches: [main]`.
- .github/workflows/render.yml:62-91 — path includes `templates/**`, `scripts/build_aibrief.py` (line 88), `scripts/build_am_edition.py` (line 91).
- .github/workflows/render.yml:823 — sweep `run_py "AM edition producer (build_am_edition)" scripts.build_am_edition`.
- .github/workflows/closing-bell.yml:242-247 — standard `run_py` wrapper idiom (label + module + tee to e.log + rc-tagged ::error).
- .github/workflows/closing-bell.yml:303 — closing-bell's `run_py` list.
- .github/workflows/earlyclose.yml:204-209 — parallel `run_py` wrapper.
- .github/workflows/earlyclose.yml:249 — earlyclose's `run_py` list.

Existing AM Edition producer invocation in the canonical nightly:

- .github/workflows/daily.yml:4048-4056 — `- name: AI Daily Brief page (build_aibrief)` (line 4048); `python -m scripts.build_aibrief` (line 4052); `- name: AM Edition producer (build_am_edition)` (lines 4053-4056).
- scripts/build_am_edition.py:716-742 — `_feasibility()` classifies 12:15Z invocation as AVAILABLE / DEGRADED, never broken.
- scripts/build_am_edition.py:786-792 — `build_payload` entrypoint takes explicit `now`.
- scripts/build_am_edition.py:834 — main returns 0 on ANY error (additive, never breaks the site build).

## §2 Owner-artifact census (DEC §3.1 block list)

Each row: block, producer cite(s), timestamp key (verified against `git show origin/main:<path>`), typed state at 11:30Z weekday.

- Block 1 (clock) — producer scripts/build_am_edition.py:328-365 (`_session_clock_block`) + scripts/build_am_edition.py:786-792 (`build_payload`); writer .github/workflows/daily.yml:4056 at 22:30/23:30Z; timestamp `generated_at` (block-level); state CURRENT.
- Block 2 (tape) — producer scripts/build_am_edition.py:367-470 (`_tape_block`) + scripts/build_live_quotes.py:1; writers .github/workflows/intraday-fastpath.yml:21 (*/30 11-21), .github/workflows/live-quotes.yml:67 (*/5 force-add), .github/workflows/btc-live.yml:67 (hourly force-add); timestamp `asof` (top-level on site/live/quotes.json); state CURRENT.
- Block 3 (rates/dollar/credit/commodity/intl) — artifacts data/regime/latest.json + data/neuralweb/market_plane.json + data/neuralweb/liquidity_plumbing.json + data/neuralweb/world_state.json (all committed by .github/workflows/daily.yml:4056); producers scripts/build_am_edition.py:472-502 (`_owner_state_block`) + scripts/build_am_edition.py:507-557 (`_regime_block`) + scripts/build_am_edition.py:562-626 (`_plane_block`); timestamp `asof` (top-level on regime/market_plane/liquidity_plumbing); nested `verdict.asof`, `alerts.asof`, `rotation_events.as_of` on world_state.json (NO top-level `asof`); state STALE_WITH_LAST_KNOWN (14–18h stale).
- Block 4 (calendar) — artifacts data/release_forecast/latest.json + data/release_forecast/scoreboard.json (committed by .github/workflows/daily.yml:4056); producer scripts/build_am_edition.py:628-686 (`_calendar_block`) reading `upcoming[]`; scripts/build_am_edition.py:660-670 filter uses `release_date` (NOT raw `date` slug); timestamp `asof` (top-level on both); state CURRENT (date-keyed).
- Block 5 (disagreement/attention) — artifact data/neuralweb/world_state.json; producer scripts/build_am_edition.py:562-626 (`_plane_block`); timestamp `verdict.asof` (nested); `contradiction_count` + `stale` machine fields not shipped; state STALE_WITH_LAST_KNOWN.
- Block 6 (research watch) — artifacts data/master_brain/track_record.json (top-level `as_of`) + data/master_brain/theses.jsonl (per-row `logged_at` + `state_asof`); readers scripts/build_aibrief.py:347 (entrypoint) + scripts/build_aibrief.py:373 (track_record) + scripts/build_aibrief.py:405 (theses.jsonl) — NO pre-open update lane; AM producer does NOT currently read theses/track_record; state STALE_WITH_LAST_KNOWN.
- Block 7 (prior-close brief) — artifact site/master_brief.json (committed by master_brain via daily.yml post-RTH); reader scripts/build_aibrief.py:90-99 (`_load_briefs`); producer engine/master_brain.py; timestamp `generated_at` (top-level); also `state_asof` per block; state CURRENT but visibly older (~13–17h old); MUST be labelled "Yesterday's brief / 昨日简报" per agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:146.
- Block 8 (links/Reference) — nav templates/_navlinks.html.j2:276 (`reference.html`); served site/reference.html; producer scripts/build_market_reference.py; stable anchor templates/reference.html.j2:468 (`<article class="rf-e" id="{{ e.id }}">`); writer .github/workflows/render.yml:823 (`run_py "...(build_market_reference)"`); timestamp NONE (commit-time public copy); state CURRENT.

Asia-close outputs a U.S. morning reader wants:

- .github/workflows/asia-close.yml:22-27 — crons `0 6` through `15 11 * * *`; backstop `15 11 * * *` (line 27) is the latest asia-close slot before 13:30Z.
- .github/workflows/asia-close.yml:47 — timeout 60m (collect); .github/workflows/asia-close.yml:191 — timeout 165m (builds).
- .github/workflows/asia-close.yml:222-228 — restores `data/china_breadth/_closes_cache.parquet` + `data/hk_breadth/_closes_cache.parquet`.
- .github/workflows/asia-close.yml:340 — `python -m scripts.build_china`.

Track-record reads used by `scripts/build_aibrief.py`:

- scripts/build_aibrief.py:347-434 — `_gather_record_panel` covers track_record + theses.
- scripts/build_aibrief.py:373 — opens `data/master_brain/track_record.json`; scripts/build_aibrief.py:405 — opens `data/master_brain/theses.jsonl`.

Release radar `data/release_forecast/latest.json` `upcoming[]`:

- scripts/build_am_edition.py:660-670 — reads `release_date` field (NEVER raw `date` slug).
- scripts/build_am_edition.py:64-94 — `_RELEASE_TITLES` whitelist for plain-word display copy.

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
- templates/aibrief.js:7 — comment notes brief bodies are SERVER-rendered via `templates/_aibrief_body.html.j2`.
- templates/aibrief.js:24 — `fetch("neuralweb/cortex_memo.json?_=" + Date.now())` is the only fetch target.

Build step + nav entry + asset stamps:

- .github/workflows/daily.yml:4048-4056 — `AI Daily Brief page (build_aibrief)` + `AM Edition producer (build_am_edition)`.
- templates/_navlinks.html.j2:276 — `reference.html` nav entry.
- templates/aibrief.html.j2 — NO inline `?v=` stamps; stamps applied by `scripts.optimize_assets` (render.yml:823 sweep, sector-intelligence.yml:117-123 sweep, commodity-sentinel.yml:67-70 sweep).

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
- config/market_reference.yml:1810-1842 — `coverage_exceptions` block enumerating surfaces covered elsewhere.

DEC §3.1 block → existing / missing reference ids:

- block 1 (clock): `market-regime` (existing), `market-state-score` (existing).
- block 2 (since-prior-close): `multi-timeframe-tape` (existing); SPY/QQQ/^RUT coverage lives in templates/reference.html.j2:468 stable anchors.
- block 3 (rates/dollar/credit/commodity/intl): `liquidity-state`, `real-rates`, `breakevens`, `yield-curve`, `credit-spread`, `high-yield-spread`, `dollar-index` (all existing); `commodity-sentinel` is NOT yet in the registry (a MOR-2b missing row).
- block 4 (calendar): `high-impact-event`, `surprise-skew`, `rebalance-flow`, `sue-earnings-surprise` (all existing).
- block 5 (disagreement/attention): `signal-divergence`, `risk-radar` (existing).
- block 6 (research watch): `stance-ladder`, `confidence-tier`, `buy-readiness` (existing); `watch-conditions` is NOT yet in the registry (missing).
- block 7 (prior-close brief): `market-regime`, `evidence-trend`, `evidence-risk-appetite` (all existing).
- block 8 (links): every entry above plus templates/_navlinks.html.j2:276.

Existing `coverage_exceptions` declarations (config/market_reference.yml:1810-1842):

- Prophet Stock Signals Board — see_ids: alpha-chip, buy-readiness, entry-timing, insider-buy.
- Sector Act-Now Board — see_ids: sector-heat, leadership-rotation.
- Regime Badge — covered_by market-regime.
- Posture Chip — covered_by posture-dial.

## §5 Recommended MOR-2b decomposition

```
SCHEDULE OWNER
  .github/workflows/sector-intelligence.yml
  cite: .github/workflows/sector-intelligence.yml:12
  cite: .github/workflows/sector-intelligence.yml:53
  cite: .github/workflows/sector-intelligence.yml:117-123

INSERTION POINT
  .github/workflows/sector-intelligence.yml:96-110 (rebuild job)
  one run_py call between preflight and the publish sweep:
    - name: AM Edition producer (build_am_edition)
      if: steps.preflight.outputs.skip != 'true' && github.event.schedule == '15 12 * * 1-5'
      run: python -m scripts.build_am_edition
  followed by `git add site/am_edition.html site/am_edition.json` in the publish step.
  cite: .github/workflows/closing-bell.yml:242-247
  cite: .github/workflows/earlyclose.yml:204-209

MINIMUM SOURCE SET + TYPED-STATE MAP (per block, per §2)
  block 1 (clock):         generated_at            CURRENT
  block 2 (tape):          site/live/quotes.json   CURRENT     cite scripts/build_am_edition.py:367-470
  block 3 (context):       data/regime + data/neuralweb/*  STALE_WITH_LAST_KNOWN  cite .github/workflows/daily.yml:4056
  block 4 (calendar):      data/release_forecast/latest.json  CURRENT  cite scripts/build_am_edition.py:628-686
  block 5 (disagreement):  data/neuralweb/world_state.json   STALE_WITH_LAST_KNOWN  cite scripts/build_am_edition.py:562-626
  block 6 (watch):         NEW — display over data/master_brain/* unchanged  cite scripts/build_aibrief.py:347
  block 7 (prior brief):   site/master_brief.json  CURRENT but visibly older  cite scripts/build_aibrief.py:90-99
  block 8 (links):         templates/reference.html + templates/_navlinks.html.j2:276  cite templates/reference.html.j2:468

FILES MOR-2b MAY TOUCH (DEC §6 candidate paths, verbatim):
  scripts/build_aibrief.py        owner-adjacent pure view helper only if necessary
  templates/aibrief.html.j2       shared brief partial only if shared behavior truly changes
  aibrief.js + paired site asset  only if interaction requires it
  .github/workflows/sector-intelligence.yml   the schedule owner insertion point
  focused tests (per DEC §6)

EVIDENCE MATRIX (DEC §10.5) — owed before MOR-2b can claim production proof:
  desktop 1440 × dark × EN ; desktop 1440 × dark × ZH
  desktop 1440 × light × EN ; desktop 1440 × light × ZH
  mobile  390  × dark × EN ; mobile  390  × dark × ZH
  mobile  390  × light × EN ; mobile  390  × light × ZH
  (4 × 2 = 8 screenshots minimum)

PRIOR-CLOSE BRIEF VISIBLY OLDER (handoff:146) — implementation requirement:
  cite: agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:146
  block 7 must surface site/master_brief.json under a separate "Yesterday's brief / 昨日简报"
  h2 with its own timestamp pill; NEVER share visual chrome with the live current blocks.

DO-NOT LIST (handoff:130-146, verbatim):
  cite: agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:130-146
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

— end of MOR-2a packet. Authority ceiling: `display_only`. No code, template, workflow, data, site, config, or agentos file modified by this commit. Cross-session pointers: research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md:112 (chairman override 2026-09-06); agentos/decisions/DEC-MARKET-ONTOLOGY-MARKET-ORIENTATION-PROJECTION-2026-08-30.md (frozen authority); agentos/handoffs/MARKET-ONTOLOGY-F01F13-MARKET-ORIENTATION-PROJECT-SOL-2026-08-30.md:91 (the load-bearing open question this packet closes).