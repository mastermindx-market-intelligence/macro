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
            if(url.endsWith('/me'))body={tier:'pro',quotas:{fast:{limit:-1},pro:{limit:-1}}};
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


# Prophet adopts the same shared widget; transport/auth below are synthetic.
@pytest.fixture
def prophet_launcher():
    from urllib.parse import urlsplit
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        page = context.new_page()
        state = {"fail": False, "scripts": 0, "errors": []}
        page.on("pageerror", lambda error: state["errors"].append(str(error)))
        from jinja2 import Environment
        from markupsafe import Markup, escape
        source = (ROOT / "templates/dashboard.html.j2").read_text()
        start = source.index('<div class="stk-headline">')
        end = source.index('<nav class="stk-header-links prophet-section-nav"', start)
        env = Environment(autoescape=True)
        env.globals["t"] = lambda en, zh: Markup('<span class="l-en">{}</span><span class="l-zh">{}</span>').format(escape(en), escape(zh))
        env.globals["td"] = lambda value: value
        header = env.from_string(source[start:end]).render(
            _stk_hdr_delayed=False, _stk_hdr_su={"as_of":"2026-10-30"},
            _vint_tip_en="Synthetic board date", _vint_tip_zh="测试榜单日期",
            latest={"quad_name":"Growth"}, pb={"dial":{"posture":"Selective"}},
        )
        shell = """<!doctype html><html data-lang="en" data-theme="light"><head><style>
        .l-zh{display:none}html[data-lang="zh"] .l-en{display:none}html[data-lang="zh"] .l-zh{display:inline}
        body{font-family:Arial,sans-serif} :root{--line:#b4bac2;--text:#20242b;--muted:#576270;--link:#285fff;--panel2:#edf1f6}
        </style></head><body class="page-stocks"><header id="stocks-header">""" + header + """</header>
        <button id="outside-assistant">Continue reading</button></body></html>"""
        def route(r):
            path = urlsplit(r.request.url).path
            if path == "/us_stocks.html":
                r.fulfill(content_type="text/html", body=shell)
            elif path == "/mm_brain.js":
                state["scripts"] += 1
                if state["fail"]:
                    r.abort()
                else:
                    r.fulfill(content_type="application/javascript", path=str(ROOT / "templates/mm_brain.js"))
            else:
                r.abort()
        page.route("**/*", route)
        page.goto("http://prophet-launcher.test/us_stocks.html")
        page.evaluate("""() => {
          window.__requests=[]; window.__auth=null;
          window.MDXAuth={enabled:()=>true,onChange:fn=>{window.__onAuth=fn;fn(null);},open:()=>{}};
          window.MM_BRAIN_CFG={symbol:()=> 'NVDA',onClose:()=>false};
          window.__originalConfig=window.MM_BRAIN_CFG;
          window.fetch=(url,options={})=>{
            window.__requests.push({url:String(url),method:options.method||'GET'});
            return Promise.resolve(new Response('{}',{status:503,headers:{'Content-Type':'application/json'}}));
          };
          window.__originalHeader=document.getElementById('prophet-assistant');
        }""")
        theme = (ROOT / "templates/theme.js").read_text()
        start = theme.index("  var MM_BRAIN_VER =")
        end = theme.index("\n})();", start)
        # Execute the actual bootstrap, not a copied/reimplemented loader.
        bootstrap = "(function(){var _mmSharedAssetRoot='http://prophet-launcher.test/';function curLang(){return document.documentElement.dataset.lang||'en';}\n" + theme[start:end] + "\ninitChatLauncher();})();"
        yield page, state, lambda: page.add_script_tag(content=bootstrap)
        context.close()
        browser.close()


