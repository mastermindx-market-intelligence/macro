"""Synthetic support-contract regressions over the actual compute_gex function."""
import math
import numpy as np
import pandas as pd
import pytest
from engine.options_hub import compute_gex
ASOF='2026-09-25'; FIRST='2026-10-02'; SECOND='2026-10-23'
def row(exp=FIRST,right='C',vanna=.2,charm=-.365,oi=1000,strike=500.):
    return dict(root='SPY',date=ASOF,expiration=exp,right=right,strike=strike,underlying_price=500.,implied_vol=.2,delta=.5 if right=='C' else -.5,gamma=.01,vanna=vanna,charm=charm,oi=oi)
def project(rows):
    g=pd.DataFrame([{k:v for k,v in r.items() if k!='oi'} for r in rows]);oi=pd.DataFrame([dict(expiration=r['expiration'],right=r['right'],strike=r['strike'],open_interest=r['oi'],date=ASOF) for r in rows]);return compute_gex(g,oi,ASOF,'SPY')
@pytest.mark.parametrize('lens',['vanna','charm'])
@pytest.mark.parametrize('missing',[float('nan'),float('inf'),float('-inf')])
def test_nonfinite_lens_is_unavailable(lens,missing):
    r=row();r[lens]=missing;p=project([r])['by_expiry'][0]
    assert p[lens+'_net'] is None
    assert p['exposure_support']['basis']=='admitted_input_contracts'
    assert p['exposure_support'][lens]==dict(known_contracts=0,admitted_contracts=1,known_net=None)
@pytest.mark.parametrize('lens',['vanna','charm'])
def test_absent_lens_column_is_not_measured_zero(lens):
    r=row();del r[lens];p=project([r])['by_expiry'][0]
    assert p[lens+'_net'] is None
    assert p['exposure_support'][lens]['known_net'] is None
@pytest.mark.parametrize('lens',['vanna','charm'])
def test_true_zero_and_cancellation_stay_zero(lens):
    r=row();r[lens]=0.;p=project([r])['by_expiry'][0]
    assert p[lens+'_net']==0.;assert p['exposure_support'][lens]['known_contracts']==1
    a=row(vanna=.2,charm=.365);b=row(right='P',vanna=.2,charm=.365)
    q=project([a,b])['by_expiry'][0]
    assert q[lens+'_net']==0.;assert q['exposure_support'][lens]['known_contracts']==2
@pytest.mark.parametrize('lens,known',[('vanna',.1),('charm',-.05)])
def test_partial_keeps_known_subtotal_not_complete_net(lens,known):
    a=row();b=row(right='P');b[lens]=float('nan');p=project([a,b])['by_expiry'][0]
    assert p[lens+'_net'] is None
    assert p['exposure_support'][lens]==dict(known_contracts=1,admitted_contracts=2,known_net=known)
def test_completeness_is_lens_and_expiry_local():
    a=row();b=row(right='P',vanna=float('nan'),charm=.365);c=row(exp=SECOND,vanna=.4,charm=.365,oi=2000)
    p=project([a,b,c])['by_expiry']
    assert p[0]['vanna_net'] is None and p[0]['charm_net']==-.1
    assert p[1]['vanna_net']==.4 and p[1]['charm_net']==.1
def test_input_count_excludes_rows_not_admitted_by_existing_owner():
    a=row();b=row(right='P',oi=0,vanna=float('nan'));p=project([a,b])['by_expiry'][0]
    assert p['vanna_net']==.1;assert p['exposure_support']['vanna']['admitted_contracts']==1
def test_expiry_book_not_forced_to_windowed_strike_sum():
    p=project([row(),row(exp=SECOND,strike=750)])
    assert len(p['by_expiry'])==2 and len(p['by_strike'])==1
    assert sum(e['vanna_net'] for e in p['by_expiry'])==.2
    assert sum(e['vanna_net'] for e in p['by_strike'])==.1
def test_complete_greeks_keep_existing_units_and_assumed_sign():
    p=project([row(),row(exp=SECOND,right='P',vanna=.4,charm=.365,oi=2000)])['by_expiry']
    assert p[0]['vanna_net']==.1 and p[0]['charm_net']==-.05
    assert p[1]['vanna_net']==-.4 and p[1]['charm_net']==-.1
@pytest.mark.parametrize('seed',list(range(20)))
def test_sparse_input_known_subtotal_matches_same_existing_exposure_math(seed):
    from engine.exposure_math import dealer_exposures
    rows=[]
    for i in range(6):
        rows.append(row(exp=FIRST if i<3 else SECOND,right='C' if i%2==0 else 'P',strike=498+i,oi=100+i*10,vanna=float('nan') if (i+seed)%4==0 else .01*(i-seed),charm=float('nan') if (i+seed)%5==0 else .02*(seed-i)))
    payload=project(rows)
    for entry in payload['by_expiry']:
        group=[r for r in rows if r['expiration']==entry['exp']]
        expected=dealer_exposures(is_call=[r['right']=='C' for r in group],oi=[r['oi'] for r in group],spot=500.,vanna=[r['vanna'] for r in group],charm=[r['charm'] for r in group])
        for lens in ['vanna','charm']:
            values=expected[lens];valid=np.isfinite(values);n=int(valid.sum());known=round(float(values[valid].sum())/1e6,4) if n else None
            assert entry['exposure_support'][lens]==dict(known_contracts=n,admitted_contracts=len(group),known_net=known)
            assert entry[lens+'_net']==(known if n==len(group) else None)
