# F0 — A07–A10 coverage (RIC-ORCH-B), 2026-10-14

Author: RIC-ORCH-B (native Opus orchestrator; parent = Fable Meta-CEO seat fc3dfe4b).
Inputs: fabric lane `F0-VERIFY` (static read of origin/main @ `1e9364f5ab8c4452820731e87da2c138e53b0571`,
sentinel `F0-VERIFY: PASS-WITH-GAPS`, raw at `$S/lanes/F0-VERIFY.out`), plus ORCH-B's own pytest
receipts at base `402b57defb301fc611ab81242f685a96e085d035` (ubuntu1 lane tree `~/lanes/wt/ric-f0-1`,
sparse: data/ site/ mockups/ verify_shots/ omitted) and an extended second-calendar census.
DO_NOT_REDO honoured: #6543 `a6921aa3` (F0 recovery), #8836 `db40ae32` (release_forecast.v2 consumer).

## 1. Verdicts

| Clause | Verdict | Test evidence | Gap |
|---|---|---|---|
| A07 same-vintage CPI target identities stay distinct | **COVERED** | test_release_target_truth.py (L45, L83, L137); test_release_cpi_target_history.py::test_history_is_sorted_coherent_and_manifest_bound; test_official_release_parsers.py; test_inflation_intelligence(_nw).py | none material (repo carries no NSA series: allowlist `engine/release_target_truth.py:426-432`) |
| A08 revised history appends; original forecast + first-print score recoverable | **COVERED** | test_release_forecast_v2.py::TestRevisionSweep; test_release_forecast_producer.py (L661/L774/L856/L888); test_release_target_truth.py::L45; test_inflation_intelligence.py::L311/L328 | none |
| A09 archive date precision; reconstruction stays labelled | **COVERED** | test_release_cpi_official_truth.py (L379/L425/L1090); test_release_cpi_target_history.py::L608; test_release_target_truth.py (L74/L170); test_release_forecast_producer.py::L661; test_fred_vintages.py | none material (see §2 for the data/-bound tests) |
| A10 canonical calendar owns the schedule; no second calendar | **PARTIAL** | test_event_calendar.py; test_event_window.py; test_alert_time_contract.py; test_build_options_catalyst_links.py | five hard-coded second calendars, none pinned to `engine/event_calendar.py`; two have **live drift** (§3) |

## 2. Test receipts at base 402b57de (ORCH-B, ubuntu1, `~/lanes/venv/bin/python -m pytest -q -p no:cacheprovider`)

- **F0 judge set**: test_release_forecast.py, test_release_forecast_cpi_v2.py,
  test_release_forecast_nfp_decomp.py, test_release_forecast_producer.py, test_release_forecast_v2.py,
  test_release_forecast_v3.py, test_inflation_intelligence.py, test_inflation_intelligence_nw.py,
  test_event_calendar.py, test_event_window.py →
  **376 passed, 10 skipped, 1 warning in 20.95s** (rc 0).
- **A07–A09 coverage extras + second-calendar owners**: test_release_target_truth.py,
  test_release_cpi_target_history.py, test_official_release_parsers.py, test_release_market_context.py,
  test_release_cpi_official_truth.py, test_fred_vintages.py, test_hk_event_calendar.py,
  test_catalyst_tone.py → **184 passed, 1 skipped, 4 failed in 4.93s**.
  All 4 failures are in test_release_cpi_official_truth.py
  (`test_preregistered_panel_has_fourteen_sources_and_one_explicit_gap`,
  `test_retained_real_2026_xlsx_replays_without_network`, `test_retained_real_2012_xls_replays_without_network`,
  `test_default_corpus_has_bound_fourteen_plus_one_receipts`) and are **sparse-tree artefacts**:
  `FileNotFoundError … data/release_forecast/cpi_truth/preregistered_sample.json` and
  `…/official_table1_archive/documents/sha256/<…>.xls[x]` `.is_file() == False`. The skip is
  test_release_market_context.py:831 (`data/cleveland_nowcast/nowcast.parquet not present`).
  These four A09 tests are therefore **UNVERIFIED in this run** (need a full checkout; they are wired
  in CI, whose green run is the evidence of record).
- Evidence class: `replay` (repo fixtures) + `static` (F0-VERIFY reads). No live data used.

## 3. A10 — second-calendar census (extended by ORCH-B; F0-VERIFY missed two copies)

