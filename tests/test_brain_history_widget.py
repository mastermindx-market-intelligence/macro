from pathlib import Path
import pytest
import os
try:
    from playwright.sync_api import sync_playwright, expect
except ImportError:
    if os.environ.get("MM_REQUIRE_BROWSER") == "1":
        pytest.fail("Playwright is required for this proof")
    pytest.skip("Playwright unavailable", allow_module_level=True)
ROOT=Path(__file__).resolve().parents[1]
A="11111111-1111-1111-1111-111111111111"
B="22222222-2222-2222-2222-222222222222"
@pytest.fixture
def page():
    with sync_playwright() as p:
        try:
            browser=p.chromium.launch(headless=True)
        except Exception as error:
            if os.environ.get("MM_REQUIRE_BROWSER") == "1":
                pytest.fail(str(error))
            pytest.skip("Chromium unavailable")
        context=browser.new_context(viewport={"width":1440,"height":900},reduced_motion="reduce")
        page=context.new_page()
        page.route("http://history.test/",lambda route:route.fulfill(content_type="text/html",body="<!doctype html><html data-lang='en'><head></head><body></body></html>"))
        page.goto("http://history.test/")
        page.evaluate("""() => {
          window.MDXAuth={onChange:fn=>{window.__onAuth=fn;fn({id:'user-A'});}};
          window.MM_BRAIN_CFG={api:'',anchor:'top',page:'terminal'};
          window.__requests=[];window.__listFails=false;window.__principal="A";window.__listStatus=503;
          window.fetch=(url,opts={})=>{
            window.__requests.push({url,method:opts.method||'GET'});
            let status=200,body={};
            if(url.endsWith('/me'))body={tier:'pro',quotas:{fast:{limit:-1},pro:{limit:-1}},exact_source_kinds:['macro_history_observation.v1']};
            else if(url.endsWith('/threads')){
              status=window.__listFails?window.__listStatus:200;
              body=window.__listFails?{detail:'research history temporarily unavailable'}:{threads:[
                {id:'11111111-1111-1111-1111-111111111111',title:'Retained investigation A',lane:'fast',updated_at:'2026-10-05T00:00:00Z'},
                {id:'22222222-2222-2222-2222-222222222222',title:'Retained investigation B',lane:'fast',updated_at:'2026-10-05T00:00:00Z'}]};
              if(window.__principal==='B')body={threads:[]};
              if(window.__badList!==undefined)body={threads:window.__badList};
              if(window.__holdList)return new Promise(resolve=>{window.__resolveList=()=>resolve({ok:true,status:200,json:()=>Promise.resolve(body)});});
            } else if(url.endsWith('/11111111-1111-1111-1111-111111111111')){
              body={thread:{id:'11111111-1111-1111-1111-111111111111'},messages:[{role:'assistant',content:'Exact retained answer A'}]};
            } else if(url.endsWith('/22222222-2222-2222-2222-222222222222')){
              status=503;body={detail:'research history temporarily unavailable'};
              if(window.__badB){status=200;body={thread:{id:'22222222-2222-2222-2222-222222222222'},messages:[null]};}
              if(window.__delayB)return new Promise(resolve=>{window.__resolveB=()=>resolve({ok:true,status:200,json:()=>Promise.resolve({thread:{id:'22222222-2222-2222-2222-222222222222'},messages:[{role:'assistant',content:'Delayed retained answer B'}]})});});
            }
            return Promise.resolve({ok:status===200,status,json:()=>Promise.resolve(body)});
          };
        }""")
        page.add_script_tag(path=str(ROOT/'templates/mm_brain.js'))
        page.evaluate("MMBrain.open(); MMBrain.expand();")
        expect(page.locator('#mmb-tlist')).to_contain_text('Retained investigation A')
        yield page
        context.close();browser.close()

def test_failed_list_does_not_erase_last_good_rows(page):
    page.evaluate("window.__listFails=true;MMBrain.close();MMBrain.open();")
    expect(page.locator('#mmb-tlist')).to_contain_text('temporarily unavailable')
    expect(page.locator('#mmb-tlist')).to_contain_text('Retained investigation A')
    assert all(r['method']=='GET' for r in page.evaluate('window.__requests'))

def test_failed_detail_does_not_relabel_old_answer_as_target_thread(page):
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    expect(page.locator('.mmb-msg')).to_contain_text('Exact retained answer A')
    page.locator(f'.mmb-ti[data-id="{B}"] .mmb-ti-body').click()
    expect(page.locator('.mmb-ti.on')).to_have_attribute('data-id',A)
    assert all(r['method']=='GET' for r in page.evaluate('window.__requests'))


def test_retry_recovers_last_good_list_without_writes(page):
    page.evaluate("window.__listFails=true;MMBrain.close();MMBrain.open();")
    expect(page.locator('[data-act="history-retry"]')).to_be_visible()
    page.evaluate("window.__listFails=false")
    page.locator('[data-act="side"][title="Chats"]').click()
    page.locator('[data-act="history-retry"]').click()
    expect(page.locator('[data-act="history-retry"]')).to_have_count(0)
    expect(page.locator('#mmb-tlist')).to_contain_text('Retained investigation A')
    assert all(r['method']=='GET' for r in page.evaluate('window.__requests'))


def test_late_detail_cannot_replace_a_new_chat(page):
    page.evaluate("window.__delayB=true")
    page.locator(f'.mmb-ti[data-id="{B}"] .mmb-ti-body').click()
    page.wait_for_function('!!window.__resolveB')
    page.locator('[data-act="new"]:visible').first.click()
    page.evaluate('window.__resolveB()')
    page.wait_for_timeout(80)
    expect(page.locator('.mmb-ti.on')).to_have_count(0)
    expect(page.locator('.mmb-msg')).to_have_count(0)


def test_latest_history_selection_wins_over_late_detail(page):
    page.evaluate("window.__delayB=true")
    page.locator(f'.mmb-ti[data-id="{B}"] .mmb-ti-body').click()
    page.wait_for_function('!!window.__resolveB')
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    expect(page.locator('.mmb-msg')).to_contain_text('Exact retained answer A')
    page.evaluate('window.__resolveB()')
    page.wait_for_timeout(80)
    expect(page.locator('.mmb-ti.on')).to_have_attribute('data-id',A)
    expect(page.locator('.mmb-msg')).to_contain_text('Exact retained answer A')


