import copy,datetime,gzip,hashlib,json,pathlib,re,subprocess,yaml
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");P=W/"research/market_os/evidence/shared-shell-continuation-20261019";g=["git","-C",str(W)];stem="macro-ae3-5c2d-proof-records-v2";outpath=E/(stem+".json")
H="e2d10f933587f58be8716505529a37f8839901f7";AE="ae3e6bc547361b632223e7e9bde73128b399035e";N="5c2d0a04afd19642d2dab483885d46c73b7baed4";SOURCE="39477d0a200f63fe0d1fcf1eaa4f6d21873c86aa"
HP="agentos/handoffs/MARKET-OS-SHARED-SHELL-2026-09-24.md";WP="agentos/workstreams/WS-MARKET-OS.md"
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def readj(name):return json.loads((E/name).read_text())
def savej(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n")
assert not outpath.exists()
assert git("rev-parse","HEAD").decode().strip()==AE and git("rev-parse","MERGE_HEAD").decode().strip()==N
assert git("write-tree").decode().strip()==SOURCE and not git("diff","--name-only").strip() and not git("ls-files","-u").strip()
packing=readj("macro-ae3-5c2d-packing-after.json");deploy=readj("macro-ae3-5c2d-deploy-validation.json");lineage=readj("macro-ae3-5c2d-p0b-lineage-v2.json");scope=readj("macro-e2d-42c-render-owner-scope.json")
assert packing["pass"] and deploy["pass"] and lineage["all_tree_blob_mode_maps_equal"] and lineage["bound_path_count"]==82
cfg=readj("macro-ae3-5c2d-proof-records-config.json")
mfraw=(P/"MANIFEST.json").read_bytes();assert dg(mfraw)=="a54e03e87ada47e40eac679da9b5d0e714bbb39536116220de674dd7296041a9"
mf=json.loads(mfraw);oldrows=copy.deepcopy(mf["files"]);assert len(oldrows)==322
rowmap={r["file"]:r for r in mf["files"]};assert len(rowmap)==len(oldrows)
def verify_rows(rows):
 for r in rows:
  b=(P/r["file"]).read_bytes();assert len(b)==r["bytes"] and dg(b)==r["sha256"],r["file"]
  if r.get("encoding","identity")=="gzip":
   rb=gzip.decompress(b);assert len(rb)==r["original_bytes"] and dg(rb)==r["original_sha256"],r["file"]
verify_rows(oldrows)
assert {str(p.relative_to(P)) for p in P.rglob("*") if p.is_file()}==set(rowmap)|{"MANIFEST.json"}
oldreadme=(P/"README.md").read_bytes();assert dg(oldreadme)=="68e3d5d108984ab5116e88ee2148454383f953b308bf167b7b5a0bc417495214"
hb=(W/HP).read_bytes();wb=(W/WP).read_bytes();assert hb==git("show","HEAD:"+HP) and wb==git("show","HEAD:"+WP)
hs=hb.decode();cut=hs.index("\n---\n",4);meta=yaml.safe_load(hs[4:cut]);oldbody=hs[cut+5:]
assert meta["workstream"]=="WS:MARKET-OS" and meta["prs"]==[7949]
meta["state_before"]=cfg["state_before"];meta["changed"].extend(cfg["changed"]);meta["verified"].extend(cfg["verified"]);meta["unresolved"]=cfg["unresolved"];meta["next_actions"]=cfg["next_actions"];meta["do_not_redo"].append(cfg["do_not_redo_add"])
newh="---\n"+yaml.safe_dump(meta,sort_keys=False,allow_unicode=True,width=110)+"---\n"+oldbody+"\n\n"+cfg["continuation"]
assert newh.split("\n---\n",1)[1].startswith(oldbody) and newh.split("\n---\n",1)[1]==oldbody+"\n\n"+cfg["continuation"]
neww=wb.decode()+"\n\n"+cfg["continuation"]
assert neww[:len(wb.decode())]==wb.decode()
out={"started_at":now(),"head":AE,"incoming":N,"source_index":SOURCE,"old_manifest_sha256":dg(mfraw),"old_indexed_files":len(oldrows),"old_handoff_body_sha256":dg(oldbody.encode()),"old_workstream_sha256":dg(wb),"initial_import_refusal":"v1 stopped before any repository write on a missing optional encoding key in14 legacy raw entries; v2 treats absent encoding as identity while preserving all old rows verbatim","record_writes_started":True}
savej(outpath,out)
(W/HP).write_text(newh);(W/WP).write_text(neww)
(P/"README.md").write_bytes(oldreadme+b"\n\n"+cfg["continuation"].encode()+b"\n")
newrb=(P/"README.md").read_bytes();assert newrb.startswith(oldreadme)
rowmap["README.md"]={**rowmap["README.md"],"bytes":len(newrb),"sha256":dg(newrb)}
added=[];skipped=[]
def import_file(source,target=None,force_gzip=False):
 raw=source.read_bytes()
 if target is None:target=source.name
 usegz=force_gzip or source.suffix in (".log",".patch",".stdout",".stderr",".nul",".txt",".yml") or source.name.startswith("macro-full-checkpoint-") or len(raw)>65536
 if usegz and not target.endswith(".gz"):target+=".gz"
 if target in rowmap:
  existing=rowmap[target]
  assert (existing.get("original_sha256") if existing.get("encoding","identity")=="gzip" else existing["sha256"])==dg(raw),(source,target)
  skipped.append(target);return
 assert pathlib.Path(target).name==target and not (P/target).exists()
 data=gzip.compress(raw,mtime=0) if usegz else raw
 if usegz:assert gzip.decompress(data)==raw
 (P/target).write_bytes(data)
 ent={"file":target,"source":str(source),"bytes":len(data),"sha256":dg(data),"encoding":"gzip" if usegz else "utf-8"}
 if usegz:ent.update({"original_bytes":len(raw),"original_sha256":dg(raw)})
 else:raw.decode()
 rowmap[target]=ent;added.append(target)
paths=subprocess.check_output(["rg","--files",str(E)],text=True).splitlines()
prefixes=("macro-e2d-","macro-ae3-","macro-main-","protected-master-fe7-to-e992-","protected-master-e992-","macro-beta-before-e2d-publication-20261020T0536","macro-beta-origin-tls-prepublication-20261020T0628")
checkpoints={"macro-full-checkpoint-1037-pre-browser-bind.md","macro-full-checkpoint-1103-pre-N2.md","macro-full-checkpoint-current-N2-frozen.md","macro-full-checkpoint-N2-source-green.md"}
for rawpath in sorted(paths):
 p=pathlib.Path(rawpath)
 if p==outpath:continue
 if p.parent==E and (p.name.startswith(prefixes) or p.name in checkpoints):import_file(p)
 elif p.name=="receipt.json" and p.parent.parent==E and p.parent.name.startswith("macro-e2d-42c-html"):import_file(p,p.parent.name+"-receipt.json",True)
prior_keys=[k for k in mf if k!="files" and not k.startswith("previous_frontier")]
assert "previous_frontier_before_42c" not in mf
mf["previous_frontier_before_42c"]={k:copy.deepcopy(mf[k]) for k in prior_keys}
mf.update({"indexed_at":now(),"macro_source_head":AE,"macro_incoming_main":N,"macro_integrated_index_tree_before_proof":SOURCE,"latest_confirmed_macro_publication":H,"publication_of_this_package":"Precommit/prepush ordinary N2 merge. Original PR7949 checkpoint binds eventual source head; this package does not claim hosted, rendered-main or served publication.","current_terminal_repair_candidate":"93e303cc32566e72fb086af6d04ba3aa41866c5c","latest_host_observed_at":"2026-10-20T06:05:53.075809Z","beta_publication_gate":"Protected R93 originalA bootstrap/runtime/filesystem accepted; no repeat. Historical06:05 health must refresh before arm. Public DNS/TLS/auth/browser/applicable rollback remain separate.","visual_acceptance":"Actual resolved-worktree P0B128cases/16screenshots and closure accepted; all82 finite producing/loaded/construction/output bindings preserved through source index39477. Historical CSS/About limitations retained. Public beta and canonical production build unaccepted.","local_contract_gate_scope":"Historical full d528/e2d-hosted results remain historical. Current N2 three scope nodes plus actual minimal-packing rerun and deployment suite are separate; new-head hosted admission pending.","focused_current_composition":{"source_index":SOURCE,"incoming":N,"scope_passes":3,"packing_exit":0,"packing_receipt":"macro-ae3-5c2d-packing-after.json","deployment_passes":334,"deployment_exit":0,"deployment_receipt":"macro-ae3-5c2d-deploy-validation.json","hosted_admission":False},"latest_main_read_before_publication":{"sha":"68da9a798428ad425ceda592551719d0c649a1d8","observed_at":"2026-10-20T11:31:11Z","ahead_of_composed_main":1,"changed_paths":2,"classification":"FIF additional Node test and command argument; existing exclusive paths and1630weight override unchanged; actual hosted test-merge remains required","receipt":"macro-main-68da-preproof-read.json.gz"},"current_p0b":{"receipt":"macro-e2d-42c-p0b-actual.json","binding":"macro-e2d-42c-p0b-bind-stage.json","closure":"macro-e2d-42c-p0b-closure.json","lineage":"macro-ae3-5c2d-p0b-lineage-v2.json","bound_paths":82,"screenshots":16,"production":False},"generated_publication_boundary":{"source_paths_before_proof":610,"deferred_paths":13006,"receipt":"macro-e2d-42c-render-owner-scope.json","existing_contract":"research/market_os/SHARED_SHELL_GENERATED_PUBLICATION_2026-10-18.md","published":False}})
mf["latest_main_read_before_publication"]["receipt"]=next(r["file"] for r in rowmap.values() if r.get("source")==str(E/"macro-main-68da-preproof-read.json"))
mf["files"]=[rowmap[k] for k in sorted(rowmap)];savej(P/"MANIFEST.json",mf)
subprocess.run(g+["add","--",HP,WP,str(P.relative_to(W))],check=True)
record_index=git("write-tree").decode().strip()
docs=git("diff","--name-only",SOURCE,record_index).decode().splitlines()
allowed=lambda p:p in (HP,WP) or p.startswith(str(P.relative_to(W))+"/")
assert docs and all(allowed(p) for p in docs) and not git("diff","--name-only").strip()
vpath=E/"macro-ae3-5c2d-proof-validation.json";assert not vpath.exists()
validation={"started_at":now(),"source_index":SOURCE,"record_index_before_validation":record_index,"documentation_only_delta":docs,"old322_entries_verified":True,"old_handoff_body_preserved":True,"workstream_entire_previous_bytes_preserved":True,"readme_previous_bytes_preserved":True,"checks":[]}
savej(vpath,validation)
diffpath=E/"macro-ae3-5c2d-final-changed-paths.txt";diffpath.write_bytes(git("diff","--cached","--name-only",N))
py=str(W/".venv-shared-shell/bin/python")
commands=[
 ("agentos",[py,"-B","scripts/agentos.py","validate"]),
 ("template-sync",[py,"-B","scripts/check_template_site_sync.py"]),
 ("p0b-closure",[py,"-B","scripts/check_p0b_receipt_closure.py","--diff-file",str(diffpath),"--event","pull_request"]),
 ("owned-whitespace",g+["diff","--cached","--check",N])]
for name,args in commands:
 log=E/("macro-ae3-5c2d-proof-"+name+".log");assert not log.exists();started=now()
 with log.open("xb") as f:r=subprocess.run(args,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 item={"check":name,"command":args,"started_at":started,"finished_at":now(),"exit":r.returncode,"log":str(log),"bytes":log.stat().st_size,"sha256":dg(log.read_bytes())};validation["checks"].append(item);savej(vpath,validation)
 print(json.dumps({"check":name,"exit":r.returncode,"tail":log.read_text(errors="replace")[-1800:]}),flush=True)
 assert r.returncode==0,item
assert (W/HP).read_text()==newh and (W/WP).read_text()==neww and git("write-tree").decode().strip()==record_index and not git("diff","--name-only").strip()
validation.update({"finished_at":now(),"all_checks_pass":True,"record_index_unchanged_during_checks":True,"handoff_and_workstream_unchanged_during_checks":True});savej(vpath,validation)
for c in validation["checks"]:import_file(pathlib.Path(c["log"]))
import_file(vpath);import_file(diffpath)
mf["documentation_validation"]={"receipt":vpath.name,"all_checks_exit0":True,"agentos_exit":0,"owned_whitespace_exit":0,"template_sync_exit":0,"p0b_closure_exit":0,"record_index":record_index,"handoff_unchanged_after_validation":True}
mf["files"]=[rowmap[k] for k in sorted(rowmap)];mf["indexed_at"]=now();savej(P/"MANIFEST.json",mf)
verify_rows(mf["files"])
for old in oldrows:
 if old["file"]!="README.md":assert rowmap[old["file"]]==old,old["file"]
assert {str(p.relative_to(P)) for p in P.rglob("*") if p.is_file()}==set(rowmap)|{"MANIFEST.json"}
subprocess.run(g+["add","--",str(P.relative_to(W))],check=True)
final_index=git("write-tree").decode().strip();final_docs=git("diff","--name-only",SOURCE,final_index).decode().splitlines();assert all(allowed(p) for p in final_docs) and not git("diff","--name-only").strip()
assert not git("diff","--cached","--check",N).strip()
count=len(git("diff","--name-only",N,final_index).decode().splitlines());assert count<3000
out.update({"finished_at":now(),"final_index":final_index,"documentation_only_paths":len(final_docs),"indexed_files":len(mf["files"]),"added_files":added,"skipped_existing_identical":skipped,"manifest_bytes":(P/"MANIFEST.json").stat().st_size,"manifest_sha256":dg((P/"MANIFEST.json").read_bytes()),"candidate_paths_vs_N2":count,"validation_receipt_sha256":dg(vpath.read_bytes()),"handoff_sha256":dg((W/HP).read_bytes()),"workstream_sha256":dg((W/WP).read_bytes()),"all_checks_pass":True})
savej(outpath,out)
print(json.dumps({k:v for k,v in out.items() if k not in ("added_files","skipped_existing_identical")},indent=2),flush=True)
