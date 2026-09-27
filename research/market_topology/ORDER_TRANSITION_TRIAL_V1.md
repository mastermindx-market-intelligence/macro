# Order and transition trial v1: pre-result research protocol

Status: DESIGN FROZEN BEFORE STOCK FORECAST RESULTS; EXECUTION HELD FOR DATA QUALIFICATION. This is not external preregistration, production source law, an accepted trading rule or an implementation-ready Fable commission. Any amendment must be dated and justified before examining results under the amended design. It must preserve the old specification and trial history.

Operation: `market-topology-research-20260923-astra-001`; Macro draft PR #7812. Read `INITIAL_FINDINGS_20260923.md` and `STOCK_PANEL_QUALIFICATION_20260923.md` for actual evidence. No stock-level forecast, matching analysis, recovery calibration or trading PnL has been executed under this protocol.

## 1. Questions and distinct claims

Primary question: does a fixed bundle of order-sensitive and cohort-persistence measurements improve the ranking of genuinely future 20-session security returns beyond a strong momentum/volatility/industry/size/liquidity baseline?

Separate questions are whether the bundle helps estimate subsequent holding-path damage, whether already weak securities continue deteriorating, and whether a currently observable recovery attempt fails. A good descriptive state representation can be useful without being predictive. A predictive result does not establish executable decision value.

The first industry pilot remains negative. Signed efficiency and positive-day fractions do not acquire independent value merely by receiving new names. This study is not a replication of Frog in the Pan and must not be reported as one.

## 2. Input admission: all mandatory gates remain explicit

Use the existing Data OS, security-master/alias, corporate-action, membership and data-publication owners. Do not create a second identity or data authority. A research extraction is an immutable, provenance-bound view of their outputs, not a replacement source of truth.

A candidate extraction must provide:

1. A stable security identifier with date-scoped vendor symbols and exchange/security type; correct FB/META/METV segmentation; explicit share-class treatment; effective-date conventions for index membership.
2. An economic return basis, with split/cash-dividend/other-distribution treatment declared and checked against raw trading prices and event records. Separate raw prices for price eligibility, adjusted prices or returns for comparison, and point-in-time shares for capitalization. An `adjusted` string alone is insufficient.
3. A historical eligible universe, not today's survivors. Initial scope is historical S&P 500 common-share membership, not all U.S. equities. Membership source quality and current-vintage versus archived-vintage limitations remain visible.
4. Historical industry classification, market capitalization and dollar volume. Do not backfill today's size or industry into the past and then claim matching. Missing controls block the fully controlled trial rather than being silently dropped.
5. Complete outcome handling after index exit, rename, acquisition, halt, bankruptcy and delisting, including unresolved states. The forecast denominator is frozen at formation; index exit is not permission to remove a losing observation.
6. Observation/effective timestamps, actual information-availability timestamps when known, source revision, correction policy and extraction hash. Unknown historical publication time remains unknown.
7. Separate coverage counts for membership, identity, prices, adjustments, controls and terminal outcomes. Unknown is never relabelled sideways, non-leader or failed recovery.

The audited raw local panel does not pass these gates. Its roughly 99.58% nominal ticker-close coverage does not override the failures. No model is to be fitted on that raw panel under a claim of validated stock evidence.

## 3. Formation sample, horizons and information clocks

Primary horizon: 20 observed U.S. trading sessions. Secondary horizons: 5 and 63, reported as secondary regardless of which looks best. They cannot replace a failed primary test without a new declared study.

Formation anchors: the last U.S. session of each month. Require 253 complete prior economic closing observations through formation, a valid stable identity and contemporaneous industry/size/liquidity controls. Use historical raw closing price at least USD 5 and prior-20-session mean raw dollar volume at least USD 5 million. These are initial research eligibility choices, not optimized thresholds or recommendations. Record exclusions and the population they remove, especially IPOs and illiquid/distressed names.

For the available five-year era, train initially on eligible anchors from 2021 onward, after feature warmup, whose outcomes are complete before January 1, 2024. Test 2024; expand only with fully observable training outcomes before January 1, 2025, then test 2025. Exclude outcomes ending after December 31, 2025. The resulting roughly two-year test is an initial low-regime-diversity screen, not sufficient final validation of the full thesis. Reserve 2026 from model selection in this stock trial. A materially longer qualified history requires an explicit protocol amendment before viewing its results.

The primary statistic is a conditional forecast experiment anchored to date t; it is not trading PnL. A later executable test must use the first genuinely available decision time. Massive currently documents flat files at approximately 11 a.m. ET the following day, so a flat-file-only strategy cannot assume availability before that day's 9:30 a.m. opening auction. For daily-OHLC execution analysis, the conservative default is the next session open strictly AFTER proven availability; when availability is t+1 at 11 a.m., that is t+2 open. Do not convert this convention into an assertion about archived historical release times. Faster data require their own recorded path.

## 4. Fixed baseline versus augmented forecast

Let W_i(t) be a coherent economic total-return wealth series for one security; r_i(t)=log(W_i(t)/W_i(t-1)). Let sigma_h be sample standard deviation of daily r over h complete sessions, with nonpositive/undefined sigma marked unavailable.

