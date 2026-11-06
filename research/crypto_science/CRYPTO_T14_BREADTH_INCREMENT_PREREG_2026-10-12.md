# T14 preregistration — cohort breadth, relative leadership, capital-source context

Lane `cx-t14p-20261012`. Registered 2026-10-12. Census read from the worktree after candidate base `#8050` `fd8095012e91` was applied onto `origin/main` (merge-base `7150f29a765`). This file registers a study. It computes no outcome, fits no coefficient, and reads no `data/` store.

Display-tier registration only. Portfolio allocation, position sizing, execution, and any change to Bitcoin decision exposure are outside this document.

## Census

Classifications use three roster words and two measurement words. Roster: `pit-roster` (a membership date is the study date, and a later row cannot enter), `current-roster` (the output carries `roster_label = current_roster`), or `unlabeled`. Measurement: `qualified-flow` (a creations/redemptions or equivalent print) or `price-derived`. A supply stock is named `supply-stock`, which is neither word.

### `engine/crypto_universe.py`

`load_universe_snapshot` (`engine/crypto_universe.py:52`) is `unlabeled` and `price-derived`.

- It keeps the last row of each `market_*.parquet` (`:80-86`) and then keeps only files whose last index date equals the maximum (`:95-101`, exclusion `OLDER_SNAPSHOT`).
- The collector accrues one current top-50 snapshot per asset per day and does not backfill names that have left the page (`collectors/crypto_misc.py:69-74`, `:83-90`). Departed names stop receiving rows, then drop out of the read as `OLDER_SNAPSHOT`.
- The return dict is `as_of`, `rows`, `excluded`, `requested`, `observed`, `sources` (`engine/crypto_universe.py:148-150`). There is no `roster_label`.
- Rank, price, and `change_24h_pct` / `change_7d_pct` / `change_30d_pct` are the provider market fields (`collectors/crypto_misc.py:160-173`).
- Clock: the collector stamps the parquet index with `datetime.now(timezone.utc).date()` (`collectors/crypto_misc.py:146`). `source_updated_at` is stored (`:181`) and is not read by the snapshot function. A second clock, `pd.Timestamp.now(tz="UTC")` (`engine/crypto_universe.py:64`), drops a last row dated after read-time today (`:88-90`).

`breadth_read` (`engine/crypto_universe.py:158`) is `unlabeled` and `price-derived`.

- `as_of` is the max `as_of` among the rows it was given (`:164`). A row with any other `as_of` is ineligible (`:169-170`).
- `basis` is `reported_30d_return_positive` (`:175`). Eligible means `history_days >= 30` and a finite `change_30d` (`:167-170`). Positive means `change_30d > 0` (`:172`). A missing return is excluded (`:161`). Below 10 eligible names, `available` is false and `value` is null (`:176-178`).
- Clock: that max row `as_of`. The function has no `as_of` parameter.

`_state` (`:28-41`) is a per-asset display word. `Leading` means the reported 30-day change is at least 15 (`:33-34`). It is `price-derived`. It is not a cohort leadership statistic.

### `engine/crypto_market_state.py`

`build_market_state` (`:132`) is `unlabeled`. It has no roster.

- Total cap (`total_market_cap_history`, `:49-69`) is `price-derived`: BTC cap divided by BTC dominance, then CoinGecko `total_mcap_usd` overlaid.
- The stance (`:154-184`) uses the 30-day total-cap percent and the 30-day dominance point change (`_delta`, `:39-46`).
- Alt-season heat (`:258-280`) is `price-derived`: the ETH/BTC ratio over 90 bars, minus a dominance term (`:264-266`). Words include `Bitcoin-led`.
- Clock for the page: the max of the last dates of total cap, dominance, fear-and-greed, stablecoin stock, and BTC (`:282-287`). ETF carries its own `as_of` (`:317`). Stablecoins and volume do not.

Flow object (`:312-332`):

