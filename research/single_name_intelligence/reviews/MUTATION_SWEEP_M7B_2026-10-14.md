# MUTATION SWEEP M7B — SNI DRAFT guards `sni_then_known_guard` / `sni_session_state_guard` (2026-10-14)

Bounded mutation sweep, lane M7B, program Single-Name Intelligence
(commission 8659). Method frozen by the mission brief; harness lives in
`~/lanes/scratch/m7b/` (not committed). No production code was changed:
both target modules are byte-identical to base commit `97e9d6e7c3d` (sha256
re-verified after every mutant and again before commit).

## Summary

| metric | count |
|---|---|
| mutants generated | 60 (30 per module) |
| killed before | 50 |
| survived before | 10 |
| killed after (new tests, each re-verified) | 4 |
| equivalent (semantic argument below) | 6 |
| timeout | 0 |
| **score before** | **50 / (60 − 6) = 92.6%** |
| **score after** | **54 / 54 = 100%** |

Only 4 non-equivalent survivors existed, so only 4 killing tests were
possible; a fifth test (`test_m7b_session_state__calendar_date_028`) is
committed as boundary coverage but kills nothing (its mutant is
equivalent — see arguments). Importer-test sets (grep over `tests/`):
each module is imported only by its own suite —
`tests/test_sni_then_known_guard.py` (52 tests) and
`tests/test_sni_session_state_guard.py` (34 tests); no other
`tests/test_sni_*.py` imports either module. Unmutated baseline: 86
passed in 1.17 s — under the 20 s cap, so no module was capped at 15.

## Operator set and seed

Frozen operator set: comparison flip (`<`/`<=`, `>`/`>=`, `==`/`!=`),
arithmetic swap (`+`/`-`, `*`/`/`), constant perturbation (int `n`→`n+1`,
float `x`→`x*1.001`, `True`↔`False`), `return x`→`return None` (one valued
return per function), `and`↔`or`, deletion of one `if ...: raise` guard
(span → `pass`). Sites restricted to function bodies (owned range: all
functions of the two modules; module-level constants excluded). Selection:
`random.Random(20261015)`, per-function shuffle, round-robin across
functions, 30 per module / 60 total. Each mutant applied by splicing the
replacement into the original source span; run
`python3 -m pytest <importer tests> -x -q -p no:cacheprovider` under a
60 s timeout; original bytes restored and sha256-verified after every
mutant. Exit 0 → survived; nonzero → killed; timeout → timeout.

## Per-module table

| module | generated | killed-before | survived | equivalent | killed-after | timeout | score before → after |
|---|---|---|---|---|---|---|---|
| `common/sni_then_known_guard.py` (325 lines) | 30 | 25 | 5 | 3 (003, 022, 028) | 2 (004, 014) | 0 | 25/27 = 92.6% → 27/27 = 100% |
| `common/sni_session_state_guard.py` (377 lines) | 30 | 25 | 5 | 3 (018, 022, 028) | 2 (012, 029) | 0 | 25/27 = 92.6% → 27/27 = 100% |

## Surviving-mutant list (non-equivalent) with killing tests

| mutant | site (file:line) | original → mutated | killing test (re-verified FAIL under mutant) |
|---|---|---|---|
| then_known-004 | `sni_then_known_guard.py:159` | `text[:-1] + "+00:00"` → `text[:-1] - "+00:00"` | `test_m7b_then_known__aware_value_004` — `TypeError: unsupported operand type(s) for -: 'str' and 'str'` |
| then_known-014 | `sni_then_known_guard.py:159` | `text[:-1]` → `text[:-2]` (1 → 2) | `test_m7b_then_known__aware_value_014` — `ValueError: published_at must be an ISO-8601 datetime with offset...` |
| session_state-012 | `sni_session_state_guard.py:177` | `len(head) not in (1, 2)` → `not in (2, 2)` (1 → 2) | `test_m7b_session_state__wall_minute_012` — verdict refused `('SESSION_TIME_INVALID',)` instead of `open` |
| session_state-029 | `sni_session_state_guard.py:224` | `or`-chain in `_load_zone` head → `and` | `test_m7b_session_state__load_zone_029` — `TypeError: unhashable type: 'list'` instead of `TIMEZONE_INVALID` refusal |

All 60 mutants are enumerated with kind/function/line/description in the
harness output (`~/lanes/scratch/m7b/mutants.json`,
`results_phase1.json`); the killed-before 50 were killed by the existing
suites alone.

## Equivalent arguments

- **then_known-003** (`_as_datetime:143` date-only `return` → `None`): the
  only caller `_aware_value` discards every naive parse (`tzinfo is None`
  → `None`), and the 10-char date-only branch can only produce naive
  datetimes, so both versions yield `None` on every reachable input.
- **then_known-022** (`_as_datetime:136` `or`→`and`): the only caller
  `_aware_value` already returned `None` for non-str/empty values at its
  own line-155 guard, so `text` is always a non-empty `str` and both
  `A or B` and `A and B` evaluate false at this site.
- **then_known-028** (`_as_datetime:146` `body[:-1]`→`[:-2]`): dead branch
  through the only caller — `_aware_value` rewrites a trailing `Z` to
  `+00:00` (line 159) before calling, so the argument never ends with
  `Z` and this strip never runs.
- **session_state-018** (`_iana_names:211` `lru_cache(maxsize=1)`→`2`): a
  no-argument function's cache holds at most one entry ever; any
  `maxsize ≥ 1` is observably identical.
- **session_state-022** (`_state_at:276` `spans[0][0]`→`spans[0][1]`): any
  instant inside the first span already returned `open`/`halted` from the
  loop above, so for every instant reaching line 276 the two comparisons
  agree — before open both true (pre_open), in-gap/after close both false
  (break/post_close).
- **session_state-028** (`_calendar_date:155` `or`→`and`): the
  `len(text) != 10` gate at line 149 refuses every short form before line
  155 runs, and any 10-char composition with non-(4,2,2) part lengths
  that passes the digit check also fails `date()` construction under the
  mutant (out-of-range month/day/year → `ValueError` → `None`), so both
  versions return `None` for exactly the same inputs.

## Excluded QF lines

`reviews/QF_QUARANTINE_FENCE_2026-10-13.md` enumerates fence sites only
under `residual/` (`s1_manifest.py`, `s1_prereg.py`, `s1_report.py`,
`run_s1.py`), `event_response/` (`s2_seal.py`, `s2_splits.py`,
`run_s2.py`), and `protocols/S0_PROTOCOL_REGISTER.md` — none lie in
`common/sni_then_known_guard.py` or `common/sni_session_state_guard.py`.
Zero mutants were excluded for fence overlap.

## What this does NOT prove

- A mutation score measures TEST STRENGTH only, never statistical
  validity; no acceptance row moves to DONE and no evidence claim is
  upgraded by this sweep.
- 60 mutants from six operators over 702 lines is a sample, not
  exhaustion; other operators (statement deletion, boundary-value
  mutations on strings, keyword-argument reordering) were not run.
- `-x` stops at the first failing test, so a killed mutant may hide
  additional unexercised behavioural differences behind the first kill.
- The six EQUIVALENT calls are call-graph arguments over these DRAFT
  modules as currently written: they consume owner-supplied values and
  are unwired, so branches dead today (e.g. `_as_datetime`'s own Z
  strip, the naive date-only return) could become live if a future
  owner wiring changes the call graph — the equivalence claims expire
  with the code shape, not the semantics.
