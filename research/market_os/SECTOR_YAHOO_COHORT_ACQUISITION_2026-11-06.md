# Explicit Sector Yahoo cohort acquisition

Date: 2026-11-06. Mission: [#10779](https://github.com/mastermindx-market-intelligence/macro/issues/10779). Parent source base: `d9236cdb6a8c64e4543cf93d2f537b7b11400812`. This is inactive source preparation; it does not transfer collection ownership or publish data.

## Existing owners and recovered source

The implementation extends `collectors.yahoo.YahooAdapter`, `lib.store` and `lib.yahoo_runtime_profile`. It reuses the existing Yahoo download shape, dual-basis extraction, US calendar, profile membership, store merge policy and verified-snapshot context. It introduces no collector, scheduler, repository-data writer, manifest, retry queue or selection owner.

The original immutable candidate was `379a75f9849a4f8644643441a1ddd56eea48bd1e`, patch SHA-256 `5be57d21fb3ebf2d3302a5328a35ed00b0731cab54ebb2753175967227e4501e`. The parent recovered its Yahoo/store source after earlier worker effects were reconciled. The candidate's subset/window acceptance and broad no-I/O claims were not adopted. Parent corrections implement the stricter actual cohort/history contract below. No quota-failed repair's private source or result was consumed.

## Explicit acquisition interface

```python
adapter = YahooAdapter(yahoo_config=captured_yahoo_configuration)
result = adapter.acquire_cycle_benchmarks(
    SECTOR_CLOSE_TICKERS,
    prior_frames=explicit_prior_mapping,
    evaluation_instant=aware_utc_clock,
    completed_sessions_only=True,
    period="1mo",
)
```

The exact cohort is owned once by `SECTOR_CLOSE_TICKERS`: XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY, SPY, QQQ and IWM. Subsets, extra symbols, duplicate/case-normalized aliases and vendor identity collisions are refused.

The prior mapping must have exactly those keys. `None` explicitly denotes absence. An empty, malformed, future-tailed or invalid prior is not silently treated as absence. Priors are copied before any provider request; acquisition never resolves “latest,” reads repository stores or substitutes a cache for a missing key.

The explicit constructor copies its configuration instead of calling `config.load()`. At acquisition entry, one immutable `YahooRequestSettings` captures validated batch size, retry count, backoff and basis tolerance. Every initial/recovery download and the receipt uses that same value. Runtime download does not touch the instance's WTI metadata state. The legacy no-argument constructor and download defaults retain their current behavior.

This is an acquisition-time contract. The incumbent import graph still includes `lib.config`, whose existing module initialization may read dotenv/environment state. It is not a claim that all module imports are free of ambient effects.

## One completed-session target

The target is captured once from `market_session.expected_session("US", evaluation_instant)`. The current US local year and selected target year must have verified published calendar coverage. The existing US calendar owner settles published half-days at 14:00 ET and other sessions at 17:00 ET. No historical NYSE policy is edited.

Every accepted final history must end at that exact target. Matching an old prior tip does not establish freshness. Future/developing provider rows are excluded by the explicit completed-session policy. Missing target observations refuse admission; the calendar cannot manufacture them.

Historical rows are checked through the same existing session owner. Its historical fallback remains available for older years without published notices; those years are not newly claimed to have verified annual coverage. Both prior and final histories reject weekend/holiday rows under that owner.

## Both price bases and full history

The adapter's existing `_extract` remains the sole conversion:

| Provider field | Store field | Meaning |
|---|---|---|
| Adj Close | `close` | Total-return adjusted |
| Close | `close_price` | Split-adjusted, dividend-unadjusted |
| Volume | `volume` | Existing optional volume field |

The strict runtime branch requires both genuine price columns. It never clones a missing basis. Flat data is accepted only for an actual single-symbol request; a flat batch cannot be replicated across 14 symbols. Ambiguous MultiIndex identity and duplicate columns are refused.

Both bases must be numeric, positive and finite. Missing historical observations may be removed from the refreshed span, but cannot borrow values from the old vintage. The target row must have both bases. The original fresh-span start is captured before null/session filtering.

The shared `capture_sector_history` validates unique, ordered, timezone-naive midnight session indexes, dual bases, declared tip and a minimum of **1,000 observed trading sessions**. Acquisition and `bind_snapshot` use this same minimum. It is a new runtime admission contract, not a description of what the old nightly collector guaranteed.

A short refresh is combined with prior history only when strict comparisons on both price columns establish alignment. The strict comparator uses the actual positive denominator, so small adjusted prices cannot hide a large percentage shift behind the legacy denominator floor. The legacy boolean guard keeps its historical policy.

## Merge and bounded recovery

`store.merge_frames` is the pure extraction of the incumbent merge. Reads, outlier quarantine, path creation, parquet writes and availability capture remain outside it.

The default legacy path retains `combine_first`. Runtime explicitly requests `overwrite_overlap=True` with the original fresh-span boundary: old rows survive only before that boundary. A null or omitted refreshed row cannot be filled from old history. The actual Yahoo legacy adapter inherits the default append policy; runtime overwrite is an explicit stricter choice, not claimed legacy parity.

Absent prior history, no comparable overlap, either basis shift, invalid/missing observations or insufficient depth trigger at most one bounded `max` recovery after a window attempt. An initial max attempt is not repeated. Existing per-request retries use the captured policy; no new queue or retry owner exists.

A max response must still contain the target, meet minimum depth, reach the prior archive's earliest date and preserve at least its observed row count. It is never prefixed with an incompatible older vintage. A thin response labeled max is refused. Failed acquisition returns no frames or partial accepted cohort; the caller retains its prior selected generation.

## Result and publication boundary

The result separates requested/returned/failed members, per-member reasons, request periods, basis comparison, target and observed archive bounds. Its known clocks/settings are explicit. Vendor publication time, first availability and correction time remain unknown.

Returned frames are detached private copies. Frozen dataclass bindings and top-level mapping proxies do not make DataFrames or nested metadata immutable.

This result is not a verified generation. Only the existing publisher's verified input snapshot may establish a `VerifiedYahooCohort` identity and bind it for calculation. The acquisition method does not call `store.upsert`, `run_adapter`, repository data/config writers, fallback collectors, reports, ledgers, graders or publication selection.

## Verification and remaining integration

Focused controlled-provider tests cover exact cohort/prior contracts, genuine dual bases, batch identity, target/half-day boundaries, frozen request settings, full-history recovery/refusal, archive preservation, null/omitted span ownership, nonsession priors, small-price comparison and private copies. They trap ambient store/config paths. Actual pre-extraction `upsert` and `basis_shifted` functions are retained from exact source base in `tests/fixtures/base_store_d923.py` for output/error comparison.

Final verification passed **291 tests**, with one existing skip and 14 existing pandas-deprecation/temporary-directory cleanup warnings. The run includes the existing Yahoo extraction, availability, universe backfill, freshness, store guard and holiday-retention suites. The source-linked commission record carries exact command/counts and log digest. Controlled provider fixtures are not a live-data availability receipt.

The profile remains legacy. Remaining work includes binding all relevant store/engine reads before cache/path access, excluding the transferred symbols from every legacy fetch/write/retry path, coherent private input publication and R2 transport, anti-downgrade/drain/rollback fencing, broad/member inputs, producer assembly and source-to-screen beta proof. No runtime ownership or deployment changes occur in this slice.
