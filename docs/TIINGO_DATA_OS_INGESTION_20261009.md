# Tiingo → Mastermind Data OS: bounded source acquisition and research views

**Date:** 2026-10-09
**Current implementation carrier:** macro branch sol/tiingo-data-archive-20261009
**Source authority:** existing Macro Data OS lib/dataos/identity.py, price.py,
temporal.py, registry.py, config/dataset_registry.yml.
**Physical archive:** /Volumes/Mastermind/market-data/tiingo
**Credential:** operator-only /Volumes/Mastermind/.mastermind_private/tiingo/api_key,
file permissions 0600. Never check secrets into Git or print them.
**Commercial authority:** Chairman states Business Advanced is live with full redistribution.
That present attestation is recorded; this is not a request to repurchase or reapprove it.
Actual endpoint activation, rate limits, historical availability and production proof
remain technically unverified, distinct from the Chairman's rights attestation.

## Current truthful states

| Capability | Current state | Proof vs pending |
|---|---|---|
| Tiingo credentials available to source adapter | BUILT_NOT_PROVEN | Owner-only file exists, but vendor authentication **not attempted successfully** |
| Historical EOD ingestion | BROKEN | Raw producer exists, but context/corruption/clock regressions block activation; no live response |
| Fundamentals metadata/statements/daily | PARTIAL | Source routes and offline permaTicker cohorts exist; capture integrity and real history are unproven |
| BOATS snapshots / historical bars | BUILT_NOT_PROVEN | Vendor path and 1m bar builder; entitlement not verified |
| BOATS trade/quote/break websocket | BUILT_NOT_PROVEN | Bounded streaming client and immutable segmented raw receipts; not connected |
| IEX / equity intraday / FX / crypto / news / corporate actions / fund fees | BUILT_NOT_PROVEN | Documented REST source paths, raw archive; no live data |
| L1 research Parquet | BROKEN | Happy-path fixtures pass, but content-only output names alias distinct tickers/query contexts; reader now quarantines ambiguity |
| Complete historical corpus / full symbol census | NOT_BUILT | No vendor entitlement probe; no production collector/backfill |
| Canonical L2 Data OS enrollment | NOT_BUILT | Requires as-of identity/rights/availability/quality and owning consumer gate |
| Recurring durable capture and research publication | NOT_BUILT | Must use an incumbent runtime / publication owner, not new cron or lifecycle |

The authenticated live probe was refused at the connected-tool safety boundary before
dispatch. Do not infer that a key fails or succeeds and do not reroute/retry the same
denied effect through another tool/session. Safe independent source/fixture work continued.

## Dataset families and semantic traps

1. **Daily U.S. equities and ETFs**: /tiingo/daily/{ticker}/prices includes
   raw open/high/low/close/volume and dividend/split-adjusted numbers. Preserve raw,
   label vendor adjusted as tradj, and stamp adjustment vintage. A download in 2026
   cannot prove what adjusted series an investor actually knew in 2017.
   Public metadata /tiingo/daily/{ticker} can bound coverage by startDate/endDate.
2. **Fundamental deep history**: /tiingo/fundamentals/meta exposes permaTicker,
   ticker, active/delisted, statementLastUpdated, dailyLastUpdated.
   Statements /{ticker OR permaTicker}/statements use the vendor's claimed
   *public release date*. Preserve year/quarter/report code/asReported query.
   asReported=true retrieves original period data, asReported=false may draw
   prior periods from newer filings. Neither mode on its own proves actual Tiingo
   historical availability or a canonical SEC filing as-of receipt.
   Daily /daily metrics are a revisable time series. Do not merge into existing
   XBRL or issuer engines by ticker string alone.
