# JGMUT mutation sweep — sni_join_guard — 2026-10-13

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing import tests against `common/sni_join_guard.py` (A09
mismatched-join refusal). It does not move any acceptance row to DONE.
Authority flags stay false; identity ids remain caller-supplied opaque
strings. Fixtures in the killing tests are synthetic.

Existing tests that import this module:

- `tests/test_sni_join_guard.py` — `sni_join_guard`

Kill suite used for scoring: that file only. Unmutated baseline:
42 passed in 0.60 s. Under the 20 s slow-cap, so the module was allowed
30 mutants (107 candidate sites).

## Summary

| item | count |
|---|---|
| generated (selected) | 30 |
| killed-before | 20 |
| survived-before | 10 |
| killed-after | 10 |
| equivalent | 0 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| score before | 20/30 = 66.7% |
| score after | 30/30 = 100% |
| new killing tests | 10 |

Candidate sites before sampling: 107 in `sni_join_guard.py`. Cap 30 per
module, seed `20261013`, stratified by function. All 14 functions (plus
`<module>`) contributed at least one selected site.

`python3 research/single_name_intelligence/evaluation/seal_full_check.py --study all --strict-bytes` → `SEAL FULL CHECK: OK`.
`git status --porcelain -- research/` after every mutant showed only the
mutated module; original bytes were restored and sha256-checked before
the next mutant. Committed diff contains zero bytes under `residual/`
and `event_response/`.

## Operator set and seed

Harness (scratch only, `~/lanes/scratch/jgmut/harness.py`, not committed):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: `int n → n+1`, `float x → x*1.001`, `True`↔`False`
- `return x` → `return None` (one site per return)
- `and`↔`or`
- deletion of one `if ...: raise` guard (`pass`)

`random.Random(20261013)` round-robin over shuffled per-function site lists.
Identity mutants (`0.0 * 1.001 == 0.0`) were dropped before sampling;
none appeared in this module.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest tests/test_sni_join_guard.py -x -q -p no:cacheprovider`
ran, then original bytes were restored and sha256-checked before the next.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `sni_join_guard.py` | 107 | 30 | 20 | 10 | 10 | 0 | 0 | 20/30 | 30/30 |
| **total** | **107** | **30** | **20** | **10** | **10** | **0** | **0** | **20/30** | **30/30** |

Selected by function: `<module>` 3, `__post_init__` 3, `_add_eq_mismatch` 2,
`_add_segment_rules` 3, `_add_version_rule` 3, `_as_date` 2, `_as_datetime` 2,
`_blank` 2, `_freeze_reasons` 1, `_known_at_later_than_as_of` 2, `_present` 1,
`check_join` 2, `refuse_nonfalse_authority` 2, `validate_fact` 2.

## Surviving-mutant list with killing test name

All 10 non-killed mutants were re-applied against the named new test and
failed (KILLED-after).

| file:line | original → mutated | killing test |
|---|---|---|
| `sni_join_guard.py:166` | delete `if self.authority.get(key) is not False: raise` | `test_jgmut_sni_join_guard___post_init___1` |
| `sni_join_guard.py:210` | `text == ""` → `text != ""` | `test_jgmut_sni_join_guard__as_datetime_1` |
| `sni_join_guard.py:436` | `and` → `or` (ADS ads_ratio mismatch requires both ADS) | `test_jgmut_sni_join_guard_check_join_1` |
| `sni_join_guard.py:144` | delete `if not isinstance(flags, Mapping): raise` | `test_jgmut_sni_join_guard_refuse_nonfalse_authority_1` |
| `sni_join_guard.py:176` | delete `if not self.reasons: raise` (REFUSED) | `test_jgmut_sni_join_guard___post_init___2` |
| `sni_join_guard.py:359` | `or` → `and` (skip version rule if either version blank) | `test_jgmut_sni_join_guard__add_version_rule_1` |
| `sni_join_guard.py:212` | `len(text) == 10` → `len(text) != 10` | `test_jgmut_sni_join_guard__as_datetime_2` |
| `sni_join_guard.py:238` | `return False` → `return True` (unparseable as_of) | `test_jgmut_sni_join_guard__known_at_later_than_as_of_1` |
| `sni_join_guard.py:154` | `frozen=True` → `False` (`JoinVerdict`) | `test_jgmut_sni_join_guard_module_1` |
| `sni_join_guard.py:343` | `and` → `or` (scheme mismatch needs both schemes) | `test_jgmut_sni_join_guard__add_segment_rules_1` |

## Equivalent arguments

None. Every selected mutant that the existing suite did not kill was
observable through a new test. The `__post_init__` authority-key loop is
a second check after `refuse_nonfalse_authority`; deleting it is live
when a mapping omits a required flag. The `_as_datetime` empty-string
and length-10 branches are live on ISO timestamps. The ADS `and` and
segment-scheme `and` are live on one-sided facts. Unparseable `as_of`
must stay "not later". `JoinVerdict` must stay frozen.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points in `residual/s1_manifest.py`, `s1_prereg.py`,
`s1_report.py`, `run_s1.py`, `event_response/s2_seal.py`, `s2_splits.py`,
`run_s2.py`, and `protocols/S0_PROTOCOL_REGISTER.md`. **None of those
lines are in `sni_join_guard.py`.** No mutant sites were excluded under
the QF fence.

## What this does NOT prove

Mutation score is test strength against this operator set and this
30-site sample, not statistical validity of SNI estimators and not
completeness of A09 join refusal. A killed mutant does not mean every
mismatched join in production is refused. No acceptance-matrix row
moves to DONE. The sweep does not claim completeness over unselected
sites (107 candidates, 30 applied). Nothing here feeds a ranker, gate,
sizer, signal, escalation, or trade path.
