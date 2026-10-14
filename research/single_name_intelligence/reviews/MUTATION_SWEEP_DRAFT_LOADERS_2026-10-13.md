# MUT4D mutation sweep — p04_v2_draft_loader / a8_draft_loader — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing import tests against the two draft-loader modules. It does
not move any acceptance row to DONE. Authority flags stay false; identity
ids remain caller-supplied opaque strings. Fixtures in the killing tests
are synthetic.

Existing tests that import these modules:

- `tests/test_sni_p04_v2_draft.py` — `p04_v2_draft_loader`
- `tests/test_sni_a8_us_transfer_draft.py` — `a8_draft_loader`

Kill suite used for scoring: those two files only. Unmutated baseline:
47 passed in 0.68 s (`test_sni_p04_v2_draft.py`); 38 passed in 0.61 s
(`test_sni_a8_us_transfer_draft.py`). Both under the 20 s slow-cap, so
each module was allowed 30 mutants (a8 had only 22 candidate sites).

## Summary

| item | count |
|---|---|
| generated (selected) | 52 |
| killed-before | 33 |
| survived-before | 19 |
| killed-after | 19 |
| equivalent | 0 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| score before | 33/52 = 63.5% |
| score after | 52/52 = 100% |
| new killing tests | 19 |

Candidate sites before sampling: 32 in `p04_v2_draft_loader.py`, 22 in
`a8_draft_loader.py`. Cap 30 per module, seed `20261013`, stratified by
function. p04 selected 30 of 32; a8 selected all 22.

`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --strict-bytes` → `SEAL FULL CHECK: OK`.
`git status --porcelain -- research/single_name_intelligence/runs/` was empty after every mutant.

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/mut4d/harness.py`, not committed):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
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

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `p04_v2_draft_loader.py` | 32 | 30 | 17 | 13 | 13 | 0 | 0 | 17/30 | 30/30 |
| `a8_draft_loader.py` | 22 | 22 | 16 | 6 | 6 | 0 | 0 | 16/22 | 22/22 |
| **total** | **54** | **52** | **33** | **19** | **19** | **0** | **0** | **33/52** | **52/52** |

## Surviving-mutant list with killing test name

All 19 non-killed mutants were re-applied against the named new test and
failed (KILLED-after).

### p04_v2_draft_loader.py

| file:line | original → mutated | killing test |
|---|---|---|
| `p04_v2_draft_loader.py:181` | `or` → `and` (`membership_table` rows fallback) | `test_mut4d_p04_v2_draft_loader__check_tune_empty_1` |
| `p04_v2_draft_loader.py:243` | `or` → `and` (`requires` must be a list) | `test_mut4d_p04_v2_draft_loader_validate_draft_1` |
| `p04_v2_draft_loader.py:164` | `or` → `and` (TUNE `membership_table` fallback) | `test_mut4d_p04_v2_draft_loader__check_tune_empty_2` |
| `p04_v2_draft_loader.py:73` | `or` → `and` (non-str `as_of_utc`) | `test_mut4d_p04_v2_draft_loader__require_iso_z_1` |
| `p04_v2_draft_loader.py:119` | `0` → `1` (`episodes == 0` abstention) | `test_mut4d_p04_v2_draft_loader_label_for_1` |
| `p04_v2_draft_loader.py:286` | `or` → `and` (TESTED token in ladder text) | `test_mut4d_p04_v2_draft_loader_validate_draft_2` |
| `p04_v2_draft_loader.py:115` | `or` → `and` (bool is not an int count) | `test_mut4d_p04_v2_draft_loader_label_for_2` |
| `p04_v2_draft_loader.py:121` | `2` → `3` (TESTED requires `clusters >= 2`) | `test_mut4d_p04_v2_draft_loader_label_for_3` |
| `p04_v2_draft_loader.py:263` | `or` → `and` (budget source must be str) | `test_mut4d_p04_v2_draft_loader_validate_draft_3` |
| `p04_v2_draft_loader.py:269` | `or` → `and` (`family_n` whitespace-only) | `test_mut4d_p04_v2_draft_loader_validate_draft_4` |
| `p04_v2_draft_loader.py:299` | `or` → `and` (`min_clusters` must be int) | `test_mut4d_p04_v2_draft_loader_validate_draft_5` |
| `p04_v2_draft_loader.py:276` | `or` → `and` (`labels` must be a list) | `test_mut4d_p04_v2_draft_loader_validate_draft_6` |
| `p04_v2_draft_loader.py:306` | `False` → `True` (`ensure_ascii` on identity scan) | `test_mut4d_p04_v2_draft_loader_validate_draft_7` |

### a8_draft_loader.py

| file:line | original → mutated | killing test |
|---|---|---|
| `a8_draft_loader.py:133` | `return True` → `return None` (bool True flag) | `test_mut4d_a8_draft_loader__authority_value_is_truthy_1` |
| `a8_draft_loader.py:127` | `return ""` → `return None` (non-str key) | `test_mut4d_a8_draft_loader__norm_key_1` |
| `a8_draft_loader.py:120` | delete `if code not in REFUSAL_CODES: raise` | `test_mut4d_a8_draft_loader__refuse_1` |
| `a8_draft_loader.py:133` | `True` → `False` (`return True` of bool True flag) | `test_mut4d_a8_draft_loader__authority_value_is_truthy_2` |
| `a8_draft_loader.py:203` | `or` → `and` (`names` must be a list) | `test_mut4d_a8_draft_loader_validate_draft_1` |
| `a8_draft_loader.py:213` | `or` → `and` (`then_known` must be a list) | `test_mut4d_a8_draft_loader_validate_draft_2` |

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill was
observable through a new test.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `residual/s1_manifest.py`, `s1_prereg.py`,
`s1_report.py`, `run_s1.py`, `event_response/s2_seal.py`, `s2_splits.py`,
`run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md`. **None of those
lines are in `p04_v2_draft_loader.py` or `a8_draft_loader.py`.** No mutant
sites were excluded under the QF fence.

## What this does NOT prove

Mutation score is test strength against this operator set and this
30-per-module sample, not statistical validity of SNI estimators or of
the draft JSON documents. A killed mutant does not mean a family is
estimable or that a REG §6 seal exists. No acceptance-matrix row moves
to DONE. The sweep does not claim completeness over unselected sites
(32+22 candidates, 52 applied; two p04 sites were left unsampled under
the cap). Nothing here feeds a ranker, gate, sizer, signal, escalation,
or trade path.
