from pathlib import Path
import pytest
import tests.test_ontology_explorer_brain_browser as incumbent
from tests.test_ontology_explorer_brain_browser import browser, synthetic_snapshot

PREPARED = Path(__file__).resolve().parents[1] / "templates" / "ontology.js"
def test_signout_clears_current_owner_read_and_brain_selection(browser, synthetic_snapshot, monkeypatch):
    monkeypatch.setattr(incumbent, "ONTOLOGY_JS", PREPARED)
    context, page = incumbent._open(browser, synthetic_snapshot, width=1440, height=900)
    try:
        page.locator("#ox-steps .ox-brain-action").first.click()
        assert page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()") is not None
        page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
        assert page.locator("#ox-root .ox-hero").count() == 0
        assert page.locator("#ox-root .ox-gate").count() == 1
        assert page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()") is None
    finally:
        context.close()


def test_old_uncooperative_owner_response_cannot_repaint_after_signout(browser, synthetic_snapshot):
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(incumbent.SHELL)
        page.evaluate("() => { window.fetch=()=>new Promise(resolve=>{window.finishOldReading=resolve;}); }")
        page.add_script_tag(path=str(PREPARED))
        page.wait_for_function("typeof window.finishOldReading === 'function'")
        page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
        page.evaluate("snapshot=>window.finishOldReading({ok:true,status:200,json:async()=>snapshot})",synthetic_snapshot)
        page.evaluate("()=>new Promise(resolve=>setTimeout(resolve,0))")
        assert page.locator("#ox-root .ox-hero").count() == 0
        assert page.locator("#ox-root .ox-gate").count() == 1
    finally:
        context.close()


def test_account_changes_before_publication_refuse_old_account_snapshot(browser, synthetic_snapshot):
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(incumbent.SHELL)
        page.evaluate("""snapshot=>{
          window.currentOwner={id:'first'};
          window.MDXAuth={user:()=>window.currentOwner,client:async()=>({auth:{getSession:async()=>({data:{session:{user:window.currentOwner,access_token:'fixture-'+window.currentOwner.id}}})}})};
          window.fetch=async()=>({ok:true,status:200,json:async()=>{window.currentOwner={id:'second'};return snapshot;}});
        }""",synthetic_snapshot)
        page.add_script_tag(path=str(PREPARED))
        page.wait_for_selector("#ox-root .ox-gate",state="attached")
        assert page.locator("#ox-root .ox-hero").count() == 0
    finally:
        context.close()


def test_missing_canonical_owner_refuses_even_with_stale_sdk_session(browser):
    context=browser.new_context()
    page=context.new_page()
    try:
        page.set_content(incumbent.SHELL)
        page.evaluate("""() => {
          window.calls=0;
          window.MDXAuth.user=()=>null;
          window.fetch=async()=>{window.calls++;throw new Error('must not fetch');};
        }""")
        page.add_script_tag(path=str(PREPARED))
        page.wait_for_selector("#ox-root .ox-gate",state="attached")
        assert page.evaluate("window.calls") == 0
        assert page.locator("#ox-root .ox-hero").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize('width',[390,1440])
def test_existing_membership_handoff_is_explicit_and_refusals_have_no_action(browser,synthetic_snapshot,monkeypatch,width):
    monkeypatch.setattr(incumbent,'ONTOLOGY_JS',PREPARED)
    monkeypatch.setattr(incumbent,'ONTOLOGY_CSS',PREPARED.with_suffix('.css'))
    monkeypatch.setattr(incumbent,'SHELL',incumbent.SHELL.replace('<div id="mock-brain"',
      '<section id="ox-company" data-company-ready="true"></section><div id="mock-brain"'))
    synthetic_snapshot['source']['substrate_asof']={'min':'2025-12-31','max':'2026-01-01'}
    synthetic_snapshot['exposure_screens']=[{
      'id':'fixture','label':{'en':'Synthetic exposure','zh':'合成敞口'},
      'n':2,'unevaluable':17,'cuts':{'synthetic_cut':2.5},
      'companies':{'linked':[{'symbol':'TEST','security_id':'SEC:US-XNAS-TEST'}],
                   'unlinked':[{'symbol':'UNKNOWN','reason':'unresolved'}]}
    }]
    context,page=incumbent._open(browser,synthetic_snapshot,width=width,height=900)
    try:
        page.evaluate("""() => {
          window.companyChoices=[];
          document.getElementById('ox-company').addEventListener('ontology-select-company',event=>window.companyChoices.push(event.detail));
        }""")
        assert page.evaluate('window.companyChoices') == []
        exposure=page.locator('[data-exposure-membership]')
        exposure.locator('summary').first.click()
        assert '17' in exposure.inner_text()
        assert '2026-01-01' in exposure.inner_text()
        assert exposure.locator('button').count() == 1
        assert exposure.locator('li',has_text='UNKNOWN').locator('button').count() == 0
        button=exposure.locator('button')
        assert button.bounding_box()['height'] >= 44
        original_url=page.url
        button.click()
        chosen=page.evaluate('window.companyChoices')
        assert len(chosen)==1
        assert chosen[0]['symbol']=='TEST'
        assert chosen[0]['security_id']=='SEC:US-XNAS-TEST'
        assert chosen[0]['manifest_hash']==synthetic_snapshot['source']['source_manifest_hash']
        assert page.url==original_url
        assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    finally:
        context.close()


