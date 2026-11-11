from pathlib import Path
import os,sys,json,hashlib,http.server,socketserver,threading,functools,subprocess,urllib.parse,datetime
import argparse
parser=argparse.ArgumentParser(description='Replay the recorded local WMN consumer scenarios against the bound C4 assets.')
parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[3])
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--case',choices=[f'{w}-{t}-{l}' for w in [1440,390] for t in ['dark','light'] for l in ['en','zh']])
args=parser.parse_args()
W=args.repo.resolve();P=args.output_dir.resolve();OUT=P
OUT.mkdir(parents=True,exist_ok=True);sys.path[:0]=[str(W),str(W/'tests')];os.chdir(W)

proof_dir=Path(__file__).resolve().parent
observation=json.loads((proof_dir/'render-observation.json').read_text())
for relative,expected in observation['source_blobs'].items():
 data=(W/relative).read_bytes()
 actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 assert actual==expected,(relative,expected,actual)
for relative,expected in json.loads((proof_dir/'served-assets.json').read_text())['assets'].items():
 data=(W/relative).read_bytes()
 actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
 assert actual==expected['git_blob'] and hashlib.sha256(data).hexdigest()==expected['sha256'],relative
assert hashlib.sha256((proof_dir/'wmn-api-fixture.json').read_bytes()).hexdigest()==observation['fixture_sha256']

import test_biocatalyst_wmn_api as m
from fastapi import HTTPException
from playwright.sync_api import sync_playwright
fixture=json.loads((proof_dir/'wmn-api-fixture.json').read_text());m.api._wmn_now=lambda:m.NOW
by_horizon={}
with m._app(lambda:(m._projection(fixture['inputs']),{})) as client:
 for horizon in [7,30,90,180,365]:
  r=client.get('/api/biocatalyst/v1/what-matters-next',params={'horizon_days':horizon,'limit':50});assert r.status_code==200;by_horizon[str(horizon)]=r.json()
def deny():raise HTTPException(403,'site_full_required',headers=m.api._PRIVATE_HEADERS)
with m._app(lambda:(m._projection(fixture['inputs']),{}),auth=deny) as client:
 locked=client.get('/api/biocatalyst/v1/what-matters-next');assert locked.status_code==403
with m._app(lambda:(m._projection(None),{})) as client:
 failure=client.get('/api/biocatalyst/v1/what-matters-next');assert failure.status_code==503
responses={'horizons':by_horizon,'locked':locked.json(),'error':failure.json(),'details':fixture['details']}
(P/'interaction-api-responses-r10.json').write_text(json.dumps(responses,ensure_ascii=False,indent=2)+'\n')
from copy import deepcopy
from unittest.mock import patch
from engine.company_intelligence.contracts import canonical_json_sha256
from engine.company_intelligence.events import project_catalyst_event
from test_biocatalyst_wmn_publication import CIK,COMPANY,CUTOFF
def pagination_fixture():
 inputs=m._two_event_inputs();first_event=inputs['events'][0];identity=inputs['identity_projection'][first_event['event_id']]
 for index in range(2,51):
  revision=f'doc_2026_08_01:r1-browser-fixture-{index:03d}'
  event=project_catalyst_event(company_id=COMPANY,issuer_cik=CIK,source_namespace='issuer_disclosure',native_event_key=f'doc_2026_08_01#claim/readout_browser_fixture_{index:03d}',event_family='issuer_readout_guidance',revision_ref=revision,revision_is_current=True,occurrence='uncorroborated',timing=deepcopy(first_event['timing']),source_available_at='2026-08-01T14:00:00Z',observed_at='2026-08-01T14:00:02Z',document_refs=[revision],public_evidence=[],asset_mentions=[],relationship_claims=[],generation_cutoff=CUTOFF)
  inputs['events'].append(event);inputs['identity_projection'][event['event_id']]=deepcopy(identity)
  inputs['input_cut']['members'].append({'contract_id':'company_catalyst_event.v1','ref':event['event_id'],'sha256':canonical_json_sha256(event),'observed_at':event['observed_at'],'accepted_at':event['observed_at'],'availability':'available'})
 inputs['coverage']['family_states']['issuer_readout_guidance']['observed_count']=len(inputs['events'])
 assert len(inputs['events'])==51
 state={'mode':'ready'}
 def auth():
  if state['mode']=='locked':raise HTTPException(403,'fixture-only access denial',headers=m.api._PRIVATE_HEADERS)
  return {'id':'wmn-browser-fixture-only'}
 def bundle():return m._projection(None if state['mode']=='unavailable' else inputs),{}
 query={'view':'upcoming','horizon_days':'90','limit':'50'};endpoint='/api/biocatalyst/v1/what-matters-next'
 with patch.object(m.api,'_wmn_now',return_value=m.NOW),patch.object(m.api,'_wmn_cursor_key',return_value=b'f'*32),m._app(bundle,auth=auth) as client:
  first=client.get(endpoint,params=query);assert first.status_code==200,first.text
  p1=first.json();assert len(p1['rows'])==50 and p1['pagination']['total']==51
  cursor=p1['pagination']['next_cursor'];assert isinstance(cursor,str) and cursor
  append_query={**query,'cursor':cursor}
  second=client.get(endpoint,params=append_query);assert second.status_code==200,second.text
  p2=second.json();assert len(p2['rows'])==1 and p2['pagination']=={'limit':50,'total':51,'next_cursor':None}
  assert p1['generation_id']==p2['generation_id']
  assert len({(r['event_fact_ref'],r['row_key']['issuer_id']) for r in p1['rows']+p2['rows']})==51
  state['mode']='locked';denied=client.get(endpoint,params=append_query);assert denied.status_code==403
  state['mode']='unavailable';unavailable=client.get(endpoint,params=append_query);assert unavailable.status_code==503 and unavailable.json()=={'detail':'OWNER_INPUT_UNAVAILABLE'}
  responses={'first':first,'append':second,'append_locked':denied,'append_error':unavailable}
  for r in responses.values():
   assert r.headers['cache-control']=='private, no-store' and r.headers['vary']=='Authorization' and r.headers['x-robots-tag']=='noindex, noarchive'
  return {'query':query,'append_query':append_query,'responses':{k:{'status':v.status_code,'body':v.json()} for k,v in responses.items()},'event_count':51,'auth':'existing local test seam only','cursor_key':'scoped fixture-only key; actual router signs and validates'}
