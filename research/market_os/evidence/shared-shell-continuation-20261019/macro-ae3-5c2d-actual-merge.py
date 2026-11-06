import pathlib,subprocess,json,hashlib,datetime,collections,yaml
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");g=["git","--no-optional-locks","-C",str(W)]
H="ae3e6bc547361b632223e7e9bde73128b399035e";N="5c2d0a04afd19642d2dab483885d46c73b7baed4";B="42c859546ececa797b400db0adeb8c5a22f96832";T="1a008b73af0ef56634ce89bb07c62b7a5e0a5988";outpath=E/"macro-ae3-5c2d-actual-merge.json";assert not outpath.exists()
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
assert git("rev-parse","HEAD").decode().strip()==H and not git("status","--porcelain=v1","--untracked-files=no").strip()
assert git("rev-parse","origin/main").decode().strip()==N
pr=json.loads(subprocess.check_output(["gh","pr","view","7949","--repo","mastermindx-market-intelligence/macro","--json","state,headRefOid,labels,autoMergeRequest"],cwd=W))
assert pr["state"]=="OPEN" and pr["headRefOid"]=="e2d10f933587f58be8716505529a37f8839901f7" and pr["autoMergeRequest"] is None and "merge-on-green" not in [x["name"] for x in pr["labels"]]
protected=["app/deploy/Caddyfile","app/deploy/update.sh","tests/test_ci_pack.py","lib/shared_shell.py","lib/site_assets.py","scripts/render_stock_dashboard_fixture.py","scripts/verify_stock_dashboard_mobile_layout.cjs","templates/hk.html.j2","templates/canada.html.j2","templates/sector_central.html.j2","templates/si_workspace.js","site/sector_central.html","site/theme.js","site/mm_brain.js","site/shared_shell_bridge.js","site/shared_shell.css"]+["mockups/evidence/prophet-p0b-zero-fouc/"+x for x in ["manifest.json","mobile-layout.json","mobile-layout-canada.json","rendered-fixture.json"]]
before={p:dg((W/p).read_bytes()) for p in protected}
out={"started_at":now(),"head":H,"incoming":N,"base":B,"preview_tree":T,"remote_pr":pr,"protected_before":before,"merge_attempted":True};outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"merge_started":out["started_at"]}),flush=True)
log=E/"macro-ae3-5c2d-actual-merge.log";assert not log.exists()
with log.open("xb") as f:r=subprocess.run(g+["merge","--no-ff","--no-commit",N],cwd=W,stdout=f,stderr=subprocess.STDOUT)
out["merge_exit"]=r.returncode;out["merge_finished_at"]=now();out["log"]={"path":str(log),"sha256":dg(log.read_bytes()),"bytes":log.stat().st_size};outpath.write_text(json.dumps(out,indent=2)+"\n")
assert r.returncode==0,log.read_text(errors="replace")[-5000:]
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==N and not git("ls-files","-u").strip() and not git("diff","--name-only").strip()
out["index"]=git("write-tree").decode().strip();assert out["index"]==T
after={p:dg((W/p).read_bytes()) for p in protected};assert before==after
ci=".github/ci/legacy-jobs.yml";b,h,n,c=[yaml.safe_load(git("show",ref+":"+ci)) for ref in (B,H,N,":".rstrip(":"))]
assert set(h["jobs"])<=set(n["jobs"]) and list(c["jobs"])==list(n["jobs"])
assert {k:v for k,v in c.items() if k!="jobs"}=={k:v for k,v in n.items() if k!="jobs"}
def subseq(a,b):
 it=iter(b);return all(any(x==y for y in it) for x in a)
for key,cv in c["jobs"].items():
 bv=b["jobs"].get(key);hv=h["jobs"].get(key);nv=n["jobs"].get(key)
 if bv is None:assert cv==nv and (hv is None or hv==nv);continue
 for field in set(bv)|set(hv)|set(nv)|set(cv):
  absent=object();v0=bv.get(field,absent);vh=hv.get(field,absent);vn=nv.get(field,absent);vc=cv.get(field,absent)
  if field=="paths" and isinstance(vh,list) and isinstance(vn,list):
   c0=collections.Counter(v0);ch=collections.Counter(vh);cn=collections.Counter(vn);assert not (c0-ch) and not (c0-cn)
   assert subseq(vh,vc) and subseq(vn,vc) and collections.Counter(vc)==c0+((ch-c0)|(cn-c0))
  elif vh==v0:assert vc==vn,(key,field)
  elif vn==v0:assert vc==vh,(key,field)
  else:assert vh==vn==vc,(key,field)
assert git("show",":"+ci)==(W/ci).read_bytes()
out["protected_inputs_unchanged"]=True;out["manifest_three_way_all_fields_and_ids_pass"]=True;out["manifest_jobs"]=len(c["jobs"]);out["manifest_sha256"]=dg((W/ci).read_bytes())
check=subprocess.run(g+["diff","--cached","--check",N],capture_output=True);out["owned_whitespace_exit"]=check.returncode;out["owned_whitespace_output"]=check.stdout.decode(errors="replace")+check.stderr.decode(errors="replace")
out["changed_paths_vs_incoming"]=len([x for x in git("diff","--cached","--name-only","-z",N).split(b"\0") if x]);out["finished_at"]=now();outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({"receipt":str(outpath),"sha256":dg(outpath.read_bytes()),"bytes":outpath.stat().st_size,"index":out["index"],"protected_inputs_unchanged":True,"manifest_jobs":out["manifest_jobs"],"manifest_sha256":out["manifest_sha256"],"owned_whitespace_exit":check.returncode,"changed_paths_vs_incoming":out["changed_paths_vs_incoming"],"log_tail":log.read_text(errors="replace")[-1500:]}),flush=True)
assert check.returncode==0
