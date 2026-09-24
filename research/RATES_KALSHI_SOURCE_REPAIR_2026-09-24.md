# RIC Kalshi macro-release source repair — 2026-09-24

Operation: `rates-kalshi-price-schema-20260924-sol-004`.
Parent: `WS:RATES-INFLATION-COMMAND`.
Procedure pin: Mastermind `1a7d400294b0d37c460b963b8865b40a23173b58`,
Skillpack 1.0.1 / bootstrap 1.

## Capability boundary

Before this repair, Mastermind had a nominally append-only Kalshi macro-release
store, but current API quotes were not being converted to probabilities and
daily summary rows after the first null-strike row were silently deduplicated.
The source could therefore appear fresh by `asof_date` while carrying no usable
market-implied distribution.

After this repair candidate, the incumbent collector understands the current
fixed-point dollar quote fields while retaining legacy cent compatibility, and
its first-seen key preserves distinct null-strike summary rows across dates.
The existing `engine.release_market_context.get_kalshi_implied` consumer can
consume a valid current CPI/NFP/claims implied median from the same store path.

This is source/data repair only. It creates no new collector, market-data store,
forecast model, trade score, rank, size, gate, or policy-timing authority.

## Verified production-source defect

A read of the exact `origin/main` Parquet at the repair boundary showed:

- 6,889 stored rows spanning 2026-07-08 through 2026-09-24.
- 6,888 rows had `price_type=missing`.
- only one summary row survived, dated 2026-07-08;
- that summary had no implied median;
- therefore no valid historical daily Kalshi distribution exists in the committed
  store through this boundary.

A keyless live API probe on 2026-09-24 returned fields such as:

- `yes_bid_dollars="0.0200"`;
- `yes_ask_dollars="0.0300"`;
- `last_price_dollars="0.0300"`.

The incumbent parser read only `yes_bid`, `yes_ask`, and `last_price`
integer-cent fields. Those fields are absent in the observed current payload.

A separate two-date Parquet reproduction showed that pandas propagated the null
summary strike through `str.cat`; both composite keys became missing and the
second daily summary was treated as a duplicate. The repair materializes an
explicit null sentinel before concatenating the key.

## Repair contract

Price extraction now:

1. prefers the current `*_dollars` representation;
2. accepts only finite numeric probabilities in [0, 1];
3. falls back to legacy cent fields for compatibility;
4. keeps the existing mid -> last -> bid -> ask preference;
5. returns `missing` rather than emitting an impossible probability.

The append-only store remains first-seen. Existing pre-repair missing bracket rows
are NOT overwritten. We do not fabricate historical probabilities from today's
quotes. Distinct future summary rows append correctly because date/event identity
is no longer erased by the intentionally-null summary strike.

## Real source -> store -> consumer proof

The repaired collector was run against the real keyless Kalshi API with
`config.data_dir` redirected to an isolated temporary directory. No production
or tracked data was modified.

Observed in that isolated store:

- 102 rows total;
- 94 priced bracket rows;
- zero missing-price bracket rows;
- eight summary rows;
- all eight summaries had non-null implied medians.

The existing consumer then returned current reads for:

- CPI headline 2026-09;
- NFP 2026-09;
- initial claims 2026-09-24.

These are current market prices/context, not forecasts of the Treasury response.

## Historical evidence boundary

The July–September committed rows document event/bracket identity and collector
activity, but their missing prices are not valid prediction-market history.
They must not be used in a rates-direction or surprise-distribution backtest.

A future historical reconstruction is admissible only from a lawful timestamped
market-history source that preserves what prices were known at each cutoff.
Do not overwrite the original missing rows or infer past prices from final market
outcomes/current quotes.

That admissible path exists separately: Kalshi's official market-candlestick API
returns timestamped bid/ask/trade OHLC and documents a live/historical partition
for settled markets. A read-only batch probe for KXCPI-26AUG recovered all 15
bracket markets and 73 valid daily distributions from 2026-07-01 through the
2026-09-11 release close. This proves feasibility, not a backtest. Candlestick
daily closes have their own observation clock and must live in a separate
research artifact; they do not retroactively become the missing nightly first-seen
snapshots. See `DSC:RIC-KALSHI-HISTORICAL-CANDLESTICKS-AVAILABLE`.

Prospective accrual begins only after an accepted repair is live. This source can
then be tested for incremental value—especially distribution width/tail risk—
under a newly registered rates experiment. The existing research warning that
market-implied central tendency may be weak directionally remains a hypothesis to
test rather than an authority grant.

## Verification at authoring boundary

- `python3 -m pytest tests/test_kalshi_releases.py tests/test_release_market_context.py -q --disable-warnings --tb=short`
  -> 105 passed, 1 skipped, 16 warnings.
- real keyless API -> isolated Parquet -> existing consumer proof succeeded.
- exact current-main corrupted-store audit and pre-repair summary-key reproduction
  were preserved in `DSC:RIC-KALSHI-PRICE-SCHEMA-DRIFT`.
- the previously un-enrolled collector test file is added to the incumbent
  release-forecast CI job and path map; no new job/runner is created.

Independent review, hosted exact-head CI, merge, next-day canonical-store accrual,
and subsequent forecast-value testing remain separate gates.
