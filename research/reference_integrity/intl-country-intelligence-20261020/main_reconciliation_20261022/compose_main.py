from pathlib import Path
import collections,datetime,gzip,hashlib,json,re,shutil,subprocess,yaml
R=Path("/Volumes/Mastermind 2/agent-workspaces/macro/web/intl-country-cockpit-20261018")
D=R/"research/reference_integrity/intl-country-intelligence-20261020/main_reconciliation_20261022"
OURS="7e99587336105a939c830a00b799d7787624d09b";MAIN="25051144947f027c698cd1ce10e3c8824ee6ade9"
def git(*args): return subprocess.check_output(["git",*args],cwd=R)
assert git("rev-parse","HEAD").decode().strip()==OURS
assert git("rev-parse","MERGE_HEAD").decode().strip()==MAIN
base=git("merge-base",OURS,MAIN).decode().strip();assert base=="2fed30a5a14f6bdd5e69d42c5bfcbac5814b3915"
P="mockups/evidence/prophet-p0b-zero-fouc/"
names=["manifest.json","mobile-layout.json","mobile-layout-canada.json"]
assert set(git("diff","--name-only","--diff-filter=U").decode().splitlines())=={P+n for n in names}
ci=".github/ci/legacy-jobs.yml"
bj,oj,mj=[yaml.safe_load(git("show",ref+":"+ci))["jobs"] for ref in [base,OURS,MAIN]]
cj=yaml.safe_load((R/ci).read_text())["jobs"]
changed={k for k in set(bj)|set(oj) if bj.get(k)!=oj.get(k)}
expected={"international-workspace-foundation","international-workspace-browser","intelligence-registry","itr-turn-rotation","nw-lobe-unfreeze","biocatalyst-serving","washout-turn-organ","unrun-picks-boards"}
assert changed==expected
assert set(cj)==set(mj)
checks=[]
for job,obj in cj.items():
 if job not in changed:
  assert obj==mj[job],job
  continue
 bp=set(bj[job].get("paths",[]));op=set(oj[job].get("paths",[]));mp=set(mj[job].get("paths",[]));cp=set(obj.get("paths",[]))
 assert cp==(mp-(bp-op))|(op-bp),job
 if job!="international-workspace-foundation":
  assert {k:v for k,v in obj.items() if k!="paths"}=={k:v for k,v in mj[job].items() if k!="paths"},job
 else:
  def modules(x):return set(re.findall(r"tests/[A-Za-z0-9_./-]+\.py","\n".join(str(s.get("run","")) for s in x["steps"])))
  assert modules(obj)==modules(mj[job])|modules(oj[job])
  assert len([s for s in obj["steps"] if s.get("name")=="International country evidence, outlook and publication custody"])==1
  installs="\n".join(str(s.get("run","")) for s in obj["steps"] if "install" in str(s.get("name","")))
  assert "yfinance>=0.2.50" in installs and "openpyxl>=3.1" in installs
 checks.append({"job":job,"main_and_local_closure_preserved":True,"local_added_paths":sorted(op-bp)})
D.mkdir(exist_ok=False)
lineage=[]
for label,ref in [("previous_published",OURS),("incoming_main",MAIN)]:
 d=D/label;d.mkdir()
 for name in names+["rendered-fixture.json"]:
  raw=git("show",ref+":"+P+name);(d/name).write_bytes(raw)
  lineage.append({"parent":ref,"path":P+name,"archive":str((d/name).relative_to(R)),"sha256":hashlib.sha256(raw).hexdigest()})
for name in names:(R/P/name).write_bytes(git("show",MAIN+":"+P+name))
for name in ["intl_country_cockpit.html.j2","intl_country_cockpit.css","intl_country_cockpit.js"]:
 assert (R/"templates"/name).read_bytes()==git("show",OURS+":templates/"+name)
