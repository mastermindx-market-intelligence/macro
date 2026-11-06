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


def run(tmp_path, *, search='?mode=companies&item=identity%3ABAESY&ticker=BAESY', lang='en', status=200, mutate=None, source_supported=False, atlas_input=None, workspace_input=None, actions='', rendered=False):
    atlas = copy.deepcopy(atlas_input) if atlas_input is not None else json.loads((ROOT / 'tests/fixtures/government_revenue/archetypes' / ('source_supported_ui_atlas.json' if source_supported else 'ui_atlas.json')).read_text())
    if mutate:
        mutate(atlas)
    template = (ROOT / 'templates/government_revenue.html.j2').read_text()
    old_template, old_root, old_runtime = base.TEMPLATE, base.ROOT, base._page_runtime_js
    base.TEMPLATE, base.ROOT = template, ROOT
    runtime = (ROOT / 'site/government-revenue-page.js').read_text() if rendered else base._page_runtime_js()
    prefix = "window.fetch=function(url){return Promise.resolve({ok:"+str(status == 200).lower()+",status:"+str(status)+",json:function(){return Promise.resolve("+json.dumps(atlas)+")}})};\n"
    base._page_runtime_js = lambda: prefix + runtime
    # Add only observations to the existing harness's output.
    code = inspect.getsource(base._run_runtime).replace(
        'companyBridgeHtml:node(\'companyBridge\').innerHTML,',
        'identityAtlasHtml:node(\'identityAtlas\').innerHTML, tickerOptionsHtml:node(\'tickerFilter\').innerHTML, companyBridgeHtml:node(\'companyBridge\').innerHTML,')
    code = code.replace('var afterRetry = bannerSnapshot();',
        "var copiedIdentityLinks=[];navigator.clipboard={writeText:function(url){copiedIdentityLinks.push(url);return Promise.resolve()}};var identityActionsResult={};" + actions + "\nvar afterRetry = bannerSnapshot();")
    code = code.replace('var result = {currentUrl:location.href,',
        'var result = {copiedIdentityLinks:copiedIdentityLinks,identityActions:identityActionsResult,currentUrl:location.href,')
    code = code.replace('setTimeout(function(){\n            var runtime',
        'setTimeout(async function(){\n            var runtime', 1)
    if rendered:
        assert 'ROOT / "templates" / "government-revenue-dossiers.js"' in code
        code = code.replace('ROOT / "templates" / "government-revenue-dossiers.js"', 'ROOT / "site" / "government-revenue-dossiers.js"')
    scope = dict(base.__dict__); exec(code, scope)
    try:
        payload = {'companies': [{'ticker': 'LMT', 'name': 'Lockheed Martin'}], 'market': {},
            'freshness': {'status': 'ok'}, 'opportunity_intelligence': {'market': {}, 'opportunities': [], 'events': []}}
        if workspace_input:
            shell = copy.deepcopy(workspace_input)
            shell['events'] = shell['events'][:1]
            shell['next_cursor'] = 'remaining-current-workspace'
            payload['procurement_workspace'] = shell
        return scope['_run_runtime'](tmp_path, payload,
            workspace_input or {}, 1791869800000, candidate_rows=[], candidate_status='unavailable',
            location_search=search, lang=lang, budget_module_status='unavailable',
            company_bridge_stub=True, real_dossiers_js=True)
    finally:
        base.TEMPLATE, base.ROOT = old_template, old_root
        base._page_runtime_js = old_runtime


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


@pytest.fixture
def retained_atlas():
    # Frozen reviewed observation clocks, independent of future owner refreshes.
    return json.loads((ROOT / 'tests/fixtures/government_revenue/archetypes/source_supported_ui_atlas.json').read_text())


def retained_bae(atlas):
    return next(row for row in atlas['issuers'] if row['ticker'] == 'BAESY')


