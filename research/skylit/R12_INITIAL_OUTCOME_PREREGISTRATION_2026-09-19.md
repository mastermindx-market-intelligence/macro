# Skylit Program — R12 Initial Daily Outcome Preregistration

**Date:** 2026-09-19  
**Status:** `FREEZE_CANDIDATE / OUTCOME_LABELS_CLOSED / REVIEW_REQUIRED`  
**Authority:** research-only. No rank, gate, size, signal, portfolio, Prophet, training, or trade authority.  
**Parent:** Macro #7298, R12 contract comment `5728941113`  
**Research source parent:** Macro #7035 / `research/skylit/`

## 0. Purpose

This artifact freezes the **first daily outcome-study grammar before any target values are opened**.

It does not claim an edge and does not register QLedger claims. Mastermind's current house law still treats hypothesis preregistration as a reviewed research artifact; QLedger remains the owner of actual emitted market claims/grades after lawful evaluation.

At authoring time:

- no future OHLC outcome series was loaded for these families;
- no target correlation, return, range, efficiency, win rate, threshold, subgroup, or effect size was inspected;
- no feature threshold below was selected from future outcomes;
- constructors remain Draft/HOLD until their own source/proof gates clear.

The goal is to make later falsification harder to game.

---

## 1. Source constructors this prereg may eventually consume

| Family | Constructor owner | Current dependency state | Outcome status |
|---|---|---|---|
| R2-D1 | Macro #7310 — settled exposure-change decomposition | Draft/HOLD; real-store + independent review still required | CLOSED |
| R6-D1 | Macro #7322 — cross-expiry topology | Draft/HOLD; dependent on R2; stack reconciliation currently requires exact-carrier proof | CLOSED |
| R5-D1 | Macro #7327 + Terminal #645/#646 + Macro #7402 | Producer/consumer/scenario/PIT components exist but integration is not accepted | CLOSED / DEFERRED |
| R4-D1 | Macro #7410 | Constructor exists but depends on R6 acceptance | DEFERRED |
| R8 market-outcome family | Macro #7415 | Daily position evidence construction only | DEFERRED |

No family may open target values merely because its source PR becomes green.

---

## 2. Clock law — the first non-negotiable anti-leak boundary

### 2.1 Feature-effective session is not decision availability

For R2/R6 daily settled state:

- market-effective structure is session `S`;
- settled EOD-S position is learned from OI published on next NYSE session `D = next_session(S)`;
- current source receipts bind **decision eligibility at session precision**, not an exact pre-open timestamp.

Therefore this prereg **does not** assume the feature was knowable before the open of D.

For version 1, the research decision cutoff is conservatively **after session D has completed**. Any PIT price controls may therefore use bars through D close; no information from target session T may enter.

### 2.2 Primary outcome session

For any sample whose feature receipt says:

`decision_eligible_not_before_session = D`

the first eligible target session in this prereg is:

`T = next_session(D)`.

Thus a settled R2/R6 state effective through S normally targets **S+2 NYSE sessions**, not S+1.

This is intentionally conservative.

If a later source owner proves an exact availability timestamp before D open, a new prereg version may study D. This version is never retroactively relabeled.

### 2.3 Eligibility assertion

Every sample must prove before target values are read:

`feature_decision_eligible_session < target_session`.

If only an ambiguous/missing clock exists, the sample is unavailable, not zero.

---

## 3. Independent daily target grammar

Target session is T from §2.

No target source is bound yet. Before ACCEPTED_PREREG, review must bind one existing canonical PIT daily-OHLC owner and its correction/version behavior.

### T1 — next-session range percent

`range_pct_T = 100 * (high_T - low_T) / open_T`

Eligibility:

- O/H/L are finite;
- `open_T > 0`;
- `high_T >= low_T`.

Otherwise null with reason.

### T2 — next-session OHLC directional-efficiency proxy

`ohlc_efficiency_T = abs(close_T - open_T) / (high_T - low_T)`

Eligibility:

- O/H/L/C finite;
- `high_T > low_T`.

Range: `[0,1]`.

This is explicitly an **OHLC proxy**, not intraday path efficiency and not a whipsaw count.

### T3 — signed open-to-close return (secondary only)

`oc_return_pct_T = 100 * (close_T - open_T) / open_T`

This is secondary and cannot rescue a failed primary family.

### 3.1 Primary version-1 cohort/source candidate

The first review candidate is deliberately narrow and does not mix price providers.

Fixed root set:

`SPY, QQQ, IWM, XLB, XLC, XLE, XLF, XLI, XLK, XLP, XLRE, XLU, XLV, XLY`.

