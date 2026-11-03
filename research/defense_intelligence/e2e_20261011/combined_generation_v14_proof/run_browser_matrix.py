from pathlib import Path
import subprocess,sys,time,signal,json
p=Path(__file__).parent;o=Path('/Volumes/Mastermind/evidence/defense-v3-20261012/o5');output=p/'browser-server';assert not output.exists()
with (p/'browser-server.log').open('w') as log:
 server=subprocess.Popen([sys.executable,str(o/'release-acceptance-o7/serve_final_asgi_buffered_receipts.py'),str(p/'stage'),str(output),'--port','58746'],stdout=log,stderr=subprocess.STDOUT)
 try:
  for _ in range(100):
   if server.poll() is not None:raise RuntimeError('server exited; inspect exact original log')
   if (output/'SERVER_RECEIPT.json').exists():break
   time.sleep(.1)
  else:raise RuntimeError('server receipt unavailable')
  result=subprocess.run([sys.executable,str(o/'performance-priority-build/recovery-o6/capture_final_asgi.py'),str(p/'stage'),'http://127.0.0.1:58746',str(output/'SERVER_RECEIPT.json'),str(p/'browser-matrix')]);rc=result.returncode
 finally:
  server.send_signal(signal.SIGINT);server.wait(timeout=30)
print(json.dumps({'capture_exit':rc,'server_stopped':server.returncode,'journal_saved':(output/'REQUESTS.json').exists()}));sys.exit(rc)
