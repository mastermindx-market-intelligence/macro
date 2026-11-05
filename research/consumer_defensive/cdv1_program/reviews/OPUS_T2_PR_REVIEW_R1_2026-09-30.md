# Opus review — CDV-1 Task 2, PR #8234, first review, 2026-09-30

- **Artifact:** PR #8234, head `58c72efb0165ac6db7787a7beda3e08d4f1433f0`, branch `claude/cdv1-t2-source-currentness`, merge base `3890cfc7c5ab`. The head was produced by the r3 packet (`packets/CDV1_T2_R3_PACKET_2026-09-30.md`).
- **Reviewer:** an independent, read-only Opus reviewer commissioned by the CDV-1 seat (session `251f88c8`). It worked against the task bar in `reviews/SEAT_RULING_T2_T3_R3_ERRATUM_2026-09-30.md` and the plan's Task 2. The seat also gave it six hypotheses (H1–H6) from the seat's own reading of the head.
- **Verdict:** **REJECT.** Six blocking findings.
- **Recorded by:** the seat, from the reviewer's return. Every finding was confirmed by a probe or mutant the reviewer ran against the head.

## Mechanical baseline

Reviewer and seat harness, same head:
- file grants PASS, and the Task 1 freeze diff is empty;
- pure addition is 0 for both append-only files;
- RED rc 2 at the merge base, then GREEN (15 passed);
- the dossier job's exact `run:` line: rc 0, 2,315 passed, 174 skipped;
- the source-selection job: 15 passed;
- `tests/test_ci_pack.py`: 143 passed, 2 skipped;
- `git merge-tree` against main: clean.

The grants check is file-level. B6 is a breach inside an owned file, at hunk level.

## Blocking findings

| # | Bar | Finding | Evidence |
|---|---|---|---|
| B1 | (c5) | Erratum ruling T2 R6 is not implemented. There is no `PROFILE_SOURCE_FAMILY`, no typed refusal for an unknown profile or for the private token, and no test. | `git grep` over the four owned files prints nothing. |
| B2 | (c4), (b) | `fiscal_scope` is the module constant `_PREPARED_FISCAL_SCOPE` (`pg_profile.py:2209`), byte-identical to the fixture's `FISCAL_SCOPE`, so the tests co-vary with the code. Every report date except `2026-06-30` raises. A missing report date falls back to a hardcoded quarter, labelled `quarter=1` with the year 2026, although P&G's quarter ending 31 March is fiscal Q3. `asof` defaults to `2026-06-30`. | `probe1.py`: report dates 2027-06-30, 2025-12-31, 2026-03-31 and 2026-09-30 raise; no report date gives `FY2026 Q1` with `calendar_end` 2026-03-31. |
| B3 | (e), (a) | The traced exact-accession SUCCESS path raises `KeyError: 'received_bytes'`. It takes the legacy dict, which has no receipt. Only the failure branch is tested. | `acquire_results_filing(..., accession=fixture_accession("older"), trace=...)` against `newer_fetch_failed`. |
| B4 | (a), r3 R2 | Preparation fabricates the received-byte receipt: `received_digest = transport.get("sha256") or decoded_digest`, with a decoded-length fallback and a defaulted `declared_encoding` of `utf-8`. A body decoded as latin-1 is prepared, not refused. | A `malformed_encoding` legacy result gives receipt length 29 with `utf-8`, against actual bytes of length 28 with a different digest. |
| B5 | (b), n-B2, r3 R5 | The changed-bytes test does not bind the release entry to the acquisition. It injects an impossible receipt (`"b" * 64`, length 42). | Mutant M1, copying `source_sha256`, `filing_key`, `form` and `url` from `prior`: 15 passed. Mutant M4, disabling the digest overwrite: 15 passed. |
| B6 | (d), (f) | The PR adds `scripts/publish_company_intelligence_r2.py` to the `earnings-economic-dossier` job's `paths:` (`legacy-jobs.yml` ~:14520). The r3 packet forbids touching that job, and the line is not needed. | With the line removed, `curated_exclusive` gives 2 passed. Nothing under `engine/` imports the script. |

## Hypothesis dispositions

- **H1** is confirmed (B2).
- **H2** is partly confirmed:
  - the token `unverified` matched the r3 packet's own vocabulary;
  - an out-of-vocabulary state passes through unvalidated.
- **H3** is confirmed in part (B4). The prior-dependent digest overwrite changes what `source_sha256` means depending on `prior`.
- **H4** is confirmed (B3). Tampered inputs also escape as untyped `AttributeError`, `TypeError` and bare `ValueError`.
- **H5** is confirmed (B1).
- **H6** is refuted: pyflakes reports nothing new against the merge base.

## Non-blocking notes

- The three other-job widenings, each gaining `event_workspace_build.py`, are required by the closure test. They are `conviction-profile`, `unrun-picks-boards` and `skew-accrual-lane`, and removing them fails the test by name. **The seat ratifies them (R4.8).**
- The 8-K/A test is weak: mutant M2, minting the 8-K/A as a separate `event_id`, gives 15 passed. This is plan step 2.4's "an 8-K/A is not a second fiscal quarter". **Carried as an R4.4 test.**
- "Missing prior bytes do not create a new root", also plan step 2.4, is untested. **Carried as an R4.4 test.**
- These are not carried:
  - two R4 tests largely duplicate each other;
  - `test_missing_acceptance_timestamp` depends on the order of the checks;
  - trace candidates are listed excluded-first;
  - currentness does not report `unverified` when the candidate cap truncates the list.

## Seat adjudication

All six findings are upheld. B2, B4 and B5 share one defect class: a value stated rather than derived from its source. The fixture scope is copied into the code, the receipt is copied from the decoded digest, and the release-entry fields are copied from the prior. The fix round therefore derives each one from its own source, and makes the tests compute their expectations independently:
- the scope from the admitted calendar and the acceptance clock (R4.1);
- the receipt from the received bytes, cross-checked and never copied (R4.3);
- one source-identity predicate (R4.4).

The fix round is `packets/CDV1_T2_R4_PACKET_2026-09-30.md`. The rulings are recorded in `reviews/SEAT_RULING_T2_R4_2026-09-30.md`.
