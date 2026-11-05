from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit
import base64, hashlib, json, mimetypes, time, traceback
ROOT=Path('/Volumes/Mastermind/agent-workspaces/macro/web/d05-native-source-verification-20261104/.pytest_cache/d05-ci-recovery-82c377/china-archive')
SITE=ROOT/'site-candidate-v3'
OUT=ROOT/'browser-candidate-v3';OUT.mkdir(exist_ok=True)
BASE='http://localhost:3100';CHILD='http://localhost:8765'
user={'id':'e2e-user-default','email':'responsive@example.com','aud':'authenticated','app_metadata':{},'user_metadata':{}}
session={'access_token':'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJlMmUtdXNlci1kZWZhdWx0In0.fixture-only','refresh_token':'d05-fixture-only','expires_in':3600,'expires_at':int(time.time())+3600,'token_type':'bearer','user':user}
cookie='base64-'+base64.urlsafe_b64encode(json.dumps(session,separators=(',',':')).encode()).decode().rstrip('=')
report={'candidate_source_sha256':{name:hashlib.sha256((SITE/name).read_bytes()).hexdigest() for name in ['si_workspace_china.js','sector_cycles.js','macro-desk.css','sector_central_china.html']},'schema':'d05.archived_china_browser.v1','fixture_only':True,'fixture_manifest_sha256':hashlib.sha256((ROOT/'fixture_candidate_v3_provenance.json').read_bytes()).hexdigest(),'cases':[]}
def frame(page):
 page.wait_for_function("document.querySelector('main[data-shared-shell-phase]')?.dataset.sharedShellPhase==='ready'",timeout=45000)
 f=page.locator('iframe[data-shared-shell-frame]').element_handle().content_frame()
 assert f
 f.wait_for_function("typeof window.SectorCyclesEvidence==='function'",timeout=40000)
 f.wait_for_function("window.SectorCyclesEvidence().status==='verified'",timeout=40000)
 return f
def facts(f):
 return f.evaluate("""()=>({receipt:SectorCyclesEvidence(),capture:SectorCyclesCapture?.(),meta:{region:SECTOR_CYCLES.meta.region,asOf:SECTOR_CYCLES.meta.asOf,benchmark:SECTOR_CYCLES.meta.benchmark},sectorCount:SECTOR_CYCLES.sectors.length,basketCount:SECTOR_CYCLES.baskets.length,viewButtons:[...document.querySelectorAll('.si-view-btn')].map(e=>e.dataset.view),dossierMounts:document.querySelectorAll('#sc-dossier,#sc-dossier-mount').length,dossierModule:typeof window.SectorDossierCycle,visibleDna:document.querySelectorAll('.sc-dna').length,narrativeKeys:Object.keys(window.SECTOR_NARR||{}),dnaKeys:Object.keys(window.SECTOR_DNA||{}),documentWidth:document.documentElement.scrollWidth,viewport:innerWidth,lang:document.documentElement.dataset.lang,theme:document.documentElement.dataset.theme})""")
