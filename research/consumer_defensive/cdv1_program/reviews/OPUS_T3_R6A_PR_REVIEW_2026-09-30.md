# Opus review — CDV-1 Task 3 follow-up R6a, PR #8246, 2026-09-30

- **Artifact:** PR #8246, head `20b2facd1e03ee9b3c1b2beee18fe65cffc42e60`, branch `claude/cdv1-t3-r6a-followup`, merge base `9f7cb27a8d65`.
  - It implements rulings R6a.1–R6a.7 (`packets/CDV1_T3_R6A_PACKET_2026-09-30.md`) on top of merged Task 3 (`ddf03116`).
  - The diff touches exactly two files: `engine/earnings_narrative/economic_interpretation.py` and `tests/test_earnings_economic_interpretation.py`.
- **Reviewer:** an independent, read-only Opus reviewer commissioned by the CDV-1 seat (session `251f88c8`).
  - It was bounded to R6a.1–R6a.7, to the release-blocking bar, and to eight probes of its own.
  - Two things were left to CI: the dossier job line and the contract delta.
- **Verdict:** **ACCEPT.** No blocking finding. All of R6a.1–R6a.7 are met.
- **Recorded by:** the seat, from the reviewer's return. The seat wrote the rulings, so this verdict is the acceptance the seat could not give itself.

## What the reviewer re-ran

These runs were on the head, in the dossier job's CI venv (CPython 3.12.13), under `ulimit -s hard`.

- **The suite:** `427 passed in 28.58s`.
- **EPS oracle.** The oracle is exact `Fraction` arithmetic with half-even rounding, written independently of the module.
  - Default context: 3,500 pairs (1,500 random, 1,500 near-tie, 500 negative-rate-to-zero). Mismatches: **0**.
  - Hostile ambient contexts: 4,375 runs (low precision, non-default rounding, cleared traps). Mismatches: **0**.
  - Positive control, the merge-base module under the same sweep: 388 mismatches out of 3,259 runs. The oracle does detect the defect R6a.6 fixes.
  - Hostile arguments: no exception other than `EconomicInterpretationError` escaped the module (**0**).
- **Clocks.** `_format_instant` and `_format_date` were compared against `main`'s `strftime` output over 20,004 valid instants (years 1000–9999). Mismatches: **0**.
- **R6a.5 floors.** Measured on a copy with a temporary print: **77** and **39**, the same at the head and at the merge base. The lane's deviation from the packet's 55 and 35 is correct: the ruling says to raise the floors to the count actually present, and 77 and 39 are those counts.

## Mutants the reviewer ran itself

| Id | Change | Result |
|---|---|---|
| m3 | line 940: the replay compare as `json.dumps(...)` without `sort_keys` (a true order-sensitive compare) | **KILLED** by `test_validate_ignores_nested_key_order_but_requires_exact_top_level_order` (1 failed, 426 passed) |
| m6 | the work context's precision set to 28 | **KILLED** by the two pinned double-rounding and guard-digit tests |
| m7 | quantize under the work context instead of the result context | **KILLED** by `test_compare_eps_arithmetic_stays_guarded[1.64-1.52]` and `test_compare_eps_still_refuses_a_result_with_too_many_digits` |
| m8 | drop the `:04d` from `_format_instant`'s year | **KILLED** by `test_clock_helpers_format_short_years_with_zero_padding` and `test_parsers_accept_short_years_but_keep_the_canonical_forms` |
| mz | line 468: `_json_number(abs(rounded) if rounded == 0 else rounded)` | **SURVIVES** (427 passed); see note 1 |

The lane reported m3 as surviving. Both the seat and the reviewer showed that the true order-sensitive mutant is killed. The lane's report is corrected in `SEAT_RULING_T3_R6A_2026-09-30.md`.

## Notes (non-blocking)

1. **The fuzz oracle cannot produce `-0.00`** (test file lines 1412–1414, `_exact_eps_value`).
   - For example, `('0.99999', '1', 2)` gives `0.00` from the oracle and `-0.00` from the module.
   - The module's value is the one R6a specifies, so no wrong value is shipped. But mutant mz, which normalises the negative zero away, is not killed.
   - The fix is test-only: the oracle emits `-0.` when the exact rate is negative, plus one literal case. It does not change `CODE_REVISION`.
2. The fuzz sweep does not kill m6 on its own; the literal pinned tests do.
3. `_EPS_RESULT_CONTEXT.plus` and `quantize` set flags on the shared module-level context. This is flag noise only: no result or error depends on the flags.
4. For R6a.2, the subclass and opaque kinds are reported as `'wrong'`, which is acceptable under the ruling.
5. The forms `_parse_date` refuses are not pinned by a test. This is unchanged from `main`.
6. Nit: three blank lines after `_format_date` (lines 229–230).

## Gaps the reviewer stated

- Mutants m1, m2, m4, m5 and m9 were not re-run.
- Zero-padding on Linux was not exercised on this host (m9 can only fail there).
- The dossier job line and the contract delta were left to CI.
