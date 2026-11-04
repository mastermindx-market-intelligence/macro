"""Independent bounded checks against the exact repaired function bodies.

The Parquet decoder and unrelated FX/extension/RSI functions are substituted.
This does not claim a full import, production acquisition, or rendered proof.
"""
import ast
from copy import deepcopy
from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "candidate"
TODAY = date(2026, 10, 20)
checks = []


def verify(name, condition, detail=None):
    checks.append({"id": name, "passed": bool(condition), "detail": detail})


def load_functions(path, remove_prefixes, initial=None, names=None):
    tree = ast.parse(path.read_text())
    nodes = []
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and any((node.module or "").startswith(p) for p in remove_prefixes):
            continue
        if names is not None and not isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.FunctionDef):
                if node.name not in names:
                    continue
            elif isinstance(node, ast.Assign):
                if not any(isinstance(t, ast.Name) and t.id in names for t in node.targets):
                    continue
            else:
                continue
        nodes.append(node)
    ns = dict(initial or {})
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), ns)
    return ns


inputs = load_functions(CANDIDATE / "lib/intl_country_inputs.py", ["collectors"])
assessment = load_functions(CANDIDATE / "lib/intl_country_assessment.py", ["lib", "engine", "collectors"],
    {"stored_observation_view": inputs["stored_observation_view"],
     "validate_equity_evidence": inputs["validate_equity_evidence"],
     "currency_observation_view": lambda *args, **kwargs: {"value": None, "end_date": None}},
    names={"_number", "_day", "_period_end", "_https", "_mapping", "_metric", "_market", "STATES"})

dates = ["2025-04-01", "2025-07-01", "2025-10-01", "2026-01-01", "2026-04-01"]
values = [100, 800, 700, 600, 102.345]
rows = [{"date": d, "value": v} for d, v in zip(dates, values)]
url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=JPNRGDPEXP"
gdp = inputs["_stored_observation"]("JP", "gdp", rows, url, today=TODAY)
verify("gdp_uses_same_quarter_year_earlier_endpoints", abs(gdp["value"] - 2.345) < 1e-10)
verify("gdp_quarter_end_and_original_quarter_labels", gdp["period"] == "2026-Q2" and gdp["period_end"] == "2026-06-30" and gdp["observations"] == rows)
verify("macro_absent_vintage_remains_absent", gdp["retrieved_at"] is None and gdp["vintage_custody"] == "not_recorded")

for name, altered in [
    ("skipped_quarter", [{"date": "2025-01-01", "value": 100}] + rows[1:]),
    ("duplicate_quarter", rows[:-1] + [dict(rows[-2])]),
    ("monthly_label", rows[:-1] + [{"date": "2026-05-01", "value": 102.345}]),
    ("zero_denominator", [{"date": dates[0], "value": 0}] + rows[1:]),
    ("boolean_level", [{"date": dates[0], "value": True}] + rows[1:]),
    ("interior_nonfinite", rows[:2] + [{"date": dates[2], "value": float("inf")}] + rows[3:]),
]:
    verify("reject_" + name, inputs["_stored_observation"]("JP", "gdp", altered, url, today=TODAY) is None)
verify("reject_future_quarter_before_period_end", inputs["_stored_observation"]("JP", "gdp", rows, url, today=date(2026, 6, 29)) is None)
for label, request in [("wrong_series",url.replace("JPNRGDPEXP","NGDPRSAXDCKRQ")), ("duplicate_id",url+"&id=JPNRGDPEXP"), ("unknown_query",url+"&units=pc1")]:
    verify("reject_"+label, inputs["_stored_observation"]("JP","gdp",rows,request,today=TODAY) is None)

rec = {"cc": "JP", "macro": {"gdp_yoy": 99}, "macro_asof": {"gdp": "2026-09"}}
official = {"gdp": {"value": 1.1, "period": "2024-Q2", "metric": "gdp", "unit": "% y/y", "status": "observed", "provider": "National source", "source_url": "https://example.gov/release"}}
view = assessment["_metric"]("gdp", rec, official, TODAY, {"gdp":gdp})
verify("older_qualified_official_precedence",view["value"]==1.1 and view["evidence"] is None and not view["current"])
for label, change in [("missing",{"value":None}), ("future",{"period":"2027-Q2"}), ("wrong_unit",{"unit":"index"}), ("unusable_source",{"source_url":"http://example.gov/release"})]:
    altered=deepcopy(official);altered["gdp"].update(change)
    view=assessment["_metric"]("gdp",rec,altered,TODAY,{"gdp":gdp})
    verify("stored_fallback_after_"+label,view["evidence"]==gdp and abs(view["value"]-2.345)<1e-10)
view=assessment["_metric"]("gdp",rec,{},TODAY,{})
verify("anonymous_legacy_scalar_not_promoted",view["value"] is None and rec["macro"]["gdp_yoy"]==99)