def test_previous_principals_late_list_cannot_repopulate_history(page):
    page.evaluate('window.__holdList=true;MMBrain.close();MMBrain.open();')
    page.wait_for_function('!!window.__resolveList')
    page.evaluate("window.__oldList=window.__resolveList;window.__holdList=false;window.__principal='B';window.__onAuth({id:'user-B'});")
    expect(page.locator('.mmb-ti')).to_have_count(0)
    page.evaluate('window.__oldList()')
    page.wait_for_timeout(80)
    expect(page.locator('.mmb-ti')).to_have_count(0)
    expect(page.locator('.mmb-msg')).to_have_count(0)


def test_malformed_detail_does_not_replace_current_history(page):
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    expect(page.locator('.mmb-msg')).to_contain_text('Exact retained answer A')
    page.evaluate('window.__badB=true')
    page.locator(f'.mmb-ti[data-id="{B}"] .mmb-ti-body').click()
    expect(page.locator('.mmb-history-error')).to_be_visible()
    expect(page.locator('.mmb-ti.on')).to_have_attribute('data-id',A)
    expect(page.locator('.mmb-msg')).to_contain_text('Exact retained answer A')


@pytest.mark.parametrize('status',[401,403])
def test_denied_list_clears_cached_thread_titles(page,status):
    page.evaluate('(status)=>{window.__listStatus=status;window.__listFails=true;MMBrain.close();MMBrain.open();}',status)
    expect(page.locator('[data-act="history-retry"]')).to_be_visible()
    expect(page.locator('.mmb-ti')).to_have_count(0)


