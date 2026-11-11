from pathlib import Path
import sys,json,threading,functools,hashlib
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import capture_page_evidence as cap
OUT=Path(__file__).resolve().parent
OUT.mkdir(parents=True,exist_ok=True)
class Handler(SimpleHTTPRequestHandler):
 def log_message(self,*args): pass
server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port)
metrics=[]
class Driver:
 def __init__(self,**kwargs): self.base=cap.playwright_page_driver(**kwargs)
 def close(self): self.base.close()
 def capture(self,*,url,cell,timeout_s):
  if cell.force_state is None: return self.base.capture(url=url,cell=cell,timeout_s=timeout_s)
  state={'theme':cell.theme,'locale':cell.locale}
  ctx=self.base._browser.new_context(viewport={'width':cell.width,'height':cell.height},color_scheme=cell.theme,device_scale_factor=1)
  ctx.add_init_script(cap.state_seed_source(state)); page=ctx.new_page()
  errors=[]; failures=[]
  page.on('pageerror',lambda e:errors.append({'text':str(e),'source_url':None}))
  page.on('response',lambda r:failures.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
  try:
   response=page.goto(url,wait_until='load',timeout=timeout_s*1000)
   assert response and response.ok
   applied=page.evaluate(cap._APPLY_STATE_SCRIPT,state)
   cap._wait_transient_fx_gone(page)
   # Explicit local presentation state, NOT an authenticated production witness.
   page.evaluate("window.MMXAccessPreview={isAnon:()=>false,openSignin:()=>{throw Error('Local member fixture should not sign in')}}")
   page.locator('#mx5BtnRisk').click()
   if cell.force_state.kind=='focus': page.locator(cell.force_state.value).focus()
   page.wait_for_timeout(650)
   assert page.locator('#risk-envelope-band').is_visible()
   m=page.evaluate("""() => {const b=document.getElementById('risk-envelope-band'); const d=document.querySelector('#dlg-risk .mx5-dlg-panel'); return {context_height:b.getBoundingClientRect().height,dialog_width:d.getBoundingClientRect().width,viewport_width:innerWidth,page_overflow:document.documentElement.scrollWidth>innerWidth,inside_radar:!!b.closest('#dlg-risk'),evidence_open:b.querySelector('details').open,focused_summary:document.activeElement===b.querySelector('summary')};} """)
   assert m['inside_radar'] and not m['page_overflow'],m
   if cell.force_state.kind=='focus':
    assert m['focused_summary']
    page.keyboard.press('Enter'); assert page.locator('#risk-envelope-band details').get_attribute('open') is not None
    page.keyboard.press('Enter')
   metrics.append({'cell':cell.cell_id,**m})
   png=page.screenshot(full_page=False)
   # Stable convenient review copies in the same evidence directory.
   name=f'{cell.viewport}-{cell.locale}-{cell.theme}-{cell.force_state.name}.png'
   (OUT/name).write_bytes(png)
   observed=page.evaluate(cap._OBSERVER_SCRIPT,dict(self.base._observer_config)) or {}
   return cap.CellObservation(cell_id=cell.cell_id,loaded=True,screenshot_png=png,observed=observed,console_errors=tuple(errors),failed_responses=tuple(failures),applied_theme=applied.get('theme'),applied_locale=applied.get('locale'),applied_force_state=cell.force_state.name)
  except Exception as e:
   return cap.CellObservation(cell_id=cell.cell_id,loaded=False,error=str(e),console_errors=tuple(errors),failed_responses=tuple(failures))
  finally:ctx.close()
try:
 result=cap.main(['--registry','/Volumes/Mastermind/agent-evidence/risk-radar-explanations-live-20260920/page_registry.json','--base-url',url,'--routes','macro.html','--viewports','desktop,mobile','--output-dir',str(OUT),'--manifest',str(OUT/'manifest.json'),'--smells',str(OUT/'smells.json'),'--emit-md',str(OUT/'REPORT.md'),'--settle-ms','300','--delay-ms','0','--timeout-s','40','--force-state','radar_open:.open','--force-state','radar_focus:focus(#dlg-risk .gde-disc > summary)'],driver_factory=Driver)
 (OUT/'interaction-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
 print('CAPTURE_EXIT',result,'FORCED_CELLS',len(metrics))
 print(json.dumps(metrics[:2]))
 sys.exit(result)
finally: server.shutdown();server.server_close()
