# MUT5F mutation sweep — `s2_clocklaw.py` / `s2_outcomes.py` — 2026-10-13

SNI-local DRAFT contract review. These modules consume owner-supplied
session calendars, opaque identity strings, and caller-supplied price
frames (Stock Identity / Data OS; qledger calendars). They do not mint
issuer or security ids. HISTORICAL-DESCRIPTIVE only: `rank_authority`,
`gate_authority`, `size_authority`, `signal_authority`,
`escalation_authority` and `trade_authority` stay false. Fixtures in the
killing tests are synthetic. Residuals and event-study numbers are
descriptive, never causal, never a news-impact claim. No production
module was edited.

Harness (not committed): `~/lanes/scratch/mut5f/harness.py`. Seed
`random.Random(20261013)`. Each mutant applied in place, then original
bytes restored and sha256-checked before the next. After every run,
`git status --porcelain -- research/` was inspected; extras would have
been restored and classified TIMEOUT-UNSAFE (none occurred).

BASE `5b6fd2e8798886141e074d50a4468c063d44ad28`.

## Summary

| item | count |
|---|---|
| generated (selected sites) | 60 |
| killed-before (existing importer suite) | 48 |
| survived-before (non-equivalent) | 10 |
| killed-after (new `test_mut5f_*`) | 10 |
| equivalent | 2 |
| timeout | 0 |
| TIMEOUT-UNSAFE | 0 |
| score before | 48 / 58 = 82.8% |
| score after | 58 / 58 = 100% |
| new killing tests | 10 |

Score = killed / (generated − equivalent). Wall-clock of the 60 runs:
213.1 s. 0 xfails in the new file. Unmutated importer-test set was
3.02 s (clocklaw) and 5.91 s (outcomes), both under the 20 s cap, so
each module kept the 30-mutant budget.

## Operator set and seed

Seed: `20261013`. Max 30 mutants per module, stratified by function
(round-robin over `sorted(function names)`, sites shuffled per function
with the same RNG).

Operators (AST, one site per mutant):

- comparison flip: `<`↔`<=`, `>`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation: int `n`→`n+1`, float `x`→`x*1.001`, `True`↔`False`
- `return x` → `return None` (bare `return` / `return None` skipped; one
  return per function)
- `and`↔`or`
- deletion of one `if ...: raise` guard

Annotations and docstrings were not mutated.

Kill suite (tests that import the module; run with
`timeout 60 python3 -m pytest <tests> -x -q -p no:cacheprovider`):

- `s2_clocklaw`: `tests/test_sni_clocklaw_half_days.py`,
  `tests/test_sni_clocklaw_sessions.py`, `tests/test_sni_s2_clock.py`,
  `tests/test_sni_s2_collapse.py`, `tests/test_sni_s2_property.py`,
  `tests/test_sni_s2_v1_1_hardening.py`,
  `tests/test_sni_mutation_event_stress.py`
- `s2_outcomes`: `tests/test_sni_s2_v1_1_hardening.py`,
  `tests/test_sni_a07_then_known_exclusion.py`,
  `tests/test_sni_s2_info_leak.py`,
  `tests/test_sni_mutation_event_stress.py`,
  `tests/test_sni_s2_mirror.py`,
  `tests/test_sni_s2_nonfinite_abstain.py`,
  `tests/test_sni_missing_not_zero.py`

`tests/test_sni_three_clock_census.py` names `s2_clocklaw.py` in comments
and a path walk; it does not import the module and was not part of the
kill suite.

Nine `test_sni_s2_v1_1_hardening.py` nodeids that fail on this sparse
checkout for missing `runs/` / `protocols/` / `REPORT.md` were
`--deselect`ed so an unmutated tree would pass (same nodeids MUT2
dropped). Unmutated clocklaw suite: 122 passed, 4 xfailed, 9 deselected
in 3.02 s. Unmutated outcomes suite: 129 passed, 9 deselected in 5.91 s.

## Per-module table

| module | candidate sites | selected | killed-before | survived-before | equivalent | timeout | killed-after | score before → after |
|---|---|---|---|---|---|---|---|---|
| `s2_clocklaw.py` | 37 | 30 | 27 | 3 | 0 | 0 | 3 | 27/30 → 30/30 |
| `s2_outcomes.py` | 59 | 30 | 21 | 7 | 2 | 0 | 7 | 21/28 → 28/28 |
| total | 96 | 60 | 48 | 10 | 2 | 0 | 10 | 48/58 → 58/58 |

Selected-by-function (after stratification):

| module | function | sites | selected |
|---|---|---|---|
| s2_clocklaw | `<module>` | 18 | 11 |
| s2_clocklaw | `first_session_after` | 4 | 4 |
| s2_clocklaw | `first_session_after_disclosure_date` | 2 | 2 |
| s2_clocklaw | `session_dates` | 3 | 3 |
| s2_clocklaw | `session_part` | 9 | 9 |
| s2_clocklaw | `to_utc` | 1 | 1 |
| s2_outcomes | `<module>` | 2 | 2 |
| s2_outcomes | `OutcomeEngine.episode_excess` | 7 | 5 |
| s2_outcomes | `OutcomeEngine.info_leak_scan` | 13 | 5 |
| s2_outcomes | `OutcomeEngine.leg_return` | 5 | 5 |
| s2_outcomes | `OutcomeEngine.resolve_window` | 3 | 3 |
| s2_outcomes | `OutcomeEngine.trailing63_direction` | 24 | 5 |
| s2_outcomes | `_close_series` | 1 | 1 |
| s2_outcomes | `_usable_close` | 4 | 4 |