| Key | Class | Clock |
| --- | --- | --- |
| `flows.etf` | `qualified-flow`. Sum of the last five non-null Farside `total` cells (`:193-195`). Farside is the US spot-ETF net creation table in US$m (`collectors/farside.py:1-13`, parser `:46-71`). The adapter refetches the whole table; a past cell is not revision-locked. | Last date of that `total` series (`engine/crypto_market_state.py:196`), stored as `flows.etf.as_of`. |
| `flows.stablecoins` | `supply-stock`. DefiLlama `totalCirculatingUSD.peggedUSD` (`collectors/crypto_misc.py:190-216`), column `stablecoin_mcap_usd`. The 30-day percent and USD changes (`engine/crypto_market_state.py:186-187`) are transforms of that stock. | Provider unix day, normalized (`collectors/crypto_misc.py:212`). No `as_of` on the flow object (`engine/crypto_market_state.py:319-325`). |
| `flows.volume` | `price-derived` activity. The object sets `proxy` to `BTC spot-volume proxy` (`:331`). | Volume series end. No own `as_of`. |

Funding, open interest, and DVOL (`:214-256`) come from the last row of `vector/signals` (`:125-129`). They are positioning and a volatility level. They are not a cohort flow. They have no own `as_of`.

### Roster and cohort fields `scripts/build_crypto.py` consumes

- `load_universe_snapshot(50)`, then `_enrich_universe`, then `breadth_read` (`scripts/build_crypto.py:469-473`).
- `_enrich_universe` (`:151-166`) may replace `history_days` and the spark for BTC, ETH, and SOL from a deeper close series, cut at the row `as_of` (`dates.normalize() <= cutoff`). It does not recompute `change_30d`.
- `crypto.class_state/v1` publishes `as_of` from the market-state clock (`:499`) and a separate `universe_coverage.as_of` from the snapshot (`:501`). `flows` on that object are the flow state words (`:514-516`).
- `crypto_rails` (`:383-424`) reads the current `data/baskets/membership.json` basket and skips members with `removed` set (`:393-399`). The tile (`:412-421`) has ticker, last price, a 21-session price change (`:405-406`), and a display word. It has no `roster_label` and no `as_of`. Roster class: `unlabeled`. Measurement: `price-derived`. Clock: the last stored yahoo bar, unlabeled.

`engine/eth_state.py` relative state (`:45-59`, consumed at `:157`) is a fixed ETH or SOL versus BTC pair. `Leading Bitcoin` means the 90-session relative change is at least 5 (`:55-56`). `price-derived`. `as_of` is the asset series' last date (`:75`, `:109`). `build_states` also stamps wall-clock `generated_at` (`:195`). Not a cohort roster.

`engine/alt_cycle.py` `breadth_view` (`:105-126`) bundles the ETH/BTC level, the SOL/ETH level (`beta_ratio` last bar, `:93-97`), dominance, and a judgment score. The module describes dominance as current-context (`:3-6`). The dict has no `as_of` and no roster label. `price-derived`. `unlabeled`.

### Other capital-source, stablecoin, and flow fields on the vector input path

- `engine/btc_inputs.py:124-126` loads `bgeo/etf_flow_btc` and Farside `etf_flows`. `engine/btc_signals.py:1575-1617` (`etf_flow`) is the `qualified-flow` transform. The BTC-unit series is multiplied by price to make `etf_flow_usd_mn` (`:1591`). Farside `total` is already US$m (`:1606`). Both are reindexed to the BTC close index. No `as_of` argument. No revision vintage.
- `engine/btc_inputs.py:95` and `:128-129` load DefiLlama `stablecoins` and `stablecoin_peg`. `stablecoin_tide` (`engine/btc_signals.py:1100-1123`) is `supply-stock` growth, z-scored. The peg block (`:1125-1139`) is a price deviation.
- `ssr` (`engine/btc_inputs.py:165-167`) is BTC mcap divided by the stablecoin stock. `ssr_oscillator` (`engine/btc_signals.py:1556-1562`) is that ratio. `price-derived` over a `supply-stock` denominator.
- `impulse_pos_pct` (`engine/btc_signals.py:1501-1504`) is the rolling share of positive single-asset impulse days. The comment calls it a stand-in for a top-350 breadth statistic. `price-derived`. It is not a cohort panel.
- `taker_flow` (`engine/btc_signals.py:1429-1434`) is an OKX taker buy-share. Display aggressor ratio. Not a capital-source print.

No function in this census takes a study date and ignores later roster or price rows. `breadth_read` ignores later rows only when those rows are absent from its argument, or when their `as_of` is strictly earlier than the max. `_enrich_universe` ignores closes dated after the row `as_of`.

## 1. Declared question

