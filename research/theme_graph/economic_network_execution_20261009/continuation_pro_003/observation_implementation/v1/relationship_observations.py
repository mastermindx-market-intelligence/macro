"""Private, immutable C01 evidence observations on an injected Research Vault store.

This module neither constructs a store nor acquires sources.  Its two public
operations require the incumbent conditional-write surface and its exact-length
keyword read mode.  A verified hash/binding is not producer/reviewer
authentication, independent commerce, purpose permission, or native admission.
The v1 review-binding contract is specific to the six-case pilot's C01 artifact
shapes and planned H200 integration; it is not arbitrary-case semantic validation.
"""
from __future__ import annotations

from hashlib import sha256
import json
import math
import re
from typing import Any, TYPE_CHECKING

from engine.company_intelligence.relationship_candidates import inspect_candidate

if TYPE_CHECKING:
    from engine.research_vault.r2_store import StrictConditionalWriteStore

__all__ = ["append_relationship_observation", "read_relationship_observation"]

PACKAGE_SCHEMA = "company_intelligence.relationship_observation_package/v1"
MANIFEST_SCHEMA = "company_intelligence.relationship_observation_manifest/v1"
REFERENCE_SCHEMA = "company_intelligence.relationship_observation_reference/v1"
RESULT_SCHEMA = "company_intelligence.relationship_observation_result/v1"
PRODUCER_CONTRACT = "c01_private_observation/v1"
PURPOSE = "private_current_inspection"
PREFIX = "company_intelligence/relationship_observations/v1/"
CHUNK_BYTES = 16 * 1024
MAX_MANIFEST_BYTES = 16 * 1024
MAX_PACKAGE_BYTES = 1024 * 1024
MAX_CHUNKS = 64
MAX_CANDIDATE_BYTES = 256 * 1024
MAX_REVIEW_BYTES = 64 * 1024
MAX_INSPECTION_BYTES = 512 * 1024
MAX_DEPTH = 16
MAX_NODES = 8192
MAX_SCALAR_CHARACTERS = 64 * 1024
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_ROLES = (
    "candidate", "source", "source_record", "pilot_adjudications",
    "semantic_review", "retained_first_review", "retained_independent_review",
)
_PACKAGE_KEYS = frozenset({
    "schema", "producer_contract", "review_set_id", "case_id", "components",
    "canonical_candidate_payload_sha256", "inspection_request", "inspection",
    "review_binding", "prior_observation", "purpose_scope", "admission",
    "authority", "graph1_projection", "content_boundary",
})
_MANIFEST_KEYS = frozenset({
    "schema", "producer_contract", "package_sha256", "package_byte_length", "chunks",
})
_REFERENCE_KEYS = frozenset({"schema", "sha256", "byte_length"})
_COMPONENT_KEYS = frozenset({"sha256", "byte_length", "encoding", "text"})


class _Refusal(Exception):
    def __init__(self, code: str, *, inspection: dict | None = None,
                 effect_unknown: bool = False) -> None:
        self.code = code
        self.inspection = inspection
        self.effect_unknown = effect_unknown


def _require(condition: bool, code: str = "INPUT_SHAPE_INVALID") -> None:
    if not condition:
        raise _Refusal(code)


def _closed(value: Any, keys: frozenset[str]) -> None:
    _require(type(value) is dict and len(value) == len(keys))
    _require(set(value) == keys)


def _digest(value: Any) -> None:
    _require(type(value) is str and _DIGEST.fullmatch(value) is not None)


def _identifier(value: Any) -> None:
    _require(type(value) is str and _ID.fullmatch(value) is not None)


