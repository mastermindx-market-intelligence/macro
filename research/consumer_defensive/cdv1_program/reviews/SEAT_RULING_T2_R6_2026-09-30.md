# CDV-1 Task 2 — seat ruling R6 (PR #8234, round 6)

- **Date:** 2026-09-30
- **Reviewed head:** `113323df10cb9e315c02106bf5ffdf42e1fbfbfa` (round 5). Its hosted CI concluded green, and the
  independent review returned REJECT on one blocking finding, B1 (`OPUS_T2_PR_REVIEW_R2_2026-09-30.md`).
- **Scope of this round:** B1, the four test gaps of N3, and the wording N2 falsified. Nothing else changes.

## What was wrong

A transient 503 on the newest exhibit makes the acquisition return the older filing, stamped
`newer_source_pending`. Round 5 then made that older filing the next revision on top of the stored newer one, and
the newer filing came back the next night as a third revision with a new first observation. The filing set never
changed. The code matched R5.11 and R5.13 as written, so the gap was in the seat's ruling: R5.14 ordered fiscal
periods and nothing ordered source time inside one period. The seat reproduced B1 on the pushed head with the
reviewer's script before acting.

## R6.1 — inside one fiscal period the source clock never steps back

When the prior belongs to the acquisition's fiscal period and the acquisition's acceptance clock is strictly
earlier than the prior workspace's `lifecycle.source_available_at`, the preparation refuses
`source_precedes_prior_event` with detail `prior.workspace.lifecycle.source_available_at`. An equal clock proceeds
as before. The rule reads only the two clocks. It does not look at the accession, the text or the currentness
stamp, so it is one ordering rule and not a case for the 503 fallback.

The caller's duty is the one the reason already carried for a later-period prior (row 26): keep the last good
record and mark currentness pending. The two details tell the cases apart.

Two rows implement it:

- **Row 7a of the prior read (R5.4, between rows 7 and 8).** `lifecycle["source_available_at"]` must be a canonical
  clock, else `malformed_prior` / `prior.workspace.lifecycle.source_available_at`. It is read for every prior,
  whatever its period.
- **Row 26a of the admission order (R5.2, between rows 26 and 27).** The refusal above.

The message for the reason becomes "acquisition is older than the source of the prior workspace", which is true for
rows 26 and 26a.

## What R6 amends in R5

- **R5.13.** "Otherwise the revision is the predecessor's plus 1" now applies only when row 26a did not refuse. A
  text that returns to an earlier version still repeats the first document id, but only under one accession or a
  non-decreasing acceptance clock.
- **R5.14.** A same-period prior is the predecessor unless the acquisition is older than the prior's source.
- **R5.12, rationale (N2).** The sentence "the cycle A → B → A cannot collide here" is withdrawn. When run clocks are
  equal, a generation id can repeat along a chain (A, A′, A, A′ gives step 4 the workspace and generation id of
  step 2 at revision 4). The content address stays truthful. The suite now shows the repeat in a test.

## Why one rule is enough

- A fallback across a period boundary is already refused by row 26.
- A late amendment of an earlier quarter is already refused by row 24.
- The same accession with a different acceptance clock is a malformed input, not this class.
- A fallback with no stored prior is a root, which is correct: nothing newer was ever stored.

## Known limits (replaces the opening sentence of R5's list; the nine R5 bullets stand)

The first two limits below can produce a chain that a reader would call wrong, so R5's opening sentence ("none of
these produces a wrong result for a well-formed acquisition") is withdrawn.

- **Same-second filings.** Two different filings of one period accepted in the same second are not ordered; each is
  admitted on top of the other. The seat declined a tie-break by accession because it can disagree with the
  acquisition's own order and strand the chain. Results filings of one period are hours or days apart.
- **A withdrawn newest filing.** An older filing cannot replace a stored newer one. That needs an owner act at the
  publication seam (Task 4).
- **Python version (N1).** The guarantee that only `PgPreparationRefused` leaves the preparation is stated for
  CPython 3.12, which CI and production run. On 3.11 one hostile HTML body lets `AssertionError` through. The
  backstop tuple is not widened.

## Disposition of the notes

- N1: declined, recorded above. N2: recorded above and tested. N4: no change. N5: no change (the legacy-jobs
  convention; hosted CI ran the job on `113323df` and it passed).
- N3: four pins added — the stored document's private rights stamp; `asof` is the acceptance date; row 28 binds the
  run clock for a refiling and an amendment; a token of 128 characters is admitted and one of 129 is not.

## The suite

Two round-5 scenarios were themselves instances of B1 and were asserted as correct. They are rebuilt so the
acceptance clock never decreases along any path, keeping what they pinned: `changed_in_place` then `back_to_first`
(one accession, the text returns, the first document id repeats at revision 3) and `refiled_after_correction` (the
correction refiled under a later accession). Four tests are new: an older filing never supersedes a newer one
(three nights through the traced acquisition), the source order reads the source clock and not the first
observation, a generation id can repeat and the revision cannot, and the token boundary. Rows 7a and 26a join the
row and order tables.

The second of those tests was added after the first mutant run. A mutant that ordered the chain by the prior's first
observation broke the shared `chain` fixture, so 179 tests errored during setup and none failed. A setup error is not
a kill. The added test builds its own two results and needs no fixture, and the mutant now fails it.

