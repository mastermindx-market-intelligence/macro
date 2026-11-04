# OIF P1-P6 Family Preregistration V1

**Status: STAGE-S0 FAMILY BINDING.** This document fixes family identity, membership, per-pilot targets and eligibility
rules, the stage-seal protocol, family-wise multiplicity, the holdout boundary, per-study falsifiers and the prohibited
practices for the six OIF pilots P1-P6 treated as one family. It is **not** an accepted G3 preregistration of empirical
dates, **not** fitting or evaluation authority, **not** a power claim, and **not** a promotion. All empirical dates remain
null, exactly as in R21 section 7.

Family id: `OIF-PILOT-FAMILY-V1`. Stage: `S0_FAMILY_BINDING`. Design authority: ORCH-1 rulings F1-F14. Repository commit
of all inputs: `021af584204c9fb00ad516c2dbc9467503a84083`.

## 0. Status, scope and authority boundary

**0.1 What this document is.** It is the stage-S0 binding of six pilots as a single inferential family. Before any outcome
is read it states: which pilots are members; each member's target, feature, algorithm, loss, dependence block length and
screening margin; what evidence admits a member and what falsifies it; which seals precede which stage; how the six
one-sided decisions are multiplicity-controlled; where the untouched holdout begins; and what is prohibited.

**0.2 What this document is not.** It is not an accepted G3 preregistration of dates, not fitting or evaluation authority,
not a power claim and not a promotion. It fills no gate of R21 section 9 and authorizes no collector, store, job, order,
notification or production change.

**0.3 Design status of the underlying specification.** R21 is authored as "PRINCIPAL_PROPOSAL - 2026-10-03" and states:
"All numeric design choices below are proposals for principal adjudication, not validated optima or assertions of
available data/power." R23 section 1 records the later, narrower engineering-design acceptance: "The frozen files retain
their original `PRINCIPAL_PROPOSAL` authoring status and null empirical bindings; this companion is the later,
deliberately narrower engineering-design acceptance. It does not fill the still-unbound principal-and-owner empirical
seal." Every numeric design value in this document is quoted from R21 and is never altered here.

**0.4 Empirical dates (null, copied unchanged from R21 section 7, "Dates").**

```json
{
  "training_start": null,
  "training_fit_cutoff": null,
  "validation_start": null,
  "validation_end": null,
  "test_model_sealed_at": null,
  "test_start": null,
  "test_end": null
}
```

R21 section 7 ("Date status"): "BLOCKED_UNTIL_DATA_AND_PRINCIPAL_BINDING. No historical or future empirical dates are
asserted available here."

**0.5 Traceability rule.** Every requirement below traces either to a quoted INPUT sentence, cited by R21 section, or to
an ORCH-1 ruling in the frozen spec, cited by F-number. Nothing here is invented. Where a quantity is not established by
an INPUT it is recorded as null or as an open binding, never as zero and never as a default.

**0.6 Authority boundary.** This document grants no fitting, evaluation, power, promotion or production authority. R23
section 5, quoted: "No empirical dates, historical capture, owner acceptance, power result, production source repair,
actual fill access, model promotion, release or new operational authority is implied by this decision."

## 1. Family identity, membership and row-label reconciliation

### 1.1 Family identity and members

Family id: `OIF-PILOT-FAMILY-V1`. Stage: `S0_FAMILY_BINDING`. Exactly six members, fixed at S0 and never shrinking. A
blocked, unrun or invalid member keeps p=1 (R21 section 8).

| Member | Pilot | Feature id | Acceptance row | Target (R21 frozen proposals) | Algorithm / loss (R21 frozen proposals) |
|---|---|---|---|---|---|
| P1 | P1 | OIF01 | AC30 | Next 30-minute exact log high/low range | Linear incumbent offset; nonnegative range projection; squared loss |
| P2 | P2 | OIF04 | AC31 | Next 30-minute market/sector residual log return | Linear incumbent offset; squared loss |
| P3 | P3 | OIF19 | AC32 | Matched 20-session ACT/365F variance | Positive multiplicative incumbent offset; QLIKE |
| P4 | P4 | OIF22 | AC33 | Five-session residual return after a one-session skip | Linear incumbent offset; squared loss |
| P5 | P5 | OIF13 | AC34 | Next ten-minute ACT/365F variance | Positive multiplicative incumbent offset; QLIKE |
| P6 | P6 | OIF35 | AC35 | Actual full-fill cost within 60 seconds, conditional on fills | Nonnegative scalar incumbent offset; absolute loss |

