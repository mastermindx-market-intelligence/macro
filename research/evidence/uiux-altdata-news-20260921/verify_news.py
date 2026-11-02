"""Use native controls; local cases explicitly simulate same-origin public/gated reads."""
from __future__ import annotations
import argparse, json, hashlib, threading
from pathlib import Path
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[2]
ap=argparse.ArgumentParser();ap.add_argument('--base-url');ap.add_argument('--output-dir');args=ap.parse_args()
out=Path(args.output_dir) if args.output_dir else HERE/'browser';out.mkdir(parents=True,exist_ok=True)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*_):pass
server=None
if args.base_url:base=args.base_url.rstrip('/')
else:
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(ROOT/'site')));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
fixtures={
 'altdata/mastermind.json':{'signals':[{'ticker':'EXAMPLE_B','signal_score':75},{'ticker':'EXAMPLE_A','signal_score':60}]},
 'news/by_ticker.json':{'tickers':{'EXAMPLE_B':{'top':[{'title':'Illustrative related headline','title_zh':'示例相关标题','url':'https://example.invalid/news/b','source':'Fixture source'}]},'EXAMPLE_A':{'top':[{'title':'Second illustrative headline','title_zh':'第二条示例标题','url':'https://example.invalid/news/a'}]}}},
 'news/financial.json':{'market':[]}}
results=[]
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  for device,w,h in [('desktop',1440,900),('mobile',390,844)]:
   for lang in ['en','zh']:
    for theme in ['dark','light']:
     name=f'{device}-{lang}-{theme}';mobile=device=='mobile';mode={'value':'gated'};pending=[];calls=[]
     p=browser.new_page(viewport={'width':w,'height':h},is_mobile=mobile,has_touch=mobile,reduced_motion='reduce');errors=[]
     p.on('pageerror',lambda e,errors=errors:errors.append(str(e)))
     p.add_init_script(f"localStorage.setItem('lang','{lang}');localStorage.setItem('theme','{theme}');localStorage.removeItem('themeAuto');")
     if not args.base_url:
      def intercept(route):
       key=urlparse(route.request.url).path.lstrip('/');calls.append(key)
       if mode['value']=='pending':pending.append((route,key));return
       route.fulfill(status=401 if mode['value']=='gated' else 503,content_type='application/json',body='{}')
      for path in fixtures:p.route('**/'+path,intercept)
     response=p.goto(base+'/alt_data.html',wait_until='domcontentloaded',timeout=30000);assert response and response.status==200
     document_digest=hashlib.sha256(response.body()).hexdigest()
     p.wait_for_function("document.querySelector('#sid-news')?.getAttribute('aria-busy')==='false'")
     box=p.locator('#sid-news');box.scroll_into_view_if_needed();status=p.locator('#sid-news-status');retry=p.locator('#sid-news-retry')
     assert box.get_attribute('data-state')=='gated',status.inner_text()
     assert ('登录' in status.inner_text()) if lang=='zh' else ('Sign in' in status.inner_text())
     assert not retry.is_visible() and p.locator('#sid-news-open').is_visible()
     assert not p.locator('#sid-news-results').is_visible()
     assert 'not built' not in box.inner_text() and 'daily build' not in box.inner_text()
     assert status.get_attribute('role')=='status'
     p.screenshot(path=str(out/(name+'-gated.png')))
     if not args.base_url:
      mode['value']='unavailable';p.reload(wait_until='domcontentloaded');p.wait_for_function("document.querySelector('#sid-news')?.dataset.state==='unavailable'")
      assert retry.is_visible();retry.scroll_into_view_if_needed();assert retry.bounding_box()['height']>=40
      # Change language using the real shared Settings controls, without touching renderer internals.
      p.locator('.nav-settings-btn').click();p.locator('.settings-pop .lang-toggle').click()
      other='zh' if lang=='en' else 'en';assert p.locator('html').get_attribute('data-lang')==other
      assert ('暂时' in status.inner_text()) if other=='zh' else ('unavailable' in status.inner_text())
      p.keyboard.press('Escape');retry.scroll_into_view_if_needed();before=len(calls);assert before==6
      retry.focus();mode['value']='pending'
      if mobile:retry.tap()
      else:p.keyboard.press('Enter')
      p.wait_for_function("document.querySelector('#sid-news').getAttribute('aria-busy')==='true'")
      assert retry.is_disabled();p.keyboard.press('Space');p.wait_for_timeout(100)
      assert len(calls)==before+3 and len(pending)==3,('duplicate request',calls)
      for route,key in pending:route.fulfill(status=200,content_type='application/json',body=json.dumps(fixtures[key]))
      p.wait_for_function("document.querySelector('#sid-news')?.dataset.state==='related'")
      assert p.locator('#sid-news-open').evaluate('e=>document.activeElement===e')
      assert not retry.is_visible();assert box.get_attribute('aria-busy')=='false'
      assert p.locator('#sid-news-results .sid-news-row > b').all_text_contents()==['EXAMPLE_B','EXAMPLE_A']
      titles=p.locator('#sid-news-results .sid-news-title:visible').all_inner_texts()
      assert ('示例相关标题' in titles[0]) if other=='zh' else ('Illustrative related headline' in titles[0])
      assert 'alt signal' not in box.inner_text();box.scroll_into_view_if_needed();p.screenshot(path=str(out/(name+'-related-fixture.png')))
     overflow=p.evaluate('document.documentElement.scrollWidth-document.documentElement.clientWidth')
     assert overflow<=1,(name,overflow);assert not errors,(name,errors)
     row={'cell':name,'http':response.status,'html_sha256':document_digest,'honest_anonymous_gate':True,'native_retry_and_locale':not bool(args.base_url),'single_flight_delayed_retry':not bool(args.base_url),'safe_focus_recovery':not bool(args.base_url),'fixture_headline_order_and_translation':not bool(args.base_url),'overflow':overflow,'page_errors':errors,'passed':True}
     results.append(row);print(json.dumps(row),flush=True);p.close()
  browser.close()
finally:
 if server:server.shutdown();server.server_close()
 (out/'results.json').write_text(json.dumps({'mode':'public anonymous; no interception' if args.base_url else 'local; explicit 401/503/delayed-success fixtures, illustrative non-live headlines','cells':results},indent=2)+'\n')
