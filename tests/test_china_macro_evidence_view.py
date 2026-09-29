"""Static rendering/contract tests, not a claim of browser visual verification."""
from copy import deepcopy
from datetime import date
import importlib.util
import json
from pathlib import Path
import re
import subprocess

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader, StrictUndefined
import pandas as pd
import pytest

from engine.china_macro_evidence import build_snapshot
from engine.china_macro_evidence_view import chart_svg, prepare_view
from engine.china_connect_leaderboard import build_leaderboard
from scripts.preview_china_macro_evidence import real_snapshot

ROOT=Path(__file__).resolve().parents[1]


def m(vals,dates=None,kind='line',ref=None,label='Safe <label>'):
    return {'id':'test','label_en':label,'label_zh':'测试','unit':'%','reference':ref,
            'chart_kind':kind,'chart':{'vals':vals,'dates':dates or [f'2026-09-{i+1:02d}' for i in range(len(vals))]}}


def render(snapshot,legacy=None):
    env=Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=True,undefined=StrictUndefined)
    t=env.from_string('''{% macro t(en,zh) %}<span class="l-en">{{ en }}</span><span class="l-zh">{{ zh }}</span>{% endmacro %}
    {% import '_china_macro_evidence.html.j2' as cnm with context %}
    {% for key in ['policy','property','flows','sentiment'] %}{{ cnm.panel(snapshot,key,legacy=legacy) }}{% endfor %}''')
    return t.render(snapshot=prepare_view(snapshot),legacy=legacy)


@pytest.mark.parametrize('vals', [[],[1],[None],[None,1],[1,None],[True,False]])
def test_less_than_two_finite_points_never_invents_a_trend(vals):
    assert chart_svg(m(vals))==''


def test_missing_chart_value_breaks_line_not_interpolated():
    soup=BeautifulSoup(chart_svg(m([1,2,None,3,4])),'html.parser')
    assert len(soup.select('path.cnm-line'))==2
    assert all(p['d'].startswith('M') for p in soup.select('path.cnm-line'))


def test_x_positions_use_elapsed_time_not_row_spacing():
    soup=BeautifulSoup(chart_svg(m([1,2,3],['2026-09-01','2026-09-02','2026-09-11'])),'html.parser')
    pts=[float(x) for x in re.findall(r'[ML]([0-9.]+),',soup.select_one('path')['d'])]
    assert (pts[1]-pts[0])/(pts[2]-pts[0])==pytest.approx(.1,abs=1e-4)


@pytest.mark.parametrize('dates',[['2026-09-01','2026-09-01'],['2026-09-03','2026-09-01'],['bad','2026-09-01'],['2026-09-01']])
def test_invalid_or_mismatched_timelines_are_withheld(dates):
    assert chart_svg(m([1,2],dates))==''


def test_bars_use_an_in_range_zero_baseline_when_reference_is_missing():
    soup=BeautifulSoup(chart_svg(m([80,90],kind='bars')),'html.parser')
    for bar in soup.select('.cnm-bar'):
        assert 20<=float(bar['y1'])<=174
        assert 20<=float(bar['y2'])<=174


def test_svg_user_labels_are_escaped_not_dom_injected():
    text=chart_svg(m([1,2],label='"><script>alert(1)</script>'))
    assert '<script>' not in text and '&lt;script&gt;' in text


def test_presentation_never_mutates_shared_machine_contract():
    x=real_snapshot();before=deepcopy(x);v=prepare_view(x)
    assert x==before and 'chart_svg' not in json.dumps(x)
    assert any(p['chart_svg'] for p in v['panels'].values())
    json.dumps(x,allow_nan=False)


