# CRYPTO T16 — ETH/SOL availability census and class-transfer experiment

Date: 2026-10-12. Lane `claude/cx-t16p-20261012`. Read-only census of the candidate-base worktree plus this document. No engine, collector, template, or test file was edited.

Stored parquet bounds were not opened. `data/` is sparse-omitted. No collector was run and no provider was queried. Periods below are request floors, config comments, and one committed audit table. Where those disagree, both are recorded. A first bar in a store remains UNVERIFIED until a later lane reads the parquet.

Descriptive coverage does not imply predictive parity. This is asset-class methodology for two class members, ETH and SOL. It is never single-name intelligence. An instrument reading (one venue, one quote) is not a market verdict. A Bitcoin training result does not set either target's calibration or authority.

## 1. Availability

Contract `contracts/crypto_asset_states.schema.json` requires assets `ETH` and `SOL` (`:15`). The object is `tier=display`, `display_only=true`, `authority=states_only` (`:9-11`). Each asset's `allocation` and `recommendation` are typed `null` (`:24-25`). `engine/eth_state.py` is the builder (`SCHEMA` `:19`, `build_states` `:176-198`).

### 1.1 ETH

| Series | Where | Period the code records | Venue / quote | Missing-data behavior |
|---|---|---|---|---|
| `coinbase/eth_daily` | `collectors/coinbase.py:7`, `:50-51`. Product `ETH-USD`, granularity 86400. Columns `low, high, open, close, volume` (`:29`). Daily index normalized in `validate` (`:104-106`). | Request floor `coinbase.eth_earliest = 2016-06-01` (`config.yml:2230`). This is the backfill start sent to the API, not a counted first stored bar. | Coinbase Exchange, USD spot. | No candles raises `ValueError` (`coinbase.py:89-90`). Empty or all-NaN frame raises (`:100-108`). Nothing is written as zero. `eth_state.build_states` falls through to Yahoo when the frame is missing or empty (`eth_state.py:183-187`). |
| `yahoo/ETH-USD` | `config.yml:7515` group `yahoo.tickers.crypto`. Not in the OHLC set, so High/Low are not requested (`collectors/yahoo.py:191-194`). | Committed audit, live-tested 2026-06-12, not re-checked here: ETH-USD `2017-11 →` (`research/VECTOR_DATA_AUDIT.md:1`, `:18`). Module comments say `2017->` (`engine/alt_cycle.py:4`) and the strategy caveat says `2017→` (`engine/strategies.py:872`). Signal-lab row says the port sample starts `2017-11` (`engine/signal_lab.py:834`). | Yahoo Finance via yfinance. `close` is Adj Close; `close_price` is Close (`yahoo.py:6-11`, `:197-199`). Crypto pays no dividend; whether the two stored columns differ is UNVERIFIED. | `_extract` returns `None` when the vendor frame is empty (`yahoo.py:180`, `:216-220`). No zero bar is stored. |
| Which column each reader uses | See basis note below. | — | — | — |
| `coingecko/global_market.eth_dominance_pct` | `collectors/crypto_misc.py:42-65`. One appended row per fetch day. | No backfill in this adapter. The comment that history comes from bgeo names **bitcoin** dominance (`:43-44`), not ETH share. | CoinGecko `/global`, percent of USD total crypto market cap. Key `market_cap_percentage.eth`. | Absent key becomes a null cell (`:62`), not a zero. Downstream `_value` / `_delta` return `None`, and direction text is `Unavailable` (`engine/crypto_market_state.py:31-36`, `:101-103`). |
| `crypto_universe/market_eth` | Only if that day's top-50 snapshot contains symbol `ETH`. Key `market_{symbol}` (`crypto_misc.py:148-153`). Source `CoinGecko`, or `CoinPaprika` after a CoinGecko failure (`:102-107`). | Snapshot accrual. Not a synthetic backfill (`crypto_misc.py:73-75`). Spark keeps at most 90 positive prices (`engine/crypto_universe.py:127`). | USD price, rank, reported 24h/7d/30d percent changes. Identity is `(source, coin_id)` (`crypto_universe.py:116-124`). | Bad rank, non-positive price, empty symbol, future date, older snapshot, empty file, or unreadable file is excluded with a reason (`:88-114`). A source or coin-id break resets history (`SOURCE_IDENTITY_CHANGED`) instead of splicing (`:116-142`). Breadth drops a missing 30-day return; it is not counted as zero (`:161-171`). Under 10 eligible names, breadth is `available: false`, `value: null` (`:176-178`). |
| Display state | `eth_state.build_asset_state` | Publishes a state only at `MIN_PUBLISH_DAYS = 30` (`eth_state.py:20`, `:87`, `:112`). Relative state needs 91 joined sessions (`:49-50`). | Prefers Coinbase close. Yahoo is labelled `yahoo_fallback` / "Yahoo close-only availability fallback" (`:76-85`, `:183-187`). | Under 30 days: trend `Building history`, risk `Unavailable`, relative `Building history`, `allocation` and `recommendation` stay `None` (`:103-124`). Zero rows: `price` is `None` (`:115`). Relative change stays `None` when the join is short (`:53-54`). Test lock: `tests/test_crypto_wave3.py:60-86`. |

