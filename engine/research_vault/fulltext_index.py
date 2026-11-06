"""Opt-in full-body staging in the incumbent corpus; no extraction or publication.

The producer supplies an explicit cohort, trusted canonical loaders and finite
bounds. Body and revision metadata share the existing FTS transaction. A staging
receipt alone is never a publication, writer admission or production acceptance.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable

from engine.research_vault import corpus, fulltext, fulltext_store
from engine.research_vault.producer_generation import compute_catalog_payload_digest

BINDING_SCHEMA = "research_vault.fulltext_index_binding.v1"
META_KEY = "fulltext_index_publication"
_FIELDS = frozenset({"schema", "source_pdf_sha256", "extracted_text_sha256",
    "extractor_name", "extractor_version", "extracted_text_schema", "char_count",
    "byte_count", "text_layer_state"})
MAX_ROWS = 10000
MAX_BODY_BYTES = 256 * 1024 * 1024


def _dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _cohort(document):
    rows = document.get("items") if isinstance(document, dict) else None
    if not isinstance(rows, list) or not rows or len(rows) > MAX_ROWS:
        raise ValueError("explicit finite catalog cohort required")
    ids = [row.get("id") if isinstance(row, dict) else None for row in rows]
    if any(not corpus.valid_doc_id(rid) for rid in ids) or len(set(ids)) != len(ids):
        raise ValueError("unique valid catalog identities required")
    return sorted(ids)


def _binding(value, extractor_identity):
    try:
        value = json.loads(value) if isinstance(value, str) else value
        if not isinstance(value, dict) or set(value) != _FIELDS:
            return None
        if (value["schema"] != BINDING_SCHEMA
                or value["extracted_text_schema"] != fulltext.EXTRACTED_TEXT_SCHEMA
                or (value["extractor_name"], value["extractor_version"]) != extractor_identity
                or value["text_layer_state"] not in {"full", "thin", "none"}):
            return None
        for field in ("source_pdf_sha256", "extracted_text_sha256"):
            v = value[field]
            if not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v):
                return None
        if any(type(value[field]) is not int or value[field] < 0 for field in ("char_count", "byte_count")):
            return None
        if value["byte_count"] > fulltext_store.FULLTEXT_MAX_BYTES:
            return None
        return value
    except (ValueError, TypeError):
        return None


def _record(value, rid, current, row_digest, extractor_identity):
    try:
        if not isinstance(value, dict) or value.get("report_id") != rid:
            return None
        if (value.get("source_pdf_sha256") != current or current != row_digest
                or (value.get("extractor_name"), value.get("extractor_version")) != extractor_identity
                or value.get("text_layer_state") not in {"full", "thin", "none"}):
            return None
        # Bound the string before allocating its complete UTF8 representation.
        if not isinstance(value.get("text"), str) or len(value["text"]) > fulltext_store.FULLTEXT_MAX_BYTES:
            return None
        raw = fulltext._validate_extracted_text(value)
        if len(raw) > fulltext_store.FULLTEXT_MAX_BYTES:
            return None
        result = {key: value[key] for key in ("source_pdf_sha256", "extracted_text_sha256",
            "extractor_name", "extractor_version", "char_count", "byte_count", "text_layer_state")}
        result.update(schema=BINDING_SCHEMA, extracted_text_schema=value["schema"])
        return value["text"], result
    except (KeyError, ValueError, TypeError, UnicodeError):
        return None


def stage(conn, document, *, record_loader: Callable, source_digest_reader: Callable,
          max_rows: int, max_body_bytes: int,
          extractor_identity=(fulltext_store.EXTRACTOR_NAME, fulltext_store.EXTRACTOR_VERSION)):
    """Stage selected rows atomically, under explicitly supplied pilot bounds.

    A missing or changed current receipt clears obsolete BODY postings completely.
    A confirmed-current legacy prefix may remain when no canonical record exists.
    No implicit all-corpus selection, Store factory, PDF read or extraction occurs.
    Loader exceptions abort the snapshot; the caller must not publish that stage.
    """
    if (type(max_rows) is not int or not 1 <= max_rows <= MAX_ROWS
            or type(max_body_bytes) is not int or not 1 <= max_body_bytes <= MAX_BODY_BYTES):
        raise ValueError("finite explicit stage bounds required")
    if (not isinstance(extractor_identity, tuple) or len(extractor_identity) != 2
            or any(not isinstance(x, str) or not x.strip() or len(x) > 512 for x in extractor_identity)):
        raise ValueError("explicit qualified extractor identity required")
    # Default remains the incumbent canonical Store contract. A separately
    # qualified private composition may pin its real extractor identity; no
    # extraction, relabeling or global adoption follows from this local stage.
    ids = _cohort(document)
    if len(ids) > max_rows:
        raise ValueError("catalog exceeds explicit row bound")
    if "fulltext_binding" not in corpus._existing_columns(conn):
        raise ValueError("complete index migration required")
    result = dict(selected=len(ids), full=0, thin=0, none=0, unavailable=0,
                  missing_rows=0, budget_skipped=0, body_bytes=0)
    conn.execute("SAVEPOINT rv_fulltext_stage")
    try:
        for rid in ids:
            row = conn.execute("SELECT body,content_sha256,fulltext_binding FROM documents WHERE doc_id=?", (rid,)).fetchone()
            if row is None:
                result["missing_rows"] += 1
                continue
            loaded = record_loader(rid)
            # Recheck after the actual load, before the body+binding transaction.
            current = source_digest_reader(rid)
            validated = _record(loaded, rid, current, row["content_sha256"], extractor_identity)
            old = _binding(row["fulltext_binding"], extractor_identity)
            prefix_current = (isinstance(current, str) and len(current) == 64
                and all(c in "0123456789abcdef" for c in current)
                and current == row["content_sha256"]
                and (row["fulltext_binding"] is None or old is not None
                     and old["source_pdf_sha256"] == current))
            body = (row["body"] or "")[:corpus.BODY_MAX_CHARS] if prefix_current else ""
            binding = None
            if validated is not None:
                candidate, metadata = validated
                if result["body_bytes"] + metadata["byte_count"] <= max_body_bytes:
                    body, binding = candidate, _dump(metadata)
                    result[metadata["text_layer_state"]] += 1
                    result["body_bytes"] += metadata["byte_count"]
                else:
                    result["budget_skipped"] += 1
            else:
                result["unavailable"] += 1
            if body != row['body'] or binding != row['fulltext_binding']:
                conn.execute("UPDATE documents SET body=?,fulltext_binding=? WHERE doc_id=?", (body, binding, rid))
        publication = {"schema": "research_vault.fulltext_index_publication.v1",
            "extractor_identity": list(extractor_identity),
            "catalog_payload_sha256": compute_catalog_payload_digest(document),
            "member_ids_sha256": hashlib.sha256(_dump(ids).encode()).hexdigest(),
            "counts": result}
        conn.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (META_KEY, _dump(publication)))
        conn.execute("RELEASE SAVEPOINT rv_fulltext_stage")
        return dict(result, catalog_payload_sha256=publication["catalog_payload_sha256"])
    except BaseException:
        conn.execute("ROLLBACK TO SAVEPOINT rv_fulltext_stage")
        conn.execute("RELEASE SAVEPOINT rv_fulltext_stage")
        raise


def compact_for_publication(conn):
    """Compact one already committed native image without changing its content.

    The publisher owns this explicit boundary. Ordinary staging retains its
    caller's transaction; compaction must never commit it implicitly.
    """
    if conn.in_transaction:
        raise ValueError('commit staged image before compaction')
    conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('optimize')")
    conn.commit()
    conn.execute('VACUUM')


def discovery_coverage(conn, document, visible_ids):
    """Inspect bounded producer metadata only; never load a report or resweep R2.

    Published image/catalog custody belongs to the existing reader provider.
    This consistency check cannot authenticate an arbitrary caller-supplied DB.
    """
    try:
        admitted = set(_cohort(document))
        visible = set(visible_ids)
        if not visible or not visible <= admitted:
            return "PARTIAL_CORPUS"
        publication = conn.execute("SELECT value FROM meta WHERE key=?", (META_KEY,)).fetchone()
        if publication is None:
            return "PREFIX_ONLY_LEGACY"
        binding = json.loads(publication[0])
        if (binding.get("schema") != "research_vault.fulltext_index_publication.v1"
                or binding.get("catalog_payload_sha256") != compute_catalog_payload_digest(document)
                or binding.get("member_ids_sha256") != hashlib.sha256(_dump(sorted(admitted)).encode()).hexdigest()):
            return "PARTIAL_CORPUS"
        identity = binding.get("extractor_identity")
        if (not isinstance(identity, list) or len(identity) != 2
                or any(not isinstance(x, str) or not x.strip() or len(x) > 512 for x in identity)):
            return "PARTIAL_CORPUS"
        rows = conn.execute("SELECT doc_id,content_sha256,fulltext_binding FROM documents WHERE doc_id IN (SELECT value FROM json_each(?))", (_dump(sorted(visible)),)).fetchall()
        if len(rows) != len(visible):
            return "PARTIAL_CORPUS"
        for row in rows:
            b = _binding(row["fulltext_binding"], tuple(identity))
            if b is None or b["text_layer_state"] != "full" or b["source_pdf_sha256"] != row["content_sha256"]:
                return "PARTIAL_CORPUS"
        return "FULL_TEXT"
    except (ValueError, TypeError, KeyError, AttributeError, corpus.sqlite3.Error):
        return "PARTIAL_CORPUS"