| Copy | Location @base | Canonical relation | Owner |
|---|---|---|---|
| CPI/PPI/NFP 2026 mirrors | `engine/event_window.py:151,156,161` (`_CPI_2026/_PPI_2026/_NFP_2026`) | values == canonical today; **unpinned** (docstring L21 claims "same static table" — it is a copy) | **ORCH-B** |
| FOMC 2026 rows | `engine/event_window.py:65` `_FOMC_ANNOUNCEMENT_DATES` (2000–2026 literal) | 2026 rows == canonical `_FOMC`; unpinned | **ORCH-B** |
| HK desk US CPI | `engine/hk_event_calendar.py` `US_CPI` | **DRIFT**: Oct 13 vs canonical 14; Nov 12 vs canonical 10 (comment "~mid-month (10th-13th)") | seat / not ORCH-B |
| HK desk US NFP | `engine/hk_event_calendar.py:159` `_first_friday` | **DRIFT** vs canonical published NFP: Jan 2 vs 9, May 1 vs 8, Jul 3 vs 2 | seat / not ORCH-B |
| HK desk FOMC | `engine/hk_event_calendar.py:73` `_FOMC_2026` | == canonical; unpinned | seat / not ORCH-B |
| Catalyst tone FOMC | `engine/catalyst_tone.py:506` `_FOMC_MEETINGS` (2025-09-17…2026-12-09) → consumed by `engine/event_landmine.py:65 _fomc_dates()` | 2026 subset == canonical; unpinned | seat / not ORCH-B |
| Marketing FOMC fallback | `engine/marketing/fomc_statements.py:66` `_FOMC_2026_FALLBACK` | == canonical; unpinned | seat / not ORCH-B |

Live note: `/live/release_publications.json` on www.mastermind-x.com carries `cpi:2026-10-14` 08:30 ET with
`schedule_source: static` — i.e. it echoes the canonical table, so it is not independent evidence. A
first-party BLS fetch returned 403: the true 2026-10 CPI date is **UNVERIFIED** by a primary source;
the canonical table is the A10 authority by rule, and the HK desk disagrees with it for Oct and Nov.

## 4. CI-wiring finding (affects F0 and D0)

`config/unrun_test_baseline.json` (frozen 2026-08-09, shrink-only, "NEVER add to it"; a row leaves when
its suite is wired) grandfathers these as UNRUN in CI: `tests/test_fed_path.py`,
`tests/test_event_window.py`, `tests/test_event_calendar.py`, `tests/test_hk_event_calendar.py`,
`tests/test_catalyst_tone.py`, `tests/test_official_release_parsers.py`, `tests/test_fred_vintages.py`.
So A10's cited suites (test_event_calendar/test_event_window) and D0's judge suite (test_fed_path) **do not
run in CI today**; A07/A09 still stand on wired suites (target_truth, cpi_target_history,
cpi_official_truth, inflation_intelligence, release_forecast_v2/producer). ci.yml:1739-1742 lists the
event_window paths as triggers only. Consequence: every ORCH-B package ships a seat-applied
`$S/judge/<pkg>_ci_paths.patch` that wires its suites in `.github/ci/legacy-jobs.yml` and removes the
matching baseline rows (the `contract-delta` gate reds on any NEW unwired test file).

## 5. A10 gap lane (ORCH-B-owned, tests-first) — branch `claude/ric-f0-gaps-2026-10-14`

Owned: `engine/event_window.py` [M], `tests/test_event_window.py` [M], `tests/test_ric_f0_a10.py` [A].
- Production: event_window reads canonical at CALL time — CPI/PPI/NFP from
  `engine.event_calendar._SCHED_2026[etype]`, FOMC 2026+ from `engine.event_calendar.fomc_decision_dates`;
  the 2000–2025 FOMC history stays as a renamed pre-canonical archive; literal mirrors removed; docstring fixed.
- RED on base → GREEN: moving a canonical CPI/PPI/NFP day or a canonical FOMC day moves `tag()` output.
- GREEN-on-base guards: archive ends before canonical begins; sync pins for the three non-owned FOMC
  copies; **known-drift ledgers** for the HK US_CPI and NFP drift (green while the drift is exactly
  as recorded; red if it grows, or if someone fixes it without emptying the ledger).
