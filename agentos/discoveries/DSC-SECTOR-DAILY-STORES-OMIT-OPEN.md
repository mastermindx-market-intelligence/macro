---
key: SECTOR-DAILY-STORES-OMIT-OPEN
claim: >
  The committed data/yahoo daily histories for SPY and all eleven sector ETFs
  at Macro 7f1e4ede020b53b1d86b39642e9c88f334f0d61a contain no opening-price
  column, so those exact stores cannot decompose overnight and regular-session returns.
falsifier: >
  Read the twelve immutable Parquet blobs named in daily_store_census.json
  and inspect their schemas; an opening-price field in one disproves the
  all-twelve statement. A different qualified store can resolve the capability
  gap but does not change this historical source observation.
so_what: >
  Obtain qualified opening anchors through the existing market-data owner
  before measuring overnight-versus-regular leadership. Do not infer opening
  prices from closes or mix unadjusted opens with total-return-adjusted closes.
  This is a specific source gap, not proof that every possible company store
  lacks intraday or opening data.
kind: data
verified_at: 2026-10-13
verified_by: >
  git show of the twelve data/yahoo/{symbol}.parquet blobs at the pinned
  baseline followed by pandas.read_parquet schema and date inspection;
  research/rotation_intelligence/intraday_sessions_20261013/daily_store_census.json
  retains per-file SHA256, row counts, date ranges and columns. All twelve
  were readable through 2026-10-12 and none had open.
scope:
  - macro
  - sector-rotation-intelligence
  - data/yahoo/
  - collectors/yahoo.py
confidence: verified
---

The collector's _extract method retains Close/Adj Close/Volume and optional
High/Low, not Open, at the same source revision. No collector, data file,
price basis, rights setting or production service was changed by this census.
Source schemas and aggregate metadata were inspected; market prices were not
exported into the research artifact. This observation is independent of the
failed production Terminal SSH read and does not supply its missing coverage
or latency proof.
