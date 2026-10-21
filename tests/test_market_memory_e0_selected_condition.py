"""Private synthetic selected files; no study, outcome or production effects."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile

import pytest

from engine.research_factory import market_memory_e0_selected_condition as selected_owner
from engine.research_factory import market_memory_e0_installed_control as owner
from engine.research_factory import market_memory_e0_allocation_binding as binding
from tests.test_market_memory_e0_control_records import (
    bundle, canonical, records, reference, task_bundle,
)
from tests.test_market_memory_e0_installed_control import (
    COMMIT, NOW, REFUSALS, retain, select, selection, write,
)
from tests.test_market_memory_e0_registered_method import inputs
from tests.test_market_memory_e0_selected_task_inputs import prepared_files, republish


@pytest.fixture
def condition_files(prepared_files):
    root, selected, records, inputs = prepared_files
    reg = records["registration"]
    tasks = json.loads(inputs["task_manifest"])
    declared = binding.allocator.allocate_condition_order(seed_hex=reg["allocation"]["seed_hex"],
        study_id=reg["study_id"], tasks_sha256=reg["tasks_ref"]["sha256"],
        task_ids=[row["task_id"] for row in tasks["tasks"]])
    body = canonical(declared)
    reg["allocation"]["assignment_ref"] = reference(body, binding.allocator.OUTPUT_SCHEMA,
                                                       declared["allocation_sha256"])
    source = Path(binding.allocator.__file__).read_bytes()
    reg["allocation"]["algorithm_ref"] = reference(source, "python.source.v1", "native-allocator")
    inputs["registration"] = canonical(reg)
    write(root / (sha256(body).hexdigest() + ".json"), body)
    republish(root, selected, records)
    return prepared_files, declared


def prepare(data, *, slot=0, verify=None):
    root, _, _, _ = data
    def source(commit):
        assert commit == COMMIT  # Synthetic private test seam, not source admission.
        if verify is not None:
            verify(commit)
    return owner._load_selected_control(root, "synthetic-study", source, clock=lambda: NOW,
        prepare=lambda fd, selected, records, registration: selected_owner._prepare_condition_bytes(
            fd, selected, records, registration, task_id="synthetic-task-1", slot=slot))


def test_all_slots_resolve_exact_native_order_without_writes(condition_files, monkeypatch):
    data, declared = condition_files
    root = data[0]
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    order = next(row["order"] for row in declared["assignments"] if row["task_id"] == "synthetic-task-1")
    seen = []
    original = owner._read
    def read(fd, name, *args, **kwargs):
        seen.append(name)
        return original(fd, name, *args, **kwargs)
    monkeypatch.setattr(owner, "_read", read)
    for slot in range(3):
        (values, body, condition), selection_bytes = prepare(data, slot=slot)
        assert dict(zip(owner._INPUT_NAMES, values)) == data[3]
        assert body == canonical(declared) and condition == order[slot]
        assert selection_bytes == canonical(data[1])
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    assert data[2]["registration"]["outcome_definition_ref"]["sha256"] + ".json" not in seen


@pytest.mark.parametrize("slot", [True, False, "0", -1, 3, None])
def test_invalid_slot_refuses_before_assignment_read(condition_files, monkeypatch, slot):
    data, _ = condition_files
    assignment_name = data[2]["registration"]["allocation"]["assignment_ref"]["sha256"] + ".json"
    original = owner._read
    def read(fd, name, *args, **kwargs):
        assert name != assignment_name
        return original(fd, name, *args, **kwargs)
    monkeypatch.setattr(owner, "_read", read)
    with pytest.raises(owner.E0InstalledControlError, match="registered_condition_slot_required"):
        prepare(data, slot=slot)


@pytest.mark.parametrize("defect", ["missing", "corrupt", "unsafe_mode", "source_pin", "wrong_role", "wrong_identity"])
def test_assignment_and_source_binding_refuse(condition_files, defect):
    data, _ = condition_files
    root, selected, records, _ = data
    reg = records["registration"]
    ref = reg["allocation"]["assignment_ref"]
    path = root / (ref["sha256"] + ".json")
    if defect == "missing": path.unlink()
    elif defect == "corrupt": write(path, b"{}")
    elif defect == "unsafe_mode": path.chmod(0o644)
    elif defect == "source_pin": reg["allocation"]["algorithm_ref"]["sha256"] = "f" * 64
    elif defect == "wrong_role": ref["schema"] = "annotations.v1"
    else: ref["object_id"] = "different-allocation"
    republish(root, selected, records)
    with pytest.raises(REFUSALS):
        prepare(data)


def test_self_consistent_different_task_population_refuses(condition_files):
    data, _ = condition_files
    root, selected, records, _ = data
    reg = records["registration"]
    other = binding.allocator.allocate_condition_order(seed_hex=reg["allocation"]["seed_hex"],
        study_id=reg["study_id"], tasks_sha256=reg["tasks_ref"]["sha256"], task_ids=["other-task"])
    body = canonical(other)
    reg["allocation"]["assignment_ref"] = reference(body, binding.allocator.OUTPUT_SCHEMA, other["allocation_sha256"])
    write(root / (sha256(body).hexdigest() + ".json"), body)
    republish(root, selected, records)
    with pytest.raises(owner.control.E0ControlError, match="allocation_task_manifest_mismatch"):
        prepare(data)


@pytest.mark.parametrize("change", ["revoked", "contaminated", "selection"])
def test_access_and_selection_races_prevent_return(condition_files, change):
    data, _ = condition_files
    root, selected, records, _ = data
    calls = []
    def verify(_commit):
        calls.append(_commit)
        if len(calls) == 2:
            if change == "selection": select(root, {**selected, "source_commit": "b" * 40})
            else:
                field = "status" if change == "revoked" else "contamination_state"
                records["access"][field] = change
                write(root / (selected["control_refs"]["access"]["sha256"] + ".json"), canonical(records["access"]))
    with pytest.raises(REFUSALS):
        prepare(data, verify=verify)


@pytest.fixture
def installed_allocator_source():
    # The real installed-owner guard rejects writable ancestors such as /tmp.
    # Keep this positive source-byte fixture under the same safe test placement
    # used by the installed-control owner tests; do not bypass the guard.
    with tempfile.TemporaryDirectory(prefix="mm-allocator-test-", dir=Path.home()) as base:
        root = Path(base)
        path = root / selected_owner._ALLOCATOR
        path.parent.mkdir(parents=True)
        path.write_bytes(Path(binding.allocator.__file__).read_bytes())
        yield root, path


def test_installed_allocator_bytes_are_checked_even_if_commit_check_passes(installed_allocator_source, monkeypatch):
    root, path = installed_allocator_source
    source = Path(binding.allocator.__file__).read_bytes()
    monkeypatch.setattr(owner, "INSTALLED_ROOT", root)
    monkeypatch.setattr(owner, "_verify_source", lambda *a, **kw: None)
    selected_owner._verify_sources(COMMIT)
    path.write_bytes(b"#" + source[1:])
    with pytest.raises(owner.E0InstalledControlError, match="installed_allocator_bytes_mismatch"):
        selected_owner._verify_sources(COMMIT)


@pytest.mark.parametrize("unsafe_mode", [0o770, 0o702])
def test_installed_allocator_writable_ancestor_refuses(installed_allocator_source, monkeypatch, unsafe_mode):
    root, _path = installed_allocator_source
    monkeypatch.setattr(owner, "INSTALLED_ROOT", root)
    monkeypatch.setattr(owner, "_verify_source", lambda *a, **kw: None)
    root.chmod(unsafe_mode)
    try:
        with pytest.raises(owner.E0InstalledControlError, match="unsafe_metadata_ancestor"):
            selected_owner._verify_sources(COMMIT)
    finally:
        root.chmod(0o700)


def test_prepared_condition_is_rechecked_before_consumption(condition_files, monkeypatch):
    values, pointer = prepare(condition_files[0])
    cap = selected_owner._SelectedConditionInputs("synthetic-study", "synthetic-task-1", 0,
        pointer, values, _key=selected_owner._TOKEN)
    monkeypatch.setattr(selected_owner, "_prepare_selected_condition_inputs", lambda *a: cap)
    result = selected_owner._current_selected_condition_bytes(cap)
    assert result["condition"] == values[2] and result["assignment"] == values[1]
    changed = selected_owner._SelectedConditionInputs(cap._study_id, cap._task_id, 0,
        pointer + b" ", values, _key=selected_owner._TOKEN)
    monkeypatch.setattr(selected_owner, "_prepare_selected_condition_inputs", lambda *a: changed)
    with pytest.raises(owner.E0InstalledControlError, match="prepared_condition_selection_changed"):
        selected_owner._current_selected_condition_bytes(cap)
    with pytest.raises(owner.E0InstalledControlError, match="selected_condition_inputs_required"):
        selected_owner._current_selected_condition_bytes(result)


def test_uninstalled_entry_and_caller_constructed_capability_refuse():
    with pytest.raises(owner.E0InstalledControlError, match="installed_administrator_entry_required"):
        selected_owner._prepare_selected_condition_inputs("study", "task", 0)
    with pytest.raises(owner.E0InstalledControlError, match="selected_condition_inputs_required"):
        selected_owner._SelectedConditionInputs("study", "task", 0, b"{}", ())
