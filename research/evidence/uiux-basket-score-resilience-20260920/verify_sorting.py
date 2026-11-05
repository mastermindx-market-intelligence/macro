"""Use native keyboard/click controls; never call sort/render methods from the verifier."""
from __future__ import annotations
import argparse, hashlib, json, threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from playwright.sync_api import sync_playwright

ap=argparse.ArgumentParser()
ap.add_argument('--base-url');ap.add_argument('--site-dir');ap.add_argument('--output-dir')
a=ap.parse_args()
root=Path(__file__).resolve().parents[3]
site=Path(a.site_dir) if a.site_dir else root/'site'
out=Path(a.output_dir) if a.output_dir else Path(__file__).parent/'sorting'
out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=None
if a.base_url:base=a.base_url.rstrip('/')
else:
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(site)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
results=[]
def focused(page,key):
    return page.evaluate('(key)=>document.activeElement?.dataset.holdSort===key',key)
def order(page):
    return page.locator('#hold tbody .hold-stock .tk').all_text_contents()
def seed(page,lang,theme,pending=None):
    page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');localStorage.setItem('lang','{lang}');")
    if not a.base_url:
        for pattern in ['**/live/*.json','**/basketdata/*.json','**/policy_lever.json']:
            page.route(pattern,lambda route:route.fulfill(status=401,content_type='application/json',body='{}'))
        page.route('**/crossmarketdata/links.json',(lambda route:pending.append(route)) if pending is not None else (lambda route:route.fulfill(status=401,content_type='application/json',body='{}')))
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for route in ['basket/ai_semiconductors.html','basket_china/cn_solar.html']:
            for device,width,height in [('desktop',1440,900),('mobile',390,844)]:
                for lang in ['en','zh']:
                    for theme in ['dark','light']:
                        label=f'{route.replace("/","-")}-{device}-{lang}-{theme}'
                        page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce',has_touch=device=='mobile',is_mobile=device=='mobile');errors=[]
                        page.on('pageerror',lambda e,errors=errors:errors.append(str(e)));seed(page,lang,theme)
                        response=page.goto(base+'/'+route,wait_until='domcontentloaded');assert response.status==200
                        page.locator('#hold tbody tr').first.wait_for()
                        original=order(page)
                        details=page.locator('details.ftr-anatomy-disclosure');details.locator('summary').click()
                        # Reach the first sorting button via real Tab navigation from score disclosure.
                        for tabs in range(80):
                            page.keyboard.press('Tab')
                            if focused(page,'recommend'):break
                        else:raise AssertionError((label,'sort button not reachable by Tab'))
                        potential=page.locator('#hold button[data-hold-sort="recommend"]')
                        assert page.locator('#hold th[aria-sort]').count()==1
                        assert potential.locator('..').get_attribute('aria-sort')=='other'
                        assert potential.get_attribute('type')=='button' and potential.evaluate('e=>e.tabIndex')==0
                        name=potential.inner_text().strip()
                        assert ('潜力' in name) if lang=='zh' else ('Potential' in name)
                        old=potential.element_handle()
                        page.keyboard.press('Enter')
                        assert focused(page,'recommend') and not old.evaluate('e=>e.isConnected'),label
                        assert page.evaluate('_sort.dir')==1 and order(page)!=original,label
                        assert details.is_visible() and details.evaluate('e=>e.open'),label
                        page.keyboard.press('Space')
                        assert focused(page,'recommend') and page.evaluate('_sort.dir')==-1,label
                        assert order(page)==original,(label,'Space toggled twice or changed ranking')
                        if device=='desktop':
                            page.keyboard.press('Tab')
                            assert focused(page,'r20'),(label,'second sort button not next in tab order')
                            page.keyboard.press('Enter')
                            assert focused(page,'r20')
                            h=page.locator('#hold th[aria-sort]');assert h.count()==1 and h.get_attribute('data-s')=='r20'
                            assert h.get_attribute('aria-sort')=='descending'
                            values=page.locator('#hold tbody .hold-20d').all_text_contents()
                            nums=[float(v.strip().rstrip('%')) for v in values if v.strip()!='—']
                            assert nums==sorted(nums,reverse=True),label
                            page.keyboard.press('Space')
                            assert focused(page,'r20') and h.get_attribute('aria-sort')=='ascending'
                            values=page.locator('#hold tbody .hold-20d').all_text_contents()
                            nums=[float(v.strip().rstrip('%')) for v in values if v.strip()!='—']
                            assert nums==sorted(nums),label
                        else:
                            assert not page.locator('#hold button[data-hold-sort="r20"]').is_visible()
                            potential.tap();assert focused(page,'recommend') and page.evaluate('_sort.dir')==1
                            assert not page.locator('.lens-scrim').is_visible(),(label,'help overlay blocked touch sorting')
                        # Language toggles keep focus/order and update the actual visible and accessible labels.
                        before=order(page);other='zh' if lang=='en' else 'en'
                        page.evaluate('(lang)=>window.setLang(lang)',other)
                        assert order(page)==before and focused(page,'r20' if device=='desktop' else 'recommend')
                        page.evaluate('(lang)=>window.setLang(lang)',lang)
                        overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=1
                        widths=page.locator('#hold .hold-sort:visible').evaluate_all('(els)=>els.map(e=>({client:e.clientWidth,scroll:e.scrollWidth}))')
                        assert all(v['scroll']<=v['client']+1 for v in widths),(label,'button clipped',widths)
                        labels=page.locator('#hold .hold-sort > .l-'+lang+':visible').evaluate_all('(els)=>els.map(e=>({height:e.getBoundingClientRect().height,line:parseFloat(getComputedStyle(e).lineHeight)}))')
                        assert all(v['height']<=v['line']*1.5 for v in labels),(label,'split header label',labels)
                        assert not errors,(label,errors)
                        page.locator('#hold').scroll_into_view_if_needed()
                        page.screenshot(path=str(out/(label+'.png')))
                        results.append({'cell':label,'http':200,'tab_steps':tabs+1,'row_count':len(original),'Enter_Space_click':True,'focus_preserved':True,'score_open_preserved':True,'numeric_sort_checked':device=='desktop','native_touch_checked':device=='mobile','sort_widths':widths,'overflow':overflow,'page_errors':errors,'html_sha256':hashlib.sha256(response.body()).hexdigest(),'passed':True})
                        print(json.dumps(results[-1]),flush=True);page.close()
        # A real committed optional response replaces the focused header. Neither focus nor order may be lost.
        if not a.base_url:
            for route,lang in [('basket/ai_semiconductors.html','en'),('basket_china/cn_solar.html','zh')]:
                for direction in [-1,1]:
                    pending=[];page=browser.new_page(viewport={'width':390,'height':844});errors=[]
                    page.on('pageerror',lambda e,errors=errors:errors.append(str(e)));seed(page,lang,'light',pending)
                    page.goto(base+'/'+route,wait_until='domcontentloaded');button=page.locator('#hold button[data-hold-sort="recommend"]')
                    button.focus()
                    if direction==1:page.keyboard.press('Enter')
                    original=order(page);old=button.element_handle();assert focused(page,'recommend') and len(pending)==1
                    pending[0].fulfill(status=200,content_type='application/json',path=str(site/'crossmarketdata/links.json'))
                    page.wait_for_function('e=>!e.isConnected',arg=old)
                    assert focused(page,'recommend') and page.evaluate('_sort.dir')==direction and order(page)==original
                    assert not errors,errors
                    results.append({'route':route,'lang':lang,'async_refresh':True,'direction':direction,'focus_preserved':True,'order_preserved':True,'passed':True});print(json.dumps(results[-1]),flush=True);page.close()
        browser.close()
finally:
    if server:server.shutdown();server.server_close()
    (out/'keyboard-results.json').write_text(json.dumps({'source_mode':'public, unmodified requests' if a.base_url else 'local; optional requests 401, async test uses committed crossmarket artifact','results':results},indent=2)+'\n')
