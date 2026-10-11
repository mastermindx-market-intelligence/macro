# Factor Atlas S2-P6 — source-independent predictive-value falsifier

**State: SYNTHETIC / RESEARCH_ONLY / REAL MARKET OUTCOME NOT_ADMITTED / NO CUSTOMER OR TRADING AUTHORITY.**

## Research question and scientific control

Can a **pressure-augmented forecast** materially improve next-30-minute *residual return* prediction versus an independently trained, comparably flexible price/volatility/turnover control? BVC is itself a deterministic price-volume transform and does not add new observed tape information. A gain over an artificially weak baseline cannot establish genuinely incremental information. This module never trains models or compares model capacities; the independent model/outcome owner must preregister both training procedures, feature sets, hyperparameter budgets, target construction and chronology. Merely naming a control “flexible” is not verification.

The primary outcome identity is `NEXT_30M_RESIDUAL_RETURN_BPS` (basis-point residual return, **not** fund purchasing). Other 10-minute/remaining-session targets require separate frozen experiments and cannot substitute after seeing the primary endpoint. In any real study, the residual-return beta/sector method, adjustments, price availability and label source must be selected *without* peeking at holdout outcomes.

## Causal admission

`prototype/pressure_oos.py` accepts owner-supplied `EvaluationPlan`, explicit `EvaluationSlot` factor/day/decision clocks, and `PairedForecast` source receipts. The plan freezes factor/ref, point-in-time roster, population, target, feature basis, control and pressure model reference, **30-minute horizon**, development end, evaluation period, embargo of at least the longest horizon, a minimum of **20 distinct evaluation days** and ≥80% mature paired-label coverage. The actual source owner must additionally supply at least 20 development days and adequate historical baseline history, not assume those from ticker labels.

Per observation, the last feature-known-at, both forecast-receipt clocks and decision time must be causally ordered. The real label event end must be exactly decision+30 minutes; label availability must not precede its event end. Rows with labels first learned *after* the evaluation cutoff are **unavailable** (never zero-filled or backdated). Source security/day clocks follow ET trading dates, but no exchange calendar is generated. Mixing point-in-time and current-cohort membership, a new roster version under an old reference, changed monetary basis, duplicate/unexpected observations, invalid model refs or out-of-holdout decisions are refused. A declared source identifier is evidence to validate externally, **not** authentication or admission.

## Pure descriptive assessment

For a mature label `y` and frozen forecasts `c` (control) and `p` (pressure):

    L_control  = (y-c)^2       [basis points squared]
    L_pressure = (y-p)^2
    improvement = L_control-L_pressure

A positive difference favors the pressure forecast on this *sample*, while negative differences remain visible. Mean losses are calculated per ET session first; per-session results are then equally weighted. One 30-minute label each minute on a heavily sampled day does not count as dozens of independent sessions. Aggregate results are withheld for fewer than 20 mature evaluation days or under 80% outcome coverage. `relative_mse_improvement` is NULL when control loss is zero; there is no manufactured infinite gain. A leave-one-day-out min/max is a **stability sensitivity**, not a confidence interval or p-value.

`source_rights_proven=false`, `real_market_data_admitted=false`, `is_statistical_accuracy_study=false`, `is_confidence_interval=false`, `customer_publishable=false`, and all five authority flags FALSE are hard outputs. Even 20 fabricated favorable days can never be sold as predictive alpha, executable entry, observed aggressor buying or hedge-fund flow. This kernel makes no provider request, creates no trial database, pipeline, registry, calendar, ranker, alert or order.

## Independent acceptance gates

The incumbent source owner must provide genuine equity minute/quote/trade rights and receipt clocks, corporate-action/volume basis, point-in-time factor identity and sufficient immutable label/outcome coverage; the upstream S2-P1 pilot remains NOT_ADMITTED. An independent quantitative reviewer must authenticate model freezing, compare equal-capacity nonlinearly flexible price/turnover controls, test purged chronological splits with outcome embargoes, confirm calendar/event revisions, perform session/week block-bootstrap or valid cluster uncertainty, assess regime/liquidity/phase robustness and negative controls, and consider spread/slippage/capacity before any trading interpretation.

The native `test_pressure_oos.py` suite uses exclusively fabricated calendars, forecasts and residual labels. It exercises as-of causality, missing outcome denominators, insufficient sessions/coverage, embargo, holdout date/roster/basis identity, negative performance, duplicate injection, zero-MSE behavior, per-day equal weighting and future-label isolation. A favorable synthetic fixture is a software witness only. Original previously blocked source reads and the separate blocked S2-P4 read-model integrity edit remain untouched; no waiver or bypass is implied by this new scientific geometry.


## R2 day-level outcome-coverage gate — prevent distorted OOS loss attribution

A targeted adversarial test proved that `minimum_outcome_coverage=0.8` applied **only globally** was insufficient for a day-equal forecast study. With 20 registered dates, 10 expected outcomes per date, and 19 complete dates plus a final day having just one mature label, the study still disclosed `DESCRIPTIVE_OOS_COMPARISON` at 191/200 = **95.5% global label coverage**. That one label received the same calendar-day weight as ten independent valid samples on another date. The resulting pressure-vs-price-control loss statistic could be selected by intermittent label delivery, even though the model remains research-only.

The accepted source-only `pressure_oos.py` now computes a `low_coverage_sessions` tuple of all registered days whose mature paired-label fraction is **below the same preregistered `EvaluationPlan.minimum_outcome_coverage`**. It retains the existing priority ordering: fewer than the required twenty matured date clusters -> `INSUFFICIENT_HOLDOUT_SESSIONS`; less than eighty percent global labels -> `INSUFFICIENT_OUTCOME_COVERAGE`; otherwise any undercovered day -> **`INSUFFICIENT_DAY_OUTCOME_COVERAGE`**. In every insufficient state, both MSE means, improvement and leave-one-day-out statistics remain NULL. A day with exactly 80% mature labels is eligible, but still provides no confidence/probability claim.

This correction does not extend the study target, change the original holdout after seeing outcomes, infer real source rights or train a market model. It applies the existing frozen policy consistently to the planned day-level estimand. Five fail-first synthetic tests discovered/guarded the omission, then the OOS suite passed **46/46** and the complete 13-suite research regression passed **408/408** locally on M2 Python 3.12. The new controlled witness shows 95.5% globally covered but withheld due to one 10%-covered day; one 98.5% global case withheld due to a 70%-covered day; and correctly returns descriptive-only results when all days meet the registered floor.
