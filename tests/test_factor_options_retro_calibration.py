"""TDD: retrospective 30-calendar-day factor-options outcome evaluation.

The synthetic close panels use complete owner-like daily session labels. No historical
availability claims, derived recommendation, probability fit, or vendor I/O.
"""
from datetime import date, datetime, timedelta, timezone
from importlib import import_module
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest

MODULE = 'research.factor_atlas.session3.retrospective_calibration'
CAPTURE = datetime(2026,10,11,22,tzinfo=timezone.utc)

@pytest.fixture
def m():
    path=Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/retrospective_calibration.py'
    assert path.is_file(), 'retrospective outcome evaluation module not yet built'
    return import_module(MODULE)

@pytest.fixture
def fx():
    dates=pd.bdate_range('2024-01-02',periods=560)
    roots=['AAA','BBB','CCC']
    rng=np.random.default_rng(1234)
    mkt=rng.normal(0,.012,len(dates))
    prices=pd.DataFrame({r:100*np.exp(np.cumsum(mkt+rng.normal(0,.01,len(dates)))) for r in roots},index=dates)
    anchors=[dates[365].date(),dates[410].date()]
    def rows(root,anchor):
        return pd.DataFrame([{'root':root,'date':pd.Timestamp(anchor),
            'expiration':pd.Timestamp(anchor)+pd.Timedelta(days=d),
            'strike':100.,'right':side,'bid':9.5,'ask':10.,'underlying_price':100.,
            'implied_vol':.20+0.03*roots.index(root),'iv_error':0.}
            for d in (29,36) for side in ('C','P')])
    inputs={anchor:{r:rows(r,anchor) for r in roots} for anchor in anchors}
    return dict(weights={r:1/3 for r in roots},greeks_by_anchor=inputs,closes=prices,
                sessions=list(dates.date),anchors=anchors,captured_at=CAPTURE)

def test_exact_multi_case_prediction_and_realized_forward(m,fx):
    result=m.evaluate(**fx)
    assert result['schema']=='factor_atlas.options_retrospective_outcomes/v1'
    assert len(result['cases'])==2 and result['count_total']==2
    assert result['count_evaluable']==2
    assert result['published']==False and result['historical_known_at']==None
    assert result['claims']['calibrated_probability'] is False
    first=result['cases'][0]
    assert first['expected_move'] is not None and first['realized_return'] is not None
    assert first['entry_session']>first['anchor'] and first['exit_session']>=str(fx['anchors'][0]+timedelta(days=30))
    ent=fx['closes'].loc[first['entry_session']]
    out=fx['closes'].loc[first['exit_session']]
    manual=((out/ent-1)*pd.Series(fx['weights'])).sum()
    assert first['realized_return']==pytest.approx(manual)
    assert first['breached_one_sigma']==(abs(manual)>first['expected_move'])
    assert result['descriptive']['breach_count']==sum(c['breached_one_sigma'] for c in result['cases'])
    json.dumps(result,allow_nan=False)

def test_actual_retro_calibration_output_roundtrips_into_both_s3_summaries(m,fx):
    """Use the real synthetic producer, not hand-authored evaluable receipts."""
    from research.factor_atlas.session3.extended_backtest import (
        summarize_paired_cases, summarize_volatility_scoring,
    )
    actual=m.evaluate(**fx)
    assert actual['count_evaluable']==2
    assert all(row['evaluable'] and row['reasons']==[] and
               type(row['breached_one_sigma']) is bool for row in actual['cases'])
    paired=summarize_paired_cases(actual['cases'])
    score=summarize_volatility_scoring(actual['cases'])
    assert paired['count_declared']==paired['count_evaluable']==paired['paired_sample_n']==2
    assert score['count_declared']==score['pair_count']==2
    assert paired['publication_approved'] is False and score['publication'] is False
    fx['greeks_by_anchor'][fx['anchors'][-1]].pop('AAA')
    withheld=m.evaluate(**fx)
    assert withheld['count_total']==2 and withheld['count_evaluable']==1
    assert 'INCOMPLETE_IV_COVERAGE' in withheld['cases'][-1]['reasons']
    paired=summarize_paired_cases(withheld['cases'])
    score=summarize_volatility_scoring(withheld['cases'])
    assert paired['count_declared']==2 and paired['count_evaluable']==1
    assert paired['paired_sample_n']==1 and paired['incomplete_population_count']==1
    assert score['count_declared']==2 and score['pair_count']==1 and score['count_unscored']==1
    assert all(not row['score_valid'] for row in score['case_scores'] if
               row['anchor']==withheld['cases'][-1]['anchor'])


