# B04 — frozen metric definitions (Sector Central + Sector Cycles)

Base: `3d8d14acdc8de99fa2c17316aa22de6177364dbc` (2026-10-21). One row per published
metric of the two artifacts that a user reads as a number. `tests/test_sector_metric_definitions.py`
pins the `measured` rows: synthetic-input tests where the computation is isolatable,
source-formula pins (regex over the exact source line) where it is not; the doc marks
which. A metric whose window or endpoint cannot be shown exact from the code is
`unmeasured`, never guessed.

Reading keys: **ratio−1** = relative wealth (outperformance of A over B as a fraction of
B); **pp-diff** = arithmetic difference of two percentage returns. All series are
USD-denominated Yahoo EOD closes; no FX leg exists in any of these paths, so currency is
USD for every row. The shared price owner is the yahoo parquet store
(`engine/inputs.py:37` `store.read("yahoo", name)`); `yahoo_closes(basis="tr")` is the
total-return adjusted close (default), `basis="price"` the dividend-unadjusted close
(`engine/inputs.py:115-133`).

| field | artifact | formula as implemented (file:line) | window | ratio−1 or pp-diff | price or TR | benchmark | currency | endpoint exact? | status |
|---|---|---|---|---|---|---|---|---|---|
| `rs_21d` (sector) | `sector_cycles_data.js` `sectors[].now.rs_21d`; mirrored `sector_central_data.js` `momentum.rs_21d` | `rs.pct_change(21).iloc[-1] * 100` where `rs = close[ticker] / close[SPY].reindex(...).ffill(limit=5)` — `engine/sector_cycles.py:475`, ratio at `:441`, ffill limit `RS_BENCH_FFILL_LIMIT=5` `:412` | 21 sessions (panel rows) | ratio−1, in % (ratio momentum) | TR (`yahoo_closes()` default, `engine/sector_cycles.py:1314`; meta `basis: "tr"` `:1409`) | SPY (`config engine.rs_ranking.benchmark`, `engine/sector_cycles.py:1332`; default param `bench="SPY"` `:458`) | USD | yes — session-row `pct_change`, last row | **measured** (synthetic pin) |
| `rs_63d` (sector) | same | same formula, `engine/sector_cycles.py:476` | 63 sessions | ratio−1, % | TR | SPY | USD | yes | **measured** (synthetic pin) |
| `rs_126d` (sector) | same | same formula, `engine/sector_cycles.py:477` | 126 sessions | ratio−1, % | TR | SPY | USD | yes | **measured** (synthetic pin) |
| `rs_above_trend` | same (`now.rs_above_trend`) | `rs.iloc[-1] > rs.rolling(200).mean().iloc[-1]` — `engine/sector_cycles.py:478` | 200-session MA of the RS ratio | boolean | TR | SPY | USD | yes | **measured** (synthetic pin) |
| `rs_21d`/`rs_63d`/`rs_126d` (basket) | `sector_cycles_data.js` baskets (`b-*`) | `_basket_rs`: `(full/spy.reindex(...).ffill()).pct_change(N)*100` — `engine/sector_cycles.py:1133-1143`; `full` = equal-weight member-TR deep calendar (`engine/basket_index.consolidated_candle`, called `:1154`) | 21/63/126 sessions | ratio−1, % | TR (member-TR EW index) | SPY, **ffilled without limit** (contrast `:441`) | USD | yes | **measured** (synthetic pin of the shared shape; basket index itself not pinned here) |
| `rs_rank` / `rs_21d_rank` | `sector_cycles_data.js` `now.rs_rank`/`now.rs_21d_rank`; mirrored central `momentum` | descending cross-sectional rank over the 11 sectors by `rs_63d` / `rs_21d` — `_stamp_rs_ranks`, `engine/sector_cycles.py:1271-1281` | the current night's cross-section | rank (1 = strongest) | TR (ranks the TR-basis RS) | SPY-relative | USD | yes | **measured** (synthetic pin) |
| `rs_history[]` (`date`,`rs_21d`,`rs_63d`) | `sector_cycles_series_data.js`/core per-sector trail | `_leadership_history_counted`: the same `pct_change` formula evaluated at every eligible past date, first eligible row at `_RS_MIN_ROWS=210`, capped `RS_HISTORY_MAX_POINTS=252` — `engine/sector_cycles.py:486-528` | 21/63 sessions as-of each past date | ratio−1, % | TR | SPY | USD | yes — and labelled **reconstructed** (`meta.rs_history.mode="reconstructed_price_history"`, `naturally_observed=False`, `engine/sector_cycles.py:1407-1408`) | **measured** (synthetic pin) |
| `pos` (0–100 cycle position) | `sector_cycles_data.js` `now.pos` | detrended-oscillator position, `round(pos_now, 1)` — `engine/sector_cycles.py:865`; structure math on `close_price` for the 11 sector ETFs since W2.2 (`compute` docstring `:1306-1312`) | oscillator-defined (ZigZag/detrend chain) | n/a (bounded 0–100 index) | price basis for sector ETFs (`closes_px`, `:1323`), `tr_fallback` labelled | none (absolute) | USD | no — the transform chain was not endpoint-pinned in this census | **unmeasured** |
| `ret_12m` | `sector_central_data.js` `forward.ret_12m` | `_abs_gate` → `_cum_ret(s, 252, skip=0)`: `s.iloc[-1]/s.iloc[-253] - 1.0` — `engine/narrative_rotation.py:244-251`, `_cum_ret` `:213-222`; sector closes = `yahoo_closes()` TR (`engine/sector_central.py:865-868`) | 252 sessions | ratio−1 (decimal) | TR | none (absolute return) | USD | yes | **measured** (synthetic pin) |
| `pos_12m` | same `forward.pos_12m` | `bool(ret_12m > 0)` — `engine/narrative_rotation.py:248` | inherits `ret_12m` | boolean | TR | none | USD | yes | **measured** (synthetic pin) |
| `above_200dma` / `trend_pass` | same `forward.above_200dma`; board gate | `s.iloc[-1] > s.rolling(200, min_periods=100).mean().iloc[-1]`; pass = above AND `pos_12m` — `engine/narrative_rotation.py:245-249` (`SMA_TREND_D=200` `:49`) | 200-session MA | boolean | TR | none | USD | yes | **measured** (synthetic pin) |
| `heat_1D` / `heat_1M` / `heat_YTD` | `sector_central_data.js` rows `heat.*` | cap-weighted mean of tile `perf[tf]` when `size_basis != "weight_proxy"`, else equal-weighted — `engine/sector_central.py:195-217` (cap-weight switch `:186`) | the feed's own 1D/1M/YTD windows (Finviz `perf`, consumed as delivered `:188-196`) | pp-diff-style mean of percentage numbers (not a return computation) | the feed's perf basis (upstream, not re-derived) | none (cross-sectional within sector) | USD | no — window semantics owned by `sp500_heatmap.json`'s producer, not shown exact in this repo | **unmeasured** (aggregation formula pinned by source; window upstream) |
| `adv` / `dec` | same `heat.adv`/`heat.dec` | count of sector tiles with 1M `perf > 0` / `< 0` — `engine/sector_central.py:205-219` | the feed's 1M window (upstream) | counts | upstream | none | USD | no — same upstream-window caveat | **unmeasured** (inputs' window upstream) |
| `breadth_pct` | same `heat.breadth_pct` | `round(100.0 * adv / max(adv + dec, 1), 0)` over the 1M adv/dec — `engine/sector_central.py:220` | the feed's 1M window | percent of counted tiles | upstream | none | USD | formula yes; inputs' window upstream (row above) | **measured** for the ratio itself (source pin — `_heat_table` reads a site file, not isolatable without `site/`) |
| conviction `score` (0–100) | `sector_central_data.js` `conviction.score` | `raw = clip(gated + 0.5*mom, -1, 1)`; `score = round((raw + 1.0)/2.0 * 100)` — `engine/sector_central.py:376-377`; caps: below-trend or stretched/crowded can't exceed 57 `:393-398`; risk-size shave `:406-413` (multiplier currently 1.0 everywhere — no-op) | composite of that night's layers | n/a (bounded 0–100 index, not a return) | n/a | n/a | USD-denominated inputs | yes — formula exact; fuser behaviour pinned by existing `tests/test_sector_central.py` | **measured** (source pin + existing suite) |
| `fwd` (grader realized return) | `sector_central_data.js` `grader.by_horizon.{21,63,126}d` (via `recs[].fwd`) | next-bar-filled forward return: ENTRY = close of the bar strictly after the call bar, `fwd_ret_H = close[fill+H]/entry − 1` — `engine/grading.py:177-215` (`forward_metrics`), thin wrapper `:248-254`; horizons `_HORIZONS_D=(21,63,126)` trading bars — `engine/sector_central_grader.py:30` | H ∈ {21, 63, 126} bars after the fill | ratio−1 (decimal) | sector: TR panel close (`engine/sector_central_grader.py:34-40`); basket: frozen EW `level_tr` (`:42-57`) — mixed bases, see B01 F5 | none (absolute; benchmark handled separately, next row) | USD | yes | **measured** (synthetic pin of `grade_next_bar_return`; horizons source-pinned) |
| `excess` / `mean_excess_vs_bench` | same `grader.by_horizon` | `"excess": (fr - br)` where `br` = the same next-bar SPY return over the same horizon — `engine/sector_central_grader.py:306-309`, mean `:334-335` | same H bars | **pp-diff** (arithmetic difference of two decimal returns — NOT relative wealth) | TR both sides (SPY from the same panel `:260-262,308`) | SPY | USD | yes | **measured** (source pin — inline in `grade()`, not isolatable) |
| `dir_hit_rate` | same `grader.by_horizon.{h}d.dir_hit_rate` | `((up.fwd > 0).sum() + (dn.fwd < 0).sum()) / n` over graded calls — `engine/sector_central_grader.py:319,332` | per horizon {21,63,126}d | share in [0,1] | per `fwd` row | conditional on call direction (up/down) | USD inputs | yes | **measured** (source pin; conditional directional hit rate, not a win rate) |
| `pos_rate`, `mean_fwd`, `mean_excess` (by tier) | same `grader.by_horizon.{h}d.by_tier` | per conviction-label subgroup (n≥3): `(fwd>0).mean()`, `fwd.mean()`, `excess.mean()` — `engine/sector_central_grader.py:326-330` | per horizon | share / decimal means | per `fwd` row | excess vs SPY | USD | yes | **measured** (source pin) |
| `rank_ic` | same `grader.by_horizon.{h}d.rank_ic` | mean over dates (≥3 distinct scores) of Spearman(score, fwd) — `engine/sector_central_grader.py:323,333` | per horizon | correlation in [−1,1] | per `fwd` row | none | USD inputs | yes | **measured** (source pin) |
| `n_above_trend`, `n_sectors` | `sector_central_data.js` `market.n_above_trend`/`meta.n_sectors` | `sum(1 for s in sectors if s.forward.trend_pass is True)` — `engine/sector_central.py:920` | that night's cross-section | counts | inherits `trend_pass` | none | USD inputs | yes | **measured** (source pin) |
| 20-interval basket measurement | — | **does not exist on these two artifacts.** The nearest namesake is `intervals` keyed per notch on the basket-washout surface (`scripts/build_basket_washout_state.py:46`) — a different page, out of this census's scope | — | — | — | — | — | no such field to pin | **unmeasured** (absent here; nothing to define) |

Notes that keep the table honest:

- The RS family is **relative wealth**: `rs_63d` = (ticker/SPY today ÷ ticker/SPY 63
  sessions ago) − 1, expressed in %. It is not "ticker return minus SPY return"; at
  +15.5% ticker vs +2.0% SPY over the same 63 sessions it reads 13.2, not 13.5 (the
  synthetic pin in the test uses exactly this pair).
- The grader's `excess` family is the opposite convention — an arithmetic difference of
  two decimal returns. The two families answer different questions and must never be
  pooled.
- `heat_*`/`adv`/`dec` consume the heatmap feed's `perf` fields as delivered; this repo
  aggregates but does not define their windows. They stay `unmeasured` here rather than
  borrowing an unverified Finviz definition.
- Hazard-score, sizing-multiplier and hit-rate fences are untouched: the W4.6 risk-size
  multiplier ships 1.0 in every cell (`engine/sector_central.py:406-413` — no-op by
  verdict), and `dir_hit_rate` is a conditional directional hit rate over graded calls
  only, not a win rate.