3. **BOATS overnight**: venue-specific Blue Ocean ATS top-of-book (Q) and trades
   (T) / trade breaks (B). Keep event nanoseconds, receipt clock, native quote
   sizes/bid/ask, 4 raw MEMOIR sale-condition characters, and all raw envelopes.
   BOATS is *not* the SIP NBBO, official auction tape, consolidated daytime
   close or provable order-level depth. Vendor tngoLast/mid or historical OHLC
   are calculated/convenience outputs. Store session and venue in identity.
   **Only future websocket captures can contain full quote/trade tick history**;
   BOATS REST documented history is intraday OHLC bars, not past tick-level book.
4. **Daytime / IEX**: equity intraday REST and IEX historical bars/snapshot paths.
   Record venue/access scope per product; a realtime best estimate does not
   substitute for exchange-tradable quote evidence.
5. **Other products**: crypto historical, FX prices/top, news metadata/articles,
   dividends/splits, and mutual fund/ETF fee profiles/history. The fixed source
   catalog is a technical route catalog, not evidence that each feature is licensed.
   No news republishing or fee feed redistribution before product-specific approval.
6. **Research universe**: build a dated security/universe cohort with the current
   Data OS identity and alias owner. Use permaTicker only as a source identifier;
   a 2026 live universe is not a 2016 backtest cohort.

Vendor original reference docs (current 2026):
- https://www.tiingo.com/documentation/end-of-day
- https://www.tiingo.com/documentation/fundamentals
- https://www.tiingo.com/documentation/boats
- https://www.tiingo.com/documentation/websockets/boats
- https://www.tiingo.com/documentation/mutual-fund-and-etf-fees
- https://www.tiingo.com/documentation/general/changelog
- https://www.tiingo.com/documentation/general

## Storage contract: reuse Data OS, no competing price authority

L0 paths (external only):
- raw/{source}/{observation_UTC_date}/{source_vendor_ticker_or_all}/{request_digest}-{content_digest}.raw.gz
- raw/boats-firehose/{first_receipt_UTC_date}/{content_digest}.ndjson.gz
- receipts/{source}/{date}/{request_digest}-{content_digest}.json
- receipts/boats-firehose/{date}/{content_digest}.json

Every raw partition is immutable (hard-link no-clobber publish), hashed,
has a timestamped source observation receipt, rights-status unknown until
qualified, and permits multiple revisions to coexist. A provider JSON response
that changes later generates a separate digest, never overwrites the old one.
No API token in requests URLs, partition names, receipt JSON or source code.

L1 (offline research only) is normalized/{source}/{date}/{source_sha256}.parquet
with manifests/{source}/{date}/{source_sha256}.json. Materializers currently
support EOD rows, fundamental statements, daily fundamental metric rows,
BOATS websocket events and the nine additional historical products listed below. All carry a source digest, capture clock,
explicit original-availability unknown, canonical identity not admitted,
PIT backtest not eligible, and redistribution not admitted. Unknown family
materializes to RAW_ONLY; never silently marks it normalized. The user-facing
feature engine and machine backtests must not ingest these directly as L2
price/fundamental authority until admitted in Data OS.

Data OS L2 (future, separately verified) should expose:
- vendor ticker ↔ dated canonical security aliases, including recycled/delisted IDs;
- raw and adjusted prices with adjustment_asof, session, venue, currency;
- corporate-action factors and versioned adjustment vintage;
- released vs observed vs available_at clocks on fundamental filings/metrics;
- source vintage, rights, quality and gap denominators for every day/universe;
- overlays/source comparisons rather than default-winner replacement of
  qualified Yahoo/Massive/SEC source contracts.

## Offline commands that do not require API access

Run *inside the exact macro worktree*:

    cd /Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009
    python3 -m scripts.tiingo_ingest catalog
    python3 -m scripts.tiingo_ingest plan --sources eod-bars,fund-statements,fund-daily \
       --symbols AMD,NVDA --start 2010-01-01 --end 2026-10-08
    python3 -m scripts.tiingo_ingest inventory --verify-hash
    python3 -m scripts.tiingo_materialize --dry-run --max-receipts 100
    python3 -m pytest tests/test_tiingo_archive.py tests/test_tiingo_views.py -q

