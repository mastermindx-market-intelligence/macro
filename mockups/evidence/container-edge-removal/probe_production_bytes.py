"""Read normal public URLs and compare served presentation bytes with accepted Git."""
from pathlib import Path
from urllib.parse import urljoin,urlsplit,unquote
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import argparse,hashlib,json,posixpath,re,subprocess,sys
ap=argparse.ArgumentParser();ap.add_argument('--accepted',required=True);ap.add_argument('--base',required=True);ap.add_argument('--output',required=True);args=ap.parse_args()
assert re.fullmatch(r'[0-9a-f]{40}',args.accepted) and re.fullmatch(r'[0-9a-f]{40}',args.base)
R=Path.cwd();O=Path(args.output);O.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(R))
from lib.pages import css_imports
origin='https://www.mastermind-x.com'
def git(*v):return subprocess.check_output(['git',*v])
def sha(b):return hashlib.sha256(b).hexdigest()
paths=set(git('ls-tree','-r','--name-only',args.accepted,'--','site').decode().splitlines())
changed=set(git('diff','--no-renames','--name-only',args.base,args.accepted,'--','site').decode().splitlines())
def local_path(url):
 u=urlsplit(url)
 if u.scheme!='https' or u.hostname not in {'www.mastermind-x.com','mastermind-x.com'}:return None
 p='site/'+posixpath.normpath(unquote(u.path)).lstrip('/')
 return p if p in paths else None
def read(url):
 path=local_path(url);assert path,url
 expected=git('show',args.accepted+':'+path)
 row={'url':url,'path':path,'expected_sha256':sha(expected),'expected_bytes':len(expected)}
 try:
  with urlopen(Request(url),timeout=30) as response:
   observed=response.read();row.update(status=response.status,final_url=response.url,headers={k:response.headers.get(k) for k in ('Content-Type','Cache-Control','ETag','Last-Modified','Age','CF-Cache-Status') if response.headers.get(k)})
  row.update(observed_sha256=sha(observed),observed_bytes=len(observed),equal=observed==expected)
  return row,observed
 except (HTTPError,URLError,TimeoutError) as e:
  row.update(equal=False,error=type(e).__name__+': '+str(e));return row,b''
routes=['/macro.html','/aibrief.html','/products/market-terminal.html']
rows=[];asset_urls=set();html_payloads={}
for route in routes:
 row,body=read(origin+route);rows.append(row);html_payloads[route]=body
 if not row['equal']:continue
 for ref in re.findall(rb'(?<![\w-])(?:href|src)\s*=\s*["\']([^"\']+)',body,re.I):
  url=urljoin(origin+route,ref.decode());path=local_path(url)
  if path and (path.endswith('.css') or (path.endswith('.js') and path in changed)):asset_urls.add(url)
pending=sorted(asset_urls);seen=set(pending)
while pending:
 assert len(rows)+len(pending)<=160, 'unexpected presentation closure growth'
 with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(read,pending))
 pending=[]
 for row,body in results:
  rows.append(row)
  if row['equal'] and row['path'].endswith('.css'):
   for ref in css_imports(body.decode()):
    url=urljoin(row['url'],ref);path=local_path(url)
    if path and path.endswith('.css') and url not in seen:seen.add(url);pending.append(url)
assert len(rows)<=160, 'unexpected presentation closure growth'
report={'schema':'mastermind.container_edge_served_bytes.v1','observed_at':datetime.now(timezone.utc).isoformat(),'accepted_commit':args.accepted,'comparison_base':args.base,'origin':origin,'scope':'Three normal public HTML URLs, all their same-origin committed CSS/imports, and changed same-origin JavaScript they emit. Existing emitted version parameters are preserved; no cache-busting query is invented. Raw health/runtime payloads are not captured.','observations':rows,'passed':all(r['equal'] for r in rows)}
(O/'served-bytes.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'resources':len(rows),'html':len(routes),'mismatches':[{k:r.get(k) for k in ('url','status','error','expected_sha256','observed_sha256')} for r in rows if not r['equal']]}),flush=True)
raise SystemExit(0 if report['passed'] else 1)
