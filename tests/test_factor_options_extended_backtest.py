"""S3 fixed-schedule, non-overlapping options/realized-vol experiment."""
from datetime import date,datetime,timedelta,timezone
from importlib import import_module
from pathlib import Path
import math
import numpy as np
import pytest

MODULE='research.factor_atlas.session3.extended_backtest'

@pytest.fixture
def m():
    assert (Path(__file__).resolve().parents[1]/'research/factor_atlas/session3/extended_backtest.py').exists(), 'new pure extended research study source missing'
    return import_module(MODULE)

def sessions(start=date(2023,6,1),end=date(2026,9,30)):
    from lib.us_cash_calendar import sessions_between
    return sessions_between(start,end)

def case(anchor,model=.075,realized=.055,rv=.08):
    return dict(anchor=anchor.isoformat(),evaluable=True,expected_move=model,
      historical_rv_move=rv,realized_return=realized,
      abs_error_model=abs(abs(realized)-model),
      abs_error_historical_rv=abs(abs(realized)-rv),
      breached_one_sigma=abs(realized)>model,reasons=[])

def test_schedule_predeclared_33_original_calendar_episodes(m):
    arr=m.build_fixed_schedule(start=date(2023,7,3),last_nominal=date(2026,8,15),sessions=sessions())
    assert len(arr)==33
    assert arr[0]==date(2023,7,3) and arr[-1]==date(2026,7,27)
    assert min((b-a).days for a,b in zip(arr,arr[1:]))>=34
    assert [sum(x.year==y for x in arr) for y in (2023,2024,2025,2026)]==[6,10,11,6]

def test_schedule_never_selects_dates_based_on_source_quality(m):
    a=m.build_fixed_schedule(start=date(2024,1,2),last_nominal=date(2024,8,31),sessions=sessions())
    assert len(a)==7
    assert a[0]==date(2024,1,2)
    assert all(x in sessions() for x in a)

@pytest.mark.parametrize('mode',['duplicate','unsorted','gap','before','nan_date','short_step'])
def test_calendar_contract_refuses_uncontrolled_selection(m,mode):
    s=sessions()
    start=date(2024,1,2)
    if mode=='duplicate':s=s[:100]+[s[99]]+s[100:]
    if mode=='unsorted':s=s[::-1]
    if mode=='gap':s=[x for x in s if x!=date(2024,1,2)]
    if mode=='before':start=date(2023,3,1)
    if mode=='nan_date':s=s[:-1]+['notadate']
    if mode=='short_step':
        with pytest.raises(ValueError,match='spacing'):
            m.build_fixed_schedule(start=start,last_nominal=date(2024,7,1),sessions=s,step_calendar_days=7)
        return
    with pytest.raises(ValueError):
        m.build_fixed_schedule(start=start,last_nominal=date(2024,7,1),sessions=s)

def test_summary_paired_mae_and_bootstrap_deterministic(m):
    days=[date(2025,1,2)+timedelta(days=i*35) for i in range(20)]
    cases=[case(d,model=.06+i*.0001,rv=.08,realized=.045+(i%5)*.01) for i,d in enumerate(days)]
    a=m.summarize_paired_cases(cases,bootstrap_seed=20261012)
    b=m.summarize_paired_cases(cases,bootstrap_seed=20261012)
    assert a==b
    assert a['count_declared']==a['count_evaluable']==a['paired_sample_n']==20
    assert a['mean_absolute_error_options_model']==pytest.approx(np.mean([x['abs_error_model'] for x in cases]))
    assert a['mean_absolute_error_historical_rv']==pytest.approx(np.mean([x['abs_error_historical_rv'] for x in cases]))
    assert a['mean_paired_error_diff_model_minus_rv']==pytest.approx(a['mean_absolute_error_options_model']-a['mean_absolute_error_historical_rv'])
    assert a['confidence_interval_exploratory']['lower']<=a['mean_paired_error_diff_model_minus_rv']<=a['confidence_interval_exploratory']['upper']
    assert a['predictive_superiority_certified'] is False
    assert a['historical_source_known_at_certified'] is False