@pytest.mark.parametrize('width,height,lang',[(1440,900,'en'),(1440,900,'zh'),(820,1180,'en'),(820,1180,'zh'),(390,844,'en'),(390,844,'zh'),(320,844,'en'),(320,844,'zh')])
def test_history_outage_responsive_keyboard_and_touch(page,width,height,lang):
    page.set_viewport_size({'width':width,'height':height})
    page.evaluate("lang=>{document.documentElement.dataset.lang=lang;document.dispatchEvent(new Event('langchange'));window.__listFails=true;MMBrain.close();MMBrain.open();}",lang)
    chat=page.locator('[data-act="side"][title="Chats"]')
    if chat.is_visible():chat.click()
    retry=page.locator('[data-act="history-retry"]')
    expect(retry).to_be_visible()
    if width==320:
        page.evaluate("""() => {
          const nodes=Array.from(document.querySelectorAll('#mmb-root *')).filter(n=>n.namespaceURI==='http://www.w3.org/1999/xhtml');
          const sizes=nodes.map(n=>parseFloat(getComputedStyle(n).fontSize));
          nodes.forEach((n,i)=>{if(sizes[i])n.style.fontSize=(sizes[i]*2)+'px';});
        }""")
    expect(page.locator('#mmb-tlist [role="status"]')).to_contain_text('暂时不可用' if lang=='zh' else 'temporarily unavailable')
    retry.click(trial=True)  # wait for the real sidebar transition and hit target
    box=retry.bounding_box();assert box and box['width']>=44 and box['height']>=44
    assert box['x']>=0 and box['x']+box['width']<=width
    assert retry.evaluate('(node)=>{const b=node.getBoundingClientRect();const hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return node===hit||node.contains(hit);}')
    proof=os.environ.get('MM_BRAIN_HISTORY_PROOF_DIR')
    if proof:
        folder=Path(proof);folder.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(folder/f'{width}-{lang}-history-unavailable.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    retry.focus();expect(retry).to_be_focused()
    page.evaluate('window.__listFails=false')
    retry.press('Enter')
    expect(retry).to_have_count(0)
    expect(page.locator('#mmb-tlist')).to_contain_text('Retained investigation A')
    assert all(r['method']=='GET' for r in page.evaluate('window.__requests'))


@pytest.mark.parametrize('bad',[[None],[{}],[{'id':A,'title':{'bad':'shape'},'lane':'fast'}]])
def test_malformed_list_keeps_previous_successful_history(page,bad):
    page.evaluate('(bad)=>{window.__badList=bad;MMBrain.close();MMBrain.open();}',bad)
    expect(page.locator('#mmb-tlist [role="status"]')).to_contain_text('temporarily unavailable')
    expect(page.locator('#mmb-tlist')).to_contain_text('Retained investigation A')


def test_drafts_are_partitioned_across_account_switch(page):
    page.locator('#mmb-ta').fill('Private draft A')
    page.wait_for_function("localStorage.getItem('mmb_draft_v2:user-A:new')==='Private draft A'")
    page.evaluate("window.__principal='B';window.__onAuth({id:'user-B'});MMBrain.close();MMBrain.open();")
    expect(page.locator('#mmb-ta')).to_have_value('')
    page.locator('#mmb-ta').fill('Private draft B')
    page.wait_for_function("localStorage.getItem('mmb_draft_v2:user-B:new')==='Private draft B'")
    page.evaluate("window.__principal='A';window.__onAuth({id:'user-A'});MMBrain.close();MMBrain.open();")
    expect(page.locator('#mmb-ta')).to_have_value('Private draft A')


def test_unbound_legacy_draft_is_not_restored(page):
    page.evaluate("localStorage.setItem('mmb_draft_new','Unknown prior owner');MMBrain.close();MMBrain.open();")
    expect(page.locator('#mmb-ta')).to_have_value('')


def test_pending_draft_is_bound_before_thread_switch(page):
    page.locator('#mmb-ta').fill('New-thread draft')
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    page.wait_for_timeout(450)
    page.locator('[data-act="new"]:visible').first.click()
    expect(page.locator('#mmb-ta')).to_have_value('New-thread draft')


def test_terminal_principal_entry_clears_previous_account(page):
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    expect(page.locator('.mmb-msg')).to_contain_text('Exact retained answer A')
    page.evaluate("window.__principal='B';MMBrain.setPrincipal('user-B')")
    expect(page.locator('.mmb-msg')).to_have_count(0)
    expect(page.locator('.mmb-ti')).to_have_count(0)


def test_unbound_legacy_run_is_not_resumed(page):
    page.evaluate("sessionStorage.setItem('mm.brain.run',JSON.stringify({id:'legacy-run',q:'Prior account question',ts:Date.now()}));MMBrain.close();MMBrain.open();")
    page.wait_for_timeout(80)
    assert not any('legacy-run' in r['url'] for r in page.evaluate('window.__requests'))
    expect(page.locator('#mmb-scroll')).not_to_contain_text('Prior account question')


def test_late_run_status_cannot_restore_previous_principal_question(page):
    page.evaluate("""() => {
      sessionStorage.setItem('mm.brain.run.v2:user:user-A',JSON.stringify({id:'retained-run',q:'Private question A',ts:Date.now()}));
      const original=window.fetch;window.fetch=(url,opts)=>url.endsWith('/runs/retained-run')?new Promise(resolve=>{window.__runStatus=resolve;}):original(url,opts);
      MMBrain.close();MMBrain.open();
    }""")
    page.wait_for_function('!!window.__runStatus')
    page.evaluate("window.__principal='B';MMBrain.setPrincipal('user-B');window.__runStatus({ok:true,json:()=>Promise.resolve({done:false})});")
    page.wait_for_timeout(80)
    expect(page.locator('#mmb-scroll')).not_to_contain_text('Private question A')
    expect(page.locator('.mmb-msg')).to_have_count(0)


def test_account_switch_before_auth_resolution_cannot_submit_old_prompt(page):
    page.evaluate("""() => {
      let first=true;window.MDXAuth.client=()=>{if(first){first=false;return new Promise(r=>window.__authClient=r);}return Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session:null}})}});};
    }""")
    page.locator('#mmb-ta').fill('Private unsent question A')
    page.locator('#mmb-send').click()
    page.wait_for_function('!!window.__authClient')
    page.evaluate("window.__principal='B';MMBrain.setPrincipal('user-B');window.__authClient({auth:{getSession:()=>Promise.resolve({data:{session:null}})}})")
    page.wait_for_timeout(80)
    assert not any(r['method']=='POST' for r in page.evaluate('window.__requests'))
    expect(page.locator('.mmb-msg')).to_have_count(0)


def test_late_stream_bytes_cannot_repopulate_after_account_switch(page):
    page.evaluate("""() => {
      const original=window.fetch;window.fetch=(url,opts)=>url.endsWith('/brain/stream')?Promise.resolve(new Response(new ReadableStream({start(c){window.__bytes=c;}}),{headers:{'Content-Type':'text/event-stream'}})):original(url,opts);
    }""")
    page.locator('#mmb-ta').fill('Private question A')
    page.locator('#mmb-send').click()
    page.wait_for_function('!!window.__bytes')
    page.evaluate("window.__principal='B';MMBrain.setPrincipal('user-B');window.__bytes.enqueue(new TextEncoder().encode('data: '+JSON.stringify({type:'delta',text:'Private answer A'})+'\\n\\n'));")
    page.wait_for_timeout(80)
    expect(page.locator('.mmb-msg')).to_have_count(0)
    expect(page.locator('#mmb-scroll')).not_to_contain_text('Private answer A')


def test_account_switch_discards_native_fact_inspector_contents(page):
    page.evaluate("""() => {
      window.MM_BRAIN_CFG.symbol=()=> 'AAPL';
      const original=window.fetch;window.fetch=(url,opts)=>url.endsWith('/brain/stream')?Promise.resolve(new Response(new ReadableStream({start(c){window.__factBytes=c;}}),{headers:{'Content-Type':'text/event-stream'}})):original(url,opts);
      MMBrain.close();MMBrain.open();
    }""")
    page.locator('#mmb-ta').fill('Private research A')
    page.locator('#mmb-send').click()
    page.wait_for_function('!!window.__factBytes')
    page.evaluate("""() => {
      const events=[{type:'delta',text:'Saved answer A'},{type:'done',native_fact_receipt:{facts:[{field_id:'market.price.last',status:'available',value:'PRIVATE-FACT-A',unit:'text'}]}}];
      window.__factBytes.enqueue(new TextEncoder().encode(events.map(e=>'data: '+JSON.stringify(e)).join(String.fromCharCode(10,10))+String.fromCharCode(10,10)));window.__factBytes.close();
    }""")
    page.locator('[data-act="ctx-toggle"]').click()
    expect(page.locator('#mmb-ctxinsp-body')).to_contain_text('PRIVATE-FACT-A')
    page.evaluate("window.__principal='B';MMBrain.setPrincipal('user-B')")
    expect(page.locator('#mmb-ctxinsp-body')).not_to_contain_text('PRIVATE-FACT-A')


def test_late_dictation_cannot_write_into_next_accounts_composer(page):
    page.evaluate("window.SpeechRecognition=function(){window.__speech=this;this.start=()=>{};};document.querySelector('[data-act=voice]').style.display='';")
    page.locator('[data-act="voice"]').click()
    page.evaluate("window.__principal='B';MMBrain.setPrincipal('user-B');window.__speech.onresult({results:[[{transcript:'Private dictation A'}]]});")
    expect(page.locator('#mmb-ta')).to_have_value('')


def test_late_image_decode_cannot_attach_to_next_account(page):
    page.evaluate("window.FileReader=function(){window.__file=this;this.readAsDataURL=()=>{};};")
    page.locator('#mmb-file').set_input_files({'name':'private.png','mimeType':'image/png','buffer':b'fixture'})
    page.wait_for_function('!!window.__file')
    page.evaluate("window.__principal='B';MMBrain.setPrincipal('user-B');window.__file.result='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aL1sAAAAASUVORK5CYII=';window.__file.onload();")
    page.wait_for_timeout(150)
    expect(page.locator('#mmb-thumbs img')).to_have_count(0)


def test_late_resumed_thread_cannot_attach_or_delete_next_accounts_run(page):
    page.evaluate("""() => {
      sessionStorage.setItem('mm.brain.run.v2:user:user-A',JSON.stringify({id:'held-run-A',q:'Private question A',ts:Date.now()}));
      const original=window.fetch;window.fetch=(url,opts)=>{
        if(url.endsWith('/runs/held-run-A'))return Promise.resolve({ok:true,json:()=>Promise.resolve({id:'held-run-A',thread_id:'11111111-1111-1111-1111-111111111111',done:false})});
        if(url.endsWith('/threads/11111111-1111-1111-1111-111111111111'))return new Promise(resolve=>window.__heldThread=resolve);
        return original(url,opts);
      };MMBrain.close();MMBrain.open();
    }""")
    page.wait_for_function('!!window.__heldThread')
    page.evaluate("""() => {
      window.__principal='B';MMBrain.setPrincipal('user-B');
      sessionStorage.setItem('mm.brain.run.v2:user:user-B','B-run-must-survive');
      window.__heldThread({ok:true,json:()=>Promise.resolve({thread:{id:'11111111-1111-1111-1111-111111111111'},messages:[{role:'user',content:'Private question A'}]})});
    }""")
    page.wait_for_timeout(80)
    expect(page.locator('.mmb-msg')).to_have_count(0)
    assert page.evaluate("sessionStorage.getItem('mm.brain.run.v2:user:user-B')")=='B-run-must-survive'
    assert not any('/runs/held-run-A/stream' in r['url'] for r in page.evaluate('window.__requests'))


@pytest.mark.parametrize('next_focus', ['control', 'closed', 'initial'])
def test_delayed_open_focus_respects_current_interaction(page, next_focus):
    # Wait for the fixture's opening focus, then control the next deferred focus
    # so the user interaction occurs before that callback deterministically.
    expect(page.locator('#mmb-ta')).to_be_focused()
    page.evaluate("""() => {
      const outside=document.createElement('button');outside.id='outside-focus';
      outside.textContent='Outside';document.body.appendChild(outside);
      MMBrain.close();outside.focus();
      const schedule=window.setTimeout;window.__openFocus=[];
      window.setTimeout=(fn,delay,...args)=>{
        if(delay===260){window.__openFocus.push(fn);return 0;}
        return schedule(fn,delay,...args);
      };
      MMBrain.open();window.setTimeout=schedule;
    }""")
    assert page.evaluate('window.__openFocus.length') == 1
    target=page.locator('.mmb-tools button[data-lane="fast"]')
    if next_focus=='control':
        target.focus()
    elif next_focus=='closed':
        page.evaluate('MMBrain.close()')
        target=page.locator('#outside-focus')
        target.focus()
    else:
        target=page.locator('#mmb-ta')
    page.evaluate('window.__openFocus.forEach(fn=>fn())')
    expect(target).to_be_focused()
    assert all(r['method']=='GET' for r in page.evaluate('window.__requests'))


@pytest.mark.parametrize('width',[320,390,560])
@pytest.mark.parametrize('lang',['en','zh'])
@pytest.mark.parametrize('text_scale',[1,2])
def test_composer_controls_keep_touch_targets_and_reflow(page,width,lang,text_scale):
    page.set_viewport_size({'width':width,'height':844})
    # open() hands focus to the composer 260ms after entry (focusPanel). Let that one-shot
    # handoff land first, or it can take focus from a control between focus() and the check.
    expect(page.locator('#mmb-ta')).to_be_focused()
    page.evaluate("""({lang,scale})=>{
      document.documentElement.dataset.lang=lang;document.dispatchEvent(new Event('langchange'));
      document.querySelector('[data-act=voice]').style.display='';
      const nodes=Array.from(document.querySelectorAll('#mmb-root *')).filter(n=>n.namespaceURI==='http://www.w3.org/1999/xhtml');
      const sizes=nodes.map(n=>parseFloat(getComputedStyle(n).fontSize));
      nodes.forEach((n,i)=>{if(sizes[i])n.style.fontSize=(sizes[i]*scale)+'px';});
    }""",{'lang':lang,'scale':text_scale})
    page.locator('#mmb-ta').fill('Draft only '+('x'*1850))
    buttons=page.locator('.mmb-tools button:visible')
    assert buttons.count()==5
    boxes=[]
    for button in buttons.all():
        button.click(trial=True)
        box=button.bounding_box();assert box
        assert box['width']>=44 and box['height']>=44
        assert box['x']>=0 and box['x']+box['width']<=width
        assert box['y']>=0 and box['y']+box['height']<=844
        assert button.evaluate('(node)=>{const b=node.getBoundingClientRect();const hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return node===hit||node.contains(hit);}')
        button.focus();expect(button).to_be_focused()
        boxes.append(box)
    for i,a in enumerate(boxes):
        for b in boxes[i+1:]:
            assert a['x']+a['width']<=b['x'] or b['x']+b['width']<=a['x'] or a['y']+a['height']<=b['y'] or b['y']+b['height']<=a['y']
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert all(r['method']=='GET' for r in page.evaluate('window.__requests'))
    proof=os.environ.get('MM_BRAIN_HISTORY_PROOF_DIR')
    if proof:
        folder=Path(proof);folder.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(folder/f'{width}-{lang}-{text_scale}x-composer.png'))


