"""Browser consumption of the actual published-reader fixture, never live proof."""
from copy import deepcopy
import json
from pathlib import Path
from urllib.parse import urlsplit
import pytest

from engine.entry_radar.research_read import read_published_research
from tests.test_entry_radar_research_read import published, published_context, prepared, generation, native, inputs
from tests.test_ontology_explorer_brain_browser import browser

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {'Content-Type':'application/json','Cache-Control':'private, no-store',
           'Vary':'Authorization, Cookie'}


def start(browser, published, *, mutate=None, status=200, headers=None):
    live, _, _, episode = published
    context = browser.new_context()
    page = context.new_page()
    seen, errors = [], []
    shell = (ROOT/'site/ontology.html').read_text()
    auth = '''<script>window.owner='owner-a';window.token='fixture-token';window.callbacks=[];
    window.sdk={auth:{getSession:async()=>({data:{session:{user:{id:owner},access_token:token}}}),
    onAuthStateChange:fn=>{callbacks.push(fn);return{data:{subscription:{unsubscribe(){}}}};}}};
    window.MDXAuth={user:()=>owner?({id:owner}):null,client:async()=>sdk};</script>'''
    shell = shell.replace('<head>','<head>'+auth)
    def route(r):
        path = urlsplit(r.request.url).path
        if path == '/ontology.html':
            r.fulfill(status=200,content_type='text/html',body=shell)
        elif path == '/api/ontology/explorer/radar-research/v1':
            request = json.loads(r.request.post_data)
            seen.append({'payload':request,'headers':r.request.headers})
            value = read_published_research(live,episode_id=request['episode_id'])
            if mutate: mutate(value)
            r.fulfill(status=status,headers=headers or HEADERS,body=json.dumps(value))
        elif path == '/ontology-radar-research.js' or path.endswith('.css') or '/fonts/' in path:
            source = ROOT/'site'/path.lstrip('/')
            if source.is_file():
                r.fulfill(status=200,body=source.read_bytes(),content_type='text/javascript' if path.endswith('.js') else 'text/css' if path.endswith('.css') else 'font/woff2')
            else: r.fulfill(status=404)
        else: r.fulfill(status=204)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.route('**/*',route)
    page.goto('https://macro.example/ontology.html')
    page.locator('#ox-radar-research > summary').click()
    settled(page,'idle')
    return context,page,seen,errors,episode


def settled(page,state):
    page.wait_for_function("s=>document.querySelector('[data-radar-result]').dataset.state===s",arg=state)


def listing(page):
    page.locator('[data-radar-read]').click()
    settled(page,'ready')


@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('lang',['en','zh'])
@pytest.mark.parametrize('width',[390,1440])
def test_native_candidate_case_read_drillback_and_clear(browser,published,theme,lang,width):
    context,page,seen,errors,episode = start(browser,published)
    try:
        page.set_viewport_size({'width':width,'height':1000})
        page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l;document.dispatchEvent(new Event('langchange'))}",[theme,lang])
        assert seen == []
        listing(page)
        assert seen[0]['payload'] == {'schema':'ontology_radar_research_request.v1','episode_id':None}
        page.locator('[data-episode]').click();settled(page,'ready')
        assert seen[1]['payload']['episode_id'] == episode.episode_id
        assert all(r['headers']['authorization']=='Bearer fixture-token' for r in seen)
        page.locator('[data-radar-result] details > summary').click()
        text = page.locator('[data-radar-result]').inner_text()
        assert episode.candidate_at in text and 'opc_' in text
        assert ('does not establish' in text) if lang=='en' else ('不证明' in text)
        assert page.evaluate('[localStorage.length,sessionStorage.length]') == [0,0]
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.evaluate("window.owner=null;callbacks.forEach(f=>f('SIGNED_OUT',null));window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null}}))")
        settled(page,'idle')
        assert 'opc_' not in page.locator('[data-radar-result]').inner_text()
        assert len(seen)==2 and not errors
    finally: context.close()


@pytest.mark.parametrize('status,state',[(401,'signed_out'),(403,'forbidden'),(404,'not_found'),(503,'unavailable')])
def test_refusal_discards_private_state(browser,published,status,state):
    context,page,seen,errors,_=start(browser,published,status=status)
    try:
        page.locator('[data-radar-read]').click();settled(page,state)
        assert not page.locator('[data-radar-result] dl').count() and len(seen)==1 and not errors
    finally: context.close()