def test_missing_cases_kept_and_never_enter_paired_error(m):
    cases=[case(date(2025,1,2)+timedelta(days=35*i)) for i in range(8)]
    cases[3]=dict(cases[3],evaluable=False,expected_move=None,abs_error_model=None,breached_one_sigma=None,reasons=['INCOMPLETE_IV_COVERAGE'])
    cases[6]=dict(cases[6],evaluable=False,realized_return=None,abs_error_historical_rv=None,breached_one_sigma=None,reasons=['FORWARD_HORIZON_NOT_OBSERVED'])
    r=m.summarize_paired_cases(cases)
    assert r['count_declared']==8 and r['count_evaluable']==6 and r['paired_sample_n']==6
    assert r['not_evaluable_reasons']=={'FORWARD_HORIZON_NOT_OBSERVED':1,'INCOMPLETE_IV_COVERAGE':1}
    assert r['confidence_interval_exploratory'] is None
    assert r['incomplete_population_count']==2

def test_no_paired_data_does_not_claim_win(m):
    arr=[dict(case(date(2025,1,2)+timedelta(days=i*35)),evaluable=False,expected_move=None,abs_error_model=None) for i in range(12)]
    r=m.summarize_paired_cases(arr)
    assert r['paired_sample_n']==0
    assert r['mean_paired_error_diff_model_minus_rv'] is None
    assert r['confidence_interval_exploratory'] is None
    assert r['model_wins']==0

def test_breaches_and_ties_are_not_fabricated(m):
    x=[case(date(2025,1,2)+timedelta(days=i*35),model=.06,rv=.06,realized=.055) for i in range(12)]
    y=m.summarize_paired_cases(x)
    assert y['model_wins']==0 and y['historical_rv_wins']==0 and y['ties']==12
    assert y['breaches']==0

def test_unrepresentable_source_integer_refuses_in_both_summaries(m):
    row=case(date(2025,1,2),model=.08,rv=.11,realized=.04)
    row['expected_move']=10**500
    for summary in (m.summarize_paired_cases,m.summarize_volatility_scoring):
        with pytest.raises(ValueError,match='finite'):
            summary([row])


def test_nonfinite_outcome_refuses_not_outlier_clipped(m):
    cases=[case(date(2025,1,2)+timedelta(days=i*35)) for i in range(12)]
    cases[7]['abs_error_model']=float('nan')
    with pytest.raises(ValueError,match='finite'):
        m.summarize_paired_cases(cases)

def test_sample_order_invariance_and_seeded_bootstrap(m):
    x=[case(date(2025,1,2)+timedelta(days=i*35),model=.05+.001*i,rv=.06+.001*i,realized=.03+.005*(i%3)) for i in range(16)]
    a=m.summarize_paired_cases(x)
    b=m.summarize_paired_cases(list(reversed(x)))
    assert a==b

def test_pre_registered_bootstrap_seed_and_draw_count_are_bounded(m):
    x=[case(date(2025,1,2)+timedelta(days=i*35)) for i in range(12)]
    for seed in (True, -1, 1e4, '34'):
        with pytest.raises(ValueError):m.summarize_paired_cases(x,bootstrap_seed=seed)

def test_duplicate_anchors_refused(m):
    x=[case(date(2025,1,2)),case(date(2025,1,2))]
    with pytest.raises(ValueError,match='duplicate'):
        m.summarize_paired_cases(x)


@pytest.mark.parametrize('reason', [
    'INCOMPLETE_IV_COVERAGE', 'INCOMPLETE_FORWARD_PRICE_WINDOW',
    'SOURCE_NOT_KNOWN_AT_DECISION',
])
def test_evaluable_flag_cannot_override_source_refusal(m,reason):
    row=case(date(2025,1,2),model=.08,rv=.11,realized=.04)
    row['reasons']=[reason]
    for summarize in (m.summarize_paired_cases,m.summarize_volatility_scoring):
        with pytest.raises(ValueError,match='evaluable.*source refusal'):
            summarize([row])


@pytest.mark.parametrize('model,realized,bad_breach,why', [
    (.08,.04,True,'inconsistent one-sigma breach receipt'),
    (.08,.04,1,'requires boolean one-sigma breach receipt'),
    (.08,.04,'false','requires boolean one-sigma breach receipt'),
    (.08,.04,None,'requires boolean one-sigma breach receipt'),
    (.04,.08,1,'requires boolean one-sigma breach receipt'),
    (.04,.08,1.0,'requires boolean one-sigma breach receipt'),
    (.04,.08,np.bool_(True),'requires boolean one-sigma breach receipt'),
    (.04,.08,False,'inconsistent one-sigma breach receipt'),
])
def test_invalid_one_sigma_breach_receipt_refused(m,model,realized,bad_breach,why):
    row=case(date(2025,1,2),model=model,rv=.11,realized=realized)
    row['breached_one_sigma']=bad_breach
    with pytest.raises(ValueError,match=why):
        m.summarize_paired_cases([row])


