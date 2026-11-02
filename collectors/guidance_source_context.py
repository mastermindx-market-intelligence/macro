"""Bounded source enrichment of the existing guidance-hit parquet.

The existing collector owns publication. This helper retains exact SEC bytes in
its incumbent immutable archive and adds a receipt pointer to existing rows.
Exact bounded bytes accompany the receipt in that same parquet so the existing
collector and renderer jobs need no shared filesystem or second event store.
It does not reinterpret the coarse theme tilt.
"""
from __future__ import annotations

import hashlib
import json
import logging

from collectors.sec_document_spine import SecFilingArchiveCollector, read_archive_document
from engine.guidance_source_evidence import (
    CONTENT_COLUMN, DISPLAY_TICKERS, MAX_DOCUMENT_BYTES, RECEIPT_COLUMN, archive_root,
    decode_receipt, source_document,
)
from lib import config

log = logging.getLogger(__name__)
MAX_DOCUMENTS_PER_REFRESH = 4


def enrich_guidance_hits(frame, *, collector=None):
    """Preserve every source row; a fetch failure never supplies qualified text."""
    if frame is None or frame.empty or not {"ticker", "id", "file_date"}.issubset(frame.columns):
        return frame
    out = frame.copy()
    selected = out[out["ticker"].isin(DISPLAY_TICKERS)].sort_values("file_date", ascending=False)
    if selected.empty:
        return out
    if RECEIPT_COLUMN not in out:
        out[RECEIPT_COLUMN] = None
    if CONTENT_COLUMN not in out:
        out[CONTENT_COLUMN] = None
    client = collector
    seen = {}
    attempts = 0
    for index, row in selected.iterrows():
        hit = row.to_dict()
        key = (str(hit.get("cik")), hit["id"])
        if key in seen:
            if seen[key] is not None:
                out.at[index, RECEIPT_COLUMN], out.at[index, CONTENT_COLUMN] = seen[key]
            continue
        seen[key] = None
        try:
            document = source_document(hit)
            value = hit.get(RECEIPT_COLUMN)
            if isinstance(value, str) and value:
                # Keep the original receipt/time; never relabel old bytes as a
                # fresh retrieval. Corruption remains unavailable, no refetch.
                receipt = decode_receipt(hit)
                if receipt.archive_url != document["archive_url"]:
                    continue
                content = hit.get(CONTENT_COLUMN)
                if not isinstance(content, bytes):
                    content = read_archive_document(client.cache_root if client else archive_root(), receipt)
                if (len(content) != receipt.byte_length or len(content) > MAX_DOCUMENT_BYTES
                        or hashlib.sha256(content).hexdigest() != receipt.content_sha256):
                    continue
                out.at[index, CONTENT_COLUMN] = content
                seen[key] = (value, content)
                continue
            if attempts >= MAX_DOCUMENTS_PER_REFRESH:
                continue
            if client is None:
                client = SecFilingArchiveCollector(
                    archive_root(), user_agent=config.load()["edgar"]["user_agent"],
                    max_attempts=1, max_document_bytes=MAX_DOCUMENT_BYTES,
                )
            attempts += 1
            receipt = client.fetch_document(document)
            if not hasattr(receipt, "to_dict"):
                continue
            value = json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":"))
            content = read_archive_document(client.cache_root, receipt)
            out.at[index, RECEIPT_COLUMN] = value
            out.at[index, CONTENT_COLUMN] = content
            seen[key] = (value, content)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            log.warning("guidance source unavailable for %s: %s", hit.get("id"), type(exc).__name__)
    return out
