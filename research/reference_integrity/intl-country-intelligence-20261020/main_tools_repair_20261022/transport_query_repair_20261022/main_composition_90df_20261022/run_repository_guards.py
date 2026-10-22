"""Run the required repository guards against one exact committed repair source."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import argparse, concurrent.futures, json, os, subprocess, tempfile, time
ROOT=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
OUT=Path(__file__).resolve().parent
PYTHON="/tmp/intl-country-cockpit-ci-20261021/bin/python"
def digest(raw): return sha256(raw).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--label",required=True,choices=("publication",))
 args=p.parse_args()
 target=OUT/("guards_"+args.label)
 target.mkdir(exist_ok=False)
 head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
 main_sha=subprocess.check_output(["git","rev-parse","origin/main"],cwd=ROOT,text=True).strip()
 base=subprocess.check_output(["git","merge-base",head,main_sha],cwd=ROOT,text=True).strip()
 scratch=Path(tempfile.mkdtemp(prefix="intl-tools-guards-"+head[:12]+"-"))
 diff=scratch/"full-pr.diff"
 with diff.open("wb") as output:
  subprocess.run(["git","diff","--no-ext-diff","--binary",base,head],cwd=ROOT,stdout=output,check=True)
 paths_raw=subprocess.check_output(["git","diff","--name-only",base,head],cwd=ROOT)
 paths=target/"changed_paths.txt"; paths.write_bytes(paths_raw)
 env=dict(os.environ);env["PYTHONDONTWRITEBYTECODE"]="1"
 env["PATH"]=str(Path(PYTHON).parent)+os.pathsep+env["PATH"]
 report={"schema":"intl.repair_repository_guards.v1","started_at":now(),"source_commit":head,"observed_main":main_sha,"merge_base":base,"driver_sha256":digest(Path(__file__).read_bytes()),"diff":{"path":str(diff),"bytes":diff.stat().st_size,"sha256":digest(diff.read_bytes())},"changed_path_count":len(paths_raw.splitlines()),"checks":[]}
 specs=[
 ("frozen_reference_evaluation",[PYTHON,"scripts/check_reference_integrity.py","--evaluate","intl-country-intelligence-20261020"]),
 ("reference_integrity_registry",[PYTHON,"scripts/check_reference_integrity.py"]),
 ("runtime_style_injection",[PYTHON,"scripts/check_runtime_style_injection.py"]),
 ("receipt_closure",[PYTHON,"scripts/check_p0b_receipt_closure.py","--diff-file",str(paths)]),
 ("visual_evidence",[PYTHON,"scripts/check_ui_visual_evidence.py","--diff-file",str(diff)]),
 ("design_system",[PYTHON,"scripts/check_design_system.py","--mode","enforce-added","--diff-file",str(diff)]),
 ("agentos",[PYTHON,"scripts/agentos.py","validate"])]
 def run(spec):
  name,command=spec;start=now();tick=time.monotonic();log=target/(name+".log")
  try:
   with log.open("w") as output:
    r=subprocess.run(command,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=300)
   rc=r.returncode;error=None
  except subprocess.TimeoutExpired:
   rc=124;error="execution timeout"
  row={"name":name,"command":command,"started_at":start,"completed_at":now(),"duration_seconds":round(time.monotonic()-tick,2),"exit_code":rc,"log":str(log.relative_to(ROOT)),"log_sha256":digest(log.read_bytes()),"error":error}
  print(json.dumps(row),flush=True)
  return row
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  report["checks"]=list(pool.map(run,specs))
 report["completed_at"]=now()
 report["head_unchanged"]=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==head
 report["pass"]=report["head_unchanged"] and all(x["exit_code"]==0 for x in report["checks"])
 (target/"receipt.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps({"pass":report["pass"],"receipt":str(target/"receipt.json")}),flush=True)
 return 0 if report["pass"] else 1
if __name__=="__main__":raise SystemExit(main())