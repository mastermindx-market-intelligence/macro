"""Execute the foundation CI's declared dependencies and pytest steps in the clean Python 3.12 environment."""
from pathlib import Path
from datetime import datetime, timezone
import os, sys, json, yaml, shlex, subprocess, hashlib
w=Path(__file__).resolve().parents[3]
r=Path(__file__).resolve().parent
p=w/".github/ci/legacy-jobs.yml"
cfg=yaml.safe_load(p.read_text())
jobs=cfg.get("jobs",cfg)
found=[(key,job) for key,job in jobs.items() if isinstance(job,dict) and any(step.get("name")=="International country evidence, outlook and publication custody" for step in job.get("steps",[]))]
assert len(found)==1
key,job=found[0]
steps=[s for s in job["steps"] if "run" in s and s["run"].startswith("python -m pytest ")]
assert len(steps)==2
install=[s["run"] for s in job["steps"] if "run" in s and s["run"].startswith("pip install ")]
assert len(install)==1
env=os.environ.copy()
for k in ("PYTHONPATH","PYTHONHOME"): env.pop(k,None)
env["PATH"]=str(Path(sys.executable).parent)+os.pathsep+env["PATH"]
receipt={"started_at":datetime.now(timezone.utc).isoformat(),"python":sys.version,"executable":sys.executable,"job":key,"manifest_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"installation_contract":install,"environment":"fresh Python 3.12 venv without system packages; only declared dependencies installed; PYTHONPATH and PYTHONHOME removed","steps":[]}
args=shlex.split(install[0]); assert args[:2]==["pip","install"]
with (r/"fresh_ci_completed_install.log").open("w") as log:
 proc=subprocess.run([sys.executable,"-m","pip",*args[1:]],cwd=w,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=120)
assert proc.returncode==0
receipt["installed_packages"]=subprocess.check_output([sys.executable,"-m","pip","freeze"],cwd=w,env=env,text=True).splitlines()
for i,s in enumerate(steps):
 print(json.dumps({"phase":"ci-step-started","step":s["name"],"at":datetime.now(timezone.utc).isoformat()}),flush=True)
 args=shlex.split(s["run"]); assert args[:3]==["python","-m","pytest"]; args[0]=sys.executable
 log=r/f"fresh_ci_completed_step_{i+1}.log"; started=datetime.now(timezone.utc)
 with log.open("w") as f:
  proc=subprocess.run(args,cwd=w,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 ended=datetime.now(timezone.utc)
 item={"name":s["name"],"command":s["run"],"started_at":started.isoformat(),"finished_at":ended.isoformat(),"exit_code":proc.returncode,"log":str(log.relative_to(w)),"log_sha256":hashlib.sha256(log.read_bytes()).hexdigest(),"tail":log.read_text()[-1400:]}
 receipt["steps"].append(item)
 (r/"fresh_ci_completed_job.json").write_text(json.dumps(receipt,indent=2)+"\n")
 print(json.dumps({"phase":"ci-step-finished",**item}),flush=True)
 if proc.returncode: break
receipt["finished_at"]=datetime.now(timezone.utc).isoformat()
receipt["passed"]=len(receipt["steps"])==2 and all(s["exit_code"]==0 for s in receipt["steps"])
(r/"fresh_ci_completed_job.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps({"passed":receipt["passed"],"job":key,"steps":len(receipt["steps"]),"finished_at":receipt["finished_at"]}),flush=True)
raise SystemExit(0 if receipt["passed"] else 1)