@pytest.mark.parametrize('width', [320, 390])
@pytest.mark.parametrize('lang', ['en', 'zh'])
@pytest.mark.parametrize('text_scale', [1, 2])
def test_mobile_history_and_answer_controls_are_reachable(page, width, lang, text_scale):
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    expect(page.locator('.mmb-msg')).to_contain_text('Exact retained answer A')
    page.set_viewport_size({'width': width, 'height': 844})
    page.evaluate('MMBrain.close();MMBrain.open();')
    page.evaluate("""({lang,scale})=>{
      document.documentElement.dataset.lang=lang;document.dispatchEvent(new Event('langchange'));
      const nodes=Array.from(document.querySelectorAll('#mmb-root *')).filter(n=>n.namespaceURI==='http://www.w3.org/1999/xhtml');
      const sizes=nodes.map(n=>parseFloat(getComputedStyle(n).fontSize));
      nodes.forEach((n,i)=>{if(sizes[i])n.style.fontSize=(sizes[i]*scale)+'px';});
    }""", {'lang': lang, 'scale': text_scale})

    def check_targets(selector):
        controls=page.locator(selector)
        assert controls.count()>0
        for control in controls.all():
            control.click(trial=True)
            box=control.bounding_box()
            # Chromium can return 43.99999237060547 for a 44px CSS target.
            # Preserve the accessibility threshold, allowing only subpixel float noise.
            assert box and round(box['width'],4)>=44 and round(box['height'],4)>=44
            assert box['x']>=0 and box['x']+box['width']<=width
            assert control.evaluate('(node)=>{const b=node.getBoundingClientRect();const hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return node===hit||node.contains(hit);}')
            control.focus()
            expect(control).to_be_focused()
    check_targets('.mmb-head .mmb-icon:visible, .mmb-abtn:visible')
    proof=os.environ.get('MM_BRAIN_HISTORY_PROOF_DIR')
    if proof:
        folder=Path(proof);folder.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(folder/f'{width}-{lang}-{text_scale}x-answer-actions.png'))
    page.locator('[data-act="side"][title="Chats"]').click()
    check_targets(f'.mmb-ti[data-id="{A}"] .mmb-ti-act:visible')
    if proof:
        page.screenshot(path=str(folder/f'{width}-{lang}-{text_scale}x-history-actions.png'))
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert all(r['method']=='GET' for r in page.evaluate('window.__requests'))


