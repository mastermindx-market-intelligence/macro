from pathlib import Path
import hashlib,json,shutil,subprocess,sys
from jinja2 import Environment,BaseLoader,TemplateNotFound
REPO=Path('/Volumes/Mastermind/agent-workspaces/macro/web/d05-native-source-verification-20261104')
ROOT=REPO/'.pytest_cache/d05-ci-recovery-82c377/china-archive'
OVERLAY=ROOT.parent/'china_candidate_v3_overlay.json'
SITE=ROOT/'site-candidate-v3'
SOURCE=ROOT/'candidate_source_v3'
CODE='82c377fb79ec746a0705c3c62a0be0a760cb001a'
assert not SITE.exists() and not SOURCE.exists(),'Preserve prior candidate evidence'
files=json.loads(OVERLAY.read_text())
shutil.copytree(ROOT/'site',SITE)
shutil.copytree(ROOT/'candidate_source',SOURCE)
for rel,content in files.items():
 p=SOURCE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content)
 if rel.endswith(('.js','.css')):(SITE/Path(rel).name).write_text(content)
def git(path):
 return subprocess.check_output(['git','-C',str(REPO),'show',CODE+':'+path])
for rel in ['engine/i18n.py','engine/sector_generation_guard.py','scripts/_cycles_payload.py','lib/shared_shell.py']:
 assert (REPO/rel).read_bytes()==git(rel),'Unqualified render helper: '+rel
sys.path.insert(0,str(REPO))
from engine import i18n
from lib.shared_shell import inject_shared_shell_text
class Loader(BaseLoader):
 def get_source(self,env,name):
  path='templates/'+name
  return files[path] if path in files else git(path).decode(),path,lambda:True
env=Environment(loader=Loader(),autoescape=False)
env.globals.update(td=i18n.td,tr=i18n.tr,t=i18n.t)
html=env.get_template('sector_central_china.html.j2').render()
html=html.replace('<body','<body data-d05-fixture="archived-china"',1)
html=html.replace('</body>','<div style="position:fixed;bottom:0;left:0;z-index:100000;background:var(--panel);color:var(--text);padding:3px 8px;font:11px sans-serif">D05 ARCHIVED CHINA · 2026-11-03 · not live</div></body>')
(SITE/'sector_central_china.html').write_text(inject_shared_shell_text(html,'',site_dir=SITE))
record=json.loads((ROOT/'fixture_provenance.json').read_text())
record['candidate_parent']='5344e0e19b4032c831e8cff0cd6f67d9f473d50a'
record['candidate_sources']={path:hashlib.sha256(content.encode()).hexdigest() for path,content in files.items()}
record['emitted']={str(p.relative_to(SITE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in SITE.rglob('*') if p.is_file()}
(ROOT/'fixture_candidate_v3_provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'site':str(SITE),'source':str(SOURCE),'candidate_sources':record['candidate_sources'],'assets':len(record['emitted'])}))