The member set, feature ids, targets and algorithms are the R21 "Frozen proposals and real remaining gates" table. The
member-to-acceptance-row mapping is fixed by ORCH-1 ruling F3. The same R21 table records the estimand each member tests:
"One primary feature, target and augmentation algorithm is proposed per pilot. Coefficients are learned only on admitted
training data; no alternative feature, link, regularization or horizon is selected after seeing validation/test
performance. β=0 recovers the fixed B1-RI forecast."

### 1.2 Row-label differences against R21 (recorded, never silently reconciled)

Where an ORCH-1 row label and R21 differ substantively, R21 governs and this document uses R21's definition.

| Row | Difference from R21 (R21 governs) |
|---|---|
| AC30 / P1 | Row label "exact interval range label (next 30-minute exact log high/low range)" is consistent with R21 on horizon and quantity, but does not carry R21's inclusion of the start mark, the non-negativity, dimensionless and no-annualization conditions, or the R21 section 2 rule that a bar is usable only when wholly contained in the requested interval. |
| AC31 / P2 | Row label "signed-flow residual log-total-return target (next 30-minute market/sector residual log return)" renders the unit as "log-total-return" where R21 section 6 (P2) writes "residual total-return log increment", and does not state the market/sector residualization, the beta fit or the no-intercept rule of R21 section 5. |
| AC32 / P3 | Row label "H20 variance (matched 20-session ACT/365F variance)" does not state the R21 section 6 (P3) requirements that H is the same local time 20 NYSE sessions later, that the raw integrated variance and actual T_H are kept, and that a zero label is valid. |
| AC33 / P4 | Row label "borrow-adjusted call-put IV spread with a skipped (one-session skip) residual log-return target" puts the borrow-adjusted matched IV spread first, but in R21 that spread is the primary feature (`x=Raw-X_fee*beta_fee`), and the target is the residual return after the one-session skip. The row label also omits the entry-to-horizon endpoints and the exclusion of the formation-to-entry return. |
| AC34 / P5 | Row label "ETF fixed-inventory / shock-endpoint hedge-notional variance study (next ten-minute ACT/365F variance; one fixed inventory/shock scalar)" treats the fixed inventory/shock scalar and the endpoint hedge notional as the study, but in R21 they are the feature and the target is the realized variance. The row label does not state that R21 retains the unannualized sum and T, nor that other shocks and sign allocations are diagnostics only. |
| AC35 / P6 | Row label "raw relative spread plus ACTUAL full-fill cost within 60 seconds, conditional on actual complete fills": in R21 the raw relative spread is the feature (`x=RelSpread=(ask-bid)/M0`) and the actual full-fill cost is the sole empirical primary target. The word "plus" is not an R21 statement of two targets. |
| AC28, AC29 | No row-specific wording that differs from R21 section 1, R21 section 7 and R21 section 8. |

## 2. Pilot P1 (acceptance row AC30) - feature OIF01

**Target.** R21 section 6 (P1, "Label"), quoted: "H=t+1800 seconds; y=log(max eligible underlying price/min eligible
underlying price) over the exact interval, including S(t). y>=0, dimensionless, no annualization." The
interval-eligibility rule is R21 section 2 ("High low"): "A bar can be used only when wholly contained in the requested
interval; boundary fragments require the actual eligible events or an exact interval aggregate."

**Primary feature.** R21 section 6 (P1, "Feature"), quoted: "Raw `A=sum(q*m)/Vstock` over completed 15 minutes, same
root/window and known share units; RZ(A) supplies z. Vstock<=0 or a feed gap is unavailable. Unsigned complex legs remain
activity, with package/quality controls retained."

**Algorithm and loss.** R21 section 6 (P1, "B2"): "linear_offset, projected to nonnegative range as declared." R21 section
4 ("Linear offset"): "P1 predicts max(0,b1+beta*z); this declared nonnegative projection is part of the range algorithm,
not an undisclosed numerical rescue." R21 section 6 (P1, "Primary loss"): "(y-yhat)^2 in squared log-return range units."

**Block length.** R21 section 8 ("Block lengths sessions"): `"P1": 5` NYSE sessions.

**Screening margin.** R21 section 8 ("Margins"): "2% reduction in mean squared range error". Status: PRINCIPAL_PROPOSAL
(R21 section 8, "Margin status"; quoted in section 10.2).

**Eligibility witness (AC30).** "eligible events or exact interval aggregate"

