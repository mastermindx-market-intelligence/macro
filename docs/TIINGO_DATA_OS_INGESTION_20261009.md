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

## Cumulative execution checkpoint — 2026-10-10 read-side continuation

**MISSION_COMPLETE: false. Live ingestion, unrestricted backfill and production
activation remain held.** Same carrier: Macro PR #8698,
`sol/tiingo-data-archive-20261009`, worktree
`/Volumes/Mastermind/agent-workspaces/sol/tiingo-ingestion-20261009`.
This continuation started from published
`4a2979e1839ce2c7bb07f65af7b4e85e95ee332b`; no replacement branch was created.
The commit containing this checkpoint is the cumulative source revision, verified
by the same PR's exact-head readback. Protected Mastermind procedure remains
`326c8469a21d7f50fc9ecb1848196bf1c6e66685`, skillpack 1.0.1 / bootstrap 1.
The same immutable ACTIVE_EXECUTION and SESSION_RELIABILITY blobs were reconciled;
no source law, source custody, admission or permission fence was changed.

### Accepted scope and preserved earlier capabilities

The official public catalogue, its census, bounded offline request planning,
permaTicker acquisition cohorts, nine added historical projectors and read-only
corpus audit remain on this carrier. Earlier catalogue/acquisition facts remain
in the sections above and `research/tiingo/2026-10-09/` evidence files. A catalogue
record is not downloaded price history, account endpoint access, or a historical
survivorship-safe universe. All **24 Tiingo Data OS contracts remain PROPOSED**.
News Intelligence still belongs to separate carrier #8697; nothing was moved into
an alternative news, identity, publisher, execution or scheduler owner.

This continuation was limited to the existing pure research projectors,
read-only research consumer, read-only corpus auditor, their existing test suites,
and this checkpoint/evidence. The core collector, live ingestion script,
materializer and 11 failing producer regression cases are byte-identical to the
starting revision. No rejected collector rewrite was recreated in another file,
no provider call was made, and no raw or normalized production data was written.

### Read-side capability changes

- EOD/fundamental views now reject malformed strings, booleans, non-finite
  numbers and nonzero values that underflow to zero, instead of quietly treating
  them as absent or valid numeric observations. Explicit nulls, actual zero,
  negative financial results and new numeric metric names remain supported.
- Share volumes retain exact int64 values, including decimal/exponent JSON
  representations above float64's exact-integer range. Raw and vendor-adjusted
  prices remain separate; neither becomes an executable or PIT price authority.
- Statement fiscal years/quarters, release dates, metric identifiers, explicit
  values and duplicate release/period/section/metric keys are checked. Quarter 0
  is preserved for annual statements; different release vintages stay distinct.
  Invalid or duplicate asReported query selections are refused, never guessed.
- Daily fundamental identity fields are no longer misclassified as numeric
  metrics. Explicit response identity mismatches are refused, while an exact
  vendor permaTicker request can retain a different display ticker without
  inventing a canonical historical alias.
- Duplicate JSON fields and malformed date/time components are rejected by the
  pure readers. Original date labels, timezone offsets and nanosecond text are
  retained. Dates are not silently converted into historical availability clocks.
- The common view contract is now `mastermind.tiingo.research_views.v2`.
  The research reader rejects legacy/mismatched view schemas in manifests and
  rows, even when file checksums have been recomputed. This is **refusal, not
  migration**: the unchanged materializer may still report an older artifact as
  existing, and that artifact is not thereby eligible for this reader.
- Corpus-audit v2 does not hide a newer invalid response behind an older valid
  one. It distinguishes INVALID_LATEST_CAPTURE, INVALID_UNORDERED_CAPTURE and
  UNCONFIRMED_LATEST_PARTIAL_SCAN. An older invalid response does not erase a
  valid later capture, and after-cutoff observations remain excluded. The audit
  shares strict source-date semantics with the views, still writes nothing,
  and explicitly does not claim field-semantic or full-history validation.

Direct work was retained as PRINCIPAL_JUDGMENT for this bounded source-schema
interpretation and regression repair. No worker was assigned the denied collector
or credential effect. Public primary references were rechecked:

- https://www.tiingo.com/documentation/end-of-day — volume type and distinct raw
  versus adjusted fields.
- https://www.tiingo.com/documentation/fundamentals — quarter 0 annual reporting,
  dynamic metric codes, report release labels and as-reported/restated dimensions.