def screenshot(page,f,name,case):
 if f.locator('#sc-chart').count():f.locator('#sc-chart').scroll_into_view_if_needed()
 target=OUT/(name+'.png');page.screenshot(path=str(target),full_page=False)
 case.setdefault('screenshots',[]).append({'file':target.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
 case.setdefault('outer_widths',[]).append(page.evaluate("({viewport:innerWidth,document:document.documentElement.scrollWidth})"))
def mobile_surface(f):
 return f.evaluate("""()=>{const probe=e=>{const s=getComputedStyle(e),canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');ctx.fillStyle=s.backgroundColor;ctx.fillRect(0,0,1,1);return {color:s.backgroundColor,alpha:ctx.getImageData(0,0,1,1).data[3],radius:s.borderTopLeftRadius,padding:s.padding,transition:s.transitionDuration}};return {sheet:probe(document.querySelector('#sc-detail')),rail:probe(document.querySelector('.si-side')),panels:probe(document.querySelector('#sc-detail .cyc-panels')),closeHidden:!!document.querySelector('.sc-sheet-x')?.closest('[aria-hidden="true"]')}}""")
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,chromium_sandbox=True)
 for width,height,theme,lang in [(1440,1000,'dark','en'),(390,844,'light','zh'),(390,844,'dark','en')]:
  case={'viewport':[width,height],'theme':theme,'lang':lang,'steps':[],'page_errors':[],'failed_responses':[],'intercepted':[]}
  ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce',has_touch=width<1024)
  ctx.add_init_script("""(({theme,lang})=>{localStorage.setItem('theme',theme);localStorage.setItem('lang',lang);localStorage.setItem('mm.theme',theme);localStorage.setItem('mm.lang',lang);if(location.port==='8765'){window.MM_TERMINAL_BASE='https://app.mastermind-x.com/terminal';window.SUPABASE_CFG={url:'http://localhost:8765/fixture-auth',anonKey:'d05-fixture-only',ref:'d05-native-fixture'};}})("""+json.dumps({'theme':theme,'lang':lang})+");")
  ctx.add_cookies([{'name':'sb-d05-native-fixture-auth-token','value':cookie,'url':CHILD},{'name':'mm_e2e_rs30','value':'1','url':BASE}])
  def route(r):
   url=r.request.url
   if url.startswith(CHILD+'/fixture-auth/auth/v1/user'):
    r.fulfill(status=200,content_type='application/json',body=json.dumps(user));return
   if url.startswith(CHILD+'/'):
    rel=urlsplit(url).path.lstrip('/');candidate=(SITE/rel).resolve()
    if SITE.resolve() in candidate.parents and candidate.is_file():
     case['intercepted'].append(rel)
     r.fulfill(status=200,content_type=mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream',body=candidate.read_bytes());return
    r.continue_();return
   if url.startswith(BASE+'/'):r.continue_();return
   r.abort()
  ctx.route('**/*',route)
  page=ctx.new_page();page.on('pageerror',lambda e:case['page_errors'].append(str(e)))
  page.on('response',lambda r:case['failed_responses'].append({'url':r.url,'status':r.status}) if r.status>=400 and r.url.startswith((BASE,CHILD)) else None)
  prefix=str(width)+'-'+theme+'-'+lang
  try:
   page.goto(BASE+'/sector_central_china.html#map',wait_until='domcontentloaded',timeout=90000)
   f=frame(page)
   if page.evaluate("document.documentElement.dataset.theme")!=theme:
    label='浅色主题' if page.evaluate("document.documentElement.dataset.lang")=='zh' else 'Light theme'
    page.get_by_role('button',name=label,exact=True).filter(visible=True).click()
   page.wait_for_function("(v)=>document.documentElement.dataset.theme===v",arg=theme)
   f.wait_for_function("(v)=>document.documentElement.dataset.theme===v",arg=theme)
   f.locator('.si-view-btn[data-view="map"]').click()
   f.wait_for_function("document.querySelector('.si-view[data-view=map]').classList.contains('on')")
   central=facts(f);case['central']=central
   assert central['meta']=={'region':'china','asOf':'2026-11-03','benchmark':'SHCOMP'},central['meta']
   assert central['sectorCount']==31 and central['basketCount']==22
   assert central['viewButtons']==['overview','map','moving','explore','confluence']
   assert central['dossierMounts']==0
   case['steps'].append('actual Next China Central mounts archived native China cycle map')
   screenshot(page,f,prefix+'-01-central',case)
   # A separate canonical deep link qualifies the existing standalone route. It
   # is not falsely counted as a Central Dossier/Members transition.
   page.goto(BASE+'/sector_cycles_china.html#801010',wait_until='domcontentloaded',timeout=90000)
   f=frame(page)
   f.wait_for_function("SectorCyclesCapture()?.focus==='801010'",timeout=20000)
   selected=facts(f);case['standalone']=selected
   assert selected['meta']==central['meta']
   f.locator('#sc-modes [data-mode="price"]').click()
   if f.locator('#sc-adv-toggle').is_visible() and not f.locator('#sc-scale [data-scale="linear"]').is_visible():f.locator('#sc-adv-toggle').click()
   f.locator('#sc-scale [data-scale="linear"]').click()
   f.wait_for_function("SectorCyclesCapture()?.mode==='price'&&SectorCyclesCapture()?.scale==='linear'")
   case['steps'].append('standalone China deep link selects exact Shenwan 801010 and real chart controls work')
   case['members_destination']=f.evaluate("(()=>{let s=SectorCyclesCapture();return SectorCyclesMembersHref({id:s.focus,family:s.family,publicationId:s.publicationId})})()")
   assert case['members_destination'] is None
   case['first_unsupported_transition']='China cycle selection -> integrated Dossier/Members (US-only current contract)'
   f.wait_for_function("window.SECTOR_NARR && window.SECTOR_DNA",timeout=20000)
   case['selected_after_extras']=facts(f)
   assert case['selected_after_extras']['visibleDna']==0
   case['selected_panel_text']=f.locator('#sc-panel-focus').inner_text()[:4000]
   expected_read='此数据源暂无引擎解读。' if lang=='zh' else 'Engine read unavailable in this source.'
   assert expected_read in case['selected_panel_text']
   assert 'Engine read generating' not in case['selected_panel_text'] and '引擎解读生成中' not in case['selected_panel_text']
   case['steps'].append('unsupported US-only Members handoff stays unavailable; absent DNA is not synthesized')
   screenshot(page,f,prefix+'-02-cycles',case)
   case['panel_links']=f.locator('#sc-panel-focus a').evaluate_all("els=>els.map(e=>({href:e.getAttribute('href'),text:e.textContent}))")
   link=f.locator('#sc-panel-focus a[href*="sector_central_china.html"]').filter(visible=True)
   assert link.count()==1,'China canonical return link missing or ambiguous'
   case['actual_return_href']=link.get_attribute('href')
   link.click()
   page.wait_for_function("location.pathname==='/sector_central_china.html'",timeout=45000)
   f=frame(page)
   f.wait_for_function("SectorCyclesCapture()?.focus==='801010'",timeout=20000)
   case['returned']=facts(f)
   assert f.locator('.si-view[data-view="map"]').is_visible(),'returned selected chart is hidden'
   assert case['returned']['capture']['focus']=='801010'
   assert case['returned']['meta']==central['meta']
   case['steps'].append('actual Open in Sector Central link returns to China map with selected Shenwan identity')
   if width<881:
    case['mobile_surface']=mobile_surface(f)
    assert case['mobile_surface']['sheet']['alpha']==255,'mobile detail sheet is translucent'
    assert case['mobile_surface']['rail']['alpha']==255,'mobile sticky navigation is translucent'
    assert not case['mobile_surface']['closeHidden'],'mobile close control is hidden from accessibility tree'
   screenshot(page,f,prefix+'-03-return',case)
   page.go_back(wait_until='domcontentloaded')
   page.wait_for_function("location.pathname==='/sector_cycles_china.html'",timeout=30000)
   f=frame(page);f.wait_for_function("SectorCyclesCapture()?.focus==='801010'",timeout=20000)
   case['history_back']=facts(f)
   assert case['history_back']['meta']==central['meta']
   page.go_forward(wait_until='domcontentloaded')
   page.wait_for_function("location.pathname==='/sector_central_china.html'",timeout=30000)
   f=frame(page);f.wait_for_function("SectorCyclesCapture()?.focus==='801010'",timeout=20000)
   assert f.locator('.si-view[data-view="map"]').is_visible(),'Forward restored a hidden chart'
   case['history_forward']=facts(f)
   assert case['history_forward']['meta']==central['meta']
   case['steps'].append('browser Back and Forward preserve China source and selected sector across both routes')
   if width<881:
    close=f.get_by_role('button',name='关闭' if lang=='zh' else 'Close',exact=True)
    assert close.is_visible(),'accessible localized close control missing'
    close.focus();close.press('Enter')
    f.wait_for_function("!SectorCyclesCapture()?.focus&&!document.querySelector('#sc-detail').classList.contains('sc-sheet-half')&&!document.querySelector('#sc-detail').classList.contains('sc-sheet-full')")
    case['steps'].append('localized close control is exposed to accessibility tree and Enter dismisses the selected sheet')
   case['passed']=not case['page_errors'] and all(x['document']<=x['viewport']+1 for x in case['outer_widths'])
   if not case['passed']:case['failure']='page error or outer overflow'
  except Exception as e:
   case['passed']=False;case['failure']=type(e).__name__+': '+str(e)[:1400];case['trace']=traceback.format_exc()[-2200:]
   try:page.screenshot(path=str(OUT/(prefix+'-failure.png')),full_page=False)
   except Exception:pass
  finally:
   ctx.close();report['cases'].append(case);(OUT/'result.json').write_text(json.dumps(report,indent=2)+'\n')
   print(json.dumps({'viewport':width,'steps':case['steps'],'passed':case.get('passed'),'failure':case.get('failure'),'page_errors':case['page_errors'],'failed_responses':case['failed_responses'][:12]}),flush=True)
 browser.close()
print('REPORT',OUT/'result.json',flush=True)
