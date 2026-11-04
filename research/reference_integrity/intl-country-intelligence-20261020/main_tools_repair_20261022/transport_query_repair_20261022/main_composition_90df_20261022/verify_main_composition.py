"""Run unchanged fragment/country proof against the exact main-composed build."""
import concurrent.futures,datetime,hashlib,json,os,pathlib,subprocess,sys,time
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018");C=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_90df_20261022");E=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020")
SOURCE="48b5c3312a22548010f330f03ac0b261695c16b6";LABEL="main90df20261022"
def sha(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()==SOURCE
br=C/("repair_"+LABEL+"_build_receipt.json");build=json.loads(br.read_text())
assert build["source_commit"]==SOURCE and build["exit_code"]==0 and build["source_overlays"]==[]
snapshot=E/"production_input_snapshot.json";assert sha(snapshot.read_bytes())==build["input_snapshot_sha256"]
clarification={"schema":"intl.build_input_path_clarification.v1","recorded_at":now(),"build_receipt":str(br.relative_to(R)),"original_receipt_sha256":sha(br.read_bytes()),"display_field_as_recorded":build["input_snapshot"],"actual_input_snapshot":str(snapshot.relative_to(R)),"correct_relative_to_receipt":"../../../production_input_snapshot.json","verified_sha256":sha(snapshot.read_bytes()),"reason":"Relocated driver used the correct explicit absolute snapshot path and verified every retained input. Its inherited display-only relative path was not adjusted. This clarification preserves the original execution receipt and driver unchanged.","execution_change":False,"retained_input_count":len(json.loads(snapshot.read_text())["files"])}
(C/"BUILD_INPUT_PATH_CLARIFICATION.json").write_text(json.dumps(clarification,indent=2)+"\n")
s={"schema":"intl.main_composition_runtime_summary.v1","started_at":now(),"source_commit":SOURCE,"html_sha256":build["html_sha256"],"build_receipt_sha256":sha(br.read_bytes()),"retained_input_count":clarification["retained_input_count"],"retained_assets":len(build["files"]),"checks":[]}
def run(name,args):
 log=C/(name+".log");tick=time.monotonic()
 with log.open("w") as f:rc=subprocess.run([sys.executable,*args],cwd=R,stdout=f,stderr=subprocess.STDOUT,timeout=600).returncode
 row={"name":name,"exit_code":rc,"duration_seconds":round(time.monotonic()-tick,2),"log":str(log.relative_to(R)),"log_sha256":sha(log.read_bytes())}
 print(json.dumps(row),flush=True)
 if rc:print("\n".join(log.read_text().splitlines()[-20:]),flush=True)
 return row
s["checks"].append(run("frozen_country_equivalence",[str(C/"compare_main_country.py")]))
if s["checks"][-1]["exit_code"]:sys.exit(s["checks"][-1]["exit_code"])
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(run,"standalone_fragment_landings",[str(C/"verify_standalone_toolbar_landings.py"),"--label",LABEL]),pool.submit(run,"standalone_country_history",[str(C/"verify_standalone_country_history.py"),"--label",LABEL])]
 s["checks"].extend(f.result() for f in futures)
for key,name in [("landings","toolbar_"+LABEL+"_landings.json"),("country_history","country_history_"+LABEL+".json")]:
 p=C/name
 if p.exists():
  v=json.loads(p.read_text());s[key]={"receipt":str(p.relative_to(R)),"sha256":sha(p.read_bytes()),"passed":v["passed"],"failed":v["failed"],"source_commit":v["source_commit"],"html_sha256":v["html_sha256"]}
  assert v["source_commit"]==SOURCE and v["html_sha256"]==build["html_sha256"]
s["countries_equal"]=json.loads((C/"country_equivalence.json").read_text())["pass"]
s["completed_at"]=now();s["head_unchanged"]=subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()==SOURCE
s["pass"]=s["head_unchanged"] and s["countries_equal"] and all(x["exit_code"]==0 for x in s["checks"])
(C/"MAIN_COMPOSITION_RUNTIME_SUMMARY.json").write_text(json.dumps(s,indent=2)+"\n")
print(json.dumps(s,indent=2),flush=True)
sys.exit(0 if s["pass"] else 1)
