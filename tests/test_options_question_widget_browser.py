"""Actual singleton browser proof, inert same-page HTTP only; no source/provider access."""
import json
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[1]
REF={"schema":"options.selection_question/v1","evidence":{"owner":"options_evidence","object_type":"options_matrix_selection","object_id":"v1/SPY/test","mode":"pinned","version_ref":"sha256:"+"a"*64,"fingerprint":"a"*64},"selection":'{"schema":"options_matrix_selection.v1"}'}
@pytest.mark.parametrize('width,height',[(1440,900),(820,1180),(390,844)])
@pytest.mark.parametrize('lang,theme',[("en","dark"),("en","light"),("zh","dark"),("zh","light")])
def test_exact_question_widget(width,height,lang,theme):
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":width,"height":height},reduced_motion='reduce')
        page=context.new_page(); errors=[]; page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('http://options-widget.test/',lambda r:r.fulfill(content_type='text/html',body=f'<html data-lang="{lang}" data-theme="{theme}"><body></body></html>'))
        page.goto('http://options-widget.test/')
        page.evaluate('''() => {
          window.MM_BRAIN_CFG={principal:'fixture-principal',api:'',anchor:'top'};
          window.MDXAuth={onChange:fn=>fn({id:'fixture-principal'}),client:()=>Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session:{access_token:'inert-fixture',user:{id:'fixture-principal'}}}})}})};
          window.__posts=[];
          window.fetch=async (url,opts={}) => {
            if(opts.method==='POST') {
              window.__posts.push(JSON.parse(opts.body));
              return new Response('data: {"type":"meta","thread_id":null}\\n\\ndata: {"type":"delta","text":"Fixture answer"}\\n\\ndata: {"type":"done","ok":true}\\n\\n',{headers:{'content-type':'text/event-stream'}});
            }
            return new Response(JSON.stringify(url.endsWith('/me')?{tier:'pro',quotas:{fast:{limit:-1},pro:{limit:-1}}}:{threads:[],runs:[]}));
          };
        }''')
        page.add_script_tag(path=str(ROOT/'templates/mm_brain.js'))
        assert page.evaluate('(r)=>MMBrain.submitOptionsQuestion(r)',REF) is True
        expect(page.locator('#mmb-optq')).to_be_visible()
        expect(page.locator('#mmb-optq')).to_contain_text('所选合约' if lang=='zh' else 'selected contracts')
        assert page.evaluate('window.__posts.length')==0
        textarea=page.locator('textarea'); textarea.fill('Explain the selected contracts'); textarea.press('Control+Enter')
        expect(page.locator('.mmb-msg.assistant')).to_contain_text('Fixture answer')
        assert page.evaluate('window.__posts.length')==1
        body=page.evaluate('window.__posts[0]')
        assert body['options_question_reference']==REF
        assert sorted(body)==['context','lane','message','mode','options_question_reference']
        assert body['context']=={'lang':lang}
        expect(page.locator('.mmb-msg.assistant .mmb-regen')).to_have_count(0)
        textarea.fill('Do not fall back');textarea.press('Control+Enter');page.wait_for_timeout(50)
        assert page.evaluate('window.__posts.length')==1
        assert page.evaluate('localStorage.length')==0
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#mmb-optq-exit').click()
        expect(page.locator('.mmb-msg.assistant')).to_contain_text('Fixture answer')
        textarea.fill('A separate ordinary question');textarea.press('Control+Enter')
        page.wait_for_function('window.__posts.length===2')
        ordinary=page.evaluate('window.__posts[1]')
        assert 'options_question_reference' not in ordinary
        assert 'thread_id' not in ordinary
        assert errors==[]
        context.close();browser.close()


@pytest.fixture
def review_page():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":900})
        page.route('http://options-widget.test/',lambda r:r.fulfill(content_type='text/html',body='<html data-lang="en" data-theme="dark"><body></body></html>'))
        page.goto('http://options-widget.test/')
        page.evaluate("""() => {
          window.MM_BRAIN_CFG={principal:'fixture-principal',api:'',anchor:'top'};
          window.__session={access_token:'inert-fixture',user:{id:'fixture-principal'}};
          window.MDXAuth={onChange:fn=>fn({id:'fixture-principal'}),client:()=>Promise.resolve({auth:{getSession:()=>window.__authFails?Promise.reject(Error('fixture')):Promise.resolve({data:{session:window.__session}})}})};
          window.__posts=[];window.__reads=[];
          window.fetch=async(url,opts={})=>{
            if(opts.method==='POST'){window.__posts.push(JSON.parse(opts.body));window.__lastHeaders=opts.headers;return new Response('data: {"type":"delta","text":"Fixture answer"}\\n\\ndata: {"type":"done"}\\n\\n');}
            window.__reads.push(url);
            if(String(url).includes('/runs/'))return new Promise(r=>window.__resolveRun=r);
            return new Response(JSON.stringify(String(url).endsWith('/me')?{tier:'pro',quotas:{fast:{limit:-1},pro:{limit:-1}}}:{threads:[],runs:[]}));
          };
        }""")
        page.add_script_tag(path=str(ROOT/'templates/mm_brain.js'))
        yield page
        browser.close()

