# MACD cycle-aware research — measured continuation, 2026-09-15

Status: **PARTIAL research; zero production authority.** This is a second exploratory look on an already exposed current-universe panel, not an accepted signal, a fresh holdout, or an investment recommendation. Numerical percentages below are rounded from locally generated evidence; percentage-point differences are not percent relative improvements.

## What changed in this continuation

The unfinished extension now runs. Three synthetic tests passed after an expected RED on the missing event-builder result. The expanded replay completed with exit code 0: **360,571 signal observations across 242 stocks**, spanning 18 indicator/grain variants and 13 declared exit/horizon policies. It reproduced all **126,440 original event identities, depth bins, and 21/63-session raw/SPY-relative outcomes** to the declared 1e-12 numerical tolerance. These are overlapping observations and alternative descriptions of shared histories, not 360,571 independent trades.

All equity series end on 2025-12-31, and each has no missing market sessions inside its own covered span. Event dates start in 2010; both events and labels are constrained to end no later than 2025-12-31. The longer SPY/calendar record did not expose 2026 equity outcomes. The original files were not changed.

A separate, predeclared attribution pass completed on **13,288 original repair-context observations**, with an additional synthetic date/spell-weighting test passing. It used the original selected-context file and price snapshot, not the blocked expanded output tables described below.

## 1. Two-day versus three-day is partly a filter-memory question

All rows here are bullish crosses in the indicator's own deep-negative bin. Entry is the following market-session adjusted close. A positive return is not a target-before-stop win, and different constructions select different observations.

| Construction | Grain | 21-session n | Positive rate | Mean return | Mean excess vs SPY |
|---|---:|---:|---:|---:|---:|
| Price, fast 12/26/9 recipe | 2D | 2,062 | 60.82% | 2.20% | 0.33% |
| Price, fast recipe with 3D-equivalent per-session decay | 2D | 1,239 | 65.62% | 3.31% | 1.33% |
| Price, fast 12/26/9 recipe | 3D | 1,178 | 67.49% | 3.68% | 1.42% |
| Incumbent RSI14, slow 14/60/5 recipe | 2D | 5,194 | 59.90% | 1.90% | 0.10% |
| Incumbent RSI14, slow recipe with 3D-equivalent per-session decay | 2D | 3,494 | 58.76% | 1.60% | 0.24% |
| Incumbent RSI14, slow 14/60/5 recipe | 3D | 3,355 | 59.14% | 1.62% | 0.27% |

Matching price-filter decay substantially narrows the raw 2D/3D difference. This is evidence that unchanged bar-count parameters confound sampling frequency with memory. It is not a causal decomposition of the percentage-point gap: matching memory also changes selected dates and the depth-normalization history. The RSI result does not display the same large improvement.

The decay control is `alpha_2D = 1 - (1 - alpha_3D)^(2/3)`; nominal normalization-history span is adjusted too. Equal decay is not identical sampled information. No bar-anchor search or per-name outcome optimization was performed. No statistical-superiority or production timing claim is accepted from these aggregate contrasts.

## 2. Price versus RSI is not explained solely by the EMA recipe

| 3D input and recipe | 21-session n | Positive rate | Mean return | Mean SPY excess |
|---|---:|---:|---:|---:|
| Price / fast 12/26/9 recursive recipe | 1,178 | 67.49% | 3.68% | 1.42% |
| RSI14 / same fast recipe | 2,724 | 58.48% | 1.82% | 0.44% |
| Price / slow 14/60/5 adjusted recipe | 990 | 63.13% | 2.86% | 0.73% |
| RSI14 / same slow recipe | 3,355 | 59.14% | 1.62% | 0.27% |

The input gap persists within either recipe, but its magnitude changes with the recipe. The original 67.49% versus 59.14% comparison changed both input and recipe. Own-indicator deep-negative bins are not identical economic populations: the displayed counts differ sharply. Therefore these results justify keeping price MACD as a serious challenger, not immediately replacing Prophet's incumbent signal or declaring a causal price-input advantage.

At 63 sessions, fast-price 3D has 66.70% positive returns and 0.77% mean SPY excess, while incumbent RSI-slow 3D has 63.96% and 0.67%. Slow-price 3D has 67.01% positive returns but only 0.024% mean SPY excess and approximately -0.286% prior-beta-adjusted excess. A high positive-return frequency is not synonymous with useful excess return.

