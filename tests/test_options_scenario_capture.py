"""Controlled producer/retainer composition; none of these seams is live authority."""
from copy import deepcopy
from dataclasses import replace
import json
from datetime import timedelta

import pytest
from engine import options_hub_retention as retention
from engine import options_scenario_capture as capture
from engine.intelligence_workspace import scenario_source_resolution as source
from tests.test_scenario_source_resolution import Harness, BASE, DECIDED
from tests.test_options_hub_retention import FakeS3, controlled_decision

OP = "10000000-0000-4000-8000-000000000001"


def world(with_moves=True):
    h = Harness(with_moves=with_moves)
    h.s3 = FakeS3()
    h.descriptor_owner = replace(h.descriptor, grant_id=None)
    h.reads, h.saves = [], []
    h.current = h.viewer
    def producer_read(kind):
        h.reads.append(kind)
        return h.gex_bytes if kind == "gex" else h.moves_bytes
    def save(binding):
        h.saves.append(deepcopy(binding))
        return {"status": "allowed", "binding": deepcopy(binding), "policy_id": "controlled-policy",
                "policy_revision": "controlled-rev", "registry_revision": "controlled-registry",
                "decided_at": DECIDED}
    h.params = dict(operation_id=OP, producer_read=producer_read, s3=h.s3, bucket="b",
                    destination=h.destination_qualifier, source_save_decision=save,
                    retention_decision=controlled_decision(), current_viewer=lambda: h.current,
                    clock=lambda: BASE)
    return h


def run(h, **overrides):
    return capture.capture_producer_sources(h.descriptor_owner, h.viewer, **{**h.params, **overrides})


@pytest.mark.parametrize("missing", ["producer_read", "s3", "bucket", "destination", "source_save_decision", "retention_decision", "current_viewer"])
def test_missing_binding_refuses_before_producer_or_protected_io(missing):
    h = world()
    with pytest.raises(capture.ProducerCaptureRefused, match="capture_binding_unavailable"):
        run(h, **{missing: None})
    assert not h.reads and not h.s3.log and not h.saves


def test_exact_sources_retained_before_reference_metadata_without_calculation_claim():
    h = world()
    result = run(h)
    assert h.reads == ["gex", "moves"]
    assert h.s3.objects[h.gex_ref.key] == h.gex_bytes
    assert h.s3.objects[h.moves_ref.key] == h.moves_bytes
    body = result.boundary()
    assert body["status"] == "sources_retained"
    assert body["basis_calculation_verified"] is False and body["canonical_save_performed"] is False
    assert body["gex"]["sha256"] == h.gex_ref.sha256
    assert body["moves"]["byte_length"] == len(h.moves_bytes)
    assert body["evaluated_at"] == h.descriptor_owner.evaluated_at
    assert body["lens"] == dict(h.descriptor_owner.lens)
    text = json.dumps(body)
    assert "600.25" not in text and "by_strike" not in text and "atm_iv" not in text
    binding = h.saves[0]
    assert binding["action"] == "save_scenario_sources" and binding["purpose"] == capture.SAVE_PURPOSE
    assert binding["operation_id"] == OP and binding["auth_epoch"] == h.viewer.auth_epoch
    assert all(kind == "put" for kind, _ in h.s3.log if kind != "get")


@pytest.mark.parametrize("action", ["evaluate", "display", "export"])
def test_existing_read_action_cannot_authorize_save(action):
    h = world()
    def wrong(binding):
        return {"status": "allowed", "binding": {**binding, "action": action}, "policy_id": "p",
                "policy_revision": "r", "registry_revision": "g", "decided_at": DECIDED}
    with pytest.raises(capture.ProducerCaptureRefused, match="save_decision_invalid"):
        run(h, source_save_decision=wrong)
    assert not h.reads and not h.s3.log


@pytest.mark.parametrize("status,code", [("denied", "save_denied"), ("unavailable", "save_unavailable"), ("unknown", "save_decision_invalid")])
def test_save_decision_outcomes_preserved(status, code):
    h = world()
    original = h.params["source_save_decision"]
    def denied(binding):
        return {**original(binding), "status": status}
    with pytest.raises(capture.ProducerCaptureRefused, match=code) as exc:
        run(h, source_save_decision=denied)
    assert exc.value.status == ("denied" if status == "denied" else "unavailable")
    assert not h.reads and not h.s3.log