paged=pagination_fixture()
(P/'pagination-api-fixture-r10.json').write_text(json.dumps(paged,ensure_ascii=False,indent=2)+'\n')

mode={'state':'ready','paged':False};release=threading.Event();release.set();requests=[];arrivals=[]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  u=urllib.parse.urlparse(self.path);q=urllib.parse.parse_qs(u.query)
  if not u.path.startswith('/api/'):return super().do_GET()
  state=mode['state'];status=200;is_paged=mode['paged'];arrivals.append({'path':u.path,'query':q,'state':state,'paged':is_paged})
  if u.path=='/api/biocatalyst/v1/what-matters-next':
   if state=='slow':release.wait(30)
   if is_paged:
    for k,v in paged['query'].items():assert q.get(k)==[v],(k,q)
    if q.get('cursor'):
     assert q['cursor']==[paged['append_query']['cursor']]
     r=paged['responses']['append_'+state if state in ('locked','error') else 'append']
    else:r=paged['responses']['first']
    status=r['status'];body=r['body']
   elif state=='locked':status=403;body=responses['locked']
   elif state=='error':status=503;body=responses['error']
   else:body=responses['horizons'][q.get('horizon_days',['90'])[0]]
  elif u.path=='/api/biocatalyst/v1/what-matters-next/detail':
   ref=q.get('event_fact_ref',[''])[0]
   if q.get('generation_id',[''])[0]!=fixture['list']['generation_id']:status=409;body={'detail':'RELOAD_REQUIRED'}
   elif ref not in responses['details']:status=404;body={'detail':'EVENT_NOT_IN_GENERATION'}
   else:body=responses['details'][ref]
  else:status=503;body={'detail':'LOCAL_FIXTURE_ROUTE_NOT_PROVIDED'}
  b=json.dumps(body,ensure_ascii=False).encode();requests.append({'path':u.path,'query':q,'state':state,'status':status,'body_sha256':hashlib.sha256(b).hexdigest()})
  self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','private, no-store');self.send_header('Content-Length',str(len(b)));self.end_headers()
  try:self.wfile.write(b)
  except BrokenPipeError:pass
