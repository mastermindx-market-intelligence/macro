# Served definition — Prophet US indicator, clock, ranks (code receipts)

Every claim is a `path:line` receipt from this checkout. No paraphrase beyond what the cited lines say.

## 1. Indicator cascade — `engine/canon.py`

Constants (single source; Terminal imports these) at `engine/canon.py:417-427`:

```
RSI_LEN, FAST_LEN, BASE_LEN, SIG_LEN = 14, 14, 60, 5
STOCH_LEN, SMOOTH_K, SMOOTH_D = 14, 3, 3
OB, OS = 80, 20
CONF_W, BUY_RSI_MAX, EXT_RSI, REV_BARS = 8, 65, 70, 3
CONFLUENCE_PARAMS = {
    "rsiLen": RSI_LEN, "macd_fast": FAST_LEN, "macd_slow": BASE_LEN, "macd_signal": SIG_LEN,
    "stoch_len": STOCH_LEN, "smooth_k": SMOOTH_K, "smooth_d": SMOOTH_D,
    ...
    "resample": "session_grouped_3", "ema": "adjust_false", "rma": "sma_seeded",
}
```

| function | file:line | what the code says |
|---|---|---|
| `rma` | `engine/canon.py:311-340` | Wilder's RMA == Pine `ta.rma`: SMA-seeded on the first `n` finite values, then recursive `adjust=False` with `alpha = 1.0 / n`. NaN after seed: output carries `prev`. |
| `ema` | `engine/canon.py:343-350` | Recursive EMA == Pine `ta.ema`: `s.ewm(span=span, adjust=False, min_periods=span).mean()`. |
| `rsi` | `engine/canon.py:353-362` | Wilder RSI on SMA-seeded RMA (== Pine `ta.rsi`): `d = close.diff()`; `up = rma(d.clip(lower=0), n)`; `dn = rma((-d).clip(lower=0), n)`; `100 - 100 / (1 + up/dn)`. Default `n=14`. |
| `rsi_macd` | `engine/canon.py:430-434` | Pine 'RSI-based MACD': `r = rsi(close, RSI_LEN)`; `macd = ema(r, FAST_LEN) - ema(r, BASE_LEN)`; return `macd, ema(macd, SIG_LEN)` → EMA(RSI,14) − EMA(RSI,60), signal = EMA(macd,5). |
| `stoch_rsi_kd` | `engine/canon.py:437-443` | Pine StochRSI: stochastic OF the RSI over `STOCH_LEN`, then `%K = rolling(SMOOTH_K).mean()`, `%D = k.rolling(SMOOTH_D).mean()`. |
| `resample_sessions` | `engine/canon.py:365-398` | Session-GROUPED resample: `grp = np.arange(len(s)) // n`; last close of each group. Phase is counted from **this series' first bar**. |
| `confluence_signals` | `engine/canon.py:446-502` | Oracle frame: `s3, _ = resample_sessions(daily_close, 3)`; RSI-MACD + StochRSI on that 3D grid; weekly confirm `W-FRI` (`engine/canon.py:466-469`, `_resample_weekly` at `:505-513`); CB/CS use `w_bull_on3 \| b1_from_os` (`:476-482`). Extra regime columns: monthly `ME` and `2W-FRI` RSI-MACD (`:489-494`). |

**Production does not call `engine.canon.rsi_macd` for the live board.** Served call path (the path that actually runs):

- `scripts/build_stock_library.py:234` `from engine import signal_gate  # owner's confluence T1->T4 cascade`
- `scripts/build_stock_library.py:3745` `sig_verdict[ticker] = signal_gate.gate(ticker, close)`
- `engine/signal_gate.py:65-67` `from engine import signal_quality` / `from engine.signal_quality import analyze` / `from engine import confluence_tiers`
- `engine/signal_gate.py:379` `def gate(ticker, daily_close, ...)`
- `engine/signal_gate.py:468` `casc = confluence_tiers.cascade(daily_close, take_active=take_active, ...)`
- `engine/signal_gate.py:110` `BUYABLE_TIERS = ("T1", "T2", "T3")`
- `engine/signal_gate.py:113-120` `is_buyable`: `eligible` and `tier_cascade in BUYABLE_TIERS`
- `engine/confluence_tiers.py:45` `from engine.technicals import rsi`
- `engine/confluence_tiers.py:255-262` `_ema = s.ewm(span=span, min_periods=span).mean()` (pandas default `adjust=True`); `_rsi_macd` = `_ema(rsi,14) - _ema(rsi,60)`, signal = `_ema(macd,5)`
- `engine/signal_quality.py:44` `from engine.technicals import rsi`
- `engine/signal_quality.py:68-75` same `_ema` / `_rsi_macd` as confluence_tiers (pandas default `adjust=True`)
- `engine/technicals.py:26-31` `rsi`: `delta.clip(lower=0).ewm(alpha=1/n, min_periods=n).mean()` — **not** SMA-seeded RMA.
- `engine/confluence_tiers.py:56-57` same `RSI_LEN, FAST_LEN, BASE_LEN, SIG_LEN = 14, 14, 60, 5` and `STOCH_LEN, SMOOTH_K, SMOOTH_D = 14, 3, 3`.
- No module on this gate path imports `engine.canon`.
- `engine/mtf_upturn.py:45-47` 3D leg reuses `signal_quality.signal_frame` verbatim; RSI from `engine.technicals`.

