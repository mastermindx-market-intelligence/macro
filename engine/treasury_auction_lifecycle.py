"""Receipt-time Treasury auction context, subordinate to Macro's event/data owner.

No network, scheduler, forecasts, risk contribution, or trading effects. Current
TreasuryDirect JSON and inspected tentative/pending XML adapters only. Stored
observations are immutable inputs; snapshots never rewrite them.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

JSON_SCHEMA = "treasury_direct_json_current_v1"
TENTATIVE_SCHEMA = "treasury_quarterly_tentative_xml_v1"
PENDING_SCHEMA = "treasury_pending_auctions_xml_v4"
RECEIPT_VERSION = 1
ET_ZONE = ZoneInfo("America/New_York")
MAX_PAYLOAD_BYTES = 2 * 1024 * 1024
MAX_RECEIPT_BYTES = 8 * 1024 * 1024  # raw_text plus decoded payload and escaping
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILES = 128
MAX_ROWS = 2048
MAX_ENVELOPES = 128
SOURCE_SCHEMAS = {
    "treasurydirect_json": JSON_SCHEMA,
    "quarterly_tentative_xml": TENTATIVE_SCHEMA,
    "pending_auctions_xml": PENDING_SCHEMA,
}
_PRECEDENCE = {JSON_SCHEMA: 3, PENDING_SCHEMA: 2, TENTATIVE_SCHEMA: 1}
_CLASSES = {"bill": "Bill", "cmb": "CMB", "note": "Note", "bond": "Bond", "tips": "TIPS", "frn": "FRN"}
_MONEY = {
    "offering_amount_usd": "offeringAmount",
    "competitive_accepted_usd": "competitiveAccepted",
    "competitive_tendered_usd": "competitiveTendered",
    "total_accepted_usd": "totalAccepted",
    "primary_dealer_accepted_usd": "primaryDealerAccepted",
    "direct_bidder_accepted_usd": "directBidderAccepted",
    "indirect_bidder_accepted_usd": "indirectBidderAccepted",
}
_RESULT_NUMBERS = ("competitiveAccepted", "competitiveTendered", "bidToCoverRatio", "highYield", "highDiscountRate", "highDiscountMargin")


class UnsupportedSchema(ValueError):
    """Shape or version has no explicitly inspected adapter."""


def _aware(value: datetime | str, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{name} must be an offset-aware datetime") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be an offset-aware datetime")
    return value.astimezone(timezone.utc)


def _text(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return None if text.lower() in ("", "null", "none", "nan") else text


def _number(value, *, money: bool = False) -> str | None:
    text = _text(value)
    if text is None:
        return None
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid_numeric_field") from exc
    if not number.is_finite():
        return None
    if money and number < 0:
        raise ValueError("negative_monetary_field")
    return format(number, "f")


def _day(value, field: str, required: bool = False) -> str | None:
    text = _text(value)
    if text is None:
        if required:
            raise ValueError(f"missing_{field}")
        return None
    # API date fields are date-only or precisely ISO date + midnight (not clocks).
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T00:00:00)?", text):
        raise ValueError(f"invalid_{field}")
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError as exc:
        raise ValueError(f"invalid_{field}") from exc


def _flag(value) -> bool | None:
    text = _text(value)
    if text is None:
        return None
    if text.lower() in ("yes", "y"):
        return True
    if text.lower() in ("no", "n"):
        return False
    raise ValueError("invalid_class_flag")


def _class(row: dict) -> str:
    raw_base = _text(row.get("securityType"))
    base = _CLASSES.get(raw_base.lower()) if raw_base else None
    raw_type = _text(row.get("type"))
    explicit = _CLASSES.get(raw_type.lower()) if raw_type else None
    if base not in ("Bill", "Note", "Bond") or (raw_type and not explicit):
        raise ValueError("unsupported_instrument_class")
    flags = {"CMB": _flag(row.get("cashManagementBillCMB")), "TIPS": _flag(row.get("tips")), "FRN": _flag(row.get("floatingRate"))}
    true = [k for k, v in flags.items() if v is True]
    if len(true) > 1:
        raise ValueError("instrument_type_flag_conflict")
    inferred = true[0] if true else base
    kind = explicit or inferred
    allowed_base = {"CMB": ("Bill",), "TIPS": ("Note", "Bond"), "FRN": ("Note",)}
    if kind in allowed_base and base not in allowed_base[kind]:
        raise ValueError("instrument_type_flag_conflict")
    if kind in flags and flags[kind] is False:
        raise ValueError("instrument_type_flag_conflict")
    if true and kind != inferred:
        raise ValueError("instrument_type_flag_conflict")
    if kind in ("Bill", "Note", "Bond") and kind != base:
        raise ValueError("instrument_type_flag_conflict")
    return kind


def _deadline(day: str, raw) -> tuple[str | None, str | None]:
    text = _text(raw)
    if text is None:
        return None, "missing_competitive_deadline"
    parsed = None
    for fmt in ("%I:%M %p", "%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(text, fmt).time()
            break
        except ValueError:
            pass
    if parsed is None:
        return None, "invalid_competitive_deadline"
    stamp = datetime.combine(date.fromisoformat(day), parsed, ET_ZONE)
    return stamp.astimezone(timezone.utc).isoformat(), None


def _decode(raw_text: str, schema: str):
    if schema == JSON_SCHEMA:
        payload = json.loads(raw_text)
        if isinstance(payload, list):
            return payload, payload, {}
        if isinstance(payload, dict) and set(payload) == {"schema_id", "rows"} and payload["schema_id"] == JSON_SCHEMA and isinstance(payload["rows"], list):
            return payload, payload["rows"], {}
        raise UnsupportedSchema("unsupported_json_shape_or_migrated_schema")
    if schema not in (TENTATIVE_SCHEMA, PENDING_SCHEMA):
        raise UnsupportedSchema("unsupported_schema_id")
    if "<!DOCTYPE" in raw_text.upper() or "<!ENTITY" in raw_text.upper():
        raise ValueError("xml_dtd_or_entity_forbidden")
    root = ET.fromstring(raw_text)
    if schema == TENTATIVE_SCHEMA:
        if root.tag != "AuctionCalendar":
            raise UnsupportedSchema("unsupported_tentative_xml_root")
        edition = _text(root.findtext("AuctionCalendarName"))
        start, end = _day(root.findtext("StartDate"), "schedule_start", True), _day(root.findtext("EndDate"), "schedule_end", True)
        if not edition or start > end:
            raise UnsupportedSchema("unsupported_tentative_xml_header")
        if any(child.tag not in {"AuctionCalendarName", "StartDate", "EndDate", "AuctionCalendarDate"} for child in root):
            raise UnsupportedSchema("unsupported_tentative_xml_shape")
        nodes = root.findall("AuctionCalendarDate")
        coverage = {"schedule_edition": edition, "schedule_start": start, "schedule_end": end}
    else:
        location = root.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}schemaLocation", "")
        if root.tag != "{http://www.treasurydirect.gov/}PendingAuctionData" or not location.endswith("/PendingAuctions_v4_0_0.xsd"):
            raise UnsupportedSchema("unsupported_pending_xml_version")
        nodes = list(root)
        if any(node.tag != "PendingOfficialAnnouncement" for node in nodes):
            raise UnsupportedSchema("unsupported_pending_xml_shape")
        coverage = {}
    rows = []
    for node in nodes:
        row = {child.tag: child.text for child in node}
        rows.append(row)
    return raw_text, rows, coverage


def make_observation(raw_text: bytes | str, *, source_kind: str, source_url: str,
                     observed_at: datetime | str, schema_id: str | None = None,
                     metadata: dict | None = None) -> dict:
    """Create a JSON-serializable receipt; hash exact UTF-8 bytes, without fetching.

    observed_at is caller-supplied successful receipt/verified local availability,
    never publication or HTTP metadata. Unknown schemas can be retained for a
    later adapter: build_context marks them unsupported rather than empty.
    """
    observed = _aware(observed_at, "observed_at")
    raw_bytes = raw_text if isinstance(raw_text, bytes) else raw_text.encode("utf-8")
    if len(raw_bytes) > MAX_PAYLOAD_BYTES:
        raise ValueError("payload_size_limit")
    text = raw_bytes.decode("utf-8")  # exact reversible encoding, no newline rewriting
    schema = schema_id or SOURCE_SCHEMAS.get(source_kind, "unsupported")
    try:
        payload, _, _ = _decode(text, schema)
    except (ValueError, ET.ParseError, RecursionError):
        payload = None  # retain malformed/unknown bytes; quarantine at consumption
    return {"receipt_version": RECEIPT_VERSION, "status": "available", "source_kind": source_kind,
            "source_url": source_url, "schema_id": schema, "observed_at": observed.isoformat(),
            "payload_sha256": hashlib.sha256(raw_bytes).hexdigest(), "raw_text": text,
            "payload": payload, "metadata": copy.deepcopy(metadata or {})}


def _adapt_xml(row: dict, schema: str) -> dict | None:
    if schema == TENTATIVE_SCHEMA and "HolidayName" in row and "HolidayDate" in row and not _text(row.get("AuctionDate")):
        _day(row["HolidayDate"], "holiday_date", True)
        return None
    mapping = {"SecurityType": "securityType", "SecurityTermWeekYear": "securityTerm",
               "TIPS": "tips", "InflationIndexSecurity": "tips", "FloatingRate": "floatingRate",
               "AnnouncementDate": "announcementDate", "AuctionDate": "auctionDate",
               "SettlementDate": "issueDate", "IssueDate": "issueDate", "ReOpeningIndicator": "reopening",
               "CUSIP": "cusip"}
    return {mapping[key]: value for key, value in row.items() if key in mapping}


def _normalize(row, receipt: dict, index: int, coverage: dict, as_of: datetime) -> dict | None:
    if not isinstance(row, dict):
        raise ValueError("row_not_object")
    schema = receipt["schema_id"]
    raw_row = copy.deepcopy(row)
    if schema != JSON_SCHEMA:
        row = _adapt_xml(row, schema)
        if row is None:
            return None
    elif (not {"securityType", "auctionDate", "cusip"}.issubset(row) or
          any(key.casefold() in {"competitiveauctionclosedate", "competitiveauctionclosetime", "noncompetitiveauctionclosedate", "announcedascusip", "subtotalcompetitiveparawardedinsideofofferingamount"} for key in row)):
        # A migrated JSON row is explicitly quarantined, never an empty schedule.
        raise UnsupportedSchema("unsupported_json_row_schema")
    kind = _class(row)
    auction = _day(row.get("auctionDate"), "auction_date", True)
    issue = _day(row.get("issueDate"), "issue_date", True)
    announcement = _day(row.get("announcementDate"), "announcement_date")
    if issue < auction:
        raise ValueError("issue_before_auction")
    term = _text(row.get("securityTerm"))
    if not term:
        raise ValueError("missing_security_term")
    cusip = _text(row.get("cusip"))
    announced = _text(row.get("announcedCusip"))
    original = _text(row.get("originalCusip"))
    if announced and original and announced != original:
        raise ValueError("announced_original_alias_conflict")
    # originalCusip is an announced alias only with a documented special notice.
    alias_supported = bool(original and _text(row.get("pdfFilenameSpecialAnnouncement")) and _flag(row.get("reopening")) is True)
    identity_cusip = announced or (original if alias_supported else cusip)
    if schema == JSON_SCHEMA and not identity_cusip:
        raise ValueError("missing_cusip_identity")
    for candidate in (cusip, announced, original):
        if candidate and not re.fullmatch(r"[A-Z0-9]{9}", candidate):
            raise ValueError("invalid_cusip")
    deadline, deadline_reason = _deadline(auction, row.get("closingTimeCompetitive"))
    result_evidence = []
    for field in ("pdfFilenameCompetitiveResults", "xmlFilenameCompetitiveResults"):
        if _text(row.get(field)):
            result_evidence.append(field)
    for field in _RESULT_NUMBERS:
        if _number(row.get(field)) is not None:
            result_evidence.append(field)
    observed = _aware(receipt["observed_at"], "observed_at")
    if result_evidence and (auction > observed.astimezone(ET_ZONE).date().isoformat() or
                            (deadline and observed < _aware(deadline, "deadline"))):
        raise ValueError("future_result_bearing_contradiction")
    source_state = "RESULT_OBSERVED" if result_evidence else ("ANNOUNCED" if schema == JSON_SCHEMA else "TENTATIVE")
    if source_state == "RESULT_OBSERVED":
        physical = "RESULT_OBSERVED"
    elif deadline and as_of >= _aware(deadline, "deadline"):
        physical = "AWAITING_RESULT"
    elif auction < as_of.astimezone(ET_ZONE).date().isoformat():
        physical = "AWAITING_RESULT"  # date elapsed; deadline was never fabricated
    else:
        physical = source_state
    issue_passed = issue < as_of.astimezone(ET_ZONE).date().isoformat()
    amounts = {name: _number(row.get(field), money=True) for name, field in _MONEY.items()}
    result = None
    if result_evidence:
        result = {k: v for k, v in amounts.items() if k != "offering_amount_usd"}
        result.update({"bid_to_cover_ratio": _number(row.get("bidToCoverRatio")),
                       "high_discount_rate_pct": _number(row.get("highDiscountRate")),
                       "high_discount_margin_pct": _number(row.get("highDiscountMargin")),
                       "frn_spread_pct": _number(row.get("spread")),
                       "real_yield_pct": _number(row.get("highYield")) if kind == "TIPS" else None,
                       "nominal_yield_pct": _number(row.get("highYield")) if kind in ("Note", "Bond") else None,
                       "bidder_shares": None})
    edition = coverage.get("schedule_edition", "pending_v4")
    original_term = _text(row.get("originalSecurityTerm"))
    # Coupons in the quarterly schedule use official original cohorts. An
    # unscheduled alias into another security is not assumed to keep that cohort.
    use_original_term = (schema == JSON_SCHEMA and kind in ("Note", "Bond", "TIPS", "FRN")
                         and _flag(row.get("reopening")) is True and original_term
                         and (not announced or announced == cusip) and not alias_supported)
    match_term = original_term if use_original_term else term
    match = [kind, re.sub(r"\s+", " ", match_term).casefold(), auction, issue]
    slot = "tentative:" + hashlib.sha256(json.dumps([edition, match, index], separators=(",", ":")).encode()).hexdigest()[:24]
    identity = f"auction:{identity_cusip}:{auction}" if identity_cusip else slot
    reasons = [deadline_reason] if deadline_reason else []
    if any(_text(row.get(k)) is None for k in ("tips", "floatingRate", "cashManagementBillCMB")):
        reasons.append("one_or_more_class_flags_missing")
    return {"episode_id": identity, "tentative_slot_id": slot if source_state == "TENTATIVE" else None,
            "normalized_class": kind, "raw_security_type": row.get("securityType"), "raw_type": row.get("type"),
            "raw_class_flags": {k: row.get(k) for k in ("tips", "floatingRate", "cashManagementBillCMB")},
            "announced_cusip": identity_cusip, "issued_cusip": cusip, "original_cusip_raw": original,
            "original_cusip_alias_documented": alias_supported, "auction_date": auction, "issue_date": issue,
            "announcement_date": announcement, "original_issue_date": _day(row.get("originalIssueDate"), "original_issue_date"),
            "security_term": term, "original_security_term": original_term,
            "schedule_match_term": match_term, "schedule_match_basis": "official_original_security_term" if use_original_term else "security_term",
            "reopening": _flag(row.get("reopening")), "competitive_deadline_utc": deadline,
            "competitive_deadline_raw": row.get("closingTimeCompetitive"), "deadline_timezone": "America/New_York",
            "source_state": source_state, "physical_state": physical,
            "issue_calendar_state": "ISSUE_DATE_PASSED" if issue_passed else "ISSUE_DATE_NOT_PASSED",
            "settled_payment_observed": None, "offering_amount_usd": amounts["offering_amount_usd"],
            "result": result, "result_evidence_fields": result_evidence,
            "known_at": observed.isoformat(), "known_at_basis": "conservative_observed_at",
            "source_update_raw": row.get("updatedTimestamp"), "record_date_raw": row.get("record_date"),
            "publication_time": None, "source_url": receipt["source_url"], "source_kind": receipt["source_kind"],
            "schema_id": schema, "payload_sha256": receipt["payload_sha256"], "row_index": index,
            "row_sha256": hashlib.sha256(json.dumps(raw_row, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "schedule_edition": coverage.get("schedule_edition"), "null_reasons": reasons,
            "is_context_only": True, "importance": "NOT_SCORED", "forecast_authority": "RESEARCH_ONLY",
            "probabilities": None, "_match": match}


def _semantic(version: dict) -> dict:
    ignored = {"source_url", "source_kind", "schema_id", "payload_sha256", "row_index", "row_sha256", "known_at", "source_update_raw", "schedule_edition", "null_reasons", "schedule_match_basis"}
    return {k: v for k, v in version.items() if k not in ignored and not k.startswith("_")}


def build_context(envelopes: Iterable[dict], as_of: datetime | str, horizon_days: int = 30) -> dict:
    """Pure snapshot of eligible receipts; no observation later than as_of leaks.

    ET date windows are inclusive [today, today + horizon_days]. Recently resulted
    auctions are inclusive [today - horizon_days, today], plus any result with a
    future issue date. Counts describe observed coverage, never every future CMB.
    """
    at = _aware(as_of, "as_of")
    if isinstance(horizon_days, bool) or not isinstance(horizon_days, int) or not 1 <= horizon_days <= 366:
        raise ValueError("horizon_days must be an integer between 1 and 366")
    today = at.astimezone(ET_ZONE).date()
    end, recent_start = today + timedelta(days=horizon_days), today - timedelta(days=horizon_days)
    states, quarantine, conflicts, receipts, versions = [], [], [], [], []
    excluded, byte_count, truncated, holidays = 0, 0, False, 0
    def rejected(reason, **details):
        quarantine.append({"reason": reason, **details})
    for ordinal, original in enumerate(envelopes):
        if ordinal >= MAX_ENVELOPES:
            truncated = True
            break
        if not isinstance(original, dict):
            rejected("envelope_not_object", envelope_index=ordinal)
            continue
        try:
            observed = _aware(original.get("observed_at"), "observed_at")
        except (ValueError, TypeError):
            rejected("invalid_observed_at", envelope_index=ordinal)
            continue
        # Exclude completely before parsing, hashing, or exposing source facts.
        if observed > at:
            excluded += 1
            continue
        info = {"source_kind": original.get("source_kind"), "source_url": original.get("source_url"),
                "schema_id": original.get("schema_id"), "observed_at": observed.isoformat(),
                "payload_sha256": original.get("payload_sha256"), "receipt_status": original.get("status"),
                "body_received_at": None}
        try:
            receipt = copy.deepcopy(original)
            if receipt.get("receipt_version") != RECEIPT_VERSION:
                raise ValueError("invalid_receipt_version")
            if not _text(receipt.get("source_url")):
                raise ValueError("missing_source_url")
            metadata = receipt.get("metadata", {})
            if not isinstance(metadata, dict):
                raise ValueError("invalid_receipt_metadata")
            # System knowledge may be a conservative parse/verification bound.
            # It is never an invented HTTP-body arrival timestamp. Older
            # receipts without that separately measured clock stay unknown.
            body = metadata.get("body_received_at")
            body_at = _aware(body, "body_received_at") if body is not None else None
            if body_at is not None and body_at > observed:
                raise ValueError("body_received_after_observation")
            info["body_received_at"] = body_at.isoformat() if body_at else None
            if receipt.get("status") == "unavailable":
                states.append({**info, "status": "unavailable", "reason": str(receipt.get("error", "source_unavailable"))})
                continue
            if receipt.get("status") != "available":
                raise ValueError("invalid_receipt_status")
            raw = receipt.get("raw_text")
            if not isinstance(raw, str):
                raise ValueError("missing_raw_text")
            size = len(raw.encode("utf-8"))
            byte_count += size
            if size > MAX_PAYLOAD_BYTES or byte_count > MAX_TOTAL_BYTES:
                truncated = True
                raise ValueError("payload_size_limit")
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            if digest != receipt.get("payload_sha256"):
                raise ValueError("payload_digest_mismatch")
            schema = receipt.get("schema_id")
            if SOURCE_SCHEMAS.get(receipt.get("source_kind")) != schema:
                raise UnsupportedSchema("unsupported_source_kind_schema_pair")
            payload, rows, source_coverage = _decode(raw, schema)
            if receipt.get("payload") != payload:
                raise ValueError("decoded_payload_mismatch")
            info["coverage"] = source_coverage
            info["rows_observed"] = len(rows)
            receipts.append({**info, "receipt_version": RECEIPT_VERSION, "bytes": size,
                             "metadata": copy.deepcopy(receipt.get("metadata", {})),
                             "payload_retained_in_immutable_receipt": True})
            row_bad, row_good, unsupported = 0, 0, 0
            if len(rows) > MAX_ROWS:
                truncated = True
            for index, row in enumerate(rows[:MAX_ROWS]):
                try:
                    version = _normalize(row, receipt, index, source_coverage, at)
                    if version is None:
                        holidays += 1
                    else:
                        versions.append(version)
                        row_good += 1
                except (ValueError, TypeError, AttributeError) as exc:
                    row_bad += 1
                    unsupported += isinstance(exc, UnsupportedSchema)
                    rejected(str(exc), source_url=info["source_url"], payload_sha256=digest, row_index=index)
            status = "empty" if not rows else ("unsupported" if unsupported and not row_good else ("degraded" if row_bad or len(rows) > MAX_ROWS else "available"))
            states.append({**info, "status": status, "valid_rows": row_good, "quarantined_rows": row_bad,
                           "rows_truncated": max(0, len(rows) - MAX_ROWS)})
        except UnsupportedSchema as exc:
            states.append({**info, "status": "unsupported", "reason": str(exc)})
        except (ValueError, TypeError, ET.ParseError, RecursionError, UnicodeError) as exc:
            rejected(str(exc), envelope_index=ordinal)
            states.append({**info, "status": "degraded", "reason": str(exc)})
    # Bind slots only to one exact class/term/auction/issue tuple, and only if a
    # unique slot exists in each schedule edition. Multiple vintages remain.
    announcements = defaultdict(set)
    slot_ids = defaultdict(set)
    for version in versions:
        if version["source_state"] != "TENTATIVE":
            announcements[tuple(version["_match"])].add(version["episode_id"])
        else:
            slot_ids[(version["schedule_edition"], tuple(version["_match"]))].add(version["episode_id"])
    for version in versions:
        if version["source_state"] != "TENTATIVE":
            continue
        matches = announcements[tuple(version["_match"])]
        if len(matches) == 1 and len(slot_ids[(version["schedule_edition"], tuple(version["_match"]))]) == 1:
            version["episode_id"] = next(iter(matches))
            version["tentative_merge_state"] = "EXACT_UNIQUE_MATCH"
        elif matches:
            version["tentative_merge_state"] = "AMBIGUOUS"
            conflicts.append({"reason": "ambiguous_tentative_join", "tentative_slot_id": version["tentative_slot_id"], "candidate_episode_ids": sorted(matches)})
        else:
            version["tentative_merge_state"] = "UNRESOLVED"
    grouped = defaultdict(list)
    for version in versions:
        grouped[version["episode_id"]].append(version)
    episodes = []
    for identity, history in sorted(grouped.items()):
        # Observed result is durable against stale schedule/announcement snapshots.
        result_history = [v for v in history if v["source_state"] == "RESULT_OBSERVED"]
        candidates = result_history or history
        # Prioritize source authority over receipt recency only for tentative vs
        # announced. Within equivalent evidence, the newest receipt is selected.
        best_schema = max(_PRECEDENCE[v["schema_id"]] for v in candidates)
        candidates = [v for v in candidates if _PRECEDENCE[v["schema_id"]] == best_schema]
        latest = max(v["known_at"] for v in candidates)
        tied = [v for v in candidates if v["known_at"] == latest]
        fact_sets = {json.dumps(_semantic(v), sort_keys=True) for v in tied}
        # Equal receipt clocks do not resolve contradictory shared facts simply
        # because one row also contains results. Missing result fields in a
        # sibling announcement alone are not a contradiction.
        same_clock = [v for v in history if v["known_at"] == latest and _PRECEDENCE[v["schema_id"]] == best_schema]
        shared_fields = ("normalized_class", "auction_date", "issue_date", "announcement_date",
                         "competitive_deadline_utc", "security_term", "offering_amount_usd")
        contradicted = [field for field in shared_fields
                        if len({json.dumps(v[field], sort_keys=True) for v in same_clock if v[field] is not None}) > 1]
        if len(fact_sets) > 1 or contradicted:
            conflicts.append({"reason": "same_time_conflicting_facts", "episode_id": identity,
                              "known_at": latest, "conflicting_fields": contradicted,
                              "row_sha256s": sorted(v["row_sha256"] for v in same_clock)})
            continue  # no arbitrary winner, including digest-order winner
        selected = copy.deepcopy(sorted(tied, key=lambda v: (v["source_url"], v["payload_sha256"], v["row_index"]))[0])
        semantic_vintage = _semantic(selected)
        selected["first_observed_at"] = min(v["known_at"] for v in history if _semantic(v) == semantic_vintage)
        selected["first_observed_at_basis"] = "first matching semantic vintage among eligible retained receipts; not public release"
        selected["observation_versions"] = [{k: copy.deepcopy(value) for k, value in v.items() if not k.startswith("_")} for v in sorted(history, key=lambda v: (v["known_at"], v["schema_id"], v["payload_sha256"], v["row_index"]))]
        selected["tentative_slot_ids"] = sorted({v["tentative_slot_id"] for v in history if v["tentative_slot_id"]})
        selected.pop("_match", None)
        d = date.fromisoformat(selected["auction_date"])
        awaiting_recent_result = selected["physical_state"] == "AWAITING_RESULT" and recent_start <= d <= today
        if today <= d <= end or awaiting_recent_result or (selected["source_state"] == "RESULT_OBSERVED" and (recent_start <= d <= today or selected["issue_date"] >= today.isoformat())):
            episodes.append(selected)
    episodes.sort(key=lambda v: (v["auction_date"], v["competitive_deadline_utc"] or "", v["episode_id"]))
    events = []
    for episode in episodes:
        deadline = episode["competitive_deadline_utc"]
        local_time = _aware(deadline, "deadline").astimezone(ET_ZONE).strftime("%H:%M") if deadline else None
        events.append({**episode, "type": "AUCTION", "date": episode["auction_date"], "time_et": local_time,
                       "label": f"{episode['security_term']} {episode['normalized_class']} auction",
                       "source": episode["source_url"], "impact": None, "assets": ["bonds"]})
    known = [e for e in episodes if e["source_state"] == "ANNOUNCED" and today.isoformat() <= e["auction_date"] <= end.isoformat() and (not e["competitive_deadline_utc"] or _aware(e["competitive_deadline_utc"], "deadline") > at)]
    recent = [e for e in episodes if e["source_state"] == "RESULT_OBSERVED"]
    tentative = [e for e in episodes if e["source_state"] == "TENTATIVE"]
    usable = any(s["status"] == "empty" or s.get("valid_rows", 0) > 0 or (s["status"] == "available" and s.get("rows_observed", 0) > 0) for s in states)
    degraded = bool(quarantine or conflicts or truncated or any(s["status"] in ("unavailable", "unsupported", "degraded") for s in states))
    status = "degraded" if usable and degraded else ("available" if usable else ("unsupported" if states and all(s["status"] == "unsupported" for s in states) else "unavailable"))
    health_groups = defaultdict(list)
    for state in states:
        health_groups[(state["source_kind"], state["source_url"])].append(state)
    source_health = []
    for (source_kind, source_url), observations in sorted(health_groups.items(), key=lambda item: str(item[0])):
        latest_at = max(s["observed_at"] for s in observations)
        latest_states = sorted({s["status"] for s in observations if s["observed_at"] == latest_at})
        received = [s for s in observations if s["receipt_status"] == "available"]
        valid = [s for s in observations if s["status"] in ("available", "empty") or s.get("valid_rows", 0) > 0]
        failed = [s for s in observations if s["status"] == "unavailable"]
        body_at = max((s["body_received_at"] for s in received if s.get("body_received_at")), default=None)
        valid_at = max((s["observed_at"] for s in valid), default=None)
        failure_at = max((s["observed_at"] for s in failed), default=None)
        source_health.append({"source_kind": source_kind, "source_url": source_url,
            "latest_attempt_at": latest_at,
            "latest_attempt_status": latest_states[0] if len(latest_states) == 1 else "conflicting_source_states",
            "latest_attempt_states": latest_states,
            "last_successful_body_receipt_at": body_at,
            "last_valid_observation_at": valid_at,
            "last_valid_observation_age_seconds": (at - _aware(valid_at, "observed_at")).total_seconds() if valid_at else None,
            "latest_failure_at": failure_at,
            "latest_failure_reasons": sorted({s.get("reason", "source_unavailable") for s in failed if s["observed_at"] == failure_at}),
            "freshness_basis": "receipt_time; build_time_never_refreshes_source",
            "stale_after_seconds": None})
    source_observed_at = max((s["last_valid_observation_at"] for s in source_health if s["last_valid_observation_at"]), default=None)
    counts_known = usable and not truncated
    return {"schema_version": "sovereign_auction_context_v1", "as_of": at.isoformat(), "decision_cutoff_utc": at.isoformat(),
            "source_observed_at": source_observed_at, "asof": source_observed_at[:10] if source_observed_at else None, "status": status,
            "is_context_only": True, "forecast_authority": "RESEARCH_ONLY", "probabilities": None,
            "importance": "NOT_SCORED", "events": events, "episodes": episodes,
            "source_states": states, "source_health": source_health, "observation_receipts": receipts, "quarantine": quarantine,
            "conflicts": conflicts, "coverage": {"timezone": "America/New_York", "horizon_days": horizon_days,
                "upcoming_start_date": today.isoformat(), "upcoming_end_date_inclusive": end.isoformat(),
                "recent_start_date_inclusive": recent_start.isoformat(), "known_upcoming_count": len(known) if counts_known else None,
                "recently_resulted_or_issue_future_count": len(recent) if counts_known else None,
                "unresolved_tentative_count": len(tentative) if counts_known else None,
                "awaiting_result_count": sum(e["physical_state"] == "AWAITING_RESULT" for e in episodes) if counts_known else None,
                "excluded_after_as_of_count": excluded, "exclusion_reason": "observed_at_after_as_of" if excluded else None,
                "holiday_nodes_skipped": holidays, "truncated": truncated,
                "universe": "observed official snapshots; future unannounced CMB coverage unknown",
                "counts_are_observed_not_complete_universe": True,
                "limits": {"max_envelopes": MAX_ENVELOPES, "max_rows_per_payload": MAX_ROWS,
                           "max_payload_bytes": MAX_PAYLOAD_BYTES, "max_total_bytes": MAX_TOTAL_BYTES}}}


def snapshot(data_dir: Path | None = None, as_of: datetime | str | None = None,
             horizon_days: int = 30) -> dict:
    """Read bounded immutable receipt files under existing data owner; no writes.

    data_dir is Macro's data root. Default is <repo>/data, resolved from this
    module rather than cwd; no dependency on network-aware Macro modules.
    """
    at = _aware(as_of, "as_of") if as_of is not None else datetime.now(timezone.utc)
    root = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parents[1] / "data"
    directory = root / "treasury_auctions" / "observations"
    envelopes, errors = [], []
    total, truncated = 0, False
    try:
        # Current snapshots read the most recently written local receipts first.
        # File mtime chooses bounded candidates only, NEVER knowledge eligibility.
        # Copying old files can change candidate selection but cannot backdate
        # their verified observed_at. Large historical replays must use explicitly
        # selected eligible envelopes through build_context and disclose bounds.
        def newest_file_key(path):
            try:
                return path.stat().st_mtime_ns, path.name
            except OSError:
                return -1, path.name  # still quarantined if in the bounded set
        paths = sorted(directory.glob("*.json"), key=newest_file_key, reverse=True) if directory.is_dir() else []
        if len(paths) > MAX_FILES:
            truncated = True
        for path in paths[:MAX_FILES]:
            try:
                if path.is_symlink():
                    raise ValueError("symlink_receipt_rejected")
                size = path.stat().st_size
                total += size
                if size > MAX_RECEIPT_BYTES or total > MAX_TOTAL_BYTES:
                    truncated = True
                    raise ValueError("receipt_file_size_limit")
                with path.open("rb") as stream:
                    raw = stream.read(MAX_RECEIPT_BYTES + 1)
                if len(raw) > MAX_RECEIPT_BYTES:
                    truncated = True
                    raise ValueError("receipt_file_size_limit")
                envelopes.append(json.loads(raw))
            except (OSError, ValueError, UnicodeError, RecursionError) as exc:
                errors.append({"file": path.name, "reason": str(exc)})
    except OSError as exc:
        errors.append({"reason": str(exc)})
    out = build_context(envelopes, at, horizon_days)
    out["quarantine"].extend(errors)
    out["coverage"].update({"receipt_files_read": len(envelopes), "receipt_files_quarantined": len(errors),
                               "receipt_directory_available": directory.is_dir()})
    if truncated:
        out["coverage"]["truncated"] = True
        for name in ("known_upcoming_count", "recently_resulted_or_issue_future_count", "unresolved_tentative_count", "awaiting_result_count"):
            out["coverage"][name] = None
    if errors or truncated:
        out["status"] = "degraded" if out["status"] == "available" else out["status"]
    return out