@pytest.mark.parametrize('failure',['foreign','missing','token','rejected'])
def test_review_actual_session_must_match_staged_principal(review_page,failure):
    page=review_page
    assert page.evaluate('(r)=>MMBrain.submitOptionsQuestion(r)',REF)
    page.evaluate("""f=>{if(f==='foreign')window.__session.user.id='other-user';
      if(f==='missing')window.__session=null;if(f==='token')window.__session.access_token='';if(f==='rejected')window.__authFails=true;}""",failure)
    page.locator('textarea').fill('No cross-account disclosure');page.locator('textarea').press('Control+Enter')
    expect(page.locator('.mmb-scroll')).to_contain_text('request outcome could not be confirmed')
    assert page.evaluate('window.__posts.length')==0
    expect(page.locator('#mmb-optq')).to_be_visible()


def test_review_actual_pending_resume_cannot_replace_staged_question(review_page):
    page=review_page
    page.evaluate("""()=>{sessionStorage.setItem('mm.brain.run.v2:user:fixture-principal',JSON.stringify({id:'old-run',ts:Date.now(),q:'ordinary private question'}));MMBrain.open();}""")
    page.wait_for_function('typeof window.__resolveRun==="function"')
    assert page.evaluate('(r)=>MMBrain.submitOptionsQuestion(r)',REF)
    page.evaluate("""()=>{window.__resolveRun(new Response(JSON.stringify({thread_id:'old-thread',done:false})));document.dispatchEvent(new Event('visibilitychange'));}""")
    page.wait_for_timeout(60)
    expect(page.locator('#mmb-optq')).to_be_visible()
    assert page.evaluate('window.__reads.filter(x=>x.includes("/threads/old-thread")).length')==0
    assert page.evaluate('window.__reads.filter(x=>x.includes("/runs/")).length')==1
    assert page.evaluate('window.__posts.length')==0


@pytest.mark.parametrize('decision',['match','foreign','missing','rejected'])
def test_terminal_cookie_proxy_requires_explicit_current_account(review_page,decision):
    page=review_page
    page.evaluate("""d=>{delete window.MDXAuth; window.__expectedOwners=[];
      if(d!=='missing')window.MM_BRAIN_CFG.authorizeOptionsQuestion=owner=>{window.__expectedOwners.push(owner);return d==='rejected'?Promise.reject(Error('offline')):Promise.resolve(d==='match');};
    }""",decision)
    assert page.evaluate('(r)=>MMBrain.submitOptionsQuestion(r)',REF)
    page.locator('textarea').fill('Exact cookie session');page.locator('textarea').press('Control+Enter')
    if decision=='match':
        expect(page.locator('.mmb-msg.assistant')).to_contain_text('Fixture answer')
        assert page.evaluate('window.__posts.length')==1
        assert page.evaluate('window.__lastHeaders')=={'Content-Type':'application/json','X-MM-Options-Principal':'fixture-principal'}
    else:
        expect(page.locator('.mmb-scroll')).to_contain_text('request outcome could not be confirmed')
        assert page.evaluate('window.__posts.length')==0
    assert page.evaluate('window.__expectedOwners')==([] if decision=='missing' else ['fixture-principal'])


@pytest.mark.parametrize('settlement',['reply','network'])
def test_exact_inflight_withdrawal_fences_late_paint_and_releases_busy(review_page,settlement):
    page=review_page
    page.evaluate("""() => {
      const previous=window.fetch;
      window.fetch=(url,opts={})=>{
        if(opts.method!=='POST')return previous(url,opts);
        window.__posts.push(JSON.parse(opts.body));
        return new Promise((resolve,reject)=>{window.__finishQuestion=resolve;window.__failQuestion=reject;});
      };
    }""")
    assert page.evaluate('(r)=>MMBrain.submitOptionsQuestion(r)',REF)
    page.locator('textarea').fill('Original selected contract')
    page.locator('textarea').press('Control+Enter')
    page.wait_for_function('window.__posts.length===1')
    foreign=dict(REF,selection='foreign-selection')
    assert page.evaluate('(r)=>MMBrain.clearOptionsQuestion(r)',foreign) is False
    assert page.evaluate('(r)=>MMBrain.clearOptionsQuestion(r)',REF) is True
    assert page.evaluate('(r)=>MMBrain.submitOptionsQuestion(r)',foreign) is False
    expect(page.locator('#mmb-optq-exit')).to_be_disabled()
    expect(page.locator('.mmb-scroll')).not_to_contain_text('nothing was sent')
    if settlement=='reply':
        page.evaluate("""()=>window.__finishQuestion(new Response('data: {"type":"delta","text":"STALE PRIVATE ANSWER"}\\n\\ndata: {"type":"done"}\\n\\n'))""")
    else:
        page.evaluate("()=>window.__failQuestion(Error('inert transport failure'))")
    expect(page.locator('#mmb-optq-exit')).to_be_enabled()
    expect(page.locator('.mmb-msg.assistant')).to_have_count(0)
    expect(page.locator('.mmb-scroll')).not_to_contain_text('nothing was sent')
    expect(page.locator('.mmb-scroll')).not_to_contain_text('request outcome could not be confirmed')
    assert page.evaluate('window.__posts.length')==1
    assert page.evaluate('(r)=>MMBrain.submitOptionsQuestion(r)',foreign) is True
    assert page.evaluate('(r)=>MMBrain.clearOptionsQuestion(r)',REF) is False
    expect(page.locator('#mmb-optq')).to_be_visible()
