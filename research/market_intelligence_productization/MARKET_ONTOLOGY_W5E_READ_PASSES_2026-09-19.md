# Market Ontology W5-E-M read passes (macro)

Verified in this worktree at `origin/main` `9a4a389c0d21d1ae4f195ec31e950eb5c07fb381` (`git rev-parse HEAD`). Operator commission W5-E-M: this file **is** the ledger's deferred read pass / archaeology memo. No build, no strategy, no network except the commission-allowed read-only `gh pr view 6958` and `gh pr view 6904`. No git writes. Every path:line below was opened or grepped in this session.

Left alone (earlier commissions, untracked): `research/market_intelligence_productization/MARKET_ONTOLOGY_W5_EXECUTOR_CONTRACTS_MACRO_2026-09-19.md`, `research/market_intelligence_productization/MARKET_ONTOLOGY_W5D_EXECUTOR_CONTRACTS_MACRO_2026-09-19.md`.

Cheap fixture-only pytest on this head (no `data/`):

```
python3 -m pytest -q tests/test_credit_window.py tests/test_worldmap_base.py tests/test_sanctions_map_nav.py tests/test_sanctions_map_page.py tests/test_f01_fx_commodity_source_rights.py
# 86 passed, 83 warnings in 4.77s

python3 -m pytest -q tests/test_credit_momentum.py::TestForwardLedgerSessionStamp
# 19 passed, 83 warnings in 2.87s

python3 -m pytest -q tests/test_f01_credit_wiring_trace.py
# 1 failed, 6 passed, 83 warnings in 2.32s
# FAILED test_major_a_e4_credit_surface_anchors_pin_actual_content
# AssertionError: dashboard.html.j2:14029 no longer holds E4_credit_stress
```

The 2026-09-06 F01 wiring-trace test is **RED on this head** because the E4 label moved (`templates/dashboard.html.j2:14062`, was `:14029`). That is evidence the 2026-09-06 trace's line anchors drifted; it is not a MiniMax contract in this packet.

Do not re-decompose (open PRs / already-disposed today): W5-A and W5-D packets; #7121 MO-DELTA-018, #7127 MO-PAID-062, #7128 MO-PAID-060, #7126 MO-PAID-064, #7110 MO-DELTA-029, #7122 MO-PAID-020, #7133 MO-PAID-088, #7125 MO-DELTA-011, #7117/#7134 F07, #7100/#7106/#7124 F11, #7132 F12, #7102 F06, #7131 F08. W5-D already disposed MO-DELTA-031 as RECORDS_MOVE (sanctions map on this head).

No MiniMax CONTRACT in this packet. The six rows were archaeology / read-pass / probe-description work. Two remain HOLD on a named owner; four are ledger-text stale.

## Summary

