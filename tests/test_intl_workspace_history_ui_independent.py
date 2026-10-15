"""Independent C2 R2 tests for History mount/renderer and frozen INPUT_MANIFEST."""
from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
import json
import re

import pytest
from jinja2 import Environment, FileSystemLoader

from lib.intl_history_mount import attach_history
from lib.intl_workspace_binding import binding_version
from tests.test_intl_history_mount import GENERATION, fixture

ROOT = Path(__file__).resolve().parents[1]




def mount(change=None):
    workspace, args = fixture()
    if change:
        change(workspace, args)
    before = deepcopy((workspace, args))
    result = attach_history(workspace, **args)
    return result, before, workspace, args


def render_html(change=None, autoescape=False):
    result, _, _, _ = mount(change)
    env = Environment(loader=FileSystemLoader(ROOT / 'templates'), autoescape=autoescape)
    return env.get_template('intl_workspace/history.html.j2').render(
        history_panel=result['histories'][0], history_registry=result['history_registry']
    ), result


class Nodes(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.nodes = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))






def test_one_catalogue_keeps_configured_roster_when_source_is_absent():
    result, before, workspace, args = mount()
    panel = result['histories'][0]
    assert panel['context_id'] == 'im-history'
    assert [section['selected_market'] for section in panel['sections']] == ['JP', 'KR']
    assert panel['sections'][0]['source_read_status'] == 'ready'
    assert panel['sections'][1]['source_read_status'] == 'unknown'
    assert panel['sections'][1]['points'] == []
    assert panel['sections'][1]['events']['records'] == []
    assert (workspace, args) == before


def test_v1_withholds_all_new_history_grants_and_omits_generation():
    def change(workspace, args):
        workspace.pop('binding_version')
        workspace['config']['source_reference'] = 'legacy:fixture'
        for panel in workspace['panels']:
            panel.pop('generation')
            panel['overview']['context']['source_reference'] = 'legacy:fixture'

    result, _, _, _ = mount(change)
    panel = result['histories'][0]
    assert 'generation' not in panel
    assert panel['source_reference'] == 'legacy:fixture'
    for section in panel['sections']:
        assert section['source_read_status'] == 'unknown'
        assert section['points'] == []
        assert section['events']['records'] == []
        assert section['track_record']['status'] == 'unknown'
        assert section['track_record']['graded_count'] is None
        assert section['snapshot_compare']['eligible'] is False
        assert section['as_known']['available'] is False
        assert section['revisions']['status'] == 'unavailable'


def test_v1_html_keeps_presentation_source_without_generation_or_values():
    def change(workspace, args):
        workspace.pop('binding_version')
        workspace['config']['source_reference'] = 'legacy:fixture'
        for panel in workspace['panels']:
            panel.pop('generation')
            panel['overview']['context']['source_reference'] = 'legacy:fixture'

    html, result = render_html(change)
    assert 'data-im-generation' not in html
    assert 'legacy:fixture' in html
    assert '0.4375' not in html
    assert 'MA turn' not in html
    assert 'Graded observations' not in html
    assert 'JP_history.parquet' not in html
    assert result['histories'][0]['source_reference'] == 'legacy:fixture'


def test_v2_sidecar_generation_is_owned_by_shared_binding():
    result, _, _, _ = mount()
    assert binding_version(result) == (2, GENERATION)
    assert result['histories'][0]['generation'] == GENERATION
    result['histories'][0]['generation'] = 'im-workspace-generation:00000000-0000-4000-8000-000000000000'
    with pytest.raises(ValueError):
        binding_version(result)


def test_extra_or_mismatched_source_is_refused_without_mutating_inputs():
    def extra(workspace, args):
        args['sources']['US'] = deepcopy(args['sources']['JP'])

    def mismatched(workspace, args):
        args['sources']['JP']['history_read']['market_id'] = 'KR'

    for change in (extra, mismatched):
        workspace, args = fixture()
        change(workspace, args)
        before = deepcopy((workspace, args))
        with pytest.raises(ValueError, match='^invalid_history_workspace$'):
            attach_history(workspace, **args)
        assert (workspace, args) == before


def test_html_does_not_disclose_track_metrics_foreign_events_or_destinations():
    html, result = render_html()
    jp = result['histories'][0]['sections'][0]
    assert jp['track_record']['hit_rate'] == 0.25
    assert jp['track_record']['lift'] == 1.5
    assert jp['as_known']['destination'] == '/research/as-known'
    for secret in (
        '0.25', 'hit_rate', '/research/as-known', '/research/track-record',
        'global_top_ten', 'Other market', '其他市场', 'intl_regime.classifier_history',
        'as_known', 'false_alarms', 'drawdowns',
    ):
        assert secret not in html, secret
    assert 'No success rate is inferred' in html
    assert 'Original-known history unavailable' in html
    assert 'No linked revision records' in html
    assert 'record.turn.events:0' in html
    assert re.search(r'(^|[^.\w])record\.turn([^.\w]|$)', html) is None


def test_autoescape_false_still_escapes_every_source_string_surface():
    def change(workspace, args):
        args['registry']['markets'][0]['name_en'] = '<img src=x onerror=alert(1)>'
        args['registry']['markets'][0]['name_zh'] = '<svg onload=alert(2)>'
        src = args['sources']['JP']
        src['turn_events'][0]['text_en'] = '<script>alert(5)</script>'
        src['turn_events'][0]['text_zh'] = '<img src=y>'
        src['turn_events'][0]['evidence_ref'] = '" onload="alert(6)'
        src['track_record']['qualification_notes'] = '<iframe src=evil>'

    html, _ = render_html(change)
    for raw in ('<script>', '<img', '<svg', '<iframe'):
        assert raw not in html
    assert '&lt;script&gt;' in html
    assert '&lt;img' in html
    assert '&lt;svg' in html
    assert '&#34; onload=' in html
    assert '&lt;iframe' in html


