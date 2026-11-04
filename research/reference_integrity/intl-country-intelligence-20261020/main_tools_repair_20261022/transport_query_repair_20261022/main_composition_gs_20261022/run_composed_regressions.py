"""Root verification of the exact integrated navigation repair; no installation or data acquisition."""
from pathlib import Path
from datetime import datetime, timezone
from hashlib import sha256
import argparse, concurrent.futures, json, os, re, shlex, shutil, subprocess, time
import yaml
ROOT=Path(__file__).resolve().parents[6]
OUT=Path(__file__).resolve().parent
PYTHON="/tmp/intl-country-cockpit-ci-20261021/bin/python"
DEPS="/Users/chriswong/Documents/Cluade/charting-app/.claude/worktrees/intl-parent-proof-20261022/terminal/node_modules"
FILES=("templates/shared_shell_bridge.js","site/shared_shell_bridge.js","templates/intl_country_cockpit.js","tests/js/shared_shell_bridge.test.cjs","tests/intl_country_cockpit_navigation.test.cjs",".github/ci/legacy-jobs.yml","templates/intl_workspace.js","site/intl_workspace.js","templates/intl_workspace_state.js","tests/intl_workspace_controller.test.cjs","tests/intl_workspace_state.test.cjs")
FILES += ("site/intl_workspace_state.js","templates/intl.html.j2","scripts/build_intl.py","tests/test_intl_build.py","tests/test_intl_gs_foundation.py","tests/intl_gs_foundation_browser.test.cjs","tests/intl_gs_fixture_site.py","tests/test_site_access_boundary.py","config/site_access.yml","app/deploy/Caddyfile","lib/intl_gs_display.py","lib/intl_gs_observations.py","lib/intl_surveillance_mount.py","templates/intl_workspace_surveillance.css","site/intl_workspace_surveillance.css","site/research_screener.html")

def now(): return datetime.now(timezone.utc).isoformat()
def digest(b): return sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--label",required=True,choices=("candidate",))
 args=p.parse_args()
 target=OUT/("regressions_"+args.label)
 target.mkdir(exist_ok=False)
 assert all((ROOT/name).is_file() for name in FILES)
 env=dict(os.environ)
 env["NODE_PATH"]=DEPS
 env["PLAYWRIGHT_CHROMIUM_CHANNEL"]="chrome"
 env["PATH"]=str(Path(PYTHON).parent)+os.pathsep+env["PATH"]
 env["PYTHONDONTWRITEBYTECODE"]="1"
 node=shutil.which("node",path=env["PATH"])
 assert node
 jobs=yaml.safe_load((ROOT/".github/ci/legacy-jobs.yml").read_text())["jobs"]
 job=jobs["international-workspace-browser"]
 cmd=next(x["run"] for x in job["steps"] if x.get("name")=="Actual DOM controller and page entry in Chromium")
 browser=shlex.split(cmd)
 assert browser[:2]==["node","--test"] and "tests/intl_country_cockpit_navigation.test.cjs" in browser
 browser[0]=node
 browser.insert(2,"--test-concurrency=3")
 browser.insert(2,"--test-reporter=tap")
 report={"schema":"intl.integrated_navigation_regressions.v1","started_at":now(),"subject":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),"driver_sha256":digest(Path(__file__).read_bytes()),"files":[{"path":name,"sha256":digest((ROOT/name).read_bytes())} for name in FILES],"environment":{"node":subprocess.check_output([node,"--version"],text=True).strip(),"python":subprocess.check_output([PYTHON,"--version"],text=True).strip(),"playwright":json.loads((Path(DEPS)/"playwright/package.json").read_text())["version"],"channel":"chrome","browser_concurrency":3},"checks":[],"source_acquisition":False,"production_mutation":False,"working_tree_candidate":True,"merge_parent":"2d33475adef502ab6b00b8003356c1b0ad1673c0"}
 specs=[
 ("shared_bridge_and_adapters",[node,"--test","--test-reporter=tap","tests/js/shared_shell_bridge.test.cjs","tests/js/shared_shell_navigation_adapters.test.cjs","tests/js/shared_shell_owner_adapters.test.cjs","tests/js/shared_shell_terminal_handoff.test.cjs"],180),
 ("international_browser",browser,900),
 ("workspace_state",[node,"--test","--test-reporter=tap","tests/intl_workspace_state.test.cjs"],180),
 ("shared_shell_injection",[PYTHON,"-m","pytest","tests/test_shared_shell_injection.py","-q"],180),
 ("template_site_sync",[PYTHON,"scripts/check_template_site_sync.py"],120),
 ("ci_manifest",[PYTHON,"scripts/run_ci_pack.py","--workflow",".github/ci/legacy-jobs.yml","--gate","code","--validate-only"],180),
 ("gs_build_and_screener",[PYTHON,"-m","pytest","tests/test_intl_build.py","tests/test_intl_gs_foundation.py","tests/test_research_screener.py","-q"],360),
 ("site_access_boundary",[PYTHON,"-m","pytest","tests/test_site_access_boundary.py","-q"],360)]
 def run(spec):
  name,command,limit=spec; start=now(); tick=time.monotonic(); log=target/(name+".log")
  try:
   with log.open("w") as output: result=subprocess.run(command,cwd=ROOT,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=limit)
   rc=result.returncode; error=None
  except subprocess.TimeoutExpired:
   rc=124; error="execution timeout"
  raw=log.read_bytes()
  row={"name":name,"command":command,"started_at":start,"completed_at":now(),"duration_seconds":round(time.monotonic()-tick,2),"exit_code":rc,"log":str(log.relative_to(ROOT)),"log_sha256":digest(raw),"error":error}
  counts={k:int(v) for k,v in re.findall(r"^# (tests|pass|fail|cancelled|skipped|todo) (\d+)$",raw.decode(errors="replace"),re.M)}
  if counts: row["counts"]=counts
  print(json.dumps(row),flush=True)
  return row
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  report["checks"]=list(pool.map(run,specs))
 report["completed_at"]=now()
 report["source_bindings_unchanged"]=all(digest((ROOT/row["path"]).read_bytes())==row["sha256"] for row in report["files"])
 report["pass"]=report["source_bindings_unchanged"] and all(x["exit_code"]==0 for x in report["checks"])
 (target/"receipt.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps({"pass":report["pass"],"receipt":str(target/"receipt.json")}),flush=True)
 return 0 if report["pass"] else 1
if __name__=="__main__": raise SystemExit(main())
