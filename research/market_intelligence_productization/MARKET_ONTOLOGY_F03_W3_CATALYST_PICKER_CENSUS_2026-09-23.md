---
title: "[MO-A3] A-F03-W3-0: catalyst→exposure→structure (Catalyst Picker) census (DRAFT, evidence only - not for merge)"
packet: A-F03-W3-0 (evidence only; not for merge)
seat: Meta-CEO A
date: 2026-09-23
authority: Chairman override 09-06 — Meta-CEO A owns this program. This file does not write a Sol hold token.
read_at: merge-base with origin/main is d90de2d0c9; origin/main tip d34993def9. `git diff --name-only d90de2d0c9..origin/main -- '*.py' '*.j2' '*.yml'` is only templates/markets.html.j2 and tests/test_markets_cyc_stage_mobile.py. W2-5a ref refs/remotes/origin/pr-7759 = 0ea35f07b439390efbeec47184ce8dc86d7b55a8.
---

## §0 State of the chain today

On this worktree (merge-base with `origin/main` `d34993def9` is `d90de2d0c9`) two F03 substrates are present and one producer is not. `engine/options_catalyst_link.py:1-16` is a hermetic read-model (`SCHEMA` at `engine/options_catalyst_link.py:52`) that binds one live-flow event to a catalyst, a ticker identity, and an expiry, and says exposure-map and structure legs are deferred to A-F03-W2-5. `engine/options_payoff.py:1-5` and `engine/options_payoff.py:43` (`MODEL_VERSION = "options_payoff.v1"`) compute payoff, scenario, and Greeks-drift from a caller-supplied chain. On `origin/main` the only Python consumer of each module is its own test (`tests/test_options_catalyst_link.py:17`, `tests/test_options_payoff.py`). The payoff-lab producer is on PR #7759's head `0ea35f07`, not on `origin/main`: `git cat-file -e origin/main:engine/options_payoff_lab.py` fails. The F00C ledger still carries the four rows the seat named (`research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv:24` MO-DELTA-033, `:26` MO-DELTA-035, `:32` MO-PAID-070, `:38` MO-PAID-076). The six module names live on the F00B crosswalk, not in the C0 freeze. No template calls `bind_event`.

## §1 Q1 — Catalyst-link read-model

`bind_events` (`engine/options_catalyst_link.py:714-723`) takes `events` plus the same keyword inputs as `bind_event` (`engine/options_catalyst_link.py:489-498`): `asof: date`, `catalysts: Mapping[str, Sequence[CatalystCandidate]]`, `calendar: CalendarContext`, `known_symbols: AbstractSet[str]`, `horizon_days` default `63` (`engine/options_catalyst_link.py:75`), `session_date`. It loops `bind_event` in input order (`engine/options_catalyst_link.py:725-735`).

Event-plane shape is the dict built at `engine/live_flow.py:1068-1111`: `id`, `ts`, `observed_at`, `root`, `group`, `group_zh`, `right`, `exp`, `strike`, `dte`, `dte_bucket`, `mny_bucket`, `side`, `n_prints`, `size`, `avg_price`, `premium`, `premium_z`, `baseline_source`, `selection_rule`, `selection_floor_usd`, `selection_root_class`, `vol_gt_oi`, `vol_gt_oi_ratio`, `oi_vintage`, `repeated`, `zerodte`, `signing_source`, `swept`, `microstructure`. `session_date` is not on that dict. `engine/options_catalyst_link.py:217-221` says live_flow hashes the session into `id` and the caller must pass `session_date`.

Catalyst table: `bind_event` does not read an earnings table. It imports only `STALE_AGE_TD` (`engine/options_catalyst_link.py:48`; value `10` at `engine/earnings_catalyst.py:54`). The caller injects `CatalystCandidate` rows (`engine/options_catalyst_link.py:118-127`: `kind`, `date`, `source`, `artifact`, `stale`, `known_as_of`, `as_of_age_td`, `label`, `locator`). Staleness text points at `fields_from_assessment` (`engine/options_catalyst_link.py:25-28`, `engine/earnings_catalyst.py:167-183`): `stale=False` is fresh only when an age accompanies it. Macro candidates ride `CalendarContext.macro_catalysts` (`engine/options_catalyst_link.py:131-136`). `third_friday` and `is_quad_witching` are imported at `engine/options_catalyst_link.py:49` (`from engine.event_calendar import is_quad_witching, third_friday`). `engine/event_calendar.py:49` is the comment `# Fed-published 2026 FOMC decision dates. SEP/dot-plot meetings are Mar/Jun/Sep/Dec.` It is not the import. The definitions are `third_friday` at `engine/event_calendar.py:132` and `is_quad_witching` at `engine/event_calendar.py:136`.

`known_symbols` is an injected set. The docstring at `engine/options_catalyst_link.py:18-23` says membership is exact after `.upper()`. The `.upper()` is `root = str(root_raw).upper()` at `engine/options_catalyst_link.py:167`, inside `contract_key`. `bind_event` calls `contract_key` at `engine/options_catalyst_link.py:500`. The membership test at `engine/options_catalyst_link.py:507-513` is `root_norm = root` then `if root_norm in known_symbols`. Those lines do not call `.upper()`. `symbols_on_plane` (`engine/stock_identity/plane.py:87-92`) is the cited authority for that set and is not called inside `bind_event`.

