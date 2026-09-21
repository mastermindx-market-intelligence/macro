"""Deterministic, rights-safe projections from a grounded Research Intelligence Object."""
from __future__ import annotations

import hashlib
from typing import Any

from engine.qual_extraction import quote_span_verified
from .schema import validate_rio


def _text_hash(text: str) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def _grounded_rio(rio: dict[str, Any]) -> dict[str, Any]:
    return validate_rio(rio, require_grounded_claims=True)


def _text_is_verbatim_private_evidence(
    text: str,
    claims: list[dict[str, Any]],
) -> bool:
    for claim in claims:
        for evidence in claim["evidence"]:
            quote = evidence["quote_span"]
            if quote_span_verified(quote, text, minimum_chars=4):
                return True
            if quote_span_verified(text, quote, minimum_chars=4):
                return True
    return False


def summary_points(rio: dict[str, Any], *, limit: int = 6) -> list[dict[str, Any]]:
    """Project private references without copying licensed source-claim text."""
    obj = _grounded_rio(rio)
    if limit <= 0:
        return []
    doc = obj["document"]
    thesis = obj["analysis"]["thesis"]
    if _text_is_verbatim_private_evidence(thesis["summary"], obj["claims"]):
        raise ValueError("analysis.thesis.summary contains verbatim private evidence")
    rows: list[dict[str, Any]] = [{
        "schema": "mastermind.research_summary_point.v1",
        "source_document_id": doc["id"],
        "source_content_sha256": doc["content_sha256"],
        "epistemic_layer": "model_synthesis",
        "text": thesis["summary"],
        "text_visibility": "derived_summary",
        "support_claim_indices": list(thesis["support_claim_indices"]),
        "authority": "descriptive_research_only",
    }]
    for index, claim in enumerate(obj["claims"]):
        rows.append({
            "schema": "mastermind.research_summary_point.v1",
            "source_document_id": doc["id"],
            "source_content_sha256": doc["content_sha256"],
            "epistemic_layer": "source_claim",
            "text": "",
            "text_visibility": "private_rio_only",
            "claim_statement_sha256": _text_hash(claim["statement"]),
            "support_claim_indices": [index],
            "authority": "descriptive_research_only",
        })
    dedup: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, tuple[int, ...]]] = set()
    for row in rows:
        key = (
            row["epistemic_layer"],
            row["text"],
            str(row.get("claim_statement_sha256") or ""),
            tuple(row["support_claim_indices"]),
        )
        if key not in seen:
            seen.add(key)
            dedup.append(row)
    return dedup[:limit]


def claim_edges(rio: dict[str, Any]) -> list[dict[str, Any]]:
    """Project descriptive claim edges without exposing licensed source text.

    Source-content, statement, and evidence hashes preserve lineage while all
    private claim/quote text remains inside the entitled RIO artifact.
    """
    obj = _grounded_rio(rio)
    doc = obj["document"]
    edges: list[dict[str, Any]] = []
    for idx, claim in enumerate(obj["claims"]):
        evidence_sha256 = [_text_hash(e["quote_span"]) for e in claim["evidence"]]
        grounded_entities = [
            entity for entity in claim["entities"]
            if any(
                quote_span_verified(evidence["quote_span"], entity, minimum_chars=1)
                for evidence in claim["evidence"]
            )
        ]
        entities: list[str | None] = grounded_entities if grounded_entities else [None]
        for entity in entities:
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
                "entity_grounding": "unresolved" if entity is None else "quote_mention",
                "statement_sha256": _text_hash(claim["statement"]),
                "horizon": claim["horizon"],
                "explicit": claim["explicit"],
                "evidence_sha256": evidence_sha256,
                "authority": "descriptive_research_only",
            })
    return edges
