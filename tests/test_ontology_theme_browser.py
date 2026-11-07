"""Actual native Theme Map emitter -> fully intercepted Macro shell.
All rows are synthetic; no production graph or company body is read.
"""
from copy import deepcopy
import json
from pathlib import Path
import pytest
import pyarrow as arrow
import pyarrow.parquet as parquet
from tests.test_ontology_explorer_brain_browser import browser
from tests.test_ontology_exposure_company_browser import portfolio_start
from tests.test_ontology_company_browser import fixtures, HEADERS
from tests.test_ontology_explorer_transport import _theme_owner_root
from tests import ontology_explorer_fixtures as fx
from engine import ontology_explorer, ontology_theme

CHAIN='oil_inflation_duration_derate'

@pytest.fixture
def theme_reading(tmp_path):
    return native_theme_reading(tmp_path)

def native_theme_reading(tmp_path, *, etf=False, etf_identity=False, monkeypatch=None, chain=CHAIN, hierarchy=True, master_clock=None):
    root=_theme_owner_root(tmp_path)
    fx.build_root(root,slug=chain)
    if master_clock is not None:
        # The native security-master _iso_now() emits naive UTC; identity
        # resolution copies that receipt clock verbatim into its published row.
        identity_path=root/'data/theme_graph/identity_resolution.parquet'
        identity_rows=parquet.read_table(identity_path).to_pylist()
        identity_rows[0]['master_generated_at']=master_clock
        parquet.write_table(arrow.Table.from_pylist(identity_rows),identity_path)
    if etf:
        from tests.test_theme_graph_hierarchy_paths import _selected_etf_view
        view=_selected_etf_view()
        if etf_identity:
            from tests.test_theme_graph_hierarchy_paths import _etf_adoption_inputs
            view,sources,*_=_etf_adoption_inputs(tmp_path/'listing',monkeypatch)
            for rel,raw in sources.items():
                path=root/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        if not hierarchy:
            view._edges = [e for e in view._edges if e['type'] not in {'EXPRESSES','PARENT_OF'}]
        for name, rows in [('nodes',view._nodes),('edges',view._edges),('evidence',view._evidence)]:
            parquet.write_table(arrow.Table.from_pylist(rows),root/'data/theme_graph'/f'{name}.parquet')
    path=root/'data/theme_graph/nodes.parquet'
    rows=parquet.read_table(path).to_pylist()
    labels={'macro:energy':('Synthetic energy','合成能源'),'theme:solar':('Synthetic solar','合成太阳能'),
            'basket:baskets:solar':('Synthetic solar basket','合成太阳能组合')}
    for row in rows:
        if row['node_id'] in labels: row['name_en'],row['name_zh']=labels[row['node_id']]
    parquet.write_table(arrow.Table.from_pylist(rows),path)
    snapshot=ontology_explorer.compose_snapshot(root,chain=chain)
    payload=dict(schema='ontology_theme_request.v1',chain=chain,source_manifest_hash=snapshot['source']['source_manifest_hash'],
                 identity_kind='security',identity_id='SEC:US-XNAS-AAA')
    result=ontology_theme.compose_theme_continuation(root,payload)
    assert result['theme_map']['availability']['state']==('AVAILABLE' if hierarchy else 'NO_QUALIFIED_HOUSE_PATH')
    return snapshot,result


@pytest.mark.parametrize('clock,width,theme,language',[
    ('2026-09-18T00:00:00',1440,'dark','en'),
    ('2026-09-18T00:00:00.123456',390,'light','zh'),
])
def test_company_native_master_clock_survives_emitter_and_explicit_theme_read(browser,tmp_path,clock,width,theme,language):
    reading=native_theme_reading(tmp_path,master_clock=clock)
    assert reading[1]['theme_map']['bindings'][0]['resolution']['master_generated_at']==clock
    ctx,page,seen,errors=start(browser,reading,width=width,theme=theme,language=language)
    try:
        assert seen==[]
        page.locator('[data-theme-read]').click();settled(page,'ready')
        text=page.locator('[data-theme-result]').inner_text()
        assert ('Synthetic solar' if language=='en' else '合成太阳能') in text
        page.locator('[data-theme-result] details').first.locator('summary').click()
        assert clock in page.locator('[data-theme-result]').inner_text()
        assert len(seen)==1 and not errors and page.evaluate('pCalls.queries')==0
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    finally:ctx.close()


