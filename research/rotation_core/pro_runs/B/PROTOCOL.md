# PRO-RUN B — frozen protocol v1

## Pre-specified rules (10 trials; no outcome has been calculated)

Notation: M is the French value-weighted market total-return index; C and D are the cyclical/growth and defensive sleeves defined below; P denotes a gross cumulative total-return index. SMA(n) includes the current close and requires n valid sessions. A positive signal means the stated condition is strictly true; equality selects the other state. Rules are evaluated every session. There is no optimization, parameter selection or threshold revision after outcomes. Cost stress changes costs, not positions, and is not another allocation rule.

| ID | Exact daily decision at close t |
|---|---|
| R1 Trend | Hold M if P_M(t) > SMA200(P_M)(t); otherwise bills. |
| R2 Credit | Hold bills if the latest eligible monthly BAA10YM is above the arithmetic mean of its preceding 12 monthly observations; otherwise M. |
| R3 Unemployment | Let U3 be the three-month mean of UNRATE. Hold bills if U3 minus the minimum U3 over the current and preceding 11 months is at least 0.50 percentage point; otherwise M. |
| R4 Confluence | Count R1's bearish trend, R2's credit stress and R3's unemployment stress. Hold bills if at least two are true; otherwise M. Require all three available; never substitute a benign vote for missing data. |
| R5 Relative momentum | Hold C if P_C(t)/P_C(t-126) > P_D(t)/P_D(t-126); otherwise D. |
| R6 Confluence rotation | Hold D when R4 says bills; otherwise C. Require all three R4 inputs available. |
| R7 Breadth divergence | Start in C. Switch C to D when C's 63-session return is positive, fewer than 50% of eligible C industries are above their own SMA200, and that fraction is at least 20 percentage points below its maximum over the current and prior 62 sessions. Stay in D until more than 60% are above SMA200 AND P_C > SMA200(P_C), then switch to C. No other exit/re-entry/reset. |
| R8 Washout confirmation | Start in C. Switch to D when P_C < SMA200(P_C). During each D spell set a washout flag once at most 20% of eligible C industries are above SMA50. Re-enter C only after that flag is set, more than 50% are above SMA50, and P_C > SMA50(P_C). Reset the flag at re-entry. The flag has no time expiry; prolonged defensive residency is a reportable cost, not a reason to change the rule. |
| R9 Nominal-rate rotation | Hold D when the latest eligible Shiller long nominal yield is above the arithmetic mean of its preceding 12 monthly observations; otherwise C. |
| R10 Real-rate plus credit | Define backward-looking real yield as Shiller long nominal yield minus 100*(CPI/CPI_12months_ago - 1). Hold D only when this real-yield proxy exceeds the median of its preceding 36 monthly observations AND the R2 credit-stress condition is true; otherwise C. |

These are return-allocation hypotheses, not tests of actual capital flows. C is a sector-economic proxy, not a fitted high-beta or valuation-growth universe.

## Fixed sleeves and data eligibility

D labels from French 49 industries: Food, Soda, Beer, Smoke, Hshld, Hlth, MedEq, Drugs, Util.
C labels: Toys, Fun, Clths, Chems, Rubbr, Txtls, BldMt, Cnstr, Steel, FabPr, Mach, ElcEq, Autos, Aero, Ships, BusSv, Hardw, Softw, Chips, LabEq, Trans, Rtail.

Within each sleeve use equal allocations across eligible industry portfolios, each using its French value-weighted return. A member becomes eligible after 200 consecutive nonmissing observed returns, determined at the decision close. New industries are never backfilled. At least 4 D and 10 C members are required; otherwise affected rules are unavailable. All 49 members are used for the broad equal-industry benchmark and breadth diagnostics. Missing sentinels -99.99/-999 become missing, never zero. Unexpected missing returns on an existing holding invalidate the affected calculation. Breadth uses the fraction of eligible C industries above their own SMA(n). Coverage counts are retained.

Gross sleeve indexes use yesterday's eligible industry set, equal weighted each close; they are signal objects. Executable strategies implement individual-industry weights with the delay below, include sleeve rebalancing turnover and costs, and can differ slightly from gross signal indexes. The market and each industry portfolio are synthetic research instruments: turnover within French constituent portfolios is not observed, so charged costs are a lower bound.

