# MUTATION SWEEP M7E — 2026-10-14

SNI-local DRAFT mutation sweep (SNI commission 8659, lane M7E). Two guard
modules, frozen operator set, deterministic seeded draw. Target modules are
pure DRAFT refusal contracts; no authority flag, no identity minting, no
then-known violation introduced by this sweep — the sweep mutates and
restores module bytes in place inside the lane worktree only.

Target modules (read-only for this lane; byte-identical to base after the
sweep, sha256 verified after every mutant):

- `research/single_name_intelligence/common/sni_kpi_missingness_guard.py`
- `research/single_name_intelligence/common/sni_release_evidence_guard.py`

Importer-test sets (grep for the module name across `tests/` at base
commit `97e9d6e7c3d15eeb3f8bb9e8996bfec710e6bfe0`): exactly one file each —
`tests/test_sni_kpi_missingness_guard.py` (46 tests, 0.92 s unmutated) and
`tests/test_sni_release_evidence_guard.py` (37 tests, 0.80 s unmutated).
Both suites are far under the 20 s threshold, so the 15-mutant slow-suite
cap was never invoked; per-module cap stayed 40 / total 60.

## Summary

| metric | count |
|---|---|
| mutants generated | 60 (40 kpi + 20 release) |
| killed by existing suite (before) | 44 |
| survived (before) | 16 |
| equivalent | 8 |
| non-equivalent survivors (before) | 8 |
| killed after `tests/test_sni_mut7_e.py` | 52 (all 8 non-equivalent survivors killed) |
| timeout | 0 |

Score before: **44/60 = 73.3 %** raw; **44/52 = 84.6 %** excluding
equivalents. Score after: **52/60 = 86.7 %** raw; **52/52 = 100 %** of
non-equivalent mutants. Every killed-after claim was re-verified by
re-applying that exact mutant and running
`python3 -m pytest tests/test_sni_mut7_e.py -x -q -p no:cacheprovider`
(8/8 KILLED, each by its targeted test name).

## Operator set and seed

AST harness in a scratch path outside the repo (not committed). Operators,
frozen per method: comparison flip (`<`↔`>`, `<=`↔`>=`, `==`↔`!=`);
arithmetic swap (`+`↔`-`, `*`↔`/`); constant perturbation (int n→n+1,
float x→x*1.001, `True`↔`False`); `return x`→`return None` on one value
return per mutant; `and`↔`or`; deletion of one `if …: raise` guard.
Draw: `random.Random(20261015)`, stratified by enclosing function
(round-robin over functions, shuffled within each stratum). Sites drawn
only from the two owned modules. Candidate pools: kpi 58, release 46.
Restore discipline: original bytes rewritten and sha256-verified after
every mutant; a sanity run of `ast.unparse` on the UNMUTATED tree passes
both suites (so unparse formatting is not what kills mutants). Each mutant
run: `timeout 60 python3 -m pytest <importer tests> -x -q -p no:cacheprovider`.

## Per-module table

| module | candidates | sampled | killed-before | equiv | real survivors | killed-after | timeout |
|---|---|---|---|---|---|---|---|
| `sni_kpi_missingness_guard.py` | 58 | 40 | 31 | 4 | 5 | 36 | 0 |
| `sni_release_evidence_guard.py` | 46 | 20 | 13 | 4 | 3 | 16 | 0 |
| total | 104 | 60 | 44 | 8 | 8 | 52 | 0 |

## Surviving mutants and killing tests

All 8 non-equivalent survivors were killed by new tests in
`tests/test_sni_mut7_e.py`; each mutant was re-run against that file to
prove the kill (fail lines quoted from the re-run).

