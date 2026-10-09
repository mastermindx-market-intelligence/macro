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
import json
from pathlib import Path
import re
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--as-of")
    parser.add_argument("--registry", help="Optional native dataset registry YAML, loaded once")
    parser.add_argument("--include-support-text", action="store_true",
                        help=("Include dedicated machine-replayed analyst support text. "
                              "Manual annotations are echoed in either mode and may contain source text; "
                              "neither mode certifies quote-free/public-safe content or export rights."))
    args = parser.parse_args(argv)
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
