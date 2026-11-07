#!/usr/bin/env python3
"""Read-only companion: reconcile legacy diagnostic with raw first/latest boards.

Inputs are deterministic board extractions with original Git blob/commit receipts.
Output is research-only and never upgrades candidate or evidence authority.
"""
import argparse
import hashlib
import json
from pathlib import Path
import pandas as pd
from reproduce_ignition_study import GitSource, REF, LEDGER, FLAGS, clean, describe, write_json, outcome_values


def flatten(boards, variant):
    rows=[]
    for b in boards:
        for r in b.get("buy",[]):
            s=r.get("signal") or {}
            sm=r.get("smartmoney_chip") or {}
            es=r.get("entry_signal") or {}
            nb=r.get("news_burst") or {}
            ps=r.get("prophet") or {}
            record={"variant":variant,"as_of":b["as_of"],"ticker":r["ticker"],
                    "source_blob":b["source_blob"],"source_commit":b["source_commit"],
                    "source_commit_at":b["source_commit_at"],"source_sha256":b["source_sha256"],
                    "emit_at":(b.get("emit") or {}).get("at_utc"),
                    "raw_tier":s.get("tier_cascade"),"tier_event_date":s.get("tier_event_date"),
                    "tier_observed_date":s.get("tier_observed_date"),"anchor_era":s.get("anchor_era"),
                    "tier_observation_provisional":s.get("tier_observation_provisional"),
                    "board_definition":b.get("board_definition"),
                    "selection_era":(b.get("ranking") or {}).get("selection_era"),
                    "raw_news_burst":bool((nb.get("n_recent") or 0)>=3),
                    "raw_sue_fresh":bool(r.get("sue_z") and (r.get("sue_fresh_days") or 999)<=60),
                    "raw_smartmoney_add":bool(sm),
                    "news_n_recent":nb.get("n_recent"),"news_n_pos":nb.get("n_pos"),"news_n_neg":nb.get("n_neg"),
                    "news_sentiment_lean":nb.get("sentiment_lean"),"sue_z":r.get("sue_z"),
                    "sue_fresh_days":r.get("sue_fresh_days"),"ownership_period_end":sm.get("period_end"),
                    "ownership_staleness_label":sm.get("staleness_caveat"),"ownership_fund":sm.get("best_fund"),
                    "ownership_grade":sm.get("best_grade"),"ownership_action":sm.get("action"),
                    "raw_entry_status":es.get("status"),"board_spot":es.get("spot",r.get("price")),
                    "board_price":r.get("price"),"buy_zone_low":(es.get("buy_zone") or {}).get("low"),
                    "buy_zone_high":(es.get("buy_zone") or {}).get("high"),"chase_above":es.get("chase_above"),
                    "c1_score":ps.get("score"),"c1_score_rank":r.get("score_rank"),"raw_alpha":r.get("alpha"),
                    "raw_off_high":r.get("off_high"),"ext_z":r.get("ext_z"),"sector":r.get("sector"),
                    "mixed_vintage":(((b.get("staleness") or {}).get("inputs") or {}).get("panel") or {}).get("mixed_vintage"),
                    "source_delayed":(b.get("staleness") or {}).get("delayed")}
            record["raw_evidence_n"]=sum(record[k] for k in ("raw_news_burst","raw_sue_fresh","raw_smartmoney_add"))
            rows.append(record)
    return pd.DataFrame(rows)


