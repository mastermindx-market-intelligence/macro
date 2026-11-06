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
from urllib.parse import parse_qsl, unquote, urlsplit

from engine.company_intelligence.contracts import ContractError, safe_ticker

SCHEMA_VERSION = "catalyst.public_event/v1"
SCHEMA_REVISION = 1
STAGE_A_PACKET_SCHEMA = "catalyst.public_event/v2"
STAGE_A_PACKET_REVISION = 2
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
_PRIVATE_URL_KEYS = frozenset({
    "email", "e_mail", "phone", "ip", "token", "access_token", "auth",
    "authorization", "api_key", "apikey", "secret", "session", "user_id",
    "session_id", "signature", "password", "credential", "client_secret",
    "jwt", "bearer",
})
_URL_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I)

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
    # EXACT owner-approved document URL, not a filing-level allow-all.
    # Default is empty to keep older callers fail-closed.
    document_url: str = ""
    # Exact retained document bytes, when a verified source-read contract exists.
    document_sha256: str = ""


@dataclass(frozen=True, slots=True)
class VerifiedEarningsFigure:
    """Document-byte-replayed numeric evidence from the incumbent release parser.

    This value is not a license, a forecast or an independent earnings estimate.
    It must come from deterministic earnings_release.span receipts bound to the
    already pinned document SHA-256. Test doubles are explicitly synthetic.
    """
    field: str
    value: float
    basis: str
    document_sha256: str
    span_sha256: str


@dataclass(frozen=True, slots=True)
class VerifiedDocumentObservation:
    """Immutable successful source-owner observation; not a client claim.

    The incumbent SEC document reader supplies a retained first verified time,
    its current successful recheck, exact displayed document and content digest.
    SEC acceptance, producer processing and first verified availability are
    different clocks. Official publication may be unknown (None).
    """
    source_id: str
    document_url: str
    document_sha256: str
    receipt_id: str
    owner_ref: str
    first_verified_at_utc: datetime
    checked_at_utc: datetime
    # Common retained source-reader snapshot/version for packet→window join.
    source_snapshot_version: str = ""
    filing_form: str = ""
    amends_filing_key: str = ""
    verified_figures: tuple[VerifiedEarningsFigure, ...] = ()
    status: str = "verified"
    official_published_at_utc: datetime | None = None
    official_publication_ref: str = ""


_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
_SNAPSHOT_VERSION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


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
    # Every PUBLIC_READY packet can be consumed outside the HTTP serializer.
    # Unwrap nested query/fragment encoding before allowing a link to leave
    # the source boundary; refuse ambiguous excessive encoding and URL PII.
    decoded = raw
    for _ in range(4):
        try:
            parts = urlsplit(decoded)
        except ValueError:
            return None
        fields = (parse_qsl(parts.query, keep_blank_values=True) +
                  parse_qsl(parts.fragment, keep_blank_values=True))
        if any(key.strip().lower().replace("-", "_") in _PRIVATE_URL_KEYS
               for key, _ in fields):
            return None
        if (_URL_EMAIL.search(decoded) or
                any(ord(c) < 32 or ord(c) == 127 for c in decoded)):
            return None
        expanded = unquote(decoded)
        if expanded == decoded:
            break
        decoded = expanded
    else:
        if unquote(decoded) != decoded:
            return None
    # A fourth decoding pass may reveal a private key in the final string.
    # Scan it too, even if a fifth decode would make no further change.
    try:
        final = urlsplit(decoded)
    except ValueError:
        return None
    final_fields = (parse_qsl(final.query, keep_blank_values=True) +
                    parse_qsl(final.fragment, keep_blank_values=True))
    if any(key.strip().lower().replace("-", "_") in _PRIVATE_URL_KEYS
           for key, _ in final_fields):
        return None
    if _URL_EMAIL.search(decoded) or any(ord(c) < 32 or ord(c) == 127 for c in decoded):
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


