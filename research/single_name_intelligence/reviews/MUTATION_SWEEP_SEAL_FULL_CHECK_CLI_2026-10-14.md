# MUTATION SWEEP — seal_full_check CLI (SEAL-TOOLING) — 2026-10-14

Lane M6D (SNI commission 8659). Target module:
`research/single_name_intelligence/evaluation/seal_full_check.py`, owned site
range ONLY the functions `main`, `_print_result`, `_walk_authority`,
`_load_s1_build_seal`. No production code was changed; the only committed
artifacts are this review and
`tests/test_sni_mut6_seal_full_check_cli.py`.

This module is an SNI-local DRAFT contract that CONSUMES owner-supplied
values; nothing here feeds a ranker, gate, sizer, signal, escalation, or
trade path, and every authority flag stays false everywhere it is written.

## Summary

| generated | killed-before | survived-before | killed-after | equivalent | timeout | TIMEOUT-UNSAFE |
|---|---|---|---|---|---|---|
| 30 | 10 | 20 | 18 | 2 | 0 | 0 |

- Score before: 10/30 = 33.3% raw; 10/28 = 35.7% excluding equivalents.
- Score after: 28/28 = 100% non-equivalent (30/30 with equivalents counted
  as not-killable).
- Every killed-after claim was re-verified by re-applying that single mutant
  and watching `tests/test_sni_mut6_seal_full_check_cli.py` fail (rc=1),
  then restoring the original bytes and verifying sha256.

## Operator set and seed

Frozen M6D operator set, applied via a scratch AST harness
(`~/lanes/scratch/m6d/`, not committed): comparison flip (`< <= > >= == !=`
bidirectional); arithmetic swap (`+ -`, `* /`); constant perturbation (int
n -> n+1, float x -> x*1.001, True <-> False); `return x` -> `return None`
on one return per function; `and` <-> `or`; deletion of one `if ...: raise`
guard (guard body replaced by `pass` where the guard is an only-child).
Deterministic selection with `random.Random(20261014)`, stratified
round-robin by function. 36 candidate sites existed (main 22,
`_walk_authority` 5, `_load_s1_build_seal` 9, `_print_result` 0 — it is
pure f-string printing with no mutable operators); the one-return-per-function
rule reduced the draw to 30 (<= 40 budget; module cap not triggered).
Each mutant ran against ONLY the tests that import the module under
`timeout 60`; original bytes restored and sha256-verified between mutants;
`git status --porcelain -- research/` checked after every mutant run (no
mutant wrote anything).

## Per-module table

| module / function | candidates | mutants run | killed-before | survived | killed-after | equivalent |
|---|---|---|---|---|---|---|
| `seal_full_check.py::main` | 22 | 19 | 4 | 15 | 15 | 0 |
| `seal_full_check.py::_print_result` | 0 | 0 | 0 | 0 | 0 | 0 |
| `seal_full_check.py::_walk_authority` | 5 | 5 | 2 | 3 | 1 | 2 |
| `seal_full_check.py::_load_s1_build_seal` | 9 | 6 | 4 | 2 | 2 | 0 |
| total | 36 | 30 | 10 | 20 | 18 | 2 |

Importer test set (all `tests/test_sni_*.py` importing the module):
`tests/test_sni_seal_full_check.py`, `tests/test_sni_injection_safety.py`,
`tests/test_sni_injection_safety_ext.py`,
`tests/test_sni_mutation_ledger_seal.py` — 247 selected, 246 passed /
1 skipped / 1 deselected in 5.06 s on unmutated code (budget 20 s not
triggered).

## Surviving-mutant list with killing test name

All in `tests/test_sni_mut6_seal_full_check_cli.py`; each test docstring
pins the exact mutant (file:line, original -> mutated).

