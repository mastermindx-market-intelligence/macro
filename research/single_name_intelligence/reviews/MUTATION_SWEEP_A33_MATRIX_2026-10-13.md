# MUT4E mutation sweep — A33 checker / render_matrix — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing importer tests against two acceptance-evidence modules. It
does not move any acceptance row to DONE. Authority flags stay false;
identity ids remain caller-supplied opaque strings. Fixtures in the
killing tests are synthetic. No production module was edited.

Existing tests that import these modules:

- `tests/test_sni_a33_reference_evidence.py` — `a33_reference_evidence_check`
- `tests/test_sni_acceptance_matrix.py` — `render_matrix`

Kill suite used for scoring: those two files only. Unmutated run:
16 passed (A33, 0.71 s) and 11 passed (matrix, 0.65 s). Neither exceeded
20 s, so the cap stayed at 30 mutants per module.

## Summary

| item | count |
|---|---|
| generated (selected sites) | 60 |
| killed-before (existing importer suite) | 38 |
| survived-before (non-equivalent) | 21 |
| killed-after (new `test_mut4e_*`) | 21 |
| equivalent | 1 |
| timeout | 0 |
| TIMEOUT-UNSAFE (runs/ dirty) | 0 |
| score before | 38 / 59 = 64.4% |
| score after | 59 / 59 = 100% |
| new killing tests | 21 |

Score = killed / (generated − equivalent). Wall-clock of the 60 runs:
54.6 s. 0 xfails. Candidate sites before sampling: 43 in
`a33_reference_evidence_check.py`, 52 in `render_matrix.py`. Cap 30 per
module, seed `20261013`, stratified by function.

`SEAL FULL CHECK: OK` from
`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --strict-bytes`
after the sweep (s1 48 compared / 0 failures; s2 23 compared / 0 failures).

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut4e/harness.py`, not committed):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n → n+1`, float `x → x*1.001` (identity
  `0.0 * 1.001 == 0.0` dropped before sampling), `True`↔`False`
- `return x` → `return None` (bare `return` / `return None` skipped)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, then original bytes were restored and sha256-checked before the next.
After every mutant, `git status --porcelain -- research/` was compared;
any change outside the mutated file (including
`research/single_name_intelligence/runs/`) would have been restored and
classified TIMEOUT-UNSAFE. None fired.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `a33_reference_evidence_check.py` | 43 | 30 | 20 | 10 | 10 | 0 | 0 | 20/30 | 30/30 |
| `render_matrix.py` | 52 | 30 | 18 | 11 | 11 | 1 | 0 | 18/29 | 29/29 |
| **total** | **95** | **60** | **38** | **21** | **21** | **1** | **0** | **38/59** | **59/59** |

Selected-by-function (after stratification):

| module | function | sites | selected |
|---|---|---|---|
| a33 | `_class_gap_reason` | 3 | 3 |
| a33 | `a33_class_table` | 3 | 3 |
| a33 | `owner_path_error` | 9 | 4 |
| a33 | `real_cells` | 9 | 4 |
| a33 | `real_evidence_present` | 2 | 2 |
| a33 | `recount_statuses` | 4 | 4 |
| a33 | `reference_floor` | 4 | 4 |
| a33 | `refuse_authority_grant` | 2 | 2 |
| a33 | `strip_owner_suffix` | 1 | 1 |
| a33 | `structural_errors` | 6 | 3 |
| matrix | `<module>` | 1 | 1 |
| matrix | `_cell` | 1 | 1 |
| matrix | `_evidence_cell` | 1 | 1 |
| matrix | `_gated_on_cell` | 2 | 2 |
| matrix | `_is_done_evidence_path` | 3 | 3 |
| matrix | `_walk_authority` | 3 | 3 |
| matrix | `check_counts` | 9 | 3 |
| matrix | `check_done_status_law` | 7 | 3 |
| matrix | `check_gated_status_law` | 6 | 3 |
| matrix | `check_main_evidence_paths` | 3 | 3 |
| matrix | `check_non_done_gaps` | 5 | 3 |
| matrix | `load_matrix` | 1 | 1 |
| matrix | `main` | 1 | 1 |
| matrix | `render` | 9 | 2 |

## Surviving-mutant list with killing test name

All 21 non-equivalent survivors were re-applied against the named new test
and failed (KILLED-after). Production bytes were restored and sha256-checked
after each re-verify.

### a33_reference_evidence_check.py