with TemporaryDirectory(prefix="intl-principal-") as directory:
    root=Path(directory);folder=root/"intl_macro";folder.mkdir()
    path=folder/"JP_gdp.parquet";path.write_bytes(b"decoder fixture")
    cfg={"countries":{"JP":{"fred":{"gdp":"JPNRGDPEXP"}}},"macro":{"fred_base_url":"https://fred.stlouisfed.org/graph/fredgraph.csv"}}
    meta={"schema":"intl_macro_provenance.v1","series":{"JP_gdp":{"provider":"fred_fallback","source_id":"JPNRGDPEXP","source_url":url,"unit":None,"status":"fallback","last_observation":dates[-1]}}}
    frame=pd.DataFrame({"JP_gdp":values},index=pd.to_datetime(dates))
    original_decoder=pd.read_parquet
    pd.read_parquet=lambda p:frame.copy(deep=True)
    try:
        (folder/"provenance.json").write_text(json.dumps(meta))
        admitted=inputs["load_stored_country_observations"](root,cfg,today=TODAY)
        verify("reader_binds_config_metadata_and_raw_column",admitted=={"JP":{"gdp":gdp}})
        meta["series"]["JP_gdp"]["requested_at"]="2099-01-01T00:00:00Z"
        (folder/"provenance.json").write_text(json.dumps(meta))
        verify("reader_does_not_borrow_request_clock",inputs["load_stored_country_observations"](root,cfg,today=TODAY)==admitted)
        meta["series"]["JP_gdp"]["last_observation"]="2026-01-01"
        (folder/"provenance.json").write_text(json.dumps(meta))
        verify("reader_rejects_stale_sidecar_row_binding",inputs["load_stored_country_observations"](root,cfg,today=TODAY)=={})
    finally:
        pd.read_parquet=original_decoder

source = SimpleNamespace(countries=lambda:{"JP":{"index":"^N225"}})
unrelated = {"intl_inputs":source, "extension_signals":lambda m:{}, "rsi":lambda p:pd.Series(50.,index=p.index),
             "EQUITY_OBSERVATION_SCHEMA": inputs["EQUITY_OBSERVATION_SCHEMA"], "equity_source_for":inputs["equity_source_for"]}
engine=load_functions(CANDIDATE/"engine/intl_equity_risk.py",["engine","lib"],unrelated)
base_engine=load_functions(ROOT/"base/engine/intl_equity_risk.py",["engine","lib"],unrelated)
for n in [60,99,100,199,200,252,400]:
    index=pd.bdate_range(end="2026-10-15",periods=n)
    prices=pd.Series(100+np.sin(np.arange(n)/2)+np.arange(n)*0.031,index=index)
    source._intl_closes=lambda:pd.DataFrame({"^N225":prices})
    out=engine["equity_risk_all"]()["JP"]
    old=base_engine["equity_risk_all"]()["JP"]
    verify(f"legacy_scalars_preserved_{n}",{k:v for k,v in out.items() if k!="observation_evidence"}==old)
    evidence=inputs["validate_equity_evidence"](out,"JP",today=TODAY)
    verify(f"equity_actual_windows_{n}",evidence is not None and evidence["mean_200"]["observations"]==min(n,200) and evidence["recent_high"]["start"]==prices.index[-min(n,252)].date().isoformat())
    market=assessment["_market"]({"cc":"JP","equity":out},TODAY)
    verify(f"trend_only_on_complete_200_{n}",(market["state"]=="unknown") if n<200 else market["state"]!="unknown")
    if n==400:
        changed=deepcopy(out);changed["observation_evidence"]["mean_200"]["value"]+=1
        verify("equity_tampered_average_rejected",inputs["validate_equity_evidence"](changed,"JP",today=TODAY) is None)
        custom=engine["equity_risk_all"](pd.DataFrame({"JP":prices}))["JP"]
        verify("custom_matrix_has_no_provider_identity",custom["observation_evidence"] is None)
        later=assessment["_market"]({"cc":"JP","equity":out},date(2026,11,20))
        verify("dated_equity_evidence_preserved_without_current_read",later["state"]=="unknown" and later["drawdown"] is None and later["equity_evidence"]["as_of"]=="2026-10-15")

index=pd.bdate_range(end="2026-10-15",periods=300)
prices=pd.Series(100.001,index=index);prices.iloc[-1]=100.002
source._intl_closes=lambda:pd.DataFrame({"^N225":prices})
out=engine["equity_risk_all"]()["JP"]
evidence=inputs["validate_equity_evidence"](out,"JP",today=TODAY)
verify("strict_comparisons_keep_unrounded_precision",out["price"]==100.0 and evidence["above_50d"] is True and evidence["above_200d"] is True)
prices[:]=100.
out=engine["equity_risk_all"]()["JP"]
evidence=inputs["validate_equity_evidence"](out,"JP",today=TODAY)
verify("equal_average_is_not_above",evidence["above_50d"] is False and evidence["above_200d"] is False and evidence["drawdown_pct"]==0)
verify("latest_tied_high_date",evidence["recent_high"]["high_date"]=="2026-10-15")
verify("equity_missing_acquisition_and_finality",evidence["retrieved_at"] is None and evidence["vintage_custody"]=="not_recorded" and evidence["session_finality"]=="not_verified")

receipt={"patch_sha256":sha256((ROOT.parent/"intl_source_trace_repair.patch").read_bytes()).hexdigest(),
    "checks":checks,"passed":sum(c["passed"] for c in checks),"failed":sum(not c["passed"] for c in checks),
    "limits":["Actual function bodies extracted by AST; unrelated imports substituted.","Local pandas arithmetic executed; Parquet decoding substituted.","No remote process or file mutation; no production acquisition, full import, builder or browser run."]}
(ROOT/"review_checks.json").write_text(json.dumps(receipt,indent=2)+"\n")
print(json.dumps(receipt,indent=2))
raise SystemExit(bool(receipt["failed"]))
