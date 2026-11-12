#!/usr/bin/env python3
"""Exercise the actual D05 native Cycles candidate on an authorized local browser.

No auth changes, external network, production writes or substituted chart engine.
The preview carries archived-source labels; equal sessions are not PIT proof.
"""
from __future__ import annotations
import argparse, functools, hashlib, http.server, json, threading
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser();parser.add_argument('--preview',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--single',action='store_true');args=parser.parse_args()
args.out.mkdir(parents=True,exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*_args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(args.preview.resolve())))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
cases=[(1440,1000,'dark','en'),(1440,1000,'light','en'),(1440,1000,'dark','zh'),(1440,1000,'light','zh'),(768,1024,'light','en'),(768,1024,'dark','zh'),(390,844,'dark','en'),(390,844,'light','en'),(390,844,'dark','zh'),(390,844,'light','zh'),(320,740,'dark','zh')]
if args.single:cases=cases[:1]
results=[];active=None;page=None
try:
 with sync_playwright() as tool:
  browser=tool.chromium.launch(headless=True,chromium_sandbox=True)
  try:
   for width,height,theme,lang in cases:
    active=f'{width}-{theme}-{lang}';errors=[];failed=[]
    context=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce');page=context.new_page();page.set_default_timeout(12000)
    context.add_init_script(f"localStorage.setItem('theme',{json.dumps(theme)});localStorage.setItem('lang',{json.dumps(lang)});")
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:failed.append({'url':urlsplit(r.url).path,'status':r.status}) if r.status>=400 else None)
    page.route('**/*',lambda r:r.continue_() if urlsplit(r.request.url).netloc==urlsplit(base).netloc and r.request.method=='GET' else r.abort())
    page.goto(base+'/sector_central.html?g=XLE#map',wait_until='networkidle')
    assert page.locator('body').get_attribute('data-d05-fixture')=='archived-source'
    page.locator('#mr-cycle-link').wait_for()
    assert page.locator('#sc-chart svg').count()==0,'hidden chart mounted in map'
    page.locator('.mr-segbtn[data-h="obs"]').click();page.locator('#mr-cycle-link').click()
    page.wait_for_function("['applied','source_mismatch','source_unavailable','unsupported'].includes(document.querySelector('#sc-cycle-status').dataset.state)")
    source_state=page.locator('#sc-cycle-status').get_attribute('data-state')
    if source_state=='source_mismatch':
     assert not page.locator('#sc-native-study').is_visible()
     page.screenshot(path=str(args.out/(active+'-mismatch.png')),full_page=True)
     page.locator('#sc-cycle-latest').click()
    page.wait_for_function("document.querySelector('#sc-cycle-status').dataset.state==='applied'")
    assert urlsplit(page.url).fragment=='cycles' and parse_qs(urlsplit(page.url).query)['g']==['XLE']
    page.locator('#sc-chart svg').wait_for();assert page.locator('#sc-chart svg').count()==1
    assert page.locator('#sc-chart').bounding_box()['width']>200
    assert 'on' in page.locator('.cyc-chip[data-id="xle"]').get_attribute('class')
    # Desktop exposes advanced controls inline; only narrow layouts have a disclosure.
    if page.locator('#sc-adv-toggle').is_visible():page.locator('#sc-adv-toggle').click()
    assert page.locator('#sc-advbody').is_visible(),'advanced controls must be reachable'
    page.locator('#sc-modes [data-mode="price"]').click();page.locator('#sc-scale [data-scale="linear"]').click()
    page.locator('#sc-zoom [data-i="3"]').click();page.locator('#sc-zreset').click()
    assert page.locator('#sc-scale [data-scale="linear"]').get_attribute('aria-pressed')=='true'
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1'),'horizontal overflow'
    page.locator('#sc-cycle-heading').scroll_into_view_if_needed();page.screenshot(path=str(args.out/(active+'.png')),full_page=True)
    page.locator('#sc-tabs [data-fam="baskets"]').click()
    assert parse_qs(urlsplit(page.url).query)['cycleFamily']==['baskets']
    assert 'cycle' not in parse_qs(urlsplit(page.url).query)
    page.locator('#sc-cycle-return').click();page.wait_for_url('**/sector_central.html?g=XLE#map')
    assert page.locator('.mr-segbtn[data-h="obs"]').get_attribute('aria-pressed')=='true'
    page.wait_for_function("document.activeElement.id==='mr-cycle-link'")
    page.go_forward();page.wait_for_url('**#cycles')
    assert page.locator('#sc-tabs [data-fam="baskets"]').get_attribute('aria-pressed')=='true'
    assert page.locator('#sc-chart svg').count()==1
    assert errors==[],errors
    results.append({'width':width,'height':height,'theme':theme,'lang':lang,'sourceState':source_state,'status':'passed','httpFailures':failed})
    context.close();page=None
   version=browser.version
  except Exception:
   if page:
    page.screenshot(path=str(args.out/(active+'-failure.png')),full_page=True)
    (args.out/'failure-details.json').write_text(json.dumps({'case':active,'errors':errors,'httpFailures':failed,'url':page.url,'body':page.locator('body').inner_text()[:14000]},indent=2)+'\n')
   raise
  finally:browser.close()
 report={'status':'passed','candidate':'9906c882d56e5bed829b2d11aa7b837c5b7abc7f','browser':version,'cases':results,
  'served_asset_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.preview.glob('*') if p.suffix in ('.html','.js','.css')}}
 (args.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':'passed','cases':len(results),'out':str(args.out)}))
except Exception as exc:
 (args.out/'result.json').write_text(json.dumps({'status':'failed','completed':results,'case':active,'error':str(exc)},indent=2)+'\n');raise
finally:server.shutdown();server.server_close();thread.join(timeout=2)
