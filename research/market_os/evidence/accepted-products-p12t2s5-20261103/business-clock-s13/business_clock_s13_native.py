"""Retained raw-artifact/native renderer composition; no financial producer."""
import sys,json,hashlib,subprocess,types,copy,os
from pathlib import Path
from jinja2 import ChoiceLoader,DictLoader
root=Path.cwd(); sys.path.insert(0,str(root))
from scripts import build_macro_suite_pages as B
from lib import macro_suite_view as V
from engine.market_os.macro_workspaces import contract
out=Path('/Volumes/Mastermind/evidence/accepted-products-p12t2s5-20261103/business-clock-s13-native');out.mkdir(exist_ok=True)
base='c7e6a8a7e9a6d3716e72f08555395c8f8e59e330'
old=types.ModuleType('lib._business_clock_previous');old.__file__=str(root/'lib/macro_suite_view.py');old.__package__='lib';sys.modules[old.__name__]=old
exec(compile(subprocess.check_output(['git','show',base+':lib/macro_suite_view.py']),old.__file__,'exec'),old.__dict__)
env=B._environment(root);oldenv=env.overlay(loader=ChoiceLoader([DictLoader({'_macro_suite_shell.html.j2':subprocess.check_output(['git','show',base+':templates/_macro_suite_shell.html.j2'],text=True)}),env.loader]))
stamp='2026-11-03T21:52:38Z';data=root/'site/macrodata';page=next(p for p in B.SUITE_PAGES if p.workspace_id=='business_activity')
rawpaths=[data/'workspaces/manifest.json',data/'workspaces/business_activity/US/latest.json']
hashes=lambda:{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in rawpaths}
before=hashes();snapshot,artifact=B.read_workspace(data,page);contract.validate(snapshot);raw=copy.deepcopy(snapshot)
prior=old.build_view(snapshot,page_built_at=stamp,artifact=artifact,layout=B._layout_for(page.workspace_id));now=V.build_view(snapshot,page_built_at=stamp,artifact=artifact,layout=B._layout_for(page.workspace_id))
assert prior['context']['calculation_as_of']=='2026-11-30', prior['context']
assert prior['context']['state_tone']!='neutral', prior['context']
assert now['context']['calculation_as_of'] is None and now['context']['state_tone']=='neutral'
for priorrow,newrow,rawrow in zip(prior['metrics'],now['metrics'],raw['metrics']['items']):
 assert priorrow['value']==newrow['value'] and priorrow['reference_period']==newrow['reference_period']==rawrow['reference_period']
 assert {k:v for k,v in priorrow.items() if k not in ['clocks','freshness','freshness_tone']}=={k:v for k,v in newrow.items() if k not in ['clocks','freshness','freshness_tone']}
assert len(now['metrics'])==31 and snapshot==raw
for r in now['evidence']['sources']:
 assert next(c['value'] for c in r['clocks'] if c['key']=='observed_at') is None
assert now['evidence']['artifact']==artifact and now['evidence']['generation']['content_sha256']==artifact['sha256']
others=[];unavailable=[]
for p in B.SUITE_PAGES:
 if p.workspace_id=='business_activity':continue
 try:s,a=B.read_workspace(data,p)
 except B.SnapshotRefused as e:unavailable.append({'id':p.workspace_id,'reason':e.kind});continue
 av=old.build_view(s,page_built_at=stamp,artifact=a,layout=B._layout_for(p.workspace_id));bv=V.build_view(s,page_built_at=stamp,artifact=a,layout=B._layout_for(p.workspace_id))
 assert av==bv,p.workspace_id
 ah=B.render_page(oldenv,p,av);bh=B.render_page(env,p,bv);assert ah==bh,p.workspace_id
 others.append({'id':p.workspace_id,'view_equal':True,'html_sha256':hashlib.sha256(bh.encode()).hexdigest()})
assert others
# Native normal single-page entry; writes restricted to external evidence output.
writes=[];blocked=[]
def pathof(x):return Path(os.fsdecode(x)).absolute() if isinstance(x,(str,bytes,os.PathLike)) else None
def guard(event,args):
 if event=='open':
  p=pathof(args[0]);mode=args[1];flags=args[2];writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC)))
  if writing and p is not None:
   if not p.is_relative_to(out):blocked.append([event,str(p)]);raise PermissionError('S13 external output-only fence')
   writes.append([event,str(p)])
 elif event in ['os.rename','os.remove','os.chmod','os.mkdir']:
  p=pathof(args[0]);ok=p is not None and (p.is_relative_to(out) or (event=='os.mkdir' and p==out and p.exists()))
  if event=='os.rename':ok=ok and pathof(args[1]).is_relative_to(out)
  if not ok:blocked.append([event,str(p)]);raise PermissionError('S13 external output-only fence')
  writes.append([event,str(p)])
sys.addaudithook(guard)
result=B.build_page(root,page,data_root=data,out_dir=out,env=env,page_built_at=stamp);assert result[1]
html=result[0].read_text();assert 'Source present; freshness unverified' in html and '来源已提供；时效性未核实' in html
assert 'Latest reference period' in html and 'Not supplied' in html
assert hashes()==before and snapshot==raw and not blocked
report={'scope':'existing verified raw owner+normal single-page native renderer; no full producer or current/PIT/served claim','raw_input_sha256':before,'raw_artifact':artifact,'raw_immutable':True,'closed_raw_digest_valid':True,'raw31_values_periods_and_all_nonclock_metric_metadata_equal':True,'old_context':prior['context'],'new_context':now['context'],'other_family_exact_view_and_html':others,'unavailable_other_inputs':unavailable,'controlled_page_built_at':stamp,'html_sha256':hashlib.sha256(result[0].read_bytes()).hexdigest(),'writes':writes,'blocked':blocked,'network':'OS deny network*','limits':'No fresh visual/browser/touch/currentness/availability/release/PIT authenticity claim.'}
print(json.dumps(report,ensure_ascii=False,indent=2))