Baseline numerical features at t:

- cumulative log returns over 5, 21, 63 and 126 sessions;
- log(W(t-21)/W(t-252)), the 252-session lookback excluding the latest 21 sessions;
- realized daily volatility over 20 and 63 sessions;
- 63-session cumulative return / (sigma_63 * sqrt(63));
- historical beta over the last 126 sessions versus SPY on the same return basis;
- log of point-in-time market capitalization;
- log of trailing-20-session mean raw price-times-volume.

Add contemporaneous historical industry indicators. Numerical preprocessing uses training-only mean and standard deviation; constant features map to zero. No test-outcome-dependent winsorization or hyperparameter selection. No missing-value imputation for identity, economics, outcomes or required controls. Before fitting, validate finite inputs and the explicit eligibility report.

Model: ridge regression with an unpenalized intercept and a fixed penalty lambda=10 under the objective sum of squared errors plus lambda times the sum of squared non-intercept coefficients. The target is the within-formation-universe percentile rank of the genuinely future total return. Baseline and augmented versions use exactly the same eligible observations, training dates and outcome support. The model is deliberately simple; changing it after viewing results creates a new experiment.

Augmented bundle, fixed before results:

A. Maximum drawdown over the last 63 sessions. Include the starting wealth level before the first return; running peaks use only observations within this trailing window.
B. Root-mean-square drawdown over the same 63-session path.
C. Sessions since the most recent maximum closing wealth within the 63-session window, divided by 63. Define ties deterministically by the most recent maximum.
D. Fraction of the last 20 sessions in which the security was in the top quintile of 63-session relative-return ranks among that session's eligible peers. All 20 daily ranks require valid contemporaneous peer sets. Keep population-entry/exit flags separately; changing eligibility is not a state transition.
E. Number of changes in sign of the 21-session benchmark-relative cumulative return during the last 20 sessions, divided by the number of valid adjacent observations. Exact zero is its own state; no sign is inferred from missing data.

The primary comparison is full augmented bundle versus baseline. Order-only and cohort-only ablations are diagnostic secondary comparisons, not opportunities to select and advertise the best backtest. Do not add efficiency as an independent alpha leg simply because the initial pilot's near-redundancy is inconvenient.

## 5. Non-overlapping future outcomes

Primary return label:

Y_i,t,h = log(W_i(t+h)/W_i(t)); all label increments are after t. Primary metric is monthly Spearman rank IC, with paired augmented-minus-baseline differences. Also report top-quintile future-return overlap against its chance baseline, annual results and sample/exclusion counts. Subtracting one common benchmark does not change the within-date return ranks; do not claim a new target merely from that subtraction.

Holding-path outcomes are separate: maximum drawdown of the forward wealth path beginning at W(t), and the fraction of future closes below W(t). Do not conflate running-peak maximum drawdown with adverse excursion below the entry value. These are research outcomes, not stop-loss instructions.

Current trailing-window state persistence is allowed as a descriptive endpoint, but it must not be used as the only evidence for forward predictability. A 63-session leader label evaluated 20 sessions later shares 43 returns with its origin label. The completed IID null experiment produced approximately 54.7% top-quintile retention with no predictive signal. Always report future-only outcomes and the mechanical-overlap baseline.

## 6. Matched diagnostic: not a causal claim

Regression adjustment and matching are not synonyms. In addition to the primary controlled forecast, conduct a predeclared descriptive matching diagnostic once inputs qualify:

- within the SAME formation date and SAME historical industry;
- compare high versus low trailing-63-session underwater fractions, defined as at least 0.75 versus at most 0.25 of closes below the running window peak;
- nearest-neighbour one-to-one matching without replacement on cross-sectional percentile ranks of 21- and 63-session momentum, 63-session volatility, log size and log dollar volume;
- calipers: at most 0.10 percentile-rank distance on each momentum and volatility coordinate; at most 0.20 on size and liquidity;
- choose the minimum squared distance among eligible pairs; resolve ties by stable security identifier;
- report overlap/support, matched count, unmatched fraction and before/after balance on ALL baseline controls, including 5-/126-/long momentum and beta.

Poor balance on any required control means the diagnostic does not establish matched incremental information. Sparse support is a result: do not relax calipers or change industry granularity after examining outcomes. Associations are not causal treatment effects, and underwater fraction is not labelled inherently good or bad.

## 7. Prospective recovery and loser-continuation label contract

Avoid retrospective turning-point labels masquerading as real-time signals. Separate the time an observation is visible from the time its outcome becomes known.

Experimental recovery-attempt trigger at t, computed only from data through t:

- 63-session absolute and SPY-relative returns are both negative;
- at least one of the previous 20 sessions set a 63-session closing low;
- closing wealth crosses from at or below its 20-session moving average on t-1 to above it on t;
- the last five-session return is positive.

This is an initial research proxy, not an accepted definition of a bottom. Signal clustering: after one trigger, do not originate another primary event for the same stable security for 20 sessions. Keep the suppressed triggers for sensitivity diagnostics rather than pretending they are independent episodes.

