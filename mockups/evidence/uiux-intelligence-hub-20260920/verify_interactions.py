"""Reproduce the real View all path without invoking private renderer hooks."""
from pathlib import Path
from functools import partial
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
import hashlib,json,threading,argparse
from playwright.sync_api import sync_playwright
p=argparse.ArgumentParser();p.add_argument('--base-url');p.add_argument('--output-dir');a=p.parse_args()
root=Path(__file__).resolve().parents[3];out=Path(a.output_dir) if a.output_dir else Path(__file__).parent;out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=None
if a.base_url:base=a.base_url.rstrip('/')
else:
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root/'site')));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
rows=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for device,width,height in [('desktop',1440,900),('mobile',390,844)]:
   for lang in ['en','zh']:
    for theme in ['dark','light']:
     key=f'{device}-{lang}-{theme}';page=browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce');errors=[];page.on('pageerror',lambda e,errs=errors:errs.append(str(e)))
     page.add_init_script(f"localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');localStorage.setItem('lang','{lang}');")
     response=page.goto(base+'/intelligence_hub.html',wait_until='domcontentloaded');page.wait_for_timeout(400)
     assert response and response.status==200,key
     digest=hashlib.sha256(response.body()).hexdigest();assert digest==hashlib.sha256((root/'site/intelligence_hub.html').read_bytes()).hexdigest(),key
     assert page.locator('html').get_attribute('data-lang')==lang and page.locator('html').get_attribute('data-theme')==theme,key
     ledger=page.locator('.lst-wrap').filter(has=page.locator('.led')).first
     ledger.locator('button.lst-more').click();page.wait_for_timeout(100)
     dialog=page.locator('[role="dialog"]').filter(has=page.locator('.led-row')).last
     assert dialog.is_visible(),key
     assert dialog.locator('.led-row').count()==30,key
     analysis=dialog.locator('.led-analysis').first
     width_ratio=analysis.evaluate('e=>e.getBoundingClientRect().width/e.closest(".led-row").getBoundingClientRect().width')
     if device=='mobile':assert width_ratio>=0.70,(key,width_ratio)
     texts=dialog.locator('.watch').all_inner_texts();assert len(texts)==2,key
     assert all('subject_ticker' not in t and "'check':" not in t and 'horizon_d' not in t for t in texts),key
     assert 'Developer momentum declines' in ' '.join(texts),key
     assert dialog.locator('.chip.en-buy').inner_text().strip().lower()==('可复核' if lang=='zh' else 'ready to review'),key
     page.screenshot(path=str(out/(key+'-view-all.png')))
     page.keyboard.press('Escape');assert not dialog.is_visible(),key
     overflow=page.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=1 and not errors,(key,overflow,errors)
     result={'cell':key,'http':response.status,'html_sha256':digest,'rows':30,'human_conditions':len(texts),'analysis_width_ratio':round(width_ratio,3),'overflow':overflow,'page_errors':errors,'passed':True};rows.append(result);print(json.dumps(result),flush=True);page.close()
  browser.close()
finally:
 if server:server.shutdown();server.server_close()
 (out/'interaction-results.json').write_text(json.dumps({'method':'Actual View all click, row/text geometry read and Escape. No data injection or private renderer invocation.','cells':rows},indent=2)+'\n')
