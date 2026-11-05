# MUT5B mutation sweep — `run_s1.py` (SealMismatch .. load_frames) — 2026-10-13

SNI-local DRAFT contract review. `run_s1.py` consumes owner-supplied
identity strings, sealed run bytes, and registry values (Stock Identity /
Data OS / Company Event / FIF / qledger); it does not mint issuer or
security ids. HISTORICAL-DESCRIPTIVE only: `rank_authority`,
`gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. Fixtures in the
killing tests are synthetic. No production module was edited.

Harness (not committed): `~/lanes/scratch/mut5b/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next.

Owned site range: functions defined between line 91 (`class SealMismatch`)
and line 462 (`load_frames`, exclusive). `FACTOR_PATHS` / `ALL_SERIES`
module constants and `load_frames` onward are out of range.

Unmutated importer suite: 86 passed in 32.61 s (> 20 s), so this module
was capped at 15 mutants.

## Summary

| item | count |
|---|---|
| generated (selected sites) | 15 |
| killed-before (existing importer suite) | 6 |
| survived-before (non-equivalent) | 9 |
| killed-after (new `test_mut5b_*`) | 9 |
| equivalent | 0 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| score before | 6 / 15 = 40.0% |
| score after | 15 / 15 = 100% |
| new killing tests | 9 |

Score = killed / (generated − equivalent). Wall-clock of the 15 runs:
330.4 s. 0 xfails.

`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --strict-bytes` → `SEAL FULL CHECK: DIFFERS` (10 P03 observation/result files, the named ULP set). Without `--strict-bytes`: `SEAL FULL CHECK: OK (10 files float-equivalent on Linux x86_64 within rel 1e-10 / abs 1e-13, not byte-identical; byte identity rests on the XREP Linux receipt)`. Residual/event_response bytes were not edited; this is host float drift, not a mutant leftover.
`git status --porcelain -- research/` after every mutant showed only the
mutated `run_s1.py` (then restored). Committed diff contains zero bytes
under `residual/` and `event_response/`.

## Operator set and seed

Seed: `20261013`. Cap 15 (slow-suite rule; otherwise 30). Stratified by
function (round-robin over `sorted(function names)`, sites shuffled per
function with the same RNG). `return x` → `return None` is one return per
function. IEEE-identical `0.0 * 1.001` constants were dropped before
sampling.

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (bare `return` / `return None` skipped)
- `and`↔`or`
- deletion of one `if ...: raise` guard

Annotations and docstrings were not mutated.

