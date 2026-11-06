import ast,datetime,hashlib,json,pathlib,re,subprocess,sys
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27');E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
def g(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
R=json.loads((E/'macro-0f05-focused-before.json').read_text())
assert R['pytest_exit']==1 and R['index_unchanged'] and R['source_unchanged']
assert re.search(r'1 failed, 3 passed',(E/'macro-0f05-focused-before.log').read_text())
assert g('rev-parse','HEAD')==R['head'] and g('rev-parse','MERGE_HEAD')==R['incoming'] and g('write-tree')==R['index']
assert not g('diff','--name-only') and not g('ls-files','-u')
rows=json.loads((E/'macro-0f05-focused-before-probes.json').read_text())
old_rows=json.loads((E/'macro-f54-focused-before-probes.json').read_text())
assert [x['probe'] for x in rows]==[x['probe'] for x in old_rows]
for row,old in zip(rows,old_rows):
 assert row['job_ids']==old['job_ids'] and row['jobs']==old['jobs'] and row['packs']==10 and row['weight']==old['weight']+3
 assert row['jobs']<=row['max_jobs']
target=next(x for x in rows if x['probe']=='scripts/build_free_content.py')
assert (target['jobs'],target['weight'],target['max_weight'])==(134,5668,5661)
assert all(x['weight']<=x['max_weight'] for x in rows if x is not target)
A=json.loads((E/'macro-0f05-focused-before-attribution.json').read_text())
assert A['all_job_weight_deltas']=={'data-base-shim':{'incoming_manifest_weight':7,'candidate_weight':12,'delta':5},'unrun-nav-chrome':{'incoming_manifest_weight':30,'candidate_weight':32,'delta':2}}
p=W/'tests/test_ci_pack.py';before=p.read_bytes()
assert hashlib.sha256(before).hexdigest()==R['source_sha256']['tests/test_ci_pack.py']
s=before.decode();old='("scripts/build_free_content.py", 134, 5_661)';new='("scripts/build_free_content.py", 134, 5_668)'
assert s.count(old)==1;s=s.replace(old,new)
anchor='    Baselines on the pre-curation manifest (PR #5585 planner, 188 jobs):'
note='''    Shared Shell/current-main composition (2026-10-20, PR7949):
    the four existing scope/packing checks on 0f058428 plus this branch
    measure index.html 135 jobs / 5,793, build_free_content 134 / 5,668,
    and plan_book 128 / 5,542, with ten packs and the same selected job
    IDs as the prior f54 composition. That prior composition measured
    5,665 while the vector suite was still pending. Incoming 0f058428
    now includes its exact unrun-vector-baskets 31 -> 34 (+3) change.
    On these same selected IDs, incoming-manifest command weight is
    5,661; the retained Shared Shell data-base-shim +5 and nav-chrome +2
    produce 5,668. Fund only that measured seven-unit excess, 5,661 ->
    5,668. Preserve both incoming histories above, all suites, selectors,
    job and pack bounds, and the other two weight ceilings.

'''
assert s.count(anchor)==1 and 'Shared Shell/current-main composition (2026-10-20, PR7949):' not in s
s=s.replace(anchor,note+anchor)
def strip_docs(tree):
 for n in ast.walk(tree):
  if isinstance(n,(ast.Module,ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)) and n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant) and isinstance(n.body[0].value.value,str):n.body=n.body[1:]
 return tree
assert ast.dump(strip_docs(ast.parse(s.replace(new,old))))==ast.dump(strip_docs(ast.parse(before.decode())))
p.write_bytes(s.encode());subprocess.run(['git','-C',str(W),'add','--','tests/test_ci_pack.py'],check=True)
after_index=g('write-tree')
assert g('diff','--name-only',R['index'],after_index).splitlines()==['tests/test_ci_pack.py']
patch=subprocess.check_output(['git','-C',str(W),'diff',R['index'],after_index,'--','tests/test_ci_pack.py'])
(E/'macro-0f05-budget-repair.diff').write_bytes(patch)
check=subprocess.run(['git','-C',str(W),'diff','--check',R['index'],after_index,'--','tests/test_ci_pack.py'],capture_output=True,text=True);assert check.returncode==0
receipt={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':R['head'],'incoming':R['incoming'],'before_index':R['index'],'after_index':after_index,'measured_rows':[{k:v for k,v in x.items() if k!='job_ids'} for x in rows],'same_selected_ids_as_f54':True,'weight_deltas':A['all_job_weight_deltas'],'old_ceiling':5661,'new_ceiling':5668,'only_test_literal_and_history_changed':True,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(s.encode()).hexdigest(),'patch_sha256':hashlib.sha256(patch).hexdigest(),'whitespace_exit':check.returncode,'packing_green_not_yet_run':True}
(E/'macro-0f05-budget-repair.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(patch.decode());print(json.dumps(receipt,indent=2),flush=True)
