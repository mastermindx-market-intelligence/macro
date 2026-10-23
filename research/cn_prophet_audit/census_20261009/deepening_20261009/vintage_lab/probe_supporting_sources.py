#!/usr/bin/env python3
"""Inspect existing action-title metadata and alternative benchmark substrates.

An action-related title is a lead, not an ex-date, ratio, or adjustment bridge.
No filing body is fetched and no external price collection is performed.
"""
import argparse,collections,hashlib,io,json,re,subprocess
from pathlib import Path
import pandas as pd
from collect_vintage_evidence import clean,classify_bar

PIN="3d90aad6d83152dfeeaf8345bc995826ac9d3139"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--repo",default="/Users/chriswong/Documents/Cluade/macro-main");ap.add_argument("--results",required=True);args=ap.parse_args();p=Path(args.results)
    rows=json.loads((p/"entry_comparison_rows.json").read_text());witness=json.loads((p/"historical_witness_rows.json").read_text());rm={(r["date"],r["ticker"]):r for r in rows};inputs={}
    def blob(path,ref=PIN):
        b=subprocess.check_output(["git","-C",args.repo,"show",ref+":"+path]);inputs[path if ref==PIN else ref+":"+path]={"git_blob":hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest(),"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)};return b
    best={}
    for w in witness:
        key=w["date"],w["ticker"]
        if w.get("matches_latch_same_basis") and (key not in best or w["label"]=="nearest_commit_before_latch"):best[key]=w
    qualifications={}
    for label,selected in [("changed_656",[r for r in rows if r["changed"]]),("mature_v4_289",[r for r in rows if r["v4_mature"]])]:
        qualifications[label]={"n":len(selected),"matching_prior_witness":sum((r["date"],r["ticker"]) in best and best[(r["date"],r["ticker"])]["label"]=="nearest_commit_before_latch" for r in selected),"only_later_matching_witness":sum((r["date"],r["ticker"]) in best and best[(r["date"],r["ticker"])]["label"]=="nearest_commit_after_latch" for r in selected),"neither_nearest_witness_matches":sum((r["date"],r["ticker"]) not in best for r in selected),"best_matching_change_shape":dict(collections.Counter(best[(r["date"],r["ticker"])]["change_shape"] for r in selected if (r["date"],r["ticker"]) in best))}
    f=pd.read_parquet(io.BytesIO(blob("data/china_filings/filings.parquet")))
    pat=r"除权|除息|分红|派息|转增|配股|送股";action=f[f.title.fillna("").str.contains(pat,regex=True)].copy()
    affected={r["ticker"].split(".")[0] for r in rows if r["changed"]};v4affected={r["ticker"].split(".")[0] for r in rows if r["changed"] and r["v4_mature"]}
    related=action[action.sec_code.astype(str).isin(affected)]
    retained=clean(related[["announcementId","sec_code","sec_name","title","publish_ts","_collected_at","adjunct_url"]].to_dict("records"))
    closes=pd.read_parquet(io.BytesIO(blob("data/china_search/closes.parquet")))
    aliases={"510300","510300.SS","510300.SH","000300","000300.SS","000300.SH","399300","399300.SZ","CSI300","HS300"}
    state=json.loads(blob("data/china_market_state/latest.json"));hits=[]
    def walk(value,path="$"):
        if isinstance(value,dict):
            if any(str(v) in aliases for v in value.values() if isinstance(v,(str,int,float))) or any(str(k) in aliases for k in value):
                hits.append({"json_path":path,"keys":list(value),"open_like_fields":[k for k in value if "open" in k.lower()],"direct_symbol_values":{k:v for k,v in value.items() if isinstance(v,(str,int,float)) and str(v) in aliases}})
            for k,v in value.items():walk(v,path+"."+k)
        elif isinstance(value,list):
            for i,v in enumerate(value):walk(v,path+"["+str(i)+"]")
    walk(state)
    result={"study_pin":PIN,"source_inputs":inputs,"witness_qualification":qualifications,"corporate_action_metadata":{"filing_rows":len(f),"columns":list(f.columns),"title_keyword":pat,"action_title_rows":len(action),"action_title_distinct_issuers":int(action.sec_code.nunique()),"changed_entry_issuers_with_action_title":int(related.sec_code.nunique()),"related_title_rows":len(related),"mature_v4_changed_issuers_with_action_title":int(action[action.sec_code.astype(str).isin(v4affected)].sec_code.nunique()),"known_limit":"These are title/publication/collection metadata. No ex-date, distribution ratio, split factor or verified event-to-price bridge is present as a structured field. Body extraction and corporate-action verification are separate requirements. No price revision is assigned a corporate-action cause here."},"alternative_benchmark_checks":{"china_search_closes":{"rows":len(closes),"columns":len(closes.columns),"exact_alias_columns":[c for c in closes.columns if str(c) in aliases],"structure":"wide close-only stock matrix"},"china_market_state":{"symbol_bearing_objects":hits,"structure":"current derived state artifact; not a versioned benchmark OHLC store"},"scope":"Frozen Git filename census, the 38 reachable canonical benchmark versions, existing close matrix and current derived China-state artifact. This is not an exhaustive search of external databases or untracked machine files."},"representative_cases":[]}
    # Cases selected for distinct data mechanisms, never for investment outcomes.
    wanted=[("2026-09-03","000962.SZ"),("2026-09-01","600016.SS"),("2026-08-28","301489.SZ"),("2026-08-20","002290.SZ"),("2026-07-21","300803.SZ"),("2026-08-18","301000.SZ")]
    for key in wanted:
        r=rm.get(key)
        if r:
            raw_witness=None;w=best.get(key)
            if w:
                rawpath="data/china_stocks_raw/"+r["ticker"]+".parquet"
                rd=pd.read_parquet(io.BytesIO(blob(rawpath,w["commit"])));rd.index=pd.to_datetime(rd.index)
                if pd.Timestamp(r["latched_t1_date"]) in rd.index:
                    rb=clean({k:rd.loc[pd.Timestamp(r["latched_t1_date"])].get(k) for k in ["open","high","low","close","volume"]})
                    raw_witness={"commit":w["commit"],"committed_at":w["committed_at"],"path":rawpath,"bar":rb,"change_to_current_raw_shape":classify_bar(rb,r["raw_bar"]) if r["raw_bar"] else "unavailable"}
            result["representative_cases"].append({"entry":r,"preferred_matching_witness":w,"raw_at_matching_witness":raw_witness,"action_title_leads":[v for v in retained if v["sec_code"]==key[1].split(".")[0]],"causal_attribution":"UNVERIFIED"})
    (p/"supporting_sources.json").write_text(json.dumps(result,ensure_ascii=False,separators=(",",":"),allow_nan=False))
    (p/"action_title_leads.json").write_text(json.dumps(retained,ensure_ascii=False,separators=(",",":"),allow_nan=False))
    print(json.dumps({"witness_qualification":qualifications,"corporate_action_metadata":result["corporate_action_metadata"],"alternative_benchmark_checks":result["alternative_benchmark_checks"],"representative_cases":len(result["representative_cases"]),"out":"supporting_sources.json"},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
