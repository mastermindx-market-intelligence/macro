# Rates Direction & Shock Intelligence

## 0. Outcome and acceptance

Chairman Chris assigned Sol end-to-end ownership in the September 24, 2026 conversation about anticipating Treasury rate changes. The user job is to assess the short/medium-term direction, uncertainty and discontinuous-move risk of rates before they impair equity decisions. This extends WS:RATES-INFLATION-COMMAND, not a new lifecycle or parallel product.

Success is a real current-source input -> qualified forecast/context -> existing Rates & Inflation / machine consumer -> immutable forecast -> matured evaluation path. A research report, passing tests, merged code or an attractive historical case is not parent completion. Rank/size/gate/trade authority stays false unless separately admitted and empirically accepted.

Operation: `rates-direction-20260924-sol-001`.
Procedure: Mastermind `294b4c00ed668b497edb834be8108f14bc1bee8a`, Skillpack 1.0.1/bootstrap 1.
Initial Macro source: `19ba4a8f3147b487f78894d7090bd7e36080d9e4`.
Source carrier: `claude/rates-direction-20260924-sol-001` on the original Studio.
Direct principal reason: PRINCIPAL_JUDGMENT for experiment design; LOWER_TOTAL_OVERHEAD for the bounded executable research slice. No external worker has been started.

## 1. Scientific thesis, not an accepted signal

The hypothesis is that the combination of real-rate pressure, macro surprise momentum, policy-curve repricing and asymmetric news response improves rates forecasts and identifies upside/downside jump vulnerability. September 23 is a known motivating case, not a blind test. Earlier conversational confidence and scenario weights are not measured skill.

Nominal yield minus a maturity-matched TIPS yield is inflation compensation, not pure expected inflation. TIPS real yields also contain term/liquidity premia. Expected short-rate path plus term premium is an alternative decomposition; adding all these channels would double-count. Curve shape alone cannot establish causality.

Separate five jobs: descriptive state; forecast distribution; conditional event scenarios; ex-post explanatory attribution; equity transmission. Never launder one into another. Current-source freshness is distinct from historical publication/receipt qualification.

## 2. Product contract

For 2Y/5Y/10Y/30Y, target 1/5/20/63 verified Treasury sessions eventually. Each tenor/horizon gets a yield-change distribution in basis points, up/flat/down probabilities, jump-up/jump-down probability, uncertainty, as-of and availability clocks, feature coverage, counterevidence, catalysts and conditions that would change the assessment. Unknown/stale inputs cause explicit abstention, not a neutral forecast.

First research implementation uses the existing DGS10 observed-date grid. It labels horizons as source-observation intervals, NOT certified trading sessions. Missing other series never compress the grid. No filling across source gaps. Historical cache runs are corrected-history diagnostics, not point-in-time certification or a live directional call.

## 3. Existing owners and collision boundaries

- Source rows, aliases and receipts: existing FRED/lib.store/inputs owners; no new collector or archive.
- Observed yield context: engine/yield_momentum.py; #7877 owns holiday refinement.
- Policy expectations: #7521; prospective real-rate qualification: #7593. Consume only after their own acceptance.
- Synthesis/publication: existing rates_inflation_command + build_rates_command; no parallel Forward Path.
- Causal pass-through: existing Transmission; no second rates-to-equity engine.
- Trials and statistics: existing TrialLedger and engine.validation. No second evaluation or trial store.
- Organizational continuity: existing Agent OS WS:RATES-INFLATION-COMMAND. Executive owns any actual execution.

Leave #7418/#7400 entry-conditioned research, #7320 auction repair, Mastermind #769, Tactical #7274, and previously completed A/B/C studies unchanged. Preserve DNR:KILL-POLICY-TIMING-PREDICTOR and DNR:KILL-CALENDAR-GATED-RISK. Calendar proximity cannot become portfolio conviction or risk gating.

## 4. Ordered delivery

RD1: preregister a small yield-only benchmark/challenger experiment; executable purged chronological fit/calibration/test, honest coverage and a machine-readable research report. No production forecasts.
RD2: obtain independently qualified PIT inputs/vintages/consensus/market-implied paths through existing owners; replay event-time surprises without lookahead; preserve every failed candidate.
RD3: independently review methodology and reproduce untouched retrospective results. Compare a single predeclared primary endpoint and corrected secondary tests, not the best-looking cell.
RD4: integrate experimental probabilities and observed context into the existing RIC consumer under explicit evidence tier; begin immutable prospective shadow accrual through existing publication/evaluation.
RD5: validate forward calibration, false alarms, regime stability, operational freshness and correction invalidation; production browser proof in dark/light, EN/ZH, desktop/mobile.
RD6: adjudicate any promotion separately. The default remains useful context and experimental forecasts without trade authority.