- Unchanged-input control: `tag()` over every business day 2000-01-03..2026-12-31 at base and head,
  `DataFrame.equals` True and identical phase counts.
- Lane sentinel: `$S/lanes/F0-GAPS.out`.

## 6. Spec for the seat (files outside ORCH-B ownership — recommend, not performed)

1. `engine/hk_event_calendar.py`: `US_CPI` and `US_NFP` must read the canonical schedule
   (`engine.event_calendar._scheduled_release_dates(etype, …, use_fred=False)` or `_SCHED_2026`), and
   `_FOMC_2026` must come from `fomc_decision_dates`; in the SAME PR empty the two known-drift ledgers in
   `tests/test_ric_f0_a10.py` (their assertions then flip to "no drift"). This is a live, user-facing
   wrong date: the HK desk shows US CPI on 10-13 against the canonical 10-14 (today) and 11-12 against
   11-10 (still ahead), and NFP on Jan/May/Jul first-Fridays that are not the published dates.
2. `engine/catalyst_tone.py:506` `_FOMC_MEETINGS` (→ event_landmine) and
   `engine/marketing/fomc_statements.py:66` should read canonical for 2026+; the sync pins in
   `tests/test_ric_f0_a10.py` guard them until then.
3. Wire `tests/test_event_window.py` + `tests/test_ric_f0_a10.py` (F0) and `tests/test_fed_path.py` (D0)
   via the judge patches; removing their `unrun_test_baseline.json` rows is the matching shrink.

## 7. F0-VERIFY lane block (verbatim, lines 4–158 of `$S/lanes/F0-VERIFY.out`)

=====BEGIN F0_COVERAGE=====
# F0_COVERAGE — RIC-INCLUDED-CORE, task F0 "Close release and schedule evidence"
# Seam: reuse_merged_recovery_refresh_only · BASE: >= 402b57de (OK, ancestor) · HEAD: 1e9364f5ab8c4452820731e87da2c138e53b0571
# Method: static (git show/grep of origin/main only; pytest NOT runnable on this remote clone — parent re-runs all cited tests)
# Prior receipts honored (not re-done): #6543 a6921aa3 (records-only, no tests changed → coverage must live in existing suite);
#   #8836 db40ae32 (release_forecast.v2 consumer binding, pinned by tests/test_c19_wp11_reader_pins.py)

## A07 — Same-vintage CPI target identities stay distinct
VERDICT: COVERED

TESTS:
- tests/test_release_cpi_target_history.py::test_history_is_sorted_coherent_and_manifest_bound (L608)
    L627  `assert january["prior_level_same_vintage"] == 100.5`   (revised Dec level, SAME 2025-02-12 vintage)
    L628  `assert january["latent_change"] == pytest.approx((100.7 / 100.5 - 1) * 100)`
    L629  `assert january["published_proxy_1dp"] == 0.2`
    L630-633 `provenance.current_vintage/prior_vintage realtime_start == "2025-02-12"`; `same_release_vintage is True`; `cross_vintage_fallback_used is False`
    L615-619 exact `(period, release)` target list — cpi_headline and cpi_core rows stay separate keys (n_targets == 8, L614)
    L635-642 `history["source_artifacts"]["CPIAUCSL"]` sha256/bytes binding — SA series id is a pinned dict key
- tests/test_release_target_truth.py::test_annual_revision_discontinuity_uses_prior_level_from_same_release_vintage (L45)
    L70-72 `latent_change == approx(1.0)`; `published_proxy_1dp == 1.0`; `published_proxy != approx(11.1)` (cross-vintage division ruled out)
    L74 `assert result["published_proxy_is_official_release"] is False`
- tests/test_release_target_truth.py::test_all_price_targets_emit_latent_and_explicit_one_decimal_proxy (L83, parametrized over PERCENT_TARGET_SERIES = CPIAUCSL CPILFESL PCEPI PCEPILFE PPIFIS PPIFES)
    L101 `assert result["target_kind"] == "percent_mom"` — monthly identity in the target kind itself
- tests/test_release_target_truth.py::test_missing_same_vintage_prior_is_explicitly_unavailable_without_fallback (L137)
    L159 `assert ... "target_id": "cpi_core_mom" ...` inside an EXACT whole-dict equality (L154-167) — target ids pinned per series