Seven `<module>` clock-law constants sat outside the 30-cap sample
(`_REGULAR_OPEN_LOCAL` US minute 30; HK midday end hour 13 and its
minute 0; US session-end minute 0; HK session-end hour 16;
`SESSION_SPAN_START` day 1; `SESSION_SPAN_END` month 12). Twenty-nine
`s2_outcomes` sites sat outside the 30-cap, mostly
`trailing63_direction` walk arithmetic and extra `info_leak_scan`
comparisons. They are not in the score.

## Surviving-mutant list with killing test name

Each non-equivalent survivor was re-applied after the new test was
added and failed that test.

| id | file:line | function | original → mutated | killing test |
|---|---|---|---|---|
| s2_clocklaw_08 | `s2_clocklaw.py:95` | `<module>` | `SESSION_SPAN_START` year `2019` → `2020` | `test_mut5f_s2_clocklaw_module_1` |
| s2_clocklaw_09 | `s2_clocklaw.py:95` | `<module>` | `SESSION_SPAN_START` month `1` → `2` | `test_mut5f_s2_clocklaw_module_2` |
| s2_clocklaw_16 | `s2_clocklaw.py:89` | `first_session_after_disclosure_date` | delete `if nxt is None: raise ClockLawFailure` | `test_mut5f_s2_clocklaw_first_session_after_disclosure_date_1` |
| s2_outcomes_03 | `s2_outcomes.py:91` | `episode_excess` | return ABSTAIN_RESOLVER_NONE dict → `None` | `test_mut5f_s2_outcomes_episode_excess_1` |
| s2_outcomes_07 | `s2_outcomes.py:108` | `episode_excess` | `round(subj - bench, 10)` → `11` | `test_mut5f_s2_outcomes_episode_excess_2` |
| s2_outcomes_12 | `s2_outcomes.py:162` | `info_leak_scan` | `round(float(steps.max()), 12)` → `13` | `test_mut5f_s2_outcomes_info_leak_scan_1` |
| s2_outcomes_21 | `s2_outcomes.py:132` | `trailing63_direction` | KeyError `return 0` → `return None` | `test_mut5f_s2_outcomes_trailing63_direction_1` |
| s2_outcomes_24 | `s2_outcomes.py:136` | `trailing63_direction` | first `1.0` → `1.001` in the excess formula | `test_mut5f_s2_outcomes_trailing63_direction_2` |
| s2_outcomes_25 | `s2_outcomes.py:137` | `trailing63_direction` | `excess > 0` → `>=` | `test_mut5f_s2_outcomes_trailing63_direction_3` |
| s2_outcomes_27 | `s2_outcomes.py:43` | `_usable_close` | except-path `return False` → `return True` | `test_mut5f_s2_outcomes__usable_close_1` |

Re-verify FAIL lines (two samples; all ten killed):

- s2_clocklaw_08 / `test_mut5f_s2_clocklaw_module_1`:
  `assert datetime.date(2020, 1, 1) == datetime.date(2019, 1, 1)`
- s2_outcomes_21 / `test_mut5f_s2_outcomes_trailing63_direction_1`:
  `assert None == 0`

The existing importer suite never pinned January 2019 in
`SESSION_SPAN_START`, never stubbed `next_session_strictly_after` for
the disclosure-date helper, never called `episode_excess` with a
resolver-None horizon, never distinguished `round(..., 10)` from
`round(..., 11)` on excess (or 12 vs 13 on `max_abs_step`), never
hit the trailing-63 KeyError path or a true-zero excess, and never
passed a non-numeric close through `_usable_close`.

## Equivalent arguments

| id | file:line | original → mutated | argument |
|---|---|---|---|
| s2_outcomes_10 | `s2_outcomes.py:157` | `steps > INFO_LEAK_STEP_TOLERANCE` → `>=` | `1e-6` is not a multiple of `ulp(1.0)=2**-52`, so `(q/q.shift(1)-1.0)` cannot equal the tolerance; `>` and `>=` classify every representable step identically. |
| s2_outcomes_28 | `s2_outcomes.py:43` | except-path `return False` → `return None` | Both callers use the result as a boolean (`if not (_usable_close(e0) and _usable_close(e1))` and `all(_usable_close(...))`); `None` is falsy like `False`. |

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
censuses 19 fence points. None of those file:line coordinates are in
`s2_clocklaw.py` or `s2_outcomes.py`. Excluded QF lines: none.

## What this does NOT prove

Mutation score is test strength against this operator set and this
stratified sample, not statistical validity of any S2 residual,
clock-law placement, or info-leak scan. No acceptance row moves to
DONE. Sites outside the 30-per-module cap were not run. Equivalence
arguments are one-line semantic claims, not a proof over every IEEE
pair. The kill suite deselected nine v1.1 hardening nodeids that need
committed `runs/` / `protocols/` blobs on this sparse checkout.
