from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
import pytest
import options_confluence_reference_r6 as r

T = '2024-06-03T15:00:00+00:00'

def activity():
    a=dict(window_minutes=10,gross_premium_usd=2000000,baseline_premium_per_min=100000,
           signed_delta_usd=4000000,absolute_delta_usd=10000000,
           units='usd_delta_notional',population_ref='full-eligible-root',sign_method='owner-v1',
           interval_end='2024-06-03T14:50:00+00:00')
    b={**a,'gross_premium_usd':6000000,'signed_delta_usd':18000000,
       'absolute_delta_usd':24000000,'interval_end':T}
    return a,b

def topology():
    a=dict(top_share='.38',hhi='.22',event_expiry_share='.42',centroid_strike='104',
           forward='100',units='absolute_gamma_usd_per_1pct',scope='all-exact-expiries',
           support_ref='s1',normalization='raw_strike',coverage_state='COMPLETE')
    return a,{**a,'top_share':'.62','hhi':'.44','event_expiry_share':'.68','centroid_strike':'110','forward':'102'}

def skew():
    a=dict(put25_iv='.50',call25_iv='.43',atm_iv='.45',tenor_days='30',
           delta_convention='spot-unadjusted',exercise_model='owner-american-v1',
           tenor_convention='constant_30d',source_method='interpolated-owner-v1',
           asof='2024-06-03T14:50:00+00:00')
    return a,{**a,'put25_iv':'.51','call25_iv':'.50','atm_iv':'.47','asof':T}

def steps():
    return [dict(block='flow',given=[],lr='2',available_at=T),
            dict(block='skew',given=['flow'],lr='1.2',available_at=T),
            dict(block='price',given=['flow','skew'],lr='1.5',available_at=T)]


def test_activity_strengthens_and_accelerates():
    out=r.activity_change(*activity())
    assert out['pace_before']==D(2) and out['pace_after']==D(6)
    assert out['delta_balance_before']==D('.4') and out['delta_balance_after']==D('.75')
    assert out['one_sided_change']==D('.35')
    assert out['signed_rate_acceleration']==D(140000)
    assert out['direction']=='positive_delta_demand_estimate'


def test_activity_not_cumulative_acceleration():
    a,b=activity(); b.update(window_minutes=20,gross_premium_usd=4000000,signed_delta_usd=8000000,absolute_delta_usd=20000000)
    a['interval_end']='2024-06-03T14:40:00+00:00'
    out=r.activity_change(a,b)
    assert out['pace_after']==D(2) and out['signed_rate_acceleration']==D(0)


def test_missing_direction_does_not_delete_unusual_activity():
    a,b=activity(); b['signed_delta_usd']=None
    out=r.activity_change(a,b)
    assert out['pace_after']==D(6) and out['delta_balance_after'] is None
    assert out['direction']=='unavailable' and out['signed_rate_acceleration'] is None


def test_zero_activity_is_distinct_from_missing():
    a,b=activity(); b.update(gross_premium_usd=0,absolute_delta_usd=0,signed_delta_usd=0)
    out=r.activity_change(a,b)
    assert out['pace_after']==D(0) and out['delta_balance_after'] is None
    assert out['direction']=='no_directional_mass'


def test_activity_less_bearish_does_not_become_bullish():
    a,b=activity();a['signed_delta_usd']=-8000000;b['signed_delta_usd']=-1000000
    out=r.activity_change(a,b)
    assert out['signed_rate_acceleration']>0
    assert out['direction']=='negative_delta_demand_estimate'

@pytest.mark.parametrize('key,val', [('window_minutes',0),('gross_premium_usd',-1),
    ('baseline_premium_per_min',0),('gross_premium_usd',True),('signed_delta_usd','NaN'),
    ('absolute_delta_usd',1),('interval_end','nonsense')])
def test_invalid_activity_refuses(key,val):
    a,b=activity();b[key]=val
    with pytest.raises(ValueError):r.activity_change(a,b)

@pytest.mark.parametrize('key', ['population_ref','sign_method','units'])
def test_incompatible_activity_refuses(key):
    a,b=activity();b[key]='different'
    with pytest.raises(ValueError):r.activity_change(a,b)


