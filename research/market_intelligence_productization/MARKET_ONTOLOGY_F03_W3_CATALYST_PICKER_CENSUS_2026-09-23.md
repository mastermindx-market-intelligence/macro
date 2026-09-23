---
title: "[MO-A3] A-F03-W3-0 — catalyst→exposure→structure (Catalyst Picker) census"
packet: A-F03-W3-0 (evidence only; not for merge)
seat: Meta-CEO A
date: 2026-09-23
authority: Chairman override 09-06 — Meta-CEO A owns this program; no Sol hold and no merge-barrier token appears in this packet
ledger_basis: research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv rows MO-DELTA-033, MO-DELTA-035, MO-PAID-070, MO-PAID-076
---

## §0 State of the chain today

Two F03 substrates are on `origin/main` (`d90de2d0c9`): `engine/options_catalyst_link.py` (`engine/options_catalyst_link.py:1, 50` — `from engine.stock_identity.authority import authority_block`; schema declared `:52-53` `SCHEMA = "options.catalyst_link/v1"`, `SPEC_VERSION = "v1"`; landed #6936) and `engine/options_payoff.py` (`engine/options_payoff.py:1-3, 43` — `MODEL_VERSION = "options_payoff.v1"`; landed #6935; math only — zero consumers on origin/main; see the producer list in §6 below). The W2-5a payoff-lab producer (`engine/options_payoff_lab.py`, `scripts/build_options_payoff_lab.py`, `ops/launchd/com.macro.payofflab.plist`, `ops/launchd/run_options_payoff_lab.sh`, `scripts/publish_r2.py`) and W2-5b page consumer are NOT on `origin/main` — they live on the W2-5a branch fetched via `origin/pr-7759`. The DEC at `agentos/decisions/DEC-F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE.md` (`affects:` block names the five producer files; `decided_by: "META-CEO A seat, packet A-F03-W2-5a, 2026-09-23"`) governs that split. `engine/options_catalyst_link.py:3-8, 106, 698-700` declares `source_rights = "research_expression_only"` and carries the five-false `authority_block` on every emitted record; pin test at `tests/test_options_catalyst_link.py:38, 480-484`. The Options Intelligence C0 program-control freeze (`research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md:1-9`, `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md`) is records/source law only — it authorizes architecture/program sequencing and forbids new signal origination, ranking, sizing, gating, or LLM escalation. The F03 packet names six modules (`research/market_intelligence_productization/MARKET_ONTOLOGY_F00B_CURRENT_CAPABILITY_CROSSWALK_2026-08-28.csv:69`): **Catalyst Picker → Exposure Map → Structure Explorer → Related Catalysts → Thesis Builder → Alert Setup**. None of them are drafted (the F00C ledger: `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv:24` MO-DELTA-033, `:26` MO-DELTA-035, `:32` MO-PAID-070, `:38` MO-PAID-076). Four F03 rows are still SPEC_ONLY / BUILT_NOT_PROVEN / NEW_BOUNDED_BUILD. W3 is the catalyst→exposure→structure trio — facts only, no design.

## §1 Q1 — Catalyst-link read-model (`engine/options_catalyst_link.py`, 784 lines)

### Inputs to `bind_event(...)` — `engine/options_catalyst_link.py:489-498`
```
event:           Mapping[str, Any]             # one live_flow event (root, exp, strike, right, id, ts, observed_at, group, ...)
asof:            date                          # producer session asof
catalysts:       Mapping[str, Sequence[CatalystCandidate]]   # per-root single-name catalyst window
calendar:        CalendarContext               # (is_third_friday, is_quad_witching, macro_catalysts)
known_symbols:   AbstractSet[str]              # identity plane; CITED: stock_identity.plane.symbols_on_plane
horizon_days:    int = 63                      # DEFAULT_HORIZON_DAYS (:75)
session_date:    date | str | None              # live_flow does NOT emit on the event dict (:218-227); caller injects
```

### Catalyst table sources referenced
- Single-name earnings: `engine/earnings_catalyst.STALE_AGE_TD` (:48)
- Macro calendar: `engine.event_calendar.is_quad_witching`, `third_friday` (:49)
- Identity set: `engine.stock_identity.plane.symbols_on_plane` (`engine/stock_identity/plane.py:87`) — `known_symbols` is cited authority, NOT a root-to-symbol join (:22-23)
- No LLM/provider; no network; no clock reads; hermetic (:15-16)

### Outputs (`bind_event` → `CatalystLink.record`) — schema `options.catalyst_link/v1` (:52) ; `:663-701`
```
KEYS (frozen, key-set drift raises ValueError :704-709):
  schema, spec_version, session_date, asof, asof_vs_session, horizon_days,
  event_id, contract={root, exp, strike, right}, binding_state,
  identity={state, resolved_symbol, authority_source, match},
  catalyst, catalyst_state, catalyst_reason, candidates,
  expiry={state, reason, exp, dte_calendar_days, is_third_friday,
          is_quad_witching, calendar_source},
  evidence, source_rights, authority, is_context_only
```

### Binding states (typed, the ONLY legal values) — `:64-73`
```
BINDING_STATES = (BOUND, UNBOUND_NO_CATALYST, AMBIGUOUS_MULTIPLE,
                  STALE_CATALYST, IDENTITY_UNRESOLVED,
                  EXPIRY_MISMATCH, EXPIRY_BEFORE_ASOF, SAME_DAY_UNORDERED)
```
Reduce order — `_reduce_binding_state` (:457-486): identity → expiry → AMBIGUOUS_MULTIPLE / SAME_DAY_UNORDERED / STALE_CATALYST → UNBOUND_NO_CATALYST → BOUND (only when identity RESOLVED + expiry OK + catalyst BOUND).

### Inputs to `bind_event(...)` — `engine/options_catalyst_link.py:489-498`
```
event:           Mapping[str, Any]             # one live_flow event (root, exp, strike, right, id, ts, observed_at, group, ...)
asof:            date                          # producer session asof
catalysts:       Mapping[str, Sequence[CatalystCandidate]]   # per-root single-name catalyst window
calendar:        CalendarContext               # (is_third_friday, is_quad_witching, macro_catalysts)
known_symbols:   AbstractSet[str]              # identity plane; CITED: stock_identity.plane.symbols_on_plane
horizon_days:    int = 63                      # DEFAULT_HORIZON_DAYS (engine/options_catalyst_link.py:75)
session_date:    date | str | None              # live_flow does NOT emit on the event dict (engine/options_catalyst_link.py:218-227); caller injects
```

### Catalyst table sources referenced
- Single-name earnings: `engine.earnings_catalyst.STALE_AGE_TD` (engine/options_catalyst_link.py:48)
- Macro calendar: `engine.event_calendar.is_quad_witching`, `third_friday` (engine/options_catalyst_link.py:49; engine/event_calendar.py:132, 136)
- Identity set: `engine.stock_identity.plane.symbols_on_plane` (engine/stock_identity/plane.py:87) — `known_symbols` is cited authority, NOT a root-to-symbol join (engine/options_catalyst_link.py:22-23)
- No LLM/provider; no network; no clock reads; hermetic (engine/options_catalyst_link.py:15-16)

### Outputs (`bind_event` → `CatalystLink.record`) — schema `options.catalyst_link/v1` (engine/options_catalyst_link.py:52) ; `engine/options_catalyst_link.py:663-701`
```
KEYS (frozen, key-set drift raises ValueError engine/options_catalyst_link.py:704-709):
  schema, spec_version, session_date, asof, asof_vs_session, horizon_days,
  event_id, contract={root, exp, strike, right}, binding_state,
  identity={state, resolved_symbol, authority_source, match},
  catalyst, catalyst_state, catalyst_reason, candidates,
  expiry={state, reason, exp, dte_calendar_days, is_third_friday,
          is_quad_witching, calendar_source},
  evidence, source_rights, authority, is_context_only
```

### Binding states (typed, the ONLY legal values) — `engine/options_catalyst_link.py:64-73`
```
BINDING_STATES = (BOUND, UNBOUND_NO_CATALYST, AMBIGUOUS_MULTIPLE,
                  STALE_CATALYST, IDENTITY_UNRESOLVED,
                  EXPIRY_MISMATCH, EXPIRY_BEFORE_ASOF, SAME_DAY_UNORDERED)
```
Reduce order — `_reduce_binding_state` (engine/options_catalyst_link.py:457-486): identity → expiry → AMBIGUOUS_MULTIPLE / SAME_DAY_UNORDERED / STALE_CATALYST → UNBOUND_NO_CATALYST → BOUND (only when identity RESOLVED + expiry OK + catalyst BOUND).

### Frequency in test fixtures — `tests/test_options_catalyst_link.py` (914 lines)
The fixture catalogue is single-name synthetic; macro candidates are tested via an empty `macro_catalysts=tuple`. State exercise is one-`bind_event` per state, no aggregate frequency histogram is asserted; the test asserts the TYPED transition contract per state (e.g. `tests/test_options_catalyst_link.py:480-484` `is_zero_authority(rec) is True`, `rec["source_rights"] == "research_expression_only"`, `rec["authority"] == authority_block()`). Macro-state frequency on a real live_flow event is not measured in any current test.

### Every caller today (grep)
```bash
$ grep -rln -E 'options_catalyst_link|from engine.options_catalyst_link|import options_catalyst_link' engine/ scripts/ templates/ tests/ 2>&1
tests/test_options_catalyst_link.py
tests/fixtures/help/merged_prs_2026-09-06_to_2026-09-19.json
```
ONLY `tests/test_options_catalyst_link.py` imports it. `.github/ci/legacy-jobs.yml:2336` names it under `flow-surface`'s paths-trigger list (NOT a runtime caller). **Zero `scripts/`, zero `engine/`, zero `templates/`, zero `app/` consumer.** The substrate exists; no live caller binds a flow event to a catalyst.

### Live-flow event producer on a render host
- `engine/live_flow.py` (substrate cited in `engine/options_catalyst_link.py:11-13` "flow-event → catalyst / ticker / expiry leg ONLY"; `MO-DELTA-035` substrate owner).
- `scripts/live_flow_poller.py` (169812 bytes) is the launchd-managed poller on the M1; producer entrypoint docstring at `scripts/live_flow_poller.py:1-50` and module structure `scripts/live_flow_poller.py:67-470` (`def _reject_duplicate_object_pairs`, `def _strict_json_loads`, `def _max_concurrent`, `def _cfg`, `def _poll_floor_sec`, `def _r2_public_base`, `def _select_cycle_roots`, `def _select_ticker_publish_roots`, `def _out_dir`, etc.). Install at `ops/launchd/com.mastermind.liveflow.plist` (lines: "Autostart on weekdays at 09:25 ET ... RTH-only mode ... exits after 16:05 ET"). NOT a workflow invocation — there is NO `.github/workflows/*` line that calls `live_flow_poller.py`.
- Nightly consumers of the resulting R2 stage: `.github/workflows/daily.yml:3304` references `live_flow/events/{DATE}.jsonl` as the raw stage for OIP `options_signal_episode`. `.github/workflows/daily.yml:3258` references `live_flow/surface/{ROOT}/{DATE}/` per-minute stamps. `.github/workflows/daily.yml:3431` mirrors `site/flow/index.json` to R2 key `live_flow/flow_idx.json`.
- Sparse worktree: **`data/` is in `config/sparse_worktree.json`** — omitted on a fresh tree. `engine/options_catalyst_link.py:738-749` **refuses to `write_links` into repo `data/`** and asks the caller for an explicit path. `site/` is also sparse-omitted. A render-host sparse checkout does NOT carry the events; the catalyst-link read-model itself is in-memory over injected events.

### Workflow line that drives the producer
- `ops/launchd/com.mastermind.liveflow.plist` (NOT a workflow file).
- `scripts/live_flow_poller.py` has no `.github/workflows/*` producer step; the launchd plist is the producer.

## §2 Q2 — C0 control freeze citations

### `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md`
- `:7` — `**Authority:** records/source law only; no runtime, scoring, ranking, sizing, trade, execution or Prophet authority` (28 words, ≤ 40).
- `:93` — `C0 authorizes only architecture/program sequencing. LLM prose/sentiment cannot invent event identity, score, rank, sizing, entry/exit or trade authority. Current DNR decisions — including no fused positioning super-score and no unapproved LLM origination — remain binding.` (38 words, ≤ 40). Captures: signal origination, ranking, sizing, gating, LLM escalation.

The C0 masterplan (148 lines total, scanned) **does NOT name** `catalyst→exposure→structure`, `Catalyst Picker`, `Structure Builder`, `W2-5`, "six modules", or `exposure map` anywhere. The module names live in `research/market_intelligence_productization/MARKET_ONTOLOGY_F00B_CURRENT_CAPABILITY_CROSSWALK_2026-08-28.csv:69` (the F03 packet, not C0).

### `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md`
- Lines naming catalyst/exposure/structure: **NONE**. The DEC scopes the four option-owner workstreams and the records/source-law envelope; it does not enumerate child modules.
- The DEC carries the lawful-adoption of `#6585` (OA-1T-MACRO) as `BUILT_NOT_PROVEN`, not complete; `FS-4` frozen with `scoring.enabled=false`.

### The six undrafted module names (canonical source — F00B crosswalk)
`research/market_intelligence_productization/MARKET_ONTOLOGY_F00B_CURRENT_CAPABILITY_CROSSWALK_2026-08-28.csv:69`:
> `MO-DELTA-033,F03-OPTIONS-EXPRESSION,Options catalyst workflow modules (six-step),WS:MARKET-OS (F03 lane); commissioning owner = Options Intelligence C0 (#6604) + WS:ADVANCED-DATA-OPTIONS,SPEC_ONLY,F03 packet mission names Catalyst Picker→Exposure Map→Structure Explorer→Related Catalysts→Thesis Builder→Alert Setup; zero implementation hits,All six modules,catalyst/event feed + ThetaData chain/flow,research_expression_only,#6604 C0 masterplan would own commissioning,BUILD_NEW,`
Confirmed by `:24` and `:32` of the F00C ledger (current granular ledger).

### Freeze contents (what C0 forbids, in scope of W3)
From C0 masterplan `:7` and `:93`: no runtime, no scoring, no ranking, no sizing, no trade, no execution, no Prophet authority, no event identity invention by LLM, no fused positioning super-score, no unapproved LLM origination. **NEW W3 shapes cannot claim any of these or change them** — C0 is the ceiling.

### Bind DNR rows (`research/DO_NOT_REBUILD.md`)
- `research/DO_NOT_REBUILD.md:39` `DNR:KILL-POSITIONING-FUSION` — Amendment 1 (CEO 2026-08-14) opens positioning keys ONLY in the Prophet US conditional-fusion arena under `research/PROPHET_CONDITIONAL_FUSION_MASTERPLAN_BY_FABLE.md` §8.6. A W3 shape that fuses OI/GEX/positioning keys into any other score remains ILLEGAL.
- `research/DO_NOT_REBUILD.md:40` `DNR:KILL-LLM-ORIGINATION` — LLMs may only de-escalate calibrated keys.
- `research/DO_NOT_REBUILD.md:51` `DNR:KILL-FUSED-COMPOSITE` — display-tier composites are allowed under `PORTFOLIO_SUPERINTELLIGENCE_MASTERPLAN_BY_FABLE.md` §3.1.2, but authority remains prohibited.
- `research/DO_NOT_REBUILD.md:55` `DNR:KILL-PROPHET-POP-MERGE` — graded-board contamination.
- `research/DO_NOT_REBUILD.md:62` `DNR:KILL-REGIME-SCORECARD` — regime verdict fusion restates ILLEGAL positioning fusion.
- `research/DO_NOT_REBUILD.md:65` `DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION` — owner eviction by windowing is FORBIDDEN.
- `research/DO_NOT_REBUILD.md:87` `DNR:KILL-DOI-FAMILY` (predictive delta-OI; display retained).
- `research/DO_NOT_REBUILD.md:88` `DNR:KILL-SKEW-DECELERATION` (predictive skew; display retained).
- `research/DO_NOT_REBUILD.md:162` `DNR:HOLD-WF-OPTIONS` — W-F options PARKED until preconditions (1)+(2) per Options→NW masterplan.
- `research/DO_NOT_REBUILD.md:124` `DNR:KILL-FORCED-CALLS` — operator force-add of un-gauntleted directional calls to signal surfaces FORBIDDEN.
- `research/DO_NOT_REBUILD.md:128` `DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR` — restates `DNR:KILL-REGIME-SCORECARD` on a wider list of 16 inputs.

## §3 Q3 — `WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY` + `WS:ADVANCED-DATA-OPTIONS` milestones

### WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md`)
- **OA-0** status `done`, PR 6573 — recovery archaeology + architecture freeze (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:17`).
- **OA-1T-MACRO** status `in_progress`, PR 6585 — BUILT_NOT_PROVEN; natural-RTH production proof OWED (`dbd654edb0fb...`, `agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:26`). **Tied to**: FS-4 frozen `scoring.enabled=false`, FS-5 kill switch intact (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:landmines` block).
- **OA-1T-TERMINAL** status `todo` CLOSED — render measured microstructure; depends_on `OA-1T-MACRO` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:56, 59`).
- **OA-1C-MACRO** status `todo` CLOSED — `options.alpha_candidate_feed/v1` composer; depends_on `OA-1T-MACRO` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:63, 66`).
- **OA-1C-TERMINAL** status `todo` CLOSED — live candidate stream; depends_on `OA-1C-MACRO, OA-1T-TERMINAL` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:71, 74`).
- **OA-2** status `todo` CLOSED — FS-5 unsigned calibration gauntlet; depends_on `OA-1T-MACRO` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:78, 81`).
- **OA-3** status `todo` CLOSED — exact-option NBBO lifecycle/outcome (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:88, 91`).
- **OA-4** status `todo` CLOSED — right-conditioned directional family prereg; depends_on `OA-2, OA-3` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:95, 98`).
- **OA-5** status `todo` CLOSED — Issue Desk integration; depends_on `OA-1C-TERMINAL, OA-4` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:104, 107`).
- `do_not_redo` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:do_not_redo` block): "Another options collector, ThetaData Terminal instance, live-flow store, event identity, campaign ledger, outcome ledger, Issue Desk, rank/gate/sizing control plane, or generic Options super-score." Reopening AD-1T1; FS-4 promotion; backfilled later-settled OI/NBBO.
- `landmines` (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:landmines` block): `KILL-LLM-ORIGINATION`, `KILL-FUSED-COMPOSITE`, `KILL-POSITIONING-FUSION`, `HOLD-THETA-TAPE`, `KILL-DOI-FAMILY`, `KILL-SKEW-DECELERATION`, `KILL-CHARM-NARRATIVES`, `KILL-OFFHORIZON-VERDICTS`.
- **No OA milestone touches `catalyst→exposure→structure`.** The closest layer is OA-1C-MACRO (alpha_candidate_feed) which is "CLOSED until OA-1T-MACRO measured-evidence path" and depends on production-accepted AD-1T2 EOD consumer/availability (`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:63-67`).

### WS:ADVANCED-DATA-OPTIONS (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md`)
- **AD-0** done; **AD-1P0** done (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:21`); **AD-1** done, BUILT_NOT_PROVEN (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:35`); **AD-1C0** done (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:48`); **AD-1C0.1** done (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:59`); **AD-1T0** done (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:70`); **AD-1T1** done, PROVEN_LIVE (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:88`, PR 6267); **AD-1T2** status `todo` NOT STARTED (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:113`); **AD-2** CLOSED until AD-1 production acceptance (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:121`).
- AD-1T2 next_action: `AD-1T2 is NOT STARTED. Opens only after AD-1T1 is Sol-accepted and the T1 cadence is production-proven` (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:114-116`).
- `landmines` (`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:142`): AD authorizes no duplicate intraday collector; only `gex_confirm_verdict` in C1 fusion reaches live Prophet rank, lawful solely via `DNR:KILL-POSITIONING-FUSION` Amendment 1.
- **No AD milestone touches `catalyst→exposure→structure`.** OA-1C-MACRO depends on production-accepted AD-1T2 EOD (cross-WS dependency).

### Latest handoffs that touch expression / catalyst / payoff
- `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-2026-09-06.md` — W2-1b / W2-1b-round-2 skew source migration to ThetaData (MO-PAID-013).
- `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-FABLE-COO-2026-08-26.md` — sustained F03 Fable COO lane commission; mission enumerates `Strategy/P&L/Greeks depth + Structure Builder + catalyst-to-options workflow`. AS-OF 2026-08-26; no later re-broadcast in `agentos/handoffs/` indexing.
- `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-2026-09-06.md:next_actions` block for W2-1b only — does NOT charter W3.

### What each handoff says about "what's next"
- W2-1b handoff `next_actions`: W2-2 installs M1 launchd ThetaData accrual; W2-3 removes the legacy export and switches to `--emit`. **Does NOT mention W3**.
- F03 Fable-COO lane handoff `next_actions`: `Refresh owners and historical ledger; produce exact adoption map; pick first bounded vertical; RED-first prerequisite/identity/staleness/liquidity/multiplier/output-gate tests; implement over existing Options APIs`. **Does NOT name W3.**

## §4 Q4 — Existing expression surfaces for options

### `templates/options.html.j2` (canonical anonymous options surface)
- `:1077-1080` — glance-tier AIB lede (`data-aib-receipt`, `data-aib-state`, `data-aib-asof`, `data-aib-fresh`). **This is the AD-1T1 PROVEN_LIVE glance lede (MO-PAID-010)**, NOT a catalyst-chip line on a flow event.
- `:3369-3370` — `earnings_window: ['Earnings soon','临近财报', true, 'Within about two weeks of earnings — options flow around earnings is often an event bet, not a conviction position.'].` This is a **flow-tier trigger language** dict; the chip itself is wired into the rendering pipeline at `:3369+` (event_window family), but **it is not bound to a specific flow event's catalyst/ticker/expiry** — there is no `bind_event` call site.
- `:2787` — "Not measured yet. The idea: how much of this name's open interest rolls off in the next few days, and whether that concentration tends to feed on itself into expiry" — descriptive copy only.
- `:2942-3147` — Strike × expiry surface, volatility smile, IV term structure, expiry ladder, raw options structure (`The surface — strikes by expiry`). `rawItem(...)` messages. Display-only.
- `grep` for `picker|builder|payoff|structure-builder` in `templates/options.html.j2` returns ONLY: structural template jargon (`.oew-raw-*` raw-structure shelf at `:843`, builder build pipeline ownership references at `:1628, 2166, 3427, 3444`) and one payoff row in the expiry ladder template (`straddle_pct` formatting `:3076`). **No `Catalyst Picker` / `Structure Builder` / `catalyst-link` UI exists or is stubbed.**

### `templates/options_screener.html.j2` and `templates/gex.html.j2`
```
$ grep -nE 'catalyst|earnings|expiry.*event|event.*expiry|picker|structure.*picker' templates/options_screener.html.j2 templates/gex.html.j2 2>&1
(no matches)
```
Neither surface renders a catalyst line or an event-behind-flow chip today.

### `templates/onboard.js, watchstore.js, leader_radar.html.j2, fundamental_forensics.html.j2, market_structure.html.j2`
- `templates/onboard.js:1655, 1717` + `templates/onboard.css:782, 792` — "tier header = the picker" refers to the onboard flow tier selector (commodity / sell-side / radar), NOT a Catalyst Picker.
- `templates/watchstore.js:412` — "list picker once W1b makes lists server-backed" — server-driven watchlist picker, NOT catalyst.
- `templates/leader_radar.html.j2:682` — `Stock-picker's tape` is descriptive prose in a leader-radar copy line, NOT a UI picker.
- `templates/fundamental_forensics.html.j2:72` — `ff-company-picker` is the company-selector dropdown on the FF page.
- `templates/market_structure.html.j2:23, 433` — `cor1m_regime` selector + `Stock-picker window` heading (descriptive prose).
- `templates/sector_cycles.js` — Series(n) picker is the chart-series selector; unrelated.
**No `Catalyst Picker` / `Structure Builder` UI exists.**

### Builder / store consumer (`scripts/build_options_command.py`)
- `load_stores(root)` at `:142` — `tests/test_render_options_workspace_scope.py:52` pins the literal: `CMD_SRC = (ROOT / "scripts" / "build_options_command.py").read_text()`, then `:25` requires `it reads "load_stores" out of the builder and forces a wiring decision for every store`. Any new builder must declare its catalog in `load_stores()`.
- `load_intel_brief()` at `:171` is a DELIBERATELY SEPARATE loader (`tests/test_render_options_workspace_scope.py:25` test: `assert "build_options_command" not in band,` for serial post-band step), and `AIB` is fed by `load_intel_brief()` not `load_stores()`.
- Templates `templates/options.html.j2` is wired by `.github/workflows/daily.yml:3245-3255` (`OEU M-CMD — the Options workspace (build_options_command)`); the same builder at `:1557-1570` reads stores via `load_stores()`.

### Terminal cross-repo
The cross-repo product surface lives in `charting-app`. There is no documented live reference from `docs/MASTERMIND_SYSTEM_MAP.md` (or any other repo doc this census found) to a charting-app options-page `data-aib-receipt` / catalyst-chip line. The Macro-side options.html is the canonical anonymous options surface.

## §5 Q5 — ExpressionCandidate law

### Definitions and contract
- Engine docstring (`engine/options_payoff.py:1-3`, `:1620`): `RESEARCH EXPRESSION ONLY (MO-DELTA-034, MO-PAID-077: source_rights=research_expression_only).`
- Engine docstring (`engine/options_catalyst_link.py:3-8`): `Tier: research_expression_only under ExpressionCandidate law (MO-PAID-070 source_rights; MO-DELTA-035). Zero entry authority and zero scoring authority — does not rank, size, gate, originate a signal, or escalate. Every emitted record carries engine.stock_identity.authority.authority_block() (five false booleans). No LLM originates, ranks, or escalates a binding (Neural Web A7).`
- `MARKET_ONTOLOGY_AUTHENTICATED_P1_FINAL_SOL_ADJUDICATION_2026-08-23.md:185-188`: `### ExpressionCandidate — Treat as a proposal/read model over the canonical Options plane. Do not create a second option chain, surface, Greeks, flow, or strategy-pricing system.`
- `MARKET_ONTOLOGY_COMPLETE_PARITY_ADOPTION_ADDENDUM_2026-08-26.md:82`: ...Structure Builder and catalyst-to-options workflow. Converge on the accepted ExpressionCandidate direction and fail closed when prerequisites are absent.

### What a `research_expression_only` record may do
- Display-tier surface line (chip / lede / receipt badge / appendix).
- Carry `source_rights = "research_expression_only"` and `is_context_only = True`.
- Inherit the five-false `authority` block.

### What it may NOT do (binding contract)
- Rank, size, gate, originate a signal, escalate (`engine/stock_identity/authority.py:24-32` AUTHORITY_KEYS — `can_rank`, `can_size`, `can_gate`, `can_originate_signal`, `can_escalate` — all `False`; `:40-54` `authority_block()` returns `{k: False ...}`).
- Carry LLM-originated binding or escalation (`engine/options_catalyst_link.py:7-8`, `DNR:KILL-LLM-ORIGINATION`).
- Fuse positioning keys outside the Prophet US conditional-fusion arena (`DNR:KILL-POSITIONING-FUSION` Amendment 1).
- Create a second option chain / surface / Greeks / flow / strategy-pricing system (`MARKET_ONTOLOGY_AUTHENTICATED_P1_FINAL_SOL_ADJUDICATION_2026-08-23.md:185-188`).

### Pinned tests
- `tests/test_options_catalyst_link.py:38, 480-484`:
```
assert rec["authority"] == authority_block()
assert all(v is False for v in rec["authority"].values())
assert rec["source_rights"] == "research_expression_only"
assert is_zero_authority(rec) is True
```
- `tests/test_options_payoff.py` pins the same five-false contract on payoff records (parity, by import of `engine/stock_identity/authority`).
- `tests/test_options_catalyst_link.py:38` imports `authority_block, is_zero_authority` from `engine.stock_identity.authority` — any new W3 substrate that emits a record MUST use the same stamp.
- `tests/test_options_catalyst_link.py:703-709` — `if keys != _EXPECTED_RECORD_KEYS: raise ValueError("catalyst-link record key set drifted: ...")` (record-key drift guard).
- `engine/options_catalyst_link.py:738-749` — `write_links` REJECTS any path inside `data/` ("write_links refuses repo data/ paths (no data/ I/O)").

## §6 Q6 — Data joinability and the payoff engine

### `engine/options_payoff.py` (on `origin/main`, 56959 bytes)
- API surface (`grep -nE '^def '` excerpt): `leg_from_chain_row` `:418`, `structure_from_chain` `:553`, `structure_from_legs` `:753`, `expiry_payoff` `:868`, `scenario_grid` `:1030`, `greeks_drift` `:1272`, `structure_summary` `:1384`, `evidence_recipe` `:1537`. Sources cited: `engine/thetadata_store.chain` (`:1593`).
- Inputs: `chain` row frame (`engine/thetadata_store.py:544 chain(date: str, root: str, ...)`) — columns `:548-553`. Chain store is the **store-host m1** `thetadata_store`; render hosts do NOT hold the T1 store and use the legacy `polygon_gex` chain per `DEC:AD-OPTIONS-CANONICAL-SOURCE-THETADATA`.
- Frame requirements: `leg_from_chain_row(row, qty, multiplier)` takes ONE chain row (root, expiry, strike, right, bid, ask, greeks). `structure_from_chain(chain, ...)` walks a chain frame. The chain shape is THETADATA-shaped, not the LIVE-FLOW-event shape emitted by `engine/live_flow.py`.

### Can a `CatalystLink` (root, expiry, catalyst) be joined to a payoff-lab structure?
- Index ETFs only — payoff-lab catalog (per W2-5a charter) is SPY/QQQ/IWM/DIA × atm_straddle / rr25 (25-delta risk-reversal) / put_spread_95_90 / call_spread_105_110. **No single-name roots** in W2-5a.
- A `CatalystLink.event.contract.root` can be a single name (e.g. AAPL); payoff-lab cannot price it today.
- For an index ETF root the join is: `event.contract.root` ∈ {SPY, QQQ, IWM, DIA} AND `thetadata_store.chain(asof, root=...)` resolves on the store host m1 AND `nearest_tenor(exp)` exists in the catalog. There is NO code on `origin/main` that performs this join; `engine/options_catalyst_link.py` does not import `engine/options_payoff.py`.

### Single-name structure feasibility today
- A single-name structure would need: `thetadata_store.chain(asof, root=single_name)` resolves on m1 (the producer host) → call from a render host fails because render hosts do NOT carry the T1 store. The W2-5a charter documents this ("Render hosts do not hold the ThetaData store, so the same split already used for the skew ledger applies here").
- The substrate `engine/options_payoff.structure_from_chain` would also need a chain frame; `leg_from_chain_row` requires finite bid/ask. A REAL chain on m1 — `decorators` — but rendering / hybrid "render-host-thin, store-host-thick" requires a rebuild (DEC:SKEW-ACCRUAL-ON-THE-STORE-HOST precedent).
- Single-name structure is therefore **NOT viable as a single-PR follow-on to W3-0** without a fresh store-host split decision.

### Payoff-engine consumers (`engine/options_payoff.py`)
```bash
$ grep -rln 'from engine.options_payoff\|from engine import options_payoff\|options_payoff\.' engine/ scripts/ templates/ tests/
engine/options_payoff.py
tests/test_options_payoff.py
tests/fixtures/help/merged_prs_2026-09-06_to_2026-09-19.json
```
ONLY `tests/test_options_payoff.py` consumes it. **Zero `scripts/`, zero `templates/`, zero `app/` consumer.** Same dead-consumer pattern as `engine/options_catalyst_link.py`. `W2-5a` is the producer; `W2-5b` is the consumer — neither is on `origin/main` yet.

## §7 Q7 — Tests / CI homes

| Test file | Job | `gate:` line | In PR pack? | Evidence line |
|---|---|---|---|---|
| `tests/test_options_catalyst_link.py` | `flow-surface` | **`gate: data`** at `.github/ci/legacy-jobs.yml:2202` | NO (`if: ${{ false }}` trigger; `gate: data`) | `:2200` job name; `:2657` paths trigger; `:2746` `run:` step |
| `tests/test_options_payoff.py` | `flow-surface` | **`gate: data`** at `.github/ci/legacy-jobs.yml:2202` | NO | `:2663` paths trigger; `:2756` `run:` step |
| `tests/test_render_options_workspace_scope.py` | `workflow-yaml` | **`gate: data`** at `.github/ci/legacy-jobs.yml:4702` (next gate:data label after `if: ${{ false }}`) | NO | `:4702` job name (job header `:4702-4760`); `:4893` `run:` step |

### What runs in a PR pack
- `ci.yml` runs ONLY `gate: code` jobs. The two options tests above are `gate: data`, so a PR open against `origin/main` does NOT prove them locally — `ci.yml:7 pull_request:` triggers ci-plan → ci-pack-N (gate: code only). Fixing this is not part of W3-0's spec, but a seat-design follow-on would move the suite into a `gate: code` job (e.g. `options-skew-engine` already exists at `.github/ci/legacy-jobs.yml:16264` with `gate: code` and is the precedent).

## §8 Q8 — Candidate W3 shapes (FACTS ONLY, no design)

### Macro-event calendar in the repo
- `engine/event_calendar.py` (DISPLAY/CONTEXT/LEAF, `is_context_only=True`) — title says "scheduled CPI / PPI / jobs / GDP / Personal-Income-&-Outlays(PCE) release dates from the FRED release/dates API + TreasuryDirect + weekly jobless claims (Thu) / ISM Mfg/Services (1st/3rd business day) / monthly options expiry / quad-witching (3rd Friday)".
- Cited module ports: `engine.macro_news` (FOMC + first-Friday jobs) and `engine.commodity_news` (FOMC + OPEC + EIA WPSR) BOTH delegate here.
- `engine/marketing/fomc_statements.py` is a separate FOMC-statement BODY collector: `:48-58` "READ FROM event_calendar, DO NOT RESTATE".
- `engine/macro_surprise.py` — `FRED`-backed release surprise (line `:66-67` `cpi` release stub with display_name `CPI (Consumer Price Index)`); `def build_release_cards(...)` `:740`.
- No `fomc_calendar.py` / `cpi_calendar.py` / standalone macro-calendar artifact exists outside `engine/event_calendar.py`.

### (a) Tier-2 "catalyst behind this flow" line on existing `options.html.j2` flow/ticker rows
- **Producers touched (only those needed to emit the chip line)**: `engine/options_catalyst_link.bind_event` (already emits `record`); a NEW adapter would compose `bind_event(...)` outputs into a glance-tier string per `templates/options.html.j2` flow-row.
- **Stores touched**: `engine.stock_identity.plane.symbols_on_plane` (set); `engine.earnings_catalyst` window; `engine.event_calendar` macro candidates. NO `data/` store.
- **Builders / templates / tests touched**:
  - `templates/options.html.j2` (chip line in the flow/ticker rows; the row builder is around the `.oew-fl-*` and `.oew-raw-*` families at `:799`+).
  - `scripts/build_options_command.py` `load_stores()` (if any new JSON sidecar is introduced) — `tests/test_render_options_workspace_scope.py:25,52` PINS this.
  - New T2 chip requires a new `tests/` suite proving: `bind_event` `BOUND` → T2 chip string with catalyst kind + date + DTE; `UNBOUND_NO_CATALYST` / `AMBIGUOUS_MULTIPLE` / `STALE_CATALYST` → "no chip" or "context-only chip" per the glance-tier doctrine.
- **Fleet laws that bind**: design doctrine §Glance tier (state + plain-word stance under hard word budgets; falsifier/refutation language never front-facing); `DNR:KILL-LLM-ORIGINATION`; `DNR:KILL-POSITIONING-FUSION`; C0's "no signal origination / ranking / sizing / gating" ceiling; `engine/options_catalyst_link.py:703-709` record-key drift guard; `engine/options_catalyst_link.py:738-749` write-links refuses `data/`. Plain-language law (EN+ZH).

### (b) Catalyst chip on the payoff-lab card fold (W2-5b page that reads `site/options_payoff_lab/latest.json`)
- **Index ETFs have no single-name catalysts.** SPY/QQQ/IWM/DIA roots in the W2-5a catalog — a chip reading "Earnings SOON" is structurally None for index ETFs.
- **Macro-event chip path is OPEN**: `engine/event_calendar.py` + `engine/macro_surprise.py` already expose scheduled CPI/PPI/NFP/GDP/PCE/FOMC dates AND FOMC-statement bodies (`engine/marketing/fomc_statements.py`). A chip could read e.g. `Next FOMC: 2026-09-17 (statement-day body in site/fomc_statements/)`. Whether this is the seat's chosen behavior is the seat's choice.
- **Producers / stores / builders / templates / tests touched**:
  - W2-5b page is NOT on `origin/main`. Once it lands, the fold is the W2-5a R2 ingest (`site/options_payoff_lab/latest.json`) + a new T2 chip drawing from `engine/event_calendar` + `engine/marketing/fomc_statements`.
  - `engine/event_calendar.py` says `:23-30` "deliberately no event-risk score / conviction dampener ... the impact field is a DISPLAY tier (visual emphasis / strip filter) ONLY — never a multiplier on anything."
  - `engine/marketing/fomc_statements.py` body collector supplies a `body` (verbatim FOMC statement text); a fold chip would be a 1-line label, NOT a body excerpt.
  - Tests: the W2-5b test (when it lands) will own the chip-render contract; the catalog catalyst-only test would need to assert "index ETF ⇒ no earnings chip".
- **Fleet laws that bind**: C0 ceiling, plain-language law (EN+ZH), `engine/event_calendar.py:23-30` (DISPLAY tier only), `engine/options_payoff.py:1-3` (`research_expression_only`, five-false authority), `engine.stock_identity.authority.authority_block()` stamp on any record, `DNR:KILL-LLM-ORIGINATION`. **NOT bound by `DNR:KILL-POSITIONING-FUSION` or `DNR:KILL-OFFHORIZON-VERDICTS`** at this layer — pure display catalog.

### (c) Single-name "structure for this catalyst" page
- **Producers needed**: `engine/options_catalyst_link.bind_event` (already emits `BOUND`/etc.); `engine/options_payoff.structure_from_chain` (`engine/options_payoff.py:553`); `engine/options_payoff.structure_summary` (`engine/options_payoff.py:1384`); `engine/options_payoff.evidence_recipe` (`engine/options_payoff.py:1537`).
- **Stores needed**: `thetadata_store.chain` on m1 (single-name chain on the store host); identity set `engine/stock_identity.plane.symbols_on_plane`.
- **Builders / templates / tests**:
  - NEW builder `scripts/build_options_payoff_structure.py` (modeled on `scripts/build_options_payoff_lab.py`).
  - NEW launchd `ops/launchd/com.macro.payoffstructure.plist` (modeled on W2-5a's plist).
  - NEW template `templates/options_structure_single.html.j2` (consumer page).
  - NEW R2 ingest at `site/options_structure_single/latest.json` (or root-keyed).
  - NEW tests (model the W2-5a test on `tests/test_options_payoff.py`).
  - `tests/test_render_options_workspace_scope.py:25,52` PINS `load_stores()` to literal coverage — any new store MUST be declared inside `load_stores(root)` at `scripts/build_options_command.py:142`.
- **Fleet laws that bind**: **store-host-vs-render-host split** (DEC:SKEW-ACCRUAL-ON-THE-STORE-HOST — render hosts do NOT hold the T1 store); C0 ceiling; `DNR:KILL-LLM-ORIGINATION`; `DNR:KILL-POSITIONING-FUSION`; `DNR:KILL-OFFHORIZON-VERDICTS` (verdicts only at registered `horizon_role`); `DNR:KILL-FUSED-COMPOSITE` (no fused risk/health); `DNR:KILL-DOI-FAMILY` + `DNR:KILL-SKEW-DECELERATION` (predictive ΔOI and skew-decel are dead); display-tier doctrine; plain-language law (EN+ZH); ExpressionCandidate stamp; `engine/options_catalyst_link.py:703-709` record-key drift; `write_links` rejects `data/`.

## §9 Facts the seat should not trust yet

- The frequency of binding states on a real RTH session is **NOT measured in any current test** (`tests/test_options_catalyst_link.py` is per-state unit-only). The seat should not cite "X% UNBOUND_NO_CATALYST" without a production receipt run on the M1.
- `engine/options_catalyst_link.py` does NOT have a `scripts/` consumer; the only known invocation is via direct Python import in tests. A claim that "bind_event already runs in nightly/intraday" is **NOT verifiable from the current repo** — the closest nightly/intraday consumer is `options_signal_episode` on `engine/live_flow.py`, not on `engine/options_catalyst_link.py`.
- The W2-5a branch fetched from `refs/pull/7759/head` shows `engine/options_payoff_lab.py`, `scripts/build_options_payoff_lab.py`, `ops/launchd/com.macro.payofflab.plist`, `ops/launchd/run_options_payoff_lab.sh`, `scripts/publish_r2.py` (per `DEC-F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE.md:affects`). **NOT yet verified on this checkout** whether they survived `git fetch` without conflict — `git ls-tree origin/pr-7759 -- engine/options_payoff_lab.py scripts/build_options_payoff_lab.py ops/launchd/com.macro.payofflab.plist 2>&1` returned 1 line in a partial search; full list requires running on the W2-5a branch (out of scope; this packet is a CENSUS only).
- The macro-event calendar's freshness contract: `engine/event_calendar.py` says "every public function returns plain data and NEVER raises into the build; all network/parse failures degrade to the static schedule or an empty list." A seam review on whether the schedule degrades silently under a real FRED outage is NOT in scope here.
- `engine/live_flow.py` event-emission paths inside `scripts/live_flow_poller.py` are 200+ lines and were not line-by-line reviewed; only the launchd entry-point (`ops/launchd/com.mastermind.liveflow.plist`) and the docstring summary (`scripts/live_flow_poller.py:1-50`) were cited.
- `tests/test_render_options_workspace_scope.py` was not read line-by-line beyond the `load_stores()` pin claim; only the assertions on `:25, 52, 217-241` were confirmed by `grep -n`.

## §10 Files read for this census

| Path | Lines / scope | What was used |
|---|---|---|
| `engine/options_catalyst_link.py` | full (784) | Inputs/outputs/states; callers; hermeticity; data/ write-link refusal |
| `engine/options_payoff.py` | 1-50 (docstring) + grep of `^def ` | API surface, source citation to `thetadata_store.chain`, consumers |
| `engine/event_calendar.py` | 1-40 (header) + grep | DISPLAY-only macro-event calendar |
| `engine/marketing/fomc_statements.py` | 1-60, 220-240 | FOMC statement body collection; cited role as substrate for statement-diff desk |
| `engine/macro_surprise.py` | 66-67 + grep `^def ` | FRED release-stub / build_release_cards |
| `engine/stock_identity/authority.py` | full (≤60 lines) | AUTHORITY_KEYS, authority_block(), is_zero_authority() |
| `engine/stock_identity/plane.py` | 87 (`symbols_on_plane`) | Identity set authority citation |
| `engine/live_flow.py` | path-listing only | Substrate citation in MO-DELTA-035 |
| `scripts/live_flow_poller.py` | 1-50 (docstring) | Producer entrypoint; launchd relationship; no workflow caller |
| `scripts/build_options_command.py` | grep of `load_stores`, `load_intel_brief` (142, 171, 1570, 1625, 1705) | load_stores pin + AIB separate-loader note |
| `templates/options.html.j2` | grep `:1077-1080, 1628, 2166, 2787, 2942-3147, 3369-3370, 3427, 3444` + `picker`/`payoff`/`straddle` | AIB glance lede, earnings_window chip, NO catalyst-link UI |
| `templates/options_screener.html.j2`, `templates/gex.html.j2` | grep full | No catalyst/picker chip rendered |
| `templates/onboard.js`, `watchstore.js`, `leader_radar.html.j2`, `fundamental_forensics.html.j2`, `market_structure.html.j2`, `sector_cycles.js` | grep `picker` | All "picker" hits are unrelated to catalysts |
| `tests/test_options_catalyst_link.py` | 1-485 (header + relevant assertions) | Fixture shape; pin test for authority_block + source_rights |
| `tests/test_options_payoff.py` | grep | Payoff engine suite exists; no template consumer asserted |
| `tests/test_render_options_workspace_scope.py` | 1-60, 217-260 | load_stores() pin and store-path reconstruction |
| `agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md` | full | OA-0..OA-5 status; do_not_redo; landmines |
| `agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md` | full | AD-0..AD-2 status; AD-1T2 NOT STARTED |
| `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md` | full | C0 records/source law; OA-1T-MACRO lawful-adoption history |
| `agentos/decisions/DEC-F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE.md` | via `git show origin/pr-7759:...` | W2-5a producer scope; index-ETF catalog |
| `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-2026-09-06.md` | full | W2-1b skew source migration; W2-2/W2-3 next_actions |
| `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-FABLE-COO-2026-08-26.md` | full | sustained F03 Fable COO lane commission |
| `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md` | full (148 lines) | C0 ceiling; NO module names |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` | lines 24-38 (F03 rows) | MO-DELTA-033/034/035, MO-PAID-070..077 |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_F00B_CURRENT_CAPABILITY_CROSSWALK_2026-08-28.csv` | lines 67-71 (F03 rows) | Six module names + ExpressionCandidate citations |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_AUTHENTICATED_P1_FINAL_SOL_ADJUDICATION_2026-08-23.md` | lines 180-260 | ExpressionCandidate definition |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_COMPLETE_PARITY_ADOPTION_ADDENDUM_2026-08-26.md` | line 82 | ExpressionCandidate converging direction |
| `research/DO_NOT_REBUILD.md` | full (curated registry) | DNR rows cited in §2 + §8 |
| `.github/ci/legacy-jobs.yml` | lines 2200-2781 (flow-surface), 4702-4910 (workflow-yaml); gate labels throughout | Job names + gate: code/data |
| `.github/workflows/daily.yml` | lines 3245-3255, 3304, 3431 | options builder wiring + live_flow raw stage |

**DRAFT, evidence only — not for merge; the seat reads it and closes or adopts.**