import json
from urllib.parse import urlsplit
from tests.test_ontology_company_browser import fixtures, start, settled

@pytest.mark.parametrize('identity_matches',[True,False])
@pytest.mark.parametrize('width',[390,1440])
def test_explicit_owner_membership_to_private_company_read(browser,synthetic_snapshot,identity_matches,width):
    context=browser.new_context(viewport={'width':width,'height':900})
    page=context.new_page()
    try:
        company,selection,fact=fixtures()
        if not identity_matches:
            company['security_id']='SEC:US-XNAS-OTHER'
        seen,errors=start(page,context=company,selection=selection,fact=fact,full_shell=True,analytics=[])
        synthetic_snapshot['source']['substrate_asof']={'min':'2025-12-31','max':'2026-01-01'}
        synthetic_snapshot['exposure_screens']=[{
            'id':'fixture','label':{'en':'Synthetic exposure','zh':'合成敞口'},
            'n':2,'unevaluable':17,'cuts':{'synthetic_cut':2.5},
            'companies':{'linked':[{'symbol':'TEST','security_id':'SEC:US-XNAS-TEST'}],
                'unlinked':[{'symbol':'UNKNOWN','reason':'unresolved'}],'ranked':False}
        }]
        def prepared_asset(route):
            name=Path(urlsplit(route.request.url).path).name
            source=PREPARED.parent/name
            if source.is_file():
                route.fulfill(status=200,content_type='text/css' if name.endswith('.css') else 'text/javascript',body=source.read_bytes())
            else:
                route.fallback()
        page.route('**/ontology*.js*',prepared_asset)
        page.route('**/ontology.css*',prepared_asset)
        page.route('**/api/ontology/explorer/v1**',lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(synthetic_snapshot)))
        page.reload()
        page.locator('#ox-root .ox-hero').wait_for()
        settled(page,'idle')
        assert seen==[]
        membership=page.locator('[data-exposure-membership]')
        membership.locator(':scope > summary').click()
        button=membership.locator('button')
        button.wait_for(state='visible')
        button.click()
        settled(page,'ready' if identity_matches else 'unavailable')
        if identity_matches:
            assert len(seen)==2
            assert page.locator('#ox-company input').input_value()=='TEST'
            assert '2026-01-01' in membership.inner_text()
            page.locator('#ox-company .ox-company-choices button').click()
            page.get_by_text('SYNTHETIC TEST PRODUCT',exact=True).wait_for()
            assert len(seen)==3
            assert page.url.endswith('/ontology.html')
            page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}))")
            assert page.locator('#ox-root .ox-hero').count()==0
            assert 'SYNTHETIC TEST PRODUCT' not in page.content()
            assert page.locator('#ox-company input').input_value()==''
        else:
            assert len(seen)==1
            assert page.locator('#ox-company .ox-company-choices button').count()==0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert errors==[]
    finally:
        context.close()


def test_back_forward_restore_loads_a_new_reading_after_clearing_old_state(browser, synthetic_snapshot):
    context, page = incumbent._open(browser, synthetic_snapshot, width=1440, height=900)
    try:
        before = page.evaluate("window.__fetchCount")
        page.locator("#ox-steps .ox-brain-action").first.click()
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
        assert page.locator("#ox-root .ox-hero").count() == 0
        assert page.evaluate("window.MM_BRAIN_CFG.getOntologySelection()") is None
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow',{persisted:true}))")
        page.locator("#ox-root .ox-hero").wait_for()
        assert page.evaluate("window.__fetchCount") == before + 1
    finally:
        context.close()


