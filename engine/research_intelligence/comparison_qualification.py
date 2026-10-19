"""Private companion adjudications; frozen RIO/extraction receipts are unchanged.

The injected authority is an existing trusted server owner, not client JSON. It
must authenticate the author on writes and verify admission of the exact record
on reads. Strings, hashes, literal grounding and this module's shape checks do
not authenticate an adjudication. No authority means no qualified comparison.
One source-pair pointer uses the incumbent immutable/strict-CAS Store lifecycle;
revocation publishes a new immutable decision, never edits an old decision.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import re
from typing import Any, Callable

from engine.research_intelligence.store import (
    ROOT_PREFIX, _canonical_json_bytes, _decode_json_object,
    _ensure_immutable_artifact, ResearchIntelligenceConflict,
    ResearchIntelligenceEffectUnknown,
)
from engine.research_vault.r2_store import StrictConditionalWriteStore, VersionedBytes

SCHEMA = "mastermind.research_intelligence.comparison_qualification.v1"
POINTER_SCHEMA = SCHEMA + ".pointer"
PREFIX = ROOT_PREFIX + "/comparison_qualifications"
MAX_BYTES = 32 * 1024
_SHA = re.compile(r"[a-f0-9]{64}\Z")
_AXES = {"subject", "horizon", "units", "currency", "scenario"}
_BINDING = {"report_id", "source_pdf_sha256", "extracted_text_sha256", "rio_artifact_sha256", "claim_index"}


@dataclass(frozen=True)
class QualificationAuthority:
    """Only the composition root supplies these authenticated admission owners.

    authorize_write(actor, proposal) returns the authenticated adjudicator ID,
    or None. authorize_read(caller, exact_record, content_ref) verifies current
    admission (including author provenance/revocation), returning literal True.
    Neither callback may trust an author/status string alone.
    """
    authorize_write: Callable[[Any, dict], str | None]
    authorize_read: Callable[[Any, dict, str], bool]


def _text(value, limit=500):
    if type(value) is not str or not value.strip() or len(value) > limit:
        raise ValueError("qualification text invalid")
    return value


def _hash(value):
    if type(value) is not str or _SHA.fullmatch(value) is None:
        raise ValueError("qualification digest invalid")
    return value


def _date(value):
    from engine.research_vault.catalog import parse_generated_at
    _text(value, 50)
    parse_generated_at(value)
    return value


def validate_record(value):
    """Closed descriptive contract; validation is never admission/authentication."""
    if type(value) is not dict or set(value) != {"schema", "state", "legs", "bases", "subjects", "families", "revision", "review"}:
        raise ValueError("qualification fields invalid")
    obj = deepcopy(value)
    if obj["schema"] != SCHEMA or obj["state"] not in {"QUALIFIED", "REVOKED"}:
        raise ValueError("qualification state invalid")
    for name in ("legs", "bases", "subjects", "families"):
        if type(obj[name]) is not list or len(obj[name]) != 2:
            raise ValueError("qualification pair invalid")
    for leg, basis, subject, family in zip(obj["legs"], obj["bases"], obj["subjects"], obj["families"]):
        if type(leg) is not dict or set(leg) != _BINDING | {"published_at"}:
            raise ValueError("qualification leg invalid")
        _text(leg["report_id"], 240); _date(leg["published_at"])
        for name in _BINDING - {"report_id", "claim_index"}:
            _hash(leg[name])
        if type(leg["claim_index"]) is not int or not 0 <= leg["claim_index"] < 30:
            raise ValueError("qualification claim index invalid")
        if type(basis) is not dict or set(basis) != _AXES:
            raise ValueError("explicit five-axis basis required")
        for val in basis.values(): _text(val, 300)
        if type(subject) is not dict:
            raise ValueError("qualification subject invalid")
        if subject.get("kind") == "source_topic":
            if set(subject) != {"kind", "subject", "provenance"} or subject["subject"] != basis["subject"]:
                raise ValueError("topic subject mismatch")
        elif subject.get("kind") == "historical_security":
            from lib.dataos.identity import parse_id
            if set(subject) != {"kind", "security_id", "alias_vendor", "resolution_state", "resolution_date", "decision_at", "provenance"}:
                raise ValueError("historical subject fields invalid")
            if (parse_id(subject["security_id"])[0] != "security" or basis["subject"] != subject["security_id"]
                    or subject["alias_vendor"] in {"", "store", "yahoo_fetch"}
                    or subject["resolution_state"] != "RESOLVED"
                    or subject["resolution_date"] != leg["published_at"][:10]):
                raise ValueError("historical identity unresolved")
            _text(subject["alias_vendor"], 200); _date(subject["decision_at"])
        else:
            raise ValueError("qualification subject kind invalid")
        _text(subject["provenance"], 1000)
        if type(family) is not str or len(family) > 200:
            raise ValueError("qualification family invalid")
    review = obj["review"]
    if type(review) is not dict or set(review) != {"adjudicator_id", "assessed_at", "method", "provenance"}:
        raise ValueError("qualification review invalid")
    _text(review["adjudicator_id"], 200); _date(review["assessed_at"])
    _text(review["method"], 200); _text(review["provenance"], 2000)
    revision = obj["revision"]
    if revision is not None:
        if (type(revision) is not dict or set(revision) != {"kind", "support_quote", "provenance"}
                or revision["kind"] not in {"CHANGED_VIEW", "CORRECTED_FACTUAL_ERROR"}):
            raise ValueError("qualification revision invalid")
        _text(revision["support_quote"], 1600); _text(revision["provenance"], 1000)
        # Literal support/chronology/family are additionally checked against the
        # actual source bodies by comparison before either leg is exposed.
    if len(_canonical_json_bytes(obj)) > MAX_BYTES:
        raise ValueError("qualification exceeds byte budget")
    return obj


def source_pair(legs):
    if type(legs) not in (list, tuple) or len(legs) != 2:
        raise ValueError("ordered source pair required")
    keys = ("report_id", "source_pdf_sha256", "extracted_text_sha256", "rio_artifact_sha256", "published_at")
    return [{k: leg[k] for k in keys} for leg in legs]


def pair_key(legs):
    return PREFIX + "/pairs/" + hashlib.sha256(_canonical_json_bytes(source_pair(legs))).hexdigest() + ".json"


def object_key(ref):
    return PREFIX + "/objects/" + _hash(ref) + ".json"


def _pointer(data, key):
    if type(data) is not bytes or len(data) > MAX_BYTES:
        raise ValueError("qualification pointer byte boundary violated")
    obj = _decode_json_object(data, code="comparison_pointer_invalid", label="comparison pointer")
    if set(obj) != {"schema", "key", "ref"} or obj["schema"] != POINTER_SCHEMA or obj["key"] != key:
        raise ValueError("qualification pointer mismatch")
    _hash(obj["ref"])
    return obj


def publish_qualification(store, proposal, *, actor, authority, expected_ref=None):
    """Trusted authoring seam. No client route/factory calls this writer.

    The actual authority authenticates actor and approves the exact proposal;
    proposed review JSON must omit adjudicator_id. The authenticated principal
    is derived from the callback, never copied from a client field.
    """
    if not isinstance(store, StrictConditionalWriteStore) or type(authority) is not QualificationAuthority:
        raise ValueError("trusted conditional writer and authority required")
    proposal = deepcopy(proposal)
    if (type(proposal) is not dict or type(proposal.get("review")) is not dict
            or set(proposal["review"]) != {"assessed_at", "method", "provenance"}):
        raise ValueError("author must come from authenticated context")
    principal = authority.authorize_write(actor, deepcopy(proposal))
    _text(principal, 200)
    proposal["review"]["adjudicator_id"] = principal
    record = validate_record(proposal)
    store.validate_strict_conditional_write_capability()
    raw = _canonical_json_bytes(record); ref = hashlib.sha256(raw).hexdigest()
    key = pair_key(record["legs"])
    observed = store.get_bytes_strict_bounded_versioned(key, MAX_BYTES)
    if type(observed) is not VersionedBytes or (observed.data is None) != (observed.version is None):
        raise ValueError("qualification pointer version invalid")
    current = None if observed.data is None else _pointer(observed.data, key)["ref"]
    if expected_ref is not None: _hash(expected_ref)
    if current != expected_ref:
        raise ResearchIntelligenceConflict("comparison_predecessor_changed", "comparison qualification predecessor changed")
    _ensure_immutable_artifact(store, key=object_key(ref), payload=raw)
    pointer = _canonical_json_bytes({"schema": POINTER_SCHEMA, "key": key, "ref": ref})
    cause = None
    try:
        written = store.put_bytes_strict_conditional(key, pointer, expected_version=observed.version, content_type="application/json")
    except Exception as exc:
        cause = exc; written = None
    # Same-carrier readback, never blind replay of a timed-out CAS.
    try:
        final = store.get_bytes_strict_bounded_versioned(key, MAX_BYTES)
    except Exception as exc:
        raise ResearchIntelligenceEffectUnknown("comparison_effect_unknown", "qualification CAS outcome unknown", write_error=cause or exc) from exc
    if type(final) is VersionedBytes and final.data == pointer:
        return ref
    if cause is not None or written not in (True, False):
        raise ResearchIntelligenceEffectUnknown("comparison_effect_unknown", "qualification CAS outcome unknown", write_error=cause or RuntimeError("invalid CAS result"))
    raise ResearchIntelligenceConflict("comparison_pointer_changed", "qualification pointer changed")


def load_qualification(store, legs, *, caller, authority, expected_ref=None):
    """Bounded private read, no write/list/credential mutation capability needed."""
    if type(authority) is not QualificationAuthority or not callable(authority.authorize_read):
        return None
    key = pair_key(legs)
    raw_pointer = store.get_bytes_strict_bounded(key, MAX_BYTES)
    if raw_pointer is None: return None
    if type(raw_pointer) is not bytes or len(raw_pointer) > MAX_BYTES:
        raise ValueError("qualification pointer byte boundary violated")
    ref = _pointer(raw_pointer, key)["ref"]
    if expected_ref is not None and ref != expected_ref: return None
    raw = store.get_bytes_strict_bounded(object_key(ref), MAX_BYTES)
    if type(raw) is not bytes or len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != ref:
        raise ValueError("qualification artifact mismatch")
    record = validate_record(_decode_json_object(raw, code="comparison_record_invalid", label="comparison qualification"))
    if source_pair(record["legs"]) != source_pair(legs) or record["state"] != "QUALIFIED": return None
    if authority.authorize_read(caller, deepcopy(record), ref) is not True: return None
    # Admission may itself perform IO: re-admit the current pointer afterwards.
    if store.get_bytes_strict_bounded(key, MAX_BYTES) != raw_pointer: return None
    return ref, record
