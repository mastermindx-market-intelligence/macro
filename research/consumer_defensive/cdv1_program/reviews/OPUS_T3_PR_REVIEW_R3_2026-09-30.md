# Opus review — CDV-1 Task 3, PR #8232, third review, 2026-09-30

- **Artifact:** PR #8232, head `38e4e71bc02c0230a1b732629736cfb30157dc98`, branch `claude/cdv1-t3-economic-interpretation`. The head is the round-5 lane's work through `f4a167ff` (`packets/CDV1_T3_R5_PACKET_2026-09-30.md`) plus the seat commit R5a (`reviews/SEAT_RULING_T3_R5A_2026-09-30.md`).
- **Reviewer:** an independent, read-only Opus reviewer commissioned by the CDV-1 seat (session `251f88c8`). Its scope was bounded to rulings R5.1–R5.7, the R5a commit, and the findings of the second review.
- **Verdict:** **REJECT.** Seven blocking findings.
- **Recorded by:** the seat, from the reviewer's return. Each finding carried a reproducer or a surviving mutation. The seat confirmed all seven: F1–F4 fail in the round-6 suite when it runs against the rejected module, and the F5–F7 mutations survive the rejected suite.

## Mechanical baseline (seat harness, same head)

Every mechanical check passed:
- file grants, and an empty Task 1 freeze diff;
- the suite (225 passed) and the dossier job's exact `run:` line;
- `tests/test_ci_pack.py`;
- contract-delta;
- pyflakes;
- `git merge-tree` against main.

The seat's probes passed 306 of 306 round-5 checks and 155 of 155 round-4 checks. The 23 packet mutants and the 7 seat mutants were all killed. CI on this head concluded green.

None of that found what the reviewer found. The probes and the mutants check the rulings one case at a time. The findings below are values and mutations no case named.

## Blocking findings

The bar letters are the review standard's: (a) behaviour against a ruling, (b) a test that cannot fail, (c) a contract breach the round was commissioned to close, (e) an exception other than the typed one leaving a public function.

| # | Bar | Finding | Evidence |
|---|---|---|---|
| F1 | a, c | R5.7 (1), the mixed case. When the current EPS side is not selected and the prior side is selected and typed-absent, the declined comparison reports `not_selected` with no detail. R5.7 (1) requires Task 1's reason and detail whenever a side is selected and typed-absent. | A build with that selection. A mutant that reads the prior side first passes all 225 tests. |
| F2 | e | `compare_eps` lets `decimal.Overflow` escape when the prior value and the uncertainty have extreme exponents. The interval test subtracts them. | A direct `compare_eps` call. |
| F3 | e, c | A selected handle whose `fact_id` or `metric` is unhashable escapes as `TypeError`. | A build with a list as `fact_id`. |
| F4 | e | A `workspace["lifecycle"]` that is not a mapping escapes as `AttributeError`. | A build with a list as `lifecycle`. |
| F5 | b | `test_spec_strings_are_exact` never checks the segment labels against `segment_scope` (R5.6). | Both labels replaced with the constant `"Segment"`: 225 passed. |
| F6 | b | The probe named for a five-entry fiscal scope does not pass five entries. | The length test changed to `len(value) < 4`: 225 passed. |
| F7 | b | `test_currentness_state_is_a_closed_exact_string` cannot fail for a `str` subclass. | `_parse_token` rewritten without the type test, as a guarded membership test: 225 passed. |

## Non-blocking notes

1. The clock-rules test has no positive control, so its refusals could all come from one earlier rule.
2. `clocks.correction` is copied from `lifecycle.state` without a type test.
3. `_parse_decimal` accepts non-ASCII digits and surrounding whitespace, because `Decimal` does.
4. `facts: []` builds a payload with no observations, and that payload cannot be validated.
5. `_decimal` and `_definitions()` are thin leftovers.
6. One test takes the set of fixed metrics from the build it checks.

## Seat adjudication

All seven findings are upheld.

F2, F3 and F4 are three instances of one class: an untyped exception leaving a public function. Note 4 is an instance of a second class: a value the build accepts that validation then cannot replay. The second review found the same first class in round 4, and round 5 was commissioned to close it with one parsing boundary. Round 5 closed it for the scalars it named and left it open for every value it did not name.

This is the third round in which that class survived. Under the operating brief, the correction is a bounded design change, not three more special cases. The seat makes it directly. The rulings, the properties the change is held to, and the evidence are in `reviews/SEAT_RULING_T3_R6_2026-09-30.md`.

F1 is fixed as R5.7 (1) reads. F5, F6 and F7 are fixed in the suite, and each reviewer mutation is now a seat mutant that must be killed. Notes 1, 2, 4 and 6 are fixed in the same commit. Notes 3 and 5 are not carried, and the R6 ruling says why.