- tests/test_official_release_parsers.py (official layer): L178-183 metric_id list `["cpi_headline_mom","cpi_core_mom","cpi_headline_yoy","cpi_core_yoy"]` with DISTINCT values L173-176 (mom -0.4 vs yoy 3.5); PCE L318-324; NFP ids L245-248
- tests/test_inflation_intelligence.py::test_contract_separates_three_inflation_clocks (L269) L283-286 released 2026-08 vs forecast 2026-07 vs proxy 2026-08 kept as separate clocks;
  tests/test_inflation_intelligence.py::test_released_state_uses_exact_3m_6m_annualization (L295) L300 `mom_pct == approx(1.0)`;
  tests/test_inflation_intelligence_nw.py L102-105 and L201 `yoy_pct == 2.62` alongside `mom_pct 0.21` — mom and yoy coexist as distinct fields/values
- tests/test_release_market_context.py::...test_core_cpi_market_never_attaches_to_headline (L319) — core≠headline at the consumer layer
- Adjusted/unadjusted: repo contains NO NSA series anywhere (git grep CPIAUCNS|CPILFENS over engine,collectors,scripts,tests = 0 hits); production allowlist engine/release_target_truth.py:426-432 (`unsupported release-target series`) + CPI_SERIES_BY_RELEASE engine/release_cpi_target_history.py:73-76; any SA→NSA remap breaks the pinned series keys above (manifest binding by series id, source_artifacts["CPIAUCSL"], exact target_id dict).

MUTATION RULED OUT:
(a) collapse SA and NSA target ids into one key / remap cpi_headline to CPIAUCNS → KeyError on `source_artifacts["CPIAUCSL"]` (test_release_cpi_target_history.py:635) and exact-dict target_id mismatch (test_release_target_truth.py:154-167); production touch points engine/release_target_truth.py:37-45 (TARGET_IDS), engine/release_cpi_target_history.py:73-76.
(b) numerator/denominator or cross-vintage division (11.1% trap) → L70-72 and L627-629 fail; production engine/release_target_truth.py:296 (percent_mom reconstruction).
(c) mom↔yoy swap → official metric_id list and value asserts (test_official_release_parsers.py:173-183) and nw state asserts (test_inflation_intelligence_nw.py:102-105,201) fail.
(d) official-first-print conflated with derived proxy → `published_proxy_is_official_release is False` (L74), withheld-epoch asserts (test_release_cpi_target_history.py:611-613), and exact_target_id separation `"cpi_headline_mom_archived_release_edition"` vs proxy id (test_release_cpi_official_truth.py:319) fail.

MISSING SCENARIO: none material. (Note, not a gap: no dedicated test exercises `_validate_series` rejecting an unsupported series id; id-level collapse is nonetheless caught by the pinned asserts above.)

RERUN COMMAND:
python -m pytest -q -p no:cacheprovider tests/test_release_target_truth.py tests/test_release_cpi_target_history.py tests/test_official_release_parsers.py tests/test_inflation_intelligence.py tests/test_inflation_intelligence_nw.py tests/test_release_market_context.py

## A08 — Revised history appends; original forecast and first-print score recoverable
VERDICT: COVERED

TESTS:
- tests/test_release_target_truth.py::test_annual_revision_discontinuity_uses_prior_level_from_same_release_vintage (L45): vintage store holds first print (rt 2025-01-15, 100.0) AND revision row (rt 2025-02-12, 110.0) as separate rows; reconstruction picks same-vintage revised prior; latent 1.0% not 11.1%.
- tests/test_release_forecast_v2.py::TestRevisionSweep
    test_revision_emitted_when_different (L295): L304 `row_type == "revision"`, L306 `r["actual_first"] == pytest.approx(actual_first)` (first print carried INTO the revision record), L308-309 revision_pp nonzero
    test_revision_idempotent (L311) L322 `rows2 == []`
    test_revision_append_only (L324): L338 `assert scored_count == 1, "Scored rows must not be removed"`, L339 revision rows appended
