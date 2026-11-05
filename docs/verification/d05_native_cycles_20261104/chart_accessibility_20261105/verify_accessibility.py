from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urlsplit,unquote
import hashlib,json,mimetypes,traceback
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/macro/web/sector-r3-chart-accessibility-20261105')
SITE=ROOT/'.pytest_cache/d05-accessibility-20261105/site'
OUT=ROOT/'.pytest_cache/d05-accessibility-20261105/browser'
OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8765'
report={'schema':'d05.chart_accessibility_browser.v1','source_commit':'eb807572d1c1d0645801e3bc060e1507dd374111','integration_parent':'d1ebd39fb1287f69592d8a621c5db0318e7fff05','fixture_only':True,'fixture_provenance_sha256':hashlib.sha256((SITE/'fixture_provenance.json').read_bytes()).hexdigest(),'cases':[]}
def ax_chart(page):
 cdp=page.context.new_cdp_session(page)
 root=cdp.send('DOM.getDocument')['root']['nodeId']
 node=cdp.send('DOM.querySelector',{'nodeId':root,'selector':'#sc-chart'})['nodeId']
 backend=cdp.send('DOM.describeNode',{'nodeId':node})['node']['backendNodeId']
 nodes=cdp.send('Accessibility.getPartialAXTree',{'backendNodeId':backend,'fetchRelatives':False})['nodes']
 n=next(n for n in nodes if not n.get('ignored'))
 cdp.detach()
 return {k:n.get(k,{}).get('value') for k in ['role','name','description']}
def geometry(page):
 return page.locator('#sc-chart svg path[d]').evaluate_all('(nodes)=>nodes.map(n=>n.getAttribute("d"))')
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='chrome',headless=True,chromium_sandbox=True)
 for width,height in [(1440,1000),(390,844)]:
  for theme in ['dark','light']:
   for lang in ['en','zh']:
    case={'viewport':[width,height],'theme':theme,'lang':lang,'page_errors':[],'missing_assets':[],'steps':[]}
    report['cases'].append(case)
    ctx=browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
    ctx.add_init_script('localStorage.setItem("theme",'+json.dumps(theme)+');localStorage.setItem("lang",'+json.dumps(lang)+');')
    def route(r):
     u=urlsplit(r.request.url)
     if u.scheme+'://'+u.netloc!=BASE:
      r.abort();return
     path=(SITE/unquote(u.path.lstrip('/'))).resolve()
     if SITE.resolve() in path.parents and path.is_file():
      r.fulfill(status=200,content_type=mimetypes.guess_type(path.name)[0] or 'application/octet-stream',body=path.read_bytes());return
     case['missing_assets'].append(u.path)
     r.fulfill(status=404,content_type='text/plain',body='Unstaged fixture asset')
    ctx.route('**/*',route)
    page=ctx.new_page();page.on('pageerror',lambda e:case['page_errors'].append(str(e)))
    try:
     page.goto(BASE+'/sector_cycles.html',wait_until='load',timeout=30000)
     page.wait_for_function('typeof SectorCyclesCapture==="function" && !!document.querySelector("#sc-chart svg")',timeout=20000)
     page.wait_for_function('SectorCyclesEvidence().status==="verified"',timeout=20000)
     assert page.locator('html').get_attribute('data-theme')==theme
     assert page.locator('html').get_attribute('data-lang')==lang
     assert page.locator('#sc-chart-a11y').count()==1
     expected_name='Sector rotation overlay' if lang=='en' else '板块轮动叠加'
     expected_desc='Price shows rebased sector ETF prices' if lang=='en' else '“价格”展示板块 ETF 的再基准化价格'
     for mode in ['osc','price','osc']:
      button=page.locator('#sc-modes [data-mode="'+mode+'"]')
      button.focus();button.press('Enter')
      page.wait_for_function('(mode)=>SectorCyclesCapture().mode===mode',arg=mode)
      assert button.get_attribute('aria-pressed')=='true'
      if mode=='price':
       options=page.locator('#sc-adv-toggle')
       if options.is_visible() and options.get_attribute('aria-expanded')!='true':
        options.focus();options.press('Enter')
       linear=page.locator('#sc-scale [data-scale="linear"]')
       linear.focus();linear.press('Space')
       page.wait_for_function('SectorCyclesCapture().scale==="linear"')
      tree=ax_chart(page)
      assert tree['role']=='image',tree
      assert tree['name']==expected_name,tree
      assert expected_desc in tree['description'],tree
      assert ('not a table of plotted points' if lang=='en' else '而非图表逐点数据表') in tree['description']
      assert ('板块' not in tree['description']) if lang=='en' else ('Price shows' not in tree['description'])
      points=geometry(page);assert len(points)>0
      step={'mode':mode,'scale':page.evaluate('SectorCyclesCapture().scale'),'ax':tree,'path_count':len(points),'geometry_sha256':hashlib.sha256(json.dumps(points).encode()).hexdigest()}
      case['steps'].append(step)
      if len(case['steps'])<3:
       page.locator('#sc-chart').scroll_into_view_if_needed()
       name=f'{width}-{theme}-{lang}-{mode}.png'
       page.screenshot(path=str(OUT/name),full_page=False)
       step['screenshot']={'file':name,'sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest()}
     assert case['steps'][0]['geometry_sha256']!=case['steps'][1]['geometry_sha256'],'Price must change actual plotted geometry'
     assert case['steps'][0]['geometry_sha256']==case['steps'][2]['geometry_sha256'],'Returning to Cycle must restore plotted geometry'
     case['evidence']=page.evaluate('SectorCyclesEvidence()')
     case['source']=page.evaluate('({asOf:SECTOR_CYCLES.meta.asOf,region:SECTOR_CYCLES.meta.region})')
     case['overflow']=page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
     assert not case['overflow']
     assert not case['page_errors'],case['page_errors']
     case['passed']=True
    except Exception as e:
     case['passed']=False;case['error']=str(e);case['traceback']=traceback.format_exc()
     page.screenshot(path=str(OUT/f'{width}-{theme}-{lang}-failure.png'),full_page=False)
    finally:
     ctx.close()
    print(json.dumps({k:case.get(k) for k in ['viewport','theme','lang','passed','error','page_errors']},ensure_ascii=False),flush=True)
    (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 browser.close()
report['passed']=all(x.get('passed') for x in report['cases'])
(OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'cases':len(report['cases']),'result':str(OUT/'result.json')}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
