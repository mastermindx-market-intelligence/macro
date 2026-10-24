import concurrent.futures,datetime,hashlib,json,pathlib,subprocess,time
R=pathlib.Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
C=R/"research/reference_integrity/intl-country-intelligence-20261020/main_composition_20261021"
PY="/tmp/intl-country-cockpit-ci-20261021/bin/python"
D="/tmp/intl-pr9596-composed-20261022.diff"
N="/tmp/intl-pr9596-composed-20261022-paths.txt"
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
checks=[
 ("reference_repo",[PY,"scripts/check_reference_integrity.py"]),
 ("reference_artifact",[PY,"scripts/check_reference_integrity.py","--evaluate","intl-country-intelligence-20261020"]),
 ("design",[PY,"scripts/check_design_system.py","--mode","enforce-added","--diff-file",D]),
 ("runtime_styles",[PY,"scripts/check_runtime_style_injection.py"]),
 ("visual_evidence",[PY,"scripts/check_ui_visual_evidence.py","--diff-file",D]),
 ("p0b_closure",[PY,"scripts/check_p0b_receipt_closure.py","--diff-file",N]),
 ("p0b_receipt_contract",[PY,"-m","pytest","tests/test_stock_dashboard_first_frame.py","-q"])
]
report={"schema":"intl.main_composition_local_gates.v1","source_commit":"eac74360b9a423ece8b1af786aca5fd29cb48c3f","incoming_main":"2fed30a5a14f6bdd5e69d42c5bfcbac5814b3915","diff_sha256":hashlib.sha256(pathlib.Path(D).read_bytes()).hexdigest(),"diff_bytes":pathlib.Path(D).stat().st_size,"changed_paths":pathlib.Path(N).read_text().splitlines(),"started_at":now(),"checks":[],"state":"RUNNING"}
target=C/"local_gates.json"
def save(): target.write_text(json.dumps(report,indent=2)+"\n")
def execute(name,command):
 start=now();tick=time.monotonic();log=C/("guard_"+name+".log")
 with log.open("wb") as out: p=subprocess.run(command,cwd=R,stdout=out,stderr=subprocess.STDOUT)
 raw=log.read_bytes()
 row={"name":name,"command":command,"started_at":start,"completed_at":now(),"duration_seconds":round(time.monotonic()-tick,2),"exit_code":p.returncode,"log":str(log.relative_to(R)),"sha256":hashlib.sha256(raw).hexdigest()}
 print(json.dumps({**row,"tail":raw.decode(errors="replace")[-3500:]}),flush=True);return row
save()
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 futures=[pool.submit(execute,*item) for item in checks]
 for f in concurrent.futures.as_completed(futures): report["checks"].append(f.result());save()
report["completed_at"]=now();report["failed"]=sum(row["exit_code"]!=0 for row in report["checks"]);report["state"]="PASS" if not report["failed"] else "FAILED"
save(); print(json.dumps({"failed":report["failed"],"state":report["state"]}),flush=True)
raise SystemExit(bool(report["failed"]))
