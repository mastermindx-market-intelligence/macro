# MUT3A mutation sweep — sni_eval_ledger / seal_full_check — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing import tests against the evaluation ledger and full-coverage
seal verifier. It does not move any acceptance row to DONE. Authority flags
stay false; identity ids remain caller-supplied opaque strings. Fixtures in
the killing tests are synthetic. No production module was edited.

Existing tests that import these modules:

- `tests/test_sni_eval_ledger.py` — `sni_eval_ledger`
- `tests/test_sni_eval_ledger_property.py` — `sni_eval_ledger`
- `tests/test_sni_seal_full_check.py` — `seal_full_check`

`tests/test_sni_injection_safety.py` names `seal_full_check.py` in a path
table and does not import the module; it was not in the kill suite.

Kill suite used for scoring:

- ledger: both importer files (60 passed on unmutated code in 28.42 s)
- seal: `test_schk_01`, `test_schk_02`, `test_schk_07`, `test_schk_08`
  (`test_schk_03` / `04` / `05` / `06` deselected: sparse worktree has no
  `runs/` JSON and no `residual/` / `event_response/` runners; those four
  fail or pass vacuously on unmutated code and would mis-label mutants)

Ledger unmutated suite > 20 s, so that module was capped at 15 mutants.

## Summary

| item | count |
|---|---|
| generated (selected) | 45 |
| killed-before | 15 |
| survived-before | 30 |
| killed-after | 27 |
| equivalent | 3 |
| timeout | 0 |
| score before | 15/42 = 35.7% |
| score after | 42/42 = 100% |
| new killing tests | 27 |