def test_company_master_clock_decoder_preserves_refusals_and_utc_interpretation(browser,theme_reading):
    ctx,page,seen,errors=start(browser,theme_reading)
    try:
        outcomes=page.evaluate("""async ({v,reading})=>{
          const m=await import('/ontology-theme.js'),out=[];
          for(const clock of ['2026-09-18T00:00:00Z','2026-09-18T00:00:00+00:00',
              '2026-09-18T00:00:00','2026-09-18T00:00:00.123456',
              '2026-02-31T00:00:00','2026-02-31T00:00:00Z',
              '2999-01-01T00:00:00','2999-01-01T00:00:00Z',
              '2026-09-18T25:00:00','not-a-clock',null]) {
            const x=structuredClone(v);
            x.theme_map.bindings[0].resolution.master_generated_at=clock;
            try {await m.decodeTheme(x,reading,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});out.push(true)}
            catch {out.push(false)}
          }return out;
        }""",{'v':theme_reading[1],'reading':theme_reading[0]['source']})
        assert outcomes==[True,True,True,True,False,False,False,False,False,False,False]
        assert seen==[] and not errors
    finally:ctx.close()


@pytest.mark.parametrize('width,theme,language',[(1440,'dark','en'),(390,'light','zh')])
def test_unmapped_basket_keeps_qualified_etf_without_inventing_hierarchy(browser,tmp_path,monkeypatch,width,theme,language):
    reading = native_theme_reading(tmp_path,etf=True,etf_identity=True,monkeypatch=monkeypatch,hierarchy=False)
    ctx,page,seen,errors=start(browser,reading,width=width,theme=theme,language=language)
    try:
        page.locator('[data-theme-read]').click()
        card=page.locator('[data-etf-reference]')
        card.wait_for()
        text=page.locator('[data-theme-result]').inner_text()
        assert ('No house path is qualified' if language=='en' else '暂无合格的自有主题路径') in text
        assert ('does not require a complete theme hierarchy' if language=='en' else '不要求完整的主题层级') in text
        assert ('does not prove that the fund holds' if language=='en' else '不证明基金持有') in text
        card.locator('summary').click()
        assert 'SEC:US-XNAS-DIFFERENT' in card.inner_text()
        assert not errors
    finally:
        ctx.close()


@pytest.mark.parametrize('mutation',[
    'delete r.membership', 'r.membership.subject_node_id="co:us:OTHER"',
    'r.membership.relationship="EXPRESSES"', 'r.membership.basket.node_id="basket:baskets:OTHER"',
    'r.membership.basket.rights.public_display_allowed=false',
    'r.membership.clocks.valid_to=x.theme_map.asof', 'r.membership.clocks.belief_time="2099-01-01"',
    'r.membership.evidence=[]', 'r.membership.evidence[0].published_at=null',
])
def test_etf_decoder_requires_own_selected_membership_evidence(browser,etf_identity_reading,mutation):
    ctx,page,seen,errors=start(browser,etf_identity_reading)
    try:
        rejected=page.evaluate("""async ({v,reading})=>{
          const x=structuredClone(v),r=x.theme_map.etf_tracking.references[0];"""+mutation+""";
          const m=await import('/ontology-theme.js');
          try{await m.decodeTheme(x,reading,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});return false}catch{return true}
        }""",{'v':etf_identity_reading[1],'reading':etf_identity_reading[0]['source']})
        assert rejected
    finally:
        ctx.close()

