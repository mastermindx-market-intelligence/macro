from pathlib import Path
import subprocess,sys,time,json
P=Path(__file__).parent
server_dir=P/'timing-server'
assert not server_dir.exists()
with (P/'timing-server.log').open('w') as server_log:
 server=subprocess.Popen([sys.executable,str(P/'diagnostic_server.py'),str(P/'stage'),str(server_dir),'--port','58746'],stdout=server_log,stderr=subprocess.STDOUT)
 try:
  for _ in range(100):
   if server.poll() is not None:raise RuntimeError('server exited before receipt')
   if (server_dir/'SERVER_RECEIPT.json').exists():break
   time.sleep(.1)
  else:raise RuntimeError('server receipt unavailable')
  with (P/'timing.log').open('w') as log:
   subprocess.run([sys.executable,str(P/'diagnostic_timing.py'),'http://127.0.0.1:58746/government_revenue.html',str(P/'stage'),str(server_dir/'SERVER_RECEIPT.json'),str(P/'TIMING_TEN.json'),'--samples','10','--initial-server-state','fresh-process-cold-readers','--expected-issuer','LMT','--expected-unit','USD millions','--expected-value','4101','--expected-period','2026Q2'],stdout=log,stderr=subprocess.STDOUT,check=True)
 finally:
  server.terminate();server.wait(timeout=30)
x=json.loads((P/'TIMING_TEN.json').read_text())
print(json.dumps({k:x[k] for k in ['all_pass','measurement_complete','median_ms','p95_ms','max_ms']}))
