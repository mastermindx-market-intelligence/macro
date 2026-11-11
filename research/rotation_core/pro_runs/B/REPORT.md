PRO-RUN B

## 1. Pre-specified rules (10 trials; no outcome has been calculated)

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



### Fixed definitions and implementation

**D:** Food, Soda, Beer, Smoke, Hshld, Hlth, MedEq, Drugs, Util. **C:** Toys, Fun, Clths, Chems, Rubbr, Txtls, BldMt, Cnstr, Steel, FabPr, Mach, ElcEq, Autos, Aero, Ships, BusSv, Hardw, Softw, Chips, LabEq, Trans, Rtail. These are fixed French49 economic groups, not estimated high-beta or valuation-growth stocks. Each sleeve equally allocates across eligible value-weighted industry portfolios. Members require 200 consecutive nonmissing returns, with at least 10 C and 4 D members. No backfill of later industries. Industry breadth is the fraction of eligible C industries above their own stated moving average.

Signals use gross total-return sleeve indexes. Decisions at close t execute at close t+1; new holdings first earn the return ending t+2. Existing holdings earn t+1, and that close incurs the fee. Initial holdings are bills. Costs are 25 bp per traded equity side before 1975, 5 bp thereafter; market-to-bills is one sale, C-to-D is two sides. Daily sleeve rebalancing and drift are charged. Fees multiply gross wealth by (1−cost). Stress doubles fees on identical allocations. Costs inside the published French portfolios are unobserved and omitted.

Macro observation month m is available on day1 of m+2 for credit/nominal yields and m+3 for unemployment/real yield. These are current-vintage conservative-lag simulations, not reconstructed real-time decisions. Credit/confluence do not exist before their inputs. Cash earns French RF; TB3MS is a yield diagnostic. No leverage or shorts.

**Three requested references:** (B1) French cap-weighted market total return; (B2) true equal-weighted stock market; (B3) a causal expanding-mean equity-exposure market/bills portfolio, traded with the same delay and fees. B3's target at t is the rule's mean intended equity allocation through t. It uses no future era average; its realized average exposure need not equal the strategy's ex-post average. Exact B2 is unavailable. A separate **E49 proxy** averages French49 equal-weighted industry returns with previous-close membership; it is not equal weight across stocks. B1/E49 are gross index references; B3 is costed. Passive C, D and a daily 50:50 C/D mix are additional fixed descriptive controls.

CAGR uses calendar time; volatility uses observed sessions/year, allowing historical Saturday sessions. Drawdown includes initial wealth. Up/down capture is the ratio of conditional mean daily strategy and market returns on positive/negative market sessions. Turnover is annual **gross equity traded notional**, not halved turnover.


