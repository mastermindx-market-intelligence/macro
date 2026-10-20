from copy import deepcopy
from pathlib import Path
from html.parser import HTMLParser
from bs4 import BeautifulSoup
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


EVENT_CASES = {
    'metadata_denied': ('Attached changes withheld.', '附带变化记录未披露。'),
    'value_denied': ('Attached changes withheld.', '附带变化记录未披露。'),
    'metadata_unknown': ('Disclosure of attached changes is unknown.', '附带变化记录的披露状态未知。'),
    'value_unknown': ('Disclosure of attached changes is unknown.', '附带变化记录的披露状态未知。'),
    'empty': ('No qualified changes supplied for this market.', '此市场尚未提供符合条件的变化记录。'),
    'wrong_market': ('Supplied changes do not match this market.', '已提供的变化记录与此市场不匹配。'),
    'available': ('MA turn', '均线转折'),
}


def event_source(kind, market='JP'):
    """Synthetic native History inputs; these grants are test-only."""
    _, args = fixture()
    source = args['sources']['JP']
    source['history_read']['market_id'] = market
    source['history_read']['identity']['market_id'] = market
    source['track_record']['market_id'] = market
    source['turn_events'] = [source['turn_events'][0]]
    source['turn_events'][0]['market_id'] = market
    if kind.startswith('metadata_'):
        state = kind.removeprefix('metadata_')
        source['capabilities']['events'] = dict(metadata=state, value=state)
    elif kind.startswith('value_'):
        source['capabilities']['events']['value'] = kind.removeprefix('value_')
    elif kind == 'empty':
        source['turn_events'] = []
    elif kind == 'wrong_market':
        source['turn_events'][0]['market_id'] = 'OTHER'
    return source


@pytest.mark.parametrize('kind', EVENT_CASES)
def test_event_disclosure_state_is_not_reported_as_empty_history(kind):
    source = event_source(kind)
    before = deepcopy(source)
    text = render(lambda w, a: a['sources'].update(JP=source))
    article = BeautifulSoup(text, 'html.parser').select_one('[data-im-history-market="JP"]')
    heading = next(h for h in article.find_all('h4') if 'Attached changes' in h.get_text())
    state = heading.find_next_sibling()
    for expected in EVENT_CASES[kind]:
        assert expected in state.get_text()
    assert ('No qualified changes supplied' in state.get_text()) == (kind == 'empty')
    assert ('MA turn' in str(article)) == (kind == 'available')
    assert ('record.turn.events:0' in str(article)) == (kind == 'available')
    assert ('<time>' in str(article)) == (kind == 'available')
    # The independent history read and its date remain available.
    assert 'Recomputed observations' in article.get_text()
    assert '2026-01-03T00:00:00.123456789+09:00' in article.get_text()
    assert source == before


TRACK_CASES = {
    'metadata_denied': ('Forward record withheld.', '前瞻记录未披露。'),
    'value_denied': ('Forward record withheld.', '前瞻记录未披露。'),
    'metadata_unknown': ('Forward-record disclosure is unknown.', '前瞻记录的披露状态未知。'),
    'value_unknown': ('Forward-record disclosure is unknown.', '前瞻记录的披露状态未知。'),
    'not_supplied': ('No forward record supplied.', '未提供前瞻记录。'),
    'wrong_market': ('The supplied forward record does not match this market.', '已提供的前瞻记录与此市场不匹配。'),
    'failed': ('The forward record could not be read. A failed read does not establish an empty record.', '无法读取前瞻记录。读取失败不代表记录为空。'),
    'missing': ('The forward-record source is missing.', '缺少前瞻记录来源。'),
    'invalid': ('The forward-record source is invalid.', '前瞻记录来源无效。'),
    'unsupported': ('The forward-record source is unsupported.', '不支持此前瞻记录来源。'),
    'available': ('Counts are source-reported. No success rate is inferred.', '数量由来源报告，未据此推算成功率。'),
    'zero': ('Counts are source-reported. No success rate is inferred.', '数量由来源报告，未据此推算成功率。'),
}


def track_source(kind, market='JP'):
    """Use native input states; no production grant or record is created."""
    source = event_source('available', market)
    if kind.startswith('metadata_'):
        state = kind.removeprefix('metadata_')
        source['capabilities']['track_record'] = dict(metadata=state, value=state)
    elif kind.startswith('value_'):
        source['capabilities']['track_record']['value'] = kind.removeprefix('value_')
    elif kind == 'not_supplied':
        source['track_record'] = None
    elif kind == 'wrong_market':
        source['track_record']['market_id'] = 'OTHER'
    elif kind in {'failed', 'missing', 'invalid', 'unsupported'}:
        source['track_record'].update(read_health=kind, graded_count=0, alert_count=0)
    elif kind == 'zero':
        source['track_record'].update(graded_count=0, alert_count=0)
    return source


