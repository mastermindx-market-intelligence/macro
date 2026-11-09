# MUTATION SWEEP M8D — 2026-10-14

Bounded mutation sweep over two SNI DRAFT guard modules, run per the frozen
MUT-lane method (32 sibling lanes MUT1-MUT7 preceded it). The sweep measures
TEST STRENGTH of the existing per-module suites; it changes no production code.
Lane M8D, branch `claude/sni-m8d-20261014-20261014T092504Z`, base
`9a2682e4a5f1f9794acf168f512d96d819476b05`.

- `research/single_name_intelligence/common/sni_join_guard.py` (all functions)
- `research/single_name_intelligence/common/sni_ads_ratio_guard.py` (all functions)

SNI DRAFT contract language holds throughout: the guards consume
owner-supplied opaque identity strings (Stock Identity / Data OS), never mint
identifiers, keep every authority flag literal False, and feed no ranker,
gate, sizer, signal, escalation, or trade path. New fixtures are synthetic.

## Summary

| metric | value |
|---|---|
| mutants generated (drawn) | 80 (40 per module, of 165 / 156 candidates) |
| killed by the EXISTING suite ("killed-before") | 70 |
| survived the existing suite ("survived-before") | 10 |
| killed-after (survivors killed by `tests/test_sni_mut8_d.py`, each re-verified by re-applying the mutant) | 7 |
| equivalent (one-line semantic argument below) | 3 |
| timeout | 0 |
| mutation score before | 70/80 = 87.5% |
| mutation score after | 77/77 non-equivalent = 100% (raw 77/80 = 96.25%; the 3 equivalents are unkillable by construction) |
| new tests | 8 (7 killing tests + 1 hardening test for an un-observable module-level guard) |

Unmutated baselines: `tests/test_sni_join_guard.py` 48 passed (test set under
importer-test-csv, ~1.85 s), `tests/test_sni_ads_ratio_guard.py` 46 passed
(~1.34 s); both far under the 20 s cap, so the full 40-per-module budget
applied (cap 40/module, 60 total). After the new tests: 389 passed in 3.05 s
across all eight importer test files and the new killing test file.

Importer-test sets (grep over `tests/test_sni_*.py` at the base commit):

- `sni_join_guard.py` importers (6): `test_sni_join_guard.py`,
  `test_sni_mutation_join_guard.py`, `test_sni_famj_repair.py`,
  `test_sni_famj2_repair.py`, `test_sni_guard_family_invariants.py`,
  `test_sni_mut7_d.py`.
- `sni_ads_ratio_guard.py` importers (4): `test_sni_ads_ratio_guard.py`,
  `test_sni_guard_family_invariants.py`, `test_sni_mut7_d.py`,
  `test_sni_x8crepc_repair.py`.

## Operator set and seed

Operators (frozen method): comparison flip (`<`↔`<=`, `>`↔`>=`, `==`↔`!=`,
`is`↔`is not`, `in`↔`not in`); arithmetic swap (`+`↔`-`, `*`↔`/`,
`//`↔`%`); constant perturbation (int n→n+1, float x→x*1.001, `True`↔`False`);
one `return <expr>`→`return None` per function (first eligible);
`and`↔`or` (first connector per BoolOp); deletion of one `if ...: raise`
guard (raise body→`pass`).

Selection: AST harness (scratch, `~/lanes/scratch/m8d/`, NOT committed) with
`random.Random(20261016)` fresh per module, stratified by function
(round-robin over sorted function groups, each group shuffled by the rng).
Join module: 40 mutants over 24 functions (12 const, 11 ret, 11 cmp, 4
boolop, 2 ifraise; no arith). Ads module: 40 mutants over 17 functions (15
const, 12 ret, 8 cmp, 1 arith, 4 ifraise). Each mutant applied in place
inside the lane worktree, then `timeout 60 python3 -m pytest <importer
tests> -x -q -p no:cacheprovider`; original bytes restored and
sha256-verified after EVERY mutant and at the end (join
`23e3a38f419ea0781…`, ads `78713da74fec448141…` — both byte-identical to
base at commit time; `git diff --stat <base> -- …/common/` is empty).

## Per-module table

| module | candidates | drawn | killed-before | survived-before | killed-after | equivalent | timeout | score before → after (non-equiv) |
|---|---|---|---|---|---|---|---|---|
| `common/sni_ads_ratio_guard.py` | 156 | 40 | 36 | 4 | 3 | 1 | 0 | 36/40 (90.0%) → 39/39 (100%) |
| `common/sni_join_guard.py`     | 165 | 40 | 34 | 6 | 4 | 2 | 0 | 34/40 (85.0%) → 38/38 (100%) |
| **total**                      | 321 | **80** | **70** | **10** | **7** | **3** | **0** | 70/80 (87.5%) → 77/77 (100%) |

## Surviving-mutant list with killing test name

All 7 non-equivalent survivors are killed by `tests/test_sni_mut8_d.py`;
every kill was re-verified by re-applying the stored mutant source and
re-running ONLY the named test with `pytest -k` (each run rc=1, the named
test FAILED, the rest deselected).

