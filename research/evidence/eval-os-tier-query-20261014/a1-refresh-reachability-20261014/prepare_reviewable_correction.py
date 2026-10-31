import ast,copy,datetime,difflib,hashlib,json,re,subprocess
from pathlib import Path
import yaml
R=Path('/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/eval-os-a1-preflight-20260922-f75c61cdabe6f12c');E=Path(__file__).parent
preview=json.loads((E/'source-preview.json').read_text());assert preview['rc']==0;tree=preview['tree']
def blob(p):return subprocess.check_output(['git','show',tree+':'+p],cwd=R,text=True)
manifest='.github/ci/legacy-jobs.yml';test='tests/test_ci_pack.py';old={p:blob(p) for p in [manifest,test]};new=dict(old)
inputs=['engine/rates_command_basis.py','engine/neuralweb/market_memory_brain_citations.py','engine/neuralweb/market_memory_retained_catalog.py','engine/neuralweb/market_memory_retained_legacy_guard.py','engine/neuralweb/market_memory_retained_saved.py']
a=yaml.safe_load(old[manifest]);job=a['jobs']['eval-os-a1'];missing=[x for x in inputs if x not in job['paths']]
m=re.search(r'(?m)^  eval-os-a1:\n',new[manifest]);assert m
start=new[manifest].index('    paths:\n',m.start())+len('    paths:\n');new[manifest]=new[manifest][:start]+''.join('      - '+x+'\n' for x in missing)+new[manifest][start:]
b=yaml.safe_load(new[manifest]);expected=copy.deepcopy(a);expected['jobs']['eval-os-a1']['paths']=missing+expected['jobs']['eval-os-a1']['paths'];assert b==expected
needle='("scripts/build_free_content.py", 134, 5_600)';assert new[test].count(needle)==1;new[test]=new[test].replace(needle,'("scripts/build_free_content.py", 135, 5_600)')
local=(R/test).read_text();docstart=local.index('    2026-10-14 (PR #6651, Eval OS A1):');docend=local.index('    Baselines on the pre-curation manifest',docstart);doc=local[docstart:docend].replace('Preserve\n    those exact values to resolve the adjacent-literal merge conflict; this','Preserve\n    those exact protected-main values in the final integration; this')
anchor='    Baselines on the pre-curation manifest';assert new[test].count(anchor)==1;new[test]=new[test].replace(anchor,doc+anchor)
def probes(txt):
 for n in ast.parse(txt).body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PACKING_PROBES' for t in n.targets):return ast.literal_eval(n.value)
p0=probes(old[test]);p1=probes(new[test]);assert p1==tuple((p,135 if p=='scripts/build_free_content.py' else n,w) for p,n,w in p0)
patch=''.join(''.join(difflib.unified_diff(old[p].splitlines(True),new[p].splitlines(True),fromfile='a/'+p,tofile='b/'+p)) for p in old)
(E/'reviewable-post-update-correction.patch').write_text(patch)
report={'recorded_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'basis':preview,'missing_a1_inputs_added':missing,'job_count':len(a['jobs']),'all_job_execution_definitions_and_existing_paths_preserved':b==expected,'packing_before':p0,'packing_after':p1,'weight_and_pack_limits_unchanged':True,'files':list(old),'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'status':'PREVIEW_ONLY_NOT_APPLIED','authority':'No manual base integration or source push authorized by this receipt; incumbent-only order remains binding pending Chairman decision','test_scope':'Structural proposal qualification only; accepted prior measured packing and full closure evidence retained, final merged-source checks still required'}
(E/'reviewable-correction.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='basis'},indent=2))
