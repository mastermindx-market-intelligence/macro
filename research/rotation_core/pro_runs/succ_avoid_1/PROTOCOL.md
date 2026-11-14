# SUCC-AVOID-1: protocol fixed before outcome inspection

Run: SUCC-AVOID-1. Ledger: successor-avoid-1. Authorized return: numbered comments on Macro #11014. Scope is research only; no PR, production change, trading or sizing. Current Chairman commission's 2013–2023 dates supersede the carrier issue's older experiment dates. Procedure pin: Mastermind protected master 8323d7a774a72da20d0e4db21c9080398da185e7 (skillpack v1.0.1, bootstrap major 1). GitHub actor mastermindx-3. Work is a new isolated research carrier; no predecessor result for this run was found. Principal direct work is retained for PRINCIPAL_JUDGMENT / LOWER_TOTAL_OVERHEAD; native child is a methodological reasoning auditor, not an implementation worker. WHY NOT FABLE: no distinct scarce principal is needed.

## Outcome and plan

1. Freeze this protocol with an immutable GitHub commit before computing signals or outcomes.
2. Acquire public observations, immediately date-filter to 2013-01-02..2023-12-29, retain input hashes; no numeric observations outside that interval are examined, retained or used, including warm-up.
3. Implement the eight fixed candidates, controls, month bootstrap and failure audit. Correct coding defects only; disclose any specification clarification or rerun, retain all candidates.
4. Publish reproducible code and derived result tables on this branch (no raw vendor/FRED data), then the complete ordered report on #11014; read back every posted part. DONE_WHEN is that complete verified posting, not a winning result.

## Inputs and universe

Ken French daily value-weighted total returns for FF12 and FF49. Yahoo public daily adjusted closes for SPY, XLB, XLE, XLF, XLI, XLK, XLP, XLU, XLV, XLY, XLRE and XLC, only where they actually exist. FRED DGS2, DGS10, BAMLH0A0HYM2, DTWEXB, DTWEXBGS and VIXCLS. Date-bounded acquisition only for HTTP APIs that allow it; French bulk files are filtered on the date field before numeric conversion and discarded outside the interval. No post-2023 outcomes. Current-vintage historical files are not proof of point-in-time vintages; disclose revision uncertainty.

Three cohorts remain separately visible: ETF (11), FF12 (12), FF49 (49). FF12 and FF49 overlap economically and are not independent confirmation samples. Primary cross-market aggregate is descriptive only. No stock-level member claim for an FF49 index or ETF.

FF49 are not literally nested within FF12. Fix the following economic proxy children before results, each FF49 code assigned once; never call it an exact constituent reconstruction:

- NoDur: Agric Food Soda Beer Smoke Hshld Clths Txtls
- Durbl: Toys Autos
- Manuf: BldMt Steel FabPr Mach ElcEq Aero Ships Guns Paper Boxes
- Enrgy: Coal Oil
- Chems: Chems Rubbr
- BusEq: Hardw Softw Chips LabEq
- Telcm: Telcm
- Utils: Util
- Shops: Whlsl Rtail Meals
- Hlth: Hlth MedEq Drugs
- Money: Banks Insur RlEst Fin
- Other: Fun Books Cnstr Gold Mines PerSv BusSv Trans Other

For FF12 breadth and member drawdown use equal-weighted statistics across those proxy children; for ETF use the ETF; for FF49 use its own index, explicitly not its individual stocks. The breadth candidate is only applicable to FF12.

## Bars, indicators, clocks

Use SPY's observed exchange-session calendar. All input series are aligned to that calendar; no future backfill. A group with missing returns/prices is ineligible until the necessary trailing observations exist. FF prices compound returns from the first permitted day. Relative price R=P_group/P_SPY; scale is immaterial.

Three-session bars use the shared calendar anchored 2013-01-02: sessions 0–2, 3–5, etc.; an incomplete trailing bar cannot fire. Weekly closes are the last session of each calendar week. Two-week bars combine successive weeks anchored to the week beginning 2012-12-31, using only permitted observations from January 2013 onward; no earlier price is needed. The first close is just an initial level, not a historical return. A higher bar becomes visible only at its completed close and is then forward-filled.

RSI14: Wilder averages, arithmetic seed from the first 14 price changes, recursive alpha=1/14; no losses gives 100, no gains gives 0, both zero gives 50. MACD on RSI: EMA14 minus EMA60; each EMA seeds with its first n finite observations' arithmetic mean, then alpha=2/(n+1). Signal EMA5 on MACD; histogram H=MACD-signal. StochRSI raw S=100*(RSI-min14RSI)/(max14RSI-min14RSI); zero range is missing; K=SMA3(S), D=SMA3(K). No reset or annual reseeding.