| mutant # | site (file:line, original -> mutated) | killing test |
|---|---|---|
| 1 | seal_full_check.py:681 `proc.returncode != 0` -> `!= 1` | `test_m6d_seal_full_check_main_3` |
| 4 | seal_full_check.py:693 `failed = False` -> `True` | `test_m6d_seal_full_check_main_6` |
| 7 | seal_full_check.py:688 `return 2` -> `return None` | `test_m6d_seal_full_check_main_5` |
| 8 | seal_full_check.py:154 `or` -> `and` (authority-key match) | `test_m6d_seal_full_check__walk_authority_1` |
| 9 | seal_full_check.py:499 `or` -> `and` (spec guard) | `test_m6d_seal_full_check__load_s1_build_seal_1` |
| 10 | seal_full_check.py:718 `results[0]` -> `results[1]` | `test_m6d_seal_full_check_main_7` |
| 16 | seal_full_check.py:679 `capture_output=True` -> `False` | `test_m6d_seal_full_check_main_2` |
| 18 | seal_full_check.py:688 `return 2` -> `return 3` | `test_m6d_seal_full_check_main_5` |
| 19 | seal_full_check.py:496 `and` -> `or` (cached-module check) | `test_m6d_seal_full_check__load_s1_build_seal_2` |
| 20 | seal_full_check.py:726 `return 0` -> `return 1` | `test_m6d_seal_full_check_main_6` |
| 23 | seal_full_check.py:679 `text=True` -> `False` | `test_m6d_seal_full_check_main_2` |
| 24 | seal_full_check.py:681 `!=` -> `==` | `test_m6d_seal_full_check_main_3` |
| 25 | seal_full_check.py:665 `required=True` -> `False` | `test_m6d_seal_full_check_main_1` |
| 26 | seal_full_check.py:690 `args.study == "all"` -> `!=` | `test_m6d_seal_full_check_main_6` |
| 27 | seal_full_check.py:724 `return 0` -> `return 1` | `test_m6d_seal_full_check_main_7` |
| 28 | seal_full_check.py:711 `return 1` -> `return 2` (porcelain drift) | `test_m6d_seal_full_check_main_8` |
| 29 | seal_full_check.py:683 `return 2` -> `return 3` | `test_m6d_seal_full_check_main_4` |
| 30 | seal_full_check.py:707 `after != before` -> `==` | `test_m6d_seal_full_check_main_8` |

Killed-before (no new test needed): #3 delguard L499, #6/#12/#21 `/*`
arithmetic L493, #11 delguard L155, #13 int L715, #14 bool L155, #15
retnone L497, #17 cmp L496, #22 bool L704.

## Equivalent arguments

- #2 `_walk_authority` L165 `and` -> `or` in
  `elif obj is not None and obj is not False and path:` — the branch body
  is a bare `return` and the function ends immediately after the elif, so
  taking or skipping the branch both leave the function returning None.
- #5 `_walk_authority` L165 `False` -> `True` (inside `obj is not False`)
  — same dead branch: `_walk_authority` recurses only into dict/list
  values, so a scalar obj always arrives from the top-level call with
  `path=""`, making `... and path` false under either constant; even when
  taken, the body is the same bare `return`. Empirically both mutants still
  survive the new test file.

## Excluded QF lines

`reviews/QF_QUARANTINE_FENCE_2026-10-13.md` contains no fence lines inside
this module (no mention of `seal_full_check` or its CLI); nothing was
excluded on QF grounds.

## Environment note (pre-existing, not caused by this lane)

On this host `tests/test_sni_seal_full_check.py::test_schk_05_full_regeneration_s1`
fails on UNMUTATED code: the regenerated `LANE_MANIFEST.json` records
`seal_commit_sha = db946217...` while the committed seal records
`5ebab11d...` — `seal_commit_sha` is `git log -n1 -- <SEAL_AND_BUDGET.json>`
and history resolves differently in this clone. The byte-compare of the
other 47 S1 files and the whole S2 study are unaffected. That one
environment-dependent test was `--deselect`ed for every mutant run (both
unmutated baseline and mutants, identically) so KILLED/SURVIVED stay
meaningful; it is reported, not hidden.

## What this does NOT prove

- A mutation score measures TEST STRENGTH, not statistical validity of the
  studies the seal checks; nothing here validates any residual or
  event-response number.
- No acceptance row moves to DONE because of this sweep.
- Only the four owned functions were swept; the comparator internals
  (`walk_compare`, ULP classification, XREP exceptions) belong to other
  lanes' site ranges.
- 36 candidate sites existed and 30 were drawn under the frozen budget; a
  different seed could surface different survivors.
- The two equivalent mutants are equivalent by the arguments above, not by
  proof of unreachable inputs beyond the reachability argument given.