@pytest.mark.parametrize("user,token", [({}, "fixture-token"), ({"id":""}, "fixture-token"), ({"id":"first"}, {"invalid":"token"})])
def test_malformed_auth_binding_never_reads_owner_snapshot(browser, user, token):
    context = browser.new_context()
    page = context.new_page()
    try:
        page.set_content(incumbent.SHELL)
        page.evaluate("""([user,token]) => {
          window.calls=0;
          window.MDXAuth={user:()=>user,client:async()=>({auth:{getSession:async()=>({data:{session:{user,access_token:token}}})}})};
          window.fetch=async()=>{window.calls++;throw new Error('must not fetch');};
        }""", [user, token])
        page.add_script_tag(path=str(PREPARED))
        page.wait_for_selector("#ox-root .ox-gate", state="attached")
        assert page.evaluate("window.calls") == 0
        assert page.locator("#ox-root .ox-hero").count() == 0
    finally:
        context.close()


# X4 uses the real read-only WatchStore and Portfolio authority computation. Every
# data response is synthetic and intercepted; no cloud or production calls occur.
_PORTFOLIO_AUTH = """
window.pOwner='owner-a';window.pToken='fixture-token';window.pCalls={queries:0,sessions:0,writes:0};
window.pRows=[{id:'a',user_id:'owner-a',ticker:'AAA',shares:2,entry_price:30,status:'open',entry_date:null,created_at:null},
 {id:'b',user_id:'owner-a',ticker:'BBB',shares:1,entry_price:40,status:'open',entry_date:null,created_at:null}];
window.wLists=[{id:'wl-a',user_id:'owner-a',name:'Energy <private>',position:0,created_at:null}];
window.wSymbols=[{watchlist_id:'wl-a',symbol:'AAA',position:0,created_at:null},
 {watchlist_id:'wl-a',symbol:'BBB',position:1,created_at:null},{watchlist_id:'wl-a',symbol:'AAA',position:2,created_at:null}];
window.pCallbacks=[];
window.pClient={auth:{getSession:async()=>{pCalls.sessions++;if(window.pSessionHook)return pSessionHook();
 return{data:{session:pOwner?{user:{id:pOwner},access_token:pToken}:null}};},
 onAuthStateChange:fn=>{pCallbacks.push(fn);return{data:{subscription:{unsubscribe(){}}}};}},
 from:table=>{pCalls.queries++;(pCalls.tables||(pCalls.tables=[])).push(table);
 if(!['portfolio_positions','watchlists','watchlist_symbols'].includes(table))throw Error('wrong table');
 const filters={};let q={select:(cols,opts)=>{if(cols.includes('notes')||opts.count!=='exact')throw Error('private scope');return q;},
 eq:(key,value)=>{filters[key]=value;return q;},order:()=>q,limit:()=>q,abortSignal:()=>q,
 then:(ok,no)=>{let rows;
 if(table==='portfolio_positions'){if(filters.user_id!==pOwner)throw Error('wrong owner');
 return(window.pQueryGate||Promise.resolve({data:pRows,count:pRows.length,error:null})).then(ok,no);}
 if(table==='watchlists'){if(filters.user_id!==pOwner)throw Error('wrong owner');rows=wLists.filter(r=>!filters.id||r.id===filters.id);}
 else {if(!filters.watchlist_id)throw Error('missing list');rows=wSymbols;}
 return(window.wQueryGate||Promise.resolve({data:rows,count:window.wCount===undefined?rows.length:wCount,error:null})).then(ok,no);}};return q;}};
window.MDXAuth={user:()=>pOwner?{id:pOwner}:null,client:async()=>pClient};
"""


