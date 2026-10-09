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
support EOD rows, fundamental statements, daily fundamental metric rows and
BOATS websocket event rows. All carry a source digest, capture clock,
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

**No real Tiingo data was downloaded in this branch/session.** Dummy fixture
bytes written by tests are not sourced vendor data. Data OS registry rows
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

## Cumulative execution checkpoint — 2026-10-09 continuation

MISSION_COMPLETE: false. This is an implementation/recovery checkpoint, not
production acceptance. Original carrier remains Macro PR #8698, branch
`sol/tiingo-data-archive-20261009`, worktree
`/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009`.
Recovery began from published commit `22adbf2a9304564f3977b9d791cf943bf61b2383`.
Current protected procedure was read from Mastermind
`326c8469a21d7f50fc9ecb1848196bf1c6e66685`, compatible skillpack 1.0.1 / bootstrap 1.

### Verified deltas in this continuation

- Recovered the earlier uncommitted research reader, cohort builder, bounded
  WebSocket rejection tests and interrupted-Parquet-manifest recovery code.
- Added a consumer-only quarantine for identical raw body hashes claimed by
  different ticker/request/capture contexts. The reader refuses ambiguous
  evidence instead of returning the wrong ticker's prices. This does NOT
  repair the producer's content-only normalized output key.
- Removed the false point-in-time admission path: setting a manifest boolean
  can no longer authorize PIT_BACKTEST. Inspection rejects asserted PIT or
  canonical identity flags, and row/source capture clocks must agree.
- Added delisted/inactive permaTicker cohort tests, including ambiguous IDs,
  missing identifiers, duplicate rows, checksum failure and dry-run behavior.
  These are current vendor-reference acquisition cohorts, not historical
  security membership or canonical Data OS aliases.
- Fixed repo-root import pinning for all three Tiingo executable scripts.
  Their offline catalog/help modes now run from outside the Macro directory.
- Wired ALL Tiingo tests, including the still-failing integrity regressions,
  into the existing `dataos-prospective-reference` CI job. Kept the deliberately
  thin `dataos-foundation` dependency environment unchanged. No waiver, xfail,
  skipped integrity suite, replacement scheduler or extra CI job was added.

### Evidence, with passing and failing denominators kept separate

1. Archive/views/reader/cohort/registry tests: **107 passed**, 8 warnings.
   Exact command: `python3 -m pytest tests/test_tiingo_archive.py
   tests/test_tiingo_views.py tests/test_tiingo_reader.py
   tests/test_tiingo_vendor_cohort.py tests/test_dataos_registry.py -q
   --tb=short --disable-warnings`. Studio process 87890 exited 0.
2. Repository-root import guard: **11 passed**, 8 warnings.
   `python3 -m pytest tests/test_check_script_import_pinning.py -q
   --tb=short --disable-warnings`; process 88942.
3. New ingestion-integrity regression suite: **11 failed, 1 passed**.
   `python3 -m pytest tests/test_tiingo_ingestion_integrity.py -q
   --tb=no --disable-warnings`; process 88942 ended with exit 1.
   The manifest-only PIT escalation now fails closed. The other tests remain
   real red release gates, not tests waived to obtain a green result.
4. Existing CI scope functions infer **34 concrete dependency paths** for
   `dataos-prospective-reference`, with **zero uncovered paths**. Existing
   `gated_unrun_suites()` reports zero unwired Tiingo suites and zero other
   unwired suites in this observed source tree. Process 92979 exited 0.
   This is local ownership/closure evidence, not full hosted CI acceptance.
5. Direct offline entrypoint proofs were run from `/Volumes/Mastermind`:
   `python3 <worktree>/scripts/tiingo_ingest.py catalog`, and `--help` for
   `tiingo_materialize.py` and `tiingo_vendor_cohort.py` succeeded.
   No provider request, credential read, live stream or production import ran.

### Material unresolved defects

The original producer and normalizer are NOT safe for an unrestricted backfill.
The red tests demonstrate that identical body bytes can alias two tickers or two
asReported query selections into one normalized file; existing corrupted raw or
normalized files can be reported as idempotently present; capture clocks are not
validated as aware timestamps; and source/endpoint checking accepts a mere prefix
instead of exact ticker/query context. Source-observation identity also needs a
stable context binding rather than the body checksum alone. Eleven failing test
cases represent these related defects, not eleven independent root causes.

The read-side quarantine prevents ambiguous evidence from being consumed; it does
not make the raw writer or full backfill ready. Additional scope remains: true
resumable acquisition progress instead of repeatedly starting a bounded prefix,
endpoint-specific date parameters, complete vendor-symbol/earliest-date census,
real record quality/coverage measurements, historical availability and Data OS
identity admission, durable runtime enrollment, and downstream production proof.

### Actual tool gates and effect reconciliation

The earlier authenticated Tiingo probe was explicitly refused by the connected
tool safety boundary before dispatch. Its result is NOT a Tiingo 401/403 and does
not show a subscription or key failure. This continuation did not replay it.

A source rewrite of `collectors/tiingo_archive.py` was also explicitly refused by
OpenAI's safety checks before dispatch in this continuation. Readback confirms
that file is unchanged at SHA-256
`1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d`.
No accepted part of that proposed rewrite exists. Do not recreate the same denied
change through smaller patches, another helper/file, a second tool, account,
provider, worker or session. Any resumption of that effect requires a genuinely
permitted resolution at the controlling permission boundary; a routine Continue,
mode change, new chat or ordinary user authorization is not effect clearance.

Independent changes were limited to CI/import wiring, tests, documentation and
read-only consumer refusal. No production data, user-visible prices, live alerts,
trades, source aliases, runtime state or installed service was changed. There are
no active child workers, background imports, scheduled tasks or unresolved remote
writes associated with this checkpoint.

### Ownership and next action

Tiingo News Intelligence already has a separate open carrier, Macro PR #8697,
`sol/tiingo-news-quality-20261009`; preserve its existing financial_news/qbus
ownership and do not duplicate its identity, historical-observation or publisher
work here. PR #8698 owns this archive/research ingestion work only.

Next critical action is resolution of the precise collector-write permission
gate, followed by a reviewed source/observation-integrity repair that turns all
red regression cases green. Only after those code gates, independent review and
required hosted CI pass may the separate authenticated live-probe gate be
resolved and live endpoint/BOATS qualification, measured storage pilot, complete
backfill and canonical consumer activation proceed.

DO_NOT_REDO: do not recreate a second Tiingo branch or key file, repeat a denied
probe/write, silently accept content-only identity, discard the red regressions,
claim current metadata is a historical universe, or declare code/test success to
be live-data delivery. Preserve this same PR and its exact published revision.
