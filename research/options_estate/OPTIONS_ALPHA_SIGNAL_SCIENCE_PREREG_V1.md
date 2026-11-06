# Options Alpha Signal-Science Preregistration v1

**Date:** 2026-09-19  
**Operation:** `oa-signal-science-prereg-20260919-sol-001`  
**Parent:** `options-alpha-product-integration-20260917-sol-001`  
**State:** `PREREGISTERED_FIT_FREE / INACTIVE`  
**Machine policy:** `research/options_estate/options_alpha_signal_science_prereg_v1.json`

This is a research-control artifact. It does **not** fit a model or calibrator, run a market backtest, enable scoring, create a candidate, publish a probability, alter the exact-option ruler, or grant rank/size/gate/issue/trade authority.

## 1. Why this prereg exists

Packet B reproduced five method failures or ambiguities in the current Flow-Score path before any new fit:

1. the actual binary label is `1[spy_excess_H > 0]`, which is underlying outperformance versus SPY, not option-side success or option P&L;
2. the serving loader can concatenate `tape_recon` and `live_feed` even though the registered population law is source/version-specific;
3. the current embargo implementation uses calendar-day distance while the registered rulers are trading-session horizons, and current block assignment can split one session;
4. the calibration fallback can fit isotonic on rows that are later evaluated when the inner slice is one-class;
5. the local `deployable` predicate can pass calibration-health checks without satisfying the registered newest-era discrimination, multiple-testing and FS-5 acceptance laws.

Those are not reasons to tune a better model. They are reasons to freeze the scientific claim and evaluation geometry before any fit.

## 2. Scope and supersession

This preregistration preserves the existing sequence:

`Flow -> Package -> Positioning -> Candidate -> Outcome -> Calibration -> Decision Support`.

It does not replace OA-1T, campaign v2, #7290 candidate formation, the exact-option ruler, Evaluation/qledger, or the existing promotion owner.

For any future Flow-Score fit governed by this preregistration, it resolves only the method ambiguities below. It does **not** silently revise already published historical artifacts. Existing scoring remains disabled.

Where older Flow-Score prose uses a broader phrase such as “underlying-move outcome,” the first fit under this prereg must use the exact currently implemented registered target in §3 unless a separately reviewed target amendment lands first.

## 3. Target contract

Primary target by registered horizon:

`Y_H = 1[spy_excess_H > 0]`.

This means:

> Did the underlying outperform SPY over the registered forward horizon?

It does **not** mean:

- absolute positive return;
- a call or put was correct;
- the option made money;
- the event was bullish or bearish;
- a particular customer opened or closed;
- expected return or expected option P&L.

Registered primary horizons remain 5, 21 and 63 trading sessions for the current three DTE constructions. The existing 126-session secondary ruler for the long-DTE construction remains separately reported only where its own clean horizon exists.

Absolute return may be reported alongside for context but is not another decision target.

### SPY degeneracy

SPY against the identical SPY benchmark has zero excess by construction. Therefore SPY-root events are **not a legal two-class training/calibration/evaluation cell** for this target. They may remain descriptive evidence.

Changing the benchmark or target is a new preregistration event, never a trainer convenience.

## 4. Population contract

A fitted artifact has exactly one population key:

`(source, detector_version, DTE construction)`.

### Legal serving-distribution sources

- `tape_recon`
- `live_feed`

They may each support a model/evaluation cell when all other gates pass, but they are **not pooled into one fit or calibration set**.

`eod_proxy` remains prior/pretraining context only. It is never a calibration set or published OOS verdict population.

Cross-source generalization is a separately named transfer test. It cannot be implied by concatenating sources.

Mixed or missing detector versions fail closed.

### Root/generalization claim

The existing registered FS family is **root-disjoint and time-controlled per fold**.

Binding rule from the governing Flow-Score amendment:

