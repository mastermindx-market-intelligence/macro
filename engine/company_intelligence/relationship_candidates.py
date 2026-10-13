"""Inspect manually reviewed, source-local relationship candidates.

This module is an ephemeral analyst boundary, not Graph1, a dataset producer, or
a publisher. Native byte replay is structural support, never independent
economic adjudication. Optional native temporal filtering precedes construction
of every semantic view; supplied rows still do not authenticate historical state.

Manual assertions and document/identity annotations are echoed as supplied and
may contain source text. The default omits dedicated machine-replayed support,
not all quotes. No result or flag certifies a quote-free or public-safe payload;
source credibility and purpose-specific rights remain unverified. Prefer concise
product/scope labels when preparing the manually reviewed candidate.
"""
from __future__ import annotations

import argparse
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

from engine.earnings_release.receipts import (
    RECEIPT_KEYS, RECEIPT_SCHEMA, ReceiptError, SpanReceipt, byte_offsets,
    replay_receipt,
)
from lib.dataos.temporal import (
    TemporalError, TemporalProfile, as_of_filter, assert_pit_readable, known_at, utc,
)

SCHEMA = "company_intelligence.relationship_candidate/v1"
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_CANDIDATE_BYTES = 256 * 1024
_TOP_KEYS = frozenset({
    "schema", "candidate_id", "document", "dataset_id", "temporal_row",
    "receipt", "assertion", "revision", "identity_annotations",
})
_LIFECYCLES = {
    "product_integration": {"planned", "announced", "reported_use", "ended", "disputed"},
    "supplier_roster": {"listed", "ended", "disputed"},
    "framework_agreement": {"planned", "announced", "in_force", "ended", "disputed"},
    "administrative_party": {"appointed", "ended", "disputed"},
    "anonymous_counterparty": {"planned", "announced", "reported_use", "ended", "disputed"},
    "thematic_similarity": {"observed"},
    "market_correlation": {"observed"},
}
_DISPOSITIONS = {
    "product_integration": ("product_integration_candidate", "product_only", True),
    "supplier_roster": ("roster_observation_only", "named_roster_only", False),
    "framework_agreement": ("framework_candidate_no_deliveries", "framework_only", True),
    "administrative_party": ("administrative_role_only", "administrative_only", False),
    "anonymous_counterparty": ("counterparty_unresolved", "source_scope_only", False),
    "thematic_similarity": ("non_relationship_observation", "similarity_only", False),
    "market_correlation": ("non_relationship_observation", "correlation_only", False),
}


