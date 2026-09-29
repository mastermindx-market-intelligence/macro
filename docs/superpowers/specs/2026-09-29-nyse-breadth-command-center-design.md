# NYSE Breadth & Participation Command Center — Design

**Date:** 2026-09-29
**Chairman approval:** 2026-09-29 (`Approved, continue`)
**Macro base:** `942956ea69f6cd118a153ff3eceb58bfe4813f60`
**Mastermind law source:** `mastermindx-market-intelligence/Mastermind@0b3bdf78be9b86bc3672f224ddacf80854a4c3fb`
**Sol skill index blob:** `c74ca3054ef8111a0601886d8eb7946698669962`
**Authority:** display and research context only. No rank, allocation, Prophet, Risk Radar, sizing, execution, alert, or trade authority.

## 1. Mission

Build a truthful NYSE new-high/new-low breadth plane and integrate it into Macro's existing Markets evidence surface. The system must explain whether visible index price is broadly confirmed beneath the surface across exchange, index-size, and sector universes, while preserving point-in-time identity, membership, price basis, source clock, and coverage truth.

The first production slice must be useful immediately, but it must not relabel the incumbent S&P constituent proxy as NYSE breadth. `NYSE` means `XNYS` only. NYSE American (`XASE`) remains a separate universe.

## 2. Existing owners reused

This feature creates no parallel identity, calendar, price, live-poll, event, publication, or control plane.

* **Identity:** `lib.dataos.identity.VendorAliasTable` and `data/reference/{security_master,vendor_aliases}.parquet` remain the canonical security identity owner. Massive `share_class_figi` and `composite_figi` are source observations, not a new stable-ID allocator.
* **Calendar:** `lib.nyse_calendar` remains the XNYS-session owner.
* **Listing observations:** Massive `/v3/reference/tickers` is the point-in-time roster source. `collectors.symbol_directory` remains an independent prospective exchange-directory evidence source and reconciliation comparator.
* **Prices:** `data/massive_stock_day` remains the canonical whole-market daily OHLCV store. Its flat-file bars are raw/unadjusted, so exchange breadth normalizes them on read with dated Massive split observations; it never creates a second canonical close store.
* **Corporate actions:** Massive `/stocks/v1/splits` provides point-in-time split observations. `data/exchange_breadth/source_splits.parquet` is a refreshable source cache for this data product, not a second identity or price authority.
* **Index breadth:** `data/{breadth,midcap_breadth,smallcap_breadth,russell_breadth}` remain owners of S&P 500/400/600 and Russell breadth.
* **Live snapshot:** `scripts.live_breadth_poller.fetch_full_market` remains the sole market-wide snapshot fetch. The XNYS live sidecar consumes the same in-memory snapshot.
* **Historical observations/outcomes:** Market Memory remains the durable experience owner. This program emits display/research artifacts only and does not create a second experience ledger.

## 3. Universe contracts

### 3.1 `nyse_operating`

Primary XNYS operating-equity cohort. Massive source rows must satisfy:

* `primary_exchange == "XNYS"`
* `market == "stocks"`
* `active == true` for the requested point-in-time date
* `type in {"CS", "ADRC"}`

`CS` is Common Stock and `ADRC` is American Depository Receipt Common in Massive's stock ticker-type catalog. The allowlist is versioned in config/code and surfaced in receipts.

### 3.2 `nyse_all_issues`

Comparator cohort: every active XNYS stock-market ticker returned by the point-in-time endpoint, regardless of type, except rows whose ticker or required exchange identity is missing. This cohort intentionally includes preferreds, ETFs, funds, units, warrants, rights, ETNs, structured products, and liquidating trusts. The UI must label it `all listed issues` and disclose the broader composition.

### 3.3 Point-in-time identity key

A source row resolves in this order:

1. existing canonical `security_id` through the incumbent dated alias space for the requested session, when available;
2. Massive `share_class_figi` as `FIGI:<value>`;
3. Massive `composite_figi` as `CFIGI:<value>`;
4. unresolved.

