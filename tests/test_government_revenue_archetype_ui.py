"""Execute the incumbent identity-rail consumer against frozen owner examples."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / 'templates/government-revenue-dossiers.js'
FIXTURE = ROOT / 'tests/fixtures/government_revenue/archetypes/ui_atlas.json'
pytestmark = pytest.mark.skipif(shutil.which('node') is None, reason='node is required')


def render(tmp_path, *, language='en', ticker='LMT', mutate=None, status=200, switch=None, source_supported=False):
    atlas = json.loads((FIXTURE.with_name("source_supported_ui_atlas.json") if source_supported else FIXTURE).read_text())
    if mutate:
        mutate(atlas)
    script = r'''
const fs=require('fs'),vm=require('vm');
global.window=globalThis;
const atlas=JSON.parse(fs.readFileSync(process.argv[3],'utf8'));
let fetches=0,host={innerHTML:'',classList:{add(){},remove(){}}},historyTouched=0;
global.history={pushState(){historyTouched++},replaceState(){historyTouched++}};
global.fetch=async()=>{fetches++;return{status:STATUS,ok:STATUS===200,json:async()=>atlas}};
vm.runInThisContext(fs.readFileSync(process.argv[2],'utf8'));
const esc=x=>String(x==null?'':x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const api={obj:x=>!!x&&typeof x==='object'&&!Array.isArray(x),arr:x=>Array.isArray(x)?x:[],
 esc,text:(x,fb)=>x==null||x===''?(fb==null?'—':fb):String(x),
 n:x=>x==null||x===''||typeof x==='boolean'?null:Number.isFinite(Number(x))?Number(x):null,
 date:x=>String(x||'—').slice(0,10),tr:(en,zh)=>LANG==='zh'?zh:en,zh:()=>LANG==='zh',
 safeUrl:x=>{try{const u=new URL(String(x||''));return u.protocol==='https:'?u.href:''}catch{return''}},host:()=>host};
const ui=window.createGovernmentRevenueIdentityAtlas(api);
ui.loadCompany(TICKER);
if(SWITCH)ui.loadCompany(SWITCH);
setTimeout(()=>process.stdout.write(JSON.stringify({html:host.innerHTML,state:ui.state(),fetches,historyTouched})),5);
'''
    script = script.replace('STATUS', str(status)).replace('LANG', json.dumps(language)).replace('TICKER', json.dumps(ticker)).replace('SWITCH', json.dumps(switch))
    inp = tmp_path / 'atlas.json'; inp.write_text(json.dumps(atlas, ensure_ascii=False))
    runner = tmp_path / 'consumer.js'; runner.write_text(script)
    result = subprocess.run(['node', str(runner), str(JS), str(inp)], text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def context(atlas, ticker='LMT'):
    return next(row for row in atlas['issuers'] if row['ticker'] == ticker)['archetype_context']


def test_jv_interest_accounting_period_and_unknown_capture_are_visible(tmp_path):
    out = render(tmp_path)
    html = out['html']
    assert 'data-archetype-case="ownership"' in html
    assert '50% ownership interest' in html and 'Equity method' in html
    assert 'Disclosure period: 2026-06-28' in html
    assert 'Ownership interest is not revenue, workshare or distributable cash.' in html
    assert 'The Boeing Company · 50%' in html
    assert 'identity path unestablished in this view' in html
    assert 'Recipient attribution: unestablished' in html
    assert 'Disclosure snapshot only; later ownership continuity is unestablished.' in html
    assert 'Retained representation: source response bytes' in html
    assert 'Source reuse rights: unknown' in html
    assert 'https://www.sec.gov/Archives/edgar/data/936468/000162828026049411/R19.htm' in html
    assert 'record: 0001628280-26-049411:R19.htm' in html
    assert out['fetches'] == 1 and out['historyTouched'] == 0


def test_foreign_ordinary_and_adr_are_distinct_and_not_promoted(tmp_path):
    out = render(tmp_path, ticker='BAESY'); html = out['html']
    assert 'data-archetype-case="ordinary_share"' in html and 'data-archetype-case="adr"' in html
    assert 'Ordinary share' in html and 'ADR / depositary receipt' in html
    assert 'London Stock Exchange' in html and 'BA.LN' in html and 'OTC' in html and 'BAESY' in html
    assert '1 ADR represents 4 ordinary shares.' in html
    assert 'Native issuer identifier: 01470151' in html
    assert 'Quote currency: USD' in html and 'Quote currency unestablished' in html
    assert 'not in the covered listing universe' in html
    assert 'Data OS listing admission: unestablished.' in html
    assert 'Listing admission and issuer capture are unestablished.' in html
    assert 'https://www.baesystems.com/investors/adr-information' in html
    assert 'record: bae:adr:BAESY' in html
    assert 'Retained representation: reviewed web extract' in html
    assert 'Verified foreign listing' not in html


@pytest.mark.parametrize('ticker', ['LMT', 'BAESY'])
def test_chinese_disclosure_and_partial_states_do_not_fall_back_to_english(tmp_path, ticker):
    html = render(tmp_path, language='zh', ticker=ticker)['html']
    assert '所有权与上市身份限定条件' in html
    assert '来源复用权利：未知' in html
    assert 'Ownership interest is not' not in html and 'Data OS listing admission:' not in html
    if ticker == 'LMT':
        assert '50% 所有权权益' in html and '权益法' in html and '首次获知：' in html
    else:
        assert '1份ADR代表4股普通股。' in html and 'Data OS上市身份准入：尚未确立。' in html


def test_old_optional_payload_remains_usable_without_extra_disclosures(tmp_path):
    def mutate(atlas):
        for row in atlas['issuers']:
            row.pop('archetype_context', None)
    out = render(tmp_path, mutate=mutate)
    assert out['state'] == 'ok' and 'Ownership and listing qualifications' not in out['html']
    assert 'Identity record as of' in out['html']


def test_denied_context_is_not_rendered(tmp_path):
    def mutate(atlas):
        for row in context(atlas)['ownership_cases']:
            row['rights_state'] = 'denied'
    assert 'Ownership and listing qualifications' not in render(tmp_path, mutate=mutate)['html']


def test_hostile_names_and_source_text_are_escaped_and_unsafe_urls_omitted(tmp_path):
    def mutate(atlas):
        row = context(atlas)['ownership_cases'][0]
        row['canonical_name'] = '<img src=x onerror=alert(1)>'
        row['documentary_counterparties'][0]['name_as_printed'] = '<script>bad()</script>'
        row['evidence'][0]['url'] = 'javascript:alert(1)'
        row['evidence'][0]['publisher'] = '<script>publisher()</script>'
    html = render(tmp_path, mutate=mutate)['html']
    assert '<img' not in html and '<script>' not in html and 'href="javascript:' not in html
    assert '&lt;img' in html and '&lt;script&gt;' in html


@pytest.mark.parametrize('status', [401, 403])
def test_entitlement_denial_keeps_existing_locked_surface(tmp_path, status):
    out = render(tmp_path, status=status)
    assert out['state'] == 'locked' and 'Identity path locked' in out['html']
    assert 'Ownership and listing qualifications' not in out['html']
    assert 'United Launch Alliance' not in out['html']


def test_latest_selected_issuer_wins_without_url_or_focus_side_effects(tmp_path):
    out = render(tmp_path, switch='BAESY')
    assert 'BAE Systems plc' in out['html'] and 'United Launch Alliance' not in out['html']
    assert out['fetches'] == 1 and out['historyTouched'] == 0


def test_renderer_reuses_canonical_material_and_contains_no_ticker_strategy():
    source = JS.read_text(); start = source.index('    function contextClockRows(')
    end = source.index('    function unresolvedGroups(', start); extension = source[start:end]
    for banned in ('style.textContent', '<style', 'scrollIntoView', '.focus(', 'LMT', 'BAESY', 'IRDM', 'HII'):
        assert banned not in extension
    for required in ('atlas-entity', 'atlas-receipt', 'evidenceLinks', 'evidenceCode', 'tr('):
        assert required in extension


@pytest.mark.parametrize('language', ['en','zh'])
def test_source_supported_research_identity_reaches_real_identity_rail_with_limits(tmp_path, language):
    out = render(tmp_path, ticker='BAESY', language=language, source_supported=True)
    html = out['html']
    assert '0000895564' in html and 'US05523R1077' in html and 'GB0002634946' in html
    assert 'data/symbol_directory/cik_map/2026-10-05.parquet' in html
    assert 'https://www.adr.com/drprofile/05523R107' in html
    assert 'https://www.sec.gov/Archives/edgar/data/895564/0000895564-26-000004-index.htm' in html
    if language == 'en':
        assert 'Source-supported research identity' in html
        assert 'Current research identity only; historical eligibility, price coverage and award attribution remain unestablished.' in html
        assert 'Retained representation: reviewed browser extract' in html
        assert 'Data OS listing admission: unestablished.' in html
        assert 'Source reuse rights: unknown' in html
    else:
        assert '来源支持的研究身份' in html and '已复核浏览器摘录' in html
        assert '仅支持当前研究身份；历史准入、价格覆盖与授标归属尚未确立。' in html
        assert 'Source-supported research identity' not in html
    assert out['fetches'] == 1 and out['historyTouched'] == 0


def test_wrong_consumer_scope_cannot_render_supported_badge(tmp_path):
    def mutate(atlas):
        context(atlas, 'BAESY')['listing_cases'][1]['research_identity']['scope'] = 'global_security_master'
    html = render(tmp_path, ticker='BAESY', source_supported=True, mutate=mutate)['html']
    assert 'Source-supported research identity' not in html
    assert 'Source observation' in html


def test_support_source_fields_are_escaped(tmp_path):
    def mutate(atlas):
        q = context(atlas, 'BAESY')['listing_cases'][1]['research_identity']
        q['depositary_as_printed'] = '<img src=x onerror=bad()>'
        q['mapping_owner_path'] = '<script>bad()</script>'
    html = render(tmp_path, ticker='BAESY', source_supported=True, mutate=mutate)['html']
    assert '<img' not in html and '<script>' not in html
    assert '&lt;img' in html and '&lt;script&gt;' in html