class CandidateInputError(ValueError):
    """Bounded refusal with a stable code; never interpolates source prose."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require(condition: bool, code: str = "INPUT_INVALID") -> None:
    if not condition:
        raise CandidateInputError(code)


def _closed(value: Any, keys: frozenset[str] | set[str]) -> None:
    _require(type(value) is dict and set(value) == keys)


def _text(value: Any, *, nullable: bool = False, limit: int = 512) -> None:
    if nullable and value is None:
        return
    _require(type(value) is str and bool(value.strip()) and len(value) <= limit)
    _require(not any(ord(c) < 32 for c in value))


def _bounded_json(value: Any, depth: int = 0, budget: list[int] | None = None) -> None:
    """Bound nesting and scalar sizes before native parsers see caller input."""
    if budget is None:
        budget = [4096]
    budget[0] -= 1
    _require(budget[0] >= 0 and depth <= 12, "INPUT_LIMIT")
    if type(value) is dict:
        _require(all(type(k) is str and len(k) <= 128 for k in value))
        for item in value.values():
            _bounded_json(item, depth + 1, budget)
    elif type(value) is list:
        for item in value:
            _bounded_json(item, depth + 1, budget)
    elif type(value) is str:
        _require(len(value) <= 65536, "INPUT_LIMIT")
        try:
            value.encode("utf-8")
        except UnicodeError:
            raise CandidateInputError("INPUT_ENCODING") from None
    else:
        _require(value is None or type(value) in (bool, int))
        if type(value) is int:
            _require(abs(value) <= 2**63 - 1, "INPUT_LIMIT")


def _validate(candidate: Any, source: Any) -> None:
    _bounded_json(candidate)
    _closed(candidate, _TOP_KEYS)
    _require(candidate["schema"] == SCHEMA, "SCHEMA_UNSUPPORTED")
    _text(candidate["candidate_id"])
    _require(type(source) is str, "SOURCE_INVALID")
    try:
        _require(0 < len(source.encode("utf-8")) <= MAX_SOURCE_BYTES, "SOURCE_LIMIT")
    except UnicodeError:
        raise CandidateInputError("SOURCE_ENCODING") from None
    document = candidate["document"]
    _closed(document, {"document_id", "version", "source_ref", "published_date"})
    for key in ("document_id", "version", "source_ref"):
        _text(document[key], limit=2048)
    published_date = document["published_date"]
    if published_date is not None:
        _text(published_date, limit=10)
        try:
            _require(date.fromisoformat(published_date).isoformat() == published_date)
        except ValueError:
            raise CandidateInputError("PUBLICATION_DATE_INVALID") from None
    _text(candidate["dataset_id"], nullable=True)
    _require(candidate["temporal_row"] is None or type(candidate["temporal_row"]) is dict)
    assertion = candidate["assertion"]
    _closed(assertion, {
        "kind", "subject_label", "object_label", "product_scope", "lifecycle", "magnitude",
    })
    _text(assertion["kind"])
    _require(assertion["kind"] in _LIFECYCLES, "KIND_UNSUPPORTED")
    _text(assertion["lifecycle"])
    _require(assertion["lifecycle"] in _LIFECYCLES[assertion["kind"]], "LIFECYCLE_UNSUPPORTED")
    _text(assertion["subject_label"])
    _text(assertion["object_label"], nullable=True)
    _text(assertion["product_scope"])
    _require(assertion["magnitude"] is None, "QUANTITY_MUST_BE_NULL")
    if assertion["kind"] == "anonymous_counterparty":
        _require(assertion["object_label"] is None, "ANONYMOUS_PARTY_MUST_BE_NULL")
    else:
        _require(assertion["object_label"] is not None, "OBJECT_LABEL_REQUIRED")
    _require(assertion["subject_label"] != assertion["object_label"], "SUPPORT_AMBIGUOUS")
    revision = candidate["revision"]
    _closed(revision, {"supersedes_candidate_id", "relation"})
    _text(revision["supersedes_candidate_id"], nullable=True)
    _require(revision["relation"] in {"original", "corrects", "contradicts"})
    _require((revision["relation"] == "original") == (revision["supersedes_candidate_id"] is None))
    _require(revision["supersedes_candidate_id"] != candidate["candidate_id"], "REVISION_SELF_REFERENCE")
    annotation = candidate["identity_annotations"]
    if annotation is not None:
        _closed(annotation, {"subject_id", "object_id"})
        for value in annotation.values():
            _text(value, nullable=True)
    receipt = candidate["receipt"]
    _closed(receipt, RECEIPT_KEYS)
    _require(receipt["schema"] == RECEIPT_SCHEMA, "RECEIPT_SCHEMA_UNSUPPORTED")
    for key in ("char_start", "char_end", "byte_start", "byte_end", "span_bytes"):
        _require(type(receipt[key]) is int and receipt[key] >= 0, "RECEIPT_COORDINATES_INVALID")
    _require(0 <= receipt["char_start"] < receipt["char_end"] <= len(source), "RECEIPT_SPAN_EMPTY_OR_INVALID")
    _require(receipt["byte_start"] < receipt["byte_end"] and receipt["span_bytes"] > 0, "RECEIPT_SPAN_EMPTY_OR_INVALID")
    for key in ("source_sha256", "span_sha256", "value_text_sha256"):
        _require(type(receipt[key]) is str and re.fullmatch(r"[0-9a-f]{64}", receipt[key]) is not None, "RECEIPT_HASH_INVALID")
    for key in ("span_text", "value_text"):
        _require(type(receipt[key]) is str and bool(receipt[key].strip()), "RECEIPT_SUPPORT_EMPTY")
    # Native replay compares slice text; explicit native offset calculation also
    # prevents pointing the character coordinates at a different identical span.
    _require(
        byte_offsets(source, receipt["char_start"], receipt["char_end"])
        == (receipt["byte_start"], receipt["byte_end"]),
        "RECEIPT_COORDINATES_DISAGREE",
    )


def _base() -> dict[str, Any]:
    return {
        "schema": "company_intelligence.relationship_inspection/v1",
        "inspection_status": "REFUSED",
        "refusal": None,
        "admission": "NOT_ADMITTED",
        "assertion_basis": "manual_review",
        "authority": {key: False for key in ("rank", "gate", "size", "trade", "prediction")},
        "graph1_projection": None,
        "current_candidate_view": None,
        "source_provenance": None,
        "support": None,
        "annotation_trust": {
            key: "caller_supplied_not_authenticated"
            for key in ("manual_assertions", "document_annotations", "identity_annotations")
        },
        "content_boundary": {
            "annotations": "echoed_as_supplied_may_contain_source_text",
            "machine_replayed_support_text": "OMITTED",
            "quote_free_payload": "NOT_CERTIFIED",
            "public_safe_payload": "NOT_CERTIFIED",
            "public_export": "NOT_AUTHORIZED",
        },
        "temporal": {"mode": "current_inspection", "historical_system_replay": False},
        "gaps": {
            "native_adoption": ["relationship_dataset_and_owner_adoption_required"],
            "time": ["native_dataset_profile_and_bound_row_not_established"],
            "identity": ["as_of_native_issuer_identity_not_established"],
            "rights": ["purpose_specific_rights_not_established", "public_export_not_authorized"],
        },
        "limitations": [
            "structural_byte_replay_is_not_independent_semantic_adjudication",
            "manual_assertion_is_not_verified_economic_truth",
            "source_credibility_and_document_metadata_not_authenticated",
            "echoed_annotations_may_contain_source_text_no_public_safe_certification",
            "no_shipments_revenue_weight_theme_membership_or_propagation_inferred",
        ],
    }


def _temporal(candidate: dict, as_of: Any, registry: Any, result: dict) -> bool:
    """Filter a supplied row with its native profile; never invent an instant.

    Field shape checks are a bounded candidate-inspection probe, not a universal
    native row schema. In particular input_cutoffs here must be a nonempty mapping
    of input names to offset-bearing instants; other native formats need their
    owning reader rather than coercion through this probe.
    """
    if as_of is None:
        return True
    cutoff = utc(as_of)
    result["temporal"]["mode"] = "supplied_native_row_as_of_inspection"
    result["temporal"]["row_validation"] = "bounded_candidate_probe_not_universal_native_schema"
    result["temporal"]["as_of"] = cutoff.isoformat()
    # Registry import is lazy, and loading is solely the CLI's optional action.
    from lib.dataos.registry import DatasetContract, DatasetStatus, Registry

    _require(isinstance(registry, Registry), "AS_OF_REGISTRY_REQUIRED")
    dataset_id = candidate["dataset_id"]
    _require(dataset_id is not None, "AS_OF_DATASET_REQUIRED")
    _require(dataset_id not in registry.duplicate_ids(), "AS_OF_DATASET_AMBIGUOUS")
    contract = registry.get(dataset_id)
    _require(isinstance(contract, DatasetContract), "AS_OF_DATASET_UNREGISTERED")
    _require(contract.status is DatasetStatus.PRODUCED, "AS_OF_DATASET_NOT_PRODUCED")
    _require(contract.dataset_id == dataset_id, "AS_OF_DATASET_UNREGISTERED")
    # A produced price/PG/etc. profile cannot be borrowed for this document.
    # Require the native contract itself to declare this candidate/document grain
    # and source binding, rather than accepting caller-added row columns.
    _require(
        {"candidate_id", "document_id", "document_version"} <= set(contract.grain)
        and {"candidate_id", "document_id", "document_version", "source_sha256"} <= set(contract.schema),
        "AS_OF_DATASET_GRAIN_UNRELATED",
    )
    _require(isinstance(contract.temporal_profile, TemporalProfile), "AS_OF_PROFILE_INVALID")
    profile = contract.temporal_profile
    assert_pit_readable(profile)  # native DERIVED refusal precedes probe shape checks
    row = candidate["temporal_row"]
    _require(type(row) is dict, "AS_OF_ROW_REQUIRED")
    bindings = {
        "candidate_id": candidate["candidate_id"],
        "document_id": candidate["document"]["document_id"],
        "document_version": candidate["document"]["version"],
        "source_sha256": candidate["receipt"]["source_sha256"],
    }
    _require(all(row.get(k) == v for k, v in bindings.items()), "AS_OF_ROW_SOURCE_UNBOUND")
    _require(all(row.get(k) is not None for k in profile.required_fields), "AS_OF_PROFILE_FIELDS_MISSING")
    if "revision_seq" in profile.required_fields:
        _require(type(row["revision_seq"]) is int and row["revision_seq"] >= 0,
                 "AS_OF_REQUIRED_FIELD_INVALID")
    if "code_version" in profile.required_fields:
        _require(type(row["code_version"]) is str and bool(row["code_version"].strip()),
                 "AS_OF_REQUIRED_FIELD_INVALID")
    if "input_cutoffs" in profile.required_fields:
        cutoffs = row["input_cutoffs"]
        _require(type(cutoffs) is dict and bool(cutoffs), "AS_OF_REQUIRED_FIELD_INVALID")
        for input_name, input_cutoff in cutoffs.items():
            _require(type(input_name) is str and bool(input_name.strip()),
                     "AS_OF_REQUIRED_FIELD_INVALID")
            utc(input_cutoff)
    for field in ("data_cutoff_at", "expires_at"):
        if field in profile.required_fields:
            utc(row[field])
    for clock in profile.required_clocks:
        value = row.get(clock.value)
        _require(value is not None, "AS_OF_PROFILE_CLOCK_MISSING")
        if clock.value in {"period_start", "period_end"}:
            _require(type(value) is str and bool(value.strip()), "AS_OF_INTERVAL_LABEL_INVALID")
            try:
                # Exact ISO DATE labels remain labels, never promoted to instants.
                is_date_label = date.fromisoformat(value).isoformat() == value
            except ValueError:
                is_date_label = False
            if not is_date_label:
                utc(value)
        else:
            utc(value)
    # Native refusal (including DERIVED) and future-known exclusion happen
    # before replayed labels are interpreted into a semantic candidate view.
    visible = as_of_filter([row], cutoff, profile)
    result["temporal"].update({
        "dataset_id": dataset_id, "profile": profile.value,
        "known_at": known_at(row, profile).isoformat(),
    })
    result["gaps"]["time"] = [
        "supplied_row_not_authenticated_native_history",
        "historical_system_output_log_not_established",
    ]
    if not visible:
        result["inspection_status"] = "NOT_KNOWN_AS_OF"
        return False
    return True


def inspect_candidate(
    candidate: Any, *, source: str, as_of: Any = None,
    registry: Any = None, include_support_text: bool = False,
) -> dict[str, Any]:
    """Return a deterministic candidate inspection or a bounded typed refusal.

    Supplying registry, row, identity annotations, or support-text opt-in never
    grants production admission, public rights, or decision authority. Manual
    assertions and document/identity annotations are echoed as supplied and may
    contain source text. Default omission covers dedicated machine-replayed
    support only; no result or flag certifies quote-free or public-safe content.
    Source hash matching authenticates neither document metadata nor credibility.
    Supplied-row checks are a bounded probe, not a universal dataset schema;
    input_cutoffs must be a nonempty mapping of input names to aware instants.
    """
    result = _base()
    try:
        _require(type(include_support_text) is bool)
        if as_of is not None:
            utc(as_of)  # reject invalid cutoff before any semantic view
        _validate(candidate, source)
        if not _temporal(candidate, as_of, registry, result):
            return result
        normalized = replay_receipt(SpanReceipt.from_dict(candidate["receipt"]), source=source)
        assertion = candidate["assertion"]
        anchors = (assertion["subject_label"], assertion["object_label"], assertion["product_scope"])
        _require(all(label is None or label in normalized for label in anchors), "SOURCE_LOCAL_LABEL_UNSUPPORTED")
        disposition, scope, bilateral = _DISPOSITIONS[assertion["kind"]]
        result["inspection_status"] = "INSPECTABLE"
        result["source_provenance"] = {
            **candidate["document"],
            "source_sha256": candidate["receipt"]["source_sha256"],
            "dataset_id": candidate["dataset_id"],
            "metadata_authenticity": "caller_supplied_not_authenticated",
            "source_hash_status": "matched_supplied_bytes",
            "source_credibility": "not_verified",
        }
        result["support"] = {
            "status": "STRUCTURALLY_REPLAYED",
            "semantic_adjudication": "NOT_PERFORMED",
            **{k: candidate["receipt"][k] for k in (
                "schema", "char_start", "char_end", "byte_start", "byte_end",
                "span_bytes", "span_sha256", "value_text_sha256",
            )},
        }
        if include_support_text:
            result["support"]["replayed_value_text"] = normalized
            result["content_boundary"]["machine_replayed_support_text"] = "INCLUDED"
        result["current_candidate_view"] = {
            "candidate_id": candidate["candidate_id"],
            "assertion": dict(assertion),
            "disposition": disposition,
            "scope": scope,
            "bilateral_candidate": bilateral,
            "canonical_subject_id": None,
            "canonical_object_id": None,
            "identity_annotations": (
                dict(candidate["identity_annotations"])
                if candidate["identity_annotations"] is not None else None
            ),
            "identity_annotation_status": "UNTRUSTED_NOT_RESOLVED",
            "revision": dict(candidate["revision"]),
            "revision_resolution": "NO_AUTOMATIC_SELECTION_OR_ORIGINAL_ERASURE",
            "shipments": None, "revenue": None, "economic_weight": None,
            "theme_membership": None,
        }
        return result
    except CandidateInputError as exc:
        result["refusal"] = {"code": exc.code}
    except ReceiptError:
        result["refusal"] = {"code": "SOURCE_REPLAY_FAILED"}
    except TemporalError:
        result["refusal"] = {"code": "NATIVE_TEMPORAL_REFUSAL"}
    except (TypeError, ValueError, OverflowError, RecursionError):
        result["refusal"] = {"code": "INPUT_INVALID"}
    return result


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        _require(key not in result, "JSON_DUPLICATE_KEY")
        result[key] = value
    return result


def _read_bytes(path: str, limit: int) -> bytes:
    with Path(path).open("rb") as stream:
        data = stream.read(limit + 1)
    _require(len(data) <= limit, "INPUT_LIMIT")
    return data


REVIEW_SET_SCHEMA = "company_intelligence.relationship_review_set/v1"
REVIEW_FILES_SCHEMA = "company_intelligence.relationship_review_files/v1"
REVIEW_SCHEMA = "company_intelligence.relationship_review/v1"
MAX_REVIEW_CASES = 64
MAX_REVIEW_MANIFEST_BYTES = 256 * 1024
MAX_REVIEW_CANDIDATE_BYTES = 8 * 1024 * 1024
MAX_REVIEW_SOURCE_BYTES = 64 * 1024 * 1024
MAX_REVIEW_OUTPUT_BYTES = 8 * 1024 * 1024
_REVIEW_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")


def _review_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _review_base() -> dict[str, Any]:
    original = _base()
    return {
        "schema": REVIEW_SCHEMA,
        "review_set_id": None,
        "review_status": "REFUSED",
        "refusal": None,
        "admission": "NOT_ADMITTED",
        "authority": original["authority"],
        "graph1_projection": None,
        "content_sha256": None,
        "content_identity_scope": "canonical_review_content_not_manifest_byte_order_or_native_attestation",
        "input_manifest": None,
        "options": None,
        "registry_input": None,
        "processing": {"requested_cases": None, "prepared_cases": 0, "processed_cases": 0,
                       "inspector_calls": 0, "retained_case_results": 0},
        "denominators": None,
        "cases": [],
        "reconciliation": {
            "scope": "inspectable_cases_only",
            "resolution": "UNRESOLVED_NO_AUTOMATIC_SELECTION",
            "candidate_collisions": [],
            "repeated_input_references": [],
            "revision_links": [],
        },
        "content_boundary": original["content_boundary"],
        "gaps": original["gaps"],
        "limitations": original["limitations"] + [
            "counts_describe_requested_inputs_not_universe_coverage_recall_or_precision",
            "unique_source_byte_digests_do_not_establish_independent_corroboration",
            "only_inspectable_results_contribute_semantic_reconciliation",
            "registry_is_caller_supplied_not_authenticated_native_history_or_adoption",
            "content_sha256_is_not_a_native_registry_history_custody_or_rights_receipt",
        ],
    }


def _review_identify(result: dict[str, Any]) -> dict[str, Any]:
    # Exact manifest bytes remain separately witnessed, but their JSON ordering,
    # whitespace and path spellings do not change canonical reviewed content.
    identity = {key: value for key, value in result.items()
                if key not in {"content_sha256", "input_manifest"}}
    result["content_sha256"] = sha256(_review_json_bytes(identity)).hexdigest()
    return result


def _review_refusal(code: str, manifest: dict[str, Any] | None = None,
                    processing: dict[str, Any] | None = None) -> dict[str, Any]:
    result = _review_base()
    result["refusal"] = {"code": code}
    result["input_manifest"] = manifest
    if processing is not None:
        result["processing"] = {**processing, "retained_case_results": 0}
    return _review_identify(result)


def _review_envelope(value: Any, *, files: bool) -> list[dict[str, Any]]:
    _require(type(value) is dict and len(value) == 3 and all(type(key) is str for key in value)
             and set(value) == {"schema", "review_set_id", "cases"},
             "REVIEW_INPUT_INVALID")
    expected_schema = REVIEW_FILES_SCHEMA if files else REVIEW_SET_SCHEMA
    _require(type(value["schema"]) is str and value["schema"] == expected_schema, "REVIEW_SCHEMA_UNSUPPORTED")
    _require(type(value["review_set_id"]) is str
             and _REVIEW_ID.fullmatch(value["review_set_id"]) is not None,
             "REVIEW_ID_INVALID")
    cases = value["cases"]
    _require(type(cases) is list, "REVIEW_INPUT_INVALID")
    _require(bool(cases), "REVIEW_SET_EMPTY")
    _require(len(cases) <= MAX_REVIEW_CASES, "REVIEW_CASE_LIMIT")
    keys = {"case_id", "candidate_file", "source_file"} if files else {"case_id", "candidate", "source"}
    seen: set[str] = set()
    for case in cases:
        _require(type(case) is dict and len(case) == 3 and all(type(key) is str for key in case)
                 and set(case) == keys, "REVIEW_INPUT_INVALID")
        case_id = case["case_id"]
        _require(type(case_id) is str and _REVIEW_ID.fullmatch(case_id) is not None,
                 "REVIEW_CASE_ID_INVALID")
        _require(case_id not in seen, "REVIEW_CASE_ID_DUPLICATE")
        seen.add(case_id)
        if files:
            for name in ("candidate_file", "source_file"):
                path = case[name]
                _require(type(path) is str and 0 < len(path) <= 4096
                         and not any(ord(char) < 32 for char in path), "REVIEW_FILE_PATH_INVALID")
                try:
                    path.encode("utf-8")
                except UnicodeError:
                    raise CandidateInputError("REVIEW_FILE_PATH_INVALID") from None
    return sorted(cases, key=lambda case: case["case_id"])


def _review_options(as_of: Any, include_support_text: Any) -> dict[str, Any]:
    _require(type(include_support_text) is bool, "REVIEW_OPTIONS_INVALID")
    return {
        "as_of": utc(as_of).isoformat() if as_of is not None else None,
        "include_support_text": include_support_text,
    }


def _review_candidate_bytes(candidate: Any) -> bytes:
    """Stop canonical serialization at the byte budget, never after joining it.

    Existing node/depth/scalar/type checks run first. A shared string may occur
    thousands of times within those limits; streaming prevents that compact input
    from forcing its entire expanded JSON into memory. Each individual encoder
    chunk is bounded by the existing scalar limit, and retained chunks together
    never exceed the candidate byte cap.
    """
    _bounded_json(candidate)
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, sort_keys=True,
                               separators=(",", ":"))
    chunks = []
    total = 0
    for chunk in encoder.iterencode(candidate):
        encoded = chunk.encode("utf-8")
        total += len(encoded)
        _require(total <= MAX_CANDIDATE_BYTES, "INPUT_LIMIT")
        chunks.append(encoded)
    return b"".join(chunks)


def _review_candidate_binding(candidate: Any, *, file_bytes: bytes | None = None,
                              files: bool = False) -> tuple[dict[str, Any], str | None]:
    binding = {
        "representation": "original_file_bytes" if files else "canonical_api_payload",
        "raw_file_sha256": sha256(file_bytes).hexdigest() if file_bytes is not None else None,
        "raw_file_bytes": len(file_bytes) if file_bytes is not None else None,
        "canonical_payload_sha256": None,
        "canonical_payload_bytes": None,
    }
    try:
        encoded = _review_candidate_bytes(candidate)
        binding.update(canonical_payload_sha256=sha256(encoded).hexdigest(),
                       canonical_payload_bytes=len(encoded))
        return binding, None
    except CandidateInputError as exc:
        return binding, exc.code
    except UnicodeError:
        return binding, "INPUT_ENCODING"
    except (ValueError, TypeError, RecursionError, OverflowError):
        return binding, "INPUT_INVALID"


def _review_source_binding(source: Any, *, file_bytes: bytes | None = None,
                           files: bool = False) -> tuple[dict[str, Any], str | None]:
    binding = {
        "representation": "original_file_bytes" if files else "api_utf8_bytes",
        "sha256": sha256(file_bytes).hexdigest() if file_bytes is not None else None,
        "bytes": len(file_bytes) if file_bytes is not None else None,
        "utf8": None,
    }
    try:
        _require(type(source) is str, "SOURCE_INVALID")
        _require(len(source) <= MAX_SOURCE_BYTES, "SOURCE_LIMIT")
        encoded = source.encode("utf-8")
        _require(len(encoded) <= MAX_SOURCE_BYTES, "SOURCE_LIMIT")
        if file_bytes is not None:
            _require(encoded == file_bytes, "SOURCE_ENCODING")
        binding.update(sha256=sha256(encoded).hexdigest(), bytes=len(encoded), utf8=True)
        return binding, None
    except CandidateInputError as exc:
        return binding, exc.code
    except UnicodeError:
        return binding, "SOURCE_ENCODING"


def _review_regular_bytes(path: Path, limit: int) -> bytes:
    """Read bounded regular bytes; refuse symlinks in every path component.

    Descriptor-relative traversal prevents a changed parent path from redirecting
    the final open. Paths are explicit caller inputs, never discovery roots. This
    is not an entitlement grant or a filesystem sandbox.
    """
    required = ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")
    _require(all(hasattr(os, name) for name in required), "REVIEW_FILE_TYPE_UNSUPPORTED")
    absolute = path.absolute()
    parts = absolute.parts
    _require(bool(parts) and parts[0] == os.sep and ".." not in parts, "REVIEW_FILE_PATH_INVALID")
    directory_fd = None
    file_fd = None
    try:
        directory_fd = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        _require(stat.S_ISREG(before.st_mode), "REVIEW_FILE_NOT_REGULAR")
        _require(before.st_size <= limit, "INPUT_LIMIT")
        with os.fdopen(file_fd, "rb") as stream:
            file_fd = None
            data = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        _require(len(data) <= limit, "INPUT_LIMIT")
        before_key = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        after_key = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
        _require(before_key == after_key and len(data) == before.st_size, "REVIEW_FILE_CHANGED")
        return data
    except OSError as exc:
        # Only errno classification is used; no path or exception text is emitted.
        import errno

        code = "REVIEW_FILE_NOT_REGULAR" if exc.errno in {errno.ELOOP, errno.ENOTDIR} else "REVIEW_FILE_UNAVAILABLE"
        raise CandidateInputError(code) from None
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def _review_parse_json(data: bytes) -> Any:
    try:
        return json.loads(
            data.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(CandidateInputError("JSON_CONSTANT_INVALID")),
        )
    except UnicodeError:
        raise CandidateInputError("INPUT_ENCODING") from None
    except CandidateInputError:
        raise
    except (ValueError, TypeError, RecursionError):
        raise CandidateInputError("INPUT_FILE_OR_JSON_INVALID") from None


def _review_file_case(case: dict[str, Any], directory: Path) -> dict[str, Any]:
    prepared: dict[str, Any] = {"case_id": case["case_id"], "candidate": None, "source": None,
                                "input_refusals": []}
    for name, limit in (("candidate", MAX_CANDIDATE_BYTES), ("source", MAX_SOURCE_BYTES)):
        data = None
        error = None
        value = None
        try:
            data = _review_regular_bytes(directory / case[name + "_file"], limit)
            if name == "candidate":
                value = _review_parse_json(data)
            else:
                try:
                    value = data.decode("utf-8")
                except UnicodeError:
                    raise CandidateInputError("SOURCE_ENCODING") from None
        except CandidateInputError as exc:
            error = exc.code
        binding_fn = _review_candidate_binding if name == "candidate" else _review_source_binding
        binding, shape_error = binding_fn(value, file_bytes=data, files=True)
        if error is not None:
            if name == "candidate":
                binding["canonical_payload_sha256"] = None
                binding["canonical_payload_bytes"] = None
            elif data is not None:
                binding["utf8"] = False if error == "SOURCE_ENCODING" else None
        error = error or shape_error
        prepared[name] = value
        prepared[name + "_binding"] = binding
        if error:
            prepared["input_refusals"].append({"input": name, "code": error})
    return prepared


def _review_reconcile(cases: list[dict[str, Any]]) -> dict[str, Any]:
    reconciliation = _review_base()["reconciliation"]
    visible = [case for case in cases if case["inspection"]["inspection_status"] == "INSPECTABLE"]
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    by_input: dict[tuple[str, str], list[str]] = {}
    for case in visible:
        candidate_id = case["inspection"]["current_candidate_view"]["candidate_id"]
        by_candidate.setdefault(candidate_id, []).append(case)
        payload_sha = case["input_bindings"]["candidate"]["canonical_payload_sha256"]
        source_sha = case["input_bindings"]["source"]["sha256"]
        by_input.setdefault((payload_sha, source_sha), []).append(case["case_id"])
    for candidate_id in sorted(by_candidate):
        references = by_candidate[candidate_id]
        payloads = sorted({case["input_bindings"]["candidate"]["canonical_payload_sha256"] for case in references})
        if len(payloads) > 1:
            reconciliation["candidate_collisions"].append({
                "candidate_id": candidate_id, "case_ids": sorted(case["case_id"] for case in references),
                "canonical_payload_sha256s": payloads, "resolution": "UNRESOLVED",
            })
    for (payload_sha, source_sha), case_ids in sorted(by_input.items()):
        if len(case_ids) > 1:
            reconciliation["repeated_input_references"].append({
                "case_ids": sorted(case_ids), "canonical_payload_sha256": payload_sha,
                "source_sha256": source_sha,
                "basis": "same_canonical_candidate_payload_and_source_bytes",
                "independent_corroboration": "NOT_ESTABLISHED",
            })
    for case in visible:
        view = case["inspection"]["current_candidate_view"]
        revision = view["revision"]
        if revision["relation"] == "original":
            continue
        targets = by_candidate.get(revision["supersedes_candidate_id"], [])
        reconciliation["revision_links"].append({
            "case_id": case["case_id"], "candidate_id": view["candidate_id"],
            "relation": revision["relation"], "target_candidate_id": revision["supersedes_candidate_id"],
            "target_case_ids": sorted(target["case_id"] for target in targets),
            "target_status": "ABSENT_FROM_INSPECTABLE_SET" if not targets else
                             "AMBIGUOUS_TARGET" if len(targets) > 1 else "PRESENT_UNRESOLVED",
            "resolution": "UNRESOLVED_NO_AUTOMATIC_SELECTION",
        })
    return reconciliation


def _review_enforce_totals(prepared: list[dict[str, Any]]) -> None:
    candidate_bytes = sum(case["candidate_binding"]["raw_file_bytes"]
                          if case["candidate_binding"]["raw_file_bytes"] is not None else
                          case["candidate_binding"]["canonical_payload_bytes"] or 0 for case in prepared)
    source_bytes = sum(case["source_binding"]["bytes"] or 0 for case in prepared)
    _require(candidate_bytes <= MAX_REVIEW_CANDIDATE_BYTES, "REVIEW_CANDIDATE_TOTAL_LIMIT")
    _require(source_bytes <= MAX_REVIEW_SOURCE_BYTES, "REVIEW_SOURCE_TOTAL_LIMIT")


def _review_finish(review_set_id: str, prepared: list[dict[str, Any]], *, options: dict[str, Any],
                   registry: Any, processing: dict[str, Any],
                   manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    _review_enforce_totals(prepared)
    result = _review_base()
    result.update(review_set_id=review_set_id, review_status="INSPECTED", options=options,
                  input_manifest=manifest,
                  registry_input={"supplied": registry is not None,
                                  "trust": "caller_supplied_not_authenticated_native_registry_history"})
    counts = {key: 0 for key in ("requested_cases", "supplied_source_cases", "unique_supplied_source_byte_digests",
                                 "inspectable_cases", "refused_cases", "unavailable_cases", "not_known_as_of_cases")}
    counts["requested_cases"] = len(prepared)
    source_digests: set[str] = set()
    for case in sorted(prepared, key=lambda item: item["case_id"]):
        if case["source_binding"]["sha256"] is not None:
            counts["supplied_source_cases"] += 1
            source_digests.add(case["source_binding"]["sha256"])
        if case["input_refusals"]:
            inspection = _base()
            inspection["refusal"] = {"code": case["input_refusals"][0]["code"]}
            status = "UNAVAILABLE" if any(item["code"] == "REVIEW_FILE_UNAVAILABLE"
                                          for item in case["input_refusals"]) else "REFUSED"
        else:
            processing["inspector_calls"] += 1
            inspection = inspect_candidate(case["candidate"], source=case["source"],
                                           as_of=options["as_of"], registry=registry,
                                           include_support_text=options["include_support_text"])
            status = inspection["inspection_status"]
        count_key = {"INSPECTABLE": "inspectable_cases", "REFUSED": "refused_cases",
                     "UNAVAILABLE": "unavailable_cases", "NOT_KNOWN_AS_OF": "not_known_as_of_cases"}[status]
        counts[count_key] += 1
        result["cases"].append({
            "case_id": case["case_id"], "status": status,
            "input_bindings": {"candidate": case["candidate_binding"], "source": case["source_binding"]},
            "input_refusals": case["input_refusals"], "inspection": inspection,
        })
        processing["processed_cases"] += 1
    counts["unique_supplied_source_byte_digests"] = len(source_digests)
    result["denominators"] = counts
    result["reconciliation"] = _review_reconcile(result["cases"])
    result["processing"] = {**processing, "retained_case_results": len(result["cases"])}
    if options["include_support_text"]:
        result["content_boundary"]["machine_replayed_support_text"] = "PER_INSPECTABLE_CASE_OPT_IN"
    _review_identify(result)
    _require(len(_review_json_bytes(result)) <= MAX_REVIEW_OUTPUT_BYTES, "REVIEW_OUTPUT_LIMIT")
    return result


def inspect_review_set(review_set: Any, *, as_of: Any = None, registry: Any = None,
                       include_support_text: bool = False) -> dict[str, Any]:
    """Inspect a closed, explicitly supplied set without creating an admitted fact.

    API schema: ``{schema: REVIEW_SET_SCHEMA, review_set_id, cases}``, with exact
    case keys ``case_id, candidate, source``. IDs are opaque ASCII identifiers;
    cases are canonicalized by case_id. Candidates are bounded canonical JSON
    payloads and sources are original UTF-8 strings. Complete individual results
    are retained, including refusals and historical exclusions. Only INSPECTABLE
    cases enter unresolved correction reporting. A distinct CLI file envelope
    records original file-byte hashes in addition to canonical payload hashes.

    Limits: 64 cases, 256 KiB/candidate, 4 MiB/source, 8 MiB aggregate candidates,
    64 MiB aggregate sources and 8 MiB output. Aggregate-limit/outer-shape failures
    refuse the whole request (null denominators, no partial semantic result).
    Input-processing counts are not source coverage, precision or relationships.
    content_sha256 identifies canonical review CONTENT, never manifest byte order,
    authenticated registry/history, production custody or purpose-specific rights.
    """
    processing = _review_base()["processing"]
    try:
        options = _review_options(as_of, include_support_text)
        cases = _review_envelope(review_set, files=False)
        processing["requested_cases"] = len(cases)
        prepared = []
        for case in cases:
            candidate_binding, candidate_error = _review_candidate_binding(case["candidate"])
            source_binding, source_error = _review_source_binding(case["source"])
            errors = [{"input": name, "code": code} for name, code in
                      (("candidate", candidate_error), ("source", source_error)) if code]
            prepared.append({**case, "candidate_binding": candidate_binding,
                             "source_binding": source_binding, "input_refusals": errors})
            processing["prepared_cases"] += 1
            _review_enforce_totals(prepared)
        return _review_finish(review_set["review_set_id"], prepared, options=options,
                              registry=registry, processing=processing)
    except CandidateInputError as exc:
        return _review_refusal(exc.code, processing=processing)
    except TemporalError:
        return _review_refusal("NATIVE_TEMPORAL_REFUSAL", processing=processing)
    except (UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        return _review_refusal("REVIEW_INPUT_INVALID", processing=processing)


def _review_files_cli(args: argparse.Namespace) -> dict[str, Any]:
    manifest = None
    processing = _review_base()["processing"]
    try:
        options = _review_options(args.as_of, args.include_support_text)
        path = Path(args.review_set)
        data = _review_regular_bytes(path, MAX_REVIEW_MANIFEST_BYTES)
        manifest = {"raw_file_sha256": sha256(data).hexdigest(), "raw_file_bytes": len(data)}
        review_set = _review_parse_json(data)
        cases = _review_envelope(review_set, files=True)
        processing["requested_cases"] = len(cases)
        registry = None
        if args.registry:
            try:
                from lib.dataos.registry import load_registry
                registry = load_registry(args.registry)
            except Exception:
                raise CandidateInputError("REGISTRY_LOAD_FAILED") from None
        prepared = []
        for case in cases:
            prepared.append(_review_file_case(case, path.absolute().parent))
            processing["prepared_cases"] += 1
            _review_enforce_totals(prepared)
        return _review_finish(review_set["review_set_id"], prepared, options=options,
                              registry=registry, processing=processing, manifest=manifest)
    except CandidateInputError as exc:
        return _review_refusal(exc.code, manifest, processing)
    except TemporalError:
        return _review_refusal("NATIVE_TEMPORAL_REFUSAL", manifest, processing)
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        return _review_refusal("REVIEW_INPUT_INVALID", manifest, processing)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--candidate")
    inputs.add_argument("--review-set", help="Explicit bounded review-files/v1 manifest; no source discovery")
    parser.add_argument("--source")
    parser.add_argument("--as-of")
    parser.add_argument("--registry", help="Optional native dataset registry YAML, loaded once")
    parser.add_argument("--include-support-text", action="store_true",
                        help=("Include dedicated machine-replayed analyst support text. "
                              "Manual annotations are echoed in either mode and may contain source text; "
                              "neither mode certifies quote-free/public-safe content or export rights."))
    args = parser.parse_args(argv)
    if args.review_set is not None:
        if args.source is not None:
            parser.error("--source cannot be used with --review-set")
        result = _review_files_cli(args)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        if result["review_status"] != "INSPECTED":
            return 2
        counts = result["denominators"]
        return 2 if counts["refused_cases"] or counts["unavailable_cases"] else 0
    if args.source is None:
        parser.error("--source is required with --candidate")
    try:
        candidate = json.loads(
            _read_bytes(args.candidate, MAX_CANDIDATE_BYTES).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(CandidateInputError("JSON_CONSTANT_INVALID")),
        )
        source = _read_bytes(args.source, MAX_SOURCE_BYTES).decode("utf-8")
        registry = None
        if args.registry:
            try:
                from lib.dataos.registry import load_registry
                registry = load_registry(args.registry)
            except Exception:
                # Native optional loader can raise YAML/import/contract errors.
                # No registry content or host path is copied into the refusal.
                raise CandidateInputError("REGISTRY_LOAD_FAILED") from None
        result = inspect_candidate(candidate, source=source, as_of=args.as_of,
                                   registry=registry, include_support_text=args.include_support_text)
    except CandidateInputError as exc:
        result = _base()
        result["refusal"] = {"code": exc.code}
    except (OSError, UnicodeError, ValueError, TypeError, RecursionError):
        result = _base()
        result["refusal"] = {"code": "INPUT_FILE_OR_JSON_INVALID"}
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result["inspection_status"] in {"INSPECTABLE", "NOT_KNOWN_AS_OF"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

