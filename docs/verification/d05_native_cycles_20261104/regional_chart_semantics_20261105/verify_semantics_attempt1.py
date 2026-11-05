from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit,unquote
import hashlib,itertools,json,mimetypes,re,traceback
ROOT=Path('/tmp/mastermind-d05-regional-chart-20261105-f0f7aa17')
OUT=ROOT/'browser';OUT.mkdir(exist_ok=True)
BASE='http://127.0.0.1:8765'
CONFIG=json.loads((ROOT/'config.json').read_text())
report={'schema':'d05.regional_chart_semantics_browser.v1','parent':CONFIG['parent'],'fixture_only':True,'fixture_provenance_sha256':hashlib.sha256((ROOT/'fixture_provenance.json').read_bytes()).hexdigest(),'cases':[]}
EN='Price shows rebased price series; Cycle position shows a 0–100 oscillator.'
ZH='“价格”展示再基准化价格序列；“周期位置”展示 0–100 的振荡指标。'
def geometry(page):
 return hashlib.sha256(json.dumps(page.locator('#sc-chart svg path[d]').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("d"))')).encode()).hexdigest()
def chart_ax(cdp):
 doc=cdp.send('DOM.getDocument')
 node=cdp.send('DOM.querySelector',{'nodeId':doc['root']['nodeId'],'selector':'#sc-chart'})
 tree=cdp.send('Accessibility.getPartialAXTree',{'nodeId':node['nodeId'],'fetchRelatives':False})
 ax=next(n for n in tree['nodes'] if not n.get('ignored'))
 return {k:ax.get(k,{}).get('value') for k in ['role','name','description']}
def keyboard(page,selector):
 el=page.locator(selector)
 assert el.is_visible(),selector+' must be visible'
 el.focus();assert el.evaluate('(e)=>document.activeElement===e')
 el.press('Enter')
def assert_ax(page,cdp,name,lang):
 ax=chart_ax(cdp);assert ax['role']=='image',ax
 label=CONFIG['labels'][name]
 expected=page.locator('#'+label).inner_text().strip()
 assert expected and ax['name']==expected,ax
 assert page.locator('#'+label).is_visible()
 assert page.locator('#'+label).count()==1 and page.locator('#sc-chart-a11y').count()==1
 cncentral=name=='sector_central_china'
 suffix=(' This chart does not provide a table of plotted points.' if cncentral else ' Scorecards below are summaries, not a table of plotted points.') if lang=='en' else ('此图表未提供逐点数据表。' if cncentral else '下方记分卡是文字摘要，而非图表逐点数据表。')
 assert ax['description']==(EN if lang=='en' else ZH)+suffix,ax
 assert 'ETF' not in ax['description'],ax
 if cncentral:assert 'scorecards' not in ax['description'].lower() and '记分卡' not in ax['description']
 return ax
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='chrome',headless=True,chromium_sandbox=True)
 for name,lang,(width,height,theme) in itertools.product(CONFIG['labels'],['en','zh'],[(1440,1000,'dark'),(390,844,'light')]):
  region='china' if name.endswith('_china') else 'us';site=ROOT/region
  native='central' in name;view='map' if region=='china' else 'cycles'
  case={'surface':name,'region':region,'viewport':[width,height],'theme':theme,'lang':lang,'page_errors':[],'missing_assets':[],'blocked_external':[]};report['cases'].append(case)
  ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce',has_touch=width<1024)
  ctx.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
  def route(r):
   u=urlsplit(r.request.url)
   if u.scheme+'://'+u.netloc!=BASE:case['blocked_external'].append(r.request.url);r.abort();return
   p=(site/unquote(u.path.lstrip('/'))).resolve()
   if site.resolve() in p.parents and p.is_file():r.fulfill(status=200,content_type=mimetypes.guess_type(p.name)[0] or 'application/octet-stream',body=p.read_bytes());return
   case['missing_assets'].append(u.path);r.fulfill(status=404,content_type='text/plain',body='Unstaged fixture asset')
  ctx.route('**/*',route)
  page=ctx.new_page();page.on('pageerror',lambda e:case['page_errors'].append(str(e)))
  cdp=ctx.new_cdp_session(page)
  try:
   page.goto(BASE+'/'+name+'.html'+('#'+view if native else ''),wait_until='load',timeout=30000)
   if native:
    page.locator('.si-view-btn[data-view="'+view+'"]').click()
   page.wait_for_function('typeof SectorCyclesCapture==="function" && !!document.querySelector("#sc-chart svg") && SectorCyclesEvidence().status==="verified" && SectorCyclesEvidence().parts.series==="verified"',timeout=25000)
   assert page.locator('html').get_attribute('data-theme')==theme
   assert page.locator('html').get_attribute('data-lang')==lang
   case['source']=page.evaluate('({receipt:SectorCyclesEvidence(),region:SECTOR_CYCLES.meta.region,asOf:SECTOR_CYCLES.meta.asOf,sectors:SECTOR_CYCLES.sectors.length,baskets:SECTOR_CYCLES.baskets.length})')
   assert case['source']['region']==region
   case['cycle_ax']=assert_ax(page,cdp,name,lang)
   assert page.locator('#sc-modes [data-mode="osc"]').get_attribute('aria-pressed')=='true'
   cycle=geometry(page)
   keyboard(page,'#sc-modes [data-mode="price"]')
   assert page.evaluate('SectorCyclesCapture().mode')=='price'
   assert page.locator('#sc-modes [data-mode="price"]').get_attribute('aria-pressed')=='true'
   case['price_ax']=assert_ax(page,cdp,name,lang)
   price=geometry(page);assert cycle!=price
   case['geometry']={'cycle':cycle,'price':price}
   page.locator('#sc-chart').scroll_into_view_if_needed()
   filename=f'{name}-{width}-{theme}-{lang}-price.png';page.screenshot(path=str(OUT/filename))
   case['screenshot']={'file':filename,'sha256':hashlib.sha256((OUT/filename).read_bytes()).hexdigest()}
   keyboard(page,'#sc-tabs [data-fam="baskets"]')
   assert page.evaluate('SectorCyclesCapture().family')=='baskets'
   case['basket_ax']=assert_ax(page,cdp,name,lang)
   assert page.locator('#sc-chart svg path[d]').count()>0
   keyboard(page,'#sc-modes [data-mode="osc"]')
   assert page.locator('#sc-modes [data-mode="osc"]').get_attribute('aria-pressed')=='true'
   case['returned_cycle_ax']=assert_ax(page,cdp,name,lang)
   assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   assert not case['page_errors'],case['page_errors']
   case['passed']=True
  except Exception as e:
   case['passed']=False;case['error']=str(e);case['traceback']=traceback.format_exc()
   page.screenshot(path=str(OUT/f'{name}-{width}-{lang}-failure.png'))
  finally:ctx.close()
  print(json.dumps({k:case.get(k) for k in ['surface','viewport','theme','lang','passed','error']},ensure_ascii=False),flush=True)
  (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 browser.close()
report['passed']=all(c.get('passed') for c in report['cases'])
(OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'cases':len(report['cases'])}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