## 3. The selected repair-state headline is strongly aggregation-sensitive

The original predicate combines stock deep-negative 3D state, completed weekly stock histogram negative but easing, and SPY below its 200-session moving average. It is not an accepted market-regime-transition detector.

| 21-session construction | Event-weighted positive rate | Equal-date positive rate | Equal-spell positive rate | Observations | Dates | Stress spells |
|---|---:|---:|---:|---:|---:|---:|
| Price-MACD cross | 75.79% | 70.06% | 81.97% | 636 | 123 | 12 |
| Price context without a cross | 72.47% | 66.95% | 79.25% | 5,224 | 216 | 16 |
| RSI-MACD cross | 65.34% | 69.76% | 75.85% | 1,027 | 151 | 13 |
| RSI context without a cross | 69.91% | 65.91% | 73.89% | 6,401 | 219 | 15 |

These weightings estimate different quantities; none is a universally correct replacement. Equal-date weighting gives each represented date equal weight after averaging stocks on that date. Equal-spell weighting averages each represented spell's event mean. Tiny spells can consequently receive disproportionate weight. Dates and populations are not identical across families, so 70.06% versus 69.76% is not itself a paired price-versus-RSI estimate.

Nevertheless, the headline price/RSI gap and even the direction of the RSI cross-versus-context comparison depend on the aggregation. This is a Simpson-like composition warning, not proof of a causal reversal. A basket of simultaneous rebounds must not be mistaken for many independent regime confirmations.

### Same-date cross versus non-cross within each family

Restrict to dates on which that family's repair context has both crossing and non-crossing stocks; average the within-date cross-minus-noncross difference equally across those dates.

| Comparison | Shared dates | Difference in positive rate | Difference in mean return |
|---|---:|---:|---:|
| Price, 21 sessions | 122 | +4.06 pp | -0.046 pp |
| Price, 63 sessions | 122 | +0.80 pp | +0.056 pp |
| RSI, 21 sessions | 151 | +3.11 pp | +0.406 pp |
| RSI, 63 sessions | 151 | +1.38 pp | +0.550 pp |

The pooled RSI 21-session comparison is -4.58 pp in positive frequency, but the same-date comparison is +3.11 pp. The pooled mean-return disadvantage also becomes a positive same-date point estimate. This controls shared-date benchmark movement, not all stock-selection, sector, liquidity or risk differences. It is descriptive support for date-composition confounding, not a validated selection policy.

## 4. Higher win frequency did not establish incremental expected return

For price repair at 21 sessions, crossing observations average 6.05% gross return, 2.10% SPY excess and 1.57% trailing-beta-adjusted excess. Non-cross context observations average 6.11%, 2.17% and 1.72%, respectively. The mean trailing beta is about 1.110 in both groups, but cross observations have shallower prior 63-session drawdowns (-20.73% versus -24.13%). A beta residual is not causal alpha, and equal average beta does not establish equal dynamic rebound exposure.

For 63-session price repair, the cross positive rate is 72.80% versus 73.49% for non-cross context; gross means are 8.58% versus 9.67%. A crossover that improves a short-horizon sign statistic need not improve payoff size or longer-horizon selection.

Joint calendar-year-cluster bootstrap, 5,000 draws over 2010–2025, gives the following exploratory cross-minus-context estimates:

| Outcome | Point difference | Descriptive 95% interval |
|---|---:|---:|
| Price, 21-session positive frequency | +3.31 pp | [+0.38, +6.21] pp |
| Price, 21-session mean return | -0.063 pp | [-0.817, +0.544] pp |
| Price, 63-session positive frequency | -0.69 pp | [-5.09, +4.39] pp |
| RSI, 21-session positive frequency | -4.58 pp | [-11.98, +1.79] pp |
| RSI, 21-session mean return | -1.513 pp | [-3.344, +0.068] pp |

The first interval differs from the original study's other exploratory bootstrap, which included zero. Dependence scheme, selected context and research looks matter. None of these intervals is a multiplicity-adjusted confirmation or permission to publish a calibrated probability. The positive-frequency evidence is more favorable than the incremental-payoff evidence; both must be reported.

## 5. The repair result survives removing 2020, but is not stable across years

