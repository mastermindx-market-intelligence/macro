"""Private synthetic selections exercise the real owner filesystem boundaries."""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile

import pytest

from engine.research_factory import market_memory_e0_installed_control as owner
from engine.research_factory.market_memory_contextual_registration import E0ControlError
from engine.research_factory.market_memory_e0_access_history import E0AccessHistoryError
from tests.test_market_memory_e0_control_records import records, canonical, record_ref

NOW = "2026-10-14T01:00:00.000000Z"
COMMIT = "a" * 40
REFUSALS = (owner.E0InstalledControlError, E0ControlError, E0AccessHistoryError)


def write(path, body):
    path.write_bytes(body)
    path.chmod(0o600)


def select(root, selection):
    write(root / "SELECTED.json", canonical(selection))


def retain(root, value, identity):
    ref = record_ref(value, identity)
    write(root / (ref["sha256"] + ".json"), canonical(value))
    return ref


@pytest.fixture
def selection(records):
    # Exercise actual ancestor ownership/mode checks, with no world-writable /tmp.
    with tempfile.TemporaryDirectory(prefix="mm-control-test-", dir=Path.home()) as base:
        root = Path(base) / "selection"
        root.mkdir(mode=0o700)
        refs = {name: retain(root, records[name], identity)
                for name, (_kind, identity) in owner._CONTROL_KEYS.items()}
        selected = {"schema": owner.SELECTED_SCHEMA, "study_id": "synthetic-study",
                    "source_commit": COMMIT, "control_refs": refs}
        select(root, selected)
        yield root, selected


def load(root, *, verify=None, times=None, study="synthetic-study"):
    if verify is None:
        def verify(commit):
            assert commit == COMMIT  # Synthetic source verifier, not a production grant.
    clock = iter([NOW, NOW] if times is None else times)
    return owner._load_selected_control(root, study, verify, clock=lambda: next(clock))


def test_current_control_metadata_does_not_admit_or_read_domain_data(selection):
    root, selected = selection
    before = {path.name: path.read_bytes() for path in root.iterdir()}
    verified = []
    result = load(root, verify=lambda commit: verified.append(commit))
    assert verified == [COMMIT, COMMIT]
    assert result["metadata_consistent"] is True
    assert result["access_history"]["records"] == 1
    for flag in ("domain_payloads_read", "reservation_store_read", "labels_read",
                 "provider_invoked", "runtime_writes", "operational_admission"):
        assert result[flag] is False
    assert result["access_history"]["actual_reservation_accounting_verified"] is False
    assert before == {path.name: path.read_bytes() for path in root.iterdir()}


def test_complete_access_history_is_read_including_prior_revocation(selection, records):
    root, selected = selection
    prior = records["access"]
    current = copy.deepcopy(prior)
    current.update(sequence=1, previous_state_ref=record_ref(prior, "access_state_id"),
                   recorded_at="2026-10-14T00:05:00.000000Z", status="revoked")
    selected["control_refs"]["access"] = retain(root, current, "access_state_id")
    select(root, selected)
    result = load(root)
    assert result["access_history"]["records"] == 2
    assert result["access_history"]["status"] == "revoked"
    assert result["operational_admission"] is False
    (root / (record_ref(prior, "access_state_id")["sha256"] + ".json")).unlink()
    with pytest.raises(REFUSALS):
        load(root)


@pytest.mark.parametrize("mutation", [
    lambda value: value.update(study_id="other-study"),
    lambda value: value.update(schema="unknown"),
    lambda value: value.update(extra=True),
    lambda value: value["control_refs"].pop("registration"),
    lambda value: value["control_refs"]["registration"].update(bytes=1),
    lambda value: value["control_refs"]["registration"].update(object_id="other-object"),
    lambda value: value["control_refs"]["registration"].update(schema="unknown"),
])
def test_selected_identity_references_and_closed_shape_refuse(selection, mutation):
    root, selected = selection
    mutation(selected)
    select(root, selected)
    with pytest.raises(REFUSALS):
        load(root)


@pytest.mark.parametrize("wire", [b"{}", b"{", b"null", b"\xff"])
def test_invalid_selected_wire_is_not_a_grant(selection, wire):
    root, _ = selection
    write(root / "SELECTED.json", wire)
    with pytest.raises(REFUSALS):
        load(root)


def test_valid_but_noncanonical_selection_is_refused(selection):
    root, selected = selection
    write(root / "SELECTED.json", json.dumps(selected, indent=2).encode())
    with pytest.raises(owner.E0InstalledControlError, match="selected_control_identity_invalid"):
        load(root)


