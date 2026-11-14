# Pre-2003 industry repair pilot: observed results

Status: EXPLORATORY MECHANISM SCREEN, NOT A DOT BACKTEST OR TRADING VALIDATION.

## Execution and provenance

Protocol was committed before outcomes at `4887fbb91298cb941ecfa36456fd0d8130d76478`; code at `561db182e387222b6e2b5516ee749232a2a9956e`. The principal executed authored `pilot.py` in an isolated admitted M2 SSD workspace. Process 7704 completed with exit 0. No private dot panel or held-out industry/stock outcome was read. No PR, production change, worker dispatch or trading action occurred.

Code SHA256: `b9a5c2edbe303bed3f02403ae4544972593b557a9ad2c6286d67f390d1823de2`.
Full local aggregate RESULTS.json SHA256: `a1d9fc255469822a138a6cc04ecbf906497c6a2b0df44c28a1f3f99fc0aa5151`.
Local relative path: `research/rotation_core/pro_runs/astra_transition_repair_20261114/RESULTS.json` in the operation-bound SSD workspace. This report preserves the principal statistics; the original machine output remains local, not falsely represented as committed.

Public inputs, both using the 202609 CRSP database:
- French 49-industry daily value-weighted returns: archive SHA256 `b9d36d571e968d71f7b03207e7fed6398554f953719b8c1bf3ee3ad8d00e7520`, 4,177,116 bytes; parsed pre-2003 CSV SHA256 `984eab80452df3f6abc26d7681fc635d24ec8b4a54387a387fc3fce63486e135`.
- French daily research factors: archive SHA256 `96c23b88e651cbfff3740a53f8225e59ee39893371e96385a1d8125ec2cd9c89`, 178,326 bytes; parsed pre-2003 CSV SHA256 `da39a0e24e780fee1e2855ba69ffb6fe84600be2304a902546a4309ceb7451db`.
- Each parser retained 20,364 daily observations from 1926-07-01 through 2002-12-31. Later rows were excluded as date strings before numeric parsing. Market total return is Mkt-RF + RF. Raw inputs are not committed.

Checks passed: sentinel handling, percentage conversion, date cutoff before numeric parsing, unique industry/date events, competing-barrier partition, and feature prefix invariance at 1950-12-29, 1982-12-31 and 2001-12-31. This is author self-verification, not independent review.

## Population and definitions

8,902 eligible industry-month observations across 790 distinct decision months, first 1927-06-30 and last 2002-09-30. There were 2,659 consecutive qualifying industry-month spells. These are NOT 8,902 or 2,659 independent market episodes. Of 9,028 candidate rows, 81 lacked a complete forward horizon, 10 had missing forward data, and 35 lacked a qualified donor universe.

Candidate: trailing 126-session relative loss and at least 10% drawdown from trailing 126-session total-return-index high. Entry next-session close; outcome 63 subsequent sessions; assumed 20 bp round-trip cost. This is an industry mechanism screen, NOT a substitute for the proprietary dot/T1-T3 event population.

R = recipient's trailing 21-session return positive both absolutely and relative to market. D = prior-winner tercile's trailing 21-session average relative return negative, excluding recipient; winner ranking uses t-252 through t-22. V = market 21-session volatility below 63-session volatility.

Bad10 = closing loss of at least 10% at any time over the next 63 sessions. Upper/lower first = first crossing of symmetric log barriers at +/- 2 * pre-entry sigma63 * sqrt(21); neither crossing remains unresolved. Barrier outcomes and Bad10 are different questions. All percentages below are percent, not fractions.

## Main comparisons

| Condition | Events | Months | Positive net return | Bad10 | Mean net63 | Mean excess63 | Upper first | Lower first | Unresolved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| All candidates | 8902 | 790 | 56.93 | 35.06 | 2.97 | -0.20 | 29.16 | 26.65 | 44.19 |
| R absent | 7247 | 773 | 57.00 | 35.06 | 3.16 | -0.21 | 30.11 | 27.53 | 42.36 |
| R present | 1655 | 411 | 56.62 | 35.05 | 2.15 | -0.20 | 25.02 | 22.78 | 52.21 |
| R, D absent | 880 | 240 | 58.41 | 32.16 | 3.23 | 0.39 | 27.84 | 23.30 | 48.86 |
| R, D present | 775 | 179 | 54.58 | 38.32 | 0.93 | -0.87 | 21.81 | 22.19 | 56.00 |
| R, V absent | 475 | 149 | 56.00 | 40.42 | 2.28 | -0.81 | 28.42 | 28.42 | 43.16 |
| R, V present | 1180 | 262 | 56.86 | 32.88 | 2.10 | 0.05 | 23.64 | 20.51 | 55.85 |

R selects 18.6% of all candidate events. The lower-barrier reduction does not establish more successful trades: upper-first also falls by 5.09 percentage points, while unresolved rises by 9.84 points. The fixed 10% bad-buy rate is essentially unchanged. This is an observed outcome partition, not proof of the causal reason for it.

### Differences with descriptive 95% moving-block intervals

Blocks are 12 calendar months, 2,000 resamples, seed 20261114; all industries remain together within each sampled month. Intervals are not adjusted for the full family of outcomes/comparisons and do not establish a deployable edge.

