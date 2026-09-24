---
key: RIC-KALSHI-HISTORICAL-CANDLESTICKS-AVAILABLE
claim: >
  Kalshi's official market-candlestick API can reconstruct timestamped daily
  bracket-price histories independently of Mastermind's broken first-seen release
  snapshot store; a 2026-09-24 live batch probe for KXCPI-26AUG returned all 15
  bracket markets and 73 daily dates with enough bid/ask/last-close evidence to
  compute a daily implied median from 2026-07-01 through the 2026-09-11 close.
falsifier: >
  Run curl -fsS against
  https://api.elections.kalshi.com/trade-api/v2/events/KXCPI-26AUG?with_nested_markets=true
  and then the official /markets/candlesticks endpoint with period_interval=1440
  for those tickers. The claim is disproved if timestamped candlesticks are
  unavailable or cannot reconstruct valid bracket distributions.
so_what: >
  A future rates-event study may build a separate, clock-explicit historical
  Kalshi research dataset from official candlesticks instead of inventing values
  for the invalid first-seen parquet. Preserve daily-close identity and route
  settled markets across Kalshi's documented live/historical cutoff; never
  overwrite the original first-seen rows or claim candlestick closes equal the
  original nightly collection instant.
kind: data
verified_at: 2026-09-24
verified_by: "research/RATES_KALSHI_SOURCE_REPAIR_2026-09-24.md:98"
scope:
  - macro
  - rates-inflation-command
  - kalshi-historical-research
  - engine/release_market_context.py
confidence: verified
---