@pytest.fixture
def etf_reading(tmp_path):
    result=native_theme_reading(tmp_path,etf=True)
    assert result[1]['theme_map']['etf_tracking']['status']=='available'
    return result

@pytest.mark.parametrize('width,theme,language',[(1440,'dark','en'),(390,'light','zh')])
def test_native_etf_reference_is_displayed_without_holdings_claim(browser,etf_reading,width,theme,language):
    ctx,page,seen,errors=start(browser,etf_reading,width=width,theme=theme,language=language)
    try:
        page.locator('[data-theme-read]').click();settled(page,'ready')
        card=page.locator('[data-etf-reference]')
        assert card.count()==1 and 'AAAETF' in card.inner_text()
        assert ('seed date' if language=='en' else '种子日期') in card.inner_text()
        card.locator('summary').click()
        text=card.inner_text()
        assert 'SEC:US-XNAS-AAA' in text and 'ev:tracking' in text and '2024-01-02T00:00:00Z' in text
        full=page.locator('[data-theme-result]').inner_text()
        assert ('ETF identity unavailable' if language=='en' else 'ETF 身份不可用') in full
        assert ('Holdings, weights and performance are unavailable' if language=='en' else '持仓、权重及表现不可用') in full
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert len(seen)==1 and not errors and page.evaluate('pCalls.queries')==0
    finally:ctx.close()

@pytest.fixture
def etf_identity_reading(tmp_path,monkeypatch):
    result=native_theme_reading(tmp_path,etf=True,etf_identity=True,monkeypatch=monkeypatch)
    assert result[1]['theme_map']['etf_tracking']['security_identity']['status']=='available'
    return result

@pytest.mark.parametrize('era,provenance',[('reconstruction','curated_changelog'),('observed','seed_constant')])
@pytest.mark.parametrize('width,theme,language',[(1440,'dark','en'),(390,'light','zh')])
def test_etf_observed_tracking_preserves_membership_date_limits(browser,etf_identity_reading,era,provenance,width,theme,language):
    ref=etf_identity_reading[1]['theme_map']['etf_tracking']['references'][0]
    ref.update(era='observed',date_provenance='curated_changelog')
    ref['membership'].update(era=era,date_provenance=provenance)
    ctx,page,seen,errors=start(browser,etf_identity_reading,width=width,theme=theme,language=language)
    try:
        page.locator('[data-theme-read]').click();settled(page,'ready')
        card=page.locator('[data-etf-reference]')
        assert ('seed date' if language=='en' else '种子日期') in card.inner_text()
        card.locator('summary').click()
        assert era+' / '+provenance in card.inner_text()
        assert ('Membership era / date provenance' if language=='en' else '成员关系时期 / 日期来源') in card.inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert len(seen)==1 and not errors
    finally:ctx.close()

@pytest.mark.parametrize('width,theme,language',[(1440,'dark','en'),(390,'light','zh')])
def test_etf_native_identity_stays_distinct_from_symbol_holdings_and_graph_clock(browser,etf_identity_reading,width,theme,language):
    ctx,page,seen,errors=start(browser,etf_identity_reading,width=width,theme=theme,language=language)
    try:
        page.locator('[data-theme-read]').click();settled(page,'ready')
        card=page.locator('[data-etf-reference]');card.locator('summary').click();text=card.inner_text()
        assert 'AAAETF' in text and 'SEC:US-XNAS-DIFFERENT' in text
        assert 'SEC:US-XNAS-AAAETF' not in text
        assert '2026-08-10' in text and '2024-01-02T00:00:00Z' in text
        assert ('not a historical identity claim' if language=='en' else '不代表历史身份') in text
        assert ('Holdings, weights and performance are unavailable' if language=='en' else '持仓、权重及表现不可用') in page.locator('[data-theme-result]').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert len(seen)==1 and not errors and page.evaluate('pCalls.queries')==0
    finally:ctx.close()

