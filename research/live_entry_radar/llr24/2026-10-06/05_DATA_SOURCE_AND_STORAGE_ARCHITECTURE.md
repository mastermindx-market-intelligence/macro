# 05 — Data sources, storage and cost architecture

**Ruling:** qualify existing stocks rights and history first; add real overnight venue trades and top-of-book quotes; collect deeper book data only for a bounded challenger that can beat the L1 baseline. Storage is usually a smaller decision than entitlement, clock fidelity, integration and evaluation labor.

## 1. Current ownership and admission

The current Macro entitlement record says the operator confirmed a broad Massive enterprise license, including specified display/redistribution, non-display research/model uses and retention. This is an inherited rights record, not proof that every endpoint, direct venue feed or exchange addendum is available. Verify the particular dataset against that record; do not reopen the entire license question or publish private contract text. [D01]

Existing `engine/entry_radar/vendor_minutes.py` provides adjusted aggregates for bounded C3 episode windows, a 180-session limit and settled-cache basis checks. It is useful source plumbing, not a market-wide point-in-time minute store. The current optional Databento options collector uses OPRA trade-plus-NBBO observations and a cost guard, but its reduced output collapses timing lineage; code and an old credit comment do not establish current entitlement or an active research service. [D02–D03]

## 2. Vendor/source decision table, checked 2026-10-06

| Source | Documented useful capability | Current estate / unresolved admission | Ruling |
|---|---|---|---|
| Massive stocks | Trades, quotes/NBBO and aggregate history; vendor advertises deep U.S. history | Existing enterprise rights recorded; actual endpoint entitlement, condition history, PIT vintage and 20:00–04:00 venue coverage need receipts | Primary daytime reuse candidate; a marketing depth claim does not qualify the specific research window |
| Alpaca `boats` | BOATS historical bars, trades and quotes plus live actual venue feed on the applicable plan | Broker/feed entitlements and earliest usable BOATS history must be established; general “since 2016” history is not BOATS depth | Practical bounded overnight L1 candidate |
| Alpaca `overnight` | Indicative latest quotes, with delayed access distinctions | Indicative prices are not executable quotes | Display context only where honestly labelled; excluded from executable-low labels |
| Tiingo BOATS | Beta venue-native BBO/last; tick websocket; overnight OHLC history, 20:00–03:59 | +$9/month add-on requires Power/Commercial base; base price, business rights, full historical tick depth and beta support need qualification | Low-cost research candidate if actual feed/retention requirements pass |
| Databento `OCEA.MEMOIR` | Native BOATS trades, bars, L1/L2/L3 and status; history from 2025-08-24 | Historical usage starts at advertised $0.40/GB; actual schema/range quote and licenses required; live requires US Equities Plus/Unlimited | Strong full-fidelity overnight benchmark; buy no depth merely because it exists |
| Databento U.S. direct/SIP alternatives | Venue books, consolidated and selected composite products | A direct venue or “near NBBO” composite is not the SIP NBBO; assess coverage and timestamps per dataset | Matched daytime L1/depth challenger only after incumbent source comparison |
| Existing Theta/options owners | Chain/OI/vol/GEX and trade/NBBO observations | October source-admission reference is synthetic-only; prior OA observations and C15 dispositions must be reused | Optional context under C15 owner; no second options store |
| Native auction feeds | Imbalance, paired volume, indicative clearing price and auction phase | Entitlement/history/known-time are separate from ordinary bars | Narrow close/open-context pilot, never certify an OHLCV proxy as an auction feed |

Sources: [W06–W13, W15–W17, P34–P45]. Prices are public reference points, not procurement authorization or a current commercial quote. Alpaca's published $99/month individual plan is not an assumed business redistribution license. Tiingo's $9 is an add-on, not a total bill. Databento plan amounts are deliberately omitted because the generic pricing page's product tabs did not establish an unambiguous U.S. equities price for this use.

Tiingo's convenience `tngoLast` may substitute a calculated midpoint; historical `low` and session fields are vendor calculations. Use native bid/ask/trade fields with their separate quote and sale clocks for labels. Its websocket exposes trade breaks and raw sale conditions, which must survive normalization. Databento's venue depth exposes displayed orders on that venue, not hidden global liquidity, dealer inventory or a guaranteed queue fill. [W08–W11]

## 3. Three investment tiers

**Tier A — minimum research viability.** Existing qualified 1-minute trades-derived bars for a date-specific broad U.S. universe, a security master, corporate actions, session calendars, benchmark/sector bars and timestamped catalysts already admitted by their owners. Add actual overnight bars plus feed/status coverage. This supports price-path exploration, not buyer-executable conclusions. Sample quote/trade windows are needed immediately to measure how misleading bar lows are. Preserve an explicit price-only evidence mode.

**Tier B — minimum execution-aware capability.** Continuous ordered trades and real top-of-book quotes with displayed sizes, separate event/receipt clocks, corrections, status and access scope for the top 50/100/300 research universes. Complete the same across overnight and daytime for each claimed session. A quote sampled only when a trade prints is inadequate for continuous OFI, time-weighted spreads or recovery of quote liquidity.

**Tier C — optional complexity.** Native depth/MBO for a small matched subset and predeclared event windows; auction indications where relevant; accurately timed options context. L2/L3 survives only if it improves the same cost-aware task beyond Tier B at fixed coverage and latency. Full-market L3, packet capture retention forever, and a transformer training cluster are not prerequisites.

