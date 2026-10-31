"""Compose the two additive theme groups and reconcile the six actual main conflicts."""
from pathlib import Path
import collections,datetime,gzip,hashlib,json,re,subprocess,yaml
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
C=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018/research/reference_integrity/intl-country-intelligence-20261020/main_tools_repair_20261022/transport_query_repair_20261022/main_composition_6a4_20261022")
OURS="20d22192613f1f5eb062d85e9aca1b2bb3e48036"
MAIN="6a4c0079d1aec13b08cb554f6f7424b775165d09"
BASE="90df0e302637ade26b894aee46141b6a1813a630"
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
historical=[prefix+n for n in names[:3]]+["site/research_screener.html"]
resolved=historical+["site/theme.css","templates/theme.css"]
assert set(git("diff","--name-only","--diff-filter=U").decode().splitlines())==set(resolved)
anchor1="  --surface-skeleton-deep: color-mix(in srgb, var(--panel2) 86%, var(--line));\n"
insert1="  /* International country research: existing blends owned by shared theme. */\n  --imc-summary-hover: color-mix(in srgb, var(--panel2) 65%, transparent);\n  --imc-country-line: color-mix(in srgb, var(--line) 58%, var(--link));\n  --imc-context-surface: color-mix(in srgb, var(--panel2) 65%, var(--panel));\n"
anchor2="  --mc-stance-neutral: color-mix(in srgb, var(--muted) 6%, transparent);\n"
insert2="  --imc-country-line: color-mix(in srgb, var(--link) 35%, var(--line));\n"
def add_local(text):
 assert text.count(anchor1)==1 and text.count(anchor2)==1
 assert insert1 not in text and insert2 not in text
 return text.replace(anchor1,anchor1+insert1).replace(anchor2,anchor2+insert2)
base_theme=git("show",BASE+":templates/theme.css").decode()
local_theme=git("show",OURS+":templates/theme.css").decode()
main_theme=git("show",MAIN+":templates/theme.css").decode()
assert add_local(base_theme)==local_theme,"Local theme has changes beyond the five accepted additive lines"
assert git("show",MAIN+":site/theme.css").decode()==main_theme
merged_theme=add_local(main_theme)
assert merged_theme.replace(insert1,"").replace(insert2,"")==main_theme
assert "--esurf-ser1: #2f63c4;" in merged_theme and "--esurf-ser1: var(--info);" in merged_theme
for path in historical:(R/path).write_bytes(git("show",MAIN+":"+path))
for path in ["templates/theme.css","site/theme.css"]:(R/path).write_text(merged_theme)
assert (R/"templates/theme.css").read_bytes()==(R/"site/theme.css").read_bytes()
theme=sha((R/"site/theme.css").read_bytes())
(C/"theme_composition.json").write_text(json.dumps({"source_parents":[OURS,MAIN],"theme_sha256":theme,"local_additive_lines_preserved":5,"incoming_theme_exact_after_removing_only_local_additions":True,"template_site_equal":True},indent=2)+"\n")
unchanged=["templates/intl_country_cockpit.js","templates/intl_country_cockpit.css","templates/intl_country_cockpit.html.j2","templates/shared_shell_bridge.js","site/shared_shell_bridge.js","templates/intl_workspace.js","site/intl_workspace.js","templates/intl_workspace_state.js","site/intl_workspace_state.js","tests/js/shared_shell_bridge.test.cjs","tests/intl_workspace_controller.test.cjs","tests/intl_workspace_state.test.cjs"]
for path in unchanged:assert (R/path).read_bytes()==git("show",OURS+":"+path),path
report={"schema":"intl.main_composition.v2","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"parents":[OURS,MAIN],"base":BASE,"ci_jobs":len(cj),"changed_job_sources":checks,"ci_overlap_checks":overlaps,"foundation_job_identical_to_reviewed_ci_commit":True,"resolved_paths":resolved,"resolution":"exact_theme_union_and_main_historical_staging_requires_actual_P0B_recapture","theme_sha256":theme,"unchanged_product_inputs":unchanged,"parent_evidence":lineage,"production_acceptance":False}
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
print(json.dumps({"conflicts_resolved":6,"ci_jobs":len(cj),"ci_overlap_checks":len(overlaps),"theme_sha256":theme,"ready_for_normal_merge_commit":True}),flush=True)
result=subprocess.run(["git","-c","core.editor=true","merge","--continue"],cwd=R,capture_output=True,text=True)
Path("/tmp/intl-query-normal-merge6a4-commit-20261022.log").write_text(result.stdout+result.stderr)
print(json.dumps({"merge_continue_exit":result.returncode,"output_tail":(result.stdout+result.stderr)[-2400:]}),flush=True)
assert result.returncode==0
head=git("rev-parse","HEAD").decode().strip()
assert git("show","-s","--format=%P",head).decode().split()==[OURS,MAIN]
assert not git("status","--porcelain").strip()
print(json.dumps({"merge_commit":head,"parents":[OURS,MAIN],"clean":True,"published":False}),flush=True)