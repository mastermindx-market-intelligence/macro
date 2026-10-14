"""Reader for the stored canonical full-text derivative.

Serving processes (Brain, the F12 MCP server) import this module. Its import
closure stays on the stdlib plus ``fulltext`` and ``corpus``: no ingest, no
probe, no ``vault_head``, no ``engine.press``, no PDF library, and no
``fulltext_writer``. Extraction happens only on the research-ingest runner;
this module only reads what that runner stored.

Key layout:

| object | key | writer |
|---|---|---|
| vault PDF (existing) | ``research_vault/<rid>.pdf`` | ingest |
| RIO (existing) | ``research_vault/intelligence/v1/...`` | research_intelligence.store |
| ingest receipt (existing, READ only) | ``research_inbox/_processed/<rid>.json`` | ingest |
| full-text derivative (NEW) | ``research_vault/fulltext/v1/<rid>/<source_pdf_sha256>/<DERIVATIVE_TAG>.json`` | fulltext_writer |

A derivative key never ends in ``.pdf``, so every ``endswith(".pdf")`` vault-PDF
consumer ignores it. Listing always uses the trailing-slash prefix. A corrected
PDF is a new object, never an overwrite. The current revision is the receipt's
``content_sha256``; when that digest is unknown the reader serves None.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Mapping

from engine.research_vault import corpus, fulltext

FULLTEXT_PREFIX = "research_vault/fulltext/v1/"
RECEIPT_PREFIX = "research_inbox/_processed/"
FULLTEXT_MAX_BYTES = 2 * 1024 * 1024
RECEIPT_MAX_BYTES = 64 * 1024
EXTRACTOR_NAME = "pdftotext"
EXTRACTOR_VERSION = "research_vault.ingest.extract_pdf_text.v1"

_SHA_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_READ_LAYERS = frozenset({"full", "thin", "none"})


def _derivative_tag() -> str:
    payload = json.dumps(
        [
            fulltext.EXTRACTED_TEXT_SCHEMA,
            EXTRACTOR_NAME,
            EXTRACTOR_VERSION,
            fulltext.SEGMENTER_VERSION,
        ],
        separators=(",", ":"),
    ).encode("utf-8")
    return "v1-" + hashlib.sha256(payload).hexdigest()[:16]


DERIVATIVE_TAG = _derivative_tag()


def derivative_key(report_id: str, source_pdf_sha256: str) -> str:
    """Object key for one revision-bound derivative.

    Raises ValueError on an invalid report id or a sha that is not 64 lowercase
    hex. This is the only function in the module that raises.
    """
    if not corpus.valid_doc_id(report_id):
        raise ValueError("report_id is not a catalog slug")
    if not isinstance(source_pdf_sha256, str) or _SHA_RE.fullmatch(source_pdf_sha256) is None:
        raise ValueError("source_pdf_sha256 must be lowercase sha256")
    return f"{FULLTEXT_PREFIX}{report_id}/{source_pdf_sha256}/{DERIVATIVE_TAG}.json"


def receipt_key(report_id: str) -> str:
    """Ingest receipt key. Not validated; a bad id simply misses."""
    return f"{RECEIPT_PREFIX}{report_id}.json"


def encode_record(record: Mapping) -> bytes:
    """Deterministic UTF-8 JSON of a validated extracted-text record.

    The writer is the only caller. Invalid records raise ValueError.
    """
    fulltext._validate_extracted_text(record)
    return json.dumps(
        record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def decode_record(blob: bytes, report_id: str, source_pdf_sha256: str) -> dict | None:
    """Return the record only when it is the canonical derivative for this revision."""
    try:
        if type(blob) is not bytes:
            return None
        parsed = json.loads(blob.decode("utf-8"))
        if not isinstance(parsed, dict):
            return None
        if parsed.get("schema") != fulltext.EXTRACTED_TEXT_SCHEMA:
            return None
        if parsed.get("report_id") != report_id:
            return None
        if parsed.get("source_pdf_sha256") != source_pdf_sha256:
            return None
        if parsed.get("extractor_name") != EXTRACTOR_NAME:
            return None
        if parsed.get("extractor_version") != EXTRACTOR_VERSION:
            return None
        fulltext._validate_extracted_text(parsed)
        if parsed.get("text_layer_state") not in _READ_LAYERS:
            return None
        return parsed
    except Exception:
        return None


def parse_receipt_digest(blob: bytes, report_id: str) -> str | None:
    """Receipt ``content_sha256`` when the blob is a matching strict-UTF-8 receipt."""
    try:
        if type(blob) is not bytes:
            return None
        parsed = json.loads(blob.decode("utf-8"))
        if not isinstance(parsed, dict):
            return None
        if "id" in parsed and parsed.get("id") != report_id:
            return None
        digest = parsed.get("content_sha256")
        if isinstance(digest, str) and _SHA_RE.fullmatch(digest):
            return digest
        return None
    except Exception:
        return None


def source_digest(store, report_id: str) -> str | None:
    """Current PDF sha from the ingest receipt. Never an ETag or an MD5."""
    try:
        if not corpus.valid_doc_id(report_id):
            return None
        reader = getattr(store, "get_bytes_strict_bounded", None)
        if not callable(reader):
            return None
        blob = reader(receipt_key(report_id), RECEIPT_MAX_BYTES)
        if blob is None:
            return None
        return parse_receipt_digest(blob, report_id)
    except Exception:
        return None


def load_extracted_text(store, report_id: str, item) -> Mapping | None:
    """Load the derivative for the receipt's current PDF revision.

    ``item`` is accepted and unused. The signature is frozen for F10/F11/F12.

    At most two store operations: the receipt, then that revision's object.
    Never reads a ``.pdf`` key, never runs an extractor, and never lists.
    """
    del item
    digest = source_digest(store, report_id)
    if digest is None:
        return None
    try:
        reader = getattr(store, "get_bytes_strict_bounded", None)
        if not callable(reader):
            return None
        blob = reader(derivative_key(report_id, digest), FULLTEXT_MAX_BYTES)
    except Exception:
        return None
    if blob is None:
        return None
    return decode_record(blob, report_id, digest)


def _split_derivative_key(key: object) -> tuple[str, str] | None:
    prefix = FULLTEXT_PREFIX
    if not isinstance(key, str) or not key.startswith(prefix):
        return None
    rest = key[len(prefix):]
    report_id, slash, tail = rest.partition("/")
    source_sha, slash2, filename = tail.partition("/")
    if not slash or not slash2 or "/" in filename:
        return None
    if filename != f"{DERIVATIVE_TAG}.json":
        return None
    if not corpus.valid_doc_id(report_id) or _SHA_RE.fullmatch(source_sha) is None:
        return None
    return report_id, source_sha


def list_derivatives(store) -> frozenset[tuple[str, str]] | None:
    """``(report_id, source_pdf_sha256)`` pairs under the derivative prefix.

    One ``list_prefix``. An exception or a missing method returns None.
    """
    try:
        lister = getattr(store, "list_prefix", None)
        if not callable(lister):
            return None
        found: set[tuple[str, str]] = set()
        for key in lister(FULLTEXT_PREFIX):
            parsed = _split_derivative_key(key)
            if parsed is not None:
                found.add(parsed)
        return frozenset(found)
    except Exception:
        return None


def fulltext_inventory(store) -> frozenset[str] | None:
    """Report ids that have a materialized derivative of any layer, including ``none``.

    None when the listing failed OR came back empty. R2's ``list_prefix`` swallows
    errors and returns [], so empty is indistinguishable from failure and must
    not be reported as a confident zero.
    """
    derivs = list_derivatives(store)
    if not derivs:
        return None
    return frozenset(report_id for report_id, _sha in derivs)
