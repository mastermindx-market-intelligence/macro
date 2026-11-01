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

## Post-census landings (seat, 2026-10-31)

Appended by records lane intl-gs-rec7-r2 on the seat's instruction; the measured body above is untouched.
All PR facts below verified 2026-10-31 via `gh pr view <n> --json state,mergeCommit,mergedAt,headRefOid,title`
(batch GraphQL form) unless marked seat-attested. These merges close or move §14 rows Part A mapped:

- **#10286 S14-CLOSE → main d444ae6713b008aede6197f01989d44fa5122e4c (10:45:49Z)**: engine/intl_global_graph_boundary.py
  + §14 closure tests — moves row 4 (Graph boundary, PARTIAL: engine/label path now emits the label), row 14
  (Cross-surface consistency, PARTIAL: cross-surface identity test) and row 20 (Legacy continuity, PARTIAL:
  legacy continuity evidence).
- **#10274 W5-WATCH → c784d045f3a76dd944a7cd8af2936bd505b02fa5 (09:34:05Z)**: engine/intl_global_watch.py —
  lands the Part C recommended cut (b) GS-local watch-condition evaluator.
- **#10275 W5-REPLAY → 6c13414f379941be2806de2a6bf839d0b2c8f62a (09:34:43Z)**: engine/intl_global_replay.py —
  recommended cut (a), the replay builder engine half for row 13's missing deliverable (view mounting per
  ORCH-5 F6 stays with the view layer).
- **#10276 W5-CORRECTION → cd195298c0748e06c80c11614c7b47c78a7e2835 (09:34:28Z)**:
  engine/intl_global_correction.py — recommended cut (c); moves row 16 (Correction propagation, GAP): the
  correction chain (invalidation + visible revision) now has an engine owner on main.
- **#10258 W4B transmission board UI → 949c6adac4bc48ca7f1198b189effa86871829b2 (09:33:22Z)**: presenter
  lib/intl_gs_transmission_present.py + templates/intl_workspace/transmission.html.j2 + CI job — moves the
  W4B residuals of rows 6 and 9; the production Transmission tab stays `not_built` BY DESIGN (no
  emission-permitted candidate source).
- **#10265 W3U dislocation explorer → 281e21c600ab5031805c33fa32711b8e02f3e53c (12:49:14Z)**: moves row 11's
  residual (dislocation board 9 UI).
- **#10278 W2B IM14 market dossier → a99b539578003e7dfd32394dc1e839cba7f8bb0a (15:05:04Z)**: moves the W2B
  residuals of rows 8 and 15 (dated retained-observation display; dossier proxy labeling) and is the surface
  carrying the row-4 chip under DEC:INTL-GS-GB1-GRAPH-BOUNDARY-CHIP (follow-up lane intl-gs-w2b-gb1-r1).
- **#10288 W2A IM13 global scanner + coverage view → 92881169bb888435ab84b40740212a1fb0876a77 (21:54:40Z)**:
  moves the W2A residuals of rows 1, 2, 3 and 12 (coverage board UI; scanner display of withheld verdicts);
  IM13 DONE.
- **#10296 W5-HARDEN → b3330f3cdd29ffef0260769c73764c9ce11f4a52 (11:51:13Z)**: test-only mutant kills H1–H8
  (closes ORCH-5 F7); hardens, does not by itself close a §14 row.
- Still open after these landings: rows 18/19/21 (served-path entitled-browser proof, publication retention
  cycle, both-themes browser proof) remain PARTIAL pending the nightly render + served-journey proof; row 16
  correction propagation moved off GAP but its §14 acceptance rides IM18 completion; #10341 raised the
  international-dislocation-explorer CI budget 8→15 (20:08:34Z) separately from the W2A budget raise.

## Addendum 2026-11-01 — §14 closure after gb1/pin1

Appended by the seat (Fable Meta-CEO d7c4f490, records r8, seat-direct after the fabric refused admission on
every host — ubuntu0 `host_disk_below_staging_reserve`, a capacity wait under the 2026-10-31 no-disk-reclaim
law). The measured body and the post-census section above are untouched. PR facts verified 2026-11-01 04:4xZ in
ONE batched read (`gh api graphql`, aliases per PR → state, headRefOid, mergeCommit.oid, mergedAt):

