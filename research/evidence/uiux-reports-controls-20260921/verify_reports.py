"""Native Reports controls against immutable candidate HTML; shared assets use public reads only."""
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
import argparse,hashlib,json,threading,re
from playwright.sync_api import sync_playwright
A=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--base-url');ap.add_argument('--site-dir');ap.add_argument('--output-dir');args=ap.parse_args()
site=Path(args.site_dir) if args.site_dir else A.parents[2]/'site'
out=Path(args.output_dir) if args.output_dir else A/'browser';out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*_):pass
 def do_GET(self):
  if self.path.split('?')[0] in ['/wh_banner.js'] or self.path.startswith('/api/'):
   self.send_response(401);self.end_headers();return
  return super().do_GET()
server=None
if args.base_url:base=args.base_url.rstrip('/')
else:
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(site)))
 threading.Thread(target=server.serve_forever,daemon=True).start();base='http://127.0.0.1:'+str(server.server_port)
results=[]
try:
 with sync_playwright() as pw:
  b=pw.chromium.launch(headless=True)
  for device,w,h in [('desktop',1440,900),('mobile',390,844),('narrow',320,740)]:
   for lang in ['en','zh']:
    for theme in ['dark','light']:
     name=f'{device}-{lang}-{theme}';touch=device!='desktop'
     p=b.new_page(viewport={'width':w,'height':h},is_mobile=touch,has_touch=touch,reduced_motion='reduce');errors=[]
     p.on('pageerror',lambda e,errors=errors:errors.append(str(e)))
     p.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');window.__pushes=0;const oldPush=history.pushState.bind(history);history.pushState=function(...a){{window.__pushes++;return oldPush(...a)}}")
     response=p.goto(base+'/reports.html',wait_until='domcontentloaded');assert response.status==200
     pagehash=hashlib.sha256(response.body()).hexdigest(); search=p.locator('#repSearch');sort=p.locator('#repSort');chips=p.locator('#tagBar button')
     total=p.locator('#reportList .rc-node').count();assert total>0
     assert chips.count()>=2 and p.locator('#tagBar [aria-pressed="true"]').count()==1
     heights=chips.evaluate_all('els=>els.map(e=>e.getBoundingClientRect().height)');assert min(heights)>=40
     # Real Tab moves from one topic button to the next; native Enter/Space each activate once.
     chips.first.focus();p.keyboard.press('Tab');chosen=p.evaluate('document.activeElement.dataset.tag');assert chosen and chosen!='all'
     n=p.evaluate('window.__pushes');p.keyboard.press('Enter');assert p.evaluate('window.__pushes')==n+1
     assert p.locator('#tagBar [aria-pressed="true"]').get_attribute('data-tag')==chosen
     n=p.evaluate('window.__pushes');p.keyboard.press('Space');assert p.evaluate('window.__pushes')==n+1
     # Actual Back/Forward restores the existing URL-owned state.
     if touch:chips.first.tap()
     else:chips.first.click()
     p.go_back();assert p.locator('#tagBar [aria-pressed="true"]').get_attribute('data-tag')==chosen
     p.go_forward();assert p.locator('#tagBar [aria-pressed="true"]').get_attribute('data-tag')=='all'
     search.fill('price');sort.select_option('old')
     before={'q':search.input_value(),'sort':sort.input_value(),'url':p.url,'cards':p.locator('#reportList .rc-node:not(.hide) .rc-card').get_attribute('href') if p.locator('#reportList .rc-node:not(.hide) .rc-card').count()==1 else p.locator('#reportList .rc-node:not(.hide)').count()}
     p.locator('.nav-settings-btn').click();p.locator('.settings-pop .lang-toggle').focus();p.keyboard.press('Enter');other='zh' if lang=='en' else 'en'
     assert p.locator('html').get_attribute('data-lang')==other
     assert search.get_attribute('placeholder')==('搜索报告…' if other=='zh' else 'Search reports…')
     assert search.get_attribute('aria-label')==('搜索报告' if other=='zh' else 'Search reports')
     assert sort.locator('option').first.inner_text()==('最新优先' if other=='zh' else 'Newest first')
     count=p.locator('#repCount').inner_text();assert ('篇报告' in count) if other=='zh' else ('report' in count)
     assert search.input_value()==before['q'] and sort.input_value()==before['sort'] and p.url==before['url']
     p.keyboard.press('Escape');search.fill('__uiux_no_report__');clear=p.locator('#repClear2');assert clear.is_visible()
     clear.focus()
     if touch:clear.tap()
     else:p.keyboard.press('Enter')
     assert p.evaluate('document.activeElement.id')=='repSearch'
     assert search.input_value()=='' and p.locator('#tagBar [aria-pressed="true"]').get_attribute('data-tag')=='all'
     assert p.locator('#reportList .rc-node:not(.hide)').count()==total
     # Native chronological sort retains all report hrefs.
     dates=p.locator('#reportList .rc-node').evaluate_all('els=>els.map(e=>e.dataset.date)');assert dates==sorted(dates)
     overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth');assert overflow<=1,(name,overflow)
     assert not errors,(name,errors)
     search.scroll_into_view_if_needed();p.screenshot(path=str(out/(name+'.png')))
     row={'cell':name,'http':200,'html_sha256':pagehash,'native_tab_enter_space':True,'single_activation':True,'native_touch':touch,'keyboard_locale_sync':True,'query_sort_url_preserved':True,'reset_focus_restored':True,'back_forward_restored':True,'archive_count':total,'minimum_topic_height':min(heights),'overflow':overflow,'page_errors':errors,'passed':True};results.append(row);print(json.dumps(row),flush=True);p.close()
  b.close()
finally:
 if server:server.shutdown();server.server_close()
 (out/'results.json').write_text(json.dumps({'mode':'public anonymous; no interception' if args.base_url else 'candidate static fixture; explicit anonymous denial for member-only asset/API; not production acceptance','cases':results},indent=2))
