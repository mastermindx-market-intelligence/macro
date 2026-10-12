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
    pr: [8698, 945, 955]
next_action: >-
  Complete hosted acceptance for the fresh-main CI continuation: original Macro
  8698 merged before CI settled and its contract-delta gate then proved the missing
  NYSE-calendar path in the Data OS job. The one-path repair passes the local
  differential checker; do not infer CI acceptance from landing. Qualify the
  settled fifth EOD wave's 500 HTTP-200 responses through the existing EOD-only
  materializer and full lineage reader. Reconcile four separate intraday receipts
  before another raw capture. Verify Terminal 955's exact protected aggregate and
  merge, then use the existing VPS release path; 945 is already deployed. Complete
  actual BOATS archive/relay/Hub/API/responsive-browser acceptance only after its
  source, runtime, sole-writer, target, resource and clock gates are met. The Chris
  browser is signed in with BOATS ACTIVE; fundamentals served scope remains a
  separate current-key Dow-30 discrepancy, with no purchase or support email.
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
  - docs/tiingo-evidence/20261011-history-wave2/
  - docs/tiingo-evidence/20261011-history-wave3/
  - docs/tiingo-evidence/20261011-boats-source/
landmines:
  - Keep one existing collector, archive writer, provider/runtime owner and source carrier; News PR 8697 is separate.
  - The source archive retains a directory-swap TOCTOU limit; trust one writer and do not rename archive directories concurrently.
  - Full fundamentals activation is Chairman-attested but AMD current-key responses still expose evaluation restrictions; do not infer absent purchase or purchase again.
  - Authentic BOATS controls and historical bars do not prove actual Q/T/B or session coverage.
  - Reviewed source admits a complete BOATS-only public projection; installation and old object/cache replacement still need proof. Never inject BOATS under a legacy provider label.
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

New qualification at 2026-10-11T20:38:12.057478Z supersedes earlier corpus counts:
2,551 nonempty EOD histories / 5,278,835 distinct bars, four empty EOD responses,
2,565 immutable source receipts, every raw checksum and nonempty projection
lineage verified. The second additional 1,000-request wave returned 1,000 HTTP
200 responses / zero failures / 2,127,586 rows / 487,075,814 bytes in 2,657.548
seconds. Existing materialization returned 999 new / 1,558 existing / two RAW_ONLY
/ six empty / zero refusals. The exact audit found 999 RAW_RECORDS_CAPTURED and
one EMPTY_CAPTURED. Current wave-specific files and commands are hash-bound in
`docs/tiingo-evidence/20261011-history-wave2/`. Source logic remains bddd8da1.

The Chairman explicitly authorized an already-permitted alternative independent
review after the Fabric diagnosis. Exclusive workspace log reservation worked;
the installed directory is outside the task write grant, and a log-only override
would orphan the existing status/result/acceptance path. The failed original
Fabric operation was not retried or altered. One bounded native reasoning review
returned PASS for Terminal 945 quote route/tests at 7506ef15; those files remain
unchanged at dde9b71ee21680c1c38c2c6d86c38c4fc2dc3660. Its report is retained
on that original Terminal carrier, hash
57b98c4412837c9447c18d561a2673934d714c97b7cd87c1b96be3b0cf2d0f93.
This fulfills the bounded source-consumer review; it is not a formal GitHub
approval, producer/feed review or production acceptance. The adapter grant
still has its original limitation but no longer blocks this source review.

Terminal 945 is ready and protected native squash auto-merge is armed. At the
20:50 UTC observation, Quote Hub, unit/typecheck, ingest, PostgreSQL and both
desktop/serial shards passed on run 38170844161; tablet/mobile and aggregate
checks remain pending. No merge/deploy or live BOATS provider claim follows.
The 0032 migration namespace test was repaired against the genuine #946 merge,
then the #947 owner's reservation file was consumed unchanged; final Terminal
PR has no migration-source delta and this session executed no SQL.

The completed second wave has no remaining writer. The third attended EOD wave
started at 2026-10-11T20:46:57.412141Z, excluding 2,555 captured symbols, with
257.190 GiB free and the same 35 GiB reserve. That wave is still running at this
checkpoint; its future exit/qualification is not assumed. No second collector,
recurring runtime or future wake was created. The Tiingo browser has returned to
Login Required, ordinary autofill was unavailable, and a human sign-in request is
pending while independent data/release work continues. Do not transfer the
credential to the VPS or retry the previously refused Passwords access.


Current source/release checkpoint, 2026-10-11 22:12 UTC (supersedes dated pending
945 and third-wave states above): Terminal #945 merged at 20:55:17Z and the existing
VPS builder settled rc=0 at squash d0973ef6e7521f775801401a345792fc7c4cb3e2.
Fresh 21:43 UTC VPS/public receipts agree on source, deployment marker and public
page identity; Terminal/Quote Hub active, HTTP 200/no-store ext API with null
AMD/AAPL in the closed window. Responsive production desktop/tablet/mobile loaded.
This completes the provenance prerequisite release, not genuine BOATS delivery.
Commands and safe receipts are in docs/tiingo-evidence/20261011-boats-source/.

