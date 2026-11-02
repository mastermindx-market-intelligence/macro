import pathlib,subprocess,json,hashlib,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
g=["git","--no-optional-locks","-C",str(W)];stem="macro-e2d-42c-p0b-closure";outpath=E/(stem+".json");assert not outpath.exists()
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def snap():return {"head":git("rev-parse","HEAD").decode().strip(),"merge_head":git("rev-parse","MERGE_HEAD").decode().strip(),"index_tree":git("write-tree").decode().strip(),"index_entry_list_sha256":dg(git("ls-files","--stage","-z")),"unstaged_paths":git("diff","--name-only").decode().splitlines()}
before=snap();assert before["index_tree"]=="5cb74e747b76b3321e36f4392ac25c40c84a3aef" and not before["unstaged_paths"]
diff=E/(stem+"-changed.txt");diff.write_bytes(git("diff","--cached","--name-only","42c859546ececa797b400db0adeb8c5a22f96832"))
nodes=["tests/test_stock_dashboard_first_frame.py::test_rendered_fixture_recipe_is_committed_self_binding_and_deterministic","tests/test_stock_dashboard_first_frame.py::test_committed_browser_receipts_are_self_binding_fixture_proof","tests/test_stock_dashboard_first_frame.py::test_visual_manifest_preserves_history_and_appends_bounded_repair"]
python=str(W/".venv-shared-shell/bin/python")
commands=[("closure",[python,"-B","scripts/check_p0b_receipt_closure.py","--diff-file",str(diff),"--event","pull_request"]),("binding-tests",[python,"-B","-m","pytest","-q","--tb=short","--basetemp",str(E/(stem+"-tmp")),*nodes])]
out={"started_at":now(),"before":before,"diff":{"path":str(diff),"sha256":dg(diff.read_bytes()),"count":len(diff.read_text().splitlines())},"commands":[]};outpath.write_text(json.dumps(out,indent=2)+"\n")
for name,args in commands:
 log=E/(stem+"-"+name+".log");assert not log.exists();row={"name":name,"args":args,"started_at":now(),"log":str(log)};out["commands"].append(row);outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"started":name,"at":row["started_at"]}),flush=True)
 with log.open("xb") as f:p=subprocess.run(args,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 row.update({"exit":p.returncode,"finished_at":now(),"log_bytes":log.stat().st_size,"log_sha256":dg(log.read_bytes())});outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"finished":name,**row,"tail":log.read_text(errors="replace")[-3000:]}),flush=True)
 if p.returncode:break
out["after"]=snap();out["source_state_unchanged"]=out["before"]==out["after"];out["finished_at"]=now();out["pass"]=out["source_state_unchanged"] and len(out["commands"])==len(commands) and all(r["exit"]==0 for r in out["commands"]);outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"bytes":outpath.stat().st_size,"sha256":dg(outpath.read_bytes()),"pass":out["pass"]}),flush=True)
raise SystemExit(0 if out["pass"] else 1)