def test_denied_metadata_cannot_publish_artifact_or_scores():
    def change(workspace, args):
        args['sources']['JP']['history_read']['artifact_ref'] = 'PRIVATE-REF/file'
        args['sources']['JP']['capabilities']['history_source'] = {'metadata': 'denied', 'value': 'denied'}

    html, result = render_html(change)
    section = result['histories'][0]['sections'][0]
    assert section['source_read_status'] == 'denied'
    assert section['source_reference'] is None
    assert section['points'] == []
    assert 'PRIVATE-REF' not in html
    assert '0.4375' not in html
    assert 'History information withheld' in html


def test_value_denied_keeps_dates_without_inventing_zero_scores():
    def change(workspace, args):
        args['sources']['JP']['capabilities']['history_source'] = {'metadata': 'allowed', 'value': 'denied'}

    html, result = render_html(change)
    points = result['histories'][0]['sections'][0]['points']
    assert points and all(point['growth_score'] is None and point['inflation_score'] is None for point in points)
    assert '2026-01-01T00:00:00+09:00' in html
    assert '0.4375' not in html
    assert 'Unavailable' in html
    assert 'value="0"' not in html


def test_failed_read_stays_failed_and_does_not_drop_independently_allowed_events():
    def change(workspace, args):
        args['sources']['JP']['history_read'].update(status='failed', identity=None, points=[])

    html, result = render_html(change)
    section = result['histories'][0]['sections'][0]
    assert section['source_read_status'] == 'failed'
    assert section['events']['status'] == 'available'
    assert section['events']['records'][0]['text_en'] == 'MA turn'
    assert 'History source could not be read' in html
    assert 'MA turn' in html
    assert 'No rows in the source' not in html


def test_track_read_failure_is_not_rendered_as_zero_success():
    def change(workspace, args):
        args['sources']['JP']['track_record'].update(read_health='failed', graded_count=0, alert_count=0)

    html, _ = render_html(change)
    assert 'A qualified forward record is unavailable' in html
    assert 'Graded observations' not in html
    assert 'forward_log independent read' not in html


def test_static_form_is_disabled_blank_and_confirmation_is_outside_the_fieldset():
    html, _ = render_html()
    nodes = Nodes(html).nodes
    fieldset = next(attrs for tag, attrs in nodes if tag == 'fieldset')
    assert 'disabled' in fieldset
    inputs = [attrs for tag, attrs in nodes if tag == 'input']
    assert all(attrs.get('value', '') == '' for attrs in inputs)
    assert html.find('data-im-scenario-fields') < html.find('</fieldset>') < html.find('data-im-scenario-confirm-reset')
    assert html.find('</fieldset>') < html.find('data-im-scenario-confirm-context')
    assert 'hidden' in next(attrs for _, attrs in nodes if 'data-im-scenario-result' in attrs)


def test_history_panel_is_one_shared_catalogue_not_per_horizon_pair():
    html, result = render_html()
    nodes = Nodes(html).nodes
    panels = [attrs for _, attrs in nodes if 'data-im-panel' in attrs]
    assert len(panels) == 1
    assert panels[0]['data-view'] == 'history'
    assert panels[0]['data-horizon'] == '1m'
    assert panels[0]['data-basis'] == 'usd_unhedged'
    assert panels[0]['data-return-basis'] == 'price'
    assert len(result['histories']) == 1
    assert len(result['histories'][0]['sections']) == 2
    assert [attrs['data-im-history-market'] for _, attrs in nodes if 'data-im-history-slot' in attrs] == ['JP', 'KR']
    assert html.count('0.4375') == 1
    assert html.count('data-im-generation="' + GENERATION + '"') == 1


def test_css_is_static_scoped_and_does_not_mint_tokens_or_fetch():
    css = (ROOT / 'templates/intl_workspace_history.css').read_text()
    controller = (ROOT / 'templates/intl_workspace.js').read_text()
    assert css.startswith('/* History:')
    assert ':root' not in css
    assert 'http://' not in css and 'https://' not in css and 'url(' not in css
    assert '@media(max-width:767px)' in css
    assert '[data-theme="light"] .intl-history__notice' in css
    assert '[data-theme="light"] .intl-history__result' in css
    assert '[data-theme="light"] .intl-history__boundary' in css
    assert '[data-theme="light"] .intl-history :is(input,select)' in css
    assert 'border-inline-start:3px solid var(--link)' in css
    assert 'var(--card-shadow)' in css
    assert '.style.' not in controller
    assert 'insertRule' not in controller
    used = set(re.findall(r'var\((--[a-z0-9-]+)', css))
    expected = {
        '--text', '--panel', '--line', '--r-card', '--fs-body', '--font-ui', '--fs-h2',
        '--panel2', '--fs-sm', '--link', '--r-ctl', '--fs-num-lg', '--muted', '--down',
        '--card-shadow',
    }
    assert used <= expected
    assert '[data-theme="light"] .intl-history__header' not in css


def test_mount_never_invents_allowed_grants_or_reads():
    source = (ROOT / 'lib/intl_history_mount.py').read_text()
    assert 'open(' not in source
    assert 'requests' not in source
    assert "metadata='allowed'" not in source
    html, _ = render_html()
    assert 'data-im-history-panel' in html
    assert 'novalidate' in html


def test_history_options_publish_both_locale_label_attributes():
    html, _ = render_html()
    nodes = Nodes(html).nodes
    options = [attrs for tag, attrs in nodes if tag == 'option']
    assert options
    assert all(attrs.get('data-im-label-en') and attrs.get('data-im-label-zh') for attrs in options)
