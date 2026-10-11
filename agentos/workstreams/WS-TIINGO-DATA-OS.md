---
key: TIINGO-DATA-OS
title: Tiingo historical data and BOATS integration
objective: >-
  Deliver the Chairman-licensed Tiingo history and BOATS feed through the existing
  Macro archive/Data OS and Terminal Quote Hub. Completion requires real source
  receipts, historical identity and revision verification, admitted production
  capture, accepted consumer tests/review/CI, approved VPS release and responsive
  live browser acceptance.
status: active
program: terminal-market-data
repos: [macro, terminal]
owner: assigned Tiingo integration principal
class: build
blast_radius: user_facing
ambiguity: scoped
waves:
  - id: producer-integrity
    title: Repair original producer integrity and verify source
    status: done
    pr: 8698
  - id: historical-qualification
    title: Acquire and verify full EOD and fundamentals history
    status: in_progress
    pr: 8698
    depends_on: [producer-integrity]
  - id: boats-qualification
    title: Qualify live BOATS market frames, retention and gaps
    status: in_progress
    pr: 8698
    depends_on: [producer-integrity]
  - id: consumer-delivery
    title: Integrate incumbent Data OS and Quote Hub, release and prove live
    status: in_progress
    pr: [8698, 945]
next_action: >-
  Obtain actual BOATS Q/T/B evidence in the live session, reconcile the current
  served fundamentals restriction and retained independent-review resource gate,
  and continue the 47,689-candidate history corpus using the same collector and
  exact accepted catalogue after verifying one active writer and current reserve.
owns_paths:
  - collectors/tiingo_archive.py
  - lib/dataos/tiingo_*.py
  - scripts/tiingo_*.py
  - docs/TIINGO_DATA_OS_INGESTION_20261009.md
  - docs/tiingo-evidence/
artifacts:
  - docs/TIINGO_DATA_OS_INGESTION_20261009.md
  - docs/tiingo-evidence/20261011-producer-integrity/
  - docs/tiingo-evidence/20261011-live-qualification/
  - docs/tiingo-evidence/20261011-history-expansion/
landmines:
  - Keep one existing collector, archive writer, provider/runtime owner and source carrier; News PR 8697 is separate.
  - The source archive retains a directory-swap TOCTOU limit; trust one writer and do not rename archive directories concurrently.
  - Full fundamentals activation is Chairman-attested but AMD current-key responses still expose evaluation restrictions; do not infer absent purchase or purchase again.
  - Authentic BOATS controls and historical bars do not prove actual Q/T/B or session coverage.
  - The current relay publisher and Hub parser label their data as Yahoo; do not inject BOATS under that source label.
  - Registry PROPOSED and research PIT/identity/availability refusals remain until their incumbent owners admit real production capability.
do_not_redo:
  - Do not publish the previously blocked untracked CEO handoff by another route.
  - Do not reacquire the accepted ticker ZIP or re-download already verified histories merely to obtain another checkpoint.
  - Do not resubmit or replace frozen Fabric operations, bypass actual permission refusals, or claim a prelaunch failure is a running worker.
  - Do not introduce another quote socket/service, queue, cron, lifecycle, authority store, or Vercel deployment.
  - Do not publish credentials, subscription-ID values or licensed raw market rows in GitHub evidence.
---

This workstream records delivery under the existing Terminal Market Data and Quote
Plane programme. Macro retains upstream source, identity, temporal and entitlement
truth; the record transfers none of those owners and starts no runtime or worker.