Target/control price plane candidate:

- owner/producer: existing `scripts/fetch_basket_ohlcv.py` collection path;
- store: `data/baskets/ohlcv/<ROOT>.parquet`;
- schema: daily `open, high, low, close, volume`;
- current source basis: yfinance auto-adjusted full OHLC history;
- no per-root fallback to Massive/Yahoo/another store inside this family.

Why this is admissible for T1/T2/T3:

- all three targets are same-session **price ratios**;
- a common multiplicative adjustment to O/H/L/C cancels algebraically from these ratios;
- later cumulative adjustment-factor rewrites therefore do not create split/dividend level drift in the target definition itself.

This does **not** make arbitrary vendor corrections irrelevant. At execution, every consumed target row must bind the current file/content receipt; a material source correction creates a new scientific reconstruction while the original evaluation vintage remains auditable where required.

Roots lacking a valid bar for T are missing, not silently filled from another price plane.

SPX/SPXW are not part of this first target cohort. Index-root outcome studies require a separately bound canonical index OHLC owner.

This cohort/source remains `REVIEW_REQUIRED` until independent review confirms the exact current producer contract and receipt implementation.

### Target-source prohibition

Until the target owner/receipt and the cohort above are accepted in this prereg:

- do not materialize T1/T2/T3 values;
- do not calculate their distributions;
- do not inspect their correlation with candidate features;
- do not choose power/effect thresholds from them.

---

## 4. Chronological split law

The split operates on **unique feature-session dates**, not row-level contracts or roots, so the same market date can never appear in two eras.

After all source-only eligibility gates are applied and before target values are read:

1. sort unique eligible feature sessions ascending;
2. first 60% = training;
3. next 20% = calibration;
4. final 20% = untouched outer temporal test.

At each boundary:

- purge any feature session whose target session crosses the boundary;
- embargo one additional NYSE feature session on the later side.

All roots from one session inherit the same era.

No shuffled/random split is allowed.

A future prospective phase starts only after an outer-test verdict and a new recorded forward boundary.

---

## 5. Dependence / uncertainty law

Primary observational unit:

`root × feature_session`.

For pooled studies:

- report raw root-session N;
- report unique feature-session N;
- cluster uncertainty by session at minimum;
- report root-level heterogeneity;
- do not treat several index roots on one date as independent market regimes.

Subgroup results are descriptive unless explicitly preregistered.

---

## 6. Family R2-D1 — position-driven exposure change vs later range

**State:** `FREEZE_CANDIDATE / BLOCKED_ON_BASELINE_FIELD_AND_CONSTRUCTOR_ACCEPTANCE`

### Population

Source-qualified R2 consecutive settled-session pairs only.

Required source fields/receipts:

- `component_abs_share.position`;
- `component_abs_mass.position`;
- source input digests;
- method/sign tier;
- exposure unit;
- decision-eligible session;
- exact Shapley closure within the accepted tolerance;
- no unresolved source-quality refusal.

### Primary feature

`position_abs_share = component_abs_share["position"]`.

No thresholding; continuous only in the first study.

### Required raw-change baseline before acceptance

The scientific question is whether position attribution adds information beyond **raw map change**.

A net scalar can cancel across strikes, so `abs(raw_survivor_change_net)` is not a sufficient primary baseline by itself.

Before R2-D1 becomes ACCEPTED_PREREG, the R2 constructor must expose or reproducibly receipt-bind:

`raw_survivor_change_abs_mass = sum_contracts(abs(E1 - E0))`.

No future outcome is needed to add this descriptive field.

### Primary target

T1 `range_pct_T`.

### Primary hypothesis

The position-driven share contains incremental out-of-sample information about later range beyond raw absolute survivor-map change and frozen PIT controls.

This is an incremental-information hypothesis, not a directional claim that “more position change means up” or “means volatility.”

### Secondary target

T2 `ohlc_efficiency_T`.

Secondary only; cannot determine the family verdict.

### Baseline / controls

Version-1 candidate controls, all available no later than D close:

- `log1p(raw_survivor_change_abs_mass)`;
- 20-session close-to-close realized volatility through D;
- 5-session close-to-close return through D;
- root fixed effects for the frozen 14-root cohort.

No target-session information, target liquidity, or post-target control is legal.

The broad original R2 contract's liquidity question remains a later sensitivity arm; version 1 avoids an unreviewed historical dollar-volume adjustment convention.

---

## 7. Family R6-D1 — cross-expiry disagreement vs later directional efficiency