Acquire daily French market/size/value factors, daily momentum, daily 12/17/49 industry VW/EW portfolios, and daily size portfolios. Only 49 industries determine candidate rules. The 12/17 portfolios, size and momentum support coverage/factor diagnostics, not additional searched rules. Acquire monthly Shiller long yield/CPI/S&P composite price; FRED BAA, BAA10YM, GS10, TB3MS, UNRATE. Seek a public daily S&P price series for descriptive cross-check only; failure does not replace the market benchmark or invent daily Shiller prices.

No current-vintage revision is described as historically knowable. In the absence of obtainable real-time vintages, monthly credit and nominal yields observed in month m become available on day 1 of month m+2; UNRATE and real yield/CPI become available on day 1 of month m+3. These conservative lags do not remove revision bias. No pre-inception macro substitution. French RF is the bill total return; TB3MS is a yield diagnostic, not a daily bill return.

## Execution, costs, clock and sealed sample

Date range: French observations from 1926-07-01 through 2019-12-31 only. Source bytes may contain newer records, but parsers must inspect the date and discard every later row BEFORE parsing numerical values, computing, selecting, plotting or reporting outcomes. No later sample is used to resolve terminal episodes.

Signal decided at close t is executed at close t+1. Existing holdings earn the return ending t+1; new holdings first earn the return ending t+2. Initial holdings are bills. No forward-fill across unavailable rule inputs. Evaluation begins with the first eligible decision's execution/cost date. Warmup is excluded from scored periods and actual sample starts are reported. Holdings and causal histories continue across era boundaries.

At an execution close, pretrade weights reflect that day's returns. Reset to delayed target weights; charge c*sum(abs(target - pretrade)) over equity holdings only, with bills as the settlement asset. Thus market-to-cash costs c and C-to-D costs 2c (plus internal rebalancing). c=0.0025 before 1975-01-01 and 0.0005 thereafter. Use multiplicative net factor (1+gross_return)*(1-cost_fraction). Report also 2c with identical target paths. Annual turnover is one-way equity notional, the same sum of absolute traded equity weights, divided by calendar years. No leverage/shorting/borrowing/taxes.

