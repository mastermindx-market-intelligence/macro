# CDV-1 Task 2 — independent review of PR #8234, round 6 (third PR review)

- **Date:** 2026-09-30
- **Reviewer:** independent read-only Opus reviewer (adversarial review lane), commissioned by the CDV-1 seat
- **Artifact:** PR #8234, head `5f33a5a26635a9e565f93f4639f629b20d086937` (repair commit `e814285adcbb`, pin commit
  `19912e5dccd0`, merged with main at `8744b8c1a0af`)
- **Status returned:** PASS
- **Verdict:** **ACCEPT** — no blocking finding
- **Filed by:** the seat, from the reviewer's returned packet. The seat's disposition of the notes is at the end.

## Verdict against the review standard

B1 and its corrected-text variant no longer reproduce, the code matches ruling R6, and the new tests are not vacuous.

- **(a) The B1 class.** Not reproducible. The three-night run, the reversed order, the corrected-text variant and
  2,500 randomized seven-night trials produced no older-over-newer step, no lost first observation and no chain
  growth on an unchanged filing set.
- **(b) Wrongly refused or stranded.** None found. An in-place correction, an amendment, a refiling at an equal clock,
  an unchanged re-run and a new fiscal period are all admitted. After a refusal, the kept prior admits the returning
  newest filing, a later filing and a next-period filing.
- **(c) Wrong result.** None outside the stated known limits.
- **(d) Exception escape.** None. 21 hostile values at `lifecycle.source_available_at`, a 330-cell grid and the
  simulation raised only `PgPreparationRefused` (or `RefreshError` from the acquisition) on CPython 3.12.13.
- **(e) Code against R6.** Matches. Row 7a is at `engine/company_intelligence/pg_profile.py:2418-2420`, after the
  `observed_at` check and before the state check, and runs for every prior. Row 26a is at `:2538-2541`, inside the
  same-period branch, after row 26 (`:2533-2534`) and before row 27, with strict `<`. Reason, detail and the message
  at `:2241` are as ruled. The merge of main changed none of the PR's files.
- **(f) The suite.** 12 of 12 mutants of rows 7a and 26a are killed; the control passes 359. Removing row 26a fails
  `test_an_older_filing_never_supersedes_a_newer_one`. The rebuilt `back_to_first` still pins the repeated first
  document id at revision 3 under one accession. The rebuilt `refiled_after_correction` pins revision 3 and state
  `corrected` under another accession at an equal clock.

## Non-blocking notes

- **N1. Same accession and text with a later acceptance clock is admitted as carried.** The acceptance moved from
  17:00 to 18:00, within the prior's first observation. Revision and document id stay the same, but the workspace
  source clock and generation id move. R6 classes this as malformed input; SEC does not re-accept an accession.
  Task 4 could hold it.
- **N2. A forged prior whose source clock is later than its own `observed_at` is not called `malformed_prior`.** It
  refuses every same-period acquisition older than that clock with `source_precedes_prior_event`. The preparation
  cannot produce such a prior: all 169 returned grid results had source clock equal to acceptance, equal to the
  document's `available_at`, and not after `observed_at`. The chain still advances on a later filing or a new period.
- **N3. Pinning an older accession on a stored newer filing is refused by row 26a.**
  `acquire_results_filing(accession=<older>)` hits the same rule. This is consistent with the "withdrawn newest
  filing" limit, but an operator backfill through the pin will meet it.
- **N4. The equal-clock fallback is admitted.** Old text under another accession at the prior's exact clock becomes
  revision 3 on the corrected revision 2. This is exactly the recorded same-second limit, nothing beyond it.
- **N5. The ruling's Verification section was still marked INTERIM.** It quoted 358 passed on a scratch tree; the head
  measures 359, the extra one being the test added in `19912e5dccd0`. The record should be updated before it is
  cited.

## Evidence the reviewer recorded

`A` is the reviewer's scratch directory. Python is 3.12.13 from the Task 2 CI venv.

**Suite on the head** (run from the worktree):
`PYTHONDONTWRITEBYTECODE=1 perl -e 'alarm shift; exec @ARGV' 300 python -m pytest tests/test_pg_economic_source_selection.py -q -p no:cacheprovider --basetemp A/bt`
→ `359 passed in 65.70s`

**B1, three nights through the traced acquisition** (`A/q1_b1.py`):

- Night 1 selects …007, 8-K/A, `up_to_date` → revision 1, document `42a3aa2f`, observed 2026-07-31T02:00:00Z.
- Night 2 (the 8-K/A exhibit answers 503) selects …001, `newer_source_pending` →
  `('REFUSED', 'source_precedes_prior_event', 'prior.workspace.lifecycle.source_available_at')`.
- Night 3 selects …007 on the kept prior → revision 1, same document, observed 2026-07-31T02:00:00Z; workspace and
  document metadata equal night 1.
- Reversed order (503 on the first night, no prior): …001 is revision 1; …007 is revision 2; the next 503 night is
  refused; …007 again equals the stored revision 2.

**Corrected-text variant** (same script): original …001 → revision 1; corrected …002 → revision 2, `corrected`; the
fallback night with the stale …001 text → refused, same reason and detail; …002 again → identical to the stored
revision 2.

**Fallback attacks** (same script):

