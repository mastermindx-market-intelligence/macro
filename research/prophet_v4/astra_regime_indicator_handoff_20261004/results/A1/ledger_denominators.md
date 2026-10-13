# Ledger denominators (A1)

Price stores are FINAL-VINTAGE (as observed today, not point-in-time). Universes are SURVIVOR-SELECTED (current membership only). Ledgers below are the served artifacts on this checkout.

## (a) data/prophet/ledger.jsonl

Comment lines starting with `#` skipped. Parsed JSONL rows: **302**. Distinct names (asset): **282**. Other raw outcomes: `['NO_ENTRY']` (empty means every row used one of the five named outcomes).

### signal month × outcome counts

| month | n | n_names | T1_HIT | T2_HIT | INVALIDATED | EXPIRED | CLOSED_EARLY | other |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-02 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| 2026-03 | 2 | 2 | 0 | 0 | 0 | 2 | 0 | 0 |
| 2026-04 | 3 | 3 | 1 | 0 | 0 | 1 | 0 | 1 |
| 2026-05 | 5 | 4 | 2 | 0 | 0 | 3 | 0 | 0 |
| 2026-06 | 35 | 33 | 5 | 1 | 9 | 14 | 0 | 6 |
| 2026-07 | 87 | 79 | 10 | 1 | 15 | 47 | 0 | 14 |
| 2026-08 | 154 | 154 | 22 | 1 | 38 | 56 | 0 | 37 |
| 2026-09 | 14 | 14 | 4 | 0 | 10 | 0 | 0 | 0 |
| unknown | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| ALL | 302 | 282 | 44 | 3 | 72 | 125 | 0 | 58 |

### mean/median stock_result_pct and days_held by outcome

| outcome | n | n_names | mean_stock_result_pct | median_stock_result_pct | n_pct | mean_days_held | median_days_held | n_days |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| T1_HIT | 44 | 42 | 16.7818 | 13.9167 | 44 | 19.0227 | 16 | 44 |
| T2_HIT | 3 | 3 | 71.6744 | 13.0271 | 3 | 7.66667 | 8 | 3 |
| INVALIDATED | 72 | 68 | -10.1526 | -7.97095 | 72 | 20 | 19 | 72 |
| EXPIRED | 125 | 117 | -0.581209 | -2.2703 | 125 | 45.408 | 45 | 125 |
| CLOSED_EARLY | 0 | 0 |  |  | 0 |  |  | 0 |
| other | 58 | 58 |  |  | 0 | 45.431 | 45 | 58 |

## (b) data/us_board_ledger/retro_grades.parquet

rows=13563; distinct as_of dates: count=48, first=2026-06-15, last=2026-09-17; distinct tickers=1130. rank_by=['bottoming-alignment', 'confluence', 'conviction', 'us_prophet_v1', 'us_prophet_v2', 'us_prophet_v3']; lane=['buy', 'laggards', 'leaders', 'ran', 'watch']; horizon=[5, 10, 21]. rank_by as_of months: {'bottoming-alignment': ['2026-06', '2026-07'], 'confluence': ['2026-07'], 'conviction': ['2026-06'], 'us_prophet_v1': ['2026-08'], 'us_prophet_v2': ['2026-08'], 'us_prophet_v3': ['2026-08', '2026-09']}.

share_ret_nonnull = 1.0000 in every cell is structural: retro_grades.parquet holds graded rows only (every row has a non-null ret). It is not a coverage statistic over the published board.

Distinct as_of dates: 2026-06-15, 2026-06-16, 2026-06-17, 2026-06-18, 2026-06-22, 2026-06-23, 2026-06-24, 2026-06-30, 2026-07-01, 2026-07-02, 2026-07-06, 2026-07-09, 2026-07-10, 2026-07-14, 2026-07-15, 2026-07-17, 2026-07-20, 2026-07-21, 2026-07-24, 2026-07-27, 2026-07-28, 2026-07-29, 2026-07-30, 2026-07-31, 2026-08-07, 2026-08-12, 2026-08-13, 2026-08-14, 2026-08-17, 2026-08-18, 2026-08-19, 2026-08-20, 2026-08-21, 2026-08-24, 2026-08-25, 2026-08-26, 2026-08-27, 2026-08-28, 2026-08-31, 2026-09-03, 2026-09-04, 2026-09-08, 2026-09-09, 2026-09-10, 2026-09-11, 2026-09-14, 2026-09-16, 2026-09-17

### as_of month × rank_by × lane × horizon