def test_malformed_second_artifact_refuses_before_first_write():
    h = world()
    h.moves_bytes += b" "
    with pytest.raises(retention.RetentionUnavailable):
        run(h)
    assert h.reads == ["gex", "moves"] and not h.s3.log


def test_changed_gex_is_not_substituted_from_current_producer_head():
    h = world()
    h.gex_bytes = h.gex_bytes.replace(b"600.25", b"601.25")
    with pytest.raises(retention.RetentionUnavailable):
        run(h)
    assert not h.s3.log


def test_optional_moves_absence_is_explicit_and_does_not_read_moves():
    h = world(with_moves=False)
    body = run(h).boundary()
    assert body["moves"] is None and h.reads == ["gex"]


def test_actor_change_after_retention_withholds_metadata_without_claiming_rollback():
    h = world()
    original_put = h.s3.put_object
    def put(**kwargs):
        original_put(**kwargs)
        h.current = source.ViewerIdentity("another", "issuer", "epoch")
    h.s3.put_object = put
    with pytest.raises(capture.ProducerCaptureRefused, match="current_actor_changed"):
        run(h)
    # Retention occurred, but no canonical save/metadata success was returned.
    assert h.s3.objects[h.gex_ref.key] == h.gex_bytes


def test_second_put_uncertainty_propagates_original_effect_without_success():
    h = world()
    original_put = h.s3.put_object
    def put(**kwargs):
        if kwargs["Key"] == h.moves_ref.key:
            raise TimeoutError("controlled unknown effect")
        original_put(**kwargs)
    h.s3.put_object = put
    with pytest.raises(retention.RetentionUncertain):
        run(h)
    assert h.s3.objects[h.gex_ref.key] == h.gex_bytes
    assert h.moves_ref.key not in h.s3.objects


def test_immutable_context_survives_callback_mutation_and_has_no_recipient_save_authority():
    h = world()
    original = h.params["source_save_decision"]
    def mutate(binding):
        answer = original(binding)
        binding["lens"]["kind"] = "all"
        binding["refs"].clear()
        return answer
    result = run(h, source_save_decision=mutate)
    assert result.boundary()["lens"] == dict(h.descriptor_owner.lens)
    with pytest.raises(TypeError):
        result.descriptor.lens["kind"] = "all"
    h = world()
    h.descriptor_owner = replace(h.descriptor_owner, grant_id="20000000-0000-4000-8000-000000000002")
    with pytest.raises(capture.ProducerCaptureRefused, match="capture_intent_invalid"):
        run(h)
    assert not h.reads and not h.s3.log


def test_stale_save_decision_and_changed_source_clock_refuse():
    h = world()
    original = h.params["source_save_decision"]
    with pytest.raises(capture.ProducerCaptureRefused, match="save_decision_invalid"):
        run(h, source_save_decision=lambda binding: {**original(binding), "decided_at": (BASE-timedelta(seconds=1)).isoformat()})
    assert not h.reads
    h = world()
    payload = json.loads(h.gex_bytes)
    payload["exposure_projection"] = {"clocks": {"option_observed_at": "2026-10-22T20:00:00Z"}}
    h.gex_bytes = json.dumps(payload).encode()
    h.gex_ref = retention.reference_for_bytes("SPY", "gex", h.gex_bytes)
    h.descriptor_owner = replace(h.descriptor_owner, gex=h.gex_ref)
    with pytest.raises(capture.ProducerCaptureRefused, match="producer_source_clock_mismatch"):
        run(h)
    assert not h.s3.log


