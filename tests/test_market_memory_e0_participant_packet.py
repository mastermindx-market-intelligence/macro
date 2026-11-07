"""Real native synthetic captures -> task evidence -> selected packet vector.

Original fixtures explicitly substitute study-domain pins and source-use policy.
No issuer-service peer, selected recipient grant, runtime or study is simulated
as accepted. The vector proves the native packet boundary, not an issuer reply.
"""
import copy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from engine.research_factory import market_memory_e0_participant_packet as packet
from engine.research_factory import market_memory_e0_task_evidence as tasks
from engine.research_factory import market_memory_e0_condition_evidence as sources
from tests.test_market_memory_e0_task_evidence import request_data


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode() + packet.SUFFIX


def extract(body):
    return packet.extract_selected_citations(body, input_sha256=sha256(body).hexdigest())


def test_native_packet_and_immutable_synthetic_vector(request_data, tmp_path):
    cap = tasks.build_task_condition_evidence(**request_data)
    selected = []
    for condition in sources.CONDITIONS:
        view = tasks.disclose_task_condition_view(cap, condition=condition,
                                                 policy=request_data["policy"])
        raw = packet.build_task_condition_packet(cap, condition=condition,
                                                 policy=request_data["policy"])
        expected = {"schema": packet.SCHEMA, "task": view["task"],
                    "source_view": {k: v for k, v in view.items() if k != "task"}}
        assert raw == encode(expected) and raw.count(packet.SUFFIX) == 1
        descriptors = extract(raw)
        assert len(descriptors) == 5 * len(view["source_cards"])
        assert descriptors[0]["context_id"] == view["source_cards"][0]["context_id"]
        assert "original_evidence" not in expected["task"]
        assert expected["source_view"]["actual_blinding_established"] is False
        assert not ({"condition", "method_spec", "accounting"} & expected["source_view"].keys())
        for descriptor in descriptors:
            cite = descriptor["citation"]
            quoted = cite["quoted_json"].encode("utf-8")
            assert sha256(quoted).hexdigest() == cite["span_sha256"]
            assert len(quoted) == cite["end_byte_exclusive"] - cite["start_byte"]
        selected.append((raw, descriptors, expected))
    # Distinct allowed selections stay separate; the extractor never unions arms.
    assert [len(item[1]) for item in selected] == [5, 10, 10]
    raw, descriptors, _ = selected[-1]
    export = tmp_path / "synthetic-vector"
    export.mkdir(exist_ok=True)
    (export / "participant-input.bin").write_bytes(raw)
    (export / "selected-descriptors.json").write_text(
        json.dumps(list(descriptors), sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False, allow_nan=False))
    (export / "PROVENANCE.json").write_text(json.dumps({
        "schema": "market_memory.native_packet_source_fixture_vector.v1",
        "native_path": "synthetic TrustedFileAsKnownAtReader/captures/cohort/features -> "
            "build_condition_selections -> build_task_condition_evidence -> "
            "disclose_task_condition_view -> build_task_condition_packet",
        "input_sha256": sha256(raw).hexdigest(), "input_bytes": len(raw),
        "selected_descriptor_count": len(descriptors),
        "source_capability": "genuine native task/condition capabilities",
        "fixture_substitutions": ["temporary synthetic source store/captures",
            "frozen membership digest pin", "explicit test source-use Policy"],
        "native_service_issuer": "NOT_IMPLEMENTED_BY_THIS_COMPONENT",
        "recipient_or_registration_authenticated": False,
        "runtime_or_scientific_admission": False, "private_data_read": False,
        "actual_blinding_established": False}, indent=2) + "\n")


@pytest.mark.parametrize("value", [None, {}, b"serialized", object()])
def test_unissued_evidence_refuses_before_native_io(value, monkeypatch):
    monkeypatch.setattr(tasks, "disclose_task_condition_view",
                        lambda *a, **k: pytest.fail("forged input reached native I/O"))
    with pytest.raises(packet.ParticipantPacketError, match="genuine_native"):
        packet.build_task_condition_packet(value, condition=sources.CONDITIONS[0], policy=None)