- tests/test_release_forecast_producer.py::test_scoreboard_canonicalizes_official_score_supersession (L856): L877-885 `{"raw_n": 2, "canonical_n": 1, "superseded_n": 1, note "Official actual receipts supersede same-vintage proxies ... every receipt remains in the ledger."}`; frozen_prediction_id/frozen_asof_night/frozen_projection_point survive (L860-861, 869)
- tests/test_release_forecast_producer.py::test_append_keeps_distinct_same_day_score_receipts (L888): L911 proxy and official same-day receipts BOTH retained after double append (dedupe only exact rows)
- tests/test_release_forecast_producer.py::test_official_actual_receipt_supersedes_legacy_score_idempotently (L774)
- tests/test_inflation_intelligence.py::test_forecast_evolution_is_append_order_deduped_and_shadow_free (L311): L315-320 evolution points append-ordered with per-point prediction_id/code_receipt/inputs_hash; L321-322 tampered points excluded
- tests/test_inflation_intelligence.py::test_forecast_evolution_uses_artifact_or_explicit_historical_cutoff (L328): as-of replay sees only earlier forecast points (original forecast recoverable point-in-time)
- classification: tests/test_release_cpi_target_history.py::test_metrics_dict_parity_classifies_revision_ordinary_and_gap (L784) — annual_revision/ordinary/explicit_gap classes (production allowlist engine/release_cpi_target_history.py:92)

MUTATION RULED OUT:
(a) overwriting the first print on revision (in-place value update instead of new realtime_start row / mutating scored rows) → test_revision_append_only L338 and L306 fail; production scripts/build_release_forecast.py:2693-2766 (`_check_revision_sweep`, `actual_first` frozen at :2732/:2755, idempotency key incl. revised_value :2745, multi-revision note :199), append-only ledger writer scripts/build_release_forecast.py:717-734; vintage rows append at engine/release_target_truth.py (realtime_start interval model).
(b) dropping the original forecast row at rebuild → producer ledger equality L911 and append-order evolution L315-320 fail; scoreboard canonicalization keeps raw receipts (production scripts/build_release_forecast.py:2971 `_build_scoreboard`).
(c) losing the first-print score when official arrives → supersession test L877-885 (raw_n=2 preserved) and engine/release_actuals canonical-actual preference (test_capture_prefers_official_actual_receipt, producer L661-700).

MISSING SCENARIO: none.

RERUN COMMAND:
python -m pytest -q -p no:cacheprovider tests/test_release_forecast_v2.py::TestRevisionSweep tests/test_release_forecast_producer.py tests/test_release_target_truth.py tests/test_inflation_intelligence.py tests/test_release_cpi_target_history.py::test_metrics_dict_parity_classifies_revision_ordinary_and_gap

## A09 — Archive date precision; reconstruction remains labelled
VERDICT: COVERED

TESTS:
- tests/test_release_cpi_official_truth.py
    L379-386: `receipt["first_print_status"] == FIRST_PRINT_STATUS`, `actual_basis == ARCHIVED_TABLE1_ACTUAL_BASIS`, authority False, display_only True (production constants engine/release_cpi_official_truth.py:33-36: FIRST_PRINT_STATUS = "unverified_retrospective_archive")
    L425-435: not-publication receipt deterministic, `first == second` exact-dict, `targets == []`, distinct ARCHIVE_NONPUBLICATION basis
    L1090-1097: ALL 15 corpus receipts carry the unverified label and authority False
- tests/test_release_cpi_target_history.py::test_history_is_sorted_coherent_and_manifest_bound (L608)
    L611-613 `target_epoch == "alfred_same_release_vintage_proxy_v1"`; official epoch `official_first_print_v1` with `status == "withheld"`
    L630-631 provenance realtime_start asserted as EXACT date strings "2025-02-12" (day precision)
- tests/test_release_target_truth.py
    L74 `published_proxy_is_official_release is False`; L75-80 prior_vintage provenance exact-dict (date-only fields)
    test_as_of_before_release_cannot_observe_target (L170) L187-188 `reason == "release_not_available_by_as_of"` (build time ≠ evidence time)
- Day-level eligibility gate: engine/release_cpi_target_history.py:1054 `if not min_release_lag_days <= lag_days <= max_release_lag_days` (7–45 d, MIN/MAX L70-71), gate metadata emitted L282-285; pinned by rejected_candidate_rows n==4 (bulk-inception rows rejected, test L620; fixture labels L221-224) and by test_source_bound_nonpublication_overrides_alfred_rows_and_followup (L666).
- Minute-level house capture is a SEPARATE identity: tests/test_release_forecast_producer.py::test_capture_prefers_official_actual_receipt (L661) — official receipt carries first_seen_at/source_released_at/verified_at timestamps (L674-676), scored row labelled `actual_source == "official_release_document"` (L699); ALFRED path never emits these.
- Consumer honesty: tests/test_inflation_intelligence.py L290-292 `"not an official cpi observation" in rendered` AND `"current cpi" not in rendered`; L287 freshness `current_with_publication_lag`; L304 `revision_basis == "latest_local_fred_not_original_release_vintage"`.
- collectors/fred day-precision point-in-time: tests/test_fred_vintages.py L33-48 (as_of excludes not-yet-published), L51-55 initial_release returns first published values.

