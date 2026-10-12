# Factor Atlas S2 — trade-print minute reconstruction and real-source candidate gates

**Status:** SYNTHETIC_ONLY / ORIGINAL_TRADE_SOURCE_NOT_ADMITTED / DRAFT_HOLD. Original Macro PR #8677. This is a proposed native research consumer, not an ingestion integration, admission engine, fund-flow truth, backtest, customer release, or trading model.

## Why this is materially different from the Tiingo source-fitness work

Original Tiingo `equity-intraday-bars` may contain **derived reference OHLC** from validated quote midpoints or actual prints; its 1-minute L1 volume, raw/adjusted basis and rights have not been qualified for true traded-price notional. Source-clock completeness (1,560 nominal RTH slots on the already captured AAPL/MSFT/NVDA/SPY cohort) does not prove genuine trade-price/volume eligibility, original decision-time availability or actual beneficial-owner demand.

The S2 source-independent `prototype/trade_print_minutes.py` consumes the **existing** `quote_reference.TapeTrade` shape, with the caller's separately selected `updates_trade_ohlc` and `included_in_share_volume` eligibility claims. It **does not choose** eligible sale conditions, revisions, source archives, tickers, market calendar, exchange entitlements or a normalized real-time price feed. Those are incumbent Data OS/source-owner decisions. No independent live stream, quote signer, trade-correction selector, model registry, rights store or identity system is introduced.

**Its only arithmetic output is on `input_class=SYNTHETIC_FIXTURE`.** A caller presenting `OWNER_UNVERIFIED` inputs receives `SOURCE_UNVERIFIED_NOT_REDUCED`, no price levels, no gross, no minute rows. Even synthetic price/volume strings carry mandatory negative market/PIT/license/customer/trading authorities. The module returns no `m.Bar` and cannot silently feed the BVC or Terminal pipelines.

## Exact geometry tested

- SIP timestamps are kept as integer UTC nanoseconds and grouped into exact 60-second UTC source slots within the *caller-supplied, unverified* original `source_preflight.IntakeScope` calendar.
- The **existing** `quote_reference._trade` validates price, decimal-size share volume, session and monetary basis. Decimal 0.25 share does not become integer zero or floating-point rounding.
- **Both** original owner selection bits must explicitly say this print updates trade OHLC and counts toward the same selected interval-share population; missing or incompatible bits withhold the print. The method never asserts those bits are truly source-authenticated.
- An in-scope non-current/cancelled correction, unknown sale condition or unaligned TRF print is **withheld**, never promoted to a consolidated-price/turnover input. A duplicate original trade identity requires the incumbent revision selector.
- Event-SIP tie collisions with different prices can give valid subset high/low but **not** a fabricated first/last price. Unobserved minutes remain absent, never observed market zeros. The returned grid distinguishes all candidate-print minutes, minutes with an explicitly matched eligible synthetic subset, and minutes containing **only withheld/unknown** prints; the latter never count as qualified coverage.
- In as-observed mode, only event and receipt clocks known by the requested cutoff may enter. Future/later-received appended rows do not change an earlier research fingerprint; corrected-history mode never invents `known_at_ns`.
- The candidate trade gross is the **exact synthetic print price × decimal size sum**. BVC's bar-close × share-volume is a distinct proxy: in the controlled two-print case, executed gross is 100.025 while close × volume is 100.03. Treating them as numerically interchangeable would invalidate a calibration study.
- Results are still **candidate matched prints**, not a full consolidated universe, NBBO, aggressor truth, institutional buying, exchange-licensed availability, or authenticated dataset rights.

## Real source route — candidate assessment, not authority

The following are **public-source capability observations** at 2026-10-12 UTC, not proof of Mastermind entitlement, vendor data quality at a historical date, deployed provider selection, or paid acquisition.