def event_key_diagnostic(overlap, ids, label):
    """Deduplicate complete analysis keys, disclosing missingness and provisional rows.

    This is a raw-board/legacy-flag sensitivity, not a certification of freshness,
    canonical episode identity, serving visibility or point-in-time evidence.
    """
    candidates=overlap[overlap.raw_tier.eq("T2")].copy()
    missing=pd.DataFrame({k:candidates[k].isna() | candidates[k].astype("string").str.strip().eq("").fillna(False)
                          for k in ids},index=candidates.index)
    complete=candidates[~missing.any(axis=1)].copy()
    event=complete.sort_values(["as_of","ticker"]).drop_duplicates(ids)
    def provisional_counts(frame):
        values=frame.tier_observation_provisional
        yes=int(values.eq(True).sum());no=int(values.eq(False).sum())
        return {"true":yes,"false":no,"unknown":len(frame)-yes-no}
    return {"status":label+"; analysis key only, not canonical B1 identity or strict exposure; incomplete raw-date coverage disclosed; provisional and unknown status retained and counted",
            "key":ids,"source_T2_rows":len(candidates),
            "missing_components":{k:int(missing[k].sum()) for k in ids},
            "rows_with_any_missing_component":int(missing.any(axis=1).sum()),
            "key_complete_T2_rows":len(complete),
            "source_T2_provisional_status":provisional_counts(candidates),
            "key_complete_T2_provisional_status":provisional_counts(complete),
            "n":len(event),"tickers":event.ticker.nunique(),
            "event_provisional_status":provisional_counts(event),
            "event_evidence_flag_counts":{f:int(event["raw_"+f].sum()) for f in FLAGS},
            "event_evidence_count_distribution":{str(k):int(event.raw_evidence_n.eq(k).sum()) for k in range(4)},
            "ge2":describe(event[event.raw_evidence_n.ge(2)]),
            "lt2":describe(event[event.raw_evidence_n.lt(2)])}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo",required=True,type=Path)
    p.add_argument("--history-repo",required=True,type=Path)
    p.add_argument("--boards-first",required=True,type=Path)
    p.add_argument("--boards-latest",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if (a.out/"IGNITION_BOARD_CLOCKS_2026-10-06.json").exists():
        p.error("Preserve earlier output; choose a new directory")
    src=GitSource(a.repo,REF)
    d=src.parquet(LEDGER)
    h=d[(d.rank_by=="us_prophet_v3")&(d.lane=="buy")&(d.horizon==5)].copy()
    h["evidence_n"]=h[FLAGS].astype("boolean").sum(axis=1,min_count=3)
    h["convergence_legacy"]=h.evidence_n.ge(2)
    first=h[h.tier_cascade.eq("T2")].sort_values(["as_of","ticker"]).drop_duplicates("ticker")
    exposed=first[first.convergence_legacy]
    variants={};digest={}
    for name,path in [("first",a.boards_first),("latest",a.boards_latest)]:
        data=path.read_bytes();digest[name]={"sha256":hashlib.sha256(data).hexdigest(),"input_path":str(path)}
        variants[name]=flatten(json.loads(data),name)
    raw=pd.concat(variants.values(),ignore_index=True)
    raw.to_csv(a.out/"raw_board_clock_covariates_2026-10-06.csv",index=False)
    result={"status":"DISCOVERY_ONLY_NO_EXECUTION_OR_PROMOTION_AUTHORITY","source_ref":REF,
            "board_extraction_digests":digest,"raw_dates":{k:v.as_of.nunique() for k,v in variants.items()},
            "coverage":{},"first_issuer_cases":[],"actual_C1_negative_controls":{},"event_key_sensitivity":{},
            "prereg_shaped_event_key_sensitivity":{}}
    for name,v in variants.items():
        overlap=h.merge(v,on=["as_of","ticker"],suffixes=("","_raw"),validate="one_to_one")
        result["coverage"][name]={"h5_buy_ledger_rows":len(h),"joined_raw_rows":len(overlap),
                                  "tier_mismatch":int(overlap.tier_cascade.fillna("").ne(overlap.raw_tier.fillna("")).sum()),
                                  "flag_mismatch":{f:int(overlap[f].ne(overlap["raw_"+f]).sum()) for f in FLAGS},
                                  "convergence_mismatch":int(overlap.convergence_legacy.ne(overlap.raw_evidence_n.ge(2)).sum())}
        # Actual C1 score: compare only same raw-board overlap; a separate descriptive control.
        overlap["c1_pct"]=overlap.groupby("as_of").c1_score.rank(pct=True,method="average")
        high=overlap[overlap.c1_pct.ge(.9)&overlap.raw_evidence_n.eq(0)].sort_values(["as_of","ticker"]).drop_duplicates("ticker")
        result["actual_C1_negative_controls"][name]=describe(high)
        ids=["ticker","tier_event_date","anchor_era","board_definition","selection_era"]
        result["event_key_sensitivity"][name]=event_key_diagnostic(overlap,ids,"Coarser key omits tier_observed_date")
        full_ids=["ticker","tier_event_date","tier_observed_date","anchor_era","board_definition","selection_era"]
        result["prereg_shaped_event_key_sensitivity"][name]=event_key_diagnostic(overlap,full_ids,"Full prereg-shaped key includes tier_observed_date")
    # Directly verify the original five raw source blobs in the historical object repo.
    import subprocess
    verified={}
    for _,row in exposed.iterrows():
        for name,v in variants.items():
            z=v[v.as_of.eq(row.as_of)&v.ticker.eq(row.ticker)]
            if not len(z):
                continue
            z=z.iloc[0]
            if z.source_blob not in verified:
                b=subprocess.check_output(["git","-C",str(a.history_repo),"cat-file","blob",z.source_blob])
                assert hashlib.sha1(f"blob {len(b)}\0".encode()+b).hexdigest()==z.source_blob
                assert hashlib.sha256(b).hexdigest()==z.source_sha256
                verified[z.source_blob]={"sha256":z.source_sha256,"bytes":len(b)}
            rec=z.to_dict()
            rec.update({"ledger_entry_date":row.entry_date,"ledger_H5_ret":row.ret,
                        "ledger_H5_excess_spy":row.excess_spy,"ledger_evidence_n":row.evidence_n,
                        "publication_status":"First Git receipt bounds preserved visibility, not actual user-facing publication or fill"})
            spy=src.price("SPY",benchmark=True);px=src.price(row.ticker)
            receipt=pd.Timestamp(z.source_commit_at)
            emits=pd.Timestamp(z.emit_at) if pd.notna(z.emit_at) else receipt
            receipt=max(receipt,emits)
            opens=(spy.index.tz_localize("America/New_York")+pd.Timedelta(hours=9,minutes=30)).tz_convert("UTC")
            j=opens.searchsorted(receipt)
            if j<len(opens) and px is not None:
                date=spy.index[j]
                rec["first_regular_open_after_receipt_date"]=str(date.date())
                rec["receipt_later_than_ledger_entry_open"]=date>pd.Timestamp(row.entry_date)
                if date in px.index:
                    rec["conditional_open_after_receipt_adjusted"]=px.loc[date].get("open")
                amended=row.copy();amended["as_of"]=str((date-pd.Timedelta(days=1)).date())
                out=outcome_values(src,amended,5)
                rec["post_receipt_H5_status"]=out.get("outcome_status")
                rec["post_receipt_H5_hypothetical_open_return"]=out.get("conditional_next_open_ret_same_endpoint")
                rec["post_receipt_H5_hypothetical_open_excess_spy"]=out.get("conditional_next_open_excess_spy")
                rec["post_receipt_H5_end_date"]=out.get("horizon_date")
                if pd.Timestamp(row.as_of) in px.index:
                    rec["asof_close_final_vintage_adjusted"]=px.loc[pd.Timestamp(row.as_of),"close"]
                    if pd.notna(z.board_price) and z.board_price>0:
                        rec["board_price_vs_final_vintage_close_ratio"]=z.board_price/rec["asof_close_final_vintage_adjusted"]
                rec["geometry_executability_status"]="UNPROVEN: board nominal geometry vs adjusted opening prices; receipt is not public delivery; availability gate retained"
            result["first_issuer_cases"].append(rec)
    result["verified_raw_blobs"]=verified
    result["strict_primary_disposition"]="NOT_ESTIMABLE. Raw T2 event clocks improve observability but do not supply decision-cut independent evidence lineage or prove serving-time publication."
    write_json(a.out/"IGNITION_BOARD_CLOCKS_2026-10-06.json",result)
    pd.DataFrame(result["first_issuer_cases"]).to_csv(a.out/"five_exposure_publication_clocks_2026-10-06.csv",index=False)
    print(json.dumps(clean({"coverage":result["coverage"],"event_key_sensitivity":result["event_key_sensitivity"],
                           "prereg_shaped_event_key_sensitivity":result["prereg_shaped_event_key_sensitivity"],
                           "verified_raw_blobs":len(verified)}),indent=2))


if __name__=="__main__":
    main()
