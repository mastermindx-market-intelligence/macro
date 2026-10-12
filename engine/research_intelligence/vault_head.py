"""Bounded deep-read head over canonical Research Vault text.

The head follows the deterministic research-triage order, reads each private
PDF, and builds the F5 extracted-text record before W1. The text the model
sees is exactly that record's text, so W2 ``source_content_sha256`` is the
extracted-text hash. ``source_pdf_sha256`` is a separate binding and is not
written into the RIO or the receipt.
"""
from __future__ import annotations

from datetime import date
import hashlib
from typing import Any, Callable, Iterable

from engine.press import research_triage
from engine.research_vault import corpus as corpus_mod
from engine.research_vault import probe as vault_probe
from engine.research_vault.fulltext import build_extracted_text
from engine.research_vault.ingest import VAULT_PREFIX, extract_pdf_text

from .extractor import PROMPT_VERSION, SYSTEM_PROMPT
from .store import (
    SOURCE_BODY_MAX_BYTES,
    ResearchIntelligenceEffectUnknown,
    ResearchIntelligenceStoreError,
    _normalize_prompt_document,
    load_latest_research_intelligence,
    persist_analysis,
)
from .vault_adapter import analyze_vault_report

DEEP_READ_SCHEMA = "mastermind.research_intelligence.deep_read_item.v1"
DEFAULT_HEAD_SIZE = 20
MAX_HEAD_SIZE = 50
MAX_PDF_BYTES = 64 * 1024 * 1024
EXTRACTOR_NAME = "pdftotext"
EXTRACTOR_VERSION = "research_vault.ingest.extract_pdf_text.v1"
_NO_TEXT_LAYERS = frozenset({"none", "unavailable"})
_SOURCE_METADATA_KEYS = (
    "error_class",
    "pdf_max_bytes",
    "body_bytes",
    "body_max_bytes",
    "source_pdf_sha256",
    "extracted_text_sha256",
    "expected_pdf_sha256",
    "text_layer_state",
    "page_count",
    "extractor_name",
    "extractor_version",
)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _current_prompt_contract_sha256() -> str:
    return hashlib.sha256(
        (PROMPT_VERSION + "\n" + SYSTEM_PROMPT).encode("utf-8")
    ).hexdigest()


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
    if result.get("reconciled") is not True:
        raise ValueError("research triage did not reconcile the input denominator")
    return select_ranked_head(materialized, result, limit=limit), result


