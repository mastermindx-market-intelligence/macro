import copy,datetime,gzip,hashlib,json,pathlib,subprocess
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27")
E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
REL="research/market_os/evidence/shared-shell-continuation-20261019"
P=W/REL
G=["git","-C",str(W)]
AE="ae3e6bc547361b632223e7e9bde73128b399035e"
N="5c2d0a04afd19642d2dab483885d46c73b7baed4"
SOURCE="39477d0a200f63fe0d1fcf1eaa4f6d21873c86aa"
HP="agentos/handoffs/MARKET-OS-SHARED-SHELL-2026-09-24.md"
WP="agentos/workstreams/WS-MARKET-OS.md"
stem="macro-ae3-5c2d-proof-finalize"
result=E/(stem+".json")
def git(*args):return subprocess.check_output(G+list(args))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n")
assert not result.exists(),"existing finalizer effect needs reconciliation"
validation=json.loads((E/"macro-ae3-5c2d-proof-validation.json").read_text())
assert git("rev-parse","HEAD").decode().strip()==AE
assert git("rev-parse","MERGE_HEAD").decode().strip()==N
initial=git("write-tree").decode().strip()
assert initial==validation["record_index_before_validation"]=="8d3c7cd7b54e36fbac65b33ae43e616f58d5d752"
assert not git("diff","--name-only").strip() and not git("ls-files","-u").strip()
assert [c["exit"] for c in validation["checks"]]==[0,0,0,2]
mf=json.loads((P/"MANIFEST.json").read_text())
old=json.loads(git("show","HEAD:"+REL+"/MANIFEST.json"))
oldrows={r["file"]:r for r in old["files"]}
rows={r["file"]:r for r in mf["files"]}
assert len(oldrows)==322 and len(rows)==len(mf["files"])
def verify():
 for name,row in rows.items():
  data=(P/name).read_bytes()
  assert len(data)==row["bytes"] and dg(data)==row["sha256"],name
  if row.get("encoding","identity")=="gzip":
   raw=gzip.decompress(data)
   assert len(raw)==row["original_bytes"] and dg(raw)==row["original_sha256"],name
 assert {str(p.relative_to(P)) for p in P.rglob("*") if p.is_file()}==set(rows)|{"MANIFEST.json"}
verify()
hb=(W/HP).read_bytes();wb=(W/WP).read_bytes()
assert dg(hb)=="3bf163154b01d48c8a7732059ed9750ed27c7b19cc6415092cad350a6e46bb26"
assert dg(wb)=="fda119bcecdb0a8c0950193d7e5bef30abffecb16fa94bae57318a08b5d24387"
readme=(P/"README.md").read_bytes()
previous_readme=git("show","HEAD:"+REL+"/README.md")
assert readme.startswith(previous_readme) and readme.endswith(b"\n\n") and not readme.endswith(b"\n\n\n")
name="macro-beta-before-e2d-publication-20261020T0536-remote.py"
original_raw=(E/name).read_bytes()
assert name not in oldrows and name in rows
assert (P/name).read_bytes()==original_raw
assert dg(original_raw)=="c53b62c77cc27142fc31f20e771a50428be6311af72249eec6140e5a068e78c0"
assert not (P/(name+".gz")).exists()
out={"started_at":now(),"head":AE,"incoming":N,"source_index":SOURCE,"initial_proof_index":initial,"initial_validation":"macro-ae3-5c2d-proof-validation.json","status":"PREFLIGHT_COMPLETE_WRITES_BEGIN"}
save(result,out)
(P/"README.md").write_bytes(readme[:-1])
rows["README.md"]={**rows["README.md"],"bytes":len(readme)-1,"sha256":dg(readme[:-1])}
compressed=gzip.compress(original_raw,mtime=0)
assert gzip.decompress(compressed)==original_raw
(P/(name+".gz")).write_bytes(compressed)
rows[name+".gz"]={**rows[name],"file":name+".gz","bytes":len(compressed),"sha256":dg(compressed),"encoding":"gzip","original_bytes":len(original_raw),"original_sha256":dg(original_raw)}
(P/name).unlink()
del rows[name]
added=[]
def include(source,force_gzip=False):
 raw=source.read_bytes()
 gz=force_gzip or source.suffix in (".log",".txt",".patch") or len(raw)>65536
 target=source.name+(".gz" if gz else "")
 if target in rows:
  row=rows[target]
  assert (row.get("original_sha256") if row.get("encoding","identity")=="gzip" else row["sha256"])==dg(raw),target
  return target
 assert not (P/target).exists(),target
 data=gzip.compress(raw,mtime=0) if gz else raw
 if gz:assert gzip.decompress(data)==raw
 else:raw.decode()
 (P/target).write_bytes(data)
 row={"file":target,"source":str(source),"bytes":len(data),"sha256":dg(data),"encoding":"gzip" if gz else "utf-8"}
 if gz:row.update(original_bytes=len(raw),original_sha256=dg(raw))
 rows[target]=row;added.append(target)
 return target
