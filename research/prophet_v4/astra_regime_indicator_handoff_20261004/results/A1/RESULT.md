# A1 RESULT — baseline and clock truth census

Price stores on this checkout are FINAL-VINTAGE (as observed today, not point-in-time) and the universes are SURVIVOR-SELECTED (current membership only). Independent Pine RSI-MACD reproduces engine.canon.rsi_macd on SPY after the first 400 sessions (max|diff| macd=8.52651e-14, signal=7.86038e-14; bullish crosses 415 vs 415, cross-date mismatches=0). Production 3-session bars match manual pos//3 OHLCV exactly on open-date labels (mismatches=0) and disagree under the spec's last-session date label (ticker A: bars3d_canon=1069, bars3d_manual=1069, bars3d_mismatches=1069; closes identical, dates open vs last). Canon parity is not served parity: served (technicals.rsi + ewm adjust=True) vs canon.rsi_macd on SPY daily after session 400 max|macd|=3.2116e-05 (first-400 max|macd|=0.593189, full max|macd|=0.593189, cross-date mismatches full=0); SPY 3D _tf_grid after 400 bars max|macd|=3.37155e-05 (full max|macd|=1.07589, cross-date mismatches full=2).

## ANSWER FIRST

Independent Pine RSI-MACD reproduces engine.canon.rsi_macd on SPY after the first 400 sessions (max|diff| macd=8.52651e-14, signal=7.86038e-14; bullish crosses 415 vs 415, cross-date mismatches=0). Production 3-session bars match manual pos//3 OHLCV exactly on open-date labels (mismatches=0) and disagree under the spec's last-session date label (ticker A: bars3d_canon=1069, bars3d_manual=1069, bars3d_mismatches=1069; closes identical, dates open vs last). Canon parity is not served parity: served (technicals.rsi + ewm adjust=True) vs canon.rsi_macd on SPY daily after session 400 max|macd|=3.2116e-05 (first-400 max|macd|=0.593189, full max|macd|=0.593189, cross-date mismatches full=0); SPY 3D _tf_grid after 400 bars max|macd|=3.37155e-05 (full max|macd|=1.07589, cross-date mismatches full=2).

repo_head=`ca2e4abd4daa1e909bacdd9840310d59af4083a1`  tests=`4 passed, 1 xfailed in 0.86s`  status=`DELIVERED`

## 1. Served definition (receipts in served_definition.md)

Signal grains: **3D** (master T1 / `signal_quality.signal_frame`) and **2D** (T2/T3). Confirmation grains: **W-FRI** and **2W-FRI**. Live board ranker: `BOARD_DEFINITION = us_prophet_v3` (`engine/us_board_rank.py:100`). Served call path: `scripts/build_stock_library.py:234,:3745` → `engine/signal_gate.py:65-67,:379,:468` → `confluence_tiers.cascade` / `signal_quality._rsi_macd`. Buyable = T1 or T2 or T3 (`engine/signal_gate.py:110,:113-120`); T1 = 3D × 3D, T2/T3 = 2D-projected × 3D. Live board does **not** call `engine.canon.rsi_macd`.

| family | file | line | conditions_on |
| --- | --- | --- | --- |
| us_prophet_v1 | engine/us_board_rank.py | 147 | SUPERSEDED_ERA_STAMPS; live 2026-08-02→2026-08-10; displaced by us_prophet_v2. Same confluence admission population as later stamps; ranker was the five-leg heuristic (see us_prophet_v2). |
| us_prophet_v2 | engine/us_board_rank.py | 148 | SUPERSEDED_ERA_STAMPS; live 2026-08-10→2026-08-15; five-leg weighted heuristic ranker on the confluence-admitted pool (2D/3D RSI-MACD × StochRSI cascade). SHADOW_DEFINITION us_prophet_v2_shadow at line 128; FALLBACK_DEFINITION us_prophet_v2_fallback at line 136. |
| us_prophet_v3 | engine/us_board_rank.py | 100 | BOARD_DEFINITION live ranker; same selection population as v2; orders the pool by C1 evidence-family fusion (engine.us_prophet_fusion) inside each stage bucket. Adopted 2026-08-15 (line 119). |
| conviction | scripts/prophet_fusion_race.py | 2228 | not assigned at HEAD; legacy ledger stratum. scripts/prophet_fusion_race.py:2228-2230 quote: 'rank_by is a SELECTION-REGIME stamp (legacy eras: conviction -> bottoming-alignment -> confluence; live boards stamp us_prophet_v1/v2 from 2026-08-07)'. engine/setups.py:141 is docstring sort-key prose, not a rank_by assignment. retro_grades as_of months: ['2026-06']. |
| confluence | scripts/prophet_fusion_race.py | 2228 | not assigned at HEAD; legacy ledger stratum. scripts/prophet_fusion_race.py:2228-2230 (same quote). engine/setups.py:243 is docstring buy_gate prose, not a rank_by assignment. retro_grades as_of months: ['2026-07']. |
| bottoming-alignment | scripts/prophet_fusion_race.py | 2228 | not assigned at HEAD; legacy ledger stratum. scripts/prophet_fusion_race.py:2228-2230 (same quote). engine/setups.py:259 is docstring align_map prose, not a rank_by assignment. retro_grades as_of months: ['2026-06', '2026-07']. |

