from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
root=Path.cwd();out=Path(__file__).parent;sys.path.insert(0,str(root))
from scripts import run_ci_pack as c
from scripts import ci_scope_dependencies as d
from scripts.check_contract_delta import packing_probe_spec
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head=='7e3157596cdb009445ebe7db6ff3eef6a5b81d96'
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
manifest=root/'.github/ci/legacy-jobs.yml';inventory=out/'integrated-tracked.bin';d.write_tracked_path_inventory(inventory,head,root=root)
spec=packing_probe_spec(root/'tests/test_ci_pack.py');r={'head':head,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'inventory_sha256':hashlib.sha256(inventory.read_bytes()).hexdigest(),'spec':spec,'phase':'closure','hosted_ci':False};start=time.monotonic()
def save(): (out/'integrated-qualification.json').write_text(json.dumps(r,indent=2)+'\n')
save();print('Bound7e315759: canonical complete tracked closure starting',flush=True)
with d.planner_tracked_path_inventory(inventory,head,root=root):
 r['closure_misses']=c.curated_exclusive_closure_findings(manifest);r['phase']='packing';save();print(json.dumps({'closure_misses':r['closure_misses']}),flush=True)
 r['packing_rows']=c.packing_probe_measurements(manifest,[tuple(row) for row in spec['probes']],max_packs=spec['max_packs']);r['packing_breaches']=c.packing_probe_breaches(r['packing_rows'])
r['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();r['elapsed_seconds']=round(time.monotonic()-start,2);r['head_unchanged']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head;r['strict_green']=not r['closure_misses'] and not r['packing_breaches'] and r['head_unchanged'];r['phase']='complete';save();print(json.dumps({k:v for k,v in r.items() if k!='packing_rows'},indent=2),flush=True);print(json.dumps([{k:v for k,v in row.items() if k not in {'selected_jobs','selected_job_ids'}} for row in r['packing_rows']],indent=2),flush=True);raise SystemExit(0 if r['strict_green'] else 1)
