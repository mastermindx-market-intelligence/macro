"""Synthetic temporal declarations around frozen metadata; no actual allocation."""
import copy
import json

import pytest

from engine.research_factory import market_memory_contextual_registration as control
from engine.research_factory import market_memory_e0_domains as domain
from tests.test_market_memory_e0_control_records import (
    bundle, canonical, records, reference, task_bundle,
)


@pytest.fixture
def temporal(task_bundle):
    original, tasks = task_bundle
    reg, objects, _ = original
    reg = copy.deepcopy(reg)
    membership = json.loads(objects[control._FROZEN_DOMAIN_DIGESTS["membership"]])
    common = {"authority": "display_only", "study_id": reg["study_id"],
              "protocol_sha256": reg["design_ref"]["sha256"],
              "membership_sha256": reg["corpus"]["membership_sha256"],
              "tasks_ref": copy.deepcopy(reg["tasks_ref"])}
    fields = ("capture_id", "context_id", "query_id", "packet_sha256", "receipt_sha256",
              "source_receipt_ids", "source_artifact_sha256s", "first_available_for_contextual_analysis")
    coverage = {"schema": domain.SCHEMAS["source_coverage_ref"], "object_id": "synthetic-coverage",
                **common, "entries": [{**{key: copy.deepcopy(row[key]) for key in fields},
                    "source_measurement_session": None, "economic_episode": None,
                    "feature_support_interval": None, "label_support_interval": None}
                    for row in membership["query_candidates"]]}
    reg["source_coverage_ref"] = reference(canonical(coverage), coverage["schema"], coverage["object_id"])
    split = {"schema": domain.SCHEMAS["interval_split_ref"], "object_id": "synthetic-split",
             **common, "source_coverage_ref": copy.deepcopy(reg["source_coverage_ref"]),
             "boundaries": None, "embargo_seconds": None,
             "tasks": [{"task_id": task["task_id"], "analysis_cutoff": task["analysis_cutoff"],
                        "disposition": "unknown", "session_block": None, "economic_episode": None}
                       for task in tasks["tasks"]]}
    return reg, membership, tasks, coverage, split


def declared(value, reg, role):
    return domain.validate_declaration(value, canonical(value), role=role, registration=reg)


def source_checks(data):
    reg, membership, _, coverage, _ = data
    return domain.source_coverage_checks(declared(coverage, reg, "source_coverage_ref"),
        membership=membership, resolved_digests=set())


def split_checks(data):
    reg, membership, tasks, coverage, split = data
    return domain.interval_split_checks(declared(split, reg, "interval_split_ref"),
        tasks=tasks, coverage=coverage, membership=membership, resolved_digests=set())


def synthetic_known_case(data):
    """Invented spans/groups are test-only, never added to frozen membership."""
    reg, _, _, coverage, split = data
    proof = reference(b"synthetic provenance only")
    identity = {"id": "synthetic-episode", "provenance_ref": proof}
    interval = {"start_inclusive": "2026-09-24T00:00:00.000000Z",
                "end_exclusive": "2026-09-25T00:00:00.000000Z", "provenance_ref": proof}
    coverage["entries"][0].update(source_measurement_session={"id": "synthetic-session", "provenance_ref": proof},
        economic_episode=identity, feature_support_interval=interval,
        label_support_interval=copy.deepcopy(interval))
    split.update(boundaries={"development_end_exclusive": "2026-09-15T00:00:00.000000Z",
        "tuning_end_exclusive": "2026-09-28T00:00:00.000000Z",
        "test_start_inclusive": "2026-09-28T00:00:00.000000Z"}, embargo_seconds=0)
    split["tasks"][0].update(disposition="tuning", economic_episode=copy.deepcopy(identity),
        session_block={"id": "synthetic-block", "provenance_ref": proof,
            "start_inclusive": "2026-09-24T00:00:00.000000Z",
            "end_exclusive": "2026-09-26T00:00:00.000000Z"})
    return data


