# MUT3C mutation sweep — `s1_prereg.py` / `s1_challenger.py` — 2026-10-13

SNI-local DRAFT contract review. These modules consume caller-supplied
opaque identity strings (Stock Identity / Data OS) and sealed pins; they
do not mint issuer or security ids. HISTORICAL-DESCRIPTIVE only:
`rank_authority`, `gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. Fixtures in the
killing tests are synthetic. No production module was edited.

Harness (not committed): `~/lanes/scratch/mut3c/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next. After every mutant,
`git status --porcelain -- research/single_name_intelligence/runs/` was
empty (0 TIMEOUT-UNSAFE).

Existing tests that import these modules:

- `tests/test_sni_s1_challenger.py` — `s1_challenger`
- `tests/test_sni_s1_v1_1_hardening.py` — `s1_prereg`
- `tests/test_sni_quarantine_fence.py` — `s1_prereg`
- `tests/test_sni_common_equivalence.py` — `s1_prereg`
- `tests/test_sni_s1_cli.py` — `s1_prereg`
- `tests/test_sni_p03_ulp_stability.py` — `s1_prereg`
- `tests/test_sni_s1_seal_integrity.py` — `s1_prereg`
- `tests/test_sni_run_seal_repro.py` — `s1_prereg` (`canonical_json`)

## Summary

| item | count |
|---|---|
| generated (selected sites) | 45 |
| killed-before (existing importer suite) | 32 |
| survived-before (non-equivalent) | 13 |
| killed-after (new `test_mut3c_*`) | 13 |
| equivalent | 0 |
| timeout | 0 |
| score before | 32 / 45 = 71.1% |
| score after | 45 / 45 = 100% |
| new killing tests | 13 |

Score = killed / (generated − equivalent). `s1_prereg` unmutated importer
suite was 65.6 s on a cold run (995 passed; 22.6 s warm), so that module
was capped at 15 mutants. `s1_challenger` unmutated suite was 3.3 s
(6 passed), cap 30. 0 xfails. 0 TIMEOUT-UNSAFE.

`SEAL FULL CHECK: OK` (`seal_full_check.py --study all --strict-bytes`).

## Operator set and seed

