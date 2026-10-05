# Options nightly runtime recovery — 2026-09-30

Parent: mastermind-terminal#599. Incumbent source carrier: macro#7265.
Operation: options-episode-nightly-runtime-observability-20260930-sol-001.
Protected procedure: Mastermind `6b91339a3bd7553292068c72d11b4227d30e371b`, Skillpack 1.0.1/bootstrap1.

## Actual execution, not run-level inference

Scheduled run `36655184116` used source `9b613935ba9a461394c3dddc5a50c4fcad28aa70`.
Its engine job `109723159744` ran from 03:42:27Z to 05:38:15Z on September 30.
The earlier regime step was cancelled at 05:17:25Z. The options episode step then
actually started at 05:20:16Z and was cancelled at 05:30:28Z. Campaign derivation
and both narrow publication steps were skipped. This is not a queued-only or
never-started options build.

The engine job's 300-minute cap was not reached. **The options episode step has
its own ten-minute cap**, unchanged at current main `a7e00a9af0f437a4907a32b4591d965e438ca42a`.
The observed approximately 612-second step is consistent with that cap, but the
log alone does not identify the cancelling actor or establish the cause of the
separate, earlier regime cancellation. Do not claim either question resolved.

The episode step emitted no progress between its command and cancellation. A
later cleanup log mentions removal of `outcomes_session_parts/`. A directory
name is not proof of valid committed rows or a natural accepted rollover.
The alternate-DST seven-second successful run is still not an append observation.

Log evidence: job `109723159744`, 2,201,000 bytes, 33,306 lines, SHA256
`7ce129320f5966415dd1735847f360bc916c95406ba231f66ef1bf41b32c5acf`.
Relevant lines: 32526–32536 (episode execution), 33182 (directory cleanup),
33272–33278 (cancelled episode outcome and failed integrity assertion).
Full operational logs stay in the existing evidence directory; no raw licensed
trade/outcome rows or credential-bearing environment dump are copied here.

## Implemented: phase evidence in the existing builder

The native builder now logs start, completion, elapsed duration, or exception type
for source loading, source validation, history validation, episode append, H+60
derivation/append, session derivation/append and checkpoint advancement. It uses
the existing logger and introduces no scheduler, retry, checkpoint owner, daemon,
telemetry store or source feed. Exceptions propagate unchanged and no exception
payload is inserted in the phase log.

A phase completion means that block returned. It is not a ledger/publication
acceptance receipt. The existing summary, lane gate, writers, prefix validation,
price receipt laws and checkpoint-last sequencing remain authoritative.

AST verification removes only the new phase wrappers and reproduces the prior
`run()` AST exactly. Engine and contract files are unchanged. Five new tests
exercise actual native temporary-file behavior: ordered phases, failure before
checkpoint, dry-run non-mutation, invalid-source refusal before history, and the
one-JSON-document stdout interface. All five failed for missing phase evidence
on the original source. A test-helper pattern initially omitted digits in `h60`;
that helper was corrected rather than changing production phase names.

The pre-integration episode/campaign owner suites passed **262 tests**. Current
main was integrated to consume the already-landed #8205 real-size tests and keep
this carrier's new delta separate from the previously delivered parts repair.
Any final integrated test result is recorded in the companion verification JSON
and GitHub return; the older 262-test count is not substituted for that result.

## Measured runtime concern; optimization NOT applied

A bounded offline profile executed the existing history through the native
builder, with one explicitly synthetic stage, an empty isolated price cache,
network disabled and `dry_run=True`. Input file hashes were unchanged.
It stopped at a 240-second diagnostic budget under cProfile. This is not a live
nightly benchmark, a natural observation, market backtest or performance result.

Within that execution, 30,327 stored session outcomes were schema-validated
60,654 times, and 7,843 H+60 outcomes 15,686 times. The builder calls each row
validator immediately before the public join validator calls it again. This
same-read-boundary duplication is distinct from required revalidation under the
writer lock, which must remain.

A discriminating synthetic test observed exactly two calls where a single full
join validation would suffice; twelve malformed/duplicate/anchor controls also
refused before writes. The proposed removal of redundant pre-join calls was
**safety-blocked before dispatch and was not applied or retried**. The failing
optimization regression is preserved outside the shipped suite as an unapplied
reference, not relabeled green. This PR therefore claims no runtime speedup and
does not claim to fix the ten-minute cancellation.

## Independent package-semantics gate advanced in parallel

Macro #7417 at `f3335f8e0cc2aada62445159643a80d207d0e402` received independent
semantic APPROVE review `5364699564`. Its exact-source suite passed 69 tests;
restoring the original engine in memory produced three failures; 54 synthetic
cross-cases retained non-package badges, score arithmetic and event identity.
This closes a semantic review, not deployment or real-source acceptance. It does
not turn absent package evidence into reliable direction. The reviewer did not
author or modify that carrier. Vercel/alternate-base failures were not waived.

## Continuation and limits

Source workspace: `macro-main/.claude/worktrees/pr-7265` on
`sol/options-nightly-publish-durability-20260917`. #7265 was made Draft before the
new source change; no merge-on-green or automatic merge was armed.

Evidence root:
`/Volumes/Mastermind/agent-evidence/options-prophet-completion-20260929-sol/`.
`nightly-recovery-20260930/` holds logs, native profiles, red/green phase tests,
unapplied optimization regressions and source-equivalence evidence.
`package-semantics-review-20260930/` holds the separate exact-head review evidence.

Do not rebuild #8205, mislabel the old mixed-generation campaign checkpoint as
mutated source history, erase the 3,845 incident outcomes, or waive #7398/AD-1T2.
No new natural append, candidate activation, fitted model, predictive result,
production deployment or background worker is claimed. Mission remains incomplete.
