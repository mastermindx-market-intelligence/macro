# Risk Radar — BM-REF description read, five `-v2` sets on block D

Window 2020-01-02..2023-12-29, pre 21, primary post 5 (R-off) / 10 (R-on), seed 20261112, 2000 draws, tol 0.01, min_off 10. Paper-only; nothing sizes, ranks or executes.

**Every row below is seen before the set-level definition, not a nomination.** The `nomination` boolean is description, not a verdict.

> Part (a) in every set below is provisional: the near-turn placebo is not matched on alert exposure (placement defect, PR comment 6835380019; placed mass on these tables' window not yet measured, the desk's mass table supplies it in the follow-up). The two confluence sets were closed on part (c), so the no-nomination verdict does not rest on (a).

## Pins

- `bm_ref.py` `c5130e9e2f80c9da3ff85d66a9f3070367f02e71c10d3e411205a97f12a9f066`
- `adapter.py` `504257977843e0894a97ed53415475eab76d8fc91fa9fc9cb0bbdcb9d24929c1`
- scorer module: `<desk>/pivot/radar_eval/engine/risk_radar_eval/pivots.py`

## Cross-check vs `v2/results.csv` (shifted set rows)

| set | csv cluster share | ours | csv false/yr | ours | match |
|---|---|---|---|---|---|
| rr-roff-incumbent-v2 | 0.3333 | 0.3333 | 1.0035 | 1.0035 | True |
| rr-roff-confluence-k4-v2 | 0.5111 | 0.5111 | 2.0069 | 2.0069 | True |
| rr-ron-incumbent-v2 | 0.2500 | 0.2500 | 1.5752 | 1.5752 | True |
| rr-ron-confluence-k4-v2 | 0.4375 | 0.4375 | 3.3838 | 3.3838 | True |
| rr-ron-exit-v1-v2 | 0.2708 | 0.2708 | 0.3150 | 0.3150 | True |

## rr-roff-incumbent-v2 — R-off (top), post 5, alert `incumbent`

*seen before the set-level definition, not a nomination.*

| row | cluster share | 90% CI | median delay | false/asset-yr | alert share |
|---|---|---|---|---|---|
| **candidate** | 0.333 | [0.218, 0.466] | -9.0 | 1.004 | 0.224 |
| ref dd | 0.356 | [0.237, 0.489] | -13.5 | 0.992 | 0.224 |
| ref near **(better)** | 0.533 | [0.401, 0.662] | -9.0 | 3.850 | 0.224 |

- better reference: **near**
- ref dd budget: target 0.2240, achieved 0.2242
- ref near budget: target 0.2240, achieved 0.2239
- near-turn placebo p90 (cluster): 0.378; observed 0.333; 2000 valid draws; **not verified**: placebo not matched on alert exposure (PR comment 6835380019)
- (a) > p90: **provisional, placebo under repair**; (b) > better ref at <= false: **False**; (c) n/a (not a confluence set)
- criteria_met: `[]`; nomination (description only): **False**

### Matched threshold x per series

| series | dd x | near x |
|---|---|---|
| BAA_10Y | 0.6948 | 0.6266 |
| CYC/DEF | 0.3033 | 0.1861 |
| DIA | 0.0942 | 0.0076 |
| EEM/SPY | 0.7527 | 0.6645 |
| HYG/IEF | 0.0740 | 0.0129 |
| HY_OAS | 0.8414 | 0.7736 |
| IGV/EWDEF | 0.3666 | 0.0482 |
| IWM | 0.2489 | 0.0438 |
| IWM/SPY | 0.3465 | 0.2536 |
| MDY | 0.1412 | 0.0210 |
| QQQ | 0.2130 | 0.0100 |
| QQQ/EWDEF | 0.5725 | 0.4527 |
| RSP | 0.1177 | 0.0094 |
| RSP/SPY | 0.1624 | 0.1036 |
| RSPT/EWDEF | 0.2047 | 0.0253 |
| SMH/EWDEF | 0.6203 | 0.4762 |
| SPHB/SPLV | 0.2512 | 0.0767 |
| SPY | 0.1365 | 0.0050 |
| SPY/GLD | 0.2033 | 0.0696 |
| SPY/TLT | 0.1117 | 0.0126 |
| XLK/EWDEF | 0.5936 | 0.4982 |

## rr-roff-confluence-k4-v2 — R-off (top), post 5, alert `confluence_k4`

*seen before the set-level definition, not a nomination.*

| row | cluster share | 90% CI | median delay | false/asset-yr | alert share |
|---|---|---|---|---|---|
| **candidate** | 0.511 | [0.380, 0.641] | -15.0 | 2.007 | 0.138 |
| ref dd | 0.378 | [0.257, 0.511] | -14.0 | 1.062 | 0.139 |
| ref near **(better)** | 0.400 | [0.277, 0.533] | -12.0 | 3.944 | 0.138 |
| best single leg `rates_realrate` | 0.822 | [0.702, 0.908] | -12.0 | 4.714 | 0.139 |

