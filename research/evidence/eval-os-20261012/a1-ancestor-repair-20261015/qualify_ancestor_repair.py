from pathlib import Path
import sys,json,subprocess,time,datetime,hashlib,importlib.util
import pytest
root=Path.cwd();sys.path.insert(0,str(root))
from scripts import ci_scope_dependencies as d
from scripts import run_ci_pack as c
p=Path(__file__).parent;head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head.startswith('2d0e6e334986')
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
start=time.monotonic();inv=p/'a1-repair-tracked.bin';d.write_tracked_path_inventory(inv,head,root=root)
spec=importlib.util.spec_from_file_location('ci_contract_helpers',root/'tests/test_ci_pack.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
with d.planner_tracked_path_inventory(inv,head,root=root):
 rc=pytest.main(['-q','tests/test_ci_pack.py::test_ancestor_init_census_does_not_grow','tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared','tests/test_ci_pack.py::test_eval_os_acceptance_runs_on_ordinary_code_prs','--junitxml='+str(p/'ancestor-green.xml')])
 print(json.dumps({'phase':'focused','exit':int(rc),'source':head}),flush=True)
 misses=c.curated_exclusive_closure_findings(root/'.github/ci/legacy-jobs.yml');print(json.dumps({'phase':'closure','misses':misses}),flush=True)
 rows=c.packing_probe_measurements(root/'.github/ci/legacy-jobs.yml',t.PACKING_PROBES,max_packs=t.PACKING_PROBE_MAX_PACKS);breaches=c.packing_probe_breaches(rows)
 census=t._aic_rows_from_tracked_inventory(c.load_legacy_jobs(root/'.github/ci/legacy-jobs.yml'),t._aic_tracked_paths())
 assert not [r for r in census if r[0]=='eval-os-a1']
 assert head==subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 out={'schema':'eval_os.a1_ancestor_repair_qualification.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':head,'focused_exit':int(rc),'closure_misses':misses,'strict_probe_rows':rows,'strict_probe_breaches':breaches,'ancestor_total_rows':len(census),'a1_ancestor_rows':0,'manifest_sha256':hashlib.sha256((root/'.github/ci/legacy-jobs.yml').read_bytes()).hexdigest(),'elapsed_seconds':round(time.monotonic()-start,2),'claim_limit':'Local current-source qualification only. Hosted binding CI, incumbent merge, production and adoption remain unproved.'};(p/'ancestor-qualification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='strict_probe_rows'}),flush=True)
raise SystemExit(int(rc) or int(bool(misses) or bool(breaches)))