MUTATION RULED OUT:
(a) stamping the day-precision ALFRED date as minute-level first availability / certification → any promotion changes `first_print_status` or epoch status and fails L379-386/L1090-1097/L611-613; emitting a timestamp in provenance breaks the exact date-string and exact-dict asserts (L630-631; test_release_target_truth.py:75-80, 154-167).
(b) relabelling the reconstruction as official/house capture → `published_proxy_is_official_release is False` (L74) and the consumer string pins (L290-292) fail.
(c) admitting an early/same-month vintage as a "release" → lag-gate reject counts and target list asserts (L614-620) fail; production engine/release_cpi_target_history.py:1054.

MISSING SCENARIO: none material. (Note: the ok-path target row dict is asserted field-wise, not exact-dict; the certification mutations above are all caught because they must alter a pinned label/status/field to take effect.)

RERUN COMMAND:
python -m pytest -q -p no:cacheprovider tests/test_release_cpi_official_truth.py tests/test_release_cpi_target_history.py tests/test_release_target_truth.py tests/test_fred_vintages.py tests/test_inflation_intelligence.py tests/test_release_forecast_producer.py::test_capture_prefers_official_actual_receipt

## A10 — Canonical calendar owns schedule; no second calendar
VERDICT: PARTIAL

COVERED clauses — TESTS:
- Reschedule ownership (live override replaces static table): tests/test_event_calendar.py::test_fred_override_used_when_reachable (L154) L160 `cpi[0]["date"] == "2026-06-20" and cpi[0]["source"] == "fred"`; parser degrade tests test_parse_fred_release_dates_synthetic (L142, malformed/out-of-window skipped, L150-151). Production branch engine/event_calendar.py:236-247.
- Published-vs-naive schedule ownership (holiday/weekend shifts baked into tabulated dates): tests/test_event_calendar.py::test_jobs_report_uses_published_not_naive_first_friday (L66) L72 `nfp[0]["date"] == "2026-05-08"` while L73 proves naive trap 2026-05-01; FOMC SEP set Mar/Jun/Sep/Dec from canonical table (L52-63). Production engine/event_calendar.py:50-82 (`_FOMC`, `_SCHED_2026`).
- Time zone: event shape pins `time_et` and (date, time_et) ordering (test_event_calendar.py L85, L89); ET-day-boundary ownership at the consumer: tests/test_alert_time_contract.py L395 `seen["today"] == dt.date(2026, 8, 19)  # NOT the UTC 20th`.
- Event IDs: tests/test_release_forecast_v2.py::TestReleaseIdFormats (L211-239) `make_release_id("cpi_headline","2026-06") == "CPI:2026-06:first"` (first-print sequence in the id; production engine/release_forecast.py:380-388); locator ids `event_calendar:fomc:<date>` pinned in tests/test_build_options_catalyst_links.py L293, L370, L414-428 (source == "engine.event_calendar").
- Duplicate/coincident publications:
  · data layer: tests/test_release_target_truth.py::test_conflicting_duplicate_vintage_values_are_rejected (L507) L516 `pytest.raises(..., match="conflicting values")` — two values for one series/period/vintage are rejected, not heuristically merged (production engine/release_target_truth.py normalize_full_vintage_frame)
  · event layer: tests/test_event_window.py::TestCollisionDetection (L121-163) coincident CPI/FOMC/opex are LABELLED booleans (`cpi_fomc_same_week`, `triple_stack`), never merged or scored; RIC laws: no score/weight fields (test_event_calendar.py L94-100; test_event_window.py L504-520)
  · receipt layer: producer L888-911 (distinct same-day receipts both kept); official-vs-proxy supersession producer L856-885.