| file:line | original → mutated | killing test |
|---|---|---|
| `a33_reference_evidence_check.py:276` | `blocking or []` → `and` | `test_mut4e_a33_reference_evidence_check__class_gap_reason_1` |
| `a33_reference_evidence_check.py:222` | return prefix-not-allowed → `None` | `test_mut4e_a33_reference_evidence_check_owner_path_error_1` |
| `a33_reference_evidence_check.py:311` | `live_ok and in_real` → `or` | `test_mut4e_a33_reference_evidence_check_reference_floor_1` |
| `a33_reference_evidence_check.py:246` | non-int `rows` check `or` → `and` | `test_mut4e_a33_reference_evidence_check_real_cells_1` |
| `a33_reference_evidence_check.py:283` | return `f"{cls}: {status}"` → `None` | `test_mut4e_a33_reference_evidence_check__class_gap_reason_2` |
| `a33_reference_evidence_check.py:333` | table `blocking or []` → `and` | `test_mut4e_a33_reference_evidence_check_a33_class_table_1` |
| `a33_reference_evidence_check.py:210` | `posix == "tests" or startswith("tests/")` → `and` | `test_mut4e_a33_reference_evidence_check_owner_path_error_2` |
| `a33_reference_evidence_check.py:246` | `rows <= 0` → `rows < 0` | `test_mut4e_a33_reference_evidence_check_real_cells_2` |
| `a33_reference_evidence_check.py:205` | return non-string owner error → `None` | `test_mut4e_a33_reference_evidence_check_owner_path_error_3` |
| `a33_reference_evidence_check.py:310` | `isinstance(best_cell, str) and best_cell in cells` → `or` | `test_mut4e_a33_reference_evidence_check_reference_floor_2` |

### render_matrix.py

| file:line | original → mutated | killing test |
|---|---|---|
| `render_matrix.py:61` | return `startswith(RUNS_PREFIX)` → `None` | `test_mut4e_render_matrix__is_done_evidence_path_1` |
| `render_matrix.py:137` | delete counts-mismatch raise | `test_mut4e_render_matrix_check_counts_1` |
| `render_matrix.py:110` | delete `"R1" not in gap` raise | `test_mut4e_render_matrix_check_gated_status_law_1` |
| `render_matrix.py:120` | delete gap-must-be-string raise | `test_mut4e_render_matrix_check_non_done_gaps_1` |
| `render_matrix.py:219` | `parent / json_name` → `*` | `test_mut4e_render_matrix_main_1` |
| `render_matrix.py:60` | `return True` → `False` (test_sni path) | `test_mut4e_render_matrix__is_done_evidence_path_2` |
| `render_matrix.py:87` | `ok = False` → `True` | `test_mut4e_render_matrix_check_done_status_law_1` |
| `render_matrix.py:71` | delete missing-file raise | `test_mut4e_render_matrix_check_main_evidence_paths_1` |
| `render_matrix.py:60` | `return True` → `None` (test_sni path) | `test_mut4e_render_matrix__is_done_evidence_path_3` |
| `render_matrix.py:89` | `ref == "main" and done-path` → `or` | `test_mut4e_render_matrix_check_done_status_law_2` |
| `render_matrix.py:123` | delete DONE-gap-must-be-empty raise | `test_mut4e_render_matrix_check_non_done_gaps_2` |

## Equivalent arguments

`render_matrix.py:225` `__name__ == "__main__"` → `!=`. Under pytest the
imported module's `__name__` is never `"__main__"`. Flipping the comparison
would call `main()` on import, which rewrites
`ACCEPTANCE_EVIDENCE_MATRIX.md` with identical bytes, so the importer suite
cannot observe a failure. Classified EQUIVALENT; no killing test.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `residual/s1_manifest.py`, `s1_prereg.py`,
`s1_report.py`, `run_s1.py`, `event_response/s2_seal.py`, `s2_splits.py`,
`run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md`. **None of those
lines are in `a33_reference_evidence_check.py` or `render_matrix.py`.**
No mutant sites were excluded under the QF fence.

## What this does NOT prove

Mutation score is test strength against this operator set and this
30-per-module sample, not statistical validity of SNI estimators and not
completeness of A33 coverage. A killed mutant does not mean an acceptance
row is ready. No acceptance-matrix row moves to DONE. The sweep does not
claim completeness over unselected sites (43+52 candidates, 60 applied).
Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path.
