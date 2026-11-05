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

def belief_context_points(rio: dict[str, Any]) -> list[dict[str, Any]]:
    """Project grounded belief/consensus relationships without claiming participant state.

    These rows expose only model synthesis already carried by the RIO's
    ``belief_delta`` and ``consensus_relation`` fields. They do not infer
    positioning, constraints, market response, or trading authority.
    """
    obj = _grounded_rio(rio)
    doc = obj["document"]
    rows: list[dict[str, Any]] = []
    for relation in ("belief_delta", "consensus_relation"):
        item = obj["analysis"][relation]
        text = item["statement"]
        support = list(item["support_claim_indices"])
        if not text or not support:
            continue
        if _text_is_verbatim_private_evidence(text, obj["claims"]):
            raise ValueError(
                f"analysis.{relation}.statement contains verbatim private evidence"
            )
        rows.append({
            "schema": "mastermind.research_belief_context.v1",
            "source_document_id": doc["id"],
            "source_content_sha256": doc["content_sha256"],
            "published_at": doc["published_at"],
            "relation": relation,
            "epistemic_layer": "model_synthesis",
            "text": text,
            "text_visibility": "derived_summary",
            "support_claim_indices": support,
            "authority": "descriptive_research_only",
        })
    return rows


def compare_grounded_claims(
    left_rio: dict[str, Any], right_rio: dict[str, Any], *,
    left_source: dict[str, Any], right_source: dict[str, Any],
    left_claim_index: int, right_claim_index: int,
    left_basis: dict[str, str], right_basis: dict[str, str],
    revision_annotation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Private descriptive comparison over two actual source bodies and RIOs.

    Sources are canonical extracted-text records (report_id, source_pdf_sha256,
    extracted_text_sha256, text) supplied by the already entitled Read owner.
    This pure helper checks consistency, never authenticates a source or grants
    permission. Literal quotes remain private; existing hash-only projections
    above remain unchanged. A basis is externally adjudicated metadata, never
    invented by this function. A differing statement is not automatically a
    contradictory economic forecast.

    An optional revision annotation is an explicit independent classification
    with a literal support quote in the right body. Its output stays labeled
    adjudicated interpretation; source narrative alone cannot confer authority.
    """
    def digest_ok(value):
        return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    def bind(rio, source, index):
        obj = _grounded_rio(rio)
        body = source.get("text")
        doc = obj["document"]
        if (not isinstance(body, str) or not body
                or source.get("report_id") != doc["id"]
                or not digest_ok(source.get("source_pdf_sha256"))
                or _text_hash(body) != source.get("extracted_text_sha256")
                or doc["content_sha256"] != source["extracted_text_sha256"]):
            raise ValueError("source/RIO extracted text identity mismatch")
        if type(index) is not int or index < 0 or index >= len(obj["claims"]):
            raise ValueError("claim index outside grounded RIO")
        claim = obj["claims"][index]
        if not quote_span_verified(body, claim["statement"], require_complete_clause=True):
            raise ValueError("compared claim is not literal source content")
        raw = body.encode("utf-8")
        spans = []
        for evidence in claim["evidence"]:
            quote = evidence["quote_span"]
            if not quote_span_verified(body, quote, require_complete_clause=True):
                continue
            literal = quote.encode("utf-8")
            start = raw.find(literal)
            if start < 0:
                continue
            spans.append({"report_id": doc["id"], "source_pdf_sha256": source["source_pdf_sha256"],
                          "extracted_text_sha256": doc["content_sha256"], "text": quote,
                          "start_byte": start, "end_byte": start + len(literal),
                          "passage_text_sha256": _text_hash(quote)})
        if not spans:
            raise ValueError("no retained exact literal comparison support")
        return obj, claim, spans
    left, lc, ls = bind(left_rio, left_source, left_claim_index)
    right, rc, rs = bind(right_rio, right_source, right_claim_index)
    axes = ("subject", "horizon", "units", "currency", "scenario")
    mismatches, missing = [], []
    for axis in axes:
        a, b = left_basis.get(axis), right_basis.get(axis)
        if not isinstance(a, str) or not a.strip() or not isinstance(b, str) or not b.strip():
            missing.append(axis)
        elif a.strip().casefold() != b.strip().casefold():
            mismatches.append(axis)
    # Reject an asserted metadata horizon contradicting an explicit RIO horizon.
    for claim, basis in ((lc, left_basis), (rc, right_basis)):
        if claim["horizon"] and claim["horizon"].strip().casefold() != str(basis.get("horizon", "")).strip().casefold():
            raise ValueError("comparison horizon contradicts explicit claim horizon")
    comparable = not mismatches and not missing
    relation = "SAME_SOURCE_STATEMENT" if lc["statement"] == rc["statement"] else "DIFFERING_SOURCE_STATEMENTS"
    if not comparable:
        relation = "UNQUALIFIED_BASIS"
    family = left_source.get("family_id")
    same_family = bool(isinstance(family, str) and family and family == right_source.get("family_id")
                       and left["document"]["institution"] == right["document"]["institution"])
    revision = "UNCLASSIFIED"
    annotation_span = None
    if same_family and left_source["extracted_text_sha256"] == right_source["extracted_text_sha256"]:
        revision = ("SAME_SOURCE_REVISION" if left_source["report_id"] == right_source["report_id"]
                    and left_source["source_pdf_sha256"] == right_source["source_pdf_sha256"]
                    else "IDENTICAL_REPORT_REISSUE" if left_source["source_pdf_sha256"] == right_source["source_pdf_sha256"]
                    else "IDENTICAL_EXTRACTED_TEXT")
    elif revision_annotation is not None:
        if not same_family or not comparable:
            raise ValueError("revision classification requires same source family and qualified basis")
        kind, quote = revision_annotation.get("kind"), revision_annotation.get("support_quote")
        if kind not in {"CHANGED_VIEW", "CORRECTED_FACTUAL_ERROR"} or not isinstance(quote, str) or not quote:
            raise ValueError("explicit grounded revision annotation required")
        markers = ({"correct", "error", "mistake", "更正", "错误"} if kind == "CORRECTED_FACTUAL_ERROR"
                   else {"revis", "raised", "lowered", "upgrade", "downgrade", "changed our view", "上调", "下调", "观点调整"})
        if not any(marker in quote.casefold() for marker in markers):
            raise ValueError("revision annotation lacks explicit correction/view-change source wording")
        body = right_source["text"]
        if not quote_span_verified(body, quote, require_complete_clause=True):
            raise ValueError("revision classification support unavailable")
        raw, literal = body.encode("utf-8"), quote.encode("utf-8")
        start = raw.find(literal)
        if start < 0:
            raise ValueError("revision support must retain literal bytes")
        revision = kind
        annotation_span = {"report_id": right["document"]["id"], "source_pdf_sha256": right_source["source_pdf_sha256"],
                           "extracted_text_sha256": right_source["extracted_text_sha256"], "text": quote,
                           "start_byte": start, "end_byte": start + len(literal), "passage_text_sha256": _text_hash(quote)}
    return {"schema": "mastermind.research_source_comparison.v1", "visibility": "private_entitled_only",
            "epistemic_layer": "evidence_linked_descriptive_comparison", "relation": relation,
            "comparable": comparable, "basis_mismatches": mismatches, "basis_missing": missing,
            "left": {"document_id": left["document"]["id"], "institution": left["document"]["institution"],
                     "claim_index": left_claim_index, "statement": lc["statement"], "basis": dict(left_basis), "evidence": ls},
            "right": {"document_id": right["document"]["id"], "institution": right["document"]["institution"],
                      "claim_index": right_claim_index, "statement": rc["statement"], "basis": dict(right_basis), "evidence": rs},
            "revision_relation": revision, "revision_classification_layer": "independent_adjudication" if annotation_span else "source_byte_comparison",
            "revision_support": annotation_span,
            "limitations": ["Different statements are not automatically contradictions", "Basis metadata requires independent source adjudication",
                            "Digests bind consistency, not source authenticity", "No unentitled or public comparison route is created"],
            "authority": "descriptive_research_only"}