| Attack | Outcome |
|---|---|
| No prior | Revision 1 (a root) |
| Equal acceptance clock, other accession | Admitted as revision 3 (N4) |
| One second earlier | Refused by row 26a |
| Prior in FY27 Q1, fallback to a Q4 filing | Refused `source_precedes_prior_event` / `prior.workspace.fiscal_period` (row 26) |
| Prior accepted 10-01T00:00:00Z, acquisition accepted 09-30T23:59:59Z | Refused by row 26 |
| The reverse of the above | New-period root, revision 1 |
| In-place correction of the newer filing | Revision 3 |
| Fallback to the older filing on top of that | Refused by row 26a |
| Original text back under the same accession | Revision 4 |
| Unchanged re-run | Equal to the stored result |
| Same accession, earlier clock | Refused by row 26a |
| Same accession, clock later than the prior's first observation | `malformed_prior` / `prior.workspace.lifecycle.observed_at` |

**Prior source-clock attacks** (`A/q4_prior.py`):

- Absent, `None`, empty, offset form, date only, fractional seconds, lowercase `z`, Feb 30, year 0000, hour 24,
  second 60, trailing newline, full-width digits, int, bytes, str subclass, an object with raising dunders, a
  `datetime`, a list: all → `malformed_prior` / `prior.workspace.lifecycle.source_available_at`, for both an unchanged
  re-run and an amendment.
- `9999-12-31T23:59:59Z` → refused by row 26a. `0001-01-01T00:00:00Z` → admitted.
- Forged prior with source clock 2026-08-15 and `observed_at` 2026-07-29: re-run, in-place correction and the 07-30
  amendment are refused by row 26a; a filing at exactly 08-15T00:00:00Z is revision 2; a filing on 08-20 is
  revision 2; a next-period filing is revision 1.
- Grid of 6 priors × 5 acquisitions × 11 acceptance clocks (330 calls): 136 row-26a refusals, 169 returned, 25
  `malformed_prior` / `observed_at`. Row 26a fired exactly when acceptance was earlier than the prior's source clock,
  with 0 mismatches; every returned result was a fixed point on re-run; 0 escapes.
- Advance after refusal: on the kept amendment prior, a later filing (08-02) is revision 3 and a next-period filing
  is revision 1.
- Pinned `accession=older`: selected …001 `newer_source_pending` → refused by row 26a.

**Randomized nights** (`A/q5_sim2.py`): five fixture transports, 500 trials each, seven nights with random
503/404/500/429/empty-200 on 35% of URLs, then two clean nights →
`{'acq_refused': 11669, 'stored': 10234, 'trials': 2500, 'prep_refused:source_precedes_prior_event/prior.workspace.lifecycle.source_available_at': 597}`
and `VIOLATIONS: 0`. Invariants checked: the source clock never steps back; one document id never sits at two
positions; the first observation never moves; a clean night is always admitted; revision equals the count of distinct
documents; at most two documents.

**Mutants** (`A/mutrun6.py`, output in `A/mut6.out`), on a scratch copy of the previous reviewer's export plus the two
head files; six dependency files were checked byte-identical to the head:

| Mutant | Result |
|---|---|
| Control | 359 passed |
| `<` changed to `<=` | 4 failed, 179 errors |
| Row 26a removed | 5 failed, including `test_an_older_filing_never_supersedes_a_newer_one` |
| Row 26a reading the prior's first observation instead of its source clock | killed by `test_the_source_order_reads_the_source_clock_and_not_the_first_observation` |
| Row 7a tolerating an absent clock | 9 failed |
| Row 7a moved after the state check | 1 failed (order table) |
| Row 26a applied to any period | 2 failed |
| Detail changed to the period detail | 4 failed |
| Only when the accession differs | 3 failed |
| Only when currentness is pending | 5 failed |
| Row 26a moved after row 27 | 1 failed |
| Only when the text differs | 4 failed |
| Date-granularity comparison | 2 failed |

**Worktree:** `git status --short | wc -l` → 0; HEAD is `5f33a5a26635…`.

## Gaps the reviewer stated

- Python 3.11 was not exercised (recorded limit).
- Hosted CI on the round-6 head was not read.
- The seat's 113-mutant set, the integration check with Task 3 and RED at the merge base were not re-run.
- The mutation base is the round-5 export plus the two head files, not a full export of the merged head.
- Period-boundary attacks used synthetic `_quarter` acquisitions, not a traced transport; no fixture spans two periods.
- A 200 response carrying a wrong body under the same accession (an in-place alternation that grows the chain) was not
  attacked. It falls under round 5's accepted in-place rule and is outside R6.

## Deviations the reviewer stated

- The first mutation run failed because a control entry named `BASE` collided with `base` on the case-insensitive
  volume and deleted the reviewer's own scratch base. It was rebuilt from the previous reviewer's export, which was
  only read, and rerun. Nothing outside the reviewer's scratch directory was written.
- A first simulation (`A/q3_sim.py`) reported 381 "violations" that were harness artifacts: it compared the
  run-dependent `currentness_context`, mixed fixtures whose …001 metadata differ, and counted a no-prior fallback
  root as excess. `A/q5_sim2.py` replaces it with corrected invariants; none of the 381 was a product defect.
- About 17 tool turns were used of the 24 allowed.

## Seat disposition of the notes

- **N1** goes to Task 4. The stored chain of an event must be a prefix of the candidate's chain, entry for entry. A
  candidate whose entry at an existing revision names another workspace is refused at publication, so a re-accepted
  accession cannot replace a stored revision.
- **N2** goes to Task 4, which owns the integrity of a stored prior. Its closure validation requires
  `source_available_at <= observed_at` for every stored workspace, so the forged prior cannot be read back as a prior.
- **N3** and **N4** are the two limits already recorded in `SEAT_RULING_T2_R6_2026-09-30.md` ("a withdrawn newest
  filing" and "same-second filings"). No change.
- **N5** is done: the ruling's Verification section now carries the numbers measured on the head.