def test_real_frozen_109_unknown_spans_remain_unknown_and_detached(temporal):
    before = canonical(temporal[1])
    result = source_checks(temporal)
    assert result["accounted_capture_count"] == 109
    assert result["frozen_membership_bindings_checked"] is True
    assert result["unknown_declarations"] == dict.fromkeys(("source_measurement_session", "economic_episode",
        "feature_support_interval", "label_support_interval"), 109)
    assert set(result["frozen_owner_metadata_unknown_counts"].values()) == {109}
    assert result["authenticated_source_coverage"] is False
    assert result["actual_population_qualified"] is False
    assert result["operational_admission"] is False
    result["unknown_declarations"].clear()
    assert source_checks(temporal)["unknown_declarations"]
    assert canonical(temporal[1]) == before
    split = split_checks(temporal)
    assert split["declared_dispositions"]["unknown"] == 1
    assert {"declared_chronological_boundaries", "declared_embargo_duration",
            "declared_session_episode_and_full_support_spans"} <= set(split["unresolved"])
    assert split["actual_split_assignment_executed"] is False
    assert split["genuine_independent_clusters_verified"] is False


@pytest.mark.parametrize("field,value", [("packet_sha256", "0" * 64),
    ("receipt_sha256", "0" * 64), ("source_receipt_ids", ["mmsrc_" + "0" * 64]),
    ("source_artifact_sha256s", ["0" * 64]),
    ("first_available_for_contextual_analysis", "2026-09-24T00:00:00.000000Z")])
def test_original_source_identity_and_availability_cannot_be_rewritten(temporal, field, value):
    temporal[3]["entries"][0][field] = value
    with pytest.raises(control.E0ControlError, match="frozen_identity_or_clock"):
        source_checks(temporal)


def test_capture_denominator_cannot_drop_duplicate_or_substitute_member(temporal):
    temporal[3]["entries"].pop()
    with pytest.raises(control.E0ControlError, match="schema_violation"):
        source_checks(temporal)


def test_duplicate_capture_is_not_a_complete_denominator(temporal):
    temporal[3]["entries"][-1] = copy.deepcopy(temporal[3]["entries"][0])
    with pytest.raises(control.E0ControlError, match="duplicate_capture"):
        source_checks(temporal)


def test_synthetic_known_case_checks_declarations_without_authenticating_provenance(temporal):
    synthetic_known_case(temporal)
    result = split_checks(temporal)
    assert result["declared_dispositions"]["tuning"] == 1
    assert result["incomplete_declared_cases"] == 0
    assert "declared_split_provenance_bytes" in result["unresolved"]
    assert result["operational_admission"] is False
    assert source_checks(temporal)["unknown_declarations"]["feature_support_interval"] == 108
    assert source_checks(temporal)["frozen_owner_metadata_unknown_counts"]["feature_support_interval"] == 109


@pytest.mark.parametrize("mutation", [
    lambda row: row.update(provenance_ref="unbounded-worker-ref"),
    lambda row: row.update(id="x" * 129),
    lambda row: row["provenance_ref"].pop("bytes"),
    lambda row: row["provenance_ref"].update(bytes=True),
])
def test_named_provenance_is_an_exact_bounded_reference_not_a_string(temporal, mutation):
    synthetic_known_case(temporal)
    mutation(temporal[3]["entries"][0]["economic_episode"])
    with pytest.raises(control.E0ControlError, match="schema_violation"):
        source_checks(temporal)


def test_reused_declared_identity_cannot_change_provenance(temporal):
    synthetic_known_case(temporal)
    episode = copy.deepcopy(temporal[3]["entries"][0]["economic_episode"])
    episode["provenance_ref"] = reference(b"different synthetic proof")
    temporal[3]["entries"][1]["economic_episode"] = episode
    with pytest.raises(control.E0ControlError, match="identity_alias_mismatch"):
        source_checks(temporal)


@pytest.mark.parametrize("field", ["feature_support_interval", "label_support_interval"])
def test_reversed_or_zero_width_declared_intervals_refuse(temporal, field):
    synthetic_known_case(temporal)
    interval = temporal[3]["entries"][0][field]
    interval["end_exclusive"] = interval["start_inclusive"]
    with pytest.raises(control.E0ControlError, match="nonempty_half_open"):
        source_checks(temporal)


