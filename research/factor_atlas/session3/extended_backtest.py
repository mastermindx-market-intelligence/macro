"""Precommitted longitudinal Factor Atlas retrospective analysis (pure helpers).

This is an exploratory owner-held source evaluation. Historical availability,
mark quality, true risk-neutral implied correlation, rights, alpha, VaR and
user trading eligibility are not established by this research calculation.
No storage, network, credential, options producer or publisher is created.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from math import comb,fsum,isclose,isfinite,log,pi,sqrt
from numbers import Real
from typing import Mapping,Sequence

import numpy as np


def build_fixed_schedule(*,start:date,last_nominal:date,sessions:Sequence[date],
                         step_calendar_days:int=35)->list[date]:
    """Fixed 35-calendar-day nominal anchors, snap each after first to next cash day.

    A given calendar and start date completely determine the population.
    Observed Greek quotes, model performance and underlying price movements
    cannot influence anchor dates or be used to quietly drop a difficult date.
    """
    if type(start) is not date or type(last_nominal) is not date or last_nominal<start:
        raise ValueError('valid exact start/end dates required')
    if type(step_calendar_days) is not int or step_calendar_days!=35:
        raise ValueError('precommitted 35-calendar-day spacing only')
    if not isinstance(sessions,Sequence) or not sessions or any(type(x) is not date for x in sessions):
        raise ValueError('typed owner calendar required')
    ordered=list(sessions)
    if ordered!=sorted(set(ordered)):
        raise ValueError('owner calendar must be strictly increasing and unique')
    if start not in ordered:
        raise ValueError('precommitted first anchor must be an actual included cash session')
    if last_nominal>ordered[-1]:
        raise ValueError('last nominal date must be inside owner calendar')
    out=[]
    nominal=start
    from bisect import bisect_left
    while nominal<=last_nominal:
        index=bisect_left(ordered,nominal)
        if index>=len(ordered):
            raise ValueError('missing future owner cash session')
        day=ordered[index]
        if day>last_nominal+timedelta(days=4):
            raise ValueError('long cash-session holiday gap')
        if out and (day-out[-1]).days<33:
            raise ValueError('anchors would overlap thirty-calendar-day forward measurement')
        out.append(day)
        nominal+=timedelta(days=step_calendar_days)
        if len(out)>48:
            raise ValueError('precommitted maximum sample exceeded')
    return out


def _finite(value:object)->float|None:
    if isinstance(value,bool) or not isinstance(value,Real):
        return None
    try:
        x=float(value)
    except (OverflowError, ValueError):
        return None
    return x if isfinite(x) else None


def summarize_paired_cases(cases:Sequence[Mapping], *,bootstrap_seed:int=20261012)->dict:
    """Honest case accounting and exploratory paired absolute-error comparison.

    Paired episode bootstrap CI presumes independence between *non-overlapping*
    forward windows; it is research sensitivity, not a trading edge
    significance certificate. The sample and metric must be frozen before
    observing outcomes; missing cases retain their original denominator.
    """
    if type(bootstrap_seed) is not int or bootstrap_seed<0 or bootstrap_seed>2**32-1:
        raise ValueError('fixed non-negative 32-bit integer bootstrap seed required')
    if not isinstance(cases,Sequence) or not 1<=len(cases)<=48:
        raise ValueError('bounded nonempty declared case population required')
    rows=[];names=set()
    for entry in cases:
        if not isinstance(entry,Mapping) or not isinstance(entry.get('anchor'),str):
            raise ValueError('case must include exact anchor date')
        try:
            anchor=date.fromisoformat(entry['anchor'])
        except ValueError as error:
            raise ValueError('case anchor must be calendar date') from error
        if anchor.isoformat()!=entry['anchor']:
            raise ValueError('canonical ISO case anchor required')
        if anchor in names:raise ValueError('duplicate source cohort anchor')
        names.add(anchor)
        if type(entry.get('evaluable')) is not bool:
            raise ValueError('explicit case evaluable flag required')
        for field in ('expected_move','realized_return','historical_rv_move',
                      'abs_error_model','abs_error_historical_rv'):
            value=entry.get(field)
            if value is not None and _finite(value) is None:
                raise ValueError('finite or missing observation values required')
        reasons=entry.get('reasons')
        if not isinstance(reasons,list) or any(not isinstance(v,str) or not v for v in reasons):
            raise ValueError('explicit source-quality reasons required')
        if entry['evaluable'] and reasons:
            raise ValueError('evaluable case contains source refusal reasons')
        for field in ('expected_move','historical_rv_move','abs_error_model','abs_error_historical_rv'):
            value=entry.get(field)
            if value is not None and value < 0:
                raise ValueError('forecast scales and absolute errors must be nonnegative')
        if entry['evaluable']:
            if entry.get('expected_move') is None or entry.get('realized_return') is None:
                raise ValueError('evaluable case lacks source/model outcome')
            breach=entry.get('breached_one_sigma')
            if type(breach) is not bool:
                raise ValueError('evaluable case requires boolean one-sigma breach receipt')
            if breach!=(abs(float(entry['realized_return']))>float(entry['expected_move'])):
                raise ValueError('inconsistent one-sigma breach receipt')
            # Do not allow a stale/tampered precomputed loss to determine the
            # comparative result independently of its forecasts and outcome.
            for scale_field,error_field in (('expected_move','abs_error_model'),
                                             ('historical_rv_move','abs_error_historical_rv')):
                scale,error=entry.get(scale_field),entry.get(error_field)
                if error is not None and (scale is None or not isclose(
                    error,abs(abs(entry['realized_return'])-scale),rel_tol=1e-12,abs_tol=1e-14)):
                    raise ValueError('inconsistent precomputed absolute-error receipt')
        rows.append(entry)
    rows.sort(key=lambda x:x['anchor'])
    valid=[x for x in rows if x['evaluable']]
    paired=[x for x in valid if x.get('abs_error_model') is not None
            and x.get('abs_error_historical_rv') is not None]
    fail=Counter(reason for row in rows if not row['evaluable'] for reason in row['reasons'])
    diffs=np.array([float(x['abs_error_model']-x['abs_error_historical_rv']) for x in paired],dtype=float)
    wins=int((diffs<0).sum())
    losses=int((diffs>0).sum())
    ties=int((diffs==0).sum())
    mean_model=(float(fsum(float(x['abs_error_model']) for x in paired)/len(paired))
                if paired else None)
    mean_rv=(float(fsum(float(x['abs_error_historical_rv']) for x in paired)/len(paired))
             if paired else None)
    mean_diff=mean_model-mean_rv if paired else None
    confidence=None
    if len(paired)>=10:
        rng=np.random.default_rng(bootstrap_seed)
        b=5000
        indices=rng.integers(0,len(diffs),size=(b,len(diffs)))
        sample_means=np.mean(diffs[indices],axis=1)
        confidence={'lower':float(np.quantile(sample_means,.025)),
                    'upper':float(np.quantile(sample_means,.975)),
                    'confidence_level_nominal':.95,
                    'resamples':b,
                    'bootstrap_seed':bootstrap_seed,
                    'assumes_nonoverlapping_episode_independence':True,
                    'exploratory_not_alpha_significance_test':True}
    return {
        'schema':'factor_atlas.s3.longitudinal_pair_summary/v1',
        'count_declared':len(rows),
        'count_evaluable':len(valid),
        'incomplete_population_count':len(rows)-len(valid),
        'paired_sample_n':len(paired),
        'mean_absolute_error_options_model':mean_model,
        'mean_absolute_error_historical_rv':mean_rv,
        'mean_paired_error_diff_model_minus_rv':mean_diff,
        'median_paired_error_diff_model_minus_rv':float(np.median(diffs)) if paired else None,
        'model_wins':wins,
        'historical_rv_wins':losses,
        'ties':ties,
        'breaches':sum(bool(x['breached_one_sigma']) for x in valid if x.get('breached_one_sigma') is not None),
        'not_evaluable_reasons':dict(sorted(fail.items())),
        'confidence_interval_exploratory':confidence,
        'population_policy':'all_precommitted_anchors_in_denominator',
        'predictive_superiority_certified':False,
        'historical_source_known_at_certified':False,
        'source_rights_certified':False,
        'publication_approved':False,
    }


def summarize_by_calendar_year(cases:Sequence[Mapping])->dict[str,dict]:
    """Expose sampling imbalance by year; never erase non-evaluable episodes."""
    if not isinstance(cases,Sequence) or not cases:
        raise ValueError('nonempty precommitted cohort required')
    years:dict[str,list]= {}
    for item in cases:
        if not isinstance(item,Mapping) or not isinstance(item.get('anchor'),str):
            raise ValueError('typed exact source case required')
        anchor=item['anchor']
        try: day=date.fromisoformat(anchor)
        except ValueError as err:raise ValueError('exact date required') from err
        years.setdefault(str(day.year),[]).append(item)
    # Existing accepted summarizer owns finite-value, duplicate, and
    # original-denominator checks. It is not a secondary score calculator.
    return {year:summarize_paired_cases(items) for year,items in sorted(years.items())}


def summarize_volatility_scoring(cases:Sequence[Mapping], *,
                                  bootstrap_seed:int=20261012)->dict:
    """Compare paired horizon-variance hypotheses on a proper Gaussian score.

    Uses 30-calendar-day *modeled sigma*, not a forecast of |return|. The
    Gaussian zero-mean negative-log score and its QLIKE proportional cousin
    are conditional-variance diagnostics; neither proves a Gaussian law,
    option P&L, historical available IVs, or predictive alpha. All excluded
    cases retain their declared denominator and residual reason.
    """
    if type(bootstrap_seed) is not int or not 0<=bootstrap_seed<2**32:
        raise ValueError('bounded fixed bootstrap seed required')
    if not isinstance(cases,Sequence) or not 1<=len(cases)<=48:
        raise ValueError('bounded precommitted cohort required')
    scores=[];seen=set()
    for entry in sorted(cases,key=lambda v:v.get('anchor','')):
        if not isinstance(entry,Mapping):
            raise ValueError('original source case must be typed mapping')
        label=entry.get('anchor')
        if not isinstance(label,str):
            raise ValueError('source anchor identity required')
        try:anchor=date.fromisoformat(label)
        except ValueError as error:
            raise ValueError('invalid source anchor') from error
        if anchor.isoformat()!=label:
            raise ValueError('canonical source anchor date required')
        if anchor in seen:
            raise ValueError('duplicate precommitted anchor')
        seen.add(anchor)
        if type(entry.get('evaluable')) is not bool:
            raise ValueError('explicit original model admission required')
        reasons=entry.get('reasons')
        if not isinstance(reasons,list) or any(not isinstance(v,str) or not v for v in reasons):
            raise ValueError('explicit source-quality reasons required')
        if entry['evaluable'] and reasons:
            raise ValueError('evaluable case contains source refusal reasons')
        for key in ('expected_move','historical_rv_move','realized_return'):
            value=entry.get(key)
            if value is not None and _finite(value) is None:
                raise ValueError('finite source score inputs required')
        sigma=_finite(entry.get('expected_move'))
        rv=_finite(entry.get('historical_rv_move'))
        ret=_finite(entry.get('realized_return'))
        valid=entry['evaluable'] and sigma is not None and sigma>0 and rv is not None and rv>0 and ret is not None
        item={'anchor':label,'score_valid':bool(valid),
              'gaussian_nll_omit_constant_model':None,'gaussian_nll_omit_constant_rv':None,
              'qlike_model':None,'qlike_rv':None,
              'expected_abs_move_model_normal_assumption':None,
              'expected_abs_move_rv_normal_assumption':None,
              'abs_error_expected_abs_model':None,'abs_error_expected_abs_rv':None}
        if valid:
            # Form standardized returns before squaring. Squaring a tiny
            # positive sigma first can underflow to zero and crash the audit.
            z_model,z_rv=ret/sigma,ret/rv
            square_model,square_rv=z_model*z_model,z_rv*z_rv
            if not isfinite(square_model) or not isfinite(square_rv):
                raise ValueError('nonfinite proper-score computation')
            item.update({
                'gaussian_nll_omit_constant_model':log(sigma)+.5*square_model,
                'gaussian_nll_omit_constant_rv':log(rv)+.5*square_rv,
                'qlike_model':2*log(sigma)+square_model,
                'qlike_rv':2*log(rv)+square_rv,
                'expected_abs_move_model_normal_assumption':sigma*sqrt(2/pi),
                'expected_abs_move_rv_normal_assumption':rv*sqrt(2/pi),
                'abs_error_expected_abs_model':abs(abs(ret)-sigma*sqrt(2/pi)),
                'abs_error_expected_abs_rv':abs(abs(ret)-rv*sqrt(2/pi)),
            })
            if not all(isfinite(v) for k,v in item.items() if k not in ('anchor','score_valid') and v is not None):
                raise ValueError('nonfinite proper-score computation')
        scores.append(item)
    paired=[x for x in scores if x['score_valid']]
    def avg(key):
        return float(fsum(x[key] for x in paired)/len(paired)) if paired else None
    qlike_model=avg('qlike_model')
    qlike_rv=avg('qlike_rv')
    nll_model=avg('gaussian_nll_omit_constant_model')
    nll_rv=avg('gaussian_nll_omit_constant_rv')
    differences=np.array([x['qlike_model']-x['qlike_rv'] for x in paired],dtype=float)
    sign_n=int((differences!=0).sum())
    sign_p=None
    if sign_n:
        k=min(int((differences<0).sum()),int((differences>0).sum()))
        sign_p=min(1.,float(2*sum(comb(sign_n,i) for i in range(k+1))/(2**sign_n)))
    bootstrap=None
    if len(paired)>=10:
        rng=np.random.default_rng(bootstrap_seed)
        draw_means=differences[rng.integers(0,len(paired),size=(5000,len(paired)))].mean(axis=1)
        bootstrap={'lower':float(np.quantile(draw_means,.025)),
                   'upper':float(np.quantile(draw_means,.975)),
                   'nominal_level':.95,'seed':bootstrap_seed,'resamples':5000,
                   'not_multiple_test_corrected':True,
                   'episode_independence_only_approximate':True}
    return {
        'schema':'factor_atlas.s3.private_longitudinal_variance_score/v1',
        'count_declared':len(scores),
        'pair_count':len(paired),
        'count_unscored':len(scores)-len(paired),
        'case_scores':scores,
        'mean_gaussian_nll_omit_constant_model':nll_model,
        'mean_gaussian_nll_omit_constant_rv':nll_rv,
        'mean_qlike_model':qlike_model,
        'mean_qlike_rv':qlike_rv,
        'paired_qlike_diff_model_minus_rv':qlike_model-qlike_rv if paired else None,
        'mean_abs_error_gaussian_eabs_model':avg('abs_error_expected_abs_model'),
        'mean_abs_error_gaussian_eabs_rv':avg('abs_error_expected_abs_rv'),
        'model_qlike_wins':int((differences<0).sum()),
        'historical_rv_qlike_wins':int((differences>0).sum()),
        'qlike_ties':int((differences==0).sum()),
        'sign_test_population':sign_n,
        'paired_sign_test_two_sided_p':sign_p,
        'sign_test_multiple_comparisons_adjusted':False,
        'paired_bootstrap_qlike_diff_exploratory':bootstrap,
        'variance_proxy':'one_horizon_simple_return_squared',
        'forward_return_square_is_noisy_variance_proxy':True,
        'zero_mean_gaussian_scoring_assumption':True,
        'distribution_calibrated':False,
        'option_trade_pnl_measured':False,
        'as_known_historical_quote_rights_certified':False,
        'multiple_threshold_selection_corrected':False,
        'predictive_edge_proven':False,
        'publication':False,
    }
