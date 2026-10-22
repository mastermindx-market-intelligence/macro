import pathlib,subprocess,json,hashlib,datetime,os
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");stem="macro-e2d-42c-deploy-validation"
receipt=E/(stem+".json");assert not receipt.exists()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def hashes():return {p:hashlib.sha256((W/p).read_bytes()).hexdigest() for p in ["app/deploy/Caddyfile","app/deploy/update.sh","config/site_access.yml","tests/test_regwall_json_gate.py","tests/test_site_access_boundary.py","tests/test_deploy_update_self_heal.py","scripts/verify_shared_shell_caddy_headers.py"]}
before=hashes();assert before["app/deploy/Caddyfile"]=="cb8adb3ce636e956fdb58831b960495f6cfba4dc75c578c62bfae39a3b64af3a"
assert before["app/deploy/update.sh"]=="337664e579503b69d3bd11d4aeba817c9393f90d165a6a7821b07a52ef905394"
py=str(W/".venv-shared-shell/bin/python")
commands=[("bash-syntax",["bash","-n","app/deploy/update.sh"]),("headers",[py,"-B","scripts/verify_shared_shell_caddy_headers.py","--caddyfile","app/deploy/Caddyfile","--caddy","caddy"]),("boundary-updater",[py,"-B","-m","pytest","-q","--tb=short","--basetemp",str(E/(stem+"-pytest-tmp")),"tests/test_regwall_json_gate.py","tests/test_site_access_boundary.py","tests/test_deploy_update_self_heal.py"])]
out={"started_at":now(),"head":"e2d10f933587f58be8716505529a37f8839901f7","incoming":"42c859546ececa797b400db0adeb8c5a22f96832","source_before":before,"commands":[],"production_effect":False}
def save():receipt.write_text(json.dumps(out,indent=2)+"\n")
save()
for name,args in commands:
 log=E/(stem+"-"+name+".log");assert not log.exists()
 row={"name":name,"args":args,"started_at":now(),"log":str(log)};out["commands"].append(row);save();print(json.dumps({"started":name,"at":row["started_at"]}),flush=True)
 with log.open("xb") as f:r=subprocess.run(args,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 data=log.read_bytes();row.update({"finished_at":now(),"exit":r.returncode,"log_bytes":len(data),"log_sha256":hashlib.sha256(data).hexdigest(),"summary":data.decode(errors="replace")[-3500:]});save();print(json.dumps({"finished":name,"exit":r.returncode,"summary":row["summary"]}),flush=True)
out["finished_at"]=now();out["source_after"]=hashes();out["source_unchanged"]=out["source_after"]==before;out["pass"]=all(r["exit"]==0 for r in out["commands"]) and out["source_unchanged"];save();data=receipt.read_bytes();print(json.dumps({"receipt":str(receipt),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"pass":out["pass"]}),flush=True)