"""Expression commitments in the incumbent publisher, without a second store.

The full manifest lives in its existing durable transaction/sealed cache. Both
existing remote objects commit its digest in metadata; their v2/v1 JSON bodies
remain unchanged. A consumer needs the retained manifest and a verified pair.
Publication of a commitment proves neither source admission nor activation.
"""
from __future__ import annotations

import copy
import hashlib
import re
from datetime import datetime
from typing import Any

from engine.options_alpha_candidate_feed import canonical_bytes

SCHEMA = "options.alpha_expression_publication/v1"
METADATA_KEY = "oa-expression-manifest-sha256"
MAX_MANIFEST_BYTES = 16 * 1024 * 1024


class ExpressionPublicationError(ValueError):
    pass


def digest(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _clock(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ExpressionPublicationError("publication clock must be UTC Z")
    try:
        stamp = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ExpressionPublicationError("publication clock is malformed") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ExpressionPublicationError("publication clock must contain an aware time")
    return stamp


def _intent(value: object) -> dict[str, Any]:
    # Legacy publication never loads the new optional intent interface.
    from engine.options_alpha_expression_intent import validate_expression_intent
    return validate_expression_intent(value)


def _receipt_id(payload: bytes) -> str:
    return "oacfr_" + hashlib.sha256(
        b"options.alpha_candidate_feed_publication_receipt/v1|"
        + hashlib.sha256(payload).hexdigest().encode()
    ).hexdigest()[:25]


def validate_manifest(manifest: object, *, feed: dict, payload: bytes,
                      receipt_id: str, receipt_clock: str | None = None,
                      local_durability_clock: str | None = None) -> dict:
    if (not isinstance(manifest, dict)
            or set(manifest) != {"schema", "payload_sha256", "expressions"}
            or manifest["schema"] != SCHEMA
            or manifest["payload_sha256"] != hashlib.sha256(payload).hexdigest()
            or receipt_id != _receipt_id(payload)
            or not isinstance(manifest["expressions"], dict)
            or not manifest["expressions"]
            or len(canonical_bytes(manifest)) > MAX_MANIFEST_BYTES):
        raise ExpressionPublicationError("expression manifest binding invalid")
    candidates = {item["candidate_id"]: item for item in feed["formed_candidates"]}
    for eid, entry in manifest["expressions"].items():
        if (not isinstance(entry, dict) or set(entry) != {
                "intent", "first_receipt_id", "first_consumer_published_at"}):
            raise ExpressionPublicationError("expression publication entry invalid")
        intent = _intent(entry["intent"])
        if (local_durability_clock is not None
                and _clock(intent["decision_at"]) > _clock(local_durability_clock)):
            raise ExpressionPublicationError("intent decision follows durable publication input")
        candidate = candidates.get(intent["candidate_id"])
        if (eid != intent["expression_id"] or candidate is None
                or digest(candidate["frozen_formation"])
                != intent["candidate_frozen_formation_sha256"]):
            raise ExpressionPublicationError("expression disagrees with candidate formation")
        first_id = entry["first_receipt_id"]
        if not isinstance(first_id, str) or not re.fullmatch(r"oacfr_[a-f0-9]{25}", first_id):
            raise ExpressionPublicationError("expression first receipt identity invalid")
        first_clock = entry["first_consumer_published_at"]
        if first_id == receipt_id:
            if first_clock is not None:
                raise ExpressionPublicationError("current first publication clock must be external")
        else:
            clock = _clock(first_clock)
            if receipt_clock is not None and clock > _clock(receipt_clock):
                raise ExpressionPublicationError("expression first publication is in the future")
    return copy.deepcopy(manifest)


def make_manifest(*, feed: dict, payload: bytes, intents: list[dict] | None,
                  prior_manifest: dict | None, prior_receipt_id: str | None,
                  prior_receipt_clock: str | None) -> dict | None:
    entries = copy.deepcopy(prior_manifest["expressions"]) if prior_manifest else {}
    for entry in entries.values():
        if entry["first_receipt_id"] == prior_receipt_id:
            _clock(prior_receipt_clock)
            entry["first_consumer_published_at"] = prior_receipt_clock
    seen = set()
    for raw in intents or []:
        intent = _intent(raw)
        eid = intent["expression_id"]
        if eid in seen:
            raise ExpressionPublicationError("duplicate requested expression identity")
        seen.add(eid)
        if eid in entries:
            if entries[eid]["intent"] != intent:
                raise ExpressionPublicationError("published expression intent changed")
        else:
            entries[eid] = {"intent": intent, "first_receipt_id": _receipt_id(payload),
                            "first_consumer_published_at": None}
    if not entries:
        return None
    manifest = {"schema": SCHEMA, "payload_sha256": hashlib.sha256(payload).hexdigest(),
                "expressions": entries}
    return validate_manifest(manifest, feed=feed, payload=payload,
                             receipt_id=_receipt_id(payload))


def validate_transition(*, manifest: dict | None, feed: dict, payload: bytes,
                        receipt_id: str, receipt_clock: str,
                        prior_manifest: dict | None, prior_receipt_id: str | None,
                        prior_receipt_clock: str | None) -> None:
    intents = ([entry["intent"] for entry in manifest["expressions"].values()]
               if manifest else None)
    expected = make_manifest(feed=feed, payload=payload, intents=intents,
                             prior_manifest=prior_manifest,
                             prior_receipt_id=prior_receipt_id,
                             prior_receipt_clock=prior_receipt_clock)
    if manifest != expected:
        raise ExpressionPublicationError("expression publication history changed")
    if manifest is not None:
        validate_manifest(manifest, feed=feed, payload=payload,
                          receipt_id=receipt_id, receipt_clock=receipt_clock)


def resolve_intent_availability(pair: Any, expression_id: str) -> dict:
    """Resolve a retained intent against verified external first-publication data.

    ``pair`` must come from the incumbent private read_expression_pair path,
    which resolves the original retained manifest. A bare legacy pair or a
    caller-attached manifest cannot establish this consumer readback. Public
    expression dissemination and capture admission remain unavailable.
    """
    manifest = pair.expression_manifest
    result = {"schema": "options.alpha_expression_intent_availability/v1",
              "expression_id": expression_id, "status": "unavailable",
              "available_at": None, "reason": "RETAINED_EXPRESSION_MANIFEST_REQUIRED",
              "commitment_published_at": None, "intent": None,
              "intent_bytes_sha256": None,
              "consumer": "incumbent_private_publisher_owner",
              "consumer_expression_bytes_resolved": False,
              "public_consumer_available": False,
              "source_admission": "not_established_by_publication",
              "capture_eligible": False, "training_eligible": False,
              "authority": {key: False for key in (
                  "may_rank", "may_score", "may_gate", "may_size", "may_issue", "may_trade",
                  "may_publish_pick", "may_train_prophet", "may_feed_neural_web",
                  "may_compute_option_pnl", "may_activate", "may_capture_quotes")}}
    if manifest is None:
        return result
    if digest(manifest) != pair.expression_manifest_sha256:
        raise ExpressionPublicationError("retained manifest does not match publication")
    validate_manifest(manifest, feed=pair.feed, payload=pair.payload,
                      receipt_id=pair.receipt["receipt_id"],
                      receipt_clock=pair.receipt_last_modified,
                      local_durability_clock=pair.receipt["local_durability_confirmed_at"])
    entry = manifest["expressions"].get(expression_id)
    if entry is None:
        result["reason"] = "EXPRESSION_NOT_PUBLISHED"
        return result
    clock = (pair.receipt_last_modified
             if entry["first_receipt_id"] == pair.receipt["receipt_id"]
             else entry["first_consumer_published_at"])
    result["first_receipt_id"] = entry["first_receipt_id"]
    result["authority"] = copy.deepcopy(entry["intent"]["authority"])
    if not pair.expression_consumer_bytes_resolved:
        result["reason"] = "ORIGINAL_CONSUMER_EXPRESSION_BYTES_UNRESOLVED"
        return result
    if _clock(clock) < _clock(entry["intent"]["decision_at"]):
        result["reason"] = "EXTERNAL_PUBLICATION_CLOCK_PRECEDES_INTENT"
        return result
    result.update(status="available", available_at=clock, commitment_published_at=clock,
                  intent=copy.deepcopy(entry["intent"]),
                  intent_bytes_sha256=digest(entry["intent"]),
                  consumer_expression_bytes_resolved=True, reason=None)
    return result
