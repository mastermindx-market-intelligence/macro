"""Resolve the four reviewed conflicts and verify both parents' CI contracts."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,re,subprocess,yaml
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
C=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_90df_20261022")
OURS="a2997f8e9583f09f08acc0c5617c2c75baa87da8"
MAIN="90df0e302637ade26b894aee46141b6a1813a630"
BASE="25051144947f027c698cd1ce10e3c8824ee6ade9"
def git(*args):return subprocess.check_output(["git",*args],cwd=R)
def sha(raw):return hashlib.sha256(raw).hexdigest()
assert git("rev-parse","HEAD").decode().strip()==OURS
assert git("rev-parse","MERGE_HEAD").decode().strip()==MAIN
ci=".github/ci/legacy-jobs.yml"
bj,oj,mj=[yaml.safe_load(git("show",r+":"+ci))["jobs"] for r in [BASE,OURS,MAIN]]
cj=yaml.safe_load((R/ci).read_text())["jobs"]
assert set(cj)==set(oj)|set(mj)
checks=[]; overlaps=[]
for name in sorted(cj):
 b,o,m,c=[j.get(name) for j in [bj,oj,mj,cj]]
 if o==b:expected=m;reason="protected_main"
 elif m==b or o==m:expected=o;reason="international"
 else:
  assert name in {"intelligence-registry","nw-lobe-unfreeze","unrun-picks-boards","washout-turn-organ"}
  bp,op,mp,cp=[set(x.get("paths",[])) for x in [b,o,m,c]]
  non=lambda x:{k:v for k,v in x.items() if k!="paths"}
  assert non(o)==non(b) and non(c)==non(m),name
  assert cp==(mp-(bp-op))|(op-bp),name
  overlaps.append({"job":name,"local_added_paths":sorted(op-bp),"main_added_paths":sorted(mp-bp),"preserved_main_commands":True,"complete_path_union":True})
  reason="verified_path_union_and_main_commands";expected=c
 assert c==expected,name
 if o!=b or m!=b:checks.append({"job":name,"source":reason})
foundation=cj["international-workspace-foundation"]
assert foundation==oj["international-workspace-foundation"]
assert len(foundation["paths"])==375
assert any(s.get("run")=="python -m pytest tests/test_intl_build.py -q" for s in foundation["steps"])
(C/"CI_OVERLAP_DIAGNOSTIC.json").write_text(json.dumps({"initial_guard":"stopped_before_resolution_on_any_both_parent_job_change","initial_process":11323,"initial_exit":1,"outcome":"No conflict resolution or product writes occurred; preflight receipts only","observed_jobs":[x["job"] for x in overlaps],"subsequent_ruling":"All four changes are exact path unions; local non-path fields equal base and merged non-path fields equal main. No CI source edits required."},indent=2)+"\n")
prefix="mockups/evidence/prophet-p0b-zero-fouc/"
names=["manifest.json","mobile-layout-canada.json","mobile-layout.json","rendered-fixture.json"]
lineage=[]
for label,ref in [("previous_published",OURS),("incoming_main",MAIN)]:
 d=C/label;d.mkdir()
 for name in names:
  raw=git("show",ref+":"+prefix+name);(d/name).write_bytes(raw)
  lineage.append({"parent":ref,"path":prefix+name,"sha256":sha(raw),"blob":git("rev-parse",ref+":"+prefix+name).decode().strip(),"archive":str((d/name).relative_to(R))})
 shots={}
 for name in ["mobile-layout.json","mobile-layout-canada.json"]:
  rec=json.loads((d/name).read_text())
  for row in rec["owner_projection_matrix"]["cases"]:
   if row.get("screenshot"):
    shot=row["screenshot"];raw=git("show",ref+":"+shot["path"]);assert sha(raw)==shot["sha256"]
    shots[shot["path"]]={"sha256":sha(raw),"blob":git("rev-parse",ref+":"+shot["path"]).decode().strip()}
 (d/"screenshot_recovery.json").write_text(json.dumps({"parent":ref,"screenshots":shots},indent=2)+"\n")
resolved=[prefix+n for n in names[:3]]+["site/research_screener.html"]
assert set(git("diff","--name-only","--diff-filter=U").decode().splitlines())==set(resolved)
for path in resolved:(R/path).write_bytes(git("show",MAIN+":"+path))
assert (R/"templates/theme.css").read_bytes()==(R/"site/theme.css").read_bytes()
theme=sha((R/"site/theme.css").read_bytes())
assert theme=="50eb4991c6f9a2b00ad3accb33fa85cebc3dc0c7ceac2ab093d9e2e2f3045e51"
unchanged=["templates/intl_country_cockpit.js","templates/intl_country_cockpit.css","templates/intl_country_cockpit.html.j2","templates/shared_shell_bridge.js","site/shared_shell_bridge.js","templates/intl_workspace.js","site/intl_workspace.js","templates/intl_workspace_state.js","site/intl_workspace_state.js","tests/js/shared_shell_bridge.test.cjs","tests/intl_workspace_controller.test.cjs","tests/intl_workspace_state.test.cjs"]
for path in unchanged:assert (R/path).read_bytes()==git("show",OURS+":"+path),path
report={"schema":"intl.main_composition.v2","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"parents":[OURS,MAIN],"base":BASE,"ci_jobs":len(cj),"changed_job_sources":checks,"ci_overlap_checks":overlaps,"foundation_job_identical_to_reviewed_ci_commit":True,"resolved_paths":resolved,"resolution":"exact_main_historical_staging_requires_actual_P0B_recapture","theme_sha256":theme,"unchanged_product_inputs":unchanged,"parent_evidence":lineage,"production_acceptance":False}
(C/"composition.json").write_text(json.dumps(report,indent=2)+"\n")
subprocess.run(["git","add","--",*resolved,str(C.relative_to(R))],cwd=R,check=True)
assert not git("diff","--name-only","--diff-filter=U").strip()
def tree(ref):
 rows={}
 for line in git("ls-tree","-rz",ref).split(b"\0"):
  if line:
   meta,name=line.split(b"\t",1);rows[name.decode()]=meta.decode().split()[2]
 return rows
parents={ref:tree(ref) for ref in [OURS,MAIN]};index={}
for line in git("ls-files","--stage","-z").split(b"\0"):
 if line:
  meta,name=line.split(b"\t",1);index[name.decode()]=meta.decode().split()[1]
whitespace=[]
for label,ref in [("previous_published",OURS),("incoming_main",MAIN)]:
 result=subprocess.run(["git","diff","--cached","--check",ref],cwd=R,capture_output=True)
 raw=result.stdout+result.stderr;counts=collections.Counter()
 for line in result.stdout.decode().splitlines():
  match=re.match(r"^(.+):[0-9]+: (trailing whitespace|new blank line at EOF|space before tab in indent)\.",line)
  if match:counts[match.group(1)]+=1
 rows=[{"path":path,"count":count,"byte_identical_parents":[r for r,t in parents.items() if t.get(path)==index.get(path)]} for path,count in sorted(counts.items())]
 assert result.returncode in (0,2) and (not result.returncode or rows)
 assert all(row["byte_identical_parents"] for row in rows),[row for row in rows if not row["byte_identical_parents"]]
 log=C/(label+"_whitespace.log.gz");log.write_bytes(gzip.compress(raw,mtime=0))
 whitespace.append({"parent":ref,"exit_code":result.returncode,"warnings":sum(counts.values()),"paths":rows,"log_sha256":sha(log.read_bytes()),"uncompressed_sha256":sha(raw)})
(C/"whitespace_classification.json").write_text(json.dumps({"pass":True,"checks":whitespace},indent=2)+"\n")
result=subprocess.run(["/tmp/intl-country-cockpit-ci-20261021/bin/python","scripts/run_ci_pack.py","--workflow",ci,"--validate-only"],cwd=R,capture_output=True)
(C/"ci_manifest.log").write_bytes(result.stdout+result.stderr);assert result.returncode==0
subprocess.run(["git","add","--",str(C.relative_to(R))],cwd=R,check=True)
print(json.dumps({"conflicts_resolved":4,"ci_jobs":len(cj),"ci_overlap_checks":len(overlaps),"theme_sha256":theme,"ready_for_normal_merge_commit":True}),flush=True)
result=subprocess.run(["git","-c","core.editor=true","merge","--continue"],cwd=R,capture_output=True,text=True)
Path("/tmp/intl-query-normal-merge-commit-20261022.log").write_text(result.stdout+result.stderr)
print(json.dumps({"merge_continue_exit":result.returncode,"output_tail":(result.stdout+result.stderr)[-2400:]}),flush=True)
assert result.returncode==0
head=git("rev-parse","HEAD").decode().strip()
assert git("show","-s","--format=%P",head).decode().split()==[OURS,MAIN]
assert not git("status","--porcelain").strip()
print(json.dumps({"merge_commit":head,"parents":[OURS,MAIN],"clean":True,"published":False}),flush=True)
