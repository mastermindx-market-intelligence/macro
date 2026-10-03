from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
import hashlib, json, subprocess, threading
from playwright.sync_api import sync_playwright
out=Path('/private/tmp/china-r9-release-gates-20261003')
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(Path('site').resolve())))
threading.Thread(target=server.serve_forever,daemon=True).start()
report={'source_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'observed_at':datetime.now(timezone.utc).isoformat(),
 'proof_class':'local_actual_built_page_with_explicit_synthetic_auth_and_payload',
 'real_gateway_authentication':False,'screenshots':[],'steps':[],'errors':[]}
good=json.loads(Path('site/china_economy_detail.json').read_text())
old=deepcopy(good);old['snapshot_id']=old['client']['snapshot_id']='b'*64
state={'body':old,'calls':0}
def fixture_auth(page):
    page.evaluate('''()=>{window.MDXAuth.client=()=>Promise.resolve({auth:{getSession:()=>Promise.resolve({data:{session:{user:{id:'r9-local-test-only'}}}})}});window.dispatchEvent(new CustomEvent('mdx-auth',{detail:{user:{id:'r9-local-test-only'},event:'SIGNED_IN'}}));}''')
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True)
  page=browser.new_page(viewport={'width':1440,'height':1000})
  page.on('pageerror',lambda error: report['errors'].append(str(error)))
  def detail(route):
   state['calls']+=1
   route.fulfill(status=200,content_type='application/json',body=json.dumps(state['body']))
  page.route('**/china_economy_detail.json',detail)
  url=f'http://127.0.0.1:{server.server_port}/china.html'
  page.goto(url,wait_until='domcontentloaded',timeout=40000)
  page.wait_for_function("window.MDXAuth && document.getElementById('china-economy')",timeout=20000)
  page.wait_for_timeout(1200)
  assert state['calls']==0
  report['steps'].append('anonymous: zero protected fetches')
  fixture_auth(page)
  page.wait_for_function("document.getElementById('china-economy').dataset.ecoDetailState==='outdated'")
  assert page.locator('#eco-library').count()==0
  assert page.locator('[data-eco-retry]').count()==0
  assert page.evaluate('!window.EconomyLens')
  report['steps'].append('same-month different-snapshot payload withheld before detail installation')
  for width in (1440,390):
   page.set_viewport_size({'width':width,'height':1000 if width==1440 else 844})
   for theme in ('dark','light'):
    for locale in ('en','zh'):
     page.evaluate('''p=>{if(typeof window.setTheme==='function')window.setTheme(p.theme);else document.documentElement.dataset.theme=p.theme;document.documentElement.dataset.lang=p.locale;}''',{'theme':theme,'locale':locale})
     page.wait_for_timeout(1400)
     lock=page.locator('#eco-detail-lock');lock.scroll_into_view_if_needed()
     text=lock.locator('p').inner_text()
     if locale=='zh':assert '刷新页面' in text and 'Refresh the page' not in text,text
     else:assert 'Refresh the page' in text and '请刷新' not in text,text
     assert page.locator('[data-eco-reload]').is_visible()
     assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
     filename=f'snapshot-refresh-{width}-{theme}-{locale}.png'
     png=page.locator('#eco-detail-slot').screenshot(path=str(out/filename))
     report['screenshots'].append({'path':filename,'width':width,'theme':theme,'locale':locale,'sha256':hashlib.sha256(png).hexdigest(),'bytes':len(png)})
  assert state['calls']==1
  report['steps'].append('8 EN/ZH dark/light desktop/mobile refresh states checked; no automatic retry')
  state['body']=good
  page.locator('[data-eco-reload]').click()
  page.wait_for_load_state('domcontentloaded')
  page.wait_for_function("window.MDXAuth && document.getElementById('china-economy')")
  page.wait_for_timeout(1200)
  assert state['calls']==1
  fixture_auth(page)
  page.wait_for_selector('#eco-library',timeout=15000)
  assert page.locator('#eco-metric-select option').count()==128
  page.locator('#eco-metric-select').select_option('pmi_medium')
  assert page.locator('#eco-selected-metric').inner_text()
  assert state['calls']==2
  report['steps'].append('explicit page refresh + matching fixture snapshot restores 128-option working detail')
  assert not report['errors'],report['errors']
  report['result']='PASS';report['protected_fetches']=state['calls']
  browser.close()
finally:
 server.shutdown();server.server_close()
 (out/'browser-snapshot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
