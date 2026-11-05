from pathlib import Path
import ast, hashlib, json, mimetypes, posixpath, re, subprocess, sys
from urllib.parse import urlsplit
from jinja2 import Environment, BaseLoader, TemplateNotFound
REPO=Path('/Volumes/Mastermind/agent-workspaces/macro/web/d05-native-source-verification-20261104')
OUT=REPO/'.pytest_cache/d05-ci-recovery-82c377/china-archive'
CODE='82c377fb79ec746a0705c3c62a0be0a760cb001a'
ARCHIVE='2e6c45899a9aeb7f90f03f85272aaff3ca42f4eb'
SITE=OUT/'site'
assert not SITE.exists(), 'Existing prepared source must be inspected, not overwritten'
SITE.mkdir(parents=True)
record={'code_ref':CODE,'code_equivalent_at':'5344e0e19b4032c831e8cff0cd6f67d9f473d50a','archive_ref':ARCHIVE,'fixture_only':True,'claim':'archived China browser qualification; no engine, forward log, production auth or freshness proof','sources':{},'missing':[]}
cache={}
def git(path,ref=CODE):
 key=(ref,path)
 if key not in cache:
  cache[key]=subprocess.check_output(['git','-C',str(REPO),'show',ref+':'+path])
 record['sources'][ref+':'+path]=hashlib.sha256(cache[key]).hexdigest()
 return cache[key]
known=set(subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','--name-only',CODE,'templates','site','lib','scripts','engine'],text=True).splitlines())
archive_known=set(subprocess.check_output(['git','-C',str(REPO),'ls-tree','-r','--name-only',ARCHIVE,'site'],text=True).splitlines())
for rel in ['engine/i18n.py','engine/sector_generation_guard.py','scripts/_cycles_payload.py','lib/shared_shell.py']:
 assert (REPO/rel).read_bytes()==git(rel), 'Working helper differs from qualified source: '+rel
sys.path.insert(0,str(REPO))
from engine import i18n
from scripts._cycles_payload import publication_scripts
from lib.shared_shell import inject_shared_shell_text
class Loader(BaseLoader):
 def get_source(self,env,name):
  path='templates/'+name
  if path not in known:raise TemplateNotFound(name)
  return git(path).decode(), CODE+':'+path, lambda:True
env=Environment(loader=Loader(),autoescape=False)
env.globals.update(td=i18n.td,tr=i18n.tr,t=i18n.t)
pages=['sector_central_china.html','sector_cycles_china.html']
for page in pages:
 html=env.get_template(page+'.j2').render()
 html=html.replace('<body','<body data-d05-fixture="archived-china"',1)
 html=html.replace('</body>','<div style="position:fixed;bottom:0;left:0;z-index:100000;background:var(--panel);color:var(--text);padding:3px 8px;font:11px sans-serif">D05 ARCHIVED CHINA · 2026-11-03 · not live</div></body>')
 (SITE/page).write_text(html)
payload_path='site/chinasectordata/sector_cycles.json'
raw=git(payload_path,ARCHIVE)
assert hashlib.sha256(raw).hexdigest()=='e5fd4fa4fbe8329e4707e6d6e75168976dfc8b325c84c6b1f2499f61d1329da7'
payload=json.loads(raw)
assert payload['meta']['region']=='china' and payload['meta']['asOf']=='2026-11-03' and payload['meta']['benchmark']=='SHCOMP'
publication=publication_scripts(payload,{}, {},sources={k:{'status':'missing','reason':'archive_annotation_unavailable','records':0} for k in ['narr','dna']})
for kind,suffix in [('core','data'),('series','series_data'),('narr','narr_data'),('dna','dna_data')]:
 (SITE/('sector_cycles_china_'+suffix+'.js')).write_text(publication[kind])
record['publication']={'asOf':payload['meta']['asOf'],'region':payload['meta']['region'],'benchmark':payload['meta']['benchmark'],'sector_count':len(payload['sectors']),'basket_count':len(payload.get('baskets',[])),'sample_ids':[r['id'] for r in payload['sectors'][:2]],'narrative_status':'missing','dna_status':'missing','serialized_now_from_archive':True}
data=['sector_central_china_data.js','chinabasketdata/baskets.json','marketdata/rotation_events_china.json','marketdata/subsector_rotation_china.json','chinasectordata/subsectors_china.json']
for name in data:
 path='site/'+name
 if path in archive_known:
  dest=SITE/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(git(path,ARCHIVE))
 else:record['missing'].append(path)
assets=set()
for page in pages:
 assets.update(re.findall(r'(?:src|href)=[\'"]([^\'"?#]+)',(SITE/page).read_text()))
assets|={'sector_dossier_cycle.js','sector_dossier_cycle.css','shared_shell_bridge.js','shared_shell.css','supabase.js','terminal_overlay.js','account.js','nav_market.js','subsector_rotation.js','subsectors_china.js','forming_narratives.js','baskets_desk.js','si_workspace_china.js','lightweight-charts.js'}
dynamic={'theme.js':['account.js','terminal_overlay.js'],'account.js':['nav_market.js']}
def local(value,parent=''):
 u=urlsplit(value)
 if u.scheme or u.netloc or not u.path:return None
 name=posixpath.normpath(u.path.lstrip('/') if u.path.startswith('/') else posixpath.join(parent,u.path))
 if name.startswith('../') or Path(name).suffix not in {'.js','.css','.woff2','.woff','.svg'}:return None
 return name
pending={n for value in assets if (n:=local(value))}
copied=set()
old=REPO/'.pytest_cache/d05-composed-20261104/site'
while pending:
 name=pending.pop()
 if name in copied:continue
 copied.add(name);dest=SITE/name
 if dest.exists():continue
 path='templates/'+name if 'templates/'+name in known else 'site/'+name
 if path not in known:
  record['missing'].append(path);continue
 expected=subprocess.check_output(['git','-C',str(REPO),'rev-parse',CODE+':'+path],text=True).strip()
 prior=old/name
 body=None
 if prior.is_file():
  prior_bytes=prior.read_bytes();git_hash=hashlib.sha1(b'blob '+str(len(prior_bytes)).encode()+b'\0'+prior_bytes).hexdigest()
  if git_hash==expected:
   body=prior_bytes;record['sources'][CODE+':'+path]=hashlib.sha256(body).hexdigest()
 if body is None:body=git(path)
 dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(body)
 pending.update(n for n in dynamic.get(name,[]) if n not in copied)
 if Path(name).suffix=='.css':
  css=body.decode();deps=re.findall(r'url\(\s*[\'"]?([^\'")\s]+)',css)+re.findall(r'@import\s+[\'"]([^\'"]+)',css)
  pending.update(n for value in deps if (n:=local(value,posixpath.dirname(name))) and n not in copied)
for page in pages:
 p=SITE/page;p.write_text(inject_shared_shell_text(p.read_text(),'',site_dir=SITE))
record['emitted']={str(p.relative_to(SITE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SITE.rglob('*') if p.is_file()}
(OUT/'fixture_provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'prepared':str(SITE),'publication':record['publication'],'assets':len(record['emitted']),'missing':record['missing']},indent=2))
