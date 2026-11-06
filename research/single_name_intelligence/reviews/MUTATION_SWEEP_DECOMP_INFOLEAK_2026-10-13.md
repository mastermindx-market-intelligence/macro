# MUT1C mutation sweep — s1_decomposition / s1_infoleak — 2026-10-13

SNI-local DRAFT contract review. These modules consume caller-supplied
opaque identity strings (Stock Identity / Data OS); this lane never mints
issuer or security ids. HISTORICAL-DESCRIPTIVE only: rank_authority,
gate_authority, size_authority, signal_authority, escalation_authority and
trade_authority stay false. Fixtures in the accompanying tests are synthetic.
No production module was edited.

Existing tests that import the target modules:

- `tests/test_sni_s1_decomposition.py`
- `tests/test_sni_s1_property.py`
- `tests/test_sni_s1_info_leak.py`
- `tests/test_sni_s1_v1_1_hardening.py`

Harness (not committed): `~/lanes/scratch/mut1c/harness.py`. Each mutant was
applied in place, then the original bytes were restored and sha256-checked
before the next mutant. Final production sha256 matches the BASE blobs.

## Summary

| item | count |
|---|---|
| generated | 60 (30 + 30) |
| killed-before (existing suite) | 35 |
| survived-before (incl. later equivalent) | 25 |
| equivalent | 3 |
| timeout | 0 |
| non-equivalent survivors | 22 |
| killed-after (existing + new tests, re-verified) | 57 |
| remaining non-equivalent survivors | 0 |
| new killing tests | 22 |

Mutation score = killed / (generated − equivalent):

- **before:** 35 / 57 = **61.4%**
- **after:** 57 / 57 = **100%**

Existing importer suite on unmutated code: 54 passed
(`test_sni_s1_decomposition.py` 6, `test_sni_s1_property.py` 15,
`test_sni_s1_info_leak.py` 4, `test_sni_s1_v1_1_hardening.py` 29).
New file: 22 passed. 0 new failures.

## Operator set and seed

