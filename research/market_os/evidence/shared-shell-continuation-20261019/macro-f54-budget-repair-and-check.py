import ast,datetime,difflib,hashlib,json,pathlib,subprocess,time
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27');E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
def g(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
r=json.loads((E/'macro-f54-focused-before.json').read_text())
assert r['pytest_exit']==1 and r['index_unchanged'] and r['source_unchanged']
assert g('rev-parse','HEAD')==r['head'] and g('rev-parse','MERGE_HEAD')==r['incoming'] and g('write-tree')==r['index']
p=W/'tests/test_ci_pack.py';before=p.read_text()
assert hashlib.sha256(before.encode()).hexdigest()==r['source_sha256']['tests/test_ci_pack.py']
old='("scripts/build_free_content.py", 134, 5_661)';new='("scripts/build_free_content.py", 134, 5_665)'
assert before.count(old)==1
anchor='    Baselines on the pre-curation manifest (PR #5585 planner, 188 jobs):'
assert before.count(anchor)==1
note="""    Shared Shell after joining f54eeb09 (2026-10-20, PR7949) measures
    134 jobs / 5,665 weight / 10 packs for build_free_content. The same
    selected job IDs total 5,658 under the incoming manifest's commands;
    only data-base-shim (7 -> 12) and unrun-nav-chrome (30 -> 32) differ.
    This is command-weight attribution on the candidate selection, not a
    separate inference run on the incoming tree. Its joint W23 ceiling
    already carries three units of room, so fund only the actual four-unit
    breach: 5,661 -> 5,665. Keep both historical seven-unit changes and the
    joint twelve-unit note above. The other probes measure index.html
    135 / 5,790 / 10 and plan_book 128 / 5,539 / 10, below unchanged bounds.
    Closure, declared-set and opaque-tier checks pass. No command, suite,
    selector, job-count bound, other weight ceiling or pack limit changes.

"""
after=before.replace(old,new).replace(anchor,note+anchor)
def strip_docs(s):
 tree=ast.parse(s)
 for n in ast.walk(tree):
  if isinstance(n,(ast.Module,ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str):n.body=n.body[1:]
 return ast.dump(tree)
assert strip_docs(after.replace(new,old))==strip_docs(before)
for path,h in r['source_sha256'].items():assert hashlib.sha256((W/path).read_bytes()).hexdigest()==h
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='tests/test_ci_pack.py.before',tofile='tests/test_ci_pack.py.after'))
(E/'macro-f54-budget-repair.patch').write_text(patch)
p.write_text(after);g('add','--','tests/test_ci_pack.py')
index=g('write-tree')
record={'schema':'mastermind.attended.measured_budget_composition.v1','observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':r['head'],'incoming':r['incoming'],'index_before':r['index'],'index_after':index,'changed_path':'tests/test_ci_pack.py','before_sha256':hashlib.sha256(before.encode()).hexdigest(),'after_sha256':hashlib.sha256(after.encode()).hexdigest(),'patch_sha256':hashlib.sha256(patch.encode()).hexdigest(),'only_executable_change':'build_free_content weight ceiling 5661 -> 5665','historical_notes_preserved':True,'probe_jobs_weight_packs':[[135,5790,10],[134,5665,10],[128,5539,10]],'incoming_command_weight_for_candidate_free_ids':5658,'job_weight_deltas':r['weight_deltas'],'not_a_base_tree_inference_run':True}
(E/'macro-f54-budget-repair.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2),flush=True)
cmd=['/opt/homebrew/bin/python3.12','-m','pytest','-q','--tb=short','--basetemp',str(E/'macro-f54-packing-after-tmp'),'tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs']
assert not pathlib.Path(cmd[7]).exists()
started=datetime.datetime.now(datetime.timezone.utc).isoformat(); t=time.monotonic()
inv={'started_at':started,'args':cmd,'head':r['head'],'incoming':r['incoming'],'index':index,'test_sha256':record['after_sha256'],'manifest_sha256':r['source_sha256']['.github/ci/legacy-jobs.yml']}
(E/'macro-f54-packing-after-invocation.json').write_text(json.dumps(inv,indent=2)+'\n')
with (E/'macro-f54-packing-after.log').open('wb') as out: result=subprocess.run(cmd,cwd=W,stdout=out,stderr=subprocess.STDOUT)
assert g('write-tree')==index
assert hashlib.sha256(p.read_bytes()).hexdigest()==record['after_sha256']
for path,h in r['source_sha256'].items():
 if path!='tests/test_ci_pack.py':assert hashlib.sha256((W/path).read_bytes()).hexdigest()==h
raw=(E/'macro-f54-packing-after.log').read_bytes()
receipt={**inv,'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'seconds':round(time.monotonic()-t,3),'exit':result.returncode,'index_unchanged':True,'source_unchanged':True,'log_bytes':len(raw),'log_sha256':hashlib.sha256(raw).hexdigest()}
(E/'macro-f54-packing-after.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2));print(raw.decode())
raise SystemExit(result.returncode)
