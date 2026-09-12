"""Read-only projection for the existing transmission page, not another engine.

The analytical owner is rates_command.regime_outlook. This adapter checks the
actual transmission bytes before exposing the same object to the page. It never
fits, collects, appends a ledger, or treats a content digest as economic authority.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from engine.rates_regime_outlook import SCHEMA, _research_contract
from engine.regime_research import validate_seal
from engine.regime_research_inputs import cutoff_utc
from engine.regime_transition_research import AUTHORITY, month_number


def prepare_view(outlook: Any, transmission_bytes: bytes, *, now: str | datetime) -> dict:
    """Validate the saved generation; do not silently render a stale join."""
    cutoff = cutoff_utc(now)
    base = {"status": "unavailable", "reason": "research_not_published", "outlook": None,
            "quantitative_available": False, "quantitative_origin_current": False,
            "quantitative_age_days": None, "transmission_sha256": hashlib.sha256(transmission_bytes).hexdigest()}
    if not isinstance(outlook, dict):
        return base
    if outlook.get("schema") != SCHEMA or not validate_seal(outlook):
        return dict(base, reason="invalid_research_generation")
    authority = outlook.get("authority")
    if not isinstance(authority, dict) or set(authority) != set(AUTHORITY) or any(v is not False for v in authority.values()):
        return dict(base, reason="unsupported_research_authority")
    if outlook.get("transmission_sha256") != base["transmission_sha256"]:
        return dict(base, reason="transmission_generation_mismatch")
    try:
        analyzed = cutoff_utc(outlook.get("analysis_cutoff"))
    except (ValueError, TypeError):
        return dict(base, reason="unknown_analysis_clock")
    if analyzed > cutoff:
        return dict(base, reason="future_analysis_clock")
    # An unchanged input hash is not a license to call old analysis current.
    age = (cutoff - analyzed).total_seconds() / 86400
    status = "historical" if age > 7 else outlook.get("availability", "unavailable")
    if status not in ("partial", "unavailable", "historical"):
        return dict(base, reason="unsupported_availability_state")
    result = dict(base, status=status, reason=None, outlook=outlook,
                  analysis_age_days=age, analysis_date=analyzed.date().isoformat())
    research = outlook.get("quantitative_research")
    if research is not None:
        if not _research_contract(research):
            return dict(base, reason="invalid_quantitative_contract")
        try:
            issued = cutoff_utc(research.get("analysis_cutoff"))
            if issued > cutoff:
                return dict(base, reason="future_quantitative_clock")
            result["quantitative_age_days"] = (cutoff-issued).total_seconds()/86400
            origin = research.get("origin_period")
            latest_closed = cutoff.year*12 + cutoff.month - 2
            result["quantitative_origin_current"] = month_number(origin) == latest_closed
            result["quantitative_available"] = research.get("forecast") is not None
        except (ValueError, TypeError):
            # An unavailable research object may legitimately have no origin.
            if research.get("forecast") is not None:
                return dict(base, reason="unknown_quantitative_clock")
    return result


def inject_fragment(html: str, fragment: str) -> str:
    """Compose at the existing template boundary; absence/duplication is a defect.

    Keeping this seam explicit avoids a second page renderer or a Javascript
    stylesheet/mount system. The canonical Jinja page retains all other content.
    """
    marker = "<!-- ===================== CHANNEL RAIL ===================== -->"
    if html.count(marker) != 1 or 'id="macro-regime-outlook"' in html:
        raise ValueError("Transmission composition anchor is missing or duplicated")
    return html.replace(marker, fragment + "\n  " + marker, 1)
