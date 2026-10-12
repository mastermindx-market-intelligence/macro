# CDV-1 Task 2 — independent review of PR #8234, round 5 (second PR review)

- **Date:** 2026-09-30
- **Reviewer:** independent read-only Opus reviewer (adversarial review lane), commissioned by the CDV-1 seat
- **Artifact:** PR #8234, head `113323df10cb9e315c02106bf5ffdf42e1fbfbfa` (round-5 seat commit `09621cc5e527` merged with main at `c7e1f8edd8e5`)
- **Status returned:** PARTIAL
- **Verdict:** **REJECT** — one blocking finding (B1)
- **Filed by:** the seat, from the reviewer's returned packet. The seat reproduced B1 on the pushed head with the
  reviewer's own script before acting on it (see "Seat reproduction" at the end).

## Blocking finding

### B1 — one transient 503 makes an older filing supersede a newer one and destroys the newer filing's first observation

Bar (e) of the commission: a result that is wrong for a well-formed acquisition.

**What happens.** The traced acquisition falls back to the older filing when the newest exhibit answers 503, and
stamps the result `newer_source_pending`. `prepare_pg_workspace` then takes that older acquisition with the stored
newer result as `prior`. The period is the same and the accession differs, so R5.13's "otherwise" branch makes the
older filing the next revision, superseding the newer one. The next night the newer filing returns as a third
revision with a new first observation.

**Why it is wrong.** The filing set never changed, yet the chain grows by two revisions, the 07-29 8-K is recorded
as superseding the 07-30 8-K/A, and the 8-K/A's `fetched_at` moves from 07-31 to 08-02. Plan 2.4 says an unchanged
source carries its first observation.

**Corrected-text variant.** When the newer filing corrected the text, the fallback night yields revision 3 in state
`corrected` that carries the stale, uncorrected text.

**Status against the rulings.** The code matches R5.11 and R5.13 as written, so this is a finding against the
ruling. R5.14 orders only fiscal periods; nothing orders acceptance within a period. The case is not in the
ruling's known limits or in the Task 4 handoff list. It likely predates round 5, but it makes a result wrong for a
well-formed acquisition returned by this PR's own acquisition path.

**Repair options offered.**

1. Add a row: same period, different accession, acquisition acceptance earlier than the predecessor's
   `lifecycle.source_available_at` refuses, for example with `source_precedes_prior_event`.
2. Rule it a Task 4 obligation and record it in the known limits and the handoff list.

Either way the suite's `back_to_first` scenario needs revisiting: it prepares the older-accepted accession on top
of the newer one and is currently asserted as correct.