**Suggested initial sampling:** 50 names for source qualification, including liquid ETFs, mega caps, high-beta liquid stocks, smaller/liquidity-poor controls and names unavailable overnight. Expand to 300 only after the source receipts pass. Select historical universes as of each date; today's top-300 membership is not a historical universe. Market-wide census uses all eligible names and reports absent/delisted/unmapped coverage separately.

## 4. Physical architecture

Reuse the incumbent data/storage owners. Keep raw immutable vendor records in source/date/schema partitions with manifest checksums and entitlement pointers. Build normalized records keyed by canonical instrument and event/receipt times; revisions append rather than overwrite. Derived bars/features reside in versioned Parquet partitions. DuckDB/Arrow or the incumbent query layer reads bounded date/symbol groups; avoid millions of tiny per-symbol/per-minute objects. The existing Radar pack/spool remains the operational episode path. Research files do not become a parallel live quote hub.

Three retention layers are proposed: a 30-session SSD working set for active research; object storage for the complete accepted historical vintage and source receipts; compact feature/prediction/outcome manifests retained for every evaluated trial. Cache keys include source vintage, calendar, adjustments, feature implementation and universe version. A live prediction must reference its exact source basis even after the cold source is compacted.

Measure download bytes, decompression, normalization, sorting, query scan and feature computation separately. Before choosing hardware, benchmark a fixed 50-name/20-session slice and report wall time, peak memory, rows/sec, peak ingress, disk bytes and checksum. No host-throughput benchmark was run in this commission. A design target is that incremental inference has ample headroom within Radar's cycle; current 8–9-minute passes on a nominal five-minute timer make synchronous heavy model work inappropriate. [I784-timing]

## 5. Reproducible cost scenarios

The attached [calculation](analysis/storage_model.py) and [full scenario table](analysis/STORAGE_ARITHMETIC.md) use decimal GB, 252 economic sessions/year, 6.5 RTH + 9.5 pre/post + 8 overnight hours, one compressed copy and an intentionally full 1,440-bar daily grid. They are planning assumptions, **not measured feed volume**. Real holidays, venue gaps, sparse names and activity bursts change the bill.

| Lane | Assumed events/sec/name: RTH / pre-post / overnight | Stored bytes/event | Names | GB/day | Annual GB | Standard object storage/month at full retention |
|---|---|---:|---:|---:|---:|---:|
| 1-minute bars | 1/60 in each segment | 64 | 3,000 | 0.276 | 69.7 | $1.05 |
| Trades | 2 / 0.25 / 0.05 | 40 | 300 | 0.681 | 171.7 | $2.58 |
| L1 updates | 10 / 1 / 0.1 | 48 | 300 | 3.904 | 983.7 | $14.76 |
| L2 incremental depth | 25 / 2.5 / 0.3 | 64 | 300 | 13.039 | 3,286.0 | $49.29 |
| L3 order events | 50 / 5 / 0.6 | 48 | 300 | 19.559 | 4,928.9 | $73.93 |

| Tier B names | GB/day | Annual GB | 30-session SSD working set | One / two object copies per month |
|---:|---:|---:|---:|---:|
| 50 | 0.769 | 193.7 | 23.1 GB | $2.91 / $5.81 |
| 100 | 1.538 | 387.5 | 46.1 GB | $5.81 / $11.62 |
| 300 | 4.613 | 1,162.4 | 138.4 GB | $17.44 / $34.87 |
| 3,000 | 46.127 | 11,624.0 | 1,383.8 GB | $174.36 / $348.72 |

The same average rate is used across universes solely to make scale transparent; the most active 50 names can have much higher per-name traffic. The machine-readable table therefore includes 0.2× and 5× event-rate scenarios. At 300 names, the 5× scenario is about 23 GB/day and 5.8 TB/year before a second copy. Raw+normalized duplication, indices, manifests, backups and operational reserve add to the displayed one-copy figures. MBO is not intrinsically larger than every L2 representation: frequent full-depth snapshots may be larger than efficient order deltas.

Cloudflare currently lists Standard storage at $0.015/GB-month and Infrequent Access at $0.010, with IA retrieval at $0.010/GB and a 30-day minimum. Standard A/B operations are $4.50/$0.36 per million; IA $9/$0.90. Egress is listed free, which does not erase operations, compute or upstream vendor charges. [W13]

At these rates the IA storage saving equals about one-half of the stored volume retrieved per month; repeated scans can eliminate the saving, before operation charges. Use Standard for active partitions and consider IA only after actual query behavior is measured. Existing SSD capacity is a capacity allocation, not free durable backup; no hardware purchase price is assumed here.

Vendor billing may use **uncompressed binary bytes**, whereas the table uses compressed retained bytes. Databento explicitly makes this distinction. A public “from $0.40/GB” OCEA rate cannot price all SIP, Nasdaq, options, licensing or live plan costs. The later data owner must request one bounded, schema-specific estimate, record it before download, and stop at its approved ceiling. This commission incurred no subscription or data-purchase commitment. [W10, W12]

## 6. Source-admission output and failure behavior

One owner-native receipt per source/session/period must record entitlement scope; requested versus returned security/date coverage; empty versus unavailable distinctions; event/receive precision; corrections and condition eligibility; sample raw/normalized hashes; spread/size distribution; no-trade intervals; quote-age distribution; sequence gaps; timestamp regressions; broker-access assumptions; actual bytes and estimated full-period cost.

For quote-dependent heads, missing size/conditions/continuity means **not executable-qualified** even if a chart can draw a line. For descriptive bars, a gap is a gap. For overnight, a displayed quote is not proof of reachable liquidity. A failing source can still support a narrower declared task; it cannot be silently upgraded by combining it with a better source from another session.
