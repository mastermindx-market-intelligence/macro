"""Draft-only interchange for an admitted frontier writer, not another publisher.

The caller supplies an existing copywriter.build_context result, canonical
operation/attempt/source identities and already-authorized evidence references.
The current job owner must reconstruct current_brief from current evidence and
policy before consuming a return. Neither a digest nor a model's reference list
proves truth, rights, source independence, runtime admission or editorial merit.

No network, credential, filesystem, queue, lifecycle, approval or fallback owner
is introduced. The existing copy validator is reused, never reimplemented.
A successful result is REVIEW_REQUIRED and NEVER publication authorization.
Current production callers are not changed by this source-only first slice.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import math
from datetime import datetime, timezone
from typing import Any, Callable

SCHEMA = "marketing.frontier_writer_brief.v1"
MAX_BYTES = 131072
_IDS = ("operation_id", "attempt_id", "source_id", "source_revision", "account_id",
        "policy_revision", "persona_revision")
_BRIEF_FIELDS = set(_IDS) | {"schema", "intent", "context", "evidence_refs",
                            "media_spec_ids", "issued_at", "expires_at", "payload_sha256"}
_DRAFT_FIELDS = {"request_sha256", "decision", "headline", "body", "claims",
                 "visual_brief", "media_spec_id"}
CopyValidator = Callable[[str, str, dict[str, Any]], list[str]]


def _text(value: Any, maximum: int, *, empty: bool = False) -> str:
    if type(value) is not str or len(value) > maximum or (not empty and not value.strip()):
        raise ValueError("invalid_text")
    return value


def _json_bytes(value: Any) -> bytes:
    # Bound structure before serialization, including cycles and non-string keys.
    stack = [(value, 0)]
    count = 0
    while stack:
        node, depth = stack.pop()
        count += 1
        if depth > 16 or count > 10000:
            raise ValueError("json_structure_limit")
        if type(node) is dict:
            if len(node) > 10000:
                raise ValueError("json_structure_limit")
            if any(type(key) is not str for key in node):
                raise ValueError("non_string_key")
            stack.extend((child, depth + 1) for child in node.values())
        elif type(node) is list:
            if len(node) > 10000:
                raise ValueError("json_structure_limit")
            stack.extend((child, depth + 1) for child in node)
        elif node is None or type(node) in (str, int, bool):
            pass
        elif type(node) is float and math.isfinite(node):
            pass
        else:
            raise ValueError("non_json_value")
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise ValueError("invalid_json") from exc
    if len(raw) > MAX_BYTES:
        raise ValueError("json_byte_limit")
    return raw


def load_json(raw: str | bytes) -> dict[str, Any]:
    """Bounded external-object parser; duplicate keys and nonfinite values fail."""
    if type(raw) not in (str, bytes):
        raise ValueError("invalid_json_input")
    try:
        size = len(raw.encode("utf-8")) if isinstance(raw, str) else len(raw)
        if size > MAX_BYTES:
            raise ValueError("json_byte_limit")
        def object_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate_json_key")
                result[key] = value
            return result
        def reject_constant(_value):
            raise ValueError("nonfinite_json")
        value = json.loads(raw, object_pairs_hook=object_pairs, parse_constant=reject_constant)
        if type(value) is not dict:
            raise ValueError("json_object_required")
        _json_bytes(value)
        return value
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise ValueError("invalid_json_object") from exc


def _clone(value: Any) -> Any:
    return json.loads(_json_bytes(value))


def _refs(value: Any, *, required: bool) -> list[str]:
    if type(value) not in (list, tuple) or len(value) > 64 or (required and not value):
        raise ValueError("invalid_references")
    refs = [_text(ref, 256) for ref in value]
    if len(refs) != len(set(refs)):
        raise ValueError("duplicate_reference")
    return sorted(refs)


def _utc(value: Any) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("invalid_timestamp") from exc
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("aware_timestamp_required")
    return value.astimezone(timezone.utc)


def build_brief(*, operation_id: str, attempt_id: str, source_id: str,
                source_revision: str, account_id: str, policy_revision: str,
                persona_revision: str, context: dict[str, Any], evidence_refs: list[str],
                issued_at: datetime, expires_at: datetime,
                media_spec_ids: list[str] | tuple[str, ...] = ()) -> dict[str, Any]:
    """Seal existing context for one draft attempt. Does not grant model access.

    Rights/entitlement filtering MUST precede this call. The expiry is selected
    by the existing source policy, not by this module. Store the returned object
    only with the incumbent job/artifact owner; do not create a second queue.
    """
    identities = dict(zip(_IDS, (operation_id, attempt_id, source_id, source_revision,
                                account_id, policy_revision, persona_revision)))
    identities = {key: _text(value, 256) for key, value in identities.items()}
    if type(context) is not dict or not context:
        raise ValueError("context_required")
    if "account" in context and context["account"] != account_id:
        raise ValueError("context_account_mismatch")
    issued, expires = _utc(issued_at), _utc(expires_at)
    if issued >= expires:
        raise ValueError("invalid_validity_window")
    brief = dict(identities, schema=SCHEMA, intent="draft_only", context=_clone(context),
                 evidence_refs=_refs(evidence_refs, required=True),
                 media_spec_ids=_refs(media_spec_ids, required=False),
                 issued_at=issued.isoformat(), expires_at=expires.isoformat())
    brief["payload_sha256"] = hashlib.sha256(_json_bytes(brief)).hexdigest()
    _json_bytes(brief)
    return brief


def _check_brief(brief: Any) -> dict[str, Any]:
    if type(brief) is not dict or set(brief) != _BRIEF_FIELDS:
        raise ValueError("invalid_brief_shape")
    if brief["schema"] != SCHEMA or brief["intent"] != "draft_only":
        raise ValueError("invalid_brief_intent")
    supplied = _text(brief["payload_sha256"], 64)
    rebuilt = build_brief(**{key: brief[key] for key in _IDS}, context=brief["context"],
                          evidence_refs=brief["evidence_refs"],
                          media_spec_ids=brief["media_spec_ids"],
                          issued_at=brief["issued_at"], expires_at=brief["expires_at"])
    if not hmac.compare_digest(supplied, rebuilt["payload_sha256"]):
        raise ValueError("invalid_brief_digest")
    return rebuilt


def _outcome(status: str, reason: str | None = None, *, draft: dict | None = None,
             request_sha256: str | None = None) -> dict:
    return {"status": status, "publish_authorized": False,
            "reasons": [reason] if reason else [], "draft": draft,
            "request_sha256": request_sha256}


def evaluate_return(brief: dict[str, Any], response: Any, *, current_brief: dict[str, Any],
                    now: datetime, copy_validator: CopyValidator | None = None) -> dict[str, Any]:
    """Check a returned draft against current inputs and the canonical copy guard.

    current_brief must come from the trusted job/source owner, NOT the writer.
    Rebuild it with the original attempt/window and CURRENT source, context,
    evidence, persona and policy. Any drift invalidates this attempt's return.
    A caller-supplied validator is for explicit integration/tests; when omitted
    the actual engine.marketing.copywriter.validate_copy is imported lazily.
    Schema/reference checks do not establish semantic claim coverage or truth.
    """
    try:
        expected, current = _check_brief(brief), _check_brief(current_brief)
        clock = _utc(now)
    except (ValueError, TypeError, OverflowError):
        return _outcome("REJECTED", "invalid_brief")
    if not hmac.compare_digest(expected["payload_sha256"], current["payload_sha256"]):
        return _outcome("REJECTED", "current_inputs_changed")
    if not (_utc(expected["issued_at"]) <= clock < _utc(expected["expires_at"])):
        return _outcome("REJECTED", "expired_or_future_brief")
    try:
        response = _clone(response)
        if type(response) is not dict:
            raise ValueError("object_required")
    except (ValueError, TypeError):
        return _outcome("REJECTED", "invalid_return_shape")
    if response.get("request_sha256") != expected["payload_sha256"]:
        return _outcome("REJECTED", "return_binding_mismatch")
    if response.get("decision") == "abstain":
        try:
            if set(response) != {"request_sha256", "decision", "reason"}:
                raise ValueError("invalid_abstention")
            _text(response["reason"], 1000)
        except (ValueError, TypeError):
            return _outcome("REJECTED", "invalid_return_shape")
        # No deterministic template or cheaper model is substituted here.
        return _outcome("ABSTAINED", "writer_abstained",
                        request_sha256=expected["payload_sha256"])
    try:
        if set(response) != _DRAFT_FIELDS or response["decision"] != "draft":
            raise ValueError("invalid_draft")
        headline = _text(response["headline"], 2000, empty=True)
        body = _text(response["body"], 4000, empty=True)
        if not (headline.strip() or body.strip()):
            raise ValueError("empty_copy")
        _text(response["visual_brief"], 1600, empty=True)
    except (ValueError, TypeError):
        return _outcome("REJECTED", "invalid_return_shape")
    media_id = response["media_spec_id"]
    if media_id is not None and (type(media_id) is not str or media_id not in expected["media_spec_ids"]):
        return _outcome("REJECTED", "unknown_media_spec")
    try:
        claims = response["claims"]
        if type(claims) is not list or not 1 <= len(claims) <= 16:
            raise ValueError("claims_required")
        text = "\n\n".join(part for part in (headline, body) if part)
        for claim in claims:
            if type(claim) is not dict or set(claim) != {"statement", "kind", "evidence_refs"}:
                raise ValueError("invalid_claim")
            if _text(claim["statement"], 4000) not in text:
                raise ValueError("claim_not_in_copy")
            if claim["kind"] not in ("observation", "inference"):
                raise ValueError("invalid_claim_kind")
            if not set(_refs(claim["evidence_refs"], required=True)) <= set(expected["evidence_refs"]):
                raise ValueError("unknown_claim_reference")
    except (ValueError, TypeError):
        return _outcome("REJECTED", "invalid_claim_map")
    try:
        if copy_validator is None:
            from engine.marketing.copywriter import validate_copy
            copy_validator = validate_copy
        violations = copy_validator(headline, body, _clone(expected["context"]))
        if type(violations) is not list or any(type(item) is not str or not item for item in violations):
            raise ValueError("malformed_validator_result")
    except Exception:
        # Fixed diagnostics: provider/validator exceptions may contain secrets.
        return _outcome("REJECTED", "canonical_copy_unavailable")
    if violations:
        return _outcome("REJECTED", "canonical_copy_rejected")
    draft = {key: response[key] for key in ("headline", "body", "claims", "visual_brief", "media_spec_id")}
    return _outcome("REVIEW_REQUIRED", draft=_clone(draft),
                    request_sha256=expected["payload_sha256"])
