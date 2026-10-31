"""Producer-side materializer for the stored full-text derivative.

Imported only lazily, from inside ``ingest.run``. ``vault_head`` and ``ingest``
are imported inside functions so a test monkeypatch of ``extract_pdf_text`` is
visible. Both entry points resolve an omitted extractor for its selected version.

The ingest step is 395–435 s typical and 772 s worst. The job timeout is 900 s
and the overhead is about 31 s. The pass budget is
``min(180, max(0, 600 - elapsed_since_run_start))``. One item overruns by at
most about 35 s (a PDF download plus pdftotext's 30 s timeout). The job worst
case is about ``max(core + 31, 600 + 35 + 31 = 666)`` s, under 900 s while the
core is under about 869 s.

``FULLTEXT_MAX`` counts materializer calls (PDF downloads), not receipt reads.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from engine.research_vault import corpus as corpus_mod
from engine.research_vault import fulltext
from engine.research_vault import fulltext_store

FULLTEXT_MAX = 200
FULLTEXT_BUDGET_S = 180.0
FULLTEXT_RUN_WALL_S = 600.0

_SHA_RE_TEXT = "0123456789abcdef"
_COUNTED = (
    "materialized",
    "no_text_layer",
    "already_current",
    "pdf_missing",
    "too_large",
    "revision_mismatch",
    "existing_invalid",
)


def _valid_sha(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in _SHA_RE_TEXT for ch in value)
    )


def _meta(
    state: str,
    report_id: str,
    *,
    source_pdf_sha256: str | None = None,
    key: str | None = None,
    error_class: str | None = None,
) -> dict:
    out = {"state": state, "report_id": report_id}
    if isinstance(source_pdf_sha256, str):
        out["source_pdf_sha256"] = source_pdf_sha256
    if isinstance(key, str):
        out["key"] = key
    if isinstance(error_class, str) and error_class:
        out["error_class"] = error_class
    return out


def _write_record(
    store,
    report_id: str,
    source_pdf_sha256: str,
    record: dict,
    success: str,
    *,
    extractor_version: str = fulltext_store.EXTRACTOR_VERSION,
) -> dict:
    """Create-only put. No existence GET before the conditional write.

    The explicit ``extractor_version`` selects the derivative key plane, so a
    v2 opt-in write lands on its own immutable key and can never collide with
    — or overwrite — the v1 object for the same revision.
    """
    version = fulltext_store.validate_extractor_version(extractor_version)
    key = fulltext_store.derivative_key(
        report_id, source_pdf_sha256, extractor_version=version
    )
    blob = fulltext_store.encode_record(record)
    if len(blob) > fulltext_store.FULLTEXT_MAX_BYTES:
        return _meta("too_large", report_id, source_pdf_sha256=source_pdf_sha256)
    validator = getattr(store, "validate_strict_conditional_write_capability", None)
    putter = getattr(store, "put_bytes_strict_conditional", None)
    if not callable(validator) or not callable(putter):
        return _meta("store_unavailable", report_id, source_pdf_sha256=source_pdf_sha256)
    try:
        validator()
    except Exception as exc:
        return _meta(
            "store_unavailable",
            report_id,
            source_pdf_sha256=source_pdf_sha256,
            error_class=type(exc).__name__,
        )
    try:
        placed = putter(
            key,
            blob,
            expected_version=None,
            content_type="application/json",
        )
    except Exception as exc:
        return _meta(
            "store_unavailable",
            report_id,
            source_pdf_sha256=source_pdf_sha256,
            key=key,
            error_class=type(exc).__name__,
        )
    if placed is True:
        return _meta(success, report_id, source_pdf_sha256=source_pdf_sha256, key=key)
    if placed is not False:
        return _meta("failed", report_id, source_pdf_sha256=source_pdf_sha256, key=key)
    try:
        existing = store.get_bytes_strict_bounded(key, fulltext_store.FULLTEXT_MAX_BYTES)
    except Exception:
        return _meta(
            "existing_invalid",
            report_id,
            source_pdf_sha256=source_pdf_sha256,
            key=key,
        )
    decoded = None if existing is None else fulltext_store.decode_record(
        existing, report_id, source_pdf_sha256, extractor_version=version,
    )
    # A create conflict is idempotent only for the exact deterministic bytes
    # attempted by this producer, not merely another well-formed derivative.
    if decoded is None or existing != blob:
        return _meta(
            "existing_invalid",
            report_id,
            source_pdf_sha256=source_pdf_sha256,
            key=key,
        )
    return _meta("already_current", report_id, source_pdf_sha256=source_pdf_sha256, key=key)


# The known extractor resolution table. Exactly one known extractor per
# supported version; no second extraction plane is introduced.
_KNOWN_EXTRACTORS = {
    fulltext_store.EXTRACTOR_VERSION: "extract_pdf_text",
    fulltext_store.READING_ORDER_EXTRACTOR_VERSION: "extract_pdf_text_reading_order_v2",
}


def _resolve_extractor(version: str):
    """Resolve the known ingest extractor for a supported version at call time."""
    from engine.research_vault import ingest as ingest_mod
    return getattr(ingest_mod, _KNOWN_EXTRACTORS[version])


def materialize(
    store,
    report_id,
    *,
    expected_pdf_sha256,
    extractor=None,
    extractor_version: str = fulltext_store.EXTRACTOR_VERSION,
) -> dict:
    """Materialize one derivative. Never raises. Metadata only — never text.

    ``extractor=None`` resolves the known ingest extractor for the bound
    ``extractor_version`` at call time. The default version is the incumbent
    v1 contract, so every existing caller is unchanged; the pdftotext
    default-reading-order candidate is reached only through an explicit
    supported ``extractor_version`` and is written create-only to its own
    versioned key.
    """
    rid = report_id if isinstance(report_id, str) else str(report_id or "")
    try:
        version = fulltext_store.validate_extractor_version(extractor_version)
        if extractor is None:
            extractor = _resolve_extractor(version)
        from engine.research_intelligence import vault_head

        result = vault_head.read_canonical_text(
            store,
            rid,
            body_max_bytes=fulltext_store.FULLTEXT_MAX_BYTES,
            extractor=extractor,
            expected_pdf_sha256=expected_pdf_sha256,
            extractor_version=version,
        )
        if not isinstance(result, dict):
            return _meta("failed", rid)
        state = result.get("state")
        sha = result.get("source_pdf_sha256")
        sha_s = sha if isinstance(sha, str) else None
        error_class = result.get("error_class")
        error_s = error_class if isinstance(error_class, str) else None
        reported = result.get("report_id")
        out_id = reported if isinstance(reported, str) and reported else rid

        if state == "ok":
            record = fulltext.build_extracted_text(
                report_id=out_id,
                source_pdf_sha256=result.get("source_pdf_sha256"),
                text=result.get("body"),
                extractor_name=result.get("extractor_name"),
                extractor_version=result.get("extractor_version"),
                page_count=result.get("page_count"),
                text_layer_state=result.get("text_layer_state"),
            )
            if (
                record.get("extracted_text_sha256") != result.get("extracted_text_sha256")
                or record.get("extractor_name") != fulltext_store.EXTRACTOR_NAME
                or record.get("extractor_version") != version
            ):
                return _meta("extractor_failed", out_id, source_pdf_sha256=sha_s)
            return _write_record(
                store, out_id, record["source_pdf_sha256"], record, "materialized",
                extractor_version=version,
            )

        if state == "no_text_layer":
            # Stored text is blank-normalized: pdftotext emitted only whitespace
            # or form feeds. Never store ``unavailable``.
            if (
                result.get("text_layer_state") != "none"
                or not isinstance(sha_s, str)
                or result.get("extractor_version") != version
            ):
                return _meta("extractor_failed", out_id, source_pdf_sha256=sha_s, error_class=error_s)
            record = fulltext.build_extracted_text(
                report_id=out_id,
                source_pdf_sha256=sha_s,
                text="",
                extractor_name=fulltext_store.EXTRACTOR_NAME,
                extractor_version=version,
                page_count=result.get("page_count"),
                text_layer_state="none",
            )
            return _write_record(
                store, out_id, sha_s, record, "no_text_layer",
                extractor_version=version,
            )

        mapped = {
            "pdf_too_large": "too_large",
            "source_body_too_large": "too_large",
            "pdf_missing": "pdf_missing",
            "pdf_invalid": "pdf_missing",
            "source_revision_mismatch": "revision_mismatch",
            "extractor_unavailable": "extractor_unavailable",
            "extractor_failed": "extractor_failed",
            "extractor_invalid": "extractor_failed",
            "extracted_text_invalid": "extractor_failed",
            "strict_source_read_unavailable": "store_unavailable",
            "source_read_failed": "store_unavailable",
            "invalid_report_id": "failed",
        }.get(state, "failed")
        return _meta(mapped, out_id, source_pdf_sha256=sha_s, error_class=error_s)
    except Exception as exc:
        return _meta("failed", rid, error_class=type(exc).__name__)


def _empty_pass() -> dict:
    return {
        "candidates": 0,
        "attempted": 0,
        "materialized": 0,
        "no_text_layer": 0,
        "already_current": 0,
        "pdf_missing": 0,
        "extractor_failed": 0,
        "too_large": 0,
        "digest_unknown": 0,
        "revision_mismatch": 0,
        "existing_invalid": 0,
        "failed": 0,
        "remaining": 0,
        "aborted": None,
    }


def _corpus_shas(corpus_path) -> dict:
    conn = None
    try:
        uri = Path(corpus_path).resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        rows = conn.execute("SELECT doc_id, content_sha256 FROM documents")
        return {doc_id: sha for doc_id, sha in rows}
    except Exception:
        return {}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


def _published_at(item: dict) -> str:
    published = item.get("published_at")
    if isinstance(published, str) and published:
        return published
    return ""


def _order(items: list[dict]) -> list[dict]:
    items.sort(key=lambda it: it.get("id") if isinstance(it.get("id"), str) else "")
    items.sort(key=_published_at, reverse=True)
    return items


def _candidates(cat, shas: dict, derivs: frozenset[tuple[str, str]]) -> list[dict]:
    items = cat.get("items") if isinstance(cat, dict) else None
    seen: set[str] = set()
    class_a: list[dict] = []
    class_b: list[dict] = []
    derived_ids = {report_id for report_id, _sha in derivs}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        doc_id = item.get("id")
        if not corpus_mod.valid_doc_id(doc_id) or doc_id in seen:
            continue
        seen.add(doc_id)
        corpus_sha = shas.get(doc_id)
        if _valid_sha(corpus_sha) and (doc_id, corpus_sha) not in derivs:
            class_a.append(item)
        elif not _valid_sha(corpus_sha) and doc_id not in derived_ids:
            class_b.append(item)
    return _order(class_a) + _order(class_b)


def materialize_pending(
    store,
    cat,
    corpus_path,
    *,
    run_started,
    clock=time.monotonic,
    cap=None,
    budget_s=None,
    run_wall_s=None,
    materializer=None,
    tool_available=None,
) -> dict:
    """Bounded create-only pass over catalog items. Never raises.

    Writes nothing except derivative objects, and only through ``materialize``.
    The result is metadata counters — never text. Additive timing evidence:
    ``pre_pass_elapsed_s`` (run wall already consumed when the pass opened),
    ``budget_s`` (the exact effective budget the in-loop stop checks compare
    against) and ``pass_elapsed_s`` (one trailing sample taken after the loop);
    each is reported only on paths that actually reach it, so a missing field
    means the pass never got that far.
    """
    out = _empty_pass()
    try:
        if cap is None:
            cap = FULLTEXT_MAX
        if budget_s is None:
            budget_s = FULLTEXT_BUDGET_S
        if run_wall_s is None:
            run_wall_s = FULLTEXT_RUN_WALL_S
        if materializer is None:
            materializer = materialize
        if tool_available is None:
            from engine.research_vault import ingest as ingest_mod
            tool_available = ingest_mod._pdftotext_available

        shas = _corpus_shas(corpus_path)
        derivs = fulltext_store.list_derivatives(store)
        if derivs is None:
            out["aborted"] = "store_unavailable"
            out["pre_pass_elapsed_s"] = clock() - run_started
            return out
        pending = _candidates(cat, shas, derivs)
        out["candidates"] = len(pending)
        pass_start = clock()
        pre_pass_elapsed = pass_start - run_started
        out["pre_pass_elapsed_s"] = pre_pass_elapsed
        budget = min(float(budget_s), max(0.0, float(run_wall_s) - pre_pass_elapsed))
        out["budget_s"] = budget

        if pending and not tool_available():
            out["aborted"] = "tool_unavailable"
            out["pass_elapsed_s"] = clock() - pass_start
            out["remaining"] = len(pending)
            return out
        if pending:
            validator = getattr(store, "validate_strict_conditional_write_capability", None)
            if not callable(validator):
                out["aborted"] = "store_unavailable"
                out["remaining"] = len(pending)
                return out
            try:
                validator()
            except Exception:
                out["aborted"] = "store_unavailable"
                out["pass_elapsed_s"] = clock() - pass_start
                out["remaining"] = len(pending)
                return out

        processed = 0
        for item in pending:
            if out["attempted"] >= cap:
                out["aborted"] = "cap"
                break
            if clock() - pass_start >= budget:
                out["aborted"] = "budget"
                break
            processed += 1
            doc_id = item.get("id")
            try:
                blob = store.get_bytes_strict_bounded(
                    fulltext_store.receipt_key(doc_id),
                    fulltext_store.RECEIPT_MAX_BYTES,
                )
            except ValueError:
                out["digest_unknown"] += 1
                continue
            except Exception:
                out["aborted"] = "store_unavailable"
                break
            digest = fulltext_store.parse_receipt_digest(blob, doc_id)
            if digest is None:
                out["digest_unknown"] += 1
                continue
            if (doc_id, digest) in derivs:
                out["already_current"] += 1
                continue
            out["attempted"] += 1
            try:
                res = materializer(store, doc_id, expected_pdf_sha256=digest)
            except Exception:
                out["failed"] += 1
                continue
            state = res.get("state") if isinstance(res, dict) else None
            if state in _COUNTED:
                out[state] += 1
            elif state in {"extractor_failed", "extractor_unavailable"}:
                out["extractor_failed"] += 1
            elif state == "store_unavailable":
                out["aborted"] = "store_unavailable"
                break
            else:
                out["failed"] += 1
        out["pass_elapsed_s"] = clock() - pass_start
        out["remaining"] = len(pending) - processed
        return out
    except Exception:
        out["failed"] += 1
        return out
