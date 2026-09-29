"""Original Connect renderer regressions, migrated to actual archived-source wiring.

The builder must produce the keys/rows consumed by the REAL page+partial. Source
failures are explicit empty states, not network requests during render. Preserve
northbound turnover and both southbound signs; no cross-venue flow fabrication.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import pandas as pd
import pytest
from jinja2 import ChoiceLoader, DictLoader, Environment, FileSystemLoader
from scripts.build_china import _leaderboard
from engine.china_macro_evidence import build_snapshot
from engine.china_macro_evidence_view import prepare_view

ROOT = Path(__file__).resolve().parents[1]
DAY = (datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
def row(mt, code, name, chg, turnover, net, day=DAY):
    return dict(TRADE_DATE=day,MUTUAL_TYPE=mt,SECURITY_CODE=code,
                SECURITY_NAME=name,CHANGE_RATE=chg,DEAL_AMT=turnover,NET_BUY_AMT=net)
BY_LEG = {
    '001':[row('001','600519','贵州茅台',1.2,50e8,None)],
    '003':[row('003','300750','宁德时代',-.5,30e8,None)],
    '002':[row('002','00700','腾讯控股',-2.2,9e8,5.5e8)],
    '004':[row('004','09988','阿里巴巴-W',.3,8e8,-3.1e8)],
}
@pytest.fixture
def archived(monkeypatch):
    import requests
    from lib import store
    def deny(*args,**kwargs):raise AssertionError('render issued a network request')
    monkeypatch.setattr(requests,'get',deny)
    def read(group,name):
        assert group=='china_connect'
        rows=BY_LEG.get(name.removeprefix('top_active_'),[])
        return pd.DataFrame({'rows_json':[json.dumps(rows)]},index=pd.to_datetime([DAY]))
    monkeypatch.setattr(store,'read',read)
    return _leaderboard()

def render_snippet(start,end,lb):
    src=(ROOT/'templates/china.html.j2').read_text()
    piece=src[src.index(start):src.index(end,src.index(start))]
    pre='{% macro t(en,zh="") %}{{ en }}{% endmacro %}{% import "_china_macro_evidence.html.j2" as cnm with context %}'
    env=Environment(loader=ChoiceLoader([DictLoader({'test':pre+piece}),FileSystemLoader(ROOT/'templates')]))
    return env.get_template('test').render(leaderboard=lb,
        macro_evidence=prepare_view(build_snapshot(lambda g,n:None)),latest={'date':DAY},I={})

def test_leaderboard_shape_matches_template_contract(archived):
    lb=archived
    assert lb.keys()>={'date','northbound_turnover','southbound_buy','southbound_sell'}
    n=lb['northbound_turnover'][0]
    assert {'name_zh','name','ticker','turnover','chg'}<=n.keys()
    assert n['ticker']=='600519' and n['turnover']==50
    assert lb['southbound_buy'][0]['net']==5.5
    assert lb['southbound_sell'][0]['net']==-3.1
    assert lb['transport']=='canonical_store_no_render_network'

def test_popup_dialog_renders_real_rows_from_the_real_leaderboard_output(archived):
    html=render_snippet('<!-- Connect Flows dialog -->','<!-- Property dialog -->',archived)
    assert '<table' in html
    for token in ['贵州茅台','600519','腾讯控股','阿里巴巴-W','HKD','CNY',DAY]:assert token in html
    assert 'Northbound turnover only' in html

def test_summary_card_top_buys_line_renders_from_the_real_leaderboard_output(archived):
    html=render_snippet('{# Connect Flows card #}','{# What Changed:',archived)
    assert '腾讯控股' in html and 'Disclosed buys' in html

def test_popup_dialog_is_explicit_and_error_free_when_leaderboard_is_none():
    html=render_snippet('<!-- Connect Flows dialog -->','<!-- Property dialog -->',None)
    assert 'unavailable' in html.lower() and '腾讯控股' not in html

@pytest.mark.parametrize('age',[8,365])
def test_summary_never_projects_aged_buyers_as_current(archived,age):
    archived['southbound_buy'][0]['age_days']=age
    assert '腾讯控股' not in render_snippet('{# Connect Flows card #}','{# What Changed:',archived)

def test_builder_preserves_independent_venue_on_cache_failure(monkeypatch):
    from lib import store
    def read(group,name):
        if name!='top_active_002':raise OSError('unreadable cache')
        return pd.DataFrame({'rows_json':[json.dumps(BY_LEG['002'])]},index=pd.to_datetime([DAY]))
    monkeypatch.setattr(store,'read',read)
    lb=_leaderboard()
    assert len(lb['cache_errors'])==3 and lb['southbound_buy'][0]['ticker']=='00700'
    assert lb['northbound_turnover']==[] and lb['status']=='partial'