def portfolio_start(browser, synthetic_snapshot, *, width=1440, theme='dark', language='en', mutate=None, full_shell=False, chain='oil_inflation_duration_derate'):
    import mimetypes
    from copy import deepcopy
    snapshot=deepcopy(synthetic_snapshot)
    snapshot['source']['chain']=chain
    if chain=='oil_inflation_duration_derate':
        snapshot['company_exposure']={'asof':'2026-01-01','identity_source':{'sha256':'c'*64}}
        snapshot['exposure_screens']=[{'id':'oil','label':{'en':'Oil-sensitive screen','zh':'石油敏感度筛选'},
          'status':'available','n':2,'unevaluable':0,'cuts':{},'companies':{'linked':[], 'unlinked':[]}}]
    shell=incumbent.SHELL.replace('<html lang="en" data-lang="en" data-theme="light">',
      f'<html lang="en" data-lang="{language}" data-theme="{theme}">')
    shell=shell.replace('<main class="ox-wrap"><div id="ox-root" aria-busy="true"></div></main>', '''
    <link rel="stylesheet" href="/theme.css"><link rel="stylesheet" href="/ontology.css">
    <link rel="stylesheet" href="/ontology-company.css">
    <main class="ox-wrap"><div id="ox-root" aria-busy="true"></div>
    <section id="ox-portfolio" class="ox-company"><h2><span class="l-en">Your Portfolio in this path</span><span class="l-zh">此路径中的投资组合</span></h2>
    <div class="ox-company-choices"><button type="button" data-private-kind="portfolio" aria-pressed="true">Portfolio</button>
    <button type="button" data-private-kind="watchlist" aria-pressed="false">Watchlist</button></div>
    <div class="ox-company-form"><label class="ox-company-label" data-watchlist-picker hidden>Saved Watchlist<select data-watchlist-select></select></label>
    <button type="button" class="ox-cta" data-portfolio-read disabled>Read / 读取</button>
    <button type="button" class="ox-cta secondary" data-portfolio-clear>Clear / 清除</button></div>
    <div data-portfolio-result aria-live="polite"></div></section></main>
    <script src="/portfolio_state.js"></script><script src="/watchstore.js"></script><script src="/ontology.js"></script>
    <script type="module" src="/ontology-portfolio.js"></script>''')
    # The base fixture's MDXAuth stub is overridden before any product code runs.
    shell=shell.replace('<script src="/portfolio_state.js">', '<script>'+_PORTFOLIO_AUTH+'</script><script src="/portfolio_state.js">')
    if full_shell:
        shell=(PREPARED.parent.parent/'site/ontology.html').read_text()
    ctx=browser.new_context(viewport={'width':width,'height':1000})
    page=ctx.new_page(); seen=[];errors=[]
    if full_shell:
        page.add_init_script(_PORTFOLIO_AUTH + '''
          localStorage.setItem('theme',THEME);localStorage.setItem('lang',LANG);
          pClient.auth.onAuthStateChange=fn=>{pCallbacks.push(fn);queueMicrotask(()=>fn('INITIAL_SESSION',{user:{id:pOwner,email:'fixture@example.invalid',user_metadata:{}},access_token:pToken}));return{data:{subscription:{unsubscribe(){}}}};};
        '''.replace('THEME',json.dumps(theme)).replace('LANG',json.dumps(language)))
    page.on('pageerror',lambda e:errors.append(str(e)))
    def route(r):
        path=urlsplit(r.request.url).path
        if path=='/ontology.html': r.fulfill(status=200,content_type='text/html',body=shell)
        elif full_shell and path=='/supabase.js':r.fulfill(status=200,content_type='text/javascript',body='window.supabase={createClient:()=>pClient};')
        elif path=='/api/ontology/explorer/v1': r.fulfill(status=200,content_type='application/json',body=json.dumps(snapshot))
        elif path=='/api/ontology/explorer/portfolio/v1':
            request=json.loads(r.request.post_data);seen.append({'request':request,'url':r.request.url,'method':r.request.method})
            rows=[{'index':i,'symbol':s,'security_id':'SEC:US-XNAS-'+s,'currency':'USD','channels':['oil'] if i==0 else [],
                   'state':'covered' if i==0 else 'not_in_available_screens','reason':None} for i,s in enumerate(request['symbols'])]
            result={'schema':'ontology_portfolio_identity.v1','source_manifest_hash':request['source_manifest_hash'],
              'chain':request['chain'],'membership_asof':'2026-01-01','identity_valid_on':'2026-01-04','identity_source_sha256':'c'*64,
              'rows':rows,'counts':{state:sum(x['state']==state for x in rows) for state in ['covered','not_in_available_screens','identity_unresolved','membership_unavailable']},
              'unresolved_channels':[],'meaning':'declared_screen_membership_only','pnl':None,
              'authority':{'can_rank':False,'can_gate':False,'can_size':False,'can_trade':False}}
            status=200;headers={'Content-Type':'application/json','Cache-Control':'private, no-store','Vary':'Authorization, Cookie'}
            if mutate: status,headers,result=mutate(status,headers,result)
            r.fulfill(status=status,headers=headers,body=json.dumps(result))
        else:
            # Full-shell evidence must exercise the emitted assets, including
            # the build-bound auth configuration in site/theme.js.
            src=(PREPARED.parent.parent/'site' if full_shell else PREPARED.parent)/path.lstrip('/')
            if not src.is_file():src=PREPARED.parent.parent/'site'/path.lstrip('/')
            r.fulfill(status=200,content_type=mimetypes.guess_type(src)[0] or 'text/javascript',body=src.read_bytes()) if src.is_file() else r.fulfill(status=204)
    page.route('**/*',route);page.goto(('https://www.mastermind-x.com' if full_shell else 'https://macro.example')+'/ontology.html'+('' if chain=='oil_inflation_duration_derate' else '?chain='+chain))
    try:
        page.wait_for_function("document.querySelector('[data-portfolio-result]').dataset.state==='idle'", timeout=5000)
    except Exception:
        diagnostics=page.evaluate("({portfolio:document.querySelector('[data-portfolio-result]').dataset.state,owner:window.MDXAuth?.user?.()?.id,root:document.querySelector('#ox-root').innerText,calls:pCalls})")
        ctx.close()
        raise AssertionError({'synthetic_fixture_diagnostics':diagnostics,'errors':errors}) from None
    return ctx,page,seen,errors


