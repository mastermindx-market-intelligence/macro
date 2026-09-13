"""Frozen long-form qualitative research document contract.

This is an enrichment inside the existing qualitative-intelligence organism.
Source claims are evidence-bearing; model synthesis may only point back to those
claims.  Nothing in this schema grants score, signal, sizing, gate, or trade
authority.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "mastermind.research_intelligence.v1"
_SOURCE_TYPES = {"institutional_research", "qualitative_article", "transcript", "policy", "other"}
_DIRECTIONS = {"bullish", "bearish", "mixed", "neutral", "unclear"}
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")


def _text(value: Any, limit: int = 8000) -> str:
    return " ".join(str(value or "").split())[:limit]


def _strings(value: Any, *, limit: int = 50, item_limit: int = 1000) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value[:limit]:
        text = _text(item, item_limit)
        if text and text not in out:
            out.append(text)
    return out


def _evidence(value: Any, *, limit: int = 12) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, str]] = []
    for raw in value[:limit]:
        if not isinstance(raw, dict):
            continue
        quote = _text(raw.get("quote_span"), 1600)
        if not quote:
            continue
        row = {"quote_span": quote}
        if row not in out:
            out.append(row)
    return out


def _support(value: Any, claim_count: int) -> list[int]:
    if not isinstance(value, list):
        return []
    out: list[int] = []
    for raw in value[:30]:
        if type(raw) is not int or raw < 0 or raw >= claim_count:
            continue
        if raw not in out:
            out.append(raw)
    return out


def _analysis_rows(value: Any, claim_count: int, *, limit: int = 30) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    out: list[dict[str, Any]] = []
    for raw in value[:limit]:
        if not isinstance(raw, dict):
            continue
        statement = _text(raw.get("statement"), 1800)
        support = _support(raw.get("support_claim_indices"), claim_count)
        if statement and support:
            out.append({"statement": statement, "support_claim_indices": support})
    return out


def _relation(value: Any, claim_count: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {"statement": "", "support_claim_indices": []}
    statement = _text(value.get("statement"), 1800)
    support = _support(value.get("support_claim_indices"), claim_count)
    if not statement or not support:
        return {"statement": "", "support_claim_indices": []}
    return {"statement": statement, "support_claim_indices": support}


def validate_rio(
    value: Any,
    *,
    expected_document_id: str | None = None,
    expected_document: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a normalized RIO or raise ValueError for an off-contract object."""
    if not isinstance(value, dict):
        raise ValueError("RIO must be an object")
    if value.get("schema") != SCHEMA:
        raise ValueError(f"unexpected schema: {value.get('schema')!r}")
    document = value.get("document")
    if not isinstance(document, dict):
        raise ValueError("document must be an object")
    document_id = _text(document.get("id"), 240)
    if not document_id:
        raise ValueError("document.id is required")
    if expected_document_id and document_id != expected_document_id:
        raise ValueError("document.id does not match the submitted document")
    source_type = _text(document.get("source_type"), 80)
    if source_type not in _SOURCE_TYPES:
        raise ValueError(f"unsupported source_type: {source_type!r}")
    content_sha256 = _text(document.get("content_sha256"), 64)
    if not _SHA256_RE.fullmatch(content_sha256):
        raise ValueError("document.content_sha256 must be lowercase SHA-256 hex")

    normalized: dict[str, Any] = {
        "schema": SCHEMA,
        "document": {
            "id": document_id,
            "source_type": source_type,
            "source_name": _text(document.get("source_name"), 160),
            "institution": _text(document.get("institution"), 160),
            "desk": _text(document.get("desk"), 160),
            "title": _text(document.get("title"), 500),
            "published_at": _text(document.get("published_at"), 80),
            "content_sha256": content_sha256,
        },
        "claims": [],
        "analysis": {},
        "authority": "descriptive_research_only",
    }

    for raw in value.get("claims") if isinstance(value.get("claims"), list) else []:
        if not isinstance(raw, dict):
            continue
        statement = _text(raw.get("statement"), 1800)
        if not statement:
            continue
        normalized["claims"].append({
            "statement": statement,
            "evidence": _evidence(raw.get("evidence")),
            "numbers": _strings(raw.get("numbers"), limit=12, item_limit=300),
            "entities": _strings(raw.get("entities"), limit=20, item_limit=120),
            "horizon": _text(raw.get("horizon"), 160),
            "explicit": raw.get("explicit") if type(raw.get("explicit")) is bool else False,
        })
    if not normalized["claims"]:
        raise ValueError("at least one substantive claim is required")

    claim_count = len(normalized["claims"])
    analysis = value.get("analysis")
    if not isinstance(analysis, dict):
        raise ValueError("analysis must be an object")
    thesis = analysis.get("thesis")
    if not isinstance(thesis, dict):
        raise ValueError("analysis.thesis must be an object")
    direction = _text(thesis.get("direction"), 30).lower()
    if direction not in _DIRECTIONS:
        raise ValueError(f"unsupported analysis.thesis.direction: {direction!r}")
    thesis_summary = _text(thesis.get("summary"), 2500)
    thesis_support = _support(thesis.get("support_claim_indices"), claim_count)
    if not thesis_summary:
        raise ValueError("analysis.thesis.summary is required")
    if not thesis_support:
        raise ValueError("analysis.thesis requires grounded claim support")

    assumptions = _analysis_rows(analysis.get("assumptions"), claim_count)
    catalysts = _analysis_rows(analysis.get("catalysts"), claim_count)
    falsifiers = _analysis_rows(analysis.get("falsifiers"), claim_count)
    counterarguments = _analysis_rows(analysis.get("counterarguments"), claim_count)

    forecasts: list[dict[str, Any]] = []
    for raw in analysis.get("forecasts") if isinstance(analysis.get("forecasts"), list) else []:
        if not isinstance(raw, dict):
            continue
        statement = _text(raw.get("statement"), 1800)
        support = _support(raw.get("support_claim_indices"), claim_count)
        if statement and support:
            forecasts.append({
                "statement": statement,
                "horizon": _text(raw.get("horizon"), 160),
                "confidence": _text(raw.get("confidence"), 160),
                "support_claim_indices": support,
            })

    implications: list[dict[str, Any]] = []
    for raw in analysis.get("implications") if isinstance(analysis.get("implications"), list) else []:
        if not isinstance(raw, dict):
            continue
        statement = _text(raw.get("statement"), 1800)
        support = _support(raw.get("support_claim_indices"), claim_count)
        direction_i = _text(raw.get("direction"), 30).lower()
        if statement and support:
            implications.append({
                "statement": statement,
                "assets": _strings(raw.get("assets"), limit=30, item_limit=120),
                "direction": direction_i if direction_i in _DIRECTIONS else "unclear",
                "order": 2 if raw.get("order") == 2 else 1,
                "support_claim_indices": support,
            })

    normalized["analysis"] = {
        "thesis": {
            "summary": thesis_summary,
            "direction": direction,
            "mechanism": _strings(thesis.get("mechanism"), limit=12, item_limit=1200),
            "conviction": _text(thesis.get("conviction"), 300),
            "support_claim_indices": thesis_support,
        },
        "assumptions": assumptions,
        "forecasts": forecasts,
        "catalysts": catalysts,
        "falsifiers": falsifiers,
        "counterarguments": counterarguments,
        "implications": implications,
        "belief_delta": _relation(analysis.get("belief_delta"), claim_count),
        "consensus_relation": _relation(analysis.get("consensus_relation"), claim_count),
        "uncertainties": _analysis_rows(analysis.get("uncertainties"), claim_count),
    }

    if expected_document is not None:
        expected_fields = {
            "id": _text(expected_document.get("id"), 240),
            "source_type": _text(expected_document.get("source_type"), 80),
            "source_name": _text(expected_document.get("source_name"), 160),
            "institution": _text(expected_document.get("institution"), 160),
            "desk": _text(expected_document.get("desk"), 160),
            "title": _text(expected_document.get("title"), 500),
            "published_at": _text(expected_document.get("published_at"), 80),
            "content_sha256": _text(expected_document.get("content_sha256"), 64),
        }
        for field, expected in expected_fields.items():
            if normalized["document"][field] != expected:
                raise ValueError(f"document.{field} does not match the submitted document")
    return normalized