- group folds jointly by underlying and time block;
- the same underlying may not appear in both train and validation within one registered verdict fold;
- time-block separation remains mandatory in addition to root separation;
- if the eligible population cannot form a root-disjoint fold, the registered verdict is **INSUFFICIENT_ROOT_DIVERSITY / not evaluable**;
- a single-root population does not gain a time-forward fallback for this existing family;
- a within-root time-forward analysis may be reported only as a secondary descriptive diagnostic under its own label and cannot substitute for the registered FS verdict.

Changing the family to permit same-root train/validation evaluation would require an explicit new amendment before fitting.

The inherited index-root policy remains in force: index roots are excluded by default, with only the already-registered prior-session OI admission where lawful; 0DTE index remains outside this family. SPY is additionally excluded from model cells under the SPY-excess target because of target degeneracy.

## 5. Trading-session leakage contract

Every temporal separation is defined in **canonical NYSE trading sessions**, not elapsed calendar days.

Binding rules:

- all observations from one trading session stay in the same split;
- training rows whose label windows overlap validation/evaluation label windows are purged;
- embargo is at least the target horizon in trading sessions;
- calibration fit and calibration evaluation also obey the horizon embargo;
- missing, malformed or unresolvable session identity fails closed;
- no split may invent a fallback session from array order.

A larger arbitrary calendar-day constant is not an acceptable substitute.

## 5A. Model-selection and effective-N contract

The governing FS amendment's model-selection law remains binding.

- Model / hyperparameter selection uses **Combinatorial Purged Cross-Validation (CPCV)** over the registered purged/root-disjoint/time-controlled geometry.
- A manifest may count CPCV selection paths only if those paths were actually executed under the frozen geometry.
- The final untouched OOS block participates in no selection path.
- Replacing CPCV with another selection geometry requires a new preregistration before fitting; silently running ordinary folds while counting combinatorial paths is invalid.

The existing uniqueness/effective-support law also remains binding:

- raw rows and effective N are separate quantities;
- overlapping label windows remain uniqueness-weighted;
- same-session / same-underlying dependence remains accounted for;
- sample floors apply to the registered effective support, not duplicated print count;
- a manifest field named `effective_n` may not be populated with raw `len(frame)`.

## 6. Calibration contract

Calibration is chronological and has two distinct slices:

1. earlier **calibrator-fit** slice;
2. later **calibration-evaluation** slice.

They are disjoint and separated by at least the registered target horizon in trading sessions.

If either slice is one-class, calibration is `CALIBRATION_NOT_EVALUABLE`.

The current whole-calibration-set isotonic fallback is not allowed for a future accepted fit because it trains on rows later used to assess calibration.

Existing calibration diagnostics remain inherited where registered:

- ECE;
- Brier versus natural-prevalence base rate;
- reliability monotonicity.

Passing those diagnostics is not statistical acceptance.

## 7. Monotone constraints

No feature-level monotonic constraint is accepted by default for this target.

A future monotonic feature constraint requires a separate exact registration naming:

- the feature or transformed feature;
- the target;
- the mechanism that makes the sign defensible;
- the population where it is claimed.

Calibration **reliability monotonicity** remains a calibration diagnostic. It is not authority to impose monotonic feature effects in the predictive model.

## 8. Four states that must never collapse

### ARTIFACT_HEALTHY

The artifact can be read, hashes/config are coherent, and its local technical/calibration-health checks pass.

This is the maximum meaning of the current local `deployable` concept under this preregistration.

It grants no probability or alpha authority.

### EVALUATION_READY

In addition to artifact health:

- target is registered;
- one legal source/detector-version population is frozen;
- PIT/availability rules hold;
- trading-session splits are valid;
- session atomicity holds;
- calibration fit/eval isolation holds;
- target/root support is non-degenerate.

### STATISTICALLY_ACCEPTED

All separately registered OOS-cell, newest-era discrimination, calibration, effective-N, family/multiple-testing and FS-5 acceptance laws pass.

This prereg does not weaken the existing newest-era AUC kill, BH-FDR family accounting, N floors, or amend-on-add law.

