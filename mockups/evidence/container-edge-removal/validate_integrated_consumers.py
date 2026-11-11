from pathlib import Path
import subprocess,json,time,sys
R=Path.cwd();E=R/'mockups/evidence/container-edge-removal';I=E/'integration';py=sys.executable
checks=[
 ('focused', [py,'-m','pytest','-q','tests/test_container_edge_stripes.py','tests/test_ew_p4_descriptive_ui.py::test_receipt_shots_depict_the_source_under_test','tests/test_ew_p4_descriptive_ui.py::test_review_r1_site_copy_is_byte_identical_to_template','tests/test_stock_dashboard_first_frame.py::test_rendered_fixture_recipe_is_committed_self_binding_and_deterministic','tests/test_stock_dashboard_first_frame.py::test_committed_browser_receipts_are_self_binding_fixture_proof','tests/test_stock_dashboard_first_frame.py::test_visual_manifest_preserves_history_and_appends_bounded_repair']),
 ('covered-call', ['node','--test','tests/js/covered_call_annualized_copy.test.mjs']),
 ('template-sync',[py,'scripts/check_template_site_sync.py']),
 ('asset-refs',[py,'scripts/check_site_asset_refs.py'])]
results=[]
for name,cmd in checks:
 p=E/'logs'/('main-integration-'+name+'.log');start=time.monotonic()
 with p.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 row={'name':name,'command':cmd,'exit_code':r.returncode,'seconds':round(time.monotonic()-start,2),'log':str(p.relative_to(R))}
 results.append(row);print(json.dumps(row),flush=True)
diff=R/'.cache/delivery-checkpoint/main-integration-ui.diff'
with diff.open('wb') as f:subprocess.run(['git','diff','--no-renames','--unified=0','c58c69bf42786f29c8857550bdb244d08da35240','--','templates','site','app','scripts/build_vector.py'],stdout=f,check=True)
cmd=[py,'scripts/check_ui_visual_evidence.py','--diff-file',str(diff)]
p=E/'logs/main-integration-ui-evidence.log';start=time.monotonic()
with p.open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=300)
row={'name':'ui-evidence','command':cmd,'exit_code':r.returncode,'seconds':round(time.monotonic()-start,2),'diff_bytes':diff.stat().st_size,'log':str(p.relative_to(R))}
results.append(row);print(json.dumps(row),flush=True)
(I/'validation-receipt.json').write_text(json.dumps({'schema':'mastermind.container_edge_integration_validation.v1','main':'c58c69bf42786f29c8857550bdb244d08da35240','working_tree_nearest_head':'97abae6fa8f17bdb71f8670d59d1ba43497e3ae7','checks':results},indent=2)+'\n')
raise SystemExit(0 if all(r['exit_code']==0 for r in results) else 1)
