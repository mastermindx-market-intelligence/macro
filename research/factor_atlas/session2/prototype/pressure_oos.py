"""Pure OOS forecast-pair loss adjudicator; does not train models or fetch data.

This reference measures externally supplied, supposedly frozen forecasts.
No source authority, source decryption, feature selection, membership registry,
historical data repair, outcome service, signal, publisher or trading action.
A synthetic favorable loss is not a proven economic benefit.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
import math
from typing import Iterable

import pressure as m

_TARGET="NEXT_30M_RESIDUAL_RETURN_BPS"


@dataclass(frozen=True)
class EvaluationPlan:
    experiment_ref: str
    factor_ref: str
    population_ref: str
    roster_ref: str
    membership_mode: str
    target_ref: str
    horizon_seconds: int
    development_end_utc_s: int
    holdout_start_utc_s: int
    holdout_end_utc_s: int
    embargo_seconds: int
    minimum_days: int
    minimum_outcome_coverage: float
    control_model_ref: str
    pressure_model_ref: str
    feature_basis_ref: str

    def validate(self) -> None:
        for f in ("experiment_ref","factor_ref","population_ref","roster_ref",
                  "target_ref","control_model_ref","pressure_model_ref",
                  "feature_basis_ref"):
            m._text(getattr(self,f),f)
        if self.target_ref!=_TARGET:
            raise ValueError("unpreregistered_target")
        if self.membership_mode!="point_in_time":
            raise ValueError("forecast_requires_pit_membership")
        if self.control_model_ref==self.pressure_model_ref:
            raise ValueError("model_identity_not_distinct")
        for f in ("horizon_seconds","development_end_utc_s",
                  "holdout_start_utc_s","holdout_end_utc_s",
                  "embargo_seconds","minimum_days"):
            m._integer(getattr(self,f),f)
        if self.horizon_seconds!=1800:
            raise ValueError("primary_30min_horizon_required")
        if (self.embargo_seconds<self.horizon_seconds or
                self.holdout_start_utc_s-self.development_end_utc_s<
                self.embargo_seconds):
            raise ValueError("insufficient_training_holdout_embargo")
        if (self.holdout_start_utc_s>=self.holdout_end_utc_s or
                self.holdout_end_utc_s-self.holdout_start_utc_s>366*86400):
            raise ValueError("invalid_holdout_window")
        if not 20<=self.minimum_days<=252:
            raise ValueError("insufficient_minimum_holdout_days")
        coverage=m._finite(self.minimum_outcome_coverage,
                           "minimum_outcome_coverage",positive=True)
        if coverage>.99:
            raise ValueError("invalid_outcome_coverage_threshold")


@dataclass(frozen=True)
class EvaluationSlot:
    factor_ref: str
    session_id: str
    decision_utc_s: int

    def validate(self) -> None:
        m._text(self.factor_ref,"factor_ref")
        m._date(self.session_id)
        m._integer(self.decision_utc_s,"decision_clock")
        if m._et_clock(self.decision_utc_s)[0]!=self.session_id:
            raise ValueError("session_clock_mismatch")


@dataclass(frozen=True)
class PairedForecast:
    slot: EvaluationSlot
    factor_membership_ref: str
    population_ref: str
    membership_mode: str
    feature_known_at_utc_s: int
    control_known_at_utc_s: int
    pressure_known_at_utc_s: int
    realized_end_utc_s: int
    realized_known_at_utc_s: int | None
    control_prediction_bps: float
    pressure_prediction_bps: float
    realized_residual_return_bps: float | None
    observed_basis_ref: str
    outcome_source_ref: str
    pressure_source_ref: str
    mode: str


@dataclass(frozen=True)
class OutcomeLoss:
    session_id: str
    expected_slots: int
    matured_slots: int
    control_day_mse_bps2: float | None
    pressure_day_mse_bps2: float | None
    improvement_bps2: float | None


@dataclass(frozen=True)
class EvaluationResult:
    status: str
    expected_slots: int
    observed_forecast_slots: int
    matured_matched_slots: int
    unavailable_slots: int
    outcome_coverage: float
    scheduled_day_clusters: int
    day_clusters: int
    low_coverage_sessions: tuple[str,...]
    per_day: tuple[OutcomeLoss,...]
    control_mse_bps2: float | None
    pressure_mse_bps2: float | None
    day_equal_loss_improvement_bps2: float | None
    relative_mse_improvement: float | None
    leave_one_day_out_low: float | None
    leave_one_day_out_high: float | None
    is_confidence_interval: bool
    is_statistical_accuracy_study: bool
    real_market_data_admitted: bool
    source_rights_proven: bool
    customer_publishable: bool
    knowledge_class: str
    observed_population_ref: str
    target_ref: str
    input_digest: str
    authority: tuple[tuple[str,bool],...]=m.AUTHORITY


def _signed_bps(value: object, name: str) -> float:
    try:
        x=m._finite(value,name)
    except ValueError:
        raise ValueError(name+"_finite_number_required") from None
    if abs(x)>20000:
        raise ValueError(name+"_outside_research_bounds")
    return x


def evaluate_oos(plan: EvaluationPlan,
                 expected_slots: Iterable[EvaluationSlot],
                 rows: Iterable[PairedForecast], *,
                 evaluation_at_utc_s: int,
                 min_day_coverage_override: None = None) -> EvaluationResult:
    """Day-equal paired MSE. Positively descriptive even if test loss improves.

    Missing expected outcomes or late corrections cannot become zero labels.
    No inferential confidence, independent material alpha or trading authority.
    """
    if not isinstance(plan,EvaluationPlan):
        raise ValueError("evaluation_plan_required")
    plan.validate()
    m._integer(evaluation_at_utc_s,"evaluation_asof")
    if evaluation_at_utc_s<plan.holdout_start_utc_s:
        raise ValueError("evaluation_before_holdout")
    if min_day_coverage_override is not None:
        raise ValueError("no_runtime_coverage_threshold_override")
    expected={}
    for s in expected_slots:
        if not isinstance(s,EvaluationSlot):
            raise ValueError("expected_slot_required")
        s.validate()
        if s.factor_ref!=plan.factor_ref:
            raise ValueError("expected_factor_mismatch")
        if not(plan.holdout_start_utc_s<=s.decision_utc_s
               and s.decision_utc_s+plan.horizon_seconds<=plan.holdout_end_utc_s):
            raise ValueError("outside_holdout")
        key=(s.factor_ref,s.decision_utc_s)
        if key in expected:
            raise ValueError("duplicate_expected")
        expected[key]=s
    if not expected:
        raise ValueError("expected_holdout_grid_required")
    seen={}
    for r in rows:
        if not isinstance(r,PairedForecast) or not isinstance(r.slot,EvaluationSlot):
            raise ValueError("forecast_record_required")
        r.slot.validate()
        key=(r.slot.factor_ref,r.slot.decision_utc_s)
        if key not in expected:
            raise ValueError("unexpected_slot")
        if r.slot!=expected[key]:
            raise ValueError("expected_slot_mismatch")
        if key in seen:
            raise ValueError("duplicate_observation")
        if r.membership_mode!=plan.membership_mode or r.mode!="as_observed":
            raise ValueError("membership_mode_or_asof_mismatch")
        if r.factor_membership_ref!=plan.roster_ref:
            raise ValueError("roster_mismatch")
        if r.population_ref!=plan.population_ref:
            raise ValueError("population_mismatch")
        if r.observed_basis_ref!=plan.feature_basis_ref:
            raise ValueError("basis_mismatch")
        for attr in ("outcome_source_ref","pressure_source_ref"):
            m._text(getattr(r,attr),attr)
        for name in ("feature_known_at_utc_s","control_known_at_utc_s",
                     "pressure_known_at_utc_s","realized_end_utc_s"):
            value=getattr(r,name)
            m._integer(value,name)
            if value<=0:
                raise ValueError("clock_positive_required")
        if (r.feature_known_at_utc_s>r.slot.decision_utc_s or
                r.control_known_at_utc_s>r.slot.decision_utc_s or
                r.pressure_known_at_utc_s>r.slot.decision_utc_s):
            raise ValueError("forecast_lookahead")
        if (r.control_known_at_utc_s<r.feature_known_at_utc_s or
                r.pressure_known_at_utc_s<r.feature_known_at_utc_s):
            raise ValueError("forecast_precedes_feature")
        if r.realized_end_utc_s!=r.slot.decision_utc_s+plan.horizon_seconds:
            raise ValueError("horizon_mismatch")
        if (r.realized_residual_return_bps is None) != (r.realized_known_at_utc_s is None):
            raise ValueError("outcome_receipt_without_label")
        if r.realized_known_at_utc_s is not None:
            m._integer(r.realized_known_at_utc_s,"realized_known_at")
            if r.realized_known_at_utc_s<r.realized_end_utc_s:
                raise ValueError("outcome_before_event")
        _signed_bps(r.control_prediction_bps,"control_forecast")
        _signed_bps(r.pressure_prediction_bps,"pressure_forecast")
        if r.realized_residual_return_bps is not None:
            _signed_bps(r.realized_residual_return_bps,"realized_outcome")
        seen[key]=r

    by_day=defaultdict(list)
    scheduled=defaultdict(int)
    mature_rows=[]
    for key,s in sorted(expected.items()):
        scheduled[s.session_id]+=1
        r=seen.get(key)
        if (r is not None and r.realized_residual_return_bps is not None
                and r.realized_known_at_utc_s is not None
                and r.realized_known_at_utc_s<=evaluation_at_utc_s):
            ctrl=(r.realized_residual_return_bps-r.control_prediction_bps)**2
            augmented=(r.realized_residual_return_bps-r.pressure_prediction_bps)**2
            if not math.isfinite(ctrl+augmented):
                raise ValueError("nonfinite_squared_loss")
            by_day[s.session_id].append((ctrl,augmented))
            mature_rows.append(r)
    day_detail=[]
    usable_day_losses=[]
    for day in sorted(scheduled):
        arr=by_day.get(day,[])
        if arr:
            ctrl=math.fsum(p[0] for p in arr)/len(arr)
            aug=math.fsum(p[1] for p in arr)/len(arr)
            difference=ctrl-aug
            usable_day_losses.append((ctrl,aug,difference))
        else:
            ctrl=aug=difference=None
        day_detail.append(OutcomeLoss(day,scheduled[day],len(arr),ctrl,aug,difference))

    matured=len(mature_rows); total=len(expected)
    cov=matured/total
    nday=len(usable_day_losses)
    # The global mature-label share alone can hide a severely undersampled
    # day whose single matched label would receive a full day-equal weight.
    # Withhold the aggregate until every preregistered session independently
    # meets the same prospective outcome-coverage threshold.
    low_days=tuple(sorted(day for day,n in scheduled.items()
                          if len(by_day.get(day,()))/n < plan.minimum_outcome_coverage))
    if nday<plan.minimum_days:
        status="INSUFFICIENT_HOLDOUT_SESSIONS"
    elif cov<plan.minimum_outcome_coverage:
        status="INSUFFICIENT_OUTCOME_COVERAGE"
    elif low_days:
        status="INSUFFICIENT_DAY_OUTCOME_COVERAGE"
    else:
        status="DESCRIPTIVE_OOS_COMPARISON"
    b=p=delta=ratio=loo_low=loo_high=None
    if status=="DESCRIPTIVE_OOS_COMPARISON":
        b=math.fsum(x[0] for x in usable_day_losses)/nday
        p=math.fsum(x[1] for x in usable_day_losses)/nday
        delta=b-p
        ratio=delta/b if b else None
        differences=[x[2] for x in usable_day_losses]
        if nday>1:
            cross=[math.fsum(differences[:i]+differences[i+1:])/(nday-1)
                   for i in range(nday)]
            loo_low=min(cross);loo_high=max(cross)
    # Explicit unavailable slots enter the fingerprint by identity and status,
    # never with future label values unavailable at this evaluation cutoff.
    matched={(r.slot.factor_ref,r.slot.decision_utc_s):r for r in mature_rows}
    return EvaluationResult(
        status,total,len(seen),matured,total-matured,cov,
        len(scheduled),nday,low_days,tuple(day_detail),b,p,delta,ratio,
        loo_low,loo_high,False,False,False,False,False,
        "FORECAST_PAIR_DIAGNOSTIC_NOT_TRADING_ALPHA",
        plan.population_ref,plan.target_ref,
        m.digest({"plan":asdict(plan),"cutoff":evaluation_at_utc_s,
                  "expected":[asdict(expected[k]) for k in sorted(expected)],
                  "eligible_rows":[asdict(matched[k]) for k in sorted(matched)]}))