ETH readers and the column they take:

- `eth_state._close` requires a `close` column (`engine/eth_state.py:29-31`).
- `crypto_market_state._series(..., "yahoo", "ETH-USD", ("close", "close_price", "Close"))` (`engine/crypto_market_state.py:143`). SOL is not read here.
- `scripts/build_crypto.py:36-42` `_series` tries `close`, then `close_price`. Caller at `:301` feeds `alt_cycle.ethbtc_signal`.
- `scripts/build_vector.py:1298-1305` uses `close` when present. Callers `:4609` and `:4611`.
- `engine/btc_inputs.py:136` loads `yahoo/ETH-USD` with `col=None`, and `_col` then takes **column 0** (`:24-31`). After the Yahoo rename, column 0 is `close_price` when Adj Close exists (`yahoo.py:194-199`). This is a different column from the display readers. The predictive experiment pins `close` and does not call `load_all()["eth"]`.
- `engine/market_drivers.py:255` reads Yahoo `close` as a macro-frame leg. A missing frame returns `None` (`:237-241`).
- `engine/factor_exposure.py:161-169` lists `ETH-USD` inside an equity-style exposure book (`CRYPTO_NAMES`). That path is single-name book exposure. It is outside this class experiment.
- `engine/strategies.py:866-874` `eth_trend` scores Yahoo `ETH-USD` with `_sc_trend`. Caveat text says the history is short and one cycle, and that the drawdown cut is the headline. There is no SOL strategy row in that file (search: `sol_trend` / `SOL-USD` in `engine/strategies.py` returned only the ETH and BTC rows).

`btc_signals.btc_vs_alts` (`engine/btc_signals.py:700-718`) returns `None` when `inputs["eth"]` is `None`. When present, ETH is reindexed onto the BTC close with `ffill(limit=3)`. The leader series is born as `"BTC"` and overwritten where ETH relative strength is positive. A missing ETH series does not become a zero relative return.

`alt_cycle.ethbtc_signal` (`engine/alt_cycle.py:19-26`) returns `{}` when ETH is `None` or the ratio has fewer than 120 points. The ratio is `eth.reindex(btc.index).ffill()` with **no limit**, then `dropna`. A long ETH hole is carried at the last price. `alt_season_score` returns `(None, "—")` on an empty ETH/BTC dict (`:40-44`). `alloc_grid` is a hand-written weight table (`:63-76`), described in the module docstring as convention (`:8-11`). It is not a measured method and it is not a transfer candidate.

### 1.2 SOL

