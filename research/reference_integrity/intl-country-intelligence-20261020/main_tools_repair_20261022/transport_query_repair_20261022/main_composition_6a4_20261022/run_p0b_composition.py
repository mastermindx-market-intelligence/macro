"""Run canonical P0B fixture producers for the exact International/main composition."""
import concurrent.futures,datetime,gzip,hashlib,json,os,pathlib,subprocess,time
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
C=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_6a4_20261022")
P="mockups/evidence/prophet-p0b-zero-fouc"
SOURCE="51b217b3eb1ee211d54706d2673ab183de9452b3"
PY="/tmp/intl-country-cockpit-ci-20261021/bin/python"
OUT="/tmp/intl-p0b-remint-main6a4-20261022"
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()==SOURCE
assert not pathlib.Path(OUT).exists(),"Inspect the existing original attempt instead of rerunning"
env=os.environ.copy()
env["NODE_PATH"]="/tmp/intl-browser-node-20261021/node_modules"
env["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"]="1"
record={"schema":"intl.p0b_composition_execution.v1","source_commit":SOURCE,"started_at":now(),"driver_sha256":sha(pathlib.Path(__file__)),"canonical_commands":True,"effects":{"collectors":False,"publish":False,"ledger_advance":False,"production":False},"executions":[],"state":"RUNNING"}
receipt=C/"p0b_execution.json"
def save(): receipt.write_text(json.dumps(record,indent=2)+"\n")
def execute(name,command):
 started=now(); tick=time.monotonic(); log=C/(name+".log")
 with log.open("wb") as f:
  p=subprocess.run(command,cwd=R,env=env,stdout=f,stderr=subprocess.STDOUT)
 row={"name":name,"command":command,"started_at":started,"completed_at":now(),"duration_seconds":round(time.monotonic()-tick,2),"exit_code":p.returncode,"log":str(log.relative_to(R)),"log_sha256":sha(log)}
 print(json.dumps({k:v for k,v in row.items() if k!="command"}),flush=True)
 return row
save()
render=execute("p0b_render",[PY,"scripts/render_stock_dashboard_fixture.py","--market","all","--out-dir",OUT,"--receipt",P+"/rendered-fixture.json"])
record["executions"].append(render); save()
if render["exit_code"]:
 record["state"]="FAILED_RENDER"; save(); raise SystemExit(render["exit_code"])
commands=[]
for market,html,out in [("hk","hk_stocks.html","mobile-layout.json"),("ca","canada_stocks.html","mobile-layout-canada.json")]:
 command=["/opt/homebrew/bin/node","scripts/verify_stock_dashboard_mobile_layout.cjs","--html",OUT+"/"+html,"--site-dir","site","--fixture-receipt",P+"/rendered-fixture.json","--fixture-assets-dir",P+"/inputs/browser-data","--screenshot-dir",P,"--historical-head","3fb76ea810a8e9ef6a05fe808bb6eaee87eb1f86","--historical-tree","b4dd8fd9b29b4eb769239d35df2a7911e793c7ec","--browser","/Applications/Google Chrome.app/Contents/MacOS/Google Chrome","--out",P+"/"+out]
 commands.append(("p0b_"+market,command))
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(execute,*item) for item in commands]
 for future in concurrent.futures.as_completed(futures):
  record["executions"].append(future.result()); save()
record["completed_at"]=now()
record["state"]="PASS" if all(row["exit_code"]==0 for row in record["executions"]) else "FAILED_BROWSER"
for row in record["executions"]:
 log=R/row["log"]
 if log.stat().st_size>262144:
  raw=log.read_bytes(); target=log.with_suffix(log.suffix+".gz"); target.write_bytes(gzip.compress(raw,mtime=0))
  row["log_archive"]={"path":str(target.relative_to(R)),"sha256":sha(target),"encoding":"gzip","uncompressed_sha256":row["log_sha256"]}
  row["original_log_path"]=row.pop("log"); log.unlink()
record["actual_receipts"]=[{"path":P+"/"+name,"sha256":sha(R/P/name)} for name in ["rendered-fixture.json","mobile-layout.json","mobile-layout-canada.json"]]
save()
print(json.dumps({"state":record["state"],"source_commit":SOURCE,"completed_at":record["completed_at"]}),flush=True)
raise SystemExit(0 if record["state"]=="PASS" else 1)