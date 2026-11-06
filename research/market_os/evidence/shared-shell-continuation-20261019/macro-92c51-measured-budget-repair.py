import ast,datetime,difflib,hashlib,json,pathlib,subprocess
W=pathlib.Path('/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27');E=pathlib.Path('/tmp/shared-shell-css-visual-20261019T1107')
R=json.loads((E/'macro-92c51-focused-before.json').read_text());S=json.loads((E/'macro-92c51-measurement-summary.json').read_text())
def g(*a):return subprocess.check_output(['git','-C',str(W),*a],text=True).strip()
def sha(b):return hashlib.sha256(b).hexdigest()
assert R['pytest_exit']==1 and R['source_unchanged'] and R['index_unchanged']
assert g('rev-parse','HEAD')==R['head'] and g('rev-parse','MERGE_HEAD')==R['incoming'] and g('write-tree')==R['index']
assert not g('diff','--name-only') and not g('ls-files','-u')
for p,h in R['source_sha256'].items():assert sha((W/p).read_bytes())==h,p
assert [(x['jobs'],x['weight'],x['packs']) for x in S['rows']]==[(135,5796,10),(134,5671,10),(128,5545,10)]
assert all(x['same_selected_ids_and_order_as_prior_0f05'] and x['shell_command_weight_delta']==7 for x in S['rows'])
p=W/'tests/test_ci_pack.py';before=p.read_text()
old='    ("scripts/build_free_content.py", 134, 5_664),'
new='    ("scripts/build_free_content.py", 134, 5_671),'
assert before.count(old)==1 and new not in before
after=before.replace(old,new)
marker='    Baselines on the pre-curation manifest (PR #5585 planner, 188 jobs):'
note='''    Shared Shell/current-main92c51 composition (2026-10-20, PR7949):
    the four existing scope/packing checks measure index.html 135 jobs /
    5,796, build_free_content 134 / 5,671, and plan_book 128 / 5,545,
    all in ten packs. Selected IDs/order match the prior 0f05 composition;
    each weight rises exactly three with the incoming scorecard step.
    Incoming command weights on those same IDs are 5,789 / 5,664 / 5,538.
    The retained Shell data-base-shim +5 and nav-chrome +2 explain the
    entire seven-unit excess. Fund only 5,664 -> 5,671; keep all previous
    histories, suites, selectors, job/pack bounds and other ceilings.

'''
assert after.count(marker)==1;after=after.replace(marker,note+marker)
class StripDoc(ast.NodeTransformer):
 def visit_FunctionDef(self,node):
  self.generic_visit(node)
  if node.body and isinstance(node.body[0],ast.Expr) and isinstance(node.body[0].value,ast.Constant) and isinstance(node.body[0].value.value,str):node.body=node.body[1:]
  return node
expected=ast.parse(before)
probe=next(n for n in expected.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PACKING_PROBES' for t in n.targets))
row=next(n for n in probe.value.elts if n.elts[0].value=='scripts/build_free_content.py');assert row.elts[2].value==5664;row.elts[2].value=5671
assert ast.dump(StripDoc().visit(expected),include_attributes=False)==ast.dump(StripDoc().visit(ast.parse(after)),include_attributes=False)
patch=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/tests/test_ci_pack.py',tofile='b/tests/test_ci_pack.py'))
dp=E/'macro-92c51-budget-repair.diff';assert not dp.exists();dp.write_text(patch)
p.write_text(after);g('add','--','tests/test_ci_pack.py')
index=g('write-tree');assert g('diff','--name-only',R['index'],index).splitlines()==['tests/test_ci_pack.py']
assert not g('diff','--name-only') and not g('ls-files','-u')
q=subprocess.run(['git','-C',str(W),'diff','--cached','--check',R['incoming']],capture_output=True,text=True)
assert q.returncode==0,(q.stdout,q.stderr)
out={'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':R['head'],'incoming':R['incoming'],'before_index':R['index'],'after_index':index,'old_ceiling':5664,'new_ceiling':5671,'actual_producing_rows':S['rows'],'only_executable_change':'PACKING_PROBES build_free_content weight5664->5671','history_added':note,'test_before_sha256':sha(before.encode()),'test_after_sha256':sha(after.encode()),'patch_sha256':sha(patch.encode()),'patch_bytes':len(patch.encode()),'all_other_AST_unchanged':True,'complete_owned_whitespace_exit':q.returncode,'validation_after_patch':'PENDING'}
raw=(json.dumps(out,indent=2)+'\n').encode();dest=E/'macro-92c51-budget-repair.json';assert not dest.exists();dest.write_bytes(raw);print(patch);print(raw.decode());print(json.dumps({'receipt_sha256':sha(raw)}))
