import pathlib, subprocess, sys, re, json
release=sys.argv[1] if len(sys.argv)==2 else ''
if not re.fullmatch(r'[0-9a-f]{40}', release):
    raise SystemExit('Supply verified merged commit')
from mmx_ancestry import load_proof
ancestry=load_proof(release)
payload="""import pathlib,sys,subprocess,hashlib,json,datetime
root=pathlib.Path('/opt/macro')
sys.path.insert(0,str(root))
head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
if subprocess.run(['git','-C',str(root),'merge-base','--is-ancestor','__RELEASE__',head],capture_output=True).returncode:
    if head != '__VERIFIED_INSTALLED_HEAD__':
        raise SystemExit('Merged release ancestry not verified for this installed head')
from scripts.inspect_press_staging import inspect_staging
from engine.press import desk_planner
from scripts.run_press import _paths
cfg=desk_planner.load_config(root)
staging=_paths(cfg,root)['staging']
def snapshot():
    paths=[root/'config/press.yml',*sorted(staging.glob('*.json')),*sorted((root/'content/seo/blog').glob('*.md')),root/'scripts/inspect_press_staging.py',root/'scripts/run_press.py',root/'engine/press/validators.py',root/'engine/press/desk_planner.py']
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
before=snapshot()
r=inspect_staging(root)
after=snapshot()
head_after=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
print(json.dumps({'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'release_commit':'__RELEASE__','head':head,'head_after':head_after,
 'stable_head':head==head_after,'unchanged_validation_inputs':before==after,'observed_input_sha256':after,
 'schema':r['schema'],'config_sha256':r['config_sha256'],'cutover':r['cutover'],
 'total':r['total'],'validation_current':r['validation_current'],'blocked':r['blocked'],
 'publication_approved':r['publication_approved'],'source_freshness_verified':r['source_freshness_verified'],
 'items':[{k:v for k,v in x.items() if k in {'id','path','sha256','saved_status','validation_current','blockers'}} for x in r['items']]}))
""".replace('__RELEASE__',release).replace('__VERIFIED_INSTALLED_HEAD__',ancestry['head'])
cmd=['ssh','-i',str(pathlib.Path.home()/'.ssh/macro_dashboard_deploy_v2'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10','root@146.190.142.17','/opt/macro/.venv/bin/python -B -']
p=subprocess.run(cmd,input=payload,text=True,capture_output=True,timeout=60)
if p.returncode:
    raise SystemExit(p.stderr[:1500])
data=json.loads(p.stdout)
assert data['stable_head'] and data['unchanged_validation_inputs'], 'Concurrent runtime inputs changed; result is not accepted'
assert data['cutover'] is False and data['publication_approved'] is False
out=pathlib.Path(__file__).with_name('mmx-current-runtime-inspection.json')
out.write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps(data,indent=2))
