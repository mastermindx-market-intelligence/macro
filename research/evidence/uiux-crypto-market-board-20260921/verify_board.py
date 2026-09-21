"""Exercise the actual Crypto table and native disclosure; no data interception."""
from __future__ import annotations
import argparse,hashlib,json,threading
from pathlib import Path
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser();ap.add_argument('--site-dir',type=Path);ap.add_argument('--base-url');ap.add_argument('--output-dir',type=Path,required=True);args=ap.parse_args()
assert args.site_dir or args.base_url
out=args.output_dir;out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*_):pass
server=None
if args.base_url:base=args.base_url.rstrip('/')
else:
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(args.site_dir)))
 threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
rows=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for device,w,h in [('desktop',1440,900),('tablet',768,1024),('mobile',390,844),('narrow',320,740)]:
   for lang in ['en','zh']:
    for theme in ['dark','light']:
     label=f'{device}-{lang}-{theme}';mobile=w<500
     p=browser.new_page(viewport={'width':w,'height':h},is_mobile=mobile,has_touch=mobile,reduced_motion='reduce')
     p.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');")
     errors=[];p.on('pageerror',lambda e,errors=errors:errors.append(str(e)))
     r=p.goto(base+'/crypto.html',wait_until='domcontentloaded',timeout=30000);assert r and r.status==200
     digest=hashlib.sha256(r.body()).hexdigest();p.wait_for_timeout(500)
     table=p.get_by_role('table',name='市场看板' if lang=='zh' else 'Market Board');assert table.count()==1
     originals=p.locator('.market-row:not(.market-head)');n=originals.count();assert n>0
     order=originals.locator('.asset b').all_text_contents()
     assert table.get_by_role('rowheader').count()==n
     assert table.get_by_role('columnheader').count()==(3 if w<=720 else 5)
     assert ('每日快照' if lang=='zh' else 'Daily snapshot') in p.locator('.hero-meta').inner_text()
     # Page-wide overflow checks miss clipping inside an overflow-hidden shelf.
     checks=originals.evaluate_all('''els=>els.map(row=>{
       const rb=row.getBoundingClientRect();
       let bad=[];
       for(const sel of ['.asset b','.asset small','.market-value','.market-change']){
         const el=row.querySelector(sel);if(!el)continue;
         // Wide layouts intentionally ellipsize names; the unchanged full name is available as its title.
         if(sel==='.asset small' && innerWidth>720){ if(el.title!==el.textContent)bad.push({sel,missingTitle:true}); continue; }
         const r=el.getBoundingClientRect();const style=getComputedStyle(el);
         const range=document.createRange();range.selectNodeContents(el);const text=range.getBoundingClientRect();
         if(r.width>0 && (el.scrollWidth>el.clientWidth+1 || text.right>rb.right+1 || text.left<rb.left-1))
           bad.push({sel,text:el.textContent,scroll:el.scrollWidth,client:el.clientWidth,right:text.right,rowRight:rb.right});
       }
       return {row:row.querySelector('.asset b').textContent,bad,scroll:row.scrollWidth,client:row.clientWidth};
     })''')
     assert all(not x['bad'] for x in checks),(label,checks)
     assert all(x['scroll']<=x['client']+1 for x in checks),(label,checks)
     p.locator('#crypto-market-title').scroll_into_view_if_needed();p.screenshot(path=str(out/(label+'-board.png')))
     detail=p.locator('#market-board details.more-market');assert detail.count()==1
     summary=detail.locator('summary');assert summary.bounding_box()['height']>=40
     # Focus the actual summary; activation comes only from real keys / touch.
     summary.focus();p.keyboard.press('Enter');assert detail.get_attribute('open') is not None
     assert detail.locator('.compact-asset').first.is_visible();extra=detail.locator('.compact-asset').count()
     p.keyboard.press('Space');assert detail.get_attribute('open') is None
     if mobile:summary.tap()
     else:p.keyboard.press('Enter')
     assert detail.get_attribute('open') is not None
     p.locator('.nav-settings-btn').click();p.locator('.settings-pop .lang-toggle').click();other='zh' if lang=='en' else 'en'
     assert p.locator('html').get_attribute('data-lang')==other
     assert ('更多资产' if other=='zh' else 'More assets')==summary.inner_text().strip()
     assert detail.get_attribute('open') is not None and originals.locator('.asset b').all_text_contents()==order
     p.keyboard.press('Escape');summary.focus();p.screenshot(path=str(out/(label+'-disclosure.png')))
     overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=1 and not errors,(label,overflow,errors)
     result={'cell':label,'http':r.status,'page_sha256':digest,'rows':n,'more_rows':extra,'quotes_and_symbols_in_bounds':True,'compact_full_names_wrap':w<=720,'table_headers':3 if w<=720 else 5,'native_enter_space':True,'native_touch':mobile,'locale_open_state_and_order_preserved':True,'overflow':overflow,'page_errors':errors,'passed':True};rows.append(result);print(json.dumps(result),flush=True);p.close()
  browser.close()
finally:
 if server:server.shutdown();server.server_close()
 (out/'results.json').write_text(json.dumps({'mode':'public no interception' if args.base_url else 'exact-source static fixture; no API/data interception; no authenticated data claim','cells':rows},indent=2)+'\n')