| Series | Where | Period the code records | Venue / quote | Missing-data behavior |
|---|---|---|---|---|
| `coinbase/sol_daily` | `collectors/coinbase.py:8`, `:53-54`. Product `SOL-USD`, same daily OHLCV schema and `validate` as ETH. | Request floor `coinbase.sol_earliest = 2021-06-17` (`config.yml:2231`). | Coinbase Exchange, USD spot. | Same raise-on-empty behavior as ETH. `build_states` uses the same Yahoo fallback (`eth_state.py:182-188`). |
| `yahoo/SOL-USD` | `config.yml:7515`. Same non-OHLC Yahoo schema as ETH. | Audit table: SOL-USD `2020-04 →` (`research/VECTOR_DATA_AUDIT.md:18`). Config comment on the SOL/ETH window says `SOL-USD ~2020->` (`config.yml:6118`). Coinbase floor `2021-06-17` is later than that Yahoo claim. Stored overlap of the two venues is UNVERIFIED. | Yahoo Finance, USD. `close` vs `close_price` as for ETH. | Same `None`-on-empty extract. No zero bar. |
| `crypto_universe/market_sol` | Same snapshot adapter, key `market_sol` only while symbol `SOL` is inside that day's top 50. | Accrued snapshot days only. Spark cap 90. | USD. CoinGecko, else CoinPaprika. | Same exclusion and identity-reset rules as ETH. A day SOL is outside the top 50, that file simply does not gain a row. Absence is not a zero return. |
| Display state | Same `build_asset_state("SOL", ...)` | Same 30-day publish gate and 91-day relative join. | Coinbase close, else labelled Yahoo close. | Same `Building history` / `Unavailable` / null allocation contract. `tests/test_crypto_wave3.py:78-86` locks the short-history wording on a 12-row SOL fixture. |
| SOL/ETH ratio | `alt_cycle.beta_ratio` (`engine/alt_cycle.py:79-102`). Wired from `scripts/build_vector.py:4611` as `beta_ratio(yahoo SOL-USD, yahoo ETH, alt_cycle cfg)`. Windows: MA 100, slope 56, percentile 730 (`config.yml:6116-6118`). | Needs 120 aligned points (`alt_cycle.py:88-89`). The 730-day percentile cannot exist on the Coinbase floor alone until roughly two years after `2021-06-17`. Yahoo `2020-04` is an audit claim, not a bar count. | USD closes, ETH in the denominator. | `None` numerator or denominator, or fewer than 120 points, returns `{}` (`:85-89`). Test: `tests/test_vector_breadth.py:48-51`. Forward-fill onto the denominator index is again unlimited (`:87`). |

`engine/btc_inputs.py:137` loads SOL the same way as ETH: Yahoo column 0 (`close_price` when Adj Close exists). `crypto_market_state` does not read SOL. No `sol_hourly`, no `eth_hourly`. Coinbase `fetch` emits `btc_daily`, `btc_hourly`, `eth_daily`, `sol_daily` only (`coinbase.py:42-55`; test `tests/test_crypto_wave3.py:89-101`).

### 1.3 Series that mention ETH or SOL and are not target price history

These stay out of the predictive feature set. Using them would score the Bitcoin complex, or the whole class, under an ETH or SOL label.

| Series | Scope in code | Missing behavior |
|---|---|---|
| CoinMetrics `asset: btc`, `start_date: 2010-01-01` (`config.yml:2181-2186`). Metrics include MVRV, hashrate, issuance, address counts. | BTC only. A missing metric is skipped; the adapter raises only when no metric column survives (`collectors/coinmetrics.py:63-71`). | No ETH/SOL asset id. |
| bgeo, `window_start: 2022-06-13` (`config.yml:2203`). SOPR, STH/LTH, realized price, miner pressure, funding, OI, `etf-flow-btc`, `bitcoin-dominance`. | BTC metrics. Dominance is BTC share (`config.yml:2213`). | Quota stop returns a partial fetch; a total miss raises (`collectors/bgeo.py:13-17`). |
| Deribit `currency=BTC` (`collectors/deribit.py:307`, `:329`, `:340`). DVOL floor `2021-03-01` (`config.yml:2256`). | BTC implied vol and BTC option book. | Empty early history is the documented BTC fact (`deribit.py:3-5`). |
| OKX `inst_id: BTC-USDT-SWAP`, spot `BTC-USDT` (`config.yml:2241`, `:2249`). | BTC funding, OI, long/short, taker volume, spot. | A rubik hourly failure is logged and does not fail the daily BTC series (`collectors/okx.py:60-65`). `funding_asof` defaults to `BTC-USDT-SWAP` (`collectors/_crypto_observations.py:181`). `tests/test_crypto_collectors.py:316-317` passes `ETH-USDT-SWAP` to prove a **mismatched** instrument is not treated as the known BTC source. That test does not collect an ETH series. |
| Farside | US spot-Bitcoin ETF flows since the 2024-01-11 launch (`config.yml:2275-2279`). | No ETH or SOL flow table in `collectors/farside.py` (search for ETH/SOL/ethereum returned no matches). |
| `sentiment_crypto/fear_greed` | Class index. Collector docstring: full history `2018-02->` (`crypto_misc.py:20-21`). Audit agrees (`VECTOR_DATA_AUDIT.md:16`). | Empty payload raises (`:33-34`). |
| `defillama/stablecoins` | Aggregate stablecoin supply (`crypto_misc.py:190-193`). | Class, not a target. |
| `coingecko` `btc_dominance_pct`, `total_mcap_usd` | Class (`crypto_misc.py:61-63`). `crypto_market_state.total_market_cap_history` derives class cap from BTC cap / BTC dominance, then splices the snapshot (`engine/crypto_market_state.py:49-69`). | Empty inputs become an empty series. Deltas on a short series are `None`. |
| `engine/neuralweb/market_packet.py:132` | Display packet symbols `(BTC-USD, ETH-USD)`. SOL is absent. | Not a store. |
| `engine/us_turn_watch.py:130` | Comment that a calendar artifact once included `ETH-USD` and `SOL-USD`. | Not a series owner. |