### PROMOTION_ELIGIBLE

A separate explicit decision by the existing promotion authority accepts a bounded use.

Statistical acceptance alone cannot rank, gate, size, issue or trade.

## 9. Source repairs that become lawful after this prereg is accepted

An existing authorized FS/Evaluation writer may then make the smallest code/test corrections required to satisfy this frozen method contract:

- fail closed on mixed source or detector version;
- use canonical trading-session purging/embargo instead of calendar-day distance;
- keep sessions atomic across splits;
- fail closed with insufficient root diversity when the registered root-disjoint fold cannot be formed;
- make calibrator-fit/eval chronological, disjoint and embargoed;
- remove the whole-calibration one-class isotonic fallback;
- separate artifact-health status from statistical-acceptance status;
- execute the registered CPCV selection geometry if it is claimed/counts toward trial accounting, otherwise fail closed until a new preregistration changes the geometry;
- report actual effective N separately from raw row count.

Those repairs do **not** authorize a model fit, calibrator fit, market backtest, scoring enablement or promotion. Fit/evaluation execution requires its own later admitted operation after the repair is reviewed.

## 10. Existing safeguards and kills remain binding

Preserve:

- `eod_proxy` exclusion from serving calibration/OOS verdicts;
- missing benchmark labels remain missing;
- missing outcomes remain null;
- duplicate/concurrent-event weighting;
- `scoring.enabled=false`;
- accepted OA-1T source carriage and natural measured evidence as DO_NOT_REDO.

No resurrection without a material invalidator plus explicit new adjudication:

- `KILL-DOI-FAMILY`;
- `KILL-SKEW-DECELERATION`;
- `KILL-CHARM-NARRATIVES`;
- suspended tick-rule tape direction;
- generic fused positioning/composite authority;
- LLM origination;
- off-horizon verdicts.

## 11. Relationship to #7290 and Tactical Intelligence

This preregistration does not change #7290 candidate formation.

Candidate formation answers whether a canonical options campaign becomes a zero-authority research candidate. This document answers how a later statistical family may be evaluated without leakage or label ambiguity.

Likewise it does not originate Tactical/Radar events. Any eventual options contribution to Tactical still has to show incremental value over that program's frozen price-first baseline.

## 12. Fit-free acceptance tests for the later implementation

Before any fitting operation is admitted, code tests must prove at least:

- `tape_recon + live_feed` mixed input refuses rather than pools;
- different detector versions refuse;
- SPY under the SPY benchmark is rejected from a two-class model cell;
- one complete session cannot be divided across folds;
- a Friday-to-Monday boundary uses trading-session distance, not three calendar days;
- overlapping H-session label windows are purged;
- malformed/missing session dates refuse rather than fall back;
- a single-root population returns `INSUFFICIENT_ROOT_DIVERSITY` for the registered FS verdict rather than falling back to same-root train/validation;
- every reported CPCV selection path is actually executed under the registered purge/root/time geometry and the final OOS block is absent from selection;
- `effective_n` is not a raw row-count alias, and repeated same-session/same-root prints cannot inflate the registered N floor;
- calibrator-fit rows are strictly earlier than evaluation rows with H-session separation;
- one-class fit or eval slice returns `CALIBRATION_NOT_EVALUABLE`;
- no fallback fits isotonic on the union of fit+evaluation rows;
- an artifact that passes ECE/Brier/reliability but fails the registered newest-era discrimination gate is not `STATISTICALLY_ACCEPTED`;
- no readiness/acceptance state enables production scoring while `scoring.enabled=false`.

## 13. Completion boundary

Merging this preregistration would freeze the research method only.

It would **not** make Flow Score statistically accepted, Options Alpha functional, OA-1C active, or any option/Tactical decision support valid.

The first implementation wave after acceptance is a fit-free trainer/evaluation-method repair with discriminating tests. Only after that implementation itself is accepted may a separately authorized forward evaluation/model-fit operation begin.
