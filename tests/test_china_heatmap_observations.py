from __future__ import annotations
from datetime import date, timedelta
import importlib
import json
import math
import numpy as np
import pandas as pd
import pytest

# Tests inject session navigation. Production defaults to the existing lib.cn_calendar.
HOLIDAYS = {date(2026,9,25), *(date(2026,10,d) for d in range(1,8))}
def previous_on_or_before(d):
    while d.weekday() > 4 or d in HOLIDAYS:
        d -= timedelta(days=1)
    return d

def build(df, members=None, asof='2026-09-18'):
    module = importlib.import_module('engine.china_heatmap_observations')
    return module.build_china_observations(df, list(df.columns) if members is None else members,
                                          asof=asof, session_on_or_before=previous_on_or_before)

def panel(values):
    return pd.DataFrame(values,index=pd.to_datetime(['2026-09-16','2026-09-17','2026-09-18']))

def test_missing_current_is_null_not_older_return():
    r=build(panel({'A':[100,110,np.nan]}))
    assert r['returns']['A']['1D'] is None
    assert r['observations']['A']['last_observed_session']=='2026-09-17'
    assert r['observations']['A']['timeframes']['1D']['status']=='CURRENT_MISSING'

def test_missing_previous_is_not_a_two_day_return():
    r=build(panel({'A':[100,np.nan,120]}))
    assert r['returns']['A']['1D'] is None
    assert r['observations']['A']['timeframes']['1D']['status']=='REFERENCE_MISSING'
    assert r['observations']['A']['timeframes']['1D']['reference_session']=='2026-09-17'

def test_explicit_asof_never_uses_future_close_or_future_last_observation():
    r=build(panel({'A':[100,110,220]}),asof='2026-09-17')
    assert r['returns']['A']['1D']==10.
    assert r['observations']['A']['last_observed_session']=='2026-09-17'
    assert r['observations']['A']['last_observed_close']==110.

def test_normal_session_returns_and_denominator():
    r=build(panel({'A':[99,100,101],'B':[99,100,np.nan]}),members=['A','B','MISSING'])
    assert r['returns']['A']['1D']==1.
    assert set(r['returns'])=={'A','B','MISSING'}
    assert r['coverage']['membership_count']==3
    assert r['coverage']['current_observation_count']==1
    assert r['coverage']['timeframes']['1D']=={'valid_count':1,'missing_count':2,'denominator':3,'fraction':1/3}

def test_actual_zero_return_is_distinct_from_missing():
    r=build(panel({'FLAT':[100,100,100],'NONE':[100,100,np.nan]}))
    assert r['returns']['FLAT']['1D']==0.
    assert r['returns']['NONE']['1D'] is None

@pytest.mark.parametrize('invalid',[0,-1,np.inf,-np.inf,'bad',True])
def test_invalid_current_quote_is_not_an_observation(invalid):
    r=build(panel({'A':[100,110,invalid]}))
    assert r['returns']['A']['1D'] is None
    assert r['observations']['A']['timeframes']['1D']['status']=='CURRENT_INVALID'
    assert r['coverage']['current_observation_count']==0

@pytest.mark.parametrize('invalid',[0,-1,np.inf,-np.inf,'bad',False])
def test_invalid_reference_never_falls_back(invalid):
    r=build(panel({'A':[100,invalid,110]}))
    assert r['returns']['A']['1D'] is None
    assert r['observations']['A']['timeframes']['1D']['status']=='REFERENCE_INVALID'

def test_completely_absent_member_stays_explicit():
    r=build(panel({'A':[100,101,102]}),members=['A','NEW'])
    assert r['observations']['NEW']['last_observed_session'] is None
    assert all(x is None for x in r['returns']['NEW'].values())

def test_global_missing_session_does_not_move_anchor_back():
    r=build(pd.DataFrame({'A':[100,101]},index=pd.to_datetime(['2026-09-16','2026-09-17'])))
    assert r['asof']=='2026-09-18'
    assert r['returns']['A']['1D'] is None

def test_weekend_and_holiday_reference_are_calendar_not_stock_specific():
    df=pd.DataFrame({'A':[100,105]},index=pd.to_datetime(['2026-09-24','2026-09-28']))
    r=build(df,asof='2026-09-28')
    assert r['returns']['A']['1D']==5.
    assert r['observations']['A']['timeframes']['1D']['reference_session']=='2026-09-24'

def test_weekly_anchor_missing_is_not_silently_replaced():
    df=pd.DataFrame({'A':[100,110,120]},index=pd.to_datetime(['2026-09-10','2026-09-17','2026-09-18']))
    r=build(df)
    assert r['returns']['A']['1W'] is None
    assert r['observations']['A']['timeframes']['1W']['reference_session']=='2026-09-11'

def test_unsorted_frame_does_not_change_results_or_mutate_input():
    df=panel({'A':[100,110,121]}).iloc[::-1]; old=df.copy(deep=True)
    r=build(df);pd.testing.assert_frame_equal(df,old)
    assert r['returns']['A']['1D']==10.