| PR | head | main | mergedAt (UTC) |
|---|---|---|---|
| #10288 W2A IM13 scanner + coverage | 74e28ce960bfe2608de1aeeeba8221f75a73e4a2 | 92881169bb888435ab84b40740212a1fb0876a77 | 2026-10-31T21:54:40Z |
| #10353 records r7 | ed9b641d62ab35ef997307a34a31a6d555ce6905 | 83a77d8533c6f885f6b061207d017f27cf485a78 | 2026-10-31T22:57:30Z |
| #10354 W2B gb1 graph-boundary label | ecbd01fb8cfb36b4972fca4b1b183249a0759d50 | aba326f385ea19672e1a87f47e97c25e01c3b6d1 | 2026-11-01T01:03:18Z |
| #10355 pin1 polish | 89d7be656c772cd051f31269a749df9b2a11684f | 4e1ae041040e638028f9b189fe6dfe932f4eb5b1 | 2026-11-01T02:32:05Z |
| #10341 dislocation-explorer budget 8→15 (other author) | 51b16608d57592b52d6c4b93877d65b2590a7c95 | dbaf1e07bcccf689a740ad3f1281c59ff1b9d946 | 2026-10-31T20:08:34Z |

**Served proof (seat curl 2026-11-01 04:4xZ, independent of any CI watcher):** `https://www.mastermind-x.com/intl.html`
HTTP/2 200, `Last-Modified: Sun, 01 Nov 2026 03:12:25 GMT`, etag `dmjjnurxkzx7dhgu2`, content-length 22649978;
served `<span data-graph-boundary="…">` chips = **640** (530 `structural_research` + 110 `structural_graph_member`,
0 `qualified_candidate` — correct, since production passes `edges=[]` / `edge_basis: "no_admitted_edge_set"` and no
qualified candidate can exist without an admitted edge producer). The pin1 head-row wrapper `intl-gs__edges__head`
counted **0** at probe time: the 4e1ae041 render was still queued behind render run 41259434450 (in_progress since
02:3xZ), so the pin1 layout polish is MERGED but **not yet served**. The served page carries no commit stamp;
attribution to aba326f3 is by content (gb1 chip present, pin1 wrapper absent). This is a content-level
PRODUCTION_PROOF for row 4, not the entitled-browser journey proof row 18 requires.

### Rows whose status changes

