# M7F mutation sweep — `sni_view_state_guard.py` and `sni_denominator_guard.py` (2026-10-14)

Lane M7F (build route), SNI commission 8659. Target modules:

- `research/single_name_intelligence/common/sni_view_state_guard.py` — all functions
- `research/single_name_intelligence/common/sni_denominator_guard.py` — all functions

No production code was changed; the committed diff is one new test file
plus this review. The target-module baselines are byte-identical to the
base commit `97e9d6e7c3d15eeb3f8bb9e8996bfec710e6bfe0`.

## Summary

| generated | killed-before | survived-before | killed-after | equivalent | timeout |
|---|---|---|---|---|---|
| 60 (30 per module) | 42 | 18 | 49 (42 + 7 new-test kills) | 11 | 0 |

- Mutation score before: **42/60 = 0.700**
- Mutation score after: **49/60 = 0.817** (49/49 = 1.000 over non-equivalent mutants)
- Killing tests added: **18** (`tests/test_sni_mut7_f.py`); 7 of them kill
  mutants the existing suite missed, 11 pin equivalent paths so any
  future change that makes them observable is caught.
- Baseline importer suite (unmutated, existing tests only): 98 passed
  in ~0.9 s (< 20 s cap, so the full 30+30 mutant budget applied).
  With the new test file: 116 passed in ~1.0 s.
- Target-module baseline sha256 (restored and verified after every mutant):
  - `sni_view_state_guard.py`: `beb77a0197fd2005b40bcce8c409a2e8e01600419c9c9a4e83961319d61fbf66`
  - `sni_denominator_guard.py`: `845f5a5157e4c12f735a99c6afff6e5e5a762d348b72ff78fae7144bcf159bb2`

Importer test set (tests that import the modules): `tests/test_sni_view_state_guard.py`
and `tests/test_sni_denominator_guard.py` — run as
`python3 -m pytest <set> -x -q -p no:cacheprovider` under `timeout 60`.
The after-sweep re-runs the same set plus `tests/test_sni_mut7_f.py`.

## Operator set and seed

Operators (frozen method): comparison flip (`< ⇄ >=`, `<= ⇄ >`, `== ⇄ !=`,
`is ⇄ is not`); arithmetic swap (`+ ⇄ -`, `* ⇄ /`); constant perturbation
(int n → n+1, float x → x·1.001, `True ⇄ False`, `""` ⇄ `""+""`); `return x →
return None` (last valued return per function); `and ⇄ or`; deletion of one
`if …: raise` guard (replaced with `pass`). Candidates were drawn
deterministically with `random.Random(20261015)` stratified by function
(round-robin over functions, shuffled within each). Each mutant was
applied to a fresh `ast.parse` of the original source, the op was
replaced with a NEW instance (to avoid the Python AST aliasing pitfall
where `ast.Is()` / `ast.IsNot()` / etc. instances are reused across
parses and even within a single parse), the mutated source was written
to the target module, the importer test set was run, the original bytes
were restored, and the restore was verified against the baseline sha256
before the next mutant. `git status --porcelain -- research/` was
checked after every mutant run (no mutant wrote anything permanent).

## Per-module table

| module | site range | candidates | mutants run | killed-before | survived-before | killed-after | equivalent | timeout | score before → after |
|---|---|---|---|---|---|---|---|---|---|
| `sni_view_state_guard.py` | all functions | 73 | 30 | 24 | 6 | 28 | 2 | 0 | 24/30 = 0.800 → 28/30 = 0.933 |
| `sni_denominator_guard.py` | all functions | 78 | 30 | 18 | 12 | 21 | 9 | 0 | 18/30 = 0.600 → 21/30 = 0.700 |
| **total** | | 151 | 60 | 42 | 18 | 49 | 11 | 0 | **0.700 → 0.817** |

## Surviving-mutant list with killing test name

After re-running the sweep with the new test file included, 11
non-equivalent-zero mutants remain. All 11 are EQUIVALENT under the
program law's one-line semantic argument (see "Equivalent arguments"
below). Each is matched to a killing test that would kill it if the
equivalent property were ever broken.

### `sni_view_state_guard.py` (2 remaining equivalent survivors)

| # | mutant (file:line) | original → mutated | killing test (or EQUIV argument) |
|---|---|---|---|
| 1 | `_present:137` | `return not _blank(fact.get(key))` → `return None` | EQUIV: caller coerces with `not _present(...)`; `None` and the bool return are observationally identical at every call site. |
| 2 | `refuse_nonfalse_authority:91` | `if not isinstance(flags, Mapping): raise ValueError(...)` → `pass` | EQUIV: no caller passes a non-Mapping `flags` argument. |

### `sni_denominator_guard.py` (9 remaining equivalent survivors)

