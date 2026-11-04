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
        assert errors==[]
        context.close();browser.close()
