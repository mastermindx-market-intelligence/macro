from pathlib import Path
import subprocess,shlex,re,json,tarfile,hashlib,ast,yaml
root=Path.cwd()
rig=root/'research/reference_integrity/intl-country-intelligence-20261020'
build=Path('/tmp/intl-country-cockpit-rig-build-20261020')
build.mkdir(parents=True,exist_ok=True)
source=build/'source'
source.mkdir(exist_ok=True)
archive=build/'source.tar'
r=subprocess.run(['git','archive','--format=tar','--output='+str(archive),'6ad0c377ed80a8ccf07ecbfb6c7b44530b753cf7','config.yml','config','collectors','engine','lib','scripts','templates','requirements.txt'],capture_output=True)
if r.returncode: raise RuntimeError('Immutable source export failed')
with tarfile.open(archive) as tf: tf.extractall(source,filter='data')
target=re.search(r'ssh -i ~/.ssh/macro_dashboard_deploy_v2 (root@\d+\.\d+\.\d+\.\d+)',(root/'app/deploy/README.md').read_text()).group(1)
selected=set()
def collect(value):
 if isinstance(value,dict):
  for child in value.values(): collect(child)
 elif isinstance(value,(list,tuple)):
  for child in value: collect(child)
 elif isinstance(value,str) and re.fullmatch(r"[A-Za-z0-9^=._+-]{1,30}",value): selected.add(value)
collect(yaml.safe_load((source/'config.yml').read_text()).get('yahoo',{}).get('tickers',{}))
for folder in ['engine','lib']:
 for file in (source/folder).glob('*.py'):
  if not (file.name.startswith('intl_') or file.name.startswith('flow_regime')): continue
  for node in ast.walk(ast.parse(file.read_text())):
   if isinstance(node,ast.Constant) and isinstance(node.value,str) and re.fullmatch(r"[A-Z0-9^=._+-]{1,30}",node.value): selected.add(node.value)
selected.update(['SPY','^GSPC','DX-Y.NYB','^VIX','EMB','IEF'])
names=set()
for ticker in selected:
 names.add(ticker+'.parquet')
 names.add(re.sub(r'[^A-Za-z0-9._-]','_',ticker)+'.parquet')
remote="selected_yahoo="+repr(sorted(names))+"\n"+r"""from pathlib import Path
from datetime import datetime,timezone
import json,tarfile,io,hashlib,subprocess,sys
root=Path('/opt/macro')
groups=['intl','intl_macro','fred','yahoo','forex','intl_risk','flow_regime','intl_regime','intl_etf']
files=[]
for group in groups:
 p=root/'data'/group
 if p.is_dir():
  files += [f for f in p.rglob('*') if f.is_file() and not f.is_symlink() and (group!='yahoo' or f.name in selected_yahoo)]
for name in ['data/china/000001.SS.parquet','data/hk/_HSI.parquet','site/macrodata/global_regime_fragment.json','site/live_config.js']:
 p=root/name
 if p.is_file() and not p.is_symlink(): files.append(p)
files=sorted(set(files))
size=sum(p.stat().st_size for p in files)
if size>80*1024*1024 or len(files)>1800: raise RuntimeError('Bounded source snapshot exceeded limit')
manifest={'schema':'intl.production_input_snapshot.v1','kind':'copy_of_existing_production_store_no_source_reacquisition','started_at':datetime.now(timezone.utc).isoformat(),'code_head':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'selected_groups':groups,'yahoo_selection':'Configured Yahoo ticker groups plus literal ticker dependencies in intl and flow-regime readers; unrelated company store excluded','files':[]}
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as tf:
 for p in files:
  before=p.stat();data=p.read_bytes();after=p.stat()
  if (before.st_size,before.st_mtime_ns)!=(after.st_size,after.st_mtime_ns): raise RuntimeError('Input changed during read')
  name=str(p.relative_to(root))
  entry=tarfile.TarInfo(name);entry.size=len(data);entry.mtime=int(after.st_mtime);entry.mode=0o600
  tf.addfile(entry,io.BytesIO(data))
  manifest['files'].append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'stored_mtime':datetime.datetime.fromtimestamp(after.st_mtime,timezone.utc).isoformat()} if False else {'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'stored_mtime':datetime.fromtimestamp(after.st_mtime,timezone.utc).isoformat()})
 manifest['finished_at']=datetime.now(timezone.utc).isoformat()
 payload=(json.dumps(manifest,indent=2)+'\n').encode()
 entry=tarfile.TarInfo('production_input_snapshot.json');entry.size=len(payload);entry.mode=0o600
 tf.addfile(entry,io.BytesIO(payload))
"""
compile(remote,'<read-only-production-input-copy>','exec')
dest=rig/'production_input_snapshot.tar.gz'
with dest.open('wb') as out:
 result=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=yes','-o','IdentitiesOnly=yes','-i','/Users/chriswong/.ssh/macro_dashboard_deploy_v2',target,'python3 -c '+shlex.quote(remote)],stdout=out,stderr=subprocess.PIPE,timeout=60)
if result.returncode:
 (rig/'production_input_snapshot_failure.txt').write_text(result.stderr.decode()[-4000:])
 raise RuntimeError('Read-only production input transfer failed; bounded diagnostic retained')
with tarfile.open(dest) as tf:
 names=tf.getnames()
 if any(not (n.startswith('data/') or n in {'site/macrodata/global_regime_fragment.json','site/live_config.js'} or n=='production_input_snapshot.json') for n in names): raise RuntimeError('Unexpected input snapshot member')
 tf.extractall(source,filter='data')
manifest=json.loads((source/'production_input_snapshot.json').read_text())
for entry in manifest['files']:
 p=source/entry['path']
 if hashlib.sha256(p.read_bytes()).hexdigest()!=entry['sha256']: raise RuntimeError('Input digest mismatch')
manifest['archive']={'path':str(dest.relative_to(root)),'bytes':dest.stat().st_size,'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()}
manifest['immutable_build_source']='6ad0c377ed80a8ccf07ecbfb6c7b44530b753cf7'
(rig/'production_input_snapshot.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'snapshot_files':len(manifest['files']),'uncompressed_bytes':sum(x['bytes'] for x in manifest['files']),'archive_bytes':dest.stat().st_size,'archive_sha256':manifest['archive']['sha256'],'source_head':manifest['code_head'],'build_root':str(source),'dataset_counts':{g:sum(x['path'].startswith('data/'+g+'/') for x in manifest['files']) for g in manifest['selected_groups']}}))