def read_canonical_text(
    store: Any,
    report_id: str,
    *,
    pdf_max_bytes: int = MAX_PDF_BYTES,
    body_max_bytes: int = SOURCE_BODY_MAX_BYTES,
    extractor: Callable[[bytes], str | None] = extract_pdf_text,
    expected_pdf_sha256: str | None = None,
) -> dict[str, Any]:
    """Read one canonical PDF and bind its F5 extracted text, or an explicit miss."""
    rid = str(report_id or "").strip()
    if not corpus_mod.valid_doc_id(rid):
        return {"state": "invalid_report_id", "report_id": rid}

    reader = getattr(store, "get_bytes_strict_bounded", None)
    if not callable(reader):
        return {"state": "strict_source_read_unavailable", "report_id": rid}

    try:
        pdf = reader(f"{VAULT_PREFIX}{rid}.pdf", pdf_max_bytes)
    except ValueError:
        return {
            "state": "pdf_too_large",
            "report_id": rid,
            "pdf_max_bytes": pdf_max_bytes,
        }
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

    pdf_sha = hashlib.sha256(pdf).hexdigest()
    if expected_pdf_sha256 is not None and expected_pdf_sha256 != pdf_sha:
        return {
            "state": "source_revision_mismatch",
            "report_id": rid,
            "source_pdf_sha256": pdf_sha,
            "expected_pdf_sha256": expected_pdf_sha256,
        }

    try:
        text = extractor(pdf)
    except Exception as exc:
        return {
            "state": "extractor_failed",
            "report_id": rid,
            "error_class": type(exc).__name__[:120],
            "source_pdf_sha256": pdf_sha,
        }
    if text is None:
        return {
            "state": "extractor_unavailable",
            "report_id": rid,
            "source_pdf_sha256": pdf_sha,
        }
    if not isinstance(text, str):
        return {
            "state": "extractor_invalid",
            "report_id": rid,
            "source_pdf_sha256": pdf_sha,
        }

    pages = vault_probe.probe(pdf).get("pages")
    layer = vault_probe.text_facts(text, pages)["text_layer"]
    page_count = pages if type(pages) is int else None
    if (not text.strip()) or layer in _NO_TEXT_LAYERS:
        return {
            "state": "no_text_layer",
            "report_id": rid,
            "source_pdf_sha256": pdf_sha,
            "text_layer_state": layer,
            "page_count": page_count,
        }

    encoded = text.encode("utf-8")
    if len(encoded) > body_max_bytes:
        return {
            "state": "source_body_too_large",
            "report_id": rid,
            "body_bytes": len(encoded),
            "body_max_bytes": body_max_bytes,
            "source_pdf_sha256": pdf_sha,
        }

    try:
        record = build_extracted_text(
            report_id=rid,
            source_pdf_sha256=pdf_sha,
            text=text,
            extractor_name=EXTRACTOR_NAME,
            extractor_version=EXTRACTOR_VERSION,
            page_count=page_count,
            text_layer_state=layer,
        )
    except (ValueError, TypeError) as exc:
        return {
            "state": "extracted_text_invalid",
            "report_id": rid,
            "source_pdf_sha256": pdf_sha,
            "error_class": type(exc).__name__[:120],
        }
    extracted_sha = _sha256_text(text)
    if record.get("extracted_text_sha256") != extracted_sha:
        return {
            "state": "extracted_text_invalid",
            "report_id": rid,
            "source_pdf_sha256": pdf_sha,
        }
    canonical = record["text"]
    return {
        "state": "ok",
        "report_id": rid,
        "body": canonical,
        "body_bytes": len(canonical.encode("utf-8")),
        "source_pdf_sha256": pdf_sha,
        "extracted_text_sha256": record["extracted_text_sha256"],
        "text_layer_state": record.get("text_layer_state"),
        "page_count": record.get("page_count"),
        "extractor_name": record.get("extractor_name"),
        "extractor_version": record.get("extractor_version"),
    }


def _expected_receipt_document(
    item: dict[str, Any],
    *,
    extracted_text_sha256: str,
) -> dict[str, str]:
    """Same prompt document ``analyze_vault_report`` produces, then W2-normalized."""
    raw = {
        "id": str(item.get("id") or item.get("report_id") or ""),
        "source_type": "institutional_research",
        "source_name": str(item.get("institution") or ""),
        "institution": str(item.get("institution") or ""),
        "desk": str(item.get("desk") or ""),
        "title": str(item.get("title") or ""),
        "published_at": str(item.get("published_at") or ""),
        "content_sha256": extracted_text_sha256,
    }
    return _normalize_prompt_document(
        {key: value.strip() for key, value in raw.items()}
    )


def _latest_is_current(
    latest: Any,
    item: dict[str, Any],
    *,
    extracted_text_sha256: str,
    requested_model: str,
) -> bool:
    if latest is None:
        return False
    receipt = getattr(latest, "receipt", None)
    if not isinstance(receipt, dict):
        return False
    if getattr(latest, "source_content_sha256", "") != extracted_text_sha256:
        return False
    if receipt.get("requested_model") != requested_model:
        return False
    if receipt.get("prompt_version") != PROMPT_VERSION:
        return False
    if receipt.get("prompt_contract_sha256") != _current_prompt_contract_sha256():
        return False
    try:
        expected = _expected_receipt_document(
            item,
            extracted_text_sha256=extracted_text_sha256,
        )
    except ResearchIntelligenceStoreError:
        return False
    return receipt.get("document") == expected


def _source_metadata(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: source[key]
        for key in _SOURCE_METADATA_KEYS
        if key in source
    }