@pytest.mark.parametrize('mutation',['selection','authority','snapshot','clock','count','headers'])
def test_malformed_publication_is_not_rendered(browser,published,mutation):
    def change(v):
        if mutation=='selection': v['selection']='another'
        elif mutation=='authority': v['authority']['can_rank']=True
        elif mutation=='snapshot': v['source']['snapshot_sha256']='bad'
        elif mutation=='clock': v['source']['asof']='2099-01-01T00:00:00Z'
        elif mutation=='count': v['candidate_count']=2
    h=dict(HEADERS)
    if mutation=='headers': h['Cache-Control']='public'
    context,page,_,_,_=start(browser,published,mutate=change,headers=h)
    try:
        page.locator('[data-radar-read]').click();settled(page,'unavailable')
        assert not page.locator('[data-episode]').count()
    finally: context.close()


@pytest.mark.parametrize('edge',['account','token','clear','hidden'])
def test_delayed_old_account_response_cannot_reappear(browser,published,edge):
    context,page,_,errors,_=start(browser,published)
    try:
        page.evaluate("() => {window.savedFetch=fetch;window.fetch=(...a)=>new Promise((resolve,reject)=>{window.deliver=()=>{void savedFetch(...a).then(resolve,reject);};});}")
        page.locator('[data-radar-read]').click();settled(page,'loading')
        page.wait_for_function('typeof deliver==="function"')
        if edge=='account':
            page.evaluate("window.owner='owner-b';callbacks.forEach(f=>f('SIGNED_IN',{user:{id:owner}}));window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:owner}}}))")
        elif edge=='token': page.evaluate("window.token='rotated-token'")
        elif edge=='clear': page.locator('[data-radar-clear]').click()
        else: page.evaluate("Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'))")
        page.evaluate('() => {deliver();}')
        settled(page,'unavailable' if edge=='token' else 'idle')
        assert not page.locator('[data-episode]').count() and not errors
    finally: context.close()


def test_final_session_microtask_switch_cannot_render_previous_owner(browser,published):
    context,page,_,errors,_=start(browser,published)
    try:
        # Switch after the nested session check, before the caller's final
        # rendering continuation. The effect boundary needs its own check.
        page.evaluate("""() => {
          let calls=0;
          sdk.auth.getSession=()=>{
            const result={data:{session:{user:{id:owner},access_token:token}}};
            if(++calls===3) return new Promise(resolve=>{
              resolve(result);
              queueMicrotask(()=>queueMicrotask(()=>{
                window.owner='owner-b';callbacks.forEach(f=>f('SIGNED_IN',{user:{id:owner}}));
                window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:owner}}}));
              }));
            });
            return Promise.resolve(result);
          };
        }""")
        page.locator('[data-radar-read]').click()
        page.wait_for_function("window.owner==='owner-b'")
        settled(page,'idle')
        assert not page.locator('[data-episode]').count() and not errors
    finally: context.close()


@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('lang',['en','zh'])
@pytest.mark.parametrize('width',[390,1440])
def test_reported_earnings_context_preserves_value_period_and_distinct_clocks(browser,published_context,theme,lang,width):
    context,page,seen,errors,episode=start(browser,published_context)
    try:
        page.set_viewport_size({'width':width,'height':1000})
        page.evaluate("([t,l])=>{document.documentElement.dataset.theme=t;document.documentElement.dataset.lang=l}",[theme,lang])
        listing(page);page.locator('[data-episode]').click();settled(page,'ready')
        text=page.locator('[data-radar-result]').inner_text()
        assert '1,234' in text and '2026Q3' in text
        assert '2026-10-07T14:00:00Z' in text and '2026-10-07T14:01:00Z' in text
        assert ('Retrospective issuer context only' in text) if lang=='en' else ('仅为回溯性发行人背景' in text)
        assert 'opc_' not in text
        page.locator('[data-radar-result] details > summary').click()
        assert 'opc_' in page.locator('[data-radar-result]').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and not errors
        page.locator('[data-radar-clear]').click();settled(page,'idle')
        assert '1,234' not in page.locator('[data-radar-result]').inner_text() and len(seen)==2
    finally:context.close()


@pytest.mark.parametrize('mutation',['clock','value','unit','live'])
def test_malformed_retrospective_context_is_not_rendered(browser,published_context,mutation):
    def change(v):
        if v['state']!='published_context':return
        if mutation=='clock':v['case']['composed_at']='2020-01-01T00:00:00Z'
        elif mutation=='value':v['case']['observation']['value']=True
        elif mutation=='unit':v['case']['observation']['unit']='invented'
        else:v['case']['live_projection_eligible']=True
    context,page,_,_,_=start(browser,published_context,mutate=change)
    try:
        listing(page);page.locator('[data-episode]').click();settled(page,'unavailable')
        assert '1,234' not in page.locator('[data-radar-result]').inner_text()
    finally:context.close()
