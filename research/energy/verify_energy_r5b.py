"""R5B research integrity/arithmetic checks; not predictive or product validation."""
from pathlib import Path
import json, hashlib
from decimal import Decimal
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parent
MODEL=ROOT/"ENERGY_R5B_HISTORICAL_EXPECTATIONS_MODEL_2026-09-23.json"
m=json.loads(MODEL.read_text())
checks=[]
def ck(name, ok, detail=""):
    checks.append({"name":name,"pass":bool(ok),"detail":detail})
def pct(a,b):
    return (Decimal(str(a))/Decimal(str(b))-1)*100

ck("authority_false", all(v is False for v in m["authority"].values()), m["authority"])
ck("unique_sources", len({s["id"] for s in m["sources"]})==len(m["sources"]), len(m["sources"]))
ck("https_sources", all(urlparse(s["url"]).scheme=="https" for s in m["sources"]), "")
ck("event_date", m["case"]["result_date"]=="2025-02-05")
ck("pre_event_grade_not_exact_archive", "EXACT_BYTE" in m["case"]["historical_vintage_state"] and "NOT_ARCHIVED" in m["case"]["historical_vintage_state"])
ck("pre_event_support_scoped", m["consensus"]["pre_event_independent_timestamp_support"]=={"pre_tax":True,"after_tax":True,"production":True,"eps":False})
ck("confound_present", "Capital Markets Update" in m["case"]["confounder"])
ck("market_not_causal", m["market_context"]["causal_attribution_allowed"] is False)
ck("market_not_reproduced", m["market_context"]["return_classification"]=="EXTERNAL_REPORTED_EVENT_MOVE_NOT_REPRODUCED_RETURN")
ck("acceptance_depth", len(m["acceptance_cases"])>=16, len(m["acceptance_cases"]))

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

ck("net_income_separate", m["actual"]["adjusted_net_income_usd_m"]==1733 and m["actual"]["after_tax_adjusted_operating_income_usd_m"]==2292)
ck("mixed_sign_vector", m["derived_surprises_pct"]["pre_tax_adjusted_operating_income"]>0 and m["derived_surprises_pct"]["adjusted_eps"]<0 and m["derived_surprises_pct"]["equity_production"]<0)
ck("no_trade_authority", not any(m["authority"][k] for k in ["rank","entry","size","trade","fable_handoff"]))

fail=[c for c in checks if not c["pass"]]
result={
 "artifact_type":"r5b_research_integrity_receipt",
 "model_sha256":hashlib.sha256(MODEL.read_bytes()).hexdigest(),
 "passed":len(checks)-len(fail),
 "failed":len(fail),
 "application_tests_run":0,
 "predictive_backtests_run":0,
 "checks":checks,
 "claim_limit":"Research evidence-state and arithmetic checks only; not historical-byte attestation, source-rights admission, causal event-study validation, production behavior or investment merit."
}
(ROOT/"ENERGY_R5B_VERIFICATION_2026-09-23.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({k:v for k,v in result.items() if k!="checks"},indent=2))
if fail:
    print(json.dumps(fail,indent=2))
    raise SystemExit(1)