**Freeze/provenance:** [original ten-rule protocol](https://github.com/mastermindx-market-intelligence/macro/blob/ba5ae1e353c6f9738bbf8936b9032e71c747b9ba/research/rotation_core/pro_runs/B/PROTOCOL.md), [pre-outcome clarifications](https://github.com/mastermindx-market-intelligence/macro/blob/da384adb882181ecd33d3a0802f8c2d22f53d1d9/research/rotation_core/pro_runs/B/CLARIFICATIONS.md), and [missing-data treatment](https://github.com/mastermindx-market-intelligence/macro/blob/85f299a57d3f36fad9994a69d84853e3f07a5604/research/rotation_core/pro_runs/B/MISSING_DATA.md). No allocation definition or threshold changed after outcomes; **10 trials**. Transport fixes, missing-data identifiability and reporting corrections are recorded in [the audit](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/RESEARCH_AUDIT.md).

## 2. Verdict and what this history establishes

**No tested rule demonstrates a robust excess-return edge under this protocol.** Of 30 prespecified rule/era slots, 21 have fully identified returns from their eligible starts and nine have unidentified intervals. No primary test passes Holm30; the smallest raw one-sided superiority p among the identified rows is **0.0728**. All adjusted p-values are 1.000. This is not evidence that all economically relevant effects are zero: the study's power is weak for small edges.

The descriptive seesaw is visible. Defensives beat C in **10 of 11 identifiable declines**; C beats D in **all 10 identifiable fixed recovery windows**. But the signals usually reacted after part of the relative move, and delay, whipsaws and missed rebounds consumed the apparent opportunity. In 1990–2019 every active rotation rule's interval against the static C/D mix includes zero. The passive D sleeve delivered 11.80% CAGR, C 10.86%, and the mix 11.55%; active R5–R10 ranged from 9.72% to 11.75%. Those fixed controls make it difficult to call passive defensive resilience rotation skill.

**The requested complete nine-decade experiment is not fully identifiable from these public files.** French49 contains missing returns after industries became eligible. The official TXT counterpart confirms the CSV holes. No zero imputation, dropped loss dates, substitute industries, or favorable data vintage was used. Unknown returns invalidate full-era paths. Exact later target rebalancing can restore known normalized weights; R7/R8 recover only when their feasible states synchronize. Nine affected full-era rows below are NA, with separate descriptive clean segments. Early macro rows cover only their stated dates, not the entire first era.

The sealed sample was excluded: every analysis date is on or before **2019-12-31**, and later raw records are discarded before numerical return parsing. No later outcome is used for a terminal episode or recommendation.


## 3. Results by rule and era

All return, volatility, drawdown, exposure and capture figures below are percentages. **Δ** is a CAGR difference in percentage points/year, followed by a **pointwise 95% paired block-bootstrap interval**. Exact stock-EW excess is **NA in every row**; E49 is shown only as an explicitly different proxy. Missing benchmark observations also yield NA rather than a selected-date contrast.

`Eq` is mean realized strategy equity exposure. `B3eq` is its causal reference's mean realized exposure. `Turn` is gross equity notional traded/year. `2×` is CAGR at doubled fees. `False/calm` is mechanically defined on-to-off transitions per complete eligible calm year in the named era; it is not a claim that every such transition lost money.

`MDE80` is the approximate 80%-power detectable **annual log-return advantage**, in percentage points, using a two-sided Bonferroni/30 5% threshold. It differs from the CAGR units of Δ. Holm30 uses the frozen one-sided B3 annual log-growth superiority estimand. Partial paths take p=1 and have no full-era estimate.


### 1926-1959

|Rule|Scored dates|CAGR|Vol|Worst DD|Up/Down|Eq|Turn|2×|False/calm|
|---|---|---|---|---|---|---|---|---|---|
|R1|1927-03-04..1959-12-31|9.95|13.22|-43.51|57.96/53.88|69.26|5.76|8.37|2.30|
|R2|1954-06-02..1959-12-31|13.18|8.25|-10.35|61.12/56.51|58.17|1.61|12.72|0.75|
|R3|1949-05-03..1959-12-31|8.36|8.37|-20.65|63.98/70.02|66.33|0.47|8.24|0.29|
|R4|1954-06-02..1959-12-31|11.56|8.77|-13.45|69.15/69.70|70.17|2.33|10.91|1.00|
|R5|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|2.22|
|R6|1954-06-02..1959-12-31|20.88|9.78|-19.12|87.42/78.73|99.93|6.01|19.07|1.00|
|R7|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|0.25|
|R8|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|1.12|
|R9|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|0.33|
|R10|1954-06-02..1959-12-31|19.34|10.65|-21.88|95.19/91.05|99.93|2.49|18.60|0.25|

|Rule|Δ cap M [95% CI]|Δ E49 proxy [95% CI]|Δ B3 [95% CI]|B3eq|Holm p|MDE80|
|---|---|---|---|---|---|---|
|R1|0.72 [-5.71, 7.63]|NA|3.39 [-0.97, 7.83]|66.36|1.000|8.38|
|R2|-4.44 [-12.84, 2.96]|-9.69 [-23.22, 1.52]|5.09 [-1.67, 12.26]|52.91|1.000|12.43|
|R3|-10.56 [-19.52, -3.40]|-13.59 [-25.07, -4.09]|-1.09 [-8.01, 5.28]|53.00|1.000|12.22|
|R4|-6.06 [-13.34, -0.47]|-11.31 [-23.92, -1.27]|2.74 [-3.59, 9.93]|62.19|1.000|12.40|
|R5|NA|NA|NA|NA|1.000|NA|
|R6|3.26 [-1.96, 9.33]|-1.99 [-6.97, 2.70]|3.28 [-1.94, 9.34]|99.93|1.000|9.84|
|R7|NA|NA|NA|NA|1.000|NA|
|R8|NA|NA|NA|NA|1.000|NA|
|R9|NA|NA|NA|NA|1.000|NA|
|R10|1.72 [-2.26, 6.18]|-3.53 [-7.67, -0.08]|1.74 [-2.24, 6.19]|99.93|1.000|7.01|


### 1960-1989

|Rule|Scored dates|CAGR|Vol|Worst DD|Up/Down|Eq|Turn|2×|False/calm|
|---|---|---|---|---|---|---|---|---|---|
|R1|1960-01-04..1989-12-29|10.62|9.48|-29.44|64.58/59.04|71.44|4.74|9.89|1.57|
|R2|1960-01-04..1989-12-29|4.76|9.20|-33.11|49.64/49.96|53.31|1.70|4.48|0.71|
|R3|1960-01-04..1989-12-29|5.32|11.23|-51.92|71.80/74.57|75.94|0.40|5.25|0.07|
|R4|1960-01-04..1989-12-29|7.16|10.27|-33.11|66.22/65.62|73.21|2.13|6.83|0.64|
|R5|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|3.36|
|R6|1960-01-04..1989-12-29|9.60|14.34|-62.23|104.65/106.00|100.00|5.57|8.69|0.64|
|R7|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|0.79|
|R8|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|1.15|
|R9|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|0.71|
|R10|NA: data gaps|NA|NA|NA|NA/NA|NA|NA|NA|0.43|

|Rule|Δ cap M [95% CI]|Δ E49 proxy [95% CI]|Δ B3 [95% CI]|B3eq|Holm p|MDE80|
|---|---|---|---|---|---|---|
|R1|0.33 [-3.06, 4.22]|NA|1.46 [-1.33, 4.38]|69.35|1.000|5.19|
|R2|-5.53 [-10.13, -0.99]|NA|-3.88 [-6.59, -1.21]|56.90|1.000|5.15|
|R3|-4.97 [-8.99, -1.52]|NA|-3.86 [-7.27, -0.68]|71.19|1.000|6.35|
|R4|-3.13 [-7.28, 0.70]|NA|-1.96 [-4.96, 0.85]|70.97|1.000|5.48|
|R5|NA|NA|NA|NA|1.000|NA|
|R6|-0.69 [-3.38, 2.22]|NA|-0.69 [-3.38, 2.22]|100.00|1.000|5.25|
|R7|NA|NA|NA|NA|1.000|NA|
|R8|NA|NA|NA|NA|1.000|NA|
|R9|NA|NA|NA|NA|1.000|NA|
|R10|NA|NA|NA|NA|1.000|NA|


### 1990-2019

|Rule|Scored dates|CAGR|Vol|Worst DD|Up/Down|Eq|Turn|2×|False/calm|
|---|---|---|---|---|---|---|---|---|---|
|R1|1990-01-02..2019-12-31|8.25|11.42|-23.38|62.46/60.59|76.27|6.53|7.90|2.07|
|R2|1990-01-02..2019-12-31|7.52|10.41|-27.85|46.33/43.33|52.75|1.17|7.45|0.50|
|R3|1990-01-02..2019-12-31|10.00|13.55|-35.11|74.36/71.87|80.30|0.27|9.99|0.07|
|R4|1990-01-02..2019-12-31|9.02|11.96|-23.13|65.05/62.63|76.84|3.47|8.83|0.36|
|R5|1990-01-02..2019-12-31|9.81|15.69|-51.07|85.33/84.10|100.00|19.84|8.72|4.71|
|R6|1990-01-02..2019-12-31|9.72|16.25|-46.61|91.64/91.14|100.00|8.42|9.25|0.36|
|R7|1990-01-02..2019-12-31|10.15|17.18|-46.38|95.92/95.32|100.00|5.91|9.82|0.79|
|R8|1990-01-02..2019-12-31|9.75|15.35|-48.93|82.31/80.74|100.00|9.67|9.22|1.43|
|R9|1990-01-02..2019-12-31|11.75|18.32|-63.11|96.27/94.02|100.00|4.61|11.49|0.86|
|R10|1990-01-02..2019-12-31|9.72|18.37|-58.21|101.35/101.65|100.00|3.83|9.51|0.57|

|Rule|Δ cap M [95% CI]|Δ E49 proxy [95% CI]|Δ B3 [95% CI]|B3eq|Holm p|MDE80|
|---|---|---|---|---|---|---|
|R1|-1.83 [-5.60, 2.66]|-13.82 [-21.35, -6.89]|0.07 [-2.73, 3.19]|71.11|1.000|5.65|
|R2|-2.57 [-7.36, 2.65]|-14.56 [-23.35, -6.24]|0.55 [-2.79, 3.93]|53.54|1.000|6.35|
|R3|-0.08 [-4.12, 4.44]|-12.07 [-21.35, -3.51]|1.67 [-1.54, 5.07]|73.88|1.000|6.11|
|R4|-1.06 [-5.43, 3.79]|-13.05 [-21.16, -5.65]|0.70 [-2.69, 4.46]|73.33|1.000|6.74|
|R5|-0.27 [-3.69, 3.49]|-12.26 [-18.98, -6.35]|-0.27 [-3.69, 3.49]|100.00|1.000|6.65|
|R6|-0.37 [-3.68, 3.42]|-12.36 [-18.99, -6.59]|-0.37 [-3.68, 3.42]|100.00|1.000|6.49|
|R7|0.06 [-3.15, 3.44]|-11.93 [-18.49, -6.09]|0.06 [-3.15, 3.44]|100.00|1.000|6.09|
|R8|-0.33 [-4.87, 3.99]|-12.32 [-19.90, -5.97]|-0.33 [-4.87, 3.99]|100.00|1.000|8.06|
|R9|1.67 [-2.10, 5.14]|-10.32 [-16.96, -4.11]|1.67 [-2.10, 5.14]|100.00|1.000|6.58|
|R10|-0.36 [-2.99, 2.14]|-12.36 [-19.84, -5.50]|-0.36 [-2.99, 2.14]|100.00|1.000|4.82|


### Descriptive clean segments for the nine incomplete era paths

These rows **do not replace the missing full-era results**. Before observing outcomes, the longest contiguous identified segment within each affected era was specified; ties choose the earliest. Selection used missingness only. Intervals are descriptive; their full-era primary tests remain unavailable with p=1. Exact dates are essential.
|Rule|Scored dates|CAGR|Vol|Worst DD|Up/Down|Eq|Turn|2×|False/calm|
|---|---|---|---|---|---|---|---|---|---|
|1926-1959 R5|1946-02-26..1959-12-31|12.42|11.00|-31.56|86.75/86.29|100.00|14.46|8.41|2.22|
|1926-1959 R7|1946-05-23..1959-12-31|13.22|11.96|-33.85|97.43/97.07|100.00|3.60|12.20|0.25|
|1926-1959 R8|1946-07-24..1959-12-31|11.26|10.09|-33.85|77.06/76.25|100.00|9.31|8.69|1.12|
|1926-1959 R9|1945-09-15..1959-12-31|12.91|10.68|-37.58|80.33/78.43|100.00|2.43|12.23|0.33|
|1960-1989 R5|1971-09-14..1989-12-29|12.72|15.36|-57.89|102.58/101.50|100.00|8.14|11.58|3.36|
|1960-1989 R7|1971-12-28..1989-12-29|11.69|15.64|-60.29|103.70/104.10|100.00|5.73|11.24|0.79|
|1960-1989 R8|1972-05-23..1989-12-29|10.21|15.21|-58.06|99.61/100.78|100.00|9.63|9.36|1.15|
|1960-1989 R9|1971-03-12..1989-12-29|12.43|14.95|-54.77|101.28/100.17|100.00|4.02|11.96|0.71|
|1960-1989 R10|1971-03-12..1989-12-29|11.34|15.51|-57.07|103.74/104.25|100.00|3.22|10.99|0.43|

|Rule|Δ cap M [95% CI]|Δ E49 proxy [95% CI]|Δ B3 [95% CI]|B3eq|Holm p|MDE80|
|---|---|---|---|---|---|---|
|1926-1959 R5|-1.75 [-5.88, 2.98]|-3.70 [-8.69, 0.96]|-1.75 [-5.88, 2.98]|100.00|1.000|7.92|
|1926-1959 R7|-0.07 [-2.60, 2.86]|-1.83 [-4.07, 0.29]|-0.07 [-2.60, 2.86]|100.00|1.000|4.90|
|1926-1959 R8|-2.88 [-8.00, 2.97]|-4.89 [-9.59, -0.20]|-2.88 [-8.00, 2.97]|100.00|1.000|9.87|
|1926-1959 R9|-1.63 [-5.86, 3.04]|-4.72 [-8.52, -0.67]|-1.63 [-5.86, 3.04]|100.00|1.000|8.03|
|1960-1989 R5|1.07 [-2.42, 5.15]|-5.95 [-13.52, 1.64]|1.07 [-2.42, 5.15]|100.00|1.000|6.89|
|1960-1989 R7|-0.06 [-3.62, 4.10]|-7.50 [-13.03, -2.36]|-0.06 [-3.62, 4.10]|100.00|1.000|7.04|
|1960-1989 R8|-1.18 [-5.38, 3.28]|-8.23 [-16.85, -0.19]|-1.18 [-5.38, 3.28]|100.00|1.000|8.07|
|1960-1989 R9|0.97 [-2.27, 4.39]|-5.53 [-12.30, 0.62]|0.97 [-2.27, 4.39]|100.00|1.000|6.00|
|1960-1989 R10|-0.12 [-3.43, 3.27]|-6.62 [-12.22, -1.67]|-0.12 [-3.43, 3.27]|100.00|1.000|6.14|


### Power, full-history scope and stress

Across the 21 identified primary rows, MDE80 ranges from **4.82 to 12.43 annual log-return percentage points**. Early credit/confluence inference has only about 5.6 years and roughly six 252-session blocks. The longest complete trend span, 1927-03-04..2019-12-31, has 9.61% net CAGR and −43.51% drawdown; its descriptive B3 log-growth advantage is +1.56 pp/year, CI [−0.30,+3.50], with approximate MDE80 3.85 pp/year. That pooled calculation is not an additional primary test or untouched validation set.

Costs matter. R1's first-era CAGR falls from 9.95% to 8.37% when fees double. Recent-era R5 falls from 9.81% to 8.72%, reflecting 19.84 units of annual gross traded notional; passive sleeve constituent costs remain additional unknowns. All other stress values are above and in [results.csv](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/results.csv). No lower-cost variant was selected after inspection.

E49's 1990–2019 gross CAGR is **22.07%**, independently reproduced from its stored daily proxy. That is not a percent-unit or annualization error. It remains an uncosted equal-industry research-return proxy, with small-stock and daily-rebalancing exposure and unmeasured constituent/microstructure effects. These data do not identify which mechanism explains its magnitude. It must not be advertised as an implementable equal-weight market or used to adjudicate exact H5.


## 4. H1: common-sample confluence comparison

The following is descriptive R4-minus-single **annual log-growth** pp/year, with pointwise 95% paired intervals. All four rules use the same dates within each row's era. No additional superiority declaration is made from this panel.
|Era|Common start|Against|R4−single [95% CI]|R4 worst DD|Single worst DD|
|---|---|---|---|---|---|
|1926-1959|1954-06-02|R1|-2.26 [-7.91, 3.20]|-13.45|-17.38|
|1926-1959|1954-06-02|R2|-1.44 [-5.37, 1.13]|-13.45|-10.35|
|1926-1959|1954-06-02|R3|5.33 [-0.56, 12.06]|-13.45|-20.65|
|1960-1989|1960-01-04|R1|-3.17 [-6.59, 0.01]|-33.11|-29.44|
|1960-1989|1960-01-04|R2|2.27 [0.30, 4.54]|-33.11|-33.11|
|1960-1989|1960-01-04|R3|1.73 [-0.85, 4.81]|-33.11|-51.92|
|1990-2019|1990-01-02|R1|0.71 [-1.58, 2.69]|-23.13|-23.38|
|1990-2019|1990-01-02|R2|1.39 [-1.20, 4.18]|-23.13|-27.85|
|1990-2019|1990-01-02|R3|-0.90 [-3.40, 1.77]|-23.13|-35.11|


Confluence does not consistently beat trend: R4−R1 is −2.26, −3.17 and +0.71 log pp/year across the eras. In the recent era it reduces calm-year exits from R1's 2.07/year to 0.36/year, but fewer switches also prolong some defensive spells. That is a tradeoff, not demonstrated superiority.

## 5. Episode anchors and defensive/cyclical behavior (H2/H4)

Anchors are the maximum French-market drawdown pair **inside each predeclared calendar window**, not hand-selected conventional S&P bear-market dates. Consequently, 1962/1969 windows exclude peaks in preceding years, and 1980–82 selects its largest internal decline. They are retrospective scoring anchors, never signal inputs.

Below, C/D returns and D−C are gross sleeve returns. Recovery is the next 252 observed market sessions after the trough. `N/R/K` are the peak-date known nominal-high, backward-real-high, and credit-stress flags (1=true, 0=false, NA=unavailable); derived flags only, with no raw FRED series or vendor price levels published.


|Episode|Peak|Trough|M DD|C decline|D decline|D−C decline|D−C recovery|N/R/K|
|---|---|---|---|---|---|---|---|---|
|1929-32|1929-09-03|1932-07-08|-84.07|NA|-73.82|NA|NA|0/0/NA|
|1937|1937-03-10|1937-11-24|-42.02|-45.95|-29.30|16.66|-12.30|1/1/NA|
|1962|1962-03-15|1962-06-26|-26.38|-29.63|-29.05|0.58|-5.26|1/1/0|
|1966|1966-02-09|1966-10-07|-20.26|-28.54|-18.94|9.60|-29.41|1/1/0|
|1969-70|1969-05-14|1970-05-26|-35.38|-46.13|-25.09|21.04|NA|1/0/0|
|1973-74|1973-01-11|1974-10-03|-48.16|-52.40|-54.62|-2.22|-5.46|1/1/0|
|1980-82|1981-08-11|1982-08-12|-20.17|-23.19|2.08|25.27|-37.44|1/1/1|
|1987|1987-08-25|1987-12-04|-33.11|-38.36|-29.84|8.52|-6.06|1/0/0|
|1990|1990-07-16|1990-10-11|-20.80|-29.16|-13.58|15.57|-3.55|1/0/0|
|2000-02|2000-03-24|2002-10-09|-49.23|-38.80|32.78|71.58|-38.17|1/0/0|
|2007-09|2007-10-09|2009-03-09|-54.57|-63.05|-39.23|23.81|-60.60|0/1/1|
|late2018|2018-09-20|2018-12-24|-20.45|-25.53|-13.27|12.25|-8.48|1/0/1|


The major counterexample is 1973–74: D lost 54.62%, versus C's 52.40%; defensive leadership was absent. D also lost 39.23% during 2007–09 despite its 23.81 pp relative advantage. Relative defense is not capital preservation. The 2000–02 defensive advantage was unusually large (+71.58 pp), and the subsequent C rebound reversed 38.17 pp of relative performance over the fixed recovery. No episode count establishes literal flows of money.

### Every rule in every episode

Exit/entry offsets are **observed market sessions**, not calendar days. `PRE(−n)` means already off at the peak; the last identified exit was n sessions earlier. `ON(−n)` means already risk-on at the trough, potentially from a premature entry; it does not claim bottom recognition. `NONE` means no qualifying pivot within the frozen window; `NA` means the needed inputs/path are unidentified. The last entry or exit can be well outside the named episode. No favorable post-trough entry replaces an earlier ON state.

`Avoided` is market drawdown loss minus strategy drawdown loss on the common peak-close-to-trough-close path; positive is protection. `Missed` is market minus strategy cumulative return over the next 252 sessions; negative is strategy outperformance. Decline and recovery eligibility are evaluated separately. Every available recovery here has 252 sessions inside the cutoff. False pivots/calm-year are in section3 and the complete denominator table below, rather than repeated 12 times per rule.


#### 1929-32

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+41|+25|62.26|97.58|
|R2|NA|NA|NA|NA|
|R3|NA|NA|NA|NA|
|R4|NA|NA|NA|NA|
|R5|PRE(-45)|+25|NA|NA|
|R6|NA|NA|NA|NA|
|R7|+186|+26|NA|NA|
|R8|+40|+8|NA|NA|
|R9|+342|ON(-3)|NA|NA|
|R10|NA|NA|NA|NA|


#### 1937

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+39|+174|24.76|10.43|
|R2|NA|NA|NA|NA|
|R3|NA|NA|NA|NA|
|R4|NA|NA|NA|NA|
|R5|+42|+97|1.31|10.90|
|R6|NA|NA|NA|NA|
|R7|+136|+175|7.36|2.59|
|R8|+39|+12|3.58|4.78|
|R9|PRE(-101)|ON(-168)|-0.49|-5.87|
|R10|NA|NA|NA|NA|


#### 1962

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+18|+105|20.73|20.26|
|R2|+55|+5|4.24|14.39|
|R3|NONE|ON(-99)|0.00|0.00|
|R4|+55|+5|4.24|10.33|
|R5|PRE(-194)|+38|-7.29|23.99|
|R6|+55|+5|-3.56|2.79|
|R7|NONE|ON(-381)|-3.33|3.60|
|R8|+9|+24|-3.27|13.08|
|R9|PRE(-155)|ON(-16)|-3.31|8.00|
|R10|+55|+5|-3.56|2.79|


#### 1966

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+60|+45|13.96|19.26|
|R2|+78|+248|10.26|38.81|
|R3|NONE|ON(-1179)|0.00|0.00|
|R4|+78|+45|10.26|19.26|
|R5|+114|+104|-3.12|-20.02|
|R6|+78|+45|-2.31|-27.33|
|R7|+130|+66|-3.54|-26.56|
|R8|+66|+21|-4.05|-13.81|
|R9|PRE(-239)|+80|1.17|-14.48|
|R10|NONE|ON(-425)|-9.98|-33.27|


#### 1969-70

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+18|+82|29.51|27.76|
|R2|+13|+27|20.69|41.47|
|R3|NONE|ON(-2064)|0.00|33.37|
|R4|+18|NONE|18.68|46.91|
|R5|PRE(-100)|+135|5.32|NA|
|R6|+18|NONE|-5.71|-6.30|
|R7|+130|+93|-1.67|NA|
|R8|PRE(-8)|+42|4.51|NA|
|R9|PRE(-89)|+113|5.32|NA|
|R10|+222|ON(-16)|-8.73|NA|


#### 1973-74

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+30|+80|35.76|25.83|
|R2|+205|+231|28.83|39.42|
|R3|+435|NONE|0.74|35.73|
|R4|+207|+231|27.21|39.48|
|R5|PRE(-155)|ON(-8)|-8.34|-4.77|
|R6|+207|+231|-11.03|-4.23|
|R7|+4|+86|-8.94|-23.33|
|R8|PRE(-43)|+8|-7.45|-5.13|
|R9|PRE(-67)|+85|-3.99|-13.33|
|R10|NONE|ON(-652)|-4.62|-10.27|


#### 1980-82

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+10|+8|13.69|17.94|
|R2|PRE(-5)|+183|10.81|62.51|
|R3|+121|NONE|3.98|61.60|
|R4|+10|+183|5.21|62.51|
|R5|PRE(-114)|+70|8.49|0.10|
|R6|+10|+183|3.50|9.28|
|R7|+88|+10|2.89|-13.87|
|R8|PRE(-19)|+7|8.49|23.99|
|R9|PRE(-215)|+15|5.28|-12.00|
|R10|PRE(-5)|+183|4.02|9.28|


#### 1987

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+38|+124|3.68|20.94|
|R2|NONE|ON(-193)|0.00|9.50|
|R3|NONE|ON(-1054)|0.00|-0.00|
|R4|NONE|ON(-233)|0.00|4.59|
|R5|+35|+94|-1.97|5.07|
|R6|NONE|ON(-233)|-5.58|2.60|
|R7|NONE|ON(-232)|-5.58|-4.28|
|R8|+38|+11|2.98|9.00|
|R9|PRE(-59)|+83|3.22|-0.05|
|R10|NONE|ON(-591)|-5.58|-4.98|


#### 1990

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+15|+73|10.80|16.15|
|R2|NONE|ON(-133)|0.00|28.57|
|R3|NONE|ON(-1775)|0.00|21.86|
|R4|NONE|ON(-133)|0.00|28.57|
|R5|PRE(-11)|+126|4.83|-7.76|
|R6|NONE|ON(-133)|-8.37|6.16|
|R7|NONE|ON(-105)|-8.37|-6.81|
|R8|+14|+24|1.34|-4.71|
|R9|PRE(-71)|+57|4.83|-6.25|
|R10|NONE|ON(-1312)|-8.37|-6.81|


#### 2000-02

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+16|+113|26.71|18.44|
|R2|+26|+120|21.37|17.29|
|R3|+365|+59|17.24|23.07|
|R4|+33|+113|32.97|15.94|
|R5|+56|+36|19.96|19.94|
|R6|+33|+113|23.13|11.74|
|R7|PRE(-87)|ON(-164)|7.37|-5.16|
|R8|PRE(-94)|+18|25.33|25.17|
|R9|PRE(-226)|ON(-47)|14.15|-14.70|
|R10|+465|+18|14.15|5.79|


#### 2007-09

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+24|+58|38.84|51.19|
|R2|PRE(-5)|+103|54.57|59.75|
|R3|+142|NONE|36.51|75.36|
|R4|+24|+103|40.06|59.75|
|R5|+9|+29|6.88|11.31|
|R6|+24|+103|8.93|4.40|
|R7|+25|+59|9.16|-0.08|
|R8|+24|+11|7.79|-6.81|
|R9|NONE|ON(-360)|-8.54|-35.90|
|R10|PRE(-5)|+103|-3.65|4.40|


#### late2018

|Rule|Peak→exit|Trough→entry|Avoided (pp)|Missed (pp)|
|---|---|---|---|---|
|R1|+16|+29|7.27|26.18|
|R2|PRE(-34)|+237|20.45|33.02|
|R3|NONE|ON(-2091)|0.00|-0.00|
|R4|+16|+29|7.27|26.18|
|R5|PRE(+0)|+76|3.43|21.61|
|R6|+16|+29|-4.43|14.70|
|R7|NONE|ON(-697)|-5.10|6.21|
|R8|+15|+12|1.99|21.35|
|R9|PRE(-200)|+27|6.51|9.09|
|R10|+52|+174|-3.83|1.79|


### False-pivot denominators

Each cell is exits / complete eligible calm years = rate per calm year. These cover eligible calm years throughout the named era, including outside any displayed partial return segment.

|Rule|1926-1959|1960-1989|1990-2019|
|---|---|---|---|
|R1|23/10 = 2.30|22/14 = 1.57|29/14 = 2.07|
|R2|3/4 = 0.75|10/14 = 0.71|7/14 = 0.50|
|R3|2/7 = 0.29|1/14 = 0.07|1/14 = 0.07|
|R4|4/4 = 1.00|9/14 = 0.64|5/14 = 0.36|
|R5|20/9 = 2.22|47/14 = 3.36|66/14 = 4.71|
|R6|4/4 = 1.00|9/14 = 0.64|5/14 = 0.36|
|R7|2/8 = 0.25|11/14 = 0.79|11/14 = 0.79|
|R8|9/8 = 1.12|15/13 = 1.15|20/14 = 1.43|
|R9|3/9 = 0.33|10/14 = 0.71|12/14 = 0.86|
|R10|1/4 = 0.25|6/14 = 0.43|8/14 = 0.57|


Trend provided substantial protection in the 1929–32, 1973–74 and 2007–09 windows, but it missed 97.6, 25.8 and 51.2 pp of the following fixed-window market recoveries. In 1987 the next-close convention matters: R1 exited 38 sessions after the peak and avoided only 3.7 pp of the full decline. Credit and confluence often re-entered later: after the 2009 trough R1 re-entered at +58 sessions, R2/R4 at +103, while R3 had no re-entry within 252 sessions. R8's +11-session C re-entry was faster, but it remained fully exposed to equities and its whole-era drawdown was still 48.93%.

### Did the signal lead the defensive relative move?

For every within-window on→off transition, plus a designated earlier PRE exit, compare gross D−C over the preceding63 and next63 sessions. `Follower` means prior63 D−C>0; `Anticipator` means prior63≤0 and next63>0. Positive prior leadership may subsequently reverse. Missing horizons are NA. These overlapping dates are descriptive, not independent prediction trials.

The designated-exit classifications by episode are below: F=follower; A=anticipator; X=no prior lead and no positive subsequent defensive lead; —=no designated identified exit or unavailable relative interval. The full transition table retains actual dates, offsets and both relative-return values.


|Episode|R1|R2|R3|R4|R5|R6|R7|R8|R9|R10|
|---|---|---|---|---|---|---|---|---|---|---|
|1929-32|F|—|—|—|F|—|A|F|—|—|
|1937|F|—|—|—|F|—|A|F|X|—|
|1962|F|F|—|F|F|F|—|F|F|F|
|1966|A|F|—|F|F|F|F|F|F|—|
|1969-70|F|F|—|F|A|F|F|F|F|F|
|1973-74|F|A|A|A|F|A|A|F|F|—|
|1980-82|F|F|F|F|F|F|F|F|X|F|
|1987|F|—|—|—|F|—|—|F|A|—|
|1990|F|—|—|—|F|—|—|F|A|—|
|2000-02|A|A|F|A|F|A|X|X|X|A|
|2007-09|F|F|A|F|F|F|F|F|—|F|
|late2018|F|F|—|F|F|F|—|F|X|F|


Across 89 designated rows, 65 are followers, 17 anticipators, six have no forward defensive lead, and one is unavailable. The counts overlap heavily across rules and episodes; they are not 89 independent observations. R5 follows an existing relative move in 11 of its 12 designated exits. R8 does so in 11 of 12. This does not support presenting either as an anticipatory top detector. [All dated transitions and relative windows](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/episode_transitions.csv).

## 6. Rates, real-rate proxy and credit conditioning

At eligible month-ends, measure the next63-session gross D−C return. The table shows mean relative return in each state and the number of usable months. Months overlap; no inference or causal identification is claimed. Real yield is nominal long yield minus trailing CPI inflation, not ex-ante expected real yield. The curve is Shiller long yield minus TB3MS. Early missing states remain NA.


|Era|Known state|False: mean D−C63 (months)|True: mean D−C63 (months)|
|---|---|---|---|
|1926-1959|nominal_high|-1.65 (n=180)|0.09 (n=191)|
|1926-1959|real_high|-0.49 (n=172)|-0.98 (n=199)|
|1926-1959|credit|-0.31 (n=39)|0.69 (n=28)|
|1926-1959|curve_inverted|-0.73 (n=295)|NA|
|1960-1989|nominal_high|0.60 (n=136)|0.39 (n=221)|
|1960-1989|real_high|0.21 (n=189)|0.76 (n=168)|
|1960-1989|credit|0.98 (n=191)|-0.12 (n=166)|
|1960-1989|curve_inverted|0.51 (n=304)|0.22 (n=53)|
|1990-2019|nominal_high|-0.36 (n=216)|0.49 (n=141)|
|1990-2019|real_high|-0.15 (n=209)|0.15 (n=148)|
|1990-2019|credit|-0.02 (n=189)|-0.03 (n=168)|
|1990-2019|curve_inverted|0.03 (n=341)|-1.08 (n=16)|


Nominal-high changes from favorable relative conditioning in the first era to slightly unfavorable in the middle era and favorable again in the last. Credit-stress forward-relative returns also change sign. Recent inverted-curve months number only16 and average −1.08 pp D−C over the next63 sessions. These observations do not establish an invariant rate/credit allocation rule. R9's recent positive CAGR point estimate comes with 63.11% drawdown and a B3 interval crossing zero; R10 supplies no robust edge.

## 7. Blunt hypothesis verdicts

|Hypothesis|Verdict|Reason|
|---|---|---|
|H1: trend/credit/macro confluence beats any one alone|**Not supported**|Common-sample comparisons do not show consistent superiority; trend wins on return in the first two available eras. Full early-history and real-time macro claims also cannot be established.|
|H2: defensives lead, and switching captures an edge|**Not supported as a trading-edge claim**|The descriptive leadership clause is supported in the selected identifiable episodes (10/11 declines; reversal in10/10 recoveries), but active switching fails to establish incremental value over fixed exposures.|
|H3: breadth divergence tops and washout bottoms supply useful pivots|**Not supported where testable**|R7/R8 have no corrected edge. R7 never exits in the 1987,1990 or late2018 decline window; R8 can re-enter sooner while retaining large equity drawdowns. Earlier full paths have data gaps, and industry breadth is not stock breadth.|
|H4: rates/real rates/credit give reliable conditioning|**Not supported as a robust allocation advantage**|Descriptive associations vary by era; R9/R10 lack reliable excess. R10 combines rates with credit, so it cannot isolate a real-rate effect. Current-vintage and ex-post real-yield limitations remain.|
|H5: cap versus equal-weight stock market changes the opponent|**Untestable as specified**|True daily stock-EW history was not obtained. E49 is a visibly different proxy and cannot settle concentration-versus-equal-stock-weight claims.|

No verdict promotes a rule into live sizing, exits, rankings or alerts. These findings do not disprove every possible rotation strategy; they reject a claim of demonstrated success for this fixed family.

## 8. Three rules for a frozen second protocol

Retain a small mechanism-testing panel. These are controls/challengers selected for interpretability and the remaining question, not statistically accepted winners. Freeze exact inputs, costs, exposure references and acceptance before any new evaluation; do not silently spend the sealed sample on exploratory revisions.

1. **R1 unchanged:** M when its total-return level is strictly above its inclusive 200-session SMA; otherwise bills. It is the transparent risk-cut control. Require improvement over the causal exposure reference, with an explicit tolerated missed-upside budget.
2. **R4 unchanged:** bills when at least two of bearish M/SMA200, credit above its previous12-month mean, and U3−trailing12-month-min(U3)≥0.50 pp are true; otherwise M. All inputs must exist with the frozen lags. Keep it solely as the direct incremental-confluence challenger to R1.
3. **R5 unchanged:** C when its 126-session gross total return strictly exceeds D's; otherwise D. Keep it as the simplest direct switching test and compare it with passive C, D and the static mix. Its turnover/missed-recovery budget must be explicit.

Drop **R2 and R3 as standalone allocations** (retain their inputs inside the unchanged R4); **R6** (no demonstrated benefit from replacing cash with defensive equities under the confluence gate); **R7** (rare divergence trigger misses several requested declines); **R8** (faster washout re-entry does not establish durable-bottom or allocation value); **R9/R10** (unstable conditioning and no robust incremental edge). R9's relatively high recent CAGR is insufficient to rescue a rule that suffered a larger drawdown than the market. R8 may remain a documented failed recovery hypothesis, not an additional candidate in this three-rule panel.

The adviser suggested retaining R8/R7 if the next protocol prioritizes mechanism coverage. The principal chooses the narrower three-rule panel because this commission asks which rules merit the scarce trial budget; the data do not establish additional breadth-rule value. This is a research-design judgment, not a changed outcome or hidden trial.


## 9. Sources, actual starts, statistical method and limitations

|Input|Observed source start|Use and limit|
|---|---|---|
|French daily market/SMB/HML/RF|1926-07-01|Cap-market total return and bills; retrospective CRSP research portfolios.|
|French daily momentum|1926-11-03|Descriptive factor exposures, not a signal variant. It does not start in July.|
|French daily12/17/49 VW and EW industries|1926-07-01|All downloaded/coverage-checked;49 drives the ten rules.12/17 are not searched alternate universes. Some49 members are absent early and some eligible returns later go missing.|
|French daily size portfolios|1926-07-01|Coverage/source check. NYSE-breakpoint deciles cannot reconstruct exact whole-market stock-EW by simple averaging.|
|Shiller monthly price/CPI/long yield|1871-01-01|Long-rate and backward-real signals; monthly composite price is a descriptive source, not daily execution data.|
|FRED BAA|1919-01-01|Source context; not substituted for the missing early Treasury spread.|
|FRED BAA10YM and GS10|1953-04-01|Credit/long-rate source; after12-month history and lag, credit rules start1954-06-02.|
|FRED TB3MS|1934-01-01|Curve diagnostic, not bill total return.|
|FRED UNRATE|1948-01-01|After rolling history and lag, R3 starts1949-05-03.|
|Public Yahoo S&P500 daily price endpoint|1927-12-30|Descriptive price-return cross-check on the fixed French-market episode dates; not the total-return benchmark.|

Primary source/method documentation: [French library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html), [market/factors](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library/f-f_factors.html), [daily momentum](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_mom_factor_daily.html), [49-industry construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_49_ind_port.html), [12 industries](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_12_ind_port.html), [17 industries](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_17_ind_port.html), [size construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_port_form_sz.html), [Shiller](https://shillerdata.com/), [BAA10YM](https://fred.stlouisfed.org/series/BAA10YM), [BAA](https://fred.stlouisfed.org/series/BAA), [GS10](https://fred.stlouisfed.org/series/GS10), [TB3MS](https://fred.stlouisfed.org/series/TB3MS), [UNRATE](https://fred.stlouisfed.org/series/UNRATE), [ALFRED vintage explanation](https://alfred.stlouisfed.org/help), [FRED API-key requirements](https://fred.stlouisfed.org/docs/api/api_key.html), and [CRSP historical-index availability](https://indexes.morningstar.com/research-data-products/crsp-historical-indexes-database). Exact downloaded URLs, SHA256 hashes and coverage are in the manifest. No raw vendor prices or FRED series are committed.

**Inference:** paired circular moving blocks of252 observations,5,000 resamples,seed20261111; identical draws within each comparison. Bootstrap realized log-return paths within each era. Center the difference distribution for the one-sided superiority p, Holm-correct all30 primary slots, and use pointwise95% intervals. Pooled statistics, cost stress, passive controls, episode/rates diagnostics and H1 head-to-head comparisons are descriptive. The MDE is (z[1−.05/(2×30)]+z[.80])×bootstrap SE. No block-length or parameter search occurred.

### Limitations that constrain acceptance

- **Incomplete requested coverage:** market history begins mid1926 and signals need warmup. Credit/confluence begin1954; unemployment1949. Nine full-era rotation paths are unidentified. Clean segments do not complete them.
- **Missing returns:** early empty industries and later missing observations are different problems.200-session eligibility handles entry history, not unknown future returns. Loss-date gaps are retained; whole-path wealth across them is unknowable.
- **No exact stock-EW reference:** neither E49 nor equal averaging of NYSE-breakpoint size portfolios is the requested market. H5 and all exact B2 excess estimates remain open.
- **No real-time macro panel:** the unauthenticated ALFRED API request returned HTTP400; no complete vintage panel was obtained. Conservative lags do not eliminate revisions, seasonal-adjustment history, data-definition changes or ex-post knowledge.
- **Retrospective equity data:** French rebuilds historical research series; industry SIC assignments, CRSP corrections, delisting treatment and today's file vintage are not a tape of what an investor actually saw then. Hashes identify this input version but cannot freeze future provider revisions.
- **Synthetic instruments:** investors could not buy these exact broad/industry portfolios throughout the whole history. Index returns include theoretical portfolio construction; constituent trading, access, liquidity, taxes, fund fees and capacity are unmodeled.
- **Cost convention:** the frozen fee is the per-side rate times the absolute change from pretrade equity weights to target weights, followed by a multiplicative reduction of portfolio value. This is a target-notional approximation. Exact post-fee traded-notional financing would solve a fee-dependent rebalance equation; that refinement was not implemented. Its fee discrepancy is second order in the cost rate, with no universal conservative direction. Both the base case and doubled-cost stress retain the registered convention.
- **Omitted costs:** fees cover market/sleeve allocation and across-industry rebalancing. They omit hidden turnover inside French VW/EW portfolios, bid/ask, market impact, historical financing constraints and nonconstant slippage. Even 2× does not establish realistic all-in historical costs.
- **Execution at published close:** no opening/high/low/slippage assumptions, overnight liquidity model or market-on-close feasibility proof. The full next-close delay is enforced but cannot repair incomplete prices.
- **Group definition:** C is not a pure growth valuation factor or a fitted high-beta portfolio. Industry definitions evolved; missing early members alter composition. Industry breadth hides dispersion and concentration within each industry. Factor diagnostics show lower D beta, which can explain part of relative defense without proving timing skill.
- **Backward real rates:** nominal yield minus trailing inflation is not expected future real yield. R10 is a combined real-rate/credit rule and cannot isolate either mechanism.
- **Power and dependence:** three eras and a few crisis episodes are limited independent evidence.252-session blocks retain some dependence, not regime-transition uncertainty. Short early macro samples have few blocks; intervals/power approximations may be unstable.
- **Fixed-path uncertainty:** bootstrap paths condition on realized inputs/states. They do not rerun every strategy on hypothetical resampled histories or account for uncertainty from data revisions, omitted costs, missing data, model design or selection of the public hypotheses.
- **Historical study, not prospective validation:** this family was frozen within this commission before outcomes, but famous indicators/crises already influenced the question. Nothing here is a new untouched validation of a published strategy. Second-protocol selection is itself informed by these results.
- **Multiple endpoints:** only B3 log-growth superiority across30 rule/era slots is confirmatory. Confidence intervals on other references are pointwise; comparing many episodes, controls and conditions can generate attractive patterns by chance.
- **Exposure reference:** expanding-average B3 is causal but not perfectly matched to completed-era exposure or beta. The early and recent average differences are reported. All-equity C/D rules can still differ in market beta; the static controls are necessary but not complete risk attribution.
- **Gross benchmark asymmetry:** conventional B1/E49 are uncosted; E49's large gross return is neither a tradable quote nor an exact equal-stock-weight result. No microstructure attribution is established by this dataset.
- **Episode construction:** listed stress windows are selected by the commission. Within-window maximum drawdown uses hindsight for scoring, cannot locate a live peak, may exclude a preceding-year high, and is not an exhaustive population of corrections. Forward63 windows overlap; lead/follow labels cannot prove causal prediction.
- **Calm/false-pivot definition:** a10%-drawdown threshold and the listed excluded years mechanically define calm. Relative-rotation exits in those years can still be useful; the label is a whipsaw proxy.
- **S&P scope:** daily public price levels are supplementary, exclude dividends, and early composite history is not the modern500-stock constituent basket. No raw levels are published. The French cap-market index is the actual study opponent.
- **Asset scope:** risk-off means bills or defensive equities in these rules. No duration-Treasury, gold, commodity, currency or international allocation was tested; long yields are conditioning inputs, not a Treasury-bond total-return strategy.
- **No flow or trading authority:** asset returns do not identify literal capital flows, optimal sizing, utility/preferences or real execution. A defensive winner can still lose heavily, and a confirmed rebound can still fail.


### Validation and code location

Code and small tables: [`research/rotation_core/pro_runs/B/`](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/README.md), commit `2afbd280fe09aae929dbf9ce3be86dcccfd82db3`, branch `pro-run/rotation-b-20261111`. [Primary era table](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/primary_era_results.csv), [separate partial segments](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/partial_segments.csv), [120 episode rows](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/episodes.csv), [passive controls](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/passive_references.csv), [source/run manifest](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/run_manifest.json), [integrity tests](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/test_integrity.py), [independent accounting receipt](https://github.com/mastermindx-market-intelligence/macro/blob/2afbd280fe09aae929dbf9ce3be86dcccfd82db3/research/rotation_core/pro_runs/B/out/independent_checks.json).

Twelve synthetic integrity tests passed. A separate vectorized calculation reproduced every identified R1–R4 daily return exactly, maximum absolute error0. A distinct methodological adviser reviewed design/source before outcomes, challenged missing-data and lead/follow semantics, and checked the final tables. Technical review is not a GitHub approval or acceptance for trading. No PR, merge or production effect was requested or performed.

**Return disposition:** commissioned research delivered with explicit untestable elements; no strategy accepted. The next programme decision is whether to freeze the three-rule second protocol after resolving the stock-EW/vintage/data-gap requirements. The existing sealed sample remains reserved.
