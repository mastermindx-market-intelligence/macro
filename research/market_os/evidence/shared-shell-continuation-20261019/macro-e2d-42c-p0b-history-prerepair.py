import subprocess,pathlib,json,hashlib,datetime
W=pathlib.Path("/Users/chriswong/Documents/Cluade/macro-main/.claude/worktrees/shared-shell-r27")
E=pathlib.Path("/tmp/shared-shell-css-visual-20261019T1107")
H="e2d10f933587f58be8716505529a37f8839901f7";M="42c859546ececa797b400db0adeb8c5a22f96832"
def git(*a):return subprocess.check_output(["git","--no-optional-locks","-C",str(W),*a])
assert git("rev-parse","HEAD").decode().strip()==H
assert git("rev-parse","MERGE_HEAD").decode().strip()==M
paths=["mockups/evidence/prophet-p0b-zero-fouc/"+n for n in ["manifest.json","mobile-layout.json","mobile-layout-canada.json"]]
unmerged=git("diff","--name-only","--diff-filter=U").decode().splitlines()
assert all(p in unmerged for p in paths)
parent={r:{p:git("show",r+":"+p) for p in paths} for r in [H,M]}
mh=json.loads(parent[H][paths[0]]);mm=json.loads(parent[M][paths[0]])
assert set(mh)==set(mm)
assert all(mh[k]==mm[k] for k in mh if k not in ["repair_extension","repair_extension_history"])
assert mh["repair_extension_history"][:6]==mm["repair_extension_history"][:6]
assert len(mh["repair_extension_history"])==len(mm["repair_extension_history"])==7
history=mh["repair_extension_history"]+mm["repair_extension_history"][6:]
for r,m in [(H,mh),(M,mm)]:
 history.append({"extension":m["repair_extension"],"prior_manifest_sha256":hashlib.sha256(parent[r][paths[0]]).hexdigest(),"source_head":r})
assert len(history)==10
candidate=dict(mh);candidate["repair_extension_history"]=history
for p in paths[1:]:
 assert json.loads(parent[H][p])["historical_baseline"]==json.loads(parent[M][p])["historical_baseline"]
out={paths[0]:(json.dumps(candidate,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode(),**{p:parent[H][p] for p in paths[1:]}}
receipt=E/"macro-e2d-42c-p0b-history-prerepair.json"
assert not receipt.exists()
for p,b in out.items():(W/p).write_bytes(b)
d={"at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"head":H,"incoming":M,"operation":"preserve both complete historical extensions; restore exact H mobile receipts solely as existing producer historical-baseline input","final_candidate_accepted":False,"fresh_browser_run":False,"history_entries":len(history),"parent_receipts":{r:{p:{"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()} for p,b in rows.items()} for r,rows in parent.items()},"intermediate_files":{p:{"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()} for p,b in out.items()},"index_staged":False}
data=(json.dumps(d,indent=2)+"\n").encode();receipt.write_bytes(data)
print(json.dumps(d,indent=2))
print(json.dumps({"receipt":str(receipt),"bytes":len(data),"sha256":hashlib.sha256(data).hexdigest()}))