"""Real page + real atlas factory: source subjects never become award coverage."""
from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Reuse the incumbent bounded browser harness; no parallel production reader.
REPO = Path(__file__).resolve().parents[1]
if (ROOT / 'identity-subject-template.js.txt').exists():
    REPO = Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main')
spec = importlib.util.spec_from_file_location('govrev_incumbent_ui_harness', REPO / 'tests/test_government_revenue_ui.py')
base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='node required')


def run(tmp_path, *, search='?mode=companies&item=identity%3ABAESY&ticker=BAESY', lang='en', status=200, mutate=None, source_supported=False):
    atlas = json.loads((ROOT / 'tests/fixtures/government_revenue/archetypes' / ('source_supported_ui_atlas.json' if source_supported else 'ui_atlas.json')).read_text())
    if mutate:
        mutate(atlas)
    template = (ROOT / 'templates/government_revenue.html.j2').read_text()
    old_template, old_root = base.TEMPLATE, base.ROOT
    base.TEMPLATE, base.ROOT = template, ROOT
    runtime = base._page_runtime_js()
    prefix = "window.fetch=function(url){return Promise.resolve({ok:"+str(status == 200).lower()+",status:"+str(status)+",json:function(){return Promise.resolve("+json.dumps(atlas)+")}})};\n"
    base._page_runtime_js = lambda: prefix + runtime
    # Add only observations to the existing harness's output.
    code = inspect.getsource(base._run_runtime).replace(
        'companyBridgeHtml:node(\'companyBridge\').innerHTML,',
        'identityAtlasHtml:node(\'identityAtlas\').innerHTML, tickerOptionsHtml:node(\'tickerFilter\').innerHTML, companyBridgeHtml:node(\'companyBridge\').innerHTML,')
    scope = dict(base.__dict__); exec(code, scope)
    try:
        return scope['_run_runtime'](tmp_path,
            {'companies': [{'ticker': 'LMT', 'name': 'Lockheed Martin'}], 'market': {},
             'freshness': {'status': 'ok'}, 'opportunity_intelligence': {'market': {}, 'opportunities': [], 'events': []}},
            {}, 1791869800000, candidate_rows=[], candidate_status='unavailable',
            location_search=search, lang=lang, budget_module_status='unavailable',
            company_bridge_stub=True, real_dossiers_js=True)
    finally:
        base.TEMPLATE, base.ROOT = old_template, old_root
        base._page_runtime_js = lambda: runtime


def test_foreign_source_subject_is_reachable_from_real_page_and_deep_link(tmp_path):
    out = run(tmp_path)
    assert out['selection']['selected'] == 'identity:BAESY'
    assert 'BAE Systems plc' in out['inspectorHtml']
    assert 'Source observations only' in out['inspectorHtml']
    assert 'no award coverage or issuer capture asserted' in out['inspectorHtml']
    assert 'TTM obligations' not in out['inspectorHtml'] and 'Net award action flow' not in out['inspectorHtml']
    assert 'data-archetype-case="ordinary_share"' in out['identityAtlasHtml']
    assert 'data-archetype-case="adr"' in out['identityAtlasHtml']
    assert '1 ADR represents 4 ordinary shares.' in out['identityAtlasHtml']
    assert 'value="BAESY"' in out['tickerOptionsHtml']
    assert not any(call == {'op': 'load', 'ticker': 'BAESY'} for call in out['bridgeCalls'])


def test_source_subject_is_a_distinct_row_and_actual_company_roster_is_preserved(tmp_path):
    out = run(tmp_path, search='?mode=companies')
    assert out['queueHtml'].count('data-row="company:LMT"') == 1
    assert out['queueHtml'].count('data-row="identity:BAESY"') == 1
    assert 'data-row="company:BAESY"' not in out['queueHtml']
    assert 'data-row="identity:LMT"' not in out['queueHtml']


@pytest.mark.parametrize('status', [401, 403])
def test_private_source_denial_does_not_publish_a_subject_or_substitute_a_company(tmp_path, status):
    out = run(tmp_path, status=status)
    assert 'Source identity context locked' in out['inspectorHtml']
    assert 'identity:BAESY' not in out['queueHtml']
    assert 'Lockheed Martin' not in out['inspectorHtml']


def test_invalid_owner_content_identity_has_no_source_subject(tmp_path):
    out = run(tmp_path, mutate=lambda atlas: atlas.update(content_id='invented'))
    assert 'Source identity context unavailable' in out['inspectorHtml']
    assert 'identity:BAESY' not in out['queueHtml']


def test_active_filters_keep_source_selection_honest_and_do_not_substitute(tmp_path):
    out = run(tmp_path, search='?mode=companies&item=identity%3ABAESY&ticker=LMT')
    assert 'Source context excluded by active filters' in out['inspectorHtml']
    assert 'Lockheed Martin' not in out['inspectorHtml']


def test_chinese_real_page_source_context_has_no_award_metrics(tmp_path):
    out = run(tmp_path, lang='zh')
    assert '来源身份背景' in out['inspectorHtml']
    assert '不' in out['inspectorHtml'] and '授标覆盖' in out['inspectorHtml']
    assert '1份ADR代表4股普通股。' in out['identityAtlasHtml']
    assert 'TTM 义务额' not in out['inspectorHtml']


def test_no_fake_latest_companies_or_new_subject_truth_store():
    source = (ROOT / 'templates/government-revenue-page.js.j2').read_text()
    start = source.index('  var identitySubjects=')
    end = source.index('  function buildRows()', start)
    body = source[start:end]
    for banned in ('COMPANIES.push', 'DATA.companies=', 'metrics:', 'BAESY', 'BA.LN', 'localStorage', '<style'):
        assert banned not in body
    assert "kind:'identity_context'" in body and 'source_generation_id' in body


@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_supported_foreign_research_identity_deep_link_preserves_award_boundary(tmp_path, lang):
    out = run(tmp_path, lang=lang, source_supported=True)
    assert out['selection']['selected'] == 'identity:BAESY'
    html = out['identityAtlasHtml']
    assert '0000895564' in html and 'US05523R1077' in html and 'GB0002634946' in html
    assert 'https://www.adr.com/drprofile/05523R107' in html
    assert ('Source-supported research identity' if lang == 'en' else '来源支持的研究身份') in html
    assert 'TTM obligations' not in out['inspectorHtml'] and 'TTM 义务额' not in out['inspectorHtml']
    assert 'data-row="company:BAESY"' not in out['queueHtml']
    assert not any(call == {'op': 'load', 'ticker': 'BAESY'} for call in out['bridgeCalls'])