The following are implementation entrypoints, **not executed/authorized live
run evidence**. Production activation requires the original denied action to
be cleared by the appropriate platform/human authority, along with verified
product entitlements, rates, licensed retention and an admitted runtime.

    # Bounded EOD historical import (NOT run here):
    python3 -m scripts.tiingo_ingest collect \
      --sources eod-bars --symbols AMD,NVDA --start 2010-01-01 \
      --end 2026-10-08 --max-requests 25 --pause-seconds 1.25

    # Bounded original-statement and daily-fundamental import (NOT run here):
    python3 -m scripts.tiingo_ingest collect \
      --sources fund-statements,fund-daily --symbols AMD,NVDA \
      --start 2010-01-01 --end 2026-10-08 --max-requests 25

    # Requires explicit BOATS Real-time entitlement and optional websocket-client:
    python3 -m scripts.tiingo_ingest boats-stream \
      --max-seconds 600 --max-messages 100000
    python3 -m scripts.tiingo_materialize --max-receipts 500

No CLI invocation is an entitlement proof; real 200/authorization responses
are needed. Do not create a separate launchd, cron, queue, watcher,
publication side channel or silent price-feed override. Enroll only with
incumbent data/runtime owner and evidence.

## Storage ceilings and admission checklist

2026-10-09 M2 mount check found /Volumes/Mastermind 3.6 TiB total,
~231 GiB free (94% used). /Volumes/WD 5TB also ~323 GiB free.
The archive enforces a conservative 35 GiB free reserve and no local SSD
fallback. This is not space for indefinite all-symbol tick capture:
a 300-name overnight+daytime full L1 program may exceed a TiB/year
depending on activity; quote bursts and duplicate vintages can dominate.
Run a bounded 50-symbol, 20-session measured cost/throughput pilot before
any full-rate BOATS feed deployment and secure tiered object archive only
through the existing storage owner.

Admission evidence before calling this complete:
- [ ] Tiingo subscription + full redistribution and internal historical
      retention separately verified by product family (EOD, fundamentals,
      BOATS, news, crypto, FX, funds, IEX, equity realtime, actions).
- [ ] Authorized authenticated REST 200 response with no secret in logs.
- [ ] BOATS websocket valid subscription/ack + real Q/T/B arrivals with
      quote/trade timestamps and observed lag/gaps during live session.
- [ ] Vendor rate/bandwidth entitlement, full-symbol coverage, delisted
      universe, and earliest historical date recorded with unavailable denominator.
- [ ] External storage reserve, checksum/replay/restore, retention and
      ongoing incremental-vs-backfill refresh reconciled.
- [ ] Data OS canonical aliases/adjustment vintage/available_at checks accepted.
- [ ] Daytime/overnight non-NBBO labeling and market-hour calendar verified.
- [ ] Consumer comparison to existing Massive/Yahoo/SEC data without
      replacing accepted data source silently.
- [ ] Historical experiment leakage controls, symbol-time joins, corrections,
      and out-of-sample backtest semantics independently reviewed.
- [ ] Production process admission, continuity/return path, freshness health,
      downstream UI and machine proof, CI/independent review completed.

**No authenticated Tiingo prices/fundamentals or BOATS events have been downloaded.**
The later continuation acquired only the public symbol catalogue, recorded below.
Dummy fixture bytes written by tests are not sourced vendor market data. Data OS registry rows
should remain PROPOSED until actual production artifacts and valid receipts
exist; no downstream feed should be labeled PROVEN_LIVE from the code alone.


## Audited research consumer seam (no silent hindsight promotion)

Consumers can open a *specific* immutable source vintage from
lib/dataos/tiingo_reader.py::read_research_view(source, date, digest).
The reader verifies the materialization manifest's Parquet SHA-256, source
digest, recorded row count, source vendor, exact archive partition path,
and each row's source digest. A missing manifest means NO DATA, not
assumed successful publication.

