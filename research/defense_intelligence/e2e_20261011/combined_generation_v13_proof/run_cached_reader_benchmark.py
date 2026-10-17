from pathlib import Path
import subprocess,sys,time,json,signal,hashlib,statistics,math,concurrent.futures,urllib.request,threading
P=Path(__file__).parent
server_dir=P/'cached-reader-server'
assert not server_dir.exists()
url='http://127.0.0.1:58746'
paths=['/api/government-revenue/dossier/company/LMT','/api/government-revenue/defense-economics','/government-revenue-data/program-dossier.json']
def read(path):
 start=time.perf_counter()
 with urllib.request.urlopen(url+path,timeout=30) as r:
  raw=r.read();status=r.status
 obj=json.loads(raw);assert isinstance(obj,dict)
 return {'ms':(time.perf_counter()-start)*1000,'status':status,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
report={'scope':'Actual source local ASGI and static generated dossier; explicit local test-principal. Not installed/customer entitlement or WAN performance.','source_head':'fc04588278e12b5e693cbea72fea3193986f78d1','concurrent_readers':10,'per_reader_requests':10,'target_p95_ms':1000,'routes':{}}
with (P/'cached-reader-server.log').open('w') as log:
 server=subprocess.Popen([sys.executable,'/Volumes/Mastermind/evidence/defense-v3-20261012/o5/release-acceptance-o7/serve_final_asgi_buffered_receipts.py',str(P/'stage'),str(server_dir),'--port','58746'],stdout=log,stderr=subprocess.STDOUT)
 try:
  for _ in range(100):
   if server.poll() is not None:raise RuntimeError('server exited')
   if (server_dir/'SERVER_RECEIPT.json').exists():break
   time.sleep(.1)
  else:raise RuntimeError('server receipt unavailable')
  time.sleep(.2)
  for path in paths:
   warm=read(path);barrier=threading.Barrier(10)
   def worker(_):
    barrier.wait();return [read(path) for _ in range(10)]
   with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:rows=[r for group in pool.map(worker,range(10)) for r in group]
   values=sorted(r['ms'] for r in rows);same=all(r['sha256']==warm['sha256'] and r['status']==200 for r in rows)
   entry={'warmup':warm,'samples':rows,'samples_n':len(rows),'same_bytes':same,'median_ms':statistics.median(values),'p95_ms':values[math.ceil(len(values)*.95)-1],'max_ms':max(values)};entry['pass']=len(rows)==100 and same and entry['p95_ms']<=1000;report['routes'][path]=entry
   print(json.dumps({'route':path,**{k:entry[k] for k in ['samples_n','same_bytes','median_ms','p95_ms','max_ms','pass']}}),flush=True)
 finally:
  server.send_signal(signal.SIGINT);server.wait(timeout=30)
report['all_pass']=all(v['pass'] for v in report['routes'].values()) and len(report['routes'])==3
report['server_request_journal_retained']=(server_dir/'REQUESTS.json').exists()
report['server_receipt_sha256']=hashlib.sha256((server_dir/'SERVER_RECEIPT.json').read_bytes()).hexdigest()
(P/'CACHED_READER_BENCHMARK.json').write_text(json.dumps(report,indent=2)+'\n')