@pytest.mark.parametrize('kind', TRACK_CASES)
def test_forward_record_reports_its_own_reason_without_losing_real_zero(kind):
    source = track_source(kind)
    before = deepcopy(source)
    text = render(lambda w, a: a['sources'].update(JP=source))
    article = BeautifulSoup(text, 'html.parser').select_one('[data-im-history-market="JP"]')
    track = article.select_one('.intl-history__track')
    for expected in TRACK_CASES[kind]:
        assert expected in track.get_text()
    available = kind in {'available', 'zero'}
    assert len(track.select('dd')) == (2 if available else 0)
    if available:
        assert [n.get_text() for n in track.select('dd')] == (['0', '0'] if kind == 'zero' else ['4', '1'])
        assert '2026-01-15' in track.get_text()
    else:
        assert '2026-01-15' not in track.get_text()
        assert 'forward_log independent read' not in track.get_text()
    assert ('A failed read' in track.get_text()) == (kind == 'failed')
    assert 'MA turn' in article.get_text()
    assert '2026-01-03T00:00:00.123456789+09:00' in article.get_text()
    assert source == before


SNAPSHOT_ELIGIBLE = ('available', 'zero', 'reversed', 'monthly')
SNAPSHOT_INELIGIBLE = ('metadata_denied', 'metadata_unknown', 'value_denied',
                       'value_unknown', 'not_requested', 'same_date', 'absent_date',
                       'incomplete_identity', 'null_score', 'failed')


def snapshot_source(kind, market='JP'):
    """Existing native snapshot-query seam with explicit synthetic History grants."""
    source = event_source('available', market)
    read = source['history_read']
    query = source['capabilities']['snapshot_compare']
    if kind.startswith('metadata_'):
        state = kind.removeprefix('metadata_')
        source['capabilities']['history_source'] = dict(metadata=state, value=state)
    elif kind.startswith('value_'):
        source['capabilities']['history_source']['value'] = kind.removeprefix('value_')
    elif kind == 'zero':
        read['points'][0].update(growth_score=0, inflation_score=0)
    elif kind == 'reversed':
        query['left_observation_at'], query['right_observation_at'] = query['right_observation_at'], query['left_observation_at']
    elif kind == 'monthly':
        read['points'] = [dict(observation_at='2026-01', growth_score=0, inflation_score=-1.25),
                          dict(observation_at='2026-03', growth_score=17, inflation_score=0.1875)]
        query.update(left_observation_at='2026-01', right_observation_at='2026-03')
    elif kind == 'not_requested':
        query.update(left_observation_at=None, right_observation_at=None)
    elif kind == 'same_date':
        query['right_observation_at'] = query['left_observation_at']
    elif kind == 'absent_date':
        query['right_observation_at'] = '2026-01-04T00:00:00+09:00'
    elif kind == 'incomplete_identity':
        read['identity']['universe'] = None
    elif kind == 'null_score':
        read['points'][1]['growth_score'] = None
    elif kind == 'failed':
        read.update(status='failed', identity=None, points=[])
    return source


@pytest.mark.parametrize('kind', SNAPSHOT_ELIGIBLE)
def test_snapshot_composition_keeps_supplied_pair_order_dates_and_scores(kind):
    source = snapshot_source(kind)
    before = deepcopy(source)
    html = render(lambda w, a: a['sources'].update(JP=source))
    soup = BeautifulSoup(html, 'html.parser')
    comparison = soup.select_one('[data-im-history-market="JP"] .intl-history__snapshot')
    assert comparison is not None
    assert comparison.name == 'details' and not comparison.has_attr('open')
    assert comparison.select_one('summary').get_text() == 'Compare two supplied observations比较两条已提供的观测'
    query = source['capabilities']['snapshot_compare']
    expected = [next(p for p in source['history_read']['points'] if p['observation_at'] == query[key])
                for key in ('left_observation_at', 'right_observation_at')]
    rows = comparison.select('dl > div')
    assert len(rows) == 2
    assert [row.dt.get_text() for row in rows] == [p['observation_at'] for p in expected]
    for row, point in zip(rows, expected):
        assert row.select_one('[data-im-snapshot-growth]').get_text() == str(point['growth_score'])
        assert row.select_one('[data-im-snapshot-inflation]').get_text() == str(point['inflation_score'])
    for text in ('current reconstruction', '当前重建', 'not investment returns', '不是投资回报',
                 'not what was known at the time', '不代表当时已知的信息'):
        assert text in comparison.get_text()
    assert not comparison.select('button, input, select, a')
    assert source == before
    assert soup.select_one('[data-im-history-market="KR"] .intl-history__snapshot') is None


@pytest.mark.parametrize('kind', SNAPSHOT_INELIGIBLE)
def test_snapshot_composition_does_not_admit_ineligible_pairs(kind):
    source = snapshot_source(kind)
    html = render(lambda w, a: a['sources'].update(JP=source))
    article = BeautifulSoup(html, 'html.parser').select_one('[data-im-history-market="JP"]')
    assert article.select_one('.intl-history__snapshot') is None
    # Ineligible pairs do not hide independently permitted single observations.
    if kind in ('not_requested', 'same_date', 'absent_date', 'incomplete_identity', 'null_score'):
        assert len(article.select('.intl-history__observations tbody tr')) == 3
    if kind in ('metadata_denied', 'metadata_unknown'):
        assert '2026-01-01T00:00:00+09:00' not in article.get_text()
    if kind in ('metadata_denied', 'metadata_unknown', 'value_denied', 'value_unknown'):
        assert '0.4375' not in article.get_text()