The default INSPECTION purpose is noncanonical. The
RETROSPECTIVE_EXPLORATORY purpose requires acknowledge_hindsight=True.
PIT_BACKTEST always refuses in this research-only reader. A local manifest flag
cannot grant point-in-time or canonical-identity admission; that remains with
the existing canonical Data OS owner, not this L1 inspection API.
An R&D experiment may explore retrospectively retrieved historic returns
but must not call the result out-of-sample, live eligible, or PIT proven.

Example of a future offline reader after real source receipts exist:

    from lib.dataos.tiingo_reader import read_research_view
    view = read_research_view(
        "eod-bars", "2026-10-09", "<exact 64-char source SHA-256>",
        purpose="RETROSPECTIVE_EXPLORATORY",
        acknowledge_hindsight=True,
    )
    # view.rows preserves close_raw, close_tradj, capture vintage, and flags.

The materializer can also repair an interrupted write of a missing manifest
only after verifying that the extant Parquet rows agree with the immutable
raw source projection. Divergent orphan files are refused, not overwritten.

Live BOATS websocket support uses an optional, isolated dependency:
requirements/tiingo.txt. This package is not installed by the source
addition, and no vendor connection or live service was started.

## Public catalogue and offline request planning — current continuation

Public reference acquisition is distinct from the refused authenticated API probe.
The official EOD documentation links a keyless static ZIP; that public ZIP was
retrieved without any credential, API request or collector change at
2026-10-09T20:38:54.536319+00:00. Its bytes are stored on the external volume at
`/Volumes/Mastermind/evidence/tiingo-8698-public-catalog-20261009/supported_tickers.zip`.
SHA-256: `015cda96b828344e26f5937f426cbc40a7b8fe2edc9a023a342a3743799abcf0`.
Compressed size: 797,482 bytes; enclosed CSV: 5,039,605 bytes.
The reproducible bounded report is `research/tiingo/2026-10-09/PUBLIC_CATALOGUE_AUDIT.json`.

Measured public catalogue, not licensed/accessible price-history evidence:
- 108,970 records: 49,299 Stock; 9,791 ETF; 49,880 Mutual Fund.
- Currency rows: 101,766 USD; 7,147 CNY; 52 HKD; 5 AUD.
- 106,600 distinct ticker strings; 1,069 appear across multiple catalogue keys.
- 1,241 catalogue keys have conflicting date-range rows; these can reflect
  history/ticker reuse, not necessarily provider errors. They require resolution.
- 186 otherwise distinct catalogue keys have symbol spellings the current source
  adapter rejects. The adapter is unchanged; those names remain visible gaps.
- Oldest advertised history is 1960-01-29. That is a catalogue field, NOT a
  claim that this account has that history or that those prices were downloaded.
- Explicit USD/history-window filtering and ambiguity exclusions yield 96,937
  acquisition candidates. This is neither U.S.-only membership nor a PIT universe.
  Official docs warn the catalogue also contains reservations; metadata and real
  endpoint responses remain required for actual coverage.

`scripts/tiingo_reference_audit.py` now provides bounded ZIP/CSV validation,
metadata/date/currency/asset/ambiguity denominators and source-digest-bound
candidate pages. It is offline and writes no source data or identity records.
`plan()` now uses ex-date filters for dividend/split history, explicit minute
resolution for FX/crypto, bounded crypto symbol groups, deduplicated exact
identifiers, and early resource/date validation. Case-distinct vendor identifiers
are retained. `plan_page()` provides an exact-plan digest and bounded offline
pagination; it is NOT persistent execution progress or a scheduler. Live
`collect`, `boats_stream`, and `boats_subscribe_message` functions were verified
byte-identical across this change. The refused core collector is untouched.

Verification: **141 passed** across archive/views/reader/cohort/registry plus
new planning/reference suites, process 51325 exit 0. The existing 11 source
integrity failures remain unfixed and active release gates. New tests were wired
into the same `dataos-prospective-reference` CI lane, without waivers.