@pytest.mark.parametrize("key", ["Enter", "Space"])
def test_prophet_header_lazily_adopts_one_widget_and_returns_focus(prophet_launcher, key):
    page, state, boot = prophet_launcher
    boot()
    trigger = page.locator("#prophet-assistant")
    expect(trigger).to_be_visible()
    assert page.locator("#mmb-boot,#mmb-launch,#mmb-root").count() == 0
    trigger.focus()
    assert page.locator("#mmb-root").count() == 0  # warm fetch cannot mount
    trigger.press(key)
    expect(page.locator("#mmb-panel")).to_be_visible()
    expect(page.locator(".mmb-signin").first).to_be_focused()
    assert page.locator("#mmb-root").count() == 1
    assert page.locator("#mmb-boot,#mmb-launch").count() == 0
    assert page.evaluate("document.getElementById('prophet-assistant')===window.__originalHeader")
    assert page.evaluate("MM_BRAIN_CFG===window.__originalConfig && MM_BRAIN_CFG.symbol()==='NVDA'")
    assert not page.locator("#mmb-panel").evaluate("(n)=>n.classList.contains('mmb-top')")
    expect(trigger).to_have_attribute("aria-expanded", "true")
    page.keyboard.press("Escape")
    expect(page.locator("#mmb-panel")).to_be_hidden()
    expect(trigger).to_be_focused()
    expect(trigger).to_have_attribute("aria-expanded", "false")
    before = state["scripts"]
    trigger.press(key)
    expect(page.locator("#mmb-panel")).to_be_visible()
    assert state["scripts"] == before
    assert all(r["method"] == "GET" for r in page.evaluate("window.__requests"))
    assert not state["errors"]


def test_prophet_header_bundle_failure_is_visible_and_same_button_retries(prophet_launcher):
    page, state, boot = prophet_launcher
    state["fail"] = True
    boot()
    trigger = page.locator("#prophet-assistant")
    expect(trigger).to_be_visible()
    trigger.press("Enter")
    expect(trigger).not_to_have_attribute("aria-busy", "true")
    expect(page.locator("#prophet-assistant-status")).to_contain_text("try again")
    expect(trigger).to_be_focused()
    assert page.locator("#mmb-root").count() == 0
    state["fail"] = False
    trigger.press("Space")
    expect(page.locator("#mmb-panel")).to_be_visible()
    expect(page.locator("#prophet-assistant-status")).to_be_hidden()
    assert page.evaluate("document.getElementById('prophet-assistant')===window.__originalHeader")
    assert page.locator("#mmb-boot,#mmb-launch").count() == 0
    assert not state["errors"]


def test_prophet_header_adopts_preloaded_widget_without_replacing_conversation(prophet_launcher):
    page, state, boot = prophet_launcher
    page.add_script_tag(path=str(ROOT / "templates/mm_brain.js"))
    assert page.locator("#mmb-launch").count() == 1
    page.evaluate("window.__originalRoot=document.getElementById('mmb-root');")
    boot()
    trigger = page.locator("#prophet-assistant")
    expect(trigger).to_be_visible()
    assert page.locator("#mmb-launch,#mmb-boot").count() == 0
    trigger.press("Enter")
    expect(page.locator("#mmb-panel")).to_be_visible()
    assert page.evaluate("document.getElementById('mmb-root')===window.__originalRoot")
    assert state["scripts"] == 0
    assert not state["errors"]


@pytest.mark.parametrize("width,lang", [(320,"en"),(320,"zh"),(390,"en"),(390,"zh")])
@pytest.mark.parametrize("text_scale", [1,2])
def test_prophet_header_target_keeps_mobile_size_and_hidden_fallback(prophet_launcher, width, lang, text_scale):
    import re
    page, state, boot = prophet_launcher
    page.set_viewport_size({"width":width,"height":844})
    page.evaluate("lang=>document.documentElement.dataset.lang=lang",lang)
    css = (ROOT / "templates/_prophet_page.css.j2").read_text()
    page.add_style_tag(content=re.sub(r"{#.*?#}","",css,flags=re.S))
    expect(page.locator("#prophet-assistant")).to_be_hidden()
    boot()
    trigger=page.locator("#prophet-assistant")
    expect(trigger).to_be_visible()
    page.evaluate("""scale=>{
      const nodes=[...document.querySelectorAll('#stocks-header *')].filter(n=>n.namespaceURI==='http://www.w3.org/1999/xhtml');
      const sizes=nodes.map(n=>parseFloat(getComputedStyle(n).fontSize));
      nodes.forEach((n,i)=>{if(sizes[i])n.style.fontSize=(sizes[i]*scale)+'px';});
    }""",text_scale)
    box=trigger.bounding_box()
    assert box and box["height"]>=44 and box["width"]>=44
    assert box["x"]>=0 and box["x"]+box["width"]<=width
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert not state["errors"]