At formation, freeze B=min(W(t-19),...,W(t)) and A=W(t)*exp(sigma_63*sqrt(20)). Over the next 20 sessions classify the first observed close crossing:

- upper barrier A first: recovery objective reached before a lower low;
- below B first: failed recovery / renewed lower low;
- neither: unresolved within the specified horizon;
- verified acquisition, cancellation or other identity-changing terminal event: competing event with its economic outcome separately accounted;
- missing/halted/unresolved economics: unavailable/censored status, NOT automatically success, failure or zero return.

Because these barriers are checked at daily closes, an intraday ordering claim is prohibited. The floor/upper barrier recipe is fixed for this experiment; it is not a recommended entry or stop. Assess later relapse at 63 sessions as a distinct secondary target, not a retroactive deletion of failed initial labels.

For persistent-loser continuation, evaluate securities with negative absolute and relative 63-session return separately from the recovery-trigger subset. Report future-only return, future lower-low occurrence, drawdown and competing-event incidence. Do not infer bottoming simply from age in a loser state.

A bankruptcy filing does not itself establish that shareholder value became exactly zero at filing. Terminal distributions, surviving/OTC shares, cancellation dates and merger consideration require event-specific evidence. Existing imputation outputs, where present, must retain their imputed status and cannot become observed labels by being read from a file.

If N formation events include s observed successes and u unresolved labels, the model-free binary success-rate bounds are [s/N,(s+u)/N]. Report them along with missingness reasons; do not assume missingness is random. For return-rank targets, missing terminal outcomes prevent unqualified whole-cohort ranks. A complete-case result may be reported only as a conditional diagnostic with explicit selection limits; it cannot satisfy the primary evidence gate.

## 8. Population and rotation measurements

Maintain absolute progress, relative rank, economic drawdown, identity persistence and uncertainty as separate dimensions. A fixed top-quintile ranking always allocates 20% of names to that rank group; it cannot alone measure whether the market has 5% or 60% genuine advancing participation.

For two sets of advancing/leading identities A and B within the SAME eligible common universe of size N, report intersection, union and entries/exits. Expected random intersection conditional on set sizes is |A|*|B|/N. A candidate normalized excess-overlap measure is:

C = (|A intersect B| - |A|*|B|/N) / (min(|A|,|B|) - |A|*|B|/N).

When the denominator is zero, return unavailable with the degeneracy reason, not a perfect-persistence score. This chance adjustment does not remove market-factor correlation, shared formation returns or all sampling effects. Apply overlap/null controls separately. Negative excess overlap is not by definition a harmful market; holding-path and forward outcomes must decide usefulness.

Population changes caused by additions/removals, symbol migration or coverage changes must be projected separately from common-cohort state transitions. Preserve a visible unknown population. Do not normalize away missing stocks and then call the remaining proportions whole-market breadth.

## 9. Inference and rejection rules

Use paired monthly differences for the primary forecast comparison. In the short five-year data era, use a six-month circular block bootstrap with 5,000 resamples and seed 2026092303. Report a twelve-month-block sensitivity and the small number of effectively independent regime blocks. No security-row bootstrap pretending all stocks/days are independent.

Primary screen: augmented mean rank IC exceeds baseline with a nominal paired 95% interval above zero, no failure concentrated in one undisclosed year/sector, and all input/label gates passed. Passing is only a reason to extend validation, not acceptance of alpha, calibrated probabilities, trading authority or neural complexity. Failure is retained, not tuned away. Secondary horizons, endpoints and ablations must be listed as one research family with multiplicity acknowledged; use Holm adjustment for any familywise significance claims. A confidence interval after repeated adaptation is not untouched evidence.

Before any probabilistic leadership/recovery forecast is accepted, fit and assess a separate properly specified probability model with past-only calibration, held-out log loss/Brier score, reliability curves and support counts. Ridge return scores are not probabilities. Do not attach a percentage confidence to an uncalibrated ranking.

A subsequent decision-value study requires available-time-aligned fills, spread/slippage/fees, feasible liquidity, position/risk constraints and an accepted comparison policy. Research scores do not originate or size trades.

## 10. Integration and handoff gate

This protocol adds research requirements to the existing system, not new production components. Existing Data OS/reference owns identity and input contracts; existing economic-data/corporate-action owners own adjusted returns and terminal events; existing market-view/rotation consumers remain the integration candidates; existing research/evaluation owners retain experiment lineage.

The closest useful product slice remains a transparent market-population explanation with evidence and coverage, followed by empirically earned leader/recovery forecasts. It must not be a universal opaque breadth score or a free-standing control plane.

Fable build handoff remains held until qualified inputs, completed experiments, accepted/rejected methods, source-grounded integration seams, user workflows, cost/freshness behavior, exact tests and production-path acceptance are specified. Do not delegate unresolved broad discovery to Fable merely because raw data qualification revealed work.

Next action: consume a lawful qualified extraction/receipt from the existing identity-and-economic-return owners, first verifying the named split, rename, reused-symbol and terminal-outcome fixtures. Then execute this frozen trial, or document which exact remaining input prevents it. Independently continue hypothesis and historical-analogue work without duplicating or weakening the blocked data path.
