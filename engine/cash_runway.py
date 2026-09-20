"""Issuer cash runway — pure functions over SEC XBRL companyfacts.

No I/O. No network. No clock. Reads an already-parsed companyfacts mapping
(the SEC XBRL companyfacts JSON shape: ``{"cik": ..., "facts": {"us-gaap": {...}}}``)
and extracts three annual-filing XBRL tags to compute free cash flow and
months of runway.

Every number is a reported XBRL fact or arithmetic over reported facts. No
score, no rank, no LLM text, no escalation is produced here (Neural Web A7 /
epistemics: this module never originates a signal).

Identity is by CIK only — this module never accepts or infers a ticker or
company name, and when the companyfacts payload itself carries a ``cik`` field,
that embedded identity is cross-checked against the caller-supplied ``cik``:
a mismatch fails closed to ``identity_mismatch``.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping

# Annual filing forms accepted as the source period.
_ANNUAL_FORMS = frozenset({"10-K", "10-K/A", "20-F", "40-F"})

# The three tags for this packet (frozen spec §2).
_RUNWAY_TAGS: tuple[tuple[str, str, str, str], ...] = (
    ("cash",    "CashAndCashEquivalentsAtCarryingValue",          "Cash and equivalents",          "现金及现金等价物"),
    ("ocf",     "NetCashProvidedByUsedInOperatingActivities",      "Operating cash flow",            "经营活动现金流"),
    ("capex",   "PaymentsToAcquirePropertyPlantAndEquipment",     "Equipment spend",                "设备支出"),
)

_STALE_DAYS = 550

_UNIT_SCALES = {
    "usd": 1,
    "usdthousands": 1000,
    "usd000": 1000,
    "usdmillions": 1_000_000,
}


def _unit_scale(unit_key: str) -> int | None:
    return _UNIT_SCALES.get(str(unit_key or "").strip().lower())


def _canonical_cik(value: object) -> str:
    raw = str(value or "").strip()
    if not raw.isdigit() or len(raw) > 10 or int(raw) == 0:
        raise ValueError(f"invalid CIK: {value!r}")
    return raw.zfill(10)


def _canonical_cik_or_none(value: object) -> str | None:
    try:
        return _canonical_cik(value)
    except ValueError:
        return None


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        y, m, d = str(value).split("-")
        return date(int(y), int(m), int(d))
    except Exception:  # noqa: BLE001
        return None


def _usd_dollars(amount: float) -> str:
    a = abs(amount)
    sign = "-" if amount < 0 else ""
    if a >= 1_000_000_000:
        return f"{sign}${a / 1_000_000_000:.1f}B"
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:.1f}M"
    if a >= 1_000:
        return f"{sign}${a / 1_000:.1f}K"
    return f"{sign}${a:.0f}"


def _empty_result(status: str, canon_cik: str, as_of: date | None) -> dict[str, Any]:
    return {
        "schema": "cash_runway.v1",
        "status": status,
        "cik": canon_cik,
        "cash_usd": None,
        "cash_display": None,
        "ocf_usd": None,
        "capex_usd": None,
        "free_cash_flow_usd": None,
        "monthly_burn_usd": None,
        "monthly_burn_display": None,
        "annual_burn_usd": None,
        "annual_burn_display": None,
        "runway_months": None,
        "runway_display": None,
        "near_term_cover_pct": None,
        "period": None,
        "as_of": as_of.isoformat() if as_of else None,
    }


def _candidate_periods(companyfacts: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Every (accn, end) period across all three runway tags that is an annual
    filing, deduped and sorted by (filed desc, end desc)."""
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    facts = ((companyfacts or {}).get("facts") or {}).get("us-gaap") or {}
    for _key, tag, _en, _zh in _RUNWAY_TAGS:
        tag_facts = facts.get(tag) or {}
        units = (tag_facts.get("units") or {})
        for unit_key, entries in units.items():
            if _unit_scale(unit_key) is None:
                continue
            for entry in entries or []:
                form = entry.get("form")
                fp = entry.get("fp")
                if form not in _ANNUAL_FORMS or fp != "FY":
                    continue
                accn = entry.get("accn")
                end = entry.get("end")
                if not accn or not end:
                    continue
                k = (accn, end)
                existing = seen.get(k)
                filed = entry.get("filed") or ""
                if existing is None or filed > existing.get("filed", ""):
                    seen[k] = {
                        "accn": accn, "end": end, "filed": filed,
                        "form": form, "fy": entry.get("fy"), "fp": fp,
                    }
    return sorted(seen.values(), key=lambda p: (p.get("filed") or "", p.get("end") or ""), reverse=True)


