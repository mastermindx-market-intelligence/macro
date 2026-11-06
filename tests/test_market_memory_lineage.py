"""Certified successor tests exercise actual PIT/trusted producers and bytes."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from datetime import timedelta

import pytest

from engine.neuralweb import market_memory_lineage as lineage
from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted
from tests.test_market_memory_pit import _packet, _later_packet, _fixed_clock, CAPTURED_AT
from tests.test_market_memory_trusted import _candidate, _capture


class Policy:
    policy_id = "authenticated.test.application"

    def __init__(self, deny=False, revoke_after=None):
        self.calls = []
        self.deny = deny
        self.revoke_after = revoke_after

    def check(self, action, resource):
        self.calls.append((action, copy.deepcopy(resource)))
        if self.deny or (self.revoke_after is not None and len(self.calls) >= self.revoke_after):
            raise PermissionError("rights denied")


@pytest.fixture(params=["pit", "trusted"])
def owner(request, tmp_path, monkeypatch):
    if request.param == "pit":
        root = tmp_path / "pit"
        _fixed_clock(monkeypatch, CAPTURED_AT)
        captured = pit.capture_context(root, _packet())
        _fixed_clock(monkeypatch, CAPTURED_AT + timedelta(seconds=1))
        pit.capture_context(root, _later_packet(1))
        reader = pit.FileAsKnownAtReader(root)
    else:
        candidate = _candidate(monkeypatch, tmp_path)
        captured = _capture(candidate)
        root = candidate.public
        reader = trusted.TrustedFileAsKnownAtReader(root)
    return reader, captured


def qualify(reader, **kw):
    return reader.qualify_published_lineage(
        operation_ref="fixture.qualification.1", policy=Policy(),
        budget=lineage.OfflineQualificationBudget(), **kw)


def publish_fixture(reader, qualification):
    """Test-only publication; no production publication API is implemented."""
    certificate = lineage.build_lineage_certificate(qualification)
    body = lineage.canonical_bytes(certificate)
    pointer = lineage.build_lineage_head_pointer(certificate, publisher_revision="fixture.publisher.1")
    path = lineage.certificate_path(reader.root, certificate["certificate_id"])
    pit._write_create_once(reader.root, path, body, label="fixture lineage certificate")
    pit._write_create_once(reader.root, lineage.lineage_head_path(reader.root),
        lineage.canonical_bytes(pointer), label="fixture lineage pointer")
    return certificate, pointer


def test_real_owner_full_qualification_and_exact_capture(owner):
    reader, captured = owner
    qualification = qualify(reader)
    certificate, pointer = publish_fixture(reader, qualification)
    verification = certificate["verification"]
    assert verification["complete"] is True
    assert verification["genesis_verified"] is True
    assert verification["all_append_one_links_verified"] is True
    assert verification["cycle_depth_count_verified"] is True
    assert verification["batches"]
    generation_id = certificate["qualified_source_head"]["generation_id"]
    snapshot = lineage.read_certified_generation(reader, generation_id=generation_id,
        expected_certificate_ref=pointer["certificate_id"], policy=Policy())
    assert snapshot["state"] == "certified"
    result = lineage.read_certified_capture(reader, generation_id=generation_id,
        query_id=captured.capture_receipt["query_id"], policy=Policy())
    assert result["stored"].packet == captured.packet
    assert result["stored"].capture_receipt == captured.capture_receipt
    if type(reader) is trusted.TrustedFileAsKnownAtReader:
        assert result["feature"] is not None


def test_rights_denied_before_any_private_object_read(owner, monkeypatch):
    reader, captured = owner
    calls = []
    monkeypatch.setattr(pit, "_read_canonical_object", lambda *a, **k: calls.append(a) or pytest.fail("private read"))
    with pytest.raises(lineage.LineageRightsError):
        reader.qualify_published_lineage(operation_ref="denied", policy=Policy(deny=True),
            budget=lineage.OfflineQualificationBudget())
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader, generation_id="mmgeneration_" + "a" * 64,
            query_id=captured.capture_receipt["query_id"], policy=Policy(deny=True))
    assert calls == []


def test_revocation_at_disclosure_and_capture_resource(owner):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    policy = Policy(revoke_after=3)
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=policy)
    assert all(c[1].get("query_id") == captured.capture_receipt["query_id"] for c in policy.calls if c[1].get("query_id") is not None)


def test_actual_packet_corruption_cannot_hide_behind_asserted_digest(owner):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    digest = captured.capture_receipt["packet_sha256"]
    path = pit._object_path(reader.root, digest)
    path.write_bytes(b"{}")
    with pytest.raises(pit.MarketMemoryStoreError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=Policy())


def test_qualification_budget_and_expected_head_refuse_without_publication(owner):
    reader, _ = owner
    with pytest.raises(lineage.LineageBudgetError):
        reader.qualify_published_lineage(operation_ref="bounded", policy=Policy(),
            budget=lineage.OfflineQualificationBudget(total_bytes=1, batch_bytes=1))
    with pytest.raises(pit.MarketMemoryStoreError):
        qualify(reader, expected_head_body_sha256="0" * 64)
    assert not lineage.lineage_head_path(reader.root).exists()


def test_certificate_is_complete_only_from_real_qualification(owner):
    reader, _ = owner
    with pytest.raises(pit.MarketMemoryStoreError):
        lineage.build_lineage_certificate({"complete": True})
    certificate, pointer = publish_fixture(reader, qualify(reader))
    corrupted = copy.deepcopy(certificate)
    corrupted["verification"].pop("genesis_verified")
    with pytest.raises(pit.MarketMemoryStoreError):
        lineage.validate_certificate(corrupted)
    assert pointer["qualified_source_generation_id"] == certificate["qualified_source_head"]["generation_id"]


def test_rewritten_append_link_rejected_by_owner_qualifier(tmp_path, monkeypatch):
    root = tmp_path / "pit"
    _fixed_clock(monkeypatch, CAPTURED_AT)
    pit.capture_context(root, _packet())
    _fixed_clock(monkeypatch, CAPTURED_AT + timedelta(seconds=1))
    pit.capture_context(root, _later_packet(1))
    reader = pit.FileAsKnownAtReader(root)
    state = pit._load_store_state(root)
    # Structurally content-valid newest object, but it dropped an older capture.
    broken = pit._new_generation(store_id=state.manifest["store_id"],
        previous_generation_id=state.generation["previous_generation_id"],
        captures=state.generation["captures"][1:])
    body = pit._canonical_bytes(broken)
    path = pit._generation_path(root, broken["generation_id"])
    pit._write_create_once(root, path, body, label="fixture corrupt append generation")
    pit._replace_head(root, pit._new_head(broken, generation_body=body))
    with pytest.raises(pit.MarketMemoryStoreError, match="append|rewrites"):
        qualify(reader)


def test_proof_pending_preserves_historical_qualified_view(tmp_path, monkeypatch):
    root = tmp_path / "pit"
    _fixed_clock(monkeypatch, CAPTURED_AT)
    pit.capture_context(root, _packet())
    reader = pit.FileAsKnownAtReader(root)
    certificate, _ = publish_fixture(reader, qualify(reader))
    _fixed_clock(monkeypatch, CAPTURED_AT + timedelta(seconds=1))
    pit.capture_context(root, _later_packet(1))
    result = lineage.read_certified_generation(reader,
        generation_id=certificate["qualified_source_head"]["generation_id"], policy=Policy())
    assert result["state"] == "proof_pending"
    assert result["requested_generation"]["generation_id"] == certificate["qualified_source_head"]["generation_id"]
    active = reader.read_active_generation()
    with pytest.raises(pit.MarketMemoryStoreError, match="not certified"):
        lineage.read_certified_generation(reader, generation_id=active.generation_id, policy=Policy())


def test_v1_caps_and_schema_are_unchanged():
    assert pit._MAX_PIN_ANCESTRY_BYTES == 64 * 1024 * 1024
    assert pit._MAX_GENERATION_CAPTURES == 4096
    assert trusted.TRUSTED_STORE_PROFILE == "market_memory.trusted.macro_regime_canary.v1"


def test_declared_schemas_match_real_qualification(owner):
    from jsonschema import Draft202012Validator
    reader, _ = owner
    certificate, pointer = publish_fixture(reader, qualify(reader))
    base = Path(__file__).resolve().parents[1] / "contracts" / "market_memory"
    for name, value in (("lineage_certificate", certificate), ("lineage_head", pointer)):
        schema = json.loads((base / (name + ".v1.schema.json")).read_text())
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(value)


@pytest.mark.parametrize("fault", ["packet_missing", "receipt_extra", "alias_mismatch"])
def test_full_original_object_closure_faults_fail_closed(owner, fault):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    receipt = captured.capture_receipt
    if fault == "packet_missing":
        pit._object_path(reader.root, receipt["packet_sha256"]).unlink()
    elif fault == "receipt_extra":
        changed = dict(receipt, undocumented_private_payload="must not disclose")
        pit._query_path(reader.root, receipt["query_id"]).write_bytes(pit._canonical_bytes(changed))
    elif fault == "alias_mismatch":
        pit._context_path(reader.root, receipt["context_id"]).write_bytes(b"{}")
    with pytest.raises(pit.MarketMemoryStoreError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=receipt["query_id"], policy=Policy())


def test_actual_trusted_feature_corruption_refuses_disclosure(tmp_path, monkeypatch):
    candidate = _candidate(monkeypatch, tmp_path)
    captured = _capture(candidate)
    reader = trusted.TrustedFileAsKnownAtReader(candidate.public)
    certificate, _ = publish_fixture(reader, qualify(reader))
    trusted._feature_path(reader.root,
        captured.capture_receipt["feature_snapshot"]["content_sha256"]).write_bytes(b"{}")
    with pytest.raises(pit.MarketMemoryStoreError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=Policy())


@pytest.mark.parametrize("fault", ["orphan", "wrong_ref", "pointer_store", "certificate_bytes"])
def test_exact_published_proof_binding(owner, fault):
    reader, _ = owner
    certificate, pointer = publish_fixture(reader, qualify(reader))
    expected = None
    if fault == "orphan":
        lineage.certificate_path(reader.root, certificate["certificate_id"]).unlink()
    elif fault == "wrong_ref":
        expected = "mmcert_" + "0" * 64
    elif fault == "pointer_store":
        pointer["store_id"] = "mmstore_" + "0" * 64
        lineage.lineage_head_path(reader.root).write_bytes(lineage.canonical_bytes(pointer))
    else:
        lineage.certificate_path(reader.root, certificate["certificate_id"]).write_bytes(b"{}")
    with pytest.raises(pit.MarketMemoryStoreError):
        lineage.read_certified_generation(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            expected_certificate_ref=expected, policy=Policy())


def test_multiple_bounded_batches_account_every_input_byte(owner):
    reader, _ = owner
    source_objects = [reader.root / "store_manifest.json", reader.root / "HEAD.json",
                      *(reader.root / "generations").rglob("*.json")]
    maximum = max(path.stat().st_size for path in source_objects)
    result = reader.qualify_published_lineage(operation_ref="batched", policy=Policy(),
        budget=lineage.OfflineQualificationBudget(batch_bytes=max(maximum, 1024)))
    certificate = lineage.build_lineage_certificate(result)
    verification = certificate["verification"]
    assert len(verification["batches"]) > 1
    assert verification["total_input_bytes"] == sum(batch["input_bytes"] for batch in verification["batches"])
    assert all(batch["input_bytes"] <= max(maximum, 1024) for batch in verification["batches"])


def test_explicit_time_exhaustion_never_mints_complete_capability(owner, monkeypatch):
    reader, _ = owner
    calls = iter([0, 100, 200])
    monkeypatch.setattr(lineage.time, "process_time", lambda: next(calls))
    with pytest.raises(lineage.LineageBudgetError, match="time"):
        qualify(reader)
    assert not lineage.lineage_head_path(reader.root).exists()


def test_online_aggregate_bound_is_enforced_before_read(owner):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    # Genuine membership may be passed only within the admitted owner boundary.
    budget = lineage._ReadBudget()
    membership, _, _ = lineage._membership(reader,
        certificate["qualified_source_head"]["generation_id"], None, budget, policy=Policy())
    with pytest.raises(lineage.LineageBudgetError):
        reader.read_certified_capture(membership, query_id=captured.capture_receipt["query_id"],
            budget=lineage._ReadBudget(total_bytes=1), policy=Policy())


def test_asserted_callback_owner_and_boolean_policy_are_not_admission(owner):
    reader, _ = owner
    class FakeOwner:
        root = reader.root
    with pytest.raises(pit.MarketMemoryStoreError, match="concrete"):
        lineage.read_certified_generation(FakeOwner(), generation_id="mmgeneration_" + "a" * 64, policy=Policy())
    class BooleanPolicy(Policy):
        def check(self, action, resource):
            return True
    with pytest.raises(lineage.LineageRightsError):
        reader.qualify_published_lineage(operation_ref="boolean", policy=BooleanPolicy(),
            budget=lineage.OfflineQualificationBudget())


def test_json_boolean_alias_cannot_acquire_authority(owner):
    reader, _ = owner
    certificate = lineage.build_lineage_certificate(qualify(reader))
    certificate["authority"]["may_trade"] = 0
    certificate["certificate_id"] = lineage._content_id(certificate)
    with pytest.raises(pit.MarketMemoryStoreError, match="authority"):
        lineage.validate_certificate(certificate)


def test_rights_revoked_after_actual_packet_read_blocks_return(owner, monkeypatch):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    policy = Policy()
    original = pit._read_canonical_object
    packet_reads = []
    def revoke_after_packet(path, **kwargs):
        result = original(path, **kwargs)
        if "packet object" in kwargs["label"]:
            packet_reads.append(path)
            policy.deny = True
        return result
    monkeypatch.setattr(pit, "_read_canonical_object", revoke_after_packet)
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=policy)
    assert len(packet_reads) == 1


@pytest.mark.parametrize("boundary", ["subject", "source"])
def test_actual_capture_rights_precede_packet_and_feature_reads(owner, monkeypatch, boundary):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    subject = captured.capture_receipt["subject"]["subject_id"]
    source = captured.capture_receipt["source_receipt_ids"][0]
    class Restricted(Policy):
        def check(self, action, resource):
            if ((boundary == "subject" and resource.get("subject_id") == subject)
                    or (boundary == "source" and source in resource.get("source_receipt_ids", []))):
                raise PermissionError("actual capture rights denied")
            return super().check(action, resource)
    def forbidden(*args, **kwargs):
        pytest.fail("payload read before actual subject/source rights")
    monkeypatch.setattr(pit, "_load_stored_from_receipt", forbidden)
    monkeypatch.setattr(trusted, "_load_stored_with_feature", forbidden)
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=Restricted())


def test_capture_metadata_permission_precedes_receipt_read(owner, monkeypatch):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    original = pit._read_canonical_object
    def guarded(path, **kwargs):
        if kwargs["label"] == "certified original query receipt":
            pytest.fail("capture metadata read before permission")
        return original(path, **kwargs)
    monkeypatch.setattr(pit, "_read_canonical_object", guarded)
    class DeniedMetadata(Policy):
        def check(self, action, resource):
            if action == "read_market_memory_capture_metadata":
                raise PermissionError("capture metadata denied")
            return super().check(action, resource)
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=DeniedMetadata())


def test_disclosure_rechecks_actual_capture_rights(owner, monkeypatch):
    reader, captured = owner
    certificate, _ = publish_fixture(reader, qualify(reader))
    class RevokeOnDisclosure(Policy):
        def check(self, action, resource):
            if action == "disclose_market_memory_capture":
                assert resource["subject_id"] == captured.capture_receipt["subject"]["subject_id"]
                assert resource["source_receipt_ids"] == captured.capture_receipt["source_receipt_ids"]
                raise PermissionError("disclosure denied after permitted payload read")
            return super().check(action, resource)
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader,
            generation_id=certificate["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=RevokeOnDisclosure())


def test_qualification_head_observation_is_after_its_actual_read(owner, monkeypatch):
    reader, _ = owner
    original = lineage._owner_state
    observed = []
    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        observed.append(lineage._instant())
        return result
    monkeypatch.setattr(lineage, "_owner_state", observe)
    cert = lineage.build_lineage_certificate(qualify(reader))
    assert cert["qualified_source_head"]["observed_at"] >= observed[0]


@pytest.mark.parametrize("fault", ["missing_ranges", "wrong_first", "object_count"])
def test_certificate_batch_witnesses_cover_whole_chain(owner, fault):
    reader, _ = owner
    cert = lineage.build_lineage_certificate(qualify(reader))
    batch = next(b for b in cert["verification"]["batches"] if b["first_source_generation_id"])
    if fault == "missing_ranges":
        for item in cert["verification"]["batches"]:
            for key in ("first_source_generation_id", "last_source_generation_id",
                        "boundary_newer_generation_id", "boundary_older_generation_id"):
                item[key] = None
    elif fault == "wrong_first":
        batch["first_source_generation_id"] = cert["chain_links"][-1]["generation_id"]
    else:
        batch["input_object_count"] += 1
    cert["certificate_id"] = lineage._content_id(cert)
    with pytest.raises(pit.MarketMemoryStoreError):
        lineage.validate_certificate(cert)


def test_owned_proof_file_is_not_exact_publication_admission(owner, monkeypatch):
    reader, captured = owner
    cert, pointer = publish_fixture(reader, qualify(reader))
    class DeniedPublication(Policy):
        def check(self, action, resource):
            if action == "use_qualified_market_memory_lineage_certificate":
                assert resource["certificate_id"] == cert["certificate_id"]
                assert resource["certificate_sha256"] == pointer["certificate_sha256"]
                assert resource["publisher_revision"] == "fixture.publisher.1"
                assert resource["qualification_operation_ref"] == "fixture.qualification.1"
                raise PermissionError("qualification publication not admitted")
            return super().check(action, resource)
    def forbidden(*args, **kwargs):
        pytest.fail("requested generation read before exact publication admission")
    monkeypatch.setattr(reader, "read_certified_generation", forbidden)
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader,
            generation_id=cert["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=DeniedPublication())


def test_exact_publication_admission_is_rechecked_before_disclosure(owner, monkeypatch):
    reader, captured = owner
    cert, _ = publish_fixture(reader, qualify(reader))
    class RevokedPublication(Policy):
        admitted_once = False
        def check(self, action, resource):
            if action == "use_qualified_market_memory_lineage_certificate":
                if self.admitted_once:
                    raise PermissionError("publication admission revoked")
                self.admitted_once = True
            return super().check(action, resource)
    with pytest.raises(lineage.LineageRightsError):
        lineage.read_certified_capture(reader,
            generation_id=cert["qualified_source_head"]["generation_id"],
            query_id=captured.capture_receipt["query_id"], policy=RevokedPublication())
