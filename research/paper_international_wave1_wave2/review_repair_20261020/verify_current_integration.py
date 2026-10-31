#!/usr/bin/env python3
"""Bounded proof for the original International/main conflict composition."""
from pathlib import Path
from datetime import datetime, timezone
import copy, hashlib, json, os, re, shlex, subprocess, sys
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
import yaml
from scripts.run_ci_pack import load_legacy_jobs, curated_exclusive_closure_findings
from scripts.audit_unrun_tests import gated_unrun_suites
BASE = "422e121246f956834085853a49dfc6c2250d3dab"
PARENT = "1a292672de4bb3f14b00c88e4af1f493b854a364"
ASSETS = {"/intl_workspace.css", "/intl_workspace_macro.css", "/intl_workspace_risk.css",
          "/intl_workspace_history.css", "/intl_workspace_state.js", "/intl_library_search.js",
          "/intl_workspace_scenario.js", "/intl_workspace.js", "/intl_workspace_entry.js"}
def now(): return datetime.now(timezone.utc).isoformat()
def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True, timeout=15).stdout
def fingerprint(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
assert git("rev-parse", "HEAD").strip() == PARENT
assert git("rev-parse", "MERGE_HEAD").strip() == BASE
inputs = [".github/ci/legacy-jobs.yml", "scripts/run_ci_pack.py",
          "scripts/ci_scope_dependencies.py", "scripts/audit_unrun_tests.py",
          "app/deploy/Caddyfile", "config/site_access.yml", "tests/test_site_access_boundary.py"]
before = {p:fingerprint(p) for p in inputs}
result = {"schema":"mastermind.intl_current_integration_proof.v1", "started_at":now(),
          "source_parent":PARENT, "main_parent":BASE, "inputs":before}
main_caddy = git("show", BASE+":app/deploy/Caddyfile")
ours_caddy = git("show", PARENT+":app/deploy/Caddyfile")
candidate = (ROOT/"app/deploy/Caddyfile").read_text()
def matcher_paths(text, name):
    blocks = list(re.finditer(r"@"+name+r"\s*\{(.*?)^\s*\}", text, flags=re.S|re.M))
    directive = "not path" if name.startswith("reg_asset") else "path"
    return [{token for line in block.group(1).splitlines()
             if line.lstrip().startswith(directive+" ")
             for token in shlex.split(line.lstrip().removeprefix(directive).strip())}
            for block in blocks]
matcher_checks=[]
for name in ("reg_asset", "reg_asset_err", "public_static", "public_versioned"):
    base_sets, ours_sets, current_sets = [matcher_paths(t,name) for t in (main_caddy,ours_caddy,candidate)]
    assert len(base_sets) == len(ours_sets) == len(current_sets) and base_sets
    for index,(a,b,c) in enumerate(zip(base_sets,ours_sets,current_sets)):
        intended = ASSETS.intersection(b)
        assert not intended or intended == ASSETS, (name,index,"partial original asset set")
        assert ASSETS.isdisjoint(a) and c == a|intended, (name,index)
        matcher_checks.append({"matcher":name,"occurrence":index,"exact_international_additions":len(intended)})
result["source_matcher_checks"] = matcher_checks
main_policy = yaml.safe_load(git("show",BASE+":config/site_access.yml"))
policy = yaml.safe_load((ROOT/"config/site_access.yml").read_text())
stripped = copy.deepcopy(policy)
assert ASSETS <= set(policy["public"]["exact"]) and ASSETS.isdisjoint(main_policy["public"]["exact"])
stripped["public"]["exact"] = [p for p in stripped["public"]["exact"] if p not in ASSETS]
assert stripped == main_policy
result["policy_only_adds_exact_nine_presentation_assets"] = True
caddy_dir=HERE/"integration_caddy"; caddy_dir.mkdir(exist_ok=True)
input_path=caddy_dir/"Caddyfile.input"
environment={"PATH":"/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin","HOME":str(Path.home()),"LANG":"C"}
adapted=[]
for label,source in [("main",main_caddy),("candidate",candidate)]:
    input_path.write_text(source)
    call=subprocess.run(["/opt/homebrew/bin/caddy","adapt","--adapter","caddyfile",
                         "--config",str(input_path)],cwd=ROOT,env=environment,
                        capture_output=True,timeout=30)
    (caddy_dir/(label+".stdout.json")).write_bytes(call.stdout)
    (caddy_dir/(label+".stderr")).write_bytes(call.stderr)
    assert call.returncode==0, (label,call.returncode)
    adapted.append(json.loads(call.stdout))
changed=[]
def strip_assets(value,path=()):
    if isinstance(value,dict): return {k:strip_assets(v,path+(k,)) for k,v in value.items()}
    if isinstance(value,list):
        if value and all(isinstance(v,str) for v in value) and ASSETS.intersection(value):
            assert ASSETS <= set(value)
            changed.append({"path":list(path),"assets":9})
            return [v for v in value if v not in ASSETS]
        return [strip_assets(v,path+(str(i),)) for i,v in enumerate(value)]
    return value
assert strip_assets(adapted[1]) == adapted[0]
assert len(changed)==8, len(changed)
result["caddy_adaptation"]={"both_exit_zero":True,"changed_path_lists":changed,
                            "other_adapted_differences":0,"runtime_started_or_reloaded":False}
print(json.dumps({"phase":"access-composition-proved","at":now(),"source_matchers":len(matcher_checks),
                  "adapted_path_lists":len(changed)}),flush=True)
manifest=ROOT/".github/ci/legacy-jobs.yml"
jobs=load_legacy_jobs(manifest)
base_manifest=HERE/"main_legacy_jobs.yml"
base_manifest.write_text(git("show",BASE+":.github/ci/legacy-jobs.yml"))
main_jobs=load_legacy_jobs(base_manifest)
current={j.job_id:j for j in jobs}
missing_main_paths={j.job_id:sorted(set(j.paths)-set(current[j.job_id].paths))
                    for j in main_jobs if j.job_id in current and set(j.paths)-set(current[j.job_id].paths)}
missing_main_jobs=[j.job_id for j in main_jobs if j.job_id not in current]
assert not missing_main_jobs and not missing_main_paths,(missing_main_jobs,missing_main_paths)
engine_jobs=[j for j in jobs if "engine/intl_run.py" in j.paths]
assert engine_jobs and all("lib/intl_currency_observation.py" in j.paths for j in engine_jobs)
foundation=current["international-workspace-foundation"]
commands="\n".join(str(s.get("run","")) for s in foundation.definition.get("steps",[]) if isinstance(s,dict))
test="tests/test_intl_currency_observation.py"; fixture="tests/fixtures/intl_currency_observations_20261020.json"
assert test in foundation.paths and fixture in foundation.paths and test in commands
result["main_ci_paths_preserved"]=True
result["currency_engine_scopes"]=[j.job_id for j in engine_jobs]
print(json.dumps({"phase":"canonical-dependency-inference-started","at":now()}),flush=True)
result["import_closure_findings"]={k:list(v) for k,v in curated_exclusive_closure_findings(manifest).items()}
result["unwired_suites"]=sorted(gated_unrun_suites())
result["inputs_unchanged"]=before=={p:fingerprint(p) for p in inputs}
result["finished_at"]=now()
result["passed"]=not result["import_closure_findings"] and not result["unwired_suites"] and result["inputs_unchanged"]
(HERE/"current_integration_proof.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"passed":result["passed"],"engine_jobs":len(engine_jobs),
                  "uncovered_jobs":len(result["import_closure_findings"]),
                  "unwired_suites":len(result["unwired_suites"]),"finished_at":result["finished_at"]}),flush=True)
raise SystemExit(0 if result["passed"] else 1)
