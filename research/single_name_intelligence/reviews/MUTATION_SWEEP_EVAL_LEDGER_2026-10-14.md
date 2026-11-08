# M6E mutation sweep — `sni_eval_ledger._validate_score` / `EvalLedger.verify_chain` — 2026-10-14

SNI-local DRAFT contract review. This sweep measures **test strength** of
the existing evaluation-ledger importer suite against the score-validation
gate and the chain-verification gate — the two pieces of code whose strength
of evidence backs the acceptance rows that cite the eval-ledger tests. It
does not move any acceptance row to DONE. Authority flags stay false;
identity ids remain caller-supplied opaque strings owned by Stock
Identity / Data OS. Fixtures in the killing tests are synthetic. No
production module was edited.

## Summary

| item | count |
|---|---|
| generated (selected) | 15 |
| killed-before | 14 |
| survived-before | 1 |
| killed-after | 15 |
| equivalent | 0 |
| timeout | 0 |
| score before | 14/15 = 93.3% |
| score after | 15/15 = 100% |
| new killing tests | 2 |

Score = killed / (generated − equivalent). Candidate sites before
sampling: 38 in the owned site range. Seed `20261014`, stratified by
function (round-robin `_validate_score` ↔ `verify_chain`). 0
TIMEOUT-UNSAFE (no `runs/` writes; importer suite is
`tests/test_sni_eval_ledger.py` + `tests/test_sni_eval_ledger_property.py`).

The 14.5 minute unmutated importer suite (~30 s) placed this `matrix`
above the 20-s threshold, so the module was capped at 15 mutants per
lane rules. Both files in the kill suite are read-only assertions; their
unmutated wall-clock cost is what determined the cap.

## Operator set and seed

Harness (`~/lanes/scratch/m6e/harness.py`, not committed):

- comparison flip: `<`↔`>`, `<=`↔`>=`, `==`↔`!=`
- arithmetic swap: `+`↔`-`, `*`↔`/`
- constant perturbation on `True`/`False`
- `or`→`and` and `and`→`or`
- `is`→`is not` (insert "not "), `is not`→`is` (delete "not ")
- `not in`→`in` (delete "not "), `in`→`not in` (insert "not ")
- standalone unary `not ` → `` (drop negation)
- int perturbation: `n` → `n+1` (width-preserving only)

`random.Random(20261014)` round-robin over shuffled per-function site
lists, capped at 15 mutants total. Identity-float mutants
(`x * 1.001 == x`) and unary-minus swaps were dropped at collection.
Guard deletion (`if …: refuse` → `pass`) is out of scope for the
single-line-by-line harness: removing `if` breaks indentation and requires
cross-line surgery that the lane does not perform. The DEL_IF branch
was tested and discarded because it always emitted `SyntaxError` on this
module's structure.

Each mutant was applied in place, then
`timeout 60 python3 -m pytest <import tests> -x -q -p no:cacheprovider`
ran, `git status --porcelain -- research/` was checked (excluding the
mutated file), then original bytes were restored and sha256-checked.

## Per-module table

| module | candidates | selected | killed-before | survived-before | killed-after | equivalent | timeout | score before | score after |
|---|---|---|---|---|---|---|---|---|---|
| `sni_eval_ledger.py:_validate_score` | 33 | 11 | 10 | 1 | 11 | 0 | 0 | 10/11 | 11/11 |
| `sni_eval_ledger.py:verify_chain` | 5 | 4 | 4 | 0 | 4 | 0 | 0 | 4/4 | 4/4 |
| **total** | **38** | **15** | **14** | **1** | **15** | **0** | **0** | **14/15** | **15/15** |

`verify_chain` was fully covered by the existing suite (4/4). The single
survivor sits in `_validate_score`.

## Surviving-mutant list with killing test name

The non-equivalent survivor was re-applied against the new test file and
failed (KILLED-after).

| file:line | original → mutated | killing test |
|---|---|---|
| `sni_eval_ledger.py:660` | `or` → `and` (line 660 disjunction of `_validate_score`) | `test_m6e_validate_score_or_and_nonstring_item_refused` |

Re-verification (mutant applied, new test run, original bytes restored,
sha256 match):

```
>       assert ei.value.code == "INVALID_PAYLOAD"
E       AssertionError: assert 'NOT_MATURED' == 'INVALID_PAYLOAD'
FAILED tests/test_sni_mut6_eval_ledger.py::test_m6e_validate_score_or_and_nonstring_item_refused
```

A companion test (`test_m6e_validate_score_non_list_scored_ids_refused`)
pins the first clause of the same disjunction (`not isinstance(ids,
list)`) and also fails on the mutated code with `SCORED_IDS_UNSORTED`.
The two together pin both clauses of the disjunction: a future deletion
of either clause would be caught by exactly one of them.

## Equivalent arguments

None declared. All 15 mutants were either KILLED or SURVIVED; none were
EQUIVALENT.

## Excluded QF lines

The quarantine-fence review
(`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`)
catalogues 19 fence points. None are inside the owned site range
(`_validate_score` lines 631-698 or `verify_chain` lines 754-793); the
fence lines live in `residual/s1_manifest.py`, `event_response/s2_seal.py`,
`event_response/s2_splits.py`, `residual/s1_prereg.py`,
`residual/s1_report.py`, `residual/run_s1.py`, `event_response/run_s2.py`,
and `protocols/S0_PROTOCOL_REGISTER.md`. No mutant is excluded under the
QF rule.

## What this does NOT prove

- Mutation score is **test strength**, not statistical validity. A 100%
  mutation score on a 15-mutant sample means every tested operator
  perturbation is caught somewhere in the importer suite; it does not
  prove the gates are correct under all inputs, nor that the eval-ledger
  module matches `qledger` semantics under unregistered conditions.
- No acceptance row moves to DONE on the basis of this sweep. The
  `_validate_score` and `verify_chain` gates cited by the acceptance
  matrix are still backed by the same property and exemplar tests that
  existed before this lane; this sweep only adds two targeted regressions.
- The sweep does not exercise guard-deletion mutations (`if …: raise` →
  `pass`), return-drift mutations on intermediate returns inside
  `_validate_score`, or the `brier()` recomputation path. A future lane
  could add those with a cross-line harness.
- The sweep is bounded to two function bodies inside one file. Other
  acceptance-cited modules in `sni_eval_ledger.py` (`_validate_register`,
  `_validate_budget`, `_validate_publish`, `_validate_abstain`,
  `_validate_resolve`, `_validate_nogo`, `EvalLedger.append`,
  `EvalLedger.assert_replay_equal`, `EvalLedger.state`) are NOT swept here
  and were previously swept by MUT3A on 2026-10-13.