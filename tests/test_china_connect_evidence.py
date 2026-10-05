from datetime import date
import json

import pandas as pd

from engine.china_connect_leaderboard import build_leaderboard, normalize

ASOF = date(2026,9,29)

def row(code="00700", net=1e9, d="2026-09-28", amount=2e9):
    return {"SECURITY_CODE":code,"SECURITY_NAME":"腾讯控股","NET_BUY_AMT":net,"DEAL_AMT":amount,"TRADE_DATE":d}

def test_venue_specific_duplicate_stock_is_not_combined_or_zero_filled():
    x=normalize({"002":[row()],"004":[row(net=2e9)]},ASOF)
    assert len(x['southbound_buy'])==2
    assert {r['net'] for r in x['southbound_buy']}=={10,20}
    assert {r['currency'] for r in x['southbound_buy']}=={'HKD'}

def test_buy_and_sell_sets_are_sign_filtered_not_top_n_of_same_sorted_array():
    x=normalize({'002':[row('00700',1),row('02800',-1),row('00941',0)]},ASOF)
    assert [r['ticker'] for r in x['southbound_buy']]==['00700']
    assert [r['ticker'] for r in x['southbound_sell']]==['02800']

def test_northbound_missing_net_is_not_synthesized_from_turnover():
    x=normalize({'001':[row('600519',None)]},ASOF)
    assert x['northbound_turnover'][0]['turnover']==20
    assert 'net' not in x['northbound_turnover'][0]
    assert x['northbound_turnover'][0]['chg'] is None

def test_missing_southbound_net_does_not_become_zero_or_a_buyer():
    x=normalize({'002':[row(net=None)]},ASOF)
    assert not x['southbound_buy'] and not x['southbound_sell']

def test_duplicate_in_one_venue_withholds_that_venue():
    x=normalize({'002':[row(),row()]},ASOF)
    assert not x['southbound_buy']
    assert any('duplicate' in w for w in x['warnings'])

def test_future_and_invalid_dates_and_route_mismatch_excluded():
    bad=row();bad['MUTUAL_TYPE']='001'
    x=normalize({'002':[row(d='2026-09-30'),row(d='bad'),bad]},ASOF)
    assert not x['southbound_buy']

def test_different_venue_dates_not_ranked_together():
    x=normalize({'002':[row(net=1e9)],'004':[row('02800',2e9,d='2026-09-25')]},ASOF)
    assert len(x['southbound_buy'])==1
    assert x['southbound_date']=='2026-09-28'
    assert any('mixed venue dates' in w for w in x['warnings'])

def test_opposite_directions_keep_own_dates_not_dashboard_date():
    x=normalize({'001':[row('600519',d='2026-09-25')],'002':[row()]},ASOF)
    assert x['date'] is None
    assert x['northbound_date']=='2026-09-25' and x['southbound_date']=='2026-09-28'

def test_cache_no_network_and_bad_index_is_not_laundered():
    x=pd.DataFrame({'rows_json':[json.dumps([row()])]},index=pd.to_datetime(['2026-09-28']))
    result=build_leaderboard(lambda g,n:x if n=='top_active_002' else None,ASOF)
    assert result['southbound_buy'][0]['net']==10
    assert result['transport']=='canonical_store_no_render_network'
    x.index=pd.to_datetime(['2026-09-25'])
    result=build_leaderboard(lambda g,n:x if n=='top_active_002' else None,ASOF)
    assert result['cache_errors'] and not result['southbound_buy']

def test_age_and_empty_state_are_explicit():
    x=normalize({},ASOF)
    assert x['status']=='unavailable' and len(x['warnings'])==4
    x=normalize({'002':[row(d='2025-01-01')]},ASOF)
    assert x['venues']['002']['status']=='aged_or_unavailable'

def test_invalid_amounts_are_not_zero():
    x=normalize({'002':[row(net='NaN')],'001':[row('600519',amount=-1)]},ASOF)
    assert not x['southbound_buy'] and not x['northbound_turnover']