These references establish public schemas, not this account's active endpoint
entitlements or actual historical payload quality.

### Verification and observed effects

Current evidence: `research/tiingo/2026-10-10/READ_SIDE_VERIFICATION.json`.
The prior verification artifact remains a historical receipt, not overwritten.

- Full `tests/test_tiingo_*.py tests/test_dataos_registry.py` run: **266 passed,
  11 failed; pytest exit 1**. The same 11 failures remain active producer/context
  integrity gates. No test was skipped, marked xfail or waived to create a green
  result. The new cases include failure reproductions and valid controls.
- The first EOD/fundamental-quality regression run reproduced 49 failing cases;
  subsequent read-schema/date checks reproduced five more, and the independent
  audit-order cases reproduced four. They describe related defects and controls,
  not a claim of that many independent root causes.
- Final all-suite log:
  `/Volumes/Mastermind/evidence/tiingo-8698-readside-20261010/pytest-all-final.log`,
  SHA-256 `1e1fe5e019ac2f4ebcb0cbe9fad009ed5ecff795922dfaf3df837d6e10aaefc8`.
- Existing import-pin and CI dependency/unwired-suite checks are recorded in the
  current evidence JSON with exact results. No new CI job or scheduling mechanism
  was created; the deliberately thin foundation lane is unchanged.
- Hosted CI for the starting head reproduced the 11 known Tiingo failures in
  run 37990949442, job 114025209580. Job 114025209832 separately failed the live
  quote board-cap tests, outside this scoped change. No test waiver or unrelated
  source edit was used to bypass either. New-head hosted CI and independent
  review are still not accepted.
- The production archive was still absent at the read-only check in this
  continuation. Earlier six-symbol/174-request absence evidence is preserved;
  no new vendor corpus, fresh prices, active websocket, collector or background
  import is claimed.

### Source defects and permission boundaries, preserved exactly

The producer still needs context-bound output identity, corruption handling,
strict capture-clock and exact-request checks; the normalized writer can still
alias identical bytes from different ticker/query contexts. Pure-reader
quarantine/schema checks do not repair those source writers. Full resumable
acquisition and actual history/coverage/retention remain unproven.

The earlier authenticated Tiingo probe and rewrite of
`collectors/tiingo_archive.py` were separately refused by tool safety controls
before dispatch. Both were already reconciled as unapplied. No new attempt at
either effect occurred in this continuation. The core file remains SHA-256
`1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d`.
These are not Tiingo 401/403 responses and establish no key/subscription failure.
No mechanism for lifting the exact platform restrictions has been established;
routine Continue, renewed ordinary approval, mode/chat change or another carrier
is not treated as clearance. The Chairman's Business Advanced/full-redistribution
attestation is preserved without requesting a new purchase or blanket approval.

### Next dependency and stop frontier

The independently permitted read-side quality work is saved. The next useful
critical effect remains repair of the blocked source writer; further activation
requires the separate authenticated-probe path, exact-candidate CI/review,
actual BOATS and history qualification, measured storage pilot, full resumable
backfill and canonical machine/user consumer proof. Repeating unchanged tests or
adding another catalogue/planning artifact does not unlock that dependency.

Preserve the exact blocked effects until a genuinely permitted resolution exists;
no alternate-file implementation, alternate tool/account/provider, delegated
replay or source replacement may obtain the denied effect. No active child,
scheduled task, live collector or background reasoning exists. The same worktree
is retained, not released. Known source writes and publication are reconciled by
exact commit/PR readback before final reporting.

DO_NOT_REDO: do not recreate the branch/key, retry denied actions, waive the 11
producer regressions, overwrite prior evidence, infer complete history from the
catalogue, promote current membership to a historical universe, or call these
fixture-verified research readers PROVEN_LIVE. Keep the PR draft and the 24
registry entries PROPOSED until real acceptance evidence exists.


### October 10 additional read-only corpus audit correction

The existing corpus auditor could report NOT_FOUND for an unseen request when
receipt scanning was truncated. Equally, a sampled corrupt receipt could be
described as finally INVALID_CAPTURE although a later valid revision might be
beyond the scan cutoff. Both statuses were stronger than the bounded evidence
could prove. On every incomplete receipt scan, all selected requests now
receive UNCONFIRMED_LATEST_PARTIAL_SCAN with latest_capture null; observed
diagnostic counts remain in scan. A complete scan still distinguishes
NOT_FOUND, INVALID_CAPTURE and valid/empty/partial captures normally.
This is a pure auditor correction, not ingestion, source mutation, historical
coverage proof or a new control plane.