@pytest.mark.parametrize('mutation',[
 'i.security_id="SEC:US-XNAS-AAAETF"',
 'i.historical_identity_claim=true',
 'i.instrument_type_basis="SYMBOL_GUESS"',
 'i.master_generated_at="2999-01-01T00:00:00Z"',
 'i.listing_known_at="2999-01-01T00:00:00Z"',
 'i.listing_observed_on="2026-08-11"',
 'i.private_body="unqualified"',
 'i.status="unavailable";i.reason="ETF_IDENTITY_INPUTS_UNAVAILABLE"',
 't.security_identity.status="partial"',
 'v.source.reads=v.source.reads.filter(r=>!r.path.endsWith("vendor_aliases.parquet"))',
 'v.source.reads.find(r=>r.path.includes("receipts/snapshots")).path="data/symbol_directory/receipts/snapshots/2026-08-09.json"',
 'v.source.reads.find(r=>r.path.endsWith("vendor_aliases.parquet")).path="data/private/source_body.parquet"',
])
def test_etf_identity_decoder_refuses_unbound_claims_even_with_matching_manifest(browser,etf_identity_reading,mutation):
    ctx,page,seen,errors=start(browser,etf_identity_reading)
    try:
        rejected=page.evaluate("""async ({v,r})=>{const t=v.theme_map.etf_tracking,i=t.references[0].security_identity;"""+mutation+""";
          const reads=[...v.source.reads].sort((a,b)=>a.path.localeCompare(b.path));
          const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode([v.source.method,...reads.map(x=>x.path+':'+x.sha256)].join('\\n')));
          v.source.theme_source_manifest_hash='sha256:'+Array.from(new Uint8Array(hash),x=>x.toString(16).padStart(2,'0')).join('');
          const m=await import('/ontology-theme.js');try{await m.decodeTheme(v,r,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});return false}catch{return true}
        }""",{'v':etf_identity_reading[1],'r':etf_identity_reading[0]['source']})
        assert rejected and not errors and seen==[]
    finally:ctx.close()

def test_etf_decoder_accepts_native_naive_clock_and_partial_reads_but_not_invalid_calendar(browser,etf_identity_reading):
    ctx,page,seen,errors=start(browser,etf_identity_reading)
    try:
        outcomes=page.evaluate("""async ({v,r})=>{
          const m=await import('/ontology-theme.js'),out=[];
          for(const variant of ['naive','partial','invalid_calendar']) {
            const x=structuredClone(v),t=x.theme_map.etf_tracking,i=t.references[0].security_identity;
            if(variant==='naive') i.master_generated_at=i.master_generated_at.replace('Z','');
            if(variant==='invalid_calendar') i.master_generated_at='2026-02-31T00:00:00Z';
            if(variant==='partial') {
              t.references[0].security_identity={status:'unavailable',reason:'ETF_IDENTITY_INPUTS_UNAVAILABLE'};
              t.security_identity={status:'unavailable',reason:'ETF_IDENTITY_NOT_FULLY_RESOLVED'};
              x.source.reads=x.source.reads.filter(q=>!q.path.includes('symbol_directory/')&&!q.path.endsWith('vendor_aliases.parquet'));
              const reads=[...x.source.reads].sort((a,b)=>a.path.localeCompare(b.path));
              const hash=await crypto.subtle.digest('SHA-256',new TextEncoder().encode([x.source.method,...reads.map(q=>q.path+':'+q.sha256)].join('\\n')));
              x.source.theme_source_manifest_hash='sha256:'+Array.from(new Uint8Array(hash),q=>q.toString(16).padStart(2,'0')).join('');
            }
            try{await m.decodeTheme(x,r,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});out.push(true)}catch{out.push(false)}
          }return out;
        }""",{'v':etf_identity_reading[1],'r':etf_identity_reading[0]['source']})
        assert outcomes==[True,True,False] and not errors and seen==[]
    finally:ctx.close()


