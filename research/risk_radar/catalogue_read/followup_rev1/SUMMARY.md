# Risk Radar follow-up rev1 — frozen k=3, rule 2b, rates_realrate (PRE)

Window 2006-01-03..2019-12-31, pre 21, post 5, seed 20261112, 2000 draws, tol 0.01, min_off 10. bm_ref rev1 pin. Scorer `<desk>/pivot/radar_eval/`.

## Pins

- `bm_ref.py` `f7350e6e3f5a022a80aa2e9907f0b37cfc256fa8249960557798f50873467c76`
- `adapter.py` `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1`
- scorer module: `<desk>/pivot/radar_eval/engine/risk_radar_eval/pivots.py`

## Date guard

Every date in turns, alerts, levels, episodes and `outcomes_through` is ≤ 2019-12-31 (asserted; max values below).

| surface | max date |
|---|---|
| turns | 2019-12-31 |
| alert_index | 2019-12-31 |
| px_index | 2019-12-31 |
| levels | 2019-12-31 |
| outcomes_through | 2019-12-31 |
| episodes | 2019-12-31 |

## (a) `rr-roff-confluence-k3-followup-rev1-repro` — DECISIVE

| criterion | met |
|---|---|
| (a) cluster share > near-turn placebo p90 at cluster level (0.370) | True |
| (b) > better reference (near) at <= false rate | True |
| (c) > best single leg (rates_realrate) at <= false rate | False |

**criteria_met:** ['a', 'b']  
**nomination:** False

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

- turns scored: 471 (flagged 198), dates 2006-01-11 .. 2019-12-31
- clusters scored: 127 (flagged 57), turn dates 2006-01-11 .. 2019-12-20
- censored turns: 1
- near-turn placebo p90 (cluster): 0.370; observed 0.449; 2000 valid draws
- best single leg: `rates_realrate` (share 0.795, false 4.974)

### Matched threshold x per series (reference match)

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

### Alert share and available legs by year (description)

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

## (b) `rr-roff-confluence-k3-followup-rule2b-desc` — rule clarified after its result was seen; description, cannot be a nomination

Target alert share (pooled k3, windowed): 0.183723. Shift order: shift(1) on the full leg percentile series, then window; threshold on the shifted windowed scores.

| leg | threshold | achieved (finite) | achieved (all) | non-finite sess. | cluster share | 90% CI | false/asset-yr | set beats it |
|---|---|---|---|---|---|---|---|---|
| rates_realrate | 0.814484 | 0.183563 | 0.183351 | 0/72593 | 0.921 | [0.870, 0.957] | 8.508 | no |
| jpy_carry | 0.766865 | 0.184851 | 0.186382 | 0/72593 | 0.661 | [0.586, 0.731] | 5.200 | no |
| growth_cyc_def | 0.825397 | 0.182427 | 0.181478 | 0/72593 | 0.622 | [0.546, 0.694] | 3.628 | no |
| growth_defensives | 0.817460 | 0.184172 | 0.183213 | 0/72593 | 0.559 | [0.482, 0.634] | 3.069 | no |
| bubble_leadership | 0.841270 | 0.184117 | 0.183158 | 0/72593 | 0.409 | [0.336, 0.486] | 3.280 | yes |
| vol_term | 0.811508 | 0.183801 | 0.107132 | 30281/72593 | 0.394 | [0.321, 0.470] | 3.579 | yes |
| credit_hyg_tlt | 0.827381 | 0.184346 | 0.154726 | 11664/72593 | 0.346 | [0.276, 0.422] | 2.749 | no |
| credit_oas_roc | 0.854167 | 0.183508 | 0.182552 | 0/72593 | 0.291 | [0.225, 0.365] | 1.857 | no |
| rates_move | 0.818452 | 0.184325 | 0.183365 | 0/72593 | 0.260 | [0.197, 0.332] | 1.454 | no |
| global_breadth | 0.904762 | 0.183452 | 0.182497 | 0/72593 | 0.260 | [0.197, 0.332] | 1.323 | no |
| bubble_ext | 0.841270 | 0.182898 | 0.181946 | 0/72593 | 0.252 | [0.190, 0.323] | 2.853 | no |
| corr_floor_break | 0.000000 | 0.017743 | 0.017646 | 396/72593 | 0.087 | [0.049, 0.139] | 0.569 | no |

**verdict:** a=True, b=True, c=False, criteria_met=['a', 'b'], parts_checked=12
**nomination: False** — forced; the rule was clarified after the candidate's result was seen.

## (c) `rr-roff-leg-rates-realrate-pre-desc` — description only; NOT a nomination

CEO wording (2026-11-12): on 2006–2019 its catch came from being on often, not from timing; the displaced-clock control (bt1_pre) shows no timing signal. It keeps its forward record from the freeze date. (The ledger row text, which is append-only, records the earlier label.)

| metric | value |
|---|---|
| cluster share | 0.795 |
| 90% CI | [0.727, 0.852] |
| false/asset-yr | 4.974 |
| median delay | -11.0 |
| alert share (pooled) | 0.097 |
| turns scored / flagged | 471 / 380 |
| clusters / flagged | 127 / 101 |
| own placebo p90 | 0.378 |
| own ref dd share / false | 0.173 / 0.479 |
| own ref near share / false | 0.331 / 3.128 |
| better own reference | near |
| (a) share > own p90 | True |
| (b) > better own ref at <= false | False |