TOP(P,b): K_previous>80 AND K_previous>=D_previous AND K_current<D_current AND H_current<H_previous on a completed b-bar. BOTTOM uses K_previous<20, K_previous<=D_previous, K_current>D_current, H_current>H_previous. Ties in crosses are handled exactly by these inequalities. OLD=TOP(P,3 sessions).

VIX and Treasury/high-yield observations use the latest value at least one prior SPY session old, with at most five-session forward fill. Dollar uses five-session lag, at most five-session forward fill, to cover weekly publication. Before 2020 use the old broad-goods dollar DTWEXB; from 2020 use DTWEXBGS. Calculate each 63-session percentage change within its own series, never across the splice. Macro thresholds use percentage points where indicated.

## Exactly eight candidates, no tuning grid

All filters below use information available at the flag close.

|ID|Fixed rule|
|---|---|
|C1 REL|TOP(R,3 sessions) alone.|
|C2 BOTH|OLD AND TOP(R,3 sessions) on the same bar.|
|C3 WEEK|OLD AND last completed weekly K<D AND H<H_previous AND previous weekly K>=50 AND current weekly price>=0.90*highest weekly close over 26 completed weeks.|
|C4 TWO_WEEK|OLD AND last completed two-week K<D AND H<H_previous AND previous two-week K>=50 AND current two-week price>=0.90*highest two-week close over 13 completed bars.|
|C5 BREADTH|FF12 only: OLD AND (at least 40% of proxy children fired OLD in the inclusive last 9 sessions OR at least 60% are below their own trailing 50-session price average).|
|C6 PARTNER|OLD AND the same-cohort partner with minimum Pearson correlation of daily log relative returns over the 126 sessions ending t-1 has correlation<=-0.25 AND that partner fired BOTTOM(R,3 sessions) in the inclusive last 6 sessions. Partner ties within 1e-12 use lexicographically smallest group code; require complete 126 paired returns.|
|C7 VOL_RISE|OLD AND RV21(t)>=1.25*RV21(t-21) AND RV21(t-21)<=40th percentile of the preceding 252 RV21 observations ending t-22 AND (lagged VIX>=20 OR lagged VIX minus its five-session-earlier value>=2). RV uses sample standard deviation of daily log absolute returns times sqrt(252).|
|C8 MACRO|OLD AND at least two of: lagged DGS10-DGS2<0; lagged DGS10 minus 63-session-earlier value>=0.50 percentage point; lagged broad dollar 63-session rise>=2%; lagged high-yield OAS minus 21-session-earlier value>=0.25 percentage point. All four inputs must be available.|

## Evaluation population and fixed labels

Use a common per-group eligibility intersection for all non-breadth candidates: every indicator/lookback required above is finite, including higher bars, macro and partner history. Breadth uses the FF12 subset of that panel. This sacrifices early observations honestly; print first eligible date per group and annual denominators. No fake zeros for burn-in. Require 73 future sessions so all N10/N21/N45, 63-session outcomes and +10 shifts are fully observed. Require a 63-session relative-price window at t-10. Keep a separate all-observable OLD/C1..C8 flag tape through 2023, marking scored versus unscored dates and reasons.

On-share means event-day share: number of flagged group-days divided by eligible group-days. Each top flag is one day; do not silently turn it into a 21-day state. Report flags/year both by calendar year and count divided by sum of eligible group-days/252 (per eligible group-year).

Fake_N(t): some session u in t+1..t+N has R(u)>max(R(u-63)..R(u-1)); strict new high over the prior 63 sessions, not merely exceeding the high at t. Primary N=21; N=10 and 45 sensitivities only. High ties are not new highs. Lateness is t minus the latest date attaining max(R(t-63)..R(t-1)), excluding the flag session and ranging from 1 to 63. OLD's pooled empirical 1/3 and 2/3 lateness quantiles (nearest observed rank, lower tercile owns boundary ties) define fixed terciles; print their actual boundaries. Keep the same boundaries for all rule/control rows.

## Comparators and estimation

VOL33: RV63 at or above each group's 2/3 quantile over its finite RV63 values in the discovery block; this is intentionally the user's retrospective distribution comparator, not a deployable expanding-quantile signal. Raw state row is printed. For each target rule and group select exactly that target's number of eligible flagged days from eligible VOL33 days, ordered by SHA256('SUCC-AVOID-1|VOL|group|YYYY-MM-DD'), then chronological order for reporting. No label/forward return enters selection. If insufficient high-vol dates, mark the comparison infeasible. This preserves the top-third predicate and matches the event-day on-share exactly; never pretend the raw 33% state and a rare event have the same coverage. Random thinning uncertainty is not captured by the primary interval.

