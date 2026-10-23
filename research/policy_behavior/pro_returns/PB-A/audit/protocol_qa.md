# PB-A frozen-protocol QA

Reviewed: `PB_A_PROTOCOL_FREEZE.json`, frozen 2026-10-07 02:50:36 UTC; supplied remote commit `99253212652ba7d1248a587c249da44ec6e3b9b6`. This note does not amend the freeze or inspect/score outcomes. It is local methodological QA, not PB-F commissioned independent review.

## Verdict

The protocol can support an honest retrospective feasibility pilot of **conditional policy-direction classification** on a small purposive historical sample. Its anchor rule correctly removes the already-announced rate change from the forecast target, and its missing-data, narrow predictor-input, and common-coverage rules address important leakage and comparison risks. It cannot establish that revealed preference generally beats rhetoric, that a model is calibrated, that a heldout test succeeded, or that it forecasts markets.

No unavoidable methodological blocker prevents the bounded feasibility run. The following are **pre-score implementation blockers** unless resolved and frozen in a companion implementation record before the outcome join. Do not edit the frozen protocol or make resolutions after seeing scores.

## Pre-score blockers and exact fixes

1. **Operational definitions must uniquely determine every forecast and endpoint.** The text does not fully specify calendar-month arithmetic (e.g., May 31 plus one month), handling of nonbusiness days, numerical equality tolerance, or how a newly decided rate hold differs from reiterating an existing target in a liquidity directive. Fix: freeze month-end clamping, New York end-of-day dates, the most recent effective policy range applicable to that date, an exact decimal/rate equality rule, and an event-level `new_policy_rate_decision` Boolean justified by contemporaneous sources. Reauthorization of an unchanged range in a purchases/operations directive must not silently count as a new FOMC rate-hold decision. Freeze decision and effective dates for rate transitions separately; reconcile subsequent events at the cut boundary before generating the secondary target.

2. **M0 interpretation must be resolved before labels.** “Clean explicit forward rate path” and persistence of previous guidance require a deterministic coding policy. Fix: record the exact selected statement, type, conditions, source IDs, horizon limitation, and reason for UP/DOWN/HOLD/ABSTAIN for every event. State whether still-live earlier guidance is an admissible M0 input on a speech/Treasury/operating event; apply this uniformly. “Patient,” “act as appropriate,” macroeconomic forecasts, and conditional support must not be reinterpreted differently across episodes because the researcher knows later policy. Have the rule operate on the frozen input object, with no outcomes passed to it. Same-signal horizon extrapolation is allowed by this freeze, but must remain visibly an analyst baseline assumption.

3. **Comparable evaluation populations must be explicit.** M1 abstains on all M0 holds; M2 abstains on events without new rate decisions. As a result, own-coverage scores describe different cases and pairwise comparisons may themselves describe different intersections. Fix: produce per-horizon, per-pair scored episode IDs, counts, class counts, coverage, paired differences, and regime breakdown. Also report the three-way intersection if nonempty, but do not treat a tiny or empty intersection as an error or fill abstentions. Never rank all three using different pairwise populations. State plainly when a comparison is too sparse to be informative. The >=20 certification gate is a **casebook-row** requirement, not >=20 predictions or common-scored observations per model.

4. **Source-time certification must not overclaim execution or immutable historical bytes.** The freeze already distinguishes documentary from contemporaneous archived-byte certification. Fix: expose those scopes at row and report level, including uncertain attachments and changed links; admit only input time upper bounds at/before the cut. “Announced,” “authorized,” “effective-date scheduled,” and “executed” must be separate states. Quarantine only unsupported intraday details where possible rather than rejecting an independently timed headline announcement. In the early-Fed source packet, the March 3 implementation-date discrepancy, October 11 date-only NYFed sizes, March 23 attachment-clock association, and mutable 2020-framework link are material examples. Do not call a row execution-certified simply because an official statement announced a decision.

## Important disclosed limitations, not blockers

### Estimand and scope

The primary estimand is the sign of the **net target-midpoint change** from the most recently known decided rate to an effective horizon endpoint. This is a legitimate forecast of future net stance, but it is not “next policy-rate direction”: an intervening cut followed by an offsetting hike can yield HOLD. Keep the primary and first-subsequent-change targets separate and reconcile decision/effective dates. A decline in market yields, a Treasury funding adjustment, selective credit relief, an inflation overshoot goal, and unchanged policy rates are not interchangeable target outcomes.

