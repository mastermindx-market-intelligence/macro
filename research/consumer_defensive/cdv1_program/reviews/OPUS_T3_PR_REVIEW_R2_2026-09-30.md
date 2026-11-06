# Opus review — CDV-1 Task 3, PR #8232, second review, 2026-09-30

- **Artifact:** PR #8232, head `e8666eeda17e7e3e53afe5871ba4a9f64c1fedfc`, branch `claude/cdv1-t3-economic-interpretation`. The head was produced by the r4 packet (`packets/CDV1_T3_R4_PACKET_2026-09-30.md`).
- **Reviewer:** an independent, read-only Opus reviewer commissioned by the CDV-1 seat (session `251f88c8`). Its scope was bounded to r4 rulings R4–R13.
- **Verdict:** **REJECT.** Six blocking findings.
- **Recorded by:** the seat, from the reviewer's return. Every finding was confirmed by a probe the reviewer ran against the head. The seat re-read the code for B1, B3, B4 and B5 before adjudicating.

## Mechanical baseline (seat harness, same head)

Every mechanical check passed again:
- file grants, and an empty Task 1 freeze diff;
- the suite and the dossier job's exact `run:` line;
- `tests/test_ci_pack.py`;
- contract-delta;
- pyflakes;
- `git merge-tree` against main.

The seat's path probe of the head passed 147 checks and failed 8, all on the bridge handles (B5). The seat's mutant runs killed r4 mutants m5, m7 and m10.

## Blocking findings

| # | Ruling | Finding | Evidence |
|---|---|---|---|
| B1 | R4.1, R4.4 | Clocks are checked by regex shape only. Month 13 raises `IndexError`. Month 00 renders EN "Dec" but ZH "0月". `2026-02-31` and second 99 are accepted. `\d` matches non-ASCII digits. A month-13 `lifecycle.source_available_at` crashes the build. A list-valued `state` raises `TypeError`, because the membership test runs before any type check. | Direct build calls. Code: `_currentness`, `_valid_timestamp`, `_clock_text`. |
| B2 | R7 | A stored `selection.currentness_observed_at` with month 13 lets `IndexError` escape the validator. | A validator call on a tampered stored payload. |
| B3 | R5 | `uncertainty` is validated only after the nonpositive-prior branch. `compare_eps("1.64", "0", precision=2, uncertainty=True)` returns `nonpositive_prior` instead of refusing. | Direct `compare_eps` calls. |
| B4 | R6 | The missing-context order, the `observations` order and the identity's `facts` list follow the caller's selection order, not Task 1 row order. The same selected set in two orders yields two payloads and two identities. | Builds with a forward and a reversed selection. |
| B5 | R12 (iii) | The bridge finding carries `input_handles: [None]`, and no test pins it. | Built payloads; `_rules`. |
| B6 | R10 | The `unlocated_outcome` edit changes nothing, for two reasons. `pg_reported_eps_growth_pct` is already typed-absent in the base build, and the edit touches paragraph text, not the header text Task 1 reads. A mutant that returns the base body passes all 34 tests. | Mutant run; base and edited builds. |

## Non-blocking notes

1. The label test pins 3 of the 15 fixed labels, so a mix/FX ZH swap survives. **Carried into r5 as R5.6.**
2. `owner_lookup` tests the metric exception before the group, and `_missing` does not validate the owner. Owners come only from the closed mapping, so this is not carried.
3. `compare_eps(precision=40)` lets `decimal.InvalidOperation` escape. This predates r4. **Carried as part of R5.2.**
4. A declined comparison for a pair the caller did not select invents the reason `no_span_addressable_evidence`. This predates r4. **Carried as R5.7 (1).**
5. The unavailable payload's missing item has no `owner`, which breaks R4.5. **Carried as R5.7 (2).**

## Seat adjudication

All six findings are upheld. This is the second round in which one defect class survived: a value used before it is known to be the right type and range, or behavior written case by case. Under the operating brief, the correction is a bounded design change, not another literal case:
- one parsing boundary, with typed values downstream (R5.1, R5.2);
- one canonical order (R5.3);
- one fired set (R5.4);
- one differential rule for fixtures (R5.5).

The fix round is `packets/CDV1_T3_R5_PACKET_2026-09-30.md`. The rulings are recorded in `reviews/SEAT_RULING_T3_R5_2026-09-30.md`.
