"""Apply a CSS-only source follow-up to a completed native build through canonical asset functions."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,time
cli=argparse.ArgumentParser(description=__doc__)
cli.add_argument("--workspace",type=Path,required=True)
cli.add_argument("--base-receipt",type=Path,required=True)
cli.add_argument("--source-head",required=True)
cli.add_argument("--prior-asset-receipt",type=Path)
cli.add_argument("--log",type=Path,required=True)
cli.add_argument("--receipt",type=Path,required=True)
a=cli.parse_args();root=a.workspace.resolve()
def git(*args):return subprocess.check_output(["git",*args],cwd=root,text=True).strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def artifacts():
 return {rel:{"sha256":digest(root/rel),"bytes":(root/rel).stat().st_size} for rel in (
 "site/us_stocks.html","site/premiumdata/us_stocks.json","site/factordata/us_standouts.json",
 "templates/theme.css","site/theme.css","templates/theme.js","site/theme.js","templates/chat.html","site/chat.html")}
assert not a.receipt.exists() and not a.log.exists(),"Reconcile the original operation before trying again."
base=json.loads(a.base_receipt.read_text())
assert base.get("completed_at") and len(base["modules"])==4 and all(x["exit"]==0 for x in base["modules"])
assert Path(base["workspace"]).resolve()==root
prior=json.loads(a.prior_asset_receipt.read_text()) if a.prior_asset_receipt else None
if prior:
 assert prior["base_build_head"]==base["head"] and prior.get("completed_at")
 assert git("rev-parse","HEAD")==prior["source_head"]
 for rel,record in prior["artifacts"].items():assert digest(root/rel)==record["sha256"],rel
else:
 assert git("rev-parse","HEAD")==base["head"]
 for rel,record in base["artifacts"].items():assert digest(root/rel)==record["sha256"],rel
changed=git("diff","--name-only",base["head"],a.source_head).splitlines()
assert set(changed)=={"templates/theme.css","site/theme.css"},changed
assert not git("diff","--name-only","--","templates/theme.css","site/theme.css")
before=artifacts()
rec={"base_build_head":base["head"],"source_head":a.source_head,"workspace":str(root),
 "base_receipt_sha256":digest(a.base_receipt),"source_delta":changed,"before":before,
 "scope":"Completed four-module native build plus a CSS-only canonical asset follow-up. Data and protected fragments are unchanged. This is not a new full data build or production acceptance.",
 "started_at":time.time(),"steps":[],"tool_sha256":digest(Path(__file__)),"prior_asset_receipt_sha256":digest(a.prior_asset_receipt) if a.prior_asset_receipt else None}
def save():a.receipt.write_text(json.dumps(rec,indent=2)+"\n")
save()
with a.log.open("x") as log:
 cmd=["git","merge","--ff-only",a.source_head]
 p=subprocess.run(cmd,cwd=root,stdout=log,stderr=subprocess.STDOUT)
 rec["steps"].append({"command":cmd,"exit":p.returncode});save()
 if p.returncode:raise SystemExit(p.returncode)
 sys.path.insert(0,str(root))
 from lib.site_assets import copy_asset
 copy_asset("theme.css",root/"templates/theme.css",root/"site")
 assert (root/"templates/theme.css").read_bytes()==(root/"site/theme.css").read_bytes()
 command=[sys.executable,"-m","scripts.optimize_assets"]
 start=time.time();p=subprocess.run(command,cwd=root,stdout=log,stderr=subprocess.STDOUT)
 rec["steps"].append({"command":command,"exit":p.returncode,"seconds":round(time.time()-start,2)});save()
 if p.returncode:raise SystemExit(p.returncode)
rec["artifacts"]=artifacts()
for rel in ("site/premiumdata/us_stocks.json","site/factordata/us_standouts.json","templates/theme.js","site/theme.js"):
 assert before[rel]["sha256"]==rec["artifacts"][rel]["sha256"],rel
assert (root/"templates/chat.html").read_bytes()==(root/"site/chat.html").read_bytes()
assert git("rev-parse","HEAD")==a.source_head
rec["protected_and_model_unchanged"]=True
rec["shared_javascript_unchanged"]=True
rec["completed_at"]=time.time();save()
print(json.dumps({"source_head":a.source_head,"source_delta":changed,"steps":rec["steps"],"artifacts":rec["artifacts"],"receipt":str(a.receipt)}),flush=True)