@pytest.mark.parametrize('model,realized,expected_breach', [
    (.04,.08,True),
    (.04,.04,False),
    (.08,.04,False),
])
def test_proper_boolean_breach_and_equality_boundary_remain_admitted(m,model,realized,expected_breach):
    row=case(date(2025,1,2),model=model,rv=.11,realized=realized)
    assert row['breached_one_sigma'] is expected_breach
    result=m.summarize_paired_cases([row])
    assert result['count_evaluable']==1 and result['paired_sample_n']==1
    assert result['breaches']==int(expected_breach)
    assert result['publication_approved'] is False


@pytest.mark.parametrize('bad_reasons', [None, 'NO_SOURCE', [''], [0], ['OK', None]])
def test_proper_score_requires_typed_source_reason_list(m,bad_reasons):
    row=case(date(2025,1,2),model=.08,rv=.11,realized=.04)
    row['reasons']=bad_reasons
    with pytest.raises(ValueError,match='source-quality reasons'):
        m.summarize_volatility_scoring([row])


def test_year_strata_preserve_every_declared_anchor_and_missing_case(m):
    allcases=[]
    for year,n in ((2023,6),(2024,10),(2025,11),(2026,6)):
        for i in range(n):
            d=date(year,1,2)+timedelta(days=35*i)
            item=case(d,model=.06+.001*i,rv=.08,realized=.04+.002*i)
            if year==2023 or (year==2024 and i<7):
                item=dict(item,evaluable=False,expected_move=None,abs_error_model=None,
                          breached_one_sigma=None,reasons=['INCOMPLETE_IV_COVERAGE'])
            allcases.append(item)
    strata=m.summarize_by_calendar_year(allcases)
    assert {year:v['count_declared'] for year,v in strata.items()}=={'2023':6,'2024':10,'2025':11,'2026':6}
    assert [strata[y]['count_evaluable'] for y in ('2023','2024','2025','2026')]==[0,3,11,6]
    assert strata['2023']['mean_paired_error_diff_model_minus_rv'] is None
    assert strata['2024']['confidence_interval_exploratory'] is None
    assert all(v['predictive_superiority_certified'] is False for v in strata.values())

def test_aggregate_strata_rejects_duplicate_anchors(m):
    x=case(date(2025,1,2))
    with pytest.raises(ValueError,match='duplicate'):
        m.summarize_by_calendar_year([x,x])

def test_gaussian_volatility_logscore_and_expected_absolute_move_math(m):
    x=case(date(2025,1,2),model=.10,rv=.12,realized=-.08)
    vals=m.summarize_volatility_scoring([x])
    row=vals['case_scores'][0]
    assert row['expected_abs_move_model_normal_assumption']==pytest.approx(.10*math.sqrt(2/math.pi))
    assert row['expected_abs_move_rv_normal_assumption']==pytest.approx(.12*math.sqrt(2/math.pi))
    assert row['gaussian_nll_omit_constant_model']==pytest.approx(math.log(.10)+.5*(.08/.10)**2)
    assert row['gaussian_nll_omit_constant_rv']==pytest.approx(math.log(.12)+.5*(.08/.12)**2)
    assert row['qlike_model']==pytest.approx(math.log(.10**2)+(.08**2)/(.10**2))
    assert row['qlike_rv']==pytest.approx(math.log(.12**2)+(.08**2)/(.12**2))
    assert vals['distribution_calibrated'] is False
    assert vals['predictive_edge_proven'] is False

def test_paired_proper_score_denominator_and_sensitivity(m):
    cohorts=[case(date(2025,1,2)+timedelta(days=35*i),model=.08+.001*i,rv=.11,
                  realized=.04+.01*(i%4)) for i in range(24)]
    for i in (2,9,19):
        cohorts[i]=dict(cohorts[i],evaluable=False,expected_move=None,abs_error_model=None,
                        breached_one_sigma=None,reasons=['INCOMPLETE_IV_COVERAGE'])
    a=m.summarize_volatility_scoring(cohorts)
    assert a['count_declared']==24 and a['pair_count']==21
    assert a['count_unscored']==3
    assert a['mean_qlike_model'] is not None
    assert a['mean_qlike_rv'] is not None
    assert a['paired_qlike_diff_model_minus_rv']==pytest.approx(a['mean_qlike_model']-a['mean_qlike_rv'])
    assert a['paired_bootstrap_qlike_diff_exploratory'] is not None
    assert a==m.summarize_volatility_scoring(list(reversed(cohorts)))

