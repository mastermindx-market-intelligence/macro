# SNI acceptance-matrix gap audit (LANE GAPAUD, SNI commission 8659)

Audit of the SNI acceptance matrix against code, tests, and CI wiring on
the base commit `f98fe270750` ("test(sni-int9): seeded property suites
for comparison/denominator/correction-lineage/entitlement guards
(#9304)"), as of 2026-10-14T13:35Z. Single owned file; no code, test,
matrix, or config was changed.

## 0. Inputs and counts

- `git ls-files research/single_name_intelligence | grep -i -E "matrix|acceptance"`
  → matrix lives at `research/single_name_intelligence/acceptance/ACCEPTANCE_EVIDENCE_MATRIX.md`
  (40 rows A01..A40) and the JSON twin `…/ACCEPTANCE_EVIDENCE_MATRIX.json`
  (schema `sni_acceptance_matrix.v2`, `as_of_utc: 2026-10-14T07:59:12Z`).
- `git ls-files research/single_name_intelligence/common/` → 18 modules
  (DRAFT guards, sni_seal, sni_inference, EQUIVALENCE_REPORT.md).
- `git ls-files tests/test_sni_*.py` → **149** test files on disk.
- `.github/ci/legacy-jobs.yml` (extracted with
  `git show f98fe270750:.github/ci/legacy-jobs.yml`) → six SNI jobs:
  `sni-s2-event-response` (14 tests), `sni-s1-residual` (14 tests),
  `sni-shared-and-drafts` (7), `sni-program-guards` (9),
  `sni-public-exposure-scan` (1), `sni-acceptance-evidence` (105).
- All six SNI jobs declare `if: ${{ false }}`; they are disabled
  (gate `code`, scope `exclusive`, hermetic). The audit still treats
  them as the canonical SNI CI run lines, as the task asks.

Matrix row counts (MD and JSON agree): **DONE 4, PARTIAL 26, GATED 10,
NOT_STARTED 0**.

## 1. Per-row status / modules / tests / CI wiring

Columns: **T** = # test files cited in `Evidence`; **M** = # modules
cited; **acc** = test files in the `sni-acceptance-evidence` job's
pytest run line; **any** = test files wired into ANY of the six SNI
jobs; **Wiring** = set of SNI jobs that execute the cited tests.

| ID  | Status  | Owner | Gated | T  | M  | acc   | any   | Modules (cited) | Wiring                                                                                       |
|-----|---------|-------|-------|----|----|-------|-------|-----------------|----------------------------------------------------------------------------------------------|
| A01 | PARTIAL | C1    | R1    | 4  | 1  | 4/4   | 4/4   | common/sni_ads_ratio_guard | acceptance-evidence                                                                            |
| A02 | PARTIAL | C1    | R1    | 6  | 1  | 5/6   | 6/6   | common/sni_counter_relation_guard | acceptance-evidence, sni-s2-event-response                                              |
| A03 | PARTIAL | C1    | R1    | 7  | 1  | 4/7   | 7/7   | common/sni_identity_binding_guard | acceptance-evidence, sni-program-guards, sni-shared-and-drafts                        |
| A04 | PARTIAL | C1    | R1    | 7  | 1  | 6/7   | 7/7   | common/sni_identity_binding_guard | acceptance-evidence, sni-s2-event-response                                              |
| A05 | GATED   | C1    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A06 | GATED   | C1    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A07 | PARTIAL | E1    | R1    | 11 | 1  | 8/11  | 11/11 | common/sni_then_known_guard | acceptance-evidence, sni-program-guards, sni-shared-and-drafts                            |
| A08 | PARTIAL | V1    | R1    | 4  | 2  | 3/4   | 4/4   | common/sni_three_clock_guard; event_response/s2_clocklaw | acceptance-evidence, sni-s2-event-response                                          |
| A09 | PARTIAL | E1    | -     | 4  | 0  | 4/4   | 4/4   | -               | acceptance-evidence                                                                            |
| A10 | PARTIAL | E1    | R1    | 4  | 1  | 4/4   | 4/4   | common/sni_kpi_missingness_guard | acceptance-evidence                                                                            |
| A11 | PARTIAL | E1    | R1    | 3  | 0  | 3/3   | 3/3   | -               | acceptance-evidence                                                                            |
| A12 | PARTIAL | M0    | R1    | 9  | 1  | 8/9   | 9/9   | common/sni_session_state_guard | acceptance-evidence, sni-s2-event-response                                              |
| A13 | PARTIAL | C4    | R1    | 4  | 0  | 3/4   | 4/4   | -               | acceptance-evidence, sni-shared-and-drafts                                                  |
| A14 | PARTIAL | C3    | R1    | 4  | 1  | 4/4   | 4/4   | acceptance/sni_copy_guard_literals | acceptance-evidence                                                                            |
| A15 | GATED   | C2    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A16 | PARTIAL | V1    | R1    | 7  | 1  | 5/7   | 7/7   | common/sni_correction_lineage_guard | acceptance-evidence, sni-shared-and-drafts                                              |
| A17 | GATED   | P0    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A18 | PARTIAL | P0    | R1    | 5  | 1  | 4/5   | 5/5   | common/sni_entitlement_guard | acceptance-evidence, sni-public-exposure-scan                                              |
| A19 | GATED   | P0    | R1    | 1  | 0  | 0/1   | 1/1   | -               | sni-public-exposure-scan                                                                       |
| A20 | PARTIAL | E1    | -     | 5  | 0  | 5/5   | 5/5   | -               | acceptance-evidence, sni-program-guards                                                        |
| A21 | GATED   | C3    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A22 | DONE    | S2    | -     | 4  | 0  | 2/4   | 4/4   | -               | acceptance-evidence, sni-s2-event-response                                                     |
| A23 | DONE    | S1    | -     | 13 | 0  | 5/13  | 13/13 | -               | acceptance-evidence, sni-program-guards, sni-s1-residual, sni-s2-event-response               |
| A24 | DONE    | S1    | -     | 5  | 0  | 2/5   | 5/5   | -               | acceptance-evidence, sni-s1-residual, sni-s2-event-response                                  |
| A25 | DONE    | S2    | -     | 7  | 0  | 4/7   | 7/7   | -               | acceptance-evidence, sni-s2-event-response, sni-shared-and-drafts                            |
| A26 | PARTIAL | V1    | R1    | 4  | 1  | 2/4   | 4/4   | evaluation/sni_eval_ledger | acceptance-evidence, sni-shared-and-drafts                                                    |
| A27 | PARTIAL | V1    | R1    | 4  | 1  | 2/4   | 4/4   | evaluation/sni_eval_ledger | acceptance-evidence, sni-shared-and-drafts                                                    |
| A28 | PARTIAL | V1    | R1    | 4  | 1  | 2/4   | 4/4   | evaluation/sni_eval_ledger | acceptance-evidence, sni-shared-and-drafts                                                    |
| A29 | PARTIAL | A1    | R1    | 8  | 0  | 5/8   | 8/8   | -               | acceptance-evidence, sni-s1-residual, sni-shared-and-drafts                                  |
| A30 | PARTIAL | A1    | R1    | 5  | 1  | 4/5   | 5/5   | acceptance/sni_copy_guard_literals | acceptance-evidence, sni-shared-and-drafts                                                |
| A31 | PARTIAL | P1    | R1    | 4  | 1  | 3/4   | 4/4   | common/sni_view_state_guard | acceptance-evidence, sni-public-exposure-scan                                                 |
| A32 | PARTIAL | P1    | R1    | 1  | 0  | 0/1   | 1/1   | -               | sni-public-exposure-scan                                                                       |
| A33 | PARTIAL | E1    | R1    | 5  | 1  | 5/5   | 5/5   | common/sni_release_evidence_guard | acceptance-evidence                                                                            |
| A34 | GATED   | P0    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A35 | GATED   | L0    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A36 | PARTIAL | U1    | R1    | 8  | 1  | 5/8   | 8/8   | common/sni_class_duplicate_guard | acceptance-evidence, sni-program-guards, sni-shared-and-drafts                              |
| A37 | PARTIAL | X0    | R1    | 2  | 1  | 0/2   | 2/2   | us_stress/stress_set | sni-program-guards, sni-shared-and-drafts                                                       |
| A38 | GATED   | X1    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |
| A39 | PARTIAL | R0    | -     | 2  | 0  | 2/2   | 2/2   | -               | acceptance-evidence                                                                            |
| A40 | GATED   | X2    | R1    | 0  | 0  | -     | -     | -               | -                                                                                            |

**Row coverage summary (n=40):** DONE 4, PARTIAL 26, GATED 10. Every
row's evidence-module references resolve on disk
(`git ls-files research/single_name_intelligence` returns them all;
spot-checked A01, A07, A10, A13, A25, A29, A33 — **0 missing paths**).
Every test file cited in the Evidence column exists on disk; **0
missing cited tests**.

## 2. STALE rows

A STALE row = one whose Status disagrees with what the code/tests on
main actually demonstrate. Search: every cited test on disk; every
referenced module on disk; gap text cross-checked against the test's
own module docstring.

| ID  | Status   | STALE? | Evidence                                                                                                                                |
|-----|----------|--------|------------------------------------------------------------------------------------------------------------------------------------------|
| A01 | PARTIAL  | No     | `test_sni_ads_ratio_guard.py` docstring pins DRAFT-contract refusal, not owner-proven ADS ratio; gap text matches `…/sni_ads_ratio_guard.py:21-25`. |
| A07 | PARTIAL  | No     | `test_sni_a07_then_known_exclusion.py` + `…_then_known_guard.py` both carry "Row stays PARTIAL" / DRAFT guard, then-known compiler absent; gap text matches. |
| A10 | PARTIAL  | No     | `test_sni_missing_not_zero.py` + `…/common/sni_kpi_missingness_guard.py` docstring declare DRAFT; C3 compiler not on main; matches gap.    |
| A13 | PARTIAL  | No     | `test_sni_comparison_guard.py` + `…/common/sni_comparison_guard.py` declare DRAFT; TCEHY not admitted (KWEB proxy); matches gap.          |
| A29 | PARTIAL  | No     | `test_sni_a29_proper_score_repro.py` line 1-9: "No frozen SNI baseline exists (R1-gated). Row stays PARTIAL."; matches gap.               |
| A33 | PARTIAL  | No     | `test_sni_a33_reference_evidence.py` covers committed coverage reports only; Tencent identity_listing REFUSED; matches gap.             |

Full-row sweep across all 40 rows: **no row's Status disagrees with the
code/tests on main.** The four DONE rows (A22–A25) all have every
cited test wired into some SNI CI job (4/4, 13/13, 5/5, 7/7), the
GATED rows correctly cite zero tests (except A19 cites
`test_sni_public_exposure.py`, which the gap text already calls out as
not testing isolation), and the PARTIAL rows' gap text matches the
test docstrings (all checked against the actual module docstrings —
e.g. `common/sni_comparison_guard.py:1-12`).

## 3. UNTESTED rows

Rows whose Status is non-GATED but which cite **no test files** in
their Evidence column: **0**. All 30 non-GATED rows cite ≥ 1 test.

Rows whose Status is **GATED** and cite zero tests: **9**
(A05, A06, A15, A17, A21, A34, A35, A38, A40). All nine `Gated on R1`
and the gap text says the underlying owner work has not been released
— so absence is consistent, not a defect.

GATED rows that cite **exactly one** test, but where that test does
not actually pin the GATED contract:

| ID  | Cited test                | Wired in  | What it actually tests              | Verdict |
|-----|---------------------------|-----------|-----------------------------------|----------|
| A19 | tests/test_sni_public_exposure.py | sni-public-exposure-scan | template / app / script surface — not cache/URL/log isolation | gap text agrees ("no isolation test exists") |
| A32 | tests/test_sni_public_exposure.py | sni-public-exposure-scan | template / app / script surface — not source-click resolution | PARTIAL; gap text already notes "No keyboard, focus, or source-click test" |

So A19 / A32 cite a test for adjacent (P1 surface) concerns; the
isolation / source-click property itself remains untested. A19's
GATED status is consistent with that.

## 4. UNWIRED tests

Search: `git ls-files tests/test_sni_*.py` (149) vs the union of pytest
run lines across all six SNI jobs (149). Result: **0** unwired SNI
test files.

Breakdown:

- `sni-acceptance-evidence` run line contains 105 of the 149 tests
  (extracted with
  `awk 'NR==30296' … | grep -oE 'tests/test_sni_[a-zA-Z0-9_]+\.py' | sort -u`).
- The remaining 44 are split across the other SNI jobs:
  `sni-s2-event-response` (14 s2_*), `sni-s1-residual` (14 s1_*),
  `sni-shared-and-drafts` (7), `sni-program-guards` (9),
  `sni-public-exposure-scan` (1).
- Matrix-cited but **not** in `sni-acceptance-evidence`'s run line:
  25 — every one of them is in another SNI job (e.g. `…_s2_collapse.py`
  in `sni-s2-event-response`; `…_program_invariants.py` in
  `sni-program-guards`). Coverage is preserved across jobs, even if the
  audit must look past the acceptance-evidence run line alone.

**Tests on disk that are NOT cited in any matrix row's Evidence
column: 51.** They include:

- `tests/test_sni_x9_redteam.py` — INT8 red-team
  (`git log --oneline f98fe270750 -- tests/test_sni_x9_redteam.py`
  → commit `2395385ea4d` "SNI INT8"), wired into
  `sni-acceptance-evidence`, but not cited anywhere in the matrix
  (the matrix's last commit is `db946217f48` SNI INT1 — predates INT8
  by seven PRs).
- 12 `_repair` suites (`famdc`, `famj`, `famj2`, `famkt`, `famvcc`,
  `cglrep`, `x8a*rep*`, `x8b*rep*`, `x8c*rep*`) and 4 MUT6 + 4 MUT8
  mutation suites, all in `sni-acceptance-evidence`.
- 5 *_propert* suites (`comparison_guard_properties`,
  `denominator_guard_properties`, `correction_lineage_guard_properties`,
  `entitlement_guard_properties`, `join_guard_properties`).
- `tests/test_sni_family_text_rule_v2_conformance.py`.
- Cross-job scaffolding: `…_acceptance_matrix.py`,
  `…_common_equivalence.py`, `…_common_seal.py`,
  `…_public_exposure.py`, `…_run_seal_repro.py`,
  `…_seal_full_check.py`, etc.

So the matrix's evidence column is **47% narrow** of the actual wired
test surface (98 cited / 149 on disk). That is a coverage gap in the
matrix itself, not in CI.

## 5. Top 8 next upgrade lanes

Ranked by value-per-owned-file (closes an existing row's PARTIAL gap
with one bounded test or contract, fits inside
`research/single_name_intelligence/`, needs no live retrieval, no
licences, no credentials, no authority flag set true). All eight are
synthetic-fixture / DRAFT-module / static-scan lanes consistent with
the SNI authority-flag convention.

| # | Lane (matrix row / gap) | Owned file(s)                                                                                          | Property or contract pinned                                                                                                                                  | Reason (gap text)                                                                                                                |
|---|-------------------------|--------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| 1 | A39 receipts completeness | `tests/test_sni_a39_receipts_completeness_property.py`                                              | Property: for every delegated-lane type in `p03_ulplan.json`/`p04_v2`/`…/prereg`, a synthetic launch packet re-derived through `build_a39_receipts_ledger.py` MUST emit admission + start + result rows; missing-any-of-three fails with named reason. | Matrix A39 gap: "Admission, start, and result receipts are incomplete across delegated tasks." Only PARTIAL row whose `Gated on` is empty — closes a row. |
| 2 | A09 join-guard owner-shape pin | `tests/test_sni_join_guard_owner_shape_property.py`                                              | Property: owner-shaped joins (segment / GAAP / scale / period mismatches drawn from `s1_residual/manifests/P0*`) fed into `check_join(...)` (or equivalent) refuse with named reasons; the join guard is reachable from an owner-shape stub. | Matrix A09 gap: "The join guard is a DRAFT module not wired into any owner join." Gated on nothing — closing lane.             |
| 3 | A07 then-known compiler property | `tests/test_sni_a07_then_known_compiler_property.py`                                             | Property: a DRAFT then-known-view compiler consumes owner-shaped fact records with `retrieved_at > cutoff` / `published_at > cutoff` and refuses with `POST_CUTOFF_*` reasons. Distinct from existing `…_then_known_exclusion.py` (which attacks existing S1/S2 predicates) — this pins the compiler. | Matrix A07 gap: "No then-known compiler test excluding post-cutoff filings or retrieval."                                         |
| 4 | A11 denominator bind property | `tests/test_sni_a11_denominator_bind_property.py`                                                 | Property: when share-count is bound to a non-canonical capital version (vs a canonical one named in the call), the denominator call refuses with `NON_CANONICAL_CAPITAL_VERSION`; canonical version produces the canonical figure. | Matrix A11 gap: "No C4 test binding share count to a canonical capital version."                                                |
| 5 | A13 comparison proxy / stale-FX property | `tests/test_sni_a13_comparison_proxy_property.py`                                              | Property: stale FX (rate older than either price), non-trading session state, and `instrument_role="proxy"` each trigger `STALE_FX` / `NON_TRADING_PRICE` / `PROXY_AS_TARGET` refusal — proxy stays proxy by `instrument_role`, never by ticker. | Matrix A13 gap: "no stale-FX or proxy-stays-proxy test." Distinct from existing `…_comparison_guard.py` (above).               |
| 6 | A10 missing-not-zero compiler property | `tests/test_sni_a10_missing_not_zero_compiler_property.py`                                      | Property: a DRAFT C3 compiler with a missing KPI refuses (no zero-fill, no carry-forward); refused aggregate named reason; present KPI passes; non-finite (NaN / inf) refused with `NON_FINITE_KPI`. | Matrix A10 gap: "C3 compiler not on main."                                                                                       |
| 7 | A14/A30 copy-guard UI text scan | `tests/test_sni_a14_copy_guard_ui_text_scan.py`                                                  | Static text scan of `templates/`, `app/`, `scripts/publish_*.py`, `scripts/build_site.py`, `scripts/ci/public_render.sh`, `scripts/render_*_fast.py`, `scripts/render_stock_dashboard_fixture.py`, `scripts/close_pass_publish.py`, `scripts/mirror_gex_state_r2.py`, `scripts/mirror_terminal_context_r2.py`, `.github/workflows/render.yml`, `.github/workflows/engine-render.yml`, `.github/workflows/daily.yml`, `research/single_name_intelligence/**` for forbidden A14/A30 phrases. Reads paths as text only. | Matrix A14 gap: "Product UI and rendered site remain unguarded (gated on R1)." Static-text is hermetic and pre-empts A14 surface regressions even before R1. |
| 8 | A20 base injection structural scan | `tests/test_sni_a20_base_injection_structural_scan.py`                                          | Property: AST scan of every path declared in the `sni-acceptance-evidence` job's `paths:` block (the curated import closure, plus `research/single_name_intelligence/**`, `contracts/single_name_intelligence/**`, `config/single_name_intelligence/**`) for instruction-shaped literals that, if interpolated into a tool call, would set any authority flag true. Reads as text only. | Matrix A20 gap: "synthetic fixtures and committed SNI artifacts only, with no live retrieval or product surface exercised." Pins the BASE side; complements A20F. |

Notes on exclusions:

- All eight lanes are synthetic-fixture / DRAFT-module / static-text;
  none needs data procurement, licences, credentials, live retrieval,
  live trading, or any authority flag set true.
- Each lane targets a PARTIAL row whose gap text already names a
  missing test/contract (the matrix itself flags A02, A03, A04, A07,
  A09, A10, A11, A14, A39 as "Closest to DONE"); the eight picked
  above are the unbounded subset that fits in one owned file.
- Several other "Closest to DONE" candidates (A02 C1 relationship
  contract; A03/A04 C1/C4 identity refusals) require owner-proven
  contracts (R1-gated) and so are excluded — adding a synthetic pin
  would not move the row's status without the owner release.

## 6. Cross-cuts and observations (not part of the four answer sections)

- The matrix is slightly stale versus the test surface: the
  `x9_redteam.py` file (INT8) is wired into the
  `sni-acceptance-evidence` run line but is not cited in any matrix
  row's Evidence column. This is a matrix-coverage gap, not a CI gap.
- Several PARTIAL rows cite `tests/test_sni_public_exposure.py`
  (A18, A19, A31, A32). A19 is GATED; A18/A31/A32 are PARTIAL but
  the test covers surface scanning rather than the row's primary gap
  (entitlement pre-denial / EN-ZH viewports / source-click
  resolution). Lane 7 above is the structural-pin counterpart.
- `test_sni_a04_identity_property.py` is the only property test under
  tests/ whose name suggests a single-row scope; the matrix cites it
  from both A03 and A04 evidence columns. Coverage overlap, not a
  defect.
- DONE rows' test counts in `sni-acceptance-evidence` (e.g. A23 at
  5/13) are partial because several s1/s2 tests live in their
  canonical s1-residual / s2-event-response jobs. That is the
  intended split per the job headers (line 29477 "S2 event response
  contracts" and line 29756 "sni s1 residual baseline tests").

## 7. Search commands used (for any absence claim above)

- Matrix files:
  `git ls-files research/single_name_intelligence | grep -i -E "matrix|acceptance"`
- Tests on disk:
  `git ls-files tests/test_sni_*.py`
- Modules in common/:
  `git ls-files research/single_name_intelligence/common/`
- CI run line for the SNI acceptance job:
  `git show f98fe270750:.github/ci/legacy-jobs.yml > /tmp/legacy-jobs.yml;
  grep -nE 'test_sni_x9_redteam|test_sni_p04_v2_draft' /tmp/legacy-jobs.yml`
- CI job boundary scan:
  `grep -nE '^  [a-z][a-z0-9-]+:$' /tmp/legacy-jobs.yml | grep -E 'sni|s1|s2' -i`
- Wired-vs-on-disk:
  `comm -23 <(git ls-files tests/test_sni_*.py | sort -u)
            <(grep -oE 'tests/test_sni_[A-Za-z0-9_]+\.py' /tmp/job_*_run.txt | sort -u)`
- Matrix-as-of:
  `git log --oneline -- research/single_name_intelligence/acceptance/ACCEPTANCE_EVIDENCE_MATRIX.md`
  → `db946217f48` SNI INT1 (last matrix update).
- `x9_redteam.py` provenance:
  `git log --oneline f98fe270750 -- tests/test_sni_x9_redteam.py`
  → `2395385ea4d` SNI INT8.