assert (R/"app/deploy/Caddyfile").read_bytes()==git("show",MAIN+":app/deploy/Caddyfile")
shutil.copyfile("/tmp/intl-current-main-merge-tree-20261022.txt",D/"merge_tree.txt")
shutil.copyfile("/tmp/intl-main250-merge-20261022.log",D/"normal_merge.log")
report={"schema":"intl.current_main_reconciliation.v1","at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"parents":[OURS,MAIN],"base":base,"reason":"REST PR base and test-merge refs were stale; actual current main caused three P0B receipt conflicts and suppressed pull_request CI.","ci_jobs":len(cj),"unchanged_main_jobs":len(cj)-len(changed),"local_changed_job_checks":checks,"unmerged_paths_resolved":[P+n for n in names],"parent_evidence":lineage,"direct_country_source_unchanged":True,"shared_runtime_changed":True,"p0b_state":"Both parents archived; incoming-main receipts are only a historical staging point. Fresh actual remint required.","production_acceptance":False,"shared_shell_repair_fence":"unchanged; no retry, replacement, or consumption of unknown result"}
(D/"composition.json").write_text(json.dumps(report,indent=2)+"\n")
subprocess.run(["git","add","--",str(D.relative_to(R)),*[P+n for n in names]],cwd=R,check=True)
assert not git("diff","--name-only","--diff-filter=U").strip()
def tree(ref):
 result={}
 for line in git("ls-tree","-rz",ref).split(b"\0"):
  if line: meta,name=line.split(b"\t",1);result[name.decode()]=meta.decode().split()[2]
 return result
parents={OURS:tree(OURS),MAIN:tree(MAIN)};index={}
for line in git("ls-files","--stage","-z").split(b"\0"):
 if line: meta,name=line.split(b"\t",1);index[name.decode()]=meta.decode().split()[1]
classification=[]
for label,ref in [("from_previous_published",OURS),("from_current_main",MAIN)]:
 p=subprocess.run(["git","diff","--cached","--check",ref],cwd=R,capture_output=True);raw=p.stdout+p.stderr
 warnings=collections.Counter()
 for line in p.stdout.decode().splitlines():
  m=re.match(r"^(.+):[0-9]+: (trailing whitespace|new blank line at EOF|space before tab in indent)\.",line)
  if m:warnings[m.group(1)]+=1
 rows=[{"path":path,"count":count,"byte_identical_parents":[sha for sha,t in parents.items() if t.get(path)==index.get(path)]} for path,count in sorted(warnings.items())]
 assert p.returncode in (0,2) and (not p.returncode or rows)
 assert all(row["byte_identical_parents"] for row in rows),[row for row in rows if not row["byte_identical_parents"]]
 log=D/(label+"_whitespace.log.gz");log.write_bytes(gzip.compress(raw,mtime=0))
 classification.append({"parent":ref,"exit_code":p.returncode,"log_archive":str(log.relative_to(R)),"uncompressed_sha256":hashlib.sha256(raw).hexdigest(),"warnings":sum(warnings.values()),"paths":rows})
(D/"whitespace_classification.json").write_text(json.dumps({"pass":True,"checks":classification},indent=2)+"\n")
subprocess.run(["git","add","--",str(D.relative_to(R))],cwd=R,check=True)
p=subprocess.run(["/tmp/intl-country-cockpit-ci-20261021/bin/python","scripts/run_ci_pack.py","--workflow",ci,"--validate-only"],cwd=R,capture_output=True)
(D/"ci_manifest.log").write_bytes(p.stdout+p.stderr);assert p.returncode==0
subprocess.run(["git","add","--",str(D.relative_to(R))],cwd=R,check=True)
print(json.dumps({"ci_jobs":len(cj),"conflicts_resolved":3,"whitespace_parent_bound":True,"action":"normal_merge_commit"}),flush=True)
p=subprocess.run(["git","commit","--no-edit"],cwd=R,capture_output=True,text=True)
Path("/tmp/intl-main250-commit-20261022.log").write_text(p.stdout+p.stderr)
print(json.dumps({"commit_exit":p.returncode,"output_tail":(p.stdout+p.stderr)[-2000:]}),flush=True);assert p.returncode==0
head=git("rev-parse","HEAD").decode().strip();assert git("show","-s","--format=%P","HEAD").decode().split()==[OURS,MAIN]
assert not git("status","--porcelain").strip()
print(json.dumps({"merge_commit":head,"parents":[OURS,MAIN],"clean":True,"published":False}),flush=True)
