"""Validate and compose issuer facts from the two bounded USD read models.

Only ``debt_maturity.v1`` and ``cash_runway.v1`` establish the legacy defaults
of issuer-reported scope and USD. Explicit metadata never overrides a conflict.
Validation precedes both fact exposure and arithmetic; a reason is not a guard.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from math import isfinite, fsum
from typing import Any, Mapping

_SCHEMAS = {"debt": "debt_maturity.v1", "cash": "cash_runway.v1"}
_SCOPES = frozenset({"issuer", "issuer_reported", "consolidated"})
_FORMS = frozenset({"10-K", "10-K/A", "20-F", "40-F"})
_PERIOD_KEYS = ("accn", "end", "filed", "form", "fp", "fy")
_BUCKETS = frozenset({"y1", "y2", "y3", "y4", "y5", "after5"})


def _canonical_cik(value: object) -> str | None:
    if type(value) is int:
        return str(value).zfill(10) if 1 <= value <= 9_999_999_999 else None
    if not isinstance(value, str):
        return None
    raw = value.strip()
    if not raw.isascii() or not raw.isdigit() or len(raw) > 10 or int(raw) == 0:
        return None
    return raw.zfill(10)


def _date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and len(value) == 10:
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    return None


def _number(value: object, *, nonnegative: bool = False) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return isfinite(value) and (not nonnegative or value >= 0)
    except OverflowError:
        return False


def _scope(block: Mapping[str, Any]) -> str:
    return block.get("scope", block.get("source_scope", "issuer_reported"))


def _empty_result(status, cik, issuer_id, security_id, cutoff, reasons):
    return {
        "schema": "capital_need.v1", "version": 1, "status": status,
        "issuer": {"issuer_id": issuer_id, "security_id": security_id,
                   "cik": cik, "scope": "issuer"},
        "as_of": cutoff.isoformat() if cutoff else None,
        "coverage": {"state": status, "reasons": reasons},
        "reported": {"debt_due": None, "cash": None,
                     "operating_cash_flow": None, "capex": None},
        "derived": {"free_cash_flow": None, "scenario_runway": None,
                    "near_term_cash_cover": None, "near_term_cash_gap_usd": None},
        "authority": {"class": "context_only", "display_only": True},
        "source_clock": {"evaluation_as_of": cutoff.isoformat() if cutoff else None},
    }


def _acquisition(block):
    """Acquisition is a separate timezone-bearing cache clock, never as_of."""
    value = block.get("fetched_at")
    if isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value)
            if timestamp.tzinfo is not None:
                return {"state": "observed", "fetched_at": value}
        except ValueError:
            pass
    return {"state": "unknown", "fetched_at": None}


def _validated_period(block, label, cutoff, reasons):
    """Accept a complete annual filing and clocks, never trust a stale flag alone."""
    initial = len(reasons)
    period = block.get("period")
    if not isinstance(period, Mapping):
        reasons.append(f"{label}_period_invalid")
        return None
    accn, fy = period.get("accn"), period.get("fy")
    if (not isinstance(accn, str) or not accn.strip()
            or not isinstance(period.get("form"), str)
            or period["form"] not in _FORMS or period.get("fp") != "FY"
            or type(fy) is not int or not 1 <= fy <= 9999):
        reasons.append(f"{label}_period_invalid")
    end, filed, clock = (_date(period.get("end")), _date(period.get("filed")),
                         _date(block.get("as_of")))
    if end is None or filed is None or clock is None or cutoff is None:
        reasons.append(f"{label}_clock_unknown")
    else:
        if filed < end or clock < filed:
            reasons.append(f"{label}_clock_order_invalid")
        if filed > cutoff:
            reasons.append(f"{label}_filed_after_as_of")
        if clock > cutoff:
            reasons.append(f"{label}_source_after_as_of")
    available = None
    if "source_available_at" in block:
        available = _date(block["source_available_at"])
        if available is None and isinstance(block["source_available_at"], str):
            try:
                timestamp = datetime.fromisoformat(block["source_available_at"])
                if timestamp.tzinfo is not None:
                    available = timestamp.astimezone(timezone.utc).date()
            except ValueError:
                pass
        if (available is None or filed is None or clock is None or cutoff is None
                or not filed <= available <= clock <= cutoff):
            reasons.append(f"{label}_source_available_clock_invalid")
    acquired = _acquisition(block)
    if acquired["state"] == "observed":
        acquired_day = datetime.fromisoformat(acquired["fetched_at"]).astimezone(timezone.utc).date()
        if (filed is None or clock is None or cutoff is None
                or not filed <= acquired_day <= clock <= cutoff
                or (available is not None and available > acquired_day)):
            reasons.append(f"{label}_acquisition_clock_invalid")
    elif block.get("fetched_at") is not None:
        reasons.append(f"{label}_acquisition_clock_invalid")
    if "stale" in period and type(period["stale"]) is not bool:
        reasons.append(f"{label}_stale_flag_invalid")
    start = None
    if label == "cash":
        start = _date(period.get("start"))
        # Annual 52/53-week and calendar fiscal years; a quarter or a stub is
        # not an annual burn input. The producer binds both duration facts.
        if start is None or end is None or not 330 <= (end - start).days + 1 <= 380:
            reasons.append("cash_annual_duration_invalid")
    if len(reasons) != initial:
        return None
    accepted = {k: period[k] for k in _PERIOD_KEYS}
    accepted["end"], accepted["filed"] = end.isoformat(), filed.isoformat()
    accepted["stale"] = period.get("stale", False) or (cutoff - end).days > 550
    if start is not None:
        accepted["start"] = start.isoformat()
    return accepted


def _validated_source(raw, label, cutoff, reasons):
    if not isinstance(raw, Mapping) or not raw:
        reasons.append(f"{label}_missing" if not raw else f"{label}_block_invalid")
        return None
    initial = len(reasons)
    if raw.get("schema") != _SCHEMAS[label] or ("version" in raw and (type(raw["version"]) is not int or raw["version"] != 1)):
        reasons.append(f"{label}_schema_rejected")
    if _canonical_cik(raw.get("cik")) is None:
        reasons.append(f"{label}_cik_unknown")
    if raw.get("status") != "reported":
        reasons.append(f"{label}_not_reported")
    # Defaults belong ONLY to the accepted, USD-specific producer schemas.
    for key in ("unit", "currency"):
        if key in raw and raw[key] != "USD":
            reasons.append(f"{label}_{key}_unknown")
    for key in ("scope", "source_scope"):
        if key in raw and (not isinstance(raw[key], str) or raw[key] not in _SCOPES):
            reasons.append(f"{label}_investor_held_scope_rejected")
    if "scope" in raw and "source_scope" in raw and raw["scope"] != raw["source_scope"]:
        reasons.append(f"{label}_scope_conflict")
    if raw.get("dimensions") not in (None, {}, []):
        reasons.append(f"{label}_dimensions_unsupported")
    period = _validated_period(raw, label, cutoff, reasons)
    if len(reasons) != initial:
        return None
    return {"block": raw, "period": period, "scope": _scope(raw),
            "cik": _canonical_cik(raw["cik"]),
            "evaluation_as_of": _date(raw["as_of"]).isoformat(),
            "acquisition": _acquisition(raw)}


def _validated_debt(source, reasons):
    block = source["block"]
    rows = block.get("buckets")
    if not isinstance(rows, list) or not rows:
        reasons.append("debt_buckets_invalid")
        return None
    buckets, seen, values = [], set(), []
    for row in rows:
        if not isinstance(row, Mapping):
            reasons.append("debt_bucket_invalid")
            return None
        key = row.get("key")
        if not isinstance(key, str) or key not in _BUCKETS or key in seen:
            reasons.append("debt_bucket_key_invalid_or_duplicate")
            return None
        seen.add(key)
        if any(row.get(k) is not None and not isinstance(row[k], str)
               for k in ("tag", "drop_reason")):
            reasons.append("debt_bucket_provenance_invalid")
            return None
        if type(row.get("reported")) is not bool:
            reasons.append("debt_bucket_reported_invalid")
            return None
        if any(k in row and row[k] != "USD" for k in ("unit", "currency")):
            reasons.append("debt_bucket_unit_unknown")
            return None
        reported = row["reported"]
        value = row.get("usd") if reported else None
        if not reported and row.get("usd") is not None:
            reasons.append("debt_unreported_value_conflict")
            return None
        if reported and (not _number(value, nonnegative=True) or row.get("drop_reason") is not None):
            reasons.append("debt_bucket_value_invalid")
            return None
        if reported:
            values.append(value)
        buckets.append({"key": key, "value": value, "unit": "USD", "currency": "USD",
                        "state": "observed" if reported else "unknown",
                        "drop_reason": row.get("drop_reason"), "tag": row.get("tag")})
    try:
        total = sum(values) if all(type(v) is int for v in values) else fsum(values)
    except (OverflowError, ValueError):
        total = None
    claimed = block.get("total_reported_usd")
    if (not values or not _number(total, nonnegative=True)
            or not _number(claimed, nonnegative=True) or total != claimed):
        reasons.append("debt_total_invalid")
        return None
    return {"state": "observed", "unit": "USD", "currency": "USD",
            "period": source["period"], "scope": source["scope"],
            "issuer_debt_outstanding_only": True, "buckets": buckets,
            "total_reported_usd": total, "buckets_reported": len(values),
            "ladder_complete": seen == _BUCKETS and len(values) == len(_BUCKETS),
            "source_schema": block["schema"],
            "evaluation_as_of": source["evaluation_as_of"],
            "acquisition": source["acquisition"]}


def _cash_facts_and_scenario(source, reasons):
    block, period = source["block"], source["period"]
    cash, ocf, capex = (block.get(k) for k in ("cash_usd", "ocf_usd", "capex_usd"))
    if not (_number(cash, nonnegative=True) and _number(ocf) and _number(capex, nonnegative=True)):
        reasons.append("cash_value_invalid")
        return None
    fcf = ocf - capex
    if not _number(fcf):
        reasons.append("cash_arithmetic_nonfinite")
        return None
    annual_burn = -fcf if fcf < 0 else 0
    monthly_burn = annual_burn / 12
    months = None
    display = "self_funding"
    if annual_burn:
        if not monthly_burn:
            reasons.append("cash_arithmetic_underflow")
            return None
        months = cash / monthly_burn
        if not _number(months, nonnegative=True):
            reasons.append("cash_arithmetic_nonfinite")
            return None
        display = "more_than_10_years" if months > 120 else "months"
        months = round(months, 1)
    reported = {}
    for name, value, basis in (("cash", cash, "instant"), ("operating_cash_flow", ocf, "duration"),
                               ("capex", capex, "duration")):
        fact_period = dict(period)
        if basis == "instant":
            fact_period.pop("start")
        reported[name] = {"state": "observed", "value": value, "unit": "USD", "currency": "USD",
                          "basis": basis, "period": fact_period, "scope": source["scope"],
                          "source_schema": block["schema"], "evaluation_as_of": source["evaluation_as_of"],
            "acquisition": source["acquisition"]}
    return reported, {
        "free_cash_flow": {"state": "derived", "value": fcf, "unit": "USD", "currency": "USD",
                           "formula": "operating_cash_flow - capex_outflow", "period": period},
        "scenario_runway": {
            "state": "stale" if period["stale"] else "scenario",
            "value_months": months, "unit": "months" if months is not None else None,
            "display": display, "annual_burn_usd": annual_burn, "monthly_burn_usd": monthly_burn,
            "period": period,
            "assumptions": {"annual_filing_only": True, "no_refinancing_forecast": True,
                            "issuer_debt_payments_included": False},
            "excludes": ["financing_access", "restricted_cash", "investor_held_par", "valuation",
                         "covenant", "trade_recommendation"],
        },
    }


def assemble_capital_need(
    debt_maturity: Mapping[str, Any] | None, cash_runway: Mapping[str, Any] | None, *,
    issuer_id: str | None = None, security_id: str | None = None, as_of: object = None,
) -> dict[str, Any]:
    """Expose only validated issuer facts and same-filing, fresh cash coverage.

    A rejected debt block cannot suppress a valid standalone cash scenario, but
    cannot contribute any facts or combined arithmetic. The exact accepted USD
    producer schemas provide the only legacy unit/scope defaults. Cash v1 must
    additionally retain its matched annual start date; older lossy blocks fail
    closed until rebuilt by that producer.
    """
    debt_raw = debt_maturity if isinstance(debt_maturity, Mapping) else {}
    cash_raw = cash_runway if isinstance(cash_runway, Mapping) else {}
    cutoff, reasons = _date(as_of), []
    debt_cik, cash_cik = (_canonical_cik(b.get("cik")) for b in (debt_raw, cash_raw))
    base = _empty_result("unknown", debt_cik or cash_cik, issuer_id, security_id, cutoff, reasons)
    if all(b.get("schema") == _SCHEMAS[label] and b.get("status") == "not_applicable"
           for label, b in (("debt", debt_raw), ("cash", cash_raw))):
        return _empty_result("not_applicable", None, issuer_id, security_id, cutoff,
                             ["issuer_not_applicable"])
    if (debt_cik and cash_cik and debt_cik != cash_cik
            or any(b.get("status") == "identity_mismatch" for b in (debt_raw, cash_raw))):
        return _empty_result("identity_mismatch", None, issuer_id, security_id, cutoff,
                             ["debt_cash_cik_mismatch"])
    debt = _validated_source(debt_maturity, "debt", cutoff, reasons)
    cash = _validated_source(cash_runway, "cash", cutoff, reasons)
    debt_view = _validated_debt(debt, reasons) if debt else None
    cash_view = _cash_facts_and_scenario(cash, reasons) if cash else None
    base["reported"]["debt_due"] = debt_view
    if cash_view:
        base["reported"].update(cash_view[0])
        base["derived"].update(cash_view[1])
    for label, source, view in (("debt", debt, debt_view), ("cash", cash, cash_view)):
        if view and source["period"]["stale"]:
            reasons.append(f"{label}_period_stale")
    if debt_view and not debt_view["ladder_complete"]:
        reasons.append("debt_ladder_incomplete")
    if debt_view and cash_view:
        dp, cp = debt["period"], cash["period"]
        if any(dp[k] != cp[k] for k in _PERIOD_KEYS):
            reasons.append("debt_cash_period_mismatch")
        if debt["scope"] != cash["scope"]:
            reasons.append("debt_cash_scope_mismatch")
        y1 = next((b for b in debt_view["buckets"] if b["key"] == "y1"), None)
        if not y1 or y1["state"] != "observed":
            reasons.append("y1_debt_unknown")
        # All validation predicates participate in the gate, not just status.
        if not reasons:
            if y1["value"] == 0:
                base["derived"]["near_term_cash_cover"] = {
                    "state": "not_applicable", "reason": "reported_zero_y1_principal",
                    "value_pct": None, "period": cp,
                }
                base["derived"]["near_term_cash_gap_usd"] = 0
            else:
                cover = cash_view[0]["cash"]["value"] / y1["value"] * 100
                gap = max(y1["value"] - cash_view[0]["cash"]["value"], 0)
                if _number(cover, nonnegative=True) and _number(gap, nonnegative=True):
                    base["derived"]["near_term_cash_cover"] = {
                        "state": "derived", "value_pct": round(cover),
                        "formula": "cash / y1_debt_due * 100", "period": cp,
                    }
                    base["derived"]["near_term_cash_gap_usd"] = gap
                else:
                    reasons.append("coverage_arithmetic_nonfinite")
    else:
        reasons.append("near_term_cover_requires_valid_sources")
    status = "complete" if not reasons else "partial" if debt_view or cash_view else "unknown"
    base["status"] = status
    base["coverage"] = {"state": status, "reasons": list(dict.fromkeys(reasons))}
    for label, raw in (("debt", debt_raw), ("cash", cash_raw)):
        clock = _date(raw.get("as_of"))
        base["source_clock"][f"{label}_evaluation_as_of"] = clock.isoformat() if clock else None
        base["source_clock"][f"{label}_acquisition"] = _acquisition(raw)
        period = raw.get("period")
        filed = _date(period.get("filed")) if isinstance(period, Mapping) else None
        base["source_clock"][f"{label}_filed"] = filed.isoformat() if filed else None
    return base
