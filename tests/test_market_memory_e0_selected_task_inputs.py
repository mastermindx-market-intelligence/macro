"""Actual private files with synthetic control selection; no installed admission."""
import copy
from hashlib import sha256
import json

import pytest

from engine.research_factory import market_memory_e0_installed_control as owner
from tests.test_market_memory_e0_control_records import (
    bundle, canonical, records, record_ref, task_bundle,
)
from tests.test_market_memory_e0_installed_control import (
    COMMIT, NOW, REFUSALS, retain, select, selection, write,
)
from tests.test_market_memory_e0_registered_method import inputs


def republish(root, selected, records):
    rr = record_ref(records["registration"], "study_id")
    records["closure"]["registration_ref"] = rr
    cr = record_ref(records["closure"], "closure_id")
    records["publication"].update(registration_ref=rr, closure_ref=cr)
    pr = record_ref(records["publication"], "publication_id")
    records["installation"].update(registration_ref=rr, closure_ref=cr, publication_ref=pr)
    records["access"].update(registration_ref=rr, publication_ref=pr)
    selected["control_refs"] = {name: retain(root, records[name], identity)
        for name, (_kind, identity) in owner._CONTROL_KEYS.items()}
    select(root, selected)


@pytest.fixture
def prepared_files(selection, records, inputs):
    root, selected = selection
    records["registration"] = json.loads(inputs["registration"])
    republish(root, selected, records)
    for name in ("method_manifest", "task_manifest", "frozen_membership"):
        write(root / (sha256(inputs[name]).hexdigest() + ".json"), inputs[name])
    return root, selected, records, inputs


def prepare(data, *, task_id="synthetic-task-1", verify=None, times=None):
    root, _, _, _ = data
    if verify is None:
        def verify(commit):
            assert commit == COMMIT  # Test seam only, not installed source authentication.
    clock = iter([NOW, NOW] if times is None else times)
    return owner._load_selected_control(root, "synthetic-study", verify,
        clock=lambda: next(clock), prepare=lambda fd, selected, records, reg:
        owner._prepare_task_bytes(fd, selected, records, reg, task_id=task_id))


def observe_domains(monkeypatch, data):
    names = {sha256(data[3][name]).hexdigest() + ".json"
             for name in ("method_manifest", "task_manifest", "frozen_membership")}
    seen = []
    original = owner._read
    def read(fd, name, *args, **kwargs):
        if name in names:
            seen.append(name)
        return original(fd, name, *args, **kwargs)
    monkeypatch.setattr(owner, "_read", read)
    return seen, names


def test_only_three_exact_prelabel_objects_and_original_selection_no_writes(prepared_files, monkeypatch):
    root, selected, _, inputs = prepared_files
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    seen, names = observe_domains(monkeypatch, prepared_files)
    values, selection_bytes = prepare(prepared_files)
    assert set(seen) == names and len(seen) == 3
    assert dict(zip(owner._INPUT_NAMES, values)) == inputs
    assert selection_bytes == canonical(selected)
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    # Every opaque registration reference is absent on disk; none was followed.
    assert not (root / (json.loads(inputs["registration"])["outcome_definition_ref"]["sha256"] + ".json")).exists()


@pytest.mark.parametrize("change", ["revoked", "contaminated", "permission"])
def test_current_access_required_before_domain_reads(prepared_files, monkeypatch, change):
    root, selected, records, _ = prepared_files
    if change == "revoked": records["access"]["status"] = "revoked"
    elif change == "contaminated": records["access"]["contamination_state"] = "contaminated"
    else: records["installation"]["permitted_actions"] = ["read_e0_registration"]
    republish(root, selected, records)
    seen, _ = observe_domains(monkeypatch, prepared_files)
    with pytest.raises(REFUSALS):
        prepare(prepared_files)
    assert not seen


@pytest.mark.parametrize("change", ["wrong_role", "alias", "frozen_digest", "method_size"])
def test_all_role_checks_precede_domain_reads(prepared_files, monkeypatch, change):
    root, selected, records, _ = prepared_files
    reg = records["registration"]
    ref = reg["implementation"]["method_ref"]
    if change == "wrong_role": ref["schema"] = "annotations.v1"
    elif change == "alias": ref["sha256"] = reg["tasks_ref"]["sha256"]
    elif change == "frozen_digest": reg["corpus"]["membership_ref"]["sha256"] = "f" * 64
    else: ref["bytes"] = 65537
    republish(root, selected, records)
    seen, _ = observe_domains(monkeypatch, prepared_files)
    with pytest.raises(REFUSALS):
        prepare(prepared_files)
    assert not seen


