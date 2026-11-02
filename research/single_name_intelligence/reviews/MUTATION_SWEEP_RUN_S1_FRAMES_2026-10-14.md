# M6I mutation sweep — run_s1.py data-loading second pass — 2026-10-14

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing S1 importer suite against `residual/run_s1.py` from line 462
(`load_frames`) to EOF, using a fresh seed (`20261014`) after the MUT5C
pass (`20261013`). It does not move any acceptance row to DONE. Authority
flags stay false; identity ids remain caller-supplied opaque strings.
Fixtures in the killing tests are synthetic. `run_s1.py` consumes
owner-supplied pins, identity strings, and sealed run bytes; this lane does
not mint them.

Existing tests that import `run_s1` (grep of `tests/test_sni_*.py`):

`run_s1` importers (125 passed in 34.7 s unmutated; cap 15 mutants because
that is > 20 s):

- `tests/test_sni_s1_cli.py`
- `tests/test_sni_s1_seal_integrity.py`
- `tests/test_sni_s1_info_leak.py`
- `tests/test_sni_s1_ledger_order.py`
- `tests/test_sni_s1_report_order.py`
- `tests/test_sni_s1_v1_1_hardening.py`
- `tests/test_sni_s1_v1_2_hash_invariant.py`
- `tests/test_sni_quarantine_fence.py`
- `tests/test_sni_p03_ulp_stability.py`
- `tests/test_sni_mutation_run_s1_a.py`
- `tests/test_sni_mutation_run_s1_b.py`

## Summary

| item | count |
|---|---|
| generated (selected) | 15 |
| killed-before | 10 |
| survived-before | 5 |
| killed-after | 5 |
| equivalent | 0 |
| timeout | 0 |
| timeout-unsafe | 0 |
| score before | 10/15 = 66.7% |
| score after | 15/15 = 100% |
| new killing tests | 5 |

Candidate sites before sampling: 214 owned in `run_s1.py` (373 in the full
file; 143 outside the line-462 function range; 2 identity `0.0 * 1.001`;
14 extra `return_none` beyond one per function). Cap 15, seed `20261014`,
stratified by function. QF exact-line exclusions collected 0 sites
(points 15–17 in QF_QUARANTINE_FENCE_2026-10-13.md land on string-literal
containment tests and for-loop targets that have no operator sites).

`run_s1.py` importer set took 34.7 s (> 20 s), so this module was capped
at 15 mutants. MUT5C's killing tests (in `tests/test_sni_mutation_run_s1_b.py`)
were already in the importer set and ran against every M6I mutant. The five
M6I survivors are non-overlapping with the seven MUT5C survivors by
(file, line, operator) tuple:

| M6I survivor | MUT5C nearby |
|---|---|
| `run_s1.py:468 const_int 1 -> 2` (first d[-1] only) | `run_s1.py:468 d[-1] -> d[-2]` (second d[-1] in `max()`, killed by `test_mut5c_run_s1_load_frames_1`) |
| `run_s1.py:603 const_int 0 -> 1` (g[0] only) | `run_s1.py:603 g[3] -> g[4]` (different coefficient index, killed by `test_mut5c_run_s1_challenger_apply_1`) |
| `run_s1.py:1115 const_bool False -> True` | `run_s1.py:1113 arith_swap committed / rel -> committed * rel` (different line/operator) |
| `run_s1.py:742 cmp == -> !=` | not in MUT5C |
| `run_s1.py:569 return_none` | not in MUT5C |

Score = killed / generated. Every non-equivalent survivor was observable
through a new test.

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/m6i/harness.py`, NOT committed):

- comparison flip: `<`↔`>`, `<=`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261014)` round-robin over shuffled per-function site lists.
Identity mutants (`0.0 * 1.001 == 0.0`) were dropped before sampling.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, then original bytes were restored and sha256-checked before the next.
After every mutant, `git status --porcelain -- research/` was inspected;
no residual/event_response writes other than the module under mutation.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `run_s1.py` (from `load_frames`) | 214 | 15 | 10 | 5 | 5 | 0 | 0 | 10/15 | 15/15 |
| **total** | **214** | **15** | **10** | **5** | **5** | **0** | **0** | **10/15** | **15/15** |

`run_s1.py` importer set took 34.7 s (> 20 s), so this module is capped
at 15 mutants.

## Surviving-mutant list with killing test name

All 5 non-equivalent non-killed mutants were re-applied against the named
new test and failed (KILLED-after). Each `tests/test_sni_mut6_run_s1_frames.py`
test's docstring names the mutant (file:line, original -> mutated).