| row | disposition | tier | title |
|---|---|---|---|
| MO-DELTA-013 | HOLD | n/a | Dedicated high-yield page waits on who owns the surface |
| MO-PAID-008 | RECORDS_MOVE | n/a | The world map already exists; it does not drop live event pins |
| MO-PAID-004 | RECORDS_MOVE | n/a | Each commodities page already names its engine |
| MO-DELTA-005 | RECORDS_MOVE | n/a | Decision Zones is an alias, not a new owner |
| MO-DELTA-009 | RECORDS_MOVE | n/a | No canonical ETF identity owner (open #6958) |
| MO-PAID-001 | HOLD | n/a | Four-axis regime panel is not what the stocks page includes |

---

### MO-DELTA-013 — [MO-B F01-MACRO-MARKETS] Dedicated high-yield page waits on who owns the surface
DISPOSITION: HOLD

HOLD — Meta-CEO A / Chairman F00 unified-dashboard lane owns whether a *dedicated* high-yield / investment-grade credit page is warranted, given that aggregate HY/IG gauges already ship on the Bonds page, a credit-stress chip already ships on the rates/inflation command, and an HY/IG issuance-window read already ships on the IPO page. This memo discharges the ledger's deferred module-body read pass (joint with MO-DELTA-008). It does not contract a seventh credit surface.

Joint credit-data-plane read (MO-DELTA-013 + MO-DELTA-008 + MO-DELTA-012 curve-absorption question). Commands: `sed -n '1,50p;79p;740p;780-838p;1568p' engine/credit_momentum.py`; `sed -n '1,25p;165p' engine/bond_cross_asset.py`; `sed -n '1,29p;99-110p;581p' engine/market_drivers.py`; `rg -n 'cc_vm.gauges|ORCL|hy_oas' templates/bonds.html.j2`; `rg -n 'E4_credit_stress' templates/dashboard.html.j2 engine/rates_inflation_command.py`; `rg -n 'market_drivers' templates`; `ls templates/*credit*`; `gh pr view 6904 --json title,state,mergedAt`; `sed -n '1,80p' agentos/workstreams/WS-RATES-INFLATION-COMMAND.md`.

#### What the three named modules actually compute

- `engine/credit_momentum.py:1-49,79,1568,1995-1997` — Corporate Credit Watch momentum organ (`credit_momentum.v1`). DISPLAY-TIER / NOT VALIDATED; `AUTHORITY_V1 = {rank,size,gate,escalate: False}` at `:79`. Loads ICE BofA HY OAS (`BAMLH0A0HYM2` → `hy_oas`) and IG OAS (`BAMLC0A0CM` → `ig_oas`) plus the rating ladder, Moody's DBAA/DAAA, Yahoo LQD/HYG/TLT/IEF, FINRA breadth, own-store holdings. Writes `data/corp_bonds/credit_momentum.json` and keep-FIRST `data/corp_bonds/forward_log.jsonl`. Velocity-percentile is PRIMARY; oscillator crosses SECONDARY (CCW-R15). Command: `sed -n '1,49p;79p;1568p' engine/credit_momentum.py`.
- `engine/credit_momentum.py:740,780-838` — keep-FIRST forward log: `_upsert_forward_log` loads existing `event_id`s and only inserts `if eid and eid not in existing` (`:838`). Nightly-lane gated (`COLLECT_LANE=='nightly'` at `:800-804`). Fixture tests: `tests/test_credit_momentum.py::TestForwardLedgerSessionStamp` → **19 passed**. Command: `sed -n '740p;780,838p' engine/credit_momentum.py`.
- `engine/bond_cross_asset.py:1-24,54,165` — pure function. Contemporaneous weekly OLS of asset return on the primary bond driver; HY OAS is the equity canary. Complements (does not duplicate) the rate+inflation STATE-centric transmission page. **Writes no artifact of its own** (no `json.dump` / `write_text` in the 229-line module). Persisted only by the caller. Command: `sed -n '1,24p;54p;165p' engine/bond_cross_asset.py`.
- `engine/market_drivers.py:1-29,99-110,581` — daily “what's in the driver's seat” interpreter. `credit_stress` family at `:99-110` has defining leg `hy_oas` plus `ebp`, `hyg_lqd`, `ig_oas`, `vix`. `snapshot()` at `:581`. Display-only; nothing in the scoring path imports it. Command: `sed -n '1,29p;99,110p;581p' engine/market_drivers.py`.

#### What is actually wired (ledger “unwired to any dedicated surface” is stale)

- `scripts/build_bonds.py:925` `build_corp_credit_vm` reads `data/corp_bonds/credit_momentum.json` (`:971`). `_build_spread_gauges` at `:1182`. Render at `:1989-1995` passes `cc_vm=cc_vm` into `templates/bonds.html.j2`. `bond_cross_asset.snapshot(f)` at `:1923-1924`; persisted `snap["bond_cross_asset"] = xasset` (later in the same builder). Command: `sed -n '925p;1182p;1923,1924p;1989,1995p' scripts/build_bonds.py`.
- `templates/bonds.html.j2:995-1036` — section `id="corpcredit"`, bilingual “Company bonds — credit watch” / “公司债 · 信用观察”, hero stance, **Spread gauges** looping `cc_vm.gauges` (`:1020`). Null copy: “Building history — check back soon.” (`:1033`). Command: `sed -n '995,1036p' templates/bonds.html.j2`.
- `templates/bonds.html.j2:596-597,866-867` — HY OAS / IG OAS tiles and KPIs on the same Bonds hub (not only the corp-credit card). Command: `rg -n 'HY OAS|IG OAS' templates/bonds.html.j2`.
- `templates/bonds.html.j2:1084-1094` — ORCL watch chip (`cc_vm.watch.orcl`). The ledger's `:775-782` anchor is **stale** (file is now 1509 lines). Single-issuer is true of this chip only. Command: `sed -n '1084,1094p' templates/bonds.html.j2`.
- `templates/dashboard.html.j2:14062` — `'E4_credit_stress': {'en':'Credit stress','zh':'信用压力'}`. Producer `engine/rates_inflation_command.py:557-575` (`hy_oas_z` from transmission costate). Host is the rates/inflation command board rendered through `scripts/build_site.py:6861` (`mode="macro"` → `site/macro.html`). Command: `sed -n '14062p' templates/dashboard.html.j2`; `sed -n '557,575p' engine/rates_inflation_command.py`.
- `engine/credit_window.py:1-28` + `templates/ipo.html.j2:426-432` — HY/IG issuance-window read, DISPLAY-ONLY, `SCORED = False` (pinned by `tests/test_credit_window.py:37`). **#6904 MERGED** 2026-09-10 (`gh pr view 6904 --json state,mergedAt`). The 2026-09-06 trace's “in-flight, absent on main” sentence is stale. Consumer is `ipo.html`, not a credit page. Command: `ls engine/credit_window.py`; `sed -n '426,432p' templates/ipo.html.j2`.
- `rg -n 'market_drivers' templates` → **zero hits**. `market_drivers.credit_stress` still reaches no credit-labelled template under its own name. Positive control: `rg -n 'credit_stress' engine/market_drivers.py` hits `:99`.
- `ls templates/*credit*` → no dedicated credit dashboard template. Nav already has Bonds at `templates/_navlinks.html.j2:210` (“Curve · credit · duration compass”). Command: `rg -n 'bonds.html' templates/_navlinks.html.j2`.
- DAG: `config/dag.yml:495-504` already runs `engine.credit_momentum` and writes the two artifacts. Command: `sed -n '495,504p' config/dag.yml`.

#### Standalone curve view vs WS:RATES-INFLATION-COMMAND (MO-DELTA-012 claim)

MO-DELTA-012's `next_bounded_child` is “ABSORBED-BY WS:RATES-INFLATION-COMMAND **if** a standalone curve view is chartered there, else DEFER.” On this head:

- `agentos/workstreams/WS-RATES-INFLATION-COMMAND.md:24-30` owns `engine/rates_inflation_command.py`, `scripts/build_rates_command.py`, and `site/macro.html`. It does **not** charter a standalone curve-only route. Wave F3 “Yield momentum and canonical Transmission extension” is still `todo` (`:47-51`). Command: `sed -n '1,80p' agentos/workstreams/WS-RATES-INFLATION-COMMAND.md`.
- The curve appears as chip `H5_curve_regime` on the RIC board (`templates/dashboard.html.j2:14057`) and as an embedded panel on the Bonds hub (ledger already named `templates/bonds.html.j2` curve panel). That is a chip / embed, not a standalone curve-only dashboard.
- Therefore MO-DELTA-012's absorption condition is **not** met. Do not treat a dedicated HY/IG page as absorbed by RIC either: RIC's credit surface is the E4 chip, not a credit dashboard.

#### Prior trace, now re-pinned

`research/market_intelligence_productization/F01_CREDIT_AND_COMMODITY_WIRING_TRACE_2026-09-06.md` and `agentos/discoveries/DSC-F01-CREDIT-STRESS-REACHES-ONE-LABELLED-SURFACE-NO-DEDICATED-PAGE.md` already concluded the plane is not single-issuer-only and handed dedicated-page allocation to Meta-CEO A. Those records' **line anchors are stale** on this head (`tests/test_f01_credit_wiring_trace.py::test_major_a_e4_credit_surface_anchors_pin_actual_content` RED: E4 at `:14062` not `:14029`; ORCL at `:1084` not `:775`; gauges at `:1016-1036` not `:707-726`). The plane-level claim still holds when re-read at the new lines.

LEDGER TEXT THAT IS STALE (for a records PR **after** the Chairman allocation, not this packet): `real_producer` “unwired to any dedicated surface” → the three modules **are** wired to `templates/bonds.html.j2` `#corpcredit` + E4 on `macro.html` + `credit_window` on `ipo.html`. `real_consumer` “nearest = the ORCL block” → ORCL is one watch chip inside an aggregate corp-credit section. `state_delta` “no dashboard template found” remains true for a *dedicated* page and false as a “modules exist unused” claim.

AUTHORITY: `context_only`. Do not add calibrated confidence, ranking, size, or trade language. Do not start a second credit store. Do not duplicate the IPO issuance-window read onto a new credit page.

---

### MO-PAID-008 — [MO-B F02-POLICY-GEO] The world map already exists; it does not drop live event pins
DISPOSITION: RECORDS_MOVE

The ledger's `next_bounded_child` is `ABSORBED-BY MO-DELTA-031 (same requested capability)`. W5-D already recorded that MO-DELTA-031's rights-clear slice (Natural Earth base map + OFAC overlay) is on this head. This pass confirms: the **base map + rendering** exist; a **live event pin** does not; `engine/qbus.py` is not a map.

EVIDENCE NOW:
- Ledger still says `NEW_BOUNDED_BUILD` / `NOT_BUILT` / `real_producer=NONE` / `real_consumer=NONE` / “zero geo/event-map hits”. Command: `rg '^MO-PAID-008,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` (CSV line 18). Stale against the files below.
- `templates/_worldmap_base.html.j2:1-7` — Natural Earth 1:110m Admin 0 SVG; `data-iso3` country paths; `rungs` dict iso3 → 0|1|2|3|"x". Country coloring, not lat/lon pins. Command: `sed -n '1,7p' templates/_worldmap_base.html.j2`. `rg -n 'circle|event-pin|data-lat' templates/_worldmap_base.html.j2 templates/sanctions_map.html.j2` → **zero hits**.
- `templates/sanctions_map.html.j2` includes that base (W5-D cited `:102-126`; this session: `ls templates/sanctions_map.html.j2 templates/_worldmap_base.html.j2` and the 86-pass `tests/test_sanctions_map_page.py` / `tests/test_worldmap_base.py` / `tests/test_sanctions_map_nav.py` run).
- `engine/qbus.py:1-25` — unified qualitative **item/event store** (append `data/qbus/items.parquet`, keep-FIRST on `item_id`, `event_key` clustering, novelty/echo). LEAF · CONTEXT-ONLY. No lat, lon, ISO3, or map render. Command: `sed -n '1,25p' engine/qbus.py`; `rg -n 'lat|lon|iso3|map' engine/qbus.py` → no geo hits (the `map(` hits are pandas `.map`).
- Overlay layers remain rights-gated: MO-PAID-048/049/050 (`PENDING_RIGHTS`; ledger CSV lines 21-23). F02 `do_not_redo` forbids a second event DB / geospatial object store / map identity plane (`research/market_intelligence_productization/MARKET_ONTOLOGY_F02_OWNER_SOURCE_RIGHTS_MAP_2026-09-05.md`, cited by W5-D).
- Acceptance test “MO-DELTA-031 base map ships and renders a live event pin”: first clause is true on this head (base map ships); second clause is false (no pin). Country-rung OFAC coloring is not an event pin.

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `NOT_BUILT` → `PARTIAL` in the records PR. Rewrite `real_producer` from `NONE` to `templates/_worldmap_base.html.j2` + `engine/sanctions_map.py` (absorption target MO-DELTA-031, already on `origin/main` `9a4a389c`). Rewrite `real_consumer` from `NONE` to `templates/sanctions_map.html.j2`. Rewrite `missing_contract_or_proof` to “live event pin over the existing ISO3 base map is not built; military/maritime/satellite overlays remain CONTEXT_ONLY behind MO-PAID-048/049/050”. Rewrite `next_bounded_child` to: no new map plane; any later pin is a projection over `_worldmap_base.html.j2` + an existing event store (qbus or chronicle), never a second geospatial identity. Do not contract the pin in this packet (event-identity choice is F02 owner work; overlays stay rights-gated). Live readback of the absorbed base: `GET https://www.mastermind-x.com/sanctions_map.html` (W5-D; this session did not curl).

AUTHORITY: `context_only`. Do not add a second event DB, map identity plane, or pin layer that mints new country/event identity. Do not add military / AIS / satellite. Do not add confidence, ranking, or trade language.

---

### MO-PAID-004 — [MO-B F01-MACRO-MARKETS] Each commodities page already names its engine
DISPOSITION: RECORDS_MOVE

Wiring-trace pass (joint with the MO-DELTA-013 module-body read). The ledger `acceptance_test` is “the producing engine module chain is named per page.” That test is discharged on this head. The vendor-rights half is no longer “UNVERIFIED-absent”: `research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md` types the Yahoo price spine `rights_blocked (vendor_terms_personal_use)`.

EVIDENCE NOW:
- Ledger: `UPGRADE_EXISTING_OWNER` / `PARTIAL` / producers “engine wiring UNVERIFIED” / nav `:203-206`. Command: `rg '^MO-PAID-004,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` (CSV line 9). The UNVERIFIED wiring clause is stale.
- Nav (re-pinned; ledger `:203-206` is off-by-one on the trigger): `templates/_navlinks.html.j2:202` Commodities sub-trigger, `:204` Commodity Dashboard, `:205` Strategies, `:206` Strategic Reserves. Command: `sed -n '202,206p' templates/_navlinks.html.j2`.
- **commodities.html** — builder `scripts/build_commodities.py:1-12,1656` (`env.get_template("commodities.html.j2").render(`). Engine imports: `commodity_supply_context` `:422`, `commodity_carry_context` `:498`, `commodity_mtf` `:570` and `:1305`, `commodity_conviction` `:603`, `commodity_signals` `:609` and `:1466`, `commodity_alerts` `:1467`, `commodity_index` `:1511`, `commodity_cycle_state` `:1535`, `commodity_confluence` `:1550`, `commodity_news` `:1582`, `commodity_coverage_matrix` `:1651`. Price spine `engine/commodity_inputs.py:49-53` `store.read("yahoo", ticker)`. Nightly: `config/dag.yml:3127-3128` `scripts.build_commodities`; `.github/workflows/render.yml:909`. Command: `rg -n 'from engine import' scripts/build_commodities.py`; `sed -n '1656p' scripts/build_commodities.py`.
- **commodity_strategies.html** — builder `scripts/build_commodity_strategies.py:1-16,30-31,111`. Engine: `engine.active_commodity` + `engine.commodity_strategies`. Not a standalone `config/dag.yml` step; hooked from the landing builder `scripts/build_vector.py:4704-4706` (`from scripts.build_commodity_strategies import build`). Render.yml watches the script (`:127`) but does not `brun` it separately — the vector hook is the render-lane path. Command: `sed -n '1,16p;30,31p;111p' scripts/build_commodity_strategies.py`; `sed -n '4704,4706p' scripts/build_vector.py`.
- **spr.html** — builder `scripts/build_spr.py:1-16,35,261`. Sole engine producer `engine.strategic_reserves`. Nightly: `config/dag.yml` `scripts.build_spr` (paired with commodities at `:842-843`); `.github/workflows/render.yml:910`. Command: `sed -n '1,16p;35p;261p' scripts/build_spr.py`.
- Vendor rights record already on this head: `research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md:21-23,36-42` — Yahoo commodity closes `rights_blocked (basis: vendor_terms_personal_use, config/dataset_registry.yml)`; EIA SPR `unknown (rights-posture-unrecorded)`. Binding artifact `config/dataset_registry.yml:63,104` `licensing: vendor_terms_personal_use`. Fixture tests: `tests/test_f01_fx_commodity_source_rights.py` included in the 86-pass run. Command: `sed -n '21,23p;36,42p' research/market_intelligence_productization/F01_FX_COMMODITY_SOURCE_RIGHTS_AND_DEPTH_2026-09.md`; `sed -n '63p' config/dataset_registry.yml`.
- 2026-09-06 wiring trace §2 named the same three pages as VERIFIED; this pass re-pins the render-call lines (`build_commodities.py` render moved `:1391` → `:1656`). The chain is still named.

LEDGER MOVE ON MERGE+LIVE: keep capability_state_c2 `PARTIAL`. Rewrite `real_producer` from “engine wiring UNVERIFIED” to the per-page chain above. Rewrite `real_consumer` to `commodities.html` / `commodity_strategies.html` / `spr.html` (nav `:204-206`). Rewrite `missing_contract_or_proof` to “wiring named; Yahoo price spine is `rights_blocked (vendor_terms_personal_use)` until a Chairman/commercial `DEC-*` supersedes `config/dataset_registry.yml:63` or the spot leg migrates; EIA SPR rights still `unknown`.” Rewrite `next_bounded_child` to: no MiniMax page-build; remaining gate is commercial rights, owner Chairman / commercial contract authority. Rewrite `correction_behavior` from `UNVERIFIED (producer untraced)` to `nightly-rendered templates (producers named)`. Live readback: `GET https://www.mastermind-x.com/commodities.html` (and `/commodity_strategies.html`, `/spr.html`) HTTP 200 with the existing bilingual titles. This session did not curl. Row is not `DONE` while the Yahoo spine stays `rights_blocked` for paid redistribution.

AUTHORITY: `context_only`. Do not add ranking, size, or trade language. Do not start a second commodity store. Do not paraphrase unread Yahoo/EIA terms into a permission.

---

### MO-DELTA-005 — [MO-B F04-ONTOLOGY-TRANSMISSION] Decision Zones is an alias, not a new owner
DISPOSITION: RECORDS_MOVE

F04 archaeology memo (one pass). Alias target is named on **this head** by the 2026-09-04 closure map. Open PR #6958 corroborates ALIAS and is not merged; this records move does not wait on it.

#### Lineage — what was built, by which PR, what remains CONTEXT_ONLY

Commands: `ls engine/ontology* engine/transmission* templates/transmission.html.j2 engine/market_ontology templates/*ontolog*`; `git log --all --oneline -8 -- templates/transmission.html.j2 engine/transmission_chains.py`; `sed -n '1,50p;84,107p;125-133p' research/market_intelligence_productization/MARKET_ONTOLOGY_F04_EXACT_CAPABILITY_CLOSURE_MAP_2026-09-04.md`; `sed -n '125,133p;168-174p' research/market_intelligence_productization/MARKET_ONTOLOGY_F04_EXPLORER_ARCHITECTURE_FREEZE_2026-09-04.md`.

- **No `engine/ontology*` module and no Ontology Explorer implementation on this head.** `ls engine/ontology_explorer app/ontology_explorer.py scripts/build_ontology_explorer.py templates/*ontolog*` → absent. Freeze table: “Screenshot-level Ontology Explorer | `NOT_BUILT` | No current product implementation PR or production route exists.” (`MARKET_ONTOLOGY_F04_EXPLORER_ARCHITECTURE_FREEZE_2026-09-04.md:130`). Amendment 2 forbids committing `/premiumdata/ontology_explorer.json` to the public repo (`MARKET_ONTOLOGY_F04_EXPLORER_ARCHITECTURE_AMENDMENT_2_ACCESS_TRANSPORT_2026-09-04.md:19,74,252-254`). That remaining explorer is CONTEXT_ONLY / SPEC_ONLY.
- **`templates/transmission.html.j2:31`** — live “Transmission — Rates, Inflation & the Dollar” page. Freeze `:133,168-174`: Cascade Monitor on `/transmission.html` is `PROVEN_LIVE` but narrower than the interactive multi-owner workspace; F04 must not rewrite it into the explorer shell. Builder `scripts/build_transmission.py` exists. First-parent `git log` attributes the current bytes to `6367d46a` (dashboard-bot nightly; same first-parent quirk W5-A/W5-D recorded). `--all` history includes `#6522` theme-graph fold (`196c2273`).
- **TXI substrate on this head:** `engine/transmission_chains.py`, `engine/transmission_context.py`, `engine/transmission_publish.py`, `engine/transmission_calibration.py`. Freeze `:132` TXI chain compiler `PROVEN_LIVE` as display/context substrate. Ledger MO-PAID-016 names these plus `engine/theme_graph/` as `PARTIAL` producers.
- **GMI / exposure composer:** `engine/market_ontology/exposure_map.py:1-24` — pure shock → theme → company projection (packet A-F04-W2-1), `AUTHORITY_CEILING = research_display_only`, no new store (L2), no magnitude ordering (L3). This is a projection over the existing theme-graph store, not Decision Zones.
- **Theme Tracker** (F04 adjacent, already RECORDS_MOVE in W5-A for MO-DELTA-006): `templates/state_of_themes.html.j2`.
- **#6543** `a6921aa3 records(ric): recover Rates & Inflation Command and freeze completion architecture (#6543)` — records-only RIC freeze, not an F04 product ship (sibling note on MO-PAID-001).

#### Alias target (acceptance_test of this memo)

`research/market_intelligence_productization/MARKET_ONTOLOGY_F04_EXACT_CAPABILITY_CLOSURE_MAP_2026-09-04.md:35,48,84-105`:

- Row job: “Decision Zones — downstream research/action surface from macro catalyst.”
- State at architecture freeze: `SPEC_ONLY`, identity adjudicated as `ALIAS_OR_PROJECTION`.
- “Rows whose owner identity is clarified by this architecture: `MO-DELTA-005` only.” (`:48`)
- §2.2: Decision Zones is **not** a new canonical intelligence owner or separate database. It is an alias/projection for the downstream research-action composition inside Ontology Explorer and Market OS (selected path + blocking leg / invalidators / dislocation + private exposure + research-priority context → bounded research actions). Non-goal: do not create `decision_zones.json`, a Decision Zones engine, a second task/alert queue, or a model-generated action ranker.

Open `#6958` (not on this HEAD; `git merge-base --is-ancestor origin/claude/mo-b-a-spare-b-a-f04-3 HEAD` → exit 1; files `research/market_intelligence_productization/F04_IDENTITY_ARCHAEOLOGY_2026-09-06.md` / `DEC-F04-CANONICAL-ETF-IDENTITY-OWNER-2026-09-06.md` / `tests/test_f04_identity_archaeology.py` **absent** on `9a4a389c`) restates “`MO-DELTA-005` still resolves unambiguously to ALIAS”. The alias target does not depend on that PR merging; it is already in the closure map on this head.

LEDGER MOVE ON MERGE+LIVE: capability_state_c2 `SPEC_ONLY` stays until a Decision-lens projection actually renders (explorer still `NOT_BUILT`). Rewrite `state_delta` from “alias-vs-new archaeology still unperformed” to “alias target named: Ontology Explorer / Market OS research-action composition (`MARKET_ONTOLOGY_F04_EXACT_CAPABILITY_CLOSURE_MAP_2026-09-04.md:84-105`); no new owner.” Rewrite `real_producer` from `NONE` to “alias of MO-PAID-016 substrate (`engine/transmission_*.py` + `engine/theme_graph/` + `engine/market_ontology/exposure_map.py`); no Decision Zones engine.” Rewrite `missing_contract_or_proof` to “Decision *lens* on the explorer (still `NOT_BUILT`); do not mint `decision_zones.json`.” Rewrite `next_bounded_child` to: no scoped NOT_BUILT child for a new owner; any later child is an explorer-lens projection after the explorer shell exists, still `research_only`. Sol amendment stands: competitor direction/confidence/expected-impact/priced% semantics are NOT inheritable.

AUTHORITY: `research_only`. Do not add direction, confidence, expected-impact, or priced% (Sol amendment). Do not create `decision_zones.json` or a second task queue.

---

### MO-DELTA-009 — [MO-B F04-ONTOLOGY-TRANSMISSION] No canonical ETF identity owner (open #6958)
DISPOSITION: RECORDS_MOVE

Commission instruction: if `#6958` already answers the archaeology question, dispose RECORDS_MOVE citing it rather than redoing the pass. It does — for the **identity** half. The event-row half stays open.

EVIDENCE NOW:
- Ledger: `PROJECTION_ONLY` / `PARTIAL` / “no dedicated ETF-event module; no canonical ETF identity owner located” / next child “one archaeology pass to locate/confirm the canonical ETF identity owner, then fold as a row type over the baseline (no new store).” Command: `rg '^MO-DELTA-009,' research/market_intelligence_productization/MARKET_ONTOLOGY_F00C_GRANULAR_CLOSURE_LEDGER_2026-09-02.csv` (CSV line 43).
- **This head, closure map §2.4** (`MARKET_ONTOLOGY_F04_EXACT_CAPABILITY_CLOSURE_MAP_2026-09-04.md:131-151`): GMI permits `kind=etf` nodes and `TRACKS` edges, but “A graph node slug is not sufficient canonical listing/security identity” (`:135`). Acceptance: “No `etf:<ticker>` or `co:us:<ticker>` label alone is treated as security identity” (`:151`). Required X5-ETF archaeology steps 1-7 are listed; step 7 is “amend this map if no current owner can support the row.”
- **This head, graph-side id only:** `engine/theme_graph/identity.py:234-237` `etf_node_id` returns `etf:<SYMBOL>` and says the proxy relationship carries the market. That is a graph-node slug, which §2.4 already refuses as identity. Callers: `engine/theme_graph/materialize.py:445`, `engine/market_ontology/exposure_map.py:801-807` (sorts by `etf_node_id`, never by magnitude — L3). Command: `sed -n '234,237p' engine/theme_graph/identity.py`.
- **Open PR #6958** (`gh pr view 6958 --json title,state,mergedAt,url`): state `OPEN`, `mergedAt` null, title “[MO-BA-spare] B-A-F04-3: F04 identity archaeology: ratify NO canonical ETF identity owner (upholds 2026-09-04 closure map) and settle MO-DELTA-005 alias question.” Body (round 2): **NO canonical ETF security-identity owner exists today**; `etf_node_id` is graph-side only; the `etf:<SYMBOL>` ↔ `data/etf_holdings/<FUND>/` join contract does not exist (OPEN row naming F04 identity + Data OS); **no sentence in the PR names an ETF identity owner**; event-row half stays open with resumption condition (chronicle `engine/chronicle/impact.py` / PR #6896). Files of that PR are **not** on this HEAD (`ls` of the three paths → absent; `git merge-base --is-ancestor` of the PR branch → exit 1).
- Baseline MO-PAID-016/017: TXI + theme_graph + chronicle spine/impact. W5-A already recorded MO-PAID-017 consequence glance on `templates/news.html.j2`. No ETF-as-event-asset-class row type is rendered over that baseline on this head (`rg -l 'etf_node_id' templates` → none).
- Do not fold ETF event rows until identity is owned. Folding `etf:<SYMBOL>` as if it were security identity would violate closure map `:151`.

LEDGER MOVE ON MERGE+LIVE: keep `PARTIAL`. Rewrite `state_delta` from “no canonical ETF identity owner located” to “identity archaeology answered: **ratified absent** (closure map §2.4 on this head; open #6958 records-only PR restates NO owner; not yet merged).” Rewrite `missing_contract_or_proof` to “canonical ETF identity owner ratified absent; ETF event-row projection over MO-PAID-016/017 baseline is still unbuilt and must not treat `etf:<ticker>` as security identity.” Rewrite `next_bounded_child` to: (1) merge-or-close #6958 as the records vehicle for the identity half; (2) event-row child only after Stock Identity + Data OS can support a join, still a row type over the existing chronicle/theme-graph store (Charter P7, no new store). `source_rights` stays unresolved while identity is absent. Live proof of the identity half is the merged #6958 record + this head's `etf_node_id` remaining a graph slug; there is no live ETF-event page to curl.

AUTHORITY: `context_only`. Do not treat `etf:<SYMBOL>` as canonical listing identity. Do not add a second ETF identity store. Do not add confidence, holdings-implied size, or trade language.

---

### MO-PAID-001 — [MO-B F01-MACRO-MARKETS] Four-axis regime panel is not what the stocks page includes
DISPOSITION: HOLD

HOLD — WS:MARKET-OS F01 owns whether the labeled four-axis (growth / inflation / labor / liquidity) surface is still the product ask. On this head the named host include is a **two-axis base-effect strip** on the stocks dashboard only; the HMM probability partial is orphaned; labor is not a first-class axis. The one-shot embedding probe is specified below and was **not run** (commission: do not run it; `site/` is sparse-excluded).

#### What exists (probe inputs, not live proof)

Commands: `sed -n '1,15p;111,127p;294p' engine/regime.py`; `sed -n '1,8p;39-62p' engine/axes.py`; `cat templates/_regime_read_panel.html.j2`; `sed -n '1,16p' templates/_regime_prob_panel.html.j2`; `sed -n '1,12p' templates/_base_effect_strip.html.j2`; `sed -n '15200,15206p;11488,11512p' templates/dashboard.html.j2`; `sed -n '6178,6180p;6855,6861p;7097,7103p' scripts/build_site.py`; `rg -n 'include "_regime' templates`.

- `engine/regime.py:1-14,111-127,294` — quad classification on **growth × inflation** (Q1–Q4) plus a **liquidity overlay** (`expanding` / `contracting` / `neutral`) and `liquidity_quality`. There is **no `labor` symbol** in `engine/regime.py` or `engine/axes.py` (`rg labor engine/regime.py engine/axes.py` → zero). Payrolls enter as one **growth** component (`engine/axes.py:47` `payrolls_trend`). The ledger's “4-axis growth/inflation/labor/liquidity” is not the engine's axis set.
- `engine/axes.py:1-8,39-62` — “Growth and inflation axis scoring” only. Raises `ValueError` for any other axis name (`:62`).
- `templates/_regime_read_panel.html.j2:1-9` (9 lines) — comment: “the HMM probability read was retired because the base-effect path answers the more useful forward question directly.” Includes only `_base_effect_strip.html.j2`. Does **not** include `_regime_prob_panel.html.j2`.
- `templates/_regime_prob_panel.html.j2:1-16` — still on disk; “Regime probability” / HMM P(Quad). Comment claims include by `dashboard.html.j2` and `china.html.j2`. **Neither includes it:** `rg -n 'include "_regime_prob_panel' templates` → zero hits. Orphaned partial. Its copy uses probability / “how solid is the current read” language that would fight `context_only` + frequencies-never-confidence if restored as a confidence chip.
- `templates/_base_effect_strip.html.j2:1-12,30-35` — “Where the regime is headed” / growth + inflation YoY only. DISPLAY-ONLY / MODELED.
- Host include: `templates/dashboard.html.j2:15200-15206` `{% if mode != 'macro' %}{% include "_regime_read_panel.html.j2" %}{% endif %}`. Comment at `:15202` claims “macro mode has this inside the policy tray (sx-policy-v2).” That comment is **false** against the current tray: `templates/dashboard.html.j2:11488-11587` `sx-policy-v2` is Policy Monitor (fed stance, rate-path sparkline, FOMC countdown) — no regime-read include.
- Render lane: `scripts/build_site.py:6178-6180` same `dashboard.html.j2` twice with a `mode` flag. `:6861` `mode="macro"` → `site/macro.html`. `:7097-7103` `mode="stocks"` → `site/us_stocks.html`. So the only template path that includes `_regime_read_panel` is **stocks mode / `us_stocks.html`**, and what it includes is the 2-axis base-effect strip, not a 4-axis HMM panel. `rg -n 'regime_hmm|base_effect' scripts/build_site.py` → zero hits in that file (payload arrives via the shared `latest` VM, not a dedicated kwarg).
- `rg -n 'include "_regime_read_panel|_base_effect_strip' templates/china.html.j2` → zero. The partials' “included by china.html.j2” comments are stale.
- Sibling `#6543` is records-only RIC architecture freeze (`git log --all --grep=6543` → `a6921aa3 records(ric): recover Rates & Inflation Command and freeze completion architecture (#6543)`), matching the ledger adjudication_notes. It did not ship a 4-axis panel.

#### One-shot embedding probe (describe, do not run)

**Purpose.** Decide whether a host page already renders the labeled 4-axis regime panel via the nightly render path (the row's `acceptance_test`), without changing product code.

**Inputs (read-only).**

1. Templates: `_regime_read_panel.html.j2`, `_regime_prob_panel.html.j2`, `_base_effect_strip.html.j2`, `dashboard.html.j2` (the two `mode` branches and `sx-policy-v2`).
2. Renderers: `scripts/build_site.py` writes `site/macro.html` (`mode=macro`) and `site/us_stocks.html` (`mode=stocks`).
3. Engine outputs expected in `latest`: `latest.base_effect.{growth,inflation}`, `latest.regime_hmm.regime_probs`, `latest` liquidity overlay from `engine/regime.py:294`.
4. Live HTML **if** `site/` is checked out, or `GET https://www.mastermind-x.com/us_stocks.html` and `/macro.html` (network; **not** this commission).
5. Rights/cost gate: `source_rights=internal computed series` — no vendor. Cost is the existing nightly dashboard render; no new collector. Authority `context_only`: the probe must fail the row if the HTML prints a calibrated confidence / HMM “how solid” chip as a score.

**What it would measure (pass/fail).**

| check | pass if | this head, without running |
|---|---|---|
| Stocks host include | `us_stocks.html` contains `id="regime-read"` | template says yes (`mode != 'macro'` include) |
| Macro host include | `macro.html` contains the same panel | template says **no** (gated off; policy tray is not the panel) |
| Growth + inflation labels | bilingual Growth/Inflation in that panel | yes, via `_base_effect_strip.html.j2:30-35` |
| Labor label | a first-class Labor axis | **no** — payrolls is a growth component |
| Liquidity label | liquidity overlay on the same panel | **no** — overlay lives in `engine/regime.py` but is not in `_regime_read_panel.html.j2` |
| HMM 4-quad probability bars | `_regime_prob_panel` in the rendered HTML | **no** — partial orphaned |
| Nightly path | panel present after `scripts.build_site` | stocks mode only; live HTML unread (`site/` sparse) |
| Confidence leak | no calibrated confidence chip | HMM partial would leak probability-as-confidence if restored |

**What “regime-surface projection” would read.** A later F01 projection would read the existing `latest` object (`base_effect`, regime quad, `liquidity` overlay) and render labels over that store. It would not mint a second regime store (Charter P7). It would not restore HMM “confidence” copy under `context_only`. Adding Labor as a fourth scored axis would be new scoring (`engine/axes.py` only accepts `growth`/`inflation`) — that is not MiniMax-eligible.

**Rights / cost gate.** Internal series; no vendor licence to acquire. Probe cost: one `scripts.build_site` in a tree with `site/` opted in, or one live GET. This session did neither.

LEDGER TEXT THAT IS STALE (for the records PR that the F01 owner files with the product choice): `real_consumer` “UNCONFIRMED host-page embedding (site/ read out of sparse scope)” → template-confirmed host is `us_stocks.html` via `templates/dashboard.html.j2:15206`; live HTML still unconfirmed. `missing_contract_or_proof` “one labeled growth/inflation/labor/liquidity regime surface” remains unmet (2-axis base-effect only; labor not an axis; liquidity overlay not on the panel).

AUTHORITY: `context_only`. Do not restore HMM probability as a confidence number. Do not add ranking, size, or trade language. Do not add a labor axis to `engine/axes.py` in a MiniMax contract.

---

## Packet notes

- First-parent `git log` on several of these files attributes current bytes to `6367d46a` (dashboard-bot nightly). Feature commits are visible with `git log --all` (same honesty W5-A/W5-D used). Files named above are on `origin/main` `9a4a389c`.
- `tests/test_market_drivers.py` two failures on this sparse tree (`RuntimeError: no yahoo data in store`, missing `data/regime/market_drivers_log.parquet`) are data-tree skips, not used as gates.
- No executor contract is unblocked by this memo without a product-strategy call the operator is forbidden to make (013 dedicated page; 001 4-axis vs 2-axis).
