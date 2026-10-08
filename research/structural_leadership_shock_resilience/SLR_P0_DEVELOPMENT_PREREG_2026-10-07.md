# SLR-P0 — frozen retrospective development specification v1

Commission: 2026-10-07. **FROZEN_RESEARCH_SPEC / DATA_NOT_ADMITTED / OUTCOMES_NOT_OPENED.**

This is a pre-outcome specification for historical **development**, not an independent confirmatory preregistration, a prospective registration, a production policy, or approval to bypass an input gate. The accompanying source audit was conducted using published prior research, code, schemas, manifests and eight whitelisted parent-metadata columns. No SLR forward returns or CR1/AF1 outcomes were inspected. The immutable publication commit and file digest establish the freeze. Any methodological correction requires a versioned amendment, a reason and a statement of whether outcomes have been seen; the original stays recoverable.

## 1. Question and decision scope

Among canonical Detector-D onsets that are still in the incumbent `continuation` watch state before a common adverse challenge, does challenge-day unexpected return predict **remaining** stock-specific performance? The target is conditional predictive association. Past-only estimation does not identify a causal effect of resilience or institutional demand.

One primary estimand: the coefficient on challenge residual z in a controlled within-shock comparison for **21-session forward sector-relative total return**. Research relevance threshold: **0.50 percentage points per one-unit residual z**. This is a deliberately stated development decision threshold, not a literature estimate, expected profit, trading-cost estimate, or position-sizing rule.

The investigated population is named **Detector-D post-onset continuation**, not automatically formal Leader Radar `LEADERSHIP`. The latter additionally requires qualified weekly RS persistence and concentration semantics. No new lifecycle or leader score is introduced. [M07–M09]

## 2. Source firewall and vintage

Read only already-authorized historical sources. Outcome rows must be written only after this specification and an immutable admitted input manifest exist. Source qualifications are separate from model fitting.

The research archive ends at **2025-12-31**. Eligible onset dates begin **2014-01-01** and end on the NYSE session **126 sessions before the last session on or before 2025-12-31**. This deterministic cutoff supplies the worst-case 63-session onset-to-challenge interval and 63-session label horizon. Do not choose the end date from measured performance or available survivors. The January–December 2026 period is not opened here. Exclude all CR1/AF1/RH1 source paths and outcomes; neither historical RH1-shaped events nor interim prospective states are an input. The Winner Autopsy A2 firewall remains in force; do not access sequestered fundamental, expectation, insider or washout features to fill controls.

This can be a final-vintage historical study with causally ordered feature construction. It must not claim that Mastermind actually possessed those historical records at the original date. Require valid-time classification/security identity and source adjustment provenance; distinguish actual receipt time from hypothetical historical availability. Prospective confirmation will require actual retained first-seen/revision clocks. [M02–M07, M16–M18]

## 3. Unit and leader eligibility

Consume existing Detector-D onset identity and exact source-row provenance. Do not condition on `durable_winner`, `clean_hold`, `blow_off`, `failed`, mature forward returns, or any future outcome label. Do not reuse the Winner Autopsy control sampler's future-aware candidate exclusions.

Security scope: US-listed ordinary common stocks and ordinary-share ADRs, with historical type and stable security/issuer linkage. Exclude ETFs, funds, preferreds, warrants, crypto and unresolved ticker reuses. References to a derived SLR row point back to the existing onset; they do not establish another episode authority.

For each onset D, examine the fixed risk window **D+21 through D+63**, inclusive, on the master exchange calendar. Choose the **first qualifying common challenge** in that window, independently of the subject's current-day return. Only after that first challenge C has been chosen require the existing Winner Autopsy watch-state computation, supplied strictly with prefixes ending C−1, to return `continuation` for this onset. An ineligible first challenge excludes the episode; do not search for a later, better-looking challenge. Require the subject's prior-20-session median dollar volume at least $25 million and price at least $5 at C−1.

Why +21: this commission concerns established post-onset continuation, not immediate breakout success. One full trading month separates the test from onset-bar volume gates and a merely fresh breakout. The native last-five-session breakaway override makes +5 particularly awkward; +6 is a mechanical minimum, not a scientific definition of established leadership. +21 is a pre-outcome research choice, not an optimized window. +63 retains the incumbent episode scale. Do not run a +5/+10/+21 grid. Record earlier common shocks during D+1..D+20 as an audit field, not an exclusion or alternate clock.