def test_future_price_change_does_not_change_prediction(m,fx):
    baseline=m.evaluate(**fx)
    first_exit=pd.Timestamp(baseline['cases'][0]['exit_session'])
    fx['closes'].loc[first_exit,'AAA']*=2
    changed=m.evaluate(**fx)
    assert changed['cases'][0]['expected_move']==pytest.approx(baseline['cases'][0]['expected_move'])
    assert changed['cases'][0]['realized_return']!=pytest.approx(baseline['cases'][0]['realized_return'])

def test_missing_one_anchor_chain_retains_null_case(m,fx):
    fx['greeks_by_anchor'].pop(fx['anchors'][1])
    result=m.evaluate(**fx)
    assert result['count_total']==2 and result['count_evaluable']==1
    last=result['cases'][-1]
    assert 'INCOMPLETE_IV_COVERAGE' in last['reasons']
    assert last['expected_move'] is None

def test_forward_price_gap_withholds_outcome(m,fx):
    first=fx['anchors'][0]
    next_day=next(d for d in fx['sessions'] if d>first)
    fx['closes'].loc[pd.Timestamp(next_day),'BBB']=np.nan
    result=m.evaluate(**fx)
    assert result['cases'][0]['realized_return'] is None
    assert 'INCOMPLETE_FORWARD_PRICE_WINDOW' in result['cases'][0]['reasons']

def test_exit_not_observed_stays_in_population(m,fx):
    # Anchor still available, but preselected exit is beyond the last price day.
    later=fx['sessions'][-8]
    fx['anchors']=[later]
    fx['greeks_by_anchor']={later:{r:pd.DataFrame([{
      'root':r,'date':pd.Timestamp(later),'expiration':pd.Timestamp(later)+pd.Timedelta(days=d),
      'strike':100.,'right':side,'bid':9.5,'ask':10.,'underlying_price':100.,
      'implied_vol':.25,'iv_error':0.} for d in (29,36) for side in ('C','P')]) for r in fx['weights']}}
    result=m.evaluate(**fx)
    assert result['count_evaluable']==0
    assert 'FORWARD_HORIZON_NOT_OBSERVED' in result['cases'][0]['reasons']

def test_no_backdated_historical_clock_or_one_sigma_probability_claim(m,fx):
    result=m.evaluate(**fx)
    assert result['source_disclosure']['eod_quote_known_at']=='UNPROVEN'
    assert result['source_disclosure']['current_roster_is_pit']==False
    assert result['source_disclosure']['options_rights_certified']==False
    assert result['descriptive']['confidence_interval'] is None
    assert result['descriptive']['nominal_breach_probability'] is None
    assert result['claims']['user_trade_eligible']==False

def test_no_cherry_picking_overlapping_forward_windows(m,fx):
    anchor=fx['anchors'][0]
    next_anchor=next(day for day in fx['sessions'] if day>=anchor+timedelta(days=14))
    fx['anchors']=[anchor,next_anchor]
    fx['greeks_by_anchor']={anchor:fx['greeks_by_anchor'][anchor],next_anchor:fx['greeks_by_anchor'][anchor]}
    with pytest.raises(ValueError,match='overlap'):
        m.evaluate(**fx)

@pytest.mark.parametrize('mode',['duplicate','unordered','non_session','future','extra_greek'])
def test_anchor_identity_and_clock_fail_closed(m,fx,mode):
    if mode=='duplicate':fx['anchors']=[fx['anchors'][0],fx['anchors'][0]]
    if mode=='unordered':fx['anchors']=fx['anchors'][::-1]
    if mode=='non_session':fx['anchors']=[fx['anchors'][0]+timedelta(days=1)]
    if mode=='future':fx['anchors']=[fx['sessions'][-1]+timedelta(days=5)]
    if mode=='extra_greek':fx['greeks_by_anchor'][fx['anchors'][0]]['UNIVERSE_UNKNOWN']=pd.DataFrame()
    with pytest.raises(ValueError):m.evaluate(**fx)

def test_unrepresentable_weight_and_price_refuse_without_overflow(m,fx):
    # The producer must reject an unrepresentable numerical field in its
    # existing source-validation path, even under the system Python version.
    assert m._positive_price(10**500) is False
    fx['weights']['AAA']=10**500
    with pytest.raises(ValueError,match='positive numeric'):
        m.evaluate(**fx)


def test_nonpositive_and_empty_weights_refused(m,fx):
    fx['weights']['AAA']=0
    with pytest.raises(ValueError):m.evaluate(**fx)

def test_unmatched_source_close_price_cannot_be_used(m,fx):
    fx['closes']=fx['closes'].drop(columns='BBB')
    result=m.evaluate(**fx)
    assert result['count_evaluable']==0
    assert all('INCOMPLETE_FORWARD_PRICE_WINDOW' in c['reasons'] for c in result['cases'])

def test_breach_count_no_ghost_denominator(m,fx):
    fx['greeks_by_anchor'].pop(fx['anchors'][0])
    result=m.evaluate(**fx)
    assert result['descriptive']['evaluable_denominator']==1
    assert result['count_total']==2

