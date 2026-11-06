"""P12.T40: retained snapshot, native validator/view/Jinja; no producer or network."""
from pathlib import Path
import datetime, hashlib, json, socket, subprocess, sys
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/today-business-activity-depth-20261103-a455e0785d7ea09e')
E=Path(__file__).parent
sys.path.insert(0,str(ROOT))
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
assert not git('status','--porcelain')
HEAD=git('rev-parse','HEAD').decode().strip()
network_attempts=[]
def denied(*args,**kwargs):network_attempts.append('network refused before transport');raise RuntimeError('P12.T40 offline renderer forbids network')
old_connect,old_dns=socket.create_connection,socket.getaddrinfo
socket.create_connection,socket.getaddrinfo=denied,denied
try:
 from scripts import build_macro_suite_pages as b
 from lib import macro_suite_view as v
 from lib.pages import write_unshimmed_html
 page=next(p for p in b.SUITE_PAGES if p.workspace_id=='business_activity')
 data_root=E/'retained'/'macrodata'
 paths=['site/macrodata/workspaces/manifest.json','site/macrodata/workspaces/business_activity/US/latest.json']
 hashes={}
 for path in paths:
  raw=git('show',HEAD+':'+path);dst=data_root/Path(path).relative_to('site/macrodata');dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(raw);hashes[path]=hashlib.sha256(raw).hexdigest()
 snapshot,artifact=b.read_workspace(data_root,page)
 built=datetime.datetime.now(datetime.timezone.utc).isoformat()
 view=v.build_view(snapshot,page_built_at=built,artifact=artifact,layout=b._layout_for(page.workspace_id))
 env=b._environment(ROOT)
 healthy=b.render_page(env,page,view,analyst={'mountable':False})
 write_unshimmed_html(E/'healthy.html',healthy)
 # One technical artifact-integrity failure, no changed economic numbers/units.
 bad=E/'mismatch'/'macrodata';(bad/'workspaces/business_activity/US').mkdir(parents=True,exist_ok=True)
 for path in paths:
  relative=Path(path).relative_to('site/macrodata');(bad/relative).write_bytes((data_root/relative).read_bytes())
 snap_path=bad/'workspaces/business_activity/US/latest.json';snap_path.write_bytes(snap_path.read_bytes()+b' ')
 try:b.read_workspace(bad,page)
 except b.SnapshotRefused as ex:failure={'kind':ex.kind,'detail':ex.detail}
 else:raise AssertionError('Native validator admitted mismatched artifact byte size')
 identity=b._identity(page)
 degraded=v.degraded_view(workspace_id=page.workspace_id,title=identity['title'],subtitle=identity['subtitle'],region_code='US',region_display_name='United States',page_built_at=built,artifact={'path':artifact['path'],'manifest_path':artifact['manifest_path'],'sha256':None,'bytes':None,'min_client_contract':b.MIN_CLIENT_CONTRACT},failure_kind=failure['kind'],failure_detail=failure['detail'])
 write_unshimmed_html(E/'mismatch.html',b.render_page(env,page,degraded,analyst={'mountable':False}))
 (E/'view.json').write_text(json.dumps(view,ensure_ascii=False,indent=2)+'\n')
 (E/'snapshot-summary.json').write_text(json.dumps({'head':HEAD,'kind':'controlled standalone actual native renderer/client over retained published snapshot; not current economic or inShell claim','inputs':hashes,'artifact':artifact,'headline':snapshot['headline'],'sources':snapshot['sources'],'metrics':snapshot['metrics'],'generation':snapshot['generation'],'failure':failure,'rendererBoundary':'Native read_workspace/build_view/render_page; documented throwaway write_unshimmed_html outside site, no publication shim or analyst service','networkAttempts':network_attempts},ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'head':HEAD,'valid':view['ok'],'metricCount':len(view['metrics']),'firstMetric':view['metrics'][0],'failure':failure,'networkAttempts':network_attempts},ensure_ascii=False))
finally:socket.create_connection,socket.getaddrinfo=old_connect,old_dns
