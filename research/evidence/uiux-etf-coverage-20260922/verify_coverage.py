"""Native ETF coverage interaction proof; no page or network response interception."""
from __future__ import annotations
import argparse,hashlib,json,threading
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser();ap.add_argument('--site-dir',type=Path);ap.add_argument('--base-url');ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args()
args.output_dir.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*_):pass
server=None
if args.base_url:base=args.base_url.rstrip('/')
else:
 assert args.site_dir
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(args.site_dir)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
results=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for device,w in [('desktop',1440),('mobile',390),('narrow',320)]:
   for lang in ['en','zh']:
    for theme in ['dark','light']:
     name=f'{device}-{lang}-{theme}';mobile=device!='desktop';p=browser.new_page(viewport={'width':w,'height':900},is_mobile=mobile,has_touch=mobile,reduced_motion='reduce');errors=[];failed=[]
     p.on('pageerror',lambda e,errors=errors:errors.append(str(e)));p.on('response',lambda r,failed=failed:failed.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
     p.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.setItem('lang','{lang}');localStorage.removeItem('themeAuto');")
     response=p.goto(base+'/etfs.html',wait_until='domcontentloaded',timeout=30000);p.wait_for_timeout(800);assert response and response.status==200
     stats=p.locator('.fl-stats');directory=stats.locator('xpath=ancestor::details[1]');helpbox=directory.locator('.fl-help');summary=helpbox.locator('summary');funds=directory.locator('.fu')
     before=funds.locator('b').all_text_contents();assert len(before)>0
     assert directory.get_attribute('open') is not None
     assert helpbox.get_attribute('open') is None and not helpbox.locator('p').is_visible()
     assert directory.locator(':scope > summary .txq').count()==0
     assert ('接近最新快照' in stats.inner_text()) if lang=='zh' else ('near latest snapshot' in stats.inner_text())
     summary.scroll_into_view_if_needed();assert summary.bounding_box()['height']>=40
     p.wait_for_timeout(600);p.screenshot(path=str(args.output_dir/(name+'-rest.png')))
     if mobile:summary.tap()
     else:summary.focus();p.keyboard.press('Enter')
     assert helpbox.get_attribute('open') is not None and helpbox.locator('p').is_visible()
     assert ('并非距今天' in helpbox.inner_text()) if lang=='zh' else ('not from today' in helpbox.inner_text())
     p.wait_for_timeout(600);p.screenshot(path=str(args.output_dir/(name+'-open.png')))
     # Shared Settings, not a renderer hook: the native open state and directory remain intact.
     p.locator('.nav-settings-btn').click();button=p.locator('.settings-pop .lang-toggle');button.focus();p.keyboard.press('Enter');other='en' if lang=='zh' else 'zh'
     assert p.locator('html').get_attribute('data-lang')==other;p.keyboard.press('Escape')
     assert helpbox.get_attribute('open') is not None
     assert funds.locator('b').all_text_contents()==before
     parent=directory.locator(':scope > summary');parent.focus();p.keyboard.press('Space');assert directory.get_attribute('open') is None
     p.keyboard.press('Space');assert directory.get_attribute('open') is not None and helpbox.get_attribute('open') is not None
     summary.focus();p.keyboard.press('Space');assert helpbox.get_attribute('open') is None
     assert summary.evaluate('e=>document.activeElement===e')
     overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=1,(name,overflow)
     assert stats.evaluate('e=>e.scrollWidth<=e.clientWidth+1'),(name,'stats clipping')
     assert not errors,(name,errors)
     row={'cell':name,'http':response.status,'html_sha256':hashlib.sha256(response.body()).hexdigest(),'funds':len(before),'native_disclosures':True,'locale_and_fund_order_preserved':True,'help_height':summary.bounding_box()['height'],'overflow':overflow,'page_errors':errors,'failed_responses':failed,'passed':True};results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);p.close()
  browser.close()
finally:
 if server:server.shutdown();server.server_close()
 (args.output_dir/'results.json').write_text(json.dumps({'mode':'public anonymous no interception' if args.base_url else 'local immutable public-shell fixture, no protected payloads or response interception','cells':results},indent=2,ensure_ascii=False)+'\n')
