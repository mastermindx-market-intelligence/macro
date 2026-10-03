# Seat ruling — CDV-1 Task 3 follow-up R6a: acceptance and merge, 2026-09-30

Seat: CDV-1 Meta-CEO, session `251f88c8`.

This record covers three things for PR #8246, the bounded follow-up that the fourth Task 3 review left owed (`reviews/OPUS_T3_PR_REVIEW_R4_2026-09-30.md`, notes 1–8):
- the seat's verification of the lane's return;
- the independent review (`reviews/OPUS_T3_R6A_PR_REVIEW_2026-09-30.md`: ACCEPT);
- the merge.

It changes no grant, no placement and no Task 1 freeze.

## Dispatch and return

- **Packet:** `packets/CDV1_T3_R6A_PACKET_2026-09-30.md`, rulings R6a.1–R6a.7. It is byte-identical to the packet the lane received.
- **Lane:** `cdv1_t3_r6a_followup`, on a new branch `claude/cdv1-t3-r6a-followup` from `origin/main`. It returned head `20b2facd1e03ee9b3c1b2beee18fe65cffc42e60`.
- **Grants:** the diff against the merge base `9f7cb27a8d65` touches exactly the two owned files. The Task 1 freeze is untouched.

## Seat verification (at the head, in the dossier job's CI venv)

- The suite: `427 passed`.
- **RED, 4 failed** against the merge-base module (the lane reported 3). The four are:
  - `test_compare_eps_is_independent_of_the_callers_decimal_context`
  - `test_compare_eps_pins_the_known_default_context_double_rounding`
  - `test_compare_eps_keeps_guard_digits_below_the_result_precision`
  - `test_clock_helpers_format_short_years_with_zero_padding`

  The lane's count missed one. Every R6a behaviour change has at least one test that fails without it.
- The dossier job line: `2742 passed, 174 skipped`.
- `tests/test_ci_pack.py`: `143 passed`.
- contract delta rc 0, pyflakes clean, and the merge tree against `origin/main` is clean.

## Corrections to the lane's report

1. **m3 is killed, not a survivor.**
   - The lane reported that the order-sensitive replay compare "survived".
   - The seat replaced the replay compare `_canonical(stored_payload) != _canonical(rebuilt)` with `json.dumps(stored_payload) != json.dumps(rebuilt)` (no `sort_keys`). `test_validate_ignores_nested_key_order_but_requires_exact_top_level_order` then failed.
   - The reviewer reproduced this independently: 1 failed, 426 passed.
   - The lane's "survivor" was an equivalent mutant, not the order-sensitive one the packet named.
2. **R6a.5 floors are 77 and 39.**
   - The packet's 55 and 35 were wrong; this is a packet erratum.
   - The ruling itself said to raise the floors to the count actually present. The lane measured 77 and 39, and the reviewer measured the same at the head and at the merge base.
   - The lane's deviation is therefore compliance, not a departure.
3. **m9 is not counted.**
   - m9 restores the `strftime` round trip in `_parse_date`, and it can only fail on Linux. It was not exercised on the macOS hosts.
   - The packet said not to count it if it survives here. It stays an open platform note. CI runs the unmutated suite on Linux, which exercises the zero-padding path but not the mutant.

## Erratum to R6.6 (fourth review, note 5)

The description of R6.6 in `reviews/SEAT_RULING_T3_R6_2026-09-30.md` is replaced, as the code already behaves, by:

"The argument is read by iteration until every key is known to be an exact `str`. Only then is it read by lookup. No key that is not an exact `str` is ever hashed or compared."

## Carried follow-up (test-only; not release-blocking)

- **F-R6a-1.** The fuzz oracle `_exact_eps_value` (test file lines 1412–1414) cannot produce `-0.00`. The module correctly returns `-0.00` for, for example, `('0.99999', '1', 2)`.
  - The fix: the oracle emits `-0.` when the exact rate is negative, plus one literal case. That kills the reviewer's surviving mutant mz (`_json_number(abs(rounded) if rounded == 0 else rounded)`).
  - It is a test-only change and does not move `CODE_REVISION`. It rides the next change to that test file; it does not get its own round.
- The reviewer's other notes are recorded, not assigned:
  - the fuzz sweep alone does not kill m6;
  - flag noise on the shared result context;
  - the subclass and opaque kinds reported as `'wrong'`;
  - the forms `_parse_date` refuses are unpinned (unchanged from `main`);
  - a triple blank line.

## Sol's contract notes

The following are not in Task 3's scope:
- the `fiscal_period` text-type policy (n-B1);
- the release-entry metadata-binding question (n-B2).

Sol 5902318060 kept both as recorded contract notes and assigned neither to Task 4. Their status is recorded with the Task 4 ruling.

## Merge

- **CI at the head.** Every check concluded. `ci-pack-10` concluded SUCCESS.
  - The one red was `ci-authority/codex/merge-queue-pilot` ("CI authority context rejected"), the standing red on every PR that edits CI-authority paths. It was named, and it was neither rerun nor worked around.
- **Merge.** The seat checked the carriers (#7792 and #8246) for new rulings or holds, then squash-merged at the exact head with `--match-head-commit 20b2facd…` at 2026-09-30T19:47:29Z, as **`26b0908e2bb760e576d01b9029cd801c0649d234`**.
- **Verified in `main`'s own bytes.** `engine/earnings_narrative/economic_interpretation.py` is blob `52499130a329` and `tests/test_earnings_economic_interpretation.py` is blob `8422f39c5e17`, identical to the accepted head.

## Consequence for Task 4

- The module's bytes changed, so `CODE_REVISION` on `main` changed.
- Every interpretation built before this merge is now a stale derivation under the running code. Task 4 therefore reads stored interpretations through the stale-carry mode of R-B9 (`"stale_ok"`), and Task 5 re-derives them under R5.5.
- The Task 4 branch merges `main` before its own merge.
