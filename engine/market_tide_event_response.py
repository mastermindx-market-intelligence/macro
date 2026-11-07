"""Point-in-time event/sector response context for Market Tide.

Pure, read-only, and intentionally descriptive. It does not infer event causality,
dealer positions, trade direction, alpha, forecast probabilities or risk authority.
Original events/news, security identity, and price/bar admission remain with their
incumbent owners. Source observations are supplied explicitly.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import math
from typing import Any, Mapping

SCHEMA = "market_tide.event_response/v1"
AUTHORITY = {
    "may_rank": False, "may_gate": False, "may_size": False,
    "may_trade": False, "may_alert": False, "may_forecast": False,
}
_ALLOWED_EVENT_STATES = {"scheduled", "unresolved", "resolved", "cancelled"}
_ALLOWED_LINK_CLASSES = {"verified_fact", "scenario", "hypothesis"}


def _clock(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: timezone-aware ISO timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise ValueError(f"{name}: malformed timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{name}: timezone required")
    return parsed.astimezone(timezone.utc)


def _id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name}: nonempty identifier required")
    return value.strip()


def _number(value: Any, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{name}: finite number required")
    out = float(value)
    if not math.isfinite(out):
        raise ValueError(f"{name}: finite number required")
    return out


def _available(source: Mapping[str, Any] | None, cutoff: datetime,
               max_age_seconds: float) -> tuple[bool, str | None]:
    """Check observation, admission and freshness independently of file mtime."""
    if not isinstance(source, Mapping):
        return False, "MISSING_SOURCE"
    try:
        observed = _clock(source.get("observed_at"), "observed_at")
        usable = _clock(source.get("usable_at"), "usable_at")
        _id(source.get("source_ref"), "source_ref")
        _id(source.get("revision"), "revision")
        _id(source.get("rights_ref"), "rights_ref")
    except ValueError:
        return False, "INVALID_SOURCE"
    if observed > usable:
        return False, "IMPOSSIBLE_SOURCE_CLOCK"
    if usable > cutoff:
        return False, "SOURCE_NOT_YET_USABLE"
    if (cutoff - observed).total_seconds() > max_age_seconds:
        return False, "STALE_SOURCE"
    if source.get("status") not in ("complete", "partial"):
        return False, "SOURCE_NOT_ADMITTED"
    return True, None


def _safe_ref(source: Mapping[str, Any]) -> dict:
    out = {name: source[name] for name in
           ("source_ref", "revision", "observed_at", "usable_at", "rights_ref", "status")}
    if isinstance(source.get("return_window_ref"), str):
        out["return_window_ref"] = source["return_window_ref"]
    return out


def _same_return_window(*sources: Mapping[str, Any]) -> bool:
    """Separate price feeds may enter one factor equation only on one exact window.

    The upstream admitted price owner must establish what each window reference
    means; identical symbols or dates do not themselves prove aligned returns.
    """
    if not all(isinstance(source, Mapping) for source in sources):
        return False
    names = [source.get("return_window_ref") for source in sources]
    return all(isinstance(name, str) and bool(name.strip()) for name in names) and len(set(names)) == 1


def compose(request: Mapping[str, Any]) -> dict:
    """Compose event response facts as known at decision_at.

    Units: simple percentage-point returns (1.5 means +1.5%), betas dimensionless.
    Event links identify research hypotheses or source facts, never numerical
    portions of a price move or proof of who traded. No persistence or I/O.
    """
    if not isinstance(request, Mapping):
        raise ValueError("request: object required")
    decision = _clock(request.get("decision_at"), "decision_at")
    max_age = _number(request.get("max_age_seconds"), "max_age_seconds")
    if max_age is None or not 0 < max_age <= 86400:
        raise ValueError("max_age_seconds must be in (0, 86400]")
    raw_events = request.get("events")
    raw_rows = request.get("securities")
    if not isinstance(raw_events, list) or len(raw_events) > 256:
        raise ValueError("events must be a bounded list")
    if not isinstance(raw_rows, list) or not raw_rows or len(raw_rows) > 5000:
        raise ValueError("securities must be a bounded nonempty list")

    # Known-at filtering is BEFORE any event's content reaches the consumer.
    events, known_events, seen_events, withheld = [], {}, set(), 0
    for event in raw_events:
        if not isinstance(event, Mapping):
            raise ValueError("event must be an object")
        event_id = _id(event.get("event_id"), "event_id")
        if event_id in seen_events:
            raise ValueError("duplicate event_id")
        seen_events.add(event_id)
        known_at = _clock(event.get("known_at"), "event.known_at")
        if known_at > decision:
            withheld += 1
            continue
        _id(event.get("source_ref"), "event.source_ref")
        _id(event.get("revision"), "event.revision")
        _id(event.get("rights_ref"), "event.rights_ref")
        state = event.get("resolution_state")
        if state not in _ALLOWED_EVENT_STATES:
            raise ValueError("invalid resolution_state")
        resolution_valid = False
        if state == "resolved":
            try:
                resolution_at = _clock(event.get("resolved_at"), "resolved_at")
                _id(event.get("resolution_ref"), "resolution_ref")
                resolution_valid = resolution_at <= decision
            except ValueError:
                resolution_valid = False
        status = "admitted" if state != "resolved" or resolution_valid else "resolution_unverified"
        known_events[event_id] = status
        events.append({
            "event_id": event_id, "event_type": event.get("event_type"),
            "source_ref": event["source_ref"], "revision": event["revision"],
            "resolution_state": state if status == "admitted" else "unverified",
            "status": status, "known_at": event["known_at"],
        })

    benchmark = request.get("market")
    market_ok, market_reason = _available(benchmark, decision, max_age)
    market_return = None
    if market_ok:
        market_return = _number(benchmark.get("return_pct"), "market.return_pct")
        if market_return is None:
            market_ok, market_reason = False, "MISSING_MARKET_RETURN"

    rows, seen_ids, valid_count, modeled_count = [], set(), 0, 0
    withheld_links = 0
    for raw in raw_rows:
        if not isinstance(raw, Mapping):
            raise ValueError("security row must be an object")
        security_id = _id(raw.get("security_id"), "security_id")
        if security_id in seen_ids:
            raise ValueError("duplicate security_id")
        seen_ids.add(security_id)
        observed_ok, reason = _available(raw.get("source"), decision, max_age)
        ret = _number(raw.get("return_pct"), "security.return_pct")
        if ret is None:
            observed_ok, reason = False, reason or "MISSING_SECURITY_RETURN"
        links = raw.get("event_links", [])
        if not isinstance(links, list) or len(links) > 128:
            raise ValueError("event_links must be a bounded list")
        admitted_links = []
        for link in links:
            if not isinstance(link, Mapping):
                raise ValueError("event link must be an object")
            event_id = _id(link.get("event_id"), "link.event_id")
            link_known_at = _clock(link.get("known_at"), "link.known_at")
            if link_known_at > decision or known_events.get(event_id) != "admitted":
                withheld_links += 1
                continue
            if link.get("evidence_class") not in _ALLOWED_LINK_CLASSES:
                raise ValueError("link evidence class invalid")
            admitted_links.append({
                "event_id": event_id,
                "channel": _id(link.get("channel"), "link.channel"),
                "evidence_class": link["evidence_class"],
                "source_ref": _id(link.get("source_ref"), "link.source_ref"),
                "scenario_direction": link.get("scenario_direction"),
                "causality_established": False,
            })
        result = {
            "security_id": security_id, "ticker": raw.get("ticker"),
            "status": "observed" if observed_ok else "unavailable",
            "reason": None if observed_ok else reason,
            "return_pct": ret if observed_ok else None,
            "source": _safe_ref(raw["source"]) if observed_ok else None,
            "event_links": admitted_links, "decomposition": None,
        }
        if observed_ok:
            valid_count += 1
            # Sector excess prevents subtracting overlapping factor returns twice.
            sector_return = _number(raw.get("sector_return_pct"), "sector_return_pct")
            market_beta = _number(raw.get("market_beta"), "market_beta")
            sector_beta = _number(raw.get("sector_excess_beta"), "sector_excess_beta")
            fit_time = raw.get("factor_fit_known_at")
            factor_ready = False
            if fit_time is not None:
                factor_clock = _clock(fit_time, "factor_fit_known_at")
                event_start = _clock(raw.get("event_start_at"), "event_start_at")
                factor_ready = factor_clock <= min(event_start, decision)
            # Sector returns are an independent economic input. A bare number
            # cannot enter a pre-event attribution unless its source is admitted
            # by the same cutoff, fresh and aligned with stock and market windows.
            sector_source = raw.get("sector_source")
            sector_ok, _sector_reason = _available(sector_source, decision, max_age)
            aligned = (sector_ok and market_ok and _same_return_window(
                raw["source"], benchmark, sector_source))
            if (aligned and factor_ready and sector_return is not None
                    and market_beta is not None and sector_beta is not None):
                market_part = market_beta * market_return
                sector_part = sector_beta * (sector_return - market_return)
                residual = ret - math.fsum((market_part, sector_part))
                result["decomposition"] = {
                    "market_pct": round(market_part, 6),
                    "sector_excess_pct": round(sector_part, 6),
                    "unexplained_pct": round(residual, 6),
                    "method": "market_plus_sector_excess/v1",
                    "causal_attribution": False,
                }
                result["factor_receipts"] = {
                    "market": _safe_ref(benchmark),
                    "sector": _safe_ref(sector_source),
                    "return_window_ref": raw["source"]["return_window_ref"],
                }
                modeled_count += 1
        rows.append(result)

    return {
        "schema": SCHEMA, "evidence_class": "OBSERVATION",
        "decision_at": decision.isoformat().replace("+00:00", "Z"),
        "event_count_known": len(events), "event_count_withheld": withheld,
        "events": events, "market_status": "admitted" if market_ok else "unavailable",
        "market_reason": None if market_ok else market_reason,
        "securities": rows,
        "coverage": {
            "eligible": len(raw_rows), "observed": valid_count,
            "modeled": modeled_count, "unavailable": len(raw_rows) - valid_count,
            "event_links_withheld": withheld_links,
        },
        "interpretation": "descriptive_noncausal",
        "forecast": None, "hedge_flow": None,
        "authority": deepcopy(AUTHORITY),
    }