@pytest.mark.parametrize('mutation',[
 't.references[0].selected_security_id="SEC:US-XNAS-BBB"',
 't.references[0].basket_node_id="basket:baskets:unselected"',
 't.references[0].binding_node_id="co:us:BBB"',
 't.references[0].etf_node_id="etf:OTHER"',
 't.references[0].relationship_rights.public_display_allowed=false',
 't.references[0].relationship_rights.family="vendor"',
 't.references[0].clocks.belief_time="2026-01-03"',
 't.references[0].clocks.valid_to="2026-01-02"',
 't.references[0].evidence[0].computed_at="2026-01-03T02:11:00Z"',
 't.references[0].evidence.push(t.references[0].evidence[0])',
 't.references.push(t.references[0])',
 't.authority.can_rank=true',
 't.holdings.status="available"',
 't.security_identity.status="available"',
 't.exhaustive=true',
])
def test_etf_decoder_refuses_foreign_identity_rights_clocks_or_authority(browser,etf_reading,mutation):
    ctx,page,seen,errors=start(browser,etf_reading)
    try:
        accepted=page.evaluate("async ({v,r})=>{const m=await import('/ontology-theme.js');try{await m.decodeTheme(v,r,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});return true}catch{return false}}",{'v':etf_reading[1],'r':etf_reading[0]['source']})
        assert accepted
        rejected=page.evaluate("async ({v,r})=>{const t=v.theme_map.etf_tracking;"+mutation+";const m=await import('/ontology-theme.js');try{await m.decodeTheme(v,r,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});return false}catch{return true}}",{'v':etf_reading[1],'r':etf_reading[0]['source']})
        assert rejected and not errors and seen==[]
    finally:ctx.close()


def start(browser,theme_reading,*,width=1440,theme='dark',language='en',mutate=None):
    snapshot,result=theme_reading
    ctx,page,other,errors=portfolio_start(browser,snapshot,width=width,theme=theme,language=language,full_shell=True,chain=snapshot['source']['chain'])
    # Missing shared assets must not silently turn visual evidence into unstyled HTML.
    assert page.evaluate("Boolean(getComputedStyle(document.documentElement).getPropertyValue('--bg').trim())"), 'shared Macro theme stylesheet missing'
    assert page.evaluate("document.documentElement.dataset.theme") == theme
    assert page.evaluate("document.documentElement.dataset.lang") == language
    payloads=fixtures('AAA');seen=[]
    def company(route):
        url=route.request.url
        i=0 if 'company-context' in url else 1 if '/issuers/' in url else 2
        route.fulfill(status=200,headers=HEADERS,body=json.dumps(payloads[i]))
    page.route('**/api/company-intelligence/private/**',company)
    def respond(route):
        body=json.loads(route.request.post_data)
        seen.append({'url':route.request.url,'body':body,'headers':route.request.headers})
        assert body==dict(schema='ontology_theme_request.v1',chain=snapshot['source']['chain'],
             source_manifest_hash=snapshot['source']['source_manifest_hash'],identity_kind='security',identity_id='SEC:US-XNAS-AAA')
        status,headers,value=200,dict(HEADERS),deepcopy(result)
        if mutate: status,headers,value=mutate(status,headers,value)
        route.fulfill(status=status,headers=headers,body=json.dumps(value))
    page.route('**/api/ontology/explorer/theme/v1',respond)
    page.wait_for_function("document.querySelector('[data-theme-result]').dataset.state==='no_company'")
    page.locator('#ox-company input').fill('AAA');page.locator('#ox-company [type=submit]').click()
    page.wait_for_function("document.querySelector('[data-theme-result]').dataset.state==='idle'")
    return ctx,page,seen,errors


def settled(page,state):
    page.wait_for_function("s=>document.querySelector('[data-theme-result]').dataset.state===s",arg=state,timeout=5000)