@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_native_summary_keeps_observation_qualification_and_build_clocks_distinct(tmp_path, retained_atlas, lang):
    retained_atlas['generated_at'] = '2026-10-16T12:00:00+00:00'
    out = run(tmp_path, atlas_input=retained_atlas, lang=lang)
    row = retained_bae(retained_atlas)
    cases = row['archetype_context']['listing_cases']
    observed = cases[0]['known_at']
    qualified = next(case['research_identity']['known_at'] for case in cases if case.get('research_identity'))
    assert observed == '2026-10-13T05:36:47.904824+00:00'
    assert qualified == '2026-10-13T07:54:08.066798+00:00'
    html = out['inspectorHtml']
    assert observed in html and qualified in html and retained_atlas['generated_at'] in html
    assert ('Context known at: ' if lang == 'en' else '背景获知时间：') + qualified in html
    assert ('Source observation known at: ' if lang == 'en' else '来源观测获知时间：') + observed in html
    assert ('Research identity known at: ' if lang == 'en' else '研究身份获知时间：') + qualified in html
    assert ('First known at: ' if lang == 'en' else '首次获知：') not in html


def test_clock_order_uses_instants_not_lexical_offsets(tmp_path, retained_atlas):
    for case in retained_bae(retained_atlas)['archetype_context']['listing_cases']:
        case['known_at'] = '2026-10-13T09:00:00+02:00'
    out = run(tmp_path, atlas_input=retained_atlas)
    assert 'Context known at: 2026-10-13T07:54:08.066798+00:00' in out['inspectorHtml']
    assert 'Source observation known at: 2026-10-13T09:00:00+02:00' in out['inspectorHtml']


def test_copy_pins_evidence_content_and_matching_return_reopens_exact_subject(tmp_path, retained_atlas):
    from urllib.parse import urlsplit, parse_qs
    first = run(tmp_path, atlas_input=retained_atlas, actions="node('identityContextCopyLink').fire('click');")
    assert len(first['copiedIdentityLinks']) == 1
    copied = urlsplit(first['copiedIdentityLinks'][0])
    params = parse_qs(copied.query)
    assert params['item'] == ['identity:BAESY']
    assert params['identity_generation'] == [retained_atlas['content_id']]
    reopened = run(tmp_path, atlas_input=retained_atlas, search='?' + copied.query)
    assert reopened['selection']['selected'] == 'identity:BAESY'
    assert 'BAE Systems plc' in reopened['inspectorHtml']


def test_changed_evidence_cut_is_not_silently_substituted_on_return(tmp_path, retained_atlas):
    requested = 'gria1-' + 'a' * 24
    out = run(tmp_path, atlas_input=retained_atlas,
        search='?mode=companies&item=identity:BAESY&ticker=BAESY&identity_generation=' + requested,
        actions="node('deskSearch').fire('input');")
    assert 'Linked source evidence cut unavailable' in out['inspectorHtml']
    assert 'BAE Systems plc' not in out['inspectorHtml'] and 'Lockheed Martin' not in out['inspectorHtml']
    assert requested in out['currentUrl']


def test_same_evidence_cut_can_report_a_later_build_without_recertifying_source_clocks(tmp_path, retained_atlas):
    requested = retained_atlas['content_id']
    retained_atlas['generated_at'] = '2026-11-02T21:00:00+00:00'
    out = run(tmp_path, atlas_input=retained_atlas,
        search='?mode=companies&item=identity:BAESY&ticker=BAESY&identity_generation=' + requested)
    assert 'BAE Systems plc' in out['inspectorHtml']
    assert '2026-11-02T21:00:00+00:00' in out['inspectorHtml']
    assert '2026-10-13T07:54:08.066798+00:00' in out['inspectorHtml']


@pytest.mark.parametrize('pin', ['', 'invented', 'gria1-' + 'z' * 24])
def test_invalid_pin_is_not_downgraded_to_current_by_automatic_url_sync(tmp_path, retained_atlas, pin):
    from urllib.parse import urlsplit, parse_qs
    out = run(tmp_path, atlas_input=retained_atlas,
        search='?mode=companies&item=identity:BAESY&ticker=BAESY&identity_generation=' + pin,
        actions="node('deskSearch').fire('input');")
    assert 'Source evidence cut identifier invalid' in out['inspectorHtml']
    assert 'BAE Systems plc' not in out['inspectorHtml'] and 'Lockheed Martin' not in out['inspectorHtml']
    assert parse_qs(urlsplit(out['currentUrl']).query, keep_blank_values=True)['identity_generation'] == [pin]