def test_too_small_positive_sigma_withheld_not_infinite_score(m):
    cohort=[case(date(2025,1,2)+timedelta(days=35*i),model=.08,rv=.11,realized=.04) for i in range(12)]
    cohort[0]['expected_move']=0
    cohort[1]['historical_rv_move']=0
    r=m.summarize_volatility_scoring(cohort)
    assert r['pair_count']==10
    assert r['case_scores'][0]['score_valid'] is False
    assert r['case_scores'][1]['score_valid'] is False

def test_nonfinite_score_input_refused(m):
    cohort=[case(date(2025,1,2),model=.08,rv=.11,realized=.04)]
    cohort[0]['historical_rv_move']=float('inf')
    with pytest.raises(ValueError,match='finite'):
        m.summarize_volatility_scoring(cohort)

def test_variance_score_not_sold_as_options_pnl_or_distribution_proof(m):
    cohort=[case(date(2025,1,2)+timedelta(days=35*i),model=.08,rv=.11,realized=.04) for i in range(12)]
    r=m.summarize_volatility_scoring(cohort)
    assert r['forward_return_square_is_noisy_variance_proxy'] is True
    assert r['zero_mean_gaussian_scoring_assumption'] is True
    assert r['option_trade_pnl_measured'] is False
    assert r['as_known_historical_quote_rights_certified'] is False
    assert r['multiple_threshold_selection_corrected'] is False
    assert r['predictive_edge_proven'] is False

def test_duplicate_source_case_refused_for_proper_score(m):
    x=case(date(2025,1,2),model=.08,rv=.11,realized=.04)
    with pytest.raises(ValueError,match='duplicate'):
        m.summarize_volatility_scoring([x,x])

def test_qlike_win_count_exact_two_sided_sign_test_is_exploratory(m):
    episodes=[case(date(2024,1,2)+timedelta(days=35*i),model=.075,rv=.11,
                   realized=(.025 if i<3 else .19)) for i in range(13)]
    output=m.summarize_volatility_scoring(episodes)
    assert output['paired_sign_test_two_sided_p'] is not None
    assert output['sign_test_population']==13
    assert 0<=output['paired_sign_test_two_sided_p']<=1
    assert output['sign_test_multiple_comparisons_adjusted'] is False
    assert output['predictive_edge_proven'] is False

def test_all_tied_qlike_cases_cannot_claim_significance(m):
    episodes=[case(date(2024,1,2)+timedelta(days=35*i),model=.10,rv=.10,
                   realized=.055) for i in range(13)]
    out=m.summarize_volatility_scoring(episodes)
    assert out['model_qlike_wins']==0 and out['historical_rv_qlike_wins']==0
    assert out['sign_test_population']==0
    assert out['paired_sign_test_two_sided_p'] is None

@pytest.mark.parametrize('field,value',[
    ('abs_error_model',0.999),('abs_error_historical_rv',0.999),
    ('expected_move',-0.1),('historical_rv_move',-0.1),
])
def test_paired_summary_rejects_inconsistent_or_negative_forecast_receipts(m,field,value):
    row=case(date(2025,1,2),model=.08,rv=.11,realized=.04)
    row[field]=value
    with pytest.raises(ValueError,match='consistent|nonnegative'):
        m.summarize_paired_cases([row])


def test_gaussian_scoring_does_not_underflow_a_positive_scale_to_zero(m):
    row=case(date(2025,1,2),model=1e-200,rv=.11,realized=0.)
    out=m.summarize_volatility_scoring([row])
    assert out['pair_count']==1
    assert out['mean_qlike_model']==pytest.approx(2*math.log(1e-200))


def test_nonrepresentable_gaussian_score_is_explicitly_refused(m):
    row=case(date(2025,1,2),model=1e-200,rv=.11,realized=.04)
    with pytest.raises(ValueError,match='nonfinite'):
        m.summarize_volatility_scoring([row])