One primary row per onset. Multiple episodes of the same issuer remain dependent observations. A formal Leader Radar leadership subset is descriptive only when its complete historical inputs are genuinely qualified; `CROWDED` is not automatically proof of leadership and measured concentration must not be replaced with null to pass a gate. [M07–M09]

## 4. Common shock, ex-self identity and coverage

For each candidate day t, construct the peer basket using information valid and available by t−1: the subject's contemporaneous historical sector, historical eligible membership, historical instrument type, prior-20-session median dollar volume at least $25 million and prior close at least $5. Use one eligible listing per other issuer, chosen by highest lagged median dollar volume; break ties by stable security ID. Exclude **all listings of the subject's issuer**. Require **at least 20 other issuers**. Equal-weight them. Never use the subject to create its shock.

Freeze that candidate day's basket at t−1. Construct its trailing returns and challenge-day return from those constituents. At least 200 of the preceding 252 master-calendar daily observations must have the complete basket and valid market returns; no day is compressed away to change the horizon. All frozen constituent returns on t must be valid, including documented terminal payoffs when applicable. No missing-constituent reweighting, whole-universe fallback, current-sector substitution, inferred zero return, or stale-close fill is allowed for primary shock identification. A known official unchanged close can be a genuine observation; a missing observation cannot.

Let p_t be the equal-weight peer return, μ_p and σ_p the mean and sample standard deviation of its valid preceding 252-session history. The one event rule is:

`p_t < 0 AND (p_t − μ_p)/σ_p <= −1.0 AND fraction(other issuers with r_j,t < 0) >= 0.60`.

The breadth requirement prevents one outlier from masquerading as common stress. Twenty names, −1 z and 60% breadth are design choices, not empirically optimal constants. Severity remains continuous in subsequent models. A missing/unqualified candidate day before an apparent first challenge makes the first-challenge status **unobservable**, not permission to skip ahead. A fully observed window with no trigger is `NO_CHALLENGE`.

Primary classification requires historically valid sectors. Sector ETF, industry, theme, market-only and factor-only events are not fallback populations. They answer related but different questions and require an explicit amended development study. Store current-map/ETF diagnostic eligibility counts separately without opening their outcome labels. [M10, M12–M16]

## 5. Four response representations and the expected-move ruler

Use consistent daily total returns in decimal units for stock, peers and SPY. Market return m is SPY's qualified total return; SPY is not the event trigger. Its small subject exposure and its imperfect market proxy are disclosed limitations. Train on the preceding 252 sessions ending C−1, using at least 200 complete observations common to subject, frozen C peer basket and market.

First fit `p_u = a_s + b_sm*m_u + v_u` by OLS with an intercept on that exact window. Define orthogonal sector return `q_u = p_u − a_s − b_sm*m_u`. Then fit `r_i,u = a_i + b_m*m_u + b_s*q_u + e_i,u` on the **same window**, again with an intercept. Require full rank, finite coefficients and positive residual RMSE, using n−3 degrees of freedom. At C:

`expected_C = a_i + b_m*m_C + b_s*(p_C − a_s − b_sm*m_C)`

`epsilon_C = r_i,C − expected_C`

`Z_C = epsilon_C / RMSE(e_training)`.

Retain raw return, `r_i,C − p_C`, epsilon and Z as separate representations. No fit uses C, a future observation, or full-sample normalization. No winsorization of actual challenge or future returns. Report regression leverage/extrapolation and estimation-window sample size.

The existing residual owner supplies the architectural seam, but its current self-inclusive, sequentially estimated construction is **not** a drop-in implementation of this formula. The simple compatibility owner also requires an explicit no-fallback mask and correct other-issuer count. These are isolated research adapters, not changes to either production engine. [M10, M12, M13]

## 6. Outcomes and clocks

Primary `Y21 = (TR_i,C+21/TR_i,C − 1) − mean_j(TR_j,C+21/TR_j,C − 1)`, using the C-frozen ex-self issuer basket and equal initial peer weights. This is stock total return minus an equal-initial-weight buy-and-hold peer return. It contains **no estimated factor coefficients**. It is a relative-performance endpoint, not proof of a net trading strategy or risk-free alpha. A documented terminal payoff remains in the wealth index; after an exit its known proceeds are held in a zero-interest cash sleeve for this research benchmark. Unknown terminal proceeds are never replaced by zero.