## 2. Session clock — `engine/session_anchor.py`

| symbol | file:line | what the code says |
|---|---|---|
| `US_EPOCH` | `engine/session_anchor.py:69` | `date(1950, 1, 3)` |
| `US_FORWARD_DAYS` | `engine/session_anchor.py:73` | `400` |
| `MARKET_SUFFIX` | `engine/session_anchor.py:54` | `{".SS":"CN", ".SZ":"CN", ".HK":"HK", ".TO":"CA", ".V":"CA"}` |
| `market_for_ticker` | `engine/session_anchor.py:79-94` | Suffix → market key. Unknown/None/empty → `"US"`. Unmapped suffix → `"US"`. |
| `reference_sessions` | `engine/session_anchor.py:136-148` | Fixed ascending session index. US: `_us_reference()` = `nyse_calendar.sessions_between(US_EPOCH, date.today()+timedelta(days=US_FORWARD_DAYS))` (`:112-116`). CN/HK/CA: index store, raises if missing (`:119-133`). Cached per process. |
| `session_positions` | `engine/session_anchor.py:164-202` | `position(d) = R.searchsorted(d, side="left")`. Beyond end: `len(R) + dense_rank`. Before start: negative dense rank. |

Bucketing law stated in the module docstring (`engine/session_anchor.py:15-17`): `bucket(d) = position(d) // n`.

## 3. n-day bar builder — `engine/bar_derive.py`

| symbol | file:line | what the code says |
|---|---|---|
| `ANCHOR_ERA` | `engine/bar_derive.py:62` | `"display-grid-abs-session-2026-08-06"` |
| `_OHLCV_AGG` | `engine/bar_derive.py:181` | `{"open":"first","high":"max","low":"min","close":"last","volume":"sum"}` |
| `_anchored_ohlcv` | `engine/bar_derive.py:243-287` | `b = session_anchor.session_positions(idx, market) // n`; `groupby(b).agg(agg)`; labels = bucket's **first session carrying a finite close**; `dropna(subset=['close'])` only — **does not drop a trailing incomplete bucket**. |
| `derive_2d_ohlcv` | `engine/bar_derive.py:289-297` | `_anchored_ohlcv(daily_df, 2, market)` |
| `derive_3d_ohlcv` | `engine/bar_derive.py:300-314` | `_anchored_ohlcv(daily_df, 3, market)` |
| `bucket_ids` | `engine/bar_derive.py:323-329` | `session_positions(idx, market) // n` |
| `trim_rows_to_bucket_open` | `engine/bar_derive.py:332-356` | DG-R4: how many leading rows to drop so the window opens on a bucket boundary. `prev_date is None` → 0. |
| `chart_anchor` | `engine/bar_derive.py:359-371` | `{"era": ANCHOR_ERA, "b3": [0] + row indices where bucket id changes}` |

`signal_quality._tf_grid` (`engine/signal_quality.py:109-156`) uses the same `session_positions // n`, labels by OPEN date (`:122-127`), close = last finite close.

`confluence_tiers._tf_bars` (`engine/confluence_tiers.py:283-313`) uses the same `session_positions // n` but indexes the TF close by the bucket's **last SESSION date** (`:295-313`).

## 4. Production signal grain vs confirmation grain

**Signal (master / §7 / T1):** 3D.

- `engine/signal_quality.py:14-16`: "Faithful to the owner's `MACD STOCH RSI CONFLUENCE SIGNAL.pine`, run on the 3D: RSI-MACD : macd = EMA(RSI14,14) - EMA(RSI14,60); signal = EMA(macd,5)".
- `engine/signal_quality.py:176-184`: `grid3 = _tf_grid(daily_close, 3, market)`; MACD/StochRSI/RSI on `s3`.
- `engine/confluence_tiers.py:13`: `T1 0.90 3D MACD-RSI x 3D StochRSI, buy-filter endorsed (master)`.
- `engine/canon.py:452`: oracle `resample_sessions(daily_close, 3)`.

**Signal (T2/T3/T4 legs):** 2D RSI-MACD, with 3D StochRSI (T2/T3) or 2D StochRSI (T4).

