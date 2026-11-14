# Risk Radar follow-up — R-off confluence k=3 (PRE)

Ledger row `rr-roff-confluence-k3-followup`. Window 2006-01-03..2019-12-31, pre 21, post 5, seed 20261112, 2000 draws, tol 0.01, min_off 10.

## Pins

- `bm_ref.py` `c5130e9e2f80c9da3ff85d66a9f3070367f02e71c10d3e411205a97f12a9f066`
- `adapter.py` `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1`
- scorer module: `<desk>/pivot/radar_eval/engine/risk_radar_eval/pivots.py`

## Verdict

**selected after seeing D; decisive PRE read; next: desk attack seat; forward candidate only (no hold-out)**

> Part (a) is provisional (placebo placement defect, PR comment 6835380019). This set was closed on
> part (c), so the no-nomination verdict does not rest on (a).

> **Placebo not matched on alert exposure** (placement defect, see PR comment 6835380019). Placed mass on this table's window not yet measured; the desk's mass table supplies it in the follow-up. The p90 in this table are not verified until the repair.

| criterion | met |
|---|---|
| (a) cluster share > near-turn placebo p90 at cluster level (0.370) | provisional, placebo under repair |
| (b) > better reference (near) at <= false rate | True |
| (c) > best single leg (rates_realrate) at <= false rate | False |

**criteria_met:** ['a', 'b']  (part (a) provisional, placebo under repair)  
**nomination:** False

## Table — candidate, better reference, 12 single legs

| set | cluster share | 90% CI | median delay | false/asset-yr | alert share |
|---|---|---|---|---|---|
| **candidate k=3** | 0.449 | [0.374, 0.526] | -12.0 | 2.926 | 0.184 |
| ref dd | 0.221 | [0.161, 0.290] | -14.0 | 0.712 | 0.184 |
| ref near **(better)** | 0.323 | [0.254, 0.398] | -10.0 | 2.951 | 0.184 |
| leg rates_realrate | 0.795 | [0.727, 0.852] | -11.0 | 4.974 | 0.097 |
| leg jpy_carry | 0.528 | [0.451, 0.603] | -14.0 | 3.475 | 0.112 |
| leg growth_cyc_def | 0.370 | [0.299, 0.446] | -8.5 | 2.072 | 0.108 |
| leg bubble_leadership | 0.331 | [0.262, 0.406] | -16.0 | 2.916 | 0.127 |
| leg growth_defensives | 0.315 | [0.247, 0.389] | -15.0 | 1.906 | 0.109 |
| leg vol_term | 0.299 | [0.233, 0.373] | -8.0 | 1.805 | 0.060 |
| leg credit_hyg_tlt | 0.283 | [0.218, 0.357] | -15.0 | 1.843 | 0.095 |
| leg credit_oas_roc | 0.276 | [0.211, 0.348] | -15.0 | 1.389 | 0.135 |
| leg bubble_ext | 0.236 | [0.175, 0.306] | -5.0 | 2.562 | 0.127 |
| leg global_breadth | 0.213 | [0.155, 0.281] | -10.5 | 1.402 | 0.357 |
| leg rates_move | 0.205 | [0.148, 0.273] | -12.5 | 1.208 | 0.115 |
| leg corr_floor_break | 0.087 | [0.049, 0.139] | 2.0 | 0.569 | 0.018 |

## Turns and clusters

- turns scored: 471 (flagged 198), dates 2006-01-11 .. 2019-12-31
- clusters scored: 127 (flagged 57), turn dates 2006-01-11 .. 2019-12-20
- censored turns: 1
- near-turn placebo p90 (cluster): 0.370; observed 0.449; 2000 valid draws; **not verified**: placebo not matched on alert exposure (PR comment 6835380019)

## Alert share and available legs by year (description)

| year | alert share | mean legs available |
|---|---|---|
| 2006 | 0.0598 | 10.00 |
| 2007 | 0.3147 | 10.00 |
| 2008 | 0.5692 | 10.66 |
| 2009 | 0.0635 | 11.00 |
| 2010 | 0.0119 | 11.00 |
| 2011 | 0.1627 | 11.00 |
| 2012 | 0.0520 | 12.00 |
| 2013 | 0.0238 | 12.00 |
| 2014 | 0.3095 | 12.00 |
| 2015 | 0.3175 | 12.00 |
| 2016 | 0.1865 | 12.00 |
| 2017 | 0.0000 | 12.00 |
| 2018 | 0.3147 | 12.00 |
| 2019 | 0.1865 | 12.00 |

## Matched threshold x per series

| series | dd x | near x |
|---|---|---|
| BAA_10Y | 0.6347 | 0.4724 |
| CYC/DEF | 0.3527 | 0.1994 |
| DIA | 0.1315 | 0.0024 |
| EEM/SPY | 0.5823 | 0.0456 |
| HYG/IEF | 0.1691 | 0.0227 |
| HY_OAS | 0.8185 | 0.6526 |
| IGV/EWDEF | 0.3425 | 0.1825 |
| IWM | 0.1688 | 0.0104 |
| IWM/SPY | 0.1428 | 0.0486 |
| MDY | 0.1300 | 0.0056 |
| QQQ | 0.6192 | 0.0196 |
| QQQ/EWDEF | 0.7531 | 0.6744 |
| RSP | 0.1494 | 0.0035 |
| RSP/SPY | 0.0627 | 0.0066 |
| RSPT/EWDEF | 0.2815 | 0.0968 |
| SMH/EWDEF | 0.8284 | 0.7418 |
| SPHB/SPLV | 0.2887 | 0.1356 |
| SPY | 0.1663 | 0.0029 |
| SPY/GLD | 0.6444 | 0.1464 |
| SPY/TLT | 0.4162 | 0.0570 |
| XLK/EWDEF | 0.7669 | 0.7263 |

## Deviations

- bm_ref.build_context hard-codes block='D' via _family_rows, so turns_in_window(build_context(...)['turns'], 2006, 2019) would be empty. The PRE context is built directly: A.select(..., block='PRE') on the catalogue truncated at 2019-12-31, swing episodes from the same truncated rows, bm_ref.build_turns + turns_in_window.
- bm_ref.reference_result does not forward start_d/end_d; build_reference + score_alerts are called directly with start_d=2006-01-03, end_d=2019-12-31.
- Episodes are built from catalogue rows truncated at 2019-12-31, so no post-2019 trough or recovery can define an in-episode span (the PRE analogue of the catalogue's own 2023-12-29 truncation).
- The alert is built on the engine's SPY-session calendar and reindexed onto each series' own level index with method='ffill' (r1g/v2 windowing).
- score_alerts bounds outcomes_through at the adapter's END_D (2023-12-29); the bound is inert here because every scored alert, turn, price and episode date is <= 2019-12-31 (asserted).
- Two-phase import fix: Macro's `engine` is purged and the Macro root + cwd are dropped from sys.path before the desk kit loads, so pivots resolves under the desk (the dead worker's run had it resolving to the worktree copy).
- The window's first 21 sessions precede 2006-01-03, so the FRED legs there are the engine's pre-start (one-session-shifted) values, not the PIT replay, which begins 2006-01-03 per the ledger row.