def portfolio_settled(page,state):
    page.wait_for_function("s=>document.querySelector('[data-portfolio-result]').dataset.state===s",arg=state,timeout=5000)


@pytest.mark.parametrize('theme,language,width',[('dark','en',1440),('light','zh',390)])
def test_dollar_native_definition_on_macro_shell_keeps_proxy_and_scenario_limits(browser,tmp_path,theme,language,width):
    from tests.ontology_explorer_fixtures import dollar_root
    from engine.ontology_explorer import compose_snapshot
    chain='dollar_spike_em_multinational'
    snapshot=compose_snapshot(dollar_root(tmp_path),chain=chain)
    ctx,page,seen,errors=portfolio_start(browser,snapshot,width=width,theme=theme,language=language,full_shell=True,chain=chain)
    try:
        assert page.locator('[data-ontology-chain][aria-current=page]').get_attribute('data-ontology-chain')==chain
        assert page.locator('#ox-steps [id^="ox-leg-"]').count()==3
        page.locator('#ox-root details').evaluate_all('nodes=>nodes.forEach(n=>n.open=true)')
        text=page.locator('#ox-root').inner_text()
        assert ('includes EM equities' if language=='en' else '包含 新兴市场股票') in text
        assert ('Observed value unavailable in this view' if language=='en' else '此视图无法显示观测值') in text
        assert ('Owner verdict: met' if language=='en' else '来源判定：已满足') in text
        assert ('Observed: not published' if language=='en' else '读数：未发布') not in text
        assert ('proxy' if language=='en' else '代理') in text
        assert ('stated assumption' if language=='en' else '明示假设') in text
        terminal=page.locator('#ox-leg-em_derate').inner_text()
        assert 'FXI' in terminal and 'SPY' in terminal and '63' in terminal
        assert ('China large-cap' if language=='en' else '中国大型股') in terminal
        assert ('not an observed cause' if language=='en' else '并非该条件中已观测到的原因') in page.locator('#ox-leg-dollar_spike').inner_text()
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='path_unavailable'")
        assert page.locator('#ox-scenario [type=submit]').is_disabled()
        page.locator('#ox-scenario [name=magnitude]').fill('12')
        page.locator('#ox-scenario button[type=button]').click()
        page.evaluate("window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{event:'TOKEN_REFRESHED',user:{id:pOwner}}}))")
        assert page.locator('[data-scenario-result]').get_attribute('data-state')=='path_unavailable'
        assert ('observed reading' if language=='en' else '观测读数') in page.locator('[data-scenario-result]').inner_text()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert not errors and seen==[] and page.evaluate('pCalls.queries')==0
    finally:ctx.close()