**Falsifier (AC30).** "a boundary-overlapping bar supplies extrema"

**Void rule.** If the AC30 falsifier is observed, P1 is VOID: p=1, recorded as invalid, and never re-run under v1 with a
changed rule. The AC28 and AC29 witnesses and falsifiers (sections 8 and 9) bind this pilot on the same terms, and the
common population rule of R21 section 1 applies to P1 (section 8).

## 3. Pilot P2 (acceptance row AC31) - feature OIF04

**Target.** R21 section 6 (P2, "Label"), quoted: "H=t+1800 seconds; y is the exact market-and-sector residual total-return
log increment from the common residual_return contract." R21 section 5 ("Definition"), quoted: "For P2/P4,
y=r_stock-beta_M*r_SPY-beta_S*r_sector over the exact same endpoint interval; r values are total-return log increments.
The intercept from the beta fit is not subtracted." The benchmark mapping is R21 section 1 ("Sector benchmark rule"),
which states that "The source sector classification and its availability revision are required; unknown sector blocks the
P2/P4 residual target rather than being assigned retrospectively."

**Primary feature.** R21 section 6 (P2, "Feature"), quoted: "`D=sum classified a*q*m*Delta*S`; signed long-option delta
includes negative puts. Use RZ(D). Signing requires strictly preceding valid quotes and the pinned conservative
condition/package rule. Unknown and ambiguous exposure stays in OIF06, with unpriceable Greek mass separately unknown."

**Algorithm and loss.** R21 section 6 (P2, "B2"): "linear_offset without clipping or probability conversion." R21 section
6 (P2, "Primary loss"): "(y-yhat)^2, squared decimal log-return units."

**Block length.** R21 section 8 ("Block lengths sessions"): `"P2": 5` NYSE sessions.

**Screening margin.** R21 section 8 ("Margins"): "2% reduction in mean squared residual-return error". Status:
PRINCIPAL_PROPOSAL (R21 section 8, "Margin status"; quoted in section 10.2).

**Eligibility witness (AC31).** "strict quote/package/Greek and sector benchmark qualification"

**Falsifier (AC31).** "ask-side estimate called opening demand"

**Void rule.** If the AC31 falsifier is observed, P2 is VOID: p=1, recorded as invalid, and never re-run under v1 with a
changed rule. The AC28 and AC29 witnesses and falsifiers (sections 8 and 9) bind this pilot on the same terms, and the
common population rule of R21 section 1 applies to P2 (section 8).

## 4. Pilot P3 (acceptance row AC32) - feature OIF19

**Target.** R21 section 6 (P3, "Label"), quoted: "Matched ACT/365F RVar_H from the common twenty-session sampling path;
keep raw integrated variance and actual T_H. y=0 is valid in evaluation." R21 section 6 (P3, "Formation"), quoted:
"Nominal 09:35 ET; actual t satisfies the common ten-second delivery gate; H is the same local time 20 NYSE sessions
later." The sampling path is R21 section 2 ("Twenty session variance").

**Primary feature.** R21 section 6 (P3, "Feature"), quoted: "x=sigma_ATM(T_H)-sqrt(vhat_P,H), in decimal annualized
volatility; sigma is forward-ATM IV from linear interpolation of total variance over qualified strikes and expiries
bracketing actual T_H. No extrapolation. vhat_P is the training-only physical_HAR estimate. Use RZ(x); negative x is
valid."

**Algorithm and loss.** R21 section 6 (P3, "B2"): "positive_variance_offset: `v2=v1*exp(beta*z19)`. beta is fitted once by
the stated convex QLIKE solver; no additional smearing or intercept." R21 section 4 ("Positive variance offset"): "P3/P5:
`v2=v1*exp(beta*z)`, with beta in the fixed PRINCIPAL_PROPOSAL domain [-1,1]. Fit one beta by minimizing mean weighted
`[log(v1)+beta*z+y/v1*exp(-beta*z)]` on matured training records. No intercept. beta=0 exactly gives v1." R21 section 6
(P3, "Primary loss"): "QLIKE log(v)+y/v; paired differences only for inference."

**Block length.** R21 section 8 ("Block lengths sessions"): `"P3": 20` NYSE sessions.

**Screening margin.** R21 section 8 ("Margins"): "0.01 mean paired QLIKE loss improvement". Status: PRINCIPAL_PROPOSAL
(R21 section 8, "Margin status"; quoted in section 10.2).

