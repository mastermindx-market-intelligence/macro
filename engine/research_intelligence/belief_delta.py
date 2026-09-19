"""Deterministic longitudinal belief deltas over two grounded institutional RIOs.

This is a rights-safe derived comparison inside the existing Research Intelligence
organism. It creates no new source identity, model call, store, graph, queue, or
predictive authority. The delta retains hashes and claim references, not licensed
claim/evidence text, so a consumer can resolve detail only through the entitled
RIOs themselves.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from typing import Any, Iterable

from engine.qual_extraction import citation_normalize

from .schema import validate_rio

SCHEMA = "mastermind.research_intelligence.belief_delta.v1"
SUMMARY_SCHEMA = "mastermind.research_intelligence.belief_delta_summary.v1"

_CATEGORY_FIELDS = (
    "assumptions",
    "forecasts",
    "catalysts",
    "falsifiers",
    "counterarguments",
    "implications",
    "uncertainties",
)


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _norm(value: Any) -> str:
    return " ".join(citation_normalize(str(value or "")).split())


def _normalized_hash(value: Any) -> str:
    normalized = _norm(value)
    return _sha256_text(normalized) if normalized else ""


def _parse_timestamp(value: str, *, label: str) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} published_at is required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} published_at is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} published_at must include a timezone")
    return parsed


def _claim_hashes(rio: dict[str, Any]) -> list[str]:
    return [_normalized_hash(claim["statement"]) for claim in rio["claims"]]


def _support_hashes(
    support: Iterable[int],
    claim_hashes: list[str],
) -> list[str]:
    out: list[str] = []
    for index in support:
        if type(index) is not int or index < 0 or index >= len(claim_hashes):
            continue
        value = claim_hashes[index]
        if value and value not in out:
            out.append(value)
    return out


def _hashed_values(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for value in values:
        digest = _normalized_hash(value)
        if digest and digest not in out:
            out.append(digest)
    return out


def _category_rows(
    rio: dict[str, Any],
    field: str,
    claim_hashes: list[str],
) -> dict[str, dict[str, Any]]:
    rows = rio["analysis"].get(field) or []
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        statement_hash = _normalized_hash(row.get("statement"))
        if not statement_hash:
            continue
        payload: dict[str, Any] = {
            "statement_sha256": statement_hash,
            "support_claim_sha256": _support_hashes(
                row.get("support_claim_indices") or [],
                claim_hashes,
            ),
        }
        if field == "forecasts":
            payload["horizon_sha256"] = _normalized_hash(row.get("horizon"))
            payload["confidence_sha256"] = _normalized_hash(row.get("confidence"))
        elif field == "implications":
            payload["assets_sha256"] = _hashed_values(row.get("assets") or [])
            payload["direction"] = str(row.get("direction") or "unclear")
            payload["order"] = 2 if row.get("order") == 2 else 1
        out[statement_hash] = payload
    return out


def _set_delta(
    previous: Iterable[str],
    current: Iterable[str],
) -> dict[str, list[str]]:
    prior = set(previous)
    now = set(current)
    return {
        "added_sha256": sorted(now - prior),
        "removed_sha256": sorted(prior - now),
        "shared_sha256": sorted(prior & now),
    }


def _category_delta(
    previous: dict[str, Any],
    current: dict[str, Any],
    field: str,
    previous_claim_hashes: list[str],
    current_claim_hashes: list[str],
) -> dict[str, Any]:
    prior_rows = _category_rows(previous, field, previous_claim_hashes)
    current_rows = _category_rows(current, field, current_claim_hashes)
    prior_keys = set(prior_rows)
    current_keys = set(current_rows)
    return {
        "added": [current_rows[key] for key in sorted(current_keys - prior_keys)],
        "removed": [prior_rows[key] for key in sorted(prior_keys - current_keys)],
        "shared": [current_rows[key] for key in sorted(prior_keys & current_keys)],
    }


def _document_ref(rio: dict[str, Any]) -> dict[str, str]:
    doc = rio["document"]
    return {
        "document_id": doc["id"],
        "source_content_sha256": doc["content_sha256"],
        "published_at": doc["published_at"],
    }


def compare_institutional_rio(
    previous: Any,
    current: Any,
) -> dict[str, Any]:
    """Return one metadata-only longitudinal delta for successive institutional RIOs."""
    prior = validate_rio(previous, require_grounded_claims=True)
    now = validate_rio(current, require_grounded_claims=True)

    for label, rio in (("previous", prior), ("current", now)):
        if rio["document"]["source_type"] != "institutional_research":
            raise ValueError(f"{label} RIO is not institutional research")

    prior_doc = prior["document"]
    current_doc = now["document"]
    if prior_doc["id"] == current_doc["id"]:
        raise ValueError("longitudinal comparison requires distinct document ids")
    if not prior_doc["institution"] or prior_doc["institution"] != current_doc["institution"]:
        raise ValueError("institution identity must match across longitudinal comparison")

    prior_time = _parse_timestamp(prior_doc["published_at"], label="previous")
    current_time = _parse_timestamp(current_doc["published_at"], label="current")
    if current_time <= prior_time:
        raise ValueError("current report must be newer than previous report")

    prior_claim_hashes = _claim_hashes(prior)
    current_claim_hashes = _claim_hashes(now)
    claims = _set_delta(prior_claim_hashes, current_claim_hashes)

    prior_thesis = prior["analysis"]["thesis"]
    current_thesis = now["analysis"]["thesis"]
    prior_mechanisms = _hashed_values(prior_thesis.get("mechanism") or [])
    current_mechanisms = _hashed_values(current_thesis.get("mechanism") or [])
    mechanisms = _set_delta(prior_mechanisms, current_mechanisms)

    prior_numbers = _hashed_values(
        number for claim in prior["claims"] for number in claim.get("numbers") or []
    )
    current_numbers = _hashed_values(
        number for claim in now["claims"] for number in claim.get("numbers") or []
    )
    numbers = _set_delta(prior_numbers, current_numbers)

    prior_entities = sorted(
        {
            _norm(entity)
            for claim in prior["claims"]
            for entity in claim.get("entities") or []
            if _norm(entity)
        }
    )
    current_entities = sorted(
        {
            _norm(entity)
            for claim in now["claims"]
            for entity in claim.get("entities") or []
            if _norm(entity)
        }
    )
    entities = {
        "added": sorted(set(current_entities) - set(prior_entities)),
        "removed": sorted(set(prior_entities) - set(current_entities)),
        "shared": sorted(set(prior_entities) & set(current_entities)),
    }

    categories = {
        field: _category_delta(
            prior,
            now,
            field,
            prior_claim_hashes,
            current_claim_hashes,
        )
        for field in _CATEGORY_FIELDS
    }

    changed_categories = [
        field
        for field, delta in categories.items()
        if delta["added"] or delta["removed"]
    ]
    direction_changed = prior_thesis["direction"] != current_thesis["direction"]
    conviction_changed = (
        _normalized_hash(prior_thesis.get("conviction"))
        != _normalized_hash(current_thesis.get("conviction"))
    )
    material_change = bool(
        direction_changed
        or conviction_changed
        or claims["added_sha256"]
        or claims["removed_sha256"]
        or mechanisms["added_sha256"]
        or mechanisms["removed_sha256"]
        or numbers["added_sha256"]
        or numbers["removed_sha256"]
        or entities["added"]
        or entities["removed"]
        or changed_categories
    )

    return {
        "schema": SCHEMA,
        "institution": prior_doc["institution"],
        "desk_before": prior_doc["desk"],
        "desk_after": current_doc["desk"],
        "previous": _document_ref(prior),
        "current": _document_ref(now),
        "thesis": {
            "direction_before": prior_thesis["direction"],
            "direction_after": current_thesis["direction"],
            "direction_changed": direction_changed,
            "conviction_before_sha256": _normalized_hash(prior_thesis.get("conviction")),
            "conviction_after_sha256": _normalized_hash(current_thesis.get("conviction")),
            "conviction_changed": conviction_changed,
            "support_before_claim_sha256": _support_hashes(
                prior_thesis.get("support_claim_indices") or [],
                prior_claim_hashes,
            ),
            "support_after_claim_sha256": _support_hashes(
                current_thesis.get("support_claim_indices") or [],
                current_claim_hashes,
            ),
            "mechanisms": mechanisms,
        },
        "claims": {
            **claims,
            "previous_count": len(prior_claim_hashes),
            "current_count": len(current_claim_hashes),
        },
        "numbers": numbers,
        "entities": entities,
        "categories": categories,
        "changed_categories": changed_categories,
        "material_change": material_change,
        "text_visibility": "metadata_only",
        "authority": "descriptive_research_only",
    }


def summary(delta: Any) -> dict[str, Any]:
    """Project fixed-vocabulary metadata only, even for hostile external JSON."""
    if not isinstance(delta, dict) or delta.get("schema") != SCHEMA:
        raise ValueError("unexpected belief delta schema")
    if delta.get("text_visibility") != "metadata_only":
        raise ValueError("belief delta visibility is invalid")
    if delta.get("authority") != "descriptive_research_only":
        raise ValueError("belief delta authority is invalid")

    thesis = delta.get("thesis")
    claims = delta.get("claims")
    previous = delta.get("previous")
    current = delta.get("current")
    if not all(isinstance(value, dict) for value in (thesis, claims, previous, current)):
        raise ValueError("belief delta is malformed")

    allowed_directions = {"bullish", "bearish", "mixed", "neutral", "unclear"}
    before = thesis.get("direction_before")
    after = thesis.get("direction_after")
    if before not in allowed_directions or after not in allowed_directions:
        raise ValueError("belief delta direction is invalid")

    changed = delta.get("changed_categories")
    if not isinstance(changed, list) or any(
        not isinstance(field, str) or field not in _CATEGORY_FIELDS
        for field in changed
    ):
        raise ValueError("belief delta changed_categories is invalid")
    changed_categories = [field for field in _CATEGORY_FIELDS if field in changed]

    added = claims.get("added_sha256")
    removed = claims.get("removed_sha256")
    if not isinstance(added, list) or not isinstance(removed, list):
        raise ValueError("belief delta claim counts are invalid")

    institution = str(delta.get("institution") or "")
    previous_id = str(previous.get("document_id") or "")
    current_id = str(current.get("document_id") or "")
    if not institution or not previous_id or not current_id:
        raise ValueError("belief delta identity is incomplete")

    return {
        "schema": SUMMARY_SCHEMA,
        "institution_sha256": _sha256_text(institution),
        "previous_document_id_sha256": _sha256_text(previous_id),
        "current_document_id_sha256": _sha256_text(current_id),
        "direction_before": before,
        "direction_after": after,
        "direction_changed": bool(thesis.get("direction_changed")),
        "added_claims": len(added),
        "removed_claims": len(removed),
        "changed_categories": changed_categories,
        "material_change": bool(delta.get("material_change")),
        "text_visibility": "metadata_only",
        "authority": "descriptive_research_only",
    }
