"""Same frozen economic view; source-scoped native rendering qualification."""
from pathlib import Path
import hashlib,json,subprocess,sys,socket
from jinja2 import BaseLoader,ChoiceLoader
ROOT=Path('/Volumes/Mastermind 2/agent-workspaces/claude/14851c4656838a3b/today-business-activity-depth-20261103-a455e0785d7ea09e');E=Path(__file__).parent
sys.path.insert(0,str(ROOT))
network=[]
def deny(*a,**k):network.append('blocked before transport');raise AssertionError('offline render')
socket.create_connection=socket.getaddrinfo=deny
from scripts import build_macro_suite_pages as b
from lib import macro_suite_view as v
BASE=json.loads((E/'snapshot-summary.json').read_text())['head']
class BaselineShell(BaseLoader):
 def get_source(self,environment,template):
  if template!='_macro_suite_shell.html.j2':
   from jinja2 import TemplateNotFound
   raise TemplateNotFound(template)
  text=subprocess.check_output(['git','show',BASE+':templates/'+template],cwd=ROOT,text=True)
  return text,'baseline:'+template,lambda:True
view=json.loads((E/'view.json').read_text());before=(E/'view.json').read_bytes();summary=json.loads((E/'snapshot-summary.json').read_text());page=next(p for p in b.SUITE_PAGES if p.workspace_id=='business_activity');env=b._environment(ROOT)
(E/'candidate-healthy.html').write_text(b.render_page(env,page,view,analyst={'mountable':False}))
identity=b._identity(page)
degraded=v.degraded_view(workspace_id=page.workspace_id,title=identity['title'],subtitle=identity['subtitle'],region_code='US',region_display_name='United States',page_built_at=view['page_built_at'],artifact={'path':summary['artifact']['path'],'manifest_path':summary['artifact']['manifest_path'],'sha256':None,'bytes':None,'min_client_contract':b.MIN_CLIENT_CONTRACT},failure_kind=summary['failure']['kind'],failure_detail=summary['failure']['detail'])
(E/'candidate-mismatch.html').write_text(b.render_page(env,page,degraded,analyst={'mountable':False}))
oldenv=b._environment(ROOT);oldenv.loader=ChoiceLoader([BaselineShell(),oldenv.loader]);parity=[]
for other in b.SUITE_PAGES:
 if other.workspace_id=='business_activity':continue
 snap,artifact=b.read_workspace(ROOT/'tests/fixtures/macro_suite_t11',other)
 ov=v.build_view(snap,page_built_at=view['page_built_at'],artifact=artifact,layout=b._layout_for(other.workspace_id))
 a=b.render_page(oldenv,other,ov,analyst={'mountable':False});z=b.render_page(env,other,ov,analyst={'mountable':False});assert a==z,other.workspace_id
 parity.append({'workspace':other.workspace_id,'identicalBytes':len(a.encode()),'sha256':hashlib.sha256(a.encode()).hexdigest()})
assert before==(E/'view.json').read_bytes();assert not network
files=['templates/_macro_suite_shell.html.j2','templates/macro_business_activity.html.j2','tests/test_macro_business_activity_depth.py']
result={'baseline':BASE,'frozenViewSha256':hashlib.sha256(before).hexdigest(),'pageBuiltAt':view['page_built_at'],'inputs':summary['inputs'],'candidateSource':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in files},'unchangedOtherWorkspaces':parity,'networkAttempts':network,'semanticViewUnchanged':True}
(E/'source-qualification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