@pytest.mark.parametrize("action", ["account", "close", "new", "thread", "pagehide"])
def test_voice_recognition_is_aborted_when_composer_context_ends(page, action):
    page.evaluate("""() => {
      window.__speechInstances=[];
      window.SpeechRecognition=function(){
        window.__speechInstances.push(this); this.aborted=0;
        this.start=()=>{}; this.abort=()=>{this.aborted++;this.onresult({results:[[{transcript:'late abort result'}]]});};
      };
      document.querySelector('[data-act=voice]').style.display='';
    }""")
    page.locator('[data-act="voice"]').click()
    if action == "account":
        page.evaluate("MMBrain.setPrincipal('user-B')")
    elif action == "close":
        page.evaluate("MMBrain.close()")
    elif action == "new":
        page.locator('[data-act="new"]').first.click()
    elif action == "thread":
        page.locator(f'.mmb-ti[data-id="{A}"]').click()
    else:
        page.evaluate("window.dispatchEvent(new Event('pagehide'))")
    assert page.evaluate("window.__speechInstances[0].aborted") == 1
    expect(page.locator('#mmb-ta')).to_have_value('')


def test_voice_replacement_keeps_only_current_recognizer(page):
    page.evaluate("""() => {
      window.__speechInstances=[];
      window.SpeechRecognition=function(){window.__speechInstances.push(this);this.aborted=0;this.start=()=>{};this.abort=()=>{this.aborted++;};};
      document.querySelector('[data-act=voice]').style.display='';
    }""")
    page.locator('[data-act="voice"]').click()
    page.locator('[data-act="voice"]').click()
    assert page.evaluate("window.__speechInstances[0].aborted") == 1
    page.evaluate("""() => {
      const old=window.__speechInstances[0], current=window.__speechInstances[1];
      old.onresult({results:[[{transcript:'obsolete'}]]}); old.onend();
      current.onresult({results:[[{transcript:'current dictation'}]]});
    }""")
    expect(page.locator('#mmb-ta')).to_have_value('current dictation')
    page.evaluate("MMBrain.close()")
    assert page.evaluate("window.__speechInstances[1].aborted") == 1


def test_voice_error_aborts_and_late_end_cannot_release_a_new_session(page):
    page.evaluate("""() => {
      window.__speechInstances=[];
      window.SpeechRecognition=function(){window.__speechInstances.push(this);this.aborted=0;this.start=()=>{};this.abort=()=>{this.aborted++;};};
      document.querySelector('[data-act=voice]').style.display='';
    }""")
    page.locator('[data-act="voice"]').click()
    page.evaluate("window.__speechInstances[0].onerror()")
    assert page.evaluate("window.__speechInstances[0].aborted") == 1
    page.locator('[data-act="voice"]').click()
    page.evaluate("window.__speechInstances[0].onend();window.__speechInstances[0].onerror();MMBrain.close()")
    assert page.evaluate("window.__speechInstances[0].aborted") == 1
    assert page.evaluate("window.__speechInstances[1].aborted") == 1


@pytest.mark.parametrize("width", [390, 820])
def test_expanded_history_remains_reachable_after_phone_resize(page, width):
    """Phone and tablet history overlays must return to the selected answer."""
    page.set_viewport_size({"width": width, "height": 844})
    menu = page.locator('.mmb-menu[data-act="side"]')
    expect(menu).to_be_visible()
    expect(page.locator('.mmb-threads')).to_be_hidden()
    menu.click()
    row = page.locator('#mmb-tlist .mmb-ti').first
    expect(row).to_be_visible()
    row.locator('.mmb-ti-body').click()
    expect(page.locator('.mmb-msg.assistant')).to_be_visible()
    expect(page.locator('.mmb-threads')).to_be_hidden()
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')


def test_saved_response_has_accessible_heading_hierarchy_without_executable_markup(page):
    """One- through six-marker headings use the same safe saved-answer renderer."""
    text = '# Direct answer\nA readable first paragraph.\n## Evidence\nSupporting detail.\n### Next check\n<script>window.headingInjected=true</script>'
    page.evaluate(r'''text => {
      const old = window.fetch;
      window.fetch = (url, options = {}) => /\/api\/brain\/threads\/[a-f0-9-]+$/.test(url)
        ? Promise.resolve({ok:true,status:200,json:()=>Promise.resolve({thread:{id:'11111111-1111-1111-1111-111111111111'},messages:[{role:'assistant',content:text}]})})
        : old(url, options);
    }''', text)
    page.locator('#mmb-tlist .mmb-ti').first.locator('.mmb-ti-body').click()
    expect(page.get_by_role('heading', name='Direct answer', exact=True, level=2)).to_be_visible()
    expect(page.get_by_role('heading', name='Evidence', exact=True, level=2)).to_be_visible()
    expect(page.get_by_role('heading', name='Next check', exact=True, level=3)).to_be_visible()
    expect(page.locator('.mmb-txt')).to_contain_text('<script>window.headingInjected=true</script>')
    assert page.evaluate('window.headingInjected === undefined')
    assert page.locator('.mmb-txt script').count() == 0


