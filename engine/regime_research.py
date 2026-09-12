"""Calibration-lane integration for the existing Regime One research output.

The existing calibrate_regime_hmm producer owns persistence. This module only
reads owner stores and computes its additive transition_research object. It
must never be invoked by a page renderer or treated as a forecast issuer ledger.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import hashlib
import json
import math

import numpy as np

from engine.regime_transition_research import (
    AUTHORITY, FitConfig, MonthlyPanel, PanelError, fit_transition_model,
    fit_joint_feature_var, forecast_ensemble, observed_durations, propagate,
    walk_forward, month_number,
)
from engine.regime_research_inputs import load_research_panel, cutoff_utc
from engine.cycle_pattern.macro_regime import AssetPanel, retrieve_macro_analogs

SCHEMA = "regime_one.integrated_research.v1"


@dataclass(frozen=True)
class ResearchBudget:
    """Bounded calibration compute, not a new scheduler or runtime governor."""
    forecast_paths: int = 64
    evaluation_paths: int = 16
    evaluation_stride_months: int = 6
    minimum_training_months: int = 120
    maximum_evaluation_origins: int = 48
    seed: int = 20260912
    horizons: tuple[int, ...] = (1, 3, 6, 12)

    def __post_init__(self):
        fields = ((self.forecast_paths,1,256), (self.evaluation_paths,1,64),
                  (self.evaluation_stride_months,1,12), (self.minimum_training_months,24,600),
                  (self.maximum_evaluation_origins,1,120), (self.seed,0,2**32-1))
        if any(isinstance(v,bool) or not isinstance(v,int) or not low<=v<=high for v,low,high in fields):
            raise PanelError("Invalid bounded calibration budget")
        if self.horizons != (1,3,6,12):
            raise PanelError("This research contract has fixed 1/3/6/12-month targets")


def seal(value: dict) -> dict:
    """A content digest for this derived object, not a new identity registry."""
    value = dict(value)
    value.pop("content_sha256", None)
    raw = json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    value["content_sha256"] = hashlib.sha256(raw).hexdigest()
    return value


def validate_seal(value: Any) -> bool:
    if not isinstance(value,dict) or not isinstance(value.get("content_sha256"),str):
        return False
    try:
        return seal(value)["content_sha256"] == value["content_sha256"]
    except (TypeError,ValueError,OverflowError):
        return False


def _feature_diagnostics(panel: MonthlyPanel) -> list[dict]:
    result=[]
    for j,name in enumerate(panel.feature_names):
        data=panel.values[:,j]
        finite=data[np.isfinite(data)]
        current=float(data[-1]) if np.isfinite(data[-1]) else None
        trailing=data[max(0,len(data)-120):-1]
        trailing=trailing[np.isfinite(trailing)]
        median=float(np.median(trailing)) if len(trailing) else None
        mad=float(1.4826*np.median(np.abs(trailing-median))) if len(trailing) else None
        standard=(current-median)/mad if current is not None and mad is not None and mad>1e-9 else None
        result.append({"feature":name,"value":current,"finite_history_count":int(len(finite)),
                       "trailing_prior_median":median,"trailing_prior_robust_z":standard,
                       "trailing_prior_percentile":float(np.mean(trailing<=current)) if current is not None and len(trailing)>=24 else None,
                       "change_1_month":float(data[-1]-data[-2]) if len(data)>=2 and np.isfinite(data[-2:]).all() else None,
                       "change_3_months":float(data[-1]-data[-4]) if len(data)>=4 and np.isfinite(data[[-1,-4]]).all() else None,
                       "outside_robust_training_support":bool(abs(standard)>6) if standard is not None else None})
    return result


def _reliability(evaluation: dict, states: tuple[str,...]) -> list[dict]:
    """Observed bin counts, no independent-Bernoulli confidence interval fiction."""
    result=[]
    for h in (1,3,6,12):
        rows=[r for r in evaluation.get("forecasts",[]) if r["horizon_months"]==h]
        if not rows:
            continue
        bins=[]
        for j,state in enumerate(states):
            for lower,upper in ((0.,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.)):
                cohort=[r for r in rows if lower<=r["challenger"][j] and (r["challenger"][j]<upper or upper==1.)]
                if cohort:
                    bins.append({"state":state,"bin":[lower,upper],"n_forecasts":len(cohort),
                                 "mean_probability":float(np.mean([r["challenger"][j] for r in cohort])),
                                 "observed_frequency":float(np.mean([r["target_index"]==j for r in cohort]))})
        eras=[]
        for first,last in ((1900,2007),(2008,2014),(2015,2019),(2020,2023),(2024,9999)):
            cohort=[r for r in rows if first<=int(r["origin"][:4])<=last]
            if cohort:
                losses=[]
                for r in cohort:
                    truth=np.eye(len(states))[r["target_index"]]
                    losses.append(float(np.sum((np.array(r["challenger"])-truth)**2)))
                eras.append({"origin_years":[first,last],"n":len(cohort),"brier":float(np.mean(losses))})
        result.append({"horizon_months":h,"bins":bins,"eras":eras,
                       "forecast_errors_may_overlap":True,"calibrated_claim":False})
    return result


def analyze_panel(panel: MonthlyPanel, *, analysis_cutoff: str | datetime,
                  budget: ResearchBudget | None = None, asset_panel: AssetPanel | None = None) -> dict:
    """Real estimator composition over a supplied complete owner panel.

    Calendar, availability, target and source-basis validation lives in the input
    contract. Monthly historical diagnostics are not daily-current conditions.
    The numerical forecast and the historical analogue frequencies remain
    distinct objects with different meanings.
    """
    budget=budget or ResearchBudget()
    cutoff=cutoff_utc(analysis_cutoff)
    if month_number(panel.periods[-1]) >= cutoff.year*12+cutoff.month-1:
        raise PanelError("Current/open or future month cannot be a settled model origin")
    result={"schema":SCHEMA,"analysis_cutoff":cutoff.isoformat(),"origin_period":panel.periods[-1],
            "source_basis":panel.source_basis,"target_name":panel.target_name,
            "panel_sha256":panel.fingerprint,"source_receipts":list(panel.source_receipts),
            "status":"PARTIAL","authority":dict(AUTHORITY),"budget":asdict(budget),
            "feature_diagnostics":_feature_diagnostics(panel),"forecast":None,"markov_baseline":None,
            "historical_comparisons":None,"evaluation":None,"degraded":[],
            "production_champion":"existing_owner_unchanged",
            "historical_live_issuance_claimed":False,"forward_ledger_advanced":False,
            "empirically_calibrated":False,
            "limitations":["This target is the existing operational house quadrant, not an external recession definition.",
                           "Monthly model inputs stop at the last closed month; current daily conditions are a separate read.",
                           "This output does not certify point-in-time source vintages or historical forecast issuance.",
                           "Experimental forecast and analogue frequencies are not trade or allocation authority."]}
    try:
        model=fit_transition_model(panel)
        durations,exact=observed_durations(panel)
        if panel.labels[-1] is None:
            raise PanelError("CURRENT_OWNER_TARGET_MISSING")
        trajectory=np.repeat(panel.values[-1][None,:],12,axis=0)
        baseline=propagate(model,panel.labels[-1],int(durations[-1]),trajectory,
                           duration_is_lower_bound=not bool(exact[-1]),empirical_only=True)
        baseline["kind"]="EMPIRICAL_MARKOV_RESEARCH_BASELINE"
        baseline["horizons"]=[h for h in baseline["horizons"] if h["horizon_months"] in budget.horizons]
        result["markov_baseline"]=baseline
        try:
            var=fit_joint_feature_var(panel)
            result["forecast"]=forecast_ensemble(model,var,panel,horizons=budget.horizons,
                                                paths=budget.forecast_paths,seed=budget.seed)
        except (PanelError,np.linalg.LinAlgError) as exc:
            result["degraded"].append({"capability":"conditional_forecast","reason":str(exc)})
    except (PanelError,np.linalg.LinAlgError) as exc:
        result["degraded"].append({"capability":"transition_model","reason":str(exc)})
    try:
        result["historical_comparisons"]=retrieve_macro_analogs(panel,horizons=budget.horizons,asset_panel=asset_panel)
    except (PanelError,np.linalg.LinAlgError) as exc:
        result["degraded"].append({"capability":"historical_comparisons","reason":str(exc)})
    # Preserve the whole training history, but bound the number of evaluation
    # origins. Increasing the first training prefix is NOT trimming each fit to
    # a late, conveniently chosen sample. Exact selected origins are returned.
    first_train=max(budget.minimum_training_months,
                    len(panel.periods)-budget.maximum_evaluation_origins*budget.evaluation_stride_months)
    evaluation=walk_forward(panel,min_train_months=first_train,horizons=budget.horizons,
                             stride=budget.evaluation_stride_months,paths=budget.evaluation_paths,seed=budget.seed)
    evaluation["reliability"]= _reliability(evaluation,panel.states)
    evaluation["evaluation_origin_cap"]=budget.maximum_evaluation_origins
    evaluation["selection_status"]="fixed_parameters_no_post_outcome_tuning"
    result["evaluation"]=evaluation
    result["status"]="EXPERIMENTAL_RESEARCH" if result["forecast"] is not None else "PARTIAL"
    # Finite strict JSON is both a publication contract and a final numerical
    # overflow check. No NaN/Infinity is silently stringified into an artifact.
    return seal(result)


def build_research(data_root: Path, *, analysis_cutoff: str | datetime,
                   budget: ResearchBudget | None = None, history_snapshot=None) -> dict:
    cutoff=cutoff_utc(analysis_cutoff)
    panel,inputs=load_research_panel(Path(data_root),cutoff,history_snapshot=history_snapshot)
    if panel is None:
        return seal({"schema":SCHEMA,"analysis_cutoff":cutoff.isoformat(),"status":"UNAVAILABLE",
                     "source_basis":"LATEST_REVISED_EXPLORATORY","input_diagnostics":inputs,
                     "forecast":None,"historical_comparisons":None,"evaluation":None,
                     "authority":dict(AUTHORITY),"reason":inputs.get("reason","source_unavailable"),
                     "forward_ledger_advanced":False,"historical_live_issuance_claimed":False,
                     "empirically_calibrated":False})
    from engine.regime_research_inputs import load_asset_panel
    asset_panel, asset_inputs = load_asset_panel(Path(data_root), panel.periods, cutoff)
    result=analyze_panel(panel,analysis_cutoff=cutoff,budget=budget,asset_panel=asset_panel)
    result["asset_input_diagnostics"] = asset_inputs
    result["input_diagnostics"]=inputs
    return seal(result)
