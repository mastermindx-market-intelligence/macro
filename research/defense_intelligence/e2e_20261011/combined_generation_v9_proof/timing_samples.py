"""Source-bound useful-finance timing. Final use requires a sealed root build.

Ten fresh browser contexts; cache disabled; exact ASGI local test principal.
No credentials, route interception, payload rewriting, or customer acceptance.
"""
import argparse, hashlib, json, math, statistics
from pathlib import Path
from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('url'); ap.add_argument('stage'); ap.add_argument('server_receipt')
ap.add_argument('output'); ap.add_argument('--samples', type=int, default=10)
ap.add_argument('--initial-server-state', choices=['fresh-process-cold-readers','already-warm-readers'], required=True)
ap.add_argument('--expected-issuer', required=True)
ap.add_argument('--expected-unit', required=True, help='Exact reported unit from the frozen issuer payload; never an assumed currency')
ap.add_argument('--expected-value', required=True, help='Exact displayed reported numeric value from frozen payload')
ap.add_argument('--expected-period', required=True, help='Exact reported period from frozen payload')
a = ap.parse_args()
assert a.samples == 10, 'Contractual final batch requires exactly ten samples'
stage = Path(a.stage); server = Path(a.server_receipt); out = Path(a.output)
from verify_stage import verify_stage
verify_stage(stage)
assert not out.exists(), 'Evidence is immutable; choose a new authorized output'
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
input_receipt = stage / 'INPUT_RECEIPT.json'
bound = json.loads(input_receipt.read_text())
assert digest(stage / 'government_revenue.html') == bound['html_sha256']
runtime = json.loads(server.read_text())
def verify_router_data():
 for path, expected in runtime.get('api_data_inputs', {}).items():
  actual = hashlib.sha256(Path(path).read_bytes()).hexdigest() if Path(path).is_file() else None
  assert actual == expected, 'Router data changed during qualification: ' + path
 assert runtime.get('api_data_inputs'), 'Use source-data-bound serve_final_asgi.py'
 assert sorted(str(path) for path in Path(runtime['canonical_input_directory']).rglob('*') if path.is_file())==runtime['canonical_input_inventory'], 'Canonical input inventory changed'
 for path, expected in runtime.get('api_source_modules', {}).items():
  assert digest(Path(path)) == expected, 'Router source dependency changed: ' + path
verify_router_data()

