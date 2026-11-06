# Opus adversarial review — PR #7905 (CDV-1 Task 1) @ 262bd9675e81
MODE: READ_ONLY. Contract: plan @88970a1a Task 1 + §2.1/§2.2 + Global Constraints; seat rulings F3–F7 (OPUS_PLAN_SEAM_AUDIT_2026-09-24).
Throwaway worktree: /private/tmp/claude-501/cdv1-t1-review (detached at 262bd9675e81).

## (1) Twenty pg_ definitions — PARTIAL
- PASS: pg_profile.py:42-63 defines exactly the 20 plan keys (§2.1 :98-119) with value_kind/unit/scale/basis/scope/quarter_duration/comparison_family; current<->prior EPS paired via paired_metric (:51-55); segment_scope on 5 segment rows.
- M1 pg_profile.py:219 `value = float(literal.rstrip("%"))` for EVERY metric regardless of definition.value_kind/unit. Fixture EPS cells are "1.25%" (earnings_economic_fixtures.py:34) and are emitted as `unit=usd_per_share` with display_excerpt '1.25%' (probe dump). Violates §2.1 :94 "value kind, unit, scale" per definition and Task 1.3 "Match ... column header and period together". Correction: unit-check the literal against the definition (percent literal only for percent/pp kinds; currency kinds accept `$`/bare number only; else typed absence); fix the fixture EPS cells to non-% literals.
- m: price/mix/FX/other definitions carry no "original percentage display label" field (§2.1 :121); quarter_duration=91 constant is unused (validator uses 89-92).

(Coordinator note: head moved to 5dadd935 = CI-only `pip install pytest pyyaml`; code reviewed at 262bd967 otherwise unchanged.)