**Eligibility witness (AC32).** "causal HAR/RI forecasts, matched units, mature labels"

**Falsifier (AC32).** "volatility residual treated as variance/probability"

**Void rule.** If the AC32 falsifier is observed, P3 is VOID: p=1, recorded as invalid, and never re-run under v1 with a
changed rule. The AC28 and AC29 witnesses and falsifiers (sections 8 and 9) bind this pilot on the same terms, and the
common population rule of R21 section 1 applies to P3 (section 8).

## 5. Pilot P4 (acceptance row AC33) - feature OIF22

**Target.** R21 section 6 (P4, "Label"), quoted: "After the explicit one-session skip, y is market-and-sector residual log
total return from S(a) to S(H), with all benchmark marks synchronized. Formation-to-entry return is not part of y." The
residual construction is R21 section 5 ("Definition"), quoted in section 3.

**Primary feature.** R21 section 6 (P4, "Feature"), quoted: "Pick the expiry nearest 30 calendar days within [21,45], tie
to earlier expiry. Match call/put strike; require |log(K/F)|<=.05 and at least three eligible pairs. Raw IV spread uses
weights (OI_C+OI_P)/sum pair OI, with OI revision available at formation. `x=Raw-X_fee*beta_fee`." and "Generate training
x as-of/cross-fitted; freeze evaluation projection. Use RZ(x) from daily formations." The nuisance design is fixed in the
same R21 paragraph: "The nuisance design order is exactly (1,b,b^2,Tbar,I_div,Spr_pair,log(F/S)); coefficients retain the
implied units. No sign flip is selected after outcomes."

**Algorithm and loss.** R21 section 6 (P4, "B2"): "linear_offset, no post-outcome sign or threshold choice." R21 section 6
(P4, "Primary loss"): "Squared residual-log-return error."

**Block length.** R21 section 8 ("Block lengths sessions"): `"P4": 20` NYSE sessions.

**Screening margin.** R21 section 8 ("Margins"): "2% reduction in mean squared residual-return error". Status:
PRINCIPAL_PROPOSAL (R21 section 8, "Margin status"; quoted in section 10.2).

**Eligibility witness (AC33).** "Friday/calendar rule and one-session skip"

**Falsifier (AC33).** "formation-to-entry return included, or date shifted opportunistically"

**Void rule.** If the AC33 falsifier is observed, P4 is VOID: p=1, recorded as invalid, and never re-run under v1 with a
changed rule. The AC28 and AC29 witnesses and falsifiers (sections 8 and 9) bind this pilot on the same terms, and the
common population rule of R21 section 1 applies to P4 (section 8). The formation rule the AC33 witness refers to is R21
section 6 (P4, "Formation"), quoted: "Friday 15:30 ET only when that regular session exists and actual t passes delivery.
No Thursday substitute on Friday holidays/half days." and "Entry a is the same local clock as t on the next NYSE session;
H is that same clock five NYSE sessions after a."

## 6. Pilot P5 (acceptance row AC34) - feature OIF13

**Target.** R21 section 6 (P5, "Label"), quoted: "Horizon endpoint t+600 seconds; annualized realized variance from ten
one-minute log-return increments under the common intraday variance rule." R21 section 2 ("Intraday variance"), quoted:
"For H=t+600 seconds, take marks at t,t+60,...,t+600; sum the ten squared total-return log increments. Annualized
RVar=sum(r^2)/T, T=600/(365*86400). Keep the unannualized sum and T. Zero realized variance is valid."

**Primary feature.** R21 section 6 (P5, "Feature"), quoted: "At each session 09:35, freeze the selected same-day contract
book with |log(K/F_09:35)|<=.05 and positive prior-reported OI, using known reference identities. `h_call=+OI_call and
h_put=-OI_put` is the sole PRIMARY inventory scenario. It is not claimed to be dealer inventory." and "Raw H is USD
endpoint hedge notional. RZ(H) is an explicitly versioned model-input transform, not a change to OIF13 raw units. Other
shocks and sign allocations are diagnostics, not additional primary forecasts."

**Algorithm and loss.** R21 section 6 (P5, "B2"): "positive_variance_offset with the same one-coefficient convex solver
and fixed domain." The solver and its fixed domain are R21 section 4 ("Positive variance offset") and ("Variance solver"),
quoted in section 4. R21 section 6 (P5, "Primary loss"): "QLIKE of positive v1/v2 against nonnegative realized variance."