- better reference: **near**
- ref dd budget: target 0.1383, achieved 0.1386
- ref near budget: target 0.1383, achieved 0.1384
- near-turn placebo p90 (cluster): 0.400; observed 0.511; 2000 valid draws; **not verified**: placebo not matched on alert exposure (PR comment 6835380019)
- (a) > p90: **provisional, placebo under repair**; (b) > better ref at <= false: **True**; (c) > best single leg `rates_realrate` at <= false: **False**
- criteria_met: `['a', 'b']`; nomination (description only): **False**; part (a) provisional, placebo under repair. This set was closed on part (c), so the no-nomination verdict does not rest on (a).

### 12 single legs alone (this family)

| leg | cluster share | false/asset-yr | alert share |
|---|---|---|---|
| rates_realrate **(best)** | 0.822 | 4.714 | 0.139 |
| jpy_carry | 0.667 | 3.361 | 0.145 |
| vol_term | 0.489 | 1.902 | 0.105 |
| rates_move | 0.422 | 1.715 | 0.250 |
| growth_defensives | 0.422 | 2.322 | 0.094 |
| bubble_leadership | 0.378 | 3.197 | 0.148 |
| growth_cyc_def | 0.356 | 1.890 | 0.124 |
| credit_hyg_tlt | 0.333 | 2.404 | 0.108 |
| credit_oas_roc | 0.311 | 1.517 | 0.117 |
| bubble_ext | 0.267 | 2.462 | 0.188 |
| global_breadth | 0.222 | 0.945 | 0.329 |
| corr_floor_break | 0.111 | 0.642 | 0.021 |

### Matched threshold x per series

| series | dd x | near x |
|---|---|---|
| BAA_10Y | 0.7029 | 0.5747 |
| CYC/DEF | 0.3176 | 0.1678 |
| DIA | 0.1210 | 0.0027 |
| EEM/SPY | 0.7632 | 0.6562 |
| HYG/IEF | 0.1328 | 0.0060 |
| HY_OAS | 0.8497 | 0.7594 |
| IGV/EWDEF | 0.3904 | 0.0299 |
| IWM | 0.2682 | 0.0241 |
| IWM/SPY | 0.3705 | 0.2270 |
| MDY | 0.1631 | 0.0074 |
| QQQ | 0.2653 | 0.0019 |
| QQQ/EWDEF | 0.5937 | 0.4401 |
| RSP | 0.1383 | 0.0027 |
| RSP/SPY | 0.1767 | 0.0971 |
| RSPT/EWDEF | 0.2335 | 0.0132 |
| SMH/EWDEF | 0.6460 | 0.4451 |
| SPHB/SPLV | 0.2741 | 0.0561 |
| SPY | 0.1642 | 0.0005 |
| SPY/GLD | 0.2412 | 0.0271 |
| SPY/TLT | 0.1949 | 0.0051 |
| XLK/EWDEF | 0.6113 | 0.4722 |

## rr-ron-incumbent-v2 — R-on (bottom), post 10, alert `incumbent`

*seen before the set-level definition, not a nomination.*

| row | cluster share | 90% CI | median delay | false/asset-yr | alert share |
|---|---|---|---|---|---|
| **candidate** | 0.250 | [0.151, 0.373] | 4.0 | 1.575 | 0.224 |
| ref dd **(better)** | 0.354 | [0.240, 0.483] | 3.5 | 2.264 | 0.196 |
| ref near | 0.354 | [0.240, 0.483] | 3.5 | 2.264 | 0.196 |

- better reference: **dd**
- ref dd budget: target 0.2240, achieved 0.1965 — **budget capped: the >=5% bottom gate makes the candidate's ON share unreachable, so this reference runs a smaller budget than the candidate**
- ref near budget: target 0.2240, achieved 0.1965 — **budget capped: the >=5% bottom gate makes the candidate's ON share unreachable, so this reference runs a smaller budget than the candidate**
- note: the `dd` and `near` forms scored identically here (same cluster share and false rate); under the bottom gate `<` vs `<=` on `r` separates the two forms only at an exact tie, which the matched thresholds did not hit
- near-turn placebo p90 (cluster): 0.583; observed 0.250; 2000 valid draws; **not verified**: placebo not matched on alert exposure (PR comment 6835380019)
- (a) > p90: **provisional, placebo under repair**; (b) > better ref at <= false: **False**; (c) n/a (not a confluence set)
- criteria_met: `[]`; nomination (description only): **False**