def _tree(value: Any, *, package: bool = False) -> None:
    """Bound parsed JSON, not arbitrary executable Python caller objects."""
    remaining = MAX_NODES + (256 if package else 0)
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        remaining -= 1
        _require(remaining >= 0 and depth <= MAX_DEPTH + (8 if package else 0),
                 "INPUT_LIMIT")
        if item is None or type(item) is bool:
            continue
        if type(item) is str:
            _require(len(item) <= (MAX_PACKAGE_BYTES if package else MAX_SCALAR_CHARACTERS),
                     "INPUT_LIMIT")
            try:
                item.encode("utf-8")
            except UnicodeError:
                raise _Refusal("INPUT_UNICODE_INVALID") from None
        elif type(item) is int:
            _require(item.bit_length() <= 64, "INPUT_LIMIT")
        elif type(item) is float:
            _require(math.isfinite(item), "INPUT_JSON_INVALID")
        elif type(item) is list:
            _require(len(item) <= remaining, "INPUT_LIMIT")
            stack.extend((child, depth + 1) for child in item)
        elif type(item) is dict:
            _require(len(item) * 2 <= remaining, "INPUT_LIMIT")
            for key, child in item.items():
                _require(type(key) is str)
                stack.extend(((key, depth + 1), (child, depth + 1)))
        else:
            raise _Refusal("INPUT_SHAPE_INVALID")


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        _require(key not in result, "JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _no_constant(_: str) -> Any:
    raise _Refusal("INPUT_JSON_INVALID")


def _utf8(raw: Any, limit: int) -> str:
    _require(type(raw) is bytes)
    _require(0 < len(raw) <= limit, "INPUT_LIMIT")
    try:
        text = raw.decode("utf-8")
    except UnicodeError:
        raise _Refusal("INPUT_UNICODE_INVALID") from None
    _require(text.encode("utf-8") == raw, "INPUT_UNICODE_INVALID")
    return text


def _parse(raw: bytes, limit: int, *, package: bool = False) -> Any:
    text = _utf8(raw, limit)
    try:
        result = json.loads(text, object_pairs_hook=_no_duplicates,
                            parse_constant=_no_constant)
    except (ValueError, TypeError, RecursionError, OverflowError):
        raise _Refusal("INPUT_JSON_INVALID") from None
    _tree(result, package=package)
    return result


def _canonical(value: Any, limit: int) -> bytes:
    """Measure escaped UTF-8 JSON before allocating its complete serialization.

    The large source string is counted character by character with early exit;
    neither one huge escaped scalar nor repeated references bypass the cap.
    These values are parsed JSON or module-created envelopes, not caller code.
    """
    remaining = limit

    def use(count: int) -> None:
        nonlocal remaining
        remaining -= count
        _require(remaining >= 0, "SERIALIZED_PACKAGE_LIMIT")

    def string(text: str) -> None:
        use(2)
        for char in text:
            point = ord(char)
            if char in '\\"\b\f\n\r\t':
                use(2)
            elif point < 32:
                use(6)
            elif point < 128:
                use(1)
            elif point < 2048:
                use(2)
            elif 0xD800 <= point <= 0xDFFF:
                raise _Refusal("INPUT_UNICODE_INVALID")
            else:
                use(3 if point < 65536 else 4)

    def measure(item: Any, depth: int = 0) -> None:
        _require(depth <= MAX_DEPTH + 8, "INPUT_LIMIT")
        if item is None:
            use(4)
        elif type(item) is bool:
            use(4 if item else 5)
        elif type(item) is str:
            string(item)
        elif type(item) in (int, float):
            use(len(json.dumps(item, allow_nan=False)))
        elif type(item) is list:
            use(2 + max(0, len(item) - 1))
            for child in item:
                measure(child, depth + 1)
        elif type(item) is dict:
            use(2 + max(0, len(item) - 1))
            for key, child in item.items():
                _require(type(key) is str)
                string(key)
                use(1)
                measure(child, depth + 1)
        else:
            raise _Refusal("INPUT_SHAPE_INVALID")

    try:
        measure(value)
        result = json.dumps(value, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (ValueError, TypeError, RecursionError, OverflowError, UnicodeError):
        raise _Refusal("INPUT_JSON_INVALID") from None
    _require(len(result) == limit - remaining and len(result) <= limit,
             "SERIALIZED_PACKAGE_LIMIT")
    return result


def _authority() -> dict:
    return {key: False for key in ("rank", "gate", "size", "trade", "prediction")}


def _purpose() -> dict:
    return {"operation": PURPOSE, "source_purpose_permission": "NOT_ESTABLISHED",
            "production": False, "public_export": False, "training": False}


def _content_boundary() -> dict:
    return {"private_evidence": True, "source_text_may_be_present": True,
            "quote_free_payload": "NOT_CERTIFIED", "public_safe_payload": "NOT_CERTIFIED"}


def _reference(value: Any) -> dict:
    _closed(value, _REFERENCE_KEYS)
    _require(value["schema"] == REFERENCE_SCHEMA, "REFERENCE_INVALID")
    _digest(value["sha256"])
    _require(type(value["byte_length"]) is int
             and 0 < value["byte_length"] <= MAX_MANIFEST_BYTES, "REFERENCE_INVALID")
    return dict(value)


def _prior(value: Any) -> dict | None:
    if value is None:
        return None
    _closed(value, frozenset({"reference", "relation"}))
    _require(type(value["relation"]) is str
             and value["relation"] in {"corrects", "contradicts", "adds_review"})
    return {"reference": _reference(value["reference"]), "relation": value["relation"]}


def _component(raw: bytes, limit: int) -> dict:
    text = _utf8(raw, limit)
    return {"sha256": sha256(raw).hexdigest(), "byte_length": len(raw),
            "encoding": "utf-8", "text": text}


def _assert_equal(actual: Any, expected: Any, code: str = "REVIEW_BINDING_MISMATCH") -> None:
    _require(type(actual) is type(expected) and actual == expected, code)


def _lookup(value: Any, *path: str) -> Any:
    for key in path:
        _require(type(value) is dict and key in value, "REVIEW_BINDING_MISMATCH")
        value = value[key]
    return value


def _context_bounds(context: dict, source: str, receipt: dict, *, first: bool) -> dict:
    names = ("character_start", "character_end") if first else ("char_start", "char_end")
    start, end = (_lookup(context, name) for name in names)
    _require(type(start) is int and type(end) is int
             and 0 <= start <= receipt["char_start"] < receipt["char_end"] <= end <= len(source),
             "REVIEW_CONTEXT_MISMATCH")
    raw = source[start:end].encode("utf-8")
    result = {"character_start": start, "character_end": end,
              "byte_start": len(source[:start].encode("utf-8")),
              "byte_end": len(source[:end].encode("utf-8")),
              "byte_length": len(raw), "sha256": sha256(raw).hexdigest()}
    if first:
        for old, new in (("byte_start", "byte_start"), ("byte_end", "byte_end"),
                         ("bytes", "byte_length"), ("sha256", "sha256")):
            _assert_equal(_lookup(context, old), result[new], "REVIEW_CONTEXT_MISMATCH")
        _assert_equal(_lookup(context, "characters"), end - start, "REVIEW_CONTEXT_MISMATCH")
    return result


def _review_bindings(candidate: dict, source: str, components: dict,
                     *, case_id: str) -> tuple[dict, dict]:
    metadata = _parse(components["source_record"]["text"].encode("utf-8"), MAX_REVIEW_BYTES)
    lines = components["pilot_adjudications"]["text"].splitlines()
    _require(len(lines) == 6 and all(lines), "PILOT_CARDINALITY_INVALID")
    pilot_rows = [_parse(line.encode("utf-8"), MAX_REVIEW_BYTES) for line in lines]
    _require(all(type(row) is dict for row in pilot_rows), "PILOT_CARDINALITY_INVALID")
    ids = [row.get("case_id") for row in pilot_rows]
    _require(ids == ["C01", "C02", "C03", "C04", "C05", "C06"], "PILOT_CARDINALITY_INVALID")
    pilot = pilot_rows[0]
    web = _parse(components["semantic_review"]["text"].encode("utf-8"), MAX_REVIEW_BYTES)
    first = _parse(components["retained_first_review"]["text"].encode("utf-8"), MAX_REVIEW_BYTES)
    independent = _parse(components["retained_independent_review"]["text"].encode("utf-8"), MAX_REVIEW_BYTES)
    for item, schema in (
        (pilot, "gmi.native_adoption_pilot_case_adjudication/v1"),
        (web, "research.independent_semantic_judgments/v1"),
        (first, "gmi.retained_micron_first_reader_judgment/v1"),
        (independent, "research.retained_byte_semantic_judgment/v1"),
    ):
        _assert_equal(_lookup(item, "schema"), schema)
    web_rows = _lookup(web, "rows")
    _require(type(web_rows) is list and len(web_rows) == 6
             and all(type(row) is dict for row in web_rows), "REVIEW_CARDINALITY_INVALID")
    _require([row.get("case_id") for row in web_rows] == ids, "REVIEW_CARDINALITY_INVALID")
    web_case = web_rows[0]
    for item in (pilot, first, independent, web_case):
        _assert_equal(_lookup(item, "case_id"), case_id)
    for item, field in ((pilot, "native_admission"), (web, "admission"),
                        (independent, "native_admission")):
        _assert_equal(_lookup(item, field), "NOT_ADMITTED", "REVIEW_AUTHORITY_UNSUPPORTED")
        _assert_equal(_lookup(item, "authority"), _authority(), "REVIEW_AUTHORITY_UNSUPPORTED")
        _assert_equal(_lookup(item, "graph1_projection"), None, "REVIEW_AUTHORITY_UNSUPPORTED")
    first_limits = _lookup(first, "limits")
    _assert_equal(_lookup(first_limits, "native_production_admission"), "NOT_ADMITTED",
                  "REVIEW_AUTHORITY_UNSUPPORTED")
    _assert_equal(_lookup(first_limits, "graph1_projection"), None, "REVIEW_AUTHORITY_UNSUPPORTED")
    for key in _authority():
        _assert_equal(_lookup(first_limits, key), False, "REVIEW_AUTHORITY_UNSUPPORTED")
    for key in ("authenticated_actor_or_source_custody", "historical_system_replay",
                "production_rights_admitted", "public_export_rights_admitted", "training_rights_admitted"):
        _assert_equal(_lookup(first_limits, key), False, "REVIEW_AUTHORITY_UNSUPPORTED")
    _assert_equal(_lookup(first_limits, "source_purpose_permission_receipt"), None,
                  "REVIEW_AUTHORITY_UNSUPPORTED")
    for key in ("source_publisher_authenticated_by_this_read", "source_custody_authenticated",
                "independent_commerce_verified"):
        _assert_equal(_lookup(independent, "limitations", key), False,
                      "REVIEW_AUTHORITY_UNSUPPORTED")
    for key in ("production_rights_receipt", "public_export_rights_receipt", "training_rights_receipt"):
        _assert_equal(_lookup(independent, "limitations", key), None, "REVIEW_AUTHORITY_UNSUPPORTED")

    doc, span, assertion = candidate["document"], candidate["receipt"], candidate["assertion"]
    source_digest, source_length = components["source"]["sha256"], components["source"]["byte_length"]
    for key, expected in {
        "raw_sha256": source_digest, "source_bytes": source_length,
        "candidate_id": candidate["candidate_id"], "document_id": doc["document_id"],
        "source_url": doc["source_ref"], "published_date": doc["published_date"],
        "published_instant": None, "native_dataset_id": None,
        "canonical_identity_admission": False, "historical_system_replay": False,
        "source_purpose_rights_admitted": False, "assertion": assertion,
        "source_kind": "original_issuer_announcement", "source_encoding": "UTF-8 exact round-trip",
    }.items():
        _assert_equal(_lookup(metadata, key), expected, "SOURCE_RECORD_MISMATCH")
    for key in ("char_start", "char_end", "byte_start", "byte_end", "span_sha256"):
        _assert_equal(_lookup(metadata, key), span[key], "SOURCE_RECORD_MISMATCH")
    _assert_equal(_lookup(first, "original_case_id"), _lookup(metadata, "case_id"))
    _assert_equal(_lookup(pilot, "source_url"), doc["source_ref"])
    for key, expected in {
        "metadata_file_sha256": components["source_record"]["sha256"],
        "raw_sha256": source_digest, "source_bytes": source_length,
        "candidate_id": candidate["candidate_id"], "document_id": doc["document_id"],
    }.items():
        _assert_equal(_lookup(pilot, "source_binding", key), expected)
    _assert_equal(_lookup(pilot, "independent_review", "receipt", "sha256"),
                  components["semantic_review"]["sha256"])
    _assert_equal(_lookup(web_case, "primary_url"), doc["source_ref"])
    _assert_equal(_lookup(web_case, "source_representation_observed"),
                  "WEB_RENDERED_HTML_WITH_SEPARATE_RETAINED_INPUT_PROVENANCE")

    for key, expected in {
        "source_sha256": source_digest, "source_bytes": source_length,
        "candidate_sha256": components["candidate"]["sha256"],
        "candidate_bytes": components["candidate"]["byte_length"],
        "metadata_sha256": components["source_record"]["sha256"],
        "metadata_bytes": components["source_record"]["byte_length"],
    }.items():
        _assert_equal(_lookup(first, "source_binding", key), expected)
    for section, role in (("original_source", "source"), ("original_candidate", "candidate")):
        _assert_equal(_lookup(independent, section, "sha256"), components[role]["sha256"])
        _assert_equal(_lookup(independent, section, "bytes"), components[role]["byte_length"])
    _assert_equal(_lookup(first, "candidate_reference", "candidate_id"), candidate["candidate_id"])
    _assert_equal(_lookup(first, "candidate_reference", "document_id"), doc["document_id"])
    _assert_equal(_lookup(independent, "original_candidate", "candidate_id"), candidate["candidate_id"])
    for old, new in (("character_start", "char_start"), ("character_end", "char_end"),
                     ("byte_start", "byte_start"), ("byte_end", "byte_end"),
                     ("sha256", "span_sha256"), ("bytes", "span_bytes")):
        _assert_equal(_lookup(first, "source_binding", "span", old), span[new])
    for key in ("char_start", "char_end", "byte_start", "byte_end", "span_sha256", "span_bytes"):
        lookup = "sha256" if key == "span_sha256" else key
        _assert_equal(_lookup(independent, "source_span", lookup), span[key])

    semantic, principal = _lookup(first, "semantic_findings"), _lookup(independent, "finding")
    _assert_equal(_lookup(first, "new_evidence_basis"), "ACTUAL_RETAINED_UTF8_BYTES_AND_BOUND_CANDIDATE_READ")
    _assert_equal(_lookup(first, "judgment"), "SUPPORTED_WITH_MANDATORY_SCOPE_QUALIFIERS")
    _assert_equal(_lookup(principal, "status"), "SUPPORTED_WITH_REQUIRED_QUALIFIERS")
    for key, expected in {
        "candidate_kind_fit": assertion["kind"], "candidate_lifecycle_fit": assertion["lifecycle"],
        "source_local_subject": assertion["subject_label"], "source_local_object": assertion["object_label"],
        "upstream_configuration": assertion["product_scope"], "document_date": doc["published_date"],
        "published_instant": None, "canonical_subject_id": None, "canonical_object_id": None,
        "publication_precision": "DATE", "current_supply_state": "UNESTABLISHED",
        "independently_verified_commerce": False,
        "economics": {"quantity": None, "revenue_share": None, "purchase_amount": None,
                      "customer_allocation": None, "exclusivity": None},
    }.items():
        _assert_equal(_lookup(semantic, key), expected, "REVIEW_SUBJECT_MISMATCH")
    for key, expected in {
        "kind": assertion["kind"], "lifecycle": assertion["lifecycle"],
        "subject_label": assertion["subject_label"], "object_label": assertion["object_label"],
        "component_scope": assertion["product_scope"], "publication_date": doc["published_date"],
        "publication_instant": None, "magnitude": None,
    }.items():
        _assert_equal(_lookup(principal, key), expected, "REVIEW_SUBJECT_MISMATCH")
    target, principal_target = _lookup(semantic, "downstream_configuration"), _lookup(principal, "target_scope")
    _require(type(target) is str and 0 < len(target) <= 512
             and type(principal_target) is str and 0 < len(principal_target) <= 512,
             "REVIEW_SCOPE_MISMATCH")
    _require(target == assertion["object_label"] + " H200 Tensor Core GPUs"
             and target in span["value_text"]
             and principal_target in {target, "H200 Tensor Core GPUs"},
             "REVIEW_SCOPE_MISMATCH")
    _assert_equal(_lookup(pilot, "source_local_parties"),
                  [assertion["subject_label"], assertion["object_label"]], "REVIEW_SUBJECT_MISMATCH")
    _assert_equal(_lookup(pilot, "scope", "kind"), assertion["kind"], "REVIEW_SCOPE_MISMATCH")
    _assert_equal(_lookup(pilot, "scope", "lifecycle"), assertion["lifecycle"], "REVIEW_SCOPE_MISMATCH")
    _assert_equal(_lookup(web_case, "native_kind"), assertion["kind"], "REVIEW_SCOPE_MISMATCH")
    _assert_equal(_lookup(web_case, "lifecycle"), assertion["lifecycle"], "REVIEW_SCOPE_MISMATCH")

    first_context = _context_bounds(_lookup(first, "source_binding", "context"), source, span, first=True)
    principal_context = _context_bounds(_lookup(independent, "inspected_context"), source, span, first=False)
    binding = {
        "status": "SUPPLIED_CONTENT_BINDINGS_MATCH",
        "authorship": "NOT_AUTHENTICATED", "review_independence": "NOT_AUTHENTICATED",
        "source_custody": "NOT_AUTHENTICATED", "semantic_truth": "NOT_AUTHENTICATED",
        "web_review_representation": "WEB_RENDERED_HTML_WITH_SEPARATE_RETAINED_INPUT_PROVENANCE",
        "retained_review_representation": "SUPPLIED_REVIEW_CLAIMS_EXACT_RETAINED_BYTES",
        "scope_summary": {"component": assertion["product_scope"], "target": target,
                          "lifecycle": assertion["lifecycle"], "source_local_only": True},
        "review_sha256": {role: components[role]["sha256"] for role in _ROLES[3:]},
        "reviewed_contexts": {"first": first_context, "independent": principal_context},
        "context_digest_basis": "derived_from_supplied_source_at_supplied_review_intervals",
        "external_receipts": "references_retained_as_claims_not_independently_loaded",
    }
    visible = {"binding": binding, "pilot_case": pilot, "web_review_case": web_case,
               "retained_first_review": first, "retained_independent_review": independent}
    return binding, visible


def _prepare(*, review_set_id: str, case_id: str, inputs: dict[str, bytes],
             prior_observation: Any, registry: Any,
             _inspection: dict | None = None) -> tuple[dict, dict]:
    _identifier(review_set_id)
    _require(case_id == "C01" and type(case_id) is str, "CASE_SCOPE_UNSUPPORTED")
    prior = _prior(prior_observation)
    _require(type(inputs) is dict and len(inputs) == len(_ROLES) and set(inputs) == set(_ROLES))
    _require(all(type(raw) is bytes for raw in inputs.values()))
    _require(sum(len(raw) for raw in inputs.values()) <= MAX_PACKAGE_BYTES, "INPUT_LIMIT")
    components = {
        role: _component(inputs[role], MAX_CANDIDATE_BYTES if role == "candidate"
                         else MAX_PACKAGE_BYTES if role == "source" else MAX_REVIEW_BYTES)
        for role in _ROLES
    }
    candidate = _parse(inputs["candidate"], MAX_CANDIDATE_BYTES)
    source = components["source"]["text"]
    inspection = (_inspect(candidate, source, as_of=None, registry=registry,
                           include_support_text=False) if _inspection is None else _inspection)
    _canonical(inspection, MAX_INSPECTION_BYTES)
    if inspection.get("inspection_status") != "INSPECTABLE":
        raise _Refusal("INSPECTION_REFUSED", inspection=inspection)
    try:
        _require(candidate["assertion"]["kind"] == "product_integration"
                 and candidate["assertion"]["lifecycle"] == "planned"
                 and candidate["dataset_id"] is None and candidate["temporal_row"] is None
                 and candidate["identity_annotations"] is None, "CANDIDATE_SCOPE_UNSUPPORTED")
        _require(inspection["admission"] == "NOT_ADMITTED"
                 and inspection["authority"] == _authority() and inspection["graph1_projection"] is None,
                 "INSPECTOR_BOUNDARY_CHANGED")
        binding, visible = _review_bindings(candidate, source, components, case_id=case_id)
        canonical_candidate_digest = sha256(_canonical(candidate, MAX_CANDIDATE_BYTES)).hexdigest()
    except _Refusal as error:
        error.inspection = inspection
        raise
    package = {
        "schema": PACKAGE_SCHEMA, "producer_contract": PRODUCER_CONTRACT,
        "review_set_id": review_set_id, "case_id": case_id, "components": components,
        "canonical_candidate_payload_sha256": canonical_candidate_digest,
        "inspection_request": {"as_of": None, "include_support_text": False,
                               "registry_supplied": registry is not None},
        "inspection": inspection, "review_binding": binding,
        "prior_observation": prior, "purpose_scope": _purpose(),
        "admission": "NOT_ADMITTED", "authority": _authority(), "graph1_projection": None,
        "content_boundary": _content_boundary(),
    }
    return package, visible


def _inspect(candidate: Any, source: str, *, as_of: Any, registry: Any,
             include_support_text: Any) -> dict:
    try:
        result = inspect_candidate(candidate, source=source, as_of=as_of,
                                   registry=registry, include_support_text=include_support_text)
    except Exception:
        raise _Refusal("INSPECTOR_FAILED") from None
    _require(type(result) is dict, "INSPECTOR_RESULT_INVALID")
    _require(result.get("admission") == "NOT_ADMITTED"
             and result.get("authority") == _authority() and result.get("graph1_projection") is None,
             "INSPECTOR_BOUNDARY_CHANGED")
    return result


def _result(operation: str, status: str, *, reference: dict | None = None,
            expected_reference: dict | None = None, inspection: dict | None = None,
            provenance: dict | None = None, code: str | None = None,
            integrity: str = "NOT_ESTABLISHED", replay: str = "NOT_PERFORMED",
            effect: str = "NO_MANIFEST_ATTEMPT_BY_THIS_CALL", prior: Any = None) -> dict:
    return {
        "schema": RESULT_SCHEMA, "operation": operation, "status": status,
        "reference": reference, "expected_reference": expected_reference,
        "inspection": inspection, "review_provenance": provenance,
        "refusal": {"code": code} if code else None,
        "integrity_status": integrity, "replay_status": replay, "effect_state": effect,
        "prior_observation": ({"declaration": prior, "resolution": "UNRESOLVED_NO_SELECTION"}
                              if prior is not None and provenance is not None else None),
        "purpose_scope": _purpose(), "admission": "NOT_ADMITTED",
        "authority": _authority(), "graph1_projection": None,
        "content_boundary": _content_boundary(),
    }


def _capabilities(store: Any, *, write: bool) -> None:
    _require(callable(getattr(store, "get_bytes_strict_bounded", None)),
             "STORE_CAPABILITY_UNAVAILABLE")
    if write:
        _require(callable(getattr(store, "put_bytes_strict_conditional", None))
                 and callable(getattr(store, "validate_strict_conditional_write_capability", None)),
                 "STORE_CAPABILITY_UNAVAILABLE")
        try:
            store.validate_strict_conditional_write_capability()
        except Exception:
            raise _Refusal("STORE_CAPABILITY_UNAVAILABLE") from None


def _exact_read(store: Any, key: str, length: int) -> bytes | None:
    _require(type(length) is int and 0 < length <= CHUNK_BYTES, "STORAGE_OBJECT_LIMIT")
    try:
        raw = store.get_bytes_strict_bounded(
            key, expected_byte_length=length, max_byte_length=CHUNK_BYTES,
        )
    except Exception:
        raise _Refusal("STORE_READ_FAILED") from None
    if raw is not None:
        _require(type(raw) is bytes, "STORE_PROTOCOL_INVALID")
        _require(len(raw) == length, "STORE_LENGTH_MISMATCH")
    return raw


def _chunk_key(digest: str) -> str:
    return PREFIX + "chunks/sha256/" + digest + ".bin"


def _manifest_key(reference: dict) -> str:
    return PREFIX + "commits/sha256/" + reference["sha256"] + ".json"


def _manifest(payload: bytes) -> tuple[dict, bytes, list[bytes]]:
    _require(0 < len(payload) <= MAX_PACKAGE_BYTES, "SERIALIZED_PACKAGE_LIMIT")
    chunks = [payload[offset:offset + CHUNK_BYTES] for offset in range(0, len(payload), CHUNK_BYTES)]
    _require(1 <= len(chunks) <= MAX_CHUNKS, "CHUNK_COUNT_LIMIT")
    manifest = {
        "schema": MANIFEST_SCHEMA, "producer_contract": PRODUCER_CONTRACT,
        "package_sha256": sha256(payload).hexdigest(), "package_byte_length": len(payload),
        "chunks": [{"sha256": sha256(chunk).hexdigest(), "byte_length": len(chunk)}
                   for chunk in chunks],
    }
    raw = _canonical(manifest, MAX_MANIFEST_BYTES)
    ref = {"schema": REFERENCE_SCHEMA, "sha256": sha256(raw).hexdigest(), "byte_length": len(raw)}
    return ref, raw, chunks


def _validate_manifest(raw: bytes) -> dict:
    value = _parse(raw, MAX_MANIFEST_BYTES)
    _closed(value, _MANIFEST_KEYS)
    _require(value["schema"] == MANIFEST_SCHEMA and value["producer_contract"] == PRODUCER_CONTRACT,
             "MANIFEST_INVALID")
    _digest(value["package_sha256"])
    length, chunks = value["package_byte_length"], value["chunks"]
    _require(type(length) is int and 0 < length <= MAX_PACKAGE_BYTES, "MANIFEST_INVALID")
    _require(type(chunks) is list and 1 <= len(chunks) <= MAX_CHUNKS
             and len(chunks) == (length + CHUNK_BYTES - 1) // CHUNK_BYTES, "MANIFEST_INVALID")
    for index, chunk in enumerate(chunks):
        _closed(chunk, frozenset({"sha256", "byte_length"}))
        _digest(chunk["sha256"])
        _require(type(chunk["byte_length"]) is int
                 and chunk["byte_length"] == min(CHUNK_BYTES, length - index * CHUNK_BYTES),
                 "MANIFEST_INVALID")
    _require(_canonical(value, MAX_MANIFEST_BYTES) == raw, "MANIFEST_NONCANONICAL")
    return value


def _package_inputs(package: Any) -> dict[str, bytes]:
    _closed(package, _PACKAGE_KEYS)
    _require(package["schema"] == PACKAGE_SCHEMA and package["producer_contract"] == PRODUCER_CONTRACT,
             "PACKAGE_INVALID")
    _identifier(package["review_set_id"])
    _require(type(package["case_id"]) is str and package["case_id"] == "C01", "PACKAGE_INVALID")
    components = package["components"]
    _require(type(components) is dict and len(components) == len(_ROLES)
             and set(components) == set(_ROLES), "PACKAGE_INVALID")
    request = package["inspection_request"]
    _closed(request, frozenset({"as_of", "include_support_text", "registry_supplied"}))
    _require(request["as_of"] is None and request["include_support_text"] is False
             and type(request["registry_supplied"]) is bool, "PACKAGE_INVALID")
    _require(package["admission"] == "NOT_ADMITTED" and package["authority"] == _authority()
             and package["graph1_projection"] is None and package["purpose_scope"] == _purpose()
             and package["content_boundary"] == _content_boundary(), "PACKAGE_BOUNDARY_INVALID")
    _prior(package["prior_observation"])
    _digest(package["canonical_candidate_payload_sha256"])
    _require(type(package["inspection"]) is dict, "PACKAGE_INVALID")
    _canonical(package["inspection"], MAX_INSPECTION_BYTES)
    inputs = {}
    for role in _ROLES:
        part = components[role]
        _closed(part, _COMPONENT_KEYS)
        _digest(part["sha256"])
        _require(part["encoding"] == "utf-8" and type(part["text"]) is str, "PACKAGE_INVALID")
        limit = MAX_CANDIDATE_BYTES if role == "candidate" else MAX_PACKAGE_BYTES if role == "source" else MAX_REVIEW_BYTES
        _require(type(part["byte_length"]) is int and 0 < part["byte_length"] <= limit,
                 "PACKAGE_INVALID")
        raw = part["text"].encode("utf-8")
        _require(len(raw) == part["byte_length"] and sha256(raw).hexdigest() == part["sha256"],
                 "COMPONENT_DIGEST_MISMATCH")
        inputs[role] = raw
    return inputs


def _load_package(store: Any, reference: dict, *, manifest_raw: bytes | None = None) -> tuple[dict, bytes]:
    raw = manifest_raw if manifest_raw is not None else _exact_read(
        store, _manifest_key(reference), reference["byte_length"])
    _require(raw is not None, "OBSERVATION_NOT_FOUND")
    _require(len(raw) == reference["byte_length"] and sha256(raw).hexdigest() == reference["sha256"],
             "MANIFEST_DIGEST_MISMATCH")
    manifest = _validate_manifest(raw)
    chunks = []
    for descriptor in manifest["chunks"]:
        chunk = _exact_read(store, _chunk_key(descriptor["sha256"]), descriptor["byte_length"])
        _require(chunk is not None, "COMPONENT_MISSING")
        _require(sha256(chunk).hexdigest() == descriptor["sha256"], "CHUNK_DIGEST_MISMATCH")
        chunks.append(chunk)
    payload = b"".join(chunks)
    _require(len(payload) == manifest["package_byte_length"]
             and sha256(payload).hexdigest() == manifest["package_sha256"], "PACKAGE_DIGEST_MISMATCH")
    package = _parse(payload, MAX_PACKAGE_BYTES, package=True)
    _package_inputs(package)  # every exact original component is independently verified
    _require(_canonical(package, MAX_PACKAGE_BYTES) == payload, "PACKAGE_NONCANONICAL")
    return package, payload


def _create_only(store: Any, key: str, raw: bytes, *, final: bool = False) -> None:
    """One conditional attempt; readback resolves success, race, or lost ack."""
    _require(0 < len(raw) <= CHUNK_BYTES, "STORAGE_OBJECT_LIMIT")
    existing = _exact_read(store, key, len(raw))
    if existing is not None:
        _require(existing == raw, "EXISTING_OBJECT_CORRUPT")
        return
    try:
        # No overwrite/predecessor token is ever supplied by this module.
        store.put_bytes_strict_conditional(
            key, raw, expected_version=None,
            content_type="application/json" if final else "application/octet-stream",
        )
    except Exception:
        # The backing store may have committed before raising; never retry blind.
        pass
    try:
        observed = _exact_read(store, key, len(raw))
    except _Refusal:
        raise _Refusal("MANIFEST_EFFECT_UNKNOWN" if final else "COMPONENT_EFFECT_UNKNOWN",
                       effect_unknown=final) from None
    _require(observed is not None, "MANIFEST_NOT_AVAILABLE_AT_READBACK" if final else "COMPONENT_NOT_AVAILABLE_AT_READBACK")
    _require(observed == raw, "EXISTING_OBJECT_CORRUPT")


def append_relationship_observation(
    store: StrictConditionalWriteStore, *, review_set_id: str, case_id: str,
    candidate_bytes: bytes, source_bytes: bytes, source_record_bytes: bytes,
    pilot_adjudications_bytes: bytes, semantic_review_bytes: bytes,
    retained_first_review_bytes: bytes, retained_independent_review_bytes: bytes,
    prior_observation: Any = None, registry: Any = None,
) -> dict:
    """Commit one private current observation, or return a bounded failure.

    COMMITTED means the complete manifest/closure was verified after publication;
    REPEATED means an existing exact commit and its entire closure were verified
    without writes. REFUSED never licenses repair. EFFECT_UNKNOWN exposes only
    an expected reference after an uncertain final write/readback, not a commit.
    Reviewer bytes and binding matches never authenticate their authorship/truth.
    """
    ref = None
    manifest_attempted = False
    inspection = None
    try:
        inputs = dict(zip(_ROLES, (
            candidate_bytes, source_bytes, source_record_bytes, pilot_adjudications_bytes,
            semantic_review_bytes, retained_first_review_bytes, retained_independent_review_bytes,
        )))
        package, visible = _prepare(
            review_set_id=review_set_id, case_id=case_id, inputs=inputs,
            prior_observation=prior_observation, registry=registry,
        )
        inspection = package["inspection"]
        payload = _canonical(package, MAX_PACKAGE_BYTES)
        ref, manifest_raw, chunks = _manifest(payload)
        success = _result("append", "COMMITTED", reference=ref, inspection=inspection,
                          provenance=visible, integrity="VERIFIED_COMPLETE_CLOSURE",
                          replay="MATCHED_SEALED_REQUEST", effect="COMMITTED_OBSERVED",
                          prior=package["prior_observation"])
        _canonical(success, MAX_PACKAGE_BYTES)  # result and all object sizes preflight before writes
        _capabilities(store, write=True)
        existing = _exact_read(store, _manifest_key(ref), ref["byte_length"])
        if existing is not None:
            _, observed = _load_package(store, ref, manifest_raw=existing)
            _require(observed == payload, "EXISTING_OBSERVATION_MISMATCH")
            success["status"] = "REPEATED"
            return success
        # Probe all existing chunks before any create. Corruption is terminal.
        for chunk in chunks:
            existing = _exact_read(store, _chunk_key(sha256(chunk).hexdigest()), len(chunk))
            _require(existing is None or existing == chunk, "EXISTING_OBJECT_CORRUPT")
        for chunk in chunks:
            _create_only(store, _chunk_key(sha256(chunk).hexdigest()), chunk)
        # Reconstruct the entire package from verified chunk reads BEFORE the manifest.
        verified = []
        for chunk in chunks:
            observed = _exact_read(store, _chunk_key(sha256(chunk).hexdigest()), len(chunk))
            _require(observed == chunk, "PRECOMMIT_CLOSURE_INCOMPLETE")
            verified.append(observed)
        _require(b"".join(verified) == payload, "PRECOMMIT_CLOSURE_INCOMPLETE")
        manifest_attempted = True
        _create_only(store, _manifest_key(ref), manifest_raw, final=True)
        try:
            _, observed = _load_package(store, ref)
        except _Refusal as error:
            if error.code == "STORE_READ_FAILED":
                raise _Refusal("COMMIT_CLOSURE_VERIFICATION_UNKNOWN", effect_unknown=True) from None
            raise
        _require(observed == payload, "POSTCOMMIT_CLOSURE_MISMATCH")
        return success
    except _Refusal as error:
        if error.effect_unknown:
            return _result("append", "EFFECT_UNKNOWN", expected_reference=ref, code=error.code,
                           effect="FINAL_MANIFEST_EFFECT_UNKNOWN")
        return _result("append", "REFUSED", inspection=error.inspection or inspection,
                       expected_reference=ref if manifest_attempted else None,
                       code=error.code, effect=("MANIFEST_ATTEMPTED_COMMIT_NOT_PROVEN" if manifest_attempted
                                               else "NO_MANIFEST_ATTEMPT_BY_THIS_CALL"))
    except (TypeError, ValueError, KeyError, UnicodeError, OverflowError, RecursionError):
        return _result("append", "REFUSED", code="INPUT_SHAPE_INVALID",
                       effect=("MANIFEST_ATTEMPTED_COMMIT_NOT_PROVEN" if manifest_attempted
                               else "NO_MANIFEST_ATTEMPT_BY_THIS_CALL"))


def read_relationship_observation(
    store: StrictConditionalWriteStore, reference: Any, *, as_of: Any = None,
    registry: Any = None, include_support_text: bool = False, purpose: str = PURPOSE,
) -> dict:
    """Read exact committed bytes and return the real fresh inspector outcome.

    A historical/refused/excluded request returns the complete fresh outcome and
    no saved positive or review assertions. Changed request options are explicit;
    only an unchanged request can claim full equality with the sealed inspection.
    This function never validates write capability, constructs a store, or writes.
    """
    ref = None
    fresh = None
    try:
        _require(type(purpose) is str and purpose == PURPOSE, "PURPOSE_UNSUPPORTED")
        ref = _reference(reference)
        _capabilities(store, write=False)
        package, payload = _load_package(store, ref)
        inputs = _package_inputs(package)
        candidate = _parse(inputs["candidate"], MAX_CANDIDATE_BYTES)
        source = _utf8(inputs["source"], MAX_PACKAGE_BYTES)
        fresh = _inspect(candidate, source, as_of=as_of, registry=registry,
                         include_support_text=include_support_text)
        _canonical(fresh, MAX_INSPECTION_BYTES)
        if fresh.get("inspection_status") != "INSPECTABLE":
            return _result("read", "ABSTAINED", reference=ref, inspection=fresh,
                           integrity="VERIFIED_COMPONENT_BYTES", replay="FRESH_REQUEST_ABSTAINED",
                           effect="READ_ONLY")
        derived, visible = _prepare(
            review_set_id=package["review_set_id"], case_id=package["case_id"], inputs=inputs,
            prior_observation=package["prior_observation"], registry=registry, _inspection=fresh,
        )
        # All derived envelope fields are checked. The sealed inspection itself is
        # compared only for the original request, and is never returned as fresh.
        derived["inspection"] = package["inspection"]
        derived["inspection_request"] = package["inspection_request"]
        _require(_canonical(derived, MAX_PACKAGE_BYTES) == payload, "PACKAGE_BINDING_MISMATCH")
        unchanged = (as_of is None and include_support_text is False
                     and (registry is not None) == package["inspection_request"]["registry_supplied"])
        if unchanged and _canonical(fresh, MAX_INSPECTION_BYTES) != _canonical(package["inspection"], MAX_INSPECTION_BYTES):
            return _result("read", "REFUSED", reference=ref, inspection=fresh,
                           code="INSPECTION_REPLAY_MISMATCH", integrity="VERIFIED_COMPONENT_BYTES",
                           replay="UNCHANGED_REQUEST_MISMATCH", effect="READ_ONLY")
        result = _result("read", "VERIFIED", reference=ref, inspection=fresh, provenance=visible,
                         integrity="VERIFIED_COMPLETE_CLOSURE",
                         replay="MATCHED_SEALED_REQUEST" if unchanged else "CHANGED_REQUEST_NOT_SEALED_EQUALITY",
                         effect="READ_ONLY", prior=package["prior_observation"])
        _canonical(result, MAX_PACKAGE_BYTES)
        return result
    except _Refusal as error:
        return _result("read", "REFUSED", reference=ref, inspection=fresh,
                       code=error.code, effect="READ_ONLY")
    except (TypeError, ValueError, KeyError, UnicodeError, OverflowError, RecursionError):
        return _result("read", "REFUSED", reference=ref, inspection=fresh,
                       code="INPUT_SHAPE_INVALID", effect="READ_ONLY")
