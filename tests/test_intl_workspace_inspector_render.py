"""Render actual owner -> Overview -> Inspector projections with autoescape off."""
from copy import deepcopy
from html.parser import HTMLParser
import importlib.util
from pathlib import Path

import jinja2
import pytest

from engine.intl_performance_records import build_return_records
from lib.intl_inspector_view import INSPECTOR_COPY, build_inspector_view

# Load the existing actual-owner fixture under pytest's importlib mode as well
# as a standalone review capsule; no alternative financial fixture is created.
_fixture_spec = importlib.util.spec_from_file_location(
    'inspector_owner_fixture', Path(__file__).with_name('test_intl_inspector_view.py'),
)
_fixture_module = importlib.util.module_from_spec(_fixture_spec)
_fixture_spec.loader.exec_module(_fixture_module)
supplied = _fixture_module.supplied


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def with_attr(self, name):
        return [(tag, attrs) for tag, attrs in self.nodes if name in attrs]


ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).resolve().parents[1] / 'templates'),
    autoescape=False, undefined=jinja2.StrictUndefined,
)


def panel(overview, market='JP', context_id='im-1m-usd', **kwargs):
    context = {k: overview['context'][k] for k in ('horizon', 'currency_basis', 'return_basis', 'source_reference')}
    inspector = build_inspector_view(overview, selected_market=market, context=context, **kwargs)
    return {'context_id': context_id, 'binding': {**context, 'market_id': market}, 'inspector': inspector}


def render(*panels, root='workspace-one'):
    return ENV.get_template('intl_workspace/inspector.html.j2').render(
        inspector_panels=list(panels), root_context_id=root, inspector_copy=INSPECTOR_COPY,
    )


def test_actual_values_units_identity_and_public_source(supplied):
    p = panel(supplied[0]())
    html = render(p)
    doc = Document(html)
    assert 'Nikkei 225' in html and 'TOPIX' not in html
    assert len(doc.with_attr('data-im-inspector-metric')) == 3
    assert len(doc.with_attr('data-im-inspector-field')) == 3
    for leg in ('local', 'usd', 'fx_contribution'):
        v = p['inspector']['metrics'][leg]['value']
        assert (f'{v:+.2f}' if v > 0 else f'{v:.2f}') in html
    assert 'pp' in html and '个百分点' in html
    assert doc.with_attr('data-im-inspector-payload')[0][1]['data-source'] == 'synthetic:inspector-source'


def test_one_closed_shell_and_native_disclosures_without_javascript(supplied):
    doc = Document(render(panel(supplied[0]())))
    shells = [(tag, attrs) for tag, attrs in doc.nodes if tag == 'dialog']
    assert len(shells) == 1 and 'open' not in shells[0][1]
    assert len([tag for tag, _ in doc.nodes if tag == 'details']) == 5
    assert len([tag for tag, _ in doc.nodes if tag == 'summary']) == 5
    assert not any(tag in ('script', 'style', 'iframe') for tag, _ in doc.nodes)
    assert all('style' not in attrs and not any(k.startswith('on') for k in attrs) for _, attrs in doc.nodes)
    assert all('hidden' in attrs for _, attrs in doc.with_attr('data-im-inspector-enhancement'))


def test_every_aria_reference_exists_and_multiple_panel_ids_are_unique(supplied):
    overview = supplied[0]()
    doc = Document(render(panel(overview), panel(overview, 'GB'), panel(supplied[0](basis='local'), context_id='im-1m-local')))
    ids = [attrs['id'] for _, attrs in doc.nodes if 'id' in attrs]
    assert len(ids) == len(set(ids))
    for _, attrs in doc.nodes:
        for key in ('aria-controls', 'aria-labelledby'):
            assert all(target in ids for target in attrs.get(key, '').split())
    assert len(doc.with_attr('data-im-inspector-payload')) == 3
    assert len(doc.with_attr('data-im-inspector-shell')) == 1


def test_context_binding_is_explicit_and_inputs_detached(supplied):
    p = panel(supplied[0](), context_id='canonical-overview-panel')
    before = deepcopy(p)
    attrs = Document(render(p)).with_attr('data-im-inspector-payload')[0][1]
    assert attrs['data-im-inspector-context'] == 'canonical-overview-panel'
    assert attrs['data-horizon'] == '1m' and attrs['data-basis'] == 'usd_unhedged'
    assert attrs['data-return-basis'] == 'price'
    assert p == before


def test_denied_and_absent_are_identical_nonidentifying_markup(supplied):
    def deny(receipts):
        for receipt in receipts:
            if receipt['binding']['market_id'] == 'JP':
                receipt['disclosure']['metadata'] = 'denied'
    overview = supplied[0](edit=deny)
    denied = render(panel(overview))
    assert denied == render(panel(overview, 'PRIVATE-REQUEST'))
    for forbidden in ('JP', 'Nikkei', 'PRIVATE-REQUEST', 'synthetic:inspector-source', 'owner_ref'):
        assert forbidden not in denied
    assert not Document(denied).with_attr('data-im-inspector-payload')


def test_context_mismatch_closes_without_source_or_selected_identity(supplied):
    overview = supplied[0]()
    p = panel(overview)
    context = {k: overview['context'][k] for k in ('horizon', 'currency_basis', 'return_basis', 'source_reference')}
    context['horizon'] = '3m'
    p['inspector'] = build_inspector_view(overview, selected_market='JP', context=context)
    html = render(p)
    assert 'Nikkei' not in html and 'synthetic:inspector-source' not in html
    assert not Document(html).with_attr('data-market-id')