### Matched threshold x per series

| series | dd x | near x |
|---|---|---|
| BAA_10Y | 0.1987 | 0.1987 |
| CYC/DEF | 0.5638 | 0.5638 |
| DIA | 0.1495 | 0.1495 |
| EEM/SPY | 0.0143 | 0.0143 |
| HYG/IEF | 0.2592 | 0.2592 |
| HY_OAS | 0.1159 | 0.1159 |
| IGV/EWDEF | 0.0318 | 0.0318 |
| IWM | 0.0587 | 0.0587 |
| IWM/SPY | 0.0323 | 0.0323 |
| MDY | 0.1070 | 0.1070 |
| QQQ | 0.0662 | 0.0662 |
| QQQ/EWDEF | 0.0000 | 0.0000 |
| RSP | 0.1197 | 0.1197 |
| RSP/SPY | 0.0341 | 0.0341 |
| RSPT/EWDEF | 0.0567 | 0.0567 |
| SMH/EWDEF | 0.0000 | 0.0000 |
| SPHB/SPLV | 0.0568 | 0.0568 |
| SPY | 0.0906 | 0.0906 |
| SPY/GLD | 0.1043 | 0.1043 |
| SPY/TLT | 0.0775 | 0.0775 |
| XLK/EWDEF | 0.9989 | 0.9989 |

## rr-ron-confluence-k4-v2 — R-on (bottom), post 10, alert `confluence_k4`

*seen before the set-level definition, not a nomination.*

| row | cluster share | 90% CI | median delay | false/asset-yr | alert share |
|---|---|---|---|---|---|
| **candidate** | 0.438 | [0.315, 0.566] | -8.0 | 3.384 | 0.138 |
| ref dd **(better)** | 0.542 | [0.414, 0.666] | 3.0 | 3.034 | 0.122 |
| ref near | 0.542 | [0.414, 0.666] | 3.0 | 3.034 | 0.122 |
| best single leg `rates_realrate` | 0.875 | [0.768, 0.944] | -4.0 | 4.516 | 0.139 |

- better reference: **dd**
- ref dd budget: target 0.1383, achieved 0.1224 — **budget capped: the >=5% bottom gate makes the candidate's ON share unreachable, so this reference runs a smaller budget than the candidate**
- ref near budget: target 0.1383, achieved 0.1224 — **budget capped: the >=5% bottom gate makes the candidate's ON share unreachable, so this reference runs a smaller budget than the candidate**
- note: the `dd` and `near` forms scored identically here (same cluster share and false rate); under the bottom gate `<` vs `<=` on `r` separates the two forms only at an exact tie, which the matched thresholds did not hit
- near-turn placebo p90 (cluster): 0.646; observed 0.438; 2000 valid draws; **not verified**: placebo not matched on alert exposure (PR comment 6835380019)
- (a) > p90: **provisional, placebo under repair**; (b) > better ref at <= false: **False**; (c) > best single leg `rates_realrate` at <= false: **False**
- criteria_met: `[]`; nomination (description only): **False**

### 12 single legs alone (this family)

| leg | cluster share | false/asset-yr | alert share |
|---|---|---|---|
| rates_realrate **(best)** | 0.875 | 4.516 | 0.139 |
| growth_defensives | 0.521 | 3.127 | 0.094 |
| jpy_carry | 0.500 | 2.415 | 0.145 |
| vol_term | 0.479 | 2.754 | 0.105 |
| growth_cyc_def | 0.375 | 1.680 | 0.124 |
| credit_oas_roc | 0.333 | 2.625 | 0.117 |
| credit_hyg_tlt | 0.333 | 1.995 | 0.108 |
| bubble_leadership | 0.250 | 2.065 | 0.148 |
| rates_move | 0.208 | 2.870 | 0.250 |
| bubble_ext | 0.167 | 1.575 | 0.188 |
| global_breadth | 0.125 | 1.085 | 0.329 |
| corr_floor_break | 0.104 | 0.770 | 0.021 |

### Matched threshold x per series

| series | dd x | near x |
|---|---|---|
| BAA_10Y | 0.1667 | 0.1667 |
| CYC/DEF | 0.5317 | 0.5317 |
| DIA | 0.0593 | 0.0593 |
| EEM/SPY | 0.0065 | 0.0065 |
| HYG/IEF | 0.2052 | 0.2052 |
| HY_OAS | 0.0601 | 0.0601 |
| IGV/EWDEF | 0.0144 | 0.0144 |
| IWM | 0.0408 | 0.0408 |
| IWM/SPY | 0.0144 | 0.0144 |
| MDY | 0.0544 | 0.0544 |
| QQQ | 0.0353 | 0.0353 |
| QQQ/EWDEF | 0.0000 | 0.0000 |
| RSP | 0.0687 | 0.0687 |
| RSP/SPY | 0.0204 | 0.0204 |
| RSPT/EWDEF | 0.0279 | 0.0279 |
| SMH/EWDEF | 0.0000 | 0.0000 |
| SPHB/SPLV | 0.0337 | 0.0337 |
| SPY | 0.0462 | 0.0462 |
| SPY/GLD | 0.0641 | 0.0641 |
| SPY/TLT | 0.0376 | 0.0376 |
| XLK/EWDEF | 0.9989 | 0.9989 |

