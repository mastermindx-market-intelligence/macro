"""Private, bounded read projection of the incumbent IntelligenceStore.

This module is stdlib-only. It owns neither a database nor ingestion. The writer
projects admitted display packets into a private atomic file; the authenticated
API checks that file against the revision advertised by the current live desk.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
import unicodedata
from urllib.parse import urlsplit


PACKET_SCHEMA = "intelligence.story_packet/v1"
SCHEMA = "intelligence.retained_history/v1"
PAGE_SCHEMA = "intelligence.history_page/v1"
FILENAME = "intelligence-history.json"
DEFAULT_PATH = Path("/var/lib/macro-live/state/intelligence") / FILENAME
MAX_BYTES = 8 * 1024 * 1024
MAX_STORIES = 1500
MAX_RETENTION_HOURS = 72.0
MAX_EXPORT_AGE_SECONDS = 300.0
MAX_PAGE_SIZE = 100
MAX_CURSOR_LENGTH = 1024
QUERY_LIMITS = {"q": 256, "source": 160, "feed_id": 160, "category": 64,
                "language": 32, "from_at": 80, "to_at": 80}
_HEX = re.compile(r"[a-f0-9]{64}")
_ALLOWED_USE = {"attributed_headline_link", "attributed_feed_excerpt"}
_TEXT_FIELDS = (
    "schema", "id", "purpose", "stage", "status", "headline", "headline_zh",
    "brief", "brief_zh", "why_it_matters_en", "why_it_matters_zh",
    "lane", "lane_label_en", "lane_label_zh", "event_class", "category",
    "published_at", "source_updated_at", "provider_indexed_at", "first_seen",
    "accepted_revision_at", "source_name", "source_type",
    "feed_id", "source_item_id", "source_revision", "language", "publisher_country",
    "timestamp_quality", "attribution", "content_use",
)
_URL_FIELDS = ("url", "canonical_url", "source_use_url")
_EVIDENCE_FIELDS = ("name", "url", "headline", "published_at", "source_item_id", "source_revision")
_TIMELINE_FIELDS = ("ts", "at", "kind", "label_en", "label_zh", "source_name")
_REVISION_FIELDS = ("revision", "headline", "accepted_at", "url")
_TOP_FIELDS = {"schema", "as_of", "bounds", "retained_count", "displayable_count",
               "excluded_count", "stories"}


class HistoryArtifactError(ValueError):
    """An absent, incompatible or unsafe owner projection."""


class HistoryQueryError(ValueError):
    """A bounded query could not be interpreted as the documented contract."""


class HistoryCursorError(ValueError):
    """A cursor is malformed or belongs to another query."""


class HistoryRevisionChanged(HistoryCursorError):
    """The retained set changed; mixing pages would hide corrections/removals."""


def _at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value or len(value) > 80:
        return None
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if at.tzinfo is None or at.utcoffset() is None:
            return None
        return at.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def _iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _integer(value: object, low: int, high: int) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and low <= value <= high


def _url(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 4096:
        return ""
    try:
        parsed = urlsplit(value)
        if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username and not parsed.password:
            return value
    except ValueError:
        pass
    return ""


def _nested_rows(value: object, fields: tuple[str, ...], limit: int) -> list[dict]:
    if not isinstance(value, list):
        return []
    result = []
    for row in value[:limit]:
        if not isinstance(row, dict):
            continue
        cleaned = {key: row[key] for key in fields if isinstance(row.get(key), str)}
        if "url" in cleaned:
            cleaned["url"] = _url(cleaned["url"])
        if cleaned:
            result.append(cleaned)
    return result


def display_packet(packet: dict) -> dict:
    """Allowlist recursively; marketing drafts and internal payloads never pass."""
    result = {key: packet[key] for key in _TEXT_FIELDS if isinstance(packet.get(key), str)}
    for key in _URL_FIELDS:
        if isinstance(packet.get(key), str):
            result[key] = _url(packet[key])
    for key in ("tickers", "coverage_regions"):
        if isinstance(packet.get(key), list):
            result[key] = [value for value in packet[key] if isinstance(value, str)][:32]
    if _integer(packet.get("source_count"), 0, 10000):
        # This is the incumbent owner's label/count, not a new independence test.
        result["source_count"] = packet["source_count"]
    if isinstance(packet.get("context"), dict):
        result["context"] = {key: packet["context"][key] for key in ("evidence", "pace")
                             if isinstance(packet["context"].get(key), str)}
    if isinstance(packet.get("evidence"), list):
        result["evidence"] = _nested_rows(packet["evidence"], _EVIDENCE_FIELDS, 64)
    if isinstance(packet.get("timeline"), list):
        result["timeline"] = _nested_rows(packet["timeline"], _TIMELINE_FIELDS, 12)
    if isinstance(packet.get("revision_history"), list):
        result["revision_history"] = _nested_rows(packet["revision_history"], _REVISION_FIELDS, 12)
    return result


def display_scope(health: object) -> dict[str, str]:
    """Current source grants; conflicting identities are never an entitlement."""
    if not isinstance(health, list):
        return {}
    rows, duplicate = {}, set()
    for row in health:
        if (not isinstance(row, dict) or not isinstance(row.get("id"), str)
                or not row["id"] or len(row["id"]) > QUERY_LIMITS["feed_id"]):
            continue
        if row["id"] in rows:
            duplicate.add(row["id"])
        rows[row["id"]] = row
    return {key: row["content_use"] for key, row in rows.items() if key not in duplicate
            and row.get("enabled") is True and row.get("status") != "held"
            and not row.get("hold_reason") and isinstance(row.get("content_use"), str)
            and row["content_use"] in _ALLOWED_USE}


def is_displayable(packet: object, scope: dict[str, str]) -> bool:
    if (not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA
            or not isinstance(packet.get("id"), str) or not packet["id"].strip()
            or len(packet["id"]) > 256 or not isinstance(packet.get("headline"), str)
            or not packet["headline"].strip()):
        return False
    purpose = packet.get("purpose")
    if purpose == "research":
        feed_id, content_use = packet.get("feed_id"), packet.get("content_use")
        if (not isinstance(feed_id, str) or not isinstance(content_use, str)
                or content_use not in _ALLOWED_USE or scope.get(feed_id) != content_use):
            return False
        if packet.get("stage") != "reported":
            return False
    elif purpose not in (None, "") or packet.get("stage") not in ("developing", "confirmed", "high_impact"):
        return False
    elif packet.get("content_use") and (not isinstance(packet["content_use"], str)
                                       or packet["content_use"] not in _ALLOWED_USE):
        return False
    # A retained marketing object does not become reporting simply because its
    # JSON resembles a packet. The incumbent public-safe packet has source links.
    evidence = packet.get("evidence")
    return bool(_url(packet.get("url")) or any(
        _url(row.get("url")) for row in (evidence if isinstance(evidence, list) else [])
        if isinstance(row, dict)
    ))


def _recorded_at(row: dict) -> datetime | None:
    for key in ("accepted_revision_at", "first_seen"):
        at = _at(row.get(key))
        if at is not None:
            return at
    return None


def _clock_eligible(row: dict, as_of: datetime) -> bool:
    # Do this at projection time, not page time. A future record becoming
    # eligible must change the dataset revision, never reorder an old cursor.
    recorded = _recorded_at(row)
    published = _at(row.get("published_at"))
    return (recorded is None or recorded <= as_of) and (published is None or published <= as_of)


def build_projection(packets: list[object], *, source_health: object,
                     as_of: datetime, retention_hours: float, max_stories: int) -> dict:
    if (not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None
            or isinstance(retention_hours, bool) or not isinstance(retention_hours, (int, float))
            or not math.isfinite(retention_hours) or not _integer(max_stories, 1, 2**31 - 1)):
        raise HistoryArtifactError("invalid projection bounds or clock")
    cap = max(1, min(MAX_STORIES, max_stories))
    retention = max(1.0, min(MAX_RETENTION_HOURS, retention_hours))
    if len(packets) > cap:
        raise HistoryArtifactError("retained history cap")
    as_of = as_of.astimezone(timezone.utc)
    scope = display_scope(source_health)
    rows, seen = [], set()
    for packet in packets:
        if not is_displayable(packet, scope) or not _clock_eligible(packet, as_of):
            continue
        clean = display_packet(packet)
        if clean.get("purpose") == "research" and clean.get("content_use") == "attributed_headline_link":
            # A previously retained payload cannot extend a headline/link grant.
            clean.pop("brief", None)
            clean.pop("brief_zh", None)
        if clean["id"] in seen:
            raise HistoryArtifactError("duplicate retained identity")
        seen.add(clean["id"])
        rows.append(clean)
    # Storage order never creates a revision or an unstable page boundary.
    rows.sort(key=lambda row: row["id"])
    return {
        "schema": SCHEMA, "as_of": _iso(as_of),
        "bounds": {"retention_hours": retention, "max_stories": cap,
                   "retention_basis": "owner_updated_at"},
        "retained_count": len(packets), "displayable_count": len(rows),
        "excluded_count": len(packets) - len(rows), "stories": rows,
    }


def _bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def revision(payload: dict) -> str:
    return hashlib.sha256(_bytes({key: value for key, value in payload.items() if key != "as_of"})).hexdigest()


def descriptor(payload: dict) -> dict:
    return {"state": "available", "schema": SCHEMA, "revision": revision(payload),
            **{key: payload[key] for key in ("bounds", "retained_count", "displayable_count", "excluded_count")}}


def unavailable(reason: str) -> dict:
    return {"state": "unavailable", "schema": SCHEMA, "reason": reason}


def _strict_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise HistoryArtifactError("duplicate JSON key")
        result[key] = value
    return result


def validate(payload: object) -> dict:
    if (not isinstance(payload, dict) or set(payload) != _TOP_FIELDS
            or payload.get("schema") != SCHEMA or _at(payload.get("as_of")) is None):
        raise HistoryArtifactError("history schema")
    bounds = payload["bounds"]
    if (not isinstance(bounds, dict) or set(bounds) != {"retention_hours", "max_stories", "retention_basis"}
            or bounds.get("retention_basis") != "owner_updated_at"
            or not _integer(bounds.get("max_stories"), 1, MAX_STORIES)):
        raise HistoryArtifactError("history bounds")
    hours = bounds.get("retention_hours")
    if (isinstance(hours, bool) or not isinstance(hours, (int, float))
            or not 1 <= hours <= MAX_RETENTION_HOURS or not math.isfinite(hours)):
        raise HistoryArtifactError("history retention")
    stories = payload["stories"]
    if not isinstance(stories, list) or len(stories) > bounds["max_stories"]:
        raise HistoryArtifactError("history collection")
    for field in ("retained_count", "displayable_count", "excluded_count"):
        if not _integer(payload[field], 0, bounds["max_stories"]):
            raise HistoryArtifactError("history count")
    if (payload["displayable_count"] != len(stories)
            or payload["displayable_count"] + payload["excluded_count"] != payload["retained_count"]):
        raise HistoryArtifactError("history count consistency")
    seen = set()
    as_of = _at(payload["as_of"])
    for row in stories:
        if (not isinstance(row, dict) or row.get("schema") != PACKET_SCHEMA
                or not isinstance(row.get("id"), str) or not row["id"].strip()
                or len(row["id"]) > 256 or row["id"] in seen
                or not isinstance(row.get("headline"), str) or not row["headline"].strip()
                or display_packet(row) != row or not _clock_eligible(row, as_of)):
            raise HistoryArtifactError("history display packet")
        feed_id, content_use = row.get("feed_id"), row.get("content_use")
        local_scope = {feed_id: content_use} if isinstance(feed_id, str) and isinstance(content_use, str) else {}
        if (not is_displayable(row, local_scope)
                or (row.get("purpose") == "research" and content_use == "attributed_headline_link"
                    and ("brief" in row or "brief_zh" in row))):
            raise HistoryArtifactError("history display scope")
        seen.add(row["id"])
    _bytes(payload)  # reject non-JSON numeric constants at every admitted depth
    return payload


def encode(payload: dict) -> bytes:
    validate(payload)
    raw = _bytes(payload) + b"\n"
    if len(raw) > MAX_BYTES:
        raise HistoryArtifactError("history byte cap")
    return raw


def decode(raw: bytes) -> dict:
    if len(raw) > MAX_BYTES:
        raise HistoryArtifactError("history byte cap")
    try:
        return validate(json.loads(raw, object_pairs_hook=_strict_object))
    except (ValueError, TypeError, UnicodeError, OverflowError, RecursionError) as exc:
        raise HistoryArtifactError("invalid history artifact") from exc


def atomic_write(path: Path, payload: dict) -> None:
    """Validate the whole body before any effect; private mode on every replace."""
    raw = encode(payload)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise HistoryArtifactError("unsafe history target")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def normalize_query(*, q: str = "", source: str = "", feed_id: str = "",
                    category: str = "", language: str = "", from_at: str | None = None,
                    to_at: str | None = None, limit: int = 50) -> dict:
    values = {"q": q, "source": source, "feed_id": feed_id, "category": category,
              "language": language, "from_at": from_at, "to_at": to_at}
    result = {}
    for key, value in values.items():
        if key in ("from_at", "to_at") and value is None:
            result[key] = None
            continue
        if not isinstance(value, str) or len(value) > QUERY_LIMITS[key]:
            raise HistoryQueryError("invalid history query")
        value = value.strip()
        if key in ("from_at", "to_at"):
            at = _at(value) if value else None
            if value and at is None:
                raise HistoryQueryError("timezone date required")
            result[key] = _iso(at) if at else None
        else:
            result[key] = value.lower() if key in ("category", "language") else value
    if not _integer(limit, 1, MAX_PAGE_SIZE):
        raise HistoryQueryError("invalid page size")
    result["limit"] = limit
    if result["from_at"] and result["to_at"] and _at(result["from_at"]) >= _at(result["to_at"]):
        raise HistoryQueryError("invalid history date interval")
    return result


def _fold(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _source_labels(row: dict) -> set[str]:
    labels = {_fold(row.get("source_name", ""))}
    for source in row.get("evidence", []):
        labels.add(_fold(source.get("name", "")))
        try:
            labels.add((urlsplit(source.get("url", "")).hostname or "").casefold())
        except ValueError:
            pass
    try:
        labels.add((urlsplit(row.get("url", "")).hostname or "").casefold())
    except ValueError:
        pass
    return labels - {""}


def _matches(row: dict, query: dict) -> bool:
    if query["feed_id"] and row.get("feed_id") != query["feed_id"]:
        return False
    if query["language"] and row.get("language", "").lower() != query["language"]:
        return False
    if query["category"] and query["category"] not in {
        row.get(key, "").lower() for key in ("category", "lane", "event_class")
    }:
        return False
    if query["source"] and _fold(query["source"]) not in _source_labels(row):
        return False
    recorded = _recorded_at(row)
    if query["from_at"] and (recorded is None or recorded < _at(query["from_at"])):
        return False
    if query["to_at"] and (recorded is None or recorded >= _at(query["to_at"])):
        return False
    if query["q"]:
        text = [row.get(key, "") for key in ("headline", "headline_zh", "brief", "brief_zh", "source_name")]
        text.extend(source.get(key, "") for source in row.get("evidence", []) for key in ("name", "headline"))
        needle = _fold(query["q"])
        if not any(needle in _fold(value) for value in text):
            return False
    return True


def _cursor(rev: str, query_hash: str, offset: int) -> str:
    raw = _bytes({"v": 1, "revision": rev, "query": query_hash, "offset": offset})
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _cursor_offset(token: str | None, *, rev: str, query_hash: str, count: int, limit: int) -> int:
    if token is None:
        return 0
    if (not isinstance(token, str) or not token or len(token) > MAX_CURSOR_LENGTH
            or not re.fullmatch(r"[A-Za-z0-9_-]+", token)):
        raise HistoryCursorError("invalid history cursor")
    try:
        raw = base64.b64decode(token + "=" * (-len(token) % 4), altchars=b"-_", validate=True)
        value = json.loads(raw, object_pairs_hook=_strict_object)
    except (ValueError, TypeError, UnicodeError, binascii.Error, RecursionError) as exc:
        raise HistoryCursorError("invalid history cursor") from exc
    if (not isinstance(value, dict) or set(value) != {"v", "revision", "query", "offset"}
            or not _integer(value.get("v"), 1, 1)
            or not isinstance(value.get("revision"), str) or not _HEX.fullmatch(value["revision"])
            or value.get("query") != query_hash
            or not _integer(value.get("offset"), 1, MAX_STORIES)
            or value["offset"] % limit
            or token != _cursor(value["revision"], query_hash, value["offset"])):
        raise HistoryCursorError("invalid history cursor")
    if value["revision"] != rev:
        raise HistoryRevisionChanged("history revision changed")
    if value["offset"] >= count:
        raise HistoryCursorError("history cursor outside query")
    return value["offset"]


def page(payload: dict, *, query: dict, cursor: str | None = None) -> dict:
    """An exact-revision cursor; no persisted sessions or historical replay log."""
    rev = revision(payload)
    floor = datetime.min.replace(tzinfo=timezone.utc)
    matches = [row for row in payload["stories"] if _matches(row, query)]
    # Stable secondary identity order, including when many source clocks tie.
    matches.sort(key=lambda row: row["id"])
    matches.sort(key=lambda row: _recorded_at(row) or floor, reverse=True)
    query_hash = hashlib.sha256(_bytes(query)).hexdigest()
    offset = _cursor_offset(cursor, rev=rev, query_hash=query_hash, count=len(matches), limit=query["limit"])
    rows = matches[offset:offset + query["limit"]]
    following = offset + len(rows)
    return {
        "schema": PAGE_SCHEMA, "revision": rev, "as_of": payload["as_of"],
        "collection": "retained_current_packets", "order": "recorded_acceptance_desc_then_id",
        **{key: payload[key] for key in ("bounds", "retained_count", "displayable_count", "excluded_count")},
        "query": query, "matched_count": len(matches), "returned_count": len(rows),
        "stories": rows,
        "next_cursor": _cursor(rev, query_hash, following) if following < len(matches) else None,
    }
