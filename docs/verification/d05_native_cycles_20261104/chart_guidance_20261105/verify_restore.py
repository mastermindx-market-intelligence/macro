from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit,unquote
import hashlib,json,mimetypes,traceback
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/sector-r3-chart-accessibility-20261105')
SITE=ROOT/'.pytest_cache/d05-chart-guidance-20261105/site'
OUT=ROOT/'.pytest_cache/d05-chart-guidance-20261105/restore'
OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8765'
report={'schema':'d05.chart_guidance_restore_browser.v1','fixture_only':True,'candidate_renderer_sha256':hashlib.sha256((SITE/'sector_cycles.js').read_bytes()).hexdigest(),'cases':[]}
def geometry(page):
 return hashlib.sha256(json.dumps(page.locator('#sc-chart svg path[d]').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("d"))')).encode()).hexdigest()
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='chrome',headless=True,chromium_sandbox=True)
 for width,height,theme,lang in [(1440,1000,'dark','en'),(390,844,'light','zh')]:
  case={'viewport':[width,height],'theme':theme,'lang':lang,'page_errors':[],'missing_assets':[]};report['cases'].append(case)
  ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
  ctx.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
  def route(r):
   u=urlsplit(r.request.url);p=(SITE/unquote(u.path.lstrip('/'))).resolve()
   if u.scheme+'://'+u.netloc==BASE and SITE.resolve() in p.parents and p.is_file():
    r.fulfill(status=200,content_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream',body=p.read_bytes());return
   case['missing_assets'].append(u.path);r.fulfill(status=404,content_type='text/plain',body='Unstaged fixture asset')
  ctx.route('**/*',route)
  page=ctx.new_page();page.on('pageerror',lambda e:case['page_errors'].append(str(e)))
  try:
   page.goto(BASE+'/sector_cycles.html',wait_until='load')
   page.wait_for_function('typeof SectorCyclesApply==="function" && !!document.querySelector("#sc-chart svg") && SectorCyclesEvidence().status==="verified" && window.SECTOR_CYCLES_SERIES!==undefined')
   assert page.locator('html').get_attribute('data-theme')==theme
   assert page.locator('html').get_attribute('data-lang')==lang
   assert page.locator('#sc-firsthint').count()==1
   url=page.url;case['initial_geometry']=geometry(page)
   case['receipt']=page.evaluate('''() => {
    const snapshot=SectorCyclesCapture();snapshot.mode="price";snapshot.scale="linear";
    return SectorCyclesApply({family:snapshot.family,id:snapshot.focus,snapshot,
      strictRestore:true,restore:true,requirePublication:true,spine:SectorCyclesEvidence().spine,
      entryKey:"d05-guidance-same-url-restore"});
   }''')
   assert case['receipt']['status']=='applied',case['receipt']
   assert case['receipt']['restoration']=='restored',case['receipt']
   assert page.url==url,'Snapshot restoration must preserve the existing URL owner'
   assert page.locator('#sc-firsthint').count()==0
   restored=page.evaluate('SectorCyclesCapture()');assert restored['mode']=='price' and restored['scale']=='linear'
   case['restored_geometry']=geometry(page);assert case['restored_geometry']!=case['initial_geometry']
   reference=json.loads((ROOT/'.pytest_cache/d05-chart-guidance-20261105/browser/result.json').read_text())
   expected=next(c for c in reference['cases'] if c['viewport']==[width,height] and c['theme']==theme and c['lang']==lang and c['initial_mode']=='price')
   assert case['restored_geometry']==expected['geometry']['initial'],'Restoration must render the same price geometry as a fresh Price/Linear deep link'
   page.locator('#sc-chart').scroll_into_view_if_needed()
   name=f'{width}-{theme}-{lang}-restored.png';page.screenshot(path=str(OUT/name))
   case['screenshot']={'file':name,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
   button=page.locator('#sc-scale [data-scale="log"]')
   if not button.is_visible():
    toggle=page.locator('#sc-adv-toggle');toggle.focus();toggle.press('Enter')
   assert button.is_visible(),'Open the existing mobile Chart options before keyboard use'
   button.focus();assert button.evaluate('(b)=>document.activeElement===b')
   button.press('Enter')
   assert page.evaluate('SectorCyclesCapture().scale')=='log'
   assert page.locator('#sc-firsthint').count()==0
   page.wait_for_timeout(11500)
   assert page.locator('#sc-firsthint').count()==0
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   assert not case['page_errors'] and not case['missing_assets']
   case['passed']=True
  except Exception as e:
   case['passed']=False;case['error']=str(e);case['traceback']=traceback.format_exc()
  finally:ctx.close()
  print(json.dumps({k:case.get(k) for k in ['viewport','theme','lang','passed','error']}),flush=True)
 browser.close()
report['passed']=all(c.get('passed') for c in report['cases'])
(OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
raise SystemExit(0 if report['passed'] else 1)
