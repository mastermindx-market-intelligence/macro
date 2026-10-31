import pathlib,subprocess,os,sys,json,hashlib,datetime,time
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018");Q=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022")
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
s={"schema":"intl.screener_repair_validation.v1","started_at":now(),"source_commit":"45e70cb40d6e9ac1a49478b1920ab6a7275f7f58","checks":[]}
env=os.environ.copy();env["PATH"]="/opt/homebrew/bin:"+env.get("PATH","")
for name,cmd in [
 ("canonical_bake",[sys.executable,str(Q/"reconcile_screener_html.py"),"--apply"]),
 ("research_screener_suite",[sys.executable,"-m","pytest","tests/test_research_screener.py","-q"])
]:
 log=Q/(name+".log");start=time.monotonic()
 with log.open("w") as f: rc=subprocess.run(cmd,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT).returncode
 s["checks"].append({"name":name,"exit_code":rc,"duration_seconds":round(time.monotonic()-start,2),"log":str(log.relative_to(R)),"log_sha256":hashlib.sha256(log.read_bytes()).hexdigest()})
 (Q/"screener_validation.json").write_text(json.dumps(s,indent=2)+"\n")
 print(name,rc,flush=True);print("\n".join(log.read_text().splitlines()[-25 if rc else -2:]),flush=True)
 if rc:sys.exit(rc)
s["completed_at"]=now();s["pass"]=True
(Q/"screener_validation.json").write_text(json.dumps(s,indent=2)+"\n")
print(json.dumps(s,indent=2),flush=True)