`crypto_market_state.build_market_state` alt-participation cell (`:258-274`) is a 90-day ETH/BTC relative move minus a BTC-dominance change, clipped into a 0–100 display score. Short ETH or BTC leaves `alt_score is None` and the state `Building history` (`:267-274`). The hero stance (`:154-184`) is computed from class cap and BTC dominance. It does not read SOL, and it does not require ETH.

### 1.4 Structural regime changes the code already knows

Search bounds, 2026-10-12, no provider calls:

- `engine/eth_state.py`, `alt_cycle.py`, `crypto_market_state.py`, `crypto_universe.py`, `btc_inputs.py`, `btc_signals.py`, `btc_decision.py`, `btc_impulse_radar.py`, `strategies.py`: no match for Merge, Shanghai, beacon, Dencun, Pectra, FTX, network halt, or `2022-09-15`.
- `collectors/coinbase.py`, `crypto_misc.py`, `okx.py`, `deribit.py`, `bgeo.py`, `coinmetrics.py`, `farside.py`: no ETH or SOL protocol-regime marker. The OKX "outage" branch is a BTC rubik-hourly degrade (`okx.py:60`).
- `config.yml`: no Ethereum merge date and no Solana halt list. The dates that **are** encoded are Bitcoin book dates: Coinbase BTC floors `2015-07-20` and `2016-01-01` (`:2228-2229`); bgeo window `2022-06-13`; Deribit DVOL `2021-03-01`; halving dates `2012-11-28`, `2016-07-09`, `2020-05-11`, `2024-04-20` (`:6043`); cycle bottoms `2015-01-14`, `2018-12-15`, `2022-11-21` and tops `2017-12-16`, `2021-11-08`, `2025-10-06` (`:6055-6056`); calibration `start_date 2015-01-01`, `split_date 2021-01-01` (`:6138-6139`).

So the code knows listing floors and Bitcoin cycle calendars. It does not know the Merge, later Ethereum upgrades, or Solana halt windows. Those events are not features of this experiment. A later scorer who wants a protocol stratum has to cite a primary date **before** opening the score window. This document does not supply those dates, and it does not let the target sample pick its own worst year.

The one stress year already written next to an ETH port is calendar 2022: the signal-lab row says the Sharpe edge of that port failed `drop-2022` (`engine/signal_lab.py:834`, `:847`). That is an annotation on a prior run, not a coded regime dummy. Section 3 reuses 2022 as an exogenous class year for both targets because it is already on the ETH record. It is not estimated from SOL returns.

## 2. What may transfer, and what is Bitcoin-only

### 2.1 Candidates

Each candidate is a function that can be pointed at one target close. Bitcoin-native legs stay off. Thresholds stay the frozen Bitcoin config. No new grid is searched on the target inside this protocol.

