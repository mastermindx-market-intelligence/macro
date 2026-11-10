"""Render the integrated Prophet page through existing owners with a pinned, immutable source pair."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("--workspace",type=Path,required=True)
p.add_argument("--source-head",required=True)
p.add_argument("--output-prefix",type=Path,required=True)
p.add_argument("--board-sha256",required=True)
p.add_argument("--gate-sha256",required=True)
a=p.parse_args()
root=a.workspace.resolve()
prefix=a.output_prefix
receipt=Path(str(prefix)+".receipt.json")
log_path=Path(str(prefix)+".log")
frozen_path=Path(str(prefix)+".frozen-inputs.json")
sources_path=Path(str(prefix)+".render-inputs.json")
for path in (receipt,log_path,frozen_path,sources_path):
    assert not path.exists(),f"Existing operation requires reconciliation: {path}"
g=lambda args:subprocess.check_output(["git",*args],cwd=root,text=True).strip()
assert g(["rev-parse","HEAD"])==a.source_head
assert not g(["status","--porcelain"]),"Source checkout must start clean."
def digest(path):
    assert not path.is_symlink(),str(path)
    raw=path.read_bytes()
    return {"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
def inventory():
    paths=set()
    for rel in ("data/prophet","data/prophet_arena","site/prophet"):
        paths.update(p for p in (root/rel).rglob("*") if p.is_file())
    paths.update(root/p for p in ("site/factordata/us_standouts.json","site/factordata/signal_gate.json"))
    return {str(p.relative_to(root)):digest(p) for p in sorted(paths)}
source_paths=g(["ls-files","templates","scripts/build_site.py","scripts/inject_data_base.py","scripts/externalize_css.py","scripts/optimize_assets.py","lib/pages.py"]).splitlines()
source_before={rel:digest(root/rel) for rel in source_paths}
frozen_before=inventory()
frozen_path.write_text(json.dumps(frozen_before,indent=2)+"\n")
sources_path.write_text(json.dumps(source_before,indent=2)+"\n")
rec={"head":a.source_head,"workspace":str(root),"started_at":time.time(),"log":str(log_path),"modules":[],
 "source_mode":"existing paired board and existing published Planbook; no origination",
 "pinned_board_sha256":a.board_sha256,"pinned_gate_sha256":a.gate_sha256,
 "frozen_input_count":len(frozen_before),"frozen_inventory":digest(frozen_path),
 "render_input_count":len(source_before),"render_input_inventory":digest(sources_path),
 "render_no_drip":True,"stock_library_refresh":False}
def save():receipt.write_text(json.dumps(rec,indent=2)+"\n")
save()
env=os.environ.copy()
env["RENDER_NO_DRIP"]="1"
env["MACRO_DUMP_VM"]="1"
env["PYTHONUNBUFFERED"]="1"
env.pop("DEEPSEEK_API_KEY",None)
modules=["scripts.build_site","scripts.inject_data_base","scripts.externalize_css","scripts.optimize_assets"]
try:
    with log_path.open("x") as log:
        for module in modules:
            cmd=[sys.executable,"-m",module]
            if module=="scripts.build_site":
                cmd+=["--no-refresh-stock-library","--frozen-us-board-sha256",a.board_sha256,"--frozen-us-gate-sha256",a.gate_sha256]
            started=time.time()
            print("START",module,flush=True)
            log.write("\nMODULE "+module+"\n");log.flush()
            result=subprocess.run(cmd,cwd=root,env=env,stdout=log,stderr=subprocess.STDOUT)
            rec["modules"].append({"module":module,"exit":result.returncode,"seconds":round(time.time()-started,2),"argv":cmd[2:]})
            save()
            print("COMPLETE",module,"exit",result.returncode,"seconds",rec["modules"][-1]["seconds"],flush=True)
            if result.returncode:
                raise RuntimeError(f"{module} exited {result.returncode}; reconcile this operation")
    assert g(["rev-parse","HEAD"])==a.source_head
    frozen_after=inventory()
    changed=sorted(k for k in set(frozen_before)|set(frozen_after) if frozen_before.get(k)!=frozen_after.get(k))
    rec["frozen_changed_paths"]=changed
    rec["frozen_inputs_unchanged"]=not changed
    assert not changed,changed
    rec["render_source_changes"]={rel:{"before":source_before[rel],"after":digest(root/rel) if (root/rel).is_file() else None} for rel in source_paths if not (root/rel).is_file() or source_before[rel]!=digest(root/rel)}
    rec["artifacts"]={rel:digest(root/rel) for rel in ("site/us_stocks.html","site/premiumdata/us_stocks.json","site/factordata/us_standouts.json","site/factordata/signal_gate.json")}
    rec["git_status"]=g(["status","--porcelain"])
    rec["completed_at"]=time.time()
    save()
    print("FROZEN_NATIVE_BUILD_COMPLETE",str(receipt),"frozen_files",len(frozen_before),"source_changes",len(rec["render_source_changes"]),flush=True)
except BaseException as exc:
    rec["failed_at"]=time.time()
    rec["error"]=str(exc)
    try:
        after=inventory()
        rec["frozen_changed_paths"]=sorted(k for k in set(frozen_before)|set(after) if frozen_before.get(k)!=after.get(k))
        rec["frozen_inputs_unchanged"]=not rec["frozen_changed_paths"]
    except Exception as check:
        rec["frozen_verification_error"]=str(check)
    save()
    raise