Primary documentation checked 2026-10-09:
- https://www.tiingo.com/documentation/end-of-day (catalogue reservations/bounds)
- https://www.tiingo.com/documentation/corporate-actions/dividends (ex-date filters)
- https://www.tiingo.com/documentation/corporate-actions/splits (ex-date semantics)
- https://www.tiingo.com/documentation/crypto (explicit resampling; nested priceData)
- https://www.tiingo.com/documentation/forex (historical bar endpoint)
- https://www.tiingo.com/documentation/fundamentals (permaTicker, annual quarter=0,
  as-reported/revised dimensions and USD-converted financial values)
- https://www.tiingo.com/documentation/boats (overnight-only bars, explicit volume)

The read-only corpus audit and additional-history projections are now implemented
and verified below. Authentication and the refused collector rewrite remain held;
no worker is delegated those denied effects. No live collector has been started.

## Cumulative execution checkpoint — 2026-10-09 latest continuation

**MISSION_COMPLETE: false. Production activation remains held.**
Same carrier: Macro PR #8698, branch `sol/tiingo-data-archive-20261009`, worktree
`/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009`.
This continuation began at `4be63058e8514c3f536547b5547d2d5fef4adec4` and published
its public-catalogue/planning milestone at
`c7c719ea5e882398f4d197443e0467e565ef8871`. The commit containing this checkpoint
is the cumulative source revision; its exact head is read back from PR #8698.
Protected source remains Mastermind `326c8469a21d7f50fc9ecb1848196bf1c6e66685`,
skillpack 1.0.1 / bootstrap 1. These repository changes grant no new authority.

### Delivered independent capabilities

The public reference ZIP and bounded catalogue census are physically retained
on the external volume, with a checksum-bound report in this PR. Exact-request
planning now has ex-date filters, explicit FX/crypto minute resolution, explicit
IEX historical volume columns, bounded multi-symbol groups and digest-bound
offline paging. That paging is navigation, not durable import progress.

Nine additional historical product projections now feed the EXISTING Parquet
materializer and research reader: BOATS bars, IEX bars, equity intraday reference
bars, FX bars, crypto bars, splits, distributions, fund-fee history and distribution
yield. New intraday prices use `vendor_open/high/low/close`, not a falsely admitted
raw/adjusted execution basis. FX/crypto volume units, source time text, currencies,
venue scope, cancellation status, declaration/payment/record/ex dates, nulls and
zero remain explicit. No new split factors are applied and no forecast, trading,
ranking or point-in-time admission is introduced. News remains with #8697.

Eighteen additive source/research contracts for these nine products are registered
under the existing Data OS registry. All **24 Tiingo contracts remain PROPOSED**.
Each research contract has the corresponding raw dataset input and named existing
reader/producer; fixture success never marks a production dataset as PRODUCED.

`scripts/tiingo_corpus_audit.py` is a read-only, bounded exact-plan comparison
against raw receipts. It distinguishes missing, invalid, empty, captured,
out-of-range/partial and conflicting-latest responses; verifies source bytes and
request context; counts crypto bars instead of top-level pairs; keeps observation
cutoffs and revisions explicit; reports partial scans and never certifies complete
history, source authenticity or point-in-time eligibility. It does not repair or
write any source artifact, invoke the vendor, read a key, create an import queue
or replace the canonical Data OS reader.

### Actual storage observation

At `2026-10-09T20:59:39.677788+00:00`, a read-only audit found that the intended
`/Volumes/Mastermind/market-data/tiingo` archive did not exist. An illustrative
six-symbol request plan (AMD, NVDA, INTC, MU, SPY, QQQ; 2000-01-01 through
2026-10-08) had **174 requests NOT_FOUND**: 162 EOD chunks, six fundamental
statement requests and six daily-fundamental requests. This sample is NOT a
claim that all those products are entitled/covered for each symbol, or a limit
on the user-requested full historical universe. There were no price/fundamental
receipts at the target. The audit created no archive directory.
Report: `research/tiingo/2026-10-09/CORPUS_AUDIT.json`.

