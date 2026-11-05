from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit,unquote
import hashlib,itertools,json,mimetypes,traceback
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/sector-r3-chart-accessibility-20261105')
SITE=ROOT/'.pytest_cache/d05-chart-guidance-20261105/site'
OUT=ROOT/'.pytest_cache/d05-chart-guidance-20261105/browser'
OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8765'
report={'schema':'d05.chart_guidance_browser.v1','integration_parent':'e09f7c4667a5dfbf0b209ad826b4692c15c3ca10','candidate_renderer_sha256':hashlib.sha256((SITE/'sector_cycles.js').read_bytes()).hexdigest(),'fixture_only':True,'fixture_provenance_sha256':hashlib.sha256((SITE/'fixture_provenance.json').read_bytes()).hexdigest(),'cases':[]}
def geometry(page):
 return hashlib.sha256(json.dumps(page.locator('#sc-chart svg path[d]').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("d"))')).encode()).hexdigest()
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='chrome',headless=True,chromium_sandbox=True)
 for (width,height),theme,lang,initial in itertools.product([(1440,1000),(390,844)],['dark','light'],['en','zh'],['osc','price']):
  case={'viewport':[width,height],'theme':theme,'lang':lang,'initial_mode':initial,'page_errors':[],'missing_assets':[]}
  report['cases'].append(case)
  ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
  ctx.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
  def route(r):
   u=urlsplit(r.request.url)
   if u.scheme+'://'+u.netloc!=BASE:r.abort();return
   p=(SITE/unquote(u.path.lstrip('/'))).resolve()
   if SITE.resolve() in p.parents and p.is_file():
    r.fulfill(status=200,content_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream',body=p.read_bytes());return
   case['missing_assets'].append(u.path);r.fulfill(status=404,content_type='text/plain',body='Unstaged fixture asset')
  ctx.route('**/*',route)
  page=ctx.new_page();page.on('pageerror',lambda e:case['page_errors'].append(str(e)))
  try:
   url=BASE+'/sector_cycles.html'+('?sc_mode=price&sc_scale=linear' if initial=='price' else '')
   page.goto(url,wait_until='load',timeout=30000)
   page.wait_for_function('typeof SectorCyclesCapture==="function" && !!document.querySelector("#sc-chart svg") && SectorCyclesEvidence().status==="verified"',timeout=20000)
   assert page.locator('html').get_attribute('data-theme')==theme
   assert page.locator('html').get_attribute('data-lang')==lang
   assert page.evaluate('SectorCyclesCapture().mode')==initial
   case['initial_hint']=page.locator('#sc-firsthint').inner_text()
   prefix=('Rebased prices' if lang=='en' else '再基准化价格') if initial=='price' else ('High = stretched' if lang=='en' else '高 = 拉伸')
   assert case['initial_hint'].startswith(prefix),case['initial_hint']
   if initial=='price':
    assert 'washed-out' not in case['initial_hint'] and '超卖' not in case['initial_hint']
    assert not page.locator('.sc-mode-cap').is_visible()
   g0=geometry(page)
   page.locator('#sc-chart').scroll_into_view_if_needed()
   name=f'{width}-{theme}-{lang}-{initial}.png'
   page.screenshot(path=str(OUT/name),full_page=False)
   case['screenshot']={'file':name,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
   other='price' if initial=='osc' else 'osc'
   button=page.locator('#sc-modes [data-mode="'+other+'"]')
   button.focus();button.press('Enter')
   page.wait_for_function('(m)=>SectorCyclesCapture().mode===m',arg=other)
   assert page.locator('#sc-firsthint').count()==0,'First real presentation change must dismiss the old hint'
   assert button.get_attribute('aria-pressed')=='true'
   g1=geometry(page);assert g0!=g1
   button=page.locator('#sc-modes [data-mode="'+initial+'"]')
   button.focus();button.press('Enter')
   page.wait_for_function('(m)=>SectorCyclesCapture().mode===m',arg=initial)
   assert page.locator('#sc-firsthint').count()==0,'Returning to an earlier mode must not recreate one-shot guidance'
   g2=geometry(page);assert g0==g2
   case['geometry']={'initial':g0,'other':g1,'returned':g2}
   before=page.evaluate('SectorCyclesCapture()')
   page.reload(wait_until='load',timeout=30000)
   page.wait_for_function('typeof SectorCyclesCapture==="function" && !!document.querySelector("#sc-chart svg") && SectorCyclesEvidence().status==="verified"',timeout=20000)
   after=page.evaluate('SectorCyclesCapture()')
   assert after['mode']==before['mode'] and after['scale']==before['scale']
   case['reload_hint']=page.locator('#sc-firsthint').inner_text()
   assert case['reload_hint'].startswith(prefix)
   case['reload_geometry']=geometry(page);assert case['reload_geometry']==g0
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   assert not case['page_errors'],case['page_errors']
   case['passed']=True
  except Exception as e:
   case['passed']=False;case['error']=str(e);case['traceback']=traceback.format_exc()
   page.screenshot(path=str(OUT/f'{width}-{theme}-{lang}-{initial}-failure.png'),full_page=False)
  finally:ctx.close()
  print(json.dumps({k:case.get(k) for k in ['viewport','theme','lang','initial_mode','passed','error']},ensure_ascii=False),flush=True)
  (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 browser.close()
report['passed']=all(c.get('passed') for c in report['cases'])
(OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'cases':len(report['cases'])}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
