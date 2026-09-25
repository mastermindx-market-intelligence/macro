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

from datetime import date, datetime
from math import isfinite
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
_ANNUAL_DURATION_MIN_DAYS = 330
_ANNUAL_DURATION_MAX_DAYS = 380
_ISSUER_SCOPES = frozenset({"issuer", "issuer_reported", "consolidated"})

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
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        y, m, d = str(value).split("-")
        return date(int(y), int(m), int(d))
    except Exception:  # noqa: BLE001
        return None


def _date_iso(value: Any) -> str | None:
    parsed = _parse_date(value)
    return parsed.isoformat() if parsed is not None else None


def _finite_amount(value: Any, scale: int, *, nonnegative: bool = False) -> float | None:
    """Scale one source amount without admitting bool, NaN, or infinity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        amount = float(value) * scale
    except (OverflowError, TypeError, ValueError):
        return None
    if not isfinite(amount) or (nonnegative and amount < 0):
        return None
    return amount


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
        "as_of": _date_iso(as_of),
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
    invalid_amount = False
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
                    amount = _finite_amount(entry.get("val"), scale, nonnegative=True)
                    if amount is None:
                        invalid_amount = True
                    else:
                        found_candidates.append(amount)
    if invalid_amount:
        return None, "invalid_value"
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
    *, nonnegative: bool = False,
) -> tuple[float | None, str | None, str | None]:
    """Find a duration fact (ocf or capex) for the exact winning period.

    Returns (usd_value, start, drop_reason). The fact must match accession,
    end, and a real annual start/end span.  A same-accession quarterly or
    year-to-date duration is not interchangeable with the annual fact.
    """
    tag_node = facts.get(tag) or {}
    units = tag_node.get("units") or {}
    found_any_unit = False
    found_recognized_unit = False
    missing_start = False
    invalid_duration = False
    invalid_amount = False
    found_candidates: list[tuple[float, str]] = []
    for unit_key, entries in units.items():
        scale = _unit_scale(unit_key)
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, Mapping):
                continue
            if (entry.get("accn") == win_accn and
                    entry.get("end") == win_end and
                    entry.get("form") in _ANNUAL_FORMS and
                    entry.get("fp") == "FY"):
                found_any_unit = True
                if scale is None:
                    continue
                found_recognized_unit = True
                if not entry.get("start"):
                    missing_start = True
                    continue
                start_date = _parse_date(entry.get("start"))
                end_date = _parse_date(entry.get("end"))
                if start_date is None or end_date is None:
                    invalid_duration = True
                    continue
                duration_days = (end_date - start_date).days + 1
                if not _ANNUAL_DURATION_MIN_DAYS <= duration_days <= _ANNUAL_DURATION_MAX_DAYS:
                    invalid_duration = True
                    continue
                amount = _finite_amount(entry.get("val"), scale, nonnegative=nonnegative)
                if amount is None:
                    invalid_amount = True
                    continue
                found_candidates.append((amount, start_date.isoformat()))

    # An exact-period malformed or short-duration occurrence makes the source
    # ambiguous even if another occurrence looks annual.  Selecting the good
    # row by iteration order would recreate the same period-mixing defect.
    if missing_start:
        return None, None, "duration_start_missing"
    if invalid_duration:
        return None, None, "duration_not_annual"
    if invalid_amount:
        return None, None, "invalid_value"

    starts = {start for _value, start in found_candidates}
    values = {round(value, 2) for value, _start in found_candidates}
    if len(starts) > 1:
        return None, None, "duration_start_conflict"
    if len(values) > 1:
        return None, None, "unit_conflict"
    if len(found_candidates) >= 1:
        value, start = found_candidates[0]
        return value, start, None
    if found_any_unit:
        return None, None, "unit_not_usd" if not found_recognized_unit else "invalid_value"
    for unit_key, entries in units.items():
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, Mapping):
                continue
            if entry.get("form") in _ANNUAL_FORMS and entry.get("fp") == "FY":
                return None, None, "period_mismatch"
    return None, None, "absent"


def _ladder_matches_period(
    ladder: Mapping[str, Any] | None,
    *,
    canon_cik: str,
    winner: Mapping[str, Any],
    cash_value: float,
    requested_as_of: date | None,
) -> bool:
    """Only allow near-term coverage from the same issuer and filing.

    ``ladder`` is an optional compatibility input.  The combined
    ``capital_need.v1`` adapter applies the same rule, but enforcing it here
    prevents older callers from silently reviving the former cross-period
    arithmetic path.
    """
    if not isinstance(ladder, Mapping):
        return False
    if ladder.get("schema") != "debt_maturity.v1" or ladder.get("status") != "reported":
        return False
    if _canonical_cik_or_none(ladder.get("cik")) != canon_cik:
        return False
    if ladder.get("unit", "USD") != "USD" or ladder.get("currency", "USD") != "USD":
        return False
    declared_scopes = [
        ladder[key] for key in ("scope", "source_scope") if key in ladder
    ]
    if any(type(scope) is not str or scope not in _ISSUER_SCOPES for scope in declared_scopes):
        return False
    if len(declared_scopes) == 2 and declared_scopes[0] != declared_scopes[1]:
        return False
    if not isfinite(cash_value) or cash_value < 0:
        return False

    ladder_period = ladder.get("period")
    if not isinstance(ladder_period, Mapping):
        return False
    if (
        type(winner.get("fy")) is not int
        or type(ladder_period.get("fy")) is not int
        or not 1 <= winner["fy"] <= 9999
        or not 1 <= ladder_period["fy"] <= 9999
    ):
        return False
    if "stale" in ladder_period and type(ladder_period["stale"]) is not bool:
        return False
    for key in ("accn", "end", "filed", "form", "fp", "fy"):
        if winner.get(key) in (None, "") or ladder_period.get(key) in (None, ""):
            return False
        if ladder_period.get(key) != winner.get(key):
            return False

    # A source must have existed by its own capture cutoff, and that cutoff
    # must itself be no later than the requested calculation cutoff.
    requested = _parse_date(requested_as_of)
    cash_filed = _parse_date(winner.get("filed"))
    debt_filed = _parse_date(ladder_period.get("filed"))
    debt_as_of = _parse_date(ladder.get("as_of"))
    period_end = _parse_date(winner.get("end"))
    if None in (requested, cash_filed, debt_filed, debt_as_of, period_end):
        return False
    assert requested is not None and cash_filed is not None and debt_filed is not None
    assert debt_as_of is not None and period_end is not None
    if (
        cash_filed < period_end
        or debt_filed < period_end
        or cash_filed > requested
        or debt_filed > debt_as_of
        or debt_as_of > requested
    ):
        return False
    if (requested - period_end).days > _STALE_DAYS:
        return False
    if ladder_period.get("stale") is True or winner.get("stale") is True:
        return False
    return True


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
    ocf_val, ocf_start, ocf_drop = _find_duration_fact(
        facts, "NetCashProvidedByUsedInOperatingActivities", win_accn, win_end
    )
    capex_val, capex_start, capex_drop = _find_duration_fact(
        facts, "PaymentsToAcquirePropertyPlantAndEquipment", win_accn, win_end,
        nonnegative=True,
    )

    # OCF and capex are a single annual scenario basis only when they cover
    # the same duration.  Same accession/end alone can still mix annual and
    # quarterly/YTD facts.
    if not ocf_drop and not capex_drop and ocf_start != capex_start:
        ocf_drop = "duration_start_mismatch"
        capex_drop = "duration_start_mismatch"
    period_start = ocf_start if not ocf_drop and not capex_drop else None

    # If ANY of the three is absent for the period, report no_cash_facts with per-tag drop reasons
    missing = []
    if cash_drop:
        missing.append(("cash", cash_drop))
    if ocf_drop:
        missing.append(("ocf", ocf_drop))
    if capex_drop:
        missing.append(("capex", capex_drop))

    def no_cash_result(drop_reasons: list[tuple[str, str]]) -> dict[str, Any]:
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
                "start": period_start,
                "end": win_end,
                "filed": winner.get("filed"),
                "accn": win_accn,
                "label": f"FY{winner.get('fy')}" if winner.get("fy") else win_end,
                "stale": False,
            },
            "drop_reasons": drop_reasons,
            "as_of": _date_iso(as_of),
        }

    if missing:
        return no_cash_result(missing)

    # All three facts present
    fcf = (ocf_val or 0) - (capex_val or 0)
    if not isfinite(fcf):
        return no_cash_result([("arithmetic", "invalid_arithmetic")])

    monthly_burn: float | None = None
    monthly_burn_display: str | None = None
    annual_burn: float | None = None
    annual_burn_display: str | None = None
    runway_months: float | None = None
    runway_display: str | None = None

    if fcf < 0:
        annual_burn = -fcf
        monthly_burn = annual_burn / 12
        if not isfinite(monthly_burn) or monthly_burn <= 0:
            return no_cash_result([("arithmetic", "invalid_arithmetic")])
        annual_burn_display = _usd_dollars(annual_burn)
        monthly_burn_display = _usd_dollars(monthly_burn)
        try:
            runway_months = (cash_val or 0) / monthly_burn
        except (OverflowError, ZeroDivisionError):
            return no_cash_result([("arithmetic", "invalid_arithmetic")])
        if not isfinite(runway_months):
            return no_cash_result([("arithmetic", "invalid_arithmetic")])
        # Cap display at > 10 years (> 120 months). Closed enum: the
        # template composes the user-facing EN/ZH sentence from this
        # token plus the numeric runway_months.
        if runway_months > 120:
            runway_display = "more_than_10_years"
        else:
            runway_display = "months"
    else:
        runway_display = "self_funding"

    end_date = _parse_date(win_end)
    stale = bool(as_of and end_date and (as_of - end_date).days > _STALE_DAYS)

    near_term_cover_pct: float | None = None
    if _ladder_matches_period(
        ladder,
        canon_cik=canon_cik,
        winner=winner,
        cash_value=float(cash_val),
        requested_as_of=_parse_date(as_of),
    ):
        buckets = ladder.get("buckets")
        if isinstance(buckets, list):
            y1_rows = [
                bucket for bucket in buckets
                if isinstance(bucket, Mapping) and bucket.get("key") == "y1"
            ]
            if len(y1_rows) == 1 and y1_rows[0].get("reported") is True:
                y1_value = _finite_amount(
                    y1_rows[0].get("usd"), 1, nonnegative=True
                )
                if y1_value is not None and y1_value > 0:
                    try:
                        cover_pct = (cash_val / y1_value) * 100
                    except (OverflowError, ZeroDivisionError):
                        cover_pct = None
                    if cover_pct is not None and isfinite(cover_pct):
                        near_term_cover_pct = round(cover_pct)

    return {
        "schema": "cash_runway.v1",
        "status": "reported",
        "cik": canon_cik,
        "unit": "USD",
        "currency": "USD",
        "scope": "issuer_reported",
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
            "start": period_start,
            "end": win_end,
            "filed": winner.get("filed"),
            "accn": win_accn,
            "label": f"FY{winner.get('fy')}" if winner.get("fy") else win_end,
            "stale": stale,
        },
        "as_of": _date_iso(as_of),
    }