Outputs: frozen keys at `engine/options_catalyst_link.py:88-109`, written at `engine/options_catalyst_link.py:663-701`. Drift raises at `engine/options_catalyst_link.py:703-709`. Record fields: `schema`, `spec_version`, `session_date`, `asof`, `asof_vs_session`, `horizon_days`, `event_id`, `contract` (`root`, `exp`, `strike`, `right`), `binding_state`, `identity` (`state`, `resolved_symbol`, `authority_source`, `match`), `catalyst`, `catalyst_state`, `catalyst_reason`, `candidates`, `expiry`, `evidence`, `source_rights` = `research_expression_only` (`engine/options_catalyst_link.py:698`), `authority` = `authority_block()` (`engine/options_catalyst_link.py:699`), `is_context_only` True (`engine/options_catalyst_link.py:700`).

States, the only legal values (`engine/options_catalyst_link.py:56-73`):

```
64:BINDING_STATES: tuple[str, ...] = (
65:    BOUND,
66:    UNBOUND_NO_CATALYST,
67:    AMBIGUOUS_MULTIPLE,
68:    STALE_CATALYST,
69:    IDENTITY_UNRESOLVED,
70:    EXPIRY_MISMATCH,
71:    EXPIRY_BEFORE_ASOF,
72:    SAME_DAY_UNORDERED,
73:)
```

Reduce order is identity, then expiry, then catalyst (`engine/options_catalyst_link.py:457-486`). `tests/test_options_catalyst_link.py` is 914 lines and 40 `def test_` functions. There is no production-frequency histogram. Dedicated tests (one primary state each): BOUND `tests/test_options_catalyst_link.py:182`; AMBIGUOUS_MULTIPLE `:199`; STALE_CATALYST `:211`, `:221`, `:616`, `:633`, `:846`; IDENTITY_UNRESOLVED `:241`, `:757`, `:765`; EXPIRY_MISMATCH `:255`; EXPIRY_BEFORE_ASOF `:907`; SAME_DAY_UNORDERED `:866`; UNBOUND_NO_CATALYST `:273`, `:285`, `:300`, `:745`, `:814`. `tests/test_options_catalyst_link.py:405` lists all eight in one legal-set assertion. Five-false pin is `tests/test_options_catalyst_link.py:478-484`.

Callers: a walk of `engine/`, `scripts/`, `templates/`, and `tests/` for the module name in Python, Jinja, JS, HTML, YAML, and Markdown found the import only in `tests/test_options_catalyst_link.py`. `agentos/handoffs/MARKET-OS-2026-09-19-hold-docket.md:40` names the path inside an `ls` command. `.github/ci/legacy-jobs.yml:2336` lists `engine/options_catalyst_link.py` as a `flow-surface` path, not a runtime call. No `scripts/` module calls `bind_event` or `bind_events`.

Who produces live-flow events: no `.github/workflows/*.yml` step executes `scripts/live_flow_poller.py` (path hits are CI path filters only: `.github/workflows/ci.yml:526` and `.github/workflows/ci.yml:1984`). The producer file is `ops/launchd/com.mastermind.liveflow.plist` (weekday autostart 09:25 ET, self-exit after 16:05 ET; header comment). Local stage is `config.data_dir() / "live_flow_state" / "events" / "{session}.jsonl"`. `scripts/live_flow_poller.py:96` is `OUT_DIR = "live_flow_out"`. It is not the event path. `scripts/live_flow_poller.py:97` is `STATE_DIR = "live_flow_state"`. `_state_dir` returns `config.data_dir() / STATE_DIR` at `scripts/live_flow_poller.py:475-477`. `_event_stage_path` appends `"events" / f"{session_date}.jsonl"` at `scripts/live_flow_poller.py:576-580`. The test locator matches that shape: `tests/test_options_catalyst_link.py:709-710` expects `data/live_flow_state/events/2026-09-04.jsonl#…`. Upload key is `live_flow/events/{date}.jsonl`. `scripts/live_flow_poller.py:92` is the comment `# R2 live_flow prefix`. `scripts/live_flow_poller.py:93` is `R2_PREFIX = "live_flow/"`. The upload joins that prefix with `events/{candidate}.jsonl` at `scripts/live_flow_poller.py:2087-2089`. The nightly comment that names that events object is `.github/workflows/daily.yml:3304` (`live_flow/events/{DATE}.jsonl`) on the `build_options_signal_episode` step, run at `.github/workflows/daily.yml:3321`. `.github/workflows/daily.yml:3257-3258` names `live_flow/surface/{ROOT}/{DATE}/` stamps for session digest. It does not name the events jsonl. `.github/workflows/daily.yml:3430-3432` mirrors `site/flow/index.json` to `live_flow/flow_idx.json`. That mirror is not a read of the events stage. Sparse checkout omits `data/` and `site/` (`config/sparse_worktree.json` `exclude_dirs`; `git sparse-checkout` shows `!/data/` and `!/site/`). `write_links` refuses a repo `data/` path (`engine/options_catalyst_link.py:739-749`). A sparse worktree does not contain the event stage.

## §2 Q2 — C0 control freeze

Both C0 files landed in `31ac94918d` (`git show --stat 31ac94918d`: the masterplan, `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md`, the continuation handoff, `config/mastermind_programs.yml`, `docs/MASTERMIND_SYSTEM_MAP.md`).

