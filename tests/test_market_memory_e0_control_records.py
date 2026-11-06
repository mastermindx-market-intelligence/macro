"""Synthetic E0 metadata: structural validity must never grant label access."""
import copy
import hashlib
import json
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from engine.research_factory import market_memory_contextual_registration as e0


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def ref(name):
    return {"schema": "synthetic.metadata.v1", "object_id": name,
            "sha256": hashlib.sha256(name.encode()).hexdigest(), "bytes": 100}


def record_ref(value, identity):
    body = canonical(value)
    return {"schema": value["schema"], "object_id": value[identity],
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def record(kind, **fields):
    return {"schema": e0.SCHEMAS[kind], "authority": "display_only", "study_id": "synthetic-study", **fields}


@pytest.fixture
def records():
    reg = record("registration", registered_at="2026-10-14T00:00:00.000000Z",
        study_kind="retrospective_contextual_evidence", corpus={
            "profile": "market_memory.trusted.macro_regime_canary.v1",
            "store_id": "mmstore_794a3c80dd160cedf09f1fa510c8b2d0467a05e94e60f72f18bcdf1dde79bf88",
            "generation_id": "mmgeneration_996920d552dcbb140861f2e676c3c2ca65b288ab30c5fa21474f5adbddd77cf8",
            "generation_sha256": "166b2cc30864edbacc7e20b87c0b9ba815efb6a929922bebb43ef563b411f2fc",
            "membership_sha256": "76de9522d40c65c33de0dcde59f581a5c493f4be218df3221adb9c3af1495c8f",
            "count": 109, "membership_ref": ref("synthetic-membership")},
        **{key: ref(key) for key in ("tasks_ref", "source_coverage_ref", "interval_split_ref", "design_ref",
                                    "reviewer_plan_ref", "outcome_definition_ref", "metrics_ref", "access_rules_ref")},
        allocation={"seed_encoding": "sha256_hex_as_256bit_integer",
            "seed_hex": "7c8013e1e8092bdf91d4598a73c01d9690199dfb6c08db632b81f564367a4b03",
            "algorithm_ref": ref("synthetic-algorithm"), "assignment_ref": ref("synthetic-assignments")},
        implementation={"method_ref": ref("synthetic-method"), "baseline_refs": [ref("synthetic-baseline")],
            "code_ref": ref("synthetic-code"), "dependencies_ref": ref("synthetic-dependencies")})
    rr = record_ref(reg, "study_id")
    closed = record("prelabel_closure", closure_id="synthetic-closure", registration_ref=rr,
        closed_at="2026-10-14T00:01:00.000000Z", reviewer_principal_ref=ref("synthetic-reviewer"),
        independence_ref=ref("synthetic-independence"), checked_objects=[ref("synthetic-checked-object")],
        closure_rules_ref=ref("synthetic-rules"), verdict="complete", exposure_state_ref=ref("synthetic-exposure"))
    cr = record_ref(closed, "closure_id")
    owner = ref("synthetic-owner")
    pub = record("publication", publication_id="synthetic-publication", registration_ref=rr, closure_ref=cr,
        published_at="2026-10-14T00:02:00.000000Z", owner_principal_ref=owner,
        owner_operation_ref=ref("synthetic-publication-operation"), namespace_id="synthetic-namespace", installation_epoch="epoch-1")
    pr = record_ref(pub, "publication_id")
    bound = record("installed_binding", installation_id="synthetic-installation", installation_epoch="epoch-1",
        namespace_id="synthetic-namespace", registration_ref=rr, closure_ref=cr, publication_ref=pr,
        installed_at="2026-10-14T00:03:00.000000Z", expires_at="2026-10-15T00:00:00.000000Z",
        owner_principal_ref=owner, admin_receipt_ref=ref("synthetic-administration"), access_state_id="synthetic-access",
        permitted_actions=["read_e0_registration", "disclose_e0_registration"])
    state = record("access_state", access_state_id="synthetic-access", registration_ref=rr, publication_ref=pr,
        installation_id="synthetic-installation", installation_epoch="epoch-1", sequence=0, previous_state_ref=None,
        owner_principal_ref=owner, owner_operation_ref=ref("synthetic-access-operation"),
        recorded_at="2026-10-14T00:04:00.000000Z", status="active", contamination_state="clean", scope_ref=ref("synthetic-scope"),
        budget={"maximum_looks": 3, "consumed_looks": 0, "reserved_looks": 0}, reservations_ref=ref("synthetic-reservations"))
    return {"registration": reg, "closure": closed, "publication": pub, "installation": bound, "access": state}


def join(records, **kwargs):
    return e0.validate_e0_control_join(**records, as_of=kwargs.get("as_of", "2026-10-14T00:05:00.000000Z"))


def test_consistent_fake_owner_records_never_establish_admission(records):
    result = join(records)
    assert result["metadata_consistent"] is True
    assert result["operational_admission"] is False
    assert {"authenticated_owner_installation", "complete_domain_manifests", "exact_durable_reservation"} <= set(result["unverified_obligations"])


@pytest.mark.parametrize("name,kind", [("registration", "registration"), ("closure", "prelabel_closure"),
    ("publication", "publication"), ("installation", "installed_binding"), ("access", "access_state")])
def test_closed_records_roundtrip_and_return_detached_copy(records, name, kind):
    Draft202012Validator.check_schema(e0._validator(kind).schema)
    frozen = e0.parse_e0_control_record(canonical(records[name]), kind=kind)
    assert frozen == records[name]
    records[name]["study_id"] = "changed-after-validation"
    assert frozen["study_id"] == "synthetic-study"
    frozen["extra"] = True
    with pytest.raises(e0.E0ControlError, match="schema"):
        e0.validate_e0_control_record(frozen, kind=kind)


@pytest.mark.parametrize("mutate", [
    lambda r: r["corpus"].update(count=109.0), lambda r: r["corpus"].update(count=True),
    lambda r: r["corpus"].update(count=108), lambda r: r["corpus"].update(membership_sha256="a" * 64),
    lambda r: r["allocation"].update(seed_hex="7c8013e1e8092bdf"), lambda r: r["allocation"].update(seed_hex="0" * 64),
    lambda r: r["allocation"].update(reseed=True), lambda r: r["tasks_ref"].update(bytes=100.0),
    lambda r: r["tasks_ref"].update(bytes=True), lambda r: r["tasks_ref"].update(object_id="../../price-data"),
    lambda r: r["tasks_ref"].update(object_id="task\n"), lambda r: r["tasks_ref"].update(sha256="a" * 64 + "\n"),
    lambda r: r.update(study_id="https://external.example/registration"),
    lambda r: r.update(registered_at="2026-02-30T00:00:00.000000Z"),
    lambda r: r.update(registered_at="2026-10-14T00:00:00Z"),
    lambda r: r.update(registered_at="2026-10-14T00:00:60.000000Z"),
    lambda r: r.update(registered_at="2026-10-14T00:00:00.000000+00:00"),
    lambda r: r.update(study_kind="predictive_trading"), lambda r: r.update(authority="execute"),
])
def test_frozen_identity_integer_seed_path_and_time_corruptions_refuse(records, mutate):
    mutate(records["registration"])
    with pytest.raises(e0.E0ControlError):
        e0.validate_e0_registration(records["registration"])


@pytest.mark.parametrize("transform", [
    lambda b: b + b"\n", lambda b: b.replace(b'"authority":', b'"authority":"display_only","authority":', 1),
    lambda b: b.replace(b'"count":109', b'"count":109.0'), lambda b: b.replace(b'"count":109', b'"count":NaN'),
    lambda b: b.replace(b'"count":109', b'"count":Infinity'), lambda b: b"\xef\xbb\xbf" + b,
    lambda b: b.replace(b"synthetic-study", b"\xff"),
])
def test_noncanonical_or_ambiguous_wire_bytes_refuse(records, transform):
    with pytest.raises(e0.E0ControlError):
        e0.parse_e0_control_record(transform(canonical(records["registration"])), kind="registration")


@pytest.mark.parametrize("name,key,value", [
    ("installation", "study_id", "another-study"), ("installation", "namespace_id", "another-namespace"),
    ("installation", "installation_epoch", "old-epoch"), ("installation", "registration_ref", ref("swapped-registration")),
    ("installation", "closure_ref", ref("swapped-closure")), ("installation", "publication_ref", ref("swapped-publication")),
    ("access", "installation_id", "different-installation"), ("access", "access_state_id", "different-access-stream"),
    ("access", "owner_principal_ref", ref("different-owner")),
    ("access", "recorded_at", "2026-10-14T00:01:00.000000Z"),
    ("access", "recorded_at", "2026-10-14T00:06:00.000000Z"),
])
def test_swapped_record_refs_owner_epoch_and_clocks_refuse(records, name, key, value):
    records[name][key] = value
    with pytest.raises(e0.E0ControlError):
        join(records)


def test_reference_is_exact_full_canonical_bytes(records):
    records["installation"]["registration_ref"] = copy.deepcopy(records["installation"]["registration_ref"])
    records["installation"]["registration_ref"]["bytes"] += 1
    with pytest.raises(e0.E0ControlError, match="registration_reference"):
        join(records)


def test_expiry_is_exclusive(records):
    with pytest.raises(e0.E0ControlError, match="expiry"):
        join(records, as_of=records["installation"]["expires_at"])


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(sequence=1), lambda r: r.update(previous_state_ref=ref("unexpected-predecessor")),
    lambda r: r["budget"].update(reserved_looks=4), lambda r: r["budget"].update(reserved_looks=2, consumed_looks=2),
    lambda r: r["budget"].update(maximum_looks=0), lambda r: r.update(sequence=True),
])
def test_access_budget_and_predecessor_corruption_refuses(records, mutate):
    mutate(records["access"])
    with pytest.raises(e0.E0ControlError):
        join(records)