Does breadth, relative leadership, or a separately qualified capital-source context add out-of-sample information for fixed 7-day and 30-day BTC returns and for cohort dispersion at those same horizons?

One question. Four real contrasts, each scored on four targets. A clear on one contrast does not transfer to another. Horizons are 7 and 30 calendar days. No other horizon is part of this registration.

### Targets

BTC close is the study price. An episode uses the close on the exact calendar date. A missing date makes the episode unavailable. A missing print is unavailable. It is never filled with zero.

- `ret(t, h) = close(t+h) / close(t) - 1`
- Member return `mret(i, t, h) = price(i, t+h) / price(i, t) - 1` when both prices exist, `price(i, t) > 0`, and `i` is in the ex-stable cohort defined below. Otherwise unavailable.
- `disp(t, h)` = population standard deviation (`ddof = 0`) of the available member returns. The episode is unavailable when fewer than 10 member returns are available, or when the unavailable share of the ex-stable cohort exceeds 0.20.

The forward window starts at the close on `t` and ends at the close on `t+h`. Trailing features end at the close on `t`. The shared boundary price is known at `t`.

### Cohort used by every real contrast

`C(t)` is the set of `coin_id` with an observation whose index date is exactly `t` and whose recorded `market_cap_rank` on that row is an integer in `1..50`. Rank is the stored field. It is not recomputed from later market caps. An observation dated before `t` does not fill a missing membership on `t`.

This cohort function is not in the tree. Section 10 names it. Until it exists, the question stays unestimated. `load_universe_snapshot` and `breadth_read` are latest-cross-section reads and are not substitutes.

## 2. Matched baselines

Every real contrast and both negative controls use the same baseline block, known entirely from BTC closes dated on or before `t`:

- `btc_trail(t, h) = close(t) / close(t-h) - 1`
- `trend(t) = close(t) / mean(close on [t-89, t]) - 1`, requiring at least 60 closes in that window
- `vol(t)` = population standard deviation of the 30 daily log returns ending at `t`, requiring at least 20 of those returns. Not annualized.

The baseline model is intercept plus these three columns. The full model is the baseline block plus one candidate column. An episode missing any baseline input is unavailable for every contrast on that `(t, h)`.

## 3. Negative controls

Chosen here, before any outcome is computed.

- `NC-ROTATE`. The candidate column at episode start `t` is the same feature's value on the exact date `t - 173` days. `173` is prime and is not a multiple of 7 or 30. A missing rotated date makes that control episode unavailable.
- `NC-WEEK`. The candidate column is `1` when `date.fromisoformat(t).isocalendar().week` is odd, and `0` when it is even. No market input.

Each control is scored with the same models, split, and interval rule as a real contrast, on its own complete episodes. A real contrast on a target is runnable only when both controls on that target have `N_test >= 8`. If either control's decision interval lies entirely above 0, every real contrast on that target is void.

## 4. Survivorship, rebalancing, delisting

These are computations, not prose caveats.

Survivorship. The primary feature at `t` uses `C(t)` only. The forbidden estimator takes the symbols inside today's top 50 and pushes their later-known history back through earlier dates. The diagnostic, reported beside the primary and never substituted for it, is:

```text
surv_gap(t) = breadth_terminal_backfill(t) - breadth(t)
```

`breadth_terminal_backfill` is computed only as that diagnostic. If `breadth(t)` from `C(t)` is unavailable, the episode is unavailable. The backfill does not replace it. The collector's own record (`collectors/crypto_misc.py:73-74`) is a going-forward snapshot accrual, so dates before the first stored cross-section have no `C(t)`.

Rebalancing. For each complete dispersion episode, report:

```text
turnover(t, h) = 1 - |C(t) ∩ C(t+h)| / |C(t)|
```

`turnover` is not a model column. An identifier that first appears on a date after `t` is outside `C(t)` and outside `disp(t, h)`.

Delisting and missing follow-through. `mret` unavailable stays unavailable. It is not set to 0 and not set to -1. `disp` uses the available subset and reports `n_dropped`. The 0.20 share rule in section 1 drops the episode. One pre-declared bound, reported as a bound and not as the point estimate: recompute `disp` after setting each dropped member to the minimum observed member return in that episode. If the dispersion contrast's decision would change under that bound, the dispersion contrast is unavailable.

Identity breaks already truncate a file when `source` or `coin_id` changes (`engine/crypto_universe.py:116-124`). The study treats the post-break `coin_id` as a different asset. It does not stitch the two histories.

