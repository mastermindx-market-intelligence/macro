"""Native adaptive-weight audit, with synthetic scorecards and no production I/O."""
from __future__ import annotations
import ast
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path
import sys
from types import ModuleType

def main():
    here=Path(__file__).resolve().parent
    raw=(here/"weight_input.json").read_bytes();inp=json.loads(raw)
    checks=[]
    def check(name,value,details=None):
        assert value,name
        checks.append({"name":name,"passed":True,"details":details})
    def git_blob(text):
        b=text.encode();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
    for key,identity in [("signal_lab_source","signal_lab_git_blob"),("altdata_source","altdata_git_blob"),("scorecard_raw","scorecard_git_blob")]:
        check("exact_pinned_"+key,git_blob(inp[key])==inp[identity],{"git_blob":inp[identity]})
    native={"__name__":"native_weight_research"}
    names={"_PRIORS","_VAL_FAMILY"};functions={"load_validation","leg_weights_for"}
    nodes=[];locations={}
    for node in ast.parse(inp["signal_lab_source"]).body:
        if isinstance(node,ast.FunctionDef) and node.name in functions:
            nodes.append(node);locations[node.name]=node.lineno
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets):nodes.append(node)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),"china_signal_lab.py@"+inp["source_sha"],"exec"),native)
    validator=ModuleType("engine.china_validation")
    minimum_line=next(line for line in inp["validation_source_excerpt"].splitlines() if line.startswith("_MIN_PROVEN_N_TS ="))
    exec(compile(minimum_line,"china_validation.py@"+inp["source_sha"],"exec"),validator.__dict__)
    engine=ModuleType("engine");engine.china_validation=validator
    previous={key:sys.modules.get(key) for key in ["engine","engine.china_validation"]}
    sys.modules["engine"]=engine;sys.modules["engine.china_validation"]=validator
    card=json.loads(inp["scorecard_raw"]);scenarios=[]
    try:
        def run(label,source_card,changes,meaning):
            validator.load_scorecard=lambda:source_card
            weights=native["leg_weights_for"]("altdata")
            scenarios.append({"label":label,"synthetic":label!="current_pinned_scorecard",
                              "changes":changes,"weights":weights,"interpretation":meaning})
            return weights
        current=run("current_pinned_scorecard",card,{},"Actual current scorecard; no weight action is inferred from metadata alone.")
        prior=native["_PRIORS"]["altdata"]
        normalized={k:round(v/sum(prior.values()),4) for k,v in prior.items()}
        check("current_weights_equal_unchanged_normalized_priors",current==normalized,{"weights":current})
        check("current_mapped_families_are_not_proven",all(card["families"][name]["proven"] is False for name in ["valuation","margin","fundflow"]))
        check("native_weight_api_has_no_cutoff",list(inspect.signature(native["leg_weights_for"]).parameters)==["consumer"])
        def modify(family,updates,**top):
            x=deepcopy(card);x.update(top);x["families"][family].update(updates);return x
        good={"proven":True,"sign_ok":True,"mean_ic":0.1,"t_hac":3.0,"n_obs":400,"n_weeks":80,"n_indep":20}
        future=modify("valuation",good,generated_utc="2026-10-20T08:00:00Z")
        fw=run("future_scorecard",future,{"family":"valuation",**good,"generated_utc":future["generated_utc"]},"A future card changes native weights. This is a synthetic cutoff-blindness witness, not a detected historical board leak.")
        check("future_card_can_change_weight_without_cutoff",fw!=current and fw["value"]>current["value"])
        weak={"proven":False,"sign_ok":False,"mean_ic":-0.1,"t_hac":-3.0,"n_obs":120,"n_weeks":2,"n_indep":1}
        ww=run("dense_unproven_wrong_sign",modify("valuation",weak),{"family":"valuation",**weak},"The native negative-action branch uses n_obs >= the time-series constant 25, bypassing the cross-sectional weeks/independent-window gate.")
        check("unproven_weakly_independent_result_can_zero_leg",ww["value"]==0 and weak["proven"] is False)
        macro=dict(good,mean_ic=-0.1)
        mw=run("whole_market_margin_verdict",modify("margin",macro),{"family":"margin",**macro},"The macro margin family changes the per-issuer margin leg. Source definitions describe different predictors and targets; current weights are unchanged.")
        check("macro_margin_family_changes_per_issuer_weight",native["_VAL_FAMILY"]["margin"]=="margin" and mw["margin"]>current["margin"])
        for label,updates in [("nan_ic",dict(good,mean_ic="NaN")),("infinite_ic",dict(good,mean_ic="Infinity")),
                              ("truthy_false_verdict_strings",dict(good,proven="false",sign_ok="false"))]:
            w=run(label,modify("valuation",updates),{"family":"valuation",**updates},"Synthetic invalid evidence is consumed by the native reader; the pinned actual scorecard does not contain this payload.")
            check(label+"_can_change_weight",w!=current and w["value"]>current["value"])
    finally:
        for key,value in previous.items():
            if value is None:sys.modules.pop(key,None)
            else:sys.modules[key]=value
    result={"source_sha":inp["source_sha"],"input_sha256":hashlib.sha256(raw).hexdigest(),
            "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "source_locations":locations,"minimum_time_series_n":validator._MIN_PROVEN_N_TS,
            "checks":checks,"check_count":len(checks),"scenarios":scenarios,
            "actual_current_card_generated_utc":card["generated_utc"],
            "actual_current_weight_action":"none: normalized priors retained",
            "estimand_mapping":{"consumer":"per-issuer financing balance change, approximately 20 sessions; positively signed raw alt-data feature",
                                 "validation_family":"whole-market financing balance / float; market-wide CSI300 return timer, contrarian prior",
                                 "qualification":"source-level feature/target mismatch; no current weight action or return effect demonstrated"},
            "implementation_decision":["Freeze the current baseline weights while source-time and calibration contracts are repaired.",
                                       "At the existing calibration reader, bind exact feature, target, horizon, benchmark/basis, artifact and availability identity.",
                                       "Require all evidence labels to mature before the decision cutoff and retain the original scorecard receipt.",
                                       "Apply strict finite-number/Boolean checks and equivalent effective-evidence gates to positive and negative weight actions.",
                                       "Do not use a market-wide timer result as empirical qualification of a per-issuer cross-sectional feature.",
                                       "A qualified calibration reader is a correctness requirement; it does not itself authorize a new ranker or establish investment improvement."],
            "limits":["Unmodified native weight functions are AST-extracted; only the scorecard reader is injected with the pinned or labeled synthetic object.",
                      "No full intelligence, featured selection, historical return, vendor data, source collection or production behavior is recalculated.",
                      "Current scorecard fields are valid for the tested numerical boundaries and currently retain the prior weights.",
                      "The alternative-data and validation headers remain context-only claims; this audit does not grant empirical selection authority."]}
    (here/"weight_results.json").write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"checks":len(checks),"all_passed":True,"current_action":result["actual_current_weight_action"],"scenarios":len(scenarios)}))

if __name__=="__main__":main()
