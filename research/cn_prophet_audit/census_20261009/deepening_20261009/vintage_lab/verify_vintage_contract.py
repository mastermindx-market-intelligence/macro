#!/usr/bin/env python3
"""Executable adversarial cases and arithmetic counterfactuals; synthetic unless noted."""
import argparse, copy, json, math
from pathlib import Path
from fill_vintage_contract import EvidenceError,aligned_excess,append_event,digest,legacy_snapshot,mark_from_bar,seal_event
from collect_vintage_evidence import classify_bar

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);ap.add_argument("--evidence",default=None);args=ap.parse_args()
    tests=[]
    def passed(name,details=None):tests.append({"name":name,"result":"PASS","details":details})
    def reject(name,expected,fn):
        try:fn()
        except EvidenceError as e:
            assert str(e)==expected,(name,str(e),expected);passed(name,{"refused_with":str(e)})
        else:raise AssertionError(name+" incorrectly admitted")
    source={"sha256":"a"*64,"clock_kind":"producer_available_at","available_at":"2026-10-09T08:00:00Z","fixture_only":True}
    se=mark_from_bar(ticker="SYNTHETIC.SZ",session="2026-09-16",anchor="session_open",bar={"open":100,"high":102,"low":99,"close":101},source=source,basis_id="synthetic-stock-v1")
    sx=mark_from_bar(ticker="SYNTHETIC.SZ",session="2026-09-29",anchor="session_close",bar={"close":110},source=source,basis_id="synthetic-stock-v1")
    be=mark_from_bar(ticker="SYNTHETIC_BENCH",session="2026-09-16",anchor="session_open",bar={"open":200},source=source,basis_id="synthetic-bench-v1")
    bx=mark_from_bar(ticker="SYNTHETIC_BENCH",session="2026-09-29",anchor="session_close",bar={"close":220},source=source,basis_id="synthetic-bench-v1")
    kwargs={"published_at":"2026-09-15T08:00:00Z","entry_anchor_at":"2026-09-16T01:30:00Z","graded_at":"2026-10-09T08:01:00Z"}
    result=aligned_excess(se,sx,be,bx,**kwargs);assert math.isclose(result["excess_pp"],0,abs_tol=1e-12);passed("aligned fixed-cohort price-mark arithmetic",result)
    reject("benchmark open cannot be synthesized from close","PRICE_FIELD_UNAVAILABLE:open",lambda:mark_from_bar(ticker="510300.SS",session="2026-09-16",anchor="session_open",bar={"close":4.9,"volume":100},source=source,basis_id="unknown"))
    bad=copy.deepcopy(be);bad["anchor"]="session_close";reject("entry-day close is not opening comparator","ENTRY_ANCHOR_MISMATCH",lambda:aligned_excess(se,sx,bad,bx,**kwargs))
    bad=copy.deepcopy(sx);bad["session"]="2026-09-30";reject("mismatched exact exit dates","EXIT_ANCHOR_MISMATCH",lambda:aligned_excess(se,bad,be,bx,**kwargs))
    bad=copy.deepcopy(se);bad["anchor"]="hl2_proxy";reject("HL2 does not acquire an exact execution clock","HL2_EXACT_TIME_UNAVAILABLE",lambda:aligned_excess(bad,sx,be,bx,**kwargs))
    bad=copy.deepcopy(sx);bad["basis_id"]="synthetic-stock-v2";reject("entry and exit cannot mix basis versions","BASIS_ID_MISMATCH",lambda:aligned_excess(se,bad,be,bx,**kwargs))
    bad=copy.deepcopy(sx);bad["source"]["sha256"]="b"*64;reject("same basis label does not permit a different price vintage","WITHIN_INSTRUMENT_VINTAGE_MISMATCH",lambda:aligned_excess(se,bad,be,bx,**kwargs))
    bad=copy.deepcopy(be);bad["source"]["available_at"]="2026-10-10T08:00:00Z";reject("unavailable future source at grading","FUTURE_SOURCE_AT_GRADING",lambda:aligned_excess(se,sx,bad,bx,**kwargs))
    bad=copy.deepcopy(be);bad["source"]["clock_kind"]="git_committer_time";reject("Git commit clock is not a vendor availability receipt","SOURCE_AVAILABILITY_UNVERIFIED",lambda:aligned_excess(se,sx,bad,bx,**kwargs))
    reject("missing publication clock stays explicit","PUBLICATION_CLOCK_UNVERIFIED",lambda:aligned_excess(se,sx,be,bx,**{**kwargs,"published_at":None}))
    reject("late publication cannot support prior opening entry","PUBLICATION_AFTER_ENTRY_ANCHOR",lambda:aligned_excess(se,sx,be,bx,**{**kwargs,"published_at":"2026-09-16T02:00:00Z"}))
    original=seal_event({"kind":"original_entry","decision_id":"synthetic-decision-001","ticker":"SYNTHETIC.SZ","entry_session":"2026-09-16","price":100,"basis":"t1_open","recorded_at":"2026-09-16T08:00:00Z"})
    ledger=append_event([],original);assert append_event(ledger,original)==ledger;passed("exact original replay is idempotent")
    rewritten=seal_event({**{k:v for k,v in original.items() if k!="event_id"},"price":80});reject("silent original-entry rewrite","ORIGINAL_ENTRY_IMMUTABLE",lambda:append_event(ledger,rewritten))
    correction=seal_event({"kind":"entry_correction","decision_id":"synthetic-decision-001","ticker":"SYNTHETIC.SZ","entry_session":"2026-09-16","price":80,"basis":"t1_open","correction_of":original["event_id"],"reason":"New declared comparison vintage, original entry retained","recorded_at":"2026-10-09T08:00:00Z"})
    amended=append_event(ledger,correction);assert len(amended)==2 and amended[0]==original and ledger==[original];passed("correction is separate and original remains identical",{"original_event_id":original["event_id"],"correction_event_id":correction["event_id"]})
    bad=copy.deepcopy(correction);bad["price"]=81;reject("tampered sealed correction","EVENT_HASH_MISMATCH",lambda:append_event(ledger,bad))
    old={"open":16.3,"high":17.7,"low":17.4,"close":17.5};healed={**old,"open":17.5};old_hl2=(old["high"]+old["low"])/2;exit_price=18
    assert classify_bar(old,healed)=="open_only_rewrite" and old_hl2==(healed["high"]+healed["low"])/2
    basis_counterfactual={"type":"SYNTHETIC_MECHANISM_COUNTERFACTUAL","old_bar":old,"healed_bar":healed,"original_hl2":old_hl2,"healed_open":healed["open"],"same_fixed_exit":exit_price,"original_proxy_return_pct":(exit_price/old_hl2-1)*100,"healed_open_return_pct":(exit_price/healed["open"]-1)*100,"interpretation":"The original proxy and later healed open answer different entry-price assumptions. Unchanged HLC explains the difference without a common price-scale transformation. Neither price is evidence of an actual executed trade."}
    passed("basis-only heal preserves HL2 but changes chosen entry assumption",basis_counterfactual)
    scale=.8;old_entry=100;old_exit=110;new_entry=old_entry*scale;new_exit=old_exit*scale
    old_ret=(old_exit/old_entry-1)*100;new_ret=(new_exit/new_entry-1)*100;assert math.isclose(old_ret,new_ret,abs_tol=1e-12)
    assert classify_bar({"open":100,"high":102,"low":98,"close":101},{"open":80,"high":81.6,"low":78.4,"close":80.8})=="uniform_ohlc_scale"
    scale_counterfactual={"type":"SYNTHETIC_MECHANISM_COUNTERFACTUAL","scale":scale,"old_entry":old_entry,"old_exit":old_exit,"new_entry":new_entry,"new_exit":new_exit,"consistent_old_return_pct":old_ret,"consistent_new_return_pct":new_ret,"old_entry_with_new_exit_pct":(new_exit/old_entry-1)*100,"new_entry_with_old_exit_pct":(old_exit/new_entry-1)*100,"interpretation":"A common positive scale applied to BOTH endpoints preserves return. Replacing only one endpoint does not. A real transformation requires identified old/new vintages and a supported adjustment bridge; a numerical pattern alone cannot certify its corporate-action or vendor cause."}
    passed("uniform scale changes price levels while consistent endpoint return is invariant",scale_counterfactual)
    actual_summary=None
    if args.evidence:
        rows=json.loads((Path(args.evidence)/"entry_comparison_rows.json").read_text());snapshots=[]
        for r in rows:
            legacy={"date":r["date"],"ticker":r["ticker"],"entry":r["latched_entry"],"basis_used":r["latched_basis"],"t1_date":r["latched_t1_date"],"corrupt_bar":r["latched_corrupt"],"latched_asof":r["latched_asof"]}
            snap=legacy_snapshot(legacy);assert snap["original"]==legacy and snap["qualification"]=="LEGACY_SOURCE_VINTAGE_UNVERIFIED";snapshots.append(snap)
        actual_summary={"unique_existing_latches_preserved":len(snapshots),"no_automatic_upgrade_from_raw_numerical_match":sum(r["classification"]=="latch_matches_current_raw_same_basis" for r in rows),"snapshot_set_sha256":digest(snapshots)}
        assert len(snapshots)==1948;passed("all existing latch observations remain preserved without invented provenance",actual_summary)
    output={"status":"PASS","scope":"Research-only pure prototype; synthetic counterfactuals and explicit legacy-admission falsifiers. Not a production patch or test-suite claim.","tests":tests,"test_count":len(tests),"actual_legacy_summary":actual_summary}
    Path(args.out).write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False));print(json.dumps({"status":"PASS","test_count":len(tests),"out":args.out}))

if __name__=="__main__":main()
