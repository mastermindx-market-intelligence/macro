import pathlib,subprocess,json,hashlib,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");stem="macro-ae3-5c2d-focused-before"
log=E/(stem+".log");assert not log.exists()
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
with log.open("xb") as f:r=subprocess.run(["/opt/homebrew/opt/python@3.12/bin/python3.12","-B","-u",str(E/(stem+"-runner.py"))],cwd=W,stdout=f,stderr=subprocess.STDOUT)
out={"started_at":start,"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"exit":r.returncode,"log":str(log),"log_bytes":log.stat().st_size,"log_sha256":hashlib.sha256(log.read_bytes()).hexdigest()};(E/(stem+"-process.json")).write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({**out,"tail":log.read_text(errors="replace")[-5500:]}),flush=True)
raise SystemExit(r.returncode)