@pytest.mark.parametrize("width", [1440, 820, 390, 320])
def test_native_workspace_keeps_one_chat_in_host_bounds(page, width):
    page.set_viewport_size({"width": width, "height": 844})
    page.evaluate("""() => {
      document.body.insertAdjacentHTML('beforeend',
        '<main id="brain-slot" style="display:flex;position:absolute;inset:52px 0 0 32px"></main>');
      MM_BRAIN_CFG.getAiContext = () => ({active:{id:'AAPL',type:'security'},ambient:{page:'brain'}});
      window.releaseWorkspace = MMBrain.mountWorkspace(document.querySelector('#brain-slot'));
    }""")
    panel = page.locator("#brain-slot #mmb-panel")
    expect(panel).to_be_visible()
    assert page.locator("#mmb-root").count() == 1
    expect(page.locator("#mmb-launch")).to_have_count(0)
    slot = page.locator("#brain-slot").bounding_box()
    rect = panel.bounding_box()
    for key in ("x", "y", "width", "height"):
        assert abs(rect[key] - slot[key]) <= 1

    expect(page.locator("#mmb-ctx .src")).to_have_text("Selected symbol")
    starters = page.locator(".mmb-comp > .mmb-cards .mmb-cardp")
    expect(starters).to_have_count(3)
    assert page.locator(".mmb-box").evaluate("""box => {
      const bottom = box.getBoundingClientRect().bottom;
      return [...box.nextElementSibling.querySelectorAll('button')].every(action => {
        const rect = action.getBoundingClientRect();
        return rect.top >= bottom && rect.left >= 0 && rect.right <= innerWidth && rect.height >= 44;
      });
    }""")
    prompt = page.get_by_role("button", name="What changed today?")
    prompt.click()
    expect(page.locator("#mmb-ta")).to_have_value("What changed today?")
    assert all(item["method"] == "GET" for item in page.evaluate("window.__requests"))
    page.keyboard.press("Escape")
    expect(panel).to_be_visible()
    page.locator(".mmb-menu").click()
    expect(page.locator("#mmb-search-in")).to_be_focused()
    page.locator("#mmb-search-in").fill("investigation A")
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    expect(page.locator(".mmb-msg")).to_contain_text("Exact retained answer A")
    expect(page.locator(".mmb-answer-context")).to_have_count(0)
    expect(starters).to_have_count(0)
    page.locator(".mmb-head [data-act=new]").click()
    expect(page.locator(".mmb-msg")).to_have_count(0)

    page.evaluate("""() => {
      const next = document.body.appendChild(document.createElement('div'));
      const release = MMBrain.mountWorkspace(next);
      window.releaseWorkspace();
      if (!next.contains(document.querySelector('#mmb-root'))) throw new Error('stale release');
      release();
    }""")
    expect(page.locator("body > #mmb-root #mmb-panel")).to_be_hidden()
    page.evaluate("MMBrain.open()")
    expect(page.locator("body > #mmb-root #mmb-panel")).to_be_visible()


def test_workspace_binds_receipt_to_answer_and_confirms_research_once(page):
    page.evaluate(r"""() => {
      const slot = document.body.appendChild(document.createElement('main'));
      slot.style.cssText = 'position:absolute;inset:0;display:flex';
      MM_BRAIN_CFG.getAiContext = () => ({
        schema: 'ai_context_client.v1', origin_id: 'workbench', context_revision: 2,
        active: {type:'security', id:'AAPL'}, pinned: [], ambient: {page:'brain', symbol:'AAPL'}
      });
      window.releaseWorkspace = MMBrain.mountWorkspace(slot);
      const previous = window.fetch;
      window.__posts = [];
      window.fetch = (url, options={}) => {
        if (options.method !== 'POST' || !url.endsWith('/stream')) return previous(url, options);
        const sent = JSON.parse(options.body);
        window.__posts.push(sent);
        const receipt = {
          type:'context_receipt', request_id:'question-1',
          origin:{origin_id:'workbench',context_revision:2},
          effective_context:{source:'active',entities:[{id:'AAPL'}]}
        };
        const events = [{type:'meta',thread_id:'11111111-1111-1111-1111-111111111111'}, receipt,
          {type:'delta', text:'Example answer'}, {type:'done', context_receipt:receipt, citations:['macro.json']}];
        return Promise.resolve(new Response(events.map(e => 'data: '+JSON.stringify(e)+'\n\n').join('')));
      };
    }""")
    page.locator("#mmb-ta").fill("What changed?")
    page.locator("#mmb-send").click()
    evidence = page.locator(".mmb-answer-context")
    expect(evidence).to_have_count(1)
    evidence.locator("summary").click()
    expect(evidence).to_contain_text("AAPL")
    sources = page.get_by_role("button", name="Sources · 1")
    sources.click()
    reader = page.get_by_role("dialog", name="Sources", exact=True)
    expect(reader.get_by_role("listitem")).to_have_text("macro")
    expect(reader.get_by_role("link")).to_have_count(0)
    reader.get_by_role("button", name="Back to answer").click()
    expect(sources).to_be_focused()

    deepen = page.get_by_role("button", name="Go deeper…")
    deepen.click()
    expect(page.get_by_role("dialog", name="Research depth")).to_be_visible()
    page.get_by_role("button", name="Cancel", exact=True).click()
    assert len(page.evaluate("window.__posts")) == 1
    deepen.click()
    page.get_by_role("button", name="Start research", exact=True).click()
    page.wait_for_function("window.__posts.length === 2")
    original, followup = page.evaluate("window.__posts")
    assert followup["mode"] == "research"
    assert followup["lane"] == "pro"
    assert followup["context"] == original["context"]


@pytest.mark.parametrize("width", [1440, 390])
def test_chart_focus_preserves_draft_selection_and_returns_to_chart(page, width):
    page.set_viewport_size({"width": width, "height": 844})
    page.evaluate("""() => {
      MMBrain.close();
      window.fixtureChartContext = {
        schema:'ai_context_client.v1',origin_id:'chart-owner',context_revision:7,
        active:{id:'AAPL',type:'security'},pinned:[],ambient:{page:'terminal',timeframe:'1D'}
      };
      MM_BRAIN_CFG.getAiContext = () => window.fixtureChartContext;
      const chartEntry = document.createElement('button');
      chartEntry.id = 'chart-entry-fixture'; chartEntry.textContent = 'Open chart assistant';
      chartEntry.addEventListener('click', () => MMBrain.open()); document.body.prepend(chartEntry);
    }""")
    page.locator("#chart-entry-fixture").click()
    page.locator("#mmb-ta").fill("Examine support on this chart")
    if width > 560:
        page.get_by_role("button", name="Focus view").click()
    expect(page.locator("#mmb-root[data-focus] #mmb-panel.max")).to_be_visible()
    expect(page.locator("#mmb-ctx .src")).to_have_text("Active chart")
    return_action = page.get_by_role("button", name="Back to chart")
    expect(return_action).to_be_visible()
    assert return_action.evaluate("""button => {
      const label = button.querySelector('span').getBoundingClientRect();
      const next = button.parentElement.querySelector('[data-act="new"]').getBoundingClientRect();
      return label.right <= button.getBoundingClientRect().right + 1 && label.right <= next.left;
    }""")
    expect(page.locator("#mmb-ta")).to_have_value("Examine support on this chart")
    assert page.evaluate("MM_BRAIN_CFG.getAiContext() === window.fixtureChartContext")
    assert page.locator("#mmb-root").count() == 1
    assert page.locator("#mmb-launch").count() == 0
    if width > 560:
        page.get_by_role("button", name="Compact view").click()
        expect(page.locator("#mmb-panel.open:not(.max)")).to_be_visible()
        page.get_by_role("button", name="Focus view").click()
    page.get_by_role("button", name="Back to chart").click()
    expect(page.locator("#mmb-panel")).to_be_hidden()
    expect(page.locator("#chart-entry-fixture")).to_be_focused()
    assert all(item["method"] == "GET" for item in page.evaluate("window.__requests"))

