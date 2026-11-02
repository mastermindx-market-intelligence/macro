from pathlib import Path
import sys,json,hashlib,threading,http.server,importlib.util,datetime,subprocess,os,mimetypes
from urllib.parse import urlsplit,unquote
from playwright.sync_api import sync_playwright
REPO=Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/shared-shell-reference-release-20261024-8af5db141b6d3314');OUT=Path(__file__).resolve().parent
HEAD=os.environ.get('CAPTURE_SOURCE_HEAD','f9ae97c0890226b7e42b0ab91990aaa4008b7efd'); PAGE_SHA=os.environ.get('CAPTURE_PAGE_SHA','7b551d4c7a601e75d4f1dc018750acf15ac95e9734c17db542997f7c29a8a2b1')
ENV=dict(os.environ,GIT_NO_LAZY_FETCH='1');assets={};missing=[]
def blob(path):return subprocess.check_output(['git','show',HEAD+':'+path],cwd=REPO,env=ENV,stderr=subprocess.DEVNULL)
def load(path):
 if path not in assets:
  try:assets[path]=blob('site/'+path)
  except subprocess.CalledProcessError:return None
 return assets[path]
assert hashlib.sha256(load('reference.html')).hexdigest()==PAGE_SHA
spec=importlib.util.spec_from_file_location('canonical_capture',REPO/'scripts/capture_page_evidence.py');cap=importlib.util.module_from_spec(spec);sys.modules[spec.name]=cap;spec.loader.exec_module(cap)
class Handler(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  path=unquote(urlsplit(self.path).path).lstrip('/');b=load(path) if '..' not in Path(path).parts else None
  if b is None:missing.append(path);self.send_response(404);self.end_headers();return
  self.send_response(200);self.send_header('Content-Type',mimetypes.guess_type(path)[0] or 'application/octet-stream');self.end_headers();self.wfile.write(b)
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);base='http://127.0.0.1:'+str(server.server_port);threading.Thread(target=server.serve_forever,daemon=True).start()
measurements=[];interactions=[]
class Driver:
 def __init__(self,browser):self.browser=browser;self.expanded_done=set()
 def capture(self,*,url,cell,timeout_s):
  ctx=self.browser.new_context(user_agent=cap.USER_AGENT,viewport={'width':cell.width,'height':cell.height},locale='zh-CN' if cell.locale=='zh' else 'en-US',color_scheme=cell.theme,device_scale_factor=1,reduced_motion='reduce')
  ctx.add_init_script(cap.state_seed_source({'theme':cell.theme,'locale':cell.locale}));ctx.add_init_script(cap.timing_init_source())
  external=[]
  def route(r):
   if urlsplit(r.request.url).hostname=='127.0.0.1':r.continue_()
   else:external.append(r.request.url);r.abort()
  ctx.route('**/*',route);page=ctx.new_page();errors=[];failures=[]
  page.on('pageerror',lambda e:errors.append({'text':str(e),'source_url':None}));page.on('response',lambda r:failures.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
  try:
   page.goto(url,wait_until='load',timeout=timeout_s*1000);page.evaluate(cap._APPLY_STATE_SCRIPT,{'theme':cell.theme,'locale':cell.locale});page.evaluate('document.fonts.ready');page.wait_for_timeout(400)
   applied=page.evaluate('()=>({theme:document.documentElement.dataset.theme,locale:document.documentElement.dataset.lang||"en"})')
   applied_force=None
   if cell.force_state is not None:
    applied_force=cap._apply_interaction_force(page,cell.force_state,timeout_ms=3000);page.wait_for_timeout(200)
   observed=page.evaluate(cap._OBSERVER_SCRIPT,dict(cap.DEFAULT_OBSERVER_CONFIG));timing=page.evaluate(cap._TIMING_SNAPSHOT_SCRIPT)
   geometry=page.evaluate('''()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,height:innerHeight,h1:document.querySelector('h1')?.innerText,visibleEntries:[...document.querySelectorAll('.rf-e')].filter(e=>e.getBoundingClientRect().height>0).length,background:getComputedStyle(document.body).backgroundColor,text:getComputedStyle(document.body).color,fonts:document.fonts.status})''')
   geometry.update({'forceState':applied_force,'cell':cell.cell_id,'applied':applied,'errors':errors,'failedResponses':failures,'blockedExternalRequests':list(external)})
   measurements.append(geometry);png=page.screenshot(full_page=True)
   if cell.cell_id not in self.expanded_done and cell.force_state is None and ((cell.width==1440 and cell.theme=='light' and cell.locale=='en') or (cell.width==390 and cell.theme=='dark' and cell.locale=='zh')):
    self.expanded_done.add(cell.cell_id)
    for target in ['evidence-matrix','evidence-trend']:
     selector='#'+target+' > .rf-sum' if target=='evidence-matrix' else '#evidence-matrix a[href="#evidence-trend"]'
     page.locator(selector).click();page.wait_for_function('(id)=>document.querySelector("#"+id).classList.contains("rf-open")',arg=target);page.wait_for_timeout(200)
     row=page.evaluate('''(id)=>{const e=document.getElementById(id),c=getComputedStyle(e);const summary=e.querySelector('.rf-sum'),label=e.querySelector('.rf-label'),lr=label.getBoundingClientRect(),bar=document.querySelector('.rf-bar'),br=bar?.getBoundingClientRect(),hit=document.elementFromPoint(lr.x+lr.width/2,lr.y+lr.height/2);return {labelRect:lr.toJSON(),stickyBarRect:br?.toJSON(),labelUnobscured:!!hit&&summary.contains(hit),labelBelowSticky:lr.top>=Math.max(0,br?.bottom||0),target:id,hash:location.hash,open:e.classList.contains('rf-open'),expanded:e.querySelector('.rf-sum').getAttribute('aria-expanded'),bodyDisplay:getComputedStyle(e.querySelector('.rf-body')).display,width:innerWidth,scrollWidth:document.documentElement.scrollWidth,rect:e.getBoundingClientRect().toJSON(),leftWidth:c.borderLeftWidth,leftColor:c.borderLeftColor,rightWidth:c.borderRightWidth,rightColor:c.borderRightColor,background:c.backgroundColor,text:getComputedStyle(e.querySelector('.rf-def')).color,visibleBody:e.querySelector('.rf-body').innerText}}''',target)
     name=f'{cell.width}-{cell.theme}-{cell.locale}-{target}.png';(OUT/'interactions').mkdir(exist_ok=True);page.screenshot(path=str(OUT/'interactions'/name));row.update({'cell':cell.cell_id,'screenshot':'interactions/'+name});interactions.append(row)
    page.locator('#evidence-trend .rf-close').click();page.wait_for_timeout(200)
    close=page.evaluate('''()=>{const e=document.getElementById('evidence-trend'),s=e.querySelector('.rf-sum'),l=e.querySelector('.rf-label').getBoundingClientRect(),b=document.querySelector('.rf-bar').getBoundingClientRect(),hit=document.elementFromPoint(l.x+l.width/2,l.y+l.height/2);return {target:'close-trend',hash:location.hash,bodyDisplay:getComputedStyle(e.querySelector('.rf-body')).display,expanded:s.getAttribute('aria-expanded'),labelRect:l.toJSON(),stickyBarRect:b.toJSON(),labelUnobscured:!!hit&&s.contains(hit),labelBelowSticky:l.top>=Math.max(0,b.bottom),width:innerWidth,scrollWidth:document.documentElement.scrollWidth}}''')
    close_name=f'{cell.width}-{cell.theme}-{cell.locale}-close-trend.png';page.screenshot(path=str(OUT/'interactions'/close_name));close.update({'cell':cell.cell_id,'screenshot':'interactions/'+close_name});interactions.append(close)
   return cap.CellObservation(cell_id=cell.cell_id,loaded=True,screenshot_png=png,observed=observed,console_errors=tuple(errors),failed_responses=tuple(failures),applied_theme=applied['theme'],applied_locale=applied['locale'],applied_force_state=applied_force,timing=timing)
  finally:ctx.close()
try:
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,executable_path='/Users/chriswong/Library/Caches/ms-playwright/chromium_headless_shell-1234/chrome-headless-shell-mac-arm64/chrome-headless-shell')
  try:
   driver=Driver(browser)
   result=cap.run_capture(rows=[{'page_id':'macro:reference','repo':'macro','priority':'P0','route':'/reference.html','capture_route':'/reference.html','route_kind':'static','themes':['dark','light'],'locales':['en','zh']}],driver=driver,base_url=base,output_dir=OUT/'evidence',manifest_dir=OUT,viewports=('desktop','mobile'),locales=('en','zh'),themes=('dark','light'),delay_ms=0,timeout_s=20,generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),target={'kind':'local_exact_source_preview','base_url':base,'site_dir':str(REPO/'site'),'resolved_sha_or_none':HEAD,'method':'Unmodified immutable site blobs; standalone Reference; exact requested themes/locales applied through canonical capture seam; external requests blocked; no authenticated/public browser'},selection={'mode':'explicit source route','routes':['/reference.html']})
   interaction_result=cap.run_capture(rows=[{'page_id':'macro:reference','repo':'macro','priority':'P0','route':'/reference.html','capture_route':'/reference.html','route_kind':'static','themes':['dark','light'],'locales':['en']}],driver=driver,base_url=base,output_dir=OUT/'evidence',manifest_dir=OUT,viewports=('desktop',),locales=('en',),themes=('dark','light'),delay_ms=0,timeout_s=20,generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),target=result['manifest']['target'],selection={'mode':'governed changed hover/focus presentation','routes':['/reference.html']},force_states=cap.parse_force_states(['summary_hover:hover(#evidence-matrix > .rf-sum)','summary_focus:focus(#evidence-matrix > .rf-sum)']))
   (OUT/'interaction-canonical-raw.json').write_text(json.dumps(interaction_result['manifest'],indent=2))
   forced=[s for s in interaction_result['manifest']['pages'][0]['states'] if s.get('force_state')]
   result['manifest']['pages'][0]['states'].extend(forced)
   result['manifest']['axes']['force_states']=interaction_result['manifest']['axes']['force_states']
   result['manifest']['totals']['states_attempted']+=len(forced);result['manifest']['totals']['states_captured']+=sum(s.get('captured') is True for s in forced)
   result['manifest']['pages'][0]['page_tree_sha']=subprocess.check_output(['git','rev-parse',HEAD+':site/reference.html'],cwd=REPO,text=True).strip()
   (OUT/'manifest.json').write_text(json.dumps(result['manifest'],indent=2));(OUT/'measurements.json').write_text(json.dumps(measurements,indent=2));(OUT/'interactions.json').write_text(json.dumps(interactions,indent=2));(OUT/'source-identity.json').write_text(json.dumps({'sourceHead':HEAD,'pageSha256':PAGE_SHA,'assets':{k:hashlib.sha256(v).hexdigest() for k,v in sorted(assets.items())},'missingAssets':sorted(set(missing)),'canonicalCaptureToolSha256':cap.module_source_sha256(),'localDriverSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))
   print(json.dumps({'totals':result['manifest']['totals'],'overflow':[x['cell'] for x in measurements if x['scrollWidth']>x['width']],'missingAssets':sorted(set(missing)),'errors':[x for x in measurements if x['errors'] or x['failedResponses']],'interactions':[{k:v for k,v in x.items() if k!='visibleBody'} for x in interactions]},indent=2))
  finally:browser.close()
finally:server.shutdown();server.server_close()