Alert share by year: 2006 0.0677, 2007 0.1155, 2008 0.2569, 2009 0.0754, 2010 0.0476, 2011 0.0913, 2012 0.0720, 2013 0.2103, 2014 0.0278, 2015 0.0913, 2016 0.1071, 2017 0.0518, 2018 0.0717, 2019 0.0794

**This is a description, not a nomination.**

## Difference table vs `followup_pre/result.json`

| quantity | PRE | rev1 | delta |
|---|---|---|---|
| cluster_share | 0.4488 | 0.4488 | 0.0000 |
| false_per_asset_year | 2.9264 | 2.9264 | 0.0000 |
| p90 | 0.3701 | 0.3701 | 0.0000 |
| near_share | 0.3228 | 0.3228 | 0.0000 |
| near_false | 2.9507 | 2.9507 | 0.0000 |
| dd_share | 0.2205 | 0.2205 | 0.0000 |
| dd_false | 0.7116 | 0.7116 | 0.0000 |
| rr_share | 0.7953 | 0.7953 | 0.0000 |
| rr_false | 4.9745 | 4.9745 | 0.0000 |
| turns_scored | 471 | 471 | 0.0000 |
| clusters | 127 | 127 | 0.0000 |
| alert_budget | 0.1837 | 0.1837 | 0.0000 |

- turns: hand-built 472, rev1 472; only-hand 0, only-rev1 0 (diff on asset/date/kind/depth/cluster_id/episode_onset).

### Explanations

- **`outcomes_through`.** rev1 passes `outcomes_through=2019-12-31` into `score_alerts` and `reference_result`; PRE left the default (adapter `END_D`, 2023-12-29). The bound is inert in both runs: every alert, price and turn index already ends at 2019-12-31, so the cut shortens nothing. Any delta above therefore cannot come from this.
- **rev1 turn set vs the hand-built turns.** `build_context(..., end_d=2019-12-31)` does the same three things `build_pre_context` did by hand: block='PRE' rows, level series truncated at the end, episode rows cut before any onset/peak/trough. The turn-set diff above is the measured result of that substitution.
- **level truncation.** Both truncate each level series at 2019-12-31, so the running peak/low, the percentile inputs and the reference `dd`/`near` thresholds use the same sessions; no in-window value can move.
- **alert windowing.** Identical in both: full-series t+1 shift, then each series' own sessions from `searchsorted(start) - pre` through the end, `ffill`.
- Nothing was adjusted to match PRE. The PRE numbers are reproduced here as the record, and the deltas (including zero) are reported as they came out.

## Deviations

- bm_ref rev1 build_context(..., start_d=2006-01-03, end_d=2019-12-31) is used for rows, series, level series, swing episodes and turns; it selects block='PRE' because end_d < START_D. The PRE run hand-built the same context from a df truncated at 2019-12-31. The two turn sets are diffed in a.turns_vs_hand_built.
- bm_ref rev1 reference_result forwards start_d/end_d and passes outcomes_through=end_d to score_alerts; the PRE run called build_reference + score_alerts directly and left outcomes_through at the adapter default (2023-12-29). The bound is inert in both runs: every alert, price and turn index already ends at 2019-12-31, so the cut shortens nothing.
- score_alerts bounds outcomes_through at 2019-12-31 and cuts every alert and price series at it before scoring; the candidate alerts are also cut at 2019-12-31 before the call.
- The alert is built on the engine's SPY-session calendar and reindexed onto each series' own level index with method='ffill' (r1g/v2 windowing).
- Two-phase import: Macro's `engine` is purged and the Macro root + cwd are dropped from sys.path before the desk kit loads, so pivots resolves under the desk.
- The window's first 21 sessions precede 2006-01-03; the FRED legs there are the engine's pre-start values, not the PIT replay, which begins 2006-01-03.
- (b) shift order: the t+1 shift is applied to the FULL leg percentile series (score.shift(1)) and the window is taken afterwards, exactly the candidate's convention; part_at_matched_share then takes its threshold on the shifted windowed scores. The alternative order (threshold, then shift) would differ only at the window edges.
- (b) part_at_matched_share measures its achieved share over finite pooled observations only, and returns its alerts on that finite index. For scoring, each part's alert is rebuilt on the FULL windowed index as (shifted score >= returned threshold), with a non-finite session counting as not-alerting; this reproduces the function's own alert exactly where both are defined (asserted per asset). Two consequences, both reported rather than smoothed: (i) the passed-in target share is pooled over all windowed sessions while the function measures over finite sessions, so the finite achieved share is the rule's own number and the all-sessions share is the alert the scorer actually saw; (ii) a leg with in-window non-finite sessions (the ~21-session lead-in before its score exists, plus any data gap) alerts on fewer sessions than the target, so its effective budget is below the k3 set's. The per-leg non-finite counts are tabled.
- (b) the matched target is the k3 set's realised pooled windowed alert share; the per-series mean alert_budget is reported beside it (they differ only through rounding of per-series window lengths).
- (b) is a rule clarified AFTER the candidate's result was seen; nomination is forced False regardless of the verdict.
- The parallel p90 reproduces bm_ref.cluster_placebo_p90's draws, scoring and pooling exactly, only distributing the 2000-draw loop across processes; equivalence is asserted against the desk's own function at 50 draws and recorded in a.placebo_p90.
- (c) is description only: rates_realrate was seen on D and as k3's best PRE leg, so it cannot be a nomination.