No synthetic permanent security ID is minted. Unresolved rows remain in listed/coverage counts but are excluded from identity-continuous 252-session calculations. Receipts expose the unresolved count and bounded examples.

Ticker changes do not reset an entity when the resolved identity key stays the same. Ticker reuse does not splice two securities because intervals with different identity keys remain separate.

## 4. Membership observation ledger

`data/exchange_breadth/universe_intervals.parquet` is a provider-observation ledger, not an identity authority. One row describes one contiguous run of confirmed XNYS membership:

```text
universe_key
entity_key
security_id
share_class_figi
composite_figi
ticker
name
ticker_type
primary_exchange
currency
valid_from_session
valid_to_session
source
source_rules_version
```

Bounds are inclusive XNYS session dates. Adjacent sessions are compressed only when identity, ticker, type, exchange, and cohort membership are unchanged. Missing roster sessions are never bridged. A failed roster fetch leaves the ledger untouched.

`data/exchange_breadth/_state.json` records successfully observed roster sessions and exact source/request receipts. It is checkpoint state for this data product, not a queue or control plane.

## 5. Price and metric semantics

### 5.1 Price and split-adjustment basis

The first accepted basis is `massive_stock_day.raw_daily_aggregate + massive_splits.pit_split_adjusted`. Massive flat files are unadjusted, while Massive aggregate REST results can be split-adjusted. This program uses one explicit semantic everywhere: raw daily bars plus split events whose execution date is known on or before the observation session. It does not dividend-adjust prices.

For a raw bar on session `d`, evaluated as of observation session `t`, the split-normalized close is:

```text
adjusted_close(d,t) = raw_close(d) * product(split_from / split_to)
                      for entity split events e where d < e.execution_date <= t
```

The execution-date inequality is load-bearing: the pre-split bar is restated onto the post-split share basis, while the execution-date bar is not adjusted again. Every adjustment type returned by the source is admitted, including `stock_dividend`; filtering only `forward_split` would miss economically equivalent share changes.

The engine uses dated `split_from`/`split_to` ratios rather than today's cumulative factor, so historical replay never imports a later split into the observation's evidence set. Split events resolve through the same identity intervals as prices. A split row that cannot resolve to one entity is excluded and disclosed. A large basis discontinuity without a matching split event is a coverage fault for that entity, not a legitimate new low.

The UI says `split-adjusted daily aggregate close`; it does not claim an authenticated official NYSE statistic or exact RTH high/low.

An exact 09:30–16:00 ET high/low basis is a later additive measurement with a distinct key. It may not silently replace the close-confirmed series.

### 5.2 Close-confirmed 52-week extremes

For entity `i` on session `t`:

```text
prior_high_252(i,t) = max(close(i,t-252) ... close(i,t-1))
prior_low_252(i,t)  = min(close(i,t-252) ... close(i,t-1))
new_high(i,t)       = close(i,t) >= prior_high_252(i,t)
new_low(i,t)        = close(i,t) <= prior_low_252(i,t)
```

All closes in the comparison are on the observation session's split-normalized share basis. The current session is excluded from both thresholds. A row is seasoned only when 252 prior valid identity-continuous closes exist. A flat series can be both a new high and a new low; `both_extremes` records this explicitly.

### 5.3 Participation and direction

Each universe emits:

```text
listed_n
resolved_identity_n
priced_n
seasoned_n
adv
dec
unch
adv_pct
pct_above_20
pct_above_50
pct_above_200
nh
nl
both_extremes
nh_pct
nl_pct
net_nh
net_nh_pct
high_low_index
ad_line
high_low_line
coverage_pct
seasoned_pct
```

Moving averages compare the current split-normalized close against a trailing window including the current session, matching the incumbent breadth convention. NH/NL thresholds use prior sessions only.

`adv_pct` excludes unchanged names from its denominator. Missing prices are unavailable, never unchanged. Percentage denominators are disclosed; zero-denominator outputs are null.

### 5.4 Historical context