| Function | Transfer shape | Legs that stay off |
|---|---|---|
| `btc_signals.momentum` (`engine/btc_signals.py:135-168`) | Price votes only: `ema_trend`, `ema_cross`, `macd_hist`, `sma200` (`:149`), `roc20`, `rsi_zone`. | `sopr_momentum` and `sth_cost_basis` (`:154-160`). Those keys are omitted from the input dict so the votes are not created. |
| `btc_signals.risk` (`:174-231`) | `vol_pctile`, `drawdown`, `momentum_deterioration`. | `sopr_stress`; `intraday_vol` (hourly exists only for BTC, `btc_inputs.load_hourly` `:75-76`); `etf_outflow`, which `fillna(0)`s the flow before masking (`:207-210`); `funding_stress`. |
| `btc_signals.allocation` (`:571-641`) | The momentum × risk grid with `use_valuation_overlay` false and `bottom_overlay` false. `drawdown_brake` (`:374`) may cap size from the **target's** own close. | MVRV, NUPL, Mayer, reserve-risk overlay (`:592-606`). Bottom-pressure overlay. Anything in `btc_overrides.apply`, including `midterm_blackout` (`:485-504`). The function's own docstring says the blackout is applied **after** `allocation()` returns (`:583-587`). The ETH port record says an earlier figure inherited that blackout with no ETH basis (`engine/signal_lab.py:828-831`). This protocol does not call `btc_overrides.apply`. |
| `btc_signals.impulse` (`:1455-1506`) | The price acceleration core: z-scored MACD histogram times the Kaufman efficiency ratio (`:1468-1496`). | `funding` and `open_interest_df` (`:1480-1491`). `impulse_pos_pct` is a single-name stand-in for a breadth statistic (`:1501-1504`). It is reported as a coverage note, not as a class-breadth feature. |
| `btc_signals.tactical` (`:721-727`) | Efficiency ratio on the target close, as a state tag. | It does not become an allocation. |
| `eth_state.build_asset_state` / `build_states` | Already the display contract for both symbols. | Stays display. `allocation` and `recommendation` remain null. A rendered state is not a score in section 3. |
| `alt_cycle.ethbtc_signal`, `alt_cycle.beta_ratio`, `alt_cycle.breadth_view` | Already the display ratios. | Judgment lines `0.05` / `0.07` and `alloc_grid` weights stay off the predictive test (`alt_cycle.py:8-11`, `:60-76`). The unlimited `ffill` (`:24`, `:87`) is not the experiment join. The experiment joins on the intersection of dates. A gap is `unavailable`. |

The direct simple baseline on **each** target, named here `sma200_long_flat`:

- Position is 1 on a session whose own `close` is above that series' trailing 200-observation mean, and 0 when the close is at or below a defined mean.
- Sessions before 200 observations exist, and any session whose mean is undefined, are `unavailable`. They are left out of the scored window. They are not filled with 0.
- Same rule, fit separately, on ETH and on SOL. No shared mean, no pooled position.
- This is the same shape as the `sma200` vote inside `momentum` (`btc_signals.py:149`) and the same family as the brake-matched 200-day average the ETH signal-lab row already treats as the comparator (`signal_lab.py:832`, `:846`).
- `strategies._sc_trend` (`strategies.py:379-385`) is **not** the baseline. It calls `cross_asset_trend.tsmom_alloc`, and that function ends in `.fillna(0.0)` (`engine/cross_asset_trend.py:109-119`). A missing sign would enter the score as a flat zero. `strategies._sc_gcross` (`:401-407`) is a 50/200 cross and is a different rule; it is not substituted in after the fact.

### 2.2 Structurally Bitcoin-only

These functions encode a Bitcoin ledger, a Bitcoin venue, or the Bitcoin decision authority. Pointing them at ETH or SOL is a category error.

- `btc_decision.build_decision` and `project_budget`. Final exposure authority is `signals.alloc_optimal` (`engine/btc_decision.py:210-214`). Schema is the BTC decision projection.
- `btc_overrides` and `midterm_blackout` (`btc_signals.py:485-504`). US midterm calendar, justified in the docstring by BTC paths in 2014/2018/2022.
- `cycle_clock` (`btc_signals.py:964-989`) on `vector` halving dates (`config.yml:6043`).
- `cycle_phase_clock` (`btc_signals.py:992` onward) on the Bitcoin bottoms and tops in `config.yml:6055-6056`.
- `btc_cycle_thesis` (halving-anchored monitor).
- `valuation`, `miner`, `miner_economics`, `cost_basis`, `holder_spread`, `onchain_regime`, `bfi`. Inputs are MVRV, hashrate, issuance, SOPR, realized price, active addresses, Coinbase-premium (`btc_inputs.py:93-127`).
- `options`, `leverage`. Deribit BTC and bgeo BTC open interest.
- `cme_basis`, `futures_carry`. Yahoo `BTC_F` (`config.yml:7516`, `btc_inputs.py:157`).
- `etf_flow`. Farside spot-Bitcoin ETF table.
- `taker_flow`, `positioning`. OKX BTC-USDT-SWAP and CME Bitcoin COT (`btc_inputs.py:153`).
- `btc_impulse_radar.fire_series` / `compute`. Act legs are DVOL range, SOPR, and the fifth-percentile price path of the Bitcoin signal frame (`btc_impulse_radar.py:136-148`).
- `btc_intraday_cvd.compute`. OKX BTC taker hourly.
- `btc_inputs.load_price` / `load_hourly`. Yahoo BTC spliced under Coinbase BTC (`btc_inputs.py:54-76`). The `eth` and `sol` keys in `load_all` are context series for the Bitcoin book, not target engines.
- `alt_cycle.alloc_grid`. Hand weights. Not a measurement.
- The signal-lab row "Crypto vol-targeted risk-parity sleeve (BTC+ETH)" is already marked killed (`engine/signal_lab.py:887-898`): a 200-day average dominated it on Sharpe and MaxDD, and the split-half Sharpe sign flipped. That sleeve pools two assets. It is not a vehicle for this experiment.
- `factor_exposure.CRYPTO_NAMES` entry `ETH-USD`. Equity-book exposure of one ticker. Out of scope.
- `market_drivers` ETH leg. A macro feature column, not an ETH experiment.