Seed: `20261013`. Max 30 mutants per module (15 when unmutated suite
> 20 s), stratified by function (round-robin over `sorted(function
names)`, sites shuffled per function with the same RNG).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (one non-`None` return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

Annotations and docstrings were not mutated. Identity float sites
(`0.0 * 1.001 == 0.0`) were dropped before sampling. String constants
are outside the operator set.

Kill suite (`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `s1_prereg`: the seven importer files above, fast files first. The 15
  selected mutants were all killed in ~2.1 s by hardening / digest /
  authority tests, so `test_sni_run_seal_repro.py` (915 tests) was never
  the first fail and would not change any classification.
- `s1_challenger`: `tests/test_sni_s1_challenger.py`

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `s1_prereg.py` | 65 | 15 | 15 | 0 | 0 | 0 | 0 | 15/15 → 15/15 |
| `s1_challenger.py` | 96 | 30 | 17 | 13 | 0 | 0 | 13 | 17/30 → 30/30 |
| total | 161 | 45 | 32 | 13 | 0 | 0 | 13 | 32/45 → 45/45 |

Selected-by-function (after stratification):

| module | function | sites | selected |
|---|---|---|---|
| s1_prereg | `<module>` | 33 | 3 |
| s1_prereg | `_authority_name` | 1 | 1 |
| s1_prereg | `_forbidden_truthy_authority` | 3 | 3 |
| s1_prereg | `assert_authority_false` | 7 | 2 |
| s1_prereg | `build_spec` | 16 | 2 |
| s1_prereg | `canonical_json` | 3 | 2 |
| s1_prereg | `prereg_digest` | 2 | 2 |
| s1_challenger | `<module>` | 13 | 5 |
| s1_challenger | `build_universe` | 29 | 5 |
| s1_challenger | `characteristics_at` | 27 | 5 |
| s1_challenger | `estimability` | 8 | 4 |
| s1_challenger | `fit_gamma` | 1 | 1 |
| s1_challenger | `gamma_design` | 4 | 4 |
| s1_challenger | `month_key` | 1 | 1 |
| s1_challenger | `path_sort_key` | 1 | 1 |
| s1_challenger | `rank_standardise` | 12 | 4 |

## Surviving-mutant list with killing test name

All 13 non-killed mutants were re-applied against the named new test and
failed (KILLED-after). `s1_prereg.py` had no survivors in this sample.

### s1_challenger.py

| file:line | original → mutated | killing test |
|---|---|---|
| `s1_challenger.py:27` | `date(2012, 1, 3)` month `1` → `2` | `test_mut3c_s1_challenger_module_1` |
| `s1_challenger.py:137` | `vol != vol or mom != mom` → `and` | `test_mut3c_s1_challenger_characteristics_at_1` |
| `s1_challenger.py:180` | `n_char == 3` → `!=` | `test_mut3c_s1_challenger_estimability_1` |
| `s1_challenger.py:169` | `return f"{d.year:04d}-{d.month:02d}"` → `return None` | `test_mut3c_s1_challenger_month_key_1` |
| `s1_challenger.py:52` | `no_adjusted_close_column` init `0` → `1` | `test_mut3c_s1_challenger_build_universe_1` |
| `s1_challenger.py:27` | `date(2012, 1, 3)` day `3` → `4` | `test_mut3c_s1_challenger_module_2` |
| `s1_challenger.py:80` | coverage `intersection / n_sessions` → `*` | `test_mut3c_s1_challenger_build_universe_2` |
| `s1_challenger.py:130` | `p1 <= 0` → `p1 <= 1` | `test_mut3c_s1_challenger_characteristics_at_2` |
| `s1_challenger.py:181` | `n_months >= MIN_TRAIN_MONTHS` → `>` | `test_mut3c_s1_challenger_estimability_2` |
| `s1_challenger.py:77` | `dates[-1] < MIN_LAST_DATE` → `<=` | `test_mut3c_s1_challenger_build_universe_3` |
| `s1_challenger.py:180` | `n_char == 3` literal `3` → `4` | `test_mut3c_s1_challenger_estimability_3` |
| `s1_challenger.py:28` | `date(2026, 9, 30)` month `9` → `10` | `test_mut3c_s1_challenger_module_3` |
| `s1_challenger.py:61` | `examined += 1` → `+= 2` | `test_mut3c_s1_challenger_build_universe_4` |

Re-verified FAIL lines (two samples):

- `test_mut3c_s1_challenger_module_1`: `assert datetime.date(2012, 2, 3) == datetime.date(2012, 1, 3)`
- `test_mut3c_s1_challenger_month_key_1`: `assert None == '2024-03'`

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill was
observable through a new test.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
census points 7 and 8 are in this lane's target:

- `residual/s1_prereg.py:188` — `build_spec()["splits"]` tune/quarantine strings
- `residual/s1_prereg.py:192` — `build_spec()["splits"]["purge"]["tune"]`

Both lines are string literals. The operator set does not mutate strings,
and the collector also skipped those exact line numbers. **Zero selected
mutants sat on QF fence lines.** `s1_challenger.py` has no QF fence points.

## What this does NOT prove

Mutation score is test strength against this operator set and this
15/30-per-module sample, not statistical validity of SNI estimators or
of the IPCA-family challenger. A killed mutant does not mean Gamma is
well identified or that a CI is well-calibrated. No acceptance-matrix
row moves to DONE. The sweep does not claim completeness over unselected
sites (65+96 candidates, 45 applied). Nothing here feeds a ranker, gate,
sizer, signal, escalation, or trade path.
