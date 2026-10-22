"""Discriminating controls using exact prior source bytes; never rewrites the working source."""
from pathlib import Path
from hashlib import sha256
import concurrent.futures,json,os,re,subprocess,time
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018"); Q=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022"); T=Path("/tmp/intl-resume-main-20261022T1252")
env=dict(os.environ)
env["NODE_PATH"]="/tmp/intl-browser-node-20261021/node_modules"
env["PLAYWRIGHT_CHROMIUM_CHANNEL"]="chrome"
env["PATH"]="/tmp/intl-country-cockpit-ci-20261021/bin:/opt/homebrew/bin:"+env["PATH"]
env["PYTHONDONTWRITEBYTECODE"]="1"
expected={"base":{"shared_shell_bridge.js":"31b150d8335f7abafa6210bcaf26d98a9e7e2251e34a09ce69f4524c59720e30","intl_workspace.js":"d910e296a5d6ea9b58f79ec59ab112b79a58cad21dff96f0a4831204ab06b296"},"r1":{"shared_shell_bridge.js":"24d7bb10d1c59a2d051b3279c436c3581ced7dfe53da3872d1452a1cde2019bf","intl_workspace.js":"f09421d4dad8dcdb86e5591d63e53836347e54afdcc2a330defa79eb672f96c5"}}
for stage,files in expected.items():
 mapping={}
 for name,digest in files.items():
  target=T/"query_negative_controls"/stage/name
  assert sha256(target.read_bytes()).hexdigest()==digest
  mapping[str(R/"templates"/name)]=str(target)
 preloader=T/("query_"+stage+"_preload.cjs")
 preloader.write_text("const fs=require('node:fs'),path=require('node:path');\nconst original=fs.readFileSync;\nconst mapping="+json.dumps(mapping)+";\nfs.readFileSync=function(file,...args){const key=typeof file==='string'?path.resolve(file):null;return original.call(this,key&&mapping[key]?mapping[key]:file,...args);};\n")
paths=["templates/shared_shell_bridge.js","site/shared_shell_bridge.js","templates/intl_workspace.js","site/intl_workspace.js","templates/intl_workspace_state.js","tests/js/shared_shell_bridge.test.cjs","tests/intl_workspace_controller.test.cjs","tests/intl_workspace_state.test.cjs","tests/intl_country_cockpit_navigation.test.cjs"]
hashes={f:sha256((R/f).read_bytes()).hexdigest() for f in paths}
specs=[
("candidate_corrected_native_and_standalone",None,"^query source: (real native history|standalone search)",0),
("base_semantic_negative","base","^query source: (real bridge and entry|real native history)",1),
("r1_consumer_negative","r1","^query source: (unavailable mount rolls back (installed-deleted|installed-null|installed-foreign|occupied-undefined|occupied-null|foreign)$|actual bridge cleanup|native popstate refusal.*(provider-getter|reader-getter)$|refused native popstate|standalone search)",1)]
def run(spec):
 name,stage,pattern,expected_exit=spec
 cmd=["/opt/homebrew/bin/node"]
 if stage:cmd+=["--require",str(T/("query_"+stage+"_preload.cjs"))]
 cmd+=["--test","--test-reporter=tap","--test-name-pattern="+pattern,"tests/intl_workspace_controller.test.cjs"]
 log=Q/(name+".log");start=time.monotonic()
 with log.open("w") as output:result=subprocess.run(cmd,cwd=R,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=300)
 text=log.read_text();counts={k:int(v) for k,v in re.findall(r"^# (tests|pass|fail|cancelled|skipped|todo) (\d+)$",text,re.M)}
 row={"name":name,"source_variant":stage or "corrected candidate","command":cmd,"exit_code":result.returncode,"expected_exit":expected_exit,"expected_behavior_observed":result.returncode==expected_exit and counts.get("skipped")==0,"counts":counts,"seconds":round(time.monotonic()-start,2),"log":str(log.relative_to(R)),"log_sha256":sha256(log.read_bytes()).hexdigest()}
 if stage:row["source_sha256"]=expected[stage]
 print(json.dumps(row),flush=True);return row
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,specs))
assert hashes=={f:sha256((R/f).read_bytes()).hexdigest() for f in paths}
report={"schema":"intl.original_integrator_query_negative_controls.v1","source_files":hashes,"controls":results,"source_unchanged_during_verification":True,"all_expected_results":all(r["expected_behavior_observed"] for r in results)}
(Q/"query_negative_control_receipt.json").write_text(json.dumps(report,indent=2)+"\n")
raise SystemExit(0 if report["all_expected_results"] else 1)