**Block length.** R21 section 8 ("Block lengths sessions"): `"P5": 5` NYSE sessions.

**Screening margin.** R21 section 8 ("Margins"): "0.01 mean paired QLIKE loss improvement". Status: PRINCIPAL_PROPOSAL
(R21 section 8, "Margin status"; quoted in section 10.2).

**Eligibility witness (AC34).** "numerical domain and fixed ETF population"

**Falsifier (AC34).** "assumed exposure relabeled actual dealer holdings"

**Void rule.** If the AC34 falsifier is observed, P5 is VOID: p=1, recorded as invalid, and never re-run under v1 with a
changed rule. The AC28 and AC29 witnesses and falsifiers (sections 8 and 9) bind this pilot on the same terms. P5 retains
its separate fixed population, R21 section 6 (P5, "Universe"), quoted: "SPY, QQQ and IWM; same-day still-tradable
contracts only. One hedge underlying/currency per observation."

## 7. Pilot P6 (acceptance row AC35) - feature OIF35

**Target.** R21 section 6 (P6, "Label"), quoted: "Primary empirical target is observed quote-to-fill implementation
shortfall for an order fully filled by t+60 seconds: `y_bps=10000*(a*(VWAP_actual_fills-M0)/M0 + actual_fees/(q*m*M0))`.
Fill events/fees come from independent actual execution records. Negative price-improvement costs are valid.
Partial/unfilled/cancelled orders have explicit categorical outcomes, no invented full-order slippage. Report the primary
cost result as conditional on full fills and report that selection/coverage; it is not unconditional execution policy
value."

**Primary feature.** R21 section 6 (P6, "Feature"), quoted: "x=RelSpread=(ask-bid)/M0. Keep raw dimensionless x and
quote/depth metadata. For this cost model, no RZ is used; x is the published raw OIF35 scalar."

**Algorithm and loss.** R21 section 6 (P6, "B2"), quoted: "One nonnegative through-origin offset coefficient:
`yhat2=yhat1+beta*x`; fit `beta>=0` by weighted median of `(y-yhat1)/x` with weights `w*x` over `x>0` training rows, then
take `max(0,that median)`. This is the exact one-dimensional L1 optimum on the declared domain, no intercept/tuning.
beta=0 recovers B1. If the weighted-median minimizer is an interval, choose its smallest nonnegative minimizer; record
nonuniqueness." R21 section 6 (P6, "Primary loss"): "Absolute error in option-premium basis points against actual
full-fill cost. Proposed useful margin: 5 basis points MAE improvement."

**Block length.** R21 section 8 ("Block lengths sessions"): `"P6": 5` NYSE sessions.

**Screening margin.** R21 section 8 ("Margins"): "5 basis points of initial option premium reduction in mean absolute
execution-cost error". Status: PRINCIPAL_PROPOSAL (R21 section 8, "Margin status"; quoted in section 10.2).

**Eligibility witness (AC35).** "independent fills/fees for a frozen full-fill population"

**Falsifier (AC35).** "NBBO or simulation used as actual fills"

**Void rule.** If the AC35 falsifier is observed, P6 is VOID: p=1, recorded as invalid, and never re-run under v1 with a
changed rule. The AC28 and AC29 witnesses and falsifiers (sections 8 and 9) bind this pilot on the same terms. The
formation rule is R21 section 6 (P6, "Formation"), quoted in part: "Actual consumer order decision t with frozen side a in
{-1,+1}, requested q>0, exact contract, fees and decision NBBO M0"; the same R21 paragraph sets the displayed-size,
quote-age and last-tradable-time conditions at the decision clock. P6 keeps its separate order population and is not
folded into the P1-P4 population (section 8).

## 8. Population and history (acceptance row AC28)

**Eligibility witness (AC28, all pilots).** "original PIT cohort and availability receipts"

**Falsifier (AC28, all pilots).** "current board used as historical universe"