def test_overlapping_activity_windows_refuse_acceleration():
    a,b=activity();b['interval_end']='2024-06-03T14:55:00+00:00'
    with pytest.raises(ValueError):r.activity_change(a,b)


def test_concentration_increase_and_migration():
    out=r.concentration_change(*topology())
    assert out['top_share_change']==D('.24') and out['event_expiry_share_change']==D('.26')
    assert out['hhi_change']==D('.22') and out['raw_centroid_change']==D(6)
    assert out['log_relative_change']==pytest.approx(.03628683935486385,abs=1e-12)
    assert out['position_growth_proven'] is False


def test_spot_only_move_is_not_new_upper_strike_demand():
    a,b=topology();b.update(centroid_strike='104')
    out=r.concentration_change(a,b)
    assert out['raw_centroid_change']==0 and out['log_relative_change']<0

@pytest.mark.parametrize('key', ['scope','support_ref','units','normalization'])
def test_topology_scope_change_not_silent(key):
    a,b=topology();b[key]='new'
    out=r.concentration_change(a,b)
    assert out['state']=='NOT_COMPARABLE' and out['top_share_change'] is None


def test_incomplete_topology_not_total_mass():
    a,b=topology();b['coverage_state']='PARTIAL'
    assert r.concentration_change(a,b)['state']=='NOT_COMPARABLE'

@pytest.mark.parametrize('key,val', [('top_share','1.1'),('hhi',0),('event_expiry_share',-1),('forward',0),('centroid_strike','Infinity')])
def test_invalid_topology_refuses(key,val):
    a,b=topology();b[key]=val
    with pytest.raises(ValueError):r.concentration_change(a,b)


def test_upside_skew_bid_strengthens_even_with_put_iv_rise():
    out=r.skew_change(*skew())
    assert out['risk_reversal_before']==D('-.07') and out['risk_reversal_after']==D('-.01')
    assert out['risk_reversal_change']==D('.06')
    assert out['put_wing_change']==D('-.01')
    assert out['call_wing_change']==D('.05')

@pytest.mark.parametrize('key', ['tenor_convention','source_method','delta_convention','exercise_model'])
def test_skew_definition_change_not_averaged(key):
    a,b=skew();b[key]='other'
    assert r.skew_change(a,b)['state']=='NOT_COMPARABLE'


def test_skew_time_reversal_refuses():
    a,b=skew(); b['asof']='2024-06-02T00:00:00+00:00'
    with pytest.raises(ValueError):r.skew_change(a,b)


def test_skew_magnitude_not_direction_probability():
    out=r.skew_change(*skew())
    assert out['probability'] is None


def test_conditional_confluence_updates_probability():
    out=r.conditional_update('.55',steps(),cutoff=T,target='positive_net_5session_return',synthetic=True)
    assert abs(out['probability']-D(22)/D(27))<D('1e-25')
    assert len(out['trace'])==3 and out['empirically_qualified'] is False
    assert out['recommendation_authority'] is False


def test_contradiction_reduces_probability():
    s=steps();s[-1]['lr']='.5'
    assert r.conditional_update('.55',s,cutoff=T,target='x',synthetic=True)['probability']<D('.75')


def test_redundant_feature_conditional_lr_one_adds_no_confirmation():
    s=steps()[:1];s.append(dict(block='same-flow-summary',given=['flow'],lr=1,available_at=T))
    o=r.conditional_update('.55',s,cutoff=T,target='x',synthetic=True)
    assert o['trace'][0]['probability']==o['probability']


def test_unavailable_factor_preserves_base_forecast_and_marks_partial():
    s=[dict(block='dealer',given=[],lr=None,available_at=None)]
    out=r.conditional_update('.55',s,cutoff=T,target='x',synthetic=True)
    assert out['probability']==D('.55') and out['unavailable_blocks']==['dealer']


def test_future_factor_cannot_backfill():
    s=steps();s[1]['available_at']='2024-06-04T00:00:00+00:00'
    with pytest.raises(ValueError):r.conditional_update('.55',s,cutoff=T,target='x',synthetic=True)