Shift comparators: move each target flag -10 and +10 actual sessions without changing group. They are placebo dates, not tradable rules, and are paired to their original event. Full shared outcome support is required. Their event counts and source denominators are identical; print shifted lateness separately.

Matched OLD effect: candidate minus OLD fake rate within exact (group,integer lateness) cells, weighted by candidate flag counts in supported cells. Report matched support. OLD-filter candidates are nested and have full support; C1 can lose support. Tercile results are descriptive, not a replacement for exact matching. For C5 restrict OLD and all controls to FF12. On-share control contrast uses the matched per-group VOL sample; shift contrasts use paired source events. Negative fake-rate differences are better.

Bootstrap: 2,000 draws, seed 1101401, sampling eligible calendar months with replacement. One shared month multiplicity applies to the entire cross-section and all rules. Recompute exact-cell means/weights and intersections for OLD matching in each replicate; omit only undefined replicates and print valid count. Non-matched means are event weighted. Shift pairs are resampled on the original flag's month to keep pairing. Percentile 5th/95th endpoints give 90% intervals. These intervals are discovery uncertainty, not multiple-test-adjusted or independent holdout confirmation; overlapping 63-session windows may require longer blocks in future work.

## Drawdown and honest avoidance

For each event, include close t and the next 63 closes. Member DD is the positive maximum peak-to-trough percentage loss of each member's total-return path, then the equal-weight mean across members. Print prospective DD after every rule/control.

Also fix an executable event-level counterfactual: a unit exposure is held through t+1 close (the next session after the signal), then flat at zero return through t+63. Avoided DD is hold-through-63 DD minus this delayed-exit path DD, averaged across members. This is an event-level hypothetical exit, not a position-size recommendation, continuous portfolio backtest, or claim that overlapping trades can all be executed independently. Print the return difference exit minus hold as opportunity-cost evidence. No transaction costs or cash interest assumed. Incremental avoided DD is candidate avoidance minus comparator avoidance; positive is better. A drawdown win requires the 90% lower interval bound >0.005 against matched OLD, on-share VOL and BOTH date shifts, and fake21 90% upper difference<0 against the same controls. If only later warnings improve pooled fake rate, say 'fewer fake breakdowns, later'. If fake reduction lacks the >50 bp avoidance bound, say 'fewer fake breakdowns, nothing avoided'. No forced winner.

Additionally print continuous-policy diagnostics for each rule and matched control: any warning leaves exposure active through next close, then flat on return intervals t+2..t+63; later warnings extend the flat window. Use all scored warnings, no invented trades before eligibility. Report union flat-day fraction and average per-group full-path DD reduction and total-return difference over each group's common eligible interval. These are descriptive diagnostics, not additional candidate selection criteria or bootstrap-confirmed portfolio gains. Event-count matching need not match this flat-day coverage.

Best two for detailed reproduction: reporting selection, not promotion. Rank candidates with >=30 FF12 scored flags in >=4 FF12 groups by exact-lateness matched FF12 fake21 difference (ascending), then incremental avoidance versus matched VOL (descending), then ID. If fewer than two qualify, fill by count descending then ID. Always show ETF and FF49 results for them and mark C5 not applicable outside FF12. No thresholds are changed after ranking.

## Failure audit

Worst fake warnings: among selected best rule's N21 fake flags, rank maximum R(t+1:t+21)/R(t)-1 descending, ties larger absolute appreciation, then group code/date. Provide date, group, relative gain, first new-high delay, lateness and 63-session member DD.

Missed real tops: independently enumerate strict rolling relative highs h with at least 63 future sessions. For each high compute positive group absolute close-to-trough decline over the next 63 sessions; require >=10%. For highs sharing the same group and ensuing worst-trough date, retain the latest high. Sort remaining episodes by decline descending, high-date ascending, group code; greedily keep episodes whose [h,trough] does not overlap an already-kept episode for the same group. A timely catch needs a best-rule flag from h through min(h+21,trough-1). Print the ten largest uncaught episodes, including whether a warning came later within 63 sessions. This is a supplementary real-top definition, not a change to the user's fake label; do not use it for tuning. If fewer than ten exist, print all without changing thresholds.

## Complete test accounting

Eight candidate specifications; one OLD; raw VOL33 plus nine target-matched VOL samples; eighteen shifted tapes (OLD and eight candidates each ±10); three fake horizons; three reporting cohorts plus descriptive pooled panel; member-DD, delayed-exit-DD and return-gap outcomes. All candidate results and dropped/inapplicable cells are retained. Bootstrap draws, unit checks and coding repairs are disclosed separately from candidate specifications. No sweep, hidden candidate, post-2023 test, earlier-period test, or production claim.