**Reproducer** (fixture transport only; `$A` is the reviewer's scratch directory):
`PYTHONDONTWRITEBYTECODE=1 <venv>/python -u $A/p6_fallback.py`

| Night | Transport | Selected | Result |
|---|---|---|---|
| 1 | all 200 | …007 8-K/A, accepted 2026-07-30T18:00:00Z, `up_to_date` | revision 1, doc …a3aa2f, supersedes None, `release_amendment`, `fetched_at` 2026-07-31T02:00:00Z, `complete` |
| 2 | the 8-K/A exhibit is 503 | …001 8-K, accepted 2026-07-29T17:10:00Z, `newer_source_pending` | revision 2, doc …b6154a, supersedes …a3aa2f, `release`, `fetched_at` 2026-08-01T02:00:00Z, `complete` |
| 3 | all 200 | …007 8-K/A | revision 3, doc …a3aa2f, supersedes …b6154a, `fetched_at` 2026-08-02T02:00:00Z, `complete` |

Control: night 3 had night 2 not happened is revision 1 with `fetched_at` 2026-07-31T02:00:00Z, equal to night 1.

Corrected-text variant: corrected filing revision 2 (accession …002, state `corrected`, text has `$3.17`,
`up_to_date`); the fallback night is revision 3 (accession …001, supersedes …d0f3ae, `available_at`
2026-07-29T17:10:00Z, state `corrected`, text does not have `$3.17`, `newer_source_pending`).

## Non-blocking notes

- **N1.** On Python 3.11.10 a body containing `<![1 x]>` makes `AssertionError` leave `prepare_pg_workspace`
  (`html.parser` raises it and the backstop does not list it). It does not reproduce on 3.12.13, which CI and the
  nightly use. Reproducer: `PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.11 -u $A/p2b_311.py`.
- **N2.** R5.12's rationale "the cycle cannot collide here" fails when run clocks are equal (row 28 permits it):
  A→B→A→B at one `observed_at` gives step 4 the same workspace and `generation_id` as step 2 with a different
  `document_metadata` (revision 4 against 2). The content address is still truthful and P2 and P5 hold. **Task 4
  must not key chain position on the generation id.**
- **N3.** Surviving mutants (test gaps; the whole suite stays at 341 passed):
  - `rights_state="internal_only"` → `"licensed"` (the private rights state is unpinned);
  - `asof=acceptance_clock.date()` → `observed_clock.date()`;
  - row 28 restricted to the same accession (no test runs a refiling or an amendment with a run clock before the
    predecessor's observation);
  - `_TOKEN_RE` `{1,128}` → `{1,127}` (the upper boundary's admission is untested).
  Three further mutants are equivalent: the `OverflowError` catch, `!= "8-K"`, and `source_available_at` read back
  from the workspace.
- **N4.** `moved_url` (same text and accession, another URL) yields revision 2 whose `fetched_at` equals the
  root's. It is ruled and tested, and the native chain admits it.
- **N5.** The job line is `if: ${{ false }}` in `legacy-jobs.yml` (the legacy-jobs convention). The reviewer did not
  verify that the pack runner executes it.

## Evidence the reviewer recorded

- Head `113323df…` and a clean status before and after.
- `git diff --stat b973d9316304 09621cc5e527` on the other three owned files: empty.
  `git diff --stat 09621cc5e527 HEAD`: only `.github/ci/legacy-jobs.yml`, +5 −1.
  `git diff --stat c7e1f8edd8e5 HEAD`: six files, all owned. The frozen Task 1 files: empty diff.
  `pg_profile.py` and the fixtures file remove 0 lines (appended hunks `@@ -2194,3 +2194,449` and
  `@@ -201,3 +201,177`). No line inside `earnings-economic-dossier` changed. The job's 38 paths include the six
  owned files and the import closure.
- Suite: `341 passed in 68.13s`.
- Rulings R5.1–R5.8, R5.10–R5.12, R5.14 and R4.2a: met. R5.5, R5.11, R5.12: met as written. R5.13: met as written,
  with the ruling gap above (B1).
- Own probes:
  - acquisition and `observed_at` sweep: 1,162 calls, 0 escapes;
  - 48 solo mutations each returned the tabled reason and detail; 1,096 pairs gave 7 disagreements, all artifacts
    of the reviewer's own mutations;
  - all 19 prior rows returned the tabled reason and detail, solo and in pairs;
  - transport sweep: 24,597 answers — 18,557 `RefreshError`, 6,040 acquisitions, 0 other exceptions (conversions:
    1,560 `AttributeError`, 561 `ValueError`, 30 `RecursionError`);
  - all 6,040 returned acquisitions were prepared (4,742) or refused typed (1,298); every one of the 4,742
    re-prepared with its own result at a later clock was equal in all five parts;
  - 19 hostile HTML bodies all returned on 3.12.13.
- Chain probe, eight steps: root A (revision 1); the same A again (identical); changed text under the same
  accession (revision 2, `corrected`); text returns to A (revision 3, A's id repeats); unchanged text refiled under
  a new accession (revision 4); 8-K/A with the same text (revision 5, `release_amendment`); the same 8-K/A again
  (identical); an older accession on top of the 8-K/A (revision 6 — the B1 pattern). The native
  `DocumentRevisionChain` admits all six revisions. The next quarter on top gives revision 1, equal to the
  `prior=None` result. An earlier quarter on top of the later one is refused
  `source_precedes_prior_event` / `prior.workspace.fiscal_period`.
- Mutations killed by the sweep tests alone: K1 (`pg_profile.py:2275-2278`, the key-type loop removed), K2
  (`:2336`), K3 (`:2282`), K4 (`:2568`, the `_aliases` pop removed), K5 (`:2419`), K6 (the backstop without
  `AttributeError`), K7 (`:2369`).

## Gaps the reviewer stated

- Its prior-position hostile sweep (`p4_sweep.py`) did not finish.
- It did not re-run the seat's 94 mutants, the seat's sweeps or `tests/test_ci_pack.py`, and did not read the r3
  and r4 packets line by line.
- The `legacy-jobs.yml` merge hunks and hosted CI were not examined.
- The 29 February limit was exercised only with a March quarter-end.

## Deviations the reviewer stated

- Ran Python 3.11.10 once, for N1.
- Its transport wrapper turned the fixture's `AssertionError` for an unmapped URL into `RefreshError`.
- Mutants ran in a scratch copy under `$A/mut` with `MM_DATA_GUARD=off`.
- Nothing was written in the worktree, the seat's scratch or the records directory. No network.

## Seat reproduction

The seat ran the reviewer's `p6_fallback.py` unchanged against the pushed head `113323df10cb` and saw the three
nights exactly as tabled above (revision 1, then 2 superseding …a3aa2f, then 3 with `fetched_at`
2026-08-02T02:00:00Z). B1 is real. The seat's disposition is `SEAT_RULING_T2_R6_2026-09-30.md`: repair option 1,
stated as one ordering rule (R6.1) rather than a case keyed on the accession or the stamp; N2 and N1 are recorded;
the four N3 gaps are pinned.
