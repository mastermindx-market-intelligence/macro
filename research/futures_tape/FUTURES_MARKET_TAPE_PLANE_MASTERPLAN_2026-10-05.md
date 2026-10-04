# Futures Market Tape Plane — F0/F5 Masterplan

**Program:** `WS:FUTURES-MARKET-TAPE-PLANE`  
**Status:** implementation carrier active; source-bearing acquisition not yet proven  
**Date:** 2026-10-05  
**Owner:** Data OS / Macro market-data plane

## 0. Outcome

Build one reusable futures market-data substrate, beginning with ES, that can support
Macro/Event Intelligence, Temporal Grain, Prophet context, Entry Radar and later
microstructure research without making any of those consumers source owners.

The end state is:

```
source feeds
  -> immutable private raw partitions
  -> normalized exact/provider identities
  -> explicit contract/continuous semantics
  -> deterministic bars + event windows
  -> compact PIT-safe context features
  -> existing consumers
```

No raw futures observation has rank, gate, size or trading authority at birth.

## 1. Current estate and why this is not redundant

Mastermind already has:

- a live six-symbol Yahoo futures display relay in `app/tape.py`;
- a large ThetaData options estate and flow calibration;
- Massive stock-market trades/quotes/aggregates under a separate stock entitlement;
- Data OS identities including `FUT:<MIC>:<root>:<YYYYMM>`;
- Temporal Grain's G/A/K/D scientific split, where D is the data/instrument plane;
- active Prophet regime × indicator × timeframe research.

Those are complementary, not substitutes for a governed futures archive.

The Yahoo relay is presentation/reference infrastructure and does not supply a deep,
versioned research store. ThetaData remains canonical options data and must not be
displaced. Current internal Massive records describe the incumbent entitlement as a
Stocks product; public Massive documentation now exposes Futures as a separate product,
so Futures entitlement must be measured rather than inferred.

## 2. Source roles

### LSE

Initial classification: **secondary_deep_history / vendor_continuous / research-only**.

The official LSE SDK documents futures in the catalog, raw tick `history()` exports,
Parquet bulk jobs with resume support, and live websocket ticks. Current public terms
permit internal research, trading and model training, including commercial use, while
forbidding redistribution/resale/competing feeds. The public free databank currently
advertises 10 downloads/hour with an export ceiling of 1,000,000 rows. F1 therefore
defaults raw-tick planning to one calendar day per export and fails closed on any
at/over-cap result instead of accepting a valid-looking truncated Parquet file.

**Critical F0 unknown:** exact `ES.F` history span and roll/adjustment semantics.

Until that is proven, `LSE_ES.F` is not an exchange contract and is not the source for
execution-grade roll logic.

### Massive Futures

Preferred exact-contract source when a business/enterprise entitlement is actually
observed.

The public Futures API separates products/contracts/schedules from trade and quote
entitlements. The exact-contract API is therefore the right source for modern contract
identity, tick size, sessions, trades and BBO if Mastermind's current commercial
relationship includes it.

F0 includes a read-only probe that reuses the existing Massive probe's key resolution,
authorization headers and error scrubbing. It creates no second entitlement manifest.

### ThetaData

Remains canonical for options. If ThetaData later launches useful recent futures depth,
that may become a bounded recent-depth input. It does not erase the need for pre-2017
deep history or Mastermind-owned continuous-series semantics.

## 3. Storage ruling

Primary physical storage is operator-owned local storage selected by
`MMX_FUTURES_TAPE_ROOT`. No host path is hard-coded in source.

The current attended host census on 2026-10-05 observed:

- `/Volumes/Mastermind`: ~3.6 TiB total, ~673 GiB available;
- `/Volumes/WD 5TB`: ~323 GiB available;
- `/Volumes/Worktrees`: ~105 GiB available.

That is sufficient to qualify an ES-first plane but not permission for an unbounded
multi-terabyte BBO crawl. The producer therefore carries a free-space reserve gate
(default 100 GiB) before bulk acquisition.

When the planned larger SSD is available, it should become the hot research root and the
older device should become a mirror of critical raw/canonical partitions. A large CMR
HDD is preferred later for cheap cold redundancy. R2 remains optional for selected
private backup/derived artifacts, not the required raw primary.

## 4. Repository implementation

### `lib/dataos/futures_tape.py`

Provider-neutral primitives:

- explicit source roles;
- immutable/provisional partition states;
- external-root resolution;
- capacity fence;
- safe partition paths;
- SHA-256 receipts;
- atomic manifest writes;
- manifest audit.

### `scripts/futures_tape_ingest.py`

Bounded operator CLI:

- `storage`
- `probe-lse`
- `backfill-lse`
- `normalize-lse`
- `derive-bars`
- `audit`

The CLI deliberately does not install packages, create credentials, create a scheduler,
publish raw tape, or alter consumers.

### `scripts/probe_massive_futures.py`

Read-only Futures entitlement measurement that reuses the existing
`massive_entitlement_probe.RestProber` and credential/scrubbing logic. It checks ES
products/contracts and only tests trades/quotes after an exact contract ticker is
returned.

## 5. On-disk contract

```
$MMX_FUTURES_TAPE_ROOT/
  raw/
    source=lse/
      symbol=ES.F/
        window=<start>_<end>/
          export.parquet
          export.parquet.manifest.json

  normalized/
    ticks/
      source=lse/
        instrument=LSE_ES.F/
          date=YYYY-MM-DD/
            part-000.parquet
            part-000.parquet.manifest.json

  derived/
    bars/
      instrument=LSE_ES.F/
        freq=1min/
          date=YYYY-MM-DD/
            part-000.parquet
            part-000.parquet.manifest.json
```

