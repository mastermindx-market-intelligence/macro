"""R11 research oracle for invented Consumer examples, NOT a production adapter.
Standard library only; no network, repository imports, native IDs, rights decisions or publication.
"""
from __future__ import annotations
import copy
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
import json
from pathlib import Path
import re
import sys

class ResearchRefusal(ValueError):
    pass

FACT_KEYS = {
    "key", "metric", "value_text", "unit", "scale_power10", "period_start", "period_end",
    "role", "target", "kind", "sign_convention", "basis", "perimeter", "definition",
    "event", "evidence", "native_ref", "native_admitted"
}
AUTH_KEYS = {"can_rank", "can_gate", "can_size", "can_originate", "can_open_entry"}
CONTEXT = ("unit", "scale_power10", "basis", "perimeter", "definition", "kind")
DECIMAL_TEXT = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
METRICS = {
 "pass_through": {
    "revenue_new":"total_revenue", "revenue_old":"total_revenue",
    "fund_revenue_new":"fund_revenue", "fund_revenue_old":"fund_revenue",
    "fund_expense_new":"fund_expense", "fund_expense_old":"fund_expense"},
 "cash_bridge": {
    "operating_cash":"operating_cash", "capital_cash":"capital_cash",
    "asset_proceeds":"asset_proceeds", "issuer_defined_total":"issuer_defined_total"},
 "outlook_revision": {
    "prior_low":"revenue_outlook_low", "prior_high":"revenue_outlook_high",
    "new_low":"revenue_outlook_low", "new_high":"revenue_outlook_high"}
}
BASES = {
 "pass_through":"explicit_same_quarter_prior_year",
 "cash_bridge":"same_interval_signed_cash",
 "outlook_revision":"two_outlooks_same_target"
}

def refuse(code: str) -> None:
    raise ResearchRefusal(code)

def decimal_text(v: object) -> Decimal:
    if not isinstance(v, str) or len(v) > 48 or not DECIMAL_TEXT.fullmatch(v):
        refuse("decimal_text_required")
    return Decimal(v)