server=socketserver.ThreadingTCPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(W/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
checks=[];cases=[]
def check(case,label,ok,value=None):checks.append({'case':case,'check':label,'pass':bool(ok),'actual':value})
def toggle_language(page):
 old=page.locator('html').get_attribute('data-lang');new='zh' if old=='en' else 'en'
 gear=page.locator('button#settings-open')
 page.mouse.move(1,1)
 gear.scroll_into_view_if_needed()
 gear.focus()
 if not page.locator('#settings-pop').evaluate("(e)=>e.classList.contains('open')"):
  gear.press('Enter')
 page.wait_for_function("document.querySelector('#settings-pop').classList.contains('open')",timeout=5000)
 control=page.locator('#settings-pop #set-lang-slot .lang-toggle[role="switch"]')
 control.wait_for(state='visible',timeout=5000)
 for _ in range(20):
  if control.evaluate('(e)=>document.activeElement===e'):break
  page.keyboard.press('Tab')
 else:raise AssertionError('Language switch not reachable by native Tab')
 assert control.is_visible()
 page.keyboard.press('Space')
 page.wait_for_function("(l)=>document.documentElement.getAttribute('data-lang')===l",arg=new)
 assert page.locator('html').get_attribute('lang')==('zh-CN' if new=='zh' else 'en')
 assert control.get_attribute('aria-checked')==('true' if new=='zh' else 'false')
 page.keyboard.press('Escape')
 return new
def wait_arrival(page,before):
 for _ in range(100):
  if len(arrivals)>before:return
  page.wait_for_timeout(50)
 raise AssertionError('API request never arrived')
def failure_truth(page,state,lang):
 expected=('需要完整访问权限才能显示生物科技研究优先项。' if lang=='zh' else 'Full access is required before biotechnology research priorities can be shown.') if state=='locked' else ('“下一步看什么”暂时不可用。不会推断任何研究优先级。' if lang=='zh' else 'What Matters Next is temporarily unavailable. No research priority is inferred.')
 status=('需要完整访问权限' if lang=='zh' else 'Full access required') if state=='locked' else ('决策智能数据暂不可用' if lang=='zh' else 'Decision-intelligence cut unavailable')
 return page.locator('#bci-wmn-queue').inner_text()==expected and page.locator('#bci-wmn-status').inner_text()==status and page.locator('#bci-wmn').get_attribute('data-state')==state and page.locator('.bci-wmn-card').count()==0 and not page.locator('#bci-wmn-load-more').is_visible() and not page.locator('#bci-wmn-asof').inner_text() and not page.locator('#bci-wmn-coverage').inner_text()
def settled(page):page.wait_for_function("!document.querySelector('#bci-wmn-refresh').disabled && document.querySelector('#bci-wmn-queue').getAttribute('aria-busy')==='false'")
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(headless=True)
  for width,height in [(1440,900),(390,844)]:
   for theme in ['dark','light']:
    for lang in ['en','zh']:
     case=f'{width}-{theme}-{lang}';mode['state']='ready';mode['paged']=False;errors=[];http_errors=[];start=len(requests)
     if args.case and case!=args.case:continue
     context=browser.new_context(viewport={'width':width,'height':height},device_scale_factor=1)
     context.add_init_script("localStorage.setItem('theme',"+json.dumps(theme)+");localStorage.removeItem('themeAuto');localStorage.setItem('lang',"+json.dumps(lang)+");")
     page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:http_errors.append({'status':r.status,'url':r.url}) if r.status>=400 else None)
     page.goto(f'http://127.0.0.1:{server.server_address[1]}/biocatalyst.html',wait_until='networkidle')
     page.evaluate("(s)=>{window.setTheme(s.theme);window.setLang(s.lang)}",{'theme':theme,'lang':lang});page.wait_for_timeout(1250)
     root=page.locator('#bci-wmn');refresh=page.locator('#bci-wmn-refresh');queue=page.locator('#bci-wmn-queue');detail=page.locator('#bci-wmn-detail')
     refresh.click();settled(page)
     cards=root.locator('.bci-wmn-card');check(case,'two_actual_api_fixture_rows',cards.count()==2,cards.count())
     first=cards.nth(0);first.scroll_into_view_if_needed();page.mouse.move(1,1)
     normal=first.evaluate("(e)=>({background:getComputedStyle(e).backgroundColor,border:getComputedStyle(e).borderTopColor})")
     first.hover();hover=first.evaluate("(e)=>({matched:e.matches(':hover'),background:getComputedStyle(e).backgroundColor,border:getComputedStyle(e).borderTopColor})")
     check(case,'unselected_card_hover',hover['matched'] and (hover['background']!=normal['background'] or hover['border']!=normal['border']),{'rest':normal,'hover':hover})
     page.mouse.move(1,1);first.focus();page.keyboard.press('Shift+Tab');page.keyboard.press('Tab')
     focus=first.evaluate("(e)=>({active:document.activeElement===e,visible:e.matches(':focus-visible'),width:parseFloat(getComputedStyle(e).outlineWidth),style:getComputedStyle(e).outlineStyle})")
     check(case,'real_keyboard_card_focus',focus['active'] and focus['visible'] and focus['width']>=2 and focus['style']=='solid',focus)
     page.keyboard.press('Enter');detail.locator('.bci-wmn-authority').wait_for(state='visible')
     page.mouse.move(1,1)
     selected=cards.nth(0).evaluate("(e)=>({selected:e.classList.contains('is-selected'),aria:e.getAttribute('aria-selected'),background:getComputedStyle(e).backgroundColor,border:getComputedStyle(e).borderTopColor})")
     check(case,'keyboard_selection_and_dossier',selected['selected'] and selected['aria']=='true' and root.locator('.bci-wmn-card.is-selected').count()==1 and detail.locator('.bci-wmn-authority').is_visible(),selected)
     check(case,'selected_paint_persists',selected['background']!=normal['background'] or selected['border']!=normal['border'])
     details_requested=[r for r in requests[start:] if r['path'].endswith('/detail')]
     check(case,'detail_bound_to_selected_identity',bool(details_requested) and details_requested[-1]['query'].get('event_fact_ref')==[fixture['list']['rows'][0]['event_fact_ref']])
     representative=(width==1440 and lang=='en') or (width==390 and lang=='zh')
     if representative:root.screenshot(path=str(OUT/f'selected-{case}.png'))
     trial=root.locator('.bci-wmn-head .bci-wmn-trial-link');trial.scroll_into_view_if_needed();trial.evaluate('(e)=>e.blur()');page.mouse.move(1,1)
     linkrest=trial.evaluate('(e)=>getComputedStyle(e).backgroundColor');trial.hover();linkhover=trial.evaluate('(e)=>getComputedStyle(e).backgroundColor')
     check(case,'continuation_hover_paint',linkrest!=linkhover,{'rest':linkrest,'hover':linkhover})
     trial.click();page.wait_for_function("location.hash==='#bci-trial-intelligence'")
     check(case,'real_trial_continuation_anchor',page.locator('#bci-trial-intelligence').count()==1 and page.evaluate("location.hash==='#bci-trial-intelligence'"))
     root.locator('[data-horizon="30"]').click();settled(page)
     active=root.locator('[data-horizon].is-active');latest=[r for r in requests[start:] if r['path'].endswith('/what-matters-next')][-1]
     check(case,'actual_horizon_request_and_control',active.count()==1 and active.get_attribute('data-horizon')=='30' and active.get_attribute('aria-pressed')=='true' and latest['query'].get('horizon_days')==['30'] and latest['query'].get('limit')==['50'],latest)
     check(case,'horizon_response_rendered',cards.count()==len(by_horizon['30']['rows']),{'visible':cards.count(),'api_rows':len(by_horizon['30']['rows'])})
     root.locator('[data-horizon="90"]').click();settled(page);check(case,'return_to_ninety',cards.count()==2)
     mode['state']='slow';release.clear();before_arrival=len(arrivals);refresh.click();wait_arrival(page,before_arrival)
     page.wait_for_function("document.querySelector('#bci-wmn-refresh').disabled && document.querySelector('#bci-wmn-queue').getAttribute('aria-busy')==='true'")
     check(case,'current_request_loading_disabled',refresh.is_disabled() and page.locator('#bci-wmn-load-more').is_disabled())
     arrival_count=len(arrivals)
     for _ in range(2):
      locale=toggle_language(page)
      check(case,'pending_language_'+locale,refresh.is_disabled() and page.locator('#bci-wmn-load-more').is_disabled() and queue.get_attribute('aria-busy')=='true' and len(arrivals)==arrival_count)
     release.set();settled(page);mode['state']='ready'
     check(case,'loading_settles',not refresh.is_disabled() and queue.get_attribute('aria-busy')=='false')
     normal_border=root.locator('.bci-wmn-summary').evaluate('(e)=>getComputedStyle(e).borderTopColor')
     for state in ['locked','error']:
      mode['state']=state;refresh.click();page.wait_for_function("(s)=>document.querySelector('#bci-wmn').dataset.state===s",arg=state);settled(page)
      status=page.locator('#bci-wmn-status').inner_text();explanation=queue.inner_text();border=root.locator('.bci-wmn-summary').evaluate('(e)=>getComputedStyle(e).borderTopColor')
      check(case,state+'_real_http_state',root.get_attribute('data-state')==state and cards.count()==0,{'status':status,'explanation':explanation,'border':border})
      check(case,state+'_clears_previous_cut',not page.locator('#bci-wmn-asof').inner_text() and not page.locator('#bci-wmn-coverage').inner_text() and not page.locator('#bci-wmn-load-more').is_visible())
      check(case,state+'_warning_border',border!=normal_border,{'rest':normal_border,'warning':border})
      check(case,state+'_localized_copy',('Full access required' in status if state=='locked' else 'No research priority is inferred' in explanation) if lang=='en' else any('\u4e00'<=c<='\u9fff' for c in status+explanation))
      if representative:root.screenshot(path=str(OUT/f'{state}-{case}.png'))
      count_before_language=len(arrivals)
      for _ in range(2):
       locale=toggle_language(page)
       check(case,state+'_language_'+locale,failure_truth(page,state,locale))
       check(case,state+'_language_no_refetch_'+locale,len(arrivals)==count_before_language)
     mode['state']='ready';refresh.click();settled(page);check(case,'recover_from_failure',cards.count()==2)
     mode['paged']=True;more=page.locator('#bci-wmn-load-more')
     for append_state in ['locked','error','slow']:
      mode['state']='ready';refresh.click();settled(page)
      check(case,'pagination_first_'+append_state,cards.count()==50 and more.is_visible())
      mode['state']=append_state
      if append_state=='slow':release.clear()
      before_arrival=len(arrivals);more.click();wait_arrival(page,before_arrival)
      if append_state!='slow':
       page.wait_for_function("(s)=>document.querySelector('#bci-wmn').dataset.state===s",arg=append_state);settled(page)
      else:
       page.wait_for_function("document.querySelector('#bci-wmn-queue').getAttribute('aria-busy')==='true'")
      request_count=len(arrivals)
      for _ in range(2):
       locale=toggle_language(page)
       if append_state=='slow':
        check(case,'append_pending_language_'+locale,cards.count()==50 and more.is_visible() and more.is_disabled() and refresh.is_disabled() and queue.get_attribute('aria-busy')=='true')
       else:check(case,'append_'+append_state+'_language_'+locale,failure_truth(page,append_state,locale))
       check(case,'append_'+append_state+'_no_refetch_'+locale,len(arrivals)==request_count)
      if append_state=='slow':
       release.set();settled(page)
       keys=cards.evaluate_all("(els)=>els.map(e=>e.getAttribute('data-wmn-key'))")
       check(case,'append_pending_completes_51',cards.count()==51 and len(set(keys))==51 and not more.is_visible() and not refresh.is_disabled() and queue.get_attribute('aria-busy')=='false',{'rows':cards.count(),'unique_keys':len(set(keys))})
     mode['state']='ready';mode['paged']=False;refresh.click();settled(page)
     check(case,'no_document_overflow',page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
     check(case,'no_js_page_errors',not errors,errors)
     cases.append({'case':case,'expected_http_errors':http_errors,'page_errors':errors,'request_count':len(requests)-start})
     context.close()
  browser.close()
finally:
 release.set();server.shutdown();server.server_close()
report={'schema':'macro.biocatalyst.wmn_browser_proof.v1','source':'3901ec90c4fd5c31df3eeb670c9992a7ac1155d9','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kind':'SYNTHETIC_API_FIXTURE','production':False,'test_clock':str(m.NOW),'language_activation':'Existing Settings pane; real Tab to visible language switch and Space; no direct setLang during failed or pending states','response_fixture_sha256':hashlib.sha256((P/'interaction-api-responses-r10.json').read_bytes()).hexdigest(),'pagination_fixture_sha256':hashlib.sha256((P/'pagination-api-fixture-r10.json').read_bytes()).hexdigest(),'checks':checks,'cases':cases,'requests':requests,'arrivals':arrivals,'result':'PASS' if all(c['pass'] for c in checks) else 'FAIL'}
(OUT/'receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'result':report['result'],'checks':len(checks),'failures':[c for c in checks if not c['pass']],'receipt':str(OUT/'receipt.json')},ensure_ascii=False),flush=True)
sys.exit(0 if report['result']=='PASS' else 1)