## Findings concluded from reading (format: F<n> [SEV] file:line — claim — evidence — falsifier)
F1 [MAJOR] pg_profile.py:219 — every literal is `float(literal.rstrip("%"))` regardless of definition unit; percent literals become usd_per_share EPS — fixture :34 EPS cells "1.25%"; probe dump: `P pg_diluted_eps 1.25 usd_per_share ... display_excerpt '1.25%'` — falsifier: a currency-kind cell carrying "%" yields typed absence.
F2 [BLOCKER] pg_profile.py:274,279,281,283 — extractor vocabulary is hard-coded to the synthetic fixture: row "Fourth Quarter 2026", headings "Fourth Quarter Results"/"Sales Drivers"/"Volume Conventions", and the reconciliation "sentence" is a constant containing the word "synthetic". Period literal "2026" is NOT derived from fiscal_scope, so a FY2027 scope binds the "Fourth Quarter 2026" (prior-year) row as current (probe b below). Violates plan Task 1.3 "Match heading, row label, column header and period together" + Review Focus #2 (bind the correct period) + F3 (period comes from fiscal_scope). Correction: derive the quarter/year header tokens from fiscal_scope/fiscal_period; reconciliation = bounded paragraph under the reconciliation heading, not a constant; label vocabulary as reviewed PG definitions, not fixture strings — falsifier: FY2027 scope + table with both 2027 and 2026 rows binds the 2027 row.
F3 [MAJOR] pg_profile.py:256-265,281 + fixture :77-85 — Sales Drivers table is transposed relative to the lookup (metrics are COLUMN headers, extractor searches them as ROW labels) so 6/8 driver facts (reported/organic sales, price, mix, FX, other) are ALWAYS typed-absent in every fixture (probe dump). Plan 1.1 requires a driver table the tests exercise; no test asserts any driver value — falsifier: a test asserting pg_price_contribution_pp == 0.5 passes.
F4 [MAJOR] fixture :47-52 vs :79-82 — "columns_reordered" reverses driver VALUES but not the driver HEADER row, so the reordered fixture is internally false (values under wrong headers); once F3 is fixed it would teach the extractor wrong bindings. Correction: reorder header and values together (as EPS does :35-44).
F5 [MAJOR] economic_observations.py:151-206 — byte replay never binds `value` to the replayed span: a present row whose value is changed (9.99) or whose current/prior spans are swapped still validates (probe d/d2). §2.2 "body digest and byte replay" is hollow without it. Correction: parse the replayed display_excerpt with the same literal rule (and neutral-convention rule for dash rows) and require equality with value; text kinds require value == excerpt.
F6 [MAJOR] economic_observations.py:77-78 — validator hard-codes `quarter == "4"`; PG Q1–Q3 events are always refused. Contract §2.2: "valid quarter/prior interval" from fiscal_scope, not Q4-only. Correction: derive/verify the quarter from fiscal_scope + FY-end month 6.
F7 [MAJOR] tests/test_pg_economic_observations.py:157-165 — combined volume/mix negative control is vacuous: asserts only that no row has metric "combined_volume_mix" (a name the extractor can never emit) and set equality. Fixture keeps a pure "Total volume" row valued 2.0 == combined 2.0, so no test can tell which row fed the value. Correction: a case with ONLY the combined row must yield typed absence for pg_total_volume_growth_pct and pg_organic_volume_growth_pct.
F8 [MAJOR] fixture :34 — "Prior Core EPS 1.48" for the FY2025 Q4 prior period coincides with P&G's actual reported Q4 FY2025 core EPS ($1.48) — the commission names 1.48 as a live-figure tell. Violates plan 1.1 "synthetic values only / never copied". Correction: replace with an obviously synthetic value (e.g. 1.37).
F9 [MINOR] economic_observations.py:129-148 — absence rows: `authority` value unchecked (only key presence), subject/document_id not tied to metric/document (probe g/g2).
F10 [MINOR] economic_observations.py:170-206 — span `rights_profile` not checked (accepts rp_public_primary_v1, probe h); `rp_internal_private_v1` is a newly minted, unregistered token (only occurrence repo-wide: pg_profile.py:25).
F11 [MINOR] economic_observations.py:118-121 — fact_id not tied to `fact_{metric}`; a pg row may carry fact_id "fact_revenue_gaap" colliding with the builder's non-pg fact (probe h2); duplicate-fact-id check untested (test :63-68 fails on key set first).
F12 [MINOR] economic_observations.py:75 — `workspace.get("fiscal_period", {}).get` raises AttributeError (not EconomicObservationError) when fiscal_period is None (probe i).
F13 [MINOR] pg_profile.py:211-216 — dash→0.0 row's span is the "dash means zero" convention cell, not the dash cell; evidence drilldown will not show the observed cell.
F14 [NIT] economic_observations.py:83-94 duplicate 24-cap check; fixture :27-31 dead `headers` parameter; issuer_profiles.py seam silently ignores fiscal_scope under publication='public'.

## Probe receipts (scratchpad/probe.py, run in throwaway worktree, PYTHONPATH=.)
a dup "Diluted EPS" header -> pg_diluted_eps absent (False, None)   [ambiguity -> absence: behaviour OK, UNTESTED]
b FY2027 scope, table rows "Fourth Quarter 2027"(1.31) + "Fourth Quarter 2026"(1.25) -> pg_diluted_eps (1.25,'2027-06-30'), prior (1.5,'2026-06-30')   [CONFIRMS F2: prior-year row bound as current]
c Q1 event (2026-07-01..09-30) -> EconomicObservationError: workspace is not a fourth-quarter event   [CONFIRMS F6]
d value 9.99 with the '1.25%' span -> ACCEPTED; d2 current/prior spans swapped -> ACCEPTED; e reconciliation text replaced -> ACCEPTED   [CONFIRMS F5]
g absence authority='can_rank' -> ACCEPTED; g2 absence subject/document_id tampered -> ACCEPTED   [F9]
h span rights_profile='rp_public_primary_v1' -> ACCEPTED [F10]; h2 fact_id='fact_revenue_gaap' -> ACCEPTED [F11]
i fiscal_period=None -> AttributeError (not EconomicObservationError) [F12]
j dash without convention -> absent (OK, UNTESTED); k combined-only (pure total row removed) -> total volume absent (behaviour OK, test vacuous F7); l duplicate "Total volume" row label -> absent (OK, untested)
m "$1.25" EPS -> absent; n "(1.25)" -> absent   [F1 addendum: ordinary currency and parenthesised-negative literals of a real release are refused; only a bare/percent number parses]

