from pathlib import Path
import hashlib,json,os,subprocess,time
ROOT=Path("/Volumes/Mastermind/agent-workspaces/macro/web/clear-workstream-blockers-20261104-digest-withdrawal-fence")
BASE="7b3a8d4049fa00f3e498589b5468e82a2d2dc0a3"
PY="/tmp/clear-workstream-blockers-20261103-test-venv/bin/python"
def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=Path("/tmp/cwb10597-client-reference-applied-1104.json")
m=json.loads(manifest.read_text());assert m["mode"]=="APPLIED_COMPLETE" and m["fixed_point"]
assert git("rev-parse","HEAD").decode().strip()==BASE
source=["app/account_prefs.py","lib/site_assets.py","site/account.js","site/theme.js","templates/account.js","templates/theme.js","tests/js/account_continuity.test.mjs","tests/test_deliver_portfolio_digest.py","tests/test_portfolio_digest_consent.py","tests/test_site_assets.py"]
paths=sorted(set(source+[x["path"] for x in m["changes"]]))
assert len(paths)==13982,len(paths)
assert sorted(p for p in git("diff","--name-only","-z").decode().split("\0") if p)==paths
assert not git("diff","--cached","--name-only")
for item in m["changes"]:assert sha(ROOT/item["path"])==item["after_sha256"],item["path"]
for name in ("about.html","chat.html","index.html","movers.html"):
    assert (ROOT/"templates"/name).read_bytes()==(ROOT/"site"/name).read_bytes(),name
before={p:sha(ROOT/p) for p in paths}
pathspec=Path("/tmp/cwb10597-client-pathspec-1104");pathspec.write_bytes(("\0".join(paths)+"\0").encode())
subprocess.run(["git","add","--pathspec-from-file="+str(pathspec),"--pathspec-file-nul"],cwd=ROOT,check=True)
assert sorted(p for p in git("diff","--cached","--name-only","-z").decode().split("\0") if p)==paths
assert not git("diff","--name-only")
tree=git("write-tree","--missing-ok").decode().strip()
candidate=Path("/tmp/cwb10597-client-candidate-1104.json")
candidate.write_text(json.dumps({"base":BASE,"candidate_tree":tree,"paths":paths,"sha256":before,"reference_manifest_sha256":sha(manifest),"paired_html_exact":True},indent=2)+"\n")
print(json.dumps({"phase":"CANDIDATE_STAGED","paths":len(paths),"tree":tree,"candidate_receipt":str(candidate),"sha256":sha(candidate)}),flush=True)
cmd=[PY,"scripts/check_contract_delta.py","--base",BASE]
log=Path("/tmp/cwb10597-client-contract-delta-1104.log")
start=time.monotonic()
with log.open("w") as out:
    r=subprocess.run(cmd,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
after={p:sha(ROOT/p) for p in paths}
result={"base":BASE,"candidate_tree":tree,"command":cmd,"exit":r.returncode,"seconds":round(time.monotonic()-start,2),"log":str(log),"log_sha256":sha(log),"source_hashes_preserved":before==after,"candidate_receipt_sha256":sha(candidate),"tail":"\n".join(log.read_text().splitlines()[-18:])}
receipt=Path("/tmp/cwb10597-client-contract-delta-1104.json");receipt.write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result|{"receipt":str(receipt),"sha256":sha(receipt)}),flush=True)
assert before==after
raise SystemExit(r.returncode)
