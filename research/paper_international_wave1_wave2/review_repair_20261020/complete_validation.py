"""Bind repaired source and run the required presentation/record gates before the merge commit."""
from pathlib import Path
from datetime import datetime,timezone
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
import json,subprocess
W=Path(__file__).resolve().parents[3]
R=Path(__file__).resolve().parent
PY="/tmp/intl-country-cockpit-testenv-20261018/bin/python"
SOURCE="1a292672de4bb3f14b00c88e4af1f493b854a364"
MAIN="422e121246f956834085853a49dfc6c2250d3dab"
def git(*args): return subprocess.check_output(["git",*args],cwd=W,text=True).strip()
def digest(p): return sha256(p.read_bytes()).hexdigest()
def write(name,value): (R/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")
assert git("rev-parse","HEAD")==SOURCE and git("rev-parse","MERGE_HEAD")==MAIN
assert not git("ls-files","-u")
source=[p for p in git("diff","--name-only",MAIN).splitlines() if p.startswith((".github/","app/","collectors/","config/","engine/","lib/","scripts/","templates/","tests/","site/"))]
untracked=git("ls-files","--others","--exclude-standard").splitlines()
assert all(p.startswith(("research/paper_international_wave1_wave2/review_repair_20261020/","mockups/evidence/intl-review-repair-20261020/")) for p in untracked)
proof=json.loads((R/"current_integration_proof.json").read_text())
assert proof["passed"] and proof["inputs_unchanged"]
for p,h in proof["inputs"].items(): assert digest(W/p)==h,p
ci=json.loads((R/"fresh_ci_completed_job.json").read_text())
assert ci["passed"] and ci["manifest_sha256"]==digest(W/".github/ci/legacy-jobs.yml")
assert [s["exit_code"] for s in ci["steps"]]==[0,0]
assert json.loads((R/"final_build_access.json").read_text())["exit_code"]==0
browser=json.loads((R/"browser_verification.json").read_text())
assert browser["country_checks"]==browser["passed"]==84 and browser["ageing_passed"]==8 and not browser["page_errors"]
assert all(x["passed"] for x in browser["focus_checks"])
assert browser["html_sha256"]==digest(R/"preview/intl_integrated_preview.html")
assert json.loads((R/"history_legend_after.json").read_text())["passed"]==12
assert json.loads((R/"degraded_states/manifest.json").read_text())["passed"]
write("SOURCE_BINDING.json",{"schema":"mastermind.intl_repaired_source_binding.v1","recorded_at":datetime.now(timezone.utc).isoformat(),"source_parent":SOURCE,"main_parent":MAIN,"source":[{"path":p,"bytes":(W/p).stat().st_size,"sha256":digest(W/p)} for p in source],"scope":"All candidate product/source/test/site paths differing from the composed main; immutable SHA is supplied by the actual subsequent commit and reviewer binding."})
evidence=["fresh_ci_completed_job.json","final_build_access.json","browser_verification.json","history_legend_before.json","history_legend_after.json","degraded_states/manifest.json","current_integration_proof.json","bis_policy_acquisition.json","bis_policy_admission.json","preview/manifest.json","INDEPENDENT_REVIEW_FINDINGS.json"]
write("VALIDATION_BINDING.json",{"schema":"mastermind.intl_repaired_validation_binding.v1","source_binding_sha256":digest(R/"SOURCE_BINDING.json"),"source_parent":SOURCE,"main_parent":MAIN,"evidence":{p:digest(R/p) for p in evidence},"canonical_manifest_sha256":digest(W/"mockups/evidence/intl-review-repair-20261020/manifest.json"),"test_results":{"fresh_declared_foundation":[1363,369],"final_build_access":40},"browser_results":{"country_views":84,"focus_checks":12,"ageing_checks":8,"targeted_history_legend_accessible_names":12,"degraded_visual_states":6},"independent_review":"Concrete working-source findings closed by the separate data/logic and product reviewers; immutable binding follows.","served_adoption":False})
owned=git("diff","--name-only").splitlines()+["research/paper_international_wave1_wave2/review_repair_20261020","mockups/evidence/intl-review-repair-20261020"]
subprocess.run(["git","add","--",*owned],cwd=W,check=True)
diff=Path("/tmp/intl-review-repair-final-20261020.diff")
with diff.open("wb") as f: subprocess.run(["git","diff","--cached","--unified=0",MAIN],cwd=W,stdout=f,check=True)
whitespace=subprocess.run(["git","diff","--cached","--check",MAIN,"--",*source,"agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md"],cwd=W,capture_output=True,text=True)
write("whitespace_scope.json",{"exit_code":whitespace.returncode,"scope":source+["agentos/workstreams/WS-PAPER-INTERNATIONAL-WAVES.md"],"output":whitespace.stdout+whitespace.stderr,"retained_raw_evidence_not_normalized":True})
assert whitespace.returncode==0
commands={
 "design_system":[PY,"scripts/check_design_system.py","--mode","enforce-added","--diff-file",str(diff)],
 "runtime_style":[PY,"scripts/check_runtime_style_injection.py"],
 "visual_evidence":[PY,"scripts/check_ui_visual_evidence.py","--diff-file",str(diff)],
 "agentos":[PY,"scripts/agentos.py","validate"],
 "template_site_sync":[PY,"scripts/check_template_site_sync.py"],
}
started=datetime.now(timezone.utc).isoformat()
def run(item):
 key,cmd=item
 with (R/(key+".log")).open("w") as f: p=subprocess.run(cmd,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 return key,{"command":cmd,"exit_code":p.returncode,"log":key+".log","log_sha256":digest(R/(key+".log")),"tail":(R/(key+".log")).read_text()[-1800:]}
with ThreadPoolExecutor(max_workers=5) as pool: results=dict(pool.map(run,commands.items()))
write("design_and_record_guards.json",{"started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),"source_parent":SOURCE,"main_parent":MAIN,"diff_sha256":digest(diff),"results":results,"passed":all(x["exit_code"]==0 for x in results.values())})
print(json.dumps({"source_paths":len(source),"untracked_reviewed":len(untracked),"guards":results,"passed":all(x["exit_code"]==0 for x in results.values())},ensure_ascii=False),flush=True)
raise SystemExit(0 if all(x["exit_code"]==0 for x in results.values()) else 1)