def text(v: Decimal) -> str:
    s = format(v, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in {"-0", ""} else s

def read_facts(case: dict) -> tuple[dict, dict]:
    recipe = case["recipe"]
    if recipe not in METRICS:
        refuse("unsupported_recipe")
    if case.get("comparison_basis") != BASES[recipe]:
        refuse("comparison_basis")
    fs = case.get("facts")
    if not isinstance(fs, list) or not fs:
        refuse("facts_missing")
    keyed, numeric = {}, {}
    for item in fs:
        if not isinstance(item, dict) or set(item) != FACT_KEYS:
            refuse("fact_shape")
        key = item["key"]
        if key in keyed:
            refuse("duplicate_input_key")
        if key not in METRICS[recipe] or item["metric"] != METRICS[recipe][key]:
            refuse("metric_binding")
        for field in ("unit", "basis", "perimeter", "definition", "event"):
            if not isinstance(item[field], str) or not item[field].strip():
                refuse("context_unknown")
        if type(item["scale_power10"]) is not int or not -9 <= item["scale_power10"] <= 12:
            refuse("scale_invalid")
        if item["role"] not in {"actual", "outlook"}:
            refuse("role_invalid")
        if item["kind"] not in {"financial", "physical"}:
            refuse("kind_invalid")
        if item["sign_convention"] != "signed":
            refuse("sign_convention")
        ev = item["evidence"]
        if not isinstance(ev, dict) or set(ev) != {"document", "revision", "locator"}:
            refuse("evidence_shape")
        if not all(isinstance(v, str) and v for v in ev.values()):
            refuse("evidence_missing")
        if not ev["document"].startswith("https://example.invalid/"):
            refuse("not_invented_source")
        if item["native_ref"] is not None or item["native_admitted"] is not False:
            refuse("native_claim_forbidden")
        try:
            start, end = date.fromisoformat(item["period_start"]), date.fromisoformat(item["period_end"])
        except (TypeError, ValueError):
            refuse("period_invalid")
        if start > end:
            refuse("period_order")
        value = decimal_text(item["value_text"])
        if item["kind"] == "physical" and value < 0:
            refuse("negative_physical_quantity")
        keyed[key], numeric[key] = item, value
    if set(keyed) != set(METRICS[recipe]):
        refuse("required_input_missing")
    values = list(keyed.values())
    for fld in CONTEXT:
        if any(item[fld] != values[0][fld] for item in values[1:]):
            refuse("context_mismatch:" + fld)
    if values[0]["kind"] != "financial":
        refuse("financial_recipe_required")
    return keyed, numeric

def same_period(items: list[dict]) -> None:
    intervals = {(f["period_start"], f["period_end"]) for f in items}
    if len(intervals) != 1:
        refuse("period_mismatch")

def same_event(items: list[dict]) -> None:
    if len({f["event"] for f in items}) != 1:
        refuse("event_mismatch")
    if len({f["evidence"]["revision"] for f in items}) != 1:
        refuse("mixed_document_revision")

def run_case(case: dict) -> dict:
    fs, n = read_facts(case)
    recipe = case["recipe"]
    if recipe != "outlook_revision" and any(f["role"] != "actual" or f["target"] is not None for f in fs.values()):
        refuse("actual_role_required")
    with localcontext() as ctx:
        ctx.prec = 80
        if recipe == "pass_through":
            new = [v for k, v in fs.items() if k.endswith("_new")]
            old = [v for k, v in fs.items() if k.endswith("_old")]
            same_period(new); same_period(old)
            same_event(new); same_event(old)
            if old[0]["period_end"] >= new[0]["period_start"]:
                refuse("comparison_period_order")
            # Comparability of the quarter populations is declared in this invented
            # example, not inferred by calendar arithmetic.
            rd = n["revenue_new"] - n["revenue_old"]
            fr = n["fund_revenue_new"] - n["fund_revenue_old"]
            fe = n["fund_expense_new"] - n["fund_expense_old"]
            result = {"revenue_change":text(rd), "fund_revenue_change":text(fr),
                      "fund_expense_change":text(fe), "fund_net_change":text(fr-fe),
                      "revenue_change_excluding_fund":text(rd-fr),
                      "fund_share_of_revenue_change_pct":text(fr/rd*100) if rd > 0 else None}
            omissions = [] if rd > 0 else ["ratio_not_interpretable_without_positive_revenue_change"]
        elif recipe == "cash_bridge":
            same_period(list(fs.values())); same_event(list(fs.values()))
            if n["capital_cash"] > 0 or n["asset_proceeds"] < 0:
                refuse("cash_leg_sign")
            subtotal = n["operating_cash"] + n["capital_cash"]
            reconciled = subtotal + n["asset_proceeds"]
            if reconciled != n["issuer_defined_total"]:
                refuse("cash_reconciliation")
            result = {"pre_asset_proceeds":text(subtotal),
                      "issuer_defined_total":text(reconciled),
                      "reconciliation_residual":"0"}
            omissions = []
        else:
            if any(f["role"] != "outlook" for f in fs.values()):
                refuse("outlook_role_required")
            if any(not isinstance(f["target"], str) or not f["target"] for f in fs.values()):
                refuse("target_unknown")
            if len({f["target"] for f in fs.values()}) != 1:
                refuse("target_mismatch")
            same_period(list(fs.values()))
            same_event([fs["prior_low"],fs["prior_high"]])
            same_event([fs["new_low"],fs["new_high"]])
            if fs["prior_low"]["event"] == fs["new_low"]["event"]:
                refuse("distinct_reporting_events_required")
            if n["prior_low"] > n["prior_high"] or n["new_low"] > n["new_high"]:
                refuse("range_inverted")
            relation = ("new_range_below_prior_range" if n["new_high"] < n["prior_low"]
                        else "new_range_above_prior_range" if n["new_low"] > n["prior_high"]
                        else "ranges_overlap")
            result = {"low_change":text(n["new_low"]-n["prior_low"]),
                      "high_change":text(n["new_high"]-n["prior_high"]),
                      "new_upper_minus_prior_lower":text(n["new_high"]-n["prior_low"]),
                      "range_relation":relation}
            omissions = []
    return {
        "case_key":case["key"], "evidence_status":"INVENTED_RESEARCH_EXAMPLE",
        "production_ready":False, "recipe":recipe, "derived":result, "omissions":omissions,
        "input_keys":list(fs),
        "source_references":[fs[k]["evidence"] for k in fs],
        "authority":{k:False for k in sorted(AUTH_KEYS)}
    }

def load_examples(path: Path) -> dict:
    packet = json.loads(path.read_text(encoding="utf-8"))
    if (packet.get("research_scope_only") is not True
        or packet.get("all_values_and_identities") != "INVENTED_NONPRODUCTION"):
        refuse("research_scope")
    auth = packet.get("authority")
    if not isinstance(auth,dict) or set(auth) != AUTH_KEYS or any(v is not False for v in auth.values()):
        refuse("authority_not_false")
    return packet

def main() -> None:
    path = Path(__file__).with_name("CONSUMER_R11_SYNTHETIC_WORKED_CASES.json")
    packet = load_examples(path)
    results = [run_case(case) for case in packet["cases"]]
    target = Path(__file__).with_name("research_results.json")
    target.write_text(json.dumps(results, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({"examples":len(results),"native_tests":0,"result_path":str(target)}))

if __name__ == "__main__":
    main()