def test_actual_builder_serialization_and_deliberate_entry(tmp_path, monkeypatch):
    from scripts import build_options_hub_nightly as builder
    h = world()
    def forbidden(*args, **kwargs):
        raise AssertionError("capture must not rebuild, fetch or publish a public source")
    for name in ("_r2_client", "_upload_r2", "build_root", "moves_payload"):
        monkeypatch.setattr(builder, name, forbidden)
    gex_path, moves_path = tmp_path/"gex"/"SPY.json", tmp_path/"moves"/"SPY.json"
    builder._write_json(gex_path, json.loads(h.gex_bytes))
    builder._write_json(moves_path, json.loads(h.moves_bytes))
    h.gex_bytes, h.moves_bytes = gex_path.read_bytes(), moves_path.read_bytes()
    h.gex_ref = retention.reference_for_bytes("SPY", "gex", h.gex_bytes)
    h.moves_ref = retention.reference_for_bytes("SPY", "moves", h.moves_bytes)
    descriptor = replace(h.descriptor_owner, gex=h.gex_ref, moves=h.moves_ref)
    params = {key: value for key,value in h.params.items() if key != "producer_read"}
    result = builder.capture_built_scenario_sources(descriptor, h.viewer, out_dir=tmp_path, **params)
    assert result.boundary()["gex"]["sha256"] == h.gex_ref.sha256
    assert h.s3.objects[h.gex_ref.key] == gex_path.read_bytes()
    assert h.s3.objects[h.moves_ref.key] == moves_path.read_bytes()
    assert result.boundary()["canonical_save_performed"] is False


def test_builder_default_refuses_before_missing_files_or_linked_sources(tmp_path):
    from scripts import build_options_hub_nightly as builder
    h = world()
    with pytest.raises(capture.ProducerCaptureRefused, match="capture_binding_unavailable"):
        builder.capture_built_scenario_sources(h.descriptor_owner, h.viewer, operation_id=OP, out_dir=tmp_path/"absent")
    (tmp_path/"gex").mkdir()
    (tmp_path/"private").write_bytes(h.gex_bytes)
    (tmp_path/"gex"/"SPY.json").symlink_to(tmp_path/"private")
    params = {key: value for key,value in h.params.items() if key != "producer_read"}
    with pytest.raises(capture.ProducerCaptureRefused, match="producer_source_unavailable"):
        builder.capture_built_scenario_sources(h.descriptor_owner, h.viewer, out_dir=tmp_path, **params)
    assert not h.s3.log


def test_mixed_source_sessions_are_refused_before_any_producer_or_protected_io():
    h = world()
    payload = json.loads(h.moves_bytes)
    payload["asof"] = "2026-10-21"
    h.moves_bytes = json.dumps(payload).encode()
    h.moves_ref = retention.reference_for_bytes("SPY", "moves", h.moves_bytes)
    h.descriptor_owner = replace(h.descriptor_owner, moves=h.moves_ref)
    with pytest.raises(capture.ProducerCaptureRefused, match="capture_intent_invalid"):
        run(h)
    assert not h.reads and not h.s3.log


def test_lightweight_fixed_file_entry_refuses_before_io(tmp_path, monkeypatch):
    import builtins
    original_import = builtins.__import__
    def no_nightly_import(name, *args, **kwargs):
        if name == "scripts.build_options_hub_nightly":
            raise AssertionError("private ingress must not import the nightly builder")
        return original_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, "__import__", no_nightly_import)
    h = world()
    with pytest.raises(capture.ProducerCaptureRefused, match="capture_binding_unavailable"):
        capture.capture_built_scenario_sources(h.descriptor_owner, h.viewer,
            operation_id=OP, out_dir=tmp_path / "absent")
    assert not h.reads and not h.s3.log


def test_nightly_capture_entry_delegates_to_lightweight_fixed_file_seam(tmp_path, monkeypatch):
    from scripts import build_options_hub_nightly as builder
    h = world()
    calls = []
    sentinel = object()
    def shared(descriptor, viewer, **kwargs):
        calls.append((descriptor, viewer, kwargs))
        return sentinel
    monkeypatch.setattr(capture, "capture_built_scenario_sources", shared, raising=False)
    assert builder.capture_built_scenario_sources(h.descriptor_owner, h.viewer,
        operation_id=OP, out_dir=tmp_path) is sentinel
    assert calls == [(h.descriptor_owner, h.viewer, dict(operation_id=OP,
        out_dir=tmp_path, s3=None, bucket=None, destination=None,
        source_save_decision=None, retention_decision=None, current_viewer=None, clock=None))]
