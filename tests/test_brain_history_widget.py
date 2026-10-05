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
        page.route("http://history.test/",lambda route:route.fulfill(content_type="text/html",body="<html data-lang='en'><head></head><body></body></html>"))
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
