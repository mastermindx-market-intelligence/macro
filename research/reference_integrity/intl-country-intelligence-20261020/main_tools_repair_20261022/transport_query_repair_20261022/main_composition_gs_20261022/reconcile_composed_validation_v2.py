from pathlib import Path
import json,hashlib,subprocess,datetime,os,time
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018");Q=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022");G=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_gs_20261022")
sha=lambda b:hashlib.sha256(b).hexdigest()
now=lambda:datetime.datetime.now(datetime.timezone.utc).isoformat()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
assert head=='d7f3becfea06fbce54c3e04de5f974e257b96023'
parents=subprocess.check_output(['git','show','-s','--format=%P',head],cwd=R,text=True).strip().split()
assert parents==['96cf630b9dffec366568216e8d5ef1125e212cbf','2d33475adef502ab6b00b8003356c1b0ad1673c0']
initial=json.loads((G/'regressions_candidate/receipt.json').read_text())
corrected=json.loads((G/'gs_foundation_final_v2_receipt.json').read_text())
delta=json.loads((G/'guard_fixture_ci_delta.json').read_text())
assert initial['source_bindings_unchanged'] and not initial['pass']
assert [c['name'] for c in initial['checks'] if c['exit_code']!=0]==['gs_build_and_screener']
for c in initial['checks']:assert sha((R/c['log']).read_bytes())==c['log_sha256']
combined=(G/'regressions_candidate/gs_build_and_screener.log').read_text()
assert '1 failed, 162 passed' in combined and 'FAILED tests/test_intl_gs_foundation.py::test_frozen_files_unchanged_vs_origin_main[templates/theme.css]' in combined
assert corrected['exit_code']==0 and sha((G/'gs_foundation_final_v2.log').read_bytes())==corrected['log_sha256']
assert '112 passed' in (G/'gs_foundation_final_v2.log').read_text()
assert corrected['historical_git_objects_required_by_fixture'] is False
bindings=[];committed=[]
for row in initial['files']:
    actual=sha((R/row['path']).read_bytes())
    gitsha=sha(subprocess.check_output(['git','show',head+':'+row['path']],cwd=R))
    assert gitsha==row['sha256'],(row['path'],'committed merge differed')
    change=row['path'] in ('tests/test_intl_gs_foundation.py','.github/ci/legacy-jobs.yml')
    if row['path']=='tests/test_intl_gs_foundation.py':assert actual==corrected['test_sha256']==delta['test_sha256']
    elif row['path']=='.github/ci/legacy-jobs.yml':assert actual==corrected['manifest_sha256']==delta['after_manifest_sha256']
    else:assert actual==row['sha256'],row['path']
    bindings.append({'path':row['path'],'sha256':actual,'previous_tested_sha256':row['sha256'],'test_or_ci_only_reconciliation':change})
    committed.append({'path':row['path'],'committed_sha256':gitsha,'full_suite_sha256':row['sha256'],'identical':True})
assert (R/'templates/theme.css').read_bytes()==(R/'site/theme.css').read_bytes()
assert sha((R/'templates/theme.css').read_bytes())==corrected['theme_sha256']=='d7be48a71598c3c806deb271f346c996dc5136e1030f17546407092b6938e419'
command=next(c['command'] for c in initial['checks'] if c['name']=='ci_manifest')
env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1';tick=time.monotonic()
with (G/'ci_manifest_final_v2.log').open('w') as log:
    result=subprocess.run(command,cwd=R,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert result.returncode==0,(G/'ci_manifest_final_v2.log').read_text()
ci={'command':command,'exit_code':result.returncode,'duration_seconds':round(time.monotonic()-tick,2),'log_sha256':sha((G/'ci_manifest_final_v2.log').read_bytes()),'manifest_sha256':delta['after_manifest_sha256']}
(G/'MERGE_SOURCE_BINDING.json').write_text(json.dumps({'recorded_at':now(),'source_commit':head,'ordered_parents':parents,'commit_metadata':subprocess.check_output(['git','show','-s','--format=fuller',head],cwd=R,text=True),'bindings':committed,'all_match_full_regressions':True,'merge_ref_absent':subprocess.run(['git','rev-parse','--verify','MERGE_HEAD'],cwd=R,capture_output=True).returncode!=0},indent=2)+'\n')
record={'schema':'intl.composed_validation_reconciliation.v2','recorded_at':now(),'underlying_head':head,'merge_ordered_parents':parents,'working_tree_candidate':True,'supersedes':'COMPOSITION_VALIDATION.json (historical ancestry fixture assumption; original retained)','initial_regressions_receipt_sha256':sha((G/'regressions_candidate/receipt.json').read_bytes()),'initial_overall_result':'FAIL_RETAINED','initial_only_failure':'GS frozen-theme assertion rejected the preexisting accepted country-theme delta of a comment and four declarations','corrective_receipt_sha256':sha((G/'gs_foundation_final_v2_receipt.json').read_bytes()),'corrective_change':'Exact directional whole-byte hash-pair compatibility; canonical merge base and other frozen paths unchanged. Twelve positive/negative cases use a retained artifact, verify both full-byte identities, and require no older Git objects. Browser CI declares the exact fixture path.','production_sources_unchanged_after_full_suite':True,'final_source_bindings':bindings,'ci_manifest_verification':ci,'counts':{'international_browser':242,'bridge_and_adapters':192,'workspace_state':21,'shared_shell_injection':34,'access_boundary':32,'primary_build':12,'screener':51,'gs_foundation_with_exact_freeze_guard':112},'required_scope_checks_pass':True,'normal_build_and_actual_parent_proof':False,'production_acceptance':False}
(G/'COMPOSITION_VALIDATION_V2.json').write_text(json.dumps(record,indent=2)+'\n')
(G/'fix_gs_fixture_ci_dependency_v2.py').write_bytes(Path("/tmp/intl-resume-main-20261022T1252/fix_gs_fixture_ci_dependency_v2.py").read_bytes())
subprocess.run(['git','diff','--check','--','tests/test_intl_gs_foundation.py','.github/ci/legacy-jobs.yml'],cwd=R,check=True)
print(json.dumps({'head':head,'parents':parents,'committed_bindings':len(committed),'final_working_bindings':len(bindings),'ci_manifest':ci,'validation_sha256':sha((G/'COMPOSITION_VALIDATION_V2.json').read_bytes())}),flush=True)