MISSING SCENARIO (the GAP — "no second calendar"):
Independent hard-coded US release/FOMC date tables exist OUTSIDE engine/event_calendar.py and NO test cross-checks them against the canonical calendar:
  · engine/event_window.py:65 `_FOMC_ANNOUNCEMENT_DATES` (full literal list, 2000→2026), :151 `_CPI_2026`, :156 `_PPI_2026`, :161 `_NFP_2026` — comments admit "mirrored from event_calendar" (:150) while the module docstring claims "same static table" (:21); consumed by `_static_release_dates`/`_fomc_dates` (:170-179, :275-277).
  · engine/hk_event_calendar.py:73 `_FOMC_2026` (own literal copy), :69 own `US_CPI` month/day table, :160 `d = _first_friday(y, m)  # US payrolls — 1st Friday` — recomputes US NFP by the naive rule the canonical module explicitly forbids (canonical published date 2026-05-08 vs naive 2026-05-01).
Discriminating counterexample verified: mutate engine/event_window.py `_CPI_2026` June 10→11 (or canonical `_SCHED_2026` alone) → `tests/test_event_window.py::TestNoHistoricalBackProjection::test_2026_cpi_dates_still_tagged` (L491-498) still passes (only asserts len>0 on business-day index); NO test in the repo imports both tables → drift is invisible. Same for hk tables (tests/test_hk_event_calendar.py does not pin US_NFP dates).
Proposed test (tests-first gap lane): tests/test_ric_f0_a10.py::test_no_second_us_release_calendar
    ```python
    from engine import event_calendar as ec, event_window as ew, hk_event_calendar as hk
    def test_event_window_mirrors_match_canonical():
        assert {m: d for m, d in ew._CPI_2026.items()} == ec._SCHED_2026["CPI"]
        assert ew._PPI_2026 == ec._SCHED_2026["PPI"] and ew._NFP_2026 == ec._SCHED_2026["NFP"]
        assert [d for d in ew._FOMC_ANNOUNCEMENT_DATES if d.startswith("2026")] == [d for d, _ in ec._FOMC]
    def test_hk_us_events_read_canonical_schedule(monkeypatch):
        # RED on origin/main: hk emits naive first-Friday 2026-05-01; canonical owns 2026-05-08
        evs = hk.hk_event_calendar(date(2026, 5, 1), horizon_days=10)
        nfp = [e for e in evs if e["type"] == "US_NFP"]
        assert nfp and nfp[0]["date"] == "2026-05-08"
    ```
    RED on origin/main? The mirror-sync test is GREEN today (tables currently agree) but kills the drift mutation; the hk US_NFP assert is RED on origin/main (2026-05-01 ≠ 2026-05-08) → YES, RED without a production change at engine/hk_event_calendar.py:153-164 (replace own `_FOMC_2026`/first-Friday/US_CPI table with reads from engine.event_calendar) — return the exact spec to the seat per §6 ownership (hk_event_calendar.py is not an ORCH-B listed file; event_window.py IS ORCH-B).

RERUN COMMAND:
python -m pytest -q -p no:cacheprovider tests/test_event_calendar.py tests/test_event_window.py tests/test_alert_time_contract.py tests/test_build_options_catalyst_links.py tests/test_hk_event_calendar.py tests/test_c19_wp11_reader_pins.py

## SUMMARY
| Case | Verdict | Tests (primary) | Gap scenario |
|------|---------|-----------------|--------------|
| A07 | COVERED | test_release_target_truth.py (L45, L83, L137); test_release_cpi_target_history.py::test_history_is_sorted_coherent_and_manifest_bound; test_official_release_parsers.py; test_inflation_intelligence(.nw).py | none material |
| A08 | COVERED | test_release_forecast_v2.py::TestRevisionSweep; test_release_forecast_producer.py (L661/L774/L856/L888); test_release_target_truth.py::L45; test_inflation_intelligence.py::L311/L328 | none |
| A09 | COVERED | test_release_cpi_official_truth.py (L379/L425/L1090); test_release_cpi_target_history.py::L608; test_release_target_truth.py (L74/L170); test_release_forecast_producer.py::L661; test_fred_vintages.py | none material |
| A10 | PARTIAL | test_event_calendar.py; test_event_window.py; test_alert_time_contract.py; test_build_options_catalyst_links.py | second US calendars drift un-pinned: engine/event_window.py:65,151,156,161 + engine/hk_event_calendar.py:69,73,160; proposed tests/test_ric_f0_a10.py (hk assert RED on main; production change at hk_event_calendar.py:153-164) |

