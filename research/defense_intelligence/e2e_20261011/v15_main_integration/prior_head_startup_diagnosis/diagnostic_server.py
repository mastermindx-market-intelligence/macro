"""Loopback source-runtime test owner, with explicit local test-principal only.
Actual router entitlement dependency ordering and every payload validator retained.
No credentials or installed entitlement claim; generated static bytes unmodified.
"""
import os,sys,json,hashlib,time,argparse,asyncio
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('stage');ap.add_argument('output');ap.add_argument('--port',type=int,default=58743);a=ap.parse_args();w=Path('/Volumes/Mastermind/agent-workspaces/codex/ed19/macro-main');sys.path.insert(0,str(w));os.environ['MACRO_REPO']=str(w)
from fastapi import FastAPI,HTTPException
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
from app import government_revenue as api
from unittest.mock import patch
from threading import Lock
sys.path.append('/opt/homebrew/lib/python3.11/site-packages') # installed pure-Python uvicorn; current FastAPI stays first
import uvicorn
s=Path(a.stage);o=Path(a.output);assert not o.exists();o.mkdir();app=FastAPI();app.include_router(api.router);attempts=[]
# First prove a denied request cannot enter the finance loader/validator. Then
# install a named local test dependency; this never changes source entitlement.
def denied():raise HTTPException(status_code=401,detail='explicit local denial fixture')
app.dependency_overrides[api.require_site_full_user]=denied
with TestClient(app) as client,patch.object(api,'validate_defense_economics_payload',side_effect=AssertionError('denied request entered validator')) as validator:
 response=client.get('/api/government-revenue/defense-economics');assert response.status_code==401 and validator.call_count==0
app=FastAPI();app.include_router(api.router) # fresh server after independent denial probe
app.dependency_overrides[api.require_site_full_user]=lambda:{'sub':'local-stage-entitled-standin'}
from starlette.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware,minimum_size=500) # ordinary matched local transport approximation
app.mount('/',StaticFiles(directory=str(s),html=True),name='exact-generated-static')
lock=Lock();rows=[]
@app.middleware('http')
async def receipt(request,call_next):
 start=time.perf_counter();response=await call_next(request)
 row={'started_monotonic':start,'ended_monotonic':time.perf_counter(),'path':request.url.path,'query':str(request.url.query),'status':response.status_code,'elapsed_ms':(time.perf_counter()-start)*1000}
 with lock:
  rows.append(row)
 return response
# Freeze actual router source-data dependencies as well as generated stage bytes.
api_data_inputs = {}
api_source_modules={}
for module in tuple(sys.modules.values()):
 filename=getattr(module,'__file__',None)
 if not filename: continue
 path=Path(filename).resolve()
 if not (path.is_file() and path.is_relative_to(w.resolve()) and path.suffix=='.py'): continue
 api_source_modules[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
 for key, value in vars(module).items():
  if not key.isupper(): continue
  candidates=value if isinstance(value,(tuple,list)) else (value,)
  for dependency in candidates:
   if isinstance(dependency,Path) and dependency.resolve().is_relative_to(w.resolve()) and not dependency.is_dir():
    api_data_inputs[str(dependency)]=hashlib.sha256(dependency.read_bytes()).hexdigest() if dependency.is_file() else None
assert api_data_inputs, 'No canonical reader data dependencies discovered'
# Directory-derived reader filenames are not always module-level Path constants.
# Pin the bounded canonical government-revenue input family as a complete inventory.
canonical_input_directory=w/'data/government_revenue'
canonical_input_inventory=sorted(str(path) for path in canonical_input_directory.rglob('*') if path.is_file())
for name in canonical_input_inventory:
 path=Path(name);api_data_inputs[name]=hashlib.sha256(path.read_bytes()).hexdigest()
r={'scope':'Actual source ASGI router and all validators, local loopback test-principal dependency; NOT installed entitlement or production acceptance','source_root':str(w),'stage_receipt_sha256':hashlib.sha256((s/'INPUT_RECEIPT.json').read_bytes()).hexdigest(),'api_source_sha256':hashlib.sha256((w/'app/government_revenue.py').read_bytes()).hexdigest(),'auth_fixture':'explicit dependency override local-stage-entitled-standin; no credentials','denial_before_finance_validator':True,'validation':'all source endpoint loaders/validators unchanged','cache':'one new process; initial reader caches cold; subsequent browser samples warm server','compression_state':'gzip; ordinary Starlette GZipMiddleware minimum500/defaultlevel9; local approximation of independently verified installed gzip','port':a.port}
r['measurement_journal']='In-memory request rows, flushed after uvicorn returns; no synchronous filesystem writes on the request path'
r['harness_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
r['api_data_inputs']=api_data_inputs
r['api_source_modules']=api_source_modules
r['canonical_input_directory']=str(canonical_input_directory)
r['canonical_input_inventory']=canonical_input_inventory
(o/'SERVER_RECEIPT.json').write_text(json.dumps(r,indent=2));print(json.dumps({'scope':r['scope'],'port':a.port,'source_modules_n':len(api_source_modules),'data_inputs_n':len(api_data_inputs)}),flush=True)
loop_observations=[]
@app.on_event('startup')
async def observe_loop():
 async def sample():
  last=time.perf_counter();cpu=time.process_time()
  while True:
   await asyncio.sleep(.05)
   now=time.perf_counter();new_cpu=time.process_time()
   if now-last>.1:loop_observations.append({'monotonic':now,'gap_ms':(now-last)*1000,'process_cpu_ms':(new_cpu-cpu)*1000,'loadavg':os.getloadavg()})
   last=now;cpu=new_cpu
 app.state.diagnostic_loop_task=asyncio.create_task(sample())
def flush_diagnostics():
 (o/'REQUESTS.json').write_text(json.dumps(rows,indent=2))
 (o/'LOOP_DIAGNOSTICS.json').write_text(json.dumps(loop_observations,indent=2))
@app.on_event('shutdown')
async def retain_observation():
 app.state.diagnostic_loop_task.cancel()
 flush_diagnostics()
try:
 uvicorn.run(app,host='127.0.0.1',port=a.port,log_level='warning',http='h11',loop='asyncio')
finally:
 flush_diagnostics()