- `engine/confluence_tiers.py:13-16` (quoted): T1 `3D MACD-RSI x 3D StochRSI`; T2 `2D MACD-RSI cross & 3D StochRSI crossed`; T3 `2D MACD-RSI PROJECTED<=1-2d & 3D StochRSI already crossed`; T4 `2D MACD-RSI PROJECTED & 2D StochRSI` — computed at `:441-457`.
- Buyable set is **not** the setups.py:243 docstring "FRESH MACD-2D x StochRSI-3D". Live buyable = T1 or T2 or T3 (`engine/signal_gate.py:110` `BUYABLE_TIERS = ("T1","T2","T3")`; `:113-120` `is_buyable`). T1 = 3D × 3D; T2 and T3 = 2D-projected × 3D. T4 is excluded (`engine/signal_gate.py:108-109`).

**Confirmation:**

- Weekly `W-FRI` RSI-MACD, prior closed week: `engine/signal_quality.py:185-187,192` `wbull = (wm >= wsg).shift(1)...`; CB uses `(wbull | b1os)` at `:192`.
- Same weekly arm in the canon oracle: `engine/canon.py:466-469,476`.
- 3D StochRSI from-oversold (`d.rolling(CONF_W).min() < OS`) is the other confirm OR-arm (`engine/signal_quality.py:191-192`; `engine/canon.py:471,476`).
- HTF super-tiers: `engine/confluence_tiers.py:988-1014` `S1 = 2W confluence-active AND 3D confluence-active AND not_topped (3D)`; `S2 = 3D AND 1W AND 2W MACD pending AND not_topped (3D)`.
- 2D histogram rising is **display-only**, never a buy quality: `engine/signal_quality.py:197-204`.

Canon oracle also emits monthly `ME` and `2W-FRI` bull flags (`engine/canon.py:489-494`) as columns, not as the CB confirm gate.

## 5. Rank families (`rank_by`)

| family | defined/assigned | conditions_on (as the cited lines state) |
|---|---|---|
| `us_prophet_v3` | `engine/us_board_rank.py:100` `BOARD_DEFINITION = "us_prophet_v3"`; adopted `engine/us_board_rank.py:119` `"2026-08-15"`; stamped onto the artifact as `rank_by` at `scripts/build_stock_library.py:5445` `wide = {..., "rank_by": us_board_rank.BOARD_DEFINITION, ...}` then re-stamped from scored rows via `published_definition` (`engine/us_board_rank.py:1289-1314`). | Same selection population as v2; ranker is C1 evidence-family fusion (`engine.us_prophet_fusion`) inside each stage bucket (`engine/us_board_rank.py:104-110`). |
| `us_prophet_v2` | `engine/us_board_rank.py:148` in `SUPERSEDED_ERA_STAMPS`; live 2026-08-10 → 2026-08-15. Shadow `SHADOW_DEFINITION = "us_prophet_v2_shadow"` at `:128`. Fallback `FALLBACK_DEFINITION = "us_prophet_v2_fallback"` at `:136`. Pre-override arithmetic: `legacy_v2_values` docstring at `:1115`. | Five-leg weighted heuristic on the confluence-admitted pool; displaced by v3 as ranker, not as gate. |
| `us_prophet_v1` | `engine/us_board_rank.py:147` in `SUPERSEDED_ERA_STAMPS`; live 2026-08-02 → 2026-08-10. | Displaced by v2 (reclaim-waiver admission change, `:92-99`). |
| `conviction` | **not assigned at HEAD as a board `rank_by`**. `engine/setups.py:141` is docstring prose about a sort key (`entry_open_first`), not a `rank_by=` assignment. Live stamp is `BOARD_DEFINITION = "us_prophet_v3"` (`engine/us_board_rank.py:100`) written at `scripts/build_stock_library.py:5445` `wide = {..., "rank_by": us_board_rank.BOARD_DEFINITION, ...}`. Legacy ledger stratum: `scripts/prophet_fusion_race.py:2228-2230` quote: `"rank_by is a SELECTION-REGIME stamp (legacy eras: conviction -> bottoming-alignment -> confluence; live boards stamp us_prophet_v1/v2 from 2026-08-07)"`. `scripts/stock_conviction_phase0.py:36` says a `rank_by='conviction'` switch is "intentionally NOT automatic". retro_grades `rank_by='conviction'` as_of months: **2026-06 only** (data-derived). | Legacy selection-regime stamp; not the live ranker. |
| `confluence` | **not assigned at HEAD as a board `rank_by`**. `engine/setups.py:243` is docstring prose about a buy_gate, not a `rank_by=` assignment. Same fusion-race quote `scripts/prophet_fusion_race.py:2228-2230`. (`scripts/prophet_fusion_arena.py:1138` writes `rank_by: "confluence"` on **synthetic** race rows, not the live board.) retro_grades `rank_by='confluence'` as_of months: **2026-07 only** (data-derived). | Legacy selection-regime stamp; T1=3D×3D, T2/T3=2D-projected×3D (`engine/confluence_tiers.py:13-16`). |
| `bottoming-alignment` | **not assigned at HEAD as a board `rank_by`**. `engine/setups.py:259` is docstring prose about `align_map`, not a `rank_by=` assignment. Same fusion-race quote `scripts/prophet_fusion_race.py:2228-2230`. retro_grades `rank_by='bottoming-alignment'` as_of months: **2026-06 and 2026-07** (data-derived). | Legacy selection-regime stamp; weekly + 3-day + daily alignment gate, not the v3 fusion ranker. |

