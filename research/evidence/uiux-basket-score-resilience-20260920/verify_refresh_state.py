"""Delay a real local optional artifact; verify native open/focus state after it arrives."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import threading,json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[3];out=Path(__file__).parent/'continuation';out.mkdir(exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start();results=[]
try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True)
        for route,lang in [('basket/ai_semiconductors.html','en'),('basket_china/cn_solar.html','zh')]:
            for opened in [True,False]:
                page=browser.new_page(viewport={'width':390,'height':844});pending=[];errors=[]
                page.on('pageerror',lambda e,errors=errors:errors.append(str(e)))
                page.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','light');")
                for pattern in ['**/live/*.json','**/basketdata/*.json','**/policy_lever.json']:
                    page.route(pattern,lambda r:r.fulfill(status=401,content_type='application/json',body='{}'))
                page.route('**/crossmarketdata/links.json',lambda r:pending.append(r))
                response=page.goto(f'http://127.0.0.1:{server.server_port}/{route}',wait_until='domcontentloaded');assert response.status==200
                details=page.locator('details.ftr-anatomy-disclosure');summary=details.locator('summary')
                summary.click()
                if not opened:summary.click()
                before=details.element_handle();assert details.evaluate('e=>e.open') is opened
                assert summary.evaluate('e=>e===document.activeElement')
                assert len(pending)==1
                # Actual committed local source, not mocked positions or authenticated production access.
                pending[0].fulfill(status=200,content_type='application/json',path=str(root/'site/crossmarketdata/links.json'))
                page.wait_for_function('e=>!e.isConnected',arg=before)
                details=page.locator('details.ftr-anatomy-disclosure');assert details.count()==1
                assert details.evaluate('e=>e.open') is opened
                assert details.locator('summary').evaluate('e=>e===document.activeElement')
                assert not errors,errors
                row={'route':route,'lang':lang,'open':opened,'focus_restored':True,'optional_artifact':'local committed crossmarketdata/links.json','page_errors':errors,'passed':True};results.append(row);print(json.dumps(row));page.close()
        browser.close()
finally:
    server.shutdown();server.server_close();(out/'refresh-results.json').write_text(json.dumps(results,indent=2)+'\n')
