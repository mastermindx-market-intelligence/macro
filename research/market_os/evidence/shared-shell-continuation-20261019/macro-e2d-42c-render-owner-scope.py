import pathlib,subprocess,json,hashlib,datetime,sys,io
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
sys.path.insert(0,str(W))
from scripts.optimize_assets import make_optimizer
from scripts.check_template_site_sync import find_pairs
from lib.shared_shell import inject_shared_shell_text
from lib.pages import inject_text,dbase_prefix
g=["git","--no-optional-locks","-C",str(W)];H="e2d10f933587f58be8716505529a37f8839901f7";M="42c859546ececa797b400db0adeb8c5a22f96832";T="5cb74e747b76b3321e36f4392ac25c40c84a3aef";P="df3a71131054c6b6a2f702a38eac8a59b67026d6"
stem="macro-e2d-42c-render-owner-scope";outpath=E/(stem+".json");assert not outpath.exists()
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M and git("write-tree").decode().strip()==T
assert not git("diff","--name-only").strip()
preview=json.loads((E/"macro-e2d-42c-merge-preview.json").read_text());prelines=preview["stdout"].split("\n\n",1)[0].splitlines();assert prelines[0]==P
conflicts=set(prelines[1:]);assert len(conflicts)==33
pairs={str(s.relative_to(W)) for _,_,s in find_pairs(W)}
selected=[p.decode() for p in (E/"macro-e2d-42c-stage-paths.nul").read_bytes().split(b"\0") if p]
deferred=sorted(p for p in selected if p.startswith("site/") and p.endswith(".html") and p not in conflicts and p not in pairs)
assert len(deferred)>12000
protected=conflicts|pairs
for name in ["mobile-layout.json","mobile-layout-canada.json"]:
 r=json.loads((W/"mockups/evidence/prophet-p0b-zero-fouc"/name).read_text());protected|=set(r["loaded_assets"])|set(r["construction_inputs"])
def hashes(paths):return {p:dg((W/p).read_bytes()) for p in sorted(paths) if (W/p).is_file()}
protected_before=hashes(protected)
entries={}
for row in git("ls-tree","-r","-z",P,"--","site").split(b"\0"):
 if row:
  meta,p=row.split(b"\t",1);mode,typ,blob=meta.split()
  if p.decode() in set(deferred):assert typ==b"blob";entries[p.decode()]=blob.decode()
assert len(entries)==len(deferred)
requests=E/(stem+"-objects.txt");requests.write_text("".join(entries[p]+"\n" for p in deferred))
rows=[];mismatches=[];optimized=make_optimizer(W/"site")
out={"started_at":now(),"head":H,"incoming":M,"optimized_validation_tree":T,"normal_merge_preview_tree":P,"reason":"trusted ci-authority MAX_CHANGED_FILES=3000; defer optional bulk generated publication to incumbent scope=all render owner without changing that gate","retained_conflicts":sorted(conflicts),"retained_template_pairs":sorted(pairs),"deferred_count":len(deferred),"restore_attempted":False}
outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"prevalidate_started":now(),"candidate_deferred":len(deferred)}),flush=True)
with requests.open("rb") as f:
 proc=subprocess.Popen(g+["cat-file","--batch"],stdin=f,stdout=subprocess.PIPE)
 for i,p in enumerate(deferred):
  header=proc.stdout.readline().split();assert len(header)==3 and header[0].decode()==entries[p] and header[1]==b"blob",header
  old=proc.stdout.read(int(header[2]));assert proc.stdout.read(1)==b"\n"
  text=io.TextIOWrapper(io.BytesIO(old),encoding="utf-8").read()
  current=(W/p).read_bytes()
  injected=inject_shared_shell_text(text,dbase_prefix(W/p),site_dir=W/"site",response_kind="coming_soon" if pathlib.Path(p).name=="coming-soon.html" else "content")
  expected=inject_text(optimized(injected,(W/p).parent),dbase_prefix(W/p)).encode()
  if expected!=current:mismatches.append({"path":p,"expected_sha256":dg(expected),"actual_sha256":dg(current)})
  rows.append({"path":p,"preoptimization_blob":entries[p],"preoptimization_sha256":dg(old),"optimized_sha256":dg(current),"shell_injection_changed":injected!=text})
  if (i+1)%2000==0:print(json.dumps({"prevalidated":i+1,"mismatches":len(mismatches)}),flush=True)
 assert proc.wait()==0
out["canonical_transform_mismatches"]=mismatches;out["prevalidation_finished_at"]=now();out["shell_injection_changed_count"]=sum(x["shell_injection_changed"] for x in rows)
rowsfile=E/(stem+"-paths.json");rowsfile.write_text(json.dumps(rows,indent=2)+"\n");out["path_receipt"]={"path":str(rowsfile),"bytes":rowsfile.stat().st_size,"sha256":dg(rowsfile.read_bytes())};outpath.write_text(json.dumps(out,indent=2)+"\n")
if mismatches:print(json.dumps({"refused_before_restore":True,"mismatch_count":len(mismatches),"examples":mismatches[:10]}),flush=True);raise SystemExit(1)
assert protected_before==hashes(protected) and git("write-tree").decode().strip()==T and not git("diff","--name-only").strip()
ps=E/(stem+"-restore.nul");ps.write_bytes(b"\0".join(p.encode() for p in deferred)+b"\0")
out["restore_attempted"]=True;out["restore_started_at"]=now();outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"restore_started_at":out["restore_started_at"]}),flush=True)
r=subprocess.run(g+["restore","--source="+P,"--staged","--worktree","--pathspec-from-file="+str(ps),"--pathspec-file-nul"],capture_output=True)
out["restore_exit"]=r.returncode;out["restore_stdout"]=r.stdout.decode(errors="replace");out["restore_stderr"]=r.stderr.decode(errors="replace");outpath.write_text(json.dumps(out,indent=2)+"\n");assert r.returncode==0
assert protected_before==hashes(protected)
stage={}
for row in git("ls-files","--stage","-z").split(b"\0"):
 if row:
  meta,p=row.split(b"\t",1);mode,blob,st=meta.split();assert st==b"0";stage[p.decode()]=blob.decode()
for row in rows:
 p=row["path"];assert stage[p]==row["preoptimization_blob"] and dg((W/p).read_bytes())==row["preoptimization_sha256"],p
out["deferred_index_and_worktree_exact_preoptimization"]=True;out["protected_bytes_unchanged"]=True;out["index_tree_after"]=git("write-tree").decode().strip();out["unstaged_after"]=git("diff","--name-only").decode().splitlines();out["changed_paths_vs_M"]=len([x for x in git("diff","--cached","--name-only","-z",M).split(b"\0") if x]);out["finished_at"]=now();outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"bytes":outpath.stat().st_size,"sha256":dg(outpath.read_bytes()),"deferred":len(deferred),"shell_injection_deferred":out["shell_injection_changed_count"],"protected_bytes_unchanged":True,"tree":out["index_tree_after"],"changed_paths_vs_M":out["changed_paths_vs_M"],"unstaged_after":out["unstaged_after"],"finished_at":out["finished_at"]}),flush=True)
assert out["changed_paths_vs_M"]<3000 and not out["unstaged_after"]