def test_dollar_continuation_keeps_theme_identity_and_clears_private_read_on_owner_change(browser,tmp_path):
    reading=native_theme_reading(tmp_path,chain='dollar_spike_em_multinational')
    ctx,page,seen,errors=start(browser,reading)
    try:
        page.locator('[data-theme-read]').click();settled(page,'ready')
        assert len(seen)==1 and seen[0]['body']['chain']=='dollar_spike_em_multinational'
        assert 'Synthetic solar' in page.locator('[data-theme-result]').inner_text()
        page.evaluate("pOwner='owner-b';window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:pOwner}}}))")
        assert 'Synthetic solar' not in page.locator('[data-theme-result]').inner_text()
        assert page.locator('[data-theme-read]').is_disabled() and len(seen)==1 and not errors
    finally:ctx.close()

@pytest.mark.parametrize('width',[390,1440])
@pytest.mark.parametrize('theme,language',[('dark','en'),('light','zh')])
def test_native_house_theme_paths_on_assembled_macro(browser,theme_reading,width,theme,language):
    ctx,page,seen,errors=start(browser,theme_reading,width=width,theme=theme,language=language)
    try:
        assert seen==[] and page.evaluate('pCalls.queries')==0
        page.locator('[data-theme-read]').click();settled(page,'ready')
        assert len(seen)==1 and seen[0]['headers']['authorization']=='Bearer fixture-token'
        text=page.locator('[data-theme-result]').inner_text()
        assert ('Synthetic solar' if language=='en' else '合成太阳能') in text
        assert '2026-01-02' in text and '2026-01-03T02:10:00+00:00' in text
        assert ('latest published' if language=='en' else '最新发布') in text
        assert 'macro:energy' not in text and 'theme:solar' not in text
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.locator('[data-theme-read]').bounding_box()['height']>=44
        page.locator('[data-theme-clear]').click();settled(page,'idle')
        assert page.locator('#ox-theme article').count()==0 and len(seen)==1 and errors==[]
    finally:ctx.close()

@pytest.mark.parametrize('change',[
 "document.querySelector('#ox-company input').value='BBB';document.querySelector('#ox-company input').dispatchEvent(new Event('input'));",
 "window.pOwner=null;window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{event:'SIGNED_OUT',user:null}}));",
 "document.querySelector('#ox-theme').dispatchEvent(new CustomEvent('ontology-source-changed'));",
 "window.dispatchEvent(new PageTransitionEvent('pagehide'));",
 "window.pToken='new-token';pCallbacks.forEach(fn=>fn('TOKEN_REFRESHED',{user:{id:pOwner},access_token:pToken}));",
])
def test_theme_uncooperative_late_read_cannot_repaint(browser,theme_reading,change):
    ctx,page,seen,errors=start(browser,theme_reading)
    try:
        page.evaluate("()=>{window.themeFetch=fetch;window.fetch=(url,...args)=>String(url).endsWith('/theme/v1')?new Promise(resolve=>{window.lateTheme=resolve;}):themeFetch(url,...args);}")
        page.locator('[data-theme-read]').click();page.wait_for_function("typeof lateTheme==='function'")
        page.evaluate('()=>{'+change+'}')
        page.evaluate("v=>lateTheme(new Response(JSON.stringify(v),{status:200,headers:{'Content-Type':'application/json','Cache-Control':'private, no-store','Vary':'Authorization, Cookie'}}))",theme_reading[1])
        page.evaluate('()=>new Promise(resolve=>setTimeout(resolve,0))')
        assert page.locator('#ox-theme article').count()==0
        assert page.locator('[data-theme-result]').get_attribute('data-state')!='ready'
        assert errors==[] and seen==[]
    finally:ctx.close()


