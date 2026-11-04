"""Observe existing isolated build regressions and their repository read closure."""
from pathlib import Path
from hashlib import sha256
from datetime import datetime,timezone
import fnmatch,json,os,sys,time
ROOT=Path(__file__).resolve().parents[5]
HERE=Path(__file__).resolve().parent
OUT=HERE/"ci_build_enrollment"
OUT.mkdir(exist_ok=True)
assert not (OUT/"receipt.json").exists()
os.chdir(ROOT)
sys.path.insert(0,str(ROOT))
import yaml
manifest=ROOT/".github/ci/legacy-jobs.yml"
body=yaml.safe_load(manifest.read_text())
job=body["jobs"]["international-workspace-foundation"] if "jobs" in body else body["international-workspace-foundation"]
seen=set()
def observe(event,args):
 if event=="open" and args and isinstance(args[0],(str,bytes,os.PathLike)):
  try:
   p=Path(os.fsdecode(args[0])).resolve()
   if p.is_relative_to(ROOT):
    s=p.relative_to(ROOT).as_posix()
    if "/__pycache__/" in s and s.endswith(".pyc"):
     parent,name=s.rsplit("/__pycache__/",1);s=parent+"/"+name.split(".cpython-")[0]+".py"
    if not s.startswith(("research/","data/","site/",".git/",".pytest_cache/")):seen.add(s)
  except (OSError,ValueError,RuntimeError):pass
sys.addaudithook(observe)
start=time.monotonic()
import pytest
rc=pytest.main(["tests/test_intl_build.py","-q","--disable-warnings"])
paths=job.get("paths",[]) or job.get("x-paths",[])
record={"schema":"intl.build_ci_enrollment_probe.v1","completed_at":datetime.now(timezone.utc).isoformat(),"elapsed_seconds":round(time.monotonic()-start,3),"exit_code":rc,"subject_head":os.popen("git rev-parse HEAD").read().strip(),"test":"tests/test_intl_build.py","test_sha256":sha256((ROOT/"tests/test_intl_build.py").read_bytes()).hexdigest(),"manifest_sha256":sha256(manifest.read_bytes()).hexdigest(),"job_keys":list(job),"declared_paths":paths,"observed_repository_reads":sorted(seen),"uncovered_reads":[s for s in sorted(seen) if not any(fnmatch.fnmatchcase(s,p) for p in paths)],"boundary":"existing synthetic/temporary-store tests only; no source mutation; dynamic read closure supplements static import/read review"}
(OUT/"receipt.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps({k:v for k,v in record.items() if k not in ("declared_paths","observed_repository_reads")}))
raise SystemExit(rc)