| as_of_month | rank_by | lane | horizon | n | n_ret_nonnull | share_ret_nonnull | n_tickers |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-06 | bottoming-alignment | buy | 5 | 208 | 208 | 1.0000 | 173 |
| 2026-06 | bottoming-alignment | buy | 10 | 34 | 34 | 1.0000 | 34 |
| 2026-06 | bottoming-alignment | buy | 21 | 34 | 34 | 1.0000 | 34 |
| 2026-06 | bottoming-alignment | laggards | 5 | 32 | 32 | 1.0000 | 17 |
| 2026-06 | bottoming-alignment | laggards | 10 | 12 | 12 | 1.0000 | 12 |
| 2026-06 | bottoming-alignment | laggards | 21 | 12 | 12 | 1.0000 | 12 |
| 2026-06 | bottoming-alignment | watch | 5 | 59 | 59 | 1.0000 | 30 |
| 2026-06 | bottoming-alignment | watch | 10 | 24 | 24 | 1.0000 | 24 |
| 2026-06 | bottoming-alignment | watch | 21 | 24 | 24 | 1.0000 | 24 |
| 2026-06 | conviction | buy | 5 | 437 | 437 | 1.0000 | 208 |
| 2026-06 | conviction | buy | 10 | 177 | 177 | 1.0000 | 102 |
| 2026-06 | conviction | laggards | 5 | 43 | 43 | 1.0000 | 25 |
| 2026-06 | conviction | laggards | 10 | 15 | 15 | 1.0000 | 11 |
| 2026-06 | conviction | watch | 5 | 49 | 49 | 1.0000 | 35 |
| 2026-07 | bottoming-alignment | buy | 5 | 193 | 193 | 1.0000 | 137 |
| 2026-07 | bottoming-alignment | buy | 10 | 193 | 193 | 1.0000 | 137 |
| 2026-07 | bottoming-alignment | buy | 21 | 193 | 193 | 1.0000 | 137 |
| 2026-07 | bottoming-alignment | laggards | 5 | 84 | 84 | 1.0000 | 22 |
| 2026-07 | bottoming-alignment | laggards | 10 | 84 | 84 | 1.0000 | 22 |
| 2026-07 | bottoming-alignment | laggards | 21 | 84 | 84 | 1.0000 | 22 |
| 2026-07 | bottoming-alignment | watch | 5 | 168 | 168 | 1.0000 | 53 |
| 2026-07 | bottoming-alignment | watch | 10 | 168 | 168 | 1.0000 | 53 |
| 2026-07 | bottoming-alignment | watch | 21 | 168 | 168 | 1.0000 | 53 |
| 2026-07 | confluence | buy | 5 | 523 | 523 | 1.0000 | 252 |
| 2026-07 | confluence | buy | 10 | 523 | 523 | 1.0000 | 252 |
| 2026-07 | confluence | buy | 21 | 522 | 522 | 1.0000 | 251 |
| 2026-07 | confluence | laggards | 5 | 103 | 103 | 1.0000 | 32 |
| 2026-07 | confluence | laggards | 10 | 103 | 103 | 1.0000 | 32 |
| 2026-07 | confluence | laggards | 21 | 103 | 103 | 1.0000 | 32 |
| 2026-07 | confluence | leaders | 5 | 60 | 60 | 1.0000 | 21 |
| 2026-07 | confluence | leaders | 10 | 60 | 60 | 1.0000 | 21 |
| 2026-07 | confluence | leaders | 21 | 60 | 60 | 1.0000 | 21 |
| 2026-07 | confluence | watch | 5 | 312 | 312 | 1.0000 | 142 |
| 2026-07 | confluence | watch | 10 | 312 | 312 | 1.0000 | 142 |
| 2026-07 | confluence | watch | 21 | 312 | 312 | 1.0000 | 142 |
| 2026-08 | us_prophet_v1 | buy | 5 | 78 | 78 | 1.0000 | 78 |
| 2026-08 | us_prophet_v1 | buy | 10 | 78 | 78 | 1.0000 | 78 |
| 2026-08 | us_prophet_v1 | buy | 21 | 78 | 78 | 1.0000 | 78 |
| 2026-08 | us_prophet_v1 | laggards | 5 | 12 | 12 | 1.0000 | 12 |
| 2026-08 | us_prophet_v1 | laggards | 10 | 12 | 12 | 1.0000 | 12 |
| 2026-08 | us_prophet_v1 | laggards | 21 | 12 | 12 | 1.0000 | 12 |
| 2026-08 | us_prophet_v1 | leaders | 5 | 15 | 15 | 1.0000 | 15 |
| 2026-08 | us_prophet_v1 | leaders | 10 | 15 | 15 | 1.0000 | 15 |
| 2026-08 | us_prophet_v1 | leaders | 21 | 15 | 15 | 1.0000 | 15 |
| 2026-08 | us_prophet_v1 | ran | 5 | 12 | 12 | 1.0000 | 12 |
| 2026-08 | us_prophet_v1 | ran | 10 | 11 | 11 | 1.0000 | 11 |
| 2026-08 | us_prophet_v1 | ran | 21 | 11 | 11 | 1.0000 | 11 |
| 2026-08 | us_prophet_v1 | watch | 5 | 48 | 48 | 1.0000 | 48 |
| 2026-08 | us_prophet_v1 | watch | 10 | 48 | 48 | 1.0000 | 48 |
| 2026-08 | us_prophet_v1 | watch | 21 | 48 | 48 | 1.0000 | 48 |
| 2026-08 | us_prophet_v2 | buy | 5 | 211 | 211 | 1.0000 | 129 |
| 2026-08 | us_prophet_v2 | buy | 10 | 211 | 211 | 1.0000 | 129 |
| 2026-08 | us_prophet_v2 | buy | 21 | 211 | 211 | 1.0000 | 129 |
| 2026-08 | us_prophet_v2 | laggards | 5 | 36 | 36 | 1.0000 | 18 |
| 2026-08 | us_prophet_v2 | laggards | 10 | 36 | 36 | 1.0000 | 18 |
| 2026-08 | us_prophet_v2 | laggards | 21 | 36 | 36 | 1.0000 | 18 |
| 2026-08 | us_prophet_v2 | leaders | 5 | 44 | 44 | 1.0000 | 20 |
| 2026-08 | us_prophet_v2 | leaders | 10 | 44 | 44 | 1.0000 | 20 |
| 2026-08 | us_prophet_v2 | leaders | 21 | 44 | 44 | 1.0000 | 20 |
| 2026-08 | us_prophet_v2 | ran | 5 | 36 | 36 | 1.0000 | 25 |
| 2026-08 | us_prophet_v2 | ran | 10 | 36 | 36 | 1.0000 | 25 |
| 2026-08 | us_prophet_v2 | ran | 21 | 36 | 36 | 1.0000 | 25 |
| 2026-08 | us_prophet_v2 | watch | 5 | 144 | 144 | 1.0000 | 62 |
| 2026-08 | us_prophet_v2 | watch | 10 | 144 | 144 | 1.0000 | 62 |
| 2026-08 | us_prophet_v2 | watch | 21 | 144 | 144 | 1.0000 | 62 |
| 2026-08 | us_prophet_v3 | buy | 5 | 622 | 622 | 1.0000 | 276 |
| 2026-08 | us_prophet_v3 | buy | 10 | 622 | 622 | 1.0000 | 276 |
| 2026-08 | us_prophet_v3 | buy | 21 | 407 | 407 | 1.0000 | 200 |
| 2026-08 | us_prophet_v3 | laggards | 5 | 132 | 132 | 1.0000 | 25 |
| 2026-08 | us_prophet_v3 | laggards | 10 | 132 | 132 | 1.0000 | 25 |
| 2026-08 | us_prophet_v3 | laggards | 21 | 84 | 84 | 1.0000 | 20 |
| 2026-08 | us_prophet_v3 | leaders | 5 | 165 | 165 | 1.0000 | 29 |
| 2026-08 | us_prophet_v3 | leaders | 10 | 165 | 165 | 1.0000 | 29 |
| 2026-08 | us_prophet_v3 | leaders | 21 | 105 | 105 | 1.0000 | 23 |
| 2026-08 | us_prophet_v3 | ran | 5 | 132 | 132 | 1.0000 | 64 |
| 2026-08 | us_prophet_v3 | ran | 10 | 132 | 132 | 1.0000 | 64 |
| 2026-08 | us_prophet_v3 | ran | 21 | 84 | 84 | 1.0000 | 45 |
| 2026-08 | us_prophet_v3 | watch | 5 | 528 | 528 | 1.0000 | 92 |
| 2026-08 | us_prophet_v3 | watch | 10 | 528 | 528 | 1.0000 | 92 |
| 2026-08 | us_prophet_v3 | watch | 21 | 336 | 336 | 1.0000 | 76 |
| 2026-09 | us_prophet_v3 | buy | 5 | 476 | 476 | 1.0000 | 193 |
| 2026-09 | us_prophet_v3 | buy | 10 | 301 | 301 | 1.0000 | 131 |
| 2026-09 | us_prophet_v3 | laggards | 5 | 108 | 108 | 1.0000 | 24 |
| 2026-09 | us_prophet_v3 | laggards | 10 | 60 | 60 | 1.0000 | 16 |
| 2026-09 | us_prophet_v3 | leaders | 5 | 135 | 135 | 1.0000 | 34 |
| 2026-09 | us_prophet_v3 | leaders | 10 | 75 | 75 | 1.0000 | 25 |
| 2026-09 | us_prophet_v3 | ran | 5 | 108 | 108 | 1.0000 | 33 |
| 2026-09 | us_prophet_v3 | ran | 10 | 60 | 60 | 1.0000 | 21 |
| 2026-09 | us_prophet_v3 | watch | 5 | 432 | 432 | 1.0000 | 96 |
| 2026-09 | us_prophet_v3 | watch | 10 | 240 | 240 | 1.0000 | 77 |
