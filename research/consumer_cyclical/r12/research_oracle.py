"""R12 research reference for invented Consumer examples, NOT a production adapter.

This file exists only to make the H3/M1-M5 design obligations executable and
reviewable. It uses the Python standard library, no network, no repository
application imports, no native IDs, no source admission, and no publication.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, localcontext
import json
from pathlib import Path
import re

class ResearchRefusal(ValueError):
    pass

FACT_KEYS = {
    "key", "metric", "value_text", "unit", "scale_power10", "period_start",
    "period_end", "period_kind", "role", "target", "kind", "sign_convention",
    "basis", "perimeter", "definition", "event", "published_at",
    "display_quantum", "evidence", "native_ref", "native_admitted",
}
AUTH_KEYS = {"can_rank", "can_gate", "can_size", "can_originate", "can_open_entry"}
CONTEXT_FIELDS = ("unit", "scale_power10", "basis", "perimeter", "definition", "kind")
DECIMAL_TEXT = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
PERIOD_DAY_BOUNDS = {"quarter": (89, 93), "half_year": (180, 184), "year": (365, 366)}
METRICS = {
    "pass_through": {
        "revenue_new": "total_revenue",
        "revenue_old": "total_revenue",
        "fund_revenue_new": "fund_revenue",
        "fund_revenue_old": "fund_revenue",
        "fund_expense_new": "fund_expense",
        "fund_expense_old": "fund_expense",
    },
    "cash_bridge": {
        "operating_cash": "operating_cash",
        "capital_cash": "capital_cash",
        "asset_proceeds": "asset_proceeds",
        "issuer_defined_total": "issuer_defined_total",
    },
    "outlook_revision": {
        "prior_low": "revenue_outlook_low",
        "prior_high": "revenue_outlook_high",
        "new_low": "revenue_outlook_low",
        "new_high": "revenue_outlook_high",
    },
}
BASES = {
    "pass_through": "explicit_same_quarter_prior_year",
    "cash_bridge": "same_interval_signed_cash",
    "outlook_revision": "two_outlooks_same_target",
}

def refuse(code: str) -> None:
    raise ResearchRefusal(code)

def decimal_text(value: object) -> Decimal:
    if not isinstance(value, str) or len(value) > 48 or not DECIMAL_TEXT.fullmatch(value):
        refuse("decimal_text_required")
    return Decimal(value)

def canonical_decimal(value: Decimal) -> str:
    s = format(value, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return "0" if s in {"", "-0"} else s

def parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value:
        refuse("published_at_required")
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        refuse("published_at_invalid")
    if ts.tzinfo is None or ts.utcoffset() is None:
        refuse("published_at_timezone_required")
    return ts

def validate_calendar_period(start: date, end: date, kind: object) -> None:
    if kind not in PERIOD_DAY_BOUNDS:
        refuse("period_kind_invalid")
    days = (end - start).days + 1
    lo, hi = PERIOD_DAY_BOUNDS[kind]
    if not lo <= days <= hi:
        refuse("period_kind_interval_mismatch")

def parse_fact(item: object, recipe: str) -> dict:
    if not isinstance(item, dict):
        refuse("fact_not_object")
    key = item.get("key")
    if key not in METRICS[recipe]:
        refuse("unknown_input_key")
    rec = {"raw": item, "key": key, "value": None, "quantum": None, "published": None, "error": None}
    try:
        if set(item) != FACT_KEYS:
            refuse("fact_shape")
        if item["metric"] != METRICS[recipe][key]:
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
        if item["native_ref"] is not None or item["native_admitted"] is not False:
            refuse("native_claim_forbidden")
        evidence = item["evidence"]
        if not isinstance(evidence, dict) or set(evidence) != {"document", "revision", "locator"}:
            refuse("evidence_shape")
        if not all(isinstance(v, str) and v for v in evidence.values()):
            refuse("evidence_missing")
        if not evidence["document"].startswith("https://example.invalid/"):
            refuse("not_invented_source")
        try:
            start = date.fromisoformat(item["period_start"])
            end = date.fromisoformat(item["period_end"])
        except (TypeError, ValueError):
            refuse("period_invalid")
        if start > end:
            refuse("period_order")
        validate_calendar_period(start, end, item["period_kind"])
        value = decimal_text(item["value_text"])
        quantum = decimal_text(item["display_quantum"])
        if quantum <= 0:
            refuse("display_quantum_nonpositive")
        published = parse_timestamp(item["published_at"])
        if item["kind"] == "physical" and value < 0:
            refuse("negative_physical_quantity")
        rec.update(value=value, quantum=quantum, published=published, start=start, end=end)
    except ResearchRefusal as exc:
        rec["error"] = str(exc)
    return rec

def read_facts(case: dict) -> dict:
    recipe = case.get("recipe")
    if recipe not in METRICS:
        refuse("unsupported_recipe")
    if case.get("comparison_basis") != BASES[recipe]:
        refuse("comparison_basis")
    facts = case.get("facts")
    if not isinstance(facts, list) or not facts:
        refuse("facts_missing")
    records = {}
    for item in facts:
        rec = parse_fact(item, recipe)
        if rec["key"] in records:
            refuse("duplicate_input_key")
        records[rec["key"]] = rec
    return records

def _dependency_failure(records: dict, deps: list[str]) -> str | None:
    missing = [key for key in deps if key not in records]
    if missing:
        return "missing_input:" + ",".join(missing)
    bad = [(key, records[key]["error"]) for key in deps if records[key]["error"]]
    if bad:
        return "invalid_input:" + ";".join(f"{key}:{reason}" for key, reason in bad)
    return None

def _ensure_context(records: dict, deps: list[str]) -> None:
    raws = [records[key]["raw"] for key in deps]
    for field in CONTEXT_FIELDS:
        if any(raw[field] != raws[0][field] for raw in raws[1:]):
            refuse("context_mismatch:" + field)
    if raws[0]["kind"] != "financial":
        refuse("financial_recipe_required")

def _ensure_actual(records: dict, deps: list[str]) -> None:
    for key in deps:
        raw = records[key]["raw"]
        if raw["role"] != "actual" or raw["target"] is not None:
            refuse("actual_role_required")

def _ensure_outlook(records: dict, deps: list[str]) -> None:
    targets = []
    for key in deps:
        raw = records[key]["raw"]
        if raw["role"] != "outlook":
            refuse("outlook_role_required")
        if not isinstance(raw["target"], str) or not raw["target"]:
            refuse("target_unknown")
        targets.append(raw["target"])
    if len(set(targets)) != 1:
        refuse("target_mismatch")

def _same_period(records: dict, deps: list[str]) -> None:
    intervals = {(records[k]["raw"]["period_start"], records[k]["raw"]["period_end"], records[k]["raw"]["period_kind"]) for k in deps}
    if len(intervals) != 1:
        refuse("period_mismatch")

def _same_event(records: dict, deps: list[str]) -> None:
    raws = [records[k]["raw"] for k in deps]
    if len({raw["event"] for raw in raws}) != 1:
        refuse("event_mismatch")
    if len({raw["evidence"]["revision"] for raw in raws}) != 1:
        refuse("mixed_document_revision")
    if len({raw["published_at"] for raw in raws}) != 1:
        refuse("event_clock_mismatch")

def _validate_yoy_pair(records: dict, new_key: str, old_key: str) -> None:
    _ensure_actual(records, [new_key, old_key])
    new, old = records[new_key], records[old_key]
    if new["raw"]["period_kind"] != "quarter" or old["raw"]["period_kind"] != "quarter":
        refuse("quarter_period_required")
    if (new["start"].month, new["start"].day, new["end"].month, new["end"].day) != (
        old["start"].month, old["start"].day, old["end"].month, old["end"].day
    ):
        refuse("comparison_period_grain_mismatch")
    if new["start"].year != old["start"].year + 1 or new["end"].year != old["end"].year + 1:
        refuse("comparison_period_order")
    if not old["published"] < new["published"]:
        refuse("comparison_event_order")

def _validate_cash(records: dict, deps: list[str]) -> None:
    _ensure_actual(records, deps)
    _same_period(records, deps)
    _same_event(records, deps)
    if any(records[k]["raw"]["period_kind"] != "half_year" for k in deps):
        refuse("half_year_period_required")
    if "capital_cash" in deps and records["capital_cash"]["value"] > 0:
        refuse("cash_leg_sign")
    if "asset_proceeds" in deps and records["asset_proceeds"]["value"] < 0:
        refuse("cash_leg_sign")

def _validate_outlook_pair(records: dict, old_key: str, new_key: str) -> None:
    deps = [old_key, new_key]
    _ensure_outlook(records, deps)
    _same_period(records, deps)
    if any(records[k]["raw"]["period_kind"] != "year" for k in deps):
        refuse("year_period_required")
    if records[old_key]["raw"]["event"] == records[new_key]["raw"]["event"]:
        refuse("distinct_reporting_events_required")
    if not records[old_key]["published"] < records[new_key]["published"]:
        refuse("outlook_event_order")

def _periods(records: dict, deps: list[str]) -> list[dict]:
    out = []
    for key in deps:
        if key not in records or records[key]["error"]:
            continue
        raw = records[key]["raw"]
        out.append({
            "input_ref": key,
            "period_kind": raw["period_kind"],
            "period_start": raw["period_start"],
            "period_end": raw["period_end"],
            "event": raw["event"],
            "published_at": raw["published_at"],
        })
    return out

def _base_meta(records: dict, deps: list[str]) -> tuple[object, object, object, object]:
    valid = [records[k] for k in deps if k in records and not records[k]["error"]]
    if not valid:
        return None, None, None, None
    units = {r["raw"]["unit"] for r in valid}
    scales = {r["raw"]["scale_power10"] for r in valid}
    signs = {r["raw"]["sign_convention"] for r in valid}
    quantums = [r["quantum"] for r in valid]
    unit = next(iter(units)) if len(units) == 1 else None
    scale = next(iter(scales)) if len(scales) == 1 else None
    sign = next(iter(signs)) if len(signs) == 1 else None
    quantum = canonical_decimal(max(quantums)) if quantums else None
    return unit, scale, sign, quantum

def unavailable(records: dict, deps: list[str], reason: str) -> dict:
    unit, scale, sign, quantum = _base_meta(records, deps)
    return {
        "status": "unavailable",
        "value_text": None,
        "unit": unit,
        "scale_power10": scale,
        "sign_convention": sign,
        "periods": _periods(records, deps),
        "precision": None if quantum is None else {
            "display_quantum": quantum,
            "rounding": "derived_from_reported_values",
        },
        "input_refs": list(deps),
        "reason": reason,
    }

def ready(records: dict, deps: list[str], value: Decimal | str, *,
          unit: str | None = None, scale_power10: int | None = None,
          sign_convention: str | None = None, display_quantum: str | None = None,
          rounding: str = "derived_from_reported_values") -> dict:
    base_unit, base_scale, base_sign, base_quantum = _base_meta(records, deps)
    if isinstance(value, Decimal):
        value_text = canonical_decimal(value)
    else:
        value_text = value
    return {
        "status": "ready",
        "value_text": value_text,
        "unit": base_unit if unit is None else unit,
        "scale_power10": base_scale if scale_power10 is None else scale_power10,
        "sign_convention": base_sign if sign_convention is None else sign_convention,
        "periods": _periods(records, deps),
        "precision": {
            "display_quantum": base_quantum if display_quantum is None else display_quantum,
            "rounding": rounding,
        },
        "input_refs": list(deps),
        "reason": None,
    }

def derive(records: dict, deps: list[str], validator, calculator, **ready_overrides) -> dict:
    failure = _dependency_failure(records, deps)
    if failure:
        return unavailable(records, deps, failure)
    try:
        _ensure_context(records, deps)
        validator()
        value = calculator()
    except ResearchRefusal as exc:
        return unavailable(records, deps, str(exc))
    return ready(records, deps, value, **ready_overrides)

def pass_through_results(records: dict) -> dict:
    def pair(new_key, old_key):
        return lambda: _validate_yoy_pair(records, new_key, old_key)

    r = {}
    r["revenue_change"] = derive(
        records, ["revenue_new", "revenue_old"], pair("revenue_new", "revenue_old"),
        lambda: records["revenue_new"]["value"] - records["revenue_old"]["value"],
    )
    r["fund_revenue_change"] = derive(
        records, ["fund_revenue_new", "fund_revenue_old"], pair("fund_revenue_new", "fund_revenue_old"),
        lambda: records["fund_revenue_new"]["value"] - records["fund_revenue_old"]["value"],
    )
    r["fund_expense_change"] = derive(
        records, ["fund_expense_new", "fund_expense_old"], pair("fund_expense_new", "fund_expense_old"),
        lambda: records["fund_expense_new"]["value"] - records["fund_expense_old"]["value"],
    )

    fund_deps = ["fund_revenue_new", "fund_revenue_old", "fund_expense_new", "fund_expense_old"]
    def validate_fund():
        _validate_yoy_pair(records, "fund_revenue_new", "fund_revenue_old")
        _validate_yoy_pair(records, "fund_expense_new", "fund_expense_old")
        _same_event(records, ["fund_revenue_new", "fund_expense_new"])
        _same_event(records, ["fund_revenue_old", "fund_expense_old"])
    r["fund_net_change"] = derive(
        records, fund_deps, validate_fund,
        lambda: (records["fund_revenue_new"]["value"] - records["fund_revenue_old"]["value"]) -
                (records["fund_expense_new"]["value"] - records["fund_expense_old"]["value"]),
    )

    ex_deps = ["revenue_new", "revenue_old", "fund_revenue_new", "fund_revenue_old"]
    def validate_ex():
        _validate_yoy_pair(records, "revenue_new", "revenue_old")
        _validate_yoy_pair(records, "fund_revenue_new", "fund_revenue_old")
        _same_event(records, ["revenue_new", "fund_revenue_new"])
        _same_event(records, ["revenue_old", "fund_revenue_old"])
    r["revenue_change_excluding_fund"] = derive(
        records, ex_deps, validate_ex,
        lambda: (records["revenue_new"]["value"] - records["revenue_old"]["value"]) -
                (records["fund_revenue_new"]["value"] - records["fund_revenue_old"]["value"]),
    )

    ratio_deps = list(ex_deps)
    failure = _dependency_failure(records, ratio_deps)
    if failure:
        r["fund_share_of_revenue_change_pct"] = unavailable(records, ratio_deps, failure)
    else:
        try:
            _ensure_context(records, ratio_deps)
            validate_ex()
            denom = records["revenue_new"]["value"] - records["revenue_old"]["value"]
            numerator = records["fund_revenue_new"]["value"] - records["fund_revenue_old"]["value"]
            if denom <= 0:
                refuse("denominator_nonpositive")
            half_width = (records["revenue_new"]["quantum"] + records["revenue_old"]["quantum"]) / Decimal(2)
            if denom - half_width <= 0 <= denom + half_width:
                refuse("denominator_rounding_envelope_includes_zero")
            pct = (numerator / denom * Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            r["fund_share_of_revenue_change_pct"] = ready(
                records, ratio_deps, format(pct, ".2f"), unit="percent", scale_power10=0,
                sign_convention="signed", display_quantum="0.01", rounding="ROUND_HALF_UP",
            )
        except ResearchRefusal as exc:
            r["fund_share_of_revenue_change_pct"] = unavailable(records, ratio_deps, str(exc))
    return r

def cash_results(records: dict) -> dict:
    r = {}
    pre_deps = ["operating_cash", "capital_cash"]
    r["pre_asset_proceeds"] = derive(
        records, pre_deps, lambda: _validate_cash(records, pre_deps),
        lambda: records["operating_cash"]["value"] + records["capital_cash"]["value"],
    )
    total_deps = ["operating_cash", "capital_cash", "asset_proceeds", "issuer_defined_total"]
    def validate_total():
        _validate_cash(records, total_deps)
        computed = records["operating_cash"]["value"] + records["capital_cash"]["value"] + records["asset_proceeds"]["value"]
        if computed != records["issuer_defined_total"]["value"]:
            refuse("cash_reconciliation_mismatch")
    r["issuer_defined_total"] = derive(
        records, total_deps, validate_total,
        lambda: records["operating_cash"]["value"] + records["capital_cash"]["value"] + records["asset_proceeds"]["value"],
    )
    r["reconciliation_residual"] = derive(
        records, total_deps, validate_total, lambda: Decimal(0),
    )
    return r

def outlook_results(records: dict) -> dict:
    r = {}
    for name, old_key, new_key in (
        ("low_change", "prior_low", "new_low"),
        ("high_change", "prior_high", "new_high"),
        ("new_upper_minus_prior_lower", "prior_low", "new_high"),
    ):
        deps = [old_key, new_key]
        r[name] = derive(
            records, deps, lambda o=old_key,n=new_key: _validate_outlook_pair(records, o, n),
            lambda o=old_key,n=new_key: records[n]["value"] - records[o]["value"],
        )
    deps = ["prior_low", "prior_high", "new_low", "new_high"]
    def validate_relation():
        _ensure_outlook(records, deps)
        _same_event(records, ["prior_low", "prior_high"])
        _same_event(records, ["new_low", "new_high"])
        _same_period(records, deps)
        if any(records[k]["raw"]["period_kind"] != "year" for k in deps):
            refuse("year_period_required")
        if not records["prior_low"]["published"] < records["new_low"]["published"]:
            refuse("outlook_event_order")
        if records["prior_low"]["value"] > records["prior_high"]["value"] or records["new_low"]["value"] > records["new_high"]["value"]:
            refuse("range_inverted")
    def relation():
        p_lo, p_hi = records["prior_low"]["value"], records["prior_high"]["value"]
        n_lo, n_hi = records["new_low"]["value"], records["new_high"]["value"]
        if n_hi < p_lo:
            return "new_range_below_prior_range"
        if n_lo > p_hi:
            return "new_range_above_prior_range"
        return "ranges_overlap"
    failure = _dependency_failure(records, deps)
    if failure:
        r["range_relation"] = unavailable(records, deps, failure)
    else:
        try:
            _ensure_context(records, deps)
            validate_relation()
            r["range_relation"] = ready(
                records, deps, relation(), unit="classification", scale_power10=0,
                sign_convention="not_applicable", display_quantum=None, rounding="not_applicable",
            )
        except ResearchRefusal as exc:
            r["range_relation"] = unavailable(records, deps, str(exc))
    return r

def format_result(result: dict) -> str:
    if result["status"] != "ready":
        return "unavailable (" + result["reason"] + ")"
    value = result["value_text"]
    if result["unit"] == "classification":
        return value
    if result["unit"] == "percent":
        return f"{value} percent"
    scale = result["scale_power10"]
    unit = result["unit"]
    return f"{value} × 10^{scale} {unit}"

def build_explanation(case: dict, results: dict) -> dict:
    interpretation = case.get("interpretation")
    if not isinstance(interpretation, dict) or set(interpretation) != {"counterevidence", "next_observation", "forbidden_conclusions"}:
        refuse("interpretation_shape")
    if not isinstance(interpretation["counterevidence"], str) or not interpretation["counterevidence"].strip():
        refuse("counterevidence_required")
    if not isinstance(interpretation["next_observation"], str) or not interpretation["next_observation"].strip():
        refuse("next_observation_required")
    forbidden = interpretation["forbidden_conclusions"]
    if not isinstance(forbidden, list) or not forbidden or not all(isinstance(v, str) and v for v in forbidden):
        refuse("forbidden_conclusions_required")

    recipe = case["recipe"]
    if recipe == "pass_through":
        what = (
            "Reported revenue change: " + format_result(results["revenue_change"]) + "; "
            "fund revenue change: " + format_result(results["fund_revenue_change"]) + "; "
            "fund expense change: " + format_result(results["fund_expense_change"]) + "."
        )
        meaning = (
            "Fund contribution change: " + format_result(results["fund_net_change"]) + ". "
            "Revenue change excluding fund: " + format_result(results["revenue_change_excluding_fund"]) + ". "
            "Fund share of revenue change: " + format_result(results["fund_share_of_revenue_change_pct"]) + ". "
            "Unavailable values remain suppressed rather than inferred."
        )
    elif recipe == "cash_bridge":
        what = (
            "Pre-asset-proceeds cash subtotal: " + format_result(results["pre_asset_proceeds"]) + "; "
            "reconciled issuer-defined total: " + format_result(results["issuer_defined_total"]) + "."
        )
        meaning = (
            "Reconciliation residual: " + format_result(results["reconciliation_residual"]) + ". "
            "Signed reported scale is preserved; missing or inconsistent legs suppress only dependent reconciliation results."
        )
    else:
        what = (
            "Low-bound change: " + format_result(results["low_change"]) + "; "
            "high-bound change: " + format_result(results["high_change"]) + "; "
            "new upper minus prior lower: " + format_result(results["new_upper_minus_prior_lower"]) + "."
        )
        meaning = (
            "Range relationship: " + format_result(results["range_relation"]) + ". "
            "These are ordered management outlook events for the same target, not an actual result or consensus surprise."
        )

    explanation = {
        "what_changed": what,
        "economic_meaning": meaning,
        "counterevidence": interpretation["counterevidence"],
        "next_observation": interpretation["next_observation"],
    }
    haystack = "\n".join(explanation.values()).casefold()
    for marker in forbidden:
        if marker.casefold() in haystack:
            refuse("forbidden_conclusion_emitted:" + marker)
    return explanation

def run_case(case: dict) -> dict:
    records = read_facts(case)
    recipe = case["recipe"]
    with localcontext() as ctx:
        ctx.prec = 80
        if recipe == "pass_through":
            results = pass_through_results(records)
        elif recipe == "cash_bridge":
            results = cash_results(records)
        else:
            results = outlook_results(records)
    ready_count = sum(r["status"] == "ready" for r in results.values())
    if ready_count == 0:
        section_status = "unavailable"
    elif ready_count == len(results):
        section_status = "ready"
    else:
        section_status = "degraded"
    omissions = [{"result": name, "reason": result["reason"]} for name, result in results.items() if result["status"] != "ready"]
    return {
        "case_key": case["key"],
        "evidence_status": "INVENTED_RESEARCH_EXAMPLE",
        "production_ready": False,
        "recipe": recipe,
        "section_status": section_status,
        "derived": results,
        "omissions": omissions,
        "explanation": build_explanation(case, results),
        "source_references": [
            rec["raw"]["evidence"] for rec in records.values()
            if not rec["error"]
        ],
        "authority": {key: False for key in sorted(AUTH_KEYS)},
    }

def load_examples(path: Path) -> dict:
    packet = json.loads(path.read_text(encoding="utf-8"))
    if packet.get("research_scope_only") is not True or packet.get("all_values_and_identities") != "INVENTED_NONPRODUCTION":
        refuse("research_scope")
    auth = packet.get("authority")
    if not isinstance(auth, dict) or set(auth) != AUTH_KEYS or any(value is not False for value in auth.values()):
        refuse("authority_not_false")
    return packet

def main() -> None:
    path = Path(__file__).with_name("CONSUMER_R12_SYNTHETIC_WORKED_CASES.json")
    packet = load_examples(path)
    results = [run_case(case) for case in packet["cases"]]
    target = Path(__file__).with_name("research_results.json")
    target.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"examples": len(results), "native_tests": 0, "result_path": str(target)}))

if __name__ == "__main__":
    main()