def _find_instant_fact(
    facts: Mapping[str, Any], tag: str, win_accn: str, win_end: str,
) -> tuple[float | None, str | None]:
    """Find a cash/instant fact for the exact winning (accn, end) period.

    Returns (usd_value, drop_reason). drop_reason is None when a valid value
    is returned.
    """
    tag_node = facts.get(tag) or {}
    units = tag_node.get("units") or {}
    found_any_unit = False
    found_candidates: list[float] = []
    for unit_key, entries in units.items():
        scale = _unit_scale(unit_key)
        for entry in entries or []:
            if (entry.get("accn") == win_accn and
                    entry.get("end") == win_end and
                    entry.get("form") in _ANNUAL_FORMS and
                    entry.get("fp") == "FY"):
                found_any_unit = True
                if scale is not None and entry.get("val") is not None:
                    found_candidates.append(entry.get("val") * scale)
    distinct = {round(v, 2) for v in found_candidates}
    if len(distinct) == 1:
        return found_candidates[0], None
    if len(distinct) > 1:
        return None, "unit_conflict"
    if found_any_unit:
        return None, "unit_not_usd"
    # check whether this tag exists at all under a different period
    for unit_key, entries in units.items():
        for entry in entries or []:
            if entry.get("form") in _ANNUAL_FORMS and entry.get("fp") == "FY":
                return None, "period_mismatch"
    return None, "absent"


def _find_duration_fact(
    facts: Mapping[str, Any], tag: str, win_accn: str, win_end: str,
) -> tuple[float | None, str | None]:
    """Find a duration fact (ocf or capex) for the exact winning period.

    Returns (usd_value, drop_reason). The fact must match BOTH accn AND end.
    """
    tag_node = facts.get(tag) or {}
    units = tag_node.get("units") or {}
    found_any_unit = False
    found_candidates: list[float] = []
    for unit_key, entries in units.items():
        scale = _unit_scale(unit_key)
        for entry in entries or []:
            if (entry.get("accn") == win_accn and
                    entry.get("end") == win_end and
                    entry.get("form") in _ANNUAL_FORMS and
                    entry.get("fp") == "FY"):
                found_any_unit = True
                if scale is not None and entry.get("val") is not None:
                    found_candidates.append(entry.get("val") * scale)
    distinct = {round(v, 2) for v in found_candidates}
    if len(distinct) == 1:
        return found_candidates[0], None
    if len(distinct) > 1:
        return None, "unit_conflict"
    if found_any_unit:
        return None, "unit_not_usd"
    for unit_key, entries in units.items():
        for entry in entries or []:
            if entry.get("form") in _ANNUAL_FORMS and entry.get("fp") == "FY":
                return None, "period_mismatch"
    return None, "absent"