`engine/signal_lab.py:824-849` already records one ETH port of the live Bitcoin grid: confirmer, sample `n=3157` from `2017-11`, DSR `0.5345` at `n=50`, Sharpe `0.796` against HODL `0.647`, MaxDD `−46.6%` against `−94.0%`, brake-matched 200-day average ahead on Sharpe (`0.82` vs `0.80`), drop-2022 Sharpe edge `−0.05`, direction described as a coin-flip and not claimed. Those numbers are the prior row. This document does not rerun them, does not promote the row, and does not treat them as the section 3 result. No SOL port of that grid exists in the files searched.

## 3. Predeclared experiment

Question, asked twice, once per target: with Bitcoin-native legs removed and with thresholds frozen, does the section 2.1 transplant beat `sma200_long_flat` on that target's own held-out time block?

### 3.1 Asset holdout

- ETH is scored on ETH bars. SOL is scored on SOL bars. Neither sample chooses a window, a threshold, a cost, or a pass cut for the other.
- Bitcoin training success is not an input. `vector.calibration.start_date`, `split_date`, `n_trials`, and `cost_bps` (`config.yml:6138-6145`) stay Bitcoin-book constants. They are not the target split and they do not set the target pass cut.
- `btc_decision.build_decision` is not called. No writer sets `allocation` or `recommendation` on the asset-state contract. A later `accepted` row is a research disposition for a gauntlet. It does not size, gate, or execute.
- Feature ban on both targets: CoinMetrics, bgeo, Deribit, OKX BTC instruments, Farside, halving clock, cycle bottoms/tops, midterm blackout, BTC dominance, ETH dominance, total crypto cap, fear-and-greed, stablecoins, and any other target's return. Class context may keep rendering on the display path. It does not enter the design matrix.
- Basis, chosen before any statistic: one arm uses `coinbase/{eth,sol}_daily` `close`. A second arm, reported separately, uses `yahoo/{ETH,SOL}-USD` `close`. The arms are not spliced. `btc_inputs` column 0 is not used. The join is an inner join on dates. A missing close is `unavailable`.

### 3.2 Time holdout

Applied separately on each target's own calendar.

1. Warm-up: the first 200 sessions of that series are `unavailable` for every arm.
2. Embargo: the last 30 sessions of that series are `unavailable` for every arm. They are not a place to pick a rule.
3. The remaining sessions are cut once, at their own midpoint. The early block is a sensitivity report. The later block is the only block that can accept or reject.
4. Stress report: drop calendar year 2022 from both blocks and recompute the same difference. The year is copied from the existing ETH annotation (`signal_lab.py:834`, `:847`). It is not chosen by scanning SOL. If a target has no 2022 sessions on that arm, the stress cell is `unavailable`.

`vector.calibration.split_date = 2021-01-01` is not reused. On the Coinbase SOL floor `2021-06-17` that date leaves no pre-period.

### 3.3 Metric and pooling

One metric. On the later block, Sharpe of the transplant minus Sharpe of `sma200_long_flat`, same dates, same arm. MaxDD is reported beside it and is not optimized. The early block's Sharpe difference is reported and is not a second chance to retune.