**State:** `FREEZE_CANDIDATE / BLOCKED_ON_R6_ACCEPTANCE`

### Primary coordinate for the first study

`log_moneyness` fallback mode.

Expected-move-normalized topology is a sensitivity arm only after a qualified expected-move receipt owner is accepted. This avoids smuggling arbitrary EM estimates into the first R6 outcome study.

### Population

Source-qualified R6 states where:

- R2 state is qualified;
- at least two expirations are present;
- the primary topology descriptors are finite;
- source/unit/sign receipts are valid.

### Primary feature

`max_adjacent_wasserstein_1_x`.

Continuous only; no “high disagreement” threshold in the first study.

### Primary target

T2 `ohlc_efficiency_T`.

### Directional hypothesis

Higher cross-expiry topology disagreement is associated with **lower** next-target-session OHLC efficiency after frozen controls.

### Secondary target

T1 `range_pct_T`.

### Simple baselines / controls

Version-1 candidate baseline/control block:

- `dominant_expiration_gross_share`;
- `abs(front_back_centroid_gap_x)` when defined;
- 20-session close-to-close realized volatility through D;
- 5-session close-to-close return through D;
- root fixed effects for the frozen 14-root cohort.

If R6 does not add stable value beyond this simpler state, the complex thesis is rejected for predictive use even if the visualization remains useful.

A scalar signed-GEX baseline may be added only if its exact accepted owner/unit/population is bound **before target values are opened**; it is not silently substituted later.

---

## 8. Family R5-D1 — scenario-conditioned Greek alignment

**State:** `RESERVED / DO_NOT_UNBLIND`

No R5 market target may be opened yet.

Reason:

- #646 evaluates one explicit scenario;
- #7402 constructs a PIT conditional spot/IV distribution;
- the accepted, receipted integration that converts the PIT distribution into a fixed R5 scenario family/probability-weighted alignment object is not yet frozen.

The eventual R5-D1 target is intended to be T2 `ohlc_efficiency_T`, with raw four-quadrant GEX/VEX sign state as a mandatory baseline.

A successor prereg version must freeze, before outcomes:

- exact shock grid;
- use of PIT conditional median/quantiles or probability weights;
- materiality normalization;
- position/sign tier;
- tenor summary;
- liquidity normalization;
- one primary R5 feature.

Do not choose these after seeing T2.

---

## 9. R4 and R8 outcome studies are explicitly deferred

### R4

R4 constructor acceptance depends on R6 and on qualified common-support/expected-move semantics. No whipsaw/range/efficiency outcome is opened under this artifact.

### R8

R8 daily V/OI -> later OI evidence is construction/evidence science, not a market-return claim.

No future price target is opened until:

- daily source completeness is independently reviewed;
- live T0–T4 flow evidence is separately source-qualified where applicable;
- package/aggressor uncertainty is preserved;
- a dedicated R8 outcome prereg is reviewed.

---

## 10. Feature scaling and model-family law

For R2-D1 and R6-D1 once accepted:

- continuous features remain continuous;
- continuous predictors are standardized from **training-era values only**;
- root fixed effects are categorical and not standardized;
- no threshold/bucket search on calibration or outer-test targets;
- no nonlinear/ML model in version 1.

### 10.1 Version-1 estimator candidate

Use fixed-form ordinary least squares with an intercept and frozen root fixed effects.

**R2 baseline M0**

`T1 ~ root_FE + z(log1p(raw_survivor_change_abs_mass)) + z(rv20_D) + z(ret5_D)`

**R2 augmented M1**

`M0 + z(position_abs_share)`

**R6 baseline M0**

`T2 ~ root_FE + z(dominant_expiration_gross_share) + z(abs(front_back_centroid_gap_x)) + z(rv20_D) + z(ret5_D)`

When front/back centroid gap is structurally unavailable because only one expiry exists, that sample is not R6-D1 eligible.

**R6 augmented M1**

`M0 + z(max_adjacent_wasserstein_1_x)`

Training fits coefficients/scalers. Calibration is used only as a sealed implementation/reliability check; it may not select features, transformations, thresholds, roots, or model family. After calibration is opened, any material model change requires a new prereg version and a future outer-test boundary.

### 10.2 Primary predictive comparison candidate

On the untouched outer era:

- compute paired absolute errors for M0 and M1 by root-session;
- primary metric = relative MAE improvement `(MAE_M0 - MAE_M1) / MAE_M0`;
- uncertainty = session-block bootstrap of the paired error difference, keeping all roots from a session together.

Mechanism diagnostics:

- R2 added coefficient is reported with session-clustered robust uncertainty;
- R6 added coefficient must have the preregistered **negative** sign for its directional hypothesis.

No p-value, coefficient, or secondary target can rescue a primary outer-test failure.

### 10.3 Practical-improvement threshold

Candidate review threshold: point relative-MAE improvement >= **2%** and the 95% session-block bootstrap interval for the paired MAE improvement excludes zero in the favorable direction.

This 2% floor is **not accepted yet** and may be changed by independent review only while target values remain closed. Once any target value is opened, it cannot be lowered.

No outcome values may be opened to choose the estimator or practical threshold.

---

## 11. Multiple-testing budget

Version 1 allocates:

- one primary hypothesis/target for R2-D1;
- one primary hypothesis/target for R6-D1;
- R5-D1 reserved but unopened;
- secondary targets are diagnostics only;
- exploratory subgroups cannot produce GO_PROSPECTIVE.

Any extra feature, threshold, horizon, interaction, coordinate, or subgroup inspected against outcomes enters a trial ledger and requires a new prereg version for promotion-bearing use.

Vendor claims (80/66/33 taps, 2/3 Trinity, Flow Score, etc.) are not labels and cannot be used as target truth.

---

## 12. Power / minimum-N gate

**Candidate, not accepted; target values remain closed.**

Before ACCEPTED_PREREG, source-only eligibility counts may be measured.

Version-1 candidate floor for opening the untouched outer test:

- >= 126 unique target sessions in the outer era;
- >= 500 evaluable root-session rows in the outer era;
- >= 8 of the frozen 14 roots represented;
- each represented root has >= 63 outer-era observations.

These are information floors, not evidence of power.

Independent review must additionally freeze a minimum-effect/power rationale using only:

- source-only eligible counts;
- root/session clustering structure;
- declared standardized minimum effect of interest;
- declared alpha/power.

It may **not** inspect target values, target variance, observed correlations, model errors, or feature/outcome effect estimates to relax the floor.

If the required information cannot be supported, the family is `INSUFFICIENT_POWER` or remains descriptive. The study does not shorten the outer era after seeing results.

---

## 13. Missingness / censoring

For every family report before results:

- source-eligible root-sessions;
- source refusals by reason;
- clock-ineligible rows;
- target-source missing rows after the target owner is bound;
- final evaluable rows.

Rules:

- missing is never zero;
- stale/corrected and as-known vintages remain distinct;
- source correction mints a new scientific reconstruction/version;
- same-session rows cannot silently move between eras;
- target missingness is not imputed from future data.

---

## 14. Outer-test verdicts

Only these R12 research verdicts are legal:

- `GO_PROSPECTIVE`
- `NO_GO`
- `INSUFFICIENT_POWER`

`GO_PROSPECTIVE` means only that a frozen prospective shadow phase may begin.

It does **not** grant:

- display claim escalation;
- ranking;
- gating;
- sizing;
- portfolio authority;
- Prophet/training authority;
- trade/execution authority.

Those remain separate owner decisions.

---

## 15. Negative-result durability

A failed family/version stays discoverable with:

- exact family ID/version;
- constructor/method receipts;
- eligible era;
- hypothesis;
- baselines;
- verdict;
- reason;
- material invalidators that could justify reopening.

A failed version is not silently retuned.

A materially different source/method/population requires a new version and a new future test boundary.

---

## 16. Acceptance gate for this prereg artifact

This document is **not yet the freeze**.

Before status may become `ACCEPTED_PREREG / OUTCOME_LABELS_CLOSED_UNTIL_EXECUTION`, independent review must resolve:

1. canonical target OHLC source owner + as-known/correction receipt;
2. exact first-version estimator + cluster-robust uncertainty method;
3. minimum-N/power rule using only source eligibility counts;
4. R2 raw absolute map-change baseline field;
5. R2/R6 accepted constructor revisions and exact source clocks;
6. no target values were opened before the accepted artifact/digest existed.

At acceptance, record:

- exact artifact commit;
- file SHA-256 or canonical Git blob identity;
- accepted constructor refs;
- accepted target-source receipt;
- accepted effective freeze boundary.

If any target values are opened before then, this candidate is contaminated and a new future boundary/version is required.

---

## 17. DO NOT REDO / DO NOT CONFLATE

Do not create:

- a generic preregistration database;
- a second QLedger;
- a second outcome warehouse;
- a new ranker;
- a new feature registry;
- a parallel market-price owner.

Do not call this document an edge, a validation, or a prospective result.

Its job is only to freeze the questions tightly enough that later evidence can falsify them.
