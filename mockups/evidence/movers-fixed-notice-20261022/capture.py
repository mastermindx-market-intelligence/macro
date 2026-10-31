from pathlib import Path
import sys,json,hashlib,threading,http.server,importlib.util,datetime,subprocess,os
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
REPO=Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/shared-shell-movers-owner-20261022-f331e754beb1fa42');OUT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('canonical_capture',REPO/'scripts/capture_page_evidence.py');cap=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cap;spec.loader.exec_module(cap)
HEAD=os.environ.get('CAPTURE_SOURCE_HEAD','5a05f24dc3648adc32aa6bb5edc1dafe717b4120')
assets={}
for f in ['movers.html','theme.css','shared_shell.css','shared_shell_bridge.js','product-nav-icons.css','favicon.svg','favicon.ico']:
 p=REPO/'site'/f
 if p.exists():assets['/'+f]=subprocess.check_output(['git','show',HEAD+':site/'+f],cwd=REPO)
for font in ['Inter-400.woff2','Inter-600.woff2']:
 assets['/fonts/'+font]=subprocess.check_output(['git','show',HEAD+':site/fonts/'+font],cwd=REPO)
source_sha=hashlib.sha256(assets['/movers.html']).hexdigest();assert source_sha==os.environ.get('CAPTURE_PAGE_SHA','4cae02d74ec354ac959ab8e3cca178eda2b93437e7d08da04a4ff88a968df5c7')
class Child(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  p=urlsplit(self.path).path;b=assets.get(p)
  if b is None:self.send_response(404);self.end_headers();return
  self.send_response(200);self.send_header('Content-Type','font/woff2' if p.endswith('.woff2') else 'text/css' if p.endswith('.css') else 'text/javascript' if p.endswith('.js') else 'text/html');self.end_headers();self.wfile.write(b)
child=http.server.ThreadingHTTPServer(('127.0.0.1',0),Child);base='http://127.0.0.1:'+str(child.server_port)
class Parent(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(f'<!doctype html><html><body style="margin:0"><iframe title="Movers notice local pre-INIT preview" style="display:block;border:0;width:100vw;height:100vh" src="{base}/movers.html?mmx_shell=1&mmx_generation=visual_preview"></iframe></body></html>'.encode())
parent=http.server.ThreadingHTTPServer(('127.0.0.1',3100),Parent)
for s in [parent,child]:threading.Thread(target=s.serve_forever,daemon=True).start()
measurements=[]
class Driver:
 def __init__(self,browser):self.browser=browser
 def capture(self,*,url,cell,timeout_s):
  ctx=self.browser.new_context(viewport={'width':cell.width,'height':cell.height},locale='zh-CN' if cell.locale=='zh' else 'en-US',color_scheme=cell.theme,device_scale_factor=1)
  ctx.add_init_script(cap.state_seed_source({'theme':cell.theme,'locale':cell.locale}));ctx.add_init_script(cap.timing_init_source())
  ctx.route('**/*',lambda r:r.continue_() if urlsplit(r.request.url).hostname=='127.0.0.1' else r.abort())
  page=ctx.new_page();errors=[];failures=[];page.on('pageerror',lambda e:errors.append({'text':str(e),'source_url':None}));page.on('response',lambda r:failures.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
  try:
   page.goto('http://127.0.0.1:3100/',wait_until='load',timeout=timeout_s*1000)
   frame=next(f for f in page.frames if f.url.startswith(base+'/movers.html'))
   frame.locator('body[data-mmx-movers-redirect="1"]').wait_for()
   applied=frame.evaluate(cap._APPLY_STATE_SCRIPT,{'theme':cell.theme,'locale':cell.locale});page.wait_for_timeout(100)
   assert frame.evaluate('typeof window.MMXSharedShell.navigate')=='function'
   observed=frame.evaluate(cap._OBSERVER_SCRIPT,dict(cap.DEFAULT_OBSERVER_CONFIG));timing=frame.evaluate(cap._TIMING_SNAPSHOT_SCRIPT)
   geometry=frame.evaluate('''()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,main:document.querySelector('main').getBoundingClientRect().toJSON(),body:document.body.innerText,background:getComputedStyle(document.body).backgroundColor,text:getComputedStyle(document.body).color,paragraph:getComputedStyle(document.querySelector('p')).color,link:getComputedStyle(document.querySelector('a')).color,mainBackground:getComputedStyle(document.querySelector('main')).backgroundColor})''')
   geometry.update({'cell':cell.cell_id,'actualChildUrl':frame.url,'applied':applied,'errors':errors,'failedResponses':failures,'mode':'real bridge pre-INIT local iframe; no INIT sent; unmodified source/navigation script'})
   measurements.append(geometry)
   png=page.locator('iframe').screenshot()
   return cap.CellObservation(cell_id=cell.cell_id,loaded=True,screenshot_png=png,observed=observed,console_errors=tuple(errors),failed_responses=tuple(failures),applied_theme=applied['theme'],applied_locale=applied['locale'],timing=timing)
  finally:ctx.close()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,executable_path='/Users/chriswong/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell')
  try:
   result=cap.run_capture(rows=[{'page_id':'macro:movers','repo':'macro','priority':'P0','route':'/movers.html','capture_route':'/movers.html','route_kind':'static','themes':['dark','light'],'locales':['en','zh']}],driver=Driver(browser),base_url=base,output_dir=OUT/'evidence',manifest_dir=OUT,viewports=('desktop','mobile'),locales=('en','zh'),themes=('dark','light'),delay_ms=0,timeout_s=10,generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),target={'kind':'local_source_preview_pre_init','base_url':base,'site_dir':str(REPO/'site'),'resolved_sha_or_none':HEAD,'method':'Actual exact-source child in real bridge local iframe held before INIT; no script replacement, no public requests; screenshot iframe viewport'},selection={'mode':'explicit source route','routes':['/movers.html']})
   (OUT/'manifest.json').write_text(json.dumps(result['manifest'],indent=2));(OUT/'measurements.json').write_text(json.dumps(measurements,indent=2));(OUT/'source-identity.json').write_text(json.dumps({'sourceHead':HEAD,'pageSha256':source_sha,'assets':{k:hashlib.sha256(v).hexdigest() for k,v in assets.items()},'canonicalCaptureToolSha256':cap.module_source_sha256(),'localDriverSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))
   print(json.dumps({'totals':result['manifest']['totals'],'overflow':[x['cell'] for x in measurements if x['scrollWidth']>x['width']],'errors':[x for x in measurements if x['errors'] or x['failedResponses']]}))
  finally:browser.close()
finally:
 for s in [parent,child]:s.shutdown();s.server_close()
