from datetime import date,timedelta
from copy import deepcopy
import pytest
from engine.leader_recovery_policy_research import compare_at_landmark,POLICIES


def fixture(n=15):
    days=[date(2026,1,1)+timedelta(days=i) for i in range(n)]
    p={d:100.+i for i,d in enumerate(days)};b={d:100. for d in days}
    o={d:{'state':'DAMAGED','episode':{'opened_on':'2026-01-01','rebound_from_low':0.},'ma_fast':120.,'fast_confirmation_sessions':0,'slow_confirmation_sessions':0} for d in days}
    return days,p,b,o


def run(days,p,b,o,**kw):
    return {x['policy']:x for x in compare_at_landmark(p,b,o,sessions=days,landmark=days[0],horizon=kw.get('horizon',12),available_through=kw.get('through',days[-1]),round_trip_cost_bps=kw.get('cost',20))}


def test_every_policy_uses_same_endpoint_and_no_entry_is_retained():
    days,p,b,o=fixture();r=run(days,p,b,o)
    assert set(r)==set(POLICIES)
    assert len({v['endpoint'] for v in r.values()})==1
    assert r['reignition']['entry_status']=='NO_ENTRY'
    assert r['reignition']['net_return']==0
    assert r['immediate']['entry_on']==days[1].isoformat()
    assert r['immediate']['net_return']==pytest.approx(112/101-1-.002)


def test_signal_is_never_filled_on_its_own_close():
    days,p,b,o=fixture()
    o[days[3]].update(state='REIGNITING',ma_fast=90.,fast_confirmation_sessions=3,slow_confirmation_sessions=3)
    o[days[3]]['episode']['rebound_from_low']=.2
    p[days[3]]=80.;p[days[4]]=100.
    r=run(days,p,b,o)
    assert r['reignition']['signal_on']==days[3].isoformat()
    assert r['reignition']['entry_on']==days[4].isoformat()
    assert r['reignition']['net_return']==pytest.approx(112/100-1-.002)


def test_future_beyond_common_endpoint_cannot_change_outcomes():
    days,p,b,o=fixture();first=run(days,p,b,o)
    p[days[-1]]=99999;o[days[-1]]['state']='REIGNITING'
    assert run(days,p,b,o)==first


def test_all_policies_share_censoring_and_data_gaps():
    days,p,b,o=fixture()
    assert all(x['status']=='RIGHT_CENSORED' for x in run(days,p,b,o,through=days[5]).values())
    p[days[7]]=float('nan')
    assert all(x['status']=='DATA_GAP' for x in run(days,p,b,o).values())


def test_silent_observation_gap_is_not_a_no_entry():
    days,p,b,o=fixture();o.pop(days[4])
    assert all(x['status']=='OBSERVATION_GAP' for x in run(days,p,b,o).values())


def test_signal_from_a_different_episode_is_not_used():
    days,p,b,o=fixture();o[days[3]].update(ma_fast=90.,fast_confirmation_sessions=9,slow_confirmation_sessions=9)
    o[days[3]]['episode'].update(opened_on='2026-01-04',rebound_from_low=.2)
    assert run(days,p,b,o)['reignition']['entry_status']=='NO_ENTRY'


def test_increasing_cost_changes_only_entered_returns():
    days,p,b,o=fixture();a=run(days,p,b,o,cost=20);c=run(days,p,b,o,cost=50)
    assert a['immediate']['net_return']-c['immediate']['net_return']==pytest.approx(.003)
    assert a['repair']['net_return']==c['repair']['net_return']==0


def test_input_not_mutated():
    days,p,b,o=fixture();old=deepcopy(o);run(days,p,b,o);assert o==old


def test_missing_initial_evidence_is_not_accepted():
    days,p,b,o=fixture();o[days[0]]['state']='UNAVAILABLE'
    with pytest.raises(ValueError):run(days,p,b,o)


def test_short_deadline_retains_fixed_waits_as_no_entry():
    days,p,b,o=fixture();r=run(days,p,b,o,horizon=5)
    assert r['wait_5']['entry_status']=='NO_ENTRY'
    assert r['wait_10']['entry_status']=='NO_ENTRY'


@pytest.mark.parametrize('cost',[True,-1,float('nan')])
def test_invalid_cost_refused(cost):
    days,p,b,o=fixture()
    with pytest.raises(ValueError):run(days,p,b,o,cost=cost)
