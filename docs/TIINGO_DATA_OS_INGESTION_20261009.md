# Tiingo → Mastermind Data OS: bounded source acquisition and research views

**Date:** 2026-10-09
**Current implementation carrier:** macro branch sol/tiingo-data-archive-20261009
**Source authority:** existing Macro Data OS lib/dataos/identity.py, price.py,
temporal.py, registry.py, config/dataset_registry.yml.
**Physical archive:** /Volumes/Mastermind/market-data/tiingo
**Credential:** operator-only /Volumes/Mastermind/.mastermind_private/tiingo/api_key,
file permissions 0600. Never check secrets into Git or print them.
**Claimed commercial plan:** Chairman reports Business Advanced with full redistribution;
actual per-product rights/limits are not independently established.

## Current truthful states

| Capability | Current state | Proof vs pending |
|---|---|---|
| Tiingo credentials available to source adapter | BUILT_NOT_PROVEN | Owner-only file exists, but vendor authentication **not attempted successfully** |
| Historical EOD ingestion | BUILT_NOT_PROVEN | Bounded REST path, raw archive, fake-response tests; no live response |
| Fundamentals metadata/statements/daily | BUILT_NOT_PROVEN | REST source paths; as-reported default, research Parquet; add-on not verified |
| BOATS snapshots / historical bars | BUILT_NOT_PROVEN | Vendor path and 1m bar builder; entitlement not verified |
| BOATS trade/quote/break websocket | BUILT_NOT_PROVEN | Bounded streaming client and immutable segmented raw receipts; not connected |
| IEX / equity intraday / FX / crypto / news / corporate actions / fund fees | BUILT_NOT_PROVEN | Documented REST source paths, raw archive; no live data |
| L1 research Parquet | BUILT_NOT_PROVEN | Offline materialization passing fixture tests; four families only |
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