```
$ grep -nE 'Catalyst Picker|Structure Builder|exposure map|W2-5|catalyst→' \
    research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md
(no matches)
$ grep -nE 'Catalyst Picker|Structure Builder|exposure map|W2-5|catalyst' \
    agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md
(no matches)
```

Sentences in those two files that name the chain, Catalyst Picker, Structure Builder, exposure map, W2-5, or the six modules: not found.

What the freeze forbids, quoted under 40 words:

- `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md:7` — "records/source law only; no runtime, scoring, ranking, sizing, trade, execution or Prophet authority" (13 words).
- `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md:93` — "C0 authorizes only architecture/program sequencing." (5 words). "LLM prose/sentiment cannot invent event identity, score, rank, sizing, entry/exit or trade authority." (13 words). "Current DNR decisions — including no fused positioning super-score and no unapproved LLM origination — remain binding." (15 words).
- `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md:18-19` — "No second collector, store, event/lifecycle, score-control, queue, ranker or execution plane is authorized." (12 words).
- `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md:32` — "FS-4 remains scoring.enabled=false; FS-5 and every rank/size/gate/trade/Prophet authority remain separately earned." (11 words).
- `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md:102-104` — "This decision freezes organization, sequencing, source ownership and capability honesty." (9 words). "It changes no runtime and grants no rank, score, size, gate, trade, execution or Prophet authority." (16 words).

The word "gating" does not appear. The freeze uses "gate". The masterplan does not use the phrase "signal origination"; the closest LLM sentence is the `:93` quote above. `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md:8` names `DEC:OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL`.

Six undrafted module names, not in the C0 files, at `research/market_intelligence_productization/MARKET_ONTOLOGY_F00B_CURRENT_CAPABILITY_CROSSWALK_2026-08-28.csv:69`: Catalyst Picker, Exposure Map, Structure Explorer, Related Catalysts, Thesis Builder, Alert Setup. The same chain is named at `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-FABLE-COO-2026-08-26.md:9-13` (Thesis and Alert are shortened there) and at `research/market_intelligence_productization/MARKET_ONTOLOGY_COMPLETE_PARITY_ADOPTION_ADDENDUM_2026-08-26.md:82`.

