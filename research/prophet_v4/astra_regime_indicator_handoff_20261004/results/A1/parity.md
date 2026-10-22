# Indicator and bar-clock parity (A1)

Price stores are FINAL-VINTAGE (as observed today, not point-in-time). Universes are SURVIVOR-SELECTED (current membership only).

## (a) RSI-MACD on SPY daily `close` (data/yahoo/SPY.parquet)

Sessions=8477 (1993-01-29 → 2026-10-02). Compared after first 400 sessions. n_compared macd=8077 signal=8077.

| metric | value |
| --- | --- |
| max|diff| macd | 8.526512829121202e-14 |
| max|diff| macd date | 2006-11-16 |
| max|diff| signal | 7.860379014346108e-14 |
| max|diff| signal date | 2006-11-20 |
| agree to 1e-6 | True |
| bullish crosses canon (post-400, both finite) | 415 |
| bullish crosses pine (post-400, both finite) | 415 |
| cross-date mismatches (symmetric difference) | 0 |
| crosses canon full series | 435 |
| crosses pine full series | 439 |

Cross dates only in canon: (none)

Cross dates only in pine: (none)

### Why any |diff| > 1e-6 (read, not a canon fix)

engine.canon.ema is pandas ewm(span, adjust=False, min_periods=span) (engine/canon.py:343-350), so the first `span` RSI bars of each EMA are NaN in the output even though the recursive state is running. Pine EMA here seeds with the first finite value and emits from that bar (no min_periods). engine.canon.rma SMA-seeds on the first n finite values then recurses with alpha=1/n and carries the previous value through a NaN (engine/canon.py:311-340); the Pine RMA in code/pine_rsi_macd.py matches that seed. engine.canon.rsi is RMA(gain)/RMA(loss) with those RMAs (engine/canon.py:353-362). A residual after session 400, if any, is therefore EMA min_periods / seed-bar disagreement decaying as (1-alpha)^t, not a different RSI formula. Pine RMA (code/pine_rsi_macd.py) is ta.sma of the first n finite values then (src+(n-1)*prev)/n — not a transcription of engine.canon.rma's loop. Production board code does NOT call engine.canon.rsi_macd: scripts/build_stock_library.py:234,3745 -> engine/signal_gate.py:65-67,379,468 -> engine/signal_quality.py:68-75 and engine/confluence_tiers.py:255-262 use engine.technicals.rsi (ewm alpha=1/n, min_periods=n; engine/technicals.py:26-31) and pandas ewm default adjust=True.

## (a2) Served vs canon RSI-MACD (canon parity is not served parity)

Served path is engine.technicals.rsi (ewm alpha=1/n, min_periods=n, adjust=True default; engine/technicals.py:26-31) plus pandas ewm(span, min_periods=span) default adjust=True (engine/signal_quality.py:68-75; engine/confluence_tiers.py:255-262). 3D grid is engine.signal_quality._tf_grid (engine/signal_quality.py:109-156, called at :176-184). No module on the gate path imports engine.canon.

### SPY daily (data/yahoo/SPY.parquet `close`)

| metric | value |
| --- | --- |
| n sessions | 8477 |
| max|macd| after 400 | 3.21159730347631e-05 |
| max|signal| after 400 | 3.167919552460319e-05 |
| max|macd| first 400 | 0.5931894460276439 |
| max|macd| full series | 0.5931894460276439 |
| max|signal| full series | 0.5644622446347958 |
| cross_count canon full | 435 |
| cross_count served full | 435 |
| cross-date mismatches full | 0 |
| cross-date mismatches after 400 | 0 |

### SPY 3D `_tf_grid` (T1 master grain, engine/signal_quality.py:176-184)

| metric | value |
| --- | --- |
| n 3D bars | 2828 |
| max|macd| after 400 | 3.3715458975791535e-05 |
| max|signal| after 400 | 3.7733401444972614e-05 |
| max|macd| first 400 | 1.0758870114828554 |
| max|macd| full series | 1.0758870114828554 |
| max|signal| full series | 0.9335089972416633 |
| cross_count canon full | 142 |
| cross_count served full | 142 |
| cross-date mismatches full | 2 |
| cross-date mismatches after 400 | 0 |

### Ten per_ticker basket names on 3D `_tf_grid`