@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('language',['en','zh'])
@pytest.mark.parametrize('width',[390,1440])
def test_portfolio_private_macro_read_with_explicit_membership_and_weights(browser,synthetic_snapshot,theme,language,width):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot,width=width,theme=theme,language=language)
    try:
        assert page.evaluate('pCalls.queries')==0 and seen==[]
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        assert len(seen)==1 and seen[0]['method']=='POST'
        assert set(seen[0]['request'])=={'schema','chain','source_manifest_hash','symbols'}
        assert seen[0]['request']['symbols']==['AAA','BBB']
        assert seen[0]['url'].endswith('/portfolio/v1') and '?' not in seen[0]['url']
        text=page.locator('[data-portfolio-result]').inner_text()
        assert '60.00%' in text and '40.00%' in text and 'USD' in text
        assert 'AAA' in text and 'BBB' in text and '2026-01-01' in text
        assert ('entry-cost' if language=='en' else '建仓成本') in text
        assert ('not current market' if language=='en' else '并非当前市值') in text
        assert ('1 matched; 1 outside' if language=='en' else '1 个匹配；1 个不在') in text
        assert page.evaluate('[localStorage.length,sessionStorage.length]')==[0,0]
        assert page.url=='https://macro.example/ontology.html'
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert page.locator('[data-portfolio-read]').bounding_box()['height']>=44
        assert errors==[]
        page.locator('[data-portfolio-clear]').click();portfolio_settled(page,'idle')
        assert page.locator('.ox-portfolio-row').count()==0 and len(seen)==1
    finally: ctx.close()


@pytest.mark.parametrize('change',["pOwner=null;window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:null,event:'SIGNED_OUT'}}));",
  "pOwner='owner-b';pCallbacks.forEach(fn=>fn('SIGNED_IN',{user:{id:pOwner}}));",
  "window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}));",
  "document.querySelector('#ox-portfolio').dispatchEvent(new CustomEvent('ontology-source-changed'));",])
def test_portfolio_late_cloud_read_cannot_repaint_after_owner_or_source_change(browser,synthetic_snapshot,change):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.evaluate('()=>{pQueryGate=new Promise(resolve=>window.finishPortfolio=resolve);}')
        page.locator('[data-portfolio-read]').click();page.wait_for_function('pCalls.queries===1')
        page.evaluate(change)
        page.evaluate('finishPortfolio({data:pRows,count:pRows.length,error:null})')
        page.evaluate('()=>new Promise(r=>setTimeout(r,20))')
        assert page.locator('.ox-portfolio-row').count()==0 and seen==[] and errors==[]
    finally:ctx.close()


def test_portfolio_same_owner_token_change_clears_without_stranding_selected_path(browser,synthetic_snapshot):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        page.evaluate("pToken='rotated';pCallbacks.forEach(fn=>fn('TOKEN_REFRESHED',{user:{id:pOwner}}))")
        portfolio_settled(page,'idle');assert page.locator('.ox-portfolio-row').count()==0
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        assert len(seen)==2 and errors==[]
    finally:ctx.close()


@pytest.mark.parametrize('mutation',[
  lambda s,h,v:(s,h,{**v,'source_manifest_hash':'sha256:'+'f'*64}),
  lambda s,h,v:(s,h,{**v,'pnl':123}),
  lambda s,h,v:(s,h,{**v,'authority':{**v['authority'],'can_trade':True}}),
  lambda s,h,v:(s,{**h,'Cache-Control':'public, max-age=60'},v),
  lambda s,h,v:(s,h,{**v,'rows':list(reversed(v['rows']))}),
  lambda s,h,v:(s,h,{**v,'counts':{**v['counts'],'covered':3}}),
])
def test_portfolio_refuses_unbound_or_public_membership(browser,synthetic_snapshot,mutation):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot,mutate=mutation)
    try:
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'unavailable')
        assert page.locator('.ox-portfolio-row').count()==0 and len(seen)==1 and errors==[]
    finally:ctx.close()


@pytest.mark.parametrize('setup,state',[("pRows=[]",'empty'),("pQueryGate=Promise.resolve({data:[],count:null,error:null})",'unavailable')])
def test_portfolio_cloud_empty_is_not_an_unknown_book(browser,synthetic_snapshot,setup,state):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.evaluate('()=>{'+setup+';}');page.locator('[data-portfolio-read]').click();portfolio_settled(page,state)
        assert seen==[] and errors==[]
    finally:ctx.close()


@pytest.mark.parametrize('setup,has_weights',[
  ("pRows[0].shares=null",False),
  ("pRows.forEach(r=>r.shares=null)",True),
  ("pRows[1].ticker='AAA'",False),
  ("pRows[0].shares=1e308;pRows[0].entry_price=1e308",False),
  ("pRows[0].shares=-2",False),
])
def test_portfolio_reuses_owner_weighting_and_refuses_incomplete_or_overflow_books(browser,synthetic_snapshot,setup,has_weights):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.evaluate('()=>{'+setup+';}');page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        text=page.locator('.ox-portfolio-rows').inner_text()
        assert ('%' in text)==has_weights
        if has_weights:assert '50.00%' in text and 'equal weights assumed' in page.locator('[data-portfolio-result]').inner_text()
        assert errors==[]
    finally:ctx.close()