Operators (frozen):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/` (including `+=`↔`-=`)
- constant perturbation: `int n → n+1`, `float x → (x*1.001)`, `True`↔`False`
- one `return x` → `return None` per mutant
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

Seed: `random.Random(20261013)`. At most 30 mutants per module, stratified by
function (candidates sorted, shuffled per function, then round-robin).
Candidate pools: decomposition 68 sites → 30 selected; infoleak 32 sites → 30
selected. Tests run as
`timeout 60 python3 -m pytest <importer tests> -x -q -p no:cacheprovider`.
Decomposition importers were ordered unit → property → hardening; infoleak
importers property → info_leak, so `-x` failed fast.

## Per-module table

| module | generated | killed-before | survived-before | equivalent | killed-after | timeout | score before → after |
|---|---|---|---|---|---|---|---|
| `s1_decomposition.py` | 30 | 17 | 13 | 2 | 28 | 0 | 17/28 = 60.7% → 28/28 |
| `s1_infoleak.py` | 30 | 18 | 12 | 1 | 29 | 0 | 18/29 = 62.1% → 29/29 |
| **total** | **60** | **35** | **25** | **3** | **57** | **0** | **35/57 = 61.4% → 57/57** |

Selected-by-function (decomposition): `beta_window_dates` 5, `daily_log_returns` 5,
`decompose_unit` 5, `window_log_ret` 4, `factors_for` 3, `fit_ols` 3,
`spec_hash` 3, `<module>` 2.

Selected-by-function (infoleak): `vintage_series` 23, `detect` 6, `<module>` 1.

## Surviving-mutant list with killing test name

Every row below was SURVIVED against the existing importer suite, then
re-applied and failed the named new test (rc≠0). Docstrings on the tests
repeat `file:line, original -> mutated`.

| mutant | site | original → mutated | killing test |
|---|---|---|---|
| decomp_03 | `s1_decomposition.py:152` `decompose_unit` | `return row` → `return None` | `test_mut1c_s1_decomposition_decompose_unit_1` |
| decomp_05 | `s1_decomposition.py:115` `fit_ols` | `np.ones((len(y), 1))` 1 → 2 | `test_mut1c_s1_decomposition_fit_ols_1` |
| decomp_06 | `s1_decomposition.py:64` `spec_hash` | `ensure_ascii=False` → `True` | `test_mut1c_s1_decomposition_spec_hash_1` |
| decomp_08 | `s1_decomposition.py:25` `<module>` | `MIN_OBS = 200` → `201` | `test_mut1c_s1_decomposition_module_1` |
| decomp_09 | `s1_decomposition.py:106` `beta_window_dates` | `range(len(...) - 1)` 1 → 2 | `test_mut1c_s1_decomposition_beta_window_dates_1` |
| decomp_10 | `s1_decomposition.py:80` `daily_log_returns` | `c <= 0` 0 → 1 | `test_mut1c_s1_decomposition_daily_log_returns_1` |
| decomp_13 | `s1_decomposition.py:117` `fit_ols` | `y - design @ coef` → `+` | `test_mut1c_s1_decomposition_fit_ols_2` |
| decomp_18 | `s1_decomposition.py:135` `decompose_unit` | `subject_endpoint_fill__oc` False → True | `test_mut1c_s1_decomposition_decompose_unit_2` |
| decomp_21 | `s1_decomposition.py:64` `spec_hash` | `sort_keys=True` → `False` | `test_mut1c_s1_decomposition_spec_hash_2` |
| decomp_22 | `s1_decomposition.py:95` `window_log_ret` | `b <= 0` 0 → 1 | `test_mut1c_s1_decomposition_window_log_ret_1` |
| decomp_26 | `s1_decomposition.py:95` `window_log_ret` | `a <= 0` 0 → 1 | `test_mut1c_s1_decomposition_window_log_ret_2` |
| infoleak_00 | `s1_infoleak.py:23` `<module>` | `STEP_TOLERANCE = 1e-6` → `(1e-6*1.001)` | `test_mut1c_s1_infoleak_module_1` |
| infoleak_04 | `s1_infoleak.py:41` `vintage_series` | `range(1, len(q))` 1 → 2 | `test_mut1c_s1_infoleak_vintage_series_1` |
| infoleak_05 | `s1_infoleak.py:52` `detect` | `d <= last_bar` → `<` | `test_mut1c_s1_infoleak_detect_1` |
| infoleak_07 | `s1_infoleak.py:52` `detect` | `earliest_tune_anchor <= d` → `<` | `test_mut1c_s1_infoleak_detect_2` |
| infoleak_12 | `s1_infoleak.py:38` `vintage_series` | `len(q) < 2` 2 → 3 | `test_mut1c_s1_infoleak_vintage_series_2` |
| infoleak_13 | `s1_infoleak.py:40` `vintage_series` | `q[i]/q[i-1] - 1.0` → `+ 1.0` | `test_mut1c_s1_infoleak_vintage_series_3` |
| infoleak_14 | `s1_infoleak.py:40` `vintage_series` | stored `1.0` → `(1.0*1.001)` | `test_mut1c_s1_infoleak_vintage_series_4` |
| infoleak_18 | `s1_infoleak.py:38` `vintage_series` | `len(q) < 2` → `<= 2` | `test_mut1c_s1_infoleak_vintage_series_5` |
| infoleak_23 | `s1_infoleak.py:34` `vintage_series` | `cp != cp or c != c` → `and` | `test_mut1c_s1_infoleak_vintage_series_6` |
| infoleak_24 | `s1_infoleak.py:34` `vintage_series` | `cp <= 0` 0 → 1 | `test_mut1c_s1_infoleak_vintage_series_7` |
| infoleak_29 | `s1_infoleak.py:40` `vintage_series` | stored `q[i] / q[i-1]` → `*` | `test_mut1c_s1_infoleak_vintage_series_8` |

Re-verify samples (mutant re-applied; named test FAILED):

- decomp_05 `1` → `2` empty-X ones-column: `assert (2,) == (1,)`
- infoleak_05 `d <= last_bar` → `<`: `assert None is not None`

## Equivalent arguments

| mutant | site | original → mutated | argument |
|---|---|---|---|
| decomp_02 | `s1_decomposition.py:85` | `p > 0` → `p >= 0` | `prev_d` is stored only after a strictly positive close, so `p` is never 0. |
| decomp_17 | `s1_decomposition.py:85` | `p is not None and p > 0` → `or` | `prev_d` is only a previously accepted positive close, so `p` is never None and never non-positive. |
| infoleak_16 | `s1_infoleak.py:42` | `> STEP_TOLERANCE` → `>=` | In float64, `abs(q[i]/q[i-1]-1.0)` cannot equal `1e-6`, so `>` and `>=` agree on every finite ratio. |

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points. None of those lines live in `s1_decomposition.py` or
`s1_infoleak.py`. The review explicitly says `s1_decomposition.py:44
QUARANTINE = "QUARANTINE"` is a label token, not a fence point. The operator
set does not mutate that string. **Excluded QF lines in this sweep: none.**

QF census files (out of scope for this lane): `s1_manifest.py`, `s2_seal.py`,
`s2_splits.py`, `s1_prereg.py`, `s1_report.py`, `run_s1.py`, `run_s2.py`,
`S0_PROTOCOL_REGISTER.md`.

## What this does NOT prove

Mutation score is test strength against this operator set and this 60-mutant
sample, not statistical validity of P03 residuals or the A23 INFO-LEAK
predicate. Surviving-then-killed mutants were holes in the existing suite
(empty beta-window early return, `fit_ols` empty-X rank, canonical JSON flags,
`MIN_OBS` exact 200, last adjacent date-order pair, sub-unit positive closes,
inclusive detect window, two-bar vintage series, stored step magnitude). They
are not evidence that the registered statistics are correctly specified.

No acceptance row moves to DONE. No production code changed. The harness is
scratch-only and must not be treated as a CI mutation engine.