@pytest.mark.parametrize('mutation', ['duplicate','wrong_conditioning','target','non_synthetic','negative_lr','invalid_base','null_target'])
def test_bad_conditional_chain_refuses(mutation):
    s=steps();p='.55';target='x';synthetic=True
    if mutation=='duplicate':s[1]['block']='flow'
    elif mutation=='wrong_conditioning':s[1]['given']=[]
    elif mutation=='target':s[0]['target']='y'
    elif mutation=='non_synthetic':synthetic=False
    elif mutation=='negative_lr':s[0]['lr']=-1
    elif mutation=='invalid_base':p=1
    elif mutation=='null_target':target=''
    with pytest.raises(ValueError):r.conditional_update(p,s,cutoff=T,target=target,synthetic=synthetic)


def bars():
    return [dict(start='2024-06-03T15:01:00+00:00',end='2024-06-03T15:06:00+00:00',low=99,high=104,open=100,close=103),
            dict(start='2024-06-03T15:06:00+00:00',end='2024-06-03T15:11:00+00:00',low=102,high=106,open=103,close=105)]


def test_frozen_node_target_first():
    out=r.first_passage(bars(),cutoff=T,upper=105,lower=95)
    assert out['outcome']=='UPPER_FIRST' and out['bar_end']=='2024-06-03T15:11:00+00:00'
    assert out['fill_price'] is None


def test_same_bar_two_barriers_is_ambiguous():
    b=bars();b[0].update(low=94,high=106)
    assert r.first_passage(b,cutoff=T,upper=105,lower=95)['outcome']=='INTRABAR_ORDER_UNKNOWN'


def test_lower_first():
    b=bars();b[0]['low']=94
    assert r.first_passage(b,cutoff=T,upper=105,lower=95)['outcome']=='LOWER_FIRST'


def test_no_touch_is_unresolved_not_loss():
    assert r.first_passage(bars(),cutoff=T,upper=110,lower=90)['outcome']=='NO_TOUCH_IN_OBSERVED_WINDOW'


def test_no_observations_is_missing():
    assert r.first_passage([],cutoff=T,upper=110,lower=90)['outcome']=='NO_OBSERVATIONS'

@pytest.mark.parametrize('kind',['pre_cutoff','overlap','invalid_ohlc','reversed_barrier'])
def test_bad_event_path_refuses(kind):
    b=bars();u=105;l=95
    if kind=='pre_cutoff':b[0]['start']='2024-06-03T14:59:00+00:00'
    elif kind=='overlap':b[1]['start']='2024-06-03T15:05:00+00:00'
    elif kind=='invalid_ohlc':b[0]['close']=200
    else:u=90
    with pytest.raises(ValueError):r.first_passage(b,cutoff=T,upper=u,lower=l)


def test_inputs_never_mutated():
    a,b=activity();orig=deepcopy((a,b));r.activity_change(a,b);assert (a,b)==orig
    a,b=topology();orig=deepcopy((a,b));r.concentration_change(a,b);assert (a,b)==orig
    a,b=skew();orig=deepcopy((a,b));r.skew_change(a,b);assert (a,b)==orig
    s=steps();orig=deepcopy(s);r.conditional_update('.55',s,cutoff=T,target='x',synthetic=True);assert s==orig

# R6 self-review regressions: impossible concentration and incomplete path.
@pytest.mark.parametrize('top,hhi', [('.62','.34'),('.38','.50'),('0','.01')])
def test_internally_impossible_topology_refuses(top,hhi):
    a,b=topology();b.update(top_share=top,hhi=hhi)
    with pytest.raises(ValueError):r.concentration_change(a,b)


def test_gap_before_barrier_touch_withholds_first_passage():
    b=bars();b[1]['start']='2024-06-03T15:07:00+00:00'
    out=r.first_passage(b,cutoff=T,upper=105,lower=95)
    assert out['outcome']=='PATH_COVERAGE_GAP' and out['fill_price'] is None


def test_gap_after_known_first_touch_does_not_erase_it():
    b=bars();b[0]['high']=106;b[1]['start']='2024-06-03T15:07:00+00:00'
    assert r.first_passage(b,cutoff=T,upper=105,lower=95)['outcome']=='UPPER_FIRST'


def test_path_reports_actual_start_not_earlier_decision_time():
    out=r.first_passage(bars(),cutoff=T,upper=105,lower=95)
    assert out['evaluated_from']=='2024-06-03T15:01:00+00:00'