def observation_from_pinned_sec_archive(
    source_event: Mapping[str, object], *, authority: object,
    manifest_key: str, first_retained_receipt_id: str,
    checked_at_utc: datetime,
) -> VerifiedDocumentObservation | None:
    """Verify an EXISTING immutable SEC-archive read for Stage-A ingestion.

    This helper adds no data store, network client, source grant or new clock.
    It consumes the incumbent Filing Forensics *concrete* pinned source
    authority, which validates the canonical source snapshot and reads both
    the document's receipt sidecar and exact bytes by checksum. The caller's
    first_retained_receipt_id must come from that source owner's historical
    original-receipt selection, never from a request or a fresh reprocessing.
    A single historical receipt does not itself prove issuer/window coverage;
    the separately attested SourceCoverageReceipt remains mandatory.

    Returns None on missing, stale, ambiguous or corrupted source evidence.
    This is NOT a rights decision: the exact URL/digest still needs the current
    source-rights owner's independently issued PublicSourceGrant.
    """
    try:
        from engine.fundamental_forensics.filing_attestation import (
            PinnedSourceAuthority,
        )
        from engine.fundamental_forensics.sec_document_spine import (
            HARD_MAX_ARCHIVE_DOCUMENT_BYTES,
            HARD_MAX_FILING_MANIFEST_BYTES,
            manifest_from_json_bytes,
        )
        from collectors.sec_document_spine import manifest_storage_key
        if (type(authority) is not PinnedSourceAuthority
                or not isinstance(source_event, Mapping)
                or source_event.get("source") != _EARNINGS_SOURCE
                or not isinstance(manifest_key, str)
                or not isinstance(first_retained_receipt_id, str)
                or not first_retained_receipt_id.strip()
                or len(first_retained_receipt_id) > 128):
            return None
        now = _utc(checked_at_utc)
        pinned_at = _utc(authority.snapshot_at)
        if (now is None or pinned_at is None or pinned_at > now
                or now - pinned_at > timedelta(minutes=10)):
            return None

        filing_key = source_event.get("filing_key")
        if not isinstance(filing_key, str) or not _ACCESSION.fullmatch(filing_key):
            return None
        cik = source_event.get("cik")
        if (type(cik) is not int or cik <= 0
                or not filing_key.startswith(f"{cik:010d}:")):
            return None
        expected_url = _safe_url(source_event.get("source_url"), sec_only=True)
        accepted = _utc(source_event.get("acceptance_datetime"))
        if expected_url is None or accepted is None or accepted > now:
            return None

        raw = authority.read_file(
            kind="archive", relative_path=manifest_key,
            maximum_bytes=HARD_MAX_FILING_MANIFEST_BYTES,
        )
        manifest = manifest_from_json_bytes(raw.content)
        if (manifest_storage_key(manifest) != manifest_key
                or manifest["issuer"]["cik"] != f"{cik:010d}"
                or manifest["filing"]["accession"] != filing_key.split(":", 1)[1]
                or manifest["filing"]["base_form"] != "8-K"
                or (source_event.get("form") not in (None, "", manifest["filing"]["form"]))
                or "2.02" not in {token.strip() for token in
                                 str(manifest["filing"].get("items") or "").split(",")}
                or _utc(manifest["clocks"]["accepted_at"]) != accepted):
            return None

        matched = [doc for doc in manifest["documents"]
                   if doc["archive_url"] == expected_url
                   and doc["availability"] == "stored"]
        if len(matched) != 1:
            return None
        selected = matched[0]
        receipt = selected["retrieval"]
        original_at = _utc(receipt.get("retrieved_at"))
        if (original_at is None or not accepted <= original_at <= pinned_at
                or receipt["receipt_id"] != first_retained_receipt_id):
            return None
        verified_bytes = authority.read_archive_document(
            storage_key=selected["storage_key"], expected_receipt=receipt,
            maximum_bytes=HARD_MAX_ARCHIVE_DOCUMENT_BYTES,
        )
        if sha256(verified_bytes.content).hexdigest() != selected["content_sha256"]:
            return None
        # Existing Earnings Release owns fact extraction and exact span replay.
        # Our public adapter only projects native, byte-bound results; if
        # parsing is unavailable no numeric evidence is admitted.
        validated_figures: list[VerifiedEarningsFigure] = []
        try:
            from engine.earnings_release.binding import bind_release_document
            from engine.earnings_release.receipts import replay_receipt
            body = verified_bytes.content.decode("utf-8")
            bound = bind_release_document(
                cik=cik, accession=filing_key.split(":", 1)[1],
                body=body, form=manifest["filing"]["form"],
                filing_date=manifest["clocks"]["filed_on"],
                acceptance_datetime=manifest["clocks"]["accepted_at"],
                report_date=manifest["filing"]["report_date"],
                exhibit_url=expected_url,
            )
            if bound.revision.source_sha256 != selected["content_sha256"]:
                return None
            for f in bound.figures.figures:
                candidate: tuple[str, str, float] | None = None
                if (f.concept == "eps_diluted" and f.units == "per_share"
                        and f.currency == "USD" and f.scale_factor == 1.0
                        and f.basis in ("gaap", "non_gaap")):
                    candidate = ("eps_actual", "gaap" if f.basis == "gaap" else "adjusted", f.value)
                elif (f.concept == "revenue" and f.currency == "USD"
                      and f.basis == "gaap" and f.scale_factor is not None
                      and f.scale_factor > 0):
                    candidate = ("rev_actual", "reported", f.value * f.scale_factor)
                if candidate is None:
                    continue
                replay_receipt(f.receipt, source=body)
                field, basis, amount = candidate
                if _finite(amount) is None:
                    continue
                validated_figures.append(VerifiedEarningsFigure(
                    field=field, value=amount, basis=basis,
                    document_sha256=selected["content_sha256"],
                    span_sha256=f.receipt.span_sha256,
                ))
        except Exception:
            # A source may be a correctly retained but unreadable attachment.
            # It can establish document availability, not financial facts.
            validated_figures.clear()
        lineage = manifest["lineage"]
        parent = ""
        if (manifest["filing"]["form"] == "8-K/A"
                and lineage["relationship"] == "observed_accession"):
            accession = lineage["amends_accession"]
            if (isinstance(accession, str)
                    and accession.startswith(f"{cik:010d}-")
                    and accession != filing_key.split(":", 1)[1]):
                parent = f"{cik:010d}:{accession}"
        return VerifiedDocumentObservation(
            source_id="sec:" + filing_key,
            document_url=expected_url,
            document_sha256=selected["content_sha256"],
            receipt_id=first_retained_receipt_id,
            owner_ref="fundamental_forensics.sec_source_snapshot",
            first_verified_at_utc=original_at,
            checked_at_utc=now,
            source_snapshot_version=authority.snapshot_id,
            filing_form=manifest["filing"]["form"] or "",
            amends_filing_key=parent,
            verified_figures=tuple(validated_figures),
            official_published_at_utc=None,
        )
    except Exception:
        # A degraded incumbent source reader cannot admit a public packet.
        return None