| Comparison | Win difference, percentage points | Bad10 difference, pp | Excess63 difference, pp | Lower-first difference, pp |
|---|---:|---:|---:|---:|
| R present minus absent | -0.39 [-4.72, 3.62] | -0.02 [-4.13, 4.78] | 0.004 [-0.77, 0.76] | -4.75 [-8.19, -0.89] |
| D present minus absent within R | -3.83 [-14.87, 5.39] | 6.16 [-3.06, 15.73] | -1.26 [-3.13, 0.32] | -1.10 [-9.07, 7.81] |
| V present minus absent within R | 0.86 [-9.54, 10.36] | -7.54 [-17.28, 1.72] | 0.86 [-0.76, 2.39] | -7.91 [-16.39, -0.07] |

The D proxy does not validate a positive rotation vote. Its point estimates are adverse, but uncertainty is too broad for a general negative conclusion. The V safety direction merits a hypothesis, not promotion: its Bad10 interval crosses zero and its lower-first improvement is partly accompanied by unresolved outcomes.

## Full registered cells

| R | D | V | N | Months | Win % | Bad10 % | Net63 % | Excess63 % | Net21 % | Mean MAE % | Upper % | Lower % | Unresolved % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|0|0|0|1560|198|55.26|37.69|3.39|-0.22|0.28|-9.50|28.33|31.54|40.13|
|0|0|1|2106|289|58.40|33.24|4.14|0.67|1.23|-9.23|30.91|25.17|43.92|
|0|1|0|2063|176|59.62|35.72|3.44|-0.72|0.33|-9.42|31.12|26.81|42.07|
|0|1|1|1518|171|53.29|33.99|1.17|-0.72|0.15|-9.38|29.45|27.67|42.89|
|1|0|0|257|82|61.87|34.24|5.35|0.40|1.24|-9.20|31.91|28.02|40.08|
|1|0|1|623|158|56.98|31.30|2.36|0.39|0.70|-9.02|26.16|21.35|52.49|
|1|1|0|218|72|49.08|47.71|-1.35|-2.24|-2.19|-12.85|24.31|28.90|46.79|
|1|1|1|557|107|56.73|34.65|1.82|-0.34|1.04|-9.60|20.83|19.57|59.61|

## Era instability

| Era | R | N | Months | Win % | Bad10 % | Net63 % | Excess63 % | Upper % | Lower % | Unresolved % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|1927-1962|0|3151|348|54.55|37.89|3.04|0.06|25.74|25.99|48.27|
|1927-1962|1|674|174|50.30|43.92|0.20|-0.27|18.40|27.45|54.15|
|1963-1982|0|2183|207|56.07|35.78|2.59|-0.19|36.92|34.68|28.40|
|1963-1982|1|499|113|57.31|33.27|2.13|-0.39|32.26|26.25|41.48|
|1983-2002|0|1913|218|62.10|29.59|4.01|-0.67|29.53|21.90|48.56|
|1983-2002|1|482|124|64.73|24.48|4.91|0.09|26.76|12.66|60.58|

The modern-era directional improvement is descriptive. Selecting the modern era after seeing this table would be selection, not independent confirmation. These eras are not verified monetary regimes.

## Geometry and date matching

Same-month nearest control with replacement; feature-only standardization on log sigma63, drawdown126, distance above trailing21 low and relative126. Caliper 1 standardized Euclidean unit. Retained 1,032 pairs across 298 months, 675 unique controls, 62.36% of R events. Mean distance 0.5721. Remaining standardized mean imbalance: sigma 0.0157; drawdown 0.0337; distance-to-low 0.2643; relative126 0.0067. Matching is imperfect and restricts the population.

| Matched difference | Estimate, pp | 95% interval, pp |
|---|---:|---:|
| Win | 2.03 | [-1.57, 5.59] |
| Bad10 | 1.65 | [-0.70, 4.57] |
| Net63 / excess63 | -0.08 | [-1.15, 0.75] |
| Net21 | 0.26 | [-0.17, 0.67] |
| Mean MAE | -0.10 | [-0.59, 0.29] |
| Upper first | 1.65 | [-1.34, 4.84] |
| Lower first | -0.39 | [-2.77, 2.33] |
| Unresolved | -1.26 | [-5.13, 2.06] |

The raw lower-barrier benefit does not survive this diagnostic as a clear incremental association. This does not prove that geometry explains everything, nor that proprietary dot-low hold results are invalid.

## Execution-delay sensitivity

With entry delayed two sessions instead of one, 8,885 events remain across 789 months. R absent: 57.44% win, 35.31% Bad10, 3.22% mean net63, -0.19% excess63. R present: 56.68% win, 35.35% Bad10, 2.18% mean net63, -0.10% excess63. The broad no-improvement conclusion is not reversed by that declared sensitivity; no delay was selected for best performance.

## What this does and does not establish

This screen rejects treating these exact simple price-only gates as already validated. It does not reject context gating, proprietary dots, specific stock families, fundamentals, genuine point-in-time cohort repair, or Chris's MCD mechanism. Neither a 10% loss nor a reversal barrier is a complete definition of a durable bottom. Industry averages may conceal relevant company heterogeneity. Current-vintage returns, changing industry membership, sample selection, overlapping horizons, a long historical span, index investability and unknown historical implementation costs limit transfer.

Next independent question: does recipient resilience specifically during adverse market days add information after controlling for its pre-existing market sensitivity and ordinary rebound? This is a declared follow-up on an already examined exploratory era, not a new untouched holdout. Fundamental deterioration and economic peer-link hypotheses require additional point-in-time data and are not tested by the price-only panel.
