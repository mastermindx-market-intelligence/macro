"""Actual owner -> Overview -> Compare -> Jinja; all rights fixtures synthetic."""
from copy import deepcopy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path

import jinja2
import pytest

from engine.intl_performance_records import build_return_records
from lib.intl_compare_view import build_compare_catalogue

spec = importlib.util.spec_from_file_location(
    'compare_render_fixture', Path(__file__).with_name('test_intl_inspector_view.py'))
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
supplied = fixture.supplied
ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(Path(__file__).resolve().parents[1] / 'templates'),
    autoescape=False, undefined=jinja2.StrictUndefined,
)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.nodes = []; self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def with_attr(self, name):
        return [(tag, attrs) for tag, attrs in self.nodes if name in attrs]


def render(view, context_id='im-compare-test'):
    return ENV.get_template('intl_workspace/compare.html.j2').render(
        compare_catalogue=build_compare_catalogue(view), context_id=context_id)


def test_actual_owner_schema_context_and_three_values_per_row(supplied):
    view = supplied[0](); before = deepcopy(view); html = render(view); doc = Document(html)
    panels = doc.with_attr('data-im-panel')
    assert len(panels) == 1
    attrs = panels[0][1]
    assert attrs['data-view'] == 'compare' and attrs['data-basis'] == 'usd_unhedged'
    assert attrs['data-return-basis'] == 'price' and attrs['data-horizon'] == '1m'
    assert attrs['data-source'] == view['context']['source_reference']
    assert len(doc.with_attr('data-im-compare-slot')) == 2
    assert len(doc.with_attr('data-im-compare-metric')) == 6
    assert [a['data-im-compare-metric'] for _, a in doc.with_attr('data-im-compare-metric')] == ['local', 'usd', 'fx_contribution'] * 2
    assert 'Nikkei 225' in html and 'FTSE 100' in html
    assert len(doc.with_attr('data-im-compare-status')) == 1
    assert doc.with_attr('data-im-compare-status')[0][0] == 'p'
    assert view == before


@pytest.mark.parametrize('count', [0, 1, 4])
def test_one_row_per_slot_and_unique_ids_across_contexts(supplied, count):
    view = supplied[0]()
    for slot in range(2, count):
        row = deepcopy(view['rows'][0]); row.update(slot=slot, market_id='TEST'+str(slot))
        view['rows'].append(row)
    view['rows'] = view['rows'][:count]; view['configured_count'] = count
    view['focus_ids'] = [x for x in view['focus_ids'] if x in {r['market_id'] for r in view['rows']}]
    doc = Document(render(view, 'first') + render(view, 'second'))
    assert len(doc.with_attr('data-im-compare-slot')) == count * 2
    assert len(doc.with_attr('data-im-panel')) == 2
    ids = [attrs['id'] for _, attrs in doc.nodes if 'id' in attrs]
    assert len(ids) == len(set(ids))
    for _, attrs in doc.nodes:
        for key in ('aria-controls', 'aria-labelledby', 'aria-describedby'):
            assert all(target in ids for target in attrs.get(key, '').split())


def test_denied_identity_does_not_reappear_in_render_or_manifest(supplied):
    def deny(receipts):
        for receipt in receipts:
            if receipt['binding']['market_id'] == 'JP': receipt['disclosure']['metadata'] = 'denied'
    html = render(supplied[0](edit=deny)); doc = Document(html)
    assert 'JP' not in html and 'Nikkei' not in html
    assert len(doc.with_attr('data-im-compare-metric')) == 3
    assert [a['data-im-compare-slot'] for _, a in doc.with_attr('data-im-compare-slot')] == ['0', '1']
    assert all('hidden' in a for _, a in doc.with_attr('data-im-compare-remove'))


@pytest.mark.parametrize('value,expected', [(10**350, str(10**350)), (1e20, '100000000000000000000.00'),
                                         (-0.0, '-0.00'), (0, '0'), (-7.25, '-7.25')])
def test_owner_finite_numbers_never_float_coerce_large_ints_or_reject_valid_floats(supplied, value, expected):
    view = supplied[0](); view['rows'][0]['local']['value'] = value
    html = render(view)
    assert expected in html and 'Invalid number' not in html


def test_missing_fx_and_unknown_source_are_explicit(supplied):
    raw = build_return_records(supplied[2].drop(columns=['USDJPY=X', 'GBPUSD=X']),
                               market_ids=['JP', 'GB'], source_reference='synthetic:local')
    local = render(supplied[0](basis='local', data=raw))
    assert 'Unavailable' in local and 'Local currency' in local
    unknown = render(supplied[0](decisions=False)); doc = Document(unknown)
    assert doc.with_attr('data-im-panel')[0][1]['data-source'] == ''
    assert not doc.with_attr('data-im-compare-source')
    assert not doc.with_attr('data-im-compare-cohort')


def test_secondary_interval_is_visible_separately_from_selected_cohort(supplied):
    view = supplied[0]()
    view['rows'][0]['local']['window']['start'] = '2025-12-19T00:00:00'
    html = render(view); doc = Document(html)
    assert 'Metric interval' in html and '2025-12-19T00:00:00' in html
    assert len(doc.with_attr('data-im-compare-cohort')) == 1
    assert view['rows'][0]['metric']['window']['calendar_policy'] in html


def test_no_javascript_readability_and_bounded_inert_metadata(supplied):
    html = render(supplied[0]()); doc = Document(html)
    scripts = [(tag, a) for tag, a in doc.nodes if tag == 'script']
    assert len(scripts) == 1 and scripts[0][1]['type'] == 'application/json'
    assert len(doc.with_attr('data-im-compare-metric')) == 6
    assert not any('hidden' in a for _, a in doc.with_attr('data-im-compare-slot'))
    assert not any(tag in ('style', 'iframe') for tag, _ in doc.nodes)
    assert all('style' not in a and not any(k.startswith('on') for k in a) for _, a in doc.nodes)
    text = html.split('data-im-compare-catalogue>', 1)[1].split('</script>', 1)[0]
    payload = json.loads(text)
    assert set(payload) == {'schema', 'slot_order', 'cohorts'}
    assert payload['schema'] == 'intl-compare-catalogue.v1'
    assert all(set(c) == {'id', 'order_slots'} for c in payload['cohorts'])
    assert 'value' not in text and 'market_id' not in text and 'owner_ref' not in html


def test_hostile_public_strings_are_escaped_with_autoescape_disabled(supplied):
    view = supplied[0]()
    attack = '\"><script>alert(1)</script><img src=x onerror=alert(2)> & \u2028\u2029'
    view['rows'][0].update(name_en=attack, name_zh=attack, index_label=attack)
    view['context']['source_reference'] = attack
    html = render(view, attack); doc = Document(html)
    assert len([tag for tag, _ in doc.nodes if tag == 'script']) == 1
    assert not any(tag == 'img' or any(k.startswith('on') for k in a) for tag, a in doc.nodes)
    assert '&lt;script&gt;' in html and '&amp;' in html
    assert doc.with_attr('data-im-panel')[0][1]['data-source'] == attack