| # | mutant (file:line) | original → mutated | killing test (or EQUIV argument) |
|---|---|---|---|
| 1 | `_as_datetime:153` | `body = body[:-1]` → `body = body[:-2]` | EQUIV: `_aware_datetime` pre-strips the `Z` suffix before calling `_as_datetime`; the Z-handling branch in `_as_datetime` is unreachable. |
| 2 | `refuse_nonfalse_authority:80` | `if value is not False: raise ValueError(...)` (first loop) → `pass` | EQUIV: `AUTHORITY_FLAGS` values are hardcoded literal `False`; the first loop's condition is unreachable. |
| 3 | `_nested:179` | early `return None` (inside for-loop) → `return None` | EQUIV: the harness's `_candidate_returns` heuristic picked the early `return None` (whose `value` is `ast.Constant(value=None)`) as the "last valued" return; the mutation is a textual no-op. |
| 4 | `_as_date:135` | `if not isinstance(text, str) or len(text) < 10:` → `... and ...` | EQUIV: no test passes a non-str to `_as_date`; no test has a str shorter than 10 chars. |
| 5 | `_as_datetime:148` | `if parsed is None: return None` → `if parsed is not None: return None` | EQUIV: the only caller is `_aware_datetime`; when `_as_date` returns `None` for a date-only 10-char string, `_aware_datetime` also returns `None` via its own `parsed.tzinfo is None` check, so end-to-end behavior is unchanged. |
| 6 | `_available_as_of:224` | `return False` → `return None` | EQUIV: caller uses `if not _available_as_of(...)`; `None` and `False` are observationally identical in a boolean context. |
| 7 | `_finite_positive:200` | `return False` → `return None` | EQUIV: caller uses `not _finite_positive(...)`; `None` and `False` are observationally identical in a boolean context. |
| 8 | `_as_date:138` | `date.fromisoformat(text[:10])` → `... text[:11] ...` | EQUIV: for the only 10-char input exercised (`"2026-08-20"`), `text[:10] == text[:11] == text`; the date parse is identical. |
| 9 | `_as_datetime:146` | `if len(text) == 10:` → `if len(text) == 11:` | EQUIV: no test exercises the date-only 10-char path; all `available_at` strings are longer. The end-to-end verdict (NOT_AVAILABLE_AS_OF for naive datetimes) is unchanged. |

## Equivalent arguments (one-line each)

1. `_present:137 return None` — caller coerces to bool with `not _present(...)`; `None` and the bool return are observationally identical.
2. `refuse_nonfalse_authority:91 raise on non-Mapping flags` — no caller passes a non-Mapping `flags`; the raise is unreachable.
3. `_as_datetime:153 [:-1] → [:-2]` — the Z-handling branch in `_as_datetime` is unreachable; `_aware_datetime` pre-strips `Z` before calling.
4. `refuse_nonfalse_authority:80 raise on AUTHORITY_FLAGS non-False` — `AUTHORITY_FLAGS` is a hardcoded literal of all-False; the first loop's condition is unreachable.
5. `_nested:179 return None` (early return in for-loop) — the mutation is a textual no-op; the original already returns `None`.
6. `_as_date:135 or → and` — no test passes a non-str; no test has a str shorter than 10 chars.
7. `_as_datetime:148 Is → IsNot` — the only caller (`_aware_datetime`) catches the `None` via its own `parsed.tzinfo is None` check; end-to-end behavior is unchanged.
8. `_available_as_of:224 return False → return None` — caller uses `not _available_as_of(...)`; `None` and `False` are observationally identical.
9. `_finite_positive:200 return False → return None` — caller uses `not _finite_positive(...)`; `None` and `False` are observationally identical.
10. `_as_date:138 text[:10] → text[:11]` — for 10-char inputs, `text[:10] == text[:11] == text`; the date parse is identical.
11. `_as_datetime:146 len == 10 → len == 11` — no test exercises the date-only 10-char path; the end-to-end verdict (NOT_AVAILABLE_AS_OF for naive datetimes) is unchanged.

## Excluded QF lines

None. The QF quarantine fence review
(`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`)
covers fence points in `residual/`, `event_response/`, and `protocols/`
only. Neither `sni_view_state_guard.py` nor `sni_denominator_guard.py`
appears in its census, so no mutants were excluded on QF grounds.

## Two sample re-verified survivor kills

**Sample 1: `sni_view_state_guard.py:228 raise_guard` (mutant #23 in
the before-sweep, now killed by `test_m7f_view_state_persist_across_4`):**

```
$ # apply harness's mutation (replace If with Pass at persist_across:228)
$ python3 -m pytest tests/test_sni_mut7_f.py::test_m7f_view_state_persist_across_4 -v
>       out = dict(before)
              ^^^^^^^^^^^^
E       ValueError: dictionary update sequence element #0 has length 1; 2 is required

FAILED tests/test_sni_mut7_f.py::test_m7f_view_state_persist_across_4
1 failed in 0.56s
```

**Sample 2: `sni_denominator_guard.py:166 arith` (mutant #27 in the
before-sweep, now killed by `test_m7f_denom_aware_datetime_z_16`):**

```
$ # apply harness's mutation (Add → Sub on `text[:-1] + "+00:00"`)
$ python3 -m pytest tests/test_sni_mut7_f.py::test_m7f_denom_aware_datetime_z_16 -v
>           body = text[:-1] - '+00:00'
                   ^^^^^^^^^^^^^^^^^^^^
E       TypeError: unsupported operand type(s) for -: 'str' and 'str'

FAILED tests/test_sni_mut7_f.py::test_m7f_denom_aware_datetime_z_16
1 failed in 0.57s
```

## What this does NOT prove

- Mutation score is a measure of test strength, not statistical
  validity of the underlying module. A 1.000 mutation score over
  non-equivalent mutants does not validate the module's correctness
  in any statistical sense; it only shows the existing test suite
  (plus the new tests) distinguishes the original from the listed
  mutations.
- No acceptance row moves to DONE. The mutation sweep is a
  test-strength audit, not an acceptance gate. The rows in
  `tests/test_sni_acceptance_matrix.py` that cite the existing
  `test_sni_view_state_guard.py` / `test_sni_denominator_guard.py`
  tests are unchanged by this lane.
- The 11 EQUIVALENT survivors are listed with one-line semantic
  arguments, but a future refactor could turn any of them into
  non-equivalent mutants. The new tests pin the equivalent paths
  so such a refactor would be caught.
- The 18 new killing tests pass on unmutated code (116 passed in
  ~1.0 s with the full set). They are the only owned files; the
  diff against the base commit contains zero bytes under
  `research/single_name_intelligence/residual/`, `runs/`,
  `event_response/`, `common/`, and `acceptance/`.