`research/compiled_kill_registry.yml`: not found (`ls` fails). The compiled copy that exists is `config/compiled_kill_registry.yml`. Rows whose topic is options, positioning, catalyst, or structure, cited as `DNR:<KEY>` from `research/DO_NOT_REBUILD.md` (the key is the table's first cell) and the yml line where checked:

- `DNR:KILL-POSITIONING-FUSION` — `research/DO_NOT_REBUILD.md:39`; `config/compiled_kill_registry.yml:24`. Amendment 1 opens positioning keys only inside the Prophet US conditional-fusion arena.
- `DNR:KILL-LLM-ORIGINATION` — `research/DO_NOT_REBUILD.md:40`; `config/compiled_kill_registry.yml:31`.
- `DNR:KILL-OFFHORIZON-VERDICTS` — `research/DO_NOT_REBUILD.md:46`.
- `DNR:KILL-FUSED-COMPOSITE` — `research/DO_NOT_REBUILD.md:51`.
- `DNR:KILL-OPTIONS-CONTEXT-AUDIT-OWNER-EVICTION` — `research/DO_NOT_REBUILD.md:65`; `config/compiled_kill_registry.yml:206`.
- `DNR:KILL-CHARM-NARRATIVES` — `research/DO_NOT_REBUILD.md:86`; `config/compiled_kill_registry.yml:318`.
- `DNR:KILL-DOI-FAMILY` — `research/DO_NOT_REBUILD.md:87`; `config/compiled_kill_registry.yml:325`.
- `DNR:KILL-SKEW-DECELERATION` — `research/DO_NOT_REBUILD.md:88`; `config/compiled_kill_registry.yml:332`.
- `DNR:KILL-CPI-REVISION-MODEL` — `research/DO_NOT_REBUILD.md:119` (CPI revision-direction model, not the options chain).
- `DNR:KILL-ONSET-FINGERPRINTS` — `research/DO_NOT_REBUILD.md:121`; topic at `config/compiled_kill_registry.yml:562` (F1 catalyst-rung counts).
- `DNR:KILL-FORCED-CALLS` — `research/DO_NOT_REBUILD.md:124`.
- `DNR:KILL-PHASE3-START-WEIGHT` — `research/DO_NOT_REBUILD.md:125`; topic at `config/compiled_kill_registry.yml:590` (a scored catalyst leg).
- `DNR:KILL-COMPOSITE-REGIME-RELIABILITY-MONITOR` — `research/DO_NOT_REBUILD.md:128`.
- `DNR:HOLD-WF-OPTIONS` — `research/DO_NOT_REBUILD.md:162`; `config/compiled_kill_registry.yml:759`. W-F options parked.
- `DNR:HOLD-STRUCTURE-LEARNERS` — `research/DO_NOT_REBUILD.md:167`; `config/compiled_kill_registry.yml:794`. This row is full-graph causal structure learners. It is not the options Structure Builder.

`DNR:KILL-PROPHET-POP-MERGE` is `research/DO_NOT_REBUILD.md:55` (graded-board population). It does not name catalyst or structure.

## §3 Q3 — WS:OPTIONS-ALPHA and WS:ADVANCED-DATA-OPTIONS

`agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md` waves (status field, not the prose "CLOSED" inside `next_action`):

- OA-0 `done`, pr 6573, `agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:21-24`. Records/source law only (`:28-29`).
- OA-1T-MACRO `in_progress`, pr 6585, `:31-35`. `next_action` at `:36-37` says BUILT_NOT_PROVEN, natural-RTH proof owed. `:49-50` says FS-4 stays `scoring.enabled=false` and this wave armed no scoring, ranking, or sizing authority.
- OA-1T-TERMINAL `todo`, depends on OA-1T-MACRO, `:56-59`. `next_action` text at `:61` says CLOSED.
- OA-1C-MACRO `todo`, `:63-66`. Title is `options.alpha_candidate_feed/v1` research-candidate composer (`:64`). `next_action` `:67-70` says CLOSED until measured evidence, a preregistered formation policy, and production-accepted AD-1T2.
- OA-1C-TERMINAL `todo`, `:71-74`. `next_action` text at `:76` says CLOSED.
- OA-2 `todo`, `:78-81`. Title is the FS-5 unsigned calibration gauntlet (`:79`). `next_action` `:82-84` says CLOSED and says not to add OI/GEX/positioning fusion.
- OA-3 `todo`, `:88-91`. Exact-option NBBO lifecycle (`:89`). `next_action` text at `:93` says CLOSED.
- OA-4 `todo`, `:95-98`. Right-conditioned directional family (`:96`). `next_action` `:99-103` says CLOSED and names `DNR:KILL-POSITIONING-FUSION` before any fusion test.
- OA-5 `todo`, `:104-107`. Issue Desk (`:105`). `next_action` text at `:109` says CLOSED.

None of those titles contain catalyst, exposure map, Catalyst Picker, or Structure Builder. The expression-adjacent rows are OA-1C-MACRO (candidate feed) and OA-4 (directional family). `do_not_redo` at `agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md:138-143` forbids another collector, live-flow store, event identity, campaign ledger, outcome ledger, Issue Desk, rank/gate/sizing plane, or Options super-score; forbids reopening AD-1T1; forbids promoting FS-4 because code exists; forbids backfilling later-settled OI/NBBO. Landmines at `:135-137` name `DNR:KILL-LLM-ORIGINATION`, `DNR:KILL-FUSED-COMPOSITE`, `DNR:KILL-POSITIONING-FUSION`, `DNR:HOLD-THETA-TAPE`, `DNR:KILL-DOI-FAMILY`, `DNR:KILL-SKEW-DECELERATION`, `DNR:KILL-CHARM-NARRATIVES`, `DNR:KILL-OFFHORIZON-VERDICTS`. Workstream `next_action` at `:152-157` says review/land the OA-1T-Macro plan carrier, then choose an execution mode, and says later OA waves remain closed. No handoff filename under `agentos/handoffs/` matches `OPTIONS-ALPHA` or `OA-1T`.

`agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md`: AD-0 done `:17-19`; AD-1P0 done `:21-23`; AD-1 done `:26-28` with `next_action` at `:31`; AD-1C0 done `:37-39`; AD-1C0.1 done `:47-49`; AD-1T0 done `:58-60`; AD-1T1 done `:76-78`; AD-1T2 `todo` `:106-109`, `next_action` `:110-111` says NOT STARTED and opens only after AD-1T1 is Sol-accepted; AD-2 `todo` `:114-117`, `next_action` `:118` says CLOSED until AD-1 production acceptance. No AD id names catalyst, expression, or structure. Workstream `next_action` at `agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md:187-190` says the next product dependency is AD-1T2 and AD-2 stays closed.

Latest handoff per owner, and what it says is next:

- Options Alpha has no same-named handoff. The C0 continuation `agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-08-28-options-intelligence-c0-program-control.md:85-87` says do not auto-start children after C0; commission AD-1T2 only under a fresh operation. `agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-09-16-integration-amendment-packet-delivery.md:65-67` says packet B is OA-1T installed-source adoption after the close. Neither names W3.
- Advanced Data's latest filename is that 2026-09-16 handoff. Same `next_actions` block. It does not name catalyst→exposure→structure.
- F03 latest file is `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-2026-09-06.md`. `next_actions` at `:60-62` still list W2-2 (M1 launchd accrual) and W2-3 (render cutover). `unresolved` at `:57-58` marks both RESOLVED on 2026-09-23 (#7737, #7743). The block does not name W3. The 2026-08-26 Fable COO handoff `next_actions` at `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-FABLE-COO-2026-08-26.md:28-30` says claim F03, refresh the crosswalk, and separate one ExpressionCandidate/Structure workflow carrier. It does not name W3.

## §4 Q4 — Existing expression surfaces

`templates/options.html.j2` (3821 lines), lines that show a catalyst, an earnings date, or a "what to do" line for an option flow event:

- `templates/options.html.j2:1077-1080` — `data-aib-state`, `data-aib-asof`, `data-aib-receipt`, `data-aib-fresh`. This is the intel-brief lede on the page, not a `bind_event` result on a flow row.
- `templates/options.html.j2:3369-3370` — `earnings_window: ['Earnings soon','临近财报', true, 'Within about two weeks of earnings — options flow around earnings is often an event bet, not a conviction position.'`. Generic flow-tier copy. No `bind_event` call in the template.
- `templates/options.html.j2:3302` — "To watch this name's structure update live, open it in the Terminal." That is a pointer, not a catalyst line.
- Chain-structure copy, not a builder: `templates/options.html.j2:799` and `:843` (raw-structure shelf), `:1697` (loading sentence, EN and ZH), `:3028-3031` (IV term structure), `:3076` (`straddle_pct` cell), `:3111` and `:3147` ("no options structure" empty states), `:3280` (raw options structure summary).

```
$ grep -nE 'earnings|catalyst|picker|structure|payoff|straddle|spread' \
    templates/options_screener.html.j2 templates/gex.html.j2
(no matches)
```

Both `.j2` files exist. There is no `templates/options_screener.html` or `templates/gex.html`. That command does not search the rest of `templates/`. A `templates/` grep for `structure|picker|payoff|straddle|spread` also hits `templates/calculators/options_profit.html.j2`.

```
$ grep -nE 'structure|picker|payoff|straddle|spread' templates/calculators/options_profit.html.j2
4:  position_size.html.j2 structure: PURE compute() + WORKED_EXAMPLES self-check
71:<p>{{ t('At expiration a single option is worth only its <strong>intrinsic value</strong> — how far it is in the money — and your profit is that value minus the premium that changed hands, times 100 shares per contract. A call is in the money when the price sits above the strike; a put, when it sits below. Time value is gone, so the whole payoff reduces to simple arithmetic.',
116:<li>{{ t('<strong>One leg only.</strong> Spreads, straddles and multi-leg positions net several of these payoffs together; run each leg and add the results, or the risk picture will be wrong.',
```

`templates/calculators/options_profit.html.j2:1-3` is a one-leg expiration payoff calculator. `:71` uses the word payoff for that single leg. `:116` names spreads and straddles as a limit of the one-leg math. The file has no `bind_event` and no catalyst line. It is not a flow-event structure builder. The same token grep also hits pages that are not option structures (credit spreads, market structure, capital structure, series pickers). Those hits are not a Catalyst Picker and not a Structure Builder.

`engine/options_structure.py:1-15` is a different object: display or shadow schemas for dealer-gamma state, chain heat, and a strike×expiry matrix. It is not a Structure Builder page. It has many consumers (including `scripts/build_gex_board.py` and `scripts/build_options_structure_intraday.py`). Those consumers are outside the catalyst-link import set in §1.

Builder pin: `scripts/build_options_command.py:142` defines `load_stores`. `tests/test_render_options_workspace_scope.py:25` says the test reads `load_stores` out of the builder. `tests/test_render_options_workspace_scope.py:52` loads that source. `tests/test_render_options_workspace_scope.py:241` reconstructs paths from the `load_stores` body. `load_intel_brief` is a separate function at `scripts/build_options_command.py:178`. Nightly step: `.github/workflows/daily.yml:3245-3255`.

Terminal / charting-app: a search of `docs/`, `agentos/decisions/`, and `agentos/workstreams/` for a line containing `charting-app` and either `catalyst` or `option` returned no line. `.github/workflows/daily.yml:3434-3436` mentions the Terminal Dark Pool mini-panel and a Structure strip (lane T-E) as R2 mirror targets. That line does not name a catalyst or a picker.

## §5 Q5 — ExpressionCandidate law

No Python class named `ExpressionCandidate` was found. The prose definitions:

- `research/market_intelligence_productization/MARKET_ONTOLOGY_AUTHENTICATED_P1_FINAL_SOL_ADJUDICATION_2026-08-23.md:185-189` — "Treat as a proposal/read model over the canonical Options plane. Do not create a second option chain, surface, Greeks, flow, or strategy-pricing system."
- `research/market_intelligence_productization/MARKET_ONTOLOGY_COMPLETE_PARITY_ADOPTION_ADDENDUM_2026-08-26.md:82` — Structure Builder and catalyst-to-options workflow; converge on ExpressionCandidate and fail closed when prerequisites are absent.
- `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-FABLE-COO-2026-08-26.md:20` — proposal/read model over the existing Options plane, not a second pricing system.
- `engine/options_catalyst_link.py:3-13` — tier `research_expression_only`; zero entry and zero scoring authority; does not rank, size, gate, originate a signal, or escalate; five false booleans; no LLM originates, ranks, or escalates a binding; exposure-map and structure legs deferred.
- `engine/options_payoff.py:3-5` — `source_rights=research_expression_only`; zero entry authority; does not rank, score, size, admit a contract, or select an expiry.

What a `research_expression_only` record may do on a page, as those lines state it: be a read model / display of context. The catalyst record sets `is_context_only` True and stamps authority. `docs/DESIGN_DOCTRINE.md:19-27` puts user-facing copy on glance, hover, or study. `docs/DESIGN_DOCTRINE.md:155-157` requires bilingual plain ZH, not raw EN state names inside ZH text.

What it may not do:

- Catalyst stamp is five booleans, all false: `can_rank`, `can_size`, `can_gate`, `can_originate_signal`, `can_escalate` (`engine/stock_identity/authority.py:17-31`). `is_zero_authority` checks that set (`engine/stock_identity/authority.py:40-49`).
- Payoff stamp is a different object. `engine/options_payoff.py:1619-1625` puts `source_rights`, `entry_authority`, `ranking_authority`, `sizing_authority`, and `llm_origination` inside `authority`, and the last four are the string `none`. It does not call `authority_block()`.
- Second chain / surface / Greeks / flow / strategy-pricing system: adjudication `:187-189` and `engine/options_catalyst_link.py:10-11`.
- C0 rank, score, size, gate, trade, execution, Prophet: `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md:103-104`.
- LLM origination: `DNR:KILL-LLM-ORIGINATION` at `research/DO_NOT_REBUILD.md:40`.

Pins: `tests/test_options_catalyst_link.py:478-484` (five falses, `source_rights`, `is_context_only`, `is_zero_authority`). `tests/test_options_payoff.py:384-439` requires the four payoff disclosure keys to equal `none`. `tests/test_options_payoff.py` does not import `authority_block`. Record-key drift for the catalyst record is in the engine at `engine/options_catalyst_link.py:703-709`, not in the test file at those line numbers. `tests/test_options_catalyst_link.py:703-710` is a session-date test and the evidence locator quoted in §1.

## §6 Q6 — Joinability

A `CatalystLink` carries `contract.root` and `contract.exp` at `engine/options_catalyst_link.py:671-676`, plus `catalyst` at `:684`. Nothing on `origin/main` joins that record to a payoff structure. `engine/options_catalyst_link.py` does not import `engine/options_payoff.py`.

On PR #7759 only (`0ea35f07`), `engine/options_payoff_lab.py:19-30` imports `structure_from_chain`, `structure_summary`, `evidence_recipe`, `expiry_payoff`, `scenario_grid`, and `greeks_drift`. Catalog: `ROOTS = ("SPY", "QQQ", "IWM", "DIA")` and `CATALOG` of `atm_straddle`, `rr25`, `put_spread_95_90`, `call_spread_105_110` (`engine/options_payoff_lab.py:34-40` on that ref). Expiry is `options_skew._nearest_expiry` (`engine/options_payoff_lab.py:6` and `:403` on that ref), not the event's `contract.exp`. Store read is `thetadata_store` (`engine/options_payoff_lab.py:18` on that ref). Emit path is `site/options_payoff_lab/latest.json` (`scripts/build_options_payoff_lab.py:6-7` and `:148` on that ref). The charter's last paragraph (`agentos/decisions/DEC-F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE.md` on that ref) says W2-5b, the page that reads that JSON, is a later packet. `git diff --stat d90de2d0c9...0ea35f07 -- templates/options.html.j2` is empty.

So a join of one CatalystLink to one lab structure is not implemented. Key overlap exists only when `contract.root` is one of those four ETFs. The lab tenor is the skew ledger's nearest expiry, not the flow event's expiry. A single-name root is outside `ROOTS`.

What a single-name structure needs, from the functions that exist: `leg_from_chain_row` (`engine/options_payoff.py:418`) takes one chain row; `structure_from_chain` (`engine/options_payoff.py:553`) walks a chain frame. `engine/thetadata_store.py:544-546` defines `chain(date, root, store=None)`. `engine/options_payoff.py:18-21` says that frame supplies no mid, no multiplier, and no intraday timestamp. The W2-5a charter rationale says render hosts do not hold the ThetaData store and cites `DEC:SKEW-ACCRUAL-ON-THE-STORE-HOST`. On `origin/main`, the only consumer of `engine/options_payoff.py` found under `engine/`, `scripts/`, `templates/`, and `tests/` is `tests/test_options_payoff.py`.

## §7 Q7 — Tests and CI

PR packs call `scripts/run_ci_pack.py --gate code` at `.github/workflows/ci.yml:4616-4618` (plan), `.github/workflows/ci.yml:4934-4936` (execute), and `.github/workflows/ci.yml:4957-4959` (fail-safe full suite). `.github/ci/legacy-jobs.yml:16267-16268` states that a `gate: data` job does not run in a PR pack and that `gate: code` is the pack home (written there about `flow-surface` versus `options-skew-engine`).

| Test | Job | `gate:` line | In a `--gate code` pack? |
|---|---|---|---|
| `tests/test_options_catalyst_link.py` | `flow-surface` (`.github/ci/legacy-jobs.yml:2200`) | `gate: data` at `.github/ci/legacy-jobs.yml:2202`; `if: ${{ false }}` at `:2201` | No. Path `:2657`. Run `:2746`. |
| `tests/test_options_payoff.py` (only `test_options_payoff*.py` file) | same `flow-surface` | same `gate: data` at `.github/ci/legacy-jobs.yml:2202` | No. Path `:2663`. Run `:2756`. |
| `tests/test_render_options_workspace_scope.py` | `workflow-yaml` (`.github/ci/legacy-jobs.yml:4702`) | `gate: data` at `.github/ci/legacy-jobs.yml:4704`; `if: ${{ false }}` at `:4703` | No. Run `:4893`. |
| `tests/test_build_options_command.py` (options.html builder) | `options-estate-guards` (`.github/ci/legacy-jobs.yml:9860`) | `gate: data` at `.github/ci/legacy-jobs.yml:9862`. Comment at `:9861` says the legacy runner is off because ci-pack executes the job. The pack command still passes `--gate code`. | No. Run `:10002`. Paths include `templates/options.html.j2` at `:9951` and `site/options.html` at `:9946`. |

`options-skew-engine` is `gate: code` at `.github/ci/legacy-jobs.yml:16266` and runs `tests/test_options_skew.py`. It does not run the catalyst-link, payoff, or options.html render tests.

## §8 Q8 — Candidate shapes (facts only; not ranked)

Macro-event calendar: `engine/event_calendar.py:1-33` is the scheduled US calendar (CPI, PPI, jobs, GDP, PCE, FOMC, claims, ISM, opex, quad-witching). It sets `is_context_only=True` (`engine/event_calendar.py:23`) and says `impact` is a display tier only, never a multiplier (`engine/event_calendar.py:27-28`). A filename `macro_calendar` was not in the `engine/*.py` grep. Many other `engine/` modules contain the letters `cpi` or `fomc` as series or release models (`engine/release_cpi_bridge.py`, `engine/regime_one.py`); those are not this calendar. `CatalystCandidate.kind` already lists `earnings`, `cpi`, `ppi`, `nfp`, `gdp`, `pce`, `fomc` (`engine/options_catalyst_link.py:119`).

(a) A tier-2 line on existing `templates/options.html.j2` flow or ticker rows. Already present: the generic `earnings_window` copy at `templates/options.html.j2:3369-3370`, the page builder `scripts/build_options_command.py:142`, the nightly step `.github/workflows/daily.yml:3245`, the pin test `tests/test_render_options_workspace_scope.py`, and the read-model `engine/options_catalyst_link.py` with `tests/test_options_catalyst_link.py`. Not present: any template or script call to `bind_event`. Event bytes live under `data/live_flow_state/events/` (`scripts/live_flow_poller.py:576-580`), which a sparse tree omits. Laws that already bind that surface: `docs/DESIGN_DOCTRINE.md:19-27` and `:155-157`; ExpressionCandidate at `research/market_intelligence_productization/MARKET_ONTOLOGY_AUTHENTICATED_P1_FINAL_SOL_ADJUDICATION_2026-08-23.md:185-189`; the five-false stamp `engine/options_catalyst_link.py:698-700`; C0 at `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md:7` and `:93`; `DNR:KILL-LLM-ORIGINATION`; `DNR:KILL-POSITIONING-FUSION`; `DNR:HOLD-WF-OPTIONS`. The link test's CI home is `gate: data` (`.github/ci/legacy-jobs.yml:2202`).

(b) A catalyst chip on the payoff-lab card fold. The fold page is not on `origin/main` and not in the #7759 diff for `templates/options.html.j2`. The charter on `0ea35f07` says W2-5b reads `site/options_payoff_lab/latest.json` and is a later packet. The lab catalog roots are SPY, QQQ, IWM, DIA only (`engine/options_payoff_lab.py:34` on that ref). Those roots have no single-name earnings row inside the lab. The macro calendar that does exist is `engine/event_calendar.py` as cited above. Laws on the lab file's own header (`engine/options_payoff_lab.py:1-8` on that ref): display only; it does not rank a structure. Also C0 `:103-104`, the payoff authority strings at `engine/options_payoff.py:1619-1625`, `docs/DESIGN_DOCTRINE.md:155-157`, and `engine/event_calendar.py:23-28` if the chip reads that calendar. `DNR:KILL-POSITIONING-FUSION` binds if the chip fuses positioning keys into a score; the lab header does not do that.

(c) A single-name "structure for this catalyst" page. Not present: no template, builder, or test of that page on `origin/main`. Present pieces: `engine/options_catalyst_link.py` (bind), `engine/options_payoff.py:418` and `:553` (chain to structure), `engine/thetadata_store.py:544` (`chain`), and on #7759 only the index-ETF lab. A chain frame is required. The charter says the store host computes and render hosts do not hold the ThetaData store. Laws: that store-host split (`DEC:SKEW-ACCRUAL-ON-THE-STORE-HOST` as named in the W2-5a charter), C0 `:7` and `:103-104`, ExpressionCandidate `:185-189`, both authority stamps in §5, `docs/DESIGN_DOCTRINE.md:19-27` and `:163-164` (light is a design target on macro pages), `DNR:KILL-LLM-ORIGINATION`, `DNR:KILL-POSITIONING-FUSION`, `DNR:KILL-FUSED-COMPOSITE`, `DNR:KILL-DOI-FAMILY`, `DNR:KILL-SKEW-DECELERATION`, `DNR:HOLD-WF-OPTIONS`. `DNR:HOLD-STRUCTURE-LEARNERS` does not name this page.

## §9 Facts the seat should not trust yet

- Binding-state rates on a real RTH session were not counted. `data/` is sparse-omitted, so `data/live_flow_state/events/*.jsonl` is not in this worktree. Command not run: a read of that jsonl.
- Whether `com.mastermind.liveflow` is loaded in launchd on the store host was not checked. The plist in-repo is the file `ops/launchd/com.mastermind.liveflow.plist`. The W2-5a charter says the same thing about its own plist: until install, it is only a file.
- `engine/marketing/fomc_statements.py` and `engine/macro_surprise.py` were not read line by line. The calendar fact in §8 is only `engine/event_calendar.py:1-40`.
- The charting-app repository was not opened. The in-repo filename search in §4 is the whole of that check.
- `origin/main` tip when this file was last edited is `d34993def9`. Merge-base is still `d90de2d0c9`. `git diff --name-only d90de2d0c9..origin/main -- '*.py' '*.j2' '*.yml'` prints only `templates/markets.html.j2` and `tests/test_markets_cyc_stage_mobile.py`. `git cat-file -e origin/main:engine/options_payoff_lab.py` still fails. The nine commits in that range were not read line by line.
- Pytest for `tests/test_options_catalyst_link.py` and `tests/test_options_payoff.py` was not run. Their CI homes are `gate: data` (`.github/ci/legacy-jobs.yml:2202`), so a PR pack does not run them either.
- `config/compiled_kill_registry.yml` key lines for `DNR:KILL-ONSET-FINGERPRINTS` and `DNR:KILL-PHASE3-START-WEIGHT` were not printed past the topic lines `:562` and `:590`. The `DNR:<KEY>` cite is the `research/DO_NOT_REBUILD.md` row.

## §10 Files read

| Path | Lines read |
|---|---|
| `engine/options_catalyst_link.py` | 1-140, 200-249, 450-529, 640-784 |
| `engine/live_flow.py` | 1040-1210 (event dict and unusual row) |
| `engine/earnings_catalyst.py` | 45-184 |
| `engine/stock_identity/authority.py` | 1-50 |
| `engine/stock_identity/plane.py` | 80-119 |
| `engine/options_payoff.py` | 1-50, 1560-1628; `^def` grep for 418, 553, 753, 868, 1030, 1272, 1384, 1537 |
| `engine/thetadata_store.py` | 544-563 |
| `engine/event_calendar.py` | 1-54 (line 49 is the FOMC-date comment); defs at 132 and 136 |
| `engine/options_structure.py` | 1-25 |
| `scripts/live_flow_poller.py` | 90-130, 470-520, 540-580, 1960-2005, 2060-2095 |
| `ops/launchd/com.mastermind.liveflow.plist` | header through the program key; line 161 |
| `scripts/build_options_command.py` | defs at 142 and 178 only |
| `templates/options.html.j2` | 1077-1080, 3369-3370, plus the structure/earnings grep |
| `templates/options_screener.html.j2`, `templates/gex.html.j2` | grep only; no matching lines |
| `templates/calculators/options_profit.html.j2` | 1-10, 71, 116 |
| `tests/test_options_catalyst_link.py` | 1-40, 470-495, 690-720; `def test_` scan of all 914 lines |
| `tests/test_options_payoff.py` | 380-444 |
| `tests/test_render_options_workspace_scope.py` | 1-60 and grep of `load_stores` lines through 377 |
| `research/OPTIONS_INTELLIGENCE_CONSOLIDATED_MASTERPLAN_2026-08-28.md` | 1-120; name grep of the whole file |
| `agentos/decisions/DEC-OPTIONS-INTELLIGENCE-C0-PROGRAM-CONTROL.md` | 1-105 |
| `agentos/workstreams/WS-OPTIONS-ALPHA-INTELLIGENCE-RECOVERY.md` | 17-164 |
| `agentos/workstreams/WS-ADVANCED-DATA-OPTIONS.md` | id/status grep 1-230 |
| `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-2026-09-06.md` | 55-82 |
| `agentos/handoffs/MARKET-ONTOLOGY-F03-OPTIONS-EXPRESSION-FABLE-COO-2026-08-26.md` | 1-40 |
| `agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-08-28-options-intelligence-c0-program-control.md` | next_actions 79-98 |
| `agentos/handoffs/ADVANCED-DATA-OPTIONS-2026-09-16-integration-amendment-packet-delivery.md` | next_actions 60-67 |
| `agentos/handoffs/MARKET-OS-2026-09-19-hold-docket.md` | line 40 only |
| `research/DO_NOT_REBUILD.md` | key-row grep of all 188 lines |
| `config/compiled_kill_registry.yml` | key lines 23-31, 205-208, 318-335, 550, 562, 590, 758-759, 793-794 |
| `research/compiled_kill_registry.yml` | path absent |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_F00B_CURRENT_CAPABILITY_CROSSWALK_2026-08-28.csv` | rows 56-71 |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` | rows 24-26 and 32 and 38-39 |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_AUTHENTICATED_P1_FINAL_SOL_ADJUDICATION_2026-08-23.md` | 175-214 |
| `research/market_intelligence_productization/MARKET_ONTOLOGY_COMPLETE_PARITY_ADOPTION_ADDENDUM_2026-08-26.md` | 80-84 |
| `docs/DESIGN_DOCTRINE.md` | 1-35 and 149-164 |
| `.github/ci/legacy-jobs.yml` | 2200-2216, 2336, 2657, 2663, 2746, 2756, 4702-4712, 4893, 9860-9862, 9946-9951, 10002, 16264-16272 |
| `.github/workflows/ci.yml` | 4595-4629 and 4910-4962 |
| `.github/workflows/daily.yml` | 3235-3464 |
| `config/sparse_worktree.json` | exclude_dirs slice |
| PR #7759 at `0ea35f07`: `agentos/decisions/DEC-F03-W2-5-PAYOFF-LAB-CHARTERED-AFTER-C0-FREEZE.md` | full (64 lines) |
| PR #7759: `engine/options_payoff_lab.py` | 1-45; grep of ROOTS, CATALOG, nearest expiry, imports |
| PR #7759: `scripts/build_options_payoff_lab.py` | grep of latest.json and emit paths (file is 176 lines on that ref) |