### Verification and remaining red gates

- `PYTHONDONTWRITEBYTECODE=1 TMPDIR=/Volumes/Mastermind/agent-workspaces/tmp
  python3 -m pytest tests/test_tiingo_*.py tests/test_dataos_registry.py -q
  --tb=no --disable-warnings`: **187 passed, 11 failed**, process 93812 exit 1.
  The 11 failures are the pre-existing active ingestion-integrity regressions,
  not failures waived/hidden to publish a green result. All added projections,
  audit/planner and registry tests passed in this full run.
- `python3 -m pytest tests/test_check_script_import_pinning.py -q --tb=short
  --disable-warnings`: **11 passed**, process 97370. Direct external-directory
  `--help` for the reference and corpus audit CLIs succeeded; no source calls ran.
- Existing `dataos-prospective-reference` scope inference: **46 concrete
  dependencies, zero uncovered paths**. Existing unrun-suite census: **zero
  unwired Tiingo suites and zero other unwired suites** in the observed tree.
  Process 95803 exit 0. New suites are wired to the existing pyarrow-capable lane;
  the deliberately thin foundation lane and all release fences are unchanged.
- The core collector is unchanged. `collect`, `boats_stream` and
  `boats_subscribe_message` function text is byte-identical to the pre-resume
  `4be63058...` version. Process 95803 verified these assertions.
- These are local proof and public-reference evidence. Full required hosted CI,
  independent review and production acceptance are NOT claimed.

### Source defects and permission boundaries, preserved exactly

Eleven active red cases still cover body-only normalized keys aliasing different
tickers/query contexts; corrupt existing raw/normalized files accepted as present;
naive/invalid capture clocks; prefix-only rather than exact endpoint-context
checking; and missing source-observation context binding. The research reader
quarantines ambiguous content and always refuses PIT_BACKTEST, but does not repair
the producer. An unrestricted backfill is NOT safe yet.

The earlier authenticated Tiingo probe was explicitly refused by the connected
tool safety boundary before dispatch. It was NOT a Tiingo 401/403 and proves
nothing about the supplied key or subscription. The earlier rewrite of
`collectors/tiingo_archive.py` was separately refused before dispatch. Its unchanged
SHA-256 is `1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d`.
Neither effect was replayed, delegated or reconstructed through a different
carrier or fragmented patch. No routine Continue, new chat, mode change or user
reattestation is treated as permission to bypass a denial. No mechanism for lifting
these platform restrictions has been established in this session.

The Chairman's live Business Advanced/full-redistribution attestation remains
recorded. It is not being reopened as a purchase or blanket approval request.
Endpoint activation, historical coverage/availability, storage capacity, source
identity/quality and runtime/publication proof remain separate technical checks.

### Next dependency and stop frontier

The next critical implementation is the exact producer/context-integrity repair,
which remains blocked by the preserved collector-write restriction. It must be
resolved through a genuinely permitted controlling path, with all red cases
passing and required independent review/CI, before source activation. The separate
authenticated-probe restriction must then be resolved before endpoint/BOATS
qualification, earliest-history census, measured storage pilot, full resumable
backfill and canonical UI/machine consumer activation.

The source writer, vendor calls and production enrollment remain the limiting
lanes; further source-derived consumer proof requires real qualified captures.
No active child, live collector, scheduled task or background import exists. All
known modifying effects belong to this same PR/worktree and will be reconciled by
exact commit readback. The worktree is retained for continuation, not released.

DO_NOT_REDO: no new Tiingo branch/key, replay of denied effects, waived integrity
failures, claimed history from a catalogue, today's membership projected into past
universes, silent source replacement, or promotion from code/tests to PROVEN_LIVE.
Preserve the separate #8697 news owner and all 24 PROPOSED registry dispositions.