def test_closed_packet_and_exact_selected_citations(request_data):
    cap = tasks.build_task_condition_evidence(**request_data)
    raw = packet.build_task_condition_packet(cap, condition=sources.CONDITIONS[-1],
                                            policy=request_data["policy"])
    document = json.loads(raw[:-len(packet.SUFFIX)])
    mutations = []
    value = copy.deepcopy(document); value["audit"] = {}; mutations.append(value)
    value = copy.deepcopy(document); value["task"]["original_evidence"] = []; mutations.append(value)
    value = copy.deepcopy(document); value["source_view"]["actual_blinding_established"] = True; mutations.append(value)
    value = copy.deepcopy(document); value["source_view"]["source_cards"] *= 2; mutations.append(value)
    for key, changed in [("span_sha256", "0" * 64), ("start_byte", True),
                         ("quoted_json", "different"), ("source_bytes", False)]:
        value = copy.deepcopy(document)
        value["source_view"]["source_cards"][0]["facts"][0]["citation"][key] = changed
        mutations.append(value)
    value = copy.deepcopy(document)
    value["source_view"]["source_cards"][0]["facts"][0]["citation"]["json_pointer"] = "/state/cycle_tag"
    mutations.append(value)
    value = copy.deepcopy(document)
    value["source_view"]["source_cards"][0]["facts"][0]["value"] = 99999
    mutations.append(value)
    value = copy.deepcopy(document)
    if value["source_view"]["state_differences"]:
        value["source_view"]["state_differences"][0]["query_value"] = 99999
    else:
        value["source_view"]["state_differences"] = [{
            "context_id": value["source_view"]["source_cards"][1]["context_id"],
            "field": "growth_score", "query_value": 99999, "neighbor_value": 88888,
            "meaning": "different_dated_outputs_not_a_logical_contradiction"}]
    mutations.append(value)
    for value in mutations:
        with pytest.raises(packet.ParticipantPacketError):
            extract(encode(value))
    for malformed in [raw + b"\n", raw + packet.SUFFIX, raw[1:], b"{}" + packet.SUFFIX,
                      b'{"schema":1,"schema":2}' + packet.SUFFIX,
                      json.dumps(document, indent=2).encode() + packet.SUFFIX]:
        with pytest.raises(packet.ParticipantPacketError):
            extract(malformed)
    with pytest.raises(packet.ParticipantPacketError):
        packet.extract_selected_citations(raw, input_sha256="0" * 64)
    detached = extract(raw); detached[0]["citation"].clear()
    assert extract(raw)[0]["citation"]


def test_native_rights_and_mid_disclosure_mutation_are_not_cached(request_data, monkeypatch):
    cap = tasks.build_task_condition_evidence(**request_data)
    original = tasks.disclose_task_condition_view
    calls = []
    seal = cap._seal

    def change_after_native(*args, **kwargs):
        value = original(*args, **kwargs)
        calls.append(True)
        if len(calls) == 2:
            object.__setattr__(cap, "_seal", object())
        return value

    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(tasks, "disclose_task_condition_view", change_after_native)
            with pytest.raises(packet.ParticipantPacketError,
                               match="native_evidence_changed_during_packet_build"):
                packet.build_task_condition_packet(cap, condition=sources.CONDITIONS[-1],
                                                   policy=request_data["policy"])
        assert len(calls) == 2
    finally:
        object.__setattr__(cap, "_seal", seal)

    # A genuine final native disclosure returns, then an INNER seal changes.
    # Outer task identity and returned view remain unchanged: graph closure owes
    # the refusal, not a copied successful source-view response.
    inner, original_inner_seal = cap._sources, cap._sources._seal
    calls.clear()
    def change_inner_after_native(*args, **kwargs):
        value = original(*args, **kwargs)
        calls.append(True)
        if len(calls) == 2:
            object.__setattr__(inner, "_seal", object())
        return value
    try:
        with monkeypatch.context() as scoped:
            scoped.setattr(tasks, "disclose_task_condition_view", change_inner_after_native)
            with pytest.raises(packet.ParticipantPacketError,
                               match="native_evidence_changed_during_packet_build"):
                packet.build_task_condition_packet(cap, condition=sources.CONDITIONS[-1],
                                                   policy=request_data["policy"])
        assert len(calls) == 2
    finally:
        object.__setattr__(inner, "_seal", original_inner_seal)

    def denied(*args, **kwargs):
        raise PermissionError("fixture_current_source_rights_revoked")

    with monkeypatch.context() as scoped:
        scoped.setattr(tasks, "disclose_task_condition_view", denied)
        with pytest.raises(PermissionError, match="fixture_current_source_rights_revoked"):
            packet.build_task_condition_packet(cap, condition=sources.CONDITIONS[-1],
                                               policy=request_data["policy"])
