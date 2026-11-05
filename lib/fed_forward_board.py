"""Display projection for the Macro Fed dialog. The Rates Command producer owns all calculations."""
import json
import re
from calendar import monthrange
from datetime import date
from hashlib import sha256
from math import isfinite


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _rows(value):
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)


def _day(value):
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
    return None


def _contract_months(board, path, bond_file):
    """Keep a difference attached to the exact month, units and source that authorized it."""
    basis = _mapping(path.get("basis"))
    components = _mapping(_mapping(board.get("board_generation")).get("components"))
    source = _mapping(components.get("d1"))
    digest = source.get("content_ref")
    comparisons = _rows(board.get("qualified_comparisons"))
    # Before the nested-pointer repair, a saved board could mark D1 missing
    # while pinning the exact source bytes. Only rehydrate that known format.
    if (bond_file is not None and source.get("state") == "missing"
            and source.get("input_id") == "data/bonds/bond_health.json#/fed_path/effr_meeting_path"
            and isinstance(digest, str)):
        try:
            raw = bond_file.read_bytes()
            if sha256(raw).hexdigest() == digest:
                from engine.rates_inflation_command import contract_comparison_rows

                fed = _mapping(_mapping(json.loads(raw)).get("fed_path"))
                if (fed.get("asof") == path.get("asof") and _day(path.get("asof"))
                        and isinstance(_mapping(fed.get("implied_source_meta")).get("effr_meeting_path"), dict)):
                    stamp, comparisons = contract_comparison_rows(fed, digest)
                    source = {**stamp, "state": "present"}
        except (OSError, ValueError):
            pass
    cutoff = _day(source.get("cutoff"))
    board_cutoff = _day(basis.get("cutoff"))
    if (basis.get("value_state") != "present" or basis.get("rate_index") != "EFFR"
            or basis.get("source") != "rate_futures:ZQ" or basis.get("target") != "effr_monthly_average"
            or source.get("state") != "present" or not cutoff or not board_cutoff or cutoff > board_cutoff
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
        return []
    rows = []
    for row in comparisons:
        start, end = _day(row.get("reference_start")), _day(row.get("reference_end"))
        observed = _day(row.get("quote_observed"))
        if (row.get("quote_observed") and not observed) or (observed and observed > cutoff):
            continue
        if (row.get("component") != "d1" or row.get("rule_id") != "zq_month_vs_policy_midpoint.v1"
                or row.get("status") not in ("directly_comparable", "comparable_after_transformation")
                or row.get("unit") != "bp" or not _number(row.get("difference"))
                or row.get("content_ref") != digest or row.get("cutoff") != source.get("cutoff")
                or not row.get("left_ref") or not row.get("right_ref")
                or not all(_day(row.get(key)) and _day(row[key]) <= cutoff for key in ("left_cutoff", "right_cutoff"))
                or row.get("reference_only") is not True
                or not isinstance(row.get("contract"), str) or not row["contract"].strip()
                or not start or not end or start.day != 1
                or end != start.replace(day=monthrange(start.year, start.month)[1])):
            continue
        pointer = source.get("input_id")
        if not isinstance(pointer, str) or not re.fullmatch(
            re.escape(pointer) + r"/months/\d+/vs_target_midpoint", str(row.get("input_id", ""))
        ):
            continue
        rows.append({"month": start.isoformat()[:7], "contract": row["contract"],
                     "bp": row["difference"], "cutoff": source["cutoff"],
                     "observed": observed.isoformat() if observed else None})
    # Conflicting or duplicate entries for one month never produce two answers.
    counts = {}
    for row in rows:
        counts[row["month"]] = counts.get(row["month"], 0) + 1
    return sorted((row for row in rows if counts[row["month"]] == 1), key=lambda row: row["month"])


def fed_forward_board(rates, prediction_markets=None, *, bond_file=None):
    """Compose display fields without changing the producer or reading external data."""
    rates = _mapping(rates)
    board = _mapping(rates.get("board"))
    path = _mapping(board.get("rate_path_row"))
    pressure = _mapping(rates.get("expectations_pressure"))
    legs = _rows(pressure.get("legs"))
    sides = []
    for prefix, key in (("E", "ease_score"), ("H", "hawk_score")):
        group = [leg for leg in legs if str(leg.get("key", "")).startswith(prefix)]
        sides.append({"key": prefix, "score": pressure.get(key) if _number(pressure.get(key)) else None,
                      "active": [leg for leg in group if leg.get("active") is True and not leg.get("null_reason")],
                      "other": [leg for leg in group if leg.get("active") is not True or leg.get("null_reason")]})
    active = [leg for side in sides for leg in side["active"] if _number(leg.get("weight"))]
    top_driver = max(active, key=lambda leg: leg["weight"], default=None)
    labels = {
        "repricing_hawkish": ("Pressure leans toward tightening", "政策压力偏向收紧"),
        "pressure_building": ("Tightening pressure is building", "收紧压力积聚"),
        "repricing_dovish": ("Pressure leans toward easing", "政策压力偏向宽松"),
        "pressure_fading": ("Easing pressure is building", "宽松压力积聚"),
        "two_sided": ("Policy pressures are two-sided", "政策压力双向并存"),
    }
    title = labels.get(pressure.get("net_state"))
    if legs and all(leg.get("null_reason") or leg.get("active") is None for leg in legs):
        title = ("Policy read unavailable", "暂无政策读数")
        for side in sides:
            side["score"] = None
    months = _contract_months(rates, path, bond_file)
    dots = [row for row in _rows(path.get("dots"))
            if type(row.get("year")) is int and _number(row.get("median"))]
    check = _mapping(_mapping(rates.get("market_check")).get("prediction_markets"))
    events = _rows(check.get("events"))
    if not events:
        check = _mapping(prediction_markets)
        for event in _rows(check.get("events")):
            outcomes = [item for item in _rows(event.get("outcomes"))
                        if _number(item.get("prob")) and 0 <= item["prob"] <= 100]
            if outcomes:
                top = max(outcomes, key=lambda item: item["prob"])
                events.append({**event, "top_outcome": top.get("outcome"), "top_prob": top["prob"],
                               "chg_pp": top.get("chg_pp")})
    benchmarks = []
    for row in events:
        if not row.get("top_outcome") or not _number(row.get("top_prob")) or not 0 <= row["top_prob"] <= 100:
            continue
        benchmarks.append({**row, "chg_pp": row.get("chg_pp") if _number(row.get("chg_pp")) else None})
    return {"months": months, "sides": sides, "dots": dots, "label": ({"en": title[0], "zh": title[1]} if title else _mapping(pressure.get("state_label"))),
            "top_driver": top_driver,
            "events": benchmarks, "market_source": check.get("source"),
            "market_date": check.get("as_of") or check.get("asof"),
            "changes": _mapping(rates.get("changes")), "asof": rates.get("asof"),
            "conditions": _rows(rates.get("conditions")), "policy": _mapping(board.get("policy_row"))}
