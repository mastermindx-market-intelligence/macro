# MUT5C mutation sweep — run_s1.py (load_frames+) / s1_data.py — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing importer tests against the second half of `run_s1.py` (functions
defined from line 462 `load_frames` to EOF) and all of `s1_data.py`. It does
not move any acceptance row to DONE. Authority flags stay false; identity
ids remain caller-supplied opaque strings. Fixtures in the killing tests
are synthetic. `s1_data.py` / `run_s1.py` consume owner-supplied pins,
identity strings, and sealed run bytes; this lane does not mint them.

Existing tests that import these modules (grep of `tests/test_sni_*.py`):

`run_s1` importers (86 passed in 35.07 s unmutated; cap 15 mutants because
that is > 20 s):

- `tests/test_sni_s1_info_leak.py`
- `tests/test_sni_quarantine_fence.py`
- `tests/test_sni_s1_cli.py`
- `tests/test_sni_s1_v1_2_hash_invariant.py`
- `tests/test_sni_s1_v1_1_hardening.py`
- `tests/test_sni_p03_ulp_stability.py`
- `tests/test_sni_s1_seal_integrity.py`
- `tests/test_sni_s1_report_order.py`
- `tests/test_sni_s1_ledger_order.py`

`s1_data` importers (35 passed in 4.65 s unmutated; cap 30):

- `tests/test_sni_missing_not_zero.py`
- `tests/test_sni_s1_challenger.py`
- `tests/test_sni_mutation_prereg_challenger.py`
- `tests/test_sni_s1_manifest.py`

## Summary

| item | count |
|---|---|
| generated (selected) | 45 |
| killed-before | 14 |
| survived-before | 30 |
| killed-after | 30 |
| equivalent | 0 |
| timeout | 1 |
| score before | 14/45 = 31.1% |
| score after | 44/45 = 97.8% |
| new killing tests | 30 |

Candidate sites before sampling: 214 owned in `run_s1.py` (373 in the full
file; 143 outside the line-462 function range; 2 identity `0.0 * 1.001`;
14 extra `return_none` beyond one per function), 32 in `s1_data.py` (34
raw, 2 extra returns dropped). Cap 15 / 30, seed `20261013`, stratified
by function. QF exact-line exclusions collected 0 sites.