def test_realized_volatility_baseline_is_pit_and_math_consistent(m,fx):
    r=m.evaluate(**fx)
    case=r['cases'][0]
    sample=fx['closes'].loc[:case['anchor']].tail(253)
    returns=np.diff(np.log(sample.to_numpy(dtype=float)),axis=0)
    w=np.array([fx['weights'][k] for k in sample.columns])
    expected=np.sqrt(max(0,float(w@np.cov(returns,rowvar=False)@w))*252*30/365)
    assert case['historical_rv_move']==pytest.approx(expected)
    assert case['abs_error_model']==pytest.approx(abs(abs(case['realized_return'])-case['expected_move']))
    assert case['abs_error_historical_rv']==pytest.approx(abs(abs(case['realized_return'])-case['historical_rv_move']))
    assert r['descriptive']['paired_baseline_count']==2
    assert r['descriptive']['mean_abs_error_model'] is not None
    assert r['descriptive']['mean_abs_error_historical_rv'] is not None

def test_future_outcome_edit_cannot_move_rv_benchmark(m,fx):
    original=m.evaluate(**fx)
    day=original['cases'][0]['exit_session']
    fx['closes'].loc[pd.Timestamp(day),'AAA']*=3
    result=m.evaluate(**fx)
    assert result['cases'][0]['historical_rv_move']==pytest.approx(original['cases'][0]['historical_rv_move'])
    assert result['cases'][0]['abs_error_historical_rv']!=pytest.approx(original['cases'][0]['abs_error_historical_rv'])

def test_price_gap_withholds_benchmark_not_just_iv_model(m,fx):
    fx['closes'].iloc[-180,0]=np.nan
    r=m.evaluate(**fx)
    assert r['cases'][1]['historical_rv_move'] is None
    assert r['cases'][1]['expected_move'] is None
    assert r['cases'][1]['abs_error_historical_rv'] is None

def test_missing_iv_name_does_not_remove_independent_rv_benchmark(m,fx):
    fx['greeks_by_anchor'][fx['anchors'][0]].pop('AAA')
    r=m.evaluate(**fx)
    assert r['cases'][0]['expected_move'] is None
    assert r['cases'][0]['historical_rv_move'] is not None
    assert r['descriptive']['paired_baseline_count']==1

def test_capture_clock_never_admits_unobserved_future_exit(m,fx):
    # Source contains future rows, but the research capture occurred only 10
    # calendar days after the first anchor. Those later prices cannot label it.
    first=fx['anchors'][0]
    fx['anchors']=[first]
    fx['greeks_by_anchor']={first:fx['greeks_by_anchor'][first]}
    fx['captured_at']=datetime.combine(first+timedelta(days=10),datetime.min.time(),tzinfo=timezone.utc)
    r=m.evaluate(**fx)
    assert r['cases'][0]['realized_return'] is None
    assert r['count_evaluable']==0
    assert 'FORWARD_HORIZON_NOT_OBSERVED' in r['cases'][0]['reasons']
    assert r['source_disclosure']['last_completed_session_at_capture'] is not None

def test_capture_before_anchor_is_refused_even_if_future_price_files_exist(m,fx):
    fx['captured_at']=datetime.combine(fx['anchors'][-1]-timedelta(days=2),datetime.min.time(),tzinfo=timezone.utc)
    with pytest.raises(ValueError,match='anchor'):
        m.evaluate(**fx)

def test_non_evaluable_episode_preserves_exact_missing_roots_and_reasons(m,fx):
    first=fx['anchors'][0]
    fx['greeks_by_anchor'][first].pop('AAA')
    result=m.evaluate(**fx)
    row=result['cases'][0]
    assert row['iv_coverage_count']==2 and row['original_count']==3
    assert row['missing_iv_roots']==['AAA']
    assert row['missing_iv_reasons_by_root']=={'AAA':['NO_SOURCE_ROWS']}
    assert row['expected_move'] is None

def test_fully_evaluable_episode_has_empty_missing_root_reasons(m,fx):
    result=m.evaluate(**fx)
    assert all(case['missing_iv_roots']==[] for case in result['cases'])
    assert all(case['missing_iv_reasons_by_root']=={} for case in result['cases'])

@pytest.mark.parametrize('horizon',[1,7,29,31,60,90])
def test_non_30day_horizon_cannot_compare_against_fixed_iv30_model(m,fx,horizon):
    with pytest.raises(ValueError,match='30-calendar-day'):
        m.evaluate(**fx,horizon_calendar_days=horizon)


def test_explicit_30day_horizon_preserves_existing_result(m,fx):
    assert m.evaluate(**fx,horizon_calendar_days=30)==m.evaluate(**fx)