def test_portfolio_displays_bounded_pages_without_refetch_or_partial_weights(browser,synthetic_snapshot):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.evaluate("pRows=Array.from({length:25},(_,i)=>({...pRows[0],id:'lot'+i,ticker:'T'+i,shares:null}))")
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        assert page.locator('.ox-portfolio-row').count()==20
        assert '4.00%' in page.locator('.ox-portfolio-rows').inner_text()
        page.locator('.ox-portfolio-rows + button').click()
        assert page.locator('.ox-portfolio-row').count()==25
        assert page.locator('.ox-portfolio-rows + button').is_hidden()
        assert len(seen)==1 and page.evaluate('pCalls.queries')==1 and errors==[]
    finally:ctx.close()


def test_portfolio_identity_unknown_refuses_whole_book_weights(browser,synthetic_snapshot):
    def unknown(s,h,v):
        v['rows'][1].update(security_id=None,currency=None,state='identity_unresolved')
        v['counts'].update(not_in_available_screens=0,identity_unresolved=1)
        return s,h,v
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot,mutate=unknown)
    try:
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        assert 'BBB' in page.locator('.ox-portfolio-rows').inner_text()
        assert '%' not in page.locator('.ox-portfolio-rows').inner_text()
        assert 'Security identity unresolved' in page.locator('.ox-portfolio-rows').inner_text()
        assert errors==[]
    finally:ctx.close()


def test_portfolio_never_sums_weights_across_currencies(browser,synthetic_snapshot):
    def two_books(s,h,v):
        for r in v['rows'][2:]:r['currency']='CAD'
        return s,h,v
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot,mutate=two_books)
    try:
        page.evaluate("pRows.push({...pRows[0],id:'c',ticker:'CCC'},{...pRows[1],id:'d',ticker:'DDD'})")
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        rows=page.locator('.ox-portfolio-row')
        assert '60.00% within USD' in rows.nth(0).inner_text()
        assert '40.00% within USD' in rows.nth(1).inner_text()
        assert '60.00% within CAD' in rows.nth(2).inner_text()
        assert '40.00% within CAD' in rows.nth(3).inner_text()
        assert errors==[]
    finally:ctx.close()


def test_portfolio_missed_final_auth_event_cannot_publish_previous_book(browser,synthetic_snapshot):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.evaluate("""()=>{const original=window.fetch;
          window.fetch=async(...a)=>{const result=await original(...a);if(String(a[0]).endsWith('/portfolio/v1'))window.pReply=true;return result;};
          pSessionHook=async()=>{if(window.pReply)pOwner=null;return{data:{session:{user:{id:'owner-a'},access_token:pToken}}};};}""")
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'signed_out')
        assert page.locator('.ox-portfolio-row').count()==0 and len(seen)==1 and errors==[]
    finally:ctx.close()


@pytest.mark.parametrize('width',[390,1440])
def test_portfolio_full_macro_shell_uses_actual_owner_without_sync_enrollment(browser,synthetic_snapshot,width):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot,width=width,full_shell=True)
    try:
        assert page.evaluate('pCalls.queries')==0
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        assert page.locator('.ox-portfolio-row').count()==2
        assert len(seen)==1 and page.evaluate('pCalls.queries')==1
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert errors==[]
    finally:ctx.close()


@pytest.mark.parametrize('width,language', [(1440,'en'),(390,'zh')])
def test_watchlist_explicit_read_reuses_membership_without_weights_or_writes(browser,synthetic_snapshot,width,language):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot,width=width,language=language,full_shell=True)
    try:
        page.locator('[data-private-kind=watchlist]').click()
        assert page.evaluate('pCalls.queries')==0 and seen==[]
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'choose_list')
        assert page.evaluate('pCalls.tables')==['watchlists'] and seen==[]
        assert 'Energy <private>' in page.locator('[data-watchlist-select]').inner_text()
        page.locator('[data-watchlist-select]').select_option('wl-a')
        assert page.evaluate('pCalls.queries')==1
        page.evaluate("()=>{PS.computeSnapshot=()=>{throw Error('watchlist must not calculate weights')};}")
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,'ready')
        assert page.evaluate('pCalls.tables')==['watchlists','watchlists','watchlist_symbols']
        assert len(seen)==1 and seen[0]['request']['symbols']==['AAA','BBB']
        assert set(seen[0]['request'])=={'schema','chain','source_manifest_hash','symbols'}
        assert page.locator('.ox-portfolio-row').count()==2
        assert '%' not in page.locator('.ox-portfolio-rows').inner_text()
        assert ('not a holding' if language=='en' else '并非持仓') in page.locator('[data-portfolio-result]').inner_text()
        assert page.locator('[data-portfolio-result] private').count()==0
        assert page.evaluate('pCalls.writes')==0 and errors==[]
        assert '?' not in page.url and page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('[data-private-kind=portfolio]').click();portfolio_settled(page,'idle')
        assert page.locator('[data-watchlist-select] option').count()==0
        assert page.locator('.ox-portfolio-row').count()==0 and len(seen)==1
    finally:ctx.close()