@pytest.mark.parametrize("target", ["selection", "record"])
@pytest.mark.parametrize("defect", ["missing", "symlink", "hardlink", "permissions", "fifo", "oversized"])
def test_unsafe_metadata_file_cannot_be_read(selection, target, defect):
    root, selected = selection
    path = root / ("SELECTED.json" if target == "selection" else
                   selected["control_refs"]["registration"]["sha256"] + ".json")
    if defect in ("missing", "symlink", "fifo"):
        original = path.read_bytes()
        path.unlink()
        if defect == "symlink":
            other = root / "other.json"
            write(other, original)
            path.symlink_to(other)
        if defect == "fifo":
            os.mkfifo(path, 0o600)
    elif defect == "hardlink":
        os.link(path, root / "alias.json")
    elif defect == "permissions":
        path.chmod(0o644)
    elif defect == "oversized":
        write(path, b" " * (owner.control.MAX_CONTROL_BYTES + 1))
    with pytest.raises(owner.E0InstalledControlError):
        load(root)


@pytest.mark.parametrize("defect", ["private_mode", "ancestor_mode", "symlink"])
def test_unsafe_selection_directory_refuses(selection, defect):
    root, _ = selection
    if defect == "private_mode":
        root.chmod(0o755)
    elif defect == "ancestor_mode":
        root.parent.chmod(0o777)
    else:
        alias = root.parent / "alias"
        alias.symlink_to(root, target_is_directory=True)
        root = alias
    with pytest.raises(owner.E0InstalledControlError):
        load(root)


def test_hash_addressed_record_corruption_refuses(selection):
    root, selected = selection
    path = root / (selected["control_refs"]["registration"]["sha256"] + ".json")
    write(path, path.read_bytes().replace(b"retrospective", b"Retrospective", 1))
    with pytest.raises(owner.E0InstalledControlError, match="selected_control_bytes_mismatch"):
        load(root)


def test_source_refusal_and_wrong_verifier_contract_precede_record_reads(selection):
    root, selected = selection
    (root / (selected["control_refs"]["registration"]["sha256"] + ".json")).unlink()
    with pytest.raises(owner.E0InstalledControlError, match="source_verifier_contract"):
        load(root, verify=lambda _commit: True)
    def refuse(_commit):
        raise owner.E0InstalledControlError("source_changed")
    with pytest.raises(owner.E0InstalledControlError, match="source_changed"):
        load(root, verify=refuse)


@pytest.mark.parametrize("mutation", ["pointer", "directory", "ancestor_mode", "source"])
def test_final_source_selection_and_directory_recheck_before_return(selection, mutation):
    root, selected = selection
    calls = []
    def verify(_commit):
        calls.append(1)
        if len(calls) != 2:
            return
        if mutation == "pointer":
            selected["study_id"] = "changed"
            select(root, selected)
        elif mutation == "directory":
            root.rename(root.with_name("retired"))
            root.mkdir(mode=0o700)
        elif mutation == "ancestor_mode":
            root.parent.chmod(0o777)
        else:
            raise owner.E0InstalledControlError("source_changed")
    with pytest.raises(owner.E0InstalledControlError):
        load(root, verify=verify)
    assert len(calls) == 2


@pytest.mark.parametrize("final", ["2026-10-15T00:00:00.000000Z", "2026-10-14T00:59:59.000000Z"])
def test_expiry_and_clock_reversal_during_inspection_refuse(selection, final):
    root, _ = selection
    with pytest.raises(REFUSALS):
        load(root, times=[NOW, final])


def test_aggregate_control_read_budget_refuses(selection, monkeypatch):
    root, _ = selection
    monkeypatch.setattr(owner, "MAX_ACCESS_HISTORY_BYTES", 1)
    with pytest.raises(owner.E0InstalledControlError, match="selected_control_byte_limit"):
        load(root)


def test_record_name_replacement_during_open_read_refuses(selection, monkeypatch):
    root, _ = selection
    path = root / "SELECTED.json"
    inode = path.stat().st_ino
    original = owner.os.read
    changed = False
    def read(fd, count):
        nonlocal changed
        body = original(fd, count)
        if not changed and os.fstat(fd).st_ino == inode:
            changed = True
            replacement = root / "replacement.json"
            write(replacement, path.read_bytes())
            os.replace(replacement, path)
        return body
    monkeypatch.setattr(owner.os, "read", read)
    with pytest.raises(owner.E0InstalledControlError, match="metadata_file_changed"):
        load(root)


def test_public_entry_refuses_uninstalled_workspace():
    with pytest.raises(owner.E0InstalledControlError, match="installed_administrator_entry_required"):
        owner.inspect_selected_control("synthetic-study")
