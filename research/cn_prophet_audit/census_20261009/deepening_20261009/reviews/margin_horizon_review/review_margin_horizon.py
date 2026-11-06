#!/usr/bin/env python3
"""Bounded independent source/lookup/aggregate review; no host data reads."""
from __future__ import annotations
import ast
from collections import Counter
import copy
from datetime import date, timedelta
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pandas as pd

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SNAP = HERE / "reviewed_addendum"
MANIFEST_SHA = "d21ce925119d58094c3248a399374ddd43a4292332588eb92e06046ccb7e8ada"


def sha(b): return hashlib.sha256(b).hexdigest()


def compile_nodes(nodes, scope, filename):
    head = ast.parse("from __future__ import annotations").body
    exec(compile(ast.Module(body=head+copy.deepcopy(nodes), type_ignores=[]), filename, "exec"), scope)


def main():
    raw = (SNAP/"MARGIN_HORIZON_MANIFEST.json").read_bytes(); assert sha(raw) == MANIFEST_SHA
    manifest = json.loads(raw)
    for row in manifest["files"]:
        b = (SNAP/row["path"]).read_bytes()
        assert len(b) == row["bytes"] and sha(b) == row["sha256"], row["path"]
    checks, cases, observations = [], [], {}
    def check(name, okay, details=None, family="source"):
        checks.append({"name":name,"passed":bool(okay),"family":family,"details":details})

    result_raw = (SNAP/"margin_horizon_results.json").read_bytes()
    result = json.loads(result_raw)
    check("exact_final_probe_and_result", sha(result_raw) == "b64f137631c288b9bf85fa4adbf7f3cd4c013fccd2ab316aa83affa8c3bd923d" and
          sha((SNAP/"margin_horizon_probe.py").read_bytes()) == "1ad0ed0e5bd71011fff7b0f7fe5c54a75d9276528798c2b3ee8df0b4cbeb9fc4")
    source_raw = (SNAP/"pinned_margin_collector.py").read_bytes()
    source = source_raw.decode()
    receipts = {x["path"]:x for x in result["receipts"]}
    collector_receipt = receipts["collectors/china_margin_detail.py"]
    blob = hashlib.sha1(b"blob "+str(len(source_raw)).encode()+b"\0"+source_raw).hexdigest()
    check("collector_full_source_bytes_bound", sha(source_raw) == collector_receipt["sha256"] and blob == collector_receipt["git_blob"]
          and len(source_raw) == collector_receipt["bytes"], collector_receipt)
    tree = ast.parse(source)
    lookup = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_first_populated")
    trading = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="_trading_dates")
    refresh = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="refresh")
    lookback_node = next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="LOOKBACK_TD" for t in n.targets))
    lookback = lookback_node.value.value
    def assignment(target):
        return next(n for n in refresh.body if isinstance(n,ast.Assign) and any(isinstance(v,ast.Name) and v.id==target for t in n.targets for v in ast.walk(t)))
    current_node = assignment("cur_date")
    ci_node = next(n for n in refresh.body if isinstance(n,ast.Try) and any(isinstance(c,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="ci" for t in c.targets) for c in n.body))
    prior_slice = assignment("prior_slice")
    prior_lookup = assignment("prior_date")
    current_text = ast.get_source_segment(source,current_node)
    slice_text = ast.get_source_segment(source,prior_slice)
    check("native_lookback_and_current_lookup_contract", lookback==20 and current_text=="cur_date, cur = _first_populated(dates[-3:])",
          {"lookback":lookback,"current_statement":current_text})
    check("native_prior_slice_matches_retained_result", slice_text==result["source_contract"]["prior_slice"], slice_text)
    guard = next(n for n in refresh.body if isinstance(n,ast.If) and "LOOKBACK_TD" in ast.dump(n.test))
    guard_code = compile(ast.Expression(copy.deepcopy(guard.test)), "native_history_guard", "eval")
    check("native_guard_admits_21_rows", eval(guard_code,{"dates":list(range(20)),"LOOKBACK_TD":20}) is True and
          eval(guard_code,{"dates":list(range(21)),"LOOKBACK_TD":20}) is False,
          {"condition":ast.get_source_segment(source,guard.test),"short_history_scenarios_pass_this_guard":True})

    # Exact original probe scenario code, with its host census excluded.
    probe_tree = ast.parse((SNAP/"margin_horizon_probe.py").read_text())
    probe_run = next(n for n in probe_tree.body if isinstance(n,ast.FunctionDef) and n.name=="run")
    scenario_node = next(n for n in probe_run.body if isinstance(n,ast.FunctionDef) and n.name=="scenario")
    cases_node = next(n for n in probe_run.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="cases" for t in n.targets))
    native_scope = {}; compile_nodes([lookup],native_scope,"pinned_lookup_for_exact_probe")
    probe_scope = {"date":date,"timedelta":timedelta,"namespace":native_scope,"lookback":lookback,
                   "slice_code":compile(ast.Expression(copy.deepcopy(prior_slice.value)),"pinned_slice_for_exact_probe","eval")}
    compile_nodes([scenario_node,cases_node],probe_scope,"exact_probe_scenario_block")
    check("all_eight_original_probe_scenarios_exactly_reproduced", probe_scope["cases"]==result["synthetic_cases"] and len(probe_scope["cases"])==8,
          {"n":len(probe_scope["cases"]),"full_host_census_repeated":False},"reproduction")

    fixed = [
        ("full_history_target_20",40,[17,18,19,39],None,39,19),
        ("full_history_fallback_21",40,[17,18,39],None,39,18),
        ("full_history_fallback_22",40,[17,39],None,39,17),
        ("full_history_missing_prior",40,[39],None,39,None),
        ("short_history_21_current_oldest_recent_selects_itself",21,[18],None,18,18),
        ("short_history_21_newly_available_future_can_be_selected",21,[18,19],[18],18,19),
        ("short_history_21_current_middle_uses_19_gap",21,[0,19],None,19,0),
        ("short_history_21_current_latest_uses_20_gap",21,[0,20],None,20,0)]

    def execute_sequence(name,length,available_indices,initial_indices=None):
        days=[(date(2026,1,1)+timedelta(days=i)).strftime("%Y%m%d") for i in range(length)]
        available={days[i]:{"000001.SZ":{"fin_balance":float(1000+i)}} for i in available_indices}
        initial=available if initial_indices is None else {d:copy.deepcopy(available[d]) for d in [days[i] for i in initial_indices]}
        trace=[]; stage={"value":"current"}
        def detail(d):
            mapping=initial if stage["value"]=="current" else available
            value=mapping.get(d,{})
            trace.append({"stage":stage["value"],"index":days.index(d),"populated":bool(value)})
            return copy.deepcopy(value)
        scope={"dates":days,"LOOKBACK_TD":lookback,"_detail_for":detail}
        compile_nodes([lookup],scope,"independent_native_lookup")
        compile_nodes([current_node,ci_node,prior_slice],scope,"native_current_ci_and_slice_statements")
        stage["value"]="prior"
        compile_nodes([prior_lookup],scope,"native_prior_lookup_statement")
        ci=scope["ci"]
        chosen=days.index(scope["prior_date"]) if scope["prior_date"] else None
        bounded=[d for i,d in enumerate(days) if 20 <= ci-i <= 22]
        # This independent enumerated policy oracle has no negative slicing.
        proposed=days[max(0,ci-lookback-2):ci-lookback+1] if ci>=lookback else []
        assert bounded==proposed
        stage["value"]="bounded_prior"
        prior_day,prior_values=scope["_first_populated"](proposed)
        repaired=days.index(prior_day) if prior_day else None
        row={"name":name,"history_length":length,"current_index":ci,
             "candidate_indices":[days.index(d) for d in scope["prior_slice"]],"chosen_index":chosen,
             "source_index_gap":ci-chosen if chosen is not None else None,"bounded_repair_chosen_index":repaired,
             "availability_changes_between_current_and_prior_lookup":initial_indices is not None,"calls":trace}
        return row,scope,(prior_day,prior_values)

    outputs={}
    for name,length,available,initial,want_current,want_prior in fixed:
        got,scope,repaired=execute_sequence(name,length,available,initial)
        retained=next(x for x in result["synthetic_cases"] if x["name"]==name)
        fields=["history_length","current_index","candidate_indices","chosen_index","source_index_gap","bounded_repair_chosen_index","availability_changes_between_current_and_prior_lookup"]
        okay=got["current_index"]==want_current and got["chosen_index"]==want_prior and all(got[k]==retained[k] for k in fields)
        check("independent_native_sequence_"+name,okay,got,"lookup")
        cases.append(got);outputs[name]=(got,scope,repaired)
    future=outputs[fixed[5][0]][0]
    check("future_claim_requires_second_call_availability_change",
          {"stage":"current","index":19,"populated":False} in future["calls"] and
          {"stage":"prior","index":19,"populated":True} in future["calls"] and future["source_index_gap"]==-1,
          future["calls"],"lookup")
    stable,_,_=execute_sequence("stable_newer_date_already_available",21,[18,19])
    check("stable_available_newer_date_is_selected_as_current",stable["current_index"]==19 and stable["chosen_index"] is None,
          stable,"lookup")

    # Verify the first-nonempty store premise with a pure I/O substitute; do
    # not invent a longest-history or merged-calendar selection rule.
    primary=pd.DataFrame({"close":range(21)},index=pd.date_range("2026-01-01",periods=21))
    secondary=pd.DataFrame({"close":range(45)},index=pd.date_range("2025-12-01",periods=45))
    seen=[]
    frames={"000001.SS":primary,"510300.SS":secondary,"399001.SZ":secondary}
    def store_read(group,symbol): seen.append((group,symbol)); return frames.get(symbol)
    trading_scope={"store":SimpleNamespace(read=store_read)}
    compile_nodes([trading],trading_scope,"native_trading_dates")
    got_dates=trading_scope["_trading_dates"](40)
    check("first_nonempty_index_wins_even_if_shorter",len(got_dates)==21 and seen==[("china","000001.SS")],
          {"read_order":seen,"selected_rows":len(got_dates)},"lookup")
    seen.clear();frames["000001.SS"]=None
    fallback=trading_scope["_trading_dates"](40)
    check("existing_index_fallback_order_and_tail_preserved",len(fallback)==40 and seen==[("china","000001.SS"),("china","510300.SS")],
          {"read_order":seen,"selected_rows":len(fallback)},"lookup")

    # Native stored-row construction and exact existing feature consumer.
    cross=json.loads((HERE/"CROSSCHECK_INPUTS.json").read_bytes())
    extras_raw=(HERE/"pinned_china_extras.py").read_bytes()
    extra_id=cross["extras_source_identity"]
    extra_blob=hashlib.sha1(b"blob "+str(len(extras_raw)).encode()+b"\0"+extras_raw).hexdigest()
    check("exact_extras_consumer_source_retained",sha(extras_raw)==extra_id["sha256"] and extra_blob==extra_id["git_blob"],extra_id)
    extra_tree=ast.parse(extras_raw.decode())
    extra_nodes=[n for n in extra_tree.body if isinstance(n,ast.FunctionDef) and n.name in {"_num","margin_positioning"}]
    consumer={};compile_nodes(extra_nodes,consumer,"exact_pinned_margin_consumer")
    prior_default=next(n for n in refresh.body if isinstance(n,ast.Assign) and
                       any(isinstance(t,ast.Name) and t.id=="prior" for t in n.targets))
    cur_iso=assignment("cur_iso")
    rows_node=assignment("rows")
    asof_node=assignment("asof")
    row_loop=next(n for n in refresh.body if isinstance(n,ast.For) and isinstance(n.iter,ast.Call) and isinstance(n.iter.func,ast.Attribute) and isinstance(n.iter.func.value,ast.Name) and n.iter.func.value.id=="cur")
    def stored_rows(scope,prior_pair):
        s={**scope,"pd":pd,"prior_date":prior_pair[0],"prior":prior_pair[1],"asof_today":"2026-10-09"}
        compile_nodes([prior_default,cur_iso,rows_node,asof_node,row_loop],s,"native_stored_row_projection")
        return s["rows"]
    short_name=fixed[4][0]
    _,short_scope,repaired_pair=outputs[short_name]
    unavailable_rows=stored_rows(short_scope,repaired_pair)
    consumer["_read_table"]=lambda *_:pd.DataFrame(unavailable_rows)
    feature=consumer["margin_positioning"]()["000001.SZ"]
    check("bounded_unavailable_prior_stays_nullable_through_consumer",unavailable_rows[0]["fin_balance_prior"] is None and
          unavailable_rows[0]["prior_date"] is None and "chg_pct" not in feature,
          {"stored_rows":unavailable_rows,"consumer_block":feature},"consumer")
    native_pair=(short_scope["prior_date"],short_scope["prior"])
    self_rows=stored_rows(short_scope,native_pair)
    consumer["_read_table"]=lambda *_:pd.DataFrame(self_rows)
    self_feature=consumer["margin_positioning"]()["000001.SZ"]
    check("synthetic_native_self_selection_yields_same_date_zero_change",self_rows[0]["date"]==self_rows[0]["prior_date"] and
          self_feature.get("chg_pct")==0.0,{"stored_row":self_rows[0],"consumer_block":self_feature},"consumer")
    example=pd.DataFrame([{"ticker":"000001.SZ","fin_balance":100.0,"fin_balance_prior":80.0,"date":"2026-09-29","prior_date":"2026-09-01"}])
    consumer["_read_table"]=lambda *_:example
    block=consumer["margin_positioning"]()["000001.SZ"]
    check("consumer_uses_balance_pair_and_drops_prior_date",block.get("chg_pct")==25.0 and block["date"]=="2026-09-29" and "prior_date" not in block,block,"consumer")
    zero_prior=example.assign(fin_balance_prior=0.0);consumer["_read_table"]=lambda *_:zero_prior
    check("nonnull_prior_balance_alone_does_not_guarantee_change", "chg_pct" not in consumer["margin_positioning"]()["000001.SZ"],
          "A positive usable prior is required; nonmissing-balance aggregate counts are not automatically qualified feature counts.","consumer")
    # Whole-source date selection has no per-issuer second chance.
    scope={"cur_date":"20260209","cur":{"000001.SZ":{"fin_balance":100.0},"000002.SZ":{"fin_balance":200.0}}}
    global_prior=("20260120",{"000002.SZ":{"fin_balance":180.0}})
    global_rows=stored_rows(scope,global_prior)
    check("global_prior_date_can_be_present_when_issuer_balance_missing",global_rows[0]["prior_date"]=="2026-01-20" and
          global_rows[0]["fin_balance_prior"] is None and global_rows[1]["fin_balance_prior"]==180.0,global_rows,"consumer")

    # Aggregate reconstruction and cross-inventory receipts only. Raw Parquet
    # rows are not read again; their custody remains the producer's host census.
    data=result["data"];pairs=data["date_pairs"]
    totals=sum(x["rows"] for x in pairs)
    nonmissing=sum(x["nonmissing_prior_balance"] for x in pairs)
    weighted=Counter()
    for p in pairs:
        if p["source_index_gap"] is not None:weighted[str(p["source_index_gap"])]+=p["rows"]
    pair_dates=[p["date"] for p in pairs]
    check("all_62_pair_rows_are_unique_positive_valid_dates",len(pairs)==62 and len(set((p["date"],p["prior_date"]) for p in pairs))==62 and
          len(set(pair_dates))==62 and all(date.fromisoformat(p["prior_date"])<date.fromisoformat(p["date"]) and p["rows"]>0 and
          0<=p["nonmissing_prior_balance"]<=p["rows"] for p in pairs),{"pairs":len(pairs)},"aggregate")
    check("pair_counts_sum_to_155688",totals==data["rows"]==155688,totals,"aggregate")
    check("pair_missing_prior_balances_sum_to_916",totals-nonmissing==data["missing_prior_balance_rows"]==916,
          {"rows":totals,"nonmissing_prior_balance":nonmissing,"missing_prior_balance":totals-nonmissing},"aggregate")
    check("reported_pair_gaps_reproduce_weighted_totals",dict(weighted)==data["known_source_index_gap_weighted_rows"]=={"20":155688} and
          data["rows_without_both_dates_in_index"]==0,dict(weighted),"aggregate")
    latest=max(pair_dates);latest_pairs=[p for p in pairs if p["date"]==latest]
    latest_n=sum(p["rows"] for p in latest_pairs);latest_missing=sum(p["rows"]-p["nonmissing_prior_balance"] for p in latest_pairs)
    check("latest_pair_reconciles_3530_rows_and_9_missing",latest==data["latest_date"]=="2026-10-08" and latest_n==data["latest_rows"]==3530 and
          latest_missing==data["latest_missing_prior_balance"]==9,latest_pairs,"aggregate")
    check("no_missing_prior_dates_in_pair_aggregate",all(p["prior_date"] is not None for p in pairs) and data["missing_prior_date_rows"]==0 and
          data["latest_missing_prior_date"]==0, family="aggregate")
    def normalized_receipt(r):
        return {"bytes":r["bytes"],"sha256":r["sha256"],"git_blob":r.get("git_blob",r.get("git_blob_sha1"))}
    check("detail_receipt_matches_prior_source_inventory",normalized_receipt(receipts["data/china_margin_detail/detail.parquet"])==normalized_receipt(cross["detail_prior_receipt"]),
          cross["detail_prior_receipt"],"receipt")
    check("index_receipt_matches_corrected_native_tradability_census",normalized_receipt(receipts["data/china/000001.SS.parquet"])==normalized_receipt(cross["index_prior_receipt"]),
          cross["index_prior_receipt"],"receipt")
    inventory=cross["detail_prior_clock_inventory"]
    check("detail_rows_and_date_domain_match_prior_inventory",inventory["rows"]==totals and inventory["clock_fields"]["date"]["distinct"]==62 and
          inventory["clock_fields"]["date"]["min"]==min(pair_dates) and inventory["clock_fields"]["date"]["max"]==latest and
          inventory["clock_fields"]["prior_date"]["non_null"]==totals,inventory["clock_fields"],"receipt")
    for rel,key in [("intelligence_lab/source_input.json","source_input_sha256"),("tradability_lab/TRADABILITY_INPUT.json","tradability_input_sha256"),("intelligence_lab/weight_input.json","weight_input_sha256")]:
        check("prior_input_identity_"+rel,sha((ROOT/rel).read_bytes())==cross[key],cross[key],"receipt")
    terminal=json.loads((SNAP/"MARGIN_EXECUTION_RECEIPT.json").read_bytes())
    terminal_text="\n".join(x["text"] for x in terminal["terminal"]["content"] if x["type"]=="text")
    check("retained_host_terminal_exit_zero", "Process completed with exit code 0" in terminal_text,
          {"pid":terminal["process_id"],"terminal":terminal_text},"receipt")
    check("all_eight_sealed_payloads_unchanged",all(sha((ROOT/"intelligence_lab"/r["path"]).read_bytes())==r["sha256"] for r in manifest["files"]),
          {"n":len(manifest["files"])},"custody")
    check("final_manifest_unchanged",sha((ROOT/"intelligence_lab/MARGIN_HORIZON_MANIFEST.json").read_bytes())==MANIFEST_SHA,family="custody")
    observations={"paired_aggregate":{"rows":totals,"pairs":len(pairs),"nonmissing_prior_balance":nonmissing,"missing_prior_balance":totals-nonmissing,
                                      "reported_gap_weighted_rows":dict(weighted),"latest_date":latest,"latest_rows":latest_n,"latest_missing":latest_missing},
                  "exact_consumer_source":{"sha256":sha(extras_raw),"git_blob":extra_blob},
                  "source_locations":{"LOOKBACK_TD":lookback_node.lineno,"current_lookup":current_node.lineno,"prior_slice":prior_slice.lineno,
                                      "prior_lookup":prior_lookup.lineno,"stored_rows":row_loop.lineno,
                                      "margin_positioning":next(n.lineno for n in extra_nodes if n.name=="margin_positioning")}}
    failed=[x for x in checks if not x["passed"]]
    output={"schema":"independent_margin_horizon_review_v1","status":"ACCEPTED_BOUNDED_ADDENDUM" if not failed else "REVIEW_COMPLETE_WITH_BLOCKERS",
            "manifest_sha256":MANIFEST_SHA,"probe_sha256":sha((SNAP/"margin_horizon_probe.py").read_bytes()),"review_script_sha256":sha(Path(__file__).read_bytes()),
            "source_sha":result["pin"],"checks":checks,"check_count":len(checks),"passed_n":len(checks)-len(failed),"failed_n":len(failed),
            "original_scenarios_reproduced":8,"independent_lookup_cases":cases,"observations":observations,"remaining_blockers":failed,
            "limits":["No raw Parquet census was repeated. All 62 aggregate rows and receipt links were reconciled; unique-ticker/raw index-position counts remain the retained hash-bound producer census.",
                      "Source-index gaps are not certified exchange-calendar completeness or first-seen/publication availability.",
                      "Current stored pairs show no underfilled window failure. Self/future/19-position results are explicitly synthetic.",
                      "Eight original scenarios and connecting native statements were executed; the collector, vendor and storage writer were never invoked.",
                      "A nonmissing prior balance is not automatically a positive usable prior or a qualified feature count.",
                      "No broader weight, score, rank, board or investment-return recalculation occurred."],
            "effects":{"production_edits":0,"collector_calls":0,"vendor_calls":0,"host_census_repeats":0,"cache_writes":0,"latch_writes":0},
            "runtime":{"python":sys.version,"pandas":pd.__version__}}
    (HERE/"REVIEW_RESULTS.json").write_text(json.dumps(output,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({"status":output["status"],"checks":len(checks),"passed":len(checks)-len(failed),"failed":len(failed),"original_scenarios":8,"aggregate_pairs":len(pairs),"aggregate_rows":totals}))
    if failed:raise SystemExit(1)


if __name__=="__main__":main()