Three new synthetic tests verify absent/invalid outcomes under a scan limit
and retention of a definite invalid status under a complete scan.
Focused audit + read-side suites: 154 passed (process 86117); full
Tiingo + registry suite: 269 passed, 11 failed (process 87192).
The same 11 failed test identities remain the unrepaired core
producer/context-integrity release blocks.

Full-suite evidence log on the external drive:
/Volumes/Mastermind/evidence/tiingo-8698-readside-20261010/pytest-partial-scan-guard.log
SHA-256 92a4ec9c80eacb0e9ddd76493530dbd383113e7245bb77a6304c8c3f6823c0d1
The core collectors/tiingo_archive.py remains unchanged at SHA-256
1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d.
No previously refused effect was retried or delegated. This change does not
supersede the rights/availability limits or authorize a release. Keep
Macro PR #8698 draft and all 24 Tiingo Data OS entries PROPOSED.

Separate Tiingo News PR #8697 reports an authenticated HTTP 200 for a bounded
news sample, evidence of news API token functionality only. This is not
proof of EOD, fundamentals, BOATS, or public-news redistribution entitlements,
and does not permit replay of the separately refused authenticated probe.


### October 10 research reader rights-admission repair

An independent defect in the existing research consumer allowed editable Parquet
manifest metadata to report redistribution_admitted=true, even though only the
incumbent licensing/right-to-publication owner can admit redistribution.
Pure read-side tests reproduced this false-positive without any provider call.
The research reader now refuses a manifest that asserts rights and always
returns redistribution_admitted=false for ordinary inspected/retrospective views.
It additionally refuses tampered source_vendor, dataset_source and
source_rights_admitted fields on materialized research rows, even after an
attacker recomputes the editable Parquet checksum. These are research-only
source/rights lineage checks; they do not repair the raw writer or qualify an
actual vendor contract.

Four new synthetic regressions failed before this consumer fix and now pass.
Focused research-reader/history-view/auditor tests: 158 passed (process 59412).
Full Tiingo + registry suite: 273 passed, the SAME 11 historical producer
integrity failures remain (process 70292).
Full-suite log:
  /Volumes/Mastermind/evidence/tiingo-8698-readside-20261010/pytest-reader-rights-20261011.log
SHA-256 e8ff4e744fbd3cb8e4a93389ad54a0283c3dfc7b50ae17ee1e1ff7d6e84e626a

The entire core collector remains at SHA-256
1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d.
No source data, key, BOATS session, vendor requests, new scheduler or
producer-path workaround was touched. Keep all 24 Data OS contracts PROPOSED and
PR #8698 draft until real entitlement, producer integrity, and runtime evidence.


### October 11 UTC — bounded retrospective history research API

Delivered a direct independent research consumer in the *existing* Data OS
Tiingo reader: TiingoResearchHistory and read_research_history. No alternative
dataset registry, archive, import queue, job lifecycle or canonical price basis
was created. A researcher can explicitly select multiple **already existing,
receipt-verified** EOD or daily-fundamental Parquet partitions, inspect
historical rows across request windows and retain exact capture-vintage
lineage. This makes the stored fragments useful for retrospective experiments
once real captures exist; it is not production collection or true PIT backtesting.

The consumer:
- Requires the full exact (capture date, SHA-256) reference list, source and
  vendor symbol, requested market-date bounds, an explicit timezone-aware
  observed-before cutoff, and acknowledge_hindsight=true.
- Reuses read_research_view for each partition (real raw receipt context,
  output hash, research schema v2, source ticker/rights/identity refusal);
  it never calls Tiingo or reads any API key.
- Rejects captures after the cutoff, invalid source observation dates,
  future market dates and rows outside original vendor request-date bounds.
- Deduplicates only economically identical overlapping market-date records,
  retaining the latest *captured* provenance within the supplied cutoff.
  Conflicting source vintages, including adjusted-price corrections or
  partial changes to a daily-fundamental metric set, fail the entire assembly
  rather than being silently last-write-wins or synthesized across vintages.
- Uses exact int64 volumes, daily metric granularity and null versus zero
  from the existing validated research rows, and bounded input/row budgets.