def test_half_open_touching_boundary_is_distinct_from_crossing_it(temporal):
    synthetic_known_case(temporal)
    # Query's interval may begin exactly at its tuning boundary.
    row = temporal[3]["entries"][0]
    row["feature_support_interval"]["start_inclusive"] = "2026-09-15T00:00:00.000000Z"
    assert split_checks(temporal)["declared_dispositions"]["tuning"] == 1
    row["feature_support_interval"]["start_inclusive"] = "2026-09-14T23:59:59.999999Z"
    with pytest.raises(control.E0ControlError, match="support_crosses_boundary"):
        split_checks(temporal)


def test_feature_support_after_exact_query_cutoff_is_a_contradiction(temporal):
    synthetic_known_case(temporal)
    temporal[3]["entries"][0]["feature_support_interval"]["end_exclusive"] = "2026-09-26T00:00:00.000000Z"
    with pytest.raises(control.E0ControlError, match="feature_support_after_query_cutoff"):
        split_checks(temporal)


@pytest.mark.parametrize("change,error", [
    (lambda x: x[4].update(embargo_seconds=12 * 86400), "declared_embargo"),
    (lambda x: x[4]["tasks"][0].update(disposition="test"), "partition_cutoff"),
    (lambda x: x[4]["tasks"][0].update(task_id="not-the-task"), "exact_task_coverage"),
    (lambda x: x[4]["tasks"][0].update(analysis_cutoff="2026-09-25T02:00:00.000000Z"), "task_cutoff"),
    (lambda x: x[4]["tasks"][0]["economic_episode"].update(id="another-episode"), "episode_binding"),
    (lambda x: x[4]["tasks"][0]["session_block"].update(end_exclusive="2026-09-25T00:00:00.000000Z"), "outside_declared_session"),
    (lambda x: x[4]["tasks"][0]["session_block"].update(start_inclusive="2026-09-14T00:00:00.000000Z"), "session_block_crosses_boundary"),
])
def test_split_contradictions_do_not_become_unknown(temporal, change, error):
    synthetic_known_case(temporal)
    change(temporal)
    with pytest.raises(control.E0ControlError, match=error):
        split_checks(temporal)


def test_same_query_capture_cannot_be_declared_in_two_partitions(temporal):
    synthetic_known_case(temporal)
    extra = copy.deepcopy(temporal[2]["tasks"][0])
    extra.update(task_id="synthetic-second-query", analysis_cutoff="2026-10-01T00:00:00.000000Z")
    temporal[2]["tasks"].append(extra)
    temporal[4]["tasks"].append({"task_id": extra["task_id"], "analysis_cutoff": extra["analysis_cutoff"],
        "disposition": "test", "session_block": None, "economic_episode": None})
    # Unknown spans cannot conceal the independently knowable capture conflict.
    temporal[3]["entries"][0].update(feature_support_interval=None, label_support_interval=None)
    with pytest.raises(control.E0ControlError, match="cluster_crosses_partitions"):
        split_checks(temporal)


def test_label_nonapplicability_is_not_an_authenticated_interval(temporal):
    synthetic_known_case(temporal)
    temporal[3]["entries"][0]["label_support_interval"] = {
        "not_applicable": True, "reason": "registered_no_outcome_labels",
        "provenance_ref": temporal[0]["outcome_definition_ref"]}
    assert "outcome_definition_semantics_for_declared_nonapplicability" in source_checks(temporal)["unresolved"]
    assert "outcome_definition_semantics_for_declared_nonapplicability" in split_checks(temporal)["unresolved"]
    temporal[3]["entries"][0]["label_support_interval"]["provenance_ref"] = reference(b"unrelated")
    with pytest.raises(control.E0ControlError, match="outcome_reference_required"):
        source_checks(temporal)


