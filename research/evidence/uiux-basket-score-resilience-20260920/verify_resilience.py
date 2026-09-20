"""Real page interaction under explicit optional-data failures; no member impersonation."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import argparse,hashlib,json,threading
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser();ap.add_argument('--base-url');ap.add_argument('--site-dir');ap.add_argument('--output-dir');ap.add_argument('--expect-missing',action='store_true');a=ap.parse_args()
root=Path(__file__).resolve().parents[3];site=Path(a.site_dir) if a.site_dir else root/'site';out=Path(a.output_dir) if a.output_dir else Path(__file__).parent;out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=None
if a.base_url:base=a.base_url.rstrip('/')
else:
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(site)));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
results=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True)
  for route in ['basket/ai_semiconductors.html','basket_china/cn_solar.html']:
   for device,width,height in [('desktop',1440,900),('mobile',390,844)]:
    for lang in ['en','zh']:
     for theme in ['dark','light']:
      page=b.new_page(viewport={'width':width,'height':height},reduced_motion='reduce');errors=[];responses=[]
      page.on('pageerror',lambda e,errs=errors:errs.append(str(e)))
      page.on('response',lambda r,rs=responses:rs.append({'url':r.url,'status':r.status}) if any(x in r.url for x in ['/live/','/basketdata/','/crossmarketdata/']) else None)
      page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');localStorage.setItem('lang','{lang}');")
      # Local proof forces only optional-data failures; public proof intercepts nothing.
      if not a.base_url:
       for pattern in ['**/live/*.json','**/basketdata/*.json','**/crossmarketdata/*.json','**/policy_lever.json']:
        page.route(pattern,lambda r:r.fulfill(status=401,content_type='application/json',body='{"error":"authentication_required"}'))
      response=page.goto(base+'/'+route,wait_until='domcontentloaded',timeout=30000);assert response and response.status==200
      page.wait_for_timeout(300);detail=page.locator('details.ftr-anatomy-disclosure');label=f'{route.replace("/","-")}-{device}-{lang}-{theme}'
      if a.expect_missing:
       assert detail.count()==0,(label,'old defect not discriminated')
      else:
       assert detail.count()==1,(label,'score depends on optional data')
       assert detail.get_attribute('open') is None,label
       detail.locator('summary').click();assert detail.get_attribute('open') is not None and detail.locator('.ftr-anatomy-card').is_visible(),label
       # Sorting reconstructs #app; render must restore score details exactly once.
       page.locator('#hold th[data-s="recommend"]').click()
       detail=page.locator('details.ftr-anatomy-disclosure');assert detail.count()==1,label
       detail.locator('summary').click();assert detail.locator('.ftr-anatomy-card').is_visible(),label
       assert page.locator('.ftr-live-strip').count()==0,(label,'invented live data')
       assert page.locator('#hold tbody tr').count()>0,label
       assert page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')<=1,label
       assert not errors,(label,errors)
       page.screenshot(path=str(out/(label+'.png')))
      result={'cell':label,'http':response.status,'optional_statuses':sorted({r['status'] for r in responses}),'score_details':detail.count(),'page_errors':errors,'html_sha256':hashlib.sha256(response.body()).hexdigest(),'passed':True};results.append(result);print(json.dumps(result),flush=True);page.close()
  b.close()
finally:
 if server:server.shutdown();server.server_close()
 (out/'results.json').write_text(json.dumps({'mode':'public production' if a.base_url else 'local browser with explicitly forced optional-data 401s','expected_prior_defect':a.expect_missing,'results':results},indent=2)+'\n')