The engine derives, without changing authority:

* 5-, 10-, and 20-session averages of `net_nh_pct`;
* 20-session change in percentage above the 50-day average;
* expanding historical percentile and z-score after minimum-history gates;
* exchange-versus-S&P and large-versus-small confirmation gaps;
* descriptive states: `broad_confirmation`, `narrowing`, `broadening`, `washout`, `recovery_thrust`, `fragmentation`, and `mixed`.

States are transparent summaries of visible components. They are not forecasts or trade signals.

## 6. Nightly data flow

1. `massive_stock_day` restores and advances its existing R2 store.
2. `exchange_breadth` resolves the latest completed XNYS session from the Massive manifest and canonical calendar.
3. It fetches the point-in-time XNYS roster once, paginated and fail-closed.
4. It refreshes the bounded Massive split-event ledger through the same completed session, without filtering out stock-dividend classifications.
5. It validates exchange, requested date, pagination completion, row floors, uniqueness, split ratios, and supported ticker types.
6. It resolves roster and split source rows against incumbent identity and updates accepted source ledgers only after full validation.
7. It reads only required raw ticker histories from `massive_stock_day`, applies dated split ratios in memory, joins through identity intervals, computes both universe frames, and emits receipts.
8. `scripts.build_site` composes the XNYS frames with incumbent S&P/Russell/sector breadth into one display view.

A partial local Massive store, stale manifest, roster/session mismatch, low coverage, invalid or unresolved corporate-action evidence, or unresolved reference gap produces an unavailable state and preserves the prior accepted data.

## 7. Historical backfill

`scripts/backfill_exchange_breadth.py` is resumable and date-bounded. It:

* enumerates reviewed XNYS sessions;
* requests the Massive point-in-time XNYS roster for each missing session;
* updates identity-safe membership intervals;
* uses the existing raw `massive_stock_day` store plus the dated split ledger for dates in its available window;
* can use the Massive grouped-daily REST endpoint with `adjusted=false` for older sessions when entitlement is available, then applies the same point-in-time split algorithm;
* writes a checkpoint only after each session is fully reconciled;
* recomputes aggregate frames from accepted interval, split, and price evidence;
* never marks a failed or partial session complete.

The command supports bounded recent-history seeding first, at least 270 sessions, so live 252-session metrics can become valid before a complete 2003-present backfill finishes.

## 8. Live sidecar

The frozen `live.breadth.v1` contract remains byte-key compatible.

A separate `live.exchange_breadth.v1` payload is written to `site/live/exchange_breadth.json`. The existing poller performs exactly one full-market snapshot fetch and passes the same `last_by_symbol` map to both builders.

The live XNYS threshold store reads the latest accepted XNYS roster and split-normalized trailing histories. On a split execution session it applies the accepted event ratio to pre-event thresholds before comparing the live post-split price. It emits current adv/dec, percentages above moving averages, and NH/NL against prior completed-session thresholds. It never advances nightly stores.

Live usability requires:

* healthy feed status;
* a non-closed session;
* matching roster, split, and threshold session/rules versions;
* source clock present and within SLA;
* coverage at or above the configured floor;
* minimum resolved-identity and seasoned coverage;
* complete operating and all-issues universe payloads.

Any failure returns `usable:false`; browser code retains the baked nightly value.

## 9. Command-center composition

`engine/breadth_command_center.py` is the pure composer. It accepts XNYS and incumbent index breadth frames and returns:

* primary state and transparent reasons;
* NYSE operating and all-issues cards;
* S&P 500/400/600/1500 and Russell 2000 rows;
* cross-universe confirmation counts;
* breadth pattern state;
* freshness, coverage, basis, and universe-version disclosure;
* chart/spark data only, never executable recommendations.

No opaque 0–100 score is introduced.

## 10. UI placement

### 10.1 Macro Markets face

Inside `#sx-markets-v2`, below the existing futures/yield/dollar row, render a compact breadth strip:

```text
NYSE NH / NL | S&P 1500 >50D | universes confirming | state | source clock
```

