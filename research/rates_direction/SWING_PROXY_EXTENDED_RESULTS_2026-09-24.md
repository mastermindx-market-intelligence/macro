# Expanded indicator comparison: no predictive promotion

## Finding

On the predeclared earlier-date partition, none of the seven oscillator additions improved the trend/volatility baseline's three-class probability score. The all-three primary was effectively unchanged but slightly worse. This is a negative result for the frozen default-crossover/state construction, not a rejection of every oscillator-phase or early-turn method. No candidate is promoted.

This replication used the SAME signal definitions, 12-bar observed-session target, one-bar delay, barrier, warmup, recency, shrinkage and primary hypothesis as the small pilot. It did not select the pilot's best-looking P+R pair as the new primary. Only capture coverage and computation speed changed; exact synthetic dictionary parity checked the optimized walker against the original.

## Data and evaluation scope

Immutable two-year Yahoo ^TNX capture: 3,509 timestamped records, 2024-09-24 through 2026-09-24. Provider-session parsing produced 2,004 completed chart slots: 1,503 full two-hour bars and 501 scheduled 40-minute closing stubs. One initial expected hourly input was absent, so its aggregate remains invalid; 2,003 bars are valid, with a fresh warmup after that gap. Irregular snapshot/current incomplete intervals are excluded, and no OHLC was fabricated.

The model made 1,870 reconstructed forecast origins, each with nine distributions (16,830 model/date forecasts, NOT independent samples). The earlier primary partition has 1,597 scored origins on 401 source dates, from 2024-11-08 through 2026-06-17. Four additional earlier origins are ambiguous and excluded from probability scores. Thirteen boundary-crossing origins are counted separately. The June-September seen-overlap partition has 243 scored origins plus 13 censored tails.

Primary complete target windows end strictly before 2026-06-24. Earlier dates were unexamined in this specific intraday comparison when frozen, but are not claimed untouched by all company research, point-in-time certified, or an independent prospective holdout. Outcomes are first OBSERVED-session touches; unobserved overnight excursions cannot be classified. Closing stubs are not full two-hour intervals. Native Pine, exact TVC:US10Y and actual chart-setting parity remain unproven.

## Complete primary comparison

Lower Brier is better. Relative improvement versus trend/volatility is negative when worse. All models are evaluated on the SAME 1,597 scored origins; indicators can be inactive and then defer to the baseline.

| Model | Brier | Relative improvement | Active forecast origins | Resolved non-overlapping active episodes |
|---|---:|---:|---:|---:|
| Unconditional historical frequencies | 0.674413 | - | - | - |
| Trend + volatility baseline | 0.665530 | reference | - | - |
| M: MACD-RSI | 0.669079 | -0.533% | 429 | 83 |
| P: price Stochastic strict zone rule | 0.667760 | -0.335% | 452 | 87 |
| R: Stochastic RSI proposed crossover | 0.672016 | -0.975% | 962 | 105 |
| M+P | 0.665999 | -0.070% | 109 | 48 |
| M+R | 0.667232 | -0.256% | 197 | 60 |
| P+R | 0.669357 | -0.575% | 353 | 84 |
| M+P+R, PRIMARY | 0.665704 | -0.026% | 86 | 37 |

M, P, R, MR and PR exceed the preregistered 50-episode minimum, but none improves the score. MP and the primary MPR remain below that floor. Passing the episode floor is not statistical significance or acceptance. The all-three configuration is active on only 86/1,601 earlier origins, about 5.4%; agreement removes most opportunities without establishing extra predictive quality.

Date-averaged paired Brier improvement, positive = better: primary MPR mean -0.00021, HAC standard error 0.00090, t=-0.232, p=0.8168 (401 dates, lag 3). R's diagnostic t=-2.526, p=0.0115 is in the WORSE direction and not selection-adjusted. All uncertainty measures are descriptive; no significant-benefit or causal claim is made.

## No-hit, direction and selective-denominator cautions

The primary scored outcomes are 473 upper-first, 483 lower-first and 641 neither. Four earlier same-hour dual-touch outcomes stay ambiguous. A 'no hit' is a real outcome, not a discarded failure or a neutral forecast. These counts explain why conditional hit percentages alone can look attractive without improving the full probability forecast.

For auditability, direct directional successes / all resolved non-overlapping episodes are M 21/83, P 31/87, R 28/105, MP 14/48, MR 21/60, PR 29/84 and MPR 11/37. These are observed-session barrier successes, not trading win rates or returns. No-hit counts respectively are 29,36,40,19,21,32,16. Filtering those out changes the question and denominator; it cannot become a rescue headline.

## Small pilot did not replicate

The initial small pilot's best-looking secondary P+R improved Brier by 1.71%, with only six resolved episodes. In the larger earlier partition it is 0.575% worse. This is why no winner was chosen from that first run.

Seen overlap remains separate. Relative improvements there: M +0.280%, P -0.039%, R -0.887%, MP +0.924%, MR +0.034%, PR -0.256%, MPR +0.321%. These are not a new primary or a basis for selecting a winner; primary/all-three has only four resolved episodes there. The overlap also has longer prehistory and a later capture vintage, so it is not an exact replay of the short-window pilot.

## Immutable execution and verification

Source/spec freeze commit: 975259d0f78b090b8941af5e5168a906d39a7905, published before extended outcome access. Freeze timestamp: 2026-09-24T14:26:10.695092+00:00. Execution: original Studio process 64919, successful. Nine expanded configurations appended to the SAME ric_swing_proxy_v1 TrialLedger family, 18 cumulative including the first pilot. Source generation never resets the trial history.

Private evidence directory: /Volumes/Mastermind/evidence/rates-direction-20260924-sol-001/swing-proxy-v1/extended-975259d/.
Source SHA256: 1dc7e9121fd6aa36c5019beba303b629257eb1cab752ae937e4cef1aa8161b76.
Predictions SHA256: f97e2771ece94241c5d1f6f4e46a1519414034cc29ffbe077c0a0a592f32790c.
Summary SHA256: 9d3339455075f28e1954a38f284a74c07df2dcdb23c14d989bce442d5b80ba1b.
Aggregates: swing_proxy_extended_results_v1.json; registration and integrity companion JSON files.

Saved-row same-author arithmetic pass (process 65602): all 18 partition/model Brier recomputations match, probability normalization/finite values and strict training target-end-before-origin pass, unique origins pass, frozen code/source and nine-row append-only ledger suffix pass. Zero new fits or configurations in this audit. This is not independent review or native Pine certification.

## What this does and does not decide

Do not ship a risk-on/off switch based on these default crosses or require all three as if agreement were proven quality. Preserve observed indicators as context. This experiment does not test every early histogram curl, shallow-price-retracement reset, completed higher-timeframe context or conditional equity-response model; neither success nor failure for those can be inferred here.

The next scientific choice must be explicitly new and registered before outcomes: test causal early-phase/impulse-reset features against this frozen crossover benchmark, retaining the same scoring discipline and all seen-history disclosure. Exact-chart replication still needs native exported outputs and matching TVC/session bars. Equity usefulness needs a separate incremental forecast test against equity-only baselines. No current portfolio changes, prospective accuracy, merge, deployment or parent completion are claimed.
