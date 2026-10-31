"""Pure E0 source/split declarations; never populate, assign or admit a study.

The frozen membership's unknown sessions/episodes/spans stay unknown. Supplied
supplemental provenance is byte-bound metadata, not authenticated source truth.
These checks cannot turn publication groups into independent economic episodes.
"""
from __future__ import annotations

from datetime import timedelta
from functools import lru_cache
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from . import market_memory_contextual_registration as control


SCHEMAS = {
    "source_coverage_ref": "research_factory.market_memory_e0_source_coverage.v1",
    "interval_split_ref": "research_factory.market_memory_e0_interval_split.v1",
}
_FILES = {"source_coverage_ref": "e0_source_coverage.v1.schema.json",
          "interval_split_ref": "e0_interval_split.v1.schema.json"}
_PARTITIONS = {"development", "tuning", "test"}


@lru_cache(maxsize=2)
def _validator(role: str):
    schema = json.loads((Path(__file__).resolve().parents[2] / "contracts" /
                         "market_memory" / _FILES[role]).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return control._INTEGER_VALIDATOR(schema, format_checker=FormatChecker())


def _interval(value: dict) -> tuple:
    start, end = control._clock(value["start_inclusive"]), control._clock(value["end_exclusive"])
    if start >= end:
        raise control.E0ControlError("temporal_nonempty_half_open_interval_required")
    return start, end


def _consistent_named_declarations(rows, fields):
    seen = {}
    for row in rows:
        for field in fields:
            value = row[field]
            if value is None:
                continue
            key = (field, value["id"])
            if key in seen and seen[key] != value:
                raise control.E0ControlError("temporal_declared_identity_alias_mismatch")
            seen[key] = value


def validate_declaration(value: object, body: bytes, *, role: str, registration: dict) -> dict:
    """Validate declared bindings/intervals, never the provenance's veracity."""
    if role not in SCHEMAS:
        raise control.E0ControlError("temporal_domain_role_required")
    declared, canonical = control._domain_snapshot(value)
    if next(_validator(role).iter_errors(declared), None) is not None:
        raise control.E0ControlError("temporal_domain_schema_violation")
    if canonical != body:
        raise control.E0ControlError("noncanonical_temporal_domain_bytes")
    if (declared["study_id"] != registration["study_id"]
            or declared["protocol_sha256"] != registration["design_ref"]["sha256"]
            or declared["membership_sha256"] != registration["corpus"]["membership_sha256"]
            or declared["tasks_ref"] != registration["tasks_ref"]):
        raise control.E0ControlError("temporal_domain_registration_mismatch")
    if role == "source_coverage_ref":
        captures = [row["capture_id"] for row in declared["entries"]]
        if len(set(captures)) != len(captures):
            raise control.E0ControlError("source_coverage_duplicate_capture")
        _consistent_named_declarations(declared["entries"], ("source_measurement_session", "economic_episode"))
        for row in declared["entries"]:
            control._clock(row["first_available_for_contextual_analysis"])
            for field in ("feature_support_interval", "label_support_interval"):
                interval = row[field]
                if interval is not None and "not_applicable" not in interval:
                    _interval(interval)
                elif interval is not None and interval["provenance_ref"] != registration["outcome_definition_ref"]:
                    # An opaque arbitrary object cannot even declare the role.
                    raise control.E0ControlError("label_nonapplicability_outcome_reference_required")
    else:
        if declared["source_coverage_ref"] != registration["source_coverage_ref"]:
            raise control.E0ControlError("split_source_coverage_reference_mismatch")
        ids = [row["task_id"] for row in declared["tasks"]]
        if len(set(ids)) != len(ids):
            raise control.E0ControlError("split_duplicate_task")
        _consistent_named_declarations(declared["tasks"], ("session_block", "economic_episode"))
        for row in declared["tasks"]:
            control._clock(row["analysis_cutoff"])
            if row["session_block"] is not None:
                start, end = _interval(row["session_block"])
                if not start <= control._clock(row["analysis_cutoff"]) < end:
                    raise control.E0ControlError("split_case_outside_declared_session_block")
        boundaries = declared["boundaries"]
        if boundaries is not None:
            development, tuning, test = (control._clock(boundaries[key]) for key in
                ("development_end_exclusive", "tuning_end_exclusive", "test_start_inclusive"))
            if not development < tuning <= test:
                raise control.E0ControlError("split_boundary_order")
    return declared


def provenance_references(declared: dict, *, role: str) -> list[tuple[str, dict]]:
    """One fixed evidence layer; no recursive source/identity discovery."""
    fields = (("source_measurement_session", "economic_episode", "feature_support_interval",
               "label_support_interval") if role == "source_coverage_ref"
              else ("session_block", "economic_episode"))
    rows = declared["entries"] if role == "source_coverage_ref" else declared["tasks"]
    return [(f"{role}.{index}.{field}", row[field]["provenance_ref"])
            for index, row in enumerate(rows) for field in fields if row[field] is not None]


def source_coverage_checks(declared: dict, *, membership: dict | None,
                           resolved_digests: set[str]) -> dict:
    unresolved = []
    fields = ("source_measurement_session", "economic_episode", "feature_support_interval",
              "label_support_interval")
    unknown = {field: sum(row[field] is None for row in declared["entries"]) for field in fields}
    frozen_unknown = None
    if membership is None:
        unresolved.append("frozen_membership_bytes")
    else:
        frozen = {row["capture_id"]: row for row in membership["query_candidates"]}
        if set(frozen) != {row["capture_id"] for row in declared["entries"]}:
            raise control.E0ControlError("source_coverage_exact_membership_required")
        keys = ("capture_id", "context_id", "query_id", "packet_sha256", "receipt_sha256",
                "source_receipt_ids", "source_artifact_sha256s", "first_available_for_contextual_analysis")
        for row in declared["entries"]:
            if any(row[key] != frozen[row["capture_id"]][key] for key in keys):
                raise control.E0ControlError("source_coverage_frozen_identity_or_clock_mismatch")
        frozen_unknown = {field: sum(row[field] is None for row in frozen.values()) for field in
            ("source_measurement_session", "economic_episode_id", "feature_support_interval", "label_interval")}
        if any(frozen_unknown.values()):
            # Caller-authored supplements cannot silently rewrite null owner
            # metadata, even when their opaque reference bodies are supplied.
            unresolved.append("frozen_owner_measurement_episode_or_span_provenance")
    if any(unknown.values()):
        unresolved.append("declared_measurement_episode_feature_or_label_support")
    if any(ref["sha256"] not in resolved_digests
           for _, ref in provenance_references(declared, role="source_coverage_ref")):
        unresolved.append("declared_source_provenance_bytes")
    if any(row["label_support_interval"] is not None
           and row["label_support_interval"].get("not_applicable") is True for row in declared["entries"]):
        unresolved.append("outcome_definition_semantics_for_declared_nonapplicability")
    return {"schema": declared["schema"], "object_id": declared["object_id"],
            "accounted_capture_count": len(declared["entries"]),
            "frozen_membership_bindings_checked": membership is not None,
            "frozen_owner_metadata_unknown_counts": frozen_unknown,
            "unknown_declarations": unknown, "unresolved": unresolved,
            "authenticated_source_coverage": False, "actual_population_qualified": False,
            "operational_admission": False}


def interval_split_checks(declared: dict, *, tasks: dict | None, coverage: dict | None,
                          membership: dict | None, resolved_digests: set[str]) -> dict:
    unresolved = []
    rows = declared["tasks"]
    task_map = None if tasks is None else {row["task_id"]: row for row in tasks["tasks"]}
    if task_map is None:
        unresolved.append("exact_task_manifest_bytes")
    elif set(task_map) != {row["task_id"] for row in rows}:
        raise control.E0ControlError("split_exact_task_coverage_required")
    if coverage is None:
        unresolved.append("source_coverage_bytes")
    if membership is None:
        unresolved.append("frozen_membership_bytes")
    boundaries = declared["boundaries"]
    if boundaries is None:
        unresolved.append("declared_chronological_boundaries")
    embargo = declared["embargo_seconds"]
    if embargo is None:
        unresolved.append("declared_embargo_duration")
    coverage_map = {} if coverage is None else {row["capture_id"]: row for row in coverage["entries"]}
    sibling = {} if membership is None else {capture: group for group, captures in
                membership["publication_sibling_groups"].items() for capture in captures}
    groups: dict[tuple, set[str]] = {}
    counts = {key: 0 for key in ("unknown", "development", "tuning", "test", "purged", "embargoed", "excluded")}
    incomplete = 0
    for row in rows:
        disposition = row["disposition"]
        counts[disposition] += 1
        task = None if task_map is None else task_map[row["task_id"]]
        cutoff = control._clock(row["analysis_cutoff"])
        if task is not None and row["analysis_cutoff"] != task["analysis_cutoff"]:
            raise control.E0ControlError("split_task_cutoff_mismatch")
        support = None if task is None else coverage_map.get(task["capture_id"])
        if (row["session_block"] is None or row["economic_episode"] is None
                or support is None or support["source_measurement_session"] is None
                or support["economic_episode"] is None or support["feature_support_interval"] is None
                or support["label_support_interval"] is None):
            incomplete += 1
        if support is not None and row["economic_episode"] is not None and support["economic_episode"] is not None:
            if row["economic_episode"] != support["economic_episode"]:
                raise control.E0ControlError("split_declared_episode_binding_mismatch")
        if support is not None and support["feature_support_interval"] is not None:
            if _interval(support["feature_support_interval"])[1] > cutoff:
                raise control.E0ControlError("split_feature_support_after_query_cutoff")
        if support is not None and support["label_support_interval"] is not None:
            if support["label_support_interval"].get("not_applicable") is True:
                unresolved.append("outcome_definition_semantics_for_declared_nonapplicability")
        if disposition not in _PARTITIONS:
            continue  # No allocation/exclusion is performed by this audit.
        if boundaries is not None:
            development, tuning, test = (control._clock(boundaries[key]) for key in
                ("development_end_exclusive", "tuning_end_exclusive", "test_start_inclusive"))
            expected = "development" if cutoff < development else "tuning" if cutoff < tuning else "test" if cutoff >= test else None
            if disposition != expected:
                raise control.E0ControlError("split_declared_partition_cutoff_mismatch")
            if row["session_block"] is not None:
                start, end = _interval(row["session_block"])
                if ((disposition == "development" and end > development)
                        or (disposition == "tuning" and (start < development or end > tuning))
                        or (disposition == "test" and start < test)):
                    raise control.E0ControlError("split_included_session_block_crosses_boundary")
            if support is not None:
                for field in ("feature_support_interval", "label_support_interval"):
                    value = support[field]
                    if value is None or "not_applicable" in value:
                        continue
                    start, end = _interval(value)
                    # Only the query case's full spans are checked here. Earlier
                    # evidence used by a later query is not forced into its fold.
                    if ((disposition == "development" and end > development)
                            or (disposition == "tuning" and (start < development or end > tuning))
                            or (disposition == "test" and start < test)):
                        raise control.E0ControlError("split_included_case_support_crosses_boundary")
                if embargo is not None and disposition in {"tuning", "test"}:
                    boundary = development if disposition == "tuning" else test
                    try:
                        embargo_end = boundary + timedelta(seconds=embargo)
                    except OverflowError as exc:
                        raise control.E0ControlError("split_embargo_clock_overflow") from exc
                    if cutoff < embargo_end:
                        raise control.E0ControlError("split_included_case_in_declared_embargo")
        group_keys = [(field, row[field]["id"]) for field in ("session_block", "economic_episode")
                      if row[field] is not None]
        if task is not None:
            group_keys.append(("query_capture", task["capture_id"]))
            if task["capture_id"] in sibling:
                group_keys.append(("frozen_publication_siblings", sibling[task["capture_id"]]))
        for key in group_keys:
            groups.setdefault(key, set()).add(disposition)
    if any(len(partitions) > 1 for partitions in groups.values()):
        raise control.E0ControlError("split_declared_cluster_crosses_partitions")
    if incomplete or counts["unknown"]:
        unresolved.append("declared_session_episode_and_full_support_spans")
    if any(ref["sha256"] not in resolved_digests
           for _, ref in provenance_references(declared, role="interval_split_ref")):
        unresolved.append("declared_split_provenance_bytes")
    return {"schema": declared["schema"], "object_id": declared["object_id"],
            "accounted_task_count": len(rows), "declared_dispositions": counts,
            "exact_task_bindings_checked": task_map is not None,
            "incomplete_declared_cases": incomplete, "unresolved": sorted(set(unresolved)),
            "genuine_independent_clusters_verified": False,
            "actual_split_assignment_executed": False, "operational_admission": False}
