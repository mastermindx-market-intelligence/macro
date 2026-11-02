import ast,copy,datetime,difflib,hashlib,json,pathlib,subprocess
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");stem="macro-ae3-5c2d-packing-repair"
g=["git","-C",str(W)]
def git(*args):return subprocess.check_output(g+list(args))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
outpath=E/(stem+".json");assert not outpath.exists()
before_result=json.loads((E/"macro-ae3-5c2d-focused-before.json").read_text());dep=json.loads((E/"macro-ae3-5c2d-deploy-validation.json").read_text())
assert before_result["pytest_exit"]==1 and before_result["source_unchanged"] and before_result["index_unchanged"] and dep["pass"]
assert json.loads((E/"macro-ae3-5c2d-focused-before-process.json").read_text())["exit"]==1
index=git("write-tree").decode().strip();assert index=="1a008b73af0ef56634ce89bb07c62b7a5e0a5988" and not git("diff","--name-only").strip() and not git("ls-files","-u").strip()
assert git("rev-parse","HEAD").decode().strip()=="ae3e6bc547361b632223e7e9bde73128b399035e" and git("rev-parse","MERGE_HEAD").decode().strip()=="5c2d0a04afd19642d2dab483885d46c73b7baed4"
p=W/"tests/test_ci_pack.py";raw=p.read_bytes();before=raw.decode();assert dg(raw)=="96e6548805d3b33f5d42aec9b8a66fa8813bed108edf439ef00213878b23f352"
rows=json.loads((E/"macro-ae3-5c2d-focused-before-probes.json").read_text());attr=json.loads((E/"macro-ae3-5c2d-focused-before-attribution.json").read_text())
expected=[("templates/index.html",135,5829,10,136,5822),("scripts/build_free_content.py",134,5704,10,134,5697),("engine/prophet/plan_book.py",128,5578,10,130,5600)]
for row,ex,a in zip(rows,expected,attr["same_selected_ids_weight_comparison"]):
 assert (row["probe"],row["jobs"],row["weight"],row["packs"],row["max_jobs"],row["max_weight"])==ex
 assert len(row["job_ids"])==len(set(row["job_ids"]))==row["jobs"] and row["job_ids"]==a["candidate_selected_job_ids"]
 assert a["candidate_weight"]==row["weight"] and a["candidate_weight"]-a["incoming_manifest_weight_for_these_same_ids"]==7
 assert a["selected_command_weight_deltas"]=={"data-base-shim":{"incoming_manifest_weight":7,"candidate_weight":12,"delta":5},"unrun-nav-chrome":{"incoming_manifest_weight":30,"candidate_weight":32,"delta":2}}
assert len(rows)==len(expected)==len(attr["same_selected_ids_weight_comparison"])
text=before
for old,new in [('("templates/index.html", 136, 5_822)','("templates/index.html", 136, 5_829)'),('("scripts/build_free_content.py", 134, 5_697)','("scripts/build_free_content.py", 134, 5_704)')]:
 assert text.count(old)==1;text=text.replace(old,new,1)
tree=ast.parse(text);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="test_exclusive_curation_narrows_ordinary_code_prs")
doc=fn.body[0];assert isinstance(doc,ast.Expr) and isinstance(doc.value,ast.Constant) and isinstance(doc.value.value,str)
lines=text.splitlines(keepends=True);assert lines[doc.end_lineno-1].strip()=='"""'
note='''\n    2026-10-20 (original PR #7949, accepted 5c2d0a04 integration):
    The actual four-node run on frozen combined index
    1a008b73af0ef56634ce89bb07c62b7a5e0a5988 passed all three scope
    contracts and reproduced the two packing-weight breaches below.
    Applying incoming-main manifest weights to those SAME candidate-selected
    IDs gives the left column; this is not an incoming-tree selection run.

        templates/index.html          135 jobs, 5,822 -> 5,829 weight
        scripts/build_free_content.py 134 jobs, 5,697 -> 5,704 weight
        engine/prophet/plan_book.py    128 jobs, 5,571 -> 5,578 weight

    All three use ten packs. The only changed declared weights are retained
    Shared Shell coverage: data-base-shim 7 -> 12 (+5) and unrun-nav-chrome
    30 -> 32 (+2). Both jobs are present in every measured row. Fund only
    the two breached weight ceilings: 5,822 -> 5,829 and 5,697 -> 5,704.
    Preserve the plan-book ceiling 5,600, every job-count and pack bound,
    all suites, selectors, scope/closure audits and duration overrides.
    These are deterministic planning weights, not execution timings.
'''
lines.insert(doc.end_lineno-1,note);after="".join(lines)
bt=ast.parse(before);at=ast.parse(after);expected_ast=copy.deepcopy(bt)
assign=next(n for n in expected_ast.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="PACKING_PROBES" for t in n.targets))
assert ast.literal_eval(assign.value)==(("templates/index.html",136,5822),("scripts/build_free_content.py",134,5697),("engine/prophet/plan_book.py",130,5600))
assign.value.elts[0].elts[2].value=5829;assign.value.elts[1].elts[2].value=5704
for t in [expected_ast,at]:
 f=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=="test_exclusive_curation_narrows_ordinary_code_prs")
 f.body[0].value.value="DOCSTRING_REVIEWED_SEPARATELY"
assert ast.dump(expected_ast,include_attributes=False)==ast.dump(at,include_attributes=False)
old_doc=ast.get_docstring(next(n for n in bt.body if isinstance(n,ast.FunctionDef) and n.name==fn.name),clean=False)
new_doc=ast.get_docstring(next(n for n in ast.parse(after).body if isinstance(n,ast.FunctionDef) and n.name==fn.name),clean=False)
assert new_doc==old_doc[:-4]+note+old_doc[-4:]
patch="".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile="a/tests/test_ci_pack.py",tofile="b/tests/test_ci_pack.py"))
(E/(stem+".patch")).write_text(patch)
out={"started_at":now(),"head":git("rev-parse","HEAD").decode().strip(),"incoming":git("rev-parse","MERGE_HEAD").decode().strip(),"index_before":index,"before_sha256":dg(raw),"after_sha256":dg(after.encode()),"measured_rows":[{k:v for k,v in x.items() if k!="job_ids"} for x in rows],"changes":[{"probe":"templates/index.html","old":5822,"new":5829},{"probe":"scripts/build_free_content.py","old":5697,"new":5704}],"ast_only_two_weight_literals_plus_docstring":True,"prior_docstring_retained":True,"patch":{"path":str(E/(stem+".patch")),"bytes":len(patch.encode()),"sha256":dg(patch.encode())},"source_write_attempted":False}
outpath.write_text(json.dumps(out,indent=2)+"\n")
out["source_write_attempted"]=True;outpath.write_text(json.dumps(out,indent=2)+"\n")
p.write_text(after);subprocess.run(g+["add","--","tests/test_ci_pack.py"],check=True)
assert git("show",":tests/test_ci_pack.py")==p.read_bytes() and not git("diff","--name-only").strip()
subprocess.run(g+["diff","--cached","--check","5c2d0a04afd19642d2dab483885d46c73b7baed4","--","tests/test_ci_pack.py"],check=True)
out.update({"index_after":git("write-tree").decode().strip(),"finished_at":now(),"staged_raw_equal":True,"no_unstaged":True,"owned_whitespace_exit":0})
outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"bytes":outpath.stat().st_size,"sha256":dg(outpath.read_bytes()),"index_after":out["index_after"],"patch":patch},indent=2))
