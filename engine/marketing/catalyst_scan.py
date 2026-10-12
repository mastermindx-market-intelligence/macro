"""Read-only Catalyst scan: legacy v1 and explicit Stage-A v2 source receipts.

Data is sourced ONLY from a canonical owner-provided context. This module has
no network, file reader, background poller, public-rights mint, or second store.
The default source hook declines until a trusted adapter is wired in production.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Mapping, Sequence

from engine.company_intelligence.contracts import ContractError, safe_ticker
from engine.marketing.catalyst_packets import (
    SCHEMA_VERSION as PACKET_SCHEMA, STAGE_A_PACKET_SCHEMA,
    _SOURCE_ID, _TRIGGER_COPY, _INVALIDATOR_COPY, _RELATION_COPY,
    _URL_EMAIL, _safe_url, _utc, _stamp,
)

SCAN_SCHEMA = "catalyst.scan/v1"
STAGE_A_SCAN_SCHEMA = "catalyst.scan/v2"
MAX_TICKERS = 10
_COVERAGE_SCHEMA = "catalyst.source_coverage/v1"
_PILOT_WINDOW = timedelta(days=7)
_CURRENT_RECEIPT = timedelta(minutes=10)


@dataclass(frozen=True, slots=True)
class SourceCoverageReceipt:
    """Owner-issued complete-current read, not a scan-generated success.

    This is a read receipt from the EXISTING retained SEC source: no network,
    source collection, registry, rights grant or snapshot store is created here.
    A bare empty list and the old twenty-event limit prove no such completeness.
    """
    source: str
    receipt_id: str
    owner_ref: str
    snapshot_version: str
    issuer_tickers: frozenset[str]
    window_start_utc: datetime
    window_end_utc: datetime
    checked_at_utc: datetime
    outcome: str
    pagination_exhausted: bool
    truncated: bool
    returned_events: int
    event_limit: int
    schema: str = _COVERAGE_SCHEMA


_PUBLIC_TICKER = re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$")
_DOC_DIGEST = re.compile(r"^[0-9a-f]{64}$")


def normalize_tickers(values: Sequence[str]) -> list[str]:
    """Normalize 1–10 distinct tickers, without silently swallowing invalid input."""
    if isinstance(values, (str, bytes)) or not isinstance(values, (list, tuple)):
        raise ValueError("tickers must be a list of 1–10 symbols")
    if not 1 <= len(values) <= MAX_TICKERS:
        raise ValueError("expected 1–10 symbols")
    result = []
    for raw in values:
        if not isinstance(raw, str):
            raise ValueError("ticker must be a string")
        try:
            ticker = safe_ticker(raw)
        except ContractError as exc:
            raise ValueError("invalid ticker symbol") from exc
        # Match Session 00's public routing contract rather than the
        # larger internal multinational ticker grammar.
        if not _PUBLIC_TICKER.fullmatch(ticker):
            raise ValueError("ticker not supported by public scan")
        if ticker in result:
            raise ValueError("duplicate ticker symbol")
        result.append(ticker)
    return result


def _dossier_path(ticker: str, universe: Mapping) -> str | None:
    entry = universe.get(ticker)
    if not isinstance(entry, Mapping):
        return None
    path = entry.get("dossier_path")
    return path if path == f"/stocks/{ticker}/" else None


def _revision_identity(packet: Mapping) -> tuple[str, int] | None:
    if (packet.get("schema"), packet.get("schema_version")) not in (
            (PACKET_SCHEMA, 1), (STAGE_A_PACKET_SCHEMA, 2)):
        return None
    eid = packet.get("event_id")
    generation = packet.get("generation")
    if (not isinstance(eid, str) or not _SOURCE_ID.fullmatch(eid)
            or type(generation) is not int
            or generation < 0):
        return None
    return eid, generation


def _current_packets(packets: Sequence[Mapping]) -> tuple[dict[str, Mapping], set[str]]:
    """Latest immutable correction wins; divergent same-generation copies quarantine."""
    latest: dict[str, Mapping] = {}
    conflicts: set[str] = set()
    for packet in packets:
        if not isinstance(packet, Mapping):
            continue
        identity = _revision_identity(packet)
        if identity is None:
            continue
        eid, generation = identity
        previous = latest.get(eid)
        if previous is None or generation > previous["generation"]:
            latest[eid] = packet
            conflicts.discard(eid)
        elif generation == previous["generation"]:
            try:
                equal = json.dumps(previous, sort_keys=True, allow_nan=False) == json.dumps(
                    packet, sort_keys=True, allow_nan=False)
            except (TypeError, ValueError):
                equal = False
            if not equal:
                conflicts.add(eid)
    return latest, conflicts


def _relation(packet: Mapping, ticker: str) -> Mapping | None:
    rows = packet.get("affected_tickers")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, Mapping) and row.get("ticker") == ticker:
                return row
    return None


def _base(ticker: str, universe: Mapping, now: datetime) -> dict:
    return {"ticker": ticker, "status": "NOT_COVERED", "relationship": "UNKNOWN",
            "as_of_utc": _stamp(now), "dossier_path": _dossier_path(ticker, universe),
            "headline": None, "headline_evidence_ids": [], "relationship_evidence_ids": [],
            "what_changed": [], "scenarios": [], "invalidators": [], "sources": [],
            "correction_state": None, "public_safe": False, "coverage_note": ""}


def _safe_ids(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, (list, tuple)) or len(raw) > 12:
        return ()
    if any(not isinstance(value, str) or not _SOURCE_ID.fullmatch(value)
           for value in raw):
        return ()
    return tuple(raw)


def _public_result(ticker: str, packet: Mapping, relation: Mapping,
                   base: dict, now: datetime) -> dict:
    """Allowlist every byte and evidence link before Session 00 sanitizes again."""
    if (packet.get("public_safe") is not True or
            packet.get("public_disposition") != "PUBLIC_READY" or
            packet.get("correction_state") not in ("CURRENT", "CORRECTED")):
        base["status"] = "RIGHTS_BLOCKED" if packet.get("public_disposition") == "BLOCKED_PUBLIC" else "TEMPORARILY_UNAVAILABLE"
        return base
    expiry = _utc(packet.get("cache_expires_at_utc"))
    pkt_asof = _utc(packet.get("as_of_utc"))
    if (expiry is None or now >= expiry or pkt_asof is None or
            now - pkt_asof > timedelta(days=7) or pkt_asof > now + timedelta(minutes=5)):
        base["status"] = "TEMPORARILY_UNAVAILABLE"
        return base
    kind = relation.get("relationship")
    if kind not in ("DIRECT", "EVIDENCED_INDIRECT"):
        base["status"] = "NOT_COVERED"
        return base
    sources_raw = packet.get("sources")
    if not isinstance(sources_raw, list) or not 1 <= len(sources_raw) <= 12:
        base["status"] = "RIGHTS_BLOCKED"
        return base
    # Defensive scan-level validation: a partner/card consumer may call
    # compose_scan without passing through Session00's stricter HTTP bridge.
    # No source URL, PII-bearing query, unbound title or ambiguous ID escapes.
    sources = []
    srcids: set[str] = set()
    for i, raw_source in enumerate(sources_raw):
        if not isinstance(raw_source, Mapping):
            base["status"] = "RIGHTS_BLOCKED"
            return base
        sid, title = raw_source.get("source_id"), raw_source.get("title")
        url, receipt = raw_source.get("url"), raw_source.get("rights_receipt_id")
        publication = raw_source.get("published_at_utc")
        verified = raw_source.get("first_verified_at_utc")
        published_time = _utc(publication)
        verified_time = _utc(verified)
        if (not isinstance(sid, str) or not _SOURCE_ID.fullmatch(sid)
                or sid in srcids
                or not isinstance(title, str) or not 0 < len(title.strip()) <= 150
                or any(ord(c) < 32 or ord(c) == 127 for c in title)
                or not isinstance(receipt, str) or not 0 < len(receipt.strip()) <= 128
                or raw_source.get("display_rights") != "ALLOWED"
                or not isinstance(url, str)
                or _safe_url(url, sec_only=(packet.get("event_kind") == "earnings"
                                           and i == 0)) != url
                or (publication is not None and published_time is None)
                or (verified is not None and verified_time is None)
                or (published_time is None and verified_time is None)
                or (packet.get("schema") == PACKET_SCHEMA
                    and published_time is None)
                or (published_time is not None and published_time > now)
                or (verified_time is not None and verified_time > now)):
            base["status"] = "RIGHTS_BLOCKED"
            return base
        srcids.add(sid)
        sources.append({"source_id": sid, "url": url, "title": title.strip(),
                        "published_at_utc": _stamp(published_time),
                        "first_verified_at_utc": _stamp(verified_time),
                        "display_rights": "ALLOWED",
                        "rights_receipt_id": receipt})
    raw_evidence = packet.get("evidence")
    if not isinstance(raw_evidence, list) or len(raw_evidence) > 256:
        base["status"] = "TEMPORARILY_UNAVAILABLE"
        return base
    evidence_lookup: dict[str, str] = {}
    for row in raw_evidence:
        eid, sid = (row.get("evidence_id"), row.get("source_id")) if isinstance(row, Mapping) else (None, None)
        if (not isinstance(eid, str) or not _SOURCE_ID.fullmatch(eid)
                or sid not in srcids or eid in evidence_lookup):
            base["status"] = "TEMPORARILY_UNAVAILABLE"
            return base
        evidence_lookup[eid] = sid
    primary = packet.get("primary_subject")
    if not isinstance(primary, Mapping) or not primary.get("ticker"):
        base["status"] = "TEMPORARILY_UNAVAILABLE"
        return base
    claims = packet.get("what_changed")
    scenario_rows = packet.get("scenarios")
    if (not isinstance(claims, list) or len(claims) > 10
            or not isinstance(scenario_rows, list) or len(scenario_rows) > 10):
        base["status"] = "TEMPORARILY_UNAVAILABLE"
        return base
    primary_id = sources[0]["source_id"]
    relationship_sources = {evidence_lookup.get(e)
                            for e in _safe_ids(relation.get("relation_evidence_ids"))}
    relationship_sources.discard(None)
    if kind == "EVIDENCED_INDIRECT" and not relationship_sources:
        base["status"] = "NOT_COVERED"
        return base
    changed = []
    for claim in claims:
        if not isinstance(claim, Mapping) or not isinstance(claim.get("text"), str):
            continue
        copy = claim["text"]
        if (not 0 < len(copy.strip()) <= 300 or _URL_EMAIL.search(copy)
                or any(ord(ch) < 32 or ord(ch) == 127 for ch in copy)):
            continue
        refs = {evidence_lookup.get(k)
                for k in _safe_ids(claim.get("evidence_ids"))}
        refs.update(s for s in _safe_ids(claim.get("source_ids")) if s in srcids)
        refs.discard(None)
        if refs:
            changed.append({"text": claim["text"], "evidence_ids": sorted(refs)})
    if kind == "EVIDENCED_INDIRECT":
        link = relation.get("summary")
        relkind = relation.get("relation_type")
        if (not isinstance(relkind, str) or relkind not in _RELATION_COPY
                or link != _RELATION_COPY[relkind]):
            base["status"] = "NOT_COVERED"
            return base
        changed.insert(0, {"text": f"{link}; any financial effect on {ticker} is unverified.",
                           "evidence_ids": sorted(relationship_sources)})
    if not changed:
        base["status"] = "TEMPORARILY_UNAVAILABLE"
        return base
    scenarios = []
    invalidators = []
    for row in scenario_rows:
        if not isinstance(row, Mapping):
            continue
        refs = {evidence_lookup.get(k)
                for k in _safe_ids(row.get("evidence_ids"))}
        refs.discard(None)
        if (refs and row.get("case") in ("bull", "base", "bear")
                and row.get("trigger") in _TRIGGER_COPY.values()
                and row.get("invalidator") in _INVALIDATOR_COPY.values()):
            scenarios.append({"case": row["case"].upper(), "trigger": row["trigger"],
                              "evidence_ids": sorted(refs)})
            if isinstance(row.get("invalidator"), str):
                invalidators.append({"text": row["invalidator"], "evidence_ids": sorted(refs)})
    if kind == "DIRECT":
        label = "earnings result" if packet.get("event_kind") == "earnings" else "documented event"
        title = f"{ticker} filed a {label}: sourced facts and outstanding questions"
        headline_sources = [primary_id]
    else:
        event_label = "earnings filing" if packet.get("event_kind") == "earnings" else "event"
        title = (f"{primary['ticker']} {event_label} and a documented {relation['relation_type']}"
                 f" relationship with {ticker}; effect unverified")
        headline_sources = sorted({primary_id, *relationship_sources})
    result = dict(base, status="SUPPORTED", relationship=kind, public_safe=True,
                  headline=title, headline_evidence_ids=headline_sources,
                  relationship_evidence_ids=sorted(relationship_sources),
                  what_changed=changed[:10], scenarios=scenarios[:10],
                  invalidators=invalidators[:10], sources=sources[:12],
                  correction_state=packet["correction_state"])
    return result


def _complete_current_coverage(receipt: SourceCoverageReceipt | None,
                               *, names: Sequence[str], packets: Sequence[Mapping],
                               issuers: Mapping[str, Mapping], now: datetime) -> bool:
    if not isinstance(receipt, SourceCoverageReceipt):
        return False
    if (receipt.schema != _COVERAGE_SCHEMA or receipt.source != "edgar_8k_202"
            or not isinstance(receipt.receipt_id, str) or not receipt.receipt_id.strip()
            or not isinstance(receipt.owner_ref, str) or not receipt.owner_ref.strip()
            or not isinstance(receipt.snapshot_version, str)
            or not receipt.snapshot_version.strip()
            or not isinstance(receipt.issuer_tickers, frozenset)
            or any(not isinstance(t, str) or not _PUBLIC_TICKER.fullmatch(t)
                   for t in receipt.issuer_tickers)
            or receipt.outcome != "COMPLETE"
            or type(receipt.pagination_exhausted) is not bool
            or receipt.pagination_exhausted is not True
            or type(receipt.truncated) is not bool or receipt.truncated is not False
            or type(receipt.returned_events) is not int or receipt.returned_events < 0
            or type(receipt.event_limit) is not int or receipt.event_limit < 1
            or receipt.returned_events > receipt.event_limit
            or receipt.returned_events != len(packets)):
        return False
    if (not isinstance(issuers, Mapping) or not receipt.issuer_tickers
            or len(receipt.issuer_tickers) > 10_000):
        return False
    if any(not isinstance(issuers.get(ticker), Mapping)
           or issuers[ticker].get("supported") is not True
           for ticker in receipt.issuer_tickers):
        return False
    supported = {name for name in names if
                 isinstance(issuers.get(name), Mapping) and
                 issuers[name].get("supported") is True}
    if not supported.issubset(receipt.issuer_tickers):
        return False
    start, end, checked = (_utc(receipt.window_start_utc),
                           _utc(receipt.window_end_utc), _utc(receipt.checked_at_utc))
    if (start is None or end is None or checked is None
            or start > end or start > now - _PILOT_WINDOW
            or end > checked
            or checked > now
            or now - checked > _CURRENT_RECEIPT
            or now - end > _CURRENT_RECEIPT):
        return False
    # A selective export, stale backfill or truncated window cannot certify
    # a negative claim about current issuer coverage.
    for packet in packets:
        if (not isinstance(packet, Mapping) or packet.get("event_kind") != "earnings"
                or packet.get("schema") != STAGE_A_PACKET_SCHEMA
                or packet.get("schema_version") != 2):
            return False
        primary = packet.get("primary_subject")
        if (not isinstance(primary, Mapping)
                or not isinstance(primary.get("ticker"), str)
                or primary.get("ticker") not in receipt.issuer_tickers
                or packet.get("source_snapshot_version") != receipt.snapshot_version):
            return False
        affected = packet.get("affected_tickers")
        if not isinstance(affected, list):
            return False
        # The first event-first pilot is restricted to direct earnings issuers.
        # Indirect AI-capex/semiconductor relationships require a later owner
        # expansion and cannot be laundered through this coverage receipt.
        if any(not isinstance(row, Mapping)
               or row.get("relationship") != "DIRECT"
               or row.get("ticker") != primary.get("ticker") for row in affected):
            return False
        accepted = _utc(packet.get("event_time_utc"))
        first = _utc(packet.get("first_observed_at_utc"))
        doc_checked = _utc(packet.get("document_checked_at_utc"))
        digest = packet.get("document_sha256")
        receipt_id = packet.get("observation_receipt_id")
        if (accepted is None or not start <= accepted <= end
                or first is None or first < accepted
                or first > now
                or doc_checked is None or first > doc_checked
                or doc_checked > checked
                or now - doc_checked > _CURRENT_RECEIPT
                or not isinstance(digest, str) or not _DOC_DIGEST.fullmatch(digest)
                or not isinstance(receipt_id, str) or not receipt_id.strip()):
            return False
    return True


def compose_scan(tickers: Sequence[str], *, packets: Sequence[Mapping],
                 issuers: Mapping[str, Mapping], as_of: datetime,
                 event_id: str | None = None,
                 coverage: SourceCoverageReceipt | None = None) -> dict:
    """Pure testable producer -> public scan; inputs MUST be trusted server-owned data."""
    now = _utc(as_of)
    if now is None:
        raise ValueError("as_of must be timezone-aware")
    names = normalize_tickers(tickers)
    if event_id is not None and (not isinstance(event_id, str)
                                 or not _SOURCE_ID.fullmatch(event_id)):
        raise ValueError("invalid event reference")
    # Do not launder a v2 first-availability event through the v1 read-model
    # path. v2 requires the incumbent's complete-current snapshot, even when
    # called directly by cards/partners rather than scan_tickers/HTTP.
    if coverage is None and any(isinstance(packet, Mapping)
                                and packet.get("schema") == STAGE_A_PACKET_SCHEMA
                                for packet in packets):
        return compose_scan(names, packets=(), issuers=issuers, as_of=now,
                            event_id=event_id)
    if coverage is not None and not _complete_current_coverage(
            coverage, names=names, packets=packets, issuers=issuers, now=now):
        return compose_scan(names, packets=(), issuers=issuers, as_of=now,
                            event_id=event_id)
    complete = coverage is not None
    latest, conflicts = _current_packets(packets)
    if event_id is not None:
        selected = latest.get(event_id)
    else:
        matched = [p for p in latest.values() if any(
            _relation(p, n) is not None or n in p.get("rights_blocked_tickers", [])
            or (isinstance(p.get("primary_subject"), Mapping) and p["primary_subject"].get("ticker") == n)
            for n in names)]
        selected = max(matched, key=lambda p: (p.get("event_time_utc") or "", p["generation"]), default=None)
    results = []
    for ticker in names:
        base = _base(ticker, issuers, now)
        info = issuers.get(ticker)
        if not isinstance(info, Mapping) or info.get("supported") is not True:
            results.append(base)
            continue
        if selected is None:
            # Never upgrade a bare [] or an unrecognized event reference to
            # a factual checked-empty result. Only a complete-current owner
            # receipt proves no qualifying earnings event in this window.
            base["status"] = ("NO_QUALIFIED_EVENT" if complete and
                              event_id is None and ticker in coverage.issuer_tickers
                              else "TEMPORARILY_UNAVAILABLE")
        elif selected["event_id"] in conflicts:
            base["status"] = "TEMPORARILY_UNAVAILABLE"
        elif (relation := _relation(selected, ticker)) is not None:
            base = _public_result(ticker, selected, relation, base, now)
        elif ticker in selected.get("rights_blocked_tickers", []):
            base["status"] = "RIGHTS_BLOCKED"
        elif isinstance(selected.get("primary_subject"), Mapping) and selected["primary_subject"].get("ticker") == ticker:
            base["status"] = "RIGHTS_BLOCKED" if selected.get("public_disposition") == "BLOCKED_PUBLIC" else "TEMPORARILY_UNAVAILABLE"
        else:
            base["status"] = "NOT_COVERED"
        results.append(base)
    supported = any(r["status"] == "SUPPORTED" for r in results)
    publication = "PARTIAL" if selected is not None else "UNAVAILABLE"
    if (selected is None and complete and event_id is None
            and any(r["status"] == "NO_QUALIFIED_EVENT" for r in results)):
        publication = "COMPLETE_EMPTY"
    if selected and supported and all(r["status"] == "SUPPORTED" for r in results):
        publication = "PUBLIC_QUALIFIED"
    response = {"schema": STAGE_A_SCAN_SCHEMA if complete else SCAN_SCHEMA,
                "schema_version": 2 if complete else 1,
                "as_of_utc": _stamp(now),
                "requested_tickers": names, "event_id": selected["event_id"] if selected else None,
                "generation": selected["generation"] if selected else None,
                "publication_state": publication,
                "coverage_note": "Only independently qualified public earnings evidence is eligible.",
                "results": results}
    if complete:
        response["checked_window"] = {
            "kind": "earnings_8k",
            "start_utc": _stamp(_utc(coverage.window_start_utc)),
            "end_utc": _stamp(_utc(coverage.window_end_utc)),
            "checked_at_utc": _stamp(_utc(coverage.checked_at_utc)),
        }
    return response


def read_qualified_event_context(
    now_utc: datetime,
) -> tuple[Sequence[Mapping], Mapping[str, Mapping], SourceCoverageReceipt | None]:
    """Source-owner seam. No compatible qualified SEC read is connected yet.

    Session 00 must bind an existing admitted source/issuer/rights adapter here,
    not a browser-supplied filename, a second ledger, or private qbus site-full.
    The only optional runtime bridge is the INCUMBENT Session00 SEC
    admission owner. The source module does not configure it or grant rights.
    A missing/legacy/erroring owner is denied by scan_tickers before display.
    Test doubles may patch this seam with a separately qualified triple.
    """
    try:
        from engine.marketing.catalyst_admission import (
            read_qualified_event_context as incumbent_reader,
        )
    except ImportError:
        return (), {}, None
    try:
        return incumbent_reader(now_utc)
    except Exception:
        return (), {}, None


def scan_tickers(tickers: list[str], *, event_id: str | None = None,
                 now_utc: datetime | None = None) -> dict:
    """Frozen Session 00 entrypoint: anonymous, no storage or entitlement bypass."""
    now = now_utc if now_utc is not None else datetime.now(timezone.utc)
    normalized = normalize_tickers(tickers)
    context = read_qualified_event_context(now)
    # A legacy source reader can still return its old (packets, issuers) pair,
    # but WITHOUT a signed/source-backed complete-current read outcome it is
    # not enough to establish latest corrections or no-event semantics.
    if not isinstance(context, (tuple, list)) or len(context) != 3:
        return compose_scan(normalized, packets=(), issuers={}, as_of=now,
                            event_id=event_id)
    packets, issuers, coverage = context
    if (not isinstance(packets, (tuple, list)) or not isinstance(issuers, Mapping)
            or not _complete_current_coverage(
                coverage, names=normalized, packets=packets, issuers=issuers, now=_utc(now))):
        return compose_scan(normalized, packets=(), issuers={}, as_of=now,
                            event_id=event_id)
    return compose_scan(normalized, packets=packets, issuers=issuers, as_of=now,
                        event_id=event_id, coverage=coverage)
