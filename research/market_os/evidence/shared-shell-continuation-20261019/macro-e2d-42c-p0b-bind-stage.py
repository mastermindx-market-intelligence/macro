import pathlib,subprocess,json,hashlib,datetime,collections,yaml,copy
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
H="e2d10f933587f58be8716505529a37f8839901f7";M="42c859546ececa797b400db0adeb8c5a22f96832";B="92c51f1ff800b36fc63e7869243945996ac7315c"
g=["git","--no-optional-locks","-C",str(W)]
def git(*a):return subprocess.check_output(g+list(a))
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def dg(b):return hashlib.sha256(b).hexdigest()
def rd(p):b=(W/p).read_bytes();return {"bytes":len(b),"sha256":dg(b)}
outpath=E/"macro-e2d-42c-p0b-bind-stage.json";assert not outpath.exists()
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M
prefix="mockups/evidence/prophet-p0b-zero-fouc/"
producer=json.loads((E/"macro-e2d-42c-p0b-actual.json").read_text());assert producer["pass"] and producer["source_unchanged"]
for p,x in producer["source_after"].items():assert rd(p)==x,p
for p,x in producer["outputs_after"].items():assert rd(p)==x,p
manifest_path=prefix+"manifest.json";oldraw=(W/manifest_path).read_bytes();manifest=json.loads(oldraw);historical=copy.deepcopy(manifest)
hp=json.loads(git("show",H+":"+manifest_path));mp=json.loads(git("show",M+":"+manifest_path))
def basefields(x):return {k:v for k,v in x.items() if k not in ("repair_extension","repair_extension_history")}
assert basefields(manifest)==basefields(hp)==basefields(mp)
history=manifest["repair_extension_history"];assert len(history)==10
assert history[-2]=={"extension":hp["repair_extension"],"prior_manifest_sha256":dg(git("show",H+":"+manifest_path)),"source_head":H}
assert history[-1]=={"extension":mp["repair_extension"],"prior_manifest_sha256":dg(git("show",M+":"+manifest_path)),"source_head":M}
ext=copy.deepcopy(hp["repair_extension"]);ext["generated_at"]=now();ext["fixture_receipt"]={"path":prefix+"rendered-fixture.json","sha256":rd(prefix+"rendered-fixture.json")["sha256"]}
bindings={};shots=[];totals={"markets":0,"owner_cases_per_market":3,"primary_cases":0,"degraded_control_cases":0,"total_cases":0,"screenshots":0}
for market,name in [("hk","mobile-layout.json"),("ca","mobile-layout-canada.json")]:
 path=prefix+name;receipt=json.loads((W/path).read_text());projection=receipt["owner_projection_matrix"]
 assert receipt["pass"] is True and projection["pass"] is True and receipt["fixture_market"]==market
 assert receipt["claims"]==ext["claims"] and receipt["fixture_receipt"]["sha256"]==ext["fixture_receipt"]["sha256"]
 assert projection["primary_passed"]==48 and projection["degraded_controls_passed"]==16 and projection["screenshot_count"]==8
 assert len(projection["cases"])==64 and all(x["pass"] for x in projection["cases"])
 for p,h in receipt["loaded_assets"].items():assert rd(p)["sha256"]==h,p
 for p,h in receipt["construction_inputs"].items():assert rd(p)["sha256"]==h,p
 ms=[x["screenshot"] for x in projection["cases"] if x.get("screenshot")];assert len(ms)==8
 for x in ms:assert rd(x["path"])["sha256"]==x["sha256"];shots.append({"path":x["path"],"sha256":x["sha256"]})
 bindings[market]={"path":path,"sha256":rd(path)["sha256"],"pass":receipt["pass"],"primary_cases":projection["primary_passed"],"degraded_control_cases":projection["degraded_controls_passed"],"screenshots":projection["screenshot_count"]}
 totals["markets"]+=1;totals["primary_cases"]+=projection["primary_passed"];totals["degraded_control_cases"]+=projection["degraded_controls_passed"];totals["total_cases"]+=len(projection["cases"]);totals["screenshots"]+=projection["screenshot_count"]
assert len({x["path"] for x in shots})==16
ext["browser_receipts"]=bindings;ext["screenshots"]=sorted(shots,key=lambda x:x["path"]);ext["totals"]=totals;ext["pass"]=all(x["pass"] for x in bindings.values())
manifest["repair_extension"]=ext
assert {k:v for k,v in manifest.items() if k!="repair_extension"}=={k:v for k,v in historical.items() if k!="repair_extension"}
# Independent closure of the additive CI resolver's inventory/deletion/index gaps.
ci=".github/ci/legacy-jobs.yml";b,h,m=[yaml.safe_load(git("show",r+":"+ci)) for r in (B,H,M)]
assert set(h["jobs"])<=set(m["jobs"]) and set(b["jobs"])<=set(h["jobs"])
removed=[]
for jid,bj in b["jobs"].items():
 for label,parent in [("H",h),("M",m)]:
  gone=collections.Counter(bj.get("paths",[]))-collections.Counter(parent["jobs"][jid].get("paths",[]))
  if gone:removed.append({"job":jid,"parent":label,"removed":dict(gone)})
