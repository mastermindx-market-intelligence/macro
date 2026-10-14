# Q00 — Data OS verification baseline and discriminator map

**Status:** COMPLETE (lane O2-Q00, run id `dataos-o2-q00-1`, 2026-10-13).
**Scope:** measurement only — no code changed. This file is the lane's one owned path.
**D00:** cited frozen from `research/data_os_completion/2026-10-13/D00_SEMANTIC_DECISIONS.md`
(#9133, `52af4108676b`), read in full before any measurement.

## 1. Heads and pins

| what | value |
|---|---|
| Macro base (this lane's STEP-0 base, `origin/main`) | `eb7c4d674235` (2026-10-13T05:25:21-07:00, "research_vault: catalog 2026-10-13T12:25Z") |
| Macro D00.D6 pin `5569baad` | ancestor of base: YES (`git merge-base --is-ancestor` exit 0); identity `5569baad64b802` (2026-10-13T03:04:00-07:00, #9116) |
| Macro consumer-surface drift `5569baad..HEAD` over `lib/dataos config/dataset_registry.yml engine/basket_membership_pit.py` | EMPTY (`git diff --stat` prints nothing) — pinned surfaces did not move |
| Terminal head (`origin/master`, detached) | `f7bce8dcc4d7` ("T01 follow-ups … (#972)") |
| Terminal D00.D6 pin `4005275cc816` | ancestor of head: YES (exit 0); identity `4005275cc816` (2026-10-13T07:26:08+00:00, #981) |
| Terminal surface drift `4005275cc816..HEAD` over `ingest/ tests/test_build_universe_ohlc.py tests/test_ohlc_ingest_guard.py tests/test_macro_ohlc_leg.py` | EMPTY — pinned surfaces did not move |
| Worktrees | Macro `~/lanes/wt/dataos-o2-q00-1` (branch `lane/dataos-o2-q00-1`); Terminal `~/lanes/wt/dataos-o2-q00-term` (detached) |

Base sha note: this base may be newer than ORCH-2's judge base `f2a21e8d7f28`; the sha measured
here is `eb7c4d674235` as fetched in STEP 0 (no STACKED BASE was named in the header).

## 2. Commands (verbatim, in run order)

STEP 0 (from the shared clone, which was never otherwise touched):
```
cd ~/lanes/repos/macro && git fetch -q origin main && git worktree add -b lane/dataos-o2-q00-1 ~/lanes/wt/dataos-o2-q00-1 origin/main && cd ~/lanes/wt/dataos-o2-q00-1 && git rev-parse HEAD && git log -1 --format=%cI
cd ~/lanes/repos/mastermind-terminal && git fetch -q origin master && git worktree add --detach ~/lanes/wt/dataos-o2-q00-term origin/master && git -C ~/lanes/wt/dataos-o2-q00-term rev-parse --short=12 HEAD
```
Sparse materialization (deviation D-1 below; own worktree only):
```
cd ~/lanes/wt/dataos-o2-q00-1 && git sparse-checkout add '/research/data_os_completion/2026-10-13/'
```
STEP 1 (heads/pins):
```
git rev-parse --short=12 HEAD
git log -1 --format="%H %cI %s" HEAD
git merge-base --is-ancestor 5569baad HEAD; echo $?
git log -1 --format="%H %cI %s" 5569baad
git -C "$T" rev-parse --short=12 HEAD
git -C "$T" merge-base --is-ancestor 4005275cc816 HEAD; echo $?
git -C "$T" diff --stat 4005275cc816..HEAD -- ingest/ tests/test_build_universe_ohlc.py tests/test_ohlc_ingest_guard.py tests/test_macro_ohlc_leg.py
git diff --stat 5569baad..HEAD -- lib/dataos config/dataset_registry.yml engine/basket_membership_pit.py
```
STEP 2 (Macro file set; `<f>` = each of the 23 stems in §3; `<stem>` = `<f>`):
```
grep -l basket_membership_pit tests/*.py
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/<f>.py -q -p no:cacheprovider -rs --junitxml=~/lanes/ext/dataos-o2-q00-1.macro.<stem>.xml
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_dataos_*.py tests/test_price_ladder.py -q -p no:cacheprovider
```
STEP 3 (CI collection; `.github/` is sparse-omitted in this lane, so the byte-identical blob was
extracted to scratch first — line numbers are the file's own):
```
git show HEAD:.github/ci/legacy-jobs.yml > ~/lanes/ext/dataos-o2-q00-1.legacy-jobs.yml
grep -n <filename> ~/lanes/ext/dataos-o2-q00-1.legacy-jobs.yml
```
STEP 4 (Terminal, from `$T` root):
```
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_build_universe_ohlc.py tests/test_ohlc_ingest_guard.py tests/test_macro_ohlc_leg.py -q -p no:cacheprovider -rs --junitxml=~/lanes/ext/dataos-o2-q00-1.terminal.pytest.xml
cd $T/terminal && npm ci --no-audit --no-fund   # log: ~/lanes/ext/dataos-o2-q00-1.npm-ci.log, exit 0
npx vitest run lib/__tests__/barSnap.test.ts lib/__tests__/chartPanelPineSessionAnchor.test.ts lib/__tests__/flowStreamSessionRenewal.test.ts lib/__tests__/gexSessions.test.ts lib/__tests__/intradaySession.test.ts lib/__tests__/liveBarProjection.test.ts lib/__tests__/secondBars.test.ts lib/__tests__/sessionBars.test.ts lib/__tests__/suiteRegistrySplit.test.ts lib/__tests__/surfaceSessions.test.ts lib/__tests__/syntheticTouchHoverGuard.test.ts lib/__tests__/usEquitySessionClock.test.ts lib/__tests__/workspaceContextSession.test.ts --reporter=json --outputFile=/home/longr/lanes/ext/dataos-o2-q00-1.vitest.json
git -C "$T" status --short    # empty (node_modules ignored) — tree clean after npm/vitest
```
Terminal vitest file selection filter (`bar|ohlc|synthetic|session|adjust|split|dividend`,
case-insensitive) matched exactly the 13 files above out of 629 in `lib/__tests__/`; no file
matches `ohlc|adjust|dividend` by name.

STEP 6 (blocklist drift; run exactly once, no `--fix`):
```
python3 scripts/check_blocklist_drift.py
git status --short
```

## 3. Macro per-file table

Counts are read from the named junit XML (`~/lanes/ext/…`), not from memory.
`SPARSE-ARTIFACT` = the file fails only because a sparse-omitted path is absent in this lane's
checkout (`data/`, `contracts/`, `.github/`); the tree was NOT opted into full. All 23 files are
IN the CI collection (job named below); none is NOT IN CI COLLECTION.

| file | CI job(s) (`legacy-jobs.yml` line) | passed | failed | skipped | xfailed | errors | junit |
|---|---|---|---|---|---|---|---|
| tests/test_dataos_identity.py | dataos-foundation (23627/23645) | 110 | 0 | 0 | 0 | 0 | …macro.test_dataos_identity.xml |
| tests/test_dataos_nulls.py | dataos-foundation (23628/23648) | 72 | 0 | 0 | 0 | 0 | …macro.test_dataos_nulls.xml |
| tests/test_dataos_price.py | dataos-foundation (23629/23647) | 95 | 0 | 0 | 0 | 0 | …macro.test_dataos_price.xml |
| tests/test_dataos_prospective_reference.py | dataos-prospective-reference (23451/23492) | 47 | 0 | 0 | 0 | 0 | …macro.test_dataos_prospective_reference.xml |
| tests/test_dataos_quality.py | dataos-foundation (23630/23650) | 42 | 0 | 0 | 0 | 0 | …macro.test_dataos_quality.xml |
| tests/test_dataos_registry.py | dataos-foundation (23631/23649) | 36 | 0 | 0 | 0 | 0 | …macro.test_dataos_registry.xml |
| tests/test_dataos_security_master.py | house-law-registry (9858/9907); also named at 25765 (house-law-registry-code) | 94 | 38 | 0 | 0 | 72 | …macro.test_dataos_security_master.xml — SPARSE-ARTIFACT: `data/` (data/reference/*.parquet, data/symbol_directory/, data/stocks/) and `.github/ci/legacy-jobs.yml` absent; every failure/error message names one of those paths |
| tests/test_dataos_temporal.py | dataos-foundation (23632/23646) | 42 | 0 | 0 | 0 | 0 | …macro.test_dataos_temporal.xml |
| tests/test_dataos_web_api.py | dataos-web-workspace (23550/23569) | 64 | 0 | 0 | 0 | 0 | …macro.test_dataos_web_api.xml |
| tests/test_dataos_web_lab.py | dataos-web-workspace (23551/23569) | 48 | 0 | 0 | 0 | 0 | …macro.test_dataos_web_lab.xml |
| tests/test_dataos_web_lab_worker.py | dataos-web-workspace (23552/23570) | 32 | 0 | 0 | 0 | 0 | …macro.test_dataos_web_lab_worker.xml |
| tests/test_dataos_web_readers.py | dataos-web-workspace (23553/23570) | 63 | 0 | 0 | 0 | 0 | …macro.test_dataos_web_readers.xml |
| tests/test_dataos_web_workspace.py | dataos-web-workspace (23554/23571) | 37 | 0 | 0 | 0 | 0 | …macro.test_dataos_web_workspace.xml |
| tests/test_price_ladder.py | price-basis-census (21518; 3 real-store tests deselected there) | 37 | 0 | 4 | 0 | 0 | …macro.test_price_ladder.xml — the 4 skips are the file's own `@_REAL` skipif (committed price stores absent); the synthetic twins run and pin the contract |
| tests/test_basket_membership_pit.py | nw-lobe-unfreeze (13047/13105); unrun-intl-libraries (17409) | 21 | 0 | 0 | 0 | 0 | …macro.test_basket_membership_pit.xml |
| tests/test_cn_membership_pit_lane_gate.py | unrun-intl-libraries (17418) | 9 | 0 | 0 | 0 | 0 | …macro.test_cn_membership_pit_lane_gate.xml |
| tests/test_gmi_history_integrity.py | nw-lobe-unfreeze (12244/13105) | 68 | 0 | 0 | 0 | 0 | …macro.test_gmi_history_integrity.xml |
| tests/test_theme_graph_materialize.py | nw-lobe-unfreeze (13050/13105); unrun-intl-libraries (17448) | 90 | 18 | 0 | 0 | 0 | …macro.test_theme_graph_materialize.xml — SPARSE-ARTIFACT: `contracts/theme_graph/*.schema.json` (engine/basket_membership_pit.py:420 loads membership_collection.v2.schema.json → build returns 1 → the 8 `assert run()==0` failures) and `.github/workflows/daily.yml` |
| tests/test_theme_graph_membership_lifecycle.py | nw-lobe-unfreeze (13051/13105) | 9 | 30 | 0 | 0 | 0 | …macro.test_theme_graph_membership_lifecycle.xml — SPARSE-ARTIFACT: all 30 failures are `contracts/theme_graph/membership_collection…` FileNotFoundError |
| tests/test_theme_state_owner_adapter.py | nw-lobe-unfreeze (13002/13109) | 0 | 0 | 0 | 0 | 1 | …macro.test_theme_state_owner_adapter.xml — SPARSE-ARTIFACT: collection error; engine/theme_graph/theme_state_production.py:27 reads `contracts/theme_graph/theme_state.v2.schema.json` at import |
| tests/test_theme_state_production.py | nw-lobe-unfreeze (13003/13109) | 0 | 0 | 0 | 0 | 1 | …macro.test_theme_state_production.xml — SPARSE-ARTIFACT: same import-time schema read |
| tests/test_ths_weekly_rescrape.py | unrun-intl-libraries (17430) | 19 | 4 | 0 | 0 | 0 | …macro.test_ths_weekly_rescrape.xml — SPARSE-ARTIFACT: all 4 failures are `contracts/baskets_china_ths/…schema.json` FileNotFoundError |
| tests/test_us_basket_membership_pit.py | unrun-intl-libraries (17432) | 15 | 0 | 0 | 0 | 0 | …macro.test_us_basket_membership_pit.xml |

Combined §6 command totals: **38 failed, 819 passed, 4 skipped, 72 errors in 11.16s** — the sum of
the per-file table above (all failures/errors/skips belong to the SPARSE-ARTIFACT files and the
`@_REAL` skips; zero failures outside sparse artifacts).
CI-collection caveat recorded for honesty: `dataos-foundation`, `price-basis-census` and
`unrun-intl-libraries` carry `if: ${{ false }}` and are executed inside the ci-pack
(`run_ci_pack`), not as standalone workflow jobs; the `run:` steps quoted above are the
collection. `nw-lobe-unfreeze`, `house-law-registry`, `dataos-web-workspace` and
`dataos-prospective-reference` are ordinary collected jobs. No file in the set is outside every
`run:` line.

## 4. Terminal pytest table

From `$T` root, junit `~/lanes/ext/dataos-o2-q00-1.terminal.pytest.xml`:

| file | passed | failed | skipped | xfailed | errors |
|---|---|---|---|---|---|
| tests/test_build_universe_ohlc.py | 1 | 0 | 0 | 0 | 0 |
| tests/test_ohlc_ingest_guard.py | 7 | 0 | 0 | 0 | 0 |
| tests/test_macro_ohlc_leg.py | 7 | 0 | 0 | 0 | 0 |
| total | 15 | 0 | 0 | 0 | 0 |

CI collection (`$T/.github/workflows/ci.yml`): job `python` (ci.yml:347) runs
`python -m pytest tests/ -q` — whole-directory collection, so all three files are IN the real
collection (named nowhere individually; nothing in Terminal CI is).

`git -C "$T" status --short` after npm ci + vitest: EMPTY (clean).

## 5. Terminal vitest table

`npx vitest run` over the 13 name-matched files; JSON: `~/lanes/ext/dataos-o2-q00-1.vitest.json`
(log: `~/lanes/ext/dataos-o2-q00-1.vitest.log`, exit 0):

| file | tests | passed | failed |
|---|---|---|---|
| lib/__tests__/barSnap.test.ts | 6 | 6 | 0 |
| lib/__tests__/chartPanelPineSessionAnchor.test.ts | 2 | 2 | 0 |
| lib/__tests__/flowStreamSessionRenewal.test.ts | 6 | 6 | 0 |
| lib/__tests__/gexSessions.test.ts | 23 | 23 | 0 |
| lib/__tests__/intradaySession.test.ts | 9 | 9 | 0 |
| lib/__tests__/liveBarProjection.test.ts | 20 | 20 | 0 |
| lib/__tests__/secondBars.test.ts | 10 | 10 | 0 |
| lib/__tests__/sessionBars.test.ts | 26 | 26 | 0 |
| lib/__tests__/suiteRegistrySplit.test.ts | 29 | 29 | 0 |
| lib/__tests__/surfaceSessions.test.ts | 22 | 22 | 0 |
| lib/__tests__/syntheticTouchHoverGuard.test.ts | 3 | 3 | 0 |
| lib/__tests__/usEquitySessionClock.test.ts | 25 | 25 | 0 |
| lib/__tests__/workspaceContextSession.test.ts | 14 | 14 | 0 |
| total | 195 | 195 | 0 |

CI collection: jobs `hub` (ci.yml:37) and `terminal-unit` (ci.yml:53) run `npm test` =
`vitest run` (whole suite per config), which includes `lib/__tests__/`.

## 6. Design-vector oracle result

ACCEPTED INPUT, run by ORCH-2 (independent design-vector oracle, 12:3xZ,
`python3 -I verify_design_vectors.py` from an isolated directory), recorded verbatim:

```
{"synthetic_design_examples_checked": 12, "product_tests_executed": false, "network_or_market_data_access": false}
```
exit 0. Not re-derived here; the script is not on this host.

## 7. check_blocklist_drift result

```
$ python3 scripts/check_blocklist_drift.py
ERROR: research/DO_NOT_REBUILD.md not found     (stderr)
EXIT=1
$ git status --short                            (afterwards)
(empty) — tree still clean
```
Classification: SPARSE-ARTIFACT of the check itself, not drift. `research/DO_NOT_REBUILD.md`
exists at HEAD (blob `479c4d8ddc9a`, `git ls-tree HEAD -- research/DO_NOT_REBUILD.md`) but the
directory is outside this lane's inherited sparse set (deviation D-1 materialized only
`research/data_os_completion/2026-10-13/`), so the checker's first input lookup failed before any
scan. The packet's "run exactly once" rule was honored: no re-run after materializing. The drift
question (no DO_NOT_REBUILD artifact rebuilt) is therefore UNVERIFIED by this lane — ORCH-2
should re-run the checker on a checkout where `research/` is materialized. See GAPS.

## 8. Discriminator map

Method: every row below was written after reading the named test body in this tree at the base.
"real" = the body calls the real function under test (actual runtime evidence exists in §3–§5);
"fixture/mock-only" would be marked, but no row below is mock-only — every cited test exercises
the real function (some monkeypatch only the process/time boundary while the dispatch logic runs
real, e.g. the web_api worker-lifecycle tests). Guards: a filename match was never accepted as
coverage; rows with no base witness say `NO DISCRIMINATOR -> planned`.

### D00.D1 — modes and clocks
| rule | discriminator | note |
|---|---|---|
| per-dataset clocks declared (`KNOWN_AT_CLOCKS`) | tests/test_dataos_temporal.py::test_every_profile_has_a_known_at_declaration ; ::test_each_profile_declares_exactly_the_spec_clocks ; ::test_a_clock_value_is_its_column_name | real; ran green |
| DERIVED has no clock → read RAISES, never returns latest | tests/test_dataos_temporal.py::test_assert_pit_readable_raises_for_derived_which_has_no_known_at_clock | real `assert_pit_readable`/`PointInTimeError`; ran green |
| `known_at <= cutoff` row filter; publication ≠ observation (V08) | tests/test_dataos_temporal.py::test_as_of_filter_hides_the_revision_that_had_not_happened_yet ; ::test_as_of_filter_is_inclusive_at_the_boundary_instant ; ::test_known_at_prefers_published_at_over_ingested_at ; ::test_known_at_falls_back_to_ingested_at_when_the_source_never_said | real `as_of_filter`/`known_at`; ran green |
| later correction excluded from earlier observed view (V09) | tests/test_dataos_temporal.py::test_as_of_filter_hides_the_revision_that_had_not_happened_yet (revision_seq 1 invisible at earlier cutoff) | real; ran green |
| CURRENT / RECONSTRUCT / REPLAY as an explicit read `mode` | NO DISCRIMINATOR -> planned: ORCH-1 read_contract tests (`lib/dataos/read_contract.py` does not exist at base) | base has only the row-level as_of filter; the mode layer is the new contract |
| REPLAY without retained output → typed `NO_RETAINED_OUTPUT` | NO DISCRIMINATOR -> planned: ORCH-1 read_contract tests | same |

### D00.D2 — identity
| rule | discriminator | note |
|---|---|---|
| `security_id` = inception code, stable across curated rename | tests/test_dataos_identity.py::test_the_id_survives_the_rename_that_motivates_the_project | real; ran green |
| vendor alias namespace + half-open `[valid_from, valid_to)` per namespace (V12) | tests/test_dataos_identity.py::test_alias_table_answers_differently_either_side_of_the_mmc_rename ; ::test_alias_rows_carry_half_open_intervals ; ::test_the_lagging_rename_direction_is_the_same_table | real `VendorAliasTable`; ran green |
| reused/unmapped symbol is never guessed into an identity | tests/test_dataos_identity.py::test_an_unmapped_symbol_returns_none_rather_than_guessing_identity ; ::test_an_overlapping_pair_of_rows_is_refused_at_construction | real; ran green |
| issuer ≠ security (share classes distinct securities) | tests/test_dataos_identity.py::test_issuer_master_finds_securities_of_a_shared_issuer (GOOG/GOOGL two securities, one issuer) | real, ran green; committed-master twin: tests/test_dataos_security_master.py::test_goog_and_googl_are_two_securities_and_one_issuer (needs `data/` — SPARSE-ARTIFACT here; CI house-law-registry has it) |
| listing transfer ends one listing interval, security continues | tests/test_dataos_security_master.py::test_psky_and_skyd_are_one_security_across_the_venue_transfer ; ::test_psky_store_and_fetch_keys_did_not_move | read; requires committed master (`data/`) — SPARSE-ARTIFACT in this lane's run; CI job house-law-registry runs it with data/ |
| storage key is a frozen vendor spelling, never identity | tests/test_dataos_security_master.py::test_the_current_catalog_store_space_names_the_file_that_actually_exists ; ::test_the_membership_key_did_not_move_when_the_vendor_symbol_did | read; same `data/` caveat |
| merger/spin-off is successor economics, never identity overwrite; no second allocator | tests/test_dataos_identity.py::test_alias_table_answers_differently_either_side_of_the_mmc_rename (single table, no timeless map) + absence of any second allocator is enforced structurally (lib/dataos/identity.py is the only minter; see R00.03 row) | real; ran green |

### D00.D3 — economic units (one row per refusal/formula)
| rule | discriminator | note |
|---|---|---|
| RAW = printed exchange price; owns limit/tick/exchange-rule work; never adjusted | tests/test_dataos_price.py::test_the_raw_basis_owns_exchange_rule_work_and_tradj_is_barred_from_it ; ::test_every_basis_states_what_it_is_and_what_it_may_not_be_used_for | real `AdjustmentBasis` declarations (incl. DNR:KILL-CN-ADJUSTED-TAPE-LEGAL-LIMIT); ran green |
| measured store bases (which legacy column is RAW/SADJ/TRADJ) | tests/test_dataos_price.py::test_known_store_bases_carries_the_measured_truth ; ::test_the_same_column_name_means_different_bases_in_different_stores ; ::test_yahoos_two_columns_invert_intuition | real constants; ran green |
| SADJ formula `P_raw(t)/∏ r_e`, exact rationals, `ex_date > t`, share basis at `as_at` | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py (P03) | no split math exists at base |
| SADJ refuses already-adjusted / ambiguous / non-RAW input (adjust twice) | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py ; partial base witness: tests/test_dataos_price.py::test_every_censused_ambiguous_name_is_flagged (ambiguity detection real) and tests/test_price_ladder.py::test_cache_history_keeps_legacy_values_and_receipt_but_basis_unknown (unknown basis stays unknown, never guessed) | partial |
| ratio zero/negative/unknown refuses | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py (P03.04) | — |
| mixed OHLC bases refuse | partial base witness: tests/test_price_ladder.py::test_allow_unadjusted_false_refuses_to_mix (real refusal path, names the reason); full OHLC-row-mixed-basis refusal: NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py (P03.04) | partial |
| TRADJ never used as printed/executable price or cash ledger | tests/test_dataos_price.py::test_the_raw_basis_owns_exchange_rule_work_and_tradj_is_barred_from_it (KILL-CN clause in `TRADJ.unlawful_for`) | declaration-level; ran green |
| house TOTAL_RETURN view; declared reinvest/withholding; refusals when unknown (P04.03) | NO DISCRIMINATOR -> planned: independent holding/cash oracle under tests/ (P04) + tests/test_dataos_price_views.py | — |
| volume rule `vol_adj = vol_raw × r_e`; cash dividend never inverse split-volume | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py (P03.03) | no volume-adjustment test exists in the set at base (grep: none) |
| unsupported families (rights/spinoff/merger/… ) typed `UNSUPPORTED_ACTION`, never coerced | NO DISCRIMINATOR -> planned: tests/test_dataos_action_projection.py (P02.04) | — |
| discontinuity-inferred action never confirmed (P01.02) | NO DISCRIMINATOR -> planned: tests/test_dataos_action_projection.py / tests/test_dataos_price_revisions.py | no discontinuity-inference code exists in the set at base (grep: none) |

### D00.D4 — compatibility, absence, fallback
| rule | discriminator | note |
|---|---|---|
| fallback is context, never substitute; named when used | tests/test_price_ladder.py::test_a_stale_adjusted_rung_loses_to_a_COMPLETE_cache_and_says_so (passed-over rung must be named in `reason`); ::test_a_caller_that_refuses_unadjusted_gets_the_stale_adjusted_rung | real `resolve_close` on synthetic stores; ran green |
| member kept and disclosed, never silently dropped (V11) | tests/test_price_ladder.py::test_coverage_is_not_traded_for_basis_purity ; ::test_a_name_on_no_rung_is_null_with_the_ladder_disclosed (every rung attempted recorded) | real; ran green |
| coverage fields over the frozen population | tests/test_price_ladder.py::test_close_panel_stamps_every_name_and_counts_the_residual (unadjusted_tickers / unresolved_tickers / per-name source) ; typed absence vocabulary: tests/test_dataos_nulls.py::test_the_nine_missing_reasons_are_exactly_the_d6_vocabulary ; ::test_an_absence_with_no_reason_recorded_reads_as_no_coverage | real; ran green |
| members mixing bases refuse; current snapshot never stands in for historical | tests/test_price_ladder.py::test_allow_unadjusted_false_refuses_to_mix | real; ran green |
| never synthesize a traded open (Terminal `synthetic_open_deepstore` displayed, never passed as traded open) | NO DISCRIMINATOR -> planned: Terminal consumer-A vitest + tests/test_dataos_price_views.py | at base the producer tags it (ingest/build_universe.py:156 via ingest/sample_from_macro.py BAR_QUALITY) and the Terminal reader ignores extra keys (terminal/lib/embed/chartData.ts OhlcFile); no test asserts either half |

### D00.D5 — publication/correction
| rule | discriminator | note |
|---|---|---|
| receipt binds provenance for every input; coverage numbers add up | tests/test_dataos_security_master.py::test_the_receipt_carries_provenance_for_every_input ; ::test_the_receipt_reports_coverage_as_numbers_that_add_up ; ::test_the_receipt_row_counts_match_the_artifacts | read; requires `data/` — SPARSE-ARTIFACT here; CI house-law-registry |
| immutable complete output; rebuild never mints new ids; byte-stable noop | tests/test_dataos_security_master.py::test_nightly_is_a_byte_stable_noop_when_inputs_are_unchanged ; ::test_rebuilding_never_changes_an_existing_security_id ; ::test_the_stored_id_is_the_authority_not_the_derivation | read; `data/` caveat as above |
| interrupted publish → restore last good, never half-write (EFFECT_UNKNOWN analog) | tests/test_dataos_security_master.py::test_nightly_restores_last_good_on_an_unmodelled_rename ; ::test_nightly_restores_artifacts_on_a_mid_build_write_failure ; ::test_a_dry_run_writes_nothing | read; `data/` caveat |
| correction carries supersede semantics; prior refusal cannot vanish | tests/test_dataos_security_master.py::test_m5_a_row_pointing_at_a_superseded_id_is_pruned_and_receipted ; ::test_m1_a_registered_exception_loss_is_explained_not_silently_dropped | read; `data/` caveat |
| exact replay promised only with retained output (T02.01) | NO DISCRIMINATOR -> planned: ORCH-1 read_contract tests | same as D00.D1 REPLAY rows |

### D00.D6 — frozen matrix
| rule | discriminator | note |
|---|---|---|
| consumer A (Terminal daily OHLC producer) | tests/test_build_universe_ohlc.py::test_build_ohlc_json_drops_only_zero_volume_flat_non_trading_rows | real `build_ohlc_json`; ran green (Terminal pytest §4) |
| consumer A display half (ChartFrameBar data-origin readout) | NO DISCRIMINATOR -> planned: Terminal consumer-A vitest | readout not built at base |
| consumer B (DataWorkspace canonical read) | tests/test_dataos_web_workspace.py::test_read_filters_actual_rows_preserves_nulls_and_reproducible_query_receipt (`price_basis == "PRESERVED_AS_STORED_NOT_REBASED"`, reproducible query receipt sha256, source untouched) ; tests/test_dataos_web_api.py::test_materialize_binds_actual_parquet_columns_and_clock_without_rebasing ("no rebasing" asserted in source receipt) | real; ran green |
| consumer C (basket membership PIT composition) | tests/test_basket_membership_pit.py::test_asof_resolves_to_the_newest_snapshot_at_or_before_the_date ; ::test_added_and_removed_dates_apply_within_the_resolved_snapshot ; lane isolation: tests/test_us_basket_membership_pit.py::test_only_the_us_nightly_advances_the_us_store ; tests/test_cn_membership_pit_lane_gate.py::test_an_unnamed_lane_refuses_to_append | real; ran green |
| HK/CN identity-only enrollment | tests/test_dataos_identity.py::test_every_hk_spelling_pads_to_the_exchanges_five_digit_code ; ::test_unusable_hk_symbols_raise ; ::test_unusable_cn_symbols_raise ; ::test_the_measured_tushare_vs_repository_divergence_normalizes_to_one_key | real `normalize_hk_symbol`/`normalize_cn_symbol`; ran green; no HK/CN price-view positive witness anywhere in the set (consistent with D00.D6) |
| rights split (purchase/access ≠ computation ≠ redistribution; PROPOSED stays PROPOSED) | tests/test_tiingo_produced_contracts.py::test_bounded_evidence_supports_only_the_four_existing_research_contracts ; ::test_data_workspace_exposes_existence_without_granting_production_qualification | real `load_registry`/`validate_registry`/`DataWorkspace`; read this lane, NOT in the named file set so not run here — CI job dataos-web-workspace runs it (23571) |

### D00.01 — view-contract fields
| rule | discriminator | note |
|---|---|---|
| full view contract (purpose, identity, field_units, adjustment_reference, evidence_mode, coverage, refusal_reasons) | NO DISCRIMINATOR -> planned: ORCH-1 read_contract tests | no view_contract object at base |
| partial base witnesses for the evidence half | tests/test_price_ladder.py::test_evidence_mode_binds_the_exact_selected_file_column_and_basis ; ::test_evidence_mode_hashes_the_wide_cache_object_without_inventing_basis ; ::test_preloaded_wide_frame_never_borrows_a_configured_file_identity (unattested source stays `SOURCE_OBJECT_UNATTESTED`); tests/test_dataos_web_workspace.py::test_describe_reports_real_footer_clocks_and_unqualified_provenance | real; ran green |

### Acceptance ids
| id | discriminator | note |
|---|---|---|
| R00.01 | tests/test_dataos_registry.py::test_nothing_unproduced_is_marked_produced (real producer + real path pinned per PRODUCED row); ::test_the_committed_registry_loads_and_has_no_violations | ran green |
| R00.02 | tests/test_tiingo_produced_contracts.py::test_data_workspace_exposes_existence_without_granting_production_qualification (availability `NOT_ESTABLISHED_BY_DECLARATION`, production_qualification `NOT_ESTABLISHED_BY_THIS_ADAPTER`) | read; CI dataos-web-workspace |
| R00.03 | tests/test_dataos_registry.py::test_no_contract_declares_a_code_path_where_a_dataset_id_belongs ; ::test_code_consumers_and_the_graph_reverse_edge_are_two_different_notions ; ::test_the_real_dag_edges_and_reverse_edges_agree (one registry, one graph) | ran green |
| R00.04 | tests/test_tiingo_produced_contracts.py::test_bounded_evidence_supports_only_the_four_existing_research_contracts (exactly 24 vendor.tiingo rows, exactly 4 PRODUCED, other 20 PRODUCED-flip fails line 25) — corroborated statically: config has 20 PROPOSED + 4 PRODUCED vendor.tiingo rows | read; CI dataos-web-workspace |
| Q00.01 | process rule — witness is this document: accepted unchanged results reused (§3–§5 counts), no new defect claimed without a causal failing witness (§9 has none) | — |
| Q00.02 | enforced by this map's method: every cited row was body-read and executes the real function; the baseline counts mark SPARSE-ARTIFACT runs instead of counting them as proof | — |
| Q00.03 | enforced by §3's CI-job column: every counted file names its `run:` line; files in no run line would be marked NOT IN CI COLLECTION (none) | — |
| Q00.04 | witness: this lane changed no test; the synthetic-open labeling and disclosed fallback tests are recorded (§8 D00.D4 rows), not re-repaired | — |
| K01.01 | read-root enforcement half: tests/test_dataos_web_workspace.py::test_traversal_hidden_and_sensitive_paths_are_refused ; ::test_leaf_and_ancestor_child_symlinks_cannot_escape_root ; ::test_symlink_as_configured_root_is_refused ; ::test_hidden_entries_count_toward_scan_budget_without_being_returned. Principal/grant classes: NO DISCRIMINATOR -> planned: tests/test_dataos_rights_matrix.py | ran green |
| K01.02 | partial: tests/test_tiingo_produced_contracts.py::test_data_workspace_exposes_existence_without_granting_production_qualification (discovery ≠ qualification). Full purchase/access vs computation vs redistribution: NO DISCRIMINATOR -> planned: tests/test_dataos_rights_matrix.py | partial |
| K01.03 | tests/test_dataos_web_workspace.py::test_host_config_loads_only_explicit_roots_and_relative_registry ; ::test_host_config_rejects_unknown_fields_and_unsafe_bindings (request/config cannot widen roots); tests/test_dataos_web_api.py::test_dispatch_rejects_unknown_or_missing_action_fields ; ::test_lab_budget_and_arbitrary_calculation_fields_fail_before_run_artifacts | ran green |
| K01.04 | tests/test_dataos_web_readers.py::test_malformed_sources_have_no_raw_error_text (typed MALFORMED_SOURCE, raw error text suppressed); source-version binding: tests/test_dataos_web_workspace.py::test_expected_source_version_refuses_changed_source. Evidence-metadata/cache leak half: NO DISCRIMINATOR -> planned: tests/test_dataos_rights_matrix.py | ran green |
| P01.01 | tests/test_price_ladder.py::test_evidence_mode_binds_the_exact_selected_file_column_and_basis (exact file + column + basis + content sha256); tests/test_dataos_web_readers.py::test_real_parquet_metadata_keeps_source_columns_and_clocks | ran green |
| P01.02 | NO DISCRIMINATOR -> planned: tests/test_dataos_action_projection.py | see D00.D3 discontinuity row |
| P01.03 | partial: tests/test_dataos_nulls.py::test_the_nine_missing_reasons_are_exactly_the_d6_vocabulary (typed absence vocabulary, incl. NOT_YET_AVAILABLE vs SUPPRESSED_LICENSE); tests/test_basket_membership_pit.py::test_unknown_basket_is_not_reported_as_an_authoritative_empty (typed `unknown_basket`, pit=False). Full action-level no-action vs uncaptured/rights-limited: NO DISCRIMINATOR -> planned: tests/test_dataos_price_revisions.py | partial |
| P01.04 | partial: tests/test_dataos_temporal.py::test_as_of_filter_hides_the_revision_that_had_not_happened_yet (current knowledge never back-dated). Current-cumulative-factor labeling: NO DISCRIMINATOR -> planned: tests/test_dataos_price_revisions.py | partial |
| P02.01–P02.04 | NO DISCRIMINATOR -> planned: tests/test_dataos_action_projection.py (revision eligibility, cancellation non-retroactivity, same-day ordering, typed unsupported) | `lib/dataos/price_views.py` absent at base |
| P03.01 | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py | no split math at base |
| P03.02 | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py ; base context only: tests/test_dataos_price.py::test_known_store_bases_carries_the_measured_truth (which stores are already adjusted) | — |
| P03.03 | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py | volume rule row above |
| P03.04 | NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py ; partial: tests/test_price_ladder.py::test_allow_unadjusted_false_refuses_to_mix | — |
| P04.01–P04.03 | NO DISCRIMINATOR -> planned: independent holding/cash oracle under tests/ + tests/test_dataos_price_views.py | — |
| P04.04 | partial: tests/test_dataos_price.py::test_the_raw_basis_owns_exchange_rule_work_and_tradj_is_barred_from_it (TRADJ unlawful as printed/executable price). Brokerage-accounting half: NO DISCRIMINATOR -> planned: tests/test_dataos_price_views.py | partial |

## 9. Known defects with causal witness

**None observed.** Every failure and error in §3 is a sparse-omitted-path artifact of this lane's
checkout (message-level witness quoted in the table); the same files pass in their CI jobs, which
materialize `data/` and `contracts/`. No NEW defect is claimed, so per Q00.01 no causal failing
witness is required beyond those messages. The `@_REAL` price_ladder skips are the file's own
declared skip (synthetic twins pin the contract), inherited behavior, not a defect.

## 10. GAPS

1. **check_blocklist_drift produced no drift verdict** — it exited 1 on its missing sparse-omitted
   input (`research/DO_NOT_REBUILD.md`, present at HEAD as blob `479c4d8ddc9a`) before scanning.
   Run-exactly-once was honored; ORCH-2 should re-run it where `research/` is materialized. §7.
2. **Six Macro files are SPARSE-ARTIFACT in this lane** (test_dataos_security_master,
   test_theme_graph_materialize, test_theme_graph_membership_lifecycle,
   test_theme_state_owner_adapter, test_theme_state_production, test_ths_weekly_rescrape): their
   local red is caused solely by omitted `data/`, `contracts/`, `.github/` paths. Their green CI
   proofs live in jobs nw-lobe-unfreeze / house-law-registry / unrun-intl-libraries. The tree was
   NOT opted into full, per packet.
3. **test_tiingo_produced_contracts.py was read but not run** — it is not in this lane's named
   file set; it is cited as the R00.02/R00.04/K01.02 discriminator with its CI job
   (dataos-web-workspace, line 23571).
4. **Terminal `if: ${{ false }}` jobs** (dataos-foundation, price-basis-census,
   unrun-intl-libraries) execute inside ci-pack rather than as standalone workflow jobs; the
   collection evidence is their `run:` lines, quoted above.
5. **D00.D6 consumer-A display half** (data-origin readout in ChartFrameBar.tsx) does not exist at
   base — recorded as NO DISCRIMINATOR, per D00.D6 the wave builds/verifies it; the producer tag
   and the reader's ignore-extra-keys behavior are the only base facts.

## DEVIATIONS

- D-1: The worktree created by STEP 0 inherited the shared clone's per-worktree sparse-checkout,
  which omitted `research/` — D00 was present in HEAD's tree but not on disk. Materialized the one
  narrow directory `research/data_os_completion/2026-10-13/` via `git sparse-checkout add` in MY
  worktree only (per-worktree sparse files confirmed; no other worktree or shared config touched).
  No shared clone state changed.
- D-2: STEP 3's `grep -n <filename> .github/ci/legacy-jobs.yml` was run against
  `~/lanes/ext/dataos-o2-q00-1.legacy-jobs.yml`, the byte-identical `git show HEAD:` blob,
  because `.github/` is sparse-omitted; line numbers are the file's own.
- No other departures. D00 and this packet agree everywhere applied.