for path in ["macro-ae3-5c2d-proof-validation.json","macro-ae3-5c2d-proof-records-v2.json","macro-ae3-5c2d-resume-census-20261020T1418.json","macro-ae3-5c2d-procedure-compatibility-20261020T1422.json","macro-ae3-5c2d-final-changed-paths.txt",stem+".py"]:
 include(E/path)
for check in validation["checks"]:include(pathlib.Path(check["log"]),True)
mf["proof_import_recovery"]={"original_import_result":"macro-ae3-5c2d-proof-records-v2.json","disposition":"Partial import journal retained; original validation failed only two proof-file EOF whitespace findings. This finalizer completes packaging without repeating accepted source tests.","census":"macro-ae3-5c2d-resume-census-20261020T1418.json","prior_remote_head":"e2d10f933587f58be8716505529a37f8839901f7","no_interrupted_finalizer_commit_or_push_observed":True,"raw_receipt_script_packed_losslessly":name+".gz","readme_change":"Remove only the single new terminal blank line; complete prior committed README remains an exact prefix."}
def save_manifest():
 mf["files"]=[rows[k] for k in sorted(rows)]
 mf["indexed_at"]=now()
 save(P/"MANIFEST.json",mf)
save_manifest()
subprocess.run(G+["add","--",REL],check=True)
repaired_index=git("write-tree").decode().strip()
log=E/"macro-ae3-5c2d-proof-owned-whitespace-after.log"
assert not log.exists()
started=now()
with log.open("xb") as f:
 check=subprocess.run(G+["diff","--cached","--check",N,"--"],stdout=f,stderr=subprocess.STDOUT)
assert check.returncode==0,log.read_text()
green={"check":"owned-whitespace","command":G+["diff","--cached","--check",N,"--"],"started_at":started,"finished_at":now(),"exit":0,"log":str(log),"bytes":log.stat().st_size,"sha256":dg(log.read_bytes()),"checked_index":repaired_index}
reconciliation={"record_type":"proof_whitespace_reconciliation","started_at":out["started_at"],"finished_at":now(),"original_failed_receipt":"macro-ae3-5c2d-proof-validation.json","original_failed_log":"macro-ae3-5c2d-proof-owned-whitespace.log.gz","original_failure_retained":True,"exact_repairs":[{"file":"README.md","old_bytes":len(readme),"new_bytes":len(readme)-1,"prior_committed_prefix_unchanged":True},{"old_file":name,"new_file":name+".gz","raw_bytes":len(original_raw),"raw_sha256":dg(original_raw),"gzip_bytes":len(compressed),"gzip_sha256":dg(compressed),"roundtrip_equal":True}],"reused_unchanged_checks":validation["checks"][:3],"new_check":green,"handoff_and_workstream_unchanged":True,"source_runtime_or_tests_modified":False,"all_documentation_checks_exit0_after_repair":True}
rp=E/"macro-ae3-5c2d-proof-whitespace-reconciliation.json"
assert not rp.exists()
save(rp,reconciliation)
include(log,True);include(rp)
mf["documentation_validation"]={"receipt":rp.name,"original_failed_receipt":"macro-ae3-5c2d-proof-validation.json","all_checks_exit0_after_repair":True,"agentos_exit":0,"owned_whitespace_exit":0,"template_sync_exit":0,"p0b_closure_exit":0,"previous_three_checks_reused_on_identical_inputs":True,"record_index":repaired_index,"handoff_unchanged_after_validation":True,"workstream_unchanged_after_validation":True}
save_manifest()
verify()
for name,row in oldrows.items():
 if name!="README.md":assert rows[name]==row,name
assert (P/"README.md").read_bytes().startswith(previous_readme)
assert (W/HP).read_bytes()==hb and (W/WP).read_bytes()==wb
subprocess.run(G+["add","--",REL],check=True)
final=git("write-tree").decode().strip()
docs=git("diff","--name-only",SOURCE,final).decode().splitlines()
assert all(p in (HP,WP) or p.startswith(REL+"/") for p in docs)
assert not git("diff","--name-only").strip() and not git("ls-files","-u").strip()
assert not git("diff","--cached","--check",N,"--").strip()
paths=git("diff","--name-only",N,final).decode().splitlines()
assert len(paths)<3000
out.update({"finished_at":now(),"status":"PROOF_FINALIZED_NOT_COMMITTED_OR_PUSHED","final_index":final,"documentation_only_paths":len(docs),"indexed_files":len(rows),"added_files":added,"manifest_bytes":(P/"MANIFEST.json").stat().st_size,"manifest_sha256":dg((P/"MANIFEST.json").read_bytes()),"candidate_paths_vs_N2":len(paths),"reconciliation_receipt_sha256":dg(rp.read_bytes()),"all_hashes_and_coverage_pass":True,"all_documentation_checks_exit0_after_repair":True,"old322_rows_retained_except_readme_append":True,"handoff_sha256":dg(hb),"workstream_sha256":dg(wb)})
save(result,out)
print(json.dumps(out,indent=2),flush=True)