Third history wave settled with 1000 new HTTP 200 captures, zero failures,
1,938,218 row hints and 440,364,083 uncompressed bytes in 2351.934 seconds.
Materialization wrote 1000 new views without refusals. Exact audit inspected all
3565 receipts and verified all 1000 response bodies. The dated full proof at
21:37:28.879631Z verified 3551 nonempty EOD histories / 7,217,053 distinct bars,
every raw checksum and nonempty projection lineage, unique market dates and exact
overlap equality. Physical archive 465,839,324 bytes; free 255.615 GiB, same 35 GiB
reserve. Reproduction commands, exact plans, old observation clocks and safe hashes
are in docs/tiingo-evidence/20261011-history-wave3/. A fourth attended wave started
21:41:55.785799Z on calling head 6eccb5aa3d3f640b8aea8dc61653bc0b4b5e9bde with
explicit dirty-source/loaded-source hashes and excluded 3555 captured symbols.
Its original log and plan are in the task's tiingo-phase1 artifact directory;
settlement and qualification remain pending. Do not start a competing archive writer.

The incumbent BOATS producer/archive observer and whole public allowlist source
passed independent review and 96 combined strict producer/registry tests. Only the
two existing extended-quote families now qualify complete BOATS facts as
PUBLIC_FACT/ANONYMOUS under Chairman's existing license attestation. Unrelated
families remain unchanged and generic quote delivery stays held. Required current
LIVE-pin repairs were independently qualified against original/current blobs;
August census identity and historical data/site evidence remain unchanged.

Terminal #955 starts from the actual #945 squash on its new external-SSD carrier,
commit 07c777035b132e376b905a793065d1d611cc8918. Its independent review repaired
three timing/ordering defects and passed; 116 Hub, 48 route/freshness, 13 responsive
(two existing width skips), three regular-authority and six EN/ZH screenshot cases
passed. Captures are SOURCE_SYNTHETIC. Hosted run 38178639549 passed Hub, ingest,
PostgreSQL, CodeQL, full unit tests/typecheck, but the unit job's later copy guard
rejected one inline bilingual label. The exact red evidence is retained; the same
copy is now routed through the existing LEX/t helper and its strict local guard
passed. Current repair CI and protected landing remain pending; do not claim this
BOATS source is deployed from the earlier #945 receipt.

The same bounded reasoning reviewer is the user-authorized alternative carrier;
original failed Fabric operations remain untouched. No persistent producer schedule
was installed. Automatic approval review rejected the earlier combined publisher/
launchd scheduling change for untested persistent publication/relaunch and overlap
risks. Source-only application was separately approved and accepted; the original
persistent effect remains unadmitted. Existing provisioned R2 environment names are
present at the legitimate Cloudflare R2 origin, with no secrets printed/copied or
client constructed. The Tiingo page is still Login Required with no password;
human sign-in remains pending and the refused Passwords access is not retried.

Dated correction, 2026-10-11 around 22:30 UTC: the earlier login blocker was inferred from the wrong Chrome Ryan profile. The intended mastermindx6031 account is already signed in in Chrome Chris; Organization/BOATS are ACTIVE, with 19,620 hourly / 145,592 daily requests and 98.09 GB remaining. No login, purchase, email or token transfer was needed. Current Terminal #955 source 3e8fe8adad84a043a3454c1214bc886c42e872b1 restores global i18n to protected-base bytes and uses the existing feature-copy pattern; 554 Vitest files / 9,141 tests, type, unchanged guard and six EN/ZH browser cases pass. Hosted current-head gates are separate. Wave 4 retained 838 responses before a read timeout, rather than completing all 1,000; materialization wrote 835 new views and refused zero. Full archive qualification is running, with no raw writer.

Dated wave-four qualification, 2026-10-11 22:49 UTC: all 4,403 receipts were checked with exact identity for ambiguous body hashes. Full archive: 4,386 nonempty EOD histories / 8,919,835 bars, 577,610,201 bytes, 254.978 GiB free, reserve 35 GiB. Existing reader refusal remains intact; independent exact-context review PASS. One attended continuation requests 161 previously unattempted paths under the original 1,000-attempt total; BAFE timeout remains unresolved. No complete history or PIT admission is claimed. Terminal #955 current head 3e8fe8ad hosted unit/type, Hub, ingest, PostgreSQL, serial and CodeQL checks passed; four responsive shards remain in progress at the 22:48 observation.

Wave-four continuation settled: 161/161 succeeded, 343,787 row hints / 80,194,781 raw bytes in 368.882 seconds. Combined original batch: 999 verified bodies (996 nonempty / three empty), one absent BAFE timeout; all 4,564 archive receipts inspected. Materializer settled rc=0, final archive qualification running. Protected main 3a92cf50 integrated without source conflict; five LIVE receipt changes and three unchanged unique anchor relocations passed independent review d7ae07de, then 21 classification tests passed. CI additions retain all prior tests and add actual BOATS display coverage. No raw writer is active.

Final wave-four qualification: 2026-10-11T22:56:35.691310+00:00, 4,547 nonempty EOD histories / 9,263,622 bars / 4,564 receipts; raw/checksum/exact-context/row-lineage/date/economic-overlap proof passed. Physical archive 604,537,634 bytes, free 255.4 GiB, reserve 35 GiB. Safe exact proof and timeout are retained under docs/tiingo-evidence/20261011-history-wave4/. Original Macro #8698 accepted source is pushed at 82feebf630999c0b5a4a3ec6c922ec92f720105f; current hosted gates remain separate.

## CI continuation at 2026-10-11 23:29 UTC

The original Macro carrier landed prematurely at `fba80a12`; hosted contract-delta
run `38182746681` then found the missing calendar dependency. The fresh-main
continuation widens the existing job by one path and preserves producer/archive
bytes. `python3 scripts/check_contract_delta.py --base
8ad47787d83be8625fb387e279220b5a40efc7b2` passed with zero introduced/inherited
findings in 440.3 seconds. Actual red/green/parity/landing evidence is retained at
`docs/tiingo-evidence/20261011-ci-continuation/`. This does not establish hosted
acceptance, publication or full-programme completion.
