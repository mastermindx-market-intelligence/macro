"""Run the canonical Prophet publication pipeline from an isolated, pinned checkout."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, sys, time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--workspace", type=Path, required=True)
parser.add_argument("--source-head", required=True)
parser.add_argument("--log", type=Path, required=True)
parser.add_argument("--receipt", type=Path, required=True)
args = parser.parse_args()
root = args.workspace.resolve()
head = subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip()
assert head == args.source_head
assert not subprocess.check_output(["git","status","--porcelain"],cwd=root,text=True).strip(), "Validation checkout must start clean."
assert not args.log.exists() and not args.receipt.exists(), "Reconcile the original build; do not replay this operation."
env = os.environ.copy()
env["RENDER_NO_DRIP"] = "1"
env["MACRO_DUMP_VM"] = "1"
env.pop("DEEPSEEK_API_KEY", None)
rec = {"head": head, "workspace": str(root), "log": str(args.log),
       "started_at": time.time(), "modules": [], "external_refresh_disabled": True}
def save():
    args.receipt.write_text(json.dumps(rec,indent=2) + "\n")
save()
with args.log.open("x") as log:
    for module in ("scripts.build_site", "scripts.inject_data_base",
                   "scripts.externalize_css", "scripts.optimize_assets"):
        started = time.time()
        print("START",module,flush=True)
        log.write("\nMODULE " + module + "\n"); log.flush()
        p = subprocess.run([sys.executable,"-m",module],cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
        rec["modules"].append({"module":module,"exit":p.returncode,"seconds":round(time.time()-started,2)})
        save()
        print("COMPLETE",module,"exit",p.returncode,"seconds",rec["modules"][-1]["seconds"],flush=True)
        if p.returncode:
            rec["failed_at"] = time.time()
            save()
            raise SystemExit(p.returncode)
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=root,text=True).strip() == head
rec["artifacts"] = {}
for rel in ("site/us_stocks.html","site/premiumdata/us_stocks.json","site/factordata/us_standouts.json"):
    path = root / rel
    rec["artifacts"][rel] = {"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size}
rec["completed_at"] = time.time()
save()
print("NORMAL_BUILD_COMPLETE",str(args.receipt),flush=True)
