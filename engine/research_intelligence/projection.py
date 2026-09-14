"""Deterministic, rights-safe projections from a grounded Research Intelligence Object."""
from __future__ import annotations

import hashlib
from typing import Any

from engine.qual_extraction import quote_span_verified
from .schema import validate_rio


def summary_points(rio: dict[str, Any], *, limit: int = 6) -> list[dict[str, Any]]:
    """Project private rows without collapsing source and synthesis layers."""
    obj = validate_rio(rio)
    if limit <= 0:
        return []
    doc = obj["document"]
    thesis = obj["analysis"]["thesis"]
    rows: list[dict[str, Any]] = [{
        "schema": "mastermind.research_summary_point.v1",
        "source_document_id": doc["id"],
        "source_content_sha256": doc["content_sha256"],
        "epistemic_layer": "model_synthesis",
        "text": thesis["summary"],
        "support_claim_indices": list(thesis["support_claim_indices"]),
        "authority": "descriptive_research_only",
    }]
    for index, claim in enumerate(obj["claims"]):
        rows.append({
            "schema": "mastermind.research_summary_point.v1",
            "source_document_id": doc["id"],
            "source_content_sha256": doc["content_sha256"],
            "epistemic_layer": "source_claim",
            "text": claim["statement"],
            "support_claim_indices": [index],
            "authority": "descriptive_research_only",
        })
    dedup: list[dict[str, Any]] = []
    seen: set[tuple[str, str, tuple[int, ...]]] = set()
    for row in rows:
        key = (
            row["epistemic_layer"],
            row["text"],
            tuple(row["support_claim_indices"]),
        )
        if row["text"] and key not in seen:
            seen.add(key)
            dedup.append(row)
    return dedup[:limit]


def _quote_hash(quote: str) -> str:
    return hashlib.sha256(str(quote).encode("utf-8")).hexdigest()


def claim_edges(rio: dict[str, Any]) -> list[dict[str, Any]]:
    """Project descriptive claim edges without exposing licensed quote text.

    These are private context edges only. Source-content and evidence hashes
    preserve lineage while quote spans remain inside the entitled RIO artifact.
    Returning this projection does not waive Research Vault access controls.
    """
    obj = validate_rio(rio)
    doc = obj["document"]
    edges: list[dict[str, Any]] = []
    for idx, claim in enumerate(obj["claims"]):
        evidence_sha256 = [_quote_hash(e["quote_span"]) for e in claim["evidence"]]
        grounded_entities = [
            entity for entity in claim["entities"]
            if any(
                quote_span_verified(evidence["quote_span"], entity, minimum_chars=1)
                for evidence in claim["evidence"]
            )
        ]
        for entity in grounded_entities or ["__unresolved__"]:
            edges.append({
                "schema": "mastermind.research_claim_edge.v1",
                "source_document_id": doc["id"],
                "source_content_sha256": doc["content_sha256"],
                "source_type": doc["source_type"],
                "source_name": doc["source_name"],
                "published_at": doc["published_at"],
                "claim_index": idx,
                "epistemic_layer": "source_claim",
                "entity": entity,
                "entity_grounding": (
                    "unresolved" if entity == "__unresolved__" else "quote_mention"
                ),
                "statement": claim["statement"],
                "horizon": claim["horizon"],
                "explicit": claim["explicit"],
                "evidence_sha256": evidence_sha256,
                "authority": "descriptive_research_only",
            })
    return edges