**8.1 Point-in-time universe only.** The historical universe at every formation clock comes only from point-in-time cohort
and availability receipts (R21 section 1). R21 section 1 ("Primary stock rule"), quoted: "For P1-P4, take US common stocks
in the latest causally consumer-admitted incumbent buy-pool revision available at formation, then apply the fixed
source/reference/liquidity/contract gates below." R21 section 1 further states: "Never use the current 69-row board as a
historical universe." The current board, and any current cohort including the 26-root core cohort observed in
`live_flow.meta/v2` on 2026-10-30 (ORCH-1 ruling F6), is never the historical universe. R21 section 1 ("Identity and
age"), quoted: "Missing/unknown board revision, unknown receipt, ambiguous effective age or all-missing incumbent
covariates => unavailable, never confirmed absence."

**8.2 Separate histories.** Development, training, validation and untouched-test histories are separate and never overlap.
R21 section 7 ("Purge"), quoted: "Every observation used for any fitting, nuisance estimation, tuning, selection or
calibration must have label_mature_at <= that stage cutoff. Remove training labels overlapping validation. Also wait for
all validation labels used for planning to mature before sealing the final test; specifically exclude the H20 validation
tail from influencing an earlier test model. Use exact [label_start, label_end] intervals, not a guessed fixed gap. The
same boundary logic applies at every historical cross-fit cutoff."

**8.3 Already-observed data is development evidence.** Any data already observed by any party before the S3 seal,
including the 2017-2025 outcomes recorded under #8286, is development evidence and never an untouched holdout. R21:
"Preserve #8286 and its registered nulls. Its 2017-2025 outcomes are development evidence, never an untouched confirmatory
holdout. No completed study is rerun here."

**8.4 Captured point-in-time versus reconstructed history.** R21 section 1 ("Reconstruction"), quoted: "Captured-PIT and
reconstructed training history stay distinct. Reconstructed history may support model development when declared, but
cannot establish historical operational performance. Final confirmatory decisions and B1/B2 artifacts require captured-PIT
evidence."

**8.5 Missingness is not zero.** R21 section 2 ("Missingness"), quoted: "No missing label becomes zero and no incomplete
path is rescaled." All scheduled, eligible, forecasted and labelled counts stay visible.

**8.6 Separate populations.** P5 retains its fixed ETF scenario population and P6 its separate existing-order population
(R21 section 1, "Execution population"). Neither is converted into the P1-P4 population, and neither is widened by a
current cohort.

## 9. Stage seals (acceptance row AC29)

**Eligibility witness (AC29, all pilots).** "training, then frozen validation; mature losses; fixed test N before test
outcomes"

**Falsifier (AC29, all pilots).** "power required before its inputs exist, or test outcomes used to plan N"

**9.1 Seal protocol.** Four seals apply. Each seal is a sha256 over a frozen artifact and is recorded BEFORE the next
stage reads any data of that stage.

- **S0 family binding.** This document, `OIF_P1_P6_FAMILY_PREREG_V1.md`. Its sha256 and byte count are recorded in
  `OIF_P1_P6_FAMILY_PREREG_V1.seal.json` under schema `oif.family_prereg_seal/v1` and stage `S0_FAMILY_BINDING`. Nothing is
  fitted, simulated or evaluated before S1.
- **S1 training seal.** Covers the exact training window, the dataset manifest, the features, the nuisance/scaler procedure
  and the algorithm exactly as R21 section 4 specifies. Recorded before any fit.
- **S2 frozen-model seal.** Covers the fitted models and scalers, frozen at `training_fit_cutoff`. Recorded before any
  validation label is read.
- **S3 test seal.** Covers the frozen test plan: each pilot's N fixed by the R21 section 8 power rule run on validation
  losses only, and `test_start` fixed. Recorded before any test-window outcome exists or is viewed.

**9.2 Construction of the S3 seal, in order.** (1) All validation labels used for planning have matured; R21 section 8
("Power"): "Power is planned only after all validation labels mature, and no power number is asserted here." (2) The R21
section 8 power rule is run on validation losses only; power is never computed or required before its inputs exist. (3)
Each pilot's N is fixed inside the planning limits of 126 to 504 NYSE sessions; R21 section 7 ("Length"), quoted: "Before
any test outcomes, set N from the power rule with a principal-proposed lower bound 126 and upper bound 504 NYSE sessions.
These are planning limits, not promised duration or sufficiency. If required N exceeds 504, label the confirmatory pilot
infeasible/underpowered under v1; do not pretend the upper bound is adequate. Each pilot may bind its own N before its
test starts; the six-test multiplicity family remains fixed." (4) If the required N exceeds 504, the pilot is
INFEASIBLE_UNDERPOWERED under v1, keeps p=1, and enters no test window. (5) `test_start` is fixed. (6) The S3 seal is
recorded before any test-window outcome exists or is viewed.

**9.3 Constraints that attach to the seals.** Power is never computed or required before its inputs (matured validation
losses) exist, and test outcomes are never used to plan N. There are no interim efficacy looks, no automatic refits and no
post-validation refit in v1. R21 section 7 ("Validation"), quoted: "Validation is for pipeline audit, support/domain
checks and pretest variance/power planning, not feature, coefficient-bound, loss or hyperparameter selection. No
post-validation refit in v1. A changed algorithm creates a newly sealed version and a new untouched test." A changed
algorithm is therefore a new version with a new untouched test, never a repair of this one under v1.

## 10. Multiplicity and family-wise inference

**10.1 One family, six one-sided decisions.** The primary test is one-sided. R21 section 8 ("Test"), quoted: "Test
one-sided H0 E[g_d]<=0 with the exact centered-bootstrap p-value above." The six one-sided p-values of
`OIF-PILOT-FAMILY-V1` enter one Holm step-down. R21 section 8 ("Test"), quoted: "Apply Holm step-down to the six p-values
sorted ascending, ties by pilot ID: reject sequentially only while p_(k)<=.05/(7-k), k=1,...,6, stop at the first failure.
Unrun, blocked or invalid pilots keep p=1; the family never shrinks. Existing #8286 BH results remain a different family.
No interim efficacy looks or alpha recycling." Family-wise alpha is 0.05. A blocked, unrun or invalid member keeps p=1 and
the family does not shrink. The #8286 BH family is a different family, and there is no alpha recycling across families.

**10.2 Margin status.** R21 section 8 ("Margin status"), quoted: "PRINCIPAL_PROPOSAL statistical screening margins, not
established economic utility or validated optimal thresholds. The principal must accept/revise them before validation/test
outcome-driven decisions. Decision utility/policy promotion requires separate stakeholder costs and authority." The
margins quoted in sections 2 to 7 keep this status; this document does not revise, promote or validate any of them.

**10.3 Incorporated reference.** The R21 section 8 text at blob `db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0` is incorporated
by reference and bound by this seal. The definitions of the bootstrap resampling, the centered one-sided test, the
deterministic counter-mode SHA256 randomness, the percentile intervals, the power screens and the power simulation are
cited here by R21 section reference rather than restated, so that this document cannot drift from them. Implementers of
stages S1 to S3 must read them in R21 section 8 as bound by this seal. R21 section 4 (algorithm, numerical domain and
refusal rules), R21 section 7 (split, purge and frozen model lifetime) and R21 section 9 (availability and authority
gates) are incorporated the same way.

**10.4 Dependence and weighting.** The evaluation weights and the block construction are R21 section 8 ("Loss
aggregation", "Bootstrap"), bound by reference under 10.3. Dates without eligible paired outcomes are missing positions,
never zeros.

## 11. Holdout boundary, prohibitions and open gates

**11.1 Holdout boundary.** The untouched test window for each pilot begins at the first full NYSE session after BOTH its
S3 seal and acceptance of all gates G0-G6 (R21 section 9). No session on or before the S3 seal timestamp may enter any
test window. Operational source failures during the test are recorded without viewing comparative losses; pausing cannot
select days. R21 section 7 ("Test"), quoted: "First full session after all
capability/source/authority/principal/model/validation-label gates are accepted, then the precommitted number of NYSE
formation sessions N. Primary v1 has one final test and no interim efficacy looks or automatic refits. Operational source
failures are recorded without viewing comparative losses; pausing cannot select good-return days."

**11.2 Prohibitions.** These rules bind every stage of every member of `OIF-PILOT-FAMILY-V1`.

1. No calibration floor. Calibration is UNAVAILABLE under the accepted D13/Q01 O-A decision as recorded in ORCH-1 ruling F10.
   No newly invented support floor is introduced, and no derived S1 support floor is imposed on the six pilots.
2. No universal sample floor. The R21 section 7 fit-domain minima are carried only as per-pilot PRINCIPAL_PROPOSAL fit-domain
   eligibility. They are explicitly not a universal sample floor, not a sufficiency claim and not a power guarantee. N comes
   only from the S3 power rule.
3. No P6 simulated fill. Catalogue quote coverage and simulated hedged markouts are diagnostics only. If actual complete
   fills are unavailable, P6 is unrun with p=1 and never becomes a simulation-trained cost model (R21 P6 disposition). NBBO
   is never a fill.
4. No promotion. No member result promotes a model, signal or product state. Decision utility or policy promotion requires
   separate stakeholder costs and authority (R21 section 8 margin status).
5. No dealer predictive claim. P5 measures an assumed fixed inventory/shock scalar, never actual dealer holdings.
6. No ranking, sizing or trade language anywhere in this document. The prohibition governs this document's own assertions and
   framing. Source text quoted from R21 in sections 2 to 8 and section 10 is reproduced as quotation and is not an assertion
   of this document; where a quoted R21 sentence would carry such vocabulary outside its defining content, this document
   quotes the defining sentences and cites the R21 section for the remainder.
7. #8286 registered nulls are preserved; #8385 (REVISE) stays with its original author; this document reruns nothing.

**11.3 Gates G0-G6 (OPEN; copied verbatim from R21 section 9).**

| Gate | Owner | Required evidence | Blocked claim/work |
|---|---|---|---|
| G0 | Principal and incumbent research owner | Accept or amend the PRINCIPAL_PROPOSAL design, P6 catalogue disposition, useful margins and exact input/output identities before any trial is sealed. | All confirmatory fitting/evaluation authority |
| G1 | WS:ADVANCED-DATA-OPTIONS and WS:INTRADAY-FLOW-P0-RECOVERY | Current entitlement/resource, natural-session data, condition/correction/reference, arbitrary-interval label sampling and source/consumer clocks qualify for the named universe. | Affected pilot/source rows; no provider login/collector dispatch authorized here |
| G2 | Incumbent Prophet/OA owner | Accept the exact Appendix A RI adapter and supply causal incumbent snapshot/history receipts for it. Audit B0 lineage, selection and exact board/run/revision identity. No native forecast is assumed. | Primary incumbent incremental claim |
| G3 | WS:OPTIONS-CONTEXT-AUDIT-PREREG-V2 | Bind actual train/validation/test dates, histories, primary family, overlap/maturity manifest, exact scaler/nuisance artifacts and power-planned N. | Accepted preregistration and confirmatory run |
| G4 | Incumbent analytical/numerical owner | Accept relevant model/Greek/deliverable/clock/scenario numerical fixtures under exact source heads; no false-floor or unsigned-position substitution. | P2 Greek-dependent rows, P3/P4 surfaces, P5, P6 Greek diagnostics as applicable |
| G5 | WS:OPTIONS-ALPHA-INTELLIGENCE-RECOVERY | Authorize read use of existing order/fill/fee records and the distinct exact-option policy contract. No inherited candidate authority escalation. | P6 empirical target; absence leaves numerical/observational work only |
| G6 | Principal/research reviewer | Pass pretest finite-domain/source/coverage checks and power feasibility without test-outcome inspection. | Confirmatory seal; unmet gates are explicit findings, not automatic retries or fallback models |

**11.4 Still unbound (copied verbatim from R21 section 9).** `principal_adjudication_receipt`,
`incumbent_owners_acceptance_receipts`, `source_capability_receipt`, `B0_lineage_manifest`,
`B1_RI_adapter_and_snapshot_receipts`, `dataset_manifest`, `split_date_manifest`, `power_planned_test_lengths`,
`accepted_trial_id`. "Null values are intentional gates, not defaults that an implementation may guess."

**11.5 This document fills none of them.** No gate above is accepted, filled or partially filled by this document, and no
null binding above is guessed or defaulted.

## 12. Blindness and how it was enforced

- Authored by Mastermind Fabric lane `oi1-l3a-r1` (leaf; root `a1c77f0e-56b9-4edf-8d4f-3d31a338a8ed`; parent
  `oi-a1c77f0e-orch1`) from INPUTS inlined in its packet: R21 `PILOT_STUDY_SPEC_V1.md` blob
  `db8c9ce40b46a1e5cefc7983ded5c6faedc3cfb0`, R22 `pilot-study-spec.v1.json` blob
  `fc00aa33b11c26be9fa0ca6a4b7c0280f73dab81`, R23 `PRINCIPAL_DECISIONS_20261003.md` blob
  `5b5c6e5770481d568f458f867629d6b9ad58465e`, all at repository commit `021af584204c9fb00ad516c2dbc9467503a84083`.
- The authoring lane was forbidden from reading any repository, data store, results/outcome table, report artifact,
  parquet/csv file or network resource; its packet contained no outcome, untouched-test or holdout values.
- The framing orchestrator read specification documents only and no outcome tables before this seal.
- Enforcement is audited after the fact: ORCH-1 inspects the lane's retained Fabric log for any read outside the inlined
  inputs, and an independent Fabric review on a different pool/model attacks the document and the blindness claim. The audit
  result does not exist yet and is not claimed here.
