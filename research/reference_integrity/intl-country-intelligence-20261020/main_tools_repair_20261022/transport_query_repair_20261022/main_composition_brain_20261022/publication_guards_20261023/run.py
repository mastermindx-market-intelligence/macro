from pathlib import Path
import subprocess,json,hashlib,datetime,time,os
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018");C=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_brain_20261022");T=Path("/tmp/intl-resume-main-20261022T1252")
PY='/tmp/intl-country-cockpit-ci-20261021/bin/python'
source='f1fafde0bbf95550ed964de3a60920a2619778e4';base='a2451ccfbcfb4d32bcc4230dc8a774c4fd1d6cd3'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
assert git('rev-parse','HEAD').decode().strip()==source
out=C/'publication_guards_20261023';out.mkdir(exist_ok=False)
patch=T/'brain_composition_full_candidate_20261023.diff'
assert not patch.exists()
tracked=git('diff','--name-only',base).decode().splitlines()
new=git('ls-files','--others','--exclude-standard').decode().splitlines()
with patch.open('wb') as f:
 p=subprocess.run(['git','diff','--no-ext-diff','--no-textconv','--binary',base,'--'],cwd=R,stdout=f,stderr=subprocess.PIPE)
 assert p.returncode==0,p.stderr
 for name in new:
  p=subprocess.run(['git','diff','--no-index','--no-ext-diff','--no-textconv','--binary','--','/dev/null',name],cwd=R,stdout=f,stderr=subprocess.PIPE)
  assert p.returncode in (0,1),(name,p.stderr)
paths=out/'changed_paths.txt';paths.write_text('\n'.join(sorted(set(tracked)|set(new)))+'\n')
r={'schema':'intl.publication_guards.v1','source_commit':source,'compared_base':base,'started_at':now(),'diff_file':str(patch),'diff_sha256':sha(patch),'diff_bytes':patch.stat().st_size,'changed_paths':str(paths.relative_to(R)),'changed_paths_sha256':sha(paths),'path_count_at_guard_input':len(set(tracked)|set(new)),'receipt_closure_already_executed':'../p0b_gate_execution.json','executions':[]}
cmds=[
('reference_integrity',[PY,'scripts/check_reference_integrity.py']),
('frozen_reference_evaluation',[PY,'scripts/check_reference_integrity.py','--evaluate','intl-country-intelligence-20261020']),
('runtime_style_injection',[PY,'scripts/check_runtime_style_injection.py']),
('visual_evidence',[PY,'scripts/check_ui_visual_evidence.py','--diff-file',str(patch)]),
('design_system',[PY,'scripts/check_design_system.py','--mode','enforce-added','--diff-file',str(patch)]),
('agentos',[PY,'scripts/agentos.py','validate'])]
for name,cmd in cmds:
 log=out/(name+'.log');t=time.monotonic();started=now()
 with log.open('wb') as f:
  try:
   z=subprocess.run(cmd,cwd=R,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdout=f,stderr=subprocess.STDOUT,timeout=600)
   rc=z.returncode;error=None
  except subprocess.TimeoutExpired:
   rc=None;error='bounded 600s timeout'
 item={'name':name,'command':cmd,'started_at':started,'completed_at':now(),'duration_seconds':round(time.monotonic()-t,2),'exit_code':rc,'error':error,'log':str(log.relative_to(R)),'log_sha256':sha(log)}
 r['executions'].append(item);print(json.dumps(item),flush=True)
r['head_after']=git('rev-parse','HEAD').decode().strip();assert r['head_after']==source
r['completed_at']=now();r['pass']=all(x['exit_code']==0 for x in r['executions'])
(out/'execution.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'pass':r['pass'],'receipt':str(out/'execution.json')}),flush=True)
raise SystemExit(0 if r['pass'] else 2)
