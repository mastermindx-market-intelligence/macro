# M8A mutation sweep — 2026-10-14

SNI-local DRAFT contract review. The two target modules are pure refusal
guards; this lane CONSUMES owner-supplied opaque identity strings (Stock
Identity / Data OS) and never mints issuer, listing, or security ids.
HISTORICAL-DESCRIPTIVE only: `rank_authority`, `gate_authority`,
`size_authority`, `signal_authority`, `escalation_authority` and
`trade_authority` stay literal False everywhere they are written.
Fixtures are synthetic.

## Summary

| item | count |
|---|---|
| mutants generated | 57 |
| killed by the pre-existing suite (killed-before) | 40 |
| survived the pre-existing suite (survived-before) | 12 |
| surviving but textually identical to original (skipped) | 5 |
| survivors re-verified with a new killing test (killed-after) | 11 |
| equivalent survivors (one-line argument below) | 1 |
| timeout | 0 |
| score before (killed-before / (killed-before + survived-before)) | 40 / 52 = 0.769 |
| score after ((killed-before + killed-after) / (killed-before + survived-before)) | 51 / 52 = 0.981 |
| score after on non-equivalent sites ((killed-before + killed-after) / (52 - 1 equivalent)) | 51 / 51 = 1.000 |

The 5 textually-identical mutants are an artefact of the AST-driven
harness: `ast.unparse` can produce a string that differs in surface form
but renders to the same bytes after the slice replacement (e.g., a
`return None` at a position where the original was already `return
None`). They are counted in the 57 generated but excluded from both score
denominators, and are not counted as survived or equivalent.
(Seat repair: the lane's original "score after" row divided by all 57
generated mutants, mixing a denominator that includes the 5 skipped
identicals with a numerator that cannot; corrected to the same
52-mutant denominator as "score before".)

Per-module:

| module | generated | killed-before | survived-before | killed-after | equivalent | timeout |
|---|---|---|---|---|---|---|
| sni_class_duplicate_guard.py | 27 | 22 | 5 | 5 | 0 | 0 |
| sni_three_clock_guard.py | 30 | 18 | 7 | 6 | 1 | 0 |

## Operator set and seed

Operators (frozen by the program law):

1. **compare_flip** — `<` `<=` `>` `>=` `==` `!=` are flipped within the
   set `{<, <=, >, >=, ==, !=}` (no flip for `is` / `is not` / `in` /
   `not in`).
2. **arith_swap** — `+` <-> `-`, `*` <-> `/` (no other arithmetic
   operators; the target modules do not use `%` / `//` / `**`).
3. **const_perturb** — small int `n` -> `n+1` (|n| ≤ 1000); float `x` ->
   `x * 1.001`; `True` <-> `False`. No string or `None` perturbation.
4. **return_none** — one return per function with a non-None value is
   replaced by `return None`.
5. **boolop_flip** — `and` <-> `or` on every `BoolOp`.
6. **delete_guard** — `if X: raise Y` (single-statement body) is
   rewritten to `if False: raise Y` (cleaner than deleting the line;
   leaves the `raise` and surrounding indentation intact).

Seed: `random.Random(20261016)`, stratified per function with a
per-function cap of 5 candidates and a total cap of 30 per module.
Stratification is round-robin across the function buckets so each
function contributes to the draw before any function is over-drawn.

## Per-module table

### sni_class_duplicate_guard.py

| # | func | op | site | original -> mutated | before | after |
|---|---|---|---|---|---|---|
| 1 | `_blank` | const_bool | L139 C15-19 | `True` -> `False` | SURVIVED | KILLED `test_m8a_class_duplicate__blank_constbool_l139` |
| 2 | `_blank` | return_none | L137 C8-19 | `return True` -> `return None` | SURVIVED | KILLED `test_m8a_class_duplicate__blank_return_none_l137` |
| 3 | `_blank` | return_none | L139 C8-19 | `return True` -> `return None` | SURVIVED | KILLED `test_m8a_class_duplicate__blank_return_none_l139` |
| 4 | `_blank` | return_none | L140 C4-16 | `return False` -> `return None` | SURVIVED | KILLED `test_m8a_class_duplicate__blank_return_none_l140` |
| 5 | `_pair_shape_ok` | boolop_flip | L155 C11-50 | `not isinstance(sid, str) or _blank(sid)` -> `not isinstance(sid, str) and _blank(sid)` | SURVIVED | KILLED `test_m8a_class_duplicate__pair_shape_ok_boolop_l155` |