`engine/prophet_bridge.py:29-31`: live origination sorts by `row["prophet"]["score"]` — "the canonical ranker of whatever definition the artifact carries; C1 evidence-family fusion since `us_prophet_v3`, 2026-08-15".

## 6. Lanes (`buy`, `laggards`, `watch`, `leaders`, `ran`)

Artifact keys assembled at `scripts/build_stock_library.py:5445-5455` and `ran` at `:5879`.

| lane | file:line | what the code says |
|---|---|---|
| `buy` | `scripts/build_stock_library.py:5447` `"buy": _all_buy_rows` (`_trend_rows_ordered + _recovery_rows_ordered`, `:5430`). Origination reads **buy[] ONLY**: `engine/prophet_bridge.py:1202-1204`. `engine/setups.py:236-237` splits scored candidates into constructive `buy` shortlist. Membership lanes tuple: `engine/prophet_board_since.py:273` `US_MEMBERSHIP_LANES = ("buy", "watch", "leaders", "laggards", "ran")`. | Confluence-admitted / gated names on the published board. |
| `watch` | `scripts/build_stock_library.py:5432-5451` P2.4: watch rows must carry `lane="watch"`; `"watch": [_tag_watch(t) for t, _ in watch[:48]]`. `engine/us_candidate_lanes.py:177-178` pending-expired rows re-tagged `lane="watch"` inside `buy[]`. Weight-table row `_ENTRY_VALUE["watch"] = 0.4` at `engine/us_board_rank.py:409` (not `ENTRY_STATUS_VALUES`; that name does not exist). Featured statuses `_FEATURED_ENTRY_STATUSES` at `:463-465` do **not** include `"watch"`. | Overflow / pending-expired / watch-status names. Slice 48. |
| `leaders` | `scripts/build_stock_library.py:5452-5454` "Leaders strip — a SEPARATE display lane (`lane='leader'`); never mixed into buy[], and prophet_bridge does not originate plans from it." Selector `scripts/build_stock_library.py:1540-1578`: ranked by trailing 3-month TOTAL return z (`LEADERS_MOMENTUM_SESSIONS = 63` at `engine/us_board_rank.py:1954`); admission `above200 AND weekly_bull` (`scripts/build_stock_library.py:1588`). `engine/prophet_bridge.py:1202-1203` "standouts['leaders'] (2026-07-28 leaders strip) is deliberately excluded: those rows have no fresh entry signal". | Display leadership; 1D total-return z + weekly/200d structure, not the cascade ranker. |
| `laggards` | `scripts/build_stock_library.py:5455` `"laggards": [row_by_t[t] for t, _ in scored[-12:][::-1]] if len(scored) > 24 else []`. `engine/setups.py:236-237,290-293` `laggards` watch = worst `alpha <= lag_max`, n_lag. `engine/prophet_miss_audit.py:186-187` laggards "deliberately absent" from basket-miss lanes ("these are the weak ones" shelf). | Lowest-alpha tail of the scored universe. |
| `ran` | Stage constant `engine/us_board_rank.py:420` `STAGE_RAN = "ran"`. Row builder `engine/us_board_rank.py:2613-2626` `"stage": STAGE_RAN, "lane": "ran"`. Attached `scripts/build_stock_library.py:5879` `wide["ran"] = us_board_rank.build_ran_rows(...)`. Caps `RAN_CAP = 12` at `engine/us_board_rank.py:153`. | Names that already ran (don't chase); ticks window `RAN_TICKS_MIN/MAX` `:154-155`. |

`engine/us_candidate_lanes.py:112-126` is a **different** four-lane display partition (`featured` / `more_actionable` / `late_or_unfillable` / `forming`) of the eligible pool; it "changes no `buy[]` membership" (`:22-24`).

`engine/stock_desk.py:163-184` `gather_top_picks` reads `us_standouts.json` `buy[:n]` and echoes `rank_by`.