The full Markets card remains the trigger for `#dlg-markets`.

### 10.2 Markets dialog

The first analytical section in `#dlg-markets` becomes `Breadth & Participation`, before Index Health:

* four headline tiles: state, NYSE NH/NL, participation, and A/D direction;
* universe matrix;
* historical-context and pattern explanations;
* coverage, split-basis, and source disclosure;
* graceful accruing/unavailable state.

Existing Index Health, Sector Temperature, heatmap, rates, volatility, and credit follow unchanged.

### 10.3 US Stocks

The incumbent S&P 1500 breadth board remains. It receives a canonical link/summary from the shared command-center view rather than a separate XNYS calculation. Shared partials and one VM prevent drift.

All new visible copy has English/Chinese twins and keyboard/screen-reader behavior matching the existing dialog system.

## 11. Error and honesty rules

* Never label an S&P constituent proxy `NYSE`.
* Never call provider-derived output `official NYSE Market Statistics`.
* Never blend XNYS and XASE.
* Never use current membership for historical sessions.
* Never bridge an unobserved membership day.
* Never splice ticker histories without identity continuity.
* Never use a split event after the historical observation session.
* Never treat an unadjusted split seam as a genuine new low.
* Never count a missing price as unchanged.
* Never count an unseasoned issue in NH/NL denominators.
* Never overwrite accepted nightly data with low-coverage live data.
* Never infer a forecast from breadth state.
* Never revive Hindenburg Omen or Titanic Syndrome authority; the existing kill remains.

## 12. Testing and proof

### 12.1 Pure engine

* current session excluded from the prior-252 threshold;
* IPO/young issue excluded from seasoned denominator;
* ticker rename continuity through one entity key;
* ticker reuse separation across different entity keys;
* forward, reverse, and stock-dividend split ratios normalize pre-event bars exactly once;
* no future split event enters a historical observation;
* an unmatched split-like seam is excluded and disclosed;
* both-extremes counted;
* missing/unchanged denominator behavior;
* operating/all-issues type split;
* interval compression and gap non-bridging;
* historical percentile and descriptive states are causal.

### 12.2 Collector/backfill

* roster and split pagination, cursor propagation, and API-key redaction;
* wrong exchange/date/type, invalid ratio, and duplicate-row rejection;
* partial page and low row-floor fail closed;
* source failure leaves prior ledgers unchanged;
* checkpoint advances only after an accepted session;
* Massive store absence/staleness refuses rather than fabricates;
* raw R2 and grouped-daily unadjusted paths yield metric parity on split fixtures.

### 12.3 Live

* existing `live.breadth.v1` exact-shape tests remain green;
* one snapshot call produces both outputs;
* exchange-sidecar exact schema and finite JSON;
* current-session split factors adjust cached thresholds exactly once;
* stale/low-coverage/mismatched-roster gates fail closed;
* browser ignores an unusable sidecar.

### 12.4 Surface

* Macro compact strip and first dialog section render with a real VM fixture;
* absence renders honest accruing copy and does not crash;
* US Stocks retains its existing board and links to the shared command center;
* dark/light, desktop/mobile, EN/ZH, keyboard, focus, and screen-reader checks;
* rendered artifacts contain no signal, forecast, or official-NYSE mislabel.

## 13. Acceptance

The program is accepted only when code, tests, rendered pages, source receipts, and real-path proof establish all of the following:

1. XNYS-only universes and an explicit all-issues comparator.
2. Point-in-time identity-safe membership.
3. Prior-252 close-confirmed NH/NL with seasoned denominators.
4. Point-in-time split normalization with no false split lows and no future-event leakage.
5. Raw and normalized measures with coverage disclosure.
6. Reuse of the Massive price store and one live snapshot request.
7. Frozen `live.breadth.v1` compatibility.
8. Shared Macro/US Stocks composition.
9. Fail-closed stale/partial behavior.
10. No new predictive or trading authority.
11. Full backfill can continue resumably after the first 270-session production seed.
