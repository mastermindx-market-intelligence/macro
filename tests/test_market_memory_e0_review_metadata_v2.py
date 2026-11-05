"""Synthetic declared metadata only; no participants, reads or study exposure."""

import copy
import hashlib
import inspect
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from engine.research_factory import market_memory_e0_review_metadata_v2 as subject


ROOT = Path(__file__).resolve().parents[1]
V1 = ROOT / "contracts/market_memory/e0_reviewer_plan.v1.schema.json"
V2 = ROOT / "contracts/market_memory/e0_review_metadata.v2.schema.json"
FLAGS = ("authenticated", "qualification_verified", "independence_verified",
         "exposure_verified", "operational_admission")


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def reference(value):
    raw = encoded(value)
    return dict(schema=value["schema"], object_id=value["object_id"],
                sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


@pytest.fixture
def records():
    ids = ["participant-1", "participant-2", "participant-3"]
    bodies, participants = {}, []
    for who in ids:
        participant = {}
        for role, schema in subject.ROLE_SCHEMAS.items():
            object_id = who if role == "principal_ref" else who + ":" + role
            body = dict(schema=schema, object_id=object_id, authority="display_only",
                        study_id="synthetic-study", participant_id=who,
                        verification=dict.fromkeys(FLAGS, False))
            if role == "principal_ref":
                body["execution_identity"] = None
            elif role == "qualification_ref":
                body["declared_competencies"] = ["source_support"]
            else:
                body.update(declared_distinct_from=[i for i in ids if i != who],
                            prior_exposure_status="not_established",
                            peer_ratings_visibility="not_established")
            bodies[object_id] = body
            participant[role] = reference(body)
        participants.append(participant)
    schema = json.loads(V1.read_bytes())
    plan = dict(
        schema=subject.PLAN_SCHEMA, object_id="synthetic-plan", authority="display_only",
        study_id="synthetic-study", preregistered_at="2026-10-12T00:00:00Z",
        **{k: schema["properties"][k]["const"] for k in
           ("protocol_sha256", "annotation_guide_sha256", "membership_sha256")},
        tasks_ref=dict(schema="research_factory.market_memory_e0_tasks.v1",
                       object_id="synthetic-tasks", sha256="0" * 64, bytes=1),
        reviewers=participants[:2], adjudicator=participants[2],
        assignments=[dict(task_id=task, reviewer_principal_ids=ids[:2],
                          adjudicator_principal_id=ids[2]) for task in ("task-1", "task-2")],
        blinding={k: spec["const"] for k, spec in
                  schema["$defs"]["blinding"]["properties"].items()},
    )
    scope = dict(schema=subject.SCOPE_SCHEMA, authority="display_only",
                 owner_contract=subject.OWNER_CONTRACT, action=subject.ACTION,
                 study_id=plan["study_id"], task_id="task-1", slot=0,
                 reviewer_plan_ref=reference(plan))
    return scope, plan, bodies


def prepare(records):
    scope, plan, bodies = records
    scope["reviewer_plan_ref"] = reference(plan)
    return subject.plan_review_metadata_reads(scope, encoded(plan))


def repin_body(records, object_id):
    _, plan, bodies = records
    for participant in [*plan["reviewers"], plan["adjudicator"]]:
        for role, ref in participant.items():
            if ref["object_id"] == object_id:
                participant[role] = reference(bodies[object_id])


def validate_first(records, role="principal_ref"):
    result = prepare(records)
    descriptor = next(r for r in result["reads"] if r["evidence_role"] == role)
    return subject.validate_review_metadata_payload(
        records[0], encoded(records[1]), descriptor,
        encoded(records[2][descriptor["reference"]["object_id"]]))


def assert_unverified(value):
    assert value["verification"] == dict.fromkeys(FLAGS, False)
    assert all(type(v) is bool for v in value["verification"].values())
    assert value["native_v2_owner_read_support"] == "not_implemented"
    assert value["installed_permission"] == "not_verified"
    assert value["authority"] == "display_only"


def test_nine_refs_all_roles_all_slots_two_tasks_no_hash_cycle(records):
    scope, plan, bodies = records
    original_plan_bytes = encoded(plan)
    global_refs = copy.deepcopy([*plan["reviewers"], plan["adjudicator"]])
    validator = Draft202012Validator(json.loads(V2.read_bytes()))
    for task in ("task-1", "task-2"):
        for slot in range(3):
            scope.update(task_id=task, slot=slot)
            result = prepare(records)
            assert_unverified(result)
            assert validator.is_valid(scope)
            assert len(result["reads"]) == 9
            assert [r["participant_role"] for r in result["reads"]] == (
                ["reviewer_1"] * 3 + ["reviewer_2"] * 3 + ["adjudicator"] * 3)
            digestable = {k: v for k, v in result.items() if k != "plan_sha256"}
            assert result["plan_sha256"] == hashlib.sha256(encoded(digestable)).hexdigest()
            for descriptor in result["reads"]:
                body = bodies[descriptor["reference"]["object_id"]]
                assert validator.is_valid(body)
                assert not {"task_id", "slot", "reviewer_plan_sha256"} & body.keys()
                record = subject.validate_review_metadata_payload(
                    scope, original_plan_bytes, descriptor, encoded(body))
                assert_unverified(record)
                assert record["descriptor"]["task_id"] == task
                assert record["descriptor"]["slot"] == slot
                assert record["metadata"] == body
    assert encoded(plan) == original_plan_bytes
    assert [*plan["reviewers"], plan["adjudicator"]] == global_refs


def test_detached_outputs_and_bounded_declared_projection(records):
    scope, plan, bodies = records
    bodies["participant-1"]["execution_identity"] = dict(
        source_schema="mastermind.execution_principal_snapshot/v1",
        attempt_id="attempt-1", worker_id="worker-1", quota_class="bounded",
        provider="synthetic", placement_snapshot_digest="a" * 64)
    repin_body(records, "participant-1")
    record = validate_first(records)
    assert_unverified(record)
    record["metadata"]["execution_identity"]["provider"] = "changed"
    record["scope"]["task_id"] = "changed"
    assert bodies["participant-1"]["execution_identity"]["provider"] == "synthetic"
    assert scope["task_id"] == "task-1"
    reads = prepare(records)
    reads["reads"][0]["reference"]["object_id"] = "changed"
    assert plan["reviewers"][0]["principal_ref"]["object_id"] == "participant-1"


@pytest.mark.parametrize("field,value", [
    ("schema", subject.PREFIX + "review_metadata_scope.v1"),
    ("action", "read_e0_registration"), ("owner_contract", "legacy.v1"),
    ("authorized", True), ("installed_permission", True), ("slot", True),
    ("slot", 1.0), ("slot", -1), ("slot", 3), ("study_id", "other"),
    ("task_id", "unassigned"), ("task_id", "x" * 8193),
])
def test_invalid_scope_before_any_participant_reader(records, field, value):
    records[0][field] = value
    reads = []
    # A consumer cannot reach its own reader unless planning succeeds. The
    # module has no reader argument/callback or participant IO API at all.
    with pytest.raises(subject.ReviewMetadataError):
        result = prepare(records)
        reads.extend(result["reads"])
    assert reads == []
    assert list(inspect.signature(subject.plan_review_metadata_reads).parameters) == [
        "scope", "reviewer_plan_bytes"]


@pytest.mark.parametrize("schema", ["unknown.v2", "annotation.v1", "outcome.v1",
    "condition_output.v1", subject.ROLE_SCHEMAS["qualification_ref"]])
def test_last_ref_invalidates_entire_plan_before_payload(records, schema):
    records[1]["adjudicator"]["independence_ref"]["schema"] = schema
    with pytest.raises(subject.ReviewMetadataError, match="unsupported_participant_reference"):
        prepare(records)
    # Even valid first payload cannot hide an unsafe ninth ref.
    with pytest.raises(subject.ReviewMetadataError, match="unsupported_participant_reference"):
        subject.validate_review_metadata_payload(records[0], encoded(records[1]), {}, b"{}")


@pytest.mark.parametrize("mutation", ["duplicate_participant", "duplicate_digest",
    "duplicate_task", "foreign_reviewer", "foreign_adjudicator", "duplicate_reviewer",
    "duplicate_ref_id", "duplicate_ref_digest", "bool_bytes", "float_bytes",
    "oversize_ref", "aggregate", "wrong_guide", "extra_plan"])
def test_plan_semantic_and_native_refusal(records, mutation):
    plan = records[1]
    first = plan["reviewers"][0]["principal_ref"]
    last = plan["adjudicator"]["independence_ref"]
    if mutation == "duplicate_participant": plan["adjudicator"]["principal_ref"] = first.copy()
    elif mutation == "duplicate_digest": plan["adjudicator"]["principal_ref"]["sha256"] = first["sha256"]
    elif mutation == "duplicate_task": plan["assignments"].append(plan["assignments"][0].copy())
    elif mutation == "foreign_reviewer": plan["assignments"][1]["reviewer_principal_ids"][0] = "other"
    elif mutation == "foreign_adjudicator": plan["assignments"][1]["adjudicator_principal_id"] = "other"
    elif mutation == "duplicate_reviewer": plan["assignments"][0]["reviewer_principal_ids"] *= 2
    elif mutation == "duplicate_ref_id": last["object_id"] = first["object_id"]
    elif mutation == "duplicate_ref_digest": last["sha256"] = first["sha256"]
    elif mutation == "bool_bytes": last["bytes"] = True
    elif mutation == "float_bytes": last["bytes"] = 1.0
    elif mutation == "oversize_ref": last["bytes"] = 8193
    elif mutation == "aggregate":
        for p in [*plan["reviewers"], plan["adjudicator"]]:
            for ref in p.values(): ref["bytes"] = 8192
    elif mutation == "wrong_guide": plan["annotation_guide_sha256"] = "0" * 64
    else: plan["answer"] = "forbidden"
    with pytest.raises(subject.ReviewMetadataError): prepare(records)


@pytest.mark.parametrize("field,value", [("object_id", "other"), ("sha256", "0" * 64),
    ("bytes", 1), ("bytes", True), ("schema", "other.v1")])
def test_plan_reference_exactness(records, field, value):
    scope, plan, _ = records
    scope["reviewer_plan_ref"][field] = value
    with pytest.raises(subject.ReviewMetadataError):
        subject.plan_review_metadata_reads(scope, encoded(plan))


@pytest.mark.parametrize("field,value", [("task_id", "task-2"), ("slot", 1),
    ("slot", False), ("participant_id", "participant-2"), ("extra", False),
    ("participant_role", "adjudicator")])
def test_descriptor_requires_full_exact_membership(records, field, value):
    descriptor = prepare(records)["reads"][0]
    descriptor[field] = value
    with pytest.raises(subject.ReviewMetadataError, match="descriptor_not_in_plan"):
        subject.validate_review_metadata_payload(records[0], encoded(records[1]), descriptor,
                                                 encoded(records[2]["participant-1"]))


@pytest.mark.parametrize("field,value", [("study_id", "other"),
    ("participant_id", "other"), ("object_id", "other"),
    ("answers", []), ("ratings", []), ("outcomes", {}), ("refs", []),
    ("task_id", "task-1"), ("slot", 0), ("reviewer_plan_sha256", "a" * 64),
    ("execution_identity", {"account": "forbidden"}),
    ("verification", dict.fromkeys(FLAGS, True)),
    ("verification", dict.fromkeys(FLAGS, 0)),
    ("verification", {**dict.fromkeys(FLAGS, False), "extra": False})])
def test_payload_identity_and_closed_schema_even_when_repinned(records, field, value):
    body = records[2]["participant-1"]
    body[field] = value
    repin_body(records, "participant-1")
    with pytest.raises(subject.ReviewMetadataError): validate_first(records)


@pytest.mark.parametrize("role,field,value", [
    ("qualification_ref", "declared_competencies", ["unbounded-narrative"]),
    ("qualification_ref", "declared_competencies", ["source_support"] * 2),
    ("independence_ref", "declared_distinct_from", ["participant-1", "participant-2"]),
    ("independence_ref", "declared_distinct_from", ["participant-2", "other"]),
    ("independence_ref", "prior_exposure_status", "unexposed"),
    ("independence_ref", "peer_ratings_visibility", "hidden"),
])
def test_role_specific_unverified_metadata(records, role, field, value):
    object_id = "participant-1:" + role
    records[2][object_id][field] = value
    repin_body(records, object_id)
    with pytest.raises(subject.ReviewMetadataError): validate_first(records, role)


@pytest.mark.parametrize("bad", [b"{}", b" " * 8193, bytearray(b"{}"),
    b'{"schema":1,"schema":2}', b'{"x":{"y":1,"y":2}}', b'{"x":NaN}',
    b'{"x":Infinity}', b'{"x":1.0}', b'\xff', b'{ "x":1}', b'[' * 1100])
def test_payload_encoding_refusal(records, bad):
    descriptor = prepare(records)["reads"][0]
    with pytest.raises(subject.ReviewMetadataError):
        subject.validate_review_metadata_payload(records[0], encoded(records[1]), descriptor, bad)


def test_referenced_payload_length_hash_and_role(records):
    descriptor = prepare(records)["reads"][0]
    wrong = copy.deepcopy(records[2]["participant-1"])
    wrong["participant_id"] = "participant-2"
    assert len(encoded(wrong)) == len(encoded(records[2]["participant-1"]))
    with pytest.raises(subject.ReviewMetadataError, match="reference_mismatch"):
        subject.validate_review_metadata_payload(records[0], encoded(records[1]), descriptor, encoded(wrong))
    with pytest.raises(subject.ReviewMetadataError, match="payload_role_mismatch"):
        subject.validate_review_metadata_payload(records[0], encoded(records[1]), descriptor, encoded(records[0]))


@pytest.mark.parametrize("bad", [b" " * 262145, bytearray(b"{}"), b'{"x":NaN}',
    b'{"x":1,"x":2}', b'[' * 1100])
def test_plan_bytes_bounds_and_strict_encoding(records, bad):
    with pytest.raises(subject.ReviewMetadataError):
        subject.plan_review_metadata_reads(records[0], bad)


def test_scope_native_types_cycles_and_immutable_original_schema(records):
    assert hashlib.sha256(V1.read_bytes()).hexdigest() == (
        "a586fd7e073e624de8eafc8582e68815d167812732c0fe9673975ea5681ed490")
    class DictSubclass(dict): pass
    class StrSubclass(str): pass
    with pytest.raises(subject.ReviewMetadataError):
        subject.plan_review_metadata_reads(DictSubclass(records[0]), encoded(records[1]))
    records[0]["task_id"] = StrSubclass("task-1")
    with pytest.raises(subject.ReviewMetadataError): prepare(records)
    records[0]["task_id"] = records[0]
    with pytest.raises(subject.ReviewMetadataError, match="json_shape_bound"):
        prepare(records)


def test_schema_objects_closed(records):
    schema = json.loads(V2.read_bytes())
    Draft202012Validator.check_schema(schema)
    def visit(value):
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            for child in value.values(): visit(child)
        elif isinstance(value, list):
            for child in value: visit(child)
    visit(schema)
    validator = Draft202012Validator(schema)
    for record in [records[0], *records[2].values()]:
        assert validator.is_valid(record)
        assert not validator.is_valid({**record, "answers": []})


@pytest.mark.parametrize("suffix", ["\n", "\r", "\r\n"])
def test_provider_and_new_scope_schema_reject_terminal_controls(records, suffix):
    validator = Draft202012Validator(json.loads(V2.read_bytes()))
    projection = dict(source_schema="mastermind.execution_principal_snapshot/v1",
                      attempt_id="attempt-1", worker_id="worker-1", quota_class="bounded",
                      provider="synthetic" + suffix, placement_snapshot_digest="a" * 64)
    records[2]["participant-1"]["execution_identity"] = projection
    assert not validator.is_valid(records[2]["participant-1"])
    repin_body(records, "participant-1")
    with pytest.raises(subject.ReviewMetadataError): validate_first(records)
    scope = {**records[0], "task_id": "task-1" + suffix}
    assert not validator.is_valid(scope)


def test_v1_nonselected_task_and_participant_tokens_strict_without_schema_edit(records):
    _, plan, _ = records
    plan["assignments"][1]["task_id"] += "\n"
    # Original frozen schema admits `$` terminal LF; new semantic boundary must
    # refuse it even on an assignment that is not the selected scope's task.
    assert Draft202012Validator(json.loads(V1.read_bytes())).is_valid(plan)
    with pytest.raises(subject.ReviewMetadataError, match="metadata_token"):
        prepare(records)
    plan["assignments"][1]["task_id"] = "task-2"
    plan["reviewers"][0]["principal_ref"]["object_id"] += "\n"
    for assignment in plan["assignments"]:
        assignment["reviewer_principal_ids"][0] += "\n"
    assert Draft202012Validator(json.loads(V1.read_bytes())).is_valid(plan)
    with pytest.raises(subject.ReviewMetadataError, match="metadata_token"):
        prepare(records)
