from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json, threading, hashlib
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'mockups/evidence/uiux-government-revenue-mobile-20260920'
OUT.mkdir(parents=True,exist_ok=True)
class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'site')))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url=f'http://127.0.0.1:{server.server_port}/government_revenue.html'
results=[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for mode,w,h in [('desktop',1440,900),('mobile',390,844)]:
            for lang in ['en','zh']:
                for theme in ['dark','light']:
                    label=f'{mode}-{lang}-{theme}'
                    page=browser.new_page(viewport={'width':w,'height':h},reduced_motion='reduce')
                    errors=[];page.on('pageerror',lambda exc,errors=errors:errors.append(str(exc)))
                    page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');localStorage.setItem('lang','{lang}');")
                    response=page.goto(url,wait_until='domcontentloaded',timeout=30000)
                    assert response and response.status==200,label
                    page.wait_for_selector('#queueList .queue-row',timeout=15000)
                    page.evaluate("s=>{if(window.setTheme)window.setTheme(s.theme);else document.documentElement.setAttribute('data-theme',s.theme);if(window.setLang)window.setLang(s.lang);else {document.documentElement.setAttribute('data-lang',s.lang);document.dispatchEvent(new Event('langchange'));}}",{'lang':lang,'theme':theme})
                    page.wait_for_timeout(200)
                    def focus_id(): return page.evaluate('document.activeElement.id')
                    def inside(sel): return page.evaluate('(s)=>document.querySelector(s).contains(document.activeElement)',sel)
                    def overflow(): return page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
                    assert page.locator('html').get_attribute('data-theme')==theme,label
                    assert page.locator('html').get_attribute('data-lang')==lang,label
                    assert overflow()<=1,(label,overflow())
                    assert page.locator('#deskSearch').get_attribute('placeholder')==('公告、机构或股票代码' if lang=='zh' else 'Notice, agency or ticker'),label
                    assert page.locator('#savedViewName').get_attribute('placeholder')==('为此视图命名' if lang=='zh' else 'Name this view'),label
                    assert page.locator('#alertType option').all_text_contents()==(['机会变化','授标 / 行动变化','推导到期观察'] if lang=='zh' else ['Opportunity change','Award / action change','Derived expiry watch']),label
                    original_overflow=page.evaluate('document.body.style.overflow')
                    if mode=='mobile':
                        page.locator('#filterOpen').click();assert focus_id()=='deskSearch',(label,focus_id())
                        assert page.locator('#filterPane').get_attribute('role')=='dialog'
                        assert page.locator('#filterPane').get_attribute('aria-modal')=='true'
                        page.keyboard.press('Shift+Tab');assert inside('#filterPane'),(label,'ShiftTab escapes',focus_id())
                        page.keyboard.press('Tab');assert focus_id()=='deskSearch',(label,'wrap',focus_id())
                        page.locator('#deskSearch').fill('Department')
                        page.keyboard.press('Escape')
                        assert not page.locator('#filterPane').is_visible(),label
                        assert focus_id()=='filterOpen',(label,'dismiss',focus_id())
                        assert page.locator('#deskSearch').input_value()=='Department'
                        page.keyboard.press('/')
                        assert page.locator('#filterPane').is_visible() and focus_id()=='deskSearch',(label,'slash')
                        assert page.locator('#deskSearch').input_value()=='Department'
                        page.locator('#deskSearch').fill('')
                        page.screenshot(path=str(OUT/f'{label}-filters.png'))
                        page.keyboard.press('Escape');assert focus_id()=='filterOpen'
                        page.locator('#queueList .queue-row').first.click()
                        page.locator('#inspectorOpen').click()
                        assert page.locator('#inspectorPane').is_visible()
                        assert inside('#inspectorPane'),(label,'inspector initial focus',focus_id())
                        page.locator('#evidenceOpen').click()
                        assert page.locator('#evidenceDrawer').is_visible() and focus_id()=='drawerClose'
                        assert page.locator('#inspectorPane').evaluate('(el)=>el.inert') is True
                        # Hit testing catches a visually covered drawer that DOM visibility misses.
                        assert page.locator('#evidenceDrawer').evaluate("el=>{const r=el.getBoundingClientRect();return [0.25,0.55,0.8].every(f=>el.contains(document.elementFromPoint(r.left+r.width/2,r.top+r.height*f)))}"),(label,'source drawer is covered')
                        page.keyboard.press('Shift+Tab');assert inside('#evidenceDrawer'),(label,'source tab escape')
                        page.screenshot(path=str(OUT/f'{label}-source-details.png'))
                        page.keyboard.press('Escape')
                        assert not page.locator('#evidenceDrawer').is_visible()
                        assert page.locator('#inspectorPane').is_visible()
                        assert not page.locator('#inspectorPane').evaluate('(el)=>el.inert')
                        assert not page.locator('#drawerBackdrop').evaluate('(el)=>el.hidden')
                        assert focus_id()=='evidenceOpen',(label,'nested return',focus_id())
                        page.keyboard.press('Escape')
                        assert not page.locator('#inspectorPane').is_visible()
                        assert focus_id()=='inspectorOpen',(label,'parent return',focus_id())
                        assert page.evaluate('document.body.style.overflow')==original_overflow
                        page.locator('#filterOpen').click()
                        page.set_viewport_size({'width':1440,'height':900});page.wait_for_timeout(100)
                        assert page.locator('#filterPane').get_attribute('aria-modal') is None
                        assert page.locator('#drawerBackdrop').evaluate('(el)=>el.hidden')
                        assert page.evaluate('document.body.style.overflow')==original_overflow
                        page.set_viewport_size({'width':w,'height':h});page.wait_for_timeout(60)
                    else:
                        page.locator('#queueHeading').click();page.keyboard.press('/')
                        assert focus_id()=='deskSearch',(label,'desktop slash',focus_id())
                        page.locator('#deskSearch').fill('Department');page.keyboard.press('Escape')
                        assert page.locator('#deskSearch').input_value()=='' and focus_id()=='deskSearch'
                        page.locator('#queueList .queue-row').first.click()
                        page.locator('#evidenceOpen').click()
                        assert focus_id()=='drawerClose';page.keyboard.press('Shift+Tab')
                        assert inside('#evidenceDrawer'),(label,'desktop source trap')
                        page.screenshot(path=str(OUT/f'{label}-source-details.png'))
                        page.keyboard.press('Escape');assert focus_id()=='evidenceOpen'
                        assert page.locator('#drawerBackdrop').evaluate('(el)=>el.hidden')
                        assert page.evaluate('document.body.style.overflow')==original_overflow
                    assert overflow()<=1,(label,'final overflow',overflow())
                    assert not errors,(label,errors)
                    row={'cell':label,'status':response.status,'rows':page.locator('#queueList .queue-row').count(),'overflow':overflow(),'page_errors':errors,'passed':True}
                    results.append(row);print(json.dumps(row),flush=True)
                    page.close()
        browser.close()
finally:
    server.shutdown();server.server_close()
    (OUT/'interaction-results.json').write_text(json.dumps({'pre_repair_head':'d1172fc522837e7e9571e181c5214315aeea5506','runtime_sha256':hashlib.sha256((ROOT/'templates/government_revenue.html.j2').read_bytes()).hexdigest(),'method':'Actual clicks, typing, Tab/Shift+Tab, Escape, slash and resize against the patched generated site; no internal runtime helpers invoked. Public snapshot only; no membership simulation.','results':results},ensure_ascii=False,indent=2)+'\n')