Score = killed / (generated − equivalent). Candidate sites before sampling:
166 in `sni_eval_ledger.py`, 167 in `seal_full_check.py`. Seed `20261013`,
stratified by function. 0 TIMEOUT-UNSAFE (no `runs/` writes).

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut3a/harness.py`, not committed):

- comparison flip: `<`↔`>`, `<=`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.
Identity float mutants (`x * 1.001 == x`) were dropped at collection.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, `git status --porcelain -- research/` was checked (excluding the
mutated file), then original bytes were restored and sha256-checked.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `sni_eval_ledger.py` | 166 | 15 (cap; unmutated 28.42 s) | 10 | 5 | 4 | 1 | 0 | 10/14 | 14/14 |
| `seal_full_check.py` | 167 | 30 | 5 | 25 | 23 | 2 | 0 | 5/28 | 28/28 |
| **total** | **333** | **45** | **15** | **30** | **27** | **3** | **0** | **15/42** | **42/42** |

## Surviving-mutant list with killing test name

All 27 non-equivalent survivors were re-applied against the named new test
and failed (KILLED-after).

### sni_eval_ledger.py

| file:line | original → mutated | killing test |
|---|---|---|
| `sni_eval_ledger.py:799` | `not A or not B` → `and` (`assert_replay_equal`) | `test_mut3a_sni_eval_ledger_EvalLedger_assert_replay_equal_1` |
| `sni_eval_ledger.py:146` | delete unknown-code `ValueError` | `test_mut3a_sni_eval_ledger_LedgerRefused_init_1` |
| `sni_eval_ledger.py:163` | `to_dict` body → `return None` | `test_mut3a_sni_eval_ledger_LedgerRow_to_dict_1` |
| `sni_eval_ledger.py:188` | `sort_keys=True` → `False` (`_canonical`) | `test_mut3a_sni_eval_ledger__canonical_1` |

### seal_full_check.py

| file:line | original → mutated | killing test |
|---|---|---|
| `seal_full_check.py:109` | `ULP_REL_TOL` `1e-10` → `1.001e-10` | `test_mut3a_seal_full_check_module_1` |
| `seal_full_check.py:117` | `frozen=True` → `False` (`Diff`) | `test_mut3a_seal_full_check_Diff_1` |
| `seal_full_check.py:128` | `identical: int = 0` → `1` | `test_mut3a_seal_full_check_StudyResult_1` |
| `seal_full_check.py:129` | `named_exception_passes: int = 0` → `1` | `test_mut3a_seal_full_check_StudyResult_2` |
| `seal_full_check.py:363` | `Path / "SEAL_AND_BUDGET.json"` → `*` | `test_mut3a_seal_full_check_XREP04_S2_SEAL_V1_LEDGER_PATH_1` |
| `seal_full_check.py:375` | `got_lane != pin` → `==` | `test_mut3a_seal_full_check_XREP04_S2_SEAL_V1_LEDGER_PATH_2` |
| `seal_full_check.py:449` | `_porcelain` `text=True` → `False` | `test_mut3a_seal_full_check__porcelain_1` |
| `seal_full_check.py:451` | `return r.stdout` → `None` | `test_mut3a_seal_full_check__porcelain_2` |
| `seal_full_check.py:468` | `p / "research"` → `*` | `test_mut3a_seal_full_check__prepare_s1_imports_1` |
| `seal_full_check.py:394` | `_s1_ledger_exception` Diff list → `None` | `test_mut3a_seal_full_check__s1_ledger_exception_1` |
| `seal_full_check.py:415` | S2 ledger dumps `!=` → `==` | `test_mut3a_seal_full_check__s2_ledger_exception_1` |
| `seal_full_check.py:412` | `_s2_ledger_exception.rows` `return out` → `None` | `test_mut3a_seal_full_check__s2_ledger_exception_rows_1` |
| `seal_full_check.py:311` | `k in p_rest and values differ` → `or` | `test_mut3a_seal_full_check__xrep03_json_1` |
| `seal_full_check.py:343` | `_xrep03_md` `c_rest != p_rest` → `==` | `test_mut3a_seal_full_check__xrep03_md_1` |
| `seal_full_check.py:329` | `split(":", 1)` → `split(":", 2)` | `test_mut3a_seal_full_check__xrep03_md_split_1` |
| `seal_full_check.py:587` | `named_ok = 0` → `1` (`check_study`) | `test_mut3a_seal_full_check_check_study_1` |
| `seal_full_check.py:443` | `returncode == 0` → `== 1` | `test_mut3a_seal_full_check_input_ref_present_1` |
| `seal_full_check.py:682` | `main` failure `return 1` → `2` | `test_mut3a_seal_full_check_main_1` |
| `seal_full_check.py:491` | `mkdir(..., exist_ok=True)` → `False` | `test_mut3a_seal_full_check_regenerate_s1_1` |
| `seal_full_check.py:526` | `repo_root / "research"` → `*` | `test_mut3a_seal_full_check_regenerate_s2_1` |
| `seal_full_check.py:174` | `rel_files` missing-root `return out` → `None` | `test_mut3a_seal_full_check_rel_files_1` |
| `seal_full_check.py:424` | `s1_exceptions` dict → `None` | `test_mut3a_seal_full_check_s1_exceptions_1` |
| `seal_full_check.py:432` | `s2_exceptions` dict → `None` | `test_mut3a_seal_full_check_s2_exceptions_1` |

## Equivalent arguments

- `sni_eval_ledger.py:733` `EvalLedger._rebuild(validate=True)` default → `False`.
  Both call sites pass the flag explicitly (`__init__` False, `state` True).
  Changing the unused default cannot change behavior.
- `seal_full_check.py:165` `_walk_authority` `and` → `or` on
  `obj is not None and obj is not False and path`. That branch only
  `return`s; the function then ends. The mutated condition still neither
  raises nor returns a value.
- `seal_full_check.py:208` `return False, 0, 0.0` on `len(na) != len(nb)`.
  `_NUM.sub` already returns on skeleton mismatch, which is the same match
  set as `findall`, so equal skeletons imply equal token counts. The len
  return is unreachable.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `residual/s1_manifest.py`, `s1_prereg.py`,
`s1_report.py`, `run_s1.py`, `event_response/s2_seal.py`, `s2_splits.py`,
`run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md`. **None of those
lines are in `sni_eval_ledger.py` or `seal_full_check.py`.** No mutant
sites were excluded under the QF fence.

## What this does NOT prove

Mutation score is test strength against this operator set and this
15+30 sample, not statistical validity of SNI scores or seal bytes. A
killed mutant does not mean a Brier is well-calibrated or that a Linux
re-execution is byte-identical. No acceptance-matrix row moves to DONE.
The sweep does not claim completeness over unselected sites (166+167
candidates, 45 applied). Regeneration tests that need `runs/` and the
S1/S2 runners were not in the kill suite on this sparse worktree.
`seal_full_check.py --study all --strict-bytes` could not print OK here
(`ModuleNotFoundError: s1_data`; residual/ not checked out). Nothing here
feeds a ranker, gate, sizer, signal, escalation, or trade path.
