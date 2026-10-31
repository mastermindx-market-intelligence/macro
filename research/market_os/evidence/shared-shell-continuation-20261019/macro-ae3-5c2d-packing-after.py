import datetime,hashlib,json,pathlib,subprocess
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");stem="macro-ae3-5c2d-packing-after";g=["git","-C",str(W)]
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
R=json.loads((E/"macro-ae3-5c2d-packing-repair.json").read_text())
assert R["index_after"]=="39477d0a200f63fe0d1fcf1eaa4f6d21873c86aa" and R["ast_only_two_weight_literals_plus_docstring"] and R["staged_raw_equal"]
assert git("write-tree").decode().strip()==R["index_after"] and not git("diff","--name-only").strip()
paths=["tests/test_ci_pack.py",".github/ci/legacy-jobs.yml","scripts/run_ci_pack.py","app/deploy/Caddyfile","app/deploy/update.sh"]
before={p:dg((W/p).read_bytes()) for p in paths};assert before[paths[0]]==R["after_sha256"]
outpath=E/(stem+".json");log=E/(stem+".log");tmp=E/(stem+"-tmp")
assert not outpath.exists() and not log.exists() and not tmp.exists()
args=["/opt/homebrew/opt/python@3.12/bin/python3.12","-B","-m","pytest","-q","--tb=short","--basetemp",str(tmp),"tests/test_ci_pack.py::test_exclusive_curation_narrows_ordinary_code_prs"]
out={"started_at":now(),"head":git("rev-parse","HEAD").decode().strip(),"incoming":git("rev-parse","MERGE_HEAD").decode().strip(),"index":R["index_after"],"source_before":before,"args":args,"prior_red_receipt":"macro-ae3-5c2d-focused-before.json","scope":"Only the actually failed existing packing node; three unchanged scope nodes already passed; no selector/command/coverage change"}
outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"started_at":out["started_at"]}),flush=True)
with log.open("xb") as f:r=subprocess.run(args,cwd=W,stdout=f,stderr=subprocess.STDOUT)
out.update({"exit":r.returncode,"finished_at":now(),"log":{"path":str(log),"bytes":log.stat().st_size,"sha256":dg(log.read_bytes())},"source_after":{p:dg((W/p).read_bytes()) for p in paths},"index_after":git("write-tree").decode().strip(),"unstaged_after":git("diff","--name-only").decode().splitlines()})
out["pass"]=r.returncode==0 and out["source_before"]==out["source_after"] and out["index"]==out["index_after"] and not out["unstaged_after"]
outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"bytes":outpath.stat().st_size,"sha256":dg(outpath.read_bytes()),"pass":out["pass"],"tail":log.read_text(errors="replace")[-3000:]}),flush=True)
raise SystemExit(0 if out["pass"] else 1)