def deep_read_candidate(
    candidate: dict[str, Any],
    *,
    store: Any,
    model_id: str,
    force: bool = False,
    call: Callable[..., tuple[str, str, str]] | None = None,
    text_provider: Callable[..., dict[str, Any]] = read_canonical_text,
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
    source = text_provider(
        store,
        report_id,
        pdf_max_bytes=pdf_max_bytes,
        body_max_bytes=body_max_bytes,
        expected_pdf_sha256=candidate.get("expected_pdf_sha256"),
    )
    if not isinstance(source, dict):
        return {**base, "state": "source_read_failed", "error_class": "TypeError"}
    meta = _source_metadata(source)
    if source.get("state") != "ok":
        return {**base, "state": source.get("state"), **meta}

    source_text = source.get("body")
    extracted_text_sha256 = source.get("extracted_text_sha256")
    if not isinstance(source_text, str) or not isinstance(extracted_text_sha256, str):
        return {**base, "state": "extracted_text_invalid", **meta}

    try:
        latest = load_latest_research_intelligence(store, report_id)
    except ResearchIntelligenceStoreError as exc:
        return {
            **base,
            "state": "latest_read_failed",
            "error_code": exc.code,
            **meta,
        }

    if not force and _latest_is_current(
        latest,
        item,
        extracted_text_sha256=extracted_text_sha256,
        requested_model=requested_model,
    ):
        receipt = latest.receipt if isinstance(latest.receipt, dict) else {}
        return {
            **base,
            "state": "already_current",
            "artifact_sha256": latest.artifact_sha256,
            "source_content_sha256": extracted_text_sha256,
            "provider": receipt.get("provider", ""),
            "model": receipt.get("model", ""),
            **meta,
        }

    analysis = analyze_vault_report(
        item,
        source_text,
        model_id=requested_model,
        call=call,
    )
    if not isinstance(analysis, dict) or analysis.get("state") != "ok":
        failed = analysis if isinstance(analysis, dict) else {}
        return {
            **base,
            "state": "analysis_failed",
            "analysis_state": failed.get("state"),
            "provider": failed.get("provider", ""),
            "model": failed.get("model", ""),
            "source_content_sha256": extracted_text_sha256,
            **meta,
        }

    predecessor = latest.artifact_sha256 if latest is not None else None
    try:
        receipt = persist_analysis(
            store,
            analysis,
            source_body=source_text,
            expected_current_artifact_sha256=predecessor,
        )
    except ResearchIntelligenceEffectUnknown as exc:
        return {
            **base,
            "state": "effect_unknown",
            "error_code": exc.code,
            "source_content_sha256": extracted_text_sha256,
            **meta,
        }
    except ResearchIntelligenceStoreError as exc:
        return {
            **base,
            "state": "persistence_failed",
            "error_code": exc.code,
            "source_content_sha256": extracted_text_sha256,
            **meta,
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
        **meta,
    }


def deep_read_head(
    candidates: Any,
    *,
    store: Any,
    model_id: str,
    force: bool = False,
    call: Callable[..., tuple[str, str, str]] | None = None,
    text_provider: Callable[..., dict[str, Any]] = read_canonical_text,
) -> dict[str, Any]:
    """Deep-read candidates in order. The first unknown write effect stops the batch."""
    rows = list(candidates)
    if len(rows) > MAX_HEAD_SIZE:
        raise ValueError(
            f"deep-read batch exceeds MAX_HEAD_SIZE ({MAX_HEAD_SIZE})"
        )
    results: list[dict[str, Any]] = []
    for candidate in rows:
        result = deep_read_candidate(
            candidate,
            store=store,
            model_id=model_id,
            force=force,
            call=call,
            text_provider=text_provider,
        )
        results.append(result)
        if result.get("state") == "effect_unknown":
            return {
                "schema": DEEP_READ_SCHEMA + ".batch",
                "results": results,
                "halted": "effect_unknown",
                "unattempted": len(rows) - len(results),
            }
    return {
        "schema": DEEP_READ_SCHEMA + ".batch",
        "results": results,
        "halted": None,
        "unattempted": 0,
    }
