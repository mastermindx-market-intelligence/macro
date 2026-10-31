# INTL-GS Wave 5 census — §14 evidence map + IM18 dependencies (2026-10-31)

Read-only census for the Fable Meta-CEO seat (d7c4f490) before commissioning Wave 5.
Base: origin/main 6e721225979bc786e3a756cb41fdf71665e4efbe. No source changes; this file is the only artifact.

## Part C — seat summary

- **§14 counts: 14 DONE / 6 PARTIAL / 1 GAP** (21 rows). Engine layer is broadly proven on main;
  the open surface is UI-view rows, cross-surface identity, correction propagation and served-path/browser proof.
  324 tests passed green in this worktree across 15 suites; 11 failures were all environment artifacts
  (sparse site/, host-only data/fred parquet, missing `rjsmin`/`playwright` modules) — each diagnosed and
  the two foundation facts re-proven green via git-object replication (see appendix).
- **IM18 obligations × incumbent owners × custody risk (detail in Part B):**
  1. History/scenarios (IM06) — MERGED on main via PR #8527 (`lib/intl_history_mount.py`,
     `templates/intl_workspace_scenario.js`, history DOM ids); risk **NO** for new-module extension,
     **YES** for changing the accepted history publication contract (incumbent Paper-waves carrier; #8754
     overlaps the same workspace files, open, holds IW2 Saved/Terminal custody).
  2. International Investigation adapter (IM08) — status `todo`, **no adapter exists on main**; incumbent
     Saved surface is `templates/fif_saved_briefcase.js` (`investigation_manifest.v2`, X2-b Terminal carrier);
     risk **YES** (owner: WS-PAPER-INTERNATIONAL-WAVES IM08 + #8754 custody).
  3. Saved extension (IM09) — depends on IM08 (todo); risk **YES** (#8754 custody, updated 2026-10-31).
  4. Watch-condition evaluation/alerts — incumbents `engine/alerts.py`, `lib/user_prefs.py` ALERT_CATEGORIES
     (B-F08-1a), `lib/macro_suite_labels.py` ALERT_KIND (declared, not offered), `lib/intl_workspace_history.py`
     `_TRACK_FIELDS` (alert_count/hit_rate/false_alarms already modeled); PR #9513 ROR-1 (OPEN draft) holds the
     global warning client mount; risk **NO** for a GS-local evaluator, **YES** for riding the Terminal
     delivery drain / warning-client mount.
  5. Evidence identity / revision / correction — `engine/intl_global_observation.py` observation_id
     (deterministic, identity-only), `engine/intl_rates.py` saved_revision, incumbent byte-identity pattern
     `engine/capital_structure/saved_scenarios.py`; no intl correction chain; risk **NO** for GS-engine
     receipts, **YES** for cross-surface (Terminal/US/ontology) unification.
- **Three cheapest DONE-able §14 rows:** Graph boundary (label rule in the dossier builder + one test);
  Legacy continuity (CI-green quote of the already-wired `intl_workspace_legacy_navigation.test.cjs`);
  Cross-surface consistency (reuse the deterministic observation_id + one cross-surface identity test).
- **Three hardest:** Correction propagation (new engine chain + ontology records); Served-path proof
  (entitled-browser journeys on the live URL after views land); Publication retention (one full subsequent
  publisher cycle retaining accepted GS views + live re-proof).
- **Recommended Wave 5 cut:** land the **engine-side IM18** with zero-child lanes and without touching
  #8754/#9596 — (a) a `replay` view builder over the already-proven point-in-time chains
  (`engine/intl_global_dislocation.py:398`, `engine/intl_global_dollar_credit.py:432`), (b) a GS-local
  watch-condition evaluator reading the observation set + intl history `_TRACK_FIELDS` (pure engine + tests),
  (c) a correction-receipt skeleton (invalidation + visible revision, saved evidence never erased) as a new
  module. **Must wait for incumbent custody:** the Investigation/Saved integration (IM08/IM09, #8754),
  scenario persistence through the accepted IM06 publication contract, and cross-surface evidence-identity
  unification with Terminal/US research owners.

---

## Part A — §14 hard acceptance tests → evidence map

Status legend: DONE = semantics proven on main and a test ran green in this worktree (tail quoted in the
appendix). PARTIAL = engine or CI evidence exists but a required element is missing. GAP = no owner on main.
Owner lane legend: W2A = IM13 scanner, W2B = IM14 dossier, W3U = IM15 dislocation UI, W4B = IM17 transmission
UI, IM18 = Wave 5, records = records/handoff, served = served-path proof, OOP = OUT OF PROGRAMME (incumbent
owner outside this programme).

| # | Test | Status | Evidence on main (run green here unless noted) | Missing for DONE | Owner lane |
|---|---|---|---|---|---|
| 1 | Frozen-universe invariance | DONE | `tests/test_intl_global_universe.py:283` `test_frozen_universe_invariance`; frozen 63-jurisdiction roster + `roster_digest` `engine/intl_global_universe.py:165`, config `config/intl_global_universe_v1.json`; 11-market graph pinned by `engine/contagion_links.py` (28 tests green) | Nothing at engine level; scanner market-add path proves it end-to-end in UI | W2A |
| 2 | Coverage vector | DONE | `tests/test_intl_global_universe.py:154` `test_coverage_summary_is_a_vector_not_a_percentage`; `tests/test_intl_global_acceptance_matrix.py:136` `test_by_capability_equals_coverage_summary`, `:324` `test_coverage_board` | Coverage board UI (view `coverage` builder absent — `lib/intl_surveillance_mount.py:44-45`) | W2A |
| 3 | Denominator integrity | DONE | `tests/test_intl_global_universe.py:222` `test_missing_data_never_improves_a_capability`, `:245` `test_withdrawing_each_feeding_row_drops_its_capability_to_unavailable`, `:272` denominators; matrix `:183` downgrades never improve | Benchmark-admission clause exercised at UI acceptance when scanner lands | W2A |
| 4 | Graph boundary | PARTIAL | Fixed 11-market set + structural anchors proven: `engine/contagion_links.py`, `tests/test_contagion_links.py:138` `test_structural_shape`, `:152` `test_structural_anchors` (28 green) | No engine/label path yet emits a "qualified candidate / structural research" label for an out-of-graph market (grep empty); display rides the dossier/scanner surfaces | W2B |
| 5 | Stable aggregate meaning | DONE | `tests/test_intl_global_acceptance_matrix.py:126` `test_counts_only_output`, `:301` `test_by_region_aggregates`; US Risk Radar isolation `tests/test_risk_radar_intl_profiles.py` (12 green) | Nothing; radar incumbent owns its outputs | OOP |
| 6 | Session cutoff integrity | DONE | `engine/intl_transmission_evidence.py:88-91` pending statuses, `:131` pending wording, `:893`, `:985`; `tests/test_intl_transmission_evidence.py:509` pending assertion (21 green); clock precision `session_date` `engine/intl_global_observation.py:29` + `tests/test_intl_global_observation.py:107,116` (18 green) | Nothing at engine level; pending wording display rides W4B | W4B |
| 7 | Return identity | DONE | `tests/test_intl_global_observation.py:62-70` worked example (+5% local, −10% FX → −5.5% USD, residual ≤ 1e-9), `:140` id deterministic, `:154/:166` bases never mix; adapter `tests/test_intl_global_observation_adapter.py:141` hedged never borrows unhedged (6 green) | Nothing at engine level; scenario UI rebinding rides IM18 | IM18 |
| 8 | Closure/suspension honesty | DONE | `engine/intl_global_universe.py:47-48` `market_closed`/`suspended` states; `tests/test_intl_global_dislocation.py:778` `test_no_trading_language_in_any_receipt`, `:360` exclusions counted and change nothing (27 green) | Dated retained-observation display in dossier/history UI | W2B |
| 9 | Common-shock counterexample | DONE | `engine/intl_transmission_evidence.py:96` COMMON_SHOCK_STATUSES, `:120-121` min markets/regions, `:156` "attribution … stays undetermined", `:178` basis; `tests/test_intl_transmission_evidence.py` (21 green) | Nothing at engine level; transmission board wording rides W4B | W4B |
| 10 | Dollar-risk counterexample | DONE | `tests/test_intl_global_dollar_credit.py:607` `test_fx_observation_never_upgrades_funding`, `:638` `test_context_receipts_never_upgrade` (22 green; 2 real-store tests env-blocked, see appendix) | Real-store proof needs the host FRED parquet store (`data/fred/*.parquet` untracked at HEAD); board 12 UI rides a later UI wave | OOP |
| 11 | Opportunity/fragility coexistence | DONE | `engine/intl_global_dislocation.py:74-81` INTERPRETATION_LIMITS ("not a trading signal … or a recommendation"); `tests/test_intl_global_dislocation.py:187` vocabularies frozen, `:797` outputs closed; zero coupling to dollar-credit module (grep empty) — capabilities cannot gate each other | Dislocation board 9 UI rides W3U | W3U |
| 12 | Missing-data non-improvement | DONE | `tests/test_intl_global_universe.py:222/:245`; matrix `:183`; `tests/test_intl_global_dislocation.py:336` `test_withdrawing_a_reference_never_improves_a_result` (27 green) | Scanner coverage display of the withheld verdict | W2A |
| 13 | Point-in-time replay | DONE | `tests/test_intl_global_dislocation.py:398` `test_point_in_time_replay_equals_the_filtered_list`; `tests/test_intl_global_dollar_credit.py:432` `test_point_in_time_production_receipts` | Replay view builder (view `replay` absent) — the IM18 deliverable | IM18 |
| 14 | Cross-surface consistency | PARTIAL | observation_id binds identity only `tests/test_intl_global_observation.py:140`; intl→country receipt market-mismatch guard `scripts/build_intl.py:120-124`; radar intl profiles green | No unified evidence-identity / first-qualified / revision contract across International + country + US surfaces | IM18 |
| 15 | Proxy honesty | DONE | `engine/intl_global_acceptance_matrix.py:64-85` proxy law ("a proxy satisfies a requirement only at its actual population … never fulfils a jurisdiction requirement"); `tests/test_intl_global_acceptance_matrix.py:253` `test_permitted_measures_law` (9 green); OAS context sources `engine/intl_global_dollar_credit.py:8` | Dossier labeling of proxy populations | W2B |
| 16 | Correction propagation | GAP | Only a display label today: `lib/intl_gs_display.py:116` `corrections_none`; incumbent byte-identity/non-erasure pattern `engine/capital_structure/saved_scenarios.py:79` | An intl correction chain: corrected source → dependent invalidation → visible revision without erasing saved evidence | IM18 |
| 17 | Rights isolation | DONE | `tests/test_intl_global_universe.py:188` rights vocabulary imported, `:202` `test_rights_isolation`; `tests/test_intl_global_dollar_credit.py:388` rights variants abstain; Wave 0 production boundary: `/intl_data.json` 401 while nine presentation assets 200 anonymous (handoff `research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md:55-58`) | Periodic negative re-proof on the served URL | served |
| 18 | Served-path proof | PARTIAL | Wave 0 PRODUCTION_PROOF: anonymous 200s + negative 401/404 boundary (handoff `:55-58`); browser-level foundation suite is CI-owned (`tests/intl_gs_foundation_browser.test.cjs`, wired `.github/ci/legacy-jobs.yml:10092`) | Entitled-browser journey + navigate/state-preserve on the served URL (HTTP 200 alone fails); not runnable in this worktree (playwright absent) | served |
| 19 | Publication retention | PARTIAL | Publisher path green: `tests/test_intl_eod_publication.py` (23), `tests/test_intl_macro_publication_build.py` (13); surveillance seam wired `scripts/build_intl.py:224-226` | No GS view has completed a subsequent publication cycle yet (builders absent on main) | served |
| 20 | Legacy continuity | PARTIAL | `tests/test_intl_workspace_integration.py:112` macro mount once, `:126` library, `:152` stocks-mode isolation (11 green); `tests/intl_workspace_legacy_navigation.test.cjs` (11 tests, hash routing + state) is CI-owned and could not run here (playwright missing) | A green run quote of the cjs suite (CI or a playwright-capable host); navlinks untouched | records |
| 21 | Bilingual/theme semantics | PARTIAL | `tests/test_intl_gs_foundation.py` 98 green incl. STATE_EN/STATE_ZH vocabulary (2 site-sparse failures re-proven green via git-object replication); `tests/test_freshness_chips_language_invariant.py` (11 green); W2F dual-theme evidence `mockups/evidence/intl-gs-w2f/` (sparse-omitted here) | Browser-level both-themes/narrow-layout proof for the GS boards after W3U/W4B land (crops per the UI evidence law) | records |

Notes: four UI views (W2A scanner/coverage, W2B dossier, W3U dislocations, W4B transmission) were running on
parallel fabric lanes at census time (`agentos/workstreams/WS-INTL-GLOBAL-SURVEILLANCE.md` current-result
table); rows 4/6/9/11 carry their residual owner accordingly, not a GAP. `lib/intl_surveillance_mount.py:45`
expects `lib.intl_gs_{view}_view` builders — none exist on main yet, so all seven views currently mount
`not_built` by design (independent-failure seam, `lib/intl_surveillance_mount.py:138-145`).

---

## Part B — Wave 5 / IM18 dependency census

### B1. IM06 — history/scenarios owner (incumbent, on main via MERGED PR #8527)

- Files: `lib/intl_history_mount.py` (`attach_history(workspace, *, registry, sources)` at `:20`,
  `project_history_read` consumed at `scripts/build_intl.py:120`); `lib/intl_workspace_history.py`
  (pure projection; `_READ_STATES`/`_PERMISSIONS`/`_SCORES`/`_TRACK_FIELDS` at `:12-15` —
  `market_id, graded_count, alert_count, sample_dates, precision, hit_rate, lift, false_alarms, drawdowns,
  qualification_notes`); `templates/intl_workspace/history.html.j2` (DOM ids `im-history*` `:12-31`,
  scenario block `im-scenario-local/fx/format/confirm/reset/result` `:74-97`);
  `templates/intl_workspace_scenario.js` (pure draft reducer `:192-213` with prototype/depth/key guards;
  `calculateScenario(localPercent, fxPercent)` `:114` — binary-unit USD composition matching the §14
  identity); `templates/intl_workspace_state.js` (in-memory view/market/horizon/basis restore via
  `return_stack` `:390-397`); `scripts/build_intl.py` (`_history_publication_sources` `:108-127`,
  `attach_history` `:206`, receipts dict `_intl_history_receipts` `:363`).
- Interfaces: build-time history receipts (JSON: read states, permissions, scores, track fields) projected
  per market and guarded for market mismatch; scenario draft shape (arrays ≤ 40 keys, no prototype keys);
  workspace state machine (view/basis/horizon context).
- What persists today: server-side history receipts through the nightly build only. **No durable client
  persistence at all** — grep for localStorage/sessionStorage across `templates/intl_workspace*` and
  `templates/intl_workspace/` returns nothing; scenario drafts are ephemeral in-memory reducer state.
- Tests: `tests/test_intl_workspace_history.py` (frozen contract, detached IO, denied history),
  `test_intl_workspace_history_independent.py`, `test_intl_workspace_history_render.py`,
  `test_intl_workspace_history_ui_independent.py`, `intl_workspace_history_controller.test.cjs`,
  `intl_workspace_history_independent.test.cjs`, `intl_workspace_scenario_draft.test.cjs`,
  `intl_workspace_scenario_draft_independent.test.cjs`, `intl_workspace_scenario_math.test.cjs`.
- Owner: WS-PAPER-INTERNATIONAL-WAVES IM06 (`agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md:96-102`,
  "publish the accepted History/scenario integration on PR8527" — now MERGED, head
  `claude/ssd-paper-international-waves-ad8d40c8d3b06fff`).
- IM18 would add: durable scenario persistence + evidence-bound replay through these contracts.
- Custody risk: **NO** for new-module extension (all of the above is on main); **YES** for modifying the
  accepted history publication contract or the workspace files #8754 also touches.

### B2. IM08 — International Investigation adapter

- Grep `investigation` across lib/scripts/templates/engine: the only product surfaces are the commodity
  workspace DOM (`templates/commodity-workspace.js:241-251`, `#cw-investigation-*` — selected-cause panel
  with invalidate/tests disclosure) and the Saved briefcase manifest
  (`templates/fif_saved_briefcase.js:28` `MANIFEST_V2_SCHEMA = 'investigation_manifest.v2'`, X2-b Terminal
  investigations carrier `:31-33`). **No International/Terminal investigation adapter for intl exists.**
- Owner: WS-PAPER-INTERNATIONAL-WAVES IM08 (`agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md:113-117`,
  status `todo`, depends on IM00) + #8754 (open, head `sol/manual-paper-waves-01a1101f-release-r2`, updated
  2026-10-31T05:39:44Z, title "International workspace: preserve context, data scope and keyboard reading
  paths"; body states "Source rights, Saved custody and release permissions are unchanged" — it holds IW2
  Saved/Terminal custody; landmines: never touch).
- IM18 would add: the adapter itself, against the incumbent Investigation interface.
- Custody risk: **YES** — IM08 is the incumbent programme's own todo and its natural carrier is the #8754
  workspace line; a Wave 5 seat must not build into that custody.

### B3. IM09 — Saved extension / watchlist / thesis

- Incumbent Saved surface: `templates/fif_saved_briefcase.js` — localStorage persistence
  (`STORAGE_KEY 'mastermind.filing_forensics.saved_research.v1'` `:27`), manifest v2 with owner `fif`
  (`:31`), bounded views/evidence-refs/metric-ids/periods/cells (`:32-39`), A→B migration carrier
  (`CARRIER_KEY 'fif_saved_research'`, X2-b Terminal investigations `:29-31`), never writes back blanks.
  Related: `engine/capital_structure/saved_scenarios.py` (server-side saved-scenario identity — byte digest
  `:79`, generation ids, "identity drift" refusal `:345`), `templates/watchlist.js` (legacy watchlist DOM).
- Owner: IM09 (`WS-PAPER-INTERNATIONAL-WAVES.md:118-121`, status `todo`, depends on IM08); custody with
  #8754 (unpushed commits elsewhere per programme notes — never check out, never push).
- IM18 would add: the International Saved extension once IM08 lands.
- Custody risk: **YES** (hard dependency on IM08 + #8754 custody).

### B4. Watch-condition evaluation / alerts

- Incumbents: `engine/alerts.py` (`Alert` `:27`; rule functions transition_state_change `:71`,
  axis_confidence_floor `:88`, sector_rs_percentile_cross `:107`, holdings_active_changes `:136`,
  sector_holdings_accumulation `:166`, net_liquidity_roc_flip `:201`); `lib/user_prefs.py:68`
  ALERT_CATEGORIES (B-F08-1a enqueue-only, email opt-in `:79-80`); `engine/alert_delivery_drain.py`
  (fetch_user_record/READ_OK drain); `engine/alert_time.py`, `engine/alert_triage.py`;
  `lib/macro_suite_labels.py:1125` ALERT_KIND — "declared, not offered" label vocabulary.
  Intl-specific: `lib/intl_workspace_history.py:15` `_TRACK_FIELDS` already models watch-condition
  evaluation statistics (graded_count, alert_count, hit_rate, lift, false_alarms, drawdowns).
- PR #9513 "[ROR-1][DRAFT] Preserve global warning client through standalone and closing-bell page renders"
  — OPEN draft, head `sol/ror1-alert-write-time-mount-20261016-c2`; holds the global warning-client mount
  work (read-only here; never touched).
- IM18 would add: a GS-local watch-condition evaluator over the observation set + history track fields.
- Custody risk: **NO** for a GS-local evaluator (all inputs on main, pure engine); **YES** for riding the
  Terminal alert delivery drain or the #9513 warning-client mount.

### B5. Evidence identity / revision / correction propagation

- Owners: `engine/intl_global_observation.py` — observation_id deterministic and binds identity only
  (`tests/test_intl_global_observation.py:140` `test_observation_id_binds_identity_only_and_is_deterministic`);
  `engine/intl_rates.py:235-239` saved_revision identity policy; incumbent non-erasure/byte-identity pattern
  `engine/capital_structure/saved_scenarios.py:79` (result byte digest; re-save ≠ outcome drift);
  intl display exposes only `corrections_none` today (`lib/intl_gs_display.py:116`).
- No intl correction/invalidation chain exists (row 16 GAP). The `research_vault`/`research_codegen`
  evidence_id system is a separate research-codegen admission surface, not the market-surface identity.
- Custody risk: **NO** for GS-engine receipts (new module on main contracts); **YES** for unifying identity
  with Terminal/US research surfaces (ontology records owners).

### Served-path proof tooling (`ls scripts | grep -i -E "proof|live|probe"` + live_proof refs)

- `scripts/fif_coverage_proof.py` — proves the FIF saved-research coverage contract.
- `scripts/gmi_coverage_proof.py` — proves GMI coverage of the promoted surface.
- `scripts/ci_semantic_proof.py` — CI semantic pack proof (contract-delta class).
- `scripts/check_live_worker.py` / `check_vps_live_health.py` / `check_nightly_liveness.py` — liveness of
  the live worker / VPS / nightly pipeline.
- `scripts/marketing_liveness_tripwire.py` — public marketing-page liveness tripwire.
- `scripts/am_edition_live.py`, `verify_stock_seasonality_live.sh`, `reconcile_prophet_live.py` —
  per-surface live verifiers/reconcilers.
- `grep -rn -l "live_proof" research` → only `research/MARKET_ONTOLOGY_META_CEO_CHARTER_2026_09_06.md:502`
  (a Meta-CEO return-schema field, not a script). The Intl-GS asset proof is **not committed**:
  `scratchpad/prove_intl_assets.sh` (handoff `:39,:51`) is the Wave 0 anonymous-200/401 prover and lives in
  the seat scratchpad — Wave 5 should commit an owned served-path prover under `scripts/`.

---

## Appendix — commands run (tails quoted verbatim)

Base check: `git rev-parse HEAD` → `6e721225979bc786e3a756cb41fdf71665e4efbe` (clean; sparse profile omits
data/site/mockups/verify_shots; `scripts/worktree_sparse.py add data/fred` refused — "not tracked at HEAD:
data/fred", i.e. the FRED parquet store is host-only).

```
=== tests/test_intl_global_acceptance_matrix.py ===   .........  [100%]  9 passed in 0.75s
=== tests/test_intl_global_universe.py ===            .............. [100%]  14 passed in 2.35s
=== tests/test_intl_global_observation.py ===         .................. [100%]  18 passed in 0.86s
=== tests/test_intl_global_observation_adapter.py === ......  [100%]  6 passed in 3.60s
=== tests/test_intl_global_dislocation.py ===         ...........................  [100%]  27 passed in 1.92s
=== tests/test_intl_global_dollar_credit.py ===       2 failed, 22 passed in 1.35s
    FAILED test_production_receipts_real_store / test_real_dollar_series_qualified_with_fixture_row
    E  FileNotFoundError: [Errno 2] No such file or directory: 'data/fred/DTWEXBGS.parquet'
    (data/fred parquets untracked at HEAD — host-store-dependent, not a main defect)
=== tests/test_intl_gs_foundation.py ===              2 failed, 98 passed in 13.71s
    FAILED test_a1_superseded_tokens_and_literal_fallbacks_absent / test_site_css_is_byte_identical_to_template
    E  FileNotFoundError: .../site/intl_workspace_surveillance.css  (sparse site/)
    Re-proven green at the base revision without materializing site/ (0.73 GiB):
      git show HEAD:site/intl_workspace_surveillance.css | cmp - templates/intl_workspace_surveillance.css
        → BYTE-IDENTICAL (git-object proof)
      replicated test_a1 scan (A1_SUPERSEDED needles + var() fallback pairs + pseudo-element rule)
        → superseded-token hits: NONE; opened 16 == allowed 16; pseudo-after-modifier: none (pass)
=== tests/test_intl_workspace_integration.py ===      ...........  [100%]  11 passed in 3.55s
=== tests/intl_workspace_legacy_navigation.test.cjs (node --test) ===
    # pass 0 / # fail 1 — Error: Cannot find module 'playwright' (not installed on this host;
    suite is CI-owned: .github/ci/legacy-jobs.yml:9849 and run step :10092)
=== tests/test_intl_transmission_evidence.py ===      ..................... [100%]  21 passed in 0.78s
=== tests/test_contagion_links.py ===                 ............................ [100%]  28 passed in 1.35s
=== tests/test_international_macro_dashboards.py ===  6 failed, 11 passed in 1.52s
    E ModuleNotFoundError: No module named 'rjsmin' (×3) + FileNotFoundError site/nav_market.js,
    site/japan.html (×3) — host-env/sparse artifacts, not main defects
=== tests/test_intl_eod_publication.py ===            ....................... [100%]  23 passed in 4.46s
=== tests/test_risk_radar_intl_profiles.py ===        ............ [100%]  12 passed in 1.52s
=== tests/test_freshness_chips_language_invariant.py === ........... [100%]  11 passed in 1.98s
=== tests/test_intl_macro_publication_build.py ===    ............. [100%]  13 passed in 1.63s
```

Discovery grep `grep -rn -l -E "intl_global|intl_gs|international" tests/ engine/ lib/ scripts/ | head -80`:
115 intl test files; engine owners `engine/intl_global_universe.py`, `intl_global_observation.py`,
`intl_global_dislocation.py`, `intl_global_dollar_credit.py`, `intl_global_acceptance_matrix.py`,
`intl_transmission_evidence.py`; lib owners `lib/intl_surveillance_mount.py`, `intl_gs_display.py`,
`intl_gs_observations.py`, `intl_global_observation_adapter.py`, `intl_history_mount.py`,
`intl_workspace_history.py`; build owner `scripts/build_intl.py` (+ `build_intl_library.py`).

Records read: `agentos/decisions/DEC-INTL-GS-R14-DESIGN-FREEZE.md`,
`DEC-INTL-GS-FRED-GOVERNMENT-SERIES-RIGHTS.md` (listed); Wave 0 PRODUCTION_PROOF checkpoints at
`research/INTL_GLOBAL_SURVEILLANCE_CONTINUATION_HANDOFF_2026-10-21.md:16-17,39,46-58`; workstream
`agentos/workstreams/WS-INTL-GLOBAL-SURVEILLANCE.md` (IM16 gap note `:84-89`, IM18 `:107-111`, landmines
#8754/#9596); `agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md:90-140` (IM06/IM08/IM09/IM10).

GitHub reads (read-only): `gh pr view 8754` (open; International workspace carrier; Saved custody unchanged;
head `sol/manual-paper-waves-01a1101f-release-r2`; updated 2026-10-31T05:39:44Z); `gh pr view 8527`
(MERGED, "feat(intl): compose Paper workspace with History and scenarios"); `gh pr view 9513` (OPEN draft,
ROR-1 global warning client). #9596 not read beyond standing programme records — never touched.

Green total in this worktree: 324 passed / 11 environment-failed (0 programme-failed) across 16 suite runs.
