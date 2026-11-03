# MUT1B mutation sweep — `s1_stats.py` / `s1_direction.py` — 2026-10-13

SNI-local DRAFT contract review. These modules consume caller-supplied
counts, bars, and opaque cluster keys; they do not mint issuer or security
ids (Stock Identity / Data OS). HISTORICAL-DESCRIPTIVE only:
`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. Fixtures in the
killing tests are synthetic. No production module was edited.

Harness (not committed): `~/lanes/scratch/mut1b/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next.

## Summary

| item | count |
|---|---|
| generated (selected sites) | 57 |
| killed-before (existing importer suite) | 46 |
| survived-before (non-equivalent) | 5 |
| killed-after (new `test_mut1b_*`) | 5 |
| equivalent | 6 |
| timeout | 0 |
| score before | 46 / 51 = 90.2% |
| score after | 51 / 51 = 100% |
| new killing tests | 5 |

Score = killed / (generated − equivalent). Wall-clock of the 57 runs:
125.9 s. 0 xfails.

## Operator set and seed

Seed: `20261013`. Max 30 mutants per module, stratified by function
(round-robin over `sorted(function names)`, sites shuffled per function
with the same RNG).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (bare `return` / `return None` skipped)
- `and`↔`or`
- deletion of one `if ...: raise` guard

No `if ...: raise` guards and no boolean literals exist in either module
(0 sites). Annotations and docstrings were not mutated. `**` is outside
the arithmetic set.

Kill suite (tests that import the module; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `s1_stats`: `tests/test_sni_s1_stats.py`, `tests/test_sni_s1_mirror.py`,
  `tests/test_sni_s1_property.py`, `tests/test_sni_s1_v1_1_hardening.py`,
  `tests/test_sni_common_equivalence.py`
- `s1_direction`: `tests/test_sni_s1_stats.py`

`tests/test_sni_quarantine_fence.py` mentions “stat” in a test name but
does not import either module; it was not part of the kill suite.

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `s1_stats.py` | 27 | 27 | 21 | 0 | 6 | 0 | 0 | 21/21 → 21/21 |
| `s1_direction.py` | 37 | 30 | 25 | 5 | 0 | 0 | 5 | 25/30 → 30/30 |
| total | 64 | 57 | 46 | 5 | 6 | 0 | 5 | 46/51 → 51/51 |

Selected-by-function (after stratification):

| module | function | sites | selected |
|---|---|---|---|
| s1_stats | `<module>` (`ALPHA`) | 1 | 1 |
| s1_stats | `binom_p_one_sided_greater` | 1 | 1 |
| s1_stats | `binom_sf_ge` | 12 | 12 |
| s1_stats | `mirror_mean_ci` | 4 | 4 |
| s1_stats | `sign_test_two_sided` | 9 | 9 |
| s1_direction | `_leg_close` | 5 | 5 |
| s1_direction | `direction_always_long` | 2 | 2 |
| s1_direction | `direction_trailing63` | 20 | 13 |
| s1_direction | `sign_of` | 10 | 10 |

Seven `direction_trailing63` sites sat outside the 30-cap sample and were
not run (L43 `0`/`>`; L44 `1`/`return 1`; L45 `0`; L47 `0`/`return 0`).
They are not in the score.

## Surviving-mutant list with killing test name

All five non-equivalent survivors are in `s1_direction.py`. Each was
re-applied after the new test was added and failed that test.

| id | file:line | function | original → mutated | killing test |
|---|---|---|---|---|
| s1_direction_02 | `s1_direction.py:22` | `direction_always_long` | `return 1` → `return None` | `test_mut1b_s1_direction_direction_always_long_1` |
| s1_direction_06 | `s1_direction.py:22` | `direction_always_long` | constant `1` → `2` | `test_mut1b_s1_direction_direction_always_long_2` |
| s1_direction_09 | `s1_direction.py:27` | `_leg_close` | BoolOp `or` → `and` | `test_mut1b_s1_direction__leg_close_1` |
| s1_direction_10 | `s1_direction.py:33` | `direction_trailing63` | default `n` `63` → `64` | `test_mut1b_s1_direction_direction_trailing63_1` |
| s1_direction_12 | `s1_direction.py:27` | `_leg_close` | constant `0` → `1` in `v == 0` | `test_mut1b_s1_direction__leg_close_2` |

Re-verify FAIL lines (two samples; all five killed):

- s1_direction_02 / `test_mut1b_s1_direction_direction_always_long_1`:
  `assert None == 1` (`direction_always_long` returned `None`)
- s1_direction_10 / `test_mut1b_s1_direction_direction_trailing63_1`:
  `assert 0 == 1` (default lookback 64 hit a missing endpoint and abstained)

The existing importer suite never called `direction_always_long`, never
passed a zero/NaN close through `_leg_close`, and always passed `n=63`
explicitly, so those five mutants were invisible to it.

## Equivalent arguments

| id | file:line | original → mutated | argument |
|---|---|---|---|
| s1_stats_01 | `s1_stats.py:20` | `ALPHA = 0.05` → `0.05005` | `ALPHA` is assigned and never read in this module. |
| s1_stats_03 | `s1_stats.py:25` | `k <= 0` → `k < 0` | For int `k`, `k==0` still returns 1.0 via the full `Bin(n, 0.5)` sum; negative `k` already returned 1.0. |
| s1_stats_13 | `s1_stats.py:68` | `if n == 0` → `if n == 1` | Well-formed calls with `n<2` already return `None` from `block_bootstrap_ci` (<2 cluster labels). |
| s1_stats_22 | `s1_stats.py:41` | `if n == 0` → `if n == 1` | `n=pos+neg`; both `n=0` (explicit 1.0) and `n=1` (two-sided doubling of the single-trial tail) yield p=1.0. |
| s1_stats_23 | `s1_stats.py:28` | `0.0` → `0.0 * 1.001` | IEEE `0.0 * 1.001` is still `0.0`; the mutated constant is identical. |
| s1_stats_26 | `s1_stats.py:29` | `range(k, n + 1)` → `n + 2` | `math.comb(n, n+1)` is 0 for `n>=0`, so the extra index adds a zero term. |

s1_stats_13/22/26 passed the existing suite; they are listed here as
equivalent rather than as survivors. No killing test can distinguish them
on the functions' contracts.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `s1_manifest.py`, `s2_seal.py`, `s2_splits.py`,
`s1_prereg.py`, `s1_report.py`, `run_s1.py`, `run_s2.py`, and
`protocols/S0_PROTOCOL_REGISTER.md`. None of those lines are in
`s1_stats.py` or `s1_direction.py`. Zero mutants were excluded on QF
grounds.

## What this does NOT prove

Mutation score is test strength against this operator set and this
sampled site list, not statistical validity of the binomial, sign-test,
Wilson, or trailing-excess estimators. Equivalent mutants are a
classification, not a proof of numeric correctness. Unselected
`direction_trailing63` sites are unscored. No acceptance-matrix row
moves to DONE. Nothing here feeds a ranker, gate, sizer, signal,
escalation, or trade path.
