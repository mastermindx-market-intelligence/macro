"""Correct the actual current-protected snapshot/HTML join via the native builder."""
from pathlib import Path
import datetime, hashlib, json, socket, subprocess, sys
repo, out = map(Path, sys.argv[1:3]);sys.path.insert(0,str(repo))
base='12c551c2512fc57e12743fac17a2874e001cf6db'
network=[]
def deny(*args,**kwargs):network.append('transport refused');raise AssertionError('No network')
socket.socket.connect=socket.socket.connect_ex=socket.create_connection=socket.getaddrinfo=deny
from scripts import build_macro_suite_pages as b
from lib import macro_suite_view as view_owner

def digest(raw):return hashlib.sha256(raw).hexdigest()
root=out/'retained'/'business-current-macrodata';inputs={}
for rel in ['workspaces/manifest.json','workspaces/business_activity/US/latest.json']:
 path='site/macrodata/'+rel
 raw=subprocess.check_output(['git','show',base+':'+path],cwd=repo)
 dest=root/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
 inputs[path]={'git_blob':subprocess.check_output(['git','rev-parse',base+':'+path],cwd=repo,text=True).strip(),'sha256':digest(raw),'bytes':len(raw)}
page=next(p for p in b.SUITE_PAGES if p.workspace_id=='business_activity')
snapshot,artifact=b.read_workspace(root,page)
owner_bytes=json.dumps(snapshot,sort_keys=True)
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
view=view_owner.build_view(snapshot,page_built_at=stamp,artifact=artifact,layout=b._layout_for(page.workspace_id))
assert view['ok'] and view['metrics']
path,ok,entry=b.build_page(repo,page,data_root=root,out_dir=repo/'site',env=b._environment(repo),page_built_at=stamp)
assert ok and json.dumps(snapshot,sort_keys=True)==owner_bytes and entry['snapshot']==snapshot
for name,meta in inputs.items():assert digest((root/Path(name).relative_to('site/macrodata')).read_bytes())==meta['sha256']
report_path=out/'native-emission-report.json';old=json.loads(report_path.read_text())
(out/'native-emission-initial-retained.json').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
initial=old['business_activity']
result={'interface':'native read_workspace/build_view/build_page/render_page/write_page; actual analyst mountability, no shim',
 'base':base,'inputs':inputs,'input_artifact':artifact,'all_input_bytes_unchanged':True,
 'metric_count':len(view['metrics']),'view_metric_sha256':digest(json.dumps(view['metrics'],sort_keys=True).encode()),
 'definition_versions':sorted({m['definition_version'] for m in view['metrics'] if m['definition_version']}),
 'owner_metrics_and_clocks_unchanged_by_renderer':True,'page_built_at':stamp,'page_built_is_not_observation':True,
 'output':str(path.relative_to(repo)),'output_sha256':digest(path.read_bytes()),
 'actual_analyst_mountability':b._macro_command_analyst(repo),
 'input_join_invalidated_original_retained_emission':{'accepted_owner_artifact':initial['input_artifact'],'current_owner_artifact':artifact,'same_output_path_different_current_artifact':initial['input_artifact']!=artifact,'old_receipt_preserved':'native-emission-initial-retained.json','cause':'Source-base and retained accepted snapshot are different generations; current protected canonical snapshot and manifest are used together. No current data is overwritten.'},
 'network_attempts':network,'limits':'Actual current-protected finite published composite input, not independently current economic truth/raw source legs/new model or native/served proof.'}
assert not network
old['business_activity']=result
report_path.write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n')
(out/'business-current-native-emission.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