@pytest.mark.parametrize('phase,change',[
  ('enumerate', "pOwner='other';pCallbacks.forEach(fn=>fn('SIGNED_IN',{user:{id:pOwner}}))"),
  ('enumerate', "document.querySelector('[data-private-kind=portfolio]').click()"),
  ('members', "window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))"),
  ('members', "document.querySelector('#ox-portfolio').dispatchEvent(new CustomEvent('ontology-source-changed'))"),
])
def test_watchlist_late_reads_cannot_repopulate_private_names_or_rows(browser,synthetic_snapshot,phase,change):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.locator('[data-private-kind=watchlist]').click()
        if phase=='members':
            page.locator('[data-portfolio-read]').click();portfolio_settled(page,'choose_list')
            page.locator('[data-watchlist-select]').select_option('wl-a')
        page.evaluate('()=>{window.wQueryGate=new Promise(resolve=>window.finishWatch=resolve);}')
        before=page.evaluate('pCalls.queries');page.locator('[data-portfolio-read]').click()
        page.wait_for_function('n=>pCalls.queries>n',arg=before)
        page.evaluate(change);page.evaluate('finishWatch({data:wLists,count:wLists.length,error:null})')
        page.evaluate('()=>new Promise(r=>setTimeout(r,20))')
        assert page.locator('[data-watchlist-select] option').count()==0
        assert page.locator('.ox-portfolio-row').count()==0 and seen==[] and errors==[]
    finally:ctx.close()


@pytest.mark.parametrize('setup,state',[("wLists=[]",'empty_lists'),("wLists[0].user_id='other'",'unavailable'),("wCount=2",'unavailable')])
def test_watchlist_empty_is_distinct_from_private_or_truncated_read(browser,synthetic_snapshot,setup,state):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot)
    try:
        page.evaluate(setup);page.locator('[data-private-kind=watchlist]').click()
        page.locator('[data-portfolio-read]').click();portfolio_settled(page,state)
        assert page.locator('[data-watchlist-select] option').count()==0 and seen==[] and errors==[]
    finally:ctx.close()


@pytest.mark.parametrize('width',[390,1440])
def test_scenario_full_macro_shell_binds_selected_source_and_clears_private_inputs(browser,synthetic_snapshot,width):
    ctx,page,seen,errors=portfolio_start(browser,synthetic_snapshot,width=width,full_shell=True)
    calls=[]
    def refusal(r):
        calls.append(json.loads(r.request.post_data))
        r.fulfill(status=503,headers={'Content-Type':'application/json','Cache-Control':'private, no-store','Vary':'Authorization, Cookie'},
          body=json.dumps({'detail':{'schema':'ontology_explorer_error.v1','code':'source_unavailable'}}))
    try:
        page.route('**/api/ontology/explorer/scenario/v1',refusal)
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='idle'")
        assert calls==[] and seen==[] and page.evaluate('pCalls.queries')==0
        page.locator('[data-scenario-form] [name=magnitude]').fill('30')
        page.locator('[data-scenario-form] [type=submit]').click()
        page.wait_for_function("document.querySelector('[data-scenario-result]').dataset.state==='unavailable'")
        assert len(calls)==1 and set(calls[0])=={'schema','source_manifest_hash','assumption'}
        assert calls[0]['assumption']['magnitude']==30
        page.evaluate("window.dispatchEvent(new PageTransitionEvent('pagehide',{persisted:true}))")
        assert page.locator('[data-scenario-form] [name=magnitude]').input_value()==''
        assert page.locator('[data-scenario-result]').get_attribute('data-state')=='no_reading'
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth') and errors==[]
    finally:ctx.close()