def extract_cash_runway(
    companyfacts: Mapping[str, Any] | None,
    *,
    cik: str,
    as_of: date | None = None,
    ladder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract cash runway for one issuer.

    ``cik`` is the canonical zero-padded 10-digit SEC CIK — the only identity
    this function accepts. ``ladder``, if supplied, is the output of
    ``extract_maturity_ladder`` for the same issuer/period and is used to
    compute ``near_term_cover_pct`` when y1 bucket is reported and > 0.
    """
    canon_cik = _canonical_cik(cik)

    if not companyfacts:
        return _empty_result("no_filings", canon_cik, as_of)

    facts_cik = _canonical_cik_or_none(companyfacts.get("cik"))
    if facts_cik is not None and facts_cik != canon_cik:
        return _empty_result("identity_mismatch", canon_cik, as_of)

    periods = _candidate_periods(companyfacts)
    if not periods:
        return _empty_result("no_cash_facts", canon_cik, as_of)

    winner = periods[0]
    win_accn, win_end = winner["accn"], winner["end"]

    facts = ((companyfacts or {}).get("facts") or {}).get("us-gaap") or {}

    # cash: instant fact — must have end == win_end (period boundary match)
    cash_val, cash_drop = _find_instant_fact(facts, "CashAndCashEquivalentsAtCarryingValue", win_accn, win_end)
    # ocf and capex: duration facts — must match accn AND end
    ocf_val, ocf_drop = _find_duration_fact(facts, "NetCashProvidedByUsedInOperatingActivities", win_accn, win_end)
    capex_val, capex_drop = _find_duration_fact(facts, "PaymentsToAcquirePropertyPlantAndEquipment", win_accn, win_end)

    # If ANY of the three is absent for the period, report no_cash_facts with per-tag drop reasons
    missing = []
    if cash_drop:
        missing.append(("cash", cash_drop))
    if ocf_drop:
        missing.append(("ocf", ocf_drop))
    if capex_drop:
        missing.append(("capex", capex_drop))

    if missing:
        return {
            "schema": "cash_runway.v1",
            "status": "no_cash_facts",
            "cik": canon_cik,
            "cash_usd": None,
            "cash_display": None,
            "ocf_usd": None,
            "capex_usd": None,
            "free_cash_flow_usd": None,
            "monthly_burn_usd": None,
            "monthly_burn_display": None,
            "annual_burn_usd": None,
            "annual_burn_display": None,
            "runway_months": None,
            "runway_display": None,
            "near_term_cover_pct": None,
            "period": {
                "form": winner["form"],
                "fy": winner.get("fy"),
                "fp": winner.get("fp"),
                "end": win_end,
                "filed": winner.get("filed"),
                "accn": win_accn,
                "label": f"FY{winner.get('fy')}" if winner.get("fy") else win_end,
                "stale": False,
            },
            "drop_reasons": missing,
            "as_of": as_of.isoformat() if as_of else None,
        }

    # All three facts present
    fcf = (ocf_val or 0) - (capex_val or 0)

    monthly_burn: float | None = None
    monthly_burn_display: str | None = None
    annual_burn: float | None = None
    annual_burn_display: str | None = None
    runway_months: float | None = None
    runway_display: str | None = None

    if fcf < 0:
        annual_burn = -fcf
        monthly_burn = annual_burn / 12
        annual_burn_display = _usd_dollars(annual_burn)
        monthly_burn_display = _usd_dollars(monthly_burn)
        runway_months = (cash_val or 0) / monthly_burn
        # Cap display at > 10 years (> 120 months). Closed enum: the
        # template composes the user-facing EN/ZH sentence from this
        # token plus the numeric runway_months.
        if runway_months > 120:
            runway_display = "more_than_10_years"
        else:
            runway_display = "months"
    else:
        runway_display = "self_funding"

    near_term_cover_pct: float | None = None
    if ladder and ladder.get("status") == "reported":
        y1_bucket = (ladder.get("buckets") or [{}])[0] if ladder.get("buckets") else {}
        y1_reported = y1_bucket.get("reported", False)
        y1_usd = y1_bucket.get("usd") or 0
        if y1_reported and y1_usd > 0 and cash_val:
            near_term_cover_pct = round(100 * cash_val / y1_usd)

    end_date = _parse_date(win_end)
    stale = bool(as_of and end_date and (as_of - end_date).days > _STALE_DAYS)

    return {
        "schema": "cash_runway.v1",
        "status": "reported",
        "cik": canon_cik,
        "cash_usd": cash_val,
        "cash_display": _usd_dollars(cash_val) if cash_val is not None else None,
        "ocf_usd": ocf_val,
        "capex_usd": capex_val,
        "free_cash_flow_usd": fcf,
        "monthly_burn_usd": monthly_burn,
        "monthly_burn_display": monthly_burn_display,
        "annual_burn_usd": annual_burn,
        "annual_burn_display": annual_burn_display,
        "runway_months": round(runway_months, 1) if runway_months is not None else None,
        "runway_display": runway_display,
        "near_term_cover_pct": near_term_cover_pct,
        "period": {
            "form": winner["form"],
            "fy": winner.get("fy"),
            "fp": winner.get("fp"),
            "end": win_end,
            "filed": winner.get("filed"),
            "accn": win_accn,
            "label": f"FY{winner.get('fy')}" if winner.get("fy") else win_end,
            "stale": stale,
        },
        "as_of": as_of.isoformat() if as_of else None,
    }
