"""Verify the existing CI owner's scope, selection and raw test census."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
import json,os,subprocess,sys,time,yaml
ROOT=Path(__file__).resolve().parents[5];HERE=Path(__file__).resolve().parent;OUT=HERE/"ci_build_enrollment"
os.chdir(ROOT);sys.path.insert(0,str(ROOT))
from scripts import run_ci_pack as pack
from scripts.ci_scope_dependencies import suite_dependency_closure
start=time.monotonic();manifest=ROOT/".github/ci/legacy-jobs.yml"
jobs=pack.load_legacy_jobs(manifest,gate="code")
owner_id="international-workspace-foundation";owner=next(j for j in jobs if j.job_id==owner_id)
edit=json.loads((OUT/"edit_receipt.json").read_text())
workflow=yaml.safe_load((ROOT/".github/workflows/ci.yml").read_text())
events=workflow.get("on") or workflow.get(True);triggers=tuple(events["pull_request"]["paths"])
probes=[]
for path in edit["added_paths"]:
 match=pack._job_diff_match(owner,[path]);selected,reason=pack.select_jobs(jobs,[path])
 probes.append({"path":path,"match":match,"owner_selected":owner_id in {j.job_id for j in selected},"workflow_starts":pack._matches_any(triggers,path),"selection_reason":str(reason)})
closure=suite_dependency_closure("tests/test_intl_build.py",pytest_command="python -m pytest tests/test_intl_build.py -q")
findings=pack.curated_exclusive_closure_findings(manifest)
unrun=subprocess.run([sys.executable,"scripts/audit_unrun_tests.py","--json"],cwd=ROOT,text=True,capture_output=True)
(OUT/"unrun_census.json").write_text(unrun.stdout)
(OUT/"unrun_census.stderr.log").write_text(unrun.stderr)
census=json.loads(unrun.stdout)
mentioned='"tests/test_intl_build.py"' in json.dumps(census)
record={"schema":"intl.build_ci_enrollment_verification.v1","completed_at":datetime.now(timezone.utc).isoformat(),"elapsed_seconds":round(time.monotonic()-start,3),"subject_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),"manifest_sha256":sha256(manifest.read_bytes()).hexdigest(),"baseline_sha256":sha256((ROOT/"config/unrun_test_baseline.json").read_bytes()).hexdigest(),"owner_exclusive":owner.exclusive,"direct_manifest_validation":"PASS","probes":probes,"suite_static_dependencies":sorted(closure.files),"suite_static_ambiguities":list(map(str,closure.ambiguities)),"owner_closure_misses":findings.get(owner_id,[]),"other_owner_findings":{k:v for k,v in findings.items() if k!=owner_id},"unrun_cli_exit":unrun.returncode,"suite_in_raw_unrun_census":mentioned,"raw_unrun_census_shape":type(census).__name__,"unrun_census_sha256":sha256(unrun.stdout.encode()).hexdigest()}
record["passed"]=owner.exclusive and all(x["match"]==(x["path"],"declared") and x["owner_selected"] and x["workflow_starts"] for x in probes) and not record["owner_closure_misses"] and unrun.returncode==0 and not mentioned
(OUT/"verification.json").write_text(json.dumps(record,indent=2)+"\n")
print(json.dumps({k:v for k,v in record.items() if k not in ("suite_static_dependencies","probes")},indent=2))
raise SystemExit(0 if record["passed"] else 1)