def _allowed(source_id: str, document_url: str, resolver: RightsResolver,
             now: datetime, *, document_sha256: str = "") -> PublicSourceGrant | None:
    try:
        grant = resolver(source_id, now)
    except Exception:  # a missing/degraded rights owner is denial, not authority
        return None
    if not isinstance(grant, PublicSourceGrant):
        return None
    if (grant.source_id != source_id or grant.document_url != document_url
            or not isinstance(grant.document_url, str) or not grant.document_url
            or (document_sha256 and grant.document_sha256 != document_sha256)
            or grant.audience != PUBLIC_AUDIENCE
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
    document_observation: VerifiedDocumentObservation | None = None,
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
    if document_observation is not None:
        # Separate semantic wire identity; do not silently redefine v1's
        # mandatory published_at field as document-first-verified availability.
        out["schema"] = STAGE_A_PACKET_SCHEMA
        out["schema_version"] = STAGE_A_PACKET_REVISION
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
    # Legacy producer processing time is NOT official first availability.
    processing = _utc(source_event.get("when") if earnings else source_event.get("first_observed_at_utc"),
                      producer_utc_naive=earnings and source_event.get("when_semantics") == "processing_wall_clock")
    if event_time is None or event_time > now + timedelta(minutes=2):
        out["missing_data"].append("unqualified_source_clocks")
        return out
    # The Stage-A source's official SEC acceptance cannot be in the future,
    # even when a legacy processing-clock path tolerates modest clock skew.
    if document_observation is not None and event_time > now:
        out["missing_data"].append("future_sec_acceptance")
        return out
    if processing is not None and (processing > now + timedelta(minutes=2)
                                   or processing < event_time - timedelta(minutes=2)):
        processing = None
    observation = None
    if document_observation is not None:
        receipt = document_observation
        source_url = _safe_url(source_event.get("source_url"), sec_only=earnings)
        first = _utc(receipt.first_verified_at_utc) if isinstance(receipt, VerifiedDocumentObservation) else None
        checked = _utc(receipt.checked_at_utc) if isinstance(receipt, VerifiedDocumentObservation) else None
        if (not isinstance(receipt, VerifiedDocumentObservation)
                or receipt.status != "verified" or receipt.source_id != primary_source_id
                or source_url is None or receipt.document_url != source_url
                or not isinstance(receipt.document_sha256, str)
                or not _SHA256_HEX.fullmatch(receipt.document_sha256)
                or not isinstance(receipt.receipt_id, str)
                or not 0 < len(receipt.receipt_id.strip()) <= 128
                or not isinstance(receipt.owner_ref, str) or not receipt.owner_ref.strip()
                or not isinstance(receipt.source_snapshot_version, str)
                or not _SNAPSHOT_VERSION.fullmatch(receipt.source_snapshot_version)
                or first is None or checked is None
                or first < event_time
                or first > checked or checked > now
                or now - checked > timedelta(minutes=10)):
            out["missing_data"].append("unqualified_verified_document_observation")
            return out
        official = _utc(receipt.official_published_at_utc)
        if receipt.official_published_at_utc is not None:
            if (official is None or official < event_time
                    or official > first or not isinstance(receipt.official_publication_ref, str)
                    or not receipt.official_publication_ref.strip()):
                out["missing_data"].append("unqualified_official_publication_provenance")
                return out
        observation = receipt
        observed = first
        out["observation_receipt_id"] = receipt.receipt_id
        out["source_snapshot_version"] = receipt.source_snapshot_version
        out["document_sha256"] = receipt.document_sha256
        out["document_checked_at_utc"] = _stamp(checked)
        out["processing_time_utc"] = _stamp(processing)
        if official is not None:
            out["publication_time_utc"] = _stamp(official)
    else:
        # Frozen legacy v1 path stays fail-closed on missing publication time.
        # A real edgar_earnings_wire.build_event does not supply one; only a
        # distinct owner-backed document-read receipt can unlock Stage A.
        observed = processing
        if (observed is None or observed > now + timedelta(minutes=2)
                or observed < event_time - timedelta(minutes=2)):
            out["missing_data"].append("unqualified_source_clocks")
            return out
        pub_time = _utc(source_event.get("publication_time_utc"))
        if pub_time is not None and event_time <= pub_time <= now:
            out["publication_time_utc"] = _stamp(pub_time)
        else:
            out["missing_data"].append("publication_time_not_attested")
    out.update(primary_subject={"ticker": ticker, "issuer_id": issuer_id,
                                "company_name": str(issuer.get("name") or ticker)[:120]},
               event_time_utc=_stamp(event_time), first_observed_at_utc=_stamp(observed))

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
    if observation is not None and earnings:
        amendment = (observation.filing_form == "8-K/A"
                     or source_event.get("form") == "8-K/A")
        if amendment or revision_state == "corrected":
            root = observation.amends_filing_key
            if (observation.filing_form != "8-K/A"
                    or source_event.get("form") not in (None, "", "8-K/A")
                    or not isinstance(root, str) or not _ACCESSION.fullmatch(root)
                    or root == filing_key or not root.startswith(f"{cik:010d}:")
                    or generation != 1 or revision_state != "corrected"
                    or source_event.get("correction_reason") != "official_amendment"):
                out["missing_data"].append("amendment_lineage_not_attested")
                return out
            event_id = "sec-earnings-" + _fingerprint(root)
            out["event_id"] = event_id
            out["amends_filing_key"] = root
        elif observation.amends_filing_key:
            out["missing_data"].append("unexpected_amendment_parent")
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
    # Stage A is a seven-day acceptance-time window, never a rolling window
    # based on a late recheck, regenerated scan, or producer process clock.
    effective_age = min(max_age, timedelta(days=7)) if observation else max_age
    if now - event_time > effective_age:
        out["missing_data"].append("event_outside_freshness_window")
        return out

    if earnings:
        primary = {"source_id": primary_source_id, "url": source_event.get("source_url"),
                   "title": "SEC Form 8-K Item 2.02",
                   "published_at_utc": out["publication_time_utc"],
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
        verified_ids = ({i for i in ids if isinstance(i, str) and _SOURCE_ID.fullmatch(i)}
                        if isinstance(ids, (list, tuple)) else set())
        # A duplicate source ID with different documentary evidence is an
        # ambiguous identity even when URL/title/publication are identical.
        # The second row must never upgrade the first source's evidence.
        if sid in attested_evidence and attested_evidence[sid] != verified_ids:
            blocked.add(sid)
            accepted.pop(sid, None)
            continue
        attested_evidence.setdefault(sid, verified_ids)
        url = _safe_url(entry.get("url"), sec_only=earnings and sid == primary_source_id)
        primary_digest = observation.document_sha256 if observation and sid == primary_source_id else ""
        grant = (_allowed(sid, url, rights_resolver, now,
                          document_sha256=primary_digest) if url is not None else None)
        if url is None or grant is None:
            blocked.add(sid)
            accepted.pop(sid, None)
            continue
        if sid in accepted:
            # One source ID cannot alias differing title/URL/publication data.
            if (accepted[sid]["url"] != url
                    or accepted[sid]["title"] != entry.get("title")
                    or accepted[sid]["published_at_utc"] != _stamp(_utc(entry.get("published_at_utc")))
                    or accepted[sid]["first_observed_at_utc"] != _stamp(_utc(entry.get("first_observed_at_utc")))):
                blocked.add(sid)
                accepted.pop(sid)
            continue
        title = entry.get("title")
        if not isinstance(title, str) or not 0 < len(title.strip()) <= 150:
            blocked.add(sid)
            continue
        published = _utc(entry.get("published_at_utc"))
        first_seen = _utc(entry.get("first_observed_at_utc"))
        if published is not None and published > now:
            blocked.add(sid)
            continue
        if published is None and not (observation and sid == primary_source_id):
            blocked.add(sid)
            continue
        if first_seen is not None and first_seen > now:
            first_seen = None
        accepted[sid] = {"source_id": sid, "title": title.strip(), "url": url,
                         "display_rights": "ALLOWED",
                         "published_at_utc": _stamp(published),
                         "first_observed_at_utc": _stamp(first_seen),
                         "rights_receipt_id": grant.receipt_id}
        if observation and sid == primary_source_id:
            accepted[sid]["first_verified_at_utc"] = _stamp(observed)
            accepted[sid]["document_sha256"] = observation.document_sha256
            accepted[sid]["observation_receipt_id"] = observation.receipt_id
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
    expiry = min([now + timedelta(minutes=5), event_time + effective_age,
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
            matched_figure = None
            if observation is not None:
                qualified = observation.verified_figures
                # The pure source adapter never self-mints numeric observations.
                # Stage-A facts require a unique native, doc-hash-bound Earnings
                # Release span: knowing that a document exists is insufficient.
                matches = ([figure for figure in qualified
                            if type(figure) is VerifiedEarningsFigure
                            and figure.field == field and figure.basis == basis
                            and figure.document_sha256 == observation.document_sha256
                            and isinstance(figure.span_sha256, str)
                            and _SHA256_HEX.fullmatch(figure.span_sha256)]
                           if isinstance(qualified, tuple) and len(qualified) <= 24
                           else [])
                if (len(matches) != 1 or _finite(matches[0].value) is None
                        or not math.isclose(value, matches[0].value,
                                            rel_tol=1e-13, abs_tol=1e-8)):
                    out["missing_data"].append("no_replayed_source_figure_" + field)
                    continue
                matched_figure = matches[0]
            evid = _fingerprint(f"{event_id}:{generation}:{field}" +
                                (f":{matched_figure.span_sha256}" if matched_figure else ""))
            copy = (f"{ticker} reported {basis.upper()} EPS of {_number(value)} USD/share."
                    if field == "eps_actual" else
                    f"{ticker} reported revenue of {_number(value)} USD.")
            evidence = {"evidence_id": evid, "source_id": primary_source_id,
                        "kind": field, "value": value, "unit": unit, "basis": basis}
            if matched_figure:
                evidence["replayed_span_sha256"] = matched_figure.span_sha256
            out["evidence"].append(evidence)
            out["what_changed"].append({"text": copy, "evidence_ids": [evid]})
        out["missing_data"].append("consensus_not_independently_evidenced")
    else:
        # Model/source headlines are not independent evidence of numbers,
        # causal impact, or relationships; preserve only the verified title.
        out["what_changed"].append({"text": accepted[primary_source_id]["title"],
                                    "evidence_ids": [], "source_ids": [primary_source_id]})
        out["missing_data"].append("numerical_claims_not_qualified")

    known_evidence_ids = {row["evidence_id"] for row in out["evidence"]}
    source_evidence_owner: dict[str, str] = {}
    ambiguous_source_evidence: set[str] = set()
    for source_id, ids in attested_evidence.items():
        for evidence_id in ids:
            incumbent = source_evidence_owner.setdefault(evidence_id, source_id)
            if incumbent != source_id:
                ambiguous_source_evidence.add(evidence_id)
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
        anchor = relation.get("source_anchor")
        if (not isinstance(relkind, str) or relkind not in _RELATION_COPY
                or not isinstance(anchor, str)
                or not 0 < len(anchor.strip()) <= 256
                or eid in known_evidence_ids or eid in ambiguous_source_evidence
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
        known_evidence_ids.add(eid)
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
        if (not isinstance(case, str) or case not in _SCENARIO_CASES
                or case in cases or not isinstance(trigger, str)
                or trigger not in _TRIGGER_COPY or not isinstance(invalidator, str)
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
        # An unavailable packet must not accidentally carry qualified-source
        # links, receipt IDs or relations to an unsanitized downstream consumer.
        out["source_refs"] = []
        out["sources"] = []
        out["rights_receipt_ids"] = []
        out["evidence"] = []
        out["affected_tickers"] = []
        out["cache_expires_at_utc"] = None
        return out
    out["public_safe"] = True
    out["public_disposition"] = "PUBLIC_READY"
    out["partial_reason"] = ",".join(out["missing_data"]) or None
    return out
