# Crypto T11 — on-chain and valuation family map

Date: 2026-10-12. Lane `claude/cx-t11-20261012`. Census of the candidate-base tree (PR #8050 `fd8095012e91` source delta on `origin/main`). Line numbers below are that worktree. R10 is not on `origin/main`; it is cited as `fd8095012e91:research/CRYPTO_SCIENCE_R10_SOURCE_QUALIFICATION_RESULTS_2026-09-29.md`.

This lane does not promote any series to allocation authority. `engine/btc_decision.py` already files `valuation_state` and `market_extreme` as `context_only` receipts (`engine/btc_decision.py:237-240`, `:349-357`).

## Classes

- **OBSERVED INPUT** — a provider number stored as a series. This repo does not invent it.
- **ALGEBRAIC DERIVATION** — a formula of named parents. No new economic claim.
- **ECONOMIC HYPOTHESIS** — a threshold, vote, regime word, or narrative reading.

A null parent leaves the derived series absent or NaN in the honest paths. Where the code instead emits inf or a clipped 1.0, that defect is named below and patched, not applied, in `research/crypto_science/patches/`.

## Knowledge time (one rule for every family)

Scoped readers do not carry a received/knowledge time on valuation series.

- `engine/btc_inputs._col` (`engine/btc_inputs.py:24-31`) returns the first column of `lib/store.read`. The store is one parquet per series (`lib/store.py:36-42`). Upsert: "New values win on date collision" (`lib/store.py:62`). No vintage column.
- `CoinMetricsAdapter.fetch` (`collectors/coinmetrics.py:31-72`) writes `date` plus the metric column. No `received_at`. Incremental start is `last_good_date - 5 days` (`collectors/coinmetrics.py:36-37`), so the overlap can overwrite recent history and drop the previous number.
- `BgeoAdapter._fetch_metric` (`collectors/bgeo.py:101-133`) computes `received_at` and then calls `observations.record_response` only when `endpoint == "funding-rate"` (`collectors/bgeo.py:112-113`). `unixTs` is dropped (`collectors/bgeo.py:120`). SOPR, realized price, and supply-in-profit frames have no clock.
- `collectors/_crypto_observations.py` `SOURCES` is `okx_funding`, `okx_taker`, `bgeo_funding` only (`collectors/_crypto_observations.py:28-32`). `load_asof` filters `received_at <= cutoff` (`collectors/_crypto_observations.py:162-171`). That filter does not cover MVRV, NUPL, or SOPR.

R10's standard, reused: a receive clock is a conservative bound on what this system possessed; a fetch time must not be written back onto an old bar as earlier knowledge; a mutable parquet cannot recover a discarded vintage (`fd8095012e91:research/CRYPTO_SCIENCE_R10_SOURCE_QUALIFICATION_RESULTS_2026-09-29.md:107`). R10 also says it did not search every archive and does not declare reconstruction impossible in general. This census is narrower: **historical reconstruction from these code paths is UNAVAILABLE**. `data/` was not read (sparse checkout). An archive outside this search bound is UNVERIFIED, not a vintage this engine can read.

Provider restatement policy (does CoinMetrics or BGeometrics rewrite history?) is **UNVERIFIED**. Search bound: `collectors/coinmetrics.py`, `collectors/bgeo.py`, `collectors/_crypto_observations.py`, `engine/btc_inputs.py`, `lib/store.py`, `config.yml` coinmetrics/bgeo blocks. None records a revision flag for CapMVRVCur or SOPR. The code's own overwrite behavior is separate and is cited above.

`engine/btc_cycle_thesis.py` (`monitor`, `_monitor`) reads price and the halving/top/bottom calendar. It reads no MVRV, NUPL, SOPR, realized-price, or holder series. It adds no family.

## Family table

Vote names `nupl` and `z` are the columns `market_extreme` builds today (`engine/btc_signals.py:1745-1763`). They are one family.

### F-MVRV — market value versus realized value

| Metric | Class | Formula / parents | Module | Provider | Unit |
|---|---|---|---|---|---|
| `mvrv` | OBSERVED INPUT | CoinMetrics `CapMVRVCur` | `CoinMetricsAdapter.fetch`; `btc_inputs.load_all` | CoinMetrics Community `config.yml:2181-2196` | dimensionless ratio |
| `mcap` | OBSERVED INPUT | `CapMrktCurUSD`. Parent of realized cap, MVRV-Z, SSR | same | same | USD |
| `realized_cap` | ALGEBRAIC DERIVATION | `mcap / mvrv` (`engine/btc_inputs.py:162-163`) | `btc_inputs.load_all` | derived | USD |
| `nupl` | ALGEBRAIC DERIVATION | `1 - 1/mvrv` (`engine/btc_inputs.py:164`). Exact identity, also `research/VECTOR_DATA_AUDIT.md:12` | `btc_inputs.load_all` | derived | dimensionless |
| `mvrv_z` | ALGEBRAIC DERIVATION | `(mcap - realized_cap) / rolling_std(mcap)` (`engine/btc_signals.py:734-745`). Equals `mcap * NUPL / std(mcap)` | `btc_signals.valuation` | derived | z of USD |
| `mvrv_z_pctile` | ALGEBRAIC DERIVATION | rolling percentile of `mvrv_z` | `btc_signals.valuation` | derived | 0–100 |
| `valuation_state` | ECONOMIC HYPOTHESIS | hysteresis on `mvrv_z` only (`engine/btc_signals.py:748-750`); thresholds `config.yml:5884-5887` | `btc_signals.valuation` | derived | label |
| `realized_price` | OBSERVED INPUT | bgeo `realized-price`. Same economic object as realized cap / supply **if** definitions match. Match is UNVERIFIED. Counting it as a second confirmation of MVRV is forbidden | `BgeoAdapter._fetch_metric`; `btc_inputs.load_all`; passthrough `btc_signals.cost_basis` | bitcoin-data.com | USD per BTC (code divides `close` by the STH sibling at `engine/btc_signals.py:806`) |

`valuation()` forward-fills `mcap`, `realized_cap`, and `nupl` with no limit (`engine/btc_signals.py:742-753`). A long gap stays a carried number. That is not a knowledge time.

`allocation` ORs `mvrv_z < deep_value_z` with `nupl < deep_value_nupl` into one boolean (`engine/btc_signals.py:593-598`). Config already calls them collinear (`config.yml:5799-5800`). That OR is one flag, not two confirmations. The two thresholds are not the same event, because Z scales NUPL by mcap dispersion.

### F-SOPR — spent-output profit ratio

Separate from F-MVRV. Cohort splits are members of this family, not extra families.

| Metric | Class | Formula / parents | Module | Provider | Unit |
|---|---|---|---|---|---|
| `sopr` | OBSERVED INPUT | bgeo `sopr`. Code treats 1.0 as break-even (`engine/btc_signals.py:157`, `:194`) | `BgeoAdapter._fetch_metric`; `btc_inputs.load_all` | bitcoin-data.com. Optional older seed: `scripts/backfill_crypto.backfill` chart `sopr` into `bgeo/sopr` (`scripts/backfill_crypto.py:37-42`, `:125-132`). The engine does not check that seed | ratio |
| `sth_sopr`, `lth_sopr` | OBSERVED INPUT | bgeo `sth-sopr`, `lth-sopr` | same loader | bitcoin-data.com | ratio |
| `sth_lth_sopr_spread` | ALGEBRAIC DERIVATION | `EMA(sth_sopr) - EMA(lth_sopr)` (`engine/btc_signals.py:1384-1389`) | `btc_signals.holder_spread` | derived | ratio points |
| `holder_state` | ECONOMIC HYPOTHESIS | spread versus ±0.02 (`engine/btc_signals.py:1394-1397`) | `btc_signals.holder_spread` | derived | label |
| `sopr_momentum` | ECONOMIC HYPOTHESIS | sign of 7-day EMA versus 1 (`engine/btc_signals.py:154-157`). One momentum vote | `btc_signals.momentum` | derived | −1/0/+1 |
| `sopr_stress` | ECONOMIC HYPOTHESIS | `(1 - EMA(sopr)) * 40` clipped to 0..1 (`engine/btc_signals.py:191-194`) | `btc_signals.risk` | derived | 0–1 stress |

`engine/btc_inputs.py:8` says SOPR is "spliced 2011→". The splice is not in `load_all`. It exists only if `scripts/backfill_crypto.py` was run, and bgeo wins on dates it later upserts. Stored depth was not read.

### F-STH-COST — short-term holder cost basis

| Metric | Class | Formula / parents | Module | Provider | Unit |
|---|---|---|---|---|---|
| `sth_realized_price` | OBSERVED INPUT | bgeo `sth-realized-price` | `btc_inputs.load_all` | bitcoin-data.com | USD per BTC |
| `sth_cost_basis` | ALGEBRAIC DERIVATION | reindex, ffill limit `sth_ffill_limit_d` | `btc_signals.cost_basis` | derived | USD per BTC |
| `sth_cb_ratio` | ALGEBRAIC DERIVATION | `close / sth_cost_basis - 1` | `btc_signals.cost_basis` | derived | fraction |
| `sth_realized_premium` | ALGEBRAIC DERIVATION | `sth_realized_price / realized_price - 1` (`engine/btc_signals.py:1390-1393`). Parents: F-STH-COST and F-MVRV | `btc_signals.holder_spread` | derived | percent |

Not an algebraic function of aggregate MVRV (cohort mix is extra information). It is still one UTXO cost-basis view, so it is not an authority confirmer beside F-MVRV. `momentum` already gives it its own vote, `sth_cost_basis` (`engine/btc_signals.py:158-160`), separate from the SOPR vote.

### F-SUPPLY-IN-PROFIT — count share of supply above its cost basis

| Metric | Class | Formula / parents | Module | Provider | Unit |
|---|---|---|---|---|---|
| `supply_in_profit` | OBSERVED INPUT | bgeo `supply-profit`. Comment: BTC, not a fraction (`engine/btc_inputs.py:168`) | `btc_inputs.load_all` | bitcoin-data.com. Config places it below the 10 req/hour cap (`config.yml:2219`) | BTC |
| `supply` | OBSERVED INPUT | CoinMetrics `SplyCur`. Denominator | `CoinMetricsAdapter.fetch`; `btc_inputs.load_all` | CoinMetrics | BTC |
| `supply_in_profit_pct` | ALGEBRAIC DERIVATION | `(sip / supply.ffill).clip(0, 1)` (`engine/btc_inputs.py:169-172`) | `btc_inputs.load_all` | derived | fraction |

Not the NUPL identity. Same UTXO cost-basis distribution, value-weighted (F-MVRV) versus count-weighted (this family). `market_extreme` votes it as `sip` (`engine/btc_signals.py:1750-1754`). A zero or missing denominator becomes ±inf and `clip` turns +inf into **1.0** (100% of supply in profit). That is a plausible default. The unapplied patch stops it.

### F-RESERVE-RISK and F-VDD — checkonchain lifespan charts

| Metric | Class | Family | Module | Provider | Unit |
|---|---|---|---|---|---|
| `reserve_risk` | OBSERVED INPUT | F-RESERVE-RISK | loaded `btc_inputs.load_all`; cleaned inf and percentile in `btc_signals.valuation` (`engine/btc_signals.py:756-762`) | `scripts/backfill_crypto.py` chart `reserve_risk` (`:55-66`). No `collectors/` adapter | chart units. Code compares to 0.02 (`config.yml:5802`) |
| `reserve_risk` high as distribution cap | ECONOMIC HYPOTHESIS | F-RESERVE-RISK | `btc_signals.allocation` (`:602-605`); `composite_state` (`:660-676`) | derived | boolean / label |
| `vdd_multiple` | OBSERVED INPUT | F-VDD | `btc_inputs.load_all`; `btc_signals.behaviour` (`engine/btc_signals.py:1242-1255`) | checkonchain chart `vdd_multiple` (`scripts/backfill_crypto.py:44-53`) | multiple |
| `cdd` | OBSERVED INPUT, **not loaded** | F-VDD sibling | `BgeoAdapter.fetch` only (`config.yml:2220`) | bitcoin-data.com | coin-days. Unused by `btc_inputs` / `btc_signals` |

`behaviour`'s docstring calls VDD orthogonal to the price-versus-cost-basis cluster (`engine/btc_signals.py:1246-1247`). This census keeps F-VDD as its own family. The orthogonality claim is the code's hypothesis, not a result of this lane.

Backfill writes `pulled_at` into a sidecar JSON (`scripts/backfill_crypto.py:109-113`). The series rows themselves have no knowledge time. No license string is recorded in that script.

### Other on-chain series the same modules touch

| Metric | Class | Family | Where | Unit | Note |
|---|---|---|---|---|---|
| `active_addresses` | OBSERVED INPUT | F-ACTIVITY | CM `AdrActCnt`; `btc_signals.bfi` growth percentile (`engine/btc_signals.py:242-246`) | count | |
| `tx_count`, `transfer_count`, `block_count` | OBSERVED INPUT | F-ACTIVITY / F-SECURITY | `CoinMetricsAdapter.fetch` only (`config.yml:2194-2197`) | count | not loaded by `btc_inputs` |
| `price_usd` | OBSERVED INPUT | none (not the engine price) | CM `PriceUSD` stored, not read by `load_all` | USD | engine price is Yahoo spliced with Coinbase (`engine/btc_inputs.py:54-72`) |
| `hashrate` | OBSERVED INPUT | F-SECURITY | CM `HashRate` via `btc_inputs`; mempool hashrate is a different series and is not this input | provider-native. No conversion in `_col` | |
| `difficulty` | OBSERVED INPUT | F-SECURITY | `MempoolAdapter.fetch` (`collectors/crypto_misc.py:289-327`); `btc_inputs` comment "shallow" (`engine/btc_inputs.py:106`) | difficulty | collector docstring: ~1 month daily, ~3 years on full history |
| `issuance_usd` | OBSERVED INPUT | F-MINER-REVENUE | CM `IssTotUSD` | USD / day | mixes coin issuance and price |
| `puell` | ALGEBRAIC DERIVATION | F-MINER-REVENUE | `issuance_usd / rolling_mean` (`engine/btc_signals.py:785-789`) | ratio | |
| hash ribbon state | ECONOMIC HYPOTHESIS | F-SECURITY | SMA cross of hashrate (`engine/btc_signals.py:775-784`) | label | |
| `hashprice`, `miner_stress`, `miner_econ_state` | algebraic, then hypothesis | F-MINER-REVENUE | `issuance_usd / hashrate` (`engine/btc_signals.py:1296-1319`) | USD per hashrate unit; 0–100 stress | zero hashrate becomes NaN (`replace(0, nan)`). State words are a hypothesis |
| `miner_sell_pressure`, `mpi` | OBSERVED, then `outflow_btc * close / mean` | F-MINER-FLOW | bgeo multi-column; `btc_signals.onchain_regime` (`engine/btc_signals.py:1563-1571`) | BTC, then USD index | column `miner_sell_pressure_minerOutflowBtc` |
| `ssr` | ALGEBRAIC DERIVATION | F-SSR | `mcap / stables.ffill` (`engine/btc_inputs.py:165-167`) | USD / USD | stables are not Bitcoin UTXO data. Zero stables → inf |
| `mayer` | ALGEBRAIC DERIVATION | F-MAYER | `close / SMA` (`engine/btc_signals.py:755`) | ratio | price family. Not on-chain. Not an F-MVRV confirmer |
| `coinbase_premium` | OBSERVED INPUT plus a self-computed spread | exchange basis, not on-chain | bgeo index and OKX USDT versus Coinbase close (`engine/btc_signals.py:1522-1554`) | percent | out of this valuation census except as a neighbor |
| `btc_dominance`, `etf_flow`, `funding`, `open_interest` | OBSERVED INPUT | not on-chain valuation | bgeo via `btc_inputs.load_all` | mixed | funding is the one bgeo route with a response receipt |

## Confirmation counting

Grep of `confluence|confirm|independent|n_signals|votes` in `engine/btc_signals.py` and `engine/btc_decision.py`:

- `_confirm` (`engine/btc_signals.py:48-65`) is a persistence delay. It does not count families.
- `momentum` and `structure` are vote averages. On-chain members are `sopr_momentum` (F-SOPR) and `sth_cost_basis` (F-STH-COST). Different families.
- `market_extreme` (`engine/btc_signals.py:1735-1774`) is the counter that sums tail votes and compares to `min_votes` (default 2, `config.yml:5910`). It currently stores `capit["nupl"]` and `capit["z"]` as two columns. Both are F-MVRV, so one family can satisfy `min_votes` alone.
- `btc_decision.py` has no such counter.

The pinned table lives in `tests/test_crypto_onchain_families.py` (`FAMILY_TABLE`). `nupl`, `z`, `mvrv_z`, and `mvrv_family` map to F-MVRV. `sopr` maps to F-SOPR. `independent_confirmation_count(["mvrv", "nupl"])` is 1. The engine change that makes `market_extreme` emit one `mvrv_family` vote is the unapplied patch `research/crypto_science/patches/cx-t11-20261012__btc_signals.py.patch`.

`valuation()`'s docstring calls NUPL and Mayer "cheap orthogonal cross-checks" (`engine/btc_signals.py:735-736`). NUPL is the identity above. Mayer is F-MAYER. The same patch corrects that sentence.

## Eligibility

**Eligible today, one family: F-MVRV, for display and for research as a single family.**

Reasons that are true in this tree: the CoinMetrics community metric is the configured source (`config.yml:2188-2192`, collector docstring `collectors/coinmetrics.py:1-8`); NUPL and realized cap are algebraic children of that one series (`engine/btc_inputs.py:161-164`); the decision receipt is already `context_only`. Display of the number does not require a gauntlet. Research may use the family as one input and must not score NUPL, MVRV-Z, and realized price as three confirmations.

**Not eligible, including for this same family:**

- Authority, trade sizing, or a market verdict. This lane ran no gauntlet.
- Point-in-time historical reconstruction. UNAVAILABLE on every family in this map, because the valuation frames carry no knowledge time. A backtest on the parquet is a latest-write replay.
- Provider revision policy. UNVERIFIED for CoinMetrics and BGeometrics inside the search bound above.
- Rights records. No license grant is in `collectors/coinmetrics.py`, `collectors/bgeo.py`, or `scripts/backfill_crypto.py`. That excludes checkonchain-seeded history (F-SOPR's optional 2011 tail, F-RESERVE-RISK, F-VDD) from any claim that depends on a right to keep republishing the chart scrape.

**Excluded as their own eligible families today:**

- **F-SOPR, F-STH-COST, F-SUPPLY-IN-PROFIT.** BGeometrics free tier `window_start` is `2022-06-13` (`config.yml:2203-2204`); the collector docstring states a rolling ~4-year window (`collectors/bgeo.py:6-8`). Cohort series are one cycle of provider window. Short history. Unknown revision policy. No knowledge time. The 2011 SOPR sentence in `btc_inputs` is not an engine invariant.
- **F-SUPPLY-IN-PROFIT additionally** fails the unavailable-denominator test in current code (`clip` to 1.0).
- **F-RESERVE-RISK, F-VDD.** Checkonchain HTML scrape, no rights record, no per-row clock, unknown revision policy. `cdd` is collected and unused.
- **F-MAYER.** Price / moving average. Not an on-chain confirmer.
- **F-SSR.** Off-chain stablecoin denominator. Unqualified ratio when that denominator is unavailable (current code can emit inf).
- **F-ACTIVITY, F-SECURITY, F-MINER-REVENUE, F-MINER-FLOW.** Observed inputs can be shown as series. Regime words (`capitulation`, `euphoria`, `miner_econ_state`, hash-ribbon labels) are economic hypotheses. Same knowledge-time gap. Difficulty's mempool window is shallow. These are not a second valuation family.
- **Collected and unwired:** `price_usd`, `tx_count`, `transfer_count`, `block_count`, `cdd`.

## Patches (not applied)

This lane owns no engine module. Defects are unified diffs:

- `research/crypto_science/patches/cx-t11-20261012__btc_signals.py.patch` — `market_extreme` casts NUPL and MVRV-Z as one `mvrv_family` vote; missing observations stay missing; the false "orthogonal" sentence in `valuation` is corrected.
- `research/crypto_science/patches/cx-t11-20261012__btc_inputs.py.patch` — non-positive or non-finite MVRV, market cap, supply, or stablecoin denominators become NaN. A supply ratio outside [0, 1] becomes NaN instead of a clipped 0 or 1.

Unit labels and metric-definition ids are not on the stored frames, so the engine cannot see a silent unit change that stays finite and in range. That check is `qualify_observation` / `qualify_fraction` in `tests/test_crypto_onchain_families.py`. Wiring it into the collectors requires a unit and definition id the providers are not currently storing. Left as a patch gap, not an engine edit.

Unbounded `ffill` of MVRV/NUPL (`engine/btc_signals.py:742-753`) still carries a stale print across a gap. Not patched: it is the same helper pattern across the signal file, and this lane does not own that file.