@pytest.mark.parametrize('change',['null','other_owner','token'])
def test_theme_sdk_session_is_rechecked_after_digest(browser,theme_reading,change):
    ctx,page,seen,errors=start(browser,theme_reading)
    try:
        page.evaluate("""()=>{const digest=crypto.subtle.digest.bind(crypto.subtle);
          crypto.subtle.digest=(...args)=>digest(...args).then(value=>new Promise(resolve=>{
            window.releaseThemeDigest=()=>resolve(value);
          }));}""")
        page.locator('[data-theme-read]').click()
        page.wait_for_function("typeof releaseThemeDigest==='function'")
        reads=page.evaluate('pCalls.sessions')
        page.evaluate("""change=>{pSessionHook=async()=>({data:{session:change==='null'?null:{
          user:{id:change==='other_owner'?'owner-b':'owner-a'},
          access_token:change==='token'?'rotated-token':'fixture-token'}}});
          releaseThemeDigest();}""",change)
        page.wait_for_function("document.querySelector('[data-theme-result]').dataset.state!=='loading'")
        assert page.evaluate('pCalls.sessions') > reads
        assert page.locator('[data-theme-result]').get_attribute('data-state')!='ready'
        assert page.locator('#ox-theme article').count()==0
        assert len(seen)==1 and errors==[]
    finally:ctx.close()

@pytest.mark.parametrize('mutation',[
 'v.source.source_manifest_hash="sha256:"+"0".repeat(64)',
 'v.source.reads[0].sha256="0".repeat(64)',
 'v.selection.identity_id="SEC:US-XNAS-BBB"',
 'v.theme_map.authority_ceiling="research_internal_only"',
 'v.theme_map.historical_identity_claim=true',
 'v.theme_map.knowledge_cutoff="2026-01-03T02:11:00Z"',
 'v.theme_map.bindings[0].resolution.security_id="SEC:US-XNAS-BBB"',
 'v.theme_map.bindings[0].paths[0].path[0].rights.family="vendor"',
 'v.theme_map.bindings[0].paths[0].via[0].node.rights.public_display_allowed=false',
 'v.theme_map.bindings[0].paths[0].parent_of_edge_ids=[]',
])
def test_theme_decoder_refuses_changed_identity_rights_or_generation(browser,theme_reading,mutation):
    ctx,page,seen,errors=start(browser,theme_reading)
    try:
        okay=page.evaluate("async ({v,r})=>{let m=await import('/ontology-theme.js');try{await m.decodeTheme(v,r,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});return true}catch{return false}}",{'v':theme_reading[1],'r':theme_reading[0]['source']})
        assert okay
        rejected=page.evaluate("async ({v,r})=>{"+mutation+";let m=await import('/ontology-theme.js');try{await m.decodeTheme(v,r,{identity_kind:'security',identity_id:'SEC:US-XNAS-AAA'});return false}catch{return true}}",{'v':theme_reading[1],'r':theme_reading[0]['source']})
        assert rejected and errors==[] and seen==[]
    finally:ctx.close()

@pytest.mark.parametrize('kind',['empty','public_headers','changed'])
def test_theme_typed_unavailable_does_not_claim_no_theme(browser,theme_reading,kind):
    def mutate(status,headers,value):
        if kind=='empty':value['theme_map']['bindings']=[];value['theme_map']['availability']={'state':'NO_GRAPH_BINDING'}
        elif kind=='public_headers':headers['Cache-Control']='public, max-age=60'
        else:status=409;value={'detail':{'schema':'ontology_explorer_error.v1','code':'source_changed'}}
        return status,headers,value
    ctx,page,seen,errors=start(browser,theme_reading,mutate=mutate)
    try:
        page.locator('[data-theme-read]').click();settled(page,'ready' if kind=='empty' else 'changed' if kind=='changed' else 'unavailable')
        if kind=='empty':assert 'does not establish' in page.locator('[data-theme-result]').inner_text()
        assert page.locator('#ox-theme article').count()==0 and len(seen)==1 and errors==[]
    finally:ctx.close()
