from pathlib import Path
import json,sys,os,http.server,socketserver,threading,functools,subprocess,urllib.parse,hashlib
import argparse
parser=argparse.ArgumentParser(description='Reproduce canonical WMN captures from the bound C4 shell and synthetic API fixture.')
parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[3])
parser.add_argument('--output-dir',type=Path,required=True)
args=parser.parse_args()
W=args.repo.resolve();P=args.output_dir.resolve();E=P
P.mkdir(parents=True,exist_ok=True)

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

f=json.loads((proof_dir/'wmn-api-fixture.json').read_text());requests=[]
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  u=urllib.parse.urlparse(self.path);q=urllib.parse.parse_qs(u.query)
  if u.path.startswith('/api/'):
   requests.append({'path':u.path,'query':q})
   if u.path=='/api/biocatalyst/v1/what-matters-next':
    status=200;body=f['list']
   elif u.path=='/api/biocatalyst/v1/what-matters-next/detail':
    ref=q.get('event_fact_ref',[''])[0];gen=q.get('generation_id',[''])[0]
    if gen!=f['list']['generation_id']:status=409;body={'detail':'RELOAD_REQUIRED'}
    elif ref not in f['details']:status=404;body={'detail':'EVENT_NOT_IN_GENERATION'}
    else:status=200;body=f['details'][ref]
   else:status=503;body={'detail':'LOCAL_FIXTURE_ROUTE_NOT_PROVIDED'}
   data=json.dumps(body,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','private, no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
  return super().do_GET()
server=socketserver.ThreadingTCPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(W/'site')))
threading.Thread(target=server.serve_forever,daemon=True).start()
E.mkdir(parents=True,exist_ok=True)
env=dict(os.environ)
url=f'http://127.0.0.1:{server.server_address[1]}'
cmd=[sys.executable,'scripts/capture_page_evidence.py','--base-url',url,'--routes','/biocatalyst.html','--repo','macro','--viewports','desktop,mobile','--locales','en,zh','--themes','dark,light','--output-dir',str(E/'captures'),'--manifest',str(E/'manifest.json'),'--smells',str(E/'smells.json'),'--settle-ms','1250','--delay-ms','0','--max-pages','1','--force-state','card-hover:hover(.bci-wmn-card:first-child)','--force-state','card-focus:focus(.bci-wmn-card:first-child)','--force-state','link-hover:hover(.bci-wmn-head .bci-wmn-trial-link)','--force-state','link-focus:focus(.bci-wmn-head .bci-wmn-trial-link)']
try:
 with (P/'canonical-capture-r2.log').open('w') as log:r=subprocess.run(cmd,cwd=W,env=env,stdout=log,stderr=subprocess.STDOUT)
finally:server.shutdown();server.server_close()
(P/'canonical-request-log-r2.json').write_text(json.dumps(requests,indent=2)+'\n')
obs=json.loads((proof_dir/'render-observation.json').read_text())
assert hashlib.sha256((W/'site/biocatalyst.html').read_bytes()).hexdigest()==obs['html_sha256']
receipt={'exit_code':r.returncode,'source':obs['source'],'kind':'SYNTHETIC_API_FIXTURE','fixture_file_sha256':obs['fixture_sha256'],'html_unchanged':True,'non_wmn_apis':'Explicit local503; no production entitlement/owner claim','request_count':len(requests)}
(P/'canonical-capture-exit-r2.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
sys.exit(r.returncode)