**Reason for choosing peer-relative rather than fitted residual return as primary:** reusing one estimated model in both the challenge residual and future label can manufacture a positive association from shared estimation error. In the simple null `r_t=mu+eta_t`, let the lagged mean estimate have error delta. Then `X=eta_C−delta` and a fitted H-day residual label is `Y=sum(eta_future)−H*delta`, so `Cov(X,Y)=H*Var(delta)>0` even when future innovations are independent. Past-only fitting alone does not eliminate this artifact. The derivation is analytical, not an SLR result. See METHODS_DERIVATION.json. The primary avoids this shared fitted-label error, while its risk-exposure confounds still require the declared controls.

Secondary fitted-residual rulers keep C−1 coefficients fixed. For h=1..H define `e_forward(h) = r_i,C+h − a_i − b_m*m_C+h − b_s*(p_C+h − a_s − b_sm*m_C+h)`. Report their arithmetic sums at 5, 21 and 63 sessions, expressly labeled vulnerable to shared-model estimation error. They cannot independently justify advancement when the primary fails. Synthetic null fixtures must quantify this artifact and show that it is absent from a coefficient-free peer-relative label under the same simulated null. Do not retrospectively choose whichever label produces the desired sign.

The feature cutoff is after all required C data have become available. Labels start at **C+1**; the challenge candle is never part of future MAE, MFE or performance. A close-C reference is useful for continuation research but does not prove an executable close-C fill. Next-open economics remain a separate, qualified sensitivity, never a substitute endpoint chosen after results.

Secondary endpoints: fitted-residual sums at 5, 21 and 63 sessions; the analogous buy-and-hold stock-minus-peer return at 63; **close-based** MAE21/63 and MFE21; severe tail `MAE21 >= 10%`; restricted waiting time up to 63 sessions to a new high of the stock/peer total-return ratio above the maximum ratio over C−63..C−1; and occurrence of incumbent watch `failed` during C+1..C+63. Close-based MAE_H is `max(0, 1 − min(TR_i,C+h/TR_i,C))`; MFE_H is `max(0, max(TR_i,C+h/TR_i,C) − 1)`. They are not intraday adverse excursions.

Do not drop bankruptcies, exits or terminal missingness as if they were random unmatured rows. Report exact terminal-payoff coverage. An unresolved economic terminal return blocks inferential use of the affected cohort; do not import an arbitrary −30%, zero-return or clipping convention. The parent's `gap_leg_crossed` flag is an audit/sensitivity field, not a causal feature or a substitute for checking this study's actual windows. [M04–M07]

## 7. Controls and baselines

All ordinary controls end at C−1 unless explicitly contemporaneous environment/context. Fixed core vector: raw and residual momentum over sessions C−252..C−22; previous 1-, 5- and 21-session residual returns; market and sector betas; downside and upside market betas estimated on the negative/positive-market subsamples of the same 252-session window, requiring 40 observations per sign; 63-session realized volatility; log prior-20-session median dollar volume; log historically valid market capitalization; close/20- and 50-session moving-average extension; distance from prior 63-, 126- and 252-session highs; days since D; trailing maximum drawdown since D; prior path information discreteness; and prior-path residual volatility.

Information discreteness follows the sign-based Frog-in-the-Pan definition over C−252..C−22, with zero-return days kept in its denominator. It is not synonymous with volatility or literal smoothness. Medium-term residual momentum uses rolling past-only residuals generated before each return, not a full-history fitted residual series. [E02, E07]

Environment controls: continuous peer shock z, peer negative breadth, m_C and prior-126-session market variance. Calendar date/sector controls are handled by the fixed effects below. Ex-ante panic state is prior-504-session cumulative market return below zero; variance remains continuous rather than an optimized crisis cutoff. Include documented earnings/material-release flags for C−1 and C, plus a scheduled-earnings-within-five-sessions flag known at C−1. Unknown event/size data are not false or zero. Primary analysis is complete-case with explicit excluded-population reporting. A missing mandatory control leaves the full specification unadmitted; a price-only exploratory coefficient cannot be presented as the registered primary result. No sealed A2 inputs may be used to repair missingness.

