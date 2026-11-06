import pathlib,subprocess,json,hashlib,os,sys,re,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");D=E/"macro-e2d-42c-html-canonical-merge"
H="e2d10f933587f58be8716505529a37f8839901f7";B="92c51f1ff800b36fc63e7869243945996ac7315c";M="42c859546ececa797b400db0adeb8c5a22f96832"
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(W),*a])
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M
assert not D.exists();D.mkdir()
os.chdir(W);sys.path.insert(0,str(W))
from scripts.optimize_assets import make_optimizer
opt=make_optimizer((W/"site").resolve())
paths=[p for p in git("diff","--name-only","--diff-filter=U").decode().splitlines() if p.startswith("site/") and p.endswith(".html")]
def norm(text,page):
 return opt(text,(W/page).parent.resolve()),None
rows=[]
for p in paths:
 data={}
 prefix=p.replace("/","_")
 for label,rev in [("H",H),("B",B),("M",M)]:
  raw=git("show",rev+":"+p);text,count=norm(raw.decode(),p)
  target=D/(prefix+"."+label);target.write_text(text)
  data[label]={"original_sha256":hashlib.sha256(raw).hexdigest(),"normalized_sha256":hashlib.sha256(text.encode()).hexdigest(),"canonical_owner":"scripts.optimize_assets.make_optimizer","file":str(target)}
 r=subprocess.run(["git","--no-optional-locks","-C",str(W),"merge-file","-p","--diff3","-L","H","-L","B","-L","M",data["H"]["file"],data["B"]["file"],data["M"]["file"]],capture_output=True)
 assert r.returncode>=0
 result=D/(prefix+".candidate");result.write_bytes(r.stdout)
 row={"path":p,"parents":data,"merge_file_exit":r.returncode,"result":str(result),"result_bytes":len(r.stdout),"result_sha256":hashlib.sha256(r.stdout).hexdigest(),"conflict_markers":r.stdout.count(b"<<<<<<< H"),"stderr":r.stderr.decode(errors="replace")}
 rows.append(row);print(json.dumps({"path":p,"exit":r.returncode,"conflicts":row["conflict_markers"]}),flush=True)
receipt={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":H,"base":B,"incoming":M,"operation":"read-only worktree; apply existing scripts.optimize_assets.make_optimizer to all three immutable parent HTML strings using same current assets, then standard git merge-file3way; no placeholder stamps","prior_preapply_guard":{"pid":15057,"exit":1,"effect":"none; all23 prevalidation before writes","reason":"earlier placeholder normalization also touched Sector JS preload hrefs outside optimizer ownership; rejected and replaced by exact canonical owner transformation"},"worktree_or_index_written":False,"rows":rows}
raw=(json.dumps(receipt,indent=2)+"\n").encode();(D/"receipt.json").write_bytes(raw)
print(json.dumps({"receipt":str(D/"receipt.json"),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"clean":sum(x["merge_file_exit"]==0 for x in rows),"conflicted":[x["path"] for x in rows if x["merge_file_exit"]!=0]}),flush=True)