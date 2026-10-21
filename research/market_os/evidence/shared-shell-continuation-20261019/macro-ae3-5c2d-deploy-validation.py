import pathlib,subprocess,json,hashlib,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");g=["git","--no-optional-locks","-C",str(W)];stem="macro-ae3-5c2d-deploy-validation";outpath=E/(stem+".json");assert not outpath.exists()
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
index=git("write-tree").decode().strip();assert index=="1a008b73af0ef56634ce89bb07c62b7a5e0a5988" and not git("diff","--name-only").strip()
paths=["app/deploy/Caddyfile","app/deploy/update.sh","config/site_access.yml","tests/test_regwall_json_gate.py","tests/test_site_access_boundary.py","tests/test_deploy_update_self_heal.py"]
before={p:dg((W/p).read_bytes()) for p in paths}
assert before["app/deploy/Caddyfile"]=="cb8adb3ce636e956fdb58831b960495f6cfba4dc75c578c62bfae39a3b64af3a" and before["app/deploy/update.sh"]=="337664e579503b69d3bd11d4aeba817c9393f90d165a6a7821b07a52ef905394"
args=[str(W/".venv-shared-shell/bin/python"),"-B","-m","pytest","-q","--tb=short","--basetemp",str(E/(stem+"-tmp")),*paths[3:]]
log=E/(stem+".log");assert not log.exists() and not (E/(stem+"-tmp")).exists()
out={"started_at":now(),"head":git("rev-parse","HEAD").decode().strip(),"incoming":git("rev-parse","MERGE_HEAD").decode().strip(),"index":index,"source_before":before,"args":args,"prior_result":"334 assertions passed but session exit1 because concurrent root site/theme writes; this is unchanged rerun after full freeze","existing_bash_and_10_header_cases_reused_for_identical_bytes":True};outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"started_at":out["started_at"]}),flush=True)
with log.open("xb") as f:r=subprocess.run(args,cwd=W,stdout=f,stderr=subprocess.STDOUT)
out["exit"]=r.returncode;out["finished_at"]=now();out["log"]={"path":str(log),"bytes":log.stat().st_size,"sha256":dg(log.read_bytes())};out["source_after"]={p:dg((W/p).read_bytes()) for p in paths};out["index_after"]=git("write-tree").decode().strip();out["unstaged_after"]=git("diff","--name-only").decode().splitlines();out["pass"]=r.returncode==0 and out["source_after"]==before and out["index_after"]==index and not out["unstaged_after"];outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"bytes":outpath.stat().st_size,"sha256":dg(outpath.read_bytes()),"pass":out["pass"],"exit":r.returncode,"tail":log.read_text(errors="replace")[-3000:]}),flush=True)
raise SystemExit(0 if out["pass"] else 1)