| mutant id | site (file:line, original -> mutated) | killing test |
|---|---|---|
| `sni_ads_ratio_guard_08` | `sni_ads_ratio_guard.py:75` `if not isinstance(flags, Mapping): raise ValueError("authority flags is not a mapping")` -> `pass` | `test_m8d_ads_ratio_guard__refuse_nonfalse_authority_isinstance_08` |
| `sni_ads_ratio_guard_14` | `sni_ads_ratio_guard.py:108` `_blank` `value == ""` -> `value != ""` | `test_m8d_ads_ratio_guard__blank_empty_string_14` |
| `sni_ads_ratio_guard_33` | `sni_ads_ratio_guard.py:202` `_aware_datetime` `text[:-1] + "+00:00"` -> `text[:-1] - "+00:00"` | `test_m8d_ads_ratio_guard__aware_datetime_z_suffix_33` |
| `sni_join_guard_13`       | `sni_join_guard.py:173` `if self.reasons: raise ValueError("ALLOWED verdict cannot carry reasons")` -> `pass` | `test_m8d_join_guard___post_init___allowed_with_reasons_13` |
| `sni_join_guard_35`       | `sni_join_guard.py:263` `_known_at_later_than_as_of` `len(as_of) == 10` -> `len(as_of) != 10` (date-vs-datetime branch flip) | `test_m8d_join_guard___known_at_later_than_as_of_non10_35` |
| `sni_join_guard_38`       | `sni_join_guard.py:268` `_known_at_later_than_as_of` `kd > ad` -> `kd >= ad` (strict-later lost) | `test_m8d_join_guard___known_at_later_than_as_of_strict_38` |
| `sni_join_guard_39`       | `sni_join_guard.py:271` `_known_at_later_than_as_of` `if kt is None or at is None: return False` -> `if kt is not None or at is not None: return False` (None-check inversion) | `test_m8d_join_guard___known_at_later_than_as_of_datetime_path_39` |

The surviving-mutant classes are telling: the existing suites exercise the
public refusal contract well (nearly every reason-path, comparison, and
guard-deletion mutant died) but never pin (a) the literal class of the
raise in `refuse_nonfalse_authority` for non-Mapping input, (b) the
`_blank("")` empty-string contract (only `_blank(None)` was covered, M7D
landed that test as `test_m7d_ads_ratio_guard__blank_25`), (c) Z-suffix
parsing in `_aware_datetime`, (d) the JoinVerdict ALLOWED-cannot-carry-
reasons invariant, or (e) the date-vs-datetime branch selector and the
strict / non-strict / None-check invariants inside
`_known_at_later_than_as_of`.

`test_m8d_join_guard___module_level_authority_flags_pin` covers an
un-observable line (`sni_join_guard.py:137` / `sni_ads_ratio_guard.py:68`:
the per-key check that runs against the module-level `AUTHORITY_FLAGS`
constants, which are literal False). No test can ever make that branch
fire from the public surface, so the same constant is verified end-to-end
through the JoinVerdict post_init at line 166 (which carries an equivalent
per-key check that DOES fire on call-site `flags=MappingProxyType(...)`
arguments, including a single True slot). The hardening test pins the
OBSERVABLE family-rule for re-bound True call-site flags, not the
un-observable module self-check.

## Equivalent arguments

1. `sni_ads_ratio_guard_06` — `sni_ads_ratio_guard.py:68`
   `refuse_nonfalse_authority` first loop `if value is not False: raise
   ValueError("AUTHORITY_FLAGS[...]")` -> `pass`. The loop iterates over
   `AUTHORITY_FLAGS.items()` (a module-level constant of literal False
   values); no caller can mutate it through the public contract, so the
   branch is unreachable and the change is un-observable. The observable
   invariant of the family rule is the second loop, which is pinned by the
   new `test_m8d_join_guard___module_level_authority_flags_pin` hardening.
2. `sni_join_guard_06` — `sni_join_guard.py:137` same construct as (1) in
   `sni_join_guard.refuse_nonfalse_authority` — unreachable for the same
   reason; observable behaviour is pinned through `JoinVerdict.__post_init__`
   at line 166, also caught by the new hardening test.
3. `sni_join_guard_20` — `sni_join_guard.py:189` `_blank` `return False`
   (the falsey-default branch after the two positive cases) -> `return
   None`. Every caller uses `if _blank(x):` or `if not _blank(x):`. Both
   `False` and `None` are falsy in Python so the public contract is
   preserved exactly; no callers pin the literal type, and M7D's
   `test_m7d_ads_ratio_guard__blank_25` precedent (the sibling
   `_blank` mutation at `return True`) addressed the True→False direction,
   not the False→None direction. Equivalent by falsy-by-construction.

## Excluded QF lines

The quarantine-fence review (`research/single_name_intelligence/reviews/
QF_QUARANTINE_FENCE_2026-10-13.md`) covers only `residual/s1_manifest.py:26`,
`event_response/s2_seal.py:177`, `event_response/s2_splits.py:40/64`,
`residual/s1_prereg.py:188`, `event_response/s2_seal.py:416`,
`residual/run_s1.py:309/349/353/486/643/650`, etc. — none of the two
target modules' lines (`common/sni_join_guard.py`, `common/sni_ads_ratio_guard.py`)
appear in that list, so no mutants were excluded on QF grounds.

## What this does NOT prove

- Mutation score is test strength, not statistical validity.
- Killing every drawn non-equivalent mutant at 100% means the existing
  family-rule suite is well-pinned against FIRST-ORDER edits of these two
  DRAFT guards. It does NOT mean every property holds under second-order
  edits (two simultaneous mutations), nor under adversarial inputs not in
  the harness's draw set.
- No row in the SNI acceptance matrix moves from PARTIAL to DONE.
- The HARD-CODED `AUTHORITY_FLAGS` constants are documented as literal
  False; the family rule binds across modules, but the M8D sweep is
  bounded to two guard modules and does not re-issue that cross-module
  pin.
- The `_known_at_later_than_as_of` branch selector (date vs datetime,
  <, >=, None-check) was exercised at three boundary calls; a
  fourth mutant at the same line in different inputs could still survive.