@pytest.mark.parametrize("width", [1440, 390])
def test_workbench_source_reader_uses_this_answers_citations(page, width):
    page.set_viewport_size({"width": width, "height": 844})
    page.evaluate(r"""() => {
      const slot = document.body.appendChild(document.createElement('main'));
      slot.style.cssText = 'position:absolute;inset:0;display:flex';
      window.releaseWorkbench = MMBrain.mountWorkspace(slot);
      const old = fetch;
      window.fetch = (url, opts = {}) => {
        if (opts.method !== 'POST' || !url.endsWith('/stream')) return old(url, opts);
        const events = [{type:'delta',text:'Reported breadth'}, {type:'done',
          citations:['world_state.json', 'independent_observations.parquet']}];
        return Promise.resolve(new Response(events.map(e => 'data: '+JSON.stringify(e)+'\n\n').join('')));
      };
    }""")
    page.locator('#mmb-ta').fill('Show breadth')
    page.locator('#mmb-send').click()
    trigger = page.get_by_role('button', name='Sources · 2')
    trigger.click()
    dialog = page.get_by_role('dialog', name='Sources', exact=True)
    expect(dialog.get_by_role('listitem')).to_have_text(['world_state', 'independent_observations'])
    expect(dialog.get_by_role('link')).to_have_attribute('href', 'https://www.mastermind-x.com/macro.html')
    expect(dialog.get_by_role('button', name='Close sources')).to_be_focused()
    box = dialog.bounding_box()
    if width == 390:
        assert box['x'] == 0 and abs(box['y'] + box['height'] - 844) <= 1
    else:
        assert box['x'] > width / 2
    page.keyboard.press('Escape')
    expect(dialog).to_have_count(0)
    expect(trigger).to_be_focused()
    trigger.click()
    page.evaluate("window.__onAuth({id:'another-account'})")
    expect(dialog).to_have_count(0)
    expect(trigger).to_have_count(0)


# Exact Macro coordinates use this incumbent widget/browser owner. Provider replies
# are deterministic fixtures; these cases do not claim deployed identity or model proof.
MACRO_REF = {
    "schema": "mastermind.research-context-ref/v1", "kind": "macro_history_observation",
    "authority": "context_only", "workspace_id": "growth_real_economy", "region": "US",
    "manifest_sha256": "a" * 64, "content_sha256": "b" * 64,
    "generation_id": "growth-US-fixture", "artifact_bytes": 5000,
    "series_id": "history:fred:INDPRO", "source_id": "history:fred:INDPRO", "observation": "2026-09-01",
}
MACRO_RECEIPT = {
    "schema": "mastermind.exact-source-receipt/v1", "kind": "macro_history_observation",
    "state": "verified", "authority": "context_only", "reference": MACRO_REF,
    "label": {"en": "Industrial production", "zh": "工业生产"},
    "unit": {"en": "index", "zh": "指数"},
    "basis": {"en": "Latest revised observations · reference dates", "zh": "最新修订的观察值·参考日期"},
    "manifest_generated_at": "2026-11-14T12:00:00Z",
}


def _macro_protocol(page, mode="valid"):
    page.evaluate("""({ref,receipt,mode}) => {
      window.__macroPosts=[];window.__macroRunReads=[];window.__macroRef=ref;
      let consumed=false;const original=window.fetch;
      MM_BRAIN_CFG.getAiContext=()=>({active:{type:'security',id:'AAPL'}});
      MM_BRAIN_CFG.getExactSourceReference=()=>{if(consumed)return;consumed=true;return ref;};
      const stream=events=>new Response(events.map(e=>'data: '+JSON.stringify(e)+'\\n\\n').join(''),{headers:{'Content-Type':'text/event-stream'}});
      const exact={type:'exact_source_receipt',...receipt};
      const meta={type:'meta',thread_id:'macro-thread',lane:'fast'};
      const final=[{type:'delta',text:'Qualified observation answer.'},{type:'done',citations:[receipt]}];
      window.fetch=(url,opts={})=>{
        if(url.includes('/runs/macro-run')){
          window.__macroRunReads.push(url);
          if(mode==='reconnect')return Promise.resolve(stream([{type:'delta',text:'RECONNECTED_TAIL'},{type:'done',citations:[receipt]}]));
          if(url.includes('/stream?'))return Promise.resolve(stream([meta,exact,...final]));
          const status=()=>new Response(JSON.stringify({run_id:'macro-run',thread_id:'macro-thread',lane:'fast',mode:'chat',done:true}));
          if(mode==='late')return new Promise(resolve=>{window.__macroStatusRelease=()=>resolve(status());});
          return Promise.resolve(status());
        }
        if(url.endsWith('/api/brain/stream')&&opts.method==='POST'){
          window.__macroPosts.push(JSON.parse(opts.body));
          if(mode==='reconnect')return Promise.resolve(stream([{type:'run',run_id:'macro-run'},meta,exact,{type:'delta',text:'ORIGINAL_PREFIX '}]));
          if(mode==='missing')return Promise.resolve(stream([meta,{type:'delta',text:'UNVERIFIED_TEXT'},{type:'done'}]));
          if(mode==='retract')return Promise.resolve(stream([meta,{type:'retract',text:'UNVERIFIED_TEXT'},{type:'done'}]));
          if(mode==='mismatch')return Promise.resolve(stream([meta,{...exact,reference:{...ref,observation:'2026-08-01'}},...final]));
          if(mode==='changed')return Promise.resolve(stream([meta,{type:'exact_source_receipt',schema:receipt.schema,kind:receipt.kind,state:'refused',code:'macro_publication_changed'},{type:'done'}]));
          if(mode==='quota')return Promise.resolve(stream([meta,exact,{type:'done',quota_exhausted:true}]));
          return Promise.resolve(stream([meta,exact,...final]));
        }
        return original(url,opts);
      };
    }""", {"ref": MACRO_REF, "receipt": MACRO_RECEIPT, "mode": mode})