assert runtime['stage_receipt_sha256'] == digest(input_receipt)
assert runtime['denial_before_finance_validator'] is True
assert runtime['api_source_sha256'] == digest(Path(runtime['source_root']) / 'app/government_revenue.py')
rows = []
measurement = r"""(()=>{
 let prior=false, mutations=0, firstReady=null;
 const read=s=>{let e=document.querySelector(s);if(!e)return null;let r=e.getBoundingClientRect(),style=getComputedStyle(e),visible=typeof e.checkVisibility==='function'?e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true}):style.visibility!=='hidden'&&style.display!=='none'&&Number(style.opacity)>0;return {text:e.textContent.trim(),x:r.x,y:r.y,width:r.width,height:r.height,visible,fully_inside:visible&&r.width>0&&r.height>0&&r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight}};
 const geometry=()=>({scrollY,viewport:{width:innerWidth,height:innerHeight},value:read('#defenseInvestor[data-state=ready] .gr-investor-primary dd'),period:read('#defenseInvestor[data-state=ready] .gr-investor-primary dt'),issuer:read('[data-investor-ticker][aria-pressed=true]')});
 new MutationObserver(()=>{mutations++;let g=geometry();if(firstReady===null&&g.value&&g.period&&g.issuer)firstReady=performance.now()}).observe(document,{subtree:true,childList:true,attributes:true,characterData:true});
 function frame(){let g=geometry(), expected=window.__timingExpected, good=g.scrollY===0&&['value','period','issuer'].every(k=>g[k]&&g[k].text&&g[k].fully_inside)&&/\d/.test(g.value.text)&&/\d{4}/.test(g.period.text)&&g.issuer.text===expected.issuer&&g.value.text===expected.value+' '+expected.unit&&g.period.text.endsWith(' · '+expected.period);if(good&&prior){window.__firstUseful={ms:performance.now(),geometry:g,mutation_batches:mutations,first_ready_mutation_ms:firstReady};return}prior=good;requestAnimationFrame(frame)}requestAnimationFrame(frame);
})();"""
with sync_playwright() as p:
 b=p.chromium.launch()
 for i in range(a.samples):
  c=None; response=None; failures=[]; errors=[]
  row={'ms':None,'resources':[],'sample':i+1,'server_state':a.initial_server_state if i==0 else 'warm readers; fresh browser','content_encoding':None,'navigation_status':None}
  try:
   c=b.new_context(viewport={'width':390,'height':844},ignore_https_errors=True)
   page=c.new_page(); cdp=c.new_cdp_session(page)
   cdp.send('Network.enable'); cdp.send('Network.setCacheDisabled',{'cacheDisabled':True})
   cdp.send('Network.emulateNetworkConditions',{'offline':False,'latency':500,'downloadThroughput':200000,'uploadThroughput':200000,'connectionType':'cellular3g'})
   page.on('response',lambda r: failures.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
   page.on('pageerror',lambda e: errors.append(str(e)))
   page.add_init_script('window.__timingExpected='+json.dumps({'issuer':a.expected_issuer,'unit':a.expected_unit,'value':a.expected_value,'period':a.expected_period})+';'+measurement)
   response=page.goto(a.url,wait_until='commit')
   row['navigation_status']=response.status if response else None
   row['content_encoding']=response.headers.get('content-encoding','identity') if response else None
   assert response is not None and response.status == 200, 'Top-level page did not load'
   page.wait_for_function('window.__firstUseful',timeout=60000)
   row.update(page.evaluate('window.__firstUseful'))
  except Exception as exc:
   row['failure']=str(exc)
  if c is not None:
   try:
    row['resources']=page.evaluate("()=>performance.getEntriesByType('resource').map(p=>({path:new URL(p.name).pathname,start_ms:p.startTime,request_ms:p.requestStart,response_ms:p.responseStart,end_ms:p.responseEnd,nextHopProtocol:p.nextHopProtocol,encodedBodySize:p.encodedBodySize,transferSize:p.transferSize}))")
   except Exception as exc:
    row['resource_capture_failure']=str(exc)
   try: c.close()
   except Exception as exc: row['context_close_failure']=str(exc)
  row.update(http_errors=failures,page_errors=errors)
  geometry=row.get('geometry',{})
  row['meaningful_contract']=row['ms'] is not None and geometry.get('issuer',{}).get('text')==a.expected_issuer and geometry.get('value',{}).get('text')==a.expected_value+' '+a.expected_unit and geometry.get('period',{}).get('text','').endswith(' · '+a.expected_period)
  row['pass_target']=row['meaningful_contract'] and row['ms']<=3000 and not failures and not errors and row['content_encoding']=='gzip' and not any(key in row for key in ('failure','resource_capture_failure','context_close_failure'))
  rows.append(row)
  print(json.dumps({'sample':i+1,'ms':row['ms'],'pass_target':row['pass_target'],'navigation_status':row['navigation_status'],'http_errors_n':len(failures),'page_errors_n':len(errors),'failure':row.get('failure'),'resource_capture_failure':row.get('resource_capture_failure')}),flush=True)
 b.close()
assert runtime['api_source_sha256'] == digest(Path(runtime['source_root']) / 'app/government_revenue.py'), 'API source changed during evidence'
verify_router_data()
verify_stage(stage)
assert digest(input_receipt)==runtime['stage_receipt_sha256'], 'Stage receipt changed during evidence'
values=sorted(r['ms'] for r in rows if r['ms'] is not None)
complete=len(values)==a.samples
result={'scope':'Actual source ASGI local test-principal; installed entitlement and real customer acceptance remain separate','stage_receipt_sha256':digest(input_receipt),'server_receipt_sha256':digest(server),'url':a.url,'samples':rows,'profile':{'viewport':'390x844','latency_ms':500,'download_Bps':200000,'browser_cache':'disabled; new context per sample','measurement':'MutationObserver plus two consecutive rAF frames; numeric issuer value/unit/dated period fully visible at scrollY0','expected_issuer':a.expected_issuer,'expected_reported_unit':a.expected_unit,'expected_reported_value':a.expected_value,'expected_reported_period':a.expected_period},'target_ms':3000,'measurement_complete':complete,'all_pass':complete and all(r['pass_target'] for r in rows),'median_ms':statistics.median(values) if complete else None,'p95_ms':values[max(0,math.ceil(len(values)*.95)-1)] if complete else None,'max_ms':max(values) if complete else None,'observed_samples_n':len(values),'failed_samples_n':a.samples-len(values)}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:result[k] for k in ['all_pass','median_ms','p95_ms','max_ms']}))