def test_missing_objects_preserve_exact_unknowns_without_private_io(temporal, monkeypatch):
    reg, membership, tasks, coverage, split = temporal
    value = declared(coverage, reg, "source_coverage_ref")
    assert "frozen_membership_bytes" in domain.source_coverage_checks(value,
        membership=None, resolved_digests=set())["unresolved"]
    value = declared(split, reg, "interval_split_ref")
    def forbidden(*args, **kwargs):
        pytest.fail("pure temporal checks must not open sources or private stores")
    from pathlib import Path
    monkeypatch.setattr(Path, "open", forbidden)
    result = domain.interval_split_checks(value, tasks=None, coverage=None, membership=None, resolved_digests=set())
    assert {"exact_task_manifest_bytes", "source_coverage_bytes", "frozen_membership_bytes"} <= set(result["unresolved"])
    assert result["operational_admission"] is False


def install_temporal(task_bundle, temporal):
    original, _ = task_bundle
    reg, _, _, coverage, split = temporal
    objects = copy.deepcopy(original[1])
    for role in ("source_coverage_ref", "interval_split_ref"):
        objects.pop(original[0][role]["sha256"], None)
    body = canonical(coverage)
    reg["source_coverage_ref"] = reference(body, coverage["schema"], coverage["object_id"])
    objects[reg["source_coverage_ref"]["sha256"]] = body
    split["source_coverage_ref"] = copy.deepcopy(reg["source_coverage_ref"])
    body = canonical(split)
    reg["interval_split_ref"] = reference(body, split["schema"], split["object_id"])
    objects[reg["interval_split_ref"]["sha256"]] = body
    return {"registration": reg, "objects": objects, "prelabel_design": original[2]}


def test_existing_resolver_joins_real_109_without_turning_unknowns_into_admission(task_bundle, temporal):
    packet = install_temporal(task_bundle, temporal)
    result = control.resolve_e0_domain_references(**packet)
    assert result["references_complete"] is True
    assert result["source_coverage_binding_checks"][0]["frozen_owner_metadata_unknown_counts"]["feature_support_interval"] == 109
    assert result["interval_split_binding_checks"][0]["declared_dispositions"]["unknown"] == 1
    assert result["domain_metadata_complete"] is False
    assert result["operational_admission"] is False
    assert {gap["missing_rows"] for gap in result["frozen_metadata_gaps"]
            if gap["field"].startswith("membership.")} == {109}


@pytest.mark.parametrize("role", ["source_coverage_ref", "interval_split_ref"])
def test_known_temporal_schema_role_guard_precedes_absent_bytes(task_bundle, temporal, role):
    packet = install_temporal(task_bundle, temporal)
    ref = packet["registration"][role]
    packet["objects"].pop(ref["sha256"])
    packet["objects"].pop(packet["registration"]["metrics_ref"]["sha256"])
    packet["registration"]["metrics_ref"] = copy.deepcopy(ref)
    with pytest.raises(control.E0ControlError, match="temporal_domain_reference_role_mismatch"):
        control.resolve_e0_domain_references(**packet)


def test_provenance_byte_closure_is_opaque_and_never_source_truth(task_bundle, temporal, monkeypatch):
    synthetic_known_case(temporal)
    packet = install_temporal(task_bundle, temporal)
    proof = reference(b"synthetic provenance only")
    packet["objects"][proof["sha256"]] = b"synthetic provenance only"
    # Warm only fixed public schemas; no owner/store/path discovery follows refs.
    first = control.resolve_e0_domain_references(**packet)
    assert first["references_complete"] is True
    from pathlib import Path
    monkeypatch.setattr(Path, "open", lambda *a, **k: pytest.fail("unexpected source I/O"))
    second = control.resolve_e0_domain_references(**packet)
    assert second == first
    checked = second["source_coverage_binding_checks"][0]
    assert checked["authenticated_source_coverage"] is False
    assert checked["frozen_owner_metadata_unknown_counts"]["economic_episode_id"] == 109
    assert "frozen_owner_measurement_episode_or_span_provenance" in checked["unresolved"]


def test_temporal_provenance_shares_existing_reference_count_bound(task_bundle, temporal):
    for index, row in enumerate(temporal[3]["entries"]):
        row["source_measurement_session"] = {"id": f"synthetic-session-{index}",
            "provenance_ref": reference(f"synthetic-{index}".encode())}
    packet = install_temporal(task_bundle, temporal)
    with pytest.raises(control.E0ControlError, match="domain_reference_count_limit"):
        control.resolve_e0_domain_references(**packet)