@pytest.mark.parametrize('member_ids',[['A','A'],['A',' A '],[''],['A',None]])
def test_ambiguous_member_identity_fails_closed(member_ids):
    with pytest.raises(ValueError):build(panel({'A':[100,101,102]}),member_ids)

def test_duplicate_session_rows_fail_closed():
    df=pd.DataFrame({'A':[100,110]},index=pd.to_datetime(['2026-09-18','2026-09-18']))
    with pytest.raises(ValueError):build(df)

def test_duplicate_columns_fail_closed():
    df=pd.DataFrame([[100,100],[110,110]],columns=['A','A'],index=pd.to_datetime(['2026-09-17','2026-09-18']))
    with pytest.raises(ValueError):build(df,members=['A'])

def test_invalid_date_index_fails_closed():
    with pytest.raises(ValueError):build(pd.DataFrame({'A':[100]},index=['garbage']))

def test_anchor_must_be_a_session():
    with pytest.raises(ValueError):build(panel({'A':[100,101,102]}),asof='2026-09-19')

def test_timestamped_intraday_rows_are_not_daily_closes():
    df=pd.DataFrame({'A':[100]},index=pd.to_datetime(['2026-09-18T12:00:00']))
    with pytest.raises(ValueError):build(df)

def test_timezone_aware_session_labels():
    df=panel({'A':[100,110,121]});df.index=df.index.tz_localize('Asia/Shanghai')
    assert build(df)['returns']['A']['1D']==10.

def test_empty_panel_with_explicit_members_and_anchor():
    r=build(pd.DataFrame(),members=['A'])
    assert r['coverage']['membership_count']==1
    assert r['returns']['A']['1D'] is None

def test_json_is_finite_and_deterministic():
    r=build(panel({'A':[100,110,np.inf],'B':[100,100,100]}))
    text=json.dumps(r,allow_nan=False,sort_keys=True)
    assert text==json.dumps(build(panel({'A':[100,110,np.inf],'B':[100,100,100]})),allow_nan=False,sort_keys=True)

def test_overflowing_return_is_unavailable_not_infinity():
    r=build(panel({'A':[1,1e-308,1e308]}))
    assert r['returns']['A']['1D'] is None
    assert r['observations']['A']['timeframes']['1D']['status']=='RETURN_INVALID'

def test_existing_fact_builder_receives_only_valid_cutoff_prices():
    module=importlib.import_module('engine.china_heatmap_observations')
    called=[]
    def facts_builder(df,asof):
        called.append((df.copy(),asof))
        return {'A':{'px':110.}}
    r=module.build_china_observations(panel({'A':[100,110,999.],'B':[100,-1,np.inf]}),['A','B'],
                                      asof='2026-09-17',session_on_or_before=previous_on_or_before,
                                      facts_builder=facts_builder)
    assert r['facts']=={'A':{'px':110.}}
    received,asof=called[0]
    assert received.index.max()==pd.Timestamp('2026-09-17')
    assert math.isnan(received.loc['2026-09-17','B'])

@pytest.mark.parametrize('label',[0,1,False,1.0,np.int64(0)])
def test_numeric_index_values_are_not_implicit_epoch_dates(label):
    df=pd.DataFrame({'A':[100.]},index=[label])
    with pytest.raises(ValueError):build(df,asof='2026-09-18')

def test_current_size_1706_fixture_keeps_six_missing_quotes_out_of_daily_count():
    tickers=[f'FIXTURE{i:04}' for i in range(1706)]
    values=np.tile([100.,100.78,101.],(1706,1)).T
    values[-1,-6:]=np.nan
    df=pd.DataFrame(values,columns=tickers,index=pd.to_datetime(['2026-09-16','2026-09-17','2026-09-18']))
    r=build(df)
    assert len(r['returns'])==1706
    assert r['coverage']['timeframes']['1D']['valid_count']==1700
    assert r['coverage']['timeframes']['1D']['missing_count']==6
    assert all(r['returns'][t]['1D'] is None for t in tickers[-6:])
    assert all(r['observations'][t]['last_observed_session']=='2026-09-17' for t in tickers[-6:])
    json.dumps(r,allow_nan=False)

def test_all_daily_windows_use_their_exact_calendar_endpoints():
    prices={
        '2025-09-18':4., '2025-12-31':5., '2026-03-18':10.,
        '2026-06-18':20., '2026-08-18':30., '2026-08-31':60.,
        '2026-09-11':80., '2026-09-17':100., '2026-09-18':120.}
    df=pd.DataFrame({'A':list(prices.values())},index=pd.to_datetime(list(prices)))
    r=build(df)
    expected={
        '1D':('2026-09-17',20.), '1W':('2026-09-11',50.),
        'MTD':('2026-08-31',100.), '1M':('2026-08-18',300.),
        '3M':('2026-06-18',500.), '6M':('2026-03-18',1100.),
        'YTD':('2025-12-31',2300.), '1Y':('2025-09-18',2900.)}
    for tf,(session,pct) in expected.items():
        assert r['returns']['A'][tf]==pct
        assert r['observations']['A']['timeframes'][tf]['reference_session']==session
        assert r['coverage']['timeframes'][tf]['valid_count']==1
