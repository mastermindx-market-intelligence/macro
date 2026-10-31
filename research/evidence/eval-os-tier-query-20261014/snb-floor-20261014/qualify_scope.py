from pathlib import Path
import datetime,hashlib,json,subprocess,sys,time
import pytest
root=Path.cwd();sys.path.insert(0,str(root))
from scripts import ci_scope_dependencies as d
from scripts import run_ci_pack as c
p=Path(__file__).parent
head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
assert not subprocess.check_output(["git","status","--porcelain"],text=True).strip()
assert subprocess.check_output(["git","show","-s","--format=%s",head],text=True).strip()=="test(eval-os): add bounded SNB floor and rate-unit diagnostic"
started=time.monotonic();inv=p/"tracked.bin";d.write_tracked_path_inventory(inv,head,root=root)
print(json.dumps({"phase":"started","source":head}),flush=True)
with d.planner_tracked_path_inventory(inv,head,root=root):
 rc=pytest.main(["-q","tests/test_ci_pack.py::test_the_curated_exclusive_set_is_actually_declared","tests/test_ci_pack.py::test_eval_os_acceptance_runs_on_ordinary_code_prs","tests/test_ci_pack.py::test_qledger_scope_keeps_runtime_phrase_book_without_unrelated_builder","--junitxml="+str(p/"scope-tests.xml")])
 print(json.dumps({"phase":"focused","exit":int(rc)}),flush=True)
 misses=c.curated_exclusive_closure_findings(root/".github/ci/legacy-jobs.yml")
 print(json.dumps({"phase":"closure","misses":misses}),flush=True)
 rows=c.packing_probe_measurements(root/".github/ci/legacy-jobs.yml",[("templates/index.html",135,5803),("scripts/build_free_content.py",134,5600),("engine/prophet/plan_book.py",129,5600)],max_packs=10)
 breaches=c.packing_probe_breaches(rows)
 assert subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()==head
 report={"schema":"eval_os.snb_scope_validation.v1","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"source":head,"inventory_sha256":hashlib.sha256(inv.read_bytes()).hexdigest(),"manifest_sha256":hashlib.sha256((root/".github/ci/legacy-jobs.yml").read_bytes()).hexdigest(),"focused_exit":int(rc),"closure_misses":misses,"strict_probe_rows":rows,"strict_probe_breaches":breaches,"elapsed_seconds":round(time.monotonic()-started,2),"scope":"Exact local candidate tracked source. No hosted CI, model observation, historical byte custody, merge or production claim. Prior qledger and runtime proof reused outside this changed case/admission scope."}
 (p/"scope-validation.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps({k:v for k,v in report.items() if k!="strict_probe_rows"}),flush=True)
raise SystemExit(int(rc) or int(bool(misses) or bool(breaches)))
