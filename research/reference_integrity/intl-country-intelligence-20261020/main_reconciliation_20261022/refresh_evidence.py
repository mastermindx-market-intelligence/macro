import concurrent.futures,datetime,hashlib,json,pathlib,subprocess
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
E=R/"research/reference_integrity/intl-country-intelligence-20261020"
C=E/"main_composition_20261021";D=E/"main_reconciliation_20261022"
SOURCE="c2b0562234abbec883ea91b934ac3d09fa3bae8b";OLD="eac74360b9a423ece8b1af786aca5fd29cb48c3f"
PY="/tmp/intl-country-cockpit-ci-20261021/bin/python";LABEL="main25020261022"
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=R,text=True).strip()==SOURCE
assert subprocess.check_output(["git","show","-s","--format=%P",SOURCE],cwd=R,text=True).split()==["7e99587336105a939c830a00b799d7787624d09b","25051144947f027c698cd1ce10e3c8824ee6ade9"]
assert not (D/"refresh_execution.json").exists(),"Original attempt exists; reconcile it instead of rerunning"
def make(source,target,replacements):
 text=source.read_text()
 for old,new in replacements:
  assert old in text,(str(source),old)
  text=text.replace(old,new)
 assert not target.exists(),target
 target.write_text(text)
 return target
common=[("main_composition_20261021","main_reconciliation_20261022"),(OLD,SOURCE)]
p0b=make(C/"run_p0b_composition.py",D/"run_p0b_composition.py",common+[("/tmp/intl-p0b-remint-20261021","/tmp/intl-p0b-remint-main250-20261022")])
bind=make(C/"bind_p0b_composition.py",D/"bind_p0b_composition.py",common+[("accepted_local/manifest.json","previous_published/manifest.json")])
build=make(E/"build_review_repair.py",E/"build_main250_runtime_20261022.py",[('choices=("ui", "final", "dock", "dock2", "dock3", "dock4")','choices=("'+LABEL+'",)'),("/tmp/intl-rig-review-repair-20261020","/tmp/intl-rig-main250-20261022"),("intl.reference_complete_repair_build.v1","intl.current_main_build.v1")])
compare=make(C/"compare_build.py",D/"compare_build.py",common+[("proposed_composition20261022_repair","proposed_"+LABEL+"_repair")])
capture=make(E/"capture_review_repair.py",E/"capture_main250_runtime_20261022.py",[('choices=("ui", "final", "dock", "dock2", "dock3", "dock4")','choices=("'+LABEL+'",)'),('("dock", "dock2", "dock3", "dock4")','("dock", "dock2", "dock3", "dock4", "'+LABEL+'")'),('("dock3", "dock4")','("dock3", "dock4", "'+LABEL+'")'),("intl.rig_review_repair_browser.v1","intl.current_main_runtime_browser.v1")])
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
record={"schema":"intl.current_main_refresh_execution.v1","source_commit":SOURCE,"started_at":now(),"state":"RUNNING","pipelines":[],"effects":{"production_mutation":False,"source_reacquisition":False,"publish":False,"fenced_shell_repair":False}}
out=D/"refresh_execution.json"
def save():out.write_text(json.dumps(record,indent=2)+"\n")
def execute(name,command):
 start=now();log=D/(name+".log")
 with log.open("wb") as f:p=subprocess.run(command,cwd=R,stdout=f,stderr=subprocess.STDOUT)
 raw=log.read_bytes();row={"name":name,"command":command,"started_at":start,"completed_at":now(),"exit_code":p.returncode,"log":str(log.relative_to(R)),"sha256":hashlib.sha256(raw).hexdigest()}
 print(json.dumps({**row,"tail":raw.decode(errors="replace")[-2500:]}),flush=True);return row
def pipeline(name,steps):
 rows=[]
 for label,command in steps:
  row=execute(label,command);rows.append(row)
  if row["exit_code"]:break
 return {"name":name,"steps":rows,"pass":len(rows)==len(steps) and all(r["exit_code"]==0 for r in rows)}
save()
p0b_steps=[("p0b_run",[PY,"-u",str(p0b)]),("p0b_bind",[PY,"-u",str(bind)])]
intl_steps=[("intl_build",[PY,"-u",str(build),"--source-sha",SOURCE,"--label",LABEL]),("country_equivalence",[PY,"-u",str(compare)]),("intl_runtime_capture",[PY,"-u",str(capture),"--label",LABEL])]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(pipeline,"p0b",p0b_steps),pool.submit(pipeline,"international",intl_steps)]
 for f in concurrent.futures.as_completed(futures):record["pipelines"].append(f.result());save()
record["completed_at"]=now();record["state"]="PASS" if all(p["pass"] for p in record["pipelines"]) else "FAILED";save()
print(json.dumps({"source_commit":SOURCE,"state":record["state"],"completed_at":record["completed_at"]}),flush=True)
raise SystemExit(0 if record["state"]=="PASS" else 1)