## (2) Column reordering by header / ambiguity -> typed absence — PARTIAL
EPS: header-matched (_locate pg_profile.py:125-141), reordered EPS fixture binds correctly, duplicate header -> absence (probe a). Drivers: never extracted (F3) and reordered-driver fixture is false (F4); no test of ambiguity. Period is a constant, not bound from scope (F2, BLOCKER).
## (3) annual-first selects the QUARTER table — PASS (fixture only)
_table heading "Fourth Quarter Results" (pg_profile.py:114-122,279); test_quarter_and_basis_are_bound[annual_first] asserts 1.25/1.50/1.45 (annual would give 2.10/2.40/2.45). Caveat: selection is by fixture heading string, see F2.
## (4) combined volume/mix; blank/dash — PARTIAL
Behaviour: combined-only -> absent (probe k); blank -> absent; dash -> 0.0 only with per-row "dash means zero" (probe j). Tests: combined control vacuous (F7); dash-without-convention untested.
## (5) multibyte byte offsets / real receipts — PASS
test_multibyte_byte_offsets_are_correct (:179-189) replays source.encode('utf-8')[start:end] and asserts '全球品牌' in the byte prefix; receipts come from receipt_for_literal on the bound source, digests computed at test time (fixture :5-6, no literal digests in fixture).
## (6) hostile markup inert — PASS (thin)
<script type="text/plain">Inject 9.99</script> in <head>; all 20 rows identical to annual_first (probe dump). Thin: no hostile content inside/around tables (comment, hidden <td>, <style>); test only asserts value != 9.99.
## (7) plan test assertions verbatim — PASS
test_pg_economic_observations.py:22-33 carries 1.25/1.50/1.45/'2025-06-30'/event_id verbatim; fiscal_scope passed as FISCAL_SCOPE constant == ('2026-04-01','2026-06-30','2025-04-01','2025-06-30') (fixture :23).
## (8) Three mutants each fail a NAMED test — PASS (M2 thinly)
Run in throwaway worktree; files restored (git status clean after).
- M1 heading-blind first-table (annual) selection: 4 failed — test_quarter_and_basis_are_bound[annual_first], [columns_reordered], test_blank_is_absent_and_dash_is_neutral_zero, test_multibyte_byte_offsets_are_correct.
- M2 delete the whole span/digest/byte-replay block (economic_observations.py:170-206): 1 failed — test_wrong_event_body_period_basis_or_unit_refused (only its wrong-body / empty-texts subcases). Thin: no dedicated replay test; a mutant that keeps the digest check but drops value<->span binding is already the shipped behaviour (F5).
- M3 zero-fill blank: 1 failed — test_blank_is_absent_and_dash_is_neutral_zero.
## (9) Ownership / no data-site writes / no live values — PARTIAL
Diff = 7 files (5 owned Task-1 files + legacy-jobs.yml + test_ci_pack.py CI wiring); no data/ or site/ paths. Fixture numeric scan (every decimal/4-digit token in tests/earnings_economic_fixtures.py): 2.10/2.40/2.45/2.50, 1.25/1.50/1.45/1.48, drivers 0.5-4.0, 9.99, 0.20/0.05, segments 1.0-5.5; no 4-digit sales, "organic" appears only as label text. One tell: 1.48 as prior Q4 FY2025 core EPS (F8). 1.63 absent.
## (10) CI wiring — PASS (at head 5dadd935)
Job earnings-economic-dossier: gate code, scope exclusive, `if: ${{ false }}` = house convention (229 occurrences). paths cover both files named by run: (tests/test_pg_economic_observations.py, fixture) plus the closure. Non-stdlib imports across all job .py paths = {pytest, yaml}; install line = `pip install pytest pyyaml` (MATCH; at 262bd967 it was `pytest` only -> would have failed; fixed by 5dadd935). CURATED_EXCLUSIVE += "earnings-economic-dossier" (tests/test_ci_pack.py:3535).
`python3 -m pytest tests/test_ci_pack.py -q -p no:cacheprovider -k "exclusive or curated or contract or legacy_jobs"` -> rc=0, "16 passed, 105 deselected in 312.92s".
`python3 scripts/check_contract_delta.py --base origin/main` -> rc=0, "contract-delta: 0 introduced, 1 inherited (base 3ca9c3038061)" (inherited = tests/test_render_dead_ref_targets.py).
F15 [NOTE] plan Task 8 (:84) says extend the existing group containing tests/test_earnings_private_store.py; PR mints a new job instead (seat-ratified per program packet — note only).
## (11) Test / lint runs — PASS
- `python3 -m pytest tests/test_pg_economic_observations.py -q -p no:cacheprovider` -> rc=0, "15 passed in 4.84s"
- `-k 'issuer_profile or event_workspace' --collect-only` hits INTERNALERROR (stripe SDK) on unrelated modules; with --continue-on-collection-errors the matching files are test_company_intelligence_api, _event_compiler_e3a, _event_workspace, test_earnings_evidence_graph_deps, test_issuer_profiles_a5a, test_refresh_event_workspaces -> run whole files: rc=0, "219 passed in 37.54s"
- tests/test_earnings_private_store.py tests/test_earnings_api.py -> rc=0, "30 passed in 7.01s"
- pyflakes 3.4.0 on the five python files -> rc=0 (no output)