## rr-ron-exit-v1-v2 — R-on (bottom), post 10, alert `exit_v1`

*seen before the set-level definition, not a nomination.*

| row | cluster share | 90% CI | median delay | false/asset-yr | alert share |
|---|---|---|---|---|---|
| **candidate** | 0.271 | [0.168, 0.396] | 4.0 | 0.315 | 0.283 |
| ref dd **(better)** | 0.417 | [0.296, 0.545] | 3.0 | 2.089 | 0.247 |
| ref near | 0.417 | [0.296, 0.545] | 3.0 | 2.089 | 0.247 |

- better reference: **dd**
- ref dd budget: target 0.2833, achieved 0.2471 — **budget capped: the >=5% bottom gate makes the candidate's ON share unreachable, so this reference runs a smaller budget than the candidate**
- ref near budget: target 0.2833, achieved 0.2471 — **budget capped: the >=5% bottom gate makes the candidate's ON share unreachable, so this reference runs a smaller budget than the candidate**
- note: the `dd` and `near` forms scored identically here (same cluster share and false rate); under the bottom gate `<` vs `<=` on `r` separates the two forms only at an exact tie, which the matched thresholds did not hit
- near-turn placebo p90 (cluster): 0.458; observed 0.271; 2000 valid draws; **not verified**: placebo not matched on alert exposure (PR comment 6835380019)
- (a) > p90: **provisional, placebo under repair**; (b) > better ref at <= false: **False**; (c) n/a (not a confluence set)
- criteria_met: `[]`; nomination (description only): **False**

### Matched threshold x per series

| series | dd x | near x |
|---|---|---|
| BAA_10Y | 0.2244 | 0.2244 |
| CYC/DEF | 0.5776 | 0.5776 |
| DIA | 0.1752 | 0.1752 |
| EEM/SPY | 0.0204 | 0.0204 |
| HYG/IEF | 0.3384 | 0.3384 |
| HY_OAS | 0.1551 | 0.1551 |
| IGV/EWDEF | 0.0419 | 0.0419 |
| IWM | 0.0753 | 0.0753 |
| IWM/SPY | 0.0557 | 0.0557 |
| MDY | 0.1306 | 0.1306 |
| QQQ | 0.0899 | 0.0899 |
| QQQ/EWDEF | 0.0000 | 0.0000 |
| RSP | 0.1362 | 0.1362 |
| RSP/SPY | 0.0484 | 0.0484 |
| RSPT/EWDEF | 0.0722 | 0.0722 |
| SMH/EWDEF | 0.0000 | 0.0000 |
| SPHB/SPLV | 0.0748 | 0.0748 |
| SPY | 0.1239 | 0.1239 |
| SPY/GLD | 0.1261 | 0.1261 |
| SPY/TLT | 0.1991 | 0.1991 |
| XLK/EWDEF | 0.9989 | 0.9989 |

## Turns and end bound

- R-off: 191 turns, 2020-01-02 .. 2023-10-12
- R-on: 197 turns, 2020-03-16 .. 2023-11-13
- every scored turn row and every alert/reference date ends by 2023-12-29 (asserted; the bar is that nothing dated 2024-01-02 or later enters any alert, turn or outcome).

## Deviations and notes

- bm_ref.reference_result does not forward start_d/end_d, so each reference is built with build_reference(..., start_d='2020-01-02', pre=21, shift=1, end_d='2023-12-29') + score_alerts directly, the same path reference_result takes with its defaults.
- Alerts are reused verbatim from v2/run_read_v2.py (build_alerts + window_alert): the t+1 shift is applied to the full series before the D window is cut, exactly as v2/r1g.
- bm_ref.build_context hard-codes block='D'; turns are restricted to turns_in_window(ctx['turns'], 2020-01-02, 2023-12-29) (a no-op here: the catalogue's rows are already block D).
- ns: each set has its own p90 because the placebo draws depend on that candidate's own alert run lengths.
- include_passes=True is used so run_pass_line's require_activity=True pass line is present; the reported cluster share and false rate come from the deterministic score_pivots_multi.
- DESCRIPTION ONLY: every row was seen before the set-level definition and is not a nomination; the `nomination` boolean is reported as description.