def test_unknown_row_cannot_borrow_another_markets_disclosed_source(supplied):
    overview = supplied[0](edit=lambda r: r.__setitem__(slice(None), [x for x in r if x['binding']['market_id'] == 'GB']))
    assert overview['context']['source_reference'] is not None
    p = panel(overview)
    html = render(p)
    attrs = Document(html).with_attr('data-im-inspector-payload')[0][1]
    assert attrs['data-market-id'] == 'JP' and 'data-source' not in attrs
    assert 'synthetic:inspector-source' not in html and 'Nikkei 225' not in html
    assert len(Document(html).with_attr('data-im-inspector-missing')) == 6


def test_local_only_data_remains_useful_without_invented_usd_decomposition(supplied):
    project, _, frame = supplied
    raw = build_return_records(frame.drop(columns=['USDJPY=X']), market_ids=['JP', 'GB'], source_reference='synthetic:local-only')
    p = panel(project(basis='local', data=raw))
    html = render(p)
    assert p['inspector']['status'] == 'partial'
    assert 'Local currency' in html and 'Nikkei 225' in html
    assert 'same calculation window.' not in html
    assert len(Document(html).with_attr('data-im-inspector-missing')) >= 2


@pytest.mark.parametrize('shape', ['zero', 'negative', 'positive'])
def test_actual_numeric_signs_and_zero_are_preserved(supplied, shape):
    project, _, frame = supplied
    frame = frame.copy()
    frame['^N225'] = 100. if shape == 'zero' else (list(range(130, 100, -1)) if shape == 'negative' else list(range(100, 130)))
    raw = build_return_records(frame, market_ids=['JP', 'GB'], source_reference='synthetic:signs')
    p = panel(project(basis='local', data=raw))
    html = render(p)
    value = p['inspector']['metrics']['local']['value']
    assert (f'{value:+.2f}' if value > 0 else f'{value:.2f}') + '%' in html
    assert INSPECTOR_COPY['selected_return_' + shape]['en'] in html


@pytest.mark.parametrize('field', ['name_en', 'name_zh', 'index_id', 'index_label', 'source_reference'])
def test_dynamic_strings_escape_even_when_builder_autoescape_is_disabled(supplied, field):
    overview = supplied[0]()
    payload = '\"><img src=x onerror=evil()> & <script>evil()</script>'
    if field == 'source_reference':
        overview['context'][field] = payload
    else:
        overview['rows'][0][field] = payload
    html = render(panel(overview))
    doc = Document(html)
    assert not any(tag in ('img', 'script') for tag, _ in doc.nodes)
    assert not any('onerror' in attrs for _, attrs in doc.nodes)
    assert payload not in html
    # Index ID is intentionally not presented as a second user-facing label.
    if field != 'index_id':
        assert '&lt;' in html and '&amp;' in html


def test_calculation_and_endpoint_dates_do_not_become_source_clocks(supplied):
    p = panel(supplied[0]())
    html = render(p)
    for evidence in p['inspector']['evidence']:
        window = evidence['calculation_window']
        assert window['start'] in html and window['end'] in html
        for stamp in evidence['endpoint_observations'].values():
            if stamp is not None:
                assert stamp in html
    clocks = Document(html).with_attr('data-im-inspector-clock')
    assert len(clocks) == 12
    assert {attrs['data-im-inspector-clock'] for _, attrs in clocks} == {'observation', 'publication', 'ingestion', 'generation'}
    for block in html.split('<dl data-im-inspector-clocks>')[1:]:
        assert '<time' not in block.split('</dl>')[0]
    assert 'calculation observations do not establish publication or freshness.' in html


def test_deeper_links_only_render_actual_resolved_routes(supplied):
    links = [
        {'market_id': 'JP', 'tool_key': 'cross-country', 'label_en': 'Cross-country research', 'label_zh': '跨市场研究', 'route_state': 'available', 'target': {'page_id': 'macro:intl', 'route': '/intl.html', 'region_id': 'intl-cross-country'}},
        {'market_id': 'JP', 'tool_key': 'stocks', 'label_en': 'Stocks', 'label_zh': '股票', 'route_state': 'available', 'target': {'page_id': 'macro:intl_stocks', 'route': '/intl_stocks.html', 'region_id': None}},
    ]
    doc = Document(render(panel(supplied[0](), deeper_links=links)))
    assert [attrs['href'] for tag, attrs in doc.nodes if tag == 'a'] == ['/intl.html#intl-cross-country', '/intl_stocks.html']


def test_no_private_qualification_or_unsupported_product_actions(supplied):
    html = render(panel(supplied[0]()))
    for value in ('owner_ref', 'policy_ref', 'decision_ref', 'synthetic:source-owner', 'synthetic:policy', 'synthetic:decision', 'Follow', 'Saved', 'monitoring', '61%', 'TOPIX'):
        assert value not in html
    assert not any(tag == 'a' for tag, _ in Document(html).nodes)


def test_bilingual_pairs_share_identical_semantic_order(supplied):
    doc = Document(render(panel(supplied[0]())))
    langs = [attrs for tag, attrs in doc.nodes if tag == 'span' and attrs.get('class') in ('l-en', 'l-zh')]
    assert len(langs) % 2 == 0
    for en, zh in zip(langs[::2], langs[1::2]):
        assert en['class'] == 'l-en' and zh['class'] == 'l-zh' and zh['lang'] == 'zh'
