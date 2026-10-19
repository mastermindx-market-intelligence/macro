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
    root=_theme_owner_root(tmp_path)
    fx.build_root(root,slug=CHAIN)
    path=root/'data/theme_graph/nodes.parquet'
    rows=parquet.read_table(path).to_pylist()
    labels={'macro:energy':('Synthetic energy','合成能源'),'theme:solar':('Synthetic solar','合成太阳能'),
            'basket:baskets:solar':('Synthetic solar basket','合成太阳能组合')}
    for row in rows:
        if row['node_id'] in labels: row['name_en'],row['name_zh']=labels[row['node_id']]
    parquet.write_table(arrow.Table.from_pylist(rows),path)
    snapshot=ontology_explorer.compose_snapshot(root,chain=CHAIN)
    payload=dict(schema='ontology_theme_request.v1',chain=CHAIN,source_manifest_hash=snapshot['source']['source_manifest_hash'],
                 identity_kind='security',identity_id='SEC:US-XNAS-AAA')
    result=ontology_theme.compose_theme_continuation(root,payload)
    assert result['theme_map']['availability']['state']=='AVAILABLE'
    return snapshot,result


def start(browser,theme_reading,*,width=1440,theme='dark',language='en',mutate=None):
    snapshot,result=theme_reading
    ctx,page,other,errors=portfolio_start(browser,snapshot,width=width,theme=theme,language=language,full_shell=True)
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
        assert body==dict(schema='ontology_theme_request.v1',chain=CHAIN,
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