@pytest.mark.parametrize('status', [401, 403, 404])
def test_unavailable_pinned_source_does_not_become_an_unversioned_or_other_subject(tmp_path, retained_atlas, status):
    pin = retained_atlas['content_id']
    out = run(tmp_path, atlas_input=retained_atlas, status=status,
        search='?mode=companies&item=identity:BAESY&ticker=BAESY&identity_generation=' + pin,
        actions="node('deskSearch').fire('input');")
    assert ('locked' if status in (401, 403) else 'unavailable') in out['inspectorHtml']
    assert 'BAE Systems plc' not in out['inspectorHtml'] and 'Lockheed Martin' not in out['inspectorHtml']
    assert pin in out['currentUrl']


@pytest.mark.parametrize('clock', [None, '', 'not-a-clock', '2026-10-13'])
def test_unknown_research_identity_clock_cannot_be_replaced_by_an_earlier_observation_or_build(tmp_path, retained_atlas, clock):
    case = next(case for case in retained_bae(retained_atlas)['archetype_context']['listing_cases'] if case.get('research_identity'))
    case['research_identity']['known_at'] = clock
    out = run(tmp_path, atlas_input=retained_atlas)
    assert 'Context known at: Not retained' in out['inspectorHtml']
    assert 'Research identity known at: Not established' in out['inspectorHtml']
    assert 'Source observation known at: 2026-10-13T05:36:47.904824+00:00' in out['inspectorHtml']


def test_native_fractional_clock_precision_is_retained_within_one_millisecond(tmp_path, retained_atlas):
    for case in retained_bae(retained_atlas)['archetype_context']['listing_cases']:
        case['known_at'] = '2026-10-13T07:54:08.066798+00:00'
        if case.get('research_identity'):
            case['research_identity']['known_at'] = '2026-10-13T07:54:08.066799+00:00'
    out = run(tmp_path, atlas_input=retained_atlas)
    assert 'Context known at: 2026-10-13T07:54:08.066799+00:00' in out['inspectorHtml']


def test_rejected_pin_survives_real_workspace_hydration_and_back_forward(tmp_path, retained_atlas):
    workspace = base._discovery_timing_workspace(
        effective_at='2026-08-01T00:00:00Z', known_at='2026-08-02T00:00:00Z',
        is_late_discovery=False)
    pin = 'gria1-' + 'a' * 24
    actions = """
      await window.__hydrateGovernmentWorkspace(true);
      identityActionsResult.afterHydration={html:node('inspector').innerHTML,url:location.href};
      node('deskSearch').fire('input');
      node('companyMode').fire('click');
      history.go(-1);
      identityActionsResult.back={html:node('inspector').innerHTML,url:location.href};
      history.go(1);
      identityActionsResult.forward={html:node('inspector').innerHTML,url:location.href};
      history.go(-1);
    """
    out = run(tmp_path, atlas_input=retained_atlas, workspace_input=workspace,
        search='?mode=companies&item=identity:BAESY&ticker=BAESY&identity_generation=' + pin, actions=actions)
    assert out['fetchCalls'] >= 1
    for key in ('afterHydration', 'back'):
        assert 'Linked source evidence cut unavailable' in out['identityActions'][key]['html']
        assert pin in out['identityActions'][key]['url']
    assert 'BAE Systems plc' in out['identityActions']['forward']['html']
    assert 'identity_generation' not in out['identityActions']['forward']['url']
    assert 'Linked source evidence cut unavailable' in out['inspectorHtml']
    assert pin in out['currentUrl']


@pytest.mark.parametrize('lang', ['en', 'zh'])
def test_normal_generated_assets_preserve_native_clock_and_pinned_copy_contract(tmp_path, retained_atlas, lang):
    from urllib.parse import urlsplit, parse_qs
    out = run(tmp_path, atlas_input=retained_atlas, lang=lang, rendered=True,
        actions="node('identityContextCopyLink').fire('click');")
    assert ('Research identity known at: ' if lang == 'en' else '研究身份获知时间：') + '2026-10-13T07:54:08.066798+00:00' in out['inspectorHtml']
    assert parse_qs(urlsplit(out['copiedIdentityLinks'][0]).query)['identity_generation'] == [retained_atlas['content_id']]
    assert 'company:BAESY' not in out['currentUrl']
