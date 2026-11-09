from pathlib import Path
import importlib.util,hashlib,json,threading
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from playwright.sync_api import sync_playwright
r=Path("/Volumes/Mastermind/agent-workspaces/verify/crypto-snapshot-20261109-0cfg9psm");out=r/'current-return-injection-diagnostic.json'
assert not out.exists()
source=json.loads((r/'current-return-source-receipt.json').read_text())
for path,m in source['changed'].items():assert hashlib.sha256((r/path).read_bytes()).hexdigest()==m['sha256'],path
spec=importlib.util.spec_from_file_location('r4_browser',r/'tests/test_crypto_intelligence_r4_browser.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Quiet(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(r/'site')))
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
url=f'http://127.0.0.1:{server.server_address[1]}/crypto-r4.html'
fault="""() => {
 window.addEventListener('popstate', () => {
  if(!window.__faultArmed)return;
  window.__faultArmed=false;
  window.__faultObserved={panel:document.getElementById('cri-dialog-body').dataset.panel,
    renderedAddress:document.getElementById('crypto-intelligence').dataset.renderedAddress,address:location.href};
  const metadata=Object.assign({},history.state);
  if(metadata.reading){metadata.reading=Object.assign({},metadata.reading,{revision:'another-publication'});
    history.replaceState(metadata,'',location.href);}
 },{capture:true});
}"""
results=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True,executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
  for timing in ['after_application','before_application']:
   context=m._context(browser,url,viewport={'width':390,'height':844});page=context.new_page();page.set_default_timeout(4500)
   m._freeze_time(page)
   page.add_init_script("localStorage.setItem('lang','en');localStorage.setItem('theme','dark');")
   if timing=='before_application':page.add_init_script('('+fault+')();')
   page.goto(url+'?lang=en#scenarios?h=30',wait_until='load')
   if timing=='after_application':page.evaluate(fault)
   m._open_scenario(page);page.locator('#cri-dialog-body summary').click();m._review_saved(page)
   page.evaluate('window.__faultArmed=true')
   page.locator('#cri-dialog').get_by_role('button',name='← Scenario details',exact=True).click()
   page.wait_for_function("() => document.getElementById('cri-dialog-body').dataset.panel==='scenario:continuation' && window.__faultObserved")
   results.append({'installation':timing,'at_fault':page.evaluate('__faultObserved'),
      'disclosure_open_after':page.locator('#cri-dialog-body details').evaluate('n=>n.open')})
   context.close()
  version=browser.version;browser.close()
finally:
 server.shutdown();server.server_close();thread.join(timeout=5)
receipt={'source_assets':source['assets'],'browser':version,'results':results,'observations':m._OBSERVATIONS,'purpose':'Diagnose fault-injection timing only; not additional product acceptance.'}
out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