@pytest.mark.parametrize('snapshot_factory',[real_snapshot,lambda:build_snapshot(lambda g,n:None,date(2026,9,29))])
def test_all_four_dialogs_render_with_unique_ids_and_resolved_accessible_labels(snapshot_factory):
    x=snapshot_factory();soup=BeautifulSoup(render(x),'html.parser')
    ids=[n['id'] for n in soup.select('[id]')]
    assert len(ids)==len(set(ids))
    assert len(soup.select('[role="dialog"]'))==4
    for d in soup.select('[role="dialog"]'):
        assert d['aria-modal']=='true'
        assert soup.find(id=d['aria-labelledby']) is not None
        assert d.select_one('button[type="button"]')
    for link in soup.select('[data-cnm-method-link]'):
        assert soup.find(id=link['href'][1:])
    for payload in soup.select('[data-cnm-series]'):
        assert isinstance(json.loads(payload.string),list)
    assert 'No ranking, sizing, entry permission' in soup.get_text()


def test_empty_snapshot_has_explicit_stock_disclosure_state_not_blank_or_zero():
    html=render(build_snapshot(lambda g,n:None,date(2026,9,29)))
    assert 'stock-level snapshot is unavailable' in html
    assert 'No 70-city distribution is asserted' in html
    assert 'NaN' not in html and 'nan%' not in html


def test_legacy_components_and_accepted_history_are_preserved():
    legacy={'components':[{'label':'Legacy','label_en':'Legacy','label_zh':'原有','score':57}],
            'chart_html':'<div data-original-chart="preserved">Accepted chart</div>'}
    html=render(real_snapshot(),legacy)
    assert 'data-original-chart="preserved"' in html
    assert 'Legacy' in html and '57' in html


def test_fractional_city_counts_do_not_render_as_whole_cities():
    df=pd.DataFrame({'new_rising':[15.5],'new_falling':[49.5],'new_flat':[5],'cities':[70]},index=pd.to_datetime(['2026-08-01']))
    x=build_snapshot(lambda g,n:df if n=='home_price' else None,date(2026,9,29))
    soup=BeautifulSoup(render(x),'html.parser')
    assert soup.select_one('.cnm-city-grid') is None


def test_no_daily_change_is_mislabeled_as_percent_growth():
    x=build_snapshot(lambda g,n:pd.DataFrame({'m1_yoy':[4,5],'m2_yoy':[7,7]},index=pd.to_datetime(['2026-07-01','2026-08-01'])) if n=='money_supply' else None,date(2026,9,29))
    mm={m['id']:m for p in x['panels'].values() for m in p['metrics']}
    assert mm['money_spread']['delta_unit']=='pp'
    assert mm['margin_ratio']['delta_unit']=='pp'
    assert mm['money_spread']['reference_label']=='2026-08'


def test_incomplete_reference_month_and_quarter_are_not_current_observations():
    data={
        'money_supply':pd.DataFrame({'m1_yoy':[4,9],'m2_yoy':[7,7]},index=pd.to_datetime(['2026-08-01','2026-09-01'])),
        'gdp':pd.DataFrame({'nominal_gdp_ytd_cny100m':[695704,1050000]},index=pd.to_datetime(['2026-06-01','2026-09-01'])),
    }
    x=build_snapshot(lambda g,n:data.get(n),date(2026,9,29))
    mm={m['id']:m for p in x['panels'].values() for m in p['metrics']}
    assert mm['money_spread']['reference_date']=='2026-08-01'
    assert mm['financing_gdp_change']['reference_date'] in {None,'2026-06-30'}


def test_one_store_reader_failure_does_not_crash_the_leaderboard():
    def read(g,n):raise RuntimeError('unavailable')
    x=build_leaderboard(read,date(2026,9,29))
    assert x['status']=='unavailable' and len(x['cache_errors'])==4


def test_latest_missing_value_does_not_erase_usable_historical_research():
    x=real_snapshot()
    metric=x['panels']['policy']['metrics'][0]
    metric['status']='unavailable';metric['value']=None
    metric['chart']={'dates':['2026-06-01','2026-07-01','2026-08-01'],'vals':[1,2,None]}
    view=prepare_view(x)
    assert view['panels']['policy']['selected_chart']['id']==metric['id']
    assert 'cnm-bar' in view['panels']['policy']['chart_svg']
    assert x['panels']['policy']['metrics'][0]['value'] is None