| file:line | original → mutated | killing test |
|---|---|---|
| `run_s1.py:1115` | `return False` → `return True` in `_byte_compare` | `test_m6i_run_s1__byte_compare_1` |
| `run_s1.py:742` | `r["split"] == "QUARANTINE"` → `!=` in `_comparison_block` | `test_m6i_run_s1__comparison_block_quarantine_count_1` |
| `run_s1.py:569` | `return ctx` → `return None` on non-estimable early-return | `test_m6i_run_s1_build_challenger_context_non_estimable_1` |
| `run_s1.py:603` | `g[0]` → `g[1]` in `challenger_apply` linear beta form | `test_m6i_run_s1_challenger_apply_beta_value_1` |
| `run_s1.py:468` | first `d[-1]` → `d[-2]` on the `last_bar is None` branch only | `test_m6i_run_s1_load_frames_first_series_1` |

### Sample re-verified kill (mutant + FAIL line)

```
$ python3 -c "...mutate 1 -> 2 on run_s1.py:468 first d[-1]"
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/test_sni_mutation_run_s1_b.py::test_mut5c_run_s1_load_frames_1 -v
>       assert last_bar == date(2020, 1, 6)
E       assert datetime.date(2020, 1, 3) == datetime.date(2020, 1, 6)
E        +  where datetime.date(2020, 1, 6) = date(2020, 1, 6)
FAILED tests/test_sni_mutation_run_s1_b.py::test_mut5c_run_s1_load_frames_1
============================== 1 failed in 0.60s ==============================
```

And for the new test on the first-iteration branch (the M6I survivor):

```
=== run_s1_13 ===
FAILED tests/test_sni_mut6_run_s1_frames.py::test_m6i_run_s1_load_frames_first_series_1
1 failed, 4 passed in 1.10s
```

For mutant 11 (`g[0]` → `g[1]`):

```
=== run_s1_11 ===
FAILED tests/test_sni_mut6_run_s1_frames.py::test_m6i_run_s1_challenger_apply_beta_value_1
1 failed, 3 passed in 1.11s
```

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill was
observable through a new test.

## Timeout / timeout-unsafe

None. Every mutant returned within `timeout 60` and `git status --porcelain
-- research/` after the run showed only the module under mutation (no
`event_response/` or other `research/` writes).

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
fence points inside this lane's owned `run_s1.py` range:

- `residual/run_s1.py:486` — `evaluate_p03` skip non-TRAIN/TUNE
- `residual/run_s1.py:643` — P03 calibration TRAIN/TUNE-only
- `residual/run_s1.py:650` — P03 comparison TRAIN/TUNE-only

Those exact lines had **zero** operator sites (string literals in a
containment test / for-loop targets, not `< <= > >= == !=`, arithmetic,
boolops, int/float/bool constants, `return`, or `if ...: raise`). No
mutant was drawn on them.

## What this does NOT prove

Mutation score is test strength against this operator set and this
15-sample, not statistical validity of SNI estimators or sealed receipts.
A killed mutant does not mean a CI is well-calibrated. No acceptance-matrix
row moves to DONE. The sweep does not claim completeness over unselected
sites (214 candidates, 15 applied) or over the first half of `run_s1.py`
(owned by the sibling MUT5A lane). The first-half `run_s1.py` mutation
sweep (MUT5A) covered its owned range with a separate seed; the M6I pass
specifically targets the data-loading half — `load_frames` and every
function defined after it — and is **not** additive to MUT5A's coverage.
Nothing here feeds a ranker, gate, sizer, signal, escalation, or trade
path.

## Seal check (pre-commit)

```
$ python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --strict-bytes
s1: files compared=48 identical=34 named-exception passes=3 ulp-equivalent=0 failures=11 [Linux x86_64]
  bytes-differ: LANE_MANIFEST.json
  bytes-differ: observations/P03_adr_baba_21.json
  bytes-differ: observations/P03_adr_baba_5.json
  bytes-differ: observations/P03_adr_baba_63.json
  bytes-differ: observations/P03_hkd_0700_21.json
  bytes-differ: observations/P03_hkd_0700_5.json
  bytes-differ: observations/P03_hkd_0700_63.json
  bytes-differ: observations/P03_hkd_9988_21.json
  bytes-differ: observations/P03_hkd_9988_5.json
  bytes-differ: observations/P03_hkd_9988_63.json
  bytes-differ: results/P03.json
s2: files compared=23 identical=22 named-exception passes=2 ulp-equivalent=0 failures=0 [Linux x86_64]
SEAL FULL CHECK: DIFFERS
```

The pre-existing S1 11-failure `bytes-differ` baseline is identical at the
base commit `831e5f638e9` (verified by `git stash` + re-run + `git stash
pop`); this sweep did not produce any new seal-byte diffs. `s2` failures=0.