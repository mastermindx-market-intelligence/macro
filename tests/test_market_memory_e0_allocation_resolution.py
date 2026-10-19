"""Synthetic allocation declarations; no actual allocation or study admission."""
import copy
import hashlib
from pathlib import Path

import pytest

from engine.research_factory import market_memory_contextual_registration as control
from engine.research_factory import market_memory_e0_allocation as allocator
from engine.research_factory import market_memory_e0_allocation_binding as binding
from tests.test_market_memory_e0_control_records import (
    bundle, canonical, records, reference, resolve, task_bundle,
)


def install_assignment(original, declaration):
    reg, objects, _ = original
    objects.pop(reg["allocation"]["assignment_ref"]["sha256"], None)
    body = canonical(declaration)
    ref = reference(body, allocator.OUTPUT_SCHEMA, declaration["allocation_sha256"])
    reg["allocation"]["assignment_ref"] = ref
    objects[ref["sha256"]] = body


@pytest.fixture
def allocation_bundle(task_bundle):
    original, tasks = task_bundle
    reg, objects, _ = original
    declared = allocator.allocate_condition_order(seed_hex=reg["allocation"]["seed_hex"],
        study_id=reg["study_id"], tasks_sha256=reg["tasks_ref"]["sha256"],
        task_ids=[row["task_id"] for row in tasks["tasks"]])
    install_assignment(original, declared)
    objects.pop(reg["allocation"]["algorithm_ref"]["sha256"], None)
    source = Path(allocator.__file__).read_bytes()
    reg["allocation"]["algorithm_ref"] = reference(source, "python.source.v1", "original-native-allocator")
    objects[reg["allocation"]["algorithm_ref"]["sha256"]] = source
    return original, declared, tasks


def test_native_assignment_and_exact_source_join_preserve_admission_boundary(allocation_bundle):
    original, declared, tasks = allocation_bundle
    result = resolve(original)
    checks = result["allocation_binding_checks"]
    assert len(checks) == 1
    assert checks[0]["allocation_sha256"] == declared["allocation_sha256"]
    assert checks[0]["exact_task_manifest_bytes_bound"] is True
    assert checks[0]["allocator_source_bytes_bound"] is True
    assert checks[0]["declared_orders_match_native_allocator"] is True
    assert checks[0]["unresolved"] == []
    assert checks[0]["blinding_established"] is False
    assert checks[0]["actual_task_provenance_authenticated"] is False
    assert result["domain_metadata_complete"] is result["operational_admission"] is False
    assert "assignments" not in checks[0]
    assert allocator.OUTPUT_SCHEMA not in result["unparsed_reference_schemas"]
    source = Path(allocator.__file__).read_bytes()
    assert hashlib.sha256(source).hexdigest() == binding.ALLOCATOR_SOURCE_SHA256
    assert len(source) == binding.ALLOCATOR_SOURCE_BYTES


@pytest.mark.parametrize("role,unresolved", [
    ("tasks_ref", "exact_task_manifest_bytes"),
    ("algorithm_ref", "exact_allocator_source_bytes"),
])
def test_missing_bytes_stay_unresolved(allocation_bundle, role, unresolved):
    original, _, _ = allocation_bundle
    reg, objects, _ = original
    ref = reg[role] if role == "tasks_ref" else reg["allocation"][role]
    del objects[ref["sha256"]]
    result = resolve(original)
    assert unresolved in result["allocation_binding_checks"][0]["unresolved"]
    assert result["references_complete"] is False
    assert result["operational_admission"] is False


@pytest.mark.parametrize("task_ids", [["substitute-task"], ["synthetic-task-1", "extra-task"]])
def test_valid_allocator_record_cannot_substitute_registered_task_set(allocation_bundle, task_ids):
    original, _, _ = allocation_bundle
    reg = original[0]
    declared = allocator.allocate_condition_order(seed_hex=reg["allocation"]["seed_hex"],
        study_id=reg["study_id"], tasks_sha256=reg["tasks_ref"]["sha256"], task_ids=task_ids)
    install_assignment(original, declared)
    with pytest.raises(control.E0ControlError, match="task_manifest_mismatch"):
        resolve(original)


@pytest.mark.parametrize("change", [
    lambda d: d.update(study_id="another-study"),
    lambda d: d.update(tasks_sha256="f" * 64),
    lambda d: d.update(seed_hex="f" * 64),
    lambda d: d.update(operational_admission=0),
    lambda d: d.update(blinding_established=True),
    lambda d: d["assignments"][0]["order"].reverse(),
])
def test_self_consistent_hash_does_not_authorize_changed_declaration(allocation_bundle, change):
    original, declared, _ = allocation_bundle
    changed = copy.deepcopy(declared)
    change(changed)
    changed.pop("allocation_sha256")
    changed["allocation_sha256"] = hashlib.sha256(canonical(changed)).hexdigest()
    install_assignment(original, changed)
    with pytest.raises(control.E0ControlError, match="native_mismatch"):
        resolve(original)


def test_known_assignment_cannot_be_used_as_a_different_domain_role(allocation_bundle):
    original, _, _ = allocation_bundle
    original[0]["implementation"]["method_ref"] = copy.deepcopy(original[0]["allocation"]["assignment_ref"])
    with pytest.raises(control.E0ControlError, match="reference_role_mismatch"):
        resolve(original)


def test_reference_identity_uses_native_allocation_digest(allocation_bundle):
    original, _, _ = allocation_bundle
    original[0]["allocation"]["assignment_ref"]["object_id"] = "invented-envelope"
    with pytest.raises(control.E0ControlError, match="reference_identity_mismatch"):
        resolve(original)


def test_wrong_supplied_allocator_source_is_a_contradiction(allocation_bundle):
    original, _, _ = allocation_bundle
    reg, objects, _ = original
    del objects[reg["allocation"]["algorithm_ref"]["sha256"]]
    source = b"not the frozen native allocator"
    reg["allocation"]["algorithm_ref"] = reference(source, "python.source.v1", "substitute-source")
    objects[reg["allocation"]["algorithm_ref"]["sha256"]] = source
    with pytest.raises(control.E0ControlError, match="algorithm_source_mismatch"):
        resolve(original)
