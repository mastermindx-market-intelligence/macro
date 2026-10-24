from pathlib import Path
from urllib.parse import urlparse,unquote
import json,mimetypes,hashlib
from playwright.sync_api import sync_playwright
import argparse
from jinja2 import Environment,FileSystemLoader,Undefined
ROOT=Path(__file__).resolve().parents[3]
ap=argparse.ArgumentParser(description='Actual Sector Intelligence page, synthetic pulse only; no production network.')
ap.add_argument('--out',required=True);ap.add_argument('--browser',choices=['chromium','webkit'],default='chromium');args=ap.parse_args();OUT=Path(args.out);OUT.mkdir(parents=True,exist_ok=True)
source=(ROOT/'templates/sector_central.html.j2').read_text()
env=Environment(loader=FileSystemLoader(str(ROOT/'templates')),autoescape=False,undefined=Undefined)
html=env.from_string(source).render(flows_html='',pgate=None,bottoming=None,theme_context=None,factor_season=None,flow=None,basket_member_syms=[],action_board={'total':0,'buy_now':[],'buy_soon':[],'on_the_run':[],'take_profits':[],'hold':[],'avoid':[]},accumulation=[],accumulation_universe_n=0,theme_tape=None,generated_utc='2026-10-13')
replay=json.loads((ROOT/'research/rotation_intelligence/intraday_sessions_20261013/producer_grounding_replay_hardened.json').read_text())
rows=[dict(id=r['id'],live_ew_chg_pct=r['daily_change_pct'],tape_rank=i+1,intraday_comparison=r['intraday_comparison']) for i,r in enumerate(replay['measured_rows'])]
pulse={'schema':'basket_pulse.v1','market':'us','mode':'delayed','session':'rth','as_of_quotes':'2026-10-13T15:29:00+00:00','as_of_utc':'2026-10-13T15:30:00+00:00','baskets':rows}
reports=[]
names={'baskets':[{'id':'ai_semiconductors','name':'AI semiconductors','name_zh':'AI\u534a\u5bfc\u4f53'},{'id':'us_sector_health','name':'Health care','name_zh':'\u533b\u7597\u4fdd\u5065'}]}
with sync_playwright() as pw:
 browser=getattr(pw,args.browser).launch(headless=True)
 for width,theme,lang in [(1440,'dark','en'),(1440,'light','en'),(390,'dark','en'),(390,'light','zh')]:
  context=browser.new_context(viewport={'width':width,'height':960 if width>500 else 844},device_scale_factor=1)
  state={'status':200,'pulse':pulse,'reads':0};errors=[];console_errors=[];failed_requests=[];stubbed=set()
  context.add_init_script("localStorage.setItem('theme',"+json.dumps(theme)+");localStorage.setItem('lang',"+json.dumps(lang)+");Date.now=()=>Date.parse('2026-10-13T15:30:00Z');")
  def serve(route):
   u=urlparse(route.request.url);path=unquote(u.path).lstrip('/')
   if path=='sector_central.html':return route.fulfill(status=200,body=html,content_type='text/html')
   if path=='live/basket_pulse.json':
    state['reads']+=1;return route.fulfill(status=state['status'],body=json.dumps(state['pulse']),content_type='application/json')
   if path=='basketdata/baskets.json':return route.fulfill(status=200,body=json.dumps(names),content_type='application/json')
   if path.endswith('data.js') or path.endswith('.json'):return route.fulfill(status=200,body='{}' if path.endswith('.json') else '',content_type='application/json' if path.endswith('.json') else 'text/javascript')
   if u.hostname=='rotation.test' and path.endswith(('.css','.js','.svg')) and '..' not in Path(path).parts:
    f=ROOT/'templates'/path
    if f.is_file():return route.fulfill(status=200,body=f.read_bytes(),content_type=mimetypes.guess_type(path)[0] or 'text/plain')
   stubbed.add(u.hostname+'/'+path)
   return route.fulfill(status=200,body='',content_type='text/javascript' if path.endswith('.js') else 'text/plain')
  context.route('**/*',serve)
  page=context.new_page();page.on('pageerror',lambda exc:errors.append(str(exc)))
  page.on('console',lambda msg:console_errors.append(msg.text) if msg.type=='error' else None)
  page.on('requestfailed',lambda req:failed_requests.append({'url':req.url,'failure':req.failure}))
  page.goto('http://rotation.test/sector_central.html#moving',wait_until='domcontentloaded')
  page.evaluate("window.BASKETS="+json.dumps(names)+";window.__ftrTapeNamesReady();")
  page.locator('a.si-view-btn[data-view="moving"]').click()
  page.locator('#si-intraday').wait_for(state='visible')
  page.locator('#si-intraday .si-intra-row').first.wait_for(state='visible')
  row=page.locator('#si-intraday .si-intra-row summary').first;row.focus();page.keyboard.press('Enter')
  assert page.locator('#si-intraday details[open]').count()==1
  page.evaluate('window.__ftrTapeNamesReady()')
  assert page.locator('#si-intraday details[open]').count()==1
  assert page.evaluate("document.activeElement.tagName")=='SUMMARY'
  bounds=page.evaluate("({viewport:innerWidth,page:document.documentElement.scrollWidth,panel:document.getElementById('si-intraday').getBoundingClientRect().width,scroll:document.getElementById('si-intraday').scrollWidth})")
  contrast=page.evaluate("""() => {
    function rgb(value){return (value.match(/[0-9.]+/g)||[]).slice(0,3).map(Number);}
    function luminance(c){return c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4;}).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);}
    const panel=document.getElementById('si-intraday');const bg=rgb(getComputedStyle(panel).backgroundColor);
    return [...panel.querySelectorAll('h2,.si-intra-head p,.si-intra-value,.si-intra-detail p,.si-intra-foot')].filter(e=>e.getClientRects().length).map(e=>{const color=getComputedStyle(e).color;const a=luminance(rgb(color)),b=luminance(bg);return {class:e.className||e.tagName,color,ratio:(Math.max(a,b)+.05)/(Math.min(a,b)+.05)};});
  }""")
  slug=f'{width}-{theme}-{lang}'
  page.locator('#si-intraday').screenshot(path=str(OUT/(slug+'-panel.png')))
  page.screenshot(path=str(OUT/(slug+'-page.png')))
  rendered=page.locator('#si-intraday-body').inner_text()
  assert '-1.96%' in rendered or '\u22121.96%' in rendered
  assert '+1.01%' in rendered and '0.00%' in rendered
  assert bounds['scroll']<=bounds['panel']+1
  page.evaluate("window.__heldSummary=document.activeElement")
  with page.expect_response(lambda response:response.url.endswith('/live/basket_pulse.json')):
   page.evaluate("window.dispatchEvent(new Event('focus'))")
  page.wait_for_function("!document.getElementById('si-intraday-refresh').disabled")
  assert page.evaluate("window.__heldSummary===document.activeElement && window.__heldSummary.isConnected"), 'An unchanged refresh replaced the focused node'
  state['status']=403
  with page.expect_response(lambda response:response.url.endswith('/live/basket_pulse.json')):
   page.evaluate("window.dispatchEvent(new Event('focus'))")
  page.wait_for_function("document.querySelectorAll('#si-intraday .si-intra-row').length===0")
  assert page.evaluate("document.activeElement.id==='si-intraday-body'"), 'Automatic denial lost keyboard focus'

  denied=page.locator('#si-intraday-body').inner_text()
  page.locator('a.si-view-btn[data-view="overview"]').click()
  assert 'visible' not in (page.locator('#ftr-tape-strip').get_attribute('class') or '').split(), 'Denied refresh did not clear the overview strip class'
  page.locator('#ftr-tape-strip').wait_for(state='hidden')
  page.locator('a.si-view-btn[data-view="moving"]').click()
  state['status']=200;page.locator('#si-intraday-refresh').click();page.wait_for_function("document.querySelectorAll('#si-intraday .si-intra-row').length===2")
  page.evaluate("Date.now=()=>Date.parse('2026-10-13T16:15:00Z');window.__ftrTapeNamesReady()")
  assert page.locator('#si-intraday .si-intra-row').count()==0
  stale=page.locator('#si-intraday-body').inner_text()
  page.evaluate("Date.now=()=>Date.parse('2026-10-13T15:30:00Z')")
  expanded=json.loads(json.dumps(pulse));expanded['baskets']=[dict(pulse['baskets'][i%2],id='test_group_'+str(i)) for i in range(9)]
  state['pulse']=expanded;page.locator('#si-intraday-refresh').click();page.wait_for_function("document.querySelectorAll('#si-intraday .si-intra-row').length===6")
  before=state['reads'];page.locator('#si-intraday-more').click()
  assert page.locator('#si-intraday .si-intra-row').count()==9
  assert state['reads']==before, 'Expanding the view must not issue another source request'
  page.evaluate('window.__ftrTapeNamesReady()')
  assert page.locator('#si-intraday .si-intra-row').count()==9
  page.locator('#si-intraday-more').click();assert page.locator('#si-intraday .si-intra-row').count()==6

  reports.append({'viewport':width,'theme':theme,'language':lang,'geometry':bounds,'text_contrast':contrast,'new_view_ready':True,'keyboard_details':True,'unchanged_refresh_preserves_node':True,'denied_focus_has_landing':True,'focus_and_open_preserved':True,'denied_hides_numbers':True,'stale_hides_numbers':True,'show_all_without_refetch':True,'expansion_survives_repaint':True,'page_errors':errors,'console_errors':console_errors,'failed_requests':failed_requests,'stubbed_paths':sorted(stubbed),'pulse_requests':state['reads'],'denied_text':denied,'stale_text':stale})
  context.close()
 browser.close()
(OUT/'browser-preview-report.json').write_text(json.dumps({'browser':args.browser,'proof_kind':'actual_candidate_jinja_page_synthetic_pulse_no_production','template_sha256':hashlib.sha256(source.encode()).hexdigest(),'cases':reports},indent=2,ensure_ascii=False))
print(json.dumps({'cases':len(reports),'all_checks_passed':True,'page_errors':sum(len(r['page_errors']) for r in reports),'source_sha256':hashlib.sha256(source.encode()).hexdigest()}))