## 5. Stablecoin-denominator confound

Closed identity list, matched on uppercase `symbol` or lowercase `coin_id`. Membership is this list. It is not inferred from a small return.

```text
symbols: USDT, USDC, DAI, FDUSD, TUSD, USDE, USDS, PYUSD, USDP, GUSD, FRAX, LUSD, CRVUSD
coin_ids: tether, usd-coin, dai, first-digital-usd, true-usd, ethena-usde, usds,
          paypal-usd, paxos-standard, gemini-dollar, frax, liquity-usd, crvusd
```

`C_ex(t) = C(t)` minus that set. Primary breadth and primary leadership use `C_ex(t)`. Dispersion uses `C_ex(t)`.

```text
breadth(t) = |{i in C_ex(t) : ret30(i, t) > 0}| / |{i in C_ex(t) : ret30(i, t) available}|
```

`ret30(i, t)` is the trailing 30-calendar-day simple return from prices dated on or before `t`, for a member of `C(t)`. The provider field `change_30d_pct` on the row dated `t` is acceptable only as a receipt check against that computed return. A disagreement above 1 percentage point makes `ret30(i, t)` unavailable for that name. A missing return is excluded from the numerator and the denominator.

```text
total_ex_stable(t) = total_mcap(t) - stable_mcap(t)
dom_ex(t) = btc_mcap(t) / total_ex_stable(t)
```

`stable_mcap(t)` is the DefiLlama `stablecoin_mcap_usd` observation on date `t`. `total_mcap(t)` and `btc_mcap(t)` are the stored cap observations on date `t`. If any of the three is missing, `total_ex_stable` and `dom_ex` are unavailable. They are not reconstructed by rearranging `btc_mcap / dominance` (`engine/crypto_market_state.py:60`), and `stable_mcap` is not backed out of that identity.

The paired with-stables breadth (same formula on `C(t)` rather than `C_ex(t)`) and the raw BTC dominance share are confound diagnostics. They are not extra chances to clear the decision rule. The decision column for breadth is the ex-stable figure.

Stablecoin issuance changes raw dominance and raw total cap while the risky cohort's prices stay put. That is why the decision columns exclude the list above and, where a cap ratio is reported as a diagnostic, use `total_ex_stable`.

## 6. honest-N

Episodes do not overlap.

```text
t_k = t_0 + k * h,  k = 0, 1, 2, ...
t_0 = earliest calendar date with C(t_0) defined
honestN(h, contrast) = |{ k : episode(t_k, h, contrast) is complete }|
```

An episode is complete when every baseline input, the single candidate column, and the target are available under the rules above. A calendar day inside `(t_k, t_k+h)` is not also a start. Overlapping rolling windows are not counted.

```text
N_train = floor(honestN / 2)
N_test = honestN - N_train
```

The reported honest-N is `honestN`. The decision also prints `N_train` and `N_test`. The split is chronological: the earliest `N_train` complete episodes are the fit sample; the rest are the test sample. No random fold.

## 7. Decision rule and effect uncertainty

Fit ordinary least squares with an intercept on the train episodes. No scaling, no penalty, no column dropped after seeing the fit. A rank-deficient train matrix makes that contrast unavailable.

Freeze those coefficients. On the test episodes predict from the baseline model and from the full model.

```text
delta_r2 = (SS_base - SS_full) / SS_tot
delta_rmse = RMSE_base - RMSE_full
```

`SS_tot` uses the test-sample mean of the target. `SS` and `RMSE` use the frozen predictions. Positive `delta_rmse` means the full model has the smaller test error.

Uncertainty is a percentile interval. Resample test episodes with replacement, `B = 2000`, seed `20261012`. Recompute `delta_r2` and `delta_rmse` on each draw from the frozen coefficients. Do not refit inside the draw. The interval is test-episode sampling uncertainty conditional on the fitted coefficients.

The 95% interval is the 2.5 and 97.5 percentiles of those draws. The contrast clears only when the `delta_r2` interval lies entirely above 0 and the `delta_rmse` interval lies entirely above 0. Otherwise the contrast is not distinguished from no incremental information. If `N_test < 8`, the contrast is unavailable and no interval is computed.