assert not removed,removed
critical={"app/deploy/Caddyfile":"cb8adb3ce636e956fdb58831b960495f6cfba4dc75c578c62bfae39a3b64af3a","app/deploy/update.sh":"337664e579503b69d3bd11d4aeba817c9393f90d165a6a7821b07a52ef905394",ci:"221c0c1ad74d9d8e65e7596428fd14c453a55bf8caa9a35debff89b43640dd45","tests/test_ci_pack.py":"96e6548805d3b33f5d42aec9b8a66fa8813bed108edf439ef00213878b23f352"}
for p,sha in critical.items():assert dg(git("show",":"+p))==rd(p)["sha256"]==sha,p
unstaged=sorted(set(x.decode() for x in git("diff","--name-only","-z").split(b"\0") if x))
allowed_json={manifest_path,prefix+"mobile-layout.json",prefix+"mobile-layout-canada.json"}
assert all(p in allowed_json or (p.startswith("site/") and p.endswith(".html")) for p in unstaged)
html=[p for p in unstaged if p.endswith(".html")];assert len(html)==13006,len(html)
for p in html:
 raw=(W/p).read_bytes();assert len(raw)>100 and b"<<<<<<< HEAD" not in raw and b"?v=00000000" not in raw,p
newraw=(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n").encode()
out={"started_at":now(),"head":H,"incoming":M,"producer":{"path":str(E/"macro-e2d-42c-p0b-actual.json"),"sha256":dg((E/"macro-e2d-42c-p0b-actual.json").read_bytes())},"historical_fields_and_ten_history_entries_unchanged":True,"manifest_before_sha256":dg(oldraw),"manifest_after_sha256":dg(newraw),"current_extension":ext,"ci_additivity":{"base_jobs":len(b["jobs"]),"head_jobs":len(h["jobs"]),"incoming_jobs":len(m["jobs"]),"head_only_omitted_jobs":[],"parent_path_deletions":[],"four_critical_worktree_index_raw_hashes":critical}}
(W/manifest_path).write_bytes(newraw)
selected=sorted(set(html+list(allowed_json)+[prefix+"rendered-fixture.json"]+[x["path"] for x in shots]))
pathspec=E/"macro-e2d-42c-stage-paths.nul";assert not pathspec.exists();rawpaths=b"\0".join(x.encode() for x in selected)+b"\0";pathspec.write_bytes(rawpaths)
out["stage_paths"]={"path":str(pathspec),"count":len(selected),"sha256":dg(rawpaths)}
outpath.write_text(json.dumps(out,indent=2)+"\n")
r=subprocess.run(g+["add","--pathspec-from-file="+str(pathspec),"--pathspec-file-nul"],capture_output=True)
out["git_add"]={"exit":r.returncode,"stdout":r.stdout.decode(errors="replace"),"stderr":r.stderr.decode(errors="replace")};outpath.write_text(json.dumps(out,indent=2)+"\n");assert r.returncode==0
assert not git("diff","--name-only","--diff-filter=U").strip()
stage={}
for row in git("ls-files","--stage","-z").split(b"\0"):
 if row:
  meta,p=row.split(b"\t",1);mode,blob,st=meta.split();assert st==b"0";stage[p.decode()]=blob.decode()
for p in selected:
 raw=(W/p).read_bytes();expected=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest();assert stage[p]==expected,p
out["unmerged_after"]=[];out["selected_index_equals_worktree"]=True;out["unstaged_after"]=git("diff","--name-only").decode().splitlines();out["index_tree"]=git("write-tree").decode().strip();out["finished_at"]=now()
out["versus_incoming_changed_path_count"]=len(git("diff","--cached","--name-only","-z",M).split(b"\0"))-1
outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"sha256":dg(outpath.read_bytes()),"bytes":outpath.stat().st_size,"staged_count":len(selected),"unmerged_after":[],"unstaged_after":out["unstaged_after"],"index_tree":out["index_tree"],"versus_incoming_changed_path_count":out["versus_incoming_changed_path_count"],"ci_additive_gaps_closed":True,"finished_at":out["finished_at"]}),flush=True)