## SECOND-CALENDAR CENSUS (schedule/date tables outside engine/event_calendar.py)
| Location | What it holds | Second calendar or reader of canonical? |
|---|---|---|
| engine/event_window.py:65 `_FOMC_ANNOUNCEMENT_DATES`; :151 `_CPI_2026`; :156 `_PPI_2026`; :161 `_NFP_2026` | literal mirrors of canonical 2026 CPI/PPI/NFP + FOMC 2000-2026 list | SECOND CALENDAR (self-admitted mirror, :150/:21); no sync test; GAP |
| engine/hk_event_calendar.py:69 `US_CPI` table; :73 `_FOMC_2026`; :160 naive-first-Friday US_NFP | own copies of US macro dates for HK-display events | SECOND CALENDAR (US_NFP contradicts canonical published dates); GAP |
| engine/china_event_calendar.py:78 `_SCHED_2026` | China macro prints (CPI/TRADE/PMI…), CN jurisdiction | separate-domain calendar, NOT a duplicate of the US canonical; OK |
| engine/marketing/fomc_statements.py:230-236 | imports `engine.event_calendar._FOMC` ("READ FROM event_calendar, DO NOT RESTATE") | reader of canonical; OK |
| engine/macro_news.py, engine/commodity_news.py, engine/event_risk.py, engine/forward_calendar_context.py, engine/alert_triage.py, engine/capital_policy_projection.py, engine/news_vector.py, engine/options_catalyst_link.py, scripts/build_aibrief.py, scripts/build_crypto.py, scripts/build_feeds.py, scripts/build_site.py, scripts/build_release_forecast.py, scripts/watch_release_publications.py | import engine.event_calendar | readers of canonical; OK |
| engine/prophet_bridge.py:629-650 `_third_friday` | options EXPIRY (3rd Friday) arithmetic, not macro releases | own opex domain (canonical has its own third_friday :127-133 for opex); not a release calendar; OK |
| collectors/* holiday chatter (base.py, hk_shorts.py, china_*, finra_*, cboe*, market-session logic; lib/exchange_holidays) | market SESSION holidays/staleness, not macro release schedules | different domain (session calendars); OK |
| engine/pit.py:113 | prose cadence note ("~first Friday") in lag metadata, no date table | documentation; OK |
| engine/release_market_context.py | EXCLUDED file (held PRs #7909 #7521 #7923 #7940 #7965) — not inspected, not counted | EXCLUDED |
=====END F0_COVERAGE=====

## Seat addendum (Fable Meta-CEO seat fc3dfe4b, 2026-10-14, after F0 merged)

This receipt is the ORCH-B pre-merge coverage audit, committed as the F0 evidence record.
`$S/...` paths above refer to the seat's session scratchpad and are not committed; the
lane outputs they name were consumed by the seat when F0 was accepted.

State on `origin/main` since this audit (supersedes §1 A10 PARTIAL and §6 item 1):

- F0 merged as #9222 (`9947bf53`). It carried both lanes: F0-GAPS (`engine/event_window.py`
  reads `engine/event_calendar` at call time) **and** F0-HK (`engine/hk_event_calendar.py`
  reads the canonical calendar at call time for FOMC / US_NFP / US_CPI).
- The HK desk drift recorded in §6 item 1 (US CPI on 10-13 vs canonical 10-14; first-Friday
  NFP) is therefore **fixed on main**: `tests/test_ric_f0_a10.py` now pins
  `_HK_US_CPI_KNOWN_DRIFT = {}` and `_HK_US_NFP_KNOWN_DRIFT = {}`, so any reappearance of a
  second calendar in the HK desk turns the suite red.
- A10 is COVERED for the release families the RIC core consumes (CPI / PPI / NFP / FOMC).
  The remaining second-calendar copies listed in §6 item 2 (`engine/catalyst_tone.py`
  `_FOMC_MEETINGS`, `engine/marketing/fomc_statements.py`) are guarded by the A10 sync pins
  and are not RIC-owned; they are recorded here, not rewritten (Catalyst is an excluded
  programme in the commission).
- §4 CI wiring: every RIC package since F0 wires its own suites in
  `.github/ci/legacy-jobs.yml`. A job whose inferred closure would select it on the CI
  packing probes carries `scope: exclusive` plus a `CURATED_EXCLUSIVE` entry in
  `tests/test_ci_pack.py` (see #9282).
