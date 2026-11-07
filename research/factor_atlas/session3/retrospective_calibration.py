"""Retrospective factor-options expected-move evaluation; research, never signal.

Immutable inputs supplied by the incumbent study reader. NO source store,
producer, I/O, probability fitting, quote-time assertion, auth or publication.
The forward outcome starts at NEXT cash close after the reported EOD option
session because report generation can follow the session's official close.
This is not historical data availability proof or executable-option P&L.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from math import fsum, isfinite
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from lib.us_cash_calendar import expected_last_session
from research.factor_atlas.session3.retrospective import build_study, _numeric


def _day(value: object) -> bool:
    return type(value) is date


def _positive_price(value: object) -> bool:
    return _numeric(value) and value > 0


def _forward_return(*, closes: pd.DataFrame, sessions: list[date], roots: list[str],
                    weights: Mapping[str, float], anchor: date, horizon_days: int) -> tuple[float | None, str | None, str | None, list[str]]:
    entry = next((s for s in sessions if s > anchor), None)
    exit_ = next((s for s in sessions if s >= anchor + timedelta(days=horizon_days)), None)
    if entry is None or exit_ is None or exit_ <= entry:
        return None, (entry.isoformat() if entry else None), None, ["FORWARD_HORIZON_NOT_OBSERVED"]
    window = [s for s in sessions if entry <= s <= exit_]
    sample = closes.reindex(index=pd.to_datetime(window), columns=roots)
    if sample.shape != (len(window), len(roots)) or not sample.map(_positive_price).to_numpy(dtype=bool).all():
        return None, entry.isoformat(), exit_.isoformat(), ["INCOMPLETE_FORWARD_PRICE_WINDOW"]
    initial, terminal = sample.iloc[0].astype(float), sample.iloc[-1].astype(float)
    realized = fsum(float(weights[r]) * (float(terminal[r]) / float(initial[r]) - 1) for r in roots)
    if not isfinite(realized):
        return None, entry.isoformat(), exit_.isoformat(), ["INVALID_REALIZED_RETURN"]
    return realized, entry.isoformat(), exit_.isoformat(), []



def _historical_rv_benchmark(*, closes: pd.DataFrame, sessions: list[date], roots: list[str],
                             weights: Mapping[str,float], anchor: date, window: int,
                             horizon_days: int) -> float | None:
    """Independent historical price-risk comparator at the SAME anchor cutoff.

    Daily log-return covariance is converted to an annual 252-session basis and
    scaled to 30 calendar days on ACT/365F. This is a descriptive baseline, not
    a calibrated option implied-variance estimator or probability forecast.
    """
    available = [s for s in sessions if s <= anchor]
    days = available[-(window+1):]
    if len(days)!=window+1:
        return None
    panel = closes.reindex(index=pd.to_datetime(days), columns=roots)
    if panel.shape!=(window+1,len(roots)) or not panel.map(_positive_price).to_numpy(dtype=bool).all():
        return None
    values=panel.to_numpy(dtype=float)
    returns=np.diff(np.log(values),axis=0)
    if not np.isfinite(returns).all() or (returns.std(axis=0,ddof=1)<=1e-14).any():
        return None
    cov=np.cov(returns,rowvar=False)
    if not np.isfinite(cov).all():
        return None
    sigma=np.array([float(weights[r]) for r in roots])
    daily_var=float(sigma@cov@sigma)
    if not isfinite(daily_var) or daily_var < -1e-12:
        return None
    return float(np.sqrt(max(daily_var,0)*252*horizon_days/365))


def evaluate(*, weights: Mapping[str, float], greeks_by_anchor: Mapping[date, Mapping[str, pd.DataFrame]],
             closes: pd.DataFrame, sessions: Sequence[date], anchors: Sequence[date],
             captured_at: datetime, window: int = 252, horizon_calendar_days: int = 30,
             research_iv_error_abs_max: float = 0.) -> dict:
    """Non-overlapping preregistered cases including explicit null/withheld outcomes.

    The 252-session return correlation stops exactly at *each* anchor. The outcome
    labels use cash closes from first session AFTER anchor to first session ON OR
    AFTER the 30-calendar-day target. This differs from option exercise payoff.
    
    No normalization or row deletion may turn a 6/7 source into a basket model.
    An admitted real observation/known-at/rights receipt is a separate authority.
    """
    if not isinstance(closes, pd.DataFrame) or not isinstance(closes.index, pd.DatetimeIndex):
        raise ValueError("session-indexed owner price panel required")
    if closes.index.has_duplicates or closes.columns.has_duplicates or closes.index.tz is not None:
        raise ValueError("duplicate or ambiguous owner price sessions")
    if not isinstance(sessions, Sequence) or not sessions or any(not _day(s) for s in sessions):
        raise ValueError("owner cash-session calendar required")
    ordered_sessions = list(sessions)
    if ordered_sessions != sorted(set(ordered_sessions)):
        raise ValueError("incumbent sessions must be ordered unique")
    if not isinstance(anchors, Sequence) or not anchors or any(not _day(a) for a in anchors):
        raise ValueError("nonempty exact anchor dates required")
    chosen = list(anchors)
    if chosen != sorted(set(chosen)):
        raise ValueError("non-overlapping anchors require strict ascending identity")
    if any(a not in ordered_sessions for a in chosen):
        raise ValueError("anchor absent from incumbent session grid")
    if chosen[-1] > ordered_sessions[-1]:
        raise ValueError("source anchor is after last owner session")
    if type(window) is not int or not 63 <= window <= 756:
        raise ValueError("explicit bounded return window required")
    # Source inputs and build_study are standardized IV30. Other accepted
    # horizons previously changed the label/RV benchmark but not the model.
    if type(horizon_calendar_days) is not int or horizon_calendar_days != 30:
        raise ValueError("only the source-matched 30-calendar-day horizon is supported")
    if not isinstance(weights, Mapping) or not 3 <= len(weights) <= 50:
        raise ValueError("positive basket population required")
    if any(not isinstance(k, str) or not k or not _numeric(v) or v <= 0 for k,v in weights.items()):
        raise ValueError("positive numeric original basket weights required")
    if abs(fsum(weights.values())-1)>1e-12:
        raise ValueError("original house weights must sum to one")
    roots=sorted(weights)
    if not isinstance(greeks_by_anchor, Mapping) or not set(greeks_by_anchor).issubset(chosen):
        raise ValueError("unexpected Greek anchor identity")
    if not isinstance(captured_at, datetime) or captured_at.tzinfo is None or captured_at.utcoffset() is None:
        raise ValueError("aware research capture clock required")
    if captured_at.date() < chosen[-1]:
        raise ValueError("capture precedes requested anchor")
    # A source file can contain rows dated AFTER its claimed acquisition time.
    # The existing US cash calendar, not the wall-clock date alone, owns the
    # completed-session cutoff. Future rows must never enter forward labels.
    completed_cutoff = expected_last_session(captured_at)
    if chosen[-1] > completed_cutoff:
        raise ValueError("source anchor not completed at capture")
    ordered_sessions = [day for day in ordered_sessions if day <= completed_cutoff]
    result_cases=[]
    last_exit=None
    for anchor in chosen:
        entry=next((s for s in ordered_sessions if s>anchor),None)
        target_exit=next((s for s in ordered_sessions if s>=anchor+timedelta(days=horizon_calendar_days)),None)
        if last_exit is not None and entry is not None and entry<=last_exit:
            raise ValueError("overlapping forward outcome windows are not independent")
        if target_exit is not None:
            last_exit=target_exit
        elif last_exit is not None:
            # No later future outcomes should masquerade as non-overlap.
            raise ValueError("unresolved forward exit before next anchor")
        source=greeks_by_anchor.get(anchor,{})
        if not isinstance(source,Mapping) or not set(source).issubset(roots):
            raise ValueError("unexpected Greek membership root")
        preceding=[s for s in ordered_sessions if s<=anchor]
        study=build_study(weights=weights,greeks=source,closes=closes,
                          sessions=preceding,anchor=anchor,captured_at=captured_at,
                          windows=(window,),
                          research_iv_error_abs_max=research_iv_error_abs_max)
        model=study['models'][str(window)]
        realized,entry_day,exit_day,outcome_reasons=_forward_return(closes=closes,sessions=ordered_sessions,
            roots=roots,weights=weights,anchor=anchor,horizon_days=horizon_calendar_days)
        expected=model['move']
        historical_rv=_historical_rv_benchmark(closes=closes,sessions=ordered_sessions,
              roots=roots,weights=weights,anchor=anchor,window=window,horizon_days=horizon_calendar_days)
        eligible=expected is not None and realized is not None
        abs_error_model=abs(abs(realized)-expected) if eligible else None
        abs_error_historical_rv=abs(abs(realized)-historical_rv) if realized is not None and historical_rv is not None else None
        reasons=list(dict.fromkeys(model['reasons']+outcome_reasons))
        result_cases.append({'anchor':anchor.isoformat(),'entry_session':entry_day,'exit_session':exit_day,
              'horizon_target_day':(anchor+timedelta(days=horizon_calendar_days)).isoformat(),
              'expected_move':expected,'realized_return':realized,
              'historical_rv_move':historical_rv,
              'abs_error_model':abs_error_model,
              'abs_error_historical_rv':abs_error_historical_rv,
              'breached_one_sigma':(abs(realized)>expected) if eligible else None,
              'iv_coverage_count':study['coverage']['count'],'original_count':study['coverage']['total_count'],
              'missing_iv_roots':study['coverage']['excluded_roots'],
              'missing_iv_reasons_by_root':{
                  r['root']:r['reasons'] for r in study['members']
                  if r['iv30'] is None},
              'iv_covered_weight':study['coverage']['weight'],
              'price_returns_for_correlation':model['n_returns'],
              'reasons':reasons,'evaluable':eligible})
    valid=[s for s in result_cases if s['evaluable']]
    paired=[s for s in valid if s['historical_rv_move'] is not None]
    breaches=sum(s['breached_one_sigma'] for s in valid)
    result={'schema':'factor_atlas.options_retrospective_outcomes/v1',
            'classification':'PRIVATE_RETROSPECTIVE_RESEARCH_NOT_SOURCE_CERTIFIED',
            'captured_at':captured_at.isoformat(),'count_total':len(result_cases),
            'count_evaluable':len(valid),'historical_known_at':None,'published':False,
            'population_basis':'retrospective_current_roster',
            'method':{'horizon_calendar_days':horizon_calendar_days,'lookback_sessions':window,
                      'forward_entry':'next cash-session close strictly after option anchor',
                      'forward_exit':'first cash-session close on or after anchor plus calendar horizon',
                      'return_measure':'equal-weight constituent buy and hold simple price return',
                      'predictor':'constituent IV with as-of historical close-return correlation',
                      'label_overlap':'refused across declared anchor windows',
                      'realized_return_is_options_payoff':False},
            'cases':result_cases,
            'descriptive':{'breach_count':breaches,'evaluable_denominator':len(valid),
                           'mean_abs_realized_move':(fsum(abs(s['realized_return']) for s in valid)/len(valid) if valid else None),
                           'mean_expected_move':(fsum(s['expected_move'] for s in valid)/len(valid) if valid else None),
                           'paired_baseline_count':len(paired),
                           'mean_abs_error_model':(fsum(s['abs_error_model'] for s in paired)/len(paired) if paired else None),
                           'mean_abs_error_historical_rv':(fsum(s['abs_error_historical_rv'] for s in paired)/len(paired) if paired else None),
                           'confidence_interval':None,'nominal_breach_probability':None},
            'source_disclosure':{'eod_quote_known_at':'UNPROVEN','current_roster_is_pit':False,
                                 'options_rights_certified':False,'price_adjustment_vintage_certified':False,
                                 'last_completed_session_at_capture':completed_cutoff.isoformat()},
            'claims':{'calibrated_probability':False,'product_iv_available':False,'user_trade_eligible':False,
                      'predictive_edge_proven':False,'production_integration':False},
            'authority':{'publication':False,'prophet':False,'position_sizing':False}}
    if research_iv_error_abs_max>0:
        result['research_sensitivity']={
          'iv_error_abs_max':float(research_iv_error_abs_max),
          'historical_mark_certified':False,
          'historical_known_at_certified':False,
          'product_published':False,
        }
    return result