- Reports market-session-completeness, historical identity, redistribution
  and PIT backtest eligibility as FALSE, always. Source-capture time is NOT
  historically known-at time. This reader does not cover statements yet,
  infer the full vendor security universe, or claim missing sessions are known.

Verification: 307 passed / **the same 11 known producer-context failures** in
the full Tiingo + Data OS registry suite (process 92333, exit 1).
External-drive log:
  /Volumes/Mastermind/evidence/tiingo-8698-readside-20261010/pytest-history-assembler-accepted-20261011.log
SHA-256 fe112eced5f52681a29aad68f60719c62ae4ce4f71678a72804af83fa427f8ac
The new standalone test_tiingo_history.py suite was wired to the pre-existing
dataos-prospective-reference job and its trigger closure, **not** a new CI lane.
Independent hosted CI/review is still owed; fixture pass does not certify
real vendor entitlement, data maturity or corrected production source writer.

The denied core collector rewrite/authenticated Tiingo probe were not replayed
or reconstructed. The source collector remains unchanged at SHA-256
1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d.
All 24 proposed Data OS contracts remain PROPOSED, and the archive remains
absent. There is no actual historical corpus, live BOATS capture, collector
worker, deployment, or release authorization. Keep #8698 draft; Tiingo News
#8697 remains separately owned. The remaining user-critical gate is a genuinely
permitted collector repair and authorized vendor qualification, followed by
storage pilot, full history imports, CI/review and real consumer proof.


### October 11 UTC — historical financial-statement vintage timeline

The existing Tiingo research reader now also exposes a bounded
TiingoStatementTimeline and read_research_statement_timeline. It uses the
same *already stored, immutable receipt-verified* Parquet views and an explicit
capture reference list. This adds retrospective statement-release research
without another source writer, archive, historical universe, queue, temporal
authority or point-in-time backtest admission.

Tiingo's public fundamentals documentation differentiates
asReported=true (the **current period as originally reported**) from
asReported=false (Most-Recent, with **prior periods pulled from newer reports**):
https://www.tiingo.com/documentation/fundamentals

Every timeline therefore requires a definite as_reported boolean. A missing,
ambiguous or mixed asReported request is refused, including in the source
receipt/normalized rows. Vendor-claimed public-release labels, annual
quarter=0 and quarterly 1-4, fiscal years, statement family, metrics, real null,
zero and negative values remain distinct. Separate vendor release labels for
the same fiscal period are retained as separate revisions. A conflicting
same-release/fiscal-period value or metric-set change across captured source
vintages **fails** rather than silently choosing today's restatement. Identical
overlapping reports are deduplicated with latest capture receipt provenance
under the explicit observed-before cutoff.

Source release labels are **vendor claims, not experimentally validated
upstream availability**. This API always reports:
historical_known_at_proven=false, pit_backtest_eligible=false,
historical_identity_admitted=false, redistribution_admitted=false and
report_history_completeness_proven=false. It refuses future release claims,
dates outside original vendor request windows, unqualified capture timestamps,
missing exact partitions and mismatched vendor identifiers. Research-only
inspection remains available with hindsight acknowledgement; there is no
new production application route or implied forecast/trading eligibility.

Twenty additional synthetic statement timeline tests are present in the
**existing** test_tiingo_history.py suite and its already-wired Data OS CI
lane. Targeted run: 54 passed (process 4670). Full Tiingo + registry:
**327 passed, same 11 known producer-integrity failures** (process 5992,
pytest exit 1); no skip/xfail or red-test waiver.
External-volume test log:
  /Volumes/Mastermind/evidence/tiingo-8698-readside-20261010/pytest-statements-timeline-20261011.log
SHA-256 7480bc35d0a69f35a7d123df8efa2d990ae69a4065766f9b2ab67ba9eb8a83d6

The current external volume had approximately 397 GiB free at the verified
read-only capacity check; this is NOT a validated full-history or BOATS
storage budget. Reserve capacity and obtain measured authorized vendor pilot
sizes before sustained capture. Original collector unchanged SHA-256
1932ff35a5b2d0eff3204253c51924e945db10df07b7f05858d2f3ea3290e86d.
No data archive exists at the target path, no credential or authenticated
vendor request was used, the original explicit tool denials stand and remain
DO_NOT_REDO. PR #8698 stays draft, all 24 Tiingo contracts PROPOSED,
and Tiingo News remains separately owned by #8697. Next gate is genuinely
permitted producer repair plus live BOATS/history entitlement qualification,
followed by real archive and consumer integration proof.