@pytest.mark.parametrize("mode,message", [
    ("missing", "could not be verified"), ("mismatch", "could not be verified"),
    ("retract", "could not be verified"), ("changed", "publication changed"),
    ("quota", "chat allowance is used"),
])
def test_macro_source_receipt_precedes_content_and_keeps_refusal_reason(page, mode, message):
    _macro_protocol(page, mode)
    assert page.evaluate("MMBrain.prepareMacroHistoryObservation()")
    assert page.evaluate("__macroPosts.length") == 0
    page.locator('#mmb-ta').fill('Explain this observation.')
    page.locator('#mmb-send').click()
    expect(page.locator('.mmb-errcard')).to_contain_text(message)
    expect(page.locator('#mmb-scroll')).not_to_contain_text('UNVERIFIED_TEXT')
    expect(page.locator('#mmb-scroll')).not_to_contain_text('Qualified observation answer.')


@pytest.mark.parametrize("lang,width", [("en", 1440), ("zh", 390)])
def test_macro_source_stages_once_and_regenerate_keeps_original_coordinates(page, lang, width):
    page.set_viewport_size({"width": width, "height": 900})
    page.evaluate("lang=>document.documentElement.setAttribute('data-lang',lang)", lang)
    _macro_protocol(page)
    assert page.evaluate("MMBrain.prepareMacroHistoryObservation()")
    assert page.evaluate("__macroPosts.length") == 0
    page.locator('#mmb-ta').fill('Original observation question.')
    page.locator('#mmb-send').click()
    expect(page.locator('#mmb-scroll')).to_contain_text('Qualified observation answer.')
    first = page.evaluate('__macroPosts[0]')
    assert first['macro_history_observation'] == MACRO_REF
    assert first['context'] == {'lang': lang}
    assert 'company_source_span' not in first and 'value' not in first['macro_history_observation']
    source = page.locator('.mmb-source-group .mmb-sources-trigger').last
    source.click()
    dialog = page.get_by_role('dialog', name='来源' if lang == 'zh' else 'Sources', exact=True)
    expect(dialog).to_contain_text(MACRO_REF['content_sha256'])
    expect(dialog).to_contain_text('2026-09-01')
    assert dialog.evaluate('(node)=>node.scrollWidth<=node.clientWidth+1')
    dialog.get_by_role('button', name='返回回答' if lang == 'zh' else 'Back to answer', exact=True).click()
    expect(source).to_be_focused()
    page.evaluate("MM_BRAIN_CFG.getExactSourceReference=()=>({...__macroRef,observation:'2026-11-01'})")
    page.locator('.mmb-last .mmb-regen').click()
    page.wait_for_function('__macroPosts.length===2')
    assert page.evaluate('__macroPosts[1].macro_history_observation') == MACRO_REF
    assert page.evaluate('__macroPosts[1].message') == 'Original observation question.'


def test_macro_saved_run_replays_original_receipt_then_admits_exact_regenerate(page):
    _macro_protocol(page, 'resume')
    page.evaluate("""() => {
      MMBrain.close();sessionStorage.setItem('mm.brain.run.v2:user:user-A',JSON.stringify({id:'macro-run',q:'Recovered question.',cursor:9,ts:Date.now(),macro_reference:__macroRef}));MMBrain.open();
    }""")
    expect(page.locator('#mmb-scroll')).to_contain_text('Qualified observation answer.')
    assert page.evaluate('__macroPosts.length') == 0
    assert page.evaluate('__macroRunReads.some(url=>url.endsWith("/stream?cursor=0"))')
    assert page.evaluate("sessionStorage.getItem('mm.brain.run.v2:user:user-A')") is None
    page.locator('.mmb-last .mmb-regen').click()
    page.wait_for_function('__macroPosts.length===1')
    assert page.evaluate('__macroPosts[0].message') == 'Recovered question.'
    assert page.evaluate('__macroPosts[0].macro_history_observation') == MACRO_REF


def test_macro_socket_reconnect_preserves_receipt_and_cursor_without_second_generation(page):
    _macro_protocol(page, 'reconnect')
    assert page.evaluate('MMBrain.prepareMacroHistoryObservation()')
    page.locator('#mmb-ta').fill('Explain the original observation.')
    page.locator('#mmb-send').click()
    expect(page.locator('#mmb-scroll')).to_contain_text('RECONNECTED_TAIL')
    assert page.evaluate('__macroPosts.length') == 1
    assert page.evaluate('__macroRunReads.some(url=>url.endsWith("/stream?cursor=3"))')
    assert page.locator('#mmb-scroll').inner_text().count('ORIGINAL_PREFIX') == 1


def test_macro_late_run_status_cannot_cross_principal_boundary(page):
    _macro_protocol(page, 'late')
    page.evaluate("""() => {
      MMBrain.close();sessionStorage.setItem('mm.brain.run.v2:user:user-A',JSON.stringify({id:'macro-run',q:'Private A question.',ts:Date.now(),macro_reference:__macroRef}));MMBrain.open();
    }""")
    page.wait_for_function('typeof __macroStatusRelease === "function"')
    page.evaluate("""() => {
      __onAuth({id:'user-B'});sessionStorage.setItem('mm.brain.run.v2:user:user-B','{"id":"B-preserved"}');__macroStatusRelease();
    }""")
    expect(page.locator('#mmb-scroll')).not_to_contain_text('Private A question.')
    expect(page.locator('#mmb-scroll')).not_to_contain_text('Qualified observation answer.')
    assert page.evaluate("sessionStorage.getItem('mm.brain.run.v2:user:user-B')") == '{"id":"B-preserved"}'
    assert page.evaluate('__macroPosts.length') == 0


def test_other_history_cannot_regenerate_previous_macro_source(page):
    _macro_protocol(page)
    assert page.evaluate('MMBrain.prepareMacroHistoryObservation()')
    page.locator('#mmb-ta').fill('Original Macro question.')
    page.locator('#mmb-send').click()
    expect(page.locator('#mmb-scroll')).to_contain_text('Qualified observation answer.')
    page.locator(f'.mmb-ti[data-id="{A}"] .mmb-ti-body').click()
    expect(page.locator('#mmb-scroll')).to_contain_text('Exact retained answer A')
    expect(page.locator('.mmb-last .mmb-regen')).to_be_disabled()
    assert page.evaluate('__macroPosts.length') == 1