| # | Test | Was | Now | Citation |
|---|---|---|---|---|
| 4 | Graph boundary | PARTIAL | **DONE** | Engine label path `engine/intl_global_graph_boundary.py` (#10286 → d444ae67, gh-verified in the rec7 #10353 record); display: W2B dossier Typed-edges chip + EN/ZH footnote under DEC:INTL-GS-GB1-GRAPH-BOUNDARY-CHIP, gb1 #10354 → aba326f385ea19672e1a87f47e97c25e01c3b6d1 (tests T1–T7 in `tests/test_intl_global_graph_boundary.py` + `tests/test_intl_gs_dossier.py`, `[data-graph-boundary]` browser assertion in `tests/intl_gs_dossier_browser.test.cjs`, 64/64 evidence cells + 8 crops both themes); head-row placement pin1 #10355 → 4e1ae041040e638028f9b189fe6dfe932f4eb5b1; served: 640 labelled chips on the live page (above). Masterplan test: "an out-of-graph market displays structural research or a qualified candidate label, never an invented graph score" — 530 structural-research labels served, no score drawn, no edge implied. |
| 16 | Correction propagation | GAP | **PARTIAL** | `engine/intl_global_correction.py` on main via #10276 → cd195298c0748e06c80c11614c7b47c78a7e2835 (2026-10-31T09:34:28Z, gh-verified in the rec7 #10353 record): corrected source → dependent invalidation → visible revision, saved evidence never erased, at engine level. Missing for DONE: the surface/saved-investigation integration (rides IM18 + IM08/IM09 custody #8754). |

Rows re-examined and left unchanged (no cited PR closes the "Missing for DONE" column): 14 Cross-surface consistency
(PARTIAL — #10286 added the cross-surface identity test; the unified identity/first-qualified/revision contract
across International + country + US stays with the Terminal/US + ontology owners, ORCH-5 F4); 18 Served-path proof
(PARTIAL — the seat curl is anonymous HTTP 200 + content; "HTTP 200 alone fails", entitled-browser initialise /
navigate / state-preserve on the served URL is still unproven); 19 Publication retention (PARTIAL — the push-render
lane published the gb1 chip once at 03:12:25Z; the normal *subsequent* publisher cycle retaining it has not yet
run); 20 Legacy continuity (PARTIAL — `tests/intl_workspace_legacy_navigation.test.cjs` is CI-owned; a green-run
quote is the remaining step, no navlink was touched by any merged PR); 21 Bilingual/theme semantics (PARTIAL — the
W2B dossier board has both-theme, EN/ZH, 1440/390 evidence at gb1b/pin1 (`mockups/evidence/intl-gs-w2b/`); the
other GS boards' served both-themes/narrow proof is not yet recorded).

### Recount

Original table: **14 DONE / 6 PARTIAL / 1 GAP** (PARTIAL rows 4, 14, 18, 19, 20, 21; GAP row 16).
After this addendum: **15 DONE / 6 PARTIAL / 0 GAP** — row 4 → DONE; row 16 GAP → PARTIAL; PARTIAL set is now
rows 14, 16, 18, 19, 20, 21.

### Rows that stay PARTIAL — owner

- 14 Cross-surface consistency — Terminal/US + ontology owners (ORCH-5 F4); IM18.
- 16 Correction propagation — IM18 surface + IM08/IM09 custody #8754 (never touched by this programme).
- 18 Served-path proof — entitled-browser journey on the served URL (seat/records; needs a playwright-capable
  host or the CI browser job pointed at the live URL).
- 19 Publication retention — the next normal publisher cycle (nightly) retaining the GS views; records.
- 20 Legacy continuity — one CI-green quote of the legacy navigation suite; records.
- 21 Bilingual/theme semantics — served both-themes/narrow proof for Scanner / Dislocations boards; records.
- Deferred, not §14 rows: R2-01 scanner-abstain focus-state evidence cell; F10 structural CI-budget fetch fix (both
  international jobs do a full checkout AND a separate ~4-min `git fetch origin main` on hosted runners — shallow /
  base-only fetch, own PR); Transmission tab `not_built` BY DESIGN (no emission-permitted candidate source).

## Addendum 2026-11-01 (r9) — pin1 served, legend basis, F10

- **pin1 served (PRODUCTION_PROOF for row 4 placement).** Seat probe 2026-11-01 06:1xZ of
  `https://www.mastermind-x.com/intl.html`: HTTP/2 200, `Last-Modified: Sun, 01 Nov 2026 05:21:32 GMT`,
  etag `dmjmeq11txpydibom`; `intl-gs__edges__head` wrappers = **640**, `data-graph-boundary` chips = **640**.
  The chip now sits in the Typed-edges head row (pin1 #10355 → 4e1ae041); deferred F12 is closed in production.
  Row 4 is therefore served in full (engine #10286, display #10354, placement #10355). Counts unchanged:
  15 DONE / 6 PARTIAL / 0 GAP.
- **Legend basis for the 2026-11-01 row-4 flip (review INTL-GS-REC8 F-2).** The 2026-10-31 legend defines DONE as a
  test that ran green in this worktree with its tail quoted. The row-4 flip in the first 2026-11-01 addendum rests
  instead on tests merged through CI (gb1/pin1 suites in #10354/#10355, CI green at merge) plus the served chips;
  no local green tail was quoted. The basis is disclosed here; the count is unaffected.
- **records r8 merged.** #10362 → main `f2a7fe7436a755f47c584a1fcfb37b7ef6a85ba1` (2026-11-01T06:03:02Z), squash
  pinned to 8dbc2d5c after review INTL-GS-REC8 `PASS_WITH_NOTES` (native Opus read-only auditor; fabric refused).
- **F10 (structural CI-budget fetch fix, own PR).** PR #10367 OPEN (draft) on claude/intl-gs-f10-canonical-main: head 5ac89fd395432d688e13e583d1c15591adba58b8 (follow-up to the reviewed 8f1b1d5e; review INTL-GS-F10 PASS_WITH_NOTES with one SHOULD-FIX fixed in the follow-up; re-read INTL-GS-F10-AUDIT-2 PASS_WITH_NOTES at 5ac89fd3 with two test-hygiene NITs N5/N6 deferred to a later test PR), CI rollup pending at 06:4xZ; merge seat-only pinned to 5ac89fd3 after a green rollup including the international-dislocation-explorer check. Design: the `international-dislocation-explorer` legacy
  job acquires canonical main through `scripts/run_ci_pack.prepare_canonical_main` (blob-filtered, tag-free, fail
  closed) with a new validated `frozen_paths` keyword naming the three objects its guard compares, instead of an
  unrestricted post-checkout base fetch (~4 min on hosted runners). Budgets 15 / 20 unchanged. Not a §14 row.
- **GB1A ruling date (review F-3).** `DEC-INTL-GS-GB1A-CLOSURE-WIDENING-ACCEPTED` records `decided_at: 2026-10-31`;
  the ruling was made in the seat's 2026-10-31 local session and applied before the #10354 merge at
  2026-11-01T01:03:18Z; the exact UTC minute is not recorded, so the UTC calendar date may be 2026-11-01.

## Addendum 2026-11-01 (r10) — F10 merged, test-hygiene follow-up merged, R2-01 merged, §14 rows 20/21 closed, row 19 stays PARTIAL

- **F10 (structural CI-budget fetch fix).** PR #10367 MERGED → main c133b698b4960f5a2a8b4540e6b164c3c7c23e1b at 2026-11-01T07:40:51Z (squash pinned 5ac89fd3; merged by the seat watcher after ci-gate/ci-plan/fence-pack passed). Reviews: INTL-GS-F10 `PASS_WITH_NOTES` at 8f1b1d5e (one
  SHOULD-FIX fixed in the follow-up) and INTL-GS-F10-AUDIT-2 `PASS_WITH_NOTES` at 5ac89fd3 (native Opus read-only
  auditors; fabric refused on every host). The `international-dislocation-explorer` legacy job now acquires canonical
  main through `prepare_canonical_main(..., frozen_paths=...)`; budgets 15 / 20 unchanged; the job's PR-side time is
  to be re-measured before any budget change (on 2026-11-01 one read of the F10 ci run's job list was deferred by the
  CI read cooldown and a paginated read was refused by the shared-quota guard; not retried; next receiver: the F10 `ci` run 41280629630 (pull_request, success, #10367 head 5ac89fd3): read its job list in ONE unpaginated page (`per_page=100`, no `--paginate`), outside the read cooldown; the paginated shape was refused by the shared-quota guard and is not to be repeated). Not a §14 row.
- **F10 test hygiene (AUDIT-2 NITs N5/N6).** PR #10376 MERGED → main bacc2d765488de853291dc0f8d7c545d3b3ca29a at 2026-11-01T09:29:37Z (squash pinned d50f5839; merged by the seat watcher after ci-gate/ci-plan/fence-pack passed). The first PR (#10370) was based on F10's branch and was
  auto-closed by GitHub three seconds after the F10 squash merge deleted that branch (not retargeted); the identical
  reviewed blobs were re-homed onto main as a fresh commit. Review INTL-GS-F10-HYGIENE: AUDIT-1 `FAIL` at db8183ef
  (`monkeypatch.delenv` records no undo for an absent key, so the first isolation attempt moved the leak to module
  end) → repaired with explicit snapshot/restore yield fixtures in both pack test modules → AUDIT-2 `PASS` at
  7eae154c (auditor's own leak probe clean); carries by content identity. Two tests now prove `execute_pack`
  publishes the plan tree to the legacy step environment and never overrides an explicit `TESTED_TREE_SHA`
  (mutant-discriminating). Runtime unchanged.
- **R2-01 (W2A NIT — scanner-abstain focus crop).** PR #10384 MERGED → main 3d8ad3eb4c027126174fc2bf9f75c74f5bb04709 at 2026-11-01T09:36:34Z (squash pinned ee5ce58a; merged by the seat watcher after ci-gate/ci-plan/fence-pack passed; review INTL-GS-R2-01 PASS). Sibling pack
  `mockups/evidence/intl-gs-w2a/scanner-abstain-focus/` (8 rest + 8 real focus cells, tool 1.4.0, fixture site,
  `--as-of 2026-11-01T08:00:00Z`). Focus target = the scanner panel's no-data disclosure
  `details.intl-gs__nodata > summary.intl-gs__disclosure` (`tabindex=0`), the only focusable element in the
  abstain-state scanner panel; the scanner pack's `a[data-gs-select-market]` exists on the abstain page only inside
  the hidden dossier panel, so a first run with it was refused by the driver on all 8 cells and discarded. Second run:
  force gaps `[]`, console errors `[]`, failed responses `[]`. Review INTL-GS-R2-01 (native Opus read-only auditor)
  `PASS` with notes: ring present on all 8 focus cells, absent on all 8 rest cells; scroll-induced background /
  floating-button deltas identical to the accepted scanner pack; the selector matches 40 summaries but the ring landed
  on the visible one. Evidence only; the reviewed `scanner-abstain` pack is untouched. Not a §14 row.
- **§14 row 20 (Legacy continuity) → DONE.** The CI-owned browser suites ran on a playwright-capable host (seat Mac,
  Node playwright@1.63.0 = the same playwright version CI pins at `.github/ci/legacy-jobs.yml:10665`; `PLAYWRIGHT_CHROMIUM_CHANNEL=chrome` = the system Chrome channel, NOT CI's bundled Chromium from `npx playwright install --with-deps chromium`): `tests/intl_workspace_legacy_navigation.test.cjs`
  **14 pass / 0 fail** (12.4 s) and `tests/intl_workspace_library_controller.test.cjs` **18 pass / 0 fail** (60.5 s), on
  top of the 11 green `tests/test_intl_workspace_integration.py` cases already recorded; navlinks untouched. This is
  the exact gap the row named ("a green run quote of the cjs suite (CI or a playwright-capable host)").
- **§14 row 21 (Bilingual/theme semantics) → DONE.** Records r8 had tightened the open gap to **served** both-themes/narrow proof for the Scanner / Dislocations boards; this closes it on a served pack: `mockups/evidence/intl-gs-r21-served/` — `scripts/capture_page_evidence.py` 1.4.0 with `--base-url https://mastermind-x.com` (`target.kind=base_url`; a live origin does not disclose the revision it serves), routes `/intl.html?view=scanner&market=JP` and `/intl.html?view=dislocations`, **16/16 cells** = dark+light × desktop(1440×900)+mobile(390×844) × en+zh, anonymous access, `--as-of 2026-11-01T10:00:00Z`, console errors `[]`, failed responses `[]`, page-level horizontal overflow `false` at both viewports, while the manifest's heuristic `metrics.by_viewport.mobile.elements_wider_than_viewport` is 37 on both pages (elements wider than 390 px without page-level overflow; recorded, not interpreted). `crops/` (8 PNGs + `crops.json` recording route, selector, visible index and bounding box): the scanner market table at 1440 (`table.intl-gs__table--scanner`, 794×1134) and the phone market cards at 390 (`.intl-gs__mcards`; the table is `display:none` at ≤900 by design), plus the dislocation ranking table (`table.intl-dislocations__table`, 1210×472 at 1440, 234×2162 at 390), each in dark and light. Seat read of the crops (corrected after AUDIT-2): signed direction keeps its sign across both themes and **follows the locale colour convention** — en up = green / down = red, zh up = red / down = green (Australia +2.42 % local / +4.33 % USD; Japan −6.23 % / −6.40 %; in the zh 390 cards Euro area USD +0.57 % and local +2.24 % are red, FX −1.63 % is green) — and that mapping is identical in dark and light, so severity does not flip between themes. At 390 the Qualified / Display-permitted / Delayed-end-of-day qualifiers render as chips, column-level abstain renders as 未准入 labels, and the price-level abstain row (India, "Incumbent qualification withheld") sits behind the 展开全部 7 expand control, so it is not inside the narrow crop (it is in the 1440 crops). Disclosed bar change: the fixture-site packs `intl-gs-w3u/` (`site_dir`, crops present) and `intl-gs-w4b/` (`site_dir`, **no crops directory**) remain design-time evidence; the served pack is what closes the row. Vocabulary tests unchanged (98 + 11 green).
- **§14 row 19 (Publication retention) stays PARTIAL.** Correction of the premise: `render.yml` is NOT the only publisher of `site/` — it is triggered by `workflow_dispatch` and by pushes to main **filtered to `templates/**` with exclusions** (the top-level `templates/*.html|css|js|json|txt|svg`, the public-chrome partials, plans/seo_base/support/unsubscribe) plus the builder and post-render sweep script paths the file lists, while `daily.yml` (nightly cron 22:30 / 23:30 UTC) commits `site/` paths, `closing-bell.yml` (weekday cron 20:05 / 21:05 UTC) commits a provisional `site/`, `asia-close.yml` runs morning crons, `public-render.yml` is dispatch-only and `engine-render.yml` renders on `engine/**` pushes. No `.github/workflows/pages.yml` exists at bacc2d76 — the render.yml comment naming it is stale (AUDIT-2 correction). The gb1 chip was served at 2026-11-01T03:12:25Z (640 spans, 530 `structural_research` + 110 `structural_graph_member`) and the pin1 render served 640 head-row wrappers at 05:21:32Z — but pin1 shipped a change to the same feature, so it is not the "normal *subsequent* publisher cycle" r8 named, and the 530/110 split was not re-measured at 05:21. Missing for DONE: one probe of `mastermind-x.com/intl.html` after the next nightly (`daily.yml`) or an unrelated render showing the Graph-boundary chip with its source-qualification split and the GS views (scanner / dislocations / coverage) retained. R2-01 #10384 (merged 09:36:34Z) touched only `mockups/evidence/`, so it triggered no publisher.
- **§14 row 18 (Served-path proof) stays PARTIAL.** `tests/intl_gs_foundation_browser.test.cjs` **18 pass / 0 fail**
  (194.7 s) on the same host covers the anonymous browser half; the entitled-browser journey still requires a human
  sign-in (Chris) and is not claimed.
- **§14 recount after this addendum: 17 DONE / 4 PARTIAL (rows 14, 16, 18, 19) / 0 GAP.** Rung reached: MERGED for every
  lane including R2-01 (#10384 at 09:36:34Z), PRODUCTION_PROOF for row 4 content, not ACCEPTANCE by the commissioning authority.
- **Audit trail.** Independent read-only review INTL-GS-REC10 AUDIT-1 returned `FAIL` on the first r10 commit dd66d75d (3 major: stale workstream Remaining list; "MERGED for every lane" while #10384 was open; row 19 closed on a wrong publisher premise without a re-measured split; 4 minor: row 21 fixture-not-served + W4B without crops; row 20 CI-parity wording; F10 workstream clause dropped review facts; the dislocation re-measure named no run id). Every finding is applied in the first pinned follow-up (c63896bc); the first commit was never merged. AUDIT-2 on c63896bc returned `FAIL` on wording only (major: the crop reading said colour was kept across locales when the crops show the locale convention inverting it; minor: a non-existent `pages.yml` and an under-stated render.yml filter; the 390 abstain / 37-wide-elements nuance). Those three are applied in this second pinned follow-up; the artifacts, numstat, recount and the row-21 closure itself were PASS in AUDIT-2.