| mutant | site (original line) | original → mutated | killing test | re-run fail line |
|---|---|---|---|---|
| `kpi:guard#1@147` | `_as_records` :147 | delete `if not isinstance(series, (list, tuple)): raise TypeError` | `test_m7e_kpi_as_records_1` | `FAILED tests/test_sni_mut7_e.py::test_m7e_kpi_as_records_1 - AssertionError` |
| `kpi:guard#6@151` | `_as_records` :151 | delete `if not isinstance(item, Mapping): raise TypeError` | `test_m7e_kpi_as_records_2` | `FAILED tests/test_sni_mut7_e.py::test_m7e_kpi_as_records_2 - AttributeError` |
| `kpi:guard#2@158` | `_as_period_ids` :158 | delete `if not isinstance(periods, (list, tuple)): raise TypeError` | `test_m7e_kpi_as_period_ids_1` | `FAILED tests/test_sni_mut7_e.py::test_m7e_kpi_as_period_ids_1 - Failed: DID N[OT RAISE]` |
| `kpi:guard#3@176` | `kpi_value` :176 | delete `if not isinstance(record, Mapping): raise TypeError` | `test_m7e_kpi_kpi_value_1` | `FAILED tests/test_sni_mut7_e.py::test_m7e_kpi_kpi_value_1 - AttributeError` |
| `kpi:boolop#1@264` | `check_kpi_series` :264 | `not _blank(period_id) and not _contains(...)` → `or` | `test_m7e_kpi_check_kpi_series_1` | `FAILED tests/test_sni_mut7_e.py::test_m7e_kpi_check_kpi_series_1 - AssertionError` |
| `release:guard#2@138` | `_as_slots` :138 | delete `if not isinstance(value, (list, tuple)): raise TypeError` | `test_m7e_release_as_slots_1` | `FAILED tests/test_sni_mut7_e.py::test_m7e_release_as_slots_1 - AssertionError` |
| `release:guard#6@142` | `_as_slots` :142 | delete `if not isinstance(item, Mapping): raise TypeError` | `test_m7e_release_as_slots_2` | `FAILED tests/test_sni_mut7_e.py::test_m7e_release_as_slots_2 - AttributeError` |
| `release:const#8@98` | `ReleaseVerdict` :98 | `@dataclass(frozen=True)` → `frozen=False` | `test_m7e_release_release_verdict_1` | `FAILED tests/test_sni_mut7_e.py::test_m7e_release_release_verdict_1 - Failed: DID N[OT RAISE]` |

Pattern worth naming: five of eight survivors are deleted input-type
refusal guards whose tests existed only as "valid inputs behave well" —
the refusals were unobserved. The remaining three are the reported-periods
membership condition, the slots sequence guard, and the frozen-dataclass
guarantee on `ReleaseVerdict` (verdict immutability had no test at all).

## Equivalent arguments

| mutant | one-line semantic argument |
|---|---|
| `kpi:retnone#10@88` | bare `return` rewritten as `return None` — the identical statement in Python; a harness artifact (the AST form of a bare return has `value=None`), not a real mutant. |
| `release:retnone#5@87` | same bare-`return` → `return None` artifact in the sibling module. |
| `kpi:retnone#1@128` | `_present` is dead code — the name occurs only at its definition (line 127); no call site exists, so no behavior is observable. |
| `kpi:retnone#0@124` | `_blank`'s final `return False` → `return None`: every call site consumes the result only in a boolean context, where `None` and `False` are indistinguishable. |
| `release:retnone#0@125` | same `_blank` final-return falsy equivalence in the release module. |
| `kpi:retnone#14@138` | `_finite_number`'s final `return False` → `return None`: every call site applies `not` to the result; `None` is falsy like `False`. |
| `release:retnone#10@150` | `_required_flag`'s default `return True` → `return None`: the only consumer tests `required is not False`, and `True` and `None` agree on that test. |
| `release:boolop#0@136` | `_as_slots` `isinstance(value, (str, bytes)) or isinstance(value, Mapping)` → `and`: every input class reaching either guard still raises `TypeError` with the identical message `slots must be a sequence of mappings` (the next guard raises the same message); only an object that is simultaneously list/tuple AND Mapping could distinguish, which page data cannot construct. |

## Excluded QF lines

`QF_QUARANTINE_FENCE_2026-10-13.md` censuses fence points only in
`residual/s1_*.py`, `event_response/s2_*.py` and `run_s1.py`/`run_s2.py`,
plus `protocols/S0_PROTOCOL_REGISTER.md`. **Zero overlap** with the two
`common/` modules swept here, so no mutant was excluded for QF coverage.

## What this does NOT prove

- A mutation score measures TEST STRENGTH against this operator set and
  this seeded 60-mutant draw, not the statistical validity of anything the
  guards describe. 104 candidate sites existed; 44 were never sampled.
- No acceptance row moves to DONE because of this sweep; it only hardens
  the evidence behind rows that already cite these tests.
- The 8 equivalent classifications are semantic arguments, not machine
  proofs; the bare-`return` pair is a harness artifact recorded as such.
- Both target modules remain DRAFT refusal contracts: nothing here wires
  them into any owner, pipeline, page, or job, and every authority flag
  stays literal False.