1. **First evaluate incumbent Massive/Polygon tick-trade and quote capabilities through their existing original owner**, without reopening previously platform-denied private source files. Official Massive /v3/trades/{ticker} docs describe per-trade prices, decimal fractional sizes, exchange, conditions, participant and SIP nanosecond timestamps. The separate quotes endpoint supplies observed bid/ask and SIP clock fields. This is a potential trade-print/nanosecond quote reference—not evidence that the current account has actual usable permissions, captured data, sale-condition parity or rights for these four stocks. Sources: https://www.ny5.massive.com/docs/rest/stocks/trades-quotes/trades and https://www.massive.com/docs/rest/stocks/trades-quotes/quotes and https://massive.com/knowledge-base/article/how-does-massive-handle-fractional-share-trades
2. **NYSE Daily TAQ as retrospective consolidated scientific benchmark**, *if separately licensed*: NYSE describes CTA/UTP consolidated U.S. equities trades, quotes, NBBO and administration messages, including cross-exchange activity, delivered from the previous session. Historical Daily TAQ does NOT provide an October 9 as-observed decision receipt when first received later, and no procurement is authorized by this document. Source: https://www.nyse.com/data-products/catalog/daily-taq
3. **Direct venue-level feeds for partial-universe calibration, not consolidated flow truth**. Databento Nasdaq TotalView-ITCH documents per-venue trades and top-of-book; even orderbook-level aggressor labels at a single venue cannot stand for the whole U.S. consolidated market. Its US Equities Summary supplies daily volume, not minute-by-minute market-wide trade observations. Source: https://databento.com/docs/examples/equities/equities-introduction and https://databento.com/docs/venues-and-datasets/equs-summary
4. **Do not substitute Tiingo's consolidated derived reference prices** for an actual traded-price source merely because its RTH timestamp grid is complete. Tiingo explicitly describes quote-mid **or** trade-print construction for reference OHLC and statistical liquidity bids/asks, not the original SIP NBBO or pure print stream. Source: https://www.tiingo.com/documentation/websockets/equity-realtime-stock-data

## Evidence required from the incumbent before a single REAL internal study

The existing Data OS/price/identity/right owners must return one unambiguous source-selected, legally usable small four-symbol source episode, not a typed assertion from this consumer:

- Exact AAPL/MSFT/NVDA/SPY **canonical listed issuer/ETF IDs**, source vendor aliases, applicable market/MIC, event-time and source-first-known/effective validity; do not guess SPY's missing snapshot listing ID.
- Source byte SHA/immutable receipt and first-observed/vintage, selected correction/finality, reader completion/selected-prefix digest, unadjusted price plus **exact fractional share size**, venue and TRF classification, exchange sale-condition policy indicating independently what may update OHLC and volume.
- Calendar and auction/pre/RTH/AH eligible 1-minute denominator, out-of-session treatments, source completeness and missing/no-trade conventions. One source sample does not establish complete U.S. lit/TRF coverage.
- Dataset-use, derivative-calculation, cross-product/private-display/redistribution rights tied to the actual Mastermind agreement. Signed vendor terms and technical account readiness are distinct.
- Matched timestamp-qualified quote/NBBO rights and clocks for the independent quote-side comparator. A price-derived buy fraction and a quote-based aggressor estimate are not the same as observed institutional ownership.
- At least one explicitly **prospectively captured** episode if as-observed historical claims are desired; previous Oct 9 Tiingo snapshot first received Oct 11 remains retrospective only.

**Then** the owner can commission a positive source-admitted native caller into existing `source_preflight → intake_bridge → window_pressure` and independent S6 scientific review. This research module deliberately does **not** activate that path. S6 #8696 remains DRAFT/REVISE; Terminal consumer, rankings, alerts, sizing, trading and customer outputs all remain held.

## Verification and continuity

Test-first missing-module collection error confirmed, followed by the new synthetic cases in `prototype/test_trade_print_minutes.py`; all assertions are negative-authority or print geometry and never involve vendor/API traffic. Register the suite with the **existing** `.github/workflows/factor-atlas-reference.yml`, not a new CI plane. Native log/source digests are retained in `evidence/native_trade_print_minutes_tests.json` and the existing package manifest.

**DO_NOT_REDO:** earlier platform-denied original Massive/Polygon source-file reads and identity inspection, original P4/P6 repairs and BOATS packaging, and the effect-unknown original Executive science-review summon. These instructions are fence evidence, not permission to change carriers or repeat denials. Keep #8677 Draft/HOLD; no merge, deploy, production source capture, vendor purchase or new rights claim.
