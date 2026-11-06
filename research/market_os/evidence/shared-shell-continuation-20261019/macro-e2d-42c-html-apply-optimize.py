import pathlib,subprocess,json,hashlib,os,sys,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107");D=E/"macro-e2d-42c-html-canonical-merge"
H="e2d10f933587f58be8716505529a37f8839901f7";M="42c859546ececa797b400db0adeb8c5a22f96832"
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(W),*a])
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M
raw=(D/"receipt.json").read_bytes();assert hashlib.sha256(raw).hexdigest()=="133c6f3951159215cbe73365b80baf2513237ec46e860e3e591a2c3fa60bdcdd"
plan=json.loads(raw);paths=[r["path"] for r in plan["rows"]]
assert len(paths)==23 and all(r["merge_file_exit"]==0 and r["conflict_markers"]==0 for r in plan["rows"])
unmerged=git("diff","--name-only","--diff-filter=U").decode().splitlines();assert all(p in unmerged for p in paths)
os.chdir(W);sys.path.insert(0,str(W))
from scripts.optimize_assets import make_optimizer
from scripts.check_template_site_sync import _STAMP_RE,_sparse_refusal
from lib.shared_shell import inject_shared_shell_text,START,END
from lib.pages import dbase_prefix,write_page
assert not _sparse_refusal(W)
opt=make_optimizer((W/"site").resolve())
versions=[hashlib.sha256((W/"site"/p).read_bytes()).hexdigest()[:8] for p in ["shared_shell_bridge.js","shared_shell.css"]]
prepared={}
for row in plan["rows"]:
 p=row["path"];candidate=pathlib.Path(row["result"]).read_bytes();assert hashlib.sha256(candidate).hexdigest()==row["result_sha256"]
 text=candidate.decode();assert all(mark not in text for mark in ["<<<<<<< H","||||||| B",">>>>>>> M"])
 text=inject_shared_shell_text(text,dbase_prefix(W/p),version=versions[0],css_version=versions[1],site_dir=W/"site")
 text=opt(text,(W/p).parent.resolve())
 remaining=[m.group(0) for m in _STAMP_RE.finditer(text) if m.group(2)=="00000000"]
 assert not remaining,(p,remaining)
 assert text.count(START)==text.count(END)==1
 prepared[p]=text
receipt=E/"macro-e2d-42c-html-apply-optimize.json";assert not receipt.exists()
out={"started_at":now(),"head":H,"incoming":M,"canonical_merge_receipt_sha256":hashlib.sha256(raw).hexdigest(),"prevalidated_paths":paths,"prepared_all23_without_conflicts_or_zero_stamps":True,"commands":[]}
def save():receipt.write_text(json.dumps(out,indent=2)+"\n")
save()
for p,text in prepared.items():write_page(W/p,text)
subprocess.run(["git","--no-optional-locks","-C",str(W),"add","--",*paths],check=True)
out["applied_at"]=now();out["applied_files"]={p:{"bytes":(W/p).stat().st_size,"sha256":hashlib.sha256((W/p).read_bytes()).hexdigest()} for p in paths};save();print(json.dumps({"applied":len(paths),"at":out["applied_at"]}),flush=True)
commands=[("optimizer",[sys.executable,"-B","scripts/optimize_assets.py"]),("template-sync",[sys.executable,"-B","scripts/check_template_site_sync.py"]),("injection-check",[sys.executable,"-B","scripts/inject_shared_shell.py","--check","--site-dir",str(W/"site")])]
for name,args in commands:
 log=E/("macro-e2d-42c-"+name+".log");assert not log.exists()
 row={"name":name,"args":args,"started_at":now(),"log":str(log)};out["commands"].append(row);save();print(json.dumps({"started":name,"at":row["started_at"]}),flush=True)
 with log.open("xb") as f:r=subprocess.run(args,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 data=log.read_bytes();row.update({"finished_at":now(),"exit":r.returncode,"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"tail":data.decode(errors="replace")[-3000:]});save();print(json.dumps({"finished":name,"exit":r.returncode,"tail":row["tail"]}),flush=True)
 if r.returncode!=0:
  print(json.dumps({"stopped_at_failed_gate":name,"receipt":str(receipt)}));raise SystemExit(r.returncode)
out["finished_at"]=now();out["remaining_unmerged"]=git("diff","--name-only","--diff-filter=U").decode().splitlines()
out["unstaged_paths"]=git("diff","--name-only").decode().splitlines()
out["post_optimizer_assets"]={p:hashlib.sha256((W/p).read_bytes()).hexdigest() for p in ["site/theme.js","site/mm_brain.js","site/shared_shell_bridge.js","site/shared_shell.css"]}
save();data=receipt.read_bytes();print(json.dumps({"receipt":str(receipt),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest(),"unstaged_count":len(out["unstaged_paths"]),"remaining_unmerged":out["remaining_unmerged"]}),flush=True)