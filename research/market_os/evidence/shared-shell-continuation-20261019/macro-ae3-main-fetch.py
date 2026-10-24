import pathlib,subprocess,json,hashlib,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");g=["git","--no-optional-locks","-C",str(W)]
outpath=E/"macro-ae3-main-fetch.json";log=E/"macro-ae3-main-fetch.log";assert not outpath.exists() and not log.exists()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*a):return subprocess.check_output(g+list(a))
assert git("rev-parse","HEAD").decode().strip()=="ae3e6bc547361b632223e7e9bde73128b399035e" and not git("status","--porcelain=v1","--untracked-files=no").strip()
out={"started_at":now(),"head_before":git("rev-parse","HEAD").decode().strip(),"args":g+["fetch","--no-tags","origin","main"]};outpath.write_text(json.dumps(out,indent=2)+"\n")
with log.open("xb") as f:p=subprocess.run(out["args"],cwd=W,stdout=f,stderr=subprocess.STDOUT)
out["exit"]=p.returncode;out["finished_at"]=now();out["log"]={"path":str(log),"bytes":log.stat().st_size,"sha256":hashlib.sha256(log.read_bytes()).hexdigest()};out["head_after"]=git("rev-parse","HEAD").decode().strip();out["origin_main"]=git("rev-parse","origin/main").decode().strip();out["fetch_head"]=git("rev-parse","FETCH_HEAD").decode().strip();out["status_after"]=git("status","--porcelain=v1","--untracked-files=no").decode().splitlines();outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({**out,"log_tail":log.read_text(errors="replace")[-2000:],"receipt_sha256":hashlib.sha256(outpath.read_bytes()).hexdigest()}),flush=True)
assert p.returncode==0 and out["head_before"]==out["head_after"] and not out["status_after"] and out["fetch_head"]==out["origin_main"]
