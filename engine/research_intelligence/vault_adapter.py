"""Adapter from existing Research Vault identity/body to Research Intelligence."""
from __future__ import annotations
from typing import Any, Callable
from .extractor import analyze_document

def analyze_vault_report(item: dict[str,Any], body: str, *, model_id: str, call: Callable | None = None) -> dict[str,Any]:
    report_id=str(item.get("id") or item.get("report_id") or "").strip()
    document={
        "id": report_id,
        "source_type": "institutional_research",
        "source_name": str(item.get("institution") or ""),
        "institution": str(item.get("institution") or ""),
        "desk": str(item.get("desk") or ""),
        "title": str(item.get("title") or ""),
        "published_at": str(item.get("published_at") or ""),
    }
    return analyze_document(document, body, model_id=model_id, call=call)
