import pathlib,subprocess,json,hashlib,time
w=pathlib.Path("/home/ubuntu0/lanes/wt/d03-9495-ci-registration-c2-20261105")
head="9a8a28c557717441d2c5ef5529dad9fc7445e7b4"
prefix="/tmp/prophet-latest-main-frozen-9a8a28"
receipt=pathlib.Path(prefix+".verification.json");log=pathlib.Path(prefix+".verification.log")
assert not receipt.exists() and not log.exists(),"reconcile existing proof operation"
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=w,text=True).strip()==head
python="/home/ubuntu0/lanes/venv/bin/python"
base=w/"mockups/evidence/prophet-opportunity-workspace"
commands=[
[python,str(base/"full-page-20261103/tools/verify_native_pair.py"),"--workspace",str(w),"--source-head",head,"--output",prefix+".native-pair.json"],
[python,str(base/"main-integration-20261105/tools/verify_integrated_pair.py"),"--workspace",str(w),"--source-head",head,"--output",prefix+".complete-pair.json"],
[python,str(base/"full-page-20261103/tools/capture_native_prophet.py"),"--workspace",str(w),"--source-head",head,"--build-receipt",prefix+".receipt.json","--output",prefix+".native-browser"]
]
record={"source_head":head,"started_at":time.time(),"scope":"current pair integrity and anonymous offline16-cell capture","steps":[]}
def save():receipt.write_text(json.dumps(record,indent=2)+"\n")
save()
with log.open("x") as stream:
 for argv in commands:
  label=pathlib.Path(argv[1]).name
  print("START",label,flush=True);started=time.time()
  p=subprocess.run(argv,cwd=w,text=True,stdout=stream,stderr=subprocess.STDOUT)
  step={"script":label,"argv":argv,"exit_code":p.returncode,"elapsed_seconds":round(time.time()-started,3)}
  record["steps"].append(step);save()
  print("COMPLETE",label,"exit",p.returncode,"seconds",step["elapsed_seconds"],flush=True)
  assert p.returncode==0,step
for suffix in ("native-pair.json","complete-pair.json"):
 d=json.loads(pathlib.Path(prefix+"."+suffix).read_text())
 assert all(d["checks"].values()),suffix
b=json.loads(pathlib.Path(prefix+".native-browser/observations.json").read_text())
assert len(b["cells"])==16 and b.get("completed_at")
record["native_pair_checks"]=len(json.loads(pathlib.Path(prefix+".native-pair.json").read_text())["checks"])
record["complete_pair_checks"]=len(json.loads(pathlib.Path(prefix+".complete-pair.json").read_text())["checks"])
record["browser_cells"]=len(b["cells"]);record["original_pngs"]=len(list(pathlib.Path(prefix+".native-browser").glob("*.png")))
record["completed_at"]=time.time();save()
print(json.dumps({k:v for k,v in record.items() if k!="steps"},indent=2),flush=True)