This procedure does not use a p-value. The reported objects are the two point estimates, the two intervals, `honestN`, `N_train`, `N_test`, and `n_dropped` where a dispersion target is involved.

Sixteen real cells are pre-declared: breadth, leadership, `etf_30`, and `supply_stock_growth`, each on `ret` and `disp`, each at `h = 7` and `h = 30`. No sentence may say the block works because any cell cleared. A void from section 3 voids all real cells on that target.

Any later change to horizons, the identity list, the baseline block, the controls, the split, the seed, `B`, or the interval rule requires a new dated preregistration. Editing this file after outcomes have been computed voids every cell in it.

## 8. Missing qualified flow

A missing qualified flow field permits a price and breadth study and never an invented flow proxy.

Runnable without a flow print: `breadth` and `leadership` on `C_ex(t)`, plus the baseline block. The result says the capital-source cells are unavailable.

`etf_30(t)` is the sum of Farside `total` (US$m) on dates in `[t-29, t]`, and only when the latest print date is on or after `t-5`. Otherwise `etf_30(t)` is unavailable. The BTC-unit series times price (`engine/btc_signals.py:1591`) is not a second flow column.

`supply_stock_growth(t) = stable_mcap(t) / stable_mcap(t-30) - 1` when both stock observations exist. Its basis string is `supply_stock_growth`. It is a separate cell. It is not added to `etf_30`, and it is not renamed to a flow.

These stay out of every candidate column: BTC spot-volume percentile (`engine/crypto_market_state.py:331`), raw or ex-stable dominance, total-cap percent, the ETH/BTC ratio, `ssr` (`engine/btc_inputs.py:165-167`), `impulse_pos_pct` (`engine/btc_signals.py:1501-1504`), OKX taker share, funding, and open interest. A missing `etf_30` or a missing `stable_mcap` is unavailable. None of those series fills it.

## 9. What this grants

Display-tier reporting of a cell that has been estimated under sections 6 and 7, including a cell that is unavailable or not distinguished. The report shows the interval and honest-N.

This registration grants no portfolio allocation authority. It does not authorize sizing, execution, a new score, or a write into the Bitcoin decision exposure. Research R1–R9 stays unpromoted. An instrument cell is not a market verdict.

## 10. Signatures a later build lane must provide

No existing function computes cohort breadth or cohort relative leadership at a study date. `breadth_read` (`engine/crypto_universe.py:158`) has no `as_of` parameter and follows the newest row date in its argument. `build_asset_state` (`engine/eth_state.py:62`) and `breadth_view` (`engine/alt_cycle.py:105`) follow the last bar they are given. This lane does not add an engine module.

A later build lane provides two pure functions. Both return before any outcome window. Both are unchanged when observations dated after `as_of`, or prices dated after `as_of`, are appended.

```text
cohort_breadth_asof(
    observations: Sequence[Mapping[str, object]],
    as_of: str,
    *,
    top_n: int = 50,
    min_eligible: int = 10,
    stablecoin_ids: frozenset[str],
) -> dict
```

Output keys: `as_of`, `roster_label` (`point_in_time`), `basis` (`pit_trailing_30d_return_positive_ex_stable`), `eligible`, `n_roster`, `excluded_stablecoins`, `available`, `value`. `value` is null when `available` is false.

```text
cohort_leadership_asof(
    observations: Sequence[Mapping[str, object]],
    as_of: str,
    btc_trailing_30d: float | None,
    *,
    top_n: int = 50,
    min_eligible: int = 10,
    stablecoin_ids: frozenset[str],
) -> dict
```

`basis` is `pit_trailing_30d_return_above_btc_ex_stable`. Leadership is the share of eligible ex-stable members whose trailing 30-day return is strictly greater than `btc_trailing_30d`. `btc_trailing_30d` is the BTC trailing return known at `as_of`. When that argument is null, `available` is false and `value` is null.

A display reader that keeps today's roster may exist beside those two. Its output includes `roster_label = current_roster`, and the study in sections 1–8 refuses any measurement whose `roster_label` is not `point_in_time`. An output with no `roster_label` is unlabeled (`breadth_read` and `load_universe_snapshot` are unlabeled) and is refused by the study for the same reason.

`_state` returning `Leading` (`engine/crypto_universe.py:33-34`) and `eth_state` returning `Leading Bitcoin` (`engine/eth_state.py:55-56`) are not implementations of `cohort_leadership_asof`.
