import datetime,hashlib,json,pathlib,subprocess
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");g=["git","--no-optional-locks","-C",str(W)];stem="macro-ae3-5c2d-p0b-lineage-v2";outpath=E/(stem+".json")
assert not outpath.exists()
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
start=now();prefix="mockups/evidence/prophet-p0b-zero-fouc/"
producer=json.loads((E/"macro-e2d-42c-p0b-actual.json").read_text());assert producer["pass"] and producer["source_unchanged"]
expected={};roles={}
def add(p,sha,role):
 assert not pathlib.Path(p).is_absolute() and ".." not in pathlib.Path(p).parts
 assert p not in expected or expected[p]==sha,(p,expected.get(p),sha)
 expected[p]=sha;roles.setdefault(p,[]).append(role)
for p,x in producer["source_after"].items():add(p,x["sha256"],"actual-producing-source")
bind=json.loads((E/"macro-e2d-42c-p0b-bind-stage.json").read_text())
assert bind["historical_fields_and_ten_history_entries_unchanged"]
assert bind["producer"]["sha256"]==dg((E/"macro-e2d-42c-p0b-actual.json").read_bytes())
assert producer["outputs_after"][prefix+"manifest.json"]["sha256"]==bind["manifest_before_sha256"]=="60ec5f61b4d2014d7050c416f45f128b580bc431d121e4baf9b5d5ccb59fe9af"
for p,x in producer["outputs_after"].items():
 if p!=prefix+"manifest.json":add(p,x["sha256"],"actual-produced-output")
mp=prefix+"manifest.json";mraw=(W/mp).read_bytes();assert dg(mraw)=="14f79d2a743a267eca2f20e6f6029339b3fccdd7957eabed65898528482a84c0"
assert dg(mraw)==bind["manifest_after_sha256"]
add(mp,dg(mraw),"current-bound-manifest");manifest=json.loads(mraw);assert len(manifest["repair_extension_history"])==10 and manifest["repair_extension"]==bind["current_extension"]
screens={}
for name in ["mobile-layout.json","mobile-layout-canada.json"]:
 p=prefix+name;r=json.loads((W/p).read_bytes());assert r["pass"] and r["owner_projection_matrix"]["pass"]
 for a,h in r["loaded_assets"].items():add(a,h,"recorded-loaded-asset")
 for a,h in r["construction_inputs"].items():add(a,h,"recorded-construction-input")
 for c in r["owner_projection_matrix"]["cases"]:
  if c.get("screenshot"):
   s=c["screenshot"];add(s["path"],s["sha256"],"actual-screenshot");screens[s["path"]]=s["sha256"]
assert len(screens)==16
assert {s["path"]:s["sha256"] for s in manifest["repair_extension"]["screenshots"]}==screens
for b in manifest["repair_extension"]["browser_receipts"].values():add(b["path"],b["sha256"],"manifest-browser-binding")
f=manifest["repair_extension"]["fixture_receipt"];add(f["path"],f["sha256"],"manifest-fixture-binding")
paths=sorted(expected)
trees={"closure":"5cb74e747b76b3321e36f4392ac25c40c84a3aef","after_owner_deferral":"c9be0caaf0b45d3a76a20e28982604845bd74f00","AE_commit_tree":git("rev-parse","ae3e6bc547361b632223e7e9bde73128b399035e^{tree}").decode().strip(),"N2_integrated":"1a008b73af0ef56634ce89bb07c62b7a5e0a5988","packing_repaired":"39477d0a200f63fe0d1fcf1eaa4f6d21873c86aa"}
assert trees["AE_commit_tree"]==trees["after_owner_deferral"]
maps={}
for label,t in trees.items():
 rows={}
 for line in git("ls-tree","-rz",t,"--",*paths).split(b"\0"):
  if not line:continue
  meta,p=line.split(b"\t",1);mode,typ,oid=meta.decode().split();assert typ=="blob"
  rows[p.decode()]={"mode":mode,"oid":oid}
 assert set(rows)==set(paths),(label,set(paths)-set(rows))
 maps[label]=rows
assert all(x==maps["closure"] for x in maps.values())
stage={}
for line in git("ls-files","--stage","-z","--",*paths).split(b"\0"):
 if not line:continue
 meta,p=line.split(b"\t",1);mode,oid,stageid=meta.decode().split();assert stageid=="0";stage[p.decode()]={"mode":mode,"oid":oid}
assert stage==maps["closure"]
bound=[]
for p in paths:
 raw=(W/p).read_bytes();assert dg(raw)==expected[p],p
 oid=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest();assert oid==stage[p]["oid"],p
 bound.append({"path":p,"roles":sorted(set(roles[p])),"bytes":len(raw),"sha256":expected[p],"git_blob":oid})
assert not git("diff","--name-only").strip()
out={"started_at":start,"finished_at":now(),"trees":trees,"ae_commit":"ae3e6bc547361b632223e7e9bde73128b399035e","expected_parent_tree_mapping_pass":True,"manifest_binding_transition":{"before":bind["manifest_before_sha256"],"after":bind["manifest_after_sha256"],"receipt_sha256":dg((E/"macro-e2d-42c-p0b-bind-stage.json").read_bytes())},"prior_diagnostic":"v1 exit1 before source/index effects because it incorrectly treated the deliberately rebound manifest as an unchanged producer output; exact old/new binding receipt now reconciles that transition, all other raw bindings remain required","bound_path_count":len(paths),"screenshot_count":len(screens),"all_tree_blob_mode_maps_equal":True,"stage_and_raw_worktree_match":True,"bound_paths":bound,"scope":"Complete recorded producing-source, loaded-asset, construction-input, current core evidence and 16 screenshot bindings across closure, ordinary renderer deferral, AE commit, N2 merge and two-literal packing repair. This compares exact bytes; no producer, browser, public-beta or production acceptance is rerun or inferred."}
outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"bytes":outpath.stat().st_size,"sha256":dg(outpath.read_bytes()),"bound_paths":len(paths),"screenshots":len(screens),"pass":True},indent=2))
