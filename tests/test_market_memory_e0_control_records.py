"""Synthetic E0 metadata: structural validity must never grant label access."""
import copy
import hashlib
import json
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
