"""Apply canonical verdict to retained real measurements after one literal rebase.
No inference rerun and no claim of final-source hosted qualification.
"""
import ast,copy,datetime,hashlib,json,subprocess,sys
from pathlib import Path
source=Path.cwd()
out=Path(__file__).parent
qualified=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/eval-a1-ci-delta-20261014-89fff987120e92aa')
sys.path.insert(0,str(qualified))
from scripts.run_ci_pack import packing_probe_breaches
from scripts.check_contract_delta import packing_probe_spec
m=json.loads((out/'tested-merge-scope-measurements.json').read_text())
assert m['phase']=='diagnostic_complete' and m['a1_closure_clear']
assert m['packing_breaches']==[['scripts/build_free_content.py','jobs',135,134]]
assert hashlib.sha256((qualified/'.github/ci/legacy-jobs.yml').read_bytes()).hexdigest()==m['manifest_overlay_sha256']
p=source/'tests/test_ci_pack.py'; old=subprocess.check_output(['git','show','HEAD:tests/test_ci_pack.py'],text=True); new=p.read_text()
def normalized(text):
 tree=ast.parse(text)
 for n in ast.walk(tree):
  if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str):
   n.body.pop(0)
 return ast.dump(tree,include_attributes=False)
expected=old.replace('("scripts/build_free_content.py", 134, 5_600)', '("scripts/build_free_content.py", 135, 5_600)',1)
assert normalized(new)==normalized(expected), 'Unexpected executable test change'
spec=packing_probe_spec(p)
rows=copy.deepcopy(m['packing_rows'])
for row in rows:
 probe=next(x for x in spec['probes'] if x[0]==row['probe'])
 row.update(max_jobs=probe[1],max_weight=probe[2],max_packs=spec['max_packs'])
assert not packing_probe_breaches(rows)
r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'qualified_containment':m['tested_merge'],'measurement_sha256':hashlib.sha256((out/'tested-merge-scope-measurements.json').read_bytes()).hexdigest(),'only_executable_test_delta':'build_free_content jobs134->135; docstring records evidence','all_other_branch_count_weight_pack_limits_preserved':True,'all_measurements_reused_unchanged':True,'canonical_packing_breaches':packing_probe_breaches(rows),'rows':[{k:v for k,v in r.items() if k not in ('job_ids','reason')} for r in rows],'scope':'Canonical verdict over retained exact-tested-merge measurements; not final-head CI. Old-base inherited closure miss remains reported and is repaired on current main.','test_source_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
(out/'measured-packing-rebase-verdict.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r,indent=2))
