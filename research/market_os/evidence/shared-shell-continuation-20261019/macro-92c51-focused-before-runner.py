import datetime,hashlib,json,os,pathlib,subprocess,sys
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27');E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
os.chdir(W);sys.path.insert(0,str(W))
import pytest
R=json.loads((E/'macro-8cc-92c51-actual-merge.json').read_text())
def g(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
assert g('rev-parse','HEAD')==R['head'] and g('rev-parse','MERGE_HEAD')==R['incoming']
index=g('write-tree');assert index==R['index']
paths=['.github/ci/legacy-jobs.yml','tests/test_ci_pack.py','app/deploy/Caddyfile','config/site_access.yml']
hashes={p:hashlib.sha256((W/p).read_bytes()).hexdigest() for p in paths}
args=['-q','--tb=short','--basetemp',str(E/'macro-92c51-focused-before-tmp'),
'tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared',
'tests/test_ci_pack.py::test_curated_exclusive_scopes_cover_their_own_import_closure',
'tests/test_ci_pack.py::test_curated_exclusivity_drops_only_the_opaque_fallback_tier',
'tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs']
assert not pathlib.Path(args[3]).exists()
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
inv={'schema':'mastermind.attended.focused_merge_validation.v1','started_at':start,'head':R['head'],'incoming':R['incoming'],'index':index,'interpreter':sys.executable,'pytest_args':args,'source_sha256':hashes,'observer':'pytest_exception_interact only copies existing failing-test rows; no monkeypatch/assertion/selection change','observer_script_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
(E/'macro-92c51-focused-before-invocation.json').write_text(json.dumps(inv,indent=2)+'\n')
class Observation:
 def pytest_exception_interact(self,node,call,report):
  if node.nodeid.endswith('test_exclusive_curation_narrows_ordinary_code_prs'):
   for entry in call.excinfo.traceback:
    rows=entry.frame.f_locals.get('rows')
    if isinstance(rows,list) and rows and isinstance(rows[0],dict) and {'probe','job_ids','weight'}<=set(rows[0]):
     (E/'macro-92c51-focused-before-probes.json').write_text(json.dumps(rows,indent=2)+'\n')
code=int(pytest.main(args,plugins=[Observation()]))
extra={}
probe_file=E/'macro-92c51-focused-before-probes.json'
if probe_file.exists():
 module=next(m for m in list(sys.modules.values()) if getattr(m,'__file__',None)==str(W/'tests/test_ci_pack.py'))
 incoming_manifest=E/'macro-92c51-incoming-manifest.yml'
 incoming_manifest.write_bytes(subprocess.check_output(['git','-C',str(W),'show',R['incoming']+':.github/ci/legacy-jobs.yml']))
 base_jobs={j.job_id:j for j in module.PACK.load_legacy_jobs(incoming_manifest)}
 new_jobs={j.job_id:j for j in module.PACK.load_legacy_jobs(W/'.github/ci/legacy-jobs.yml')}
 assert list(base_jobs)==list(new_jobs)
 deltas={k:{'incoming_manifest_weight':base_jobs[k].weight,'candidate_weight':new_jobs[k].weight,'delta':new_jobs[k].weight-base_jobs[k].weight} for k in new_jobs if base_jobs[k].weight!=new_jobs[k].weight}
 rows=json.loads(probe_file.read_text())
 comparisons=[]
 for row in rows:
  ids=row['job_ids']; assert sum(new_jobs[k].weight for k in ids)==row['weight']
  comparisons.append({'probe':row['probe'],'candidate_selected_job_ids':ids,'candidate_weight':row['weight'],'incoming_manifest_weight_for_these_same_ids':sum(base_jobs[k].weight for k in ids),'selected_command_weight_deltas':{k:v for k,v in deltas.items() if k in ids}})
 extra={'all_job_weight_deltas':deltas,'same_selected_ids_weight_comparison':comparisons,'scope':'incoming-manifest command weights for candidate selected IDs; not a base-tree inference run'}
 (E/'macro-92c51-focused-before-attribution.json').write_text(json.dumps(extra,indent=2)+'\n')
assert g('write-tree')==index
assert {p:hashlib.sha256((W/p).read_bytes()).hexdigest() for p in paths}==hashes
result={**inv,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pytest_exit':code,'index_unchanged':True,'source_unchanged':True,'probe_rows_captured':probe_file.exists(),'weight_deltas':extra.get('all_job_weight_deltas')}
(E/'macro-92c51-focused-before.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
raise SystemExit(code)