Strong baselines are leader-only continuation; raw leader drawdown; sector-relative challenge return; low beta; downside beta; residual momentum plus short reversal; path quality; recent-new-high continuation; and the combined incumbent price-control vector. Fit four augmented versions adding, separately, raw challenge return, peer-relative return, epsilon, or Z to that same vector. Do not insert all four into one regression: they are transformations of shared inputs, not four independent pieces of information.

The low-beta falsifier also fits a prespecified past-only piecewise factor model using intercept, positive/negative market returns and positive/negative orthogonal sector returns on the same training window. Require 40 observations for each factor sign. Its standardized innovation replaces Z in the corresponding secondary test. This tests omitted conditional exposure rather than merely adding a low-beta label. [E08–E13]

## 8. Primary estimator, inference and chronological evaluation

Primary: weighted OLS of Y21 on Z and the complete core controls, with **challenge-date × historical-sector fixed effects**. A cell needs at least two eligible issuers and nonzero within-cell Z variation. This deliberately compares leaders under the closest observed common environment rather than unshocked names or ex-post winners. Cells that fail are counted, not silently pooled into unrelated dates. Each retained date has total weight one; within a date each eligible sector cell receives equal weight, and within each cell each issuer receives equal weight.

Use deterministic column ordering and QR checks. Remove only exactly collinear nuisance columns induced by fixed effects, recording their identities. If Z is unidentifiable, stop the estimate rather than change controls. Required reporting floor: at least 100 issuers, 50 shock dates, 250 rows and ten rows per retained non-fixed-effect coefficient, with positive residual degrees of freedom after absorbing fixed effects; these are numerical/inference safeguards, **not proof of 80% power**.

Report two-way issuer/date cluster-robust 95% intervals and a second interval from a **whole-cross-section 63-session moving-block bootstrap**, 2,000 replications, seed 20261007. Resample calendar blocks, not individual rows; preserve all issuers and outcomes in a selected block and distinguish duplicated date instances when re-fitting fixed effects. No circular end-to-start wrap. Repeated-issuer dependence extending beyond blocks and cross-date common dependence are not magically solved by either method: both intervals, cluster counts and concentration must be shown. No advancement when only the more favorable interval excludes zero. Fewer than 20 occupied nonoverlapping 63-session calendar blocks means precision is insufficient for a promotion recommendation. [E27, E28]

For incremental prediction use annual expanding chronological folds: 2014–2018 initial training, test years 2019 through the last eligible 2025 observations. Training label ends must precede the test start by at least **63 exchange sessions**; purge all overlapping label windows and keep a parent episode within one fold. No random row CV. Fit a fixed ridge model with penalty 1 on training-standardized continuous features; do not tune it. Use sector indicators and observed market-state features, not unknowable future date fixed effects. All scaling, imputation-free complete-case selection and coefficients are fit on training data. If a fold lacks the registered training floor, mark it not estimable; do not pool it opportunistically. Report paired test MSE and rank-correlation changes against every frozen baseline, not only the best-looking one. The prespecified prediction gate uses ΔMSE = MSE(combined core-control baseline) − MSE(core controls plus Z), with positive values favorable. At least three annual folds must be estimable, ΔMSE must be nonnegative in a majority, and pooled test ΔMSE must be positive. Rank-correlation changes are diagnostics, not an alternative gate selected after results.

## 9. Secondary hypothesis family and negative controls

H0: no increment. H1: positive remaining continuation. H2: reduced future tails/MAE. H3: ordinary conditional exposure explains the observation. H4: panic rebound reverses the ranking. H5: later upside participation adds information only at a second landmark. H6: qualified continuous flow/book evidence adds to the same price-defined cohort; **not opened in P0**. H7: challenge response is merely a generic residual innovation or reversal, with no shock-specific increment.

One primary test. Apply Holm family-wise correction at 5% to the following **14 secondary tests**: residual5, residual21, residual63, peer63, MAE21, MAE63, severe-tail21, MFE21, time-to-relative-high63, failed-state63, piecewise-residual21, Z×ex-ante-panic interaction, H5's R×U interaction, and H7's R×shock interaction. The family uses two-sided cluster-robust Wald p-values with reference degrees of freedom min(number of issuers, number of dates)−1; apply Holm to those p-values, not to whichever interval looks favorable. A non-estimable secondary test is reported as such and assigned p=1 for the 14-test correction. Return slopes use the primary estimator with the corresponding endpoint. Binary outcomes use a linear probability model with the same design, interpreted as association, not a calibrated probability. Restricted waiting time is capped at 63 for no new high. Report raw effects and both intervals regardless of significance. Subsets and leave-one-out analyses are diagnostics, not additional uncounted discovery claims. [E29]

