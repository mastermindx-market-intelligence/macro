"""R5C research integrity/arithmetic checks; not predictive or product validation."""
from pathlib import Path
import json, hashlib
from decimal import Decimal
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
MODEL=ROOT/"ENERGY_R5C_CLEANER_EVENT_EVALUATION_MODEL_2026-09-23.json"
m=json.loads(MODEL.read_text())
checks=[]
def ck(name, ok, detail=""):
    checks.append({"name":name,"pass":bool(ok),"detail":detail})
def pct(a,b):
    return (Decimal(str(a))/Decimal(str(b))-1)*100

ck("authority_false", all(v is False for v in m["authority"].values()), m["authority"])
ck("unique_sources", len({s["id"] for s in m["sources"]})==len(m["sources"]), len(m["sources"]))
ck("https_sources", all(urlparse(s["url"]).scheme=="https" for s in m["sources"]), "")
ck("cleaner_not_clean", m["case"]["cleanliness"]=="CLEANER_NOT_CLEAN")
ck("vintage_not_overclaimed", "EXACT_VALUE_BYTE_NOT_INDEPENDENTLY_TIMESTAMPED" in m["case"]["historical_vintage_state"])
ck("issuer_process_support", m["consensus"]["issuer_process_support"] is True)
ck("no_false_independent_pre_event_value_support", not any(m["consensus"]["pre_event_independent_timestamp_support"].values()))
ck("causal_attribution_false", m["market_context"]["causal_attribution_allowed"] is False)
ck("return_external_not_reproduced", m["market_context"]["return_classification"]=="EXTERNAL_REPORTED_SAME_DAY_CONTEXT_NOT_REPRODUCED_RETURN")
ck("confound_depth", len(m["confounds"])>=4, len(m["confounds"]))
ck("acceptance_depth", len(m["acceptance_cases"])>=20, len(m["acceptance_cases"]))
ck("eval_grammar_depth", len(m["evaluation_spec"])>=12, len(m["evaluation_spec"]))
pairs=[
("pre_tax_adjusted_operating_income","pre_tax_adjusted_operating_income_usd_m"),
("after_tax_adjusted_operating_income","after_tax_adjusted_operating_income_usd_m"),
("adjusted_eps","adjusted_eps_usd_per_share"),
("equity_production","equity_production_mboe_per_day"),
]
for name,key in pairs:
    got=Decimal(str(m["derived_surprises_pct"][name]))
    exp=pct(m["actual"][key],m["consensus"][key])
    ck("arith_"+name, abs(got-exp)<Decimal("0.000001"), {"got":str(got),"expected":str(exp)})
ck("mixed_vector", m["derived_surprises_pct"]["pre_tax_adjusted_operating_income"]>0 and m["derived_surprises_pct"]["after_tax_adjusted_operating_income"]<0 and m["derived_surprises_pct"]["adjusted_eps"]<0 and m["derived_surprises_pct"]["equity_production"]>0)
ck("issuer_net_income_separate", m["actual"]["adjusted_net_income_usd_m"]!=m["actual"]["after_tax_adjusted_operating_income_usd_m"])
ck("benchmark_residual_arith", abs(Decimal(str(m["market_context"]["equity_minus_osebx_pp"]))-(Decimal("-0.4")-Decimal("1.0")))<Decimal("0.000001"))
ck("empire_preknown", next(x for x in m["confounds"] if x["item"]=="Empire Wind halt order")["same_day_new"] is False)
ck("buyback_same_day", next(x for x in m["confounds"] if x["item"]=="Second 2025 buyback tranche")["same_day_new"] is True)
ck("no_trade_authority", not any(m["authority"][k] for k in ["rank","entry","size","trade","fable_handoff"]))
ck("predictive_gate_frozen", "out-of-sample" in m["evaluation_spec"]["predictive_rule"])

fail=[c for c in checks if not c["pass"]]
result={
 "artifact_type":"r5c_research_integrity_receipt",
 "model_sha256":hashlib.sha256(MODEL.read_bytes()).hexdigest(),
 "dossier_sha256":hashlib.sha256((ROOT/"ENERGY_R5C_CLEANER_EVENT_AND_EVALUATION_GRAMMAR_2026-09-23.md").read_bytes()).hexdigest(),
 "passed":len(checks)-len(fail),"failed":len(fail),
 "application_tests_run":0,"predictive_backtests_run":0,
 "checks":checks,
 "claim_limit":"Research evidence-state, arithmetic and evaluation-grammar checks only; not historical-byte attestation, market-data reproduction, causal event-study validation, product behavior, source-rights admission or investment merit."
}
(ROOT/"ENERGY_R5C_VERIFICATION_2026-09-23.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="checks"},indent=2))
if fail:
    print(json.dumps(fail,indent=2))
    raise SystemExit(1)
