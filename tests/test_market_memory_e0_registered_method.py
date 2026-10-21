"""Native method binding against original frozen metadata; no study activation."""
import copy
import json

import pytest

from engine.neuralweb import market_memory_episode_retrieval as retrieval
from engine.research_factory import market_memory_e0_task_evidence as subject
from tests.test_market_memory_e0_control_records import (
    bundle, canonical, records, reference, task_bundle,
)


@pytest.fixture
def inputs(task_bundle):
    (reg, objects, _), tasks = task_bundle
    method = {"schema": subject.METHOD_SCHEMA, "object_id": "synthetic-native-method",
              "authority": "display_only", "study_id": reg["study_id"],
              "tasks_ref": copy.deepcopy(reg["tasks_ref"]),
              "method_spec": retrieval.RetainedContextMethodSpec(0, 0, "historical_hypothetical").disclosure()}
    body = canonical(method)
    reg["implementation"]["method_ref"] = reference(body, method["schema"], method["object_id"])
    return {"registration": canonical(reg), "method_manifest": body,
            "task_manifest": canonical(tasks),
            "frozen_membership": objects[subject.control._FROZEN_DOMAIN_DIGESTS["membership"]]}


def replace_method(inputs, method):
    values = dict(inputs)
    values["method_manifest"] = canonical(method)
    reg = json.loads(values["registration"])
    reg["implementation"]["method_ref"] = reference(values["method_manifest"],
        method["schema"], method["object_id"])
    values["registration"] = canonical(reg)
    return values


def refuse_before_payload(inputs, monkeypatch):
    monkeypatch.setattr(subject, "build_task_condition_evidence",
                        lambda *a, **k: pytest.fail("invalid registered metadata reached source reader"))
    with pytest.raises((subject.E0TaskEvidenceError, subject.control.E0ControlError)):
        subject.build_registered_task_condition_evidence(None, None, None,
            **inputs, task_id="synthetic-task-1", policy=None)


def test_exact_native_method_and_detached_registration_references(inputs):
    method, refs = subject.resolve_registered_task_inputs(**inputs)
    assert type(method) is retrieval.RetainedContextMethodSpec
    assert method.disclosure() == json.loads(inputs["method_manifest"])["method_spec"]
    assert refs["registration_ref"]["object_id"] == "synthetic-study"
    assert refs["registered_tasks_ref"] == json.loads(inputs["registration"])["tasks_ref"]
    assert not method.disclosure()["operational_registration_admitted"]
    refs["registered_method_ref"]["object_id"] = "mutated"
    assert subject.resolve_registered_task_inputs(**inputs)[1]["registered_method_ref"]["object_id"] != "mutated"


@pytest.mark.parametrize("field", ["registration", "method_manifest", "task_manifest", "frozen_membership"])
def test_changed_exact_bytes_before_payload(inputs, monkeypatch, field):
    refuse_before_payload({**inputs, field: inputs[field] + b"\n"}, monkeypatch)


@pytest.mark.parametrize("role,field,value", [
    ("method_ref", "object_id", "wrong-object"), ("method_ref", "schema", "unknown.v1"),
    ("method_ref", "bytes", 1), ("method_ref", "sha256", "f" * 64),
    ("tasks_ref", "object_id", "wrong-tasks"), ("membership_ref", "bytes", 1),
])
def test_exact_registered_reference_before_payload(inputs, monkeypatch, role, field, value):
    reg = json.loads(inputs["registration"])
    target = reg["implementation"] if role == "method_ref" else reg["corpus"] if role == "membership_ref" else reg
    target[role][field] = value
    refuse_before_payload({**inputs, "registration": canonical(reg)}, monkeypatch)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(study_id="different-study"),
    lambda d: d.update(authority="execute"),
    lambda d: d.update(extra=True),
    lambda d: d.update(schema="unknown.method.v1"),
    lambda d: d["tasks_ref"].update(object_id="wrong-tasks"),
    lambda d: d.update(method_spec=[]),
    lambda d: d["method_spec"].update(purge_calendar_days=True),
    lambda d: d["method_spec"].update(embargo_calendar_days=367),
    lambda d: d["method_spec"].update(method_spec_id="mmretainedmethod_" + "f" * 64),
    lambda d: d["method_spec"]["retrieval_source_ref"].update(sha256="f" * 64),
    lambda d: d["method_spec"].update(representative_before_quality_filter=1),
    lambda d: d["method_spec"].pop("mode"),
    lambda d: d.update(method_spec=retrieval.RetainedContextMethodSpec(0, 0, "current_contextual_support").disclosure()),
])
def test_rehashed_method_contradictions_still_refuse_before_payload(inputs, monkeypatch, mutation):
    method = json.loads(inputs["method_manifest"])
    mutation(method)
    refuse_before_payload(replace_method(inputs, method), monkeypatch)


def test_noncanonical_rehashed_declaration_and_method_bound(inputs, monkeypatch):
    method = json.loads(inputs["method_manifest"])
    values = replace_method(inputs, method)
    body = json.dumps(method, indent=2).encode()
    reg = json.loads(values["registration"])
    reg["implementation"]["method_ref"] = reference(body, method["schema"], method["object_id"])
    refuse_before_payload({**values, "method_manifest": body, "registration": canonical(reg)}, monkeypatch)
    monkeypatch.setattr(subject, "MAX_METHOD_BYTES", 1)
    refuse_before_payload(inputs, monkeypatch)


def test_wrapper_derives_method_and_forwards_only_exact_registered_inputs(inputs, monkeypatch):
    class ReachedNativeReader(Exception):
        pass
    selection, reader, generation, policy = (object() for _ in range(4))
    def native(*args, **kwargs):
        assert args == (selection, reader, generation)
        assert kwargs["task_manifest"] is inputs["task_manifest"]
        assert kwargs["frozen_membership"] is inputs["frozen_membership"]
        assert kwargs["task_id"] == "synthetic-task-1"
        assert kwargs["policy"] is policy
        assert type(kwargs["expected_method"]) is retrieval.RetainedContextMethodSpec
        assert kwargs["expected_method"].disclosure() == json.loads(inputs["method_manifest"])["method_spec"]
        raise ReachedNativeReader
    monkeypatch.setattr(subject, "build_task_condition_evidence", native)
    with pytest.raises(ReachedNativeReader):
        subject.build_registered_task_condition_evidence(selection, reader, generation,
            **inputs, task_id="synthetic-task-1", policy=policy)
