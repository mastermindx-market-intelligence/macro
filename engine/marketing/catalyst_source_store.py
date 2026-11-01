"""Namespaced Catalyst SEC source store and the canonical cycle index reader.

The Catalyst SEC source cycle publishes exactly ONE object per run — the
canonical ``catalyst/cycle_index.json`` — through the incumbent Filing
Forensics ``sync_source_roots`` snapshot machinery.  Writing through that
machinery directly would move the production Filing Forensics ``latest``
pointer, so every key is routed through :class:`NamespacedSourceStore`, which
pins all writes inside ``marketing/catalyst-sec-source/v1/``.  The production
Filing Forensics namespace (``fundamental_forensics/sec-source/v1``) is never
touched: the pointer the incumbent pipeline reads stays exactly where it was.

D4 retention: no SEC document bytes are ever stored here.  The index carries
URL, sha256, figures, filing clocks and the first-retrieval receipt id only.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

# Private incumbent snapshot helpers.  DEVIATION (recorded in the lane record):
# the pointer read/decode pair is private in engine.fundamental_forensics.
# source_sync; re-implementing the pointer contract here would fork it instead
# of reusing it, and the reader must agree byte-for-byte with the incumbent
# publisher.
from engine.fundamental_forensics.source_sync import (
    _decode_pointer,
    _read_versioned_pointer,
)
from engine.research_vault.r2_store import LocalStore, R2Store, build_store

NAMESPACE_PREFIX = "marketing/catalyst-sec-source/v1/"
INDEX_RELATIVE_PATH = "catalyst/cycle_index.json"
INDEX_SCHEMA = "marketing.catalyst_sec_cycle_index/v1"
INDEX_MAX_BYTES = 4 * 1024 * 1024

_STATUSES = ("ok", "incomplete", "failed", "not_checked")
_OUTCOMES = ("COMPLETE", "PARTIAL", "TRUNCATED")
_FORMS = ("8-K", "8-K/A")
_PARSE_STATUSES = ("parsed", "no_figures", "parse_failed")
_HEX64 = set("0123456789abcdef")


class CatalystSourceUnavailable(RuntimeError):
    """The namespaced Catalyst source store cannot be opened or read.

    The message is always a bare reason code (or an exception TYPE name) —
    never an environment value, path or credential.
    """


def _is_hex64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _HEX64


def _is_clock(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 20:
        return False
    if value[4] != "-" or value[7] != "-" or value[10] != "T":
        return False
    if value[13] != ":" or value[16] != ":" or value[19] != "Z":
        return False
    digits = value[0:4] + value[5:7] + value[8:10] + value[11:13] + value[14:16] + value[17:19]
    return digits.isdigit()


def _parse_clock(value: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _event_sort_keys(events: list) -> list[tuple[str, str]]:
    """Acceptance descending, filing_key ascending inside an acceptance tie."""
    by_filing = sorted(events, key=lambda event: str(event["filing_key"]))
    by_acceptance = sorted(
        by_filing, key=lambda event: str(event["acceptance_datetime"]), reverse=True)
    return [(event["acceptance_datetime"], event["filing_key"]) for event in by_acceptance]


class NamespacedSourceStore:
    """Prefix-pinning adapter: every key lands under one immutable namespace.

    Satisfies the incumbent ``Store`` / ``StrictReadStore`` /
    ``StrictBoundedReadStore`` / ``StrictConditionalWriteStore`` runtime
    protocols so it can be handed to ``sync_source_roots`` and
    ``PinnedSourceAuthority`` unchanged.
    """

    def __init__(self, inner: object, prefix: str = NAMESPACE_PREFIX) -> None:
        if not isinstance(prefix, str) or not prefix or not prefix.endswith("/"):
            raise ValueError("namespace prefix must be a non-empty trailing-slash string")
        self._inner = inner
        self._prefix = prefix

    @property
    def inner(self) -> object:
        """The wrapped store, read-only accessor for diagnostics and tests."""
        return self._inner

    def _k(self, key: object) -> str:
        if not isinstance(key, str) or not key:
            raise ValueError("store key must be a non-empty string")
        if key.startswith("/"):
            raise ValueError("store key must not start with '/'")
        if "\\" in key:
            raise ValueError("store key must not contain a backslash")
        for segment in key.split("/"):
            if segment in ("", ".", ".."):
                raise ValueError("store key must not contain empty, '.' or '..' segments")
        return self._prefix + key

    # --- Store -----------------------------------------------------------

    def get_bytes(self, key: str) -> bytes | None:
        return self._inner.get_bytes(self._k(key))

    def put_bytes(self, key: str, data: bytes,
                  content_type: str = "application/octet-stream") -> bool:
        return self._inner.put_bytes(self._k(key), data, content_type=content_type)

    def exists(self, key: str) -> bool:
        return self._inner.exists(self._k(key))

    def upload_time(self, key: str) -> str | None:
        return self._inner.upload_time(self._k(key))

    def list_prefix(self, prefix: str) -> list[str]:
        if not isinstance(prefix, str):
            raise ValueError("store prefix must be a string")
        if prefix:
            full = self._k(prefix)
        else:
            full = self._prefix
        namespaced = self._inner.list_prefix(full)
        return [key[len(self._prefix):] for key in namespaced
                if key.startswith(self._prefix)]

    # --- StrictReadStore / StrictBoundedReadStore ------------------------

    def get_bytes_strict(self, key: str) -> bytes | None:
        return self._inner.get_bytes_strict(self._k(key))

    def get_bytes_strict_bounded(self, key: str, maximum_bytes: int) -> bytes | None:
        return self._inner.get_bytes_strict_bounded(self._k(key), maximum_bytes)

    def get_bytes_strict_bounded_versioned(self, key: str, maximum_bytes: int):
        return self._inner.get_bytes_strict_bounded_versioned(self._k(key), maximum_bytes)

    # --- StrictConditionalWriteStore -------------------------------------

    def validate_strict_conditional_write_capability(self) -> None:
        self._inner.validate_strict_conditional_write_capability()

    def put_bytes_strict_conditional(
        self, key: str, data: bytes, *, expected_version: str | None,
        content_type: str = "application/octet-stream",
    ) -> bool:
        return self._inner.put_bytes_strict_conditional(
            self._k(key), data, expected_version=expected_version,
            content_type=content_type,
        )


def open_production_store() -> NamespacedSourceStore:
    """Open the namespaced store over the production research-vault R2 store.

    Refuses (reason code only, never an environment value) when a local
    research store is selected, when the incumbent builder fails or yields no
    store, or when the store is not an available ``R2Store``.
    """
    if os.environ.get("RESEARCH_LOCAL_STORE"):
        raise CatalystSourceUnavailable("research_local_store_set")
    try:
        inner = build_store()
    except Exception:  # noqa: BLE001 - reason codes never carry env values.
        raise CatalystSourceUnavailable("build_store_failed") from None
    if inner is None:
        raise CatalystSourceUnavailable("no_store_available")
    if type(inner) is not R2Store:
        raise CatalystSourceUnavailable("store_not_r2")
    if inner.available is not True:
        raise CatalystSourceUnavailable("r2_store_unavailable")
    return NamespacedSourceStore(inner)


def open_local_store(path: object) -> NamespacedSourceStore:
    """Namespaced store over a filesystem ``LocalStore`` (CLI/tests only)."""
    return NamespacedSourceStore(LocalStore(path))


@dataclass(frozen=True)
class LatestIndex:
    """The decoded prior cycle index plus its pinned snapshot identity."""

    index: dict
    snapshot_id: str
    snapshot_at: datetime
    manifest_key: str


def _require(condition: object, message: str) -> None:
    if not condition:
        raise ValueError(message)


def validate_index(obj: object) -> dict:
    """Structurally validate ``marketing.catalyst_sec_cycle_index/v1``.

    Raises ``ValueError`` on any shape, type, enum or ordering violation.
    """
    _require(isinstance(obj, dict), "index must be a JSON object")
    _require(obj.get("schema") == INDEX_SCHEMA, "index schema mismatch")
    for field in ("cycle_started_at", "cycle_completed_at", "window_start", "window_end"):
        _require(_is_clock(obj.get(field)), f"index {field} must be a UTC clock")
    _require(isinstance(obj.get("requests_used"), int)
             and not isinstance(obj.get("requests_used"), bool)
             and obj["requests_used"] >= 0, "index requests_used must be a non-negative int")
    _require(isinstance(obj.get("request_budget"), int)
             and not isinstance(obj.get("request_budget"), bool)
             and obj["request_budget"] >= 1, "index request_budget must be a positive int")
    _require(obj.get("outcome") in _OUTCOMES, "index outcome is invalid")
    _require(isinstance(obj.get("truncated"), bool), "index truncated must be a bool")

    issuers = obj.get("issuers")
    _require(isinstance(issuers, list), "index issuers must be an array")
    for issuer in issuers:
        _require(isinstance(issuer, dict), "issuer entry must be an object")
        _require(isinstance(issuer.get("ticker"), str) and issuer["ticker"],
                 "issuer ticker must be a non-empty string")
        cik = issuer.get("cik")
        _require(isinstance(cik, int) and not isinstance(cik, bool) and cik > 0,
                 "issuer cik must be a positive int")
        _require(isinstance(issuer.get("name"), str), "issuer name must be a string")
        _require(issuer.get("issuer_id") == f"cik:{cik:010d}",
                 "issuer issuer_id must be the canonical cik identity")
        _require(issuer.get("status") in _STATUSES, "issuer status is invalid")
        reason = issuer.get("reason")
        _require(reason is None or isinstance(reason, str), "issuer reason must be a string or null")

    events = obj.get("events")
    _require(isinstance(events, list), "index events must be an array")
    for event in events:
        _validate_event(event)
    order = [(event["acceptance_datetime"], event["filing_key"]) for event in events]
    _require(order == _event_sort_keys(events),
             "index events must be sorted by acceptance desc, filing_key")

    skipped = obj.get("skipped")
    _require(isinstance(skipped, list), "index skipped must be an array")
    for item in skipped:
        _require(isinstance(item, dict), "skipped entry must be an object")
        _require(isinstance(item.get("ticker"), str) and item["ticker"],
                 "skipped ticker must be a non-empty string")
        _require(isinstance(item.get("accession"), str) and item["accession"],
                 "skipped accession must be a non-empty string")
        _require(isinstance(item.get("reason"), str) and item["reason"],
                 "skipped reason must be a non-empty string")
    return obj


def _validate_event(event: object) -> None:
    _require(isinstance(event, dict), "event must be an object")
    ticker = event.get("ticker")
    _require(isinstance(ticker, str) and ticker, "event ticker must be a non-empty string")
    cik = event.get("cik")
    _require(isinstance(cik, int) and not isinstance(cik, bool) and cik > 0,
             "event cik must be a positive int")
    accession = event.get("accession")
    _require(isinstance(accession, str) and accession, "event accession must be non-empty")
    _require(event.get("filing_key") == f"{cik:010d}:{accession}",
             "event filing_key must be canonical")
    _require(event.get("form") in _FORMS, "event form must be 8-K or 8-K/A")
    items = event.get("items")
    _require(isinstance(items, list) and all(isinstance(t, str) and t for t in items),
             "event items must be an array of tokens")
    filing_date = event.get("filing_date")
    _require(isinstance(filing_date, str) and len(filing_date) == 10
             and filing_date[4] == "-" and filing_date[7] == "-",
             "event filing_date must be YYYY-MM-DD")
    report_date = event.get("report_date")
    _require(report_date is None or isinstance(report_date, str), "event report_date must be a string or null")
    _require(_is_clock(event.get("acceptance_datetime")),
             "event acceptance_datetime must be a UTC clock")
    exhibit = event.get("exhibit")
    _require(isinstance(exhibit, dict), "event exhibit must be an object")
    _require(exhibit.get("exhibit_type") == "EX-99.1", "event exhibit_type must be EX-99.1")
    _require(isinstance(exhibit.get("source_url"), str)
             and exhibit["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/"),
             "event source_url must be an SEC archive URL")
    _require(_is_hex64(exhibit.get("document_sha256")), "event document_sha256 must be 64 lowercase hex")
    _require(isinstance(exhibit.get("byte_length"), int)
             and not isinstance(exhibit.get("byte_length"), bool)
             and exhibit["byte_length"] >= 0, "event byte_length must be a non-negative int")
    retention = event.get("retention")
    _require(isinstance(retention, dict), "event retention must be an object")
    _require(_is_clock(retention.get("first_retained_at")),
             "event first_retained_at must be a UTC clock")
    first_receipt = retention.get("first_retained_receipt_id")
    _require(isinstance(first_receipt, str) and first_receipt,
             "event first_retained_receipt_id must be non-empty")
    _require(_is_clock(retention.get("last_verified_at")),
             "event last_verified_at must be a UTC clock")
    figures = event.get("figures")
    _require(isinstance(figures, list), "event figures must be an array")
    for figure in figures:
        _require(isinstance(figure, dict), "figure must be an object")
        _require(isinstance(figure.get("field"), str) and figure["field"],
                 "figure field must be a non-empty string")
        _require(isinstance(figure.get("basis"), str) and figure["basis"],
                 "figure basis must be a non-empty string")
        value = figure.get("value")
        _require(isinstance(value, float) and not isinstance(value, bool),
                 "figure value must be a float")
        _require(_is_hex64(figure.get("span_sha256")), "figure span_sha256 must be 64 lowercase hex")
    lineage = event.get("lineage")
    _require(isinstance(lineage, dict), "event lineage must be an object")
    amends = lineage.get("amends_filing_key")
    _require(amends == "" or (isinstance(amends, str) and amends),
             "event amends_filing_key must be empty or canonical")
    _require(lineage.get("correction_generation") in (0, 1),
             "event correction_generation must be 0 or 1")
    _require(event.get("parse_status") in _PARSE_STATUSES, "event parse_status is invalid")


def read_latest_index(store: object) -> LatestIndex | None:
    """Read and validate the prior published cycle index, or None when absent.

    Every failure surfaces as ``CatalystSourceUnavailable`` carrying only the
    underlying exception TYPE name — no URLs, bytes or environment values.
    """
    from engine.fundamental_forensics.filing_attestation import PinnedSourceAuthority

    try:
        pointer = _read_versioned_pointer(store)
        if pointer.data is None:
            return None
        decoded = _decode_pointer(pointer.data)
        authority = PinnedSourceAuthority(
            store=store, snapshot_id=str(decoded["snapshot_id"]))
        read = authority.read_file(
            kind="raw", relative_path=INDEX_RELATIVE_PATH,
            maximum_bytes=INDEX_MAX_BYTES,
        )
        index = json.loads(read.content.decode("utf-8"))
        validate_index(index)
        return LatestIndex(
            index=index,
            snapshot_id=str(decoded["snapshot_id"]),
            snapshot_at=_parse_clock(str(decoded["snapshot_at"])),
            manifest_key=str(decoded["manifest_key"]),
        )
    except CatalystSourceUnavailable:
        raise
    except Exception as exc:  # noqa: BLE001 - reason codes carry type names only.
        raise CatalystSourceUnavailable(type(exc).__name__) from None