## Handoff notes added for Tasks 4 and 5

- A stored prior must carry a canonical `lifecycle.source_available_at`.
- On `source_precedes_prior_event` with either detail, keep the last good record and mark currentness pending.
- Task 4 must not key chain position on the generation id. Position is the document revision.
- The two limits above (same-second filings; a withdrawn newest filing) are Task 4's to hold at publication.
- From the round-6 review (note N1): the same accession and text with a later acceptance clock is carried at the
  same revision with a moved source clock and generation id. Task 4 requires the stored chain of an event to be a
  prefix of the candidate's chain, entry for entry, so that result cannot replace a stored revision.
- From the round-6 review (note N2): the preparation never produces a workspace whose source clock is later than its
  first observation, and it does not refuse a forged prior that has one. Task 4 owns the integrity of a stored prior
  and refuses such a workspace in its closure validation.

## Verification

Measured on the pushed round-6 head `5f33a5a26635a9e565f93f4639f629b20d086937` (repair commit `e814285adcbb`, pin
commit `19912e5dccd0`, merged with main at `8744b8c1a0af`), on CPython 3.12.13. Six files differ from main, all owned.

**Seat harness on the head.** Every step returned 0 except pyflakes, which is explained below.

- The suite: 359 passed (341 in round 5), 74 test functions.
- RED: with the implementation at the merge base the suite stops at collection with 1 error, so the tests depend on
  this PR's code.
- The `earnings-economic-dossier` job line: 2,717 passed, 174 skipped, 519 s locally.
- The `earnings-economic-source-selection` job line: 359 passed, 64 s locally.
- `tests/test_ci_pack.py`, the whole file: 143 passed, 2 skipped.
- Contract delta against `8744b8c1a0af`: 0 introduced, 0 inherited.
- pyflakes on the owned Python files: two lines, both already on main at `8744b8c1a0af` (an unused `html` import in
  `pg_profile.py`, an unused `parse_canonical_event_id` import in `refresh_event_workspaces.py`).
- A trial merge with `origin/main` is clean, and the worktree is clean afterwards.

**Mutants.** 113 mutants: the 94 of round 5, 15 for R6.1 and 4 for the N3 gaps. The first run, on the prototype tree,
killed 112 and reported 1 broken (`r61_ordered_by_first_observation`, the setup-error case described under "The
suite"). After the added test, the run on an export of the head killed all 113, with none surviving and none broken.

**Sweeps.** Run on the prototype tree, whose module, script and fixtures are byte-identical to the head. Every sweep
ended with 0 escapes and 0 violations. The change from round 5 is fully accounted for by the two new rows.

| Sweep | Calls | Returned | Refused, typed | Returned in round 5 | Difference |
|---|---|---|---|---|---|
| Acquisition | 6,777 | 504 | 6,273 | 567 | 63, all row 26a |
| `observed_at` | 896 | 169 | 727 | 230 | 61: 56 row 7a, 5 row 26a |
| Prior, 8 shards | 96,983 | 90,747 | 6,236 | 90,993 | 246, all row 7a |
| Transport: the traced acquisition under one tampered response | 5,744 | 2,279 | 3,465 (`RefreshError`) | 2,279 | none |
| Transport: preparing each returned acquisition, with no prior and with a prior | 4,558 | 3,950 | 608 | 3,950 | none |

**Probes.**

- The round-5 reviewer's B1 script: night 1 is revision 1 and night 2 is refused with R6.1's reason and detail, so B1
  no longer reproduces. Its chain script: steps 1 to 7 are unchanged and step 8 (the older accession on top of the
  8-K/A) is refused `source_precedes_prior_event` / `prior.workspace.lifecycle.source_available_at`.
- The seat's round-6 chain probe and the four round-5 probes (corrected text, the 43-case control, the event probe,
  the recursion probe): no failure.
- The integration check with Task 3 (Task 2's prepared result consumed with no translation): 107 checks pass, 0 fail.

**Independent review.** `OPUS_T2_PR_REVIEW_R3_2026-09-30.md`: PASS, verdict ACCEPT at this head, no blocking finding.
Its notes N1 and N2 are the two Task 4 handoff notes above; N3 and N4 are the two recorded limits.

**Hosted CI.** Run `36731011836` on this head concluded at 16:09Z. 21 checks passed, including all 12 packs, `ci-gate`, `contract-delta` and `ci-authority/main`; 4 were skipped (three fork-only variants and `trusted-ci`). One pilot context is red, `ci-authority/codex/merge-queue-pilot` ("CI authority context rejected"): it reports that the PR edits two CI-authority paths, `.github/ci/legacy-jobs.yml` and `scripts/refresh_event_workspaces.py`. It was red in the same way on PR #8232 at its merge, and it was not rerun or worked around. `ci-pack-8` (24 jobs, none of them this PR's) spent 80 minutes in its pack step on a hosted runner, against 21 and 38 minutes for the same pack on main's two latest baselines, and passed. Main gained 9 commits between the merged base `8744b8c1a0af` and the merge, all from data and render lanes; none touches a file this PR or its CI job depends on, and a trial merge with `096cd34b7b8f` is clean.
