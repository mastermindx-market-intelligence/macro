"""Adapters from existing Research Vault identity/body to Research Intelligence."""

from __future__ import annotations

from typing import Any, Callable

from .extractor import analyze_document
from .store import persist_analysis


def analyze_vault_report(
    item: dict[str, Any],
    body: str,
    *,
    model_id: str,
    call: Callable | None = None,
) -> dict[str, Any]:
    report_id = str(item.get("id") or item.get("report_id") or "").strip()
    document = {
        "id": report_id,
        "source_type": "institutional_research",
        "source_name": str(item.get("institution") or ""),
        "institution": str(item.get("institution") or ""),
        "desk": str(item.get("desk") or ""),
        "title": str(item.get("title") or ""),
        "published_at": str(item.get("published_at") or ""),
    }
    return analyze_document(document, body, model_id=model_id, call=call)


def analyze_and_persist_vault_report(
    item: dict[str, Any],
    body: str,
    *,
    model_id: str,
    store: Any,
    expected_current_artifact_sha256: str | None = None,
    call: Callable | None = None,
) -> dict[str, Any]:
    """Run W1 analysis and persist only an explicitly successful grounded artifact."""
    result = analyze_vault_report(item, body, model_id=model_id, call=call)
    if result.get("state") != "ok" or not isinstance(result.get("rio"), dict):
        return {**result, "persistence": None}
    receipt = persist_analysis(
        store,
        result,
        source_body=body,
        expected_current_artifact_sha256=expected_current_artifact_sha256,
    )
    return {**result, "persistence": receipt.to_dict()}
