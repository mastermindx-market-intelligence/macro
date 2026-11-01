from copy import deepcopy
from pathlib import Path
from html.parser import HTMLParser
import pytest
from jinja2 import Environment,FileSystemLoader
from lib.intl_history_mount import attach_history
from tests.test_intl_history_mount import fixture

ROOT=Path(__file__).resolve().parents[1]
def render(change=None):
    w,args=fixture()
    if change:change(w,args)
    data=attach_history(w,**args)
    return Environment(loader=FileSystemLoader(ROOT/'templates'),autoescape=False).get_template('intl_workspace/history.html.j2').render(history_panel=data['histories'][0],history_registry=data['history_registry'])

class Nodes(HTMLParser):
    def __init__(self,text):
        super().__init__();self.nodes=[];self.feed(text)
    def handle_starttag(self,tag,attrs):self.nodes.append((tag,dict(attrs)))

def test_real_mount_render_has_one_shared_history_panel_and_blank_form():
    html=render();nodes=Nodes(html).nodes
    panels=[attrs for _,attrs in nodes if 'data-im-panel' in attrs]
    assert len(panels)==1 and panels[0]['data-view']=='history'
    inputs=[attrs for tag,attrs in nodes if tag=='input'];assert len(inputs)==2
    assert {i['name'] for i in inputs}=={'local','fx'}
    assert all(i.get('value','')=='' and 'placeholder' not in i for i in inputs)
    assert all(i['type']=='text' and i['inputmode']=='decimal' for i in inputs)
    assert len([a for _,a in nodes if 'data-im-history-slot' in a])==2
    assert 'data-im-generation="im-workspace-generation:' in html

def test_every_input_has_real_label_and_associated_errors():
    nodes=Nodes(render()).nodes;ids=[a['id'] for _,a in nodes if 'id' in a]
    assert len(ids)==len(set(ids))
    labels={a['for'] for tag,a in nodes if tag=='label' and 'for' in a}
    for tag,a in nodes:
        if tag=='input':
            assert a['id'] in labels
            assert all(x in ids for x in a['aria-describedby'].split())

def test_both_languages_and_boundaries_are_visible_without_fake_revision_or_rank():
    text=render()
    for term in ['Recomputed history','重新计算的历史','Original-known history unavailable','当时已知的历史不可用','not investment returns','不是投资回报','No linked revision records','暂无关联的修订记录','not forecasts','不是预测','reciprocal conversion','倒数换算']:
        assert term in text
    assert '#4' not in text and '#1' not in text and '+5%' not in text and '-3%' not in text

def test_no_prefilled_result_or_live_keystroke_number():
    nodes=Nodes(render()).nodes
    result=next(a for _,a in nodes if 'data-im-scenario-result' in a);assert 'hidden' in result
    live=[a for _,a in nodes if 'aria-live' in a];assert len(live)==1 and live[0]['aria-live']=='polite'
    assert next(a for _,a in nodes if 'data-im-scenario-fields' in a).get('disabled') is None

def test_source_strings_are_always_escaped_in_non_autoescaping_owner_template():
    def change(w,a):
        a['registry']['markets'][0]['name_en']='<img src=x onerror=alert(1)>'
        a['sources']['JP']['turn_events'][0]['text_en']='<script>alert(1)</script>'
        a['sources']['JP']['turn_events'][0]['evidence_ref']='" onload="alert(1)'
        a['sources']['JP']['track_record']['qualification_notes']='<iframe src=evil>'
    text=render(change)
    assert '<script>' not in text and '<img' not in text and '<iframe' not in text
    assert '&lt;script&gt;' in text and '&#34; onload=' in text

@pytest.mark.parametrize('state',['missing','failed','empty','invalid','unsupported'])
def test_distinct_read_states_are_not_relabelled_as_zero_or_market_failure(state):
    def change(w,a):
        r=a['sources']['JP']['history_read'];r.update(status=state,points=[])
        if state!='empty':r['identity']=None
    text=render(change)
    expected={'missing':'History source missing','failed':'History source could not be read','empty':'No rows in the source','invalid':'History source is invalid','unsupported':'History source is unsupported'}[state]
    assert expected in text
    assert 'value="0"' not in text

def test_denied_metadata_cannot_leak_into_html():
    def change(w,a):
        a['sources']['JP']['history_read']['artifact_ref']='PRIVATE-REF/file'
        a['sources']['JP']['capabilities']['history_source']={'metadata':'denied','value':'denied'}
    text=render(change);assert 'PRIVATE-REF' not in text
    assert 'History information withheld' in text

def test_track_read_failure_is_not_a_zero_count_success_claim():
    def change(w,a):a['sources']['JP']['track_record'].update(read_health='failed',graded_count=0,alert_count=0)
    text=render(change)
    assert 'A qualified forward record is unavailable' in text
    assert 'Graded observations' not in text

def test_reset_and_context_confirmations_are_separate_hidden_actions():
    nodes=Nodes(render()).nodes
    for attr in ['data-im-scenario-confirm-context','data-im-scenario-confirm-reset']:
        assert 'hidden' in next(a for _,a in nodes if attr in a)
    actions={a.get('data-im-scenario-action') for _,a in nodes}
    assert {'calculate','request_reset','confirm_reset','cancel_reset','confirm_context','cancel_context','set_tab'}<=actions
