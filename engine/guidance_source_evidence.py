"""F07 reads retained SEC guidance bytes through the incumbent archive contract.

Search phrases are discovery hints. Only an exact source sentence, byte binding,
and decision-time-qualified acquisition can support a total-revenue proposal.
There is no network in the consumer, no new store, and no valuation math here.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

from engine.fundamental_forensics.models import canonical_json
from engine.fundamental_forensics.sec_document_spine import (
    archive_document_url, archive_receipt_from_json_bytes, sec_document_id,
)

RECEIPT_COLUMN = "guidance_archive_receipt"
CONTENT_COLUMN = "guidance_archive_content"
# B-F07-1 source extension: existing AAPL plus the source-qualified VCYT case.
# This is display eligibility only, not A6/A7 financial-use qualification.
DISPLAY_ISSUER_CIKS = {"AAPL": "0000320193", "VCYT": "0001384101"}
DISPLAY_TICKERS = tuple(DISPLAY_ISSUER_CIKS)
MAX_DOCUMENT_BYTES = 2 * 1024 * 1024


class QualifiedGuidanceContext(dict):
    """In-process result of byte/identity/time checks, never a persisted input."""



def archive_root() -> Path:
    from lib import config
    return config.data_dir() / "fundamental_forensics" / "archive"


def source_document(hit: dict) -> dict:
    """Resolve only the exact accession/document from the native SEC search row."""
    if not isinstance(hit, dict) or hit.get("form") != "8-K":
        raise ValueError("not an 8-K guidance hit")
    accession, separator, name = str(hit.get("id") or "").partition(":")
    if not separator:
        raise ValueError("missing exact filing document")
    cik = hit.get("cik")
    expected_cik = DISPLAY_ISSUER_CIKS.get(hit.get("ticker"))
    if expected_cik is None or str(cik).zfill(10) != expected_cik:
        raise ValueError("guidance issuer does not match the admitted display cohort")
    return {
        "document_id": sec_document_id(cik, accession, "archive", name),
        "archive_url": archive_document_url(cik, accession, name),
    }


def _instant(value: object) -> datetime:
    if not isinstance(value, str):
        raise ValueError("missing decision time")
    # A calendar day means its start, never a fabricated end-of-day visibility.
    if len(value) == 10:
        return datetime.combine(date.fromisoformat(value), datetime.min.time(), timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("decision time must have a timezone")
    return parsed.astimezone(timezone.utc)


def decode_receipt(hit: dict):
    value = hit.get(RECEIPT_COLUMN)
    if not isinstance(value, str) or len(value) > 8192:
        raise ValueError("missing bounded archive receipt")
    row = json.loads(value)
    raw = canonical_json(row).encode()
    return archive_receipt_from_json_bytes(raw)


def qualify_hit(hit: dict, content: bytes, *, as_of: object) -> dict | None:
    """Pure binding/clock gate; returns documentary context, never model values."""
    try:
        document = source_document(hit)
        receipt = decode_receipt(hit)
        accession, _, name = hit["id"].partition(":")
        identifiers = {sec_document_id(hit["cik"], accession, role, name)
                       for role in ("primary", "exhibit", "archive")}
        if receipt.archive_url != document["archive_url"] or receipt.document_id not in identifiers:
            return None
        if not isinstance(content, bytes) or len(content) > MAX_DOCUMENT_BYTES:
            return None
        if receipt.byte_length != len(content) or hashlib.sha256(content).hexdigest() != receipt.content_sha256:
            return None
        cutoff = _instant(as_of)
        retrieved = _instant(receipt.retrieved_at)
        filing = _instant(hit.get("file_date"))
        if retrieved > cutoff or filing > retrieved or filing > cutoff:
            return None
        from engine.guidance_source_context import extract_total_revenue_guidance
        parsed = extract_total_revenue_guidance(content, hit.get("direction"))
        if parsed.get("status") != "QUALIFIED":
            return None
        return QualifiedGuidanceContext({
            **parsed, "ticker": hit.get("ticker"), "hit_id": hit["id"],
            "source_url": receipt.archive_url, "document_id": receipt.document_id,
            "receipt_id": receipt.receipt_id, "content_sha256": receipt.content_sha256,
            "retrieved_at": receipt.retrieved_at, "decision_cutoff": cutoff.isoformat(),
        })
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        return None


def with_source_context(hit: dict, *, as_of: object, root: Path | None = None) -> dict:
    """Read-only hydration; missing/corrupt evidence preserves coarse abstention."""
    from collectors.sec_document_spine import read_archive_document
    out = dict(hit)
    # Never trust context forwarded by a persisted search row.
    out.pop("source_context", None)
    try:
        receipt = decode_receipt(out)
        content = out.get(CONTENT_COLUMN)
        if not isinstance(content, bytes):
            content = read_archive_document(root if root is not None else archive_root(), receipt)
        context = qualify_hit(out, content, as_of=as_of)
        if context:
            out["source_context"] = context
    except (OSError, TypeError, ValueError):
        pass
    # The retained document stays in the native source parquet/archive, never
    # in the public scenario payload or caller-facing hydrated hit.
    out.pop(CONTENT_COLUMN, None)
    return out