## 5. RD1 frozen experiment

Machine specification: research/rates_direction/prereg_v1.json. Freeze before reading target outcomes. Primary: 10Y change over five source-observation intervals. Secondary: 2Y/5Y/30Y and 1/20 intervals; all 12 tenor-horizon cells and all four models count in the existing TrialLedger. Models: no-change, trailing-five-interval momentum scaled by horizon, fixed-penalty curve-only ridge, and the same ridge augmented with real-rate/breakeven features. The ablation identifies whether real-rate decomposition adds anything beyond curve information. No model or hyperparameter rescue after outcomes.

Daily feature dates cannot exceed the forecast origin. Fits only use labels that matured before the calibration block. Calibration uses a later disjoint historical block whose labels matured strictly before the forecast origin. Standardization is fit-only. No random CV or full-sample normalization. Probabilities and 80% intervals use held-back residuals scaled by contemporaneous trailing volatility, never fitted residuals. They are experimental distributions, not guaranteed coverage or conformal certificates.

Up/flat/down uses a fixed +/-1 bp deadband. Jump means absolute change greater than max(10 bp, two trailing daily standard deviations times sqrt(horizon)); both the threshold and volatility are frozen at origin. Direction and jump are scored separately. Actual source date gaps, missingness, exclusions, training/calibration cutoffs and sample counts remain visible.

Primary metric: paired squared-error improvement of ridge over no-change, with HAC uncertainty, on the common eligible panel. Also compare momentum. Secondary: MAE, 80% coverage/width, up/down Brier and log loss, jump Brier, false-alert fraction/recall at a preregistered 0.50 jump-probability threshold. Report all periods/cells; never call overlapping dates independent episodes. Count a greedy non-overlapping subset separately. Backtests give no transaction-cost-adjusted trading evidence because these are yield forecasts, not an executable instrument strategy.

Retrospective partitions: development-era diagnostic 2010-2020 and sealed primary assessment 2021-2025. The latter is algorithmically held out, not untouched by all prior company research. 2026 through the commissioning date is motivating-case audit only. True prospective evidence starts only after the accepted live forecast generation is frozen. No retrospectively written forecast can advance that evidence clock.

A supportive retrospective result earns independent replication and prospective shadow, not promotion. Practical hurdle proposed before outcomes: >=5% common-panel MSE reduction versus BOTH baselines, positive improvement across at least three of five primary years, HAC lower 95% bound >0, reasonable interval calibration, no catastrophic regime failure. Independent statistical review must adjudicate effective sample size, selection history and secondary multiplicity before any broader claim. Failure retains diagnostic value but rejects this exact construction as an advantage.

## 6. Later high-value hypotheses (not evaluated by RD1)

Macro surprises need archived consensus, release timestamp, first vintage, revision chain and event-window quotes. Policy-path gap compares compatible meeting/year-end horizons and does not treat SEP dots as forecasts. News-response asymmetry needs predeclared event classes and asymmetric surprise regression, not selectively chosen oil days. Treasury supply uses auction-time when-issued yields for tails; absent WI means tail unknown. CFTC data use publication availability, not Tuesday position dates, and net shorts do not imply outright duration views because basis trades/hedges matter.

Positioning and volatility may improve tail risk without improving direction. Global rates, dollar, oil, supply, liquidity and real-growth inputs must compete incrementally after the benchmark. Equity dispersion/credit spreads are cross-asset evidence, not proof of Treasury causation. No vendor spend or new licensed-data purchase is authorized by this charter.

## 7. Correction, falsification and operations

Preserve observation, publisher availability, ingestion and decision clocks separately. A changed vintage or schema invalidates dependent assessments without erasing old predictions. Cross-maturity asynchronous closes or unqualified real-rate data cannot produce a precise decomposition. Source-content hashes prove identity, not historical knowledge or vendor authenticity.

Falsifiers: challengers fail baselines out of sample; apparent skill disappears with correct availability; improvement is one regime/cell only; probability calibration or false alarms are poor; future-row mutation changes past predictions; missing sources create false certainty; a real consumer cannot reproduce the report from its declared source generation.

Forecasting cannot make an unscheduled policy/geopolitical surprise knowable. The system should recognize vulnerability and uncertainty, not claim advance knowledge of an unreleased statistic.

## 8. Continuation and completion boundary

Preserve the original Studio worktree/branch. Source-only work is independent of review/production gates, but no held sibling is released by this program. No runtime, watcher, background worker or live publication is implied by this charter. Update the cumulative Agent OS handoff after material effects. The exact next action is RD1 implementation and synthetic no-lookahead tests, followed by lawful trial registration before real target evaluation.
