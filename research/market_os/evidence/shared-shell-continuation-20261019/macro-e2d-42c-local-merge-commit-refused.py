import pathlib,subprocess,json,hashlib,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27");E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
H="e2d10f933587f58be8716505529a37f8839901f7";M="42c859546ececa797b400db0adeb8c5a22f96832";T="5cb74e747b76b3321e36f4392ac25c40c84a3aef"
g=["git","--no-optional-locks","-C",str(W)];outpath=E/"macro-e2d-42c-local-merge-commit.json";assert not outpath.exists()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*a):return subprocess.check_output(g+list(a))
def dg(b):return hashlib.sha256(b).hexdigest()
assert git("rev-parse","HEAD").decode().strip()==H and git("rev-parse","MERGE_HEAD").decode().strip()==M
assert git("branch","--show-current").decode().strip()=="sol/market-os-shared-shell-design-20260924"
assert git("write-tree").decode().strip()==T and not git("diff","--name-only").strip() and not git("ls-files","-u").strip()
closure=json.loads((E/"macro-e2d-42c-p0b-closure.json").read_text());assert closure["pass"] and closure["after"]["index_tree"]==T
pr=json.loads(subprocess.check_output(["gh","pr","view","7949","--repo","mastermindx-market-intelligence/macro","--json","state,headRefOid,labels,autoMergeRequest"],cwd=W))
assert pr["state"]=="OPEN" and pr["headRefOid"]==H and pr["autoMergeRequest"] is None and "merge-on-green" not in [x["name"] for x in pr["labels"]] and "merge-blocked" in [x["name"] for x in pr["labels"]]
out={"started_at":now(),"head_before":H,"merge_head":M,"tree_before":T,"remote_pr":pr,"purpose":"local ordinary M merge checkpoint to permit subsequent normal main ancestry integration; fresh combined CI/push/publication remain pending","commit_attempted":False}
outpath.write_text(json.dumps(out,indent=2)+"\n")
checklog=E/"macro-e2d-42c-local-merge-whitespace.log";assert not checklog.exists()
p=subprocess.run(g+["diff","--cached","--check"],capture_output=True);checklog.write_bytes(p.stdout+p.stderr);out["whitespace"]={"exit":p.returncode,"log":str(checklog),"sha256":dg(checklog.read_bytes())};outpath.write_text(json.dumps(out,indent=2)+"\n")
if p.returncode:
 print(json.dumps({"precommit_refused":True,"receipt":str(outpath),"log_tail":checklog.read_text(errors="replace")[-5000:]}),flush=True);raise SystemExit(p.returncode)
msg=E/"macro-e2d-42c-local-merge-message.txt";msg.write_text("Merge main 42c859 into original Shared Shell delivery\n\nPreserve both source intents, canonical generated assets, six Sector views,\nand both P0B histories with newly produced fixture/browser receipts.\n\nLocal integration checkpoint only: current-main CI reconciliation, final\nvalidation, push, incumbent merge/render publication and public beta\nacceptance remain owned by the original attended parent.\n")
log=E/"macro-e2d-42c-local-merge-commit.log";assert not log.exists();out["commit_attempted"]=True;out["commit_started_at"]=now();outpath.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({"commit_started_at":out["commit_started_at"]}),flush=True)
with log.open("xb") as f:p=subprocess.run(g+["commit","--file",str(msg)],cwd=W,stdout=f,stderr=subprocess.STDOUT)
out["commit_exit"]=p.returncode;out["finished_at"]=now();out["log"]={"path":str(log),"bytes":log.stat().st_size,"sha256":dg(log.read_bytes())};out["head_after"]=git("rev-parse","HEAD").decode().strip();out["parents_after"]=git("show","-s","--format=%P","HEAD").decode().strip().split();out["tree_after"]=git("rev-parse","HEAD^{tree}").decode().strip();out["status_after"]=git("status","--porcelain=v1","--untracked-files=no").decode().splitlines();outpath.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps({**out,"log_tail":log.read_text(errors="replace")[-2500:],"receipt_sha256":dg(outpath.read_bytes())}),flush=True)
assert p.returncode==0 and out["parents_after"]==[H,M] and out["tree_after"]==T and not out["status_after"]