def test_unfavorable_access_state_is_metadata_not_an_admission(records):
    records["access"].update(status="revoked", contamination_state="contaminated")
    assert join(records)["operational_admission"] is False


def test_duplicate_closure_digest_with_changed_alias_refuses(records):
    alias = copy.deepcopy(records["closure"]["checked_objects"][0])
    alias["object_id"] = "another-alias"
    records["closure"]["checked_objects"].append(alias)
    with pytest.raises(e0.E0ControlError, match="duplicate_object_digest"):
        e0.validate_e0_control_record(records["closure"], kind="prelabel_closure")


def test_non_native_deep_cyclic_and_invalid_unicode_inputs_refuse(records):
    class PretendDict(dict):
        pass
    for bad in (PretendDict(records["registration"]), {"x": float("nan")}, {"x": "\ud800"}):
        with pytest.raises(e0.E0ControlError):
            e0.validate_e0_registration(bad)
    cycle = {}
    cycle["cycle"] = cycle
    with pytest.raises(e0.E0ControlError, match="cyclic"):
        e0.validate_e0_registration(cycle)
    deep = {}
    for _ in range(33):
        deep = {"deeper": deep}
    with pytest.raises(e0.E0ControlError, match="complexity"):
        e0.validate_e0_registration(deep)


def test_unknown_kind_and_oversized_input_refuse_without_schema_resolution(records, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("schema resolution must not precede input limits")
    monkeypatch.setattr(e0, "_validator", forbidden)
    with pytest.raises(e0.E0ControlError, match="unsupported"):
        e0.validate_e0_control_record(records["registration"], kind="../../private")
    with pytest.raises(e0.E0ControlError, match="bounded_control_bytes"):
        e0.parse_e0_control_record(b" " * (e0.MAX_CONTROL_BYTES + 1), kind="registration")


# Outcome-blind domain-reference resolution; original artifacts below are test inputs only.
ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/market_memory_e0"


def reference(body, schema="synthetic.domain.v1", identity="synthetic-domain"):
    return {"schema": schema, "object_id": identity,
            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


@pytest.fixture
def bundle(records):
    reg = copy.deepcopy(records["registration"])
    objects = {}

    def add(body, schema="synthetic.domain.v1", identity="synthetic-domain"):
        ref = reference(body, schema, identity)
        objects[ref["sha256"]] = body
        return ref

    body = (FIXTURES / "E0_ACTUAL_METADATA_MEMBERSHIP.json").read_bytes()
    reg["corpus"]["membership_ref"] = add(
        body, "market_memory.e0_original_owner_metadata_membership.v1", "original109-metadata")
    body = (ROOT / "research/market_memory/RETRIEVAL_PROTOCOL_2026_10_12.json").read_bytes()
    reg["design_ref"] = add(body, "market_memory.research_protocol_design.v1",
                            "market-memory-retrieval-evidence-e0-20261012")
    for key in e0._DOMAIN_KEYS:
        if key != "design_ref":
            reg[key] = add(canonical({"schema": "synthetic.domain.v1", "object_id": key}), identity=key)
    for key in ("algorithm_ref", "assignment_ref"):
        reg["allocation"][key] = add(canonical({"object_id": key}), identity=key)
    for key in ("method_ref", "code_ref", "dependencies_ref"):
        reg["implementation"][key] = add(canonical({"object_id": key}), identity=key)
    reg["implementation"]["baseline_refs"] = [add(
        b"raise AssertionError('opaque baseline must never execute')", "python.source.v1", "baseline-source")]
    # Diagnostic input is separate: the real design binding is not a reviewer plan.
    prelabel = (FIXTURES / "E0_PRELABEL_DESIGN_BINDING_V1.json").read_bytes()
    guide = (FIXTURES / "E0_ANNOTATION_GUIDE_PRELABEL_V1.md").read_bytes()
    objects[hashlib.sha256(guide).hexdigest()] = guide
    return reg, objects, prelabel


def resolve(bundle):
    reg, objects, prelabel = bundle
    return e0.resolve_e0_domain_references(registration=reg, objects=objects, prelabel_design=prelabel)


def test_exact_frozen_reference_closure_is_not_semantic_completeness_or_admission(bundle):
    result = resolve(bundle)
    assert result["references_complete"] is True
    assert result["missing_references"] == []
    assert result["frozen_artifacts_resolved"] == ["annotation_guide", "design", "membership", "prelabel_binding"]
    assert result["domain_metadata_complete"] is result["operational_admission"] is False
    assert "episode_clusters_and_interval_splits" in result["unresolved_semantics"]
    assert "exact_durable_reservation" in result["unverified_obligations"]
    # Preserve the actual null metadata, rather than filling it from UTC dates.
    original = json.loads(bundle[1][e0._FROZEN_DOMAIN_DIGESTS["membership"]])
    assert len(original["ordered_membership"]) == 109
    assert all(row["source_measurement_session"] is None for row in original["query_candidates"])
    assert all(row["feature_support_interval"] is None for row in original["query_candidates"])
    assert bundle[0]["allocation"]["seed_hex"] == "7c8013e1e8092bdf91d4598a73c01d9690199dfb6c08db632b81f564367a4b03"
    assert {"field": "membership.source_measurement_session", "missing_rows": 109} in result["frozen_metadata_gaps"]
    assert {"field": "prelabel_binding.condition_allocation", "missing_rows": 1} in result["frozen_metadata_gaps"]
    assert "ordered_membership" not in json.dumps(result)


@pytest.mark.parametrize("role", ["tasks_ref", "design_ref", "membership_ref", "guide_ref"])
def test_absent_bytes_are_unresolved_and_do_not_certify_domains(bundle, role):
    reg, objects, prelabel = bundle
    if role == "membership_ref":
        digest = reg["corpus"][role]["sha256"]
    elif role == "guide_ref":
        digest = e0._FROZEN_DOMAIN_DIGESTS["annotation_guide"]
    else:
        digest = reg[role]["sha256"]
    del objects[digest]
    result = resolve(bundle)
    assert result["references_complete"] is False
    if role == "guide_ref":
        assert result["missing_frozen_artifacts"] == ["annotation_guide"]
    else:
        assert [ref["sha256"] for ref in result["missing_references"]] == [digest]
    assert result["domain_metadata_complete"] is result["operational_admission"] is False


@pytest.mark.parametrize("mutate", [
    lambda r, o: o.update({r["tasks_ref"]["sha256"]: b"wrong bytes"}),
    lambda r, o: r["tasks_ref"].update(bytes=r["tasks_ref"]["bytes"] + 1),
    lambda r, o: r["design_ref"].update(sha256="a" * 64),
    lambda r, o: r["corpus"]["membership_ref"].update(sha256="a" * 64),
    lambda r, o: r["design_ref"].update(schema="wrong.schema"),
    lambda r, o: r["design_ref"].update(object_id="wrong-protocol"),
    lambda r, o: r["implementation"].update(method_ref={**r["tasks_ref"], "object_id": "alias"}),
])
def test_supplied_contradictions_raise_instead_of_becoming_missing(bundle, mutate):
    mutate(*bundle[:2])
    with pytest.raises(e0.E0ControlError):
        resolve(bundle)


@pytest.mark.parametrize("body", [
    b'{"object_id":"tasks_ref","object_id":"tasks_ref"}',
    b'{"object_id":"tasks_ref","number":NaN}',
    b'{"object_id":"tasks_ref"}\n',
    b'[source code rather than JSON',
])
def test_unsupported_schema_bytes_stay_opaque_even_when_starting_like_json(bundle, body):
    reg, objects, prelabel = bundle
    del objects[reg["tasks_ref"]["sha256"]]
    reg["tasks_ref"] = reference(body, "unsupported.source.v1", "tasks_ref")
    objects[reg["tasks_ref"]["sha256"]] = body
    result = resolve(bundle)
    assert result["references_complete"] is True
    assert "unsupported.source.v1" in result["unparsed_reference_schemas"]
    assert result["domain_metadata_complete"] is False


def test_prelabel_design_is_a_bounded_diagnostic_not_a_reviewer_plan(bundle):
    reg, objects, prelabel = bundle
    design_ref = reference(prelabel, "market_memory.e0_prelabel_design_binding.v1", "misbound-design")
    reg["reviewer_plan_ref"] = design_ref
    objects[design_ref["sha256"]] = prelabel
    with pytest.raises(e0.E0ControlError, match="role_mismatch"):
        resolve(bundle)
    with pytest.raises(e0.E0ControlError, match="prelabel_design_bytes_mismatch"):
        e0.resolve_e0_domain_references(registration=records_registration(bundle), objects={},
                                        prelabel_design=prelabel + b"\n")


def records_registration(bundle):
    reg = copy.deepcopy(bundle[0])
    reg["reviewer_plan_ref"] = reference(b"opaque reviewer plan", identity="reviewer_plan_ref")
    return reg


def test_known_wrong_schema_is_contradiction_even_when_bytes_missing(bundle):
    reg, objects, prelabel = bundle
    del objects[reg["design_ref"]["sha256"]]
    reg["design_ref"]["schema"] = "unsupported.wrong.schema"
    with pytest.raises(e0.E0ControlError, match="schema_identity_mismatch"):
        resolve(bundle)


def test_extra_objects_are_not_silently_scanned_as_evaluation_inputs(bundle):
    bundle[1]["f" * 64] = b"unreferenced payload"
    with pytest.raises(e0.E0ControlError, match="unreferenced"):
        resolve(bundle)


def test_bounds_precede_domain_parsing(bundle, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("domain parsing must follow input limits")
    monkeypatch.setattr(e0, "_domain_json", forbidden)
    reg, objects, prelabel = bundle
    with pytest.raises(e0.E0ControlError, match="bounded_domain_objects"):
        e0.resolve_e0_domain_references(registration=reg, objects={str(i): b"x" for i in range(65)})
    with pytest.raises(e0.E0ControlError, match="bounded_domain_bytes"):
        e0.resolve_e0_domain_references(registration=reg, objects={"a" * 64: b"x" * (e0.MAX_DOMAIN_OBJECT_BYTES + 1)})
    monkeypatch.setattr(e0, "MAX_DOMAIN_TOTAL_BYTES", 10)
    with pytest.raises(e0.E0ControlError, match="aggregate_domain_byte"):
        resolve(bundle)


def test_resolution_does_not_open_paths_or_execute_opaque_code_and_returns_detached_refs(bundle, monkeypatch):
    e0.validate_e0_registration(bundle[0])  # Warm only the existing public schema loader.
    def forbidden(*args, **kwargs):
        pytest.fail("reference resolution has no filesystem/network execution seam")
    monkeypatch.setattr(Path, "open", forbidden)
    result = resolve(bundle)
    result["resolved_references"][0]["object_id"] = "caller-mutated"
    assert all(ref["object_id"] != "caller-mutated" for ref in resolve(bundle)["resolved_references"])


def test_real_markdown_digest_link_and_seed_binding_without_invented_reference_tuple(bundle):
    binding = json.loads((FIXTURES / "E0_PRELABEL_DESIGN_BINDING_V1.json").read_bytes())
    assert type(binding["annotation_guide_sha256"]) is str
    assert binding["condition_seed"]["seed"] == bundle[0]["allocation"]["seed_hex"]
    assert binding["protocol_design_sha256"] == bundle[0]["design_ref"]["sha256"]
    assert binding["actual_membership_sha256"] == bundle[0]["corpus"]["membership_sha256"]
    result = resolve(bundle)
    assert "annotation_guide" in result["frozen_artifacts_resolved"]
    bundle[1][binding["annotation_guide_sha256"]] += b"\n"
    with pytest.raises(e0.E0ControlError, match="guide_bytes"):
        resolve(bundle)


def test_unknown_schema_does_not_claim_transitive_reference_closure(bundle):
    reg, objects, prelabel = bundle
    del objects[reg["tasks_ref"]["sha256"]]
    child_body = b"must not be interpreted"
    child = reference(child_body, "unsupported.child.v1", "child")
    body = canonical({"nested": child})
    reg["tasks_ref"] = reference(body, "unsupported.json.v1", "tasks_ref")
    objects[reg["tasks_ref"]["sha256"]] = body
    result = resolve(bundle)
    assert result["reference_scope"] == "registration_refs_and_known_domain_digest_links"
    assert "unsupported.json.v1" in result["unparsed_reference_schemas"]
    assert child not in result["missing_references"]
    objects[child["sha256"]] = child_body
    with pytest.raises(e0.E0ControlError, match="unreferenced"):
        resolve(bundle)


def test_explicit_prelabel_input_shares_object_and_aggregate_bounds(bundle, monkeypatch):
    reg, objects, prelabel = bundle
    with monkeypatch.context() as patch:
        patch.setattr(e0, "MAX_DOMAIN_OBJECTS", len(objects))
        with pytest.raises(e0.E0ControlError, match="bounded_domain_objects"):
            resolve(bundle)
    with monkeypatch.context() as patch:
        patch.setattr(e0, "MAX_DOMAIN_TOTAL_BYTES", sum(map(len, objects.values())) + len(prelabel) - 1)
        with pytest.raises(e0.E0ControlError, match="aggregate_domain_byte"):
            resolve(bundle)


@pytest.fixture
def task_bundle(bundle):
    """Synthetic task declaration only; real metadata identities are unchanged.

    This question is invented for testing. It is not an exported saved query,
    actual study task, answerability label or permission to read evidence.
    """
    membership = json.loads(bundle[1][e0._FROZEN_DOMAIN_DIGESTS["membership"]])
    row = membership["query_candidates"][0]
    identity = {key: row[key] for key in ("query_id", "context_id", "capture_id", "packet_sha256")}
    question = "Synthetic test question; no claim of answerability."
    value = {"schema": e0._TASK_SCHEMA, "object_id": "synthetic-tasks-only", "authority": "display_only",
             "protocol_sha256": e0._FROZEN_DOMAIN_DIGESTS["design"],
             "annotation_guide_sha256": e0._FROZEN_DOMAIN_DIGESTS["annotation_guide"],
             "membership_sha256": bundle[0]["corpus"]["membership_sha256"],
             "tasks": [{"task_id": "synthetic-task-1", **identity, **row["subject"],
                        "analysis_cutoff": row["first_available_for_contextual_analysis"],
                        "mode": "historical_hypothetical", "question": question,
                        "question_sha256": hashlib.sha256(question.encode()).hexdigest(),
                        "required_facet_ids": ["synthetic-facet"], "k": 1,
                        "original_evidence": [identity]}]}
    install_tasks(bundle, value)
    return bundle, value


def install_tasks(bundle, value, body=None):
    reg, objects, _prelabel = bundle
    objects.pop(reg["tasks_ref"]["sha256"], None)
    body = canonical(value) if body is None else body
    reg["tasks_ref"] = reference(body, e0._TASK_SCHEMA, value["object_id"])
    objects[reg["tasks_ref"]["sha256"]] = body


def test_task_contract_binds_frozen_sources_and_question_bytes_without_answerability(task_bundle):
    bundle, value = task_bundle
    result = resolve(bundle)
    assert result["references_complete"] is True
    assert e0._TASK_SCHEMA not in result["unparsed_reference_schemas"]
    assert result["task_binding_checks"] == [{"schema": e0._TASK_SCHEMA, "object_id": value["object_id"],
        "task_count": 1, "question_bytes_bound": True, "frozen_source_bindings_checked": True,
        "unresolved": [], "actual_task_selection_verified": False,
        "answerability_verified": False, "usefulness_verified": False}]
    assert result["operational_admission"] is result["domain_metadata_complete"] is False
    assert "tasks_and_query_selection" in result["unresolved_semantics"]
    # No supplied question/evidence bodies or fabricated interval metadata escape.
    assert value["tasks"][0]["question"] not in json.dumps(result)
    assert {"field": "membership.feature_support_interval", "missing_rows": 109} in result["frozen_metadata_gaps"]
    result["task_binding_checks"][0]["task_count"] = 999
    assert resolve(bundle)["task_binding_checks"][0]["task_count"] == 1


@pytest.mark.parametrize("mutate,error", [
    (lambda v: v["tasks"][0].update(question_sha256="f" * 64), "question_digest"),
    (lambda v: v["tasks"][0].update(question=" "), "question_required"),
    (lambda v: v["tasks"][0].update(query_id="mmquery_" + "f" * 64), "source_identity"),
    (lambda v: v["tasks"][0].update(context_id="mmctx_" + "f" * 64), "source_identity"),
    (lambda v: v["tasks"][0].update(capture_id="mmcapture_" + "f" * 64), "source_identity"),
    (lambda v: v["tasks"][0].update(packet_sha256="f" * 64), "source_identity"),
    (lambda v: v["tasks"][0].update(subject_id="mmsecurity_" + "f" * 64), "subject_identity"),
    (lambda v: v["tasks"][0].update(instrument_id="mmsecurity_" + "f" * 64), "subject_identity"),
    # Matching the older feature/event clock cannot backdate contextual availability.
    (lambda v: v["tasks"][0].update(analysis_cutoff="2026-09-25T01:18:09.907914Z"), "unavailable_at_cutoff"),
    (lambda v: v["tasks"][0].update(analysis_cutoff="2026-09-25T01:18:10Z"), "microsecond"),
    (lambda v: v["tasks"][0]["original_evidence"][0].update(packet_sha256="f" * 64), "source_identity"),
    (lambda v: v["tasks"].append(copy.deepcopy(v["tasks"][0])), "duplicate_task"),
    (lambda v: v["tasks"][0].update(k=True), "task_schema"),
    (lambda v: v["tasks"][0].update(k=9), "task_schema"),
    (lambda v: v["tasks"][0].update(required_facet_ids=["same", "same"]), "task_schema"),
    (lambda v: v["tasks"][0].update(task_id="bad\n"), "bounded_identifier"),
    (lambda v: v["tasks"][0]["original_evidence"][0].update(query_id="mmquery_" + "f" * 64 + "\n"), "exact_source_identity"),
    (lambda v: v["tasks"][0].update(answerability="answerable"), "task_schema"),
    (lambda v: v.update(membership_sha256="f" * 64), "task_schema"),
    (lambda v: v.update(protocol_sha256="f" * 64), "task_schema"),
    (lambda v: v.update(annotation_guide_sha256="f" * 64), "task_schema"),
])
def test_task_contract_rejects_metadata_contradictions(task_bundle, mutate, error):
    bundle, value = task_bundle
    mutate(value)
    install_tasks(bundle, value)
    with pytest.raises(e0.E0ControlError, match=error):
        resolve(bundle)


def test_task_evidence_uses_each_original_availability_clock(task_bundle):
    bundle, value = task_bundle
    rows = json.loads(bundle[1][e0._FROZEN_DOMAIN_DIGESTS["membership"]])["query_candidates"]
    later = max(rows, key=lambda row: row["first_available_for_contextual_analysis"])
    assert later["first_available_for_contextual_analysis"] > value["tasks"][0]["analysis_cutoff"]
    value["tasks"][0]["original_evidence"] = [{key: later[key] for key in
        ("query_id", "context_id", "capture_id", "packet_sha256")}]
    install_tasks(bundle, value)
    with pytest.raises(e0.E0ControlError, match="unavailable_at_cutoff"):
        resolve(bundle)
    value["tasks"][0]["analysis_cutoff"] = later["first_available_for_contextual_analysis"]
    install_tasks(bundle, value)
    assert resolve(bundle)["task_binding_checks"][0]["frozen_source_bindings_checked"] is True


def test_missing_membership_never_launders_supplied_tasks_as_verified_sources(task_bundle):
    bundle, value = task_bundle
    del bundle[1][e0._FROZEN_DOMAIN_DIGESTS["membership"]]
    value["tasks"][0]["query_id"] = "mmquery_" + "f" * 64
    install_tasks(bundle, value)
    result = resolve(bundle)
    assert result["references_complete"] is False
    checks = result["task_binding_checks"][0]
    assert checks["question_bytes_bound"] is True
    assert checks["frozen_source_bindings_checked"] is False
    assert checks["unresolved"] == ["frozen_membership_bytes"]
    assert result["operational_admission"] is False


def test_known_task_schema_is_role_bound_even_without_supplied_bytes(task_bundle):
    bundle, _value = task_bundle
    bundle[0]["reviewer_plan_ref"] = bundle[0]["tasks_ref"]
    del bundle[1][bundle[0]["tasks_ref"]["sha256"]]
    with pytest.raises(e0.E0ControlError, match="task_reference_role"):
        resolve(bundle)


@pytest.mark.parametrize("body", [b'{"schema":"research_factory.market_memory_e0_tasks.v1"}', b'null'])
def test_known_task_schema_rejects_malformed_payloads(task_bundle, body):
    bundle, value = task_bundle
    install_tasks(bundle, value, body)
    with pytest.raises(e0.E0ControlError):
        resolve(bundle)


def test_task_question_identity_is_not_evidence_truth_or_answerability(task_bundle):
    bundle, value = task_bundle
    # Deliberately unanswerable supplied text can bind bytes; no truth inference.
    question = "合成测试：这是一个未证明可回答的问题。"
    value["tasks"][0].update(question=question, question_sha256=hashlib.sha256(question.encode()).hexdigest())
    install_tasks(bundle, value)
    checks = resolve(bundle)["task_binding_checks"][0]
    assert checks["question_bytes_bound"] is True
    assert checks["answerability_verified"] is checks["usefulness_verified"] is False


def test_task_parser_rejects_duplicate_keys(task_bundle):
    bundle, value = task_bundle
    body = canonical(value)
    body = b'{"object_id":"duplicate",' + body[1:]
    install_tasks(bundle, value, body)
    with pytest.raises(e0.E0ControlError, match="invalid_domain_json"):
        resolve(bundle)


def test_task_bytes_are_canonical_and_guide_link_is_not_invented_prelabel_role(task_bundle, monkeypatch):
    bundle, value = task_bundle
    install_tasks(bundle, value, canonical(value) + b"\n")
    with pytest.raises(e0.E0ControlError, match="noncanonical_task"):
        resolve(bundle)
    install_tasks(bundle, value)
    # The task schema's exact guide digest is a supported link without prelabel input.
    bundle = (bundle[0], bundle[1], None)
    e0._task_validator()  # Public schema load is the only additional filesystem use.
    def forbidden(*args, **kwargs):
        pytest.fail("task metadata must not read stores or execute code")
    monkeypatch.setattr(Path, "open", forbidden)
    result = resolve(bundle)
    assert result["task_binding_checks"][0]["frozen_source_bindings_checked"] is True
    assert "annotation_guide" in result["frozen_artifacts_resolved"]
    del bundle[1][e0._FROZEN_DOMAIN_DIGESTS["annotation_guide"]]
    result = resolve(bundle)
    assert result["references_complete"] is False
    assert result["missing_frozen_artifacts"] == ["annotation_guide"]


def install_reviewer_plan(bundle, value, body=None):
    reg, objects, _prelabel = bundle
    objects.pop(reg["reviewer_plan_ref"]["sha256"], None)
    body = canonical(value) if body is None else body
    reg["reviewer_plan_ref"] = reference(body, e0._REVIEWER_PLAN_SCHEMA, value["object_id"])
    objects[reg["reviewer_plan_ref"]["sha256"]] = body


@pytest.fixture
def reviewer_bundle(task_bundle):
    """Invented actors/assignments for contract testing, never real reviewers."""
    bundle, tasks = task_bundle
    participants = []
    for actor in ("synthetic-reviewer-1", "synthetic-reviewer-2", "synthetic-adjudicator"):
        participant = {}
        for field in ("principal_ref", "qualification_ref", "independence_ref"):
            body = canonical({"synthetic_only": True, "actor": actor, "evidence_kind": field})
            identity = actor if field == "principal_ref" else actor + ":" + field
            participant[field] = reference(body, "synthetic.reviewer_evidence.v1", identity)
            bundle[1][participant[field]["sha256"]] = body
        participants.append(participant)
    plan = {"schema": e0._REVIEWER_PLAN_SCHEMA, "object_id": "synthetic-reviewer-plan-only",
            "authority": "display_only", "study_id": bundle[0]["study_id"],
            "preregistered_at": "2026-10-13T23:59:00.000000Z",
            "protocol_sha256": e0._FROZEN_DOMAIN_DIGESTS["design"],
            "annotation_guide_sha256": e0._FROZEN_DOMAIN_DIGESTS["annotation_guide"],
            "membership_sha256": bundle[0]["corpus"]["membership_sha256"],
            "tasks_ref": copy.deepcopy(bundle[0]["tasks_ref"]),
            "reviewers": participants[:2], "adjudicator": participants[2],
            "assignments": [{"task_id": task["task_id"],
                "reviewer_principal_ids": [p["principal_ref"]["object_id"] for p in participants[:2]],
                "adjudicator_principal_id": participants[2]["principal_ref"]["object_id"]}
                for task in tasks["tasks"]],
            "blinding": {"method_identity_suppressed": True, "provider_identity_suppressed": True,
                "later_outcome_values_suppressed": True, "peer_provisional_ratings_visible": False,
                "original_ratings_retained": True, "adjudication_reasons_retained": True}}
    install_reviewer_plan(bundle, plan)
    return bundle, plan


def test_reviewer_plan_closes_real_frozen_guide_tasks_and_corpus_but_authenticates_no_people(reviewer_bundle):
    bundle, plan = reviewer_bundle
    result = resolve(bundle)
    check = result["reviewer_plan_binding_checks"][0]
    assert result["references_complete"] is True
    assert check["assigned_task_count"] == check["declared_adjudicator_count"] == 1
    assert check["declared_reviewer_count"] == 2
    assert check["declared_principal_references_distinct"] is True
    assert check["exact_task_coverage_checked"] is check["frozen_membership_binding_checked"] is True
    assert check["declared_blinding_matches_guide"] is True and check["unresolved"] == []
    for key in ("authenticated_identities_verified", "qualifications_verified", "independence_verified",
                "packet_blinding_verified", "prelabel_timing_authenticated", "actual_assignment_executed",
                "operational_admission"):
        assert check[key] is False
    assert result["domain_metadata_complete"] is result["operational_admission"] is False
    assert "reviewer_plan_and_independence" in result["unresolved_semantics"]
    assert "annotation_guide" in result["frozen_artifacts_resolved"]
    assert {"field": "prelabel_binding.real_reviewer_assignment", "missing_rows": 1} in result["frozen_metadata_gaps"]
    assert plan["reviewers"][0]["principal_ref"]["object_id"] not in json.dumps(check)
    assert "synthetic.reviewer_evidence.v1" in result["unparsed_reference_schemas"]


@pytest.mark.parametrize("change", [
    lambda p: p["reviewers"].pop(),
    lambda p: p["reviewers"].append(copy.deepcopy(p["adjudicator"])),
    lambda p: p["reviewers"][0].pop("qualification_ref"),
    lambda p: p["adjudicator"].pop("independence_ref"),
    lambda p: p["reviewers"][0]["principal_ref"].update(bytes=True),
    lambda p: p.update(authority="operational"),
    lambda p: p.update(actual_ratings=[]),
    lambda p: p.update(protocol_sha256="a" * 64),
    lambda p: p.update(annotation_guide_sha256="b" * 64),
    lambda p: p.update(membership_sha256="c" * 64),
    *[lambda p, key=key: p["blinding"].update({key: not p["blinding"][key]})
      for key in ("method_identity_suppressed", "provider_identity_suppressed",
                  "later_outcome_values_suppressed", "peer_provisional_ratings_visible",
                  "original_ratings_retained", "adjudication_reasons_retained")],
])
def test_reviewer_plan_requires_evidence_declared_blinding_and_no_annotation_payload(reviewer_bundle, change):
    bundle, plan = reviewer_bundle
    change(plan)
    install_reviewer_plan(bundle, plan)
    with pytest.raises(e0.E0ControlError, match="reviewer_plan_schema"):
        resolve(bundle)


@pytest.mark.parametrize("change,reason", [
    (lambda p: p["reviewers"][1].update(principal_ref=copy.deepcopy(p["reviewers"][0]["principal_ref"])), "distinct_principal"),
    (lambda p: p["adjudicator"].update(principal_ref=copy.deepcopy(p["reviewers"][0]["principal_ref"])), "distinct_principal"),
    (lambda p: p["reviewers"][1]["principal_ref"].update(sha256=p["reviewers"][0]["principal_ref"]["sha256"]), "distinct_principal"),
    (lambda p: p["assignments"].append(copy.deepcopy(p["assignments"][0])), "duplicate_task"),
    (lambda p: p["assignments"][0].update(reviewer_principal_ids=["unregistered-one", "unregistered-two"]), "assignment_principal"),
    (lambda p: p["assignments"][0].update(adjudicator_principal_id=p["reviewers"][0]["principal_ref"]["object_id"]), "assignment_principal"),
    (lambda p: p["assignments"][0].update(task_id="unregistered-task"), "exact_task_coverage"),
    (lambda p: p.update(study_id="another-study"), "study_mismatch"),
    (lambda p: p.update(preregistered_at="2026-10-14T00:00:00.000001Z"), "declared_after_registration"),
    (lambda p: p.update(preregistered_at="2026-10-13T23:59:00+00:00"), "canonical_microsecond"),
    (lambda p: p["tasks_ref"].update(object_id="wrong-tasks"), "domain_binding"),
])
def test_reviewer_plan_rejects_knowable_contradictions(reviewer_bundle, change, reason):
    bundle, plan = reviewer_bundle
    change(plan)
    install_reviewer_plan(bundle, plan)
    with pytest.raises(e0.E0ControlError, match=reason):
        resolve(bundle)


@pytest.mark.parametrize("missing,unresolved", [
    ("tasks", "declared_tasks_bytes"), ("membership", "frozen_membership_bytes"),
    ("annotation_guide", "frozen_annotation_guide_bytes"),
    ("evidence", "reviewer_identity_qualification_independence_evidence_bytes"),
])
def test_missing_reviewer_dependencies_remain_explicit_unknowns(reviewer_bundle, missing, unresolved):
    bundle, plan = reviewer_bundle
    digest = (plan["tasks_ref"]["sha256"] if missing == "tasks" else
              plan["reviewers"][0]["qualification_ref"]["sha256"] if missing == "evidence" else
              e0._FROZEN_DOMAIN_DIGESTS[missing])
    del bundle[1][digest]
    result = resolve(bundle)
    assert result["references_complete"] is False
    check = result["reviewer_plan_binding_checks"][0]
    assert unresolved in check["unresolved"] and check["operational_admission"] is False
    if missing == "tasks":
        assert check["exact_task_coverage_checked"] is False
    if missing == "membership":
        assert check["frozen_membership_binding_checked"] is False


def test_reviewer_plan_known_role_mismatch_is_rejected_before_absent_bytes(reviewer_bundle):
    bundle, _plan = reviewer_bundle
    ref = bundle[0]["reviewer_plan_ref"]
    bundle[0]["source_coverage_ref"] = copy.deepcopy(ref)
    del bundle[1][ref["sha256"]]
    with pytest.raises(e0.E0ControlError, match="reviewer_plan_reference_role"):
        resolve(bundle)


def test_reviewer_evidence_cannot_smuggle_a_known_task_domain_even_without_bytes(reviewer_bundle):
    bundle, plan = reviewer_bundle
    plan["reviewers"][0]["qualification_ref"] = copy.deepcopy(plan["tasks_ref"])
    del bundle[1][plan["tasks_ref"]["sha256"]]
    install_reviewer_plan(bundle, plan)
    with pytest.raises(e0.E0ControlError, match="task_reference_role"):
        resolve(bundle)


def test_reviewer_evidence_bytes_are_checked_but_not_interpreted_as_qualifications(reviewer_bundle):
    bundle, plan = reviewer_bundle
    old = plan["reviewers"][0]["qualification_ref"]
    del bundle[1][old["sha256"]]
    body = b'{invalid JSON; opaque bytes cannot certify qualifications'
    plan["reviewers"][0]["qualification_ref"] = reference(body, "unsupported.qualification.v1", old["object_id"])
    bundle[1][hashlib.sha256(body).hexdigest()] = body
    install_reviewer_plan(bundle, plan)
    check = resolve(bundle)["reviewer_plan_binding_checks"][0]
    assert check["qualifications_verified"] is False
    bundle[1][hashlib.sha256(body).hexdigest()] = body + b"changed"
    with pytest.raises(e0.E0ControlError, match="domain_reference_bytes"):
        resolve(bundle)


def test_reviewer_plan_is_canonical_and_has_no_identity_store_or_annotation_io(reviewer_bundle, monkeypatch):
    bundle, plan = reviewer_bundle
    install_reviewer_plan(bundle, plan, canonical(plan) + b"\n")
    with pytest.raises(e0.E0ControlError, match="noncanonical_reviewer_plan"):
        resolve(bundle)
    install_reviewer_plan(bundle, plan)
    e0.validate_e0_registration(bundle[0])
    e0._task_validator()
    e0._reviewer_plan_validator()
    def forbidden(*args, **kwargs):
        pytest.fail("reviewer metadata cannot open identity/qualification/annotation stores")
    monkeypatch.setattr(Path, "open", forbidden)
    first = resolve(bundle)
    first["reviewer_plan_binding_checks"][0]["unresolved"].append("caller-mutated")
    assert resolve(bundle)["reviewer_plan_binding_checks"][0]["unresolved"] == []