CAGR uses elapsed calendar years (365.2425 days, including first sampled day's interval); volatility uses sample daily standard deviation times sqrt(observations/years), acknowledging historical Saturday trading. Max drawdown includes starting wealth 1. Up/down capture is ratio of conditional mean strategy return to conditional mean market return on market-positive/negative sessions, in percent; no conditional CAGR singularities.

## Three references and an explicit data gap

B1: French Mkt-RF + RF, value-weighted total-return market, buy/hold.
B2 requested: actual equal-weighted stock market. No exact public full-history daily series has yet been located. French industry averages and NYSE-breakpoint size-decile averages are not that series. If unavailable, report B2 as NA and show separately labeled E49: equal weighted French49 EW industry returns, with prior-close available members. Do NOT call E49 the equal-weighted stock market; H5's exact claim remains untestable.
B3: causal expanding-exposure market/bills reference. At decision t its market target is the arithmetic mean of the rule's eligible intended equity exposures from inception through t. Apply the same execution delay and cost schedule. Report strategy and B3 average realized equity weights. This is causally matched to past mean exposure, not to an unknowable full-era future average. All-equity C/D rules have B3=M apart from initial implementation.

Use identical scored dates for each paired comparison. B1 and E49 are gross conventional index references; B3 includes its own costs. Passive C, passive D and a fixed daily 50:50 C/D reference are descriptive diagnostics to separate passive defensive exposure from switching skill, not new candidate rules. Report paired excess against that mix for R5-R10. Actual member-stock transaction costs and taxes remain unmeasured.

## Eras, inference, power and H1 comparison

Report 1926-1959, 1960-1989, 1990-2019 separately, plus a descriptive pooled table. Require at least 252 scored observations for an inferential era row; insufficient rows retain NA and the full testing penalty.

For every rule/era show CAGR, volatility, max drawdown, captures, turnover, mean exposure, annual log-growth difference against B1/E49/B3 and pointwise 95% paired block-bootstrap intervals. Also provide CAGR-difference point estimates and intervals in machine-readable tables. Actual B2 excess remains NA if exact stock-EW data are missing.

Primary estimand: annualized mean daily log-return advantage over B3, after base costs. Compute one-sided superiority p-values via a centered paired circular moving-block bootstrap (block length 252 observations; 5,000 resamples; seed 20261111). Use common block draws for comparable rules. Holm correct the fixed 30 hypotheses (10 rules x 3 eras); unavailable tests take p=1. Pointwise intervals are not simultaneous. Pooled results, cost stress, passive mixes, factor diagnostics, H1 pair comparisons and episode panels are descriptive, not extra opportunities to declare significance.

Minimum detectable effect: approximate 80%-power annual log-return advantage at two-sided family-wise 5% Bonferroni/30, (z_(1-.05/(2*30))+z_.80)*bootstrap_SE. Report by rule/era and its range. This is an approximate historical power calculation, not evidence of absence. Blocks preserve some serial dependence, not regimes, revised-data uncertainty or implementation frictions. Do not fit or retune block length to outcomes.

H1: additionally compare R1/R2/R3/R4 on their exact common available dates in each era, reporting pairwise R4-minus-single annual log-return differences/CIs and drawdown. Do not compare a century-long trend result to a short macro result as proof of confluence.

## Frozen episode definitions

Windows: 1929-01-01..1932-12-31; 1937 calendar year; 1962; 1966; 1969-01-01..1970-12-31; 1973-01-01..1974-12-31; 1980-01-01..1982-12-31; 1987; 1990; 2000-01-01..2002-12-31; 2007-01-01..2009-12-31; 2018-07-01..2018-12-31.

In each window use B1's maximum peak-to-trough drawdown pair (first occurrence for ties); retrospective episode anchors are descriptive, never signal inputs. Exit = first executed risk-off transition after peak and on/before trough (bills for R1-R4; D for R5-R10). If already off at peak report PRE and the last transition's signed session offset; if never off before trough report NONE. Re-entry = first executed risk-on state after trough within 252 further observed sessions; ON if already risk-on at trough, NONE if absent, NA for unavailable rules. No terminal-date extrapolation.

Drawdown avoided = B1's maximum drawdown minus the rule's maximum drawdown, both expressed as positive loss magnitudes, over the peak-close to trough-close path (positive is protection). Upside missed = B1 cumulative return minus strategy cumulative return over the next 252 sessions after trough, truncated at 2019-12-31 and marked when truncated; negative is outperformance. This is a fixed recovery-window comparison, not just gains until re-entry.

A calm year is a calendar year outside all listed episode years with B1 maximum drawdown under 10%. False pivot = an executed on-to-off transition during a calm year; report counts per eligible calm year per rule/era. It is a mechanical whipsaw proxy, not hindsight proof every such decision was irrational.

For H2/H4 report C and D cumulative returns and D-minus-C percentage points peak-to-trough and during recovery; nominal yield, backward-looking real-yield proxy, credit condition and data availability at peak/trough. For each eligible executed on-to-off transition near an episode, report D-minus-C over prior63 and subsequent63 sessions when wholly available. A signal that follows an already positive relative move is a follower by that explicit descriptive definition; a nonpositive prior move followed by positive future move is an anticipator. A signal based on relative momentum is inherently partly reactive. Rates-condition future63 diagnostics remain descriptive and overlapping, with no causal/significance claim.

## Integrity, authority and delivery

Protected procedure: Mastermind master c42e812e4a754d7a95efd954441d3f01607a7fb5; compatible skillpack 1.0.1/bootstrap1. Macro source base 71405417a0ff9dfc615654deea6ea44a5305f735. Assigned research only; one branch pro-run/rotation-b-20261111, code/small results solely research/rotation_core/pro_runs/B/, one final comment on issue11014 beginning PRO-RUN B, no PR or production effect.

Phase dependencies: freeze/readback -> acquisition/coverage -> implementation and timing/integrity checks -> execute fixed outcomes -> adversarial self-audit -> code/small-table persistence/readback -> one complete issue comment/readback. Original DONE_WHEN is report delivery, not trading acceptance.
Direct execution reason: PRINCIPAL_JUDGMENT/LOWER_TOTAL_OVERHEAD for the tightly coupled empirical design, integration and accountable report. One native reasoning adviser critiques design and conclusions; no outside worker, host or paid runtime is commissioned. WHY NOT FABLE: no cross-system implementation/admission work; the current explicitly commissioned research session owns the study.

Freeze must be committed before the first outcome run. Bugs violating this protocol may be repaired and disclosed; changed allocation definitions after outcomes count as additional trials and require an explicit amendment. Every limitation, including true EW absence, vintages, retrospective industry construction, missing early members, historical trading feasibility, unrecoverable source revisions, only three eras, and episode selection, must be in the final report. A negative or untestable verdict is acceptable. Second-protocol candidates are recommendations based on this research, never validated trade instructions.

