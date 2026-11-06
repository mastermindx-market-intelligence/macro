#!/usr/bin/env python3
"""Prove where benchmark OHLC is lost; exercise a research-only retention shim.

The existing collector is never imported or run. Only its pure _extract method
is AST-extracted from the pinned Git blob and fed synthetic provider frames.
"""
import argparse,ast,hashlib,json,logging,subprocess
from pathlib import Path
import numpy as np
import pandas as pd

PIN="3d90aad6d83152dfeeaf8345bc995826ac9d3139"
def retain_optional_ohlcv(frame,ticker):
    """Maintain incumbent required Close/Volume; retain available optional OHLC.

Corrupt values remain visible in the observation, with refusal diagnostics.
No range correction, synthetic open, historical fill, or source call occurs.
"""
    names={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"}
    try:
        sub=frame[ticker] if isinstance(frame.columns,pd.MultiIndex) else frame
        sub[["Close","Volume"]]  # preserve incumbent missing-required-field refusal
        observed=sub[[c for c in names if c in sub]].rename(columns=names).dropna(subset=["close"]).copy()
        if observed.empty:return None,{"status":"NO_CLOSE_ROWS"}
    except KeyError:return None,{"status":"MISSING_REQUIRED_COLUMN"}
    refused=[]
    for day,row in observed.iterrows():
        op,hi,lo=row.get("open"),row.get("high"),row.get("low")
        reason=None
        if op is None or pd.isna(op):reason="OPEN_UNAVAILABLE"
        elif not np.isfinite(op) or op<=0:reason="OPEN_INVALID"
        elif hi is None or lo is None or pd.isna(hi) or pd.isna(lo):reason="OPEN_RANGE_UNVERIFIED"
        elif not np.isfinite(hi) or not np.isfinite(lo) or lo<=0 or hi<lo:reason="RANGE_INVALID"
        else:
            dust=max(abs(op),abs(hi),abs(lo),1)*1e-6
            if op<lo-dust or op>hi+dust:reason="OPEN_OUTSIDE_RANGE"
        if reason:refused.append({"session":str(pd.Timestamp(day).date()),"reason":reason})
    return observed,{"status":"OBSERVATIONS_RETAINED","opening_mark_refusals":refused,"qualified_open_rows":len(observed)-len(refused)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo",default="/Users/chriswong/Documents/Cluade/macro-main");ap.add_argument("--out",required=True);args=ap.parse_args()
    path="collectors/china_prices.py";source=subprocess.check_output(["git","-C",args.repo,"show",PIN+":"+path])
    node=next(n for n in ast.walk(ast.parse(source.decode())) if isinstance(n,ast.FunctionDef) and n.name=="_extract")
    ns={"pd":pd,"log":logging.getLogger("bounded_benchmark_probe")};exec(compile(ast.Module(body=[node],type_ignores=[]),"pinned_benchmark_extract","exec"),ns);old=ns["_extract"]
    index=pd.DatetimeIndex(["2026-09-16","2026-09-17"]);f=pd.DataFrame({"Open":[4.8,4.85],"High":[4.9,4.95],"Low":[4.7,4.8],"Close":[4.85,4.9],"Volume":[100.,101.]},index=index)
    incumbent=old(None,f,"510300.SS");candidate,diag=retain_optional_ohlcv(f,"510300.SS")
    assert list(incumbent)==["close","volume"] and "open" not in incumbent
    pd.testing.assert_frame_equal(candidate[["close","volume"]],incumbent);assert diag["qualified_open_rows"]==2
    tests=[{"name":"exact incumbent extractor drops available benchmark OHLC","status":"PASS","observed_columns":list(incumbent)},{"name":"candidate preserves all incumbent Close/Volume values","status":"PASS","observed_columns":list(candidate)}]
    multi=pd.concat({"510300.SS":f},axis=1);m,md=retain_optional_ohlcv(multi,"510300.SS");pd.testing.assert_frame_equal(m,candidate);tests.append({"name":"provider MultiIndex and single-instrument layouts agree","status":"PASS"})
    legacy,ld=retain_optional_ohlcv(f[["Close","Volume"]],"510300.SS");pd.testing.assert_frame_equal(legacy,incumbent);assert ld["qualified_open_rows"]==0 and all(r["reason"]=="OPEN_UNAVAILABLE" for r in ld["opening_mark_refusals"]);tests.append({"name":"legacy close-only schema remains close-only with unavailable opening marks","status":"PASS","diagnostics":ld})
    corrupt=f.copy();corrupt.loc[index[0],"Open"]=9;c,cd=retain_optional_ohlcv(corrupt,"510300.SS");assert c.loc[index[0],"open"]==9 and cd["opening_mark_refusals"]==[{"session":"2026-09-16","reason":"OPEN_OUTSIDE_RANGE"}];tests.append({"name":"corrupt open preserved as observation and refused as opening mark","status":"PASS","diagnostics":cd})
    for label,value,reason in [("zero",0.,"OPEN_INVALID"),("infinite",float("inf"),"OPEN_INVALID"),("NaN",float("nan"),"OPEN_UNAVAILABLE")]:
        bad=f.copy();bad.loc[index[0],"Open"]=value;observed,details=retain_optional_ohlcv(bad,"510300.SS")
        assert pd.isna(observed.loc[index[0],"open"]) if pd.isna(value) else observed.loc[index[0],"open"]==value
        assert observed.loc[index[0],"open"]!=observed.loc[index[0],"close"]
        assert details["opening_mark_refusals"]==[{"session":"2026-09-16","reason":reason}]
        pd.testing.assert_frame_equal(observed[["close","volume"]],incumbent)
        tests.append({"name":label+" open remains refused without close substitution or changing old consumers","status":"PASS","diagnostics":details})
    miss,mi=retain_optional_ohlcv(f.drop(columns=["Close"]),"510300.SS");assert miss is None and mi["status"]=="MISSING_REQUIRED_COLUMN";tests.append({"name":"required Close remains required","status":"PASS"})
    out={"status":"PASS","study_pin":PIN,"source_path":path,"source_sha256":hashlib.sha256(source).hexdigest(),"source_git_blob":hashlib.sha1(b"blob "+str(len(source)).encode()+b"\0"+source).hexdigest(),"source_function_lines":[node.lineno,node.end_lineno],"test_count":len(tests),"tests":tests,"decision":"Extend the existing canonical benchmark collector's extraction contract to retain optional OHLC, attach owned basis/vintage provenance, and qualify opening marks. No new collector or benchmark owner is required. Existing historical close rows must not be backfilled with invented opens.","limits":["All input frames in this probe are explicitly synthetic.","This proves the deterministic field-loss seam and a compatible extraction candidate; it does not establish that the upstream response currently includes every required field for every symbol/date.","No paid/vendor request, historical refresh, store write, production import or installation occurred.","The existing source adjustment guard, storage policies, calendar/session completion and ownership remain implementation review requirements; this shim is not a production-ready patch."]}
    Path(args.out).write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({"status":"PASS","tests":len(tests),"out":args.out}))
if __name__=="__main__":main()
