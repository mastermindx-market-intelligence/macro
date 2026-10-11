"""Public projection of admitted SEC earnings and documented issuer events.

This is a PURE read-model adapter, never a news/rights/source authority. The
caller supplies issuer identity from the existing qualified universe and a
trusted, server-side rights-owner resolver. Raw event/feed payloads must never
contain or select their own grant. No network, storage, LLM, or publication.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import ipaddress
import math
import re
from typing import Callable, Mapping, Sequence
from urllib.parse import urlsplit

from engine.company_intelligence.contracts import ContractError, safe_ticker

SCHEMA_VERSION = "catalyst.public_event/v1"
SCHEMA_REVISION = 1
PUBLIC_AUDIENCE = "public_anonymous"
_EARNINGS_SOURCE = "edgar_8k_202"
_SOURCE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")
_ACCESSION = re.compile(r"^\d{10}:\d{10}-\d{2}-\d{6}$")
_SCENARIO_CASES = {"bull", "base", "bear"}
_TRIGGER_COPY = {
    "guidance_raised": "A subsequent issuer filing raises guidance",
    "figures_confirmed": "A subsequent issuer filing confirms the reported figures",
    "guidance_reduced": "A subsequent issuer filing reduces guidance",
    "filing_amended": "A later official filing amends the reported figures",
    "relationship_confirmed": "A later official disclosure confirms the business relationship",
}
_INVALIDATOR_COPY = {
    "guidance_reversed": "Subsequent filed guidance reverses the premise",
    "source_withdrawn": "The supporting source is withdrawn",
    "filing_corrected": "The issuer corrects the cited figures",
    "relationship_disproved": "The documented relationship is disproved",
}
_RELATION_COPY = {
    "supplier": "Documented supplier relationship",
    "customer": "Documented customer relationship",
    "competitor": "Documented competitor relationship",
    "investment": "Documented investment relationship",
    "contract": "Documented commercial contract",
}


@dataclass(frozen=True, slots=True)
class PublicSourceGrant:
    """Qualified capability from the EXISTING source-rights owner, not an API input.

    Construct only inside a trusted rights adapter, after source-specific
    owner qualification (e.g. qbus receipt's public audience + capabilities).
    Merely seeing a public URL, story, vendor license, or ``site_full`` grant
    must NEVER instantiate this capability.
    """
    source_id: str
    receipt_id: str
    owner_ref: str
    audience: str
    effective_at_utc: datetime
    expires_at_utc: datetime
    display_link: bool
    display_title: bool
    display_facts: bool


RightsResolver = Callable[[str, datetime], PublicSourceGrant | None]


def _utc(value: object, *, producer_utc_naive: bool = False) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        if not producer_utc_naive:
            return None
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _stamp(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds").replace("+00:00", "Z") if value else None


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _number(value: float) -> str:
    return f"{value:,.8f}".rstrip("0").rstrip(".")


def _fingerprint(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:24]


def _safe_url(raw: object, *, sec_only: bool) -> str | None:
    if not isinstance(raw, str) or len(raw) > 2048:
        return None
    try:
        url = urlsplit(raw)
    except ValueError:
        return None
    if url.scheme != "https" or not url.hostname or url.username or url.password:
        return None
    try:
        port = url.port
    except ValueError:
        return None
    if port not in (None, 443) or any(ch.isspace() for ch in raw):
        return None
    host = url.hostname.lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
        return None
    # Public links must not point to an RFC1918, loopback, or other IP literal;
    # the Session 00 HTTP serializer independently applies the same boundary.
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        return None
    if sec_only and (host not in {"sec.gov", "www.sec.gov"}
                     or not url.path.startswith("/Archives/")):
        return None
    return raw


def _allowed(source_id: str, resolver: RightsResolver, now: datetime) -> PublicSourceGrant | None:
    try:
        grant = resolver(source_id, now)
    except Exception:  # a missing/degraded rights owner is denial, not authority
        return None
    if not isinstance(grant, PublicSourceGrant):
        return None
    if (grant.source_id != source_id or grant.audience != PUBLIC_AUDIENCE
            or not isinstance(grant.receipt_id, str)
            or not 0 < len(grant.receipt_id.strip()) <= 128
            or not isinstance(grant.owner_ref, str) or not grant.owner_ref.strip()
            or not (grant.display_link and grant.display_title and grant.display_facts)
            or not all(isinstance(v, bool) for v in
                       (grant.display_link, grant.display_title, grant.display_facts))):
        return None
    start, end = _utc(grant.effective_at_utc), _utc(grant.expires_at_utc)
    if start is None or end is None or not start <= now < end:
        return None
    return grant


def _base(event_id: str | None, as_of: datetime) -> dict:
    return {
        "schema": SCHEMA_VERSION, "schema_version": SCHEMA_REVISION,
        "event_id": event_id,
        "event_kind": None, "primary_subject": None,
        "event_time_utc": None, "first_observed_at_utc": None,
        "publication_time_utc": None, "as_of_utc": _stamp(as_of),
        "source_refs": [], "evidence": [], "affected_tickers": [],
        "what_changed": [], "scenarios": [], "invalidators": [],
        "missing_data": [], "correction": {"generation": 0, "status": "active"},
        "public_safe": False, "rights_receipt_ids": [],
        "cache_expires_at_utc": None,
        "generation": 0, "correction_state": "CURRENT",
        "sources": [], "partial_reason": None, "public_disposition": "UNAVAILABLE",
    }


def build_event_packet(
    source_event: Mapping[str, object], *,
    issuers: Mapping[str, Mapping[str, object]],
    rights_resolver: RightsResolver,
    as_of: datetime,
    source_refs: Sequence[Mapping[str, object]] = (),
    relationships: Sequence[Mapping[str, object]] = (),
    scenarios: Sequence[Mapping[str, object]] = (),
    max_age: timedelta = timedelta(days=14),
) -> dict:
    """Return safe packet; deny absent rights/identity/time. No untrusted text.

    First producer: ``edgar_earnings_wire.build_event`` with its filing key,
    acceptance datetime and processing clock. Documented-event source rows must
    instead carry an owner-assigned event_id, subject issuer and source time;
    source titles are the only display material until source-backed claims are
    explicitly integrated. Call only with canonical, server-owned inputs.
    """
    now = _utc(as_of)
    if now is None:
        raise ValueError("as_of requires timezone-aware UTC-compatible datetime")
    if not isinstance(source_event, Mapping):
        raise TypeError("source_event must be a mapping")
    source = source_event.get("source")
    earnings = source == _EARNINGS_SOURCE
    filing_key = source_event.get("filing_key")
    if earnings and isinstance(filing_key, str) and _ACCESSION.fullmatch(filing_key):
        event_id = "sec-earnings-" + _fingerprint(filing_key)
        primary_source_id = "sec:" + filing_key
        kind = "earnings"
    else:
        event_id = source_event.get("event_id") if not earnings else None
        event_id = event_id if isinstance(event_id, str) and _SOURCE_ID.fullmatch(event_id) else None
        primary_source_id = source_event.get("source_id")
        kind = source_event.get("event_kind")
        if kind not in ("ai_capex", "semiconductor_event"):
            kind = None
    out = _base(event_id, now)
    out["event_kind"] = kind
    if not event_id or not kind or not isinstance(primary_source_id, str) or not _SOURCE_ID.fullmatch(primary_source_id):
        out["missing_data"].append("unqualified_event_identity")
        return out

    ticker_raw = source_event.get("ticker")
    try:
        ticker = safe_ticker(ticker_raw)
    except ContractError:
        out["missing_data"].append("unqualified_primary_ticker")
        return out
    issuer = issuers.get(ticker)
    if not isinstance(issuer, Mapping) or issuer.get("supported") is not True:
        out["missing_data"].append("primary_not_in_qualified_universe")
        return out
    issuer_id = issuer.get("issuer_id")
    if not isinstance(issuer_id, str) or not issuer_id:
        out["missing_data"].append("missing_canonical_issuer_identity")
        return out
    if earnings:
        cik = source_event.get("cik")
        if (isinstance(cik, bool) or not isinstance(cik, int) or cik <= 0
                or issuer_id != f"cik:{cik:010d}" or not str(filing_key).startswith(f"{cik:010d}:")):
            out["missing_data"].append("filing_issuer_identity_mismatch")
            return out
    elif source_event.get("issuer_id") != issuer_id:
        out["missing_data"].append("source_issuer_identity_mismatch")
        return out

    event_time = _utc(source_event.get("acceptance_datetime") if earnings else source_event.get("event_time_utc"))
    observed = _utc(source_event.get("when") if earnings else source_event.get("first_observed_at_utc"),
                    producer_utc_naive=earnings and source_event.get("when_semantics") == "processing_wall_clock")
    if (event_time is None or observed is None or event_time > now + timedelta(minutes=2)
            or observed > now + timedelta(minutes=2) or observed < event_time - timedelta(minutes=2)):
        out["missing_data"].append("unqualified_source_clocks")
        return out
    out.update(primary_subject={"ticker": ticker, "issuer_id": issuer_id,
                                "company_name": str(issuer.get("name") or ticker)[:120]},
               event_time_utc=_stamp(event_time), first_observed_at_utc=_stamp(observed))
    pub_time = _utc(source_event.get("publication_time_utc"))
    if pub_time is not None and event_time <= pub_time <= now:
        out["publication_time_utc"] = _stamp(pub_time)
    else:
        out["missing_data"].append("publication_time_not_attested")

    generation = source_event.get("correction_generation", 0)
    if isinstance(generation, bool) or not isinstance(generation, int) or not 0 <= generation <= 10_000:
        out["missing_data"].append("invalid_revision")
        return out
    revision_state = source_event.get("revision_status", "active")
    if revision_state not in ("active", "corrected", "retracted"):
        out["missing_data"].append("invalid_revision_status")
        return out
    if (generation and revision_state == "active") or (not generation and revision_state != "active"):
        out["missing_data"].append("revision_without_correction_state")
        return out
    out["correction"] = {"generation": generation, "status": revision_state}
    out["generation"] = generation
    out["correction_state"] = {"active": "CURRENT", "corrected": "CORRECTED", "retracted": "RETRACTED"}[revision_state]
    if generation:
        prior = source_event.get("supersedes_generation")
        reason = source_event.get("correction_reason")
        if (isinstance(prior, bool) or not isinstance(prior, int) or not 0 <= prior < generation
                or reason not in ("official_amendment", "source_retraction", "data_correction")):
            out["missing_data"].append("unqualified_correction")
            return out
        out["correction"].update(supersedes_generation=prior, reason=reason)
    if revision_state == "retracted":
        out["public_safe"] = False
        out["public_disposition"] = "RETRACTED"
        out["missing_data"].append("source_retracted")
        return out
    if now - event_time > max_age:
        out["missing_data"].append("event_outside_freshness_window")
        return out

    if earnings:
        primary = {"source_id": primary_source_id, "url": source_event.get("source_url"),
                   "title": "SEC Form 8-K Item 2.02",
                   "published_at_utc": source_event.get("publication_time_utc"),
                   "first_observed_at_utc": _stamp(observed), "evidence_ids": []}
    else:
        primary = {"source_id": primary_source_id, "url": source_event.get("source_url"),
                   "title": source_event.get("source_title"),
                   "published_at_utc": source_event.get("publication_time_utc"),
                   "first_observed_at_utc": source_event.get("first_observed_at_utc"),
                   "evidence_ids": []}
    entries = [primary, *source_refs]
    accepted: dict[str, dict] = {}
    blocked: set[str] = set()
    grants: list[PublicSourceGrant] = []
    attested_evidence: dict[str, set[str]] = {}
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        sid = entry.get("source_id")
        if not isinstance(sid, str) or not _SOURCE_ID.fullmatch(sid):
            continue
        # An earlier conflicting source ID stays quarantined: a subsequent
        # duplicate cannot resurrect a disqualified display identity.
        if sid in blocked:
            continue
        ids = entry.get("evidence_ids")
        if isinstance(ids, (list, tuple)):
            attested_evidence[sid] = {i for i in ids if isinstance(i, str) and _SOURCE_ID.fullmatch(i)}
        url = _safe_url(entry.get("url"), sec_only=earnings and sid == primary_source_id)
        grant = _allowed(sid, rights_resolver, now)
        if url is None or grant is None:
            blocked.add(sid)
            continue
        if sid in accepted:
            # One source ID cannot alias differing title/URL/publication data.
            if (accepted[sid]["url"] != url
                    or accepted[sid]["title"] != entry.get("title")
                    or accepted[sid]["published_at_utc"] != _stamp(_utc(entry.get("published_at_utc")))):
                blocked.add(sid)
                accepted.pop(sid)
            continue
        title = entry.get("title")
        if not isinstance(title, str) or not 0 < len(title.strip()) <= 150:
            blocked.add(sid)
            continue
        published = _utc(entry.get("published_at_utc"))
        first_seen = _utc(entry.get("first_observed_at_utc"))
        if published is None or published > now:
            blocked.add(sid)
            continue
        if first_seen is not None and first_seen > now:
            first_seen = None
        accepted[sid] = {"source_id": sid, "title": title.strip(), "url": url,
                         "display_rights": "ALLOWED",
                         "published_at_utc": _stamp(published),
                         "first_observed_at_utc": _stamp(first_seen),
                         "rights_receipt_id": grant.receipt_id}
        grants.append(grant)
    # The public consumer accepts no more than twelve qualified sources.
    # Never silently truncate a claim's supporting evidence.
    if len(accepted) > 12:
        out["missing_data"].append("too_many_public_sources")
        return out
    if primary_source_id not in accepted or primary_source_id in blocked:
        out["public_safe"] = False
        out["public_disposition"] = "BLOCKED_PUBLIC"
        out["missing_data"].append("primary_source_public_rights_unavailable")
        return out
    out["source_refs"] = list(accepted.values())
    out["sources"] = list(accepted.values())
    out["rights_receipt_ids"] = sorted({g.receipt_id for g in grants if g.source_id in accepted})
    expiry = min([now + timedelta(minutes=5), event_time + max_age,
                  *[g.expires_at_utc for g in grants if g.source_id in accepted]])
    out["cache_expires_at_utc"] = _stamp(expiry)

    out["affected_tickers"].append({"ticker": ticker, "relationship": "DIRECT",
                                      "relation_evidence_ids": [], "relation_type": "issuer_filing"})
    if earnings:
        for field, basis, unit in (("eps_actual", source_event.get("_eps_basis"), "USD/share"),
                                   ("rev_actual", "reported", "USD")):
            value = _finite(source_event.get(field))
            if value is None or (field == "rev_actual" and value < 0):
                out["missing_data"].append("missing_or_invalid_" + field)
                continue
            if field == "eps_actual" and basis not in ("gaap", "adjusted"):
                out["missing_data"].append("unqualified_eps_basis")
                continue
            evid = _fingerprint(f"{event_id}:{generation}:{field}")
            copy = (f"{ticker} reported {basis.upper()} EPS of {_number(value)} USD/share."
                    if field == "eps_actual" else
                    f"{ticker} reported revenue of {_number(value)} USD.")
            out["evidence"].append({"evidence_id": evid, "source_id": primary_source_id,
                                     "kind": field, "value": value, "unit": unit, "basis": basis})
            out["what_changed"].append({"text": copy, "evidence_ids": [evid]})
        out["missing_data"].append("consensus_not_independently_evidenced")
    else:
        # Model/source headlines are not independent evidence of numbers,
        # causal impact, or relationships; preserve only the verified title.
        out["what_changed"].append({"text": accepted[primary_source_id]["title"],
                                    "evidence_ids": [], "source_ids": [primary_source_id]})
        out["missing_data"].append("numerical_claims_not_qualified")

    for relation in relationships:
        if not isinstance(relation, Mapping) or relation.get("relationship") != "EVIDENCED_INDIRECT":
            continue
        target = relation.get("ticker")
        try:
            target = safe_ticker(target)
        except ContractError:
            continue
        info = issuers.get(target)
        if target == ticker or not isinstance(info, Mapping) or info.get("supported") is not True:
            continue
        if relation.get("issuer_id") != info.get("issuer_id") or relation.get("primary_issuer_id") != issuer_id:
            continue
        sid, eid = relation.get("source_id"), relation.get("evidence_id")
        relkind = relation.get("relation_type")
        if not isinstance(sid, str) or not isinstance(eid, str) or not _SOURCE_ID.fullmatch(eid):
            continue
        if (relkind not in _RELATION_COPY or not relation.get("source_anchor")
                or eid not in attested_evidence.get(sid, set())):
            continue
        if sid not in accepted:
            if sid in blocked:
                out.setdefault("rights_blocked_tickers", []).append(target)
            continue
        if any(t["ticker"] == target for t in out["affected_tickers"]):
            continue
        out["evidence"].append({"evidence_id": eid, "source_id": sid, "kind": "relationship",
                                "relation_type": relkind})
        out["affected_tickers"].append({"ticker": target,
                "relationship": "EVIDENCED_INDIRECT", "relation_type": relkind,
                "relation_evidence_ids": [eid], "summary": _RELATION_COPY[relkind]})

    known = {entry["evidence_id"] for entry in out["evidence"]}
    cases: set[str] = set()
    for row in scenarios:
        if not isinstance(row, Mapping):
            continue
        case, trigger, invalidator = row.get("case"), row.get("trigger"), row.get("invalidator")
        evidence_ids = row.get("evidence_ids")
        if (case not in _SCENARIO_CASES or case in cases or trigger not in _TRIGGER_COPY
                or invalidator not in _INVALIDATOR_COPY
                or not isinstance(evidence_ids, (list, tuple)) or not evidence_ids
                or not all(isinstance(x, str) and x in known for x in evidence_ids)):
            continue
        cases.add(case)
        out["scenarios"].append({"case": case, "trigger": _TRIGGER_COPY[trigger],
                                  "evidence_ids": list(evidence_ids),
                                  "invalidator": _INVALIDATOR_COPY[invalidator],
                                  "forecast_probability": None})
        if _INVALIDATOR_COPY[invalidator] not in out["invalidators"]:
            out["invalidators"].append(_INVALIDATOR_COPY[invalidator])
    if not out["scenarios"]:
        out["missing_data"].append("no_evidence_qualified_scenarios")
    if not out["what_changed"]:
        out["missing_data"].append("no_supported_material_facts")
        return out
    out["public_safe"] = True
    out["public_disposition"] = "PUBLIC_READY"
    out["partial_reason"] = ",".join(out["missing_data"]) or None
    return out