## 2. Parity (schema keys)

| key | value |
| --- | --- |
| max_abs_diff_macd | 8.526512829121202e-14 |
| max_abs_diff_signal | 7.860379014346108e-14 |
| cross_count_canon | 415 |
| cross_count_pine | 415 |
| cross_date_mismatches | 0 |
| bars3d_canon | 1069 |
| bars3d_manual | 1069 |
| bars3d_mismatches | 1069 |
| bars2d_canon | 1604 |
| bars2d_manual | 1604 |
| bars2d_mismatches | 1603 |

### Served vs canon

| grain | max|macd| after400 | max|macd| full | max|sig| after400 | max|sig| full | xmis after400 | xmis full |
| --- | --- | --- | --- | --- | --- | --- |
| SPY daily | 3.21159730347631e-05 | 0.5931894460276439 | 3.167919552460319e-05 | 0.5644622446347958 | 0 | 0 |
| SPY 3D _tf_grid | 3.3715458975791535e-05 | 1.0758870114828554 | 3.7733401444972614e-05 | 0.9335089972416633 | 0 | 2 |

Full write-up: `parity.md`. Ledgers: `ledger_denominators.md`. Code receipts: `served_definition.md`. Git eras: `era_map.md`. Inventory: `data_inventory.json`.

## 3. Ledgers (honest-N)

| item | N |
| --- | --- |
| prophet ledger rows | 302 |
| prophet distinct names | 282 |
| retro_grades rows | 13563 |
| retro distinct as_of | 48 |
| retro as_of first | 2026-06-15 |
| retro as_of last | 2026-09-17 |
| retro distinct tickers | 1130 |

Prophet month × outcome (ALL row): T1_HIT=44, T2_HIT=3, INVALIDATED=72, EXPIRED=125, CLOSED_EARLY=0, other=58

share_ret_nonnull = 1.0000 in every cell is structural: retro_grades.parquet holds graded rows only (every row has a non-null ret). It is not a coverage statistic over the published board.

retro_grades rank_by as_of months: bottoming-alignment=['2026-06', '2026-07'], confluence=['2026-07'], conviction=['2026-06'], us_prophet_v1=['2026-08'], us_prophet_v2=['2026-08'], us_prophet_v3=['2026-08', '2026-09']

## Tests

`4 passed, 1 xfailed in 0.86s`

```
...x.                                                                    [100%]
4 passed, 1 xfailed in 0.86s

```

## Deviations

- Workspace is this git checkout (astra-ceo-handoff worktree), not ~/lanes/repos/macro (that path does not exist on this host).
- Pine RMA is ta.sma of the first n finite values then (src+(n-1)*prev)/n; interior NaN after seed is left NaN (Pine na) rather than canon.rma's prev-carry.
- Bar-parity scalars in parity.json are for the first fallback OHLCV ticker when SPY yahoo has no open/high/low and data/baskets/ohlcv/SPY.parquet is absent; per_ticker lists the first ten alphabetical basket names.
- pytest (ii) asserts production open-date labels equal manual pos//n OHLCV on all ten per_ticker names; the spec last-session date recipe is an additional xfail(strict=True) on ticker A.
- Served-vs-canon uses engine.signal_quality._rsi_macd / _tf_grid (the T1 master path), not a re-typed copy.

## Gaps

- This checkout is a shallow git repository (git rev-parse --is-shallow-repository=true) with missing objects; path-filtered `git log` on engine/canon.py, session_anchor.py, bar_derive.py, mtf_upturn.py, us_board_rank.py returns only 69268b06502c (2026-08-23, files added). Pre-squash constant/epoch/rank-family history is not readable here.
- 3D (date, close) last-session labeling mismatches=1069 (open-label mismatches=0); production labels by open date.
- engine.canon.rsi_macd is not the served indicator (no gate-path import). Served-vs-canon numbers are in parity.json served_vs_canon; later lanes that treat canon as the live cascade are reading a different RSI/EMA than production.