## VERDICT: REJECT (repairable — ACCEPT_WITH_REPAIRS once R1–R6 land; dependent T2/T3 lanes must not branch from this head)
Rationale: tests are green and CI wiring is clean, but the extractor binds period by a fixture constant (F2, proven mis-binding under FY2027 scope), 6/8 driver facts are unreachable (F3), and the validator's byte replay does not bind value to span (F5) — the two §2.2/Review-Focus-#2 properties the Task exists to prove.
Minimal repair list:
R1 (F2) derive quarter/year header + row tokens from fiscal_scope/fiscal_period; reconciliation = bounded source paragraph under its heading, not a constant; add a test: FY2027 scope over a table with 2027+2026 rows binds 2027.
R2 (F5) validator parses replayed excerpt (same literal/convention rules) and requires == value; text kinds value == excerpt; add tamper + span-swap tests.
R3 (F3+F4) read driver table by column header (metrics are columns) and reorder driver header+values together; assert at least price/mix/FX/other values in both annual_first and columns_reordered.
R4 (F1) unit-gate literals by definition (no "%" for usd_per_share; accept "$", parenthesised negatives); fix fixture EPS cells.
R5 (F6) replace hard-coded quarter==4 with scope-derived quarter check; (F7) combined-only negative-control test; (F8) replace 1.48.
R6 (minor) F9–F13: check absence authority=='context_only' and subject==metric, span rights_profile != rp_public_primary_v1, fact_id == f"fact_{metric}", EconomicObservationError on missing fiscal_period, dash span covers the dash cell; add ambiguity + dash-without-convention tests.

STATUS: PARTIAL
RESULT: REJECT (repairable); 1 BLOCKER (F2), 7 MAJOR (F1,F3–F8), 5 MINOR (F9–F13), NIT F14, NOTE F15.
EVIDENCE: probe receipts above; mutant runs; rc lines in (10)/(11).
GAPS: no clean-venv run of the CI job; real P&G release structure not examined (out of scope); M2 mutant only killed by one subtest.
DEVIATIONS: throwaway worktree HEAD moved 262bd967 -> 5dadd935 (scratch only) to test the new head; mutants applied/restored in the throwaway tree only.
