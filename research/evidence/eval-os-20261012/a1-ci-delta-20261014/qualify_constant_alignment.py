import ast,copy,datetime,hashlib,json,subprocess,sys
from pathlib import Path
out=Path(__file__).parent;source=Path.cwd();qualified=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/eval-a1-ci-delta-20261014-89fff987120e92aa');sys.path.insert(0,str(qualified))
from scripts.run_ci_pack import packing_probe_breaches
from scripts.check_contract_delta import packing_probe_spec
p=source/'tests/test_ci_pack.py';old=subprocess.check_output(['git','show','HEAD:tests/test_ci_pack.py'],text=True);new=p.read_text()
main='190311584167a164d9a78a390071b19fcb4b5382';incoming=subprocess.check_output(['git','show',main+':tests/test_ci_pack.py'],text=True);incoming_file=out/'constant-conflict/main.py';assert incoming_file.read_text()==incoming
main_spec=packing_probe_spec(incoming_file);spec=packing_probe_spec(p);expected=copy.deepcopy(main_spec);expected['probes']=[[x[0],135 if x[0]=='scripts/build_free_content.py' else x[1],x[2]] for x in expected['probes']];assert spec==expected
expected_source=old.replace('("templates/index.html", 135, 5_803)','("templates/index.html", 136, 5_803)',1).replace('("engine/prophet/plan_book.py", 129, 5_600)','("engine/prophet/plan_book.py", 130, 5_600)',1)
def normalized(text):
 tree=ast.parse(text)
 for n in ast.walk(tree):
  if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str):n.body.pop(0)
 return ast.dump(tree,include_attributes=False)
assert normalized(new)==normalized(expected_source)
m=json.loads((out/'tested-merge-scope-measurements.json').read_text());rows=copy.deepcopy(m['packing_rows'])
for r in rows:
 probe=next(x for x in spec['probes'] if x[0]==r['probe']);r.update(max_jobs=probe[1],max_weight=probe[2],max_packs=spec['max_packs'])
assert not packing_probe_breaches(rows)
r={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'parent':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'protected_main':main,'main_test_blob':subprocess.check_output(['git','rev-parse',main+':tests/test_ci_pack.py'],text=True).strip(),'source_test_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'main_spec':main_spec,'source_spec':spec,'only_new_baseline_decision':'free-content134->135; index136 and plan130 exactly retain existing main decisions','executable_test_delta_only_two_existing_main_literals':True,'prior_measurements_reused_unchanged':True,'canonical_packing_breaches':packing_probe_breaches(rows),'no_main_merge_or_remote_effect':True}
(out/'constant-alignment-proof.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