The known announcement is absorbed into the anchor, so action continuation cannot score its own already-public cut/hike as predictive. The endpoint must likewise exclude that decision's scheduled implementation. Make this anchor behavior easy to audit with a small trace of cut, known-decided range, horizon date, and effective endpoint range stored outside the predictor input.

### What M2 actually tests

M2 is mostly **current-rate-decision persistence**, plus one conventional-floor exception. It records but does not consume beneficiaries, alternatives, selective protection, prior revealed behavior, pricing, or qualitative constraints. This is permitted by its explicit minimal scope, but the result cannot answer the full actions/constraints/revealed-preference thesis. M0 consumes public forward guidance; M2 consumes an already-known current decision and a design assumption. The comparison measures these specified rules, not private-intent inference. C0 and C1 are essential comparators; display them with the same prominence as any favorable M2 result.

### Conventional floor

The 0–0.25% exception is an assumed **conventional operating floor**, not a legal impossibility of further easing or proof that negative rates were unavailable. It does not prohibit other instruments and is not evidence of a future hold by itself. Any M2 gain on the newly-zero-range event may be entirely attributable to this assumption. C1 isolates that event-level exception; disclose the episode count affected and the score contribution without promoting it into a general constraints-model victory. C0 helps test whether predicting no further rate change was already sufficient. Freeze what “newly decided conventional floor” means; do not add exceptions at other rate levels after seeing outcomes.

### Three headline metrics contain the same information here

With modal probability p and each alternative probability q=(1-p)/2, let a be modal directional accuracy on an identical scored set. Then:

- Correct-case multiclass Brier = 1.5(1-p)^2.
- Incorrect-case Brier = 0.5 + 1.5p^2.
- Mean Brier = 0.5 + 1.5p^2 - (3p-1)a.
- Mean NLL = -log(q) - a log(p/q).

At p=0.6: Brier = 1.04 - 0.8a; NLL = log(5) - a log(3).

Thus, on matched coverage, directional accuracy, Brier, and NLL are affine transformations of the same correct/incorrect indicator. All prescribed p sensitivities exceed 1/3, so changing p alone cannot change the ranking on an identical sample. Report the required proper scores, but explicitly state they are not three independent validations or evidence of calibrated probabilities. “Robust across confidence settings” would be a mechanically guaranteed headline unless coverage or rules also changed. A fixed-confidence reliability table can summarize empirical correctness, but a small selected sample cannot support general calibration claims.

### Sample dependence and four-cluster uncertainty

The 24 events are purposive and historically familiar. Close pandemic events, repeated holds, overlapping 1/3/6-month windows, and two events on May 1, 2024 share much future policy information. They are not 24 independent draws per horizon or 72 independent forecasts. Same-day events with distinct instruments may legitimately remain separate rows, but show their shared outcome and evaluate an event-day deduplication sensitivity if they contribute repeated comparisons. Never pool horizons.

Four historical regime blocks provide only four independent resampling units under the stated bootstrap. Bootstrap spread and leave-one-regime-out results are descriptive sensitivity; intervals should not be described as conventional reliable significance evidence, particularly with a regime having no common scored cases. Specify whether the estimand weights episodes equally or regimes equally, and retain the chosen weighting across metrics. Report outcome-class frequencies and C0 results to reveal whether persistence/HOLD prevalence explains apparent skill. The chronological subset is a retrospective reporting slice, not a holdout, external test, or protection against historically informed design.

## Headline/report requirements

Lead with: “Retrospective feasibility pilot on 24 purposively selected historical episodes; comparisons concern the specified rules on their common scored coverage.” Follow immediately with the scored counts, abstention coverage, target/horizon, C0/C1 comparisons, class/regime composition, and the fixed-confidence score equivalence. Distinguish >=20 historical source-time-certified rows from immutable-byte, execution, expectations, and forecasting certification. Favorable policy-direction scores cannot stand in for blocked pricing-surprise, yield, FX, inflation-expectation, or sector targets. Any unimplemented target remains a named deficiency rather than a promised later result or a pooled zero.

The strongest supportable conclusion is feasibility and transparent conditional descriptive performance. Predictive superiority/generalization requires a broader externally specified census or new prospective outcomes and richer separately frozen models; this pilot should not claim those accomplishments.
