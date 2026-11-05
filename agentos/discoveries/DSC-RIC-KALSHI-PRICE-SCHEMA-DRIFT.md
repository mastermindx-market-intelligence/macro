---
key: RIC-KALSHI-PRICE-SCHEMA-DRIFT
claim: >
  At Macro ed48709749cc47a41038b1899664cc756e0b186d the Kalshi macro-release
  collector is dark as a probability source: the live v2 API emits fixed-point
  *_dollars price fields while the collector reads legacy cent fields, and its
  null-strike summary dedup key collapses distinct dates. The committed current-main
  store through 2026-09-24 therefore contains bracket identities but not a usable
  historical probability/distribution series.
falsifier: >
  Run git show origin/main:collectors/kalshi_releases.py and inspect _mid_price;
  run curl against the keyless Kalshi v2 markets endpoint for
  KXCPI/KXPAYROLLS/KXJOBLESSCLAIMS; and read the exact origin/main Parquet bytes.
  The claim is disproved if the pre-repair collector parses the fields actually
  returned and the store has dated priced brackets plus distinct valid summary rows.
so_what: >
  Do not use the pre-repair Kalshi parquet as a rates-direction, surprise-direction,
  calibration, or event-risk history. Repair the incumbent collector and summary
  identity first, preserve the invalid historical rows, then begin truthful
  prospective market-implied accrual; any historical reconstruction needs an
  independently sourced timestamped market-history owner rather than interpolation
  or overwrite of first-seen rows.
kind: data
verified_at: 2026-09-24
verified_by: "research/RATES_KALSHI_SOURCE_REPAIR_2026-09-24.md:25"
scope:
  - macro
  - rates-inflation-command
  - collectors/kalshi_releases.py
  - data/prediction_markets/kalshi_releases.parquet
  - engine/release_market_context.py
confidence: verified
---