Verified source repair: producer head
`bddd8da1f5c5225b258ff4d6d35ce72fca5a09fb`, Macro PR #8698. The retained full suite
passed 431 checks before the final independently identified legacy-row defect;
that defect reproduced red and its requested affected suite passed 122 checks.
Commands and actual logs are in the producer-integrity evidence directory. Hosted
[CI 38137444247](https://github.com/mastermindx-market-intelligence/macro/actions/runs/38137444247)
completed success at that exact head. Archive qualification ran on documentation/evidence head
`fa2580e1615db9cf5bade13ca8c8667f08d3ff6b`. Later exact-head hosted checks are a
separate observation and are not assumed from that producer acceptance.

Verified data snapshot at 2026-10-11T18:17:12.448330+00:00: 553 nonempty EOD histories,
1,233,237 distinct bars, 565 source receipts, all raw hashes and nonempty projection
lineage verified, and two additional empty EOD responses retained. The completed
500-response expansion returned 1,103,194 rows / 250,573,134 bytes in 1,268.838 seconds.
`python3 -m scripts.tiingo_materialize --max-receipts 1000` returned zero refusals;
`audit_corpus` checked the exact 500 tasks and all receipts and found 498
RAW_RECORDS_CAPTURED / 2 EMPTY_CAPTURED. Evidence includes exact per-request
hashes, dates, receipt identities, counts and original observation clocks.

Actual fundamentals metadata has 20,352 unique permanent identifiers, including
12,540 inactive securities. AAPL's three-year original/revised/daily samples
returned 200; 45 matched fiscal metric values differed. AMD ticker and permanent-ID
requests returned 400, with free/Dow 30/limit terms. Computer Use verified the
account key equals the provisioned collector key and that Organization/BOATS are
active. No support message, subscription change or token rotation was made.

Actual BOATS: two HTTP 200 historical responses contain 1,407 minute bars with
explicit volume, all clocks within 20:00–03:59 ET. A 30-second authenticated
WebSocket sample contains actual H/200 and I/200 controls and subscription-ID
presence, but zero Q/T/B in Sunday daytime. Raw control segments stay empty in L1.
The next normal Sunday session begins 2026-10-12T00:00:00Z (17:00 PDT / 20:00 ET);
this calendar fact schedules no wake, capture, or background observer.

Terminal [draft PR #945](https://github.com/mastermindx-market-intelligence/mastermind-terminal/pull/945)
head `7506ef1539c8646e7bf52b65b697a102fd549942` preserves Hub source and basis through
the existing ext-quote proxy. Actual affected tests passed 33 checks and TypeScript
passed. Hosted aggregate typecheck/tests and all responsive desktop/mobile/tablet/serial
shards passed on run 38161624995 at this exact head. There is no activated BOATS provider or new live
consumer claim.

Retained Fabric consumer operation `tiingo-8698-consumer-contract-20261011-01`
failed before launch with no_operator_available. Retained final-review operation
`tiingo-8698-final-integrity-review-20261011-01` failed before lease/launch with
LOG_RESERVATION_FAILED errno=1. No replacement review or running child is inferred.
Independent consumer review and the original release/runtime gates remain open.

The current work is not complete. The attended 1000-request continuation settled
with 1000 HTTP 200 responses, zero failures, 1,918,012 records and
439,264,113 bytes in 2,596.673 seconds. Qualification at
2026-10-11T19:17:48.338672+00:00 verified all 1565 receipts,
1,552 nonempty EOD histories and 3,151,249 distinct bars. The exact corpus
audit found 999 RAW_RECORDS_CAPTURED / 1 EMPTY_CAPTURED; every raw hash
and nonempty projection lineage verified. These actual files are bound in the new
history-expansion manifest; licensed rows stay on the external drive.

Actual Data OS retrospective consumer reads passed on immutable AMD/AAPL captures
and refused mixed statement dimensions, pre-observation cutoff and PIT admission.
The safe, version-bound existing-store AMD comparison covers 27 dates; one close
differs by about half a cent and all stored volumes differ (max about 0.274%). The
incumbent store is an unqualified local snapshot and declares total-return close.
No equality/PIT/production claim follows from those comparisons.

The reused catalogue denominator is 47,689 US acquisition candidates, 39,574 stocks
and 8,115 ETFs, including 17,256 older ended histories. A pilot-rate extrapolation
is 33.6 hours / 23.9 GB; this estimate is not a reservation or completed backfill.
No raw writer, recurring runtime, later wake, merge or deployment is left running
by this completed bounded collection. Programme completion still needs full
served fundamentals access, actual live BOATS events/quality, complete history and
dated identities, independent consumer review, incumbent runtime admission and
approved VPS/live browser proof.
