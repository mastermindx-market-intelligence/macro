#!/usr/bin/env python3
"""Bounded immutable-source investigation; never imports or runs a collector.

Reads accepted earlier analytical CSVs only after verifying their original
manifest, then reads pinned Git objects. The two historical witnesses are the
nearest reachable price-changing commits before/after each latch timestamp.
Their commit times are repository evidence, NOT vendor availability receipts.
"""
from __future__ import annotations
import argparse, ast, collections, hashlib, io, json, math, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
ORIGINAL_MANIFEST_SHA256 = "80f38bdd75cff63d87190081c4edf027bdce5d564dc23740f9203750b70209c4"
OHLC = ("open", "high", "low", "close")

def clean(x):
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    if isinstance(x, (pd.Timestamp,)): return x.isoformat()
    if isinstance(x, (np.integer,)): return int(x)
    if isinstance(x, (np.bool_,)): return bool(x)
    if isinstance(x, (float, np.floating)): return float(x) if math.isfinite(x) else None
    if x is pd.NA or x is pd.NaT: return None
    return x

def near(a, b, rel=1e-6):
    return a is not None and b is not None and math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b)) <= max(abs(float(a)), abs(float(b)), 1.0)*rel

def classify_bar(old, new):
    """Observable change shape, never a corporate-action attribution."""
    if any(old.get(k) is None or new.get(k) is None for k in OHLC): return "incomplete_ohlc"
    changed = [k for k in OHLC if not near(old[k], new[k])]
    if not changed: return "identical_ohlc"
    if changed == ["open"]: return "open_only_rewrite"
    if all(float(old[k]) > 0 for k in OHLC):
        ratios = [float(new[k])/float(old[k]) for k in OHLC]
        if max(ratios)-min(ratios) <= 1e-5*max(abs(x) for x in ratios): return "uniform_ohlc_scale"
    x=np.array([old[k] for k in OHLC],float);y=np.array([new[k] for k in OHLC],float)
    if np.ptp(x)>1e-6:
        a,b=np.polyfit(x,y,1)
        if a>0 and np.max(abs(y-(a*x+b))) <= max(np.max(abs(y)),1)*1e-5: return "uniform_ohlc_affine"
    return "mixed_field_revision"

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo",default="/Users/chriswong/Documents/Cluade/macro-main")
    ap.add_argument("--prior",default="/tmp/mmx-cn-prophet-historical-20261009/results");ap.add_argument("--out",required=True)
    args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True);prior=Path(args.prior)
    def git(*a): return subprocess.check_output(["git","-C",args.repo,*a])
    original_manifest_bytes=(prior/"manifest.json").read_bytes()
    assert hashlib.sha256(original_manifest_bytes).hexdigest()==ORIGINAL_MANIFEST_SHA256, "prior manifest identity drift"
    original_manifest=json.loads(original_manifest_bytes);prior_inputs={}
    def csv(name):
        b=(prior/name).read_bytes();digest=hashlib.sha256(b).hexdigest()
        assert original_manifest[name]["sha256"]==digest
        prior_inputs[name]={"bytes":len(b),"sha256":digest}
        return pd.read_csv(io.BytesIO(b))
    prod=csv("production_h10_reconciliation.csv");deltas=csv("latch_deltas.csv")
    assert len(deltas)==933 and len(deltas.drop_duplicates(["date","ticker"]))==656
    p4=prod[(prod.board_definition=="cn_prophet_v4") & prod.excess.notna()]
    assert len(p4)==289
    inputs={};frames={}; proc=subprocess.Popen(["git","-C",args.repo,"cat-file","--batch"],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    def blob(path,ref=PIN):
        spec=ref+":"+path;proc.stdin.write((spec+"\n").encode());proc.stdin.flush();head=proc.stdout.readline().decode().strip().split()
        if len(head)!=3: return None
        b=proc.stdout.read(int(head[2]));proc.stdout.read(1)
        inputs[spec]={"git_blob":head[0],"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()};return b
    def frame(path,ref=PIN):
        key=(ref,path)
        if key not in frames:
            b=blob(path,ref)
            if b is None: frames[key]=None
            else:
                d=pd.read_parquet(io.BytesIO(b)).sort_index();d.index=pd.to_datetime(d.index);frames[key]=d
        return frames[key]
    def bar(d,date):
        if d is None or pd.Timestamp(date) not in d.index: return None
        r=d.loc[pd.Timestamp(date)]
        if isinstance(r,pd.DataFrame): raise AssertionError("duplicate bar index")
        return clean({k:r.get(k) for k in (*OHLC,"volume")})
    latch=pd.read_parquet(io.BytesIO(blob("data/china_standout_track/entry_latch.parquet")))
    lm={(str(r.date),str(r.ticker)):r._asdict() for r in latch.itertuples(index=False)}
    source=blob("engine/china_standout_track.py").decode()
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name in ("_dust","_t1_fill_detail")]
    ns={"pd":pd,"_PRICE_REL_TOL":1e-6,"BASIS_T1_OPEN":"t1_open","BASIS_T1_HL2":"t1_hl2","BASIS_T1_CLOSE":"t1_close","BASIS_DEFERRED":"deferred","_warn_corrupt_bar":lambda *a:None}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),"pinned_entry_functions","exec"),ns)
    fill=ns["_t1_fill_detail"]
    history_raw=git("log",PIN,"--format=%H%x09%cI","--","data/china_stocks","data/china_stocks_raw")
    history=[{"commit":x.split("\t")[0],"committed_at":x.split("\t")[1]} for x in history_raw.decode().splitlines()]
    history.sort(key=lambda x:pd.Timestamp(x["committed_at"]))
    reachable=set(git("rev-list",PIN).decode().splitlines())
    assert all(h["commit"] in reachable for h in history), "witness is not an ancestor of study pin"
    history_clock=[pd.Timestamp(x["committed_at"]) for x in history]
    latch_unique=prod[prod.latch_exists==True].drop_duplicates(["date","ticker"])
    changed={(str(r.date),str(r.ticker)) for r in deltas.itertuples()}
    mature={(str(r.date),str(r.ticker)) for r in p4.itertuples()}
    detailed=changed|mature; rows=[];witnesses=[];window_rows=[]
    for index,r in enumerate(latch_unique.itertuples(index=False)):
        key=(str(r.date),str(r.ticker));lr=lm[key];path="data/china_stocks/"+r.ticker+".parquet";rawpath="data/china_stocks_raw/"+r.ticker+".parquet"
        d=frame(path);raw=frame(rawpath)
        if d is None: continue
        now=fill(d,pd.Timestamp(r.date),r.ticker);t1=lr["t1_date"];cb=bar(d,t1);rb=bar(raw,t1)
        assert near(now["entry"],r.entry) or (now["entry"] is None and pd.isna(r.entry)), "current fill disagrees with accepted CSV"
        def value(b,basis):
            if b is None:return None
            if basis=="t1_open":return b["open"]
            if basis=="t1_close":return b["close"]
            if basis=="t1_hl2" and b["high"] is not None and b["low"] is not None:return (b["high"]+b["low"])/2
            return None
        same_basis_value=value(cb,lr["basis_used"]);rv=value(rb,lr["basis_used"])
        if key not in changed:kind="unchanged_derived_entry"
        elif str(now["t1_date"])!=str(t1):kind="first_session_changed"
        elif near(same_basis_value,lr["entry"]) and lr["basis_used"]!=now["basis_used"]:kind="basis_selection_only_at_current_bar"
        elif near(rv,lr["entry"]) and not near(same_basis_value,lr["entry"]):kind="latch_matches_current_raw_same_basis"
        else:kind="same_session_price_or_basis_revision_unresolved"
        rec={"date":r.date,"ticker":r.ticker,"exchange":r.ticker.split(".")[-1],"v4_mature":key in mature,"changed":key in changed,"latched_entry":lr["entry"],"latched_basis":lr["basis_used"],"latched_t1_date":t1,"latched_asof":lr["latched_asof"],"latched_corrupt":lr["corrupt_bar"],"current_entry":now["entry"],"current_basis":now["basis_used"],"current_t1_date":now["t1_date"],"current_corrupt":now["corrupt_bar"],"same_basis_current_value":same_basis_value,"same_basis_raw_value":rv,"classification":kind,"current_bar":cb if key in detailed else None,"raw_bar":rb if key in detailed else None,"raw_ohlc_equal_current":bool(rb and cb and classify_bar(rb,cb)=="identical_ohlc"),"latched_matches_current_fields":[b for b in ["t1_open","t1_hl2","t1_close"] if near(value(cb,b),lr["entry"])],"latched_matches_raw_fields":[b for b in ["t1_open","t1_hl2","t1_close"] if near(value(rb,b),lr["entry"])]}
        rows.append(rec)
        if key not in detailed:continue
        clock=pd.Timestamp(lr["latched_asof"]);before=[i for i,t in enumerate(history_clock) if t<=clock];after=[i for i,t in enumerate(history_clock) if t>=clock]
        for label,ix in [("nearest_commit_before_latch",before[-1] if before else None),("nearest_commit_after_latch",after[0] if after else None)]:
            if ix is None:
                witnesses.append({"date":r.date,"ticker":r.ticker,"label":label,"status":"no_reachable_commit_on_side","latched_asof":lr["latched_asof"]});continue
            h=history[ix];hd=frame(path,h["commit"]);hb=bar(hd,t1)
            w={"date":r.date,"ticker":r.ticker,"label":label,"status":"bar_present" if hb else "exact_bar_absent","commit":h["commit"],"committed_at":h["committed_at"],"ancestor_of_study_pin":h["commit"] in reachable,"witness_clock_source":"git_committer_time","latch_clock_source":"entry_latch.parquet.latched_asof","latched_asof":lr["latched_asof"],"path":path,"bar":hb,"matches_latch_same_basis":near(value(hb,lr["basis_used"]),lr["entry"]),"historical_same_basis_value":value(hb,lr["basis_used"]),"change_shape":classify_bar(hb,cb) if hb and cb else "unavailable"}
            if hb:
                hf=fill(hd,pd.Timestamp(r.date),r.ticker);w.update(derived_fill=hf,matches_latch_current_code=near(hf["entry"],lr["entry"]))
                common=hd.index.intersection(d.index);where=common.get_indexer([pd.Timestamp(t1)])[0]
                days=common[max(0,where-5):where+6] if where>=0 else []
                shapes=[];factors=[];samples=[]
                for day in days:
                    oldbar=bar(hd,day);newbar=bar(d,day);shape=classify_bar(oldbar,newbar);shapes.append(shape)
                    ratio=[newbar[c]/oldbar[c] for c in OHLC if oldbar[c] is not None and oldbar[c]>0 and newbar[c] is not None]
                    factor=float(np.mean(ratio)) if len(ratio)==4 and shape in ("uniform_ohlc_scale","identical_ohlc") else None;factors.append(factor)
                    samples.append({"date":str(day.date()),"old":oldbar,"current":newbar,"change_shape":shape,"scale":factor})
                fs=[x for x in factors if x is not None]
                w["window_shape_counts"]=dict(collections.Counter(shapes));w["window_uniform_scale_all_rows"]=len(fs)==len(days) and bool(len(fs));w["window_scale_monotone"]=bool(fs) and len(fs)==len(days) and (all(b>=a-1e-5 for a,b in zip(fs,fs[1:])) or all(b<=a+1e-5 for a,b in zip(fs,fs[1:])));w["window_scale_min"]=min(fs) if fs else None;w["window_scale_max"]=max(fs) if fs else None
                # Retain exact window bars for only shape-changing matching witnesses;
                # all witnesses retain the exact entry bar and immutable source hashes.
                if w["matches_latch_same_basis"] and w["change_shape"]!="identical_ohlc" and len(window_rows)<40:window_rows.append({"date":r.date,"ticker":r.ticker,"label":label,"commit":h["commit"],"samples":samples})
            witnesses.append(w)
        if index and index%250==0:print("PROGRESS",index,"of",len(latch_unique),flush=True)
    bench_history=[]
    benchraw=git("log",PIN,"--format=%H%x09%cI","--","data/china/510300.SS.parquet")
    for line in benchraw.decode().splitlines():
        ref,stamp=line.split("\t");d=frame("data/china/510300.SS.parquet",ref)
        bench_history.append({"commit":ref,"committed_at":stamp,"columns":list(d.columns),"rows":len(d),"start":str(d.index.min().date()),"end":str(d.index.max().date()),"valid_open_rows":int(pd.to_numeric(d.open,errors="coerce").gt(0).sum()) if "open" in d else 0})
    paths=git("ls-tree","-r","--name-only",PIN).decode().splitlines()
    try:textmatches=git("grep","-I","-l","-e","510300","-e","000300","-e","399300",PIN,"--","data").decode().splitlines()
    except subprocess.CalledProcessError as e:
        if e.returncode!=1:raise
        textmatches=[]
    for p in ["collectors/china_stock_raw.py","collectors/china_stock_prices.py","collectors/china_prices.py","collectors/_stock_ohlc.py","lib/store.py"]:blob(p)
    proc.stdin.close();proc.wait();assert proc.returncode==0
    assert len(rows)==len(latch_unique)==1948
    def counts(xs):
        return {"n":len(xs),"exchange":dict(collections.Counter(x["exchange"] for x in xs)),"classification":dict(collections.Counter(x["classification"] for x in xs)),"latched_basis":dict(collections.Counter(x["latched_basis"] for x in xs)),"current_basis":dict(collections.Counter(x["current_basis"] for x in xs)),"latched_corrupt_n":sum(x["latched_corrupt"] for x in xs),"current_corrupt_n":sum(x["current_corrupt"] for x in xs),"same_t1_date":sum(x["latched_t1_date"]==x["current_t1_date"] for x in xs),"current_raw_equal_adjusted_ohlc":sum(x["raw_ohlc_equal_current"] for x in xs),"matches_any_current_field":sum(bool(x["latched_matches_current_fields"]) for x in xs),"matches_any_raw_field":sum(bool(x["latched_matches_raw_fields"]) for x in xs)}
    def witness_stats(xs):
        return {"n":len(xs),"status":dict(collections.Counter(x["status"] for x in xs)),"matching_stored_basis":sum(x.get("matches_latch_same_basis",False) for x in xs),"matching_current_derivation":sum(x.get("matches_latch_current_code",False) for x in xs),"change_shape":dict(collections.Counter(x.get("change_shape","unavailable") for x in xs)),"matching_change_shape":dict(collections.Counter(x.get("change_shape") for x in xs if x.get("matches_latch_same_basis"))),"matching_uniform_monotone_window":sum(x.get("matches_latch_same_basis",False) and x.get("window_uniform_scale_all_rows",False) and x.get("window_scale_monotone",False) for x in xs)}
    summary={"schema":"cn-prophet-vintage-lab/v1","study_pin":PIN,"original_output_manifest_sha256":ORIGINAL_MANIFEST_SHA256,"prior_inputs":prior_inputs,"limits":["Current raw directory label does not certify original nominal basis.","Historical witnesses are nearest reachable price-changing commits on each side of the self-reported latch timestamp, not exhaustive first-publication reconstruction.","Commit clocks do not certify market-data acquisition, vendor availability, or user-visible publication.","Bar-change shapes describe arithmetic and do not establish a corporate-action/vendor cause.","No collector was run, vendor called, cache altered, or history fetched."],"all_latched_episode_rows":int((prod.latch_exists==True).sum()),"all_latched_unique_entries":counts(rows),"changed_episode_rows":len(deltas),"changed_unique_entries":counts([x for x in rows if x["changed"]]),"mature_v4":counts([x for x in rows if x["v4_mature"]]),"mature_v4_changed":counts([x for x in rows if x["v4_mature"] and x["changed"]]),"reachable_price_history":{"commits":len(history),"earliest":history[0],"latest":history[-1],"git_shallow":git("rev-parse","--is-shallow-repository").decode().strip()},"witnesses":{},"benchmark":{"path":"data/china/510300.SS.parquet","history_versions":len(bench_history),"versions_with_valid_open":sum(x["valid_open_rows"]>0 for x in bench_history),"matching_filename_paths":[p for p in paths if any(s in p.lower() for s in ["510300","000300","399300","csi300","hs300"])],"text_symbol_match_paths":textmatches,"actual_clock_only_comparison":"UNAVAILABLE_NO_VERIFIED_BENCHMARK_OPEN"},"source_blob_count":len(inputs)}
    for cohort,keys in [("changed",changed),("mature_v4",mature)]:
        summary["witnesses"][cohort]={label:witness_stats([w for w in witnesses if (str(w["date"]),str(w["ticker"])) in keys and w["label"]==label]) for label in ["nearest_commit_before_latch","nearest_commit_after_latch"]}
    classes={(x["date"],x["ticker"]):x["classification"] for x in rows}
    p4=p4.copy();p4["classification"]=[classes[(str(r.date),str(r.ticker))] for r in p4.itertuples()]
    summary["v4_fixed_current_exit_accounting_by_class"]={}
    for label,group in p4.groupby("classification"):
        summary["v4_fixed_current_exit_accounting_by_class"][label]={"n":len(group),"latched_mean_excess_pp":group.latch_excess.mean(),"current_mean_excess_pp":group.excess.mean(),"mean_current_minus_latched_pp":(group.excess-group.latch_excess).mean(),"contribution_to_289_row_mean_difference_pp":(group.excess-group.latch_excess).sum()/289,"win_sign_changes":int(((group.excess>0)!=(group.latch_excess>0)).sum()),"original_win_to_current_loss":int(((group.latch_excess>0)&(group.excess<=0)).sum()),"original_loss_to_current_win":int(((group.latch_excess<=0)&(group.excess>0)).sum())}
    summary["v4_accounting_limits"]="These retain the exact same current-at-pin exits and benchmark marks as the accepted production reconstruction. They isolate arithmetic entry differences, not original economic P&L or a return advantage from changing latches. Raw-plane equality is numerical only, and neither a prior matching blob nor a commit clock establishes actual execution or user-visible publication."
    def write(name,value):
        b=json.dumps(clean(value),ensure_ascii=False,separators=(",",":"),allow_nan=False).encode();(out/name).write_bytes(b)
        return {"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
    outputs={"vintage_results.json":write("vintage_results.json",summary),"entry_comparison_rows.json":write("entry_comparison_rows.json",rows),"historical_witness_rows.json":write("historical_witness_rows.json",witnesses),"historical_shape_cases.json":write("historical_shape_cases.json",window_rows),"benchmark_versions.json":write("benchmark_versions.json",bench_history),"vintage_inputs.json":write("vintage_inputs.json",{"source_blobs":inputs,"reachable_price_commits":history,"prior_inputs":prior_inputs,"original_manifest_sha256":ORIGINAL_MANIFEST_SHA256})}
    (out/"output_manifest.json").write_text(json.dumps(outputs,indent=2,sort_keys=True));print(json.dumps(clean(summary),ensure_ascii=False,indent=2));print("OUTPUT_MANIFEST",json.dumps(outputs))

if __name__=="__main__":main()
