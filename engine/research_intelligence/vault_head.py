"""Bounded deep-read head for canonical institutional Research Vault reports.

This module bridges the existing deterministic research triage to the existing
grounded Research Intelligence Object (W1) and private CAS persistence (W2).
It creates no new ranker, source identity, queue, scheduler, corpus, or store.

A deep read is only attempted from the canonical private PDF. The FTS corpus is
never substituted because its body is deliberately truncated for search.
"""
from __future__ import annotations

from datetime import date
import hashlib
from typing import Any, Callable, Iterable

from engine.press import research_triage
from engine.research_vault import corpus as corpus_mod
from engine.research_vault.ingest import VAULT_PREFIX, extract_pdf_text

from .extractor import PROMPT_VERSION
from .store import (
    SOURCE_BODY_MAX_BYTES,
    ResearchIntelligenceEffectUnknown,
    ResearchIntelligenceStoreError,
    load_latest_research_intelligence,
    persist_analysis,
)
from .vault_adapter import analyze_vault_report

DEEP_READ_SCHEMA = "mastermind.research_intelligence.deep_read_item.v1"
DEFAULT_HEAD_SIZE = 20
MAX_HEAD_SIZE = 50
MAX_PDF_BYTES = 64 * 1024 * 1024


def _head_size(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("deep-read head size must be an integer")
    if value < 1 or value > MAX_HEAD_SIZE:
        raise ValueError(f"deep-read head size must be in [1,{MAX_HEAD_SIZE}]")
    return value


def select_ranked_head(
    items: Iterable[dict[str, Any]],
    triage_result: dict[str, Any],
    *,
    limit: int = DEFAULT_HEAD_SIZE,
) -> list[dict[str, Any]]:
    """Select the deterministic triage head independently of press publish volume.

    research_triage.shortlist is deliberately NOT used: its flagship/note tiers
    are editorial publishing gates. Research cognition consumes the deterministic
    ranked order, including rows below today's publishing quota.
    """
    take = _head_size(limit)
    by_id: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        report_id = str(item.get("id") or "").strip()
        if report_id and report_id not in by_id:
            by_id[report_id] = item

    triage_rows = {
        str(row.get("report_id") or ""): row
        for row in (triage_result.get("rows") or [])
        if isinstance(row, dict) and row.get("report_id")
    }
    selected: list[dict[str, Any]] = []
    for report_id in research_triage.ranked_order(triage_result):
        item = by_id.get(report_id)
        row = triage_rows.get(report_id)
        if item is None or row is None:
            continue
        selected.append({"item": item, "triage": row})
        if len(selected) >= take:
            break
    return selected


def rank_vault_head(
    items: Iterable[dict[str, Any]],
    *,
    as_of: date,
    root: Any = None,
    cfg: dict[str, Any] | None = None,
    limit: int = DEFAULT_HEAD_SIZE,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run canonical research triage once and return its bounded cognition head."""
    materialized = list(items)
    result = research_triage.rank(
        materialized,
        as_of=as_of,
        root=root,
        cfg=cfg,
    )
    return select_ranked_head(materialized, result, limit=limit), result


def read_full_vault_body(
    store: Any,
    report_id: str,
    *,
    pdf_max_bytes: int = MAX_PDF_BYTES,
    body_max_bytes: int = SOURCE_BODY_MAX_BYTES,
    extractor: Callable[[bytes], str | None] = extract_pdf_text,
) -> dict[str, Any]:
    """Read and extract the complete canonical PDF without hidden truncation."""
    rid = str(report_id or "").strip()
    if not corpus_mod.valid_doc_id(rid):
        return {"state": "invalid_report_id", "report_id": rid}

    reader = getattr(store, "get_bytes_strict_bounded", None)
    if not callable(reader):
        return {"state": "strict_source_read_unavailable", "report_id": rid}

    try:
        pdf = reader(f"{VAULT_PREFIX}{rid}.pdf", pdf_max_bytes)
    except ValueError:
        return {"state": "pdf_too_large", "report_id": rid, "pdf_max_bytes": pdf_max_bytes}
    except Exception as exc:
        return {
            "state": "source_read_failed",
            "report_id": rid,
            "error_class": type(exc).__name__[:120],
        }
    if pdf is None:
        return {"state": "pdf_missing", "report_id": rid}
    if type(pdf) is not bytes or not pdf:
        return {"state": "pdf_invalid", "report_id": rid}

    body = extractor(pdf)
    if body is None:
        return {"state": "extractor_unavailable", "report_id": rid}
    if not isinstance(body, str):
        return {"state": "extractor_invalid", "report_id": rid}
    if not body.strip():
        return {"state": "no_text_layer", "report_id": rid}

    body_bytes = body.encode("utf-8")
    if len(body_bytes) > body_max_bytes:
        return {
            "state": "source_body_too_large",
            "report_id": rid,
            "body_bytes": len(body_bytes),
            "body_max_bytes": body_max_bytes,
        }
    return {
        "state": "ok",
        "report_id": rid,
        "body": body,
        "body_bytes": len(body_bytes),
        "source_content_sha256": hashlib.sha256(body_bytes).hexdigest(),
    }


def _expected_receipt_document(
    item: dict[str, Any],
    *,
    source_content_sha256: str,
) -> dict[str, str]:
    report_id = str(item.get("id") or item.get("report_id") or "").strip()
    return {
        "id": report_id,
        "source_type": "institutional_research",
        "source_name": str(item.get("institution") or "").strip(),
        "institution": str(item.get("institution") or "").strip(),
        "desk": str(item.get("desk") or "").strip(),
        "title": str(item.get("title") or "").strip(),
        "published_at": str(item.get("published_at") or "").strip(),
        "content_sha256": source_content_sha256,
    }


def _latest_is_current(
    latest: Any,
    item: dict[str, Any],
    *,
    source_content_sha256: str,
    requested_model: str,
) -> bool:
    if latest is None:
        return False
    receipt = getattr(latest, "receipt", None)
    if not isinstance(receipt, dict):
        return False
    return bool(
        getattr(latest, "source_content_sha256", "") == source_content_sha256
        and receipt.get("requested_model") == requested_model
        and receipt.get("prompt_version") == PROMPT_VERSION
        and receipt.get("document")
        == _expected_receipt_document(
            item,
            source_content_sha256=source_content_sha256,
        )
    )


def deep_read_candidate(
    candidate: dict[str, Any],
    *,
    store: Any,
    model_id: str,
    force: bool = False,
    call: Callable[..., tuple[str, str, str]] | None = None,
    extractor: Callable[[bytes], str | None] = extract_pdf_text,
    pdf_max_bytes: int = MAX_PDF_BYTES,
    body_max_bytes: int = SOURCE_BODY_MAX_BYTES,
) -> dict[str, Any]:
    """Deep-read one selected report and publish only through W2's exact CAS path."""
    item = candidate.get("item") if isinstance(candidate, dict) else None
    triage = candidate.get("triage") if isinstance(candidate, dict) else None
    if not isinstance(item, dict):
        raise ValueError("deep-read candidate requires an item")
    triage = triage if isinstance(triage, dict) else {}
    report_id = str(item.get("id") or "").strip()
    requested_model = str(model_id or "").strip()
    if not requested_model:
        raise ValueError("model_id is required")

    base = {
        "schema": DEEP_READ_SCHEMA,
        "report_id": report_id,
        "rank": triage.get("rank"),
        "w_score": triage.get("w_score"),
        "requested_model": requested_model,
    }
    source = read_full_vault_body(
        store,
        report_id,
        pdf_max_bytes=pdf_max_bytes,
        body_max_bytes=body_max_bytes,
        extractor=extractor,
    )
    if source["state"] != "ok":
        return {**base, "state": source["state"], "source": source}

    body = source["body"]
    source_sha256 = source["source_content_sha256"]
    try:
        latest = load_latest_research_intelligence(store, report_id)
    except ResearchIntelligenceStoreError as exc:
        return {
            **base,
            "state": "latest_read_failed",
            "error_code": exc.code,
            "source_content_sha256": source_sha256,
        }

    if not force and _latest_is_current(
        latest,
        item,
        source_content_sha256=source_sha256,
        requested_model=requested_model,
    ):
        return {
            **base,
            "state": "already_current",
            "artifact_sha256": latest.artifact_sha256,
            "source_content_sha256": source_sha256,
            "provider": latest.receipt.get("provider", ""),
            "model": latest.receipt.get("model", ""),
        }

    analysis = analyze_vault_report(
        item,
        body,
        model_id=requested_model,
        call=call,
    )
    if analysis.get("state") != "ok":
        return {
            **base,
            "state": "analysis_failed",
            "analysis_state": analysis.get("state"),
            "provider": analysis.get("provider", ""),
            "model": analysis.get("model", ""),
            "source_content_sha256": source_sha256,
        }

    predecessor = latest.artifact_sha256 if latest is not None else None
    try:
        receipt = persist_analysis(
            store,
            analysis,
            source_body=body,
            expected_current_artifact_sha256=predecessor,
        )
    except ResearchIntelligenceEffectUnknown as exc:
        return {
            **base,
            "state": "effect_unknown",
            "error_code": exc.code,
            "source_content_sha256": source_sha256,
        }
    except ResearchIntelligenceStoreError as exc:
        return {
            **base,
            "state": "persistence_failed",
            "error_code": exc.code,
            "source_content_sha256": source_sha256,
        }

    return {
        **base,
        "state": "persisted",
        "write_state": receipt.state,
        "artifact_sha256": receipt.artifact_sha256,
        "previous_artifact_sha256": receipt.previous_artifact_sha256,
        "source_content_sha256": receipt.source_content_sha256,
        "provider": analysis.get("provider", ""),
        "model": analysis.get("model", ""),
    }