22 other mutants were generated and KILLED by the pre-existing suite
(`tests/test_sni_class_duplicate_guard.py` and the family test
`tests/test_sni_famvcc_repair.py`). They are not enumerated here; the
harness JSONL (`~/lanes/scratch/m8a/results.jsonl`) is the full record.

### sni_three_clock_guard.py

| # | func | op | site | original -> mutated | before | after |
|---|---|---|---|---|---|---|
| 1 | `_as_date` | boolop_flip | L202 C7-51 | `not isinstance(text, str) or len(text) != 10` -> `not isinstance(text, str) and len(text) != 10` | SURVIVED | KILLED `test_m8a_three_clock__as_date_boolop_l202` |
| 2 | `_blank` | return_none | L172 C8-19 | `return True` -> `return None` | SURVIVED | KILLED `test_m8a_three_clock__blank_return_none_l172` |
| 3 | `_coerce_field_value` | return_none | L254 C4-26 | `return (parsed_dt, True)` -> `return None` | SURVIVED | KILLED `test_m8a_three_clock__coerce_field_value_return_none_l254` |
| 4 | `_present` | return_none | L192 C8-20 | `return False` -> `return None` | SURVIVED | EQUIVALENT (argument below) |
| 5 | `_as_datetime` | const_int | L215 C22-23 | `1` -> `2` in `body = body[:-1]` | SURVIVED | KILLED `test_m8a_three_clock__as_datetime_const_int_l215` |
| 6 | `_coerce_field_value` | return_none | L242 C8-26 | `return (None, False)` -> `return None` | SURVIVED | KILLED `test_m8a_three_clock__coerce_field_value_return_none_l242` |
| 7 | `_blank` | const_bool | L170 C15-19 | `True` -> `False` | SURVIVED | KILLED `test_m8a_three_clock__blank_constbool_l170` |

18 other mutants were generated and KILLED by the pre-existing suite
(`tests/test_sni_three_clock_guard.py` and the family test
`tests/test_sni_famvcc_repair.py`).

## Equivalent arguments

`_present` L192 (`return False` -> `return None`): the only call site
of `_present` in the module is the truthy check
`present = [f for f in fields if _present(record, f)]` inside
`classify_clocks`; `None` and `False` are both falsy and produce
identical filter results, identical `if not present:` and
`if len(present) > 1:` branches, and the verdict carries no None/False
discrimination. No external caller in the module or the test set
inspects the return type. Semantically equivalent for every observed
and statically reachable call path.

## Excluded QF lines

`research/single_name_intelligence/reviews/QF_QUARANTINE_FENCE_2026-10-13.md`
registers 19 fence points. All 19 are on `residual/`, `event_response/`,
`protocols/`, or report prose. None of them reference the two target
modules (`sni_class_duplicate_guard.py`, `sni_three_clock_guard.py`).
No mutants were excluded under the QF rule.

## What this does NOT prove

Mutation score is a test-strength proxy, not a statistical validity
claim. A 0.895 mutation score says the suite catches most AST-shaped
perturbations of these two modules under the chosen operator set and
seed; it does not say the underlying refusal contract is correct on
adversarial inputs, that the FAMILY TEXT RULE v2 is fully exercised,
or that a different operator set (e.g. statement deletion, identifier
renaming, type widening) would not surface fresh survivors. No
acceptance row moves to DONE on the strength of this sweep alone.

## Two sample re-verified survivor kills

Seat re-verification (2026-10-14, independent of the lane harness): the
`_pair_shape_ok` L155 and `_as_date` L202 `or`→`and` mutants were
re-applied to the module bytes; each named killing test failed on the
mutant and passed on the restored original.

1. **M8A three_clock #5** —
   `sni_three_clock_guard.py:242 col 8-26`,
   `return (None, False)` -> `return None`.
   Killing test:
   `tests/test_sni_mut8_a.py::test_m8a_three_clock__coerce_field_value_return_none_l242`.
   Against the mutant, pytest reports
   `FAILED tests/test_sni_mut8_a.py::test_m8a_three_clock__coerce_field_value_return_none_l242 - TypeError: cannot unpack non-iterable NoneType object`.

2. **M8A class_duplicate #5** —
   `sni_class_duplicate_guard.py:155 col 11-50`,
   `not isinstance(sid, str) or _blank(sid)` ->
   `not isinstance(sid, str) and _blank(sid)`.
   Killing test:
   `tests/test_sni_mut8_a.py::test_m8a_class_duplicate__pair_shape_ok_boolop_l155`.
   Against the mutant, pytest reports
   `FAILED tests/test_sni_mut8_a.py::test_m8a_class_duplicate__pair_shape_ok_boolop_l155 - assert False is True`.