Score = killed / generated. The TIMEOUT mutant stays in the denominator
of the after score as not-killed.

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut5c/harness.py`, not committed):

- comparison flip: `<`↔`>`, `<=`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.
Identity mutants (`0.0 * 1.001 == 0.0`) were dropped before sampling.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, then original bytes were restored and sha256-checked before the next.
After every mutant, `git status --porcelain -- research/` was inspected;
no residual/event_response writes other than the module under mutation.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `run_s1.py` (from `load_frames`) | 214 | 15 | 7 | 7 | 7 | 0 | 1 | 7/15 | 14/15 |
| `s1_data.py` | 32 | 30 | 7 | 23 | 23 | 0 | 0 | 7/30 | 30/30 |
| **total** | **246** | **45** | **14** | **30** | **30** | **0** | **1** | **14/45** | **44/45** |

`run_s1.py` importer set took 35.07 s (> 20 s), so that module is capped
at 15 mutants.

## Surviving-mutant list with killing test name

All 30 non-timeout non-killed mutants were re-applied against the named
new test and failed (KILLED-after). `run_s1_13` was re-verified after the
killing assertion was pointed at `d[-1]` of a later series (col 67).

### run_s1.py

| file:line | original → mutated | killing test |
|---|---|---|
| `run_s1.py:1113` | `committed / rel` → `*` | `test_mut5c_run_s1__byte_compare_1` |
| `run_s1.py:1145` | `_ledger_equal` return → `None` | `test_mut5c_run_s1__ledger_equal_1` |
| `run_s1.py:1128` | `na != nb` → `==` | `test_mut5c_run_s1__tree_equal_1` |
| `run_s1.py:603` | `g[3]` → `g[4]` | `test_mut5c_run_s1_challenger_apply_1` |
| `run_s1.py:511` | `model == "M1"` → `!=` | `test_mut5c_run_s1_evaluate_p03_1` |
| `run_s1.py:468` | `d[-1]` → `d[-2]` (max last_bar) | `test_mut5c_run_s1_load_frames_1` |
| `run_s1.py:849` | `ctx is not None and not estimable` → `or` | `test_mut5c_run_s1_log_p03_configs_1` |

### s1_data.py

| file:line | original → mutated | killing test |
|---|---|---|
| `s1_data.py:93` | cached `_blob_file` return → `None` | `test_mut5c_s1_data_GitBlobStore__blob_file_1` |
| `s1_data.py:97` | `Path / name` → `*` | `test_mut5c_s1_data_GitBlobStore__blob_file_2` |
| `s1_data.py:54` | delete git-nonzero raise | `test_mut5c_s1_data_GitBlobStore__git_bytes_1` |
| `s1_data.py:53` | `capture_output=True` → `False` | `test_mut5c_s1_data_GitBlobStore__git_bytes_2` |
| `s1_data.py:56` | `return r.stdout` → `None` | `test_mut5c_s1_data_GitBlobStore__git_bytes_3` |
| `s1_data.py:54` | `returncode != 0` → `== 0` | `test_mut5c_s1_data_GitBlobStore__git_bytes_4` |
| `s1_data.py:59` | `_git_text` return → `None` | `test_mut5c_s1_data_GitBlobStore__git_text_1` |
| `s1_data.py:73` | `ref or self.input_ref` → `and` | `test_mut5c_s1_data_GitBlobStore_commit_date_iso_1` |
| `s1_data.py:72` | `commit_date_iso` return → `None` | `test_mut5c_s1_data_GitBlobStore_commit_date_iso_2` |
| `s1_data.py:119` | `frame` return → `None` | `test_mut5c_s1_data_GitBlobStore_frame_1` |
| `s1_data.py:111` | `index_dates` return → `None` | `test_mut5c_s1_data_GitBlobStore_index_dates_1` |
| `s1_data.py:65` | `list_dir` return → `None` | `test_mut5c_s1_data_GitBlobStore_list_dir_1` |
| `s1_data.py:126` | `read_columns` return → `None` | `test_mut5c_s1_data_GitBlobStore_read_columns_1` |
| `s1_data.py:68` | `rev_parse_ref_path` return → `None` | `test_mut5c_s1_data_GitBlobStore_rev_parse_ref_path_1` |
| `s1_data.py:105` | `schema` return → `None` | `test_mut5c_s1_data_GitBlobStore_schema_1` |
| `s1_data.py:81` | `got != want` → `==` | `test_mut5c_s1_data_GitBlobStore_verify_pin_1` |
| `s1_data.py:84` | `verify_pin` return `got` → `None` | `test_mut5c_s1_data_GitBlobStore_verify_pin_2` |
| `s1_data.py:81` | delete PIN MISMATCH raise | `test_mut5c_s1_data_GitBlobStore_verify_pin_3` |
| `s1_data.py:191` | `IndexOnlySpy.list_dir` return → `None` | `test_mut5c_s1_data_IndexOnlySpy_list_dir_1` |
| `s1_data.py:183` | `IndexOnlySpy.schema` return → `None` | `test_mut5c_s1_data_IndexOnlySpy_schema_1` |
| `s1_data.py:166` | `commit_date_iso` stamp → `None` | `test_mut5c_s1_data_InjectableStore_commit_date_iso_1` |
| `s1_data.py:162` | `read_columns` return → `None` | `test_mut5c_s1_data_InjectableStore_read_columns_1` |
| `s1_data.py:32` | `_to_date` datetime branch → `None` | `test_mut5c_s1_data__to_date_1` |

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill, other
than the TIMEOUT below, was observable through a new test.

## Timeout

`run_s1_10` `build_challenger_context:539` `or` → `and` on
`t >= TRAIN_END or t < date(2012, 1, 4)` removes the train-window skip
and walks every panel date. The importer suite hit the 60 s `timeout`
(TIMEOUT, not SURVIVED). No killing test was added for it.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
fence points inside this lane's owned `run_s1.py` range:

- `residual/run_s1.py:486` — `evaluate_p03` skip non-TRAIN/TUNE
- `residual/run_s1.py:643` — P03 calibration TRAIN/TUNE-only
- `residual/run_s1.py:650` — P03 comparison TRAIN/TUNE-only

Those exact lines had **zero** operator sites (string literals in a
containment test / for-loop targets, not `< <= > >= == !=`, arithmetic,
boolops, int/float/bool constants, `return`, or `if ...: raise`). No
mutant was drawn on them. `s1_data.py` has no QF fence points.

## What this does NOT prove

Mutation score is test strength against this operator set and this
15+30 sample, not statistical validity of SNI estimators or sealed
receipts. A killed mutant does not mean a CI is well-calibrated. No
acceptance-matrix row moves to DONE. The sweep does not claim
completeness over unselected sites (214+32 candidates, 45 applied) or
over the first half of `run_s1.py` (owned by the sibling lane). The
TIMEOUT mutant is unscored as killed. Nothing here feeds a ranker,
gate, sizer, signal, escalation, or trade path.
