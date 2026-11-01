from pathlib import Path
import sys,json,subprocess,time,datetime,hashlib,importlib.util,dataclasses
import pytest
root=Path.cwd();sys.path.insert(0,str(root))
from scripts import ci_scope_dependencies as d
from scripts import run_ci_pack as c
r=Path(__file__).parent;mode=sys.argv[1];head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();start=time.monotonic()
patch=(r/'tested-closure-source-repair.patch').read_bytes()
if mode=='source':
 assert head.startswith('634750adc150');assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
else:
 assert mode=='hosted' and head=='0ec629a508fe96af93d1b1bc1d5405343952b30e'
 assert subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()==['.github/ci/legacy-jobs.yml']
 original=subprocess.check_output(['git','show',head+':.github/ci/legacy-jobs.yml']).decode()
 hunk_start=original.index('  eval-os-a1:\n');pos=original.index('    paths:\n',hunk_start)+len('    paths:\n')
 paths=json.loads((r/'hosted-missing-inputs.json').read_text())['missing']
 expected=original[:pos]+''.join('      - '+x+'\n' for x in paths)+original[pos:]
 assert (root/'.github/ci/legacy-jobs.yml').read_text()==expected
inv=r/(mode+'-closure-tracked.bin');d.write_tracked_path_inventory(inv,head,root=root)
spec=importlib.util.spec_from_file_location('ci_contract_helpers',root/'tests/test_ci_pack.py');t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
with d.planner_tracked_path_inventory(inv,head,root=root):
 rc=pytest.main(['-q','tests/test_ci_pack.py::test_ancestor_init_census_does_not_grow','tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared','tests/test_ci_pack.py::test_eval_os_acceptance_runs_on_ordinary_code_prs','--junitxml='+str(r/(mode+'-closure-green.xml'))]);print(json.dumps({'mode':mode,'phase':'focused','exit':int(rc)}),flush=True)
 misses=c.curated_exclusive_closure_findings(root/'.github/ci/legacy-jobs.yml');print(json.dumps({'mode':mode,'phase':'closure','misses':misses}),flush=True)
 rows=c.packing_probe_measurements(root/'.github/ci/legacy-jobs.yml',t.PACKING_PROBES,max_packs=t.PACKING_PROBE_MAX_PACKS);breaches=c.packing_probe_breaches(rows)
 out={'schema':'eval_os.tested_closure_repair_qualification.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'mode':mode,'head':head,'source_patch_sha256':hashlib.sha256(patch).hexdigest(),'working_manifest_sha256':hashlib.sha256((root/'.github/ci/legacy-jobs.yml').read_bytes()).hexdigest(),'focused_exit':int(rc),'closure_misses':misses,'strict_probes':rows,'strict_breaches':breaches,'elapsed_seconds':round(time.monotonic()-start,2),'scope':'Local qualification only. Hosted mode is existing GitHub synthetic commit plus exact nine-path patch; no new base integration. Hosted binding checks and incumbent merge remain required.'};(r/(mode+'-closure-qualification.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='strict_probes'}),flush=True)
raise SystemExit(int(rc) or int(bool(misses) or bool(breaches)))
