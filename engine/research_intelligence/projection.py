"""Deterministic, rights-safe projections from a grounded Research Intelligence Object."""
from __future__ import annotations

import hashlib
from typing import Any

from .schema import validate_rio


def summary_points(rio: dict[str, Any], *, limit: int = 6) -> list[str]:
    obj = validate_rio(rio)
    out = [obj["analysis"]["thesis"]["summary"]]
    out.extend(c["statement"] for c in obj["claims"][:max(0, limit - 1)])
    dedup: list[str] = []
    for text in out:
        if text and text not in dedup:
            dedup.append(text)
    return dedup[:limit]


def _quote_hash(quote: str) -> str:
    return hashlib.sha256(str(quote).encode("utf-8")).hexdigest()


def claim_edges(rio: dict[str, Any]) -> list[dict[str, Any]]:
    """Project descriptive claim edges without exposing licensed quote text.

    These are context edges only. Source-content and evidence hashes preserve
    lineage while the private quote spans remain inside the RIO artifact.
    """
    obj = validate_rio(rio)
    doc = obj["document"]
    edges: list[dict[str, Any]] = []
    for idx, claim in enumerate(obj["claims"]):
        evidence_sha256 = [_quote_hash(e["quote_span"]) for e in claim["evidence"]]
        for entity in claim["entities"] or ["__unresolved__"]:
            edges.append({
                "schema": "mastermind.research_claim_edge.v1",
                "source_document_id": doc["id"],
                "source_content_sha256": doc["content_sha256"],
                "source_type": doc["source_type"],
                "source_name": doc["source_name"],
                "published_at": doc["published_at"],
                "claim_index": idx,
                "entity": entity,
                "statement": claim["statement"],
                "horizon": claim["horizon"],
                "explicit": claim["explicit"],
                "evidence_sha256": evidence_sha256,
                "authority": "descriptive_research_only",
            })
    return edges
