"""R1: descriptive commodity guidance; numerical policy remains unchanged."""
import math
from pathlib import Path
import pytest
from jinja2 import Environment
from scripts import build_commodities as b
from engine import commodity_mtf as m

NAMES = ['oil','natgas','gasoline','heating_oil','gold','silver','platinum','palladium','copper','corn','wheat','soybeans','live_cattle','coffee','sugar','cocoa','cotton']

def board():
    return {'members': [{'name': n, 'state': 'Neutral'} for n in NAMES]}

def breadth(mom=8):
    return {'n_members':17,'n_up_trend':13,'n_bull_momentum':mom,'n_low_risk':4,'trend_diversity':0.8}

def tape(state='RALLY ON', down=('D','3D')):
    tf={k:{'macd_pos':k not in down,'macd_cross_dn':k in down,'rsi14':40 if k in down else 60} for k in ('D','3D','W','2W','ME')}
    return {'mtf':tf,'ladder':{'regime':'bull','state':state},'cycle':{}}

def test_screenshot_breadth_never_grants_sector_entry():
    v=b.sector_stance(board(),breadth(),in_sync=False)
    assert v['word_en']=='Mixed conditions'
    assert v['tone']!='act'
    assert '8/17' in v['sub_en']

@pytest.mark.parametrize('conf', [{}, {'members':[]}, {'members':[{'name':'gold','state':'Neutral'}]}])
def test_partial_confluence_is_not_clearance(conf):
    assert b.sector_stance(conf,breadth())['word_en']=='Data incomplete'

@pytest.mark.parametrize('value',[None,float('nan'),float('inf'),-1,'bad'])
def test_invalid_dispersion_is_unknown(value):
    assert b._sync_read(value)['in_sync'] is None

@pytest.mark.parametrize('key,value',[('n_members',0),('n_members',True),('n_up_trend',18),('n_bull_momentum',-1),('n_low_risk',None)])
def test_invalid_breadth_is_incomplete(key,value):
    br=breadth(); br[key]=value
    assert b.sector_stance(board(),br)['word_en']=='Data incomplete'

@pytest.mark.parametrize('state',['Neutral','Blowing off — extended','Extended — late cycle','Euphoric top — rolling over','Washout bottom forming'])
def test_sector_labels_are_descriptions_not_instructions(state):
    c=board(); c['members'][0]['state']=state
    v=b.sector_stance(c,breadth(17),in_sync=True)
    assert v['word_en'] not in ('Act','In favour','Protect gains','Get ready','Stand aside')
    assert 'trim' not in v['sub_en'].lower()

@pytest.mark.parametrize('state',['RALLY ON','FRESH BUY','TURN SIGNALED','DECLINE'])
def test_bearish_daily_three_day_never_becomes_aligned_or_buyable(state):
    v=m.confluence_verdict(tape(state),'gold')
    assert v['grade'] not in ('TREND-FOLLOW','BUY-THE-DIP')
    assert 'Aligned uptrend' not in v['headline']
    assert 'Healthy pullback' not in v['headline']
    assert v['per_tf']['D']=='down' and v['per_tf']['3D']=='down'

@pytest.mark.parametrize('missing',['D','3D','W','2W','ME'])
def test_missing_timeframe_cannot_claim_alignment(missing):
    a=tape(down=()); del a['mtf'][missing]
    v=m.confluence_verdict(a,'gold')
    assert v['grade']!='TREND-FOLLOW'
    assert 'Aligned uptrend' not in v['headline']

def test_truly_aligned_control_is_preserved():
    v=m.confluence_verdict(tape(down=()),'gold')
    assert v['grade']=='TREND-FOLLOW'
    assert v['short_sign']==1 and v['long_sign']==1

def test_fx_alias_is_not_changed_by_commodity_repair():
    assert m.confluence_verdict(tape(),'EURUSD')['grade']=='TREND-FOLLOW'

def test_pullback_is_not_automatically_an_entry():
    v=m.confluence_verdict(tape('DECLINE'),'silver')
    assert v['grade']=='WAIT'
    assert 'unconfirmed' in v['headline'].lower()

def _template():
    return (Path(__file__).resolve().parents[1]/'templates/commodities.html.j2').read_text()

@pytest.mark.parametrize('shock',[None,'unexpected','',False])
def test_missing_or_unknown_index_shock_is_not_calm(shock):
    src=_template(); start=src.index('{# 4 — shock state #}'); end=src.index('<!-- ========================= LIVE PRICE STRIP',start)
    html=Environment().from_string(src[start:end]).render(ix={'shock_state':shock,'shock_en':'Unknown','shock_zh':'未知'},t=lambda en,zh:en)
    assert 'Calm' not in html
    assert 'unavailable' in html.lower()

def test_price_proxy_does_not_claim_measured_stagflation():
    src=_template()
    assert 'gold and silver usually hold up' not in src
    assert 'Price-derived context' in src
