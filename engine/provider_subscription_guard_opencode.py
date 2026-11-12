"""Subordinate request-time guard over existing Go offer observations.

No model admission, policy approval, entitlement, reservation or I/O is created.
Expected revisions and exclusive deadlines are supplied by their existing owners.
"""
from __future__ import annotations

from dataclasses import asdict
import re
from typing import Optional
from engine.provider_subscription_catalog_opencode import (
    Metadata, GoCatalogError, MODEL_TTL_SECONDS, TERMS_TTL_SECONDS,
    _digest, _time, _ID, _PATHS,
)


def model_offer_digest(metadata: Metadata, model_id: str) -> str:
    """Identity of one advertised offer, not permission to use the model.

    Unrelated inventory additions do not invalidate an already-reviewed model.
    Shared economic conditions still invalidate the affected interpretation.
    """
    matches = [m for m in metadata.terms.models if m.model_id == model_id]
    if len(matches) != 1 or not matches[0].rates:
        raise GoCatalogError("OFFER_TERMS_UNKNOWN")
    offer = matches[0]
    return _digest({"model_id": offer.model_id, "protocol": offer.protocol,
                    "rates": [asdict(r) for r in offer.rates],
                    "fractions": metadata.terms.horizon_fractions,
                    "conditions": metadata.terms.economic_conditions_digest})


def check_request_offer(
    metadata: Metadata, *, model_id: str, protocol: str, now: str,
    expected_offer_digest: str, expected_policy_digest: str,
    review_valid_until: str, promotion_valid_until: Optional[str] = None,
    retention_valid_until: Optional[str] = None,
) -> None:
    """Refuse stale or changed facts before a request reaches its credential edge.

    Expected digests/deadlines must come from the existing reviewed plan/policy
    owner. This predicate grants no entitlement, suitability, budget or execution
    authority. It performs no I/O, reserves nothing and never refreshes a clock.
    Deadlines are exclusive. An ambiguous promotion or conditional-retention
    cutoff requires an explicit owner deadline; none is guessed from page prose.
    This private-workload predicate never accepts training-enabled models.
    """
    at = _time(now)
    if not isinstance(model_id, str) or not _ID.fullmatch(model_id):
        raise GoCatalogError("REQUEST_MODEL_INVALID")
    if protocol not in set(_PATHS.values()):
        raise GoCatalogError("REQUEST_PROTOCOL_INVALID")
    for digest in (expected_offer_digest, expected_policy_digest):
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise GoCatalogError("REVIEWED_DIGEST_REQUIRED")
    for name, observation, ttl in (
        ("INVENTORY", metadata.inventory, MODEL_TTL_SECONDS),
        ("TERMS", metadata.terms, TERMS_TTL_SECONDS),
    ):
        age = (at - _time(observation.observed_at)).total_seconds()
        if age < 0 or age >= ttl:
            raise GoCatalogError(name + "_NOT_FRESH")
    if at >= _time(review_valid_until):
        raise GoCatalogError("OFFER_REVIEW_EXPIRED")
    if model_id not in metadata.inventory.model_ids:
        raise GoCatalogError("MODEL_NOT_LISTED")
    if model_offer_digest(metadata, model_id) != expected_offer_digest:
        raise GoCatalogError("OFFER_CHANGED_REQUOTE_REQUIRED")
    if metadata.terms.policy_digest != expected_policy_digest:
        raise GoCatalogError("DATA_POLICY_CHANGED")
    offer = next(m for m in metadata.terms.models if m.model_id == model_id)
    if offer.protocol != protocol:
        raise GoCatalogError("REQUEST_PROTOCOL_MISMATCH")
    if offer.training is not False or not offer.retention_text:
        raise GoCatalogError("PRIVATE_DATA_POLICY_UNSATISFIED")
    for required, deadline, code in (
        (any(r.promotion_note for r in offer.rates), promotion_valid_until,
         "PROMOTION_REVALIDATION_REQUIRED"),
        ("*" in offer.retention_text, retention_valid_until,
         "CONDITIONAL_RETENTION_REVALIDATION_REQUIRED"),
    ):
        if required and (deadline is None or at >= _time(deadline)):
            raise GoCatalogError(code)