Accept, all of these, on that target's own arm:

- Later-block Sharpe difference is positive.
- Early-block Sharpe difference is not negative.
- Transplant MaxDD on the later block is not deeper than the baseline's MaxDD.
- The 2022-dropped report still has a positive later-block Sharpe difference. An `unavailable` stress cell blocks acceptance.

Anything else is a rejection, except the case where the later block itself is `unavailable` (too few sessions after warm-up and embargo). That case is `unresolved`.

Buy-and-hold of the same target over the same dates is reported as context. Beating buy-and-hold while losing to `sma200_long_flat` is a rejection. The prior ETH row already sits in that neighborhood on Sharpe (`signal_lab.py:846`) and is not accepted by this protocol.

No pooling. ETH and SOL are not averaged. No ETH+SOL book. No BTC+ETH book. The killed vol-target sleeve (`signal_lab.py:887-898`) stays killed. A class sentence may list the two dispositions. It may not say the method transfers while either disposition is `rejected` or `unresolved`.

Costs: the primary table is gross. A second column may subtract the Bitcoin book's one-way `10` bps (`config.yml:6143`) on both the transplant and the baseline, labelled as a copied constant. That column cannot flip an acceptance by itself, and it is not an ETH or SOL estimate.

### 3.4 Disposition template

Fill one row per target after a scorer runs section 3. Until then both rows stay `unresolved`. This lane did not compute them.

| Field | ETH | SOL |
|---|---|---|
| Target | ETH | SOL |
| Arms | `coinbase/eth_daily` close; `yahoo/ETH-USD` close. Separate. | `coinbase/sol_daily` close; `yahoo/SOL-USD` close. Separate. |
| Baseline | `sma200_long_flat` | `sma200_long_flat` |
| Transplant | Section 2.1, frozen config, Bitcoin legs off, no `btc_overrides.apply` | Same functions, own bars, own midpoint |
| Later-block Sharpe difference | | |
| Early-block Sharpe difference | | |
| Later-block MaxDD, transplant and baseline | | |
| 2022-dropped later-block Sharpe difference | | |
| Buy-and-hold Sharpe on the later block (context) | | |
| Disposition | `unresolved` | `unresolved` |
| Authority effect | none | none |

Allowed values in the disposition cell: `accepted`, `rejected`, `unresolved`. `accepted` means the metric rules in section 3.3 all held on at least one predeclared arm, and failed on none of the arms that had a scored later block. A pass on Yahoo and a failure on Coinbase is a rejection. `rejected` means a scored later block exists and the metric rules failed. `unresolved` means the later block is `unavailable`, or this protocol has not been run.

## 4. Statement

Descriptive coverage does not imply predictive parity. A Coinbase history, a Yahoo history, a 30-day display state, an ETH/BTC ratio, or a SOL/ETH ratio shows that a series can be plotted. It does not show that a Bitcoin method predicts that series. This document is asset-class methodology for ETH and SOL as two members of the crypto class. It is never single-name intelligence, never an equity-factor reading, and never a forecast a desk can size.

## 5. Bounds

- Census commands were reads and searches under `contracts/crypto_asset_states.schema.json`, `engine/crypto_universe.py`, `engine/crypto_market_state.py`, `engine/eth_state.py`, `engine/alt_cycle.py`, `engine/btc_inputs.py`, `engine/btc_signals.py`, `engine/btc_decision.py`, `engine/btc_impulse_radar.py`, `engine/strategies.py`, `collectors/coinbase.py`, `collectors/crypto_misc.py`, `collectors/yahoo.py`, `collectors/okx.py`, `collectors/deribit.py`, `collectors/bgeo.py`, `collectors/coinmetrics.py`, `collectors/farside.py`, `collectors/_crypto_observations.py`, `config.yml`, `scripts/build_crypto.py`, `scripts/build_vector.py`, `research/VECTOR_DATA_AUDIT.md`, `engine/signal_lab.py`. Grep roots were `collectors/` and `engine/` for `ETH`, `SOL`, `eth_`, `sol_`, plus the config and audit hits cited above.
- `data/**` parquet min/max dates: UNVERIFIED (sparse omit; no live read).
- Protocol-event dates beyond the 2022 annotation: absent in the search bounds in section 1.4.
- SOL grid-port result: absent in `engine/signal_lab.py` and `engine/strategies.py` under the searches above.