Price repair crosses in 2020: 148 observations, 88.51% positive, 11.86% mean gross return. Removing 2020 leaves 488 observations, 71.93% positive, 4.29% mean return and 1.12% SPY excess. Therefore the selected result is not solely a 2020 artifact, but 2020 materially lifts its headline.

Examples of adverse/less favorable periods must remain visible: 2018 price repair had only 18 observations, 27.78% positive and -4.93% mean return; 2015 had 54 observations, 68.52% positive but only 0.71% mean gross return and -2.67% SPY excess. These small, selected cells cannot train a regime classifier, but they falsify a universal-return interpretation of the rule.

Across leave-one-year-out price estimates, positive frequency ranges 71.93%–77.82%; leave-one-spell-out estimates range 71.93%–77.62%. Individual bad years and structural failure modes are not erased by that aggregate stability. The corresponding RSI leave-one-year range is 63.95%–67.42%.

## 6. Mechanism-backed next hypothesis, not another winning-cell search

Dai, Medhat, Novy-Marx and Rizova, *Reversals and the Returns to Liquidity Provision* (Financial Analysts Journal 80(2), 2024; NBER w30917), find that reversal strength and duration vary differently with stock volatility and turnover. Daniel and Moskowitz, *Momentum Crashes* (Journal of Financial Economics 122(2), 2016; NBER w20439), connect prior-loser rebounds with panic states following declines and high volatility. These primary sources motivate competing explanations; neither establishes what causes Mastermind's result.

The next mechanism test should distinguish fast volatility-linked repair, more persistent low-turnover reversal, and broad-market rebound exposure. Turnover, sector and reliable point-in-time opportunity/risk matching are not supplied by this close-only diagnostic. Their data and definitions need owner-qualified admission before tests are run. Do not optimize their thresholds on this exposed panel.

Elliott-style nesting remains a hypothesis language. No real-time wave-count classifier, pivot-recognition test or Elliott-specific outcome result was produced here. Generic causal swing structure should be the baseline before Elliott constraints are credited with incremental information.

## Evidence custody and unresolved gates

Local evidence root: `/Volumes/Mastermind/Mastermind/artifacts/macd-context-first-look-20260915-c3/cycle_extension_v2/`.

- Expanded replay: `results_run_20260915_r1/receipt.json`; script `run_extension.py`, SHA256 `4ab075bf730b780e51d904f4f7301a964b259c6c3614d1033765f4e6d289a803`; process 92932 completed exit 0. This report inspected its 2D/3D deep-negative 21/63 aggregate rows.
- Original-context attribution: `repair_attribution_20260915_r1/receipt.json`; script `run_repair_attribution.py`, SHA256 `acd8ce6bbb47011dc4ebc2a51b0d10dc495ecf4e6b41dc2ca62e87949708223b`; process 24707 completed exit 0; original context input SHA256 `1c284e1a50bd922905333be65cb40ccb07d01d551d1c1886fe9ca60892901d07`.
- Original reproduction script remains `6354a5ab3b5276b1ccd74ce173cadce055364634ad5f80a38ab8e5bca8f9968d`. Input and output hashes are in both receipts. Raw licensed/source price data remains on the host; this repository publication is research evidence and continuity, not a production implementation.

A combined expanded-table inspection for common-252-follow-up horizon curves, opposite-cross exits and common-price-depth comparisons was blocked by the platform after the replay completed. Those tables exist but were not interpreted. The action was not retried, re-encoded, relocated or routed through another carrier. The subsequent original-context attribution was an independently declared lane over original inputs and did not read those blocked tables. Clearing that gate is required before interpreting them; do not rerun the full replay merely to recreate existing artifacts.

Canonical TrialLedger reconciliation is still outstanding for the original and expanded exposed looks. This protocol is not an accepted preregistration. The current-universe/survivorship exposure, retrospectively adjusted prices, close-only fills/path extrema, overlapping events, different signal populations and lack of opportunity-matched executable policies remain material limitations. No signal, rank, availability, size, trade or hero-indicator probability was modified or promoted.

Next scientific action: reconcile the full exposed-look family and source/code custody with Evaluation OS/TrialLedger, clear the specific table-inspection gate, and independently review the existing common-cohort horizon/exit evidence. Only then commission a frozen, owner-native opportunity-matched early/confirmed policy and mechanism test. Keep the existing price and RSI constructions as separate challengers; do not select per-name winners or replace the incumbent from these descriptive tables.