Raw LSE exports remain source-shaped. Normalization creates canonical timestamp/price
columns separately. Derived bars are rebuildable.

Exact CME contract storage later uses Data OS `FUT:<MIC>:<root>:<YYYYMM>` identities and
must not overwrite the LSE continuous lane.

## 6. Scientific and consumer value

### Macro / Event Intelligence — highest initial priority

The tape enables deterministic event windows around CPI, NFP, FOMC, Treasury/refunding,
geopolitical shocks, overnight gaps and cash-open transitions. The high-value product is
reaction geometry and analog retrieval, not exposing billions of raw rows.

### Temporal Grain

A single tape can be reconstructed into multiple session-aware grains, reducing a major
confound between timeframe, anchor, kernel memory and vendor plane.

It does not retroactively prove historical TradingView WMT/silver parity. New cohorts
must use their own exact recipe and source receipts.

### Prophet / Entry Radar

Consume compact PIT-safe context only, for example overnight return, realized volatility,
gap, VWAP deviation, trade intensity and shock state. Raw ES ticks never become a
universal ranking vote.

### Microstructure

Trades alone support price path, volume-at-price, VWAP and trade intensity. Continuous
OFI, quote duration and liquidity withdrawal require quote-event/BBO data. Full CME BBO
history is therefore not part of F1.

## 7. Wave sequence

### F0 — source/storage qualification + producer implementation

Done when:

1. source code and tests merge;
2. external SSD root/capacity receipt is recorded;
3. LSE `catalog("futures")` row for `ES.F` is captured;
4. LSE key/terms are operator-approved for this internal use;
5. existing Massive credential is probed against Futures products/contracts/trades/quotes;
6. no source is mislabeled as exact-contract truth.

### F1 — bounded LSE ES backfill

Use explicit windows. `plan-lse` / `backfill-lse-range` default to one-day raw-tick
windows and a bounded per-invocation export-job budget. Every successful export writes a
checksum manifest including the exact requested start/end boundaries. Restarting skips
only a partition whose receipt re-verifies the bytes; a missing/corrupt receipt forces
reacquisition. An export returning at least 1,000,000 rows is treated as capped/incomplete
and must be retried at finer granularity. Normalization unions all receipted raw chunks
that contribute to a UTC day before it writes that daily partition; the daily output is
FINAL only when FINAL source-request intervals cover the whole UTC day without a gap,
otherwise it remains PROVISIONAL and is rebuilt as more chunks arrive. At completion,
run `audit`.

Backfill remains held if the catalog span or roll semantics invalidate the source.

### F2 — exact CME modern plane

Only if entitlement exists. Ingest ES contract specifications and exact contract trades.
Build versioned Mastermind continuous series from explicit roll laws; never silently
replace `LSE_ES.F`.

### F3 — derived bars + event windows + context

Materialize only named consumer grains. Start with 1min, 5min, 30min, 1h, 4h and session
outputs; add 1s only if an approved consumer requires it.

### F4 — consumer qualification

Priority order:

1. Macro/Event Intelligence
2. Temporal Grain
3. Prophet context
4. Entry Radar context
5. Microstructure/BBO experiments

Each consumer must use its own existing evaluation/authority owner.

### F5 — perpetual accrual

Bind the producer to the existing persistent scheduler/host and the existing data-health
plane. Live/provisional capture and post-session/final archive are separate states.
Compact consumer artifacts may publish remotely; raw tape stays private.

## 8. Acceptance gates

### Storage and immutability

- capacity reserve passes before bulk acquisition;
- no raw partition is silently overwritten;
- every finalized file has row count, byte count and SHA-256 receipt;
- interrupted writes use `.partial` then atomic rename;
- manifest audit detects mutation/corruption.

### Source identity

- provider-continuous and exchange-contract identities stay different;
- every source carries source symbol and source role;
- exact contract rows carry explicit venue/root/contract month in the later CME plane;
- roll methodology is versioned and reproducible.

### Data quality

- timestamps normalize to UTC;
- price is required;
- invalid/missing rows are dropped only in normalized derivatives, never silently from
  source bytes;
- duplicate treatment is deterministic;
- source discrepancy is classified, not averaged away.

### Operational

- rerun skips valid partitions unless `--force`;
- no key appears in Git, receipts or stdout;
- source failures fail the affected lane closed;
- the health plane detects a stopped expected accrual once F5 is armed.

## 9. Explicit non-goals

F0/F1 do not build:

- a Futures OS;
- another scheduler or event ledger;
- a full CME quote lake;
- depth-of-book;
- tick-driven trading;
- a public raw-data API;
- a new outcome evaluator;
- automatic signal promotion;
- storage procurement.

## 10. Current blocker and exact return condition

The code carrier can be completed without source credentials. **Empirical source
qualification cannot.** The next source-bearing action requires an ops host with a
valid `LSE_API_KEY` and the existing Massive credential.

The exact commands after merge are:

```bash
export MMX_FUTURES_TAPE_ROOT=/path/to/external/ssd/futures_tape
python -m scripts.futures_tape_ingest storage
python -m scripts.futures_tape_ingest probe-lse --symbol ES.F
python -m scripts.probe_massive_futures
```

Only after those receipts are accepted may F1 run a real `backfill-lse`.
