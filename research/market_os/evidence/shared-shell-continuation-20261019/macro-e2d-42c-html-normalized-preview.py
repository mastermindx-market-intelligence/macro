import pathlib,subprocess,json,hashlib,os,sys,re,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");D=E/"macro-e2d-42c-html-normalized-merge"
H="e2d10f933587f58be8716505529a37f8839901f7";B="92c51f1ff800b36fc63e7869243945996ac7315c";M="42c859546ececa797b400db0adeb8c5a22f96832"
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(W),*a])
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M
assert not D.exists();D.mkdir()
os.chdir(W);sys.path.insert(0,str(W))
from scripts.check_template_site_sync import _STAMP_RE
paths=[p for p in git("diff","--name-only","--diff-filter=U").decode().splitlines() if p.startswith("site/") and p.endswith(".html")]
def norm(text):
 count=0
 def replace(m):
  nonlocal count
  asset=m.group(1)
  if ":" in asset or asset.startswith("//") or not asset.endswith((".js",".css")):return m.group(0)
  count+=1
  a=m.start(2)-m.start();b=m.end(2)-m.start()
  return m.group(0)[:a]+"00000000"+m.group(0)[b:]
 return _STAMP_RE.sub(replace,text),count
rows=[]
for p in paths:
 data={}
 prefix=p.replace("/","_")
 for label,rev in [("H",H),("B",B),("M",M)]:
  raw=git("show",rev+":"+p);text,count=norm(raw.decode())
  target=D/(prefix+"."+label);target.write_text(text)
  data[label]={"original_sha256":hashlib.sha256(raw).hexdigest(),"normalized_sha256":hashlib.sha256(text.encode()).hexdigest(),"stamp_count":count,"file":str(target)}
 r=subprocess.run(["git","--no-optional-locks","-C",str(W),"merge-file","-p","--diff3","-L","H","-L","B","-L","M",data["H"]["file"],data["B"]["file"],data["M"]["file"]],capture_output=True)
 assert r.returncode>=0
 result=D/(prefix+".candidate");result.write_bytes(r.stdout)
 row={"path":p,"parents":data,"merge_file_exit":r.returncode,"result":str(result),"result_bytes":len(r.stdout),"result_sha256":hashlib.sha256(r.stdout).hexdigest(),"conflict_markers":r.stdout.count(b"<<<<<<< H"),"stderr":r.stderr.decode(errors="replace")}
 rows.append(row);print(json.dumps({"path":p,"exit":r.returncode,"conflicts":row["conflict_markers"]}),flush=True)
receipt={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":H,"base":B,"incoming":M,"operation":"read-only worktree; normalize only canonical local CSS/JS href/src eight-hex stamps in three immutable inputs; git merge-file standard3way to exclusive evidence scratch","worktree_or_index_written":False,"rows":rows}
raw=(json.dumps(receipt,indent=2)+"\n").encode();(D/"receipt.json").write_bytes(raw)
print(json.dumps({"receipt":str(D/"receipt.json"),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"clean":sum(x["merge_file_exit"]==0 for x in rows),"conflicted":[x["path"] for x in rows if x["merge_file_exit"]!=0]}),flush=True)