def test_aggregate_prelabel_size_checked_before_any_domain_read(prepared_files, monkeypatch):
    seen, _ = observe_domains(monkeypatch, prepared_files)
    monkeypatch.setattr(owner.control, "MAX_DOMAIN_TOTAL_BYTES", 1)
    with pytest.raises(owner.E0InstalledControlError, match="selected_prelabel_byte_limit"):
        prepare(prepared_files)
    assert not seen


@pytest.mark.parametrize("defect", ["corrupt", "symlink", "mode", "missing"])
def test_selected_domain_storage_cannot_launder_invalid_bytes(prepared_files, defect):
    root, _, _, inputs = prepared_files
    path = root / (sha256(inputs["method_manifest"]).hexdigest() + ".json")
    if defect == "corrupt": write(path, b"{}")
    elif defect == "mode": path.chmod(0o644)
    elif defect == "missing": path.unlink()
    else:
        alias = path.with_name("alias.json")
        path.rename(alias)
        path.symlink_to(alias)
    with pytest.raises(REFUSALS):
        prepare(prepared_files)


@pytest.mark.parametrize("change", ["selection", "access_record", "source"])
def test_races_after_preparation_prevent_return(prepared_files, change):
    root, selected, records, _ = prepared_files
    verified = []
    def verify(_commit):
        verified.append(_commit)
        if len(verified) != 2:
            return
        if change == "selection":
            select(root, {**selected, "source_commit": "b" * 40})
        elif change == "access_record":
            changed = {**records["access"], "status": "revoked"}
            write(root / (selected["control_refs"]["access"]["sha256"] + ".json"), canonical(changed))
        else:
            raise owner.E0InstalledControlError("installed_source_changed")
    with pytest.raises(REFUSALS):
        prepare(prepared_files, verify=verify)
    assert len(verified) == 2


def test_absent_task_and_expiry_after_preparation_refuse(prepared_files):
    with pytest.raises(owner.E0InstalledControlError, match="selected_registered_task_required"):
        prepare(prepared_files, task_id="absent")
    with pytest.raises(REFUSALS):
        prepare(prepared_files, times=[NOW, "2026-10-15T00:00:00.000000Z"])


def test_plain_inspector_keeps_domain_files_unread(prepared_files, monkeypatch):
    seen, _ = observe_domains(monkeypatch, prepared_files)
    summary = owner._load_selected_control(prepared_files[0], "synthetic-study",
        lambda _commit: None, clock=lambda: NOW)
    assert not seen
    assert summary["domain_payloads_read"] is summary["operational_admission"] is False


def test_prepared_capability_requires_current_fixed_owner_and_exact_selected_bytes(prepared_files, monkeypatch):
    values, selected = prepare(prepared_files)
    cap = owner._SelectedTaskInputs("synthetic-study", "synthetic-task-1", selected, values,
                                    _key=owner._PREPARED_TOKEN)
    with pytest.raises(owner.E0InstalledControlError, match="selected_task_inputs_required"):
        owner._current_selected_task_bytes({"inputs": values})
    calls = []
    def current(study, task):
        calls.append((study, task))
        return cap
    monkeypatch.setattr(owner, "_prepare_selected_task_inputs", current)
    disclosed = owner._current_selected_task_bytes(cap)
    assert calls == [("synthetic-study", "synthetic-task-1")]
    assert disclosed == prepared_files[3]
    changed = owner._SelectedTaskInputs(cap._study_id, cap._task_id, selected + b" ", values,
                                        _key=owner._PREPARED_TOKEN)
    monkeypatch.setattr(owner, "_prepare_selected_task_inputs", lambda *a: changed)
    with pytest.raises(owner.E0InstalledControlError, match="prepared_selection_or_inputs_changed"):
        owner._current_selected_task_bytes(cap)
    def revoked(*_args):
        raise owner.E0InstalledControlError("current_prelabel_metadata_access_required")
    monkeypatch.setattr(owner, "_prepare_selected_task_inputs", revoked)
    with pytest.raises(owner.E0InstalledControlError, match="current_prelabel_metadata_access_required"):
        owner._current_selected_task_bytes(cap)


def test_uninstalled_public_preparation_and_manual_capability_construction_refuse():
    with pytest.raises(owner.E0InstalledControlError, match="installed_administrator_entry_required"):
        owner._prepare_selected_task_inputs("synthetic-study", "synthetic-task-1")
    with pytest.raises(owner.E0InstalledControlError, match="selected_task_inputs_required"):
        owner._SelectedTaskInputs("study", "task", b"{}", ())