def test_prophet_header_hung_bundle_deadline_ignores_late_previous_attempt(prophet_launcher):
    page, state, boot = prophet_launcher
    boot()
    page.evaluate("""() => {
      const schedule=window.setTimeout, append=Node.prototype.appendChild;
      window.__deadlines=[];window.__attempts=[];
      window.setTimeout=(fn,ms,...args)=>{
        if(ms>=4000 && ms<=12000){window.__deadlines.push(fn);return 0;}
        return schedule(fn,ms,...args);
      };
      Node.prototype.appendChild=function(node){
        if(node.tagName==='SCRIPT' && node.src.includes('mm_brain.js')){
          window.__attempts.push(node);return node;
        }
        return append.call(this,node);
      };
      window.__loadCurrent=()=>append.call(document.body,window.__attempts.at(-1));
      document.getElementById('prophet-assistant').click();
      window.__oldLoad=window.__attempts[0].onload;
      window.__oldError=window.__attempts[0].onerror;
    }""")
    assert page.evaluate("window.__deadlines.length") == 1
    trigger=page.locator("#prophet-assistant")
    expect(trigger).to_have_attribute("aria-busy","true")
    page.evaluate("window.__deadlines[0]()")
    expect(trigger).not_to_have_attribute("aria-busy","true")
    expect(page.locator("#prophet-assistant-status")).to_contain_text("try again")
    page.evaluate("document.getElementById('prophet-assistant').click();window.__oldLoad();window.__oldError();")
    expect(trigger).to_have_attribute("aria-busy","true")
    assert page.evaluate("window.__attempts.length") == 2
    assert page.locator("#mmb-root").count() == 0
    page.evaluate("window.__loadCurrent()")
    expect(page.locator("#mmb-panel")).to_be_visible()
    assert page.locator("#mmb-root").count() == 1
    assert not state["errors"]


def test_default_floating_launcher_remains_retryable_without_a_prophet_host(prophet_launcher):
    page, state, boot = prophet_launcher
    page.evaluate("document.getElementById('stocks-header').remove()")
    state["fail"]=True
    boot()
    trigger=page.locator("#mmb-boot")
    expect(trigger).to_be_visible()
    assert trigger.evaluate("(n)=>getComputedStyle(n).position")=="fixed"
    trigger.press("Enter")
    expect(trigger).not_to_have_attribute("aria-busy","true")
    state["fail"]=False
    trigger.press("Space")
    expect(page.locator("#mmb-panel")).to_be_visible()
    expect(page.locator("#mmb-boot")).to_have_count(0)
    assert page.locator("#mmb-launch").count()==1
    expect(page.locator(".mmb-signin").first).to_be_focused()
    page.keyboard.press("Escape")
    expect(page.locator("#mmb-launch")).to_be_focused()
    assert not state["errors"]


@pytest.mark.parametrize("header", [True,False])
def test_late_evaluated_bundle_retires_expired_launcher_without_unsolicited_open(prophet_launcher, header):
    page, state, boot = prophet_launcher
    if not header:
        page.evaluate("document.getElementById('stocks-header').remove()")
    boot()
    selector="#prophet-assistant" if header else "#mmb-boot"
    page.evaluate("""selector => {
      const schedule=window.setTimeout,append=Node.prototype.appendChild;
      window.__deadline=null;
      window.setTimeout=(fn,ms,...args)=>{
        if(ms>=4000 && ms<=12000){window.__deadline=fn;return 0;}
        return schedule(fn,ms,...args);
      };
      Node.prototype.appendChild=function(node){
        if(node.tagName==='SCRIPT' && node.src.includes('mm_brain.js'))return node;
        return append.call(this,node);
      };
      document.querySelector(selector).click();
      window.__deadline();
    }""",selector)
    page.add_script_tag(path=str(ROOT / "templates/mm_brain.js"))
    expect(page.locator("#mmb-panel")).to_be_hidden()
    expect(page.locator("#mmb-boot")).to_have_count(0)
    trigger=page.locator("#prophet-assistant" if header else "#mmb-launch")
    expect(trigger).to_be_visible()
    before=page.evaluate("window.__requests.filter(r=>r.url.endsWith('/me')).length")
    trigger.press("Enter")
    expect(page.locator("#mmb-panel")).to_be_visible()
    assert page.evaluate("window.__requests.filter(r=>r.url.endsWith('/me')).length")==before+1
    assert page.locator("#mmb-root").count()==1
    assert not state["errors"]
