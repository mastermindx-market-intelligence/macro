"""Run and close only this invocation's local parent/child proof processes."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import argparse,json,re,signal,socket,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
def now():return datetime.now(timezone.utc).isoformat()
def ready(port):
 try:
  with socket.create_connection(("127.0.0.1",port),timeout=.2):return True
 except OSError:return False
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--artifact",required=True);p.add_argument("--output",required=True)
 p.add_argument("--source-sha",required=True);p.add_argument("--build-receipt",required=True)
 p.add_argument("--phase",choices=("baseline","candidate"),required=True)
 p.add_argument("--matrix",choices=("smoke","contract","full"),required=True)
 a=p.parse_args()
 output=Path(a.output).resolve()
 assert output.is_relative_to(HERE) and not output.exists()
 output.mkdir()
 raw=(HERE/"verify_actual_parent.cjs").read_bytes()
 version=re.search(rb"intl.actual_parent_acceptance.v(\d+)",raw).group(1).decode()
 driver=output/("verify_actual_parent_v"+version+".cjs");driver.write_bytes(raw)
 command=["node",str(driver),"--artifact",a.artifact,"--output",str(output),"--phase",a.phase,"--matrix",a.matrix,"--source-sha",a.source_sha,"--runtime",str(output/"runtime.json"),"--build-receipt",a.build_receipt]
 record={"command":command,"started_at":now(),"driver_sha256":sha256(raw).hexdigest(),"coordinator_sha256":sha256(Path(__file__).read_bytes()).hexdigest()}
 with (output/"supervisor.log").open("w") as serverlog:
  server=subprocess.Popen([sys.executable,str(HERE/"serve_actual_parent.py"),"--artifact",a.artifact,"--output",str(output),"--maximum-seconds","2200"],stdout=serverlog,stderr=subprocess.STDOUT)
  record["owned_supervisor_pid"]=server.pid
  print(json.dumps({"state":"OWNED_PROOF_STARTED","supervisor_pid":server.pid,"output":str(output)}),flush=True)
  try:
   deadline=time.monotonic()+90
   while not ((output/"runtime.json").exists() and ready(3100) and ready(3102)):
    if server.poll() is not None:raise RuntimeError("Owned server exited before readiness")
    if time.monotonic()>deadline:raise RuntimeError("Owned servers did not become ready")
    time.sleep(.2)
   with (output/"driver.log").open("w") as log:
    result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=2100)
   record["exit_code"]=result.returncode
  except BaseException as error:
   record["error"]=str(error);record["exit_code"]=124 if isinstance(error,subprocess.TimeoutExpired) else 2
  finally:
   if server.poll() is None:server.send_signal(signal.SIGTERM)
   try:server.wait(timeout=30)
   except subprocess.TimeoutExpired:record["shutdown_error"]="Owned supervisor did not finish; reconcile its process before another proof"
   record["finished_at"]=now()
   (output/"driver_execution.json").write_text(json.dumps(record,indent=2)+"\n")
 if (output/"observation.json").exists():
  report=json.loads((output/"observation.json").read_text())
  print(json.dumps({"driver_exit":record["exit_code"],"passed":sum(bool(c["passed"]) for c in report["cases"]),"failed":[{"scope":c["scope"],"id":c["id"]} for c in report["cases"] if not c["passed"]]}),flush=True)
 else:print(json.dumps(record),flush=True)
 return record["exit_code"]
if __name__=="__main__":raise SystemExit(main())