| ticker | daily_n | 3d_n | max|macd| after400 | max|macd| full | max|sig| after400 | max|sig| full | xmis after400 | xmis full |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 3207 | 1069 | 1.2386290478616502e-05 | 1.083166442699806 | 1.2025975887119955e-05 | 1.2104857579481574 | 0 | 0 |
| AADX | 85 | 29 |  |  |  |  |  | 0 |
| AAL | 3207 | 1069 | 0.00013335247476931045 | 5.546484234167025 | 0.0001424759025442368 | 5.417136587664319 | 0 | 1 |
| AAMI | 3013 | 1005 | 9.918832985533754e-05 | 3.885357504989855 | 0.00010541828302290668 | 3.77431295411648 | 0 | 2 |
| AAOI | 3207 | 1069 | 9.01375595745435e-05 | 4.912685795073607 | 9.390692808963763e-05 | 4.619130624709332 | 0 | 0 |
| AAP | 3207 | 1069 | 2.5446850628441098e-05 | 2.236705727423839 | 2.8411328832689264e-05 | 2.0407386833805257 | 0 | 0 |
| AAPL | 3207 | 1069 | 5.860023924952884e-05 | 3.279781016395134 | 6.250484666026068e-05 | 2.939487216476104 | 0 | 5 |
| AARD | 411 | 137 |  | 6.032256731316146 |  | 5.551221113324129 |  | 2 |
| AAT | 3207 | 1069 | 1.0025214727704679e-05 | 0.7077415757315748 | 9.31732728082224e-06 | 0.6888869240575772 | 0 | 2 |
| ABAT | 2668 | 890 | 8.796373456476658e-05 | 5.9621362390643995 | 9.552545799262901e-05 | 5.841156337270839 | 0 | 6 |

## (b) n-session bars

SPY yahoo columns: `['close_price', 'close', 'volume']`. Bar source: **data/baskets/ohlcv first 10 names alphabetically (no SPY OHLCV)**. Tickers: ['A', 'AADX', 'AAL', 'AAMI', 'AAOI', 'AAP', 'AAPL', 'AARD', 'AAT', 'ABAT'].

`derive_3d_ohlcv` / `derive_2d_ohlcv` do **not** drop a trailing incomplete bucket (engine/bar_derive.py:243-287: only `dropna(subset=['close'])`). Production date label = open (first finite-close session); engine/bar_derive.py:270-285. Spec manual date = last session date (A1 spec).

Primary ticker (first in the fallback list / SPY if used):

| grain | bars_canon | bars_manual_last_date | (date,close) mismatches last-date | mismatches open-label |
| --- | --- | --- | --- | --- |
| 3D | 1069 | 1069 | 1069 | 0 |
| 2D | 1604 | 1604 | 1603 | 0 |

First three 3D (date, close) mismatches under spec last-date labeling:

```json
[
  {
    "i": 0,
    "canon_date": "2014-01-02",
    "canon_close": 36.510986328125,
    "manual_date": "2014-01-06",
    "manual_close": 36.510986328125
  },
  {
    "i": 1,
    "canon_date": "2014-01-07",
    "canon_close": 37.65196228027344,
    "manual_date": "2014-01-09",
    "manual_close": 37.65196228027344
  },
  {
    "i": 2,
    "canon_date": "2014-01-10",
    "canon_close": 38.59954071044922,
    "manual_date": "2014-01-14",
    "manual_close": 38.59954071044922
  }
]
```

First three 2D (date, close) mismatches under spec last-date labeling:

```json
[
  {
    "i": 0,
    "canon_date": "2014-01-02",
    "canon_close": 36.69148254394531,
    "manual_date": "2014-01-03",
    "manual_close": 36.69148254394531
  },
  {
    "i": 1,
    "canon_date": "2014-01-06",
    "canon_close": 37.03312301635742,
    "manual_date": "2014-01-07",
    "manual_close": 37.03312301635742
  },
  {
    "i": 2,
    "canon_date": "2014-01-08",
    "canon_close": 37.65196228027344,
    "manual_date": "2014-01-09",
    "manual_close": 37.65196228027344
  }
]
```

### Per-ticker

| ticker | daily_rows | 3d_canon | 3d_manual_last | 3d_mis_last | 3d_mis_open | 2d_canon | 2d_manual_last | 2d_mis_last | 2d_mis_open |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 3207 | 1069 | 1069 | 1069 | 0 | 1604 | 1604 | 1603 | 0 |
| AADX | 85 | 29 | 29 | 28 | 0 | 43 | 43 | 42 | 0 |
| AAL | 3207 | 1069 | 1069 | 1069 | 0 | 1604 | 1604 | 1603 | 0 |
| AAMI | 3013 | 1005 | 1005 | 1004 | 0 | 1507 | 1507 | 1506 | 0 |
| AAOI | 3207 | 1069 | 1069 | 1069 | 0 | 1604 | 1604 | 1603 | 0 |
| AAP | 3207 | 1069 | 1069 | 1069 | 0 | 1604 | 1604 | 1603 | 0 |
| AAPL | 3207 | 1069 | 1069 | 1069 | 0 | 1604 | 1604 | 1603 | 0 |
| AARD | 411 | 137 | 137 | 137 | 0 | 206 | 206 | 205 | 0 |
| AAT | 3207 | 1069 | 1069 | 1069 | 0 | 1604 | 1604 | 1603 | 0 |
| ABAT | 2668 | 890 | 890 | 889 | 0 | 1335 | 1335 | 1333 | 0 |