H4's additional species control is the lagged 12−1 momentum bottom decile of qualified same-sector peers at C−1, selected without a future rebound. Deduplicate issuer/date controls. Report its performance on the same challenge dates, separated by ex-ante panic state. A subsequent positive market/sector return is an **ex-post diagnostic label**, not a C-time regime feature.

H7 uses one independent scheduled landmark D+21 per eligible onset, assessed at D+20, whether or not that day is a shock. Apply the same data/leader requirements and fit `Y21 ~ R + shock + R*shock + controls + date×sector effects`. This asks whether common stress adds context beyond the same daily residual innovation. It cannot be replaced with a retrospectively selected quiet day. Shared rows with the primary are not a fresh holdout.

## 10. Two landmarks: never backdate upside participation

For each primary C, B is the first independently qualified peer rebound during C+1..C+21, using the C-frozen peer basket, positive peer return and lagged peer z at least +1.0. The lagged mean/standard deviation use only observations through B−1; require the same coverage. No subject reclaim, selected trough, maximum bounce or future new high may choose B.

At B calculate U, the factor-adjusted standardized response, using a fresh past-only B−1 model. Keep R=Z_C fixed. Predict the coefficient-free 21-session stock-minus-peer total return measured **after B**, with the same C-frozen peers re-anchored at B and equal initial B weights, never the C+1 outcome, from R, U and R×U with B-time controls, elapsed C→B and B-date×sector effects. Keep all C rows in the accounting: no rebound, missing first-rebound status, delisting, and incomplete B models are distinct outcomes of follow-up. The risk set and conditional estimand at B are different from C. Quadrants R positive/negative × U positive/negative are explanatory displays, not a new scoring rule. H5 can improve a later decision while adding nothing to the original challenge-time decision.

## 11. Falsification, missingness and stopping

Mandatory audit: source mix by actual event/label window; all exclusions and missing controls; security-type and dead/exited linkage; era/sector composition; exact challenge dates and counts; top-date and top-name influence; leave-one-date/issuer out; technology versus other-sector results; first-challenge observability; and actual-window gap/basis sensitivity. Do not use a parent flag as proof of source truth. Results disappearing outside one shock/name/source era are fragile, not robust alpha.

**Kill the tested return-alpha construction** when a sufficiently precise interval excludes the 0.50-point relevance threshold, or a sufficiently precise controlled comparison shows that conditional-beta/reversal/path baselines remove its material increment. An attenuated point estimate with a wide interval is not a kill. A wide interval is inconclusive. A negative association is an adverse result, not permission to reverse the signal on the same history. A surviving tail effect warrants a separate tail-confirmation proposal, not a renamed return-alpha success.

Recommend prospective validation only after lawful data admission, complete result publication, positive primary effect at least 0.50 points, both specified intervals above zero, the explicit ΔMSE gate above with at least three estimable annual folds, and no dominant single-name/date or known data-bias explanation. A failed H7 limits the claim to a useful residual update, not a special shock-resilience state. Historical significance remains development; it cannot clear prospective or production authority.

## 12. Implementation acceptance and exact next gate

Before outcome execution, verify fixtures for: subject/dual-class exclusion; thin-sector abstention; membership/sector changes; ticker reuse; zero/stale/missing prices; terminal payoffs; irregular calendars; lag-only factor estimation; prefix-invariant state classification; first-event observability; no outcome columns in features; no C candle in labels; coefficient-free primary label and the shared-estimation-error null; fixed secondary forward beta ruler; H5 risk-set accounting; fold purge/embargo; and complete negative-result retention. Tests on synthetic fixtures prove these mechanics only, not empirical predictive value.

**Current gate: NOT_ADMITTED.** The inspected sector collector explicitly emits current labels and sets `era_correct=False`; the observed receipt has zero era-correct rows. The frozen experiment therefore has not run. Qualify existing historical classification/security sources first, then prices, controls and independent shock counts. Do not buy or build a new data plane by default. If the necessary substrate cannot be qualified, preserve this verdict and propose a separately authorized prospective source-qualified study. References are defined in SOURCE_REGISTER.md; source measurements are in SOURCE_DATA_AUDIT_2026-10-07.json.