Kill suite (tests that import `run_s1`; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `tests/test_sni_s1_cli.py`
- `tests/test_sni_s1_seal_integrity.py`
- `tests/test_sni_s1_info_leak.py`
- `tests/test_sni_s1_ledger_order.py`
- `tests/test_sni_s1_report_order.py`
- `tests/test_sni_s1_v1_1_hardening.py`
- `tests/test_sni_s1_v1_2_hash_invariant.py`
- `tests/test_sni_quarantine_fence.py`
- `tests/test_sni_p03_ulp_stability.py`

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `run_s1.py` (owned range) | 132 | 15 | 6 | 9 | 0 | 0 | 9 | 6/15 → 15/15 |

Selected-by-function (after stratification; cap 15 = one site per
function that had candidates):

| function | sites | selected |
|---|---|---|
| `_stamp_s1h2_repair` | 9 | 1 |
| `canon` | 3 | 1 |
| `code_tree_sha` | 2 | 1 |
| `coverage_hole_0700` | 2 | 1 |
| `directional_blocks` | 53 | 1 |
| `doc_json` | 3 | 1 |
| `evaluate_directional` | 10 | 1 |
| `git_out` | 5 | 1 |
| `leg_simple_ret` | 10 | 1 |
| `load_close_maps` | 2 | 1 |
| `rebuild_manifests` | 2 | 1 |
| `retired_scope_pairs` | 3 | 1 |
| `seal_commit_sha` | 2 | 1 |
| `verify_seal` | 23 | 1 |
| `write_json` | 3 | 1 |
| `SealMismatch` (empty class) | 0 | 0 |

117 candidate sites sat outside the 15-cap sample and were not run.
They are not in the score.

Killed-before (existing importer suite):

| id | file:line | function | original → mutated |
|---|---|---|---|
| run_s1_01 | `run_s1.py:134` | `_stamp_s1h2_repair` | `+` → `-` |
| run_s1_04 | `run_s1.py:182` | `coverage_hole_0700` | `return` coverage-hole string → `return None` |
| run_s1_10 | `run_s1.py:277` | `load_close_maps` | `return d, maps` → `return None` |
| run_s1_12 | `run_s1.py:176` | `retired_scope_pairs` | `return out` → `return None` |
| run_s1_14 | `run_s1.py:252` | `verify_seal` | path `/` → `*` |
| run_s1_15 | `run_s1.py:110` | `write_json` | `parents=True` → `False` |

## Surviving-mutant list with killing test name

All nine non-equivalent survivors were re-applied after the new test was
added and failed that test.

| id | file:line | function | original → mutated | killing test |
|---|---|---|---|---|
| run_s1_02 | `run_s1.py:99` | `canon` | `sort_keys=True` → `False` | `test_mut5b_run_s1_canon_1` |
| run_s1_03 | `run_s1.py:153` | `code_tree_sha` | BoolOp `or` → `and` | `test_mut5b_run_s1_code_tree_sha_1` |
| run_s1_05 | `run_s1.py:342` | `directional_blocks` | TUNE `abstain_resolver_none` init `0` → `1` | `test_mut5b_run_s1_directional_blocks_1` |
| run_s1_06 | `run_s1.py:106` | `doc_json` | `ensure_ascii=False` → `True` | `test_mut5b_run_s1_doc_json_1` |
| run_s1_07 | `run_s1.py:310` | `evaluate_directional` | `s - timedelta` → `s + timedelta` | `test_mut5b_run_s1_evaluate_directional_1` |
| run_s1_08 | `run_s1.py:144` | `git_out` | `return stdout.strip()` → `return None` | `test_mut5b_run_s1_git_out_1` |
| run_s1_09 | `run_s1.py:269` | `leg_simple_ret` | `a <= 0` → `a < 0` | `test_mut5b_run_s1_leg_simple_ret_1` |
| run_s1_11 | `run_s1.py:201` | `rebuild_manifests` | `dates[-1]` → `dates[-2]` | `test_mut5b_run_s1_rebuild_manifests_1` |
| run_s1_13 | `run_s1.py:158` | `seal_commit_sha` | BoolOp `or` → `and` | `test_mut5b_run_s1_seal_commit_sha_1` |

Re-verify FAIL lines (two samples; all nine killed):

- run_s1_02 / `test_mut5b_run_s1_canon_1`:
  `assert '{"z":1,"a":2}' == '{"a":2,"z":1}'` (`sort_keys` dropped)
- run_s1_07 / `test_mut5b_run_s1_evaluate_directional_1`:
  `assert 'ABSTAIN_FILL_MISMATCH' == 'OK'` (as-of date flipped past the fill)

The existing importer suite never pinned `canon` key order, never read
`code_tree_sha` / `seal_commit_sha` / `git_out` return values, never
asserted TUNE `abstain_resolver_none == 0` on a zero-init, never put
non-ASCII through `doc_json`, never checked directional excess on a
synthetic TRAIN row, never passed a zero close through `leg_simple_ret`,
and never captured `rebuild_manifests` `last_bar`.

## Equivalent arguments

None. Every selected mutant was either killed by the existing suite or
killed after a new test. No identity-noop applies were observed.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
points in this owned range:

| QF # | file:line | construct | mutants excluded |
|---|---|---|---|
| 12 | `run_s1.py:309` | `evaluate_directional` TRAIN/TUNE-only excess | 0 (the line is `if m["split"] in (...)`; `in` is outside the operator set) |
| 14 | `run_s1.py:349` | missing-endpoint count TRAIN/TUNE-only | 1 (`and` → `or` on the TRAIN/TUNE conjunct) |
| 13 | `run_s1.py:353` | `directional_blocks` TRAIN/TUNE-only stats loop | 0 (the line is `for split in (...)`; no comparison/arith/const/boolop/return/raise site) |

QF points 15–17 (`evaluate_p03` / P03 calibration / comparison) are at
lines 486 / 643 / 650, outside this lane's owned range.

One candidate site excluded on QF grounds: `directional_blocks` L349
BoolOp `and` → `or`.

## What this does NOT prove

Mutation score is test strength against this operator set and this
sampled site list, not statistical validity of the directional hit-rate,
sign-test, or excess estimators, and not byte-reproducibility of a
sealed S1 run. Unselected sites (117 of 132) are unscored. The second
half of `run_s1.py` (`load_frames` onward) is out of range. No
acceptance-matrix row moves to DONE. Nothing here feeds a ranker, gate,
sizer, signal, escalation, or trade path.
