"""Holdout Vault (engine/holdout_vault.py) — the irreversible out-of-sample gate.

Proves the three governance properties: tamper-evident sealing, an append-only peek count
(the holdout's multiple-testing budget), permanent retirement, and hash-chain integrity.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.holdout_vault import HoldoutVault, VaultError  # noqa: E402


def _root():
    return Path(tempfile.mkdtemp())


def test_seal_is_idempotent_for_same_content():
    v = HoldoutVault(_root())
    h1 = v.seal("2026H2", {"dates": ["2026-07-01", "2026-12-31"], "n": 128})
    h2 = v.seal("2026H2", {"dates": ["2026-07-01", "2026-12-31"], "n": 128})
    assert h1 == h2 and v.is_sealed("2026H2")


def test_reseal_with_different_content_is_tamper():
    v = HoldoutVault(_root())
    v.seal("2026H2", {"n": 128})
    try:
        v.seal("2026H2", {"n": 129})              # changed the holdout
    except VaultError as e:
        assert "tamper" in str(e)
    else:
        raise AssertionError("re-sealing with different content must raise")


def test_peek_requires_a_sealed_window():
    v = HoldoutVault(_root())
    try:
        v.peek("hyp-1", window_id="missing", result={"dsr": 0.9})
    except VaultError as e:
        assert "not sealed" in str(e)
    else:
        raise AssertionError("peeking an unsealed window must raise")


def test_peeks_count_into_the_budget_and_persist():
    root = _root()
    v = HoldoutVault(root)
    v.seal("W", {"n": 100})
    v.peek("hyp-1", window_id="W", result={"dsr": 0.91})
    r = v.peek("hyp-2", window_id="W", result={"dsr": 0.40})
    assert r["peek_n"] == 2 and v.peek_count("W") == 2
    # survives a reload (a fresh process can't pretend the holdout was untouched)
    assert HoldoutVault(root).peek_count("W") == 2


def test_retired_hypothesis_cannot_be_peeked_again():
    v = HoldoutVault(_root())
    v.seal("W", {"n": 100})
    v.peek("hyp-1", window_id="W", result={"dsr": 0.3})
    v.retire("hyp-1", reason="failed holdout DSR")
    assert v.is_retired("hyp-1")
    try:
        v.peek("hyp-1", window_id="W", result={"dsr": 0.95})   # "let me just re-run it"
    except VaultError as e:
        assert "retired" in str(e)
    else:
        raise AssertionError("a retired hypothesis must never be peekable again")


def test_retirement_persists_across_reload():
    root = _root()
    v = HoldoutVault(root)
    v.seal("W", {"n": 1})
    v.retire("hyp-x", "blown")
    assert HoldoutVault(root).is_retired("hyp-x")


def test_hash_chain_verifies_and_detects_tamper():
    root = _root()
    v = HoldoutVault(root)
    v.seal("W", {"n": 100})
    v.peek("hyp-1", window_id="W", result={"dsr": 0.2})
    v.peek("hyp-2", window_id="W", result={"dsr": 0.8})
    assert v.verify_chain() is True
    # tamper with the log on disk: flip a recorded result
    p = root / "data" / "vault" / "peek_log.jsonl"
    lines = p.read_text().splitlines()
    rec = json.loads(lines[0]); rec["result"] = {"dsr": 0.99}      # rewrite history
    lines[0] = json.dumps(rec); p.write_text("\n".join(lines) + "\n")
    assert HoldoutVault(root).verify_chain() is False              # chain breaks → caught

# All roots below are invented exclusive fixtures. No dataset or live Vault is read.
import hashlib
import multiprocessing
import os
from dataclasses import replace

import pytest
import engine.holdout_vault as vault_module
from engine.holdout_vault import VaultConsumptionRequest, VaultHistoryAnchor


def _fixture(tmp_path):
    vault = HoldoutVault(tmp_path)
    seal = vault.seal("W", {"invented": [1, 2, 3]})
    raw = vault.peeklog_path.read_bytes()
    anchor = VaultHistoryAnchor(hashlib.sha256(vault.seals_path.read_bytes()).hexdigest(),
        hashlib.sha256(raw).hexdigest(), len(raw), "0" * 64)
    request = VaultConsumptionRequest("request-1", "root-1", "family-1", "hyp-1", "W",
                                      "a" * 64, "b" * 64, seal)
    return vault, anchor, request


def _process_consume(root, anchor, request, start, out, mode="consume"):
    try:
        vault = HoldoutVault(root)
        start.wait(10)
        if mode == "peek":
            receipt = vault.peek("legacy", window_id="W", result={"invented": True})
            out.put(("ok", receipt["record_hash"]))
        elif mode == "retire":
            receipt = vault.retire(request.hypothesis_id, "fixture retirement")
            out.put(("ok", receipt["record_hash"]))
        else:
            receipt = vault.consume_authorization(request, history_anchor=anchor)
            out.put(("ok", receipt.record_sha256))
    except Exception as exc:
        out.put(("error", str(exc)))


def _parallel(root, anchor, request, modes):
    context = multiprocessing.get_context("spawn")
    start, out = context.Event(), context.Queue()
    processes = [context.Process(target=_process_consume, args=(root, anchor, request, start, out, mode))
                 for mode in modes]
    for process in processes:
        process.start()
    start.set()
    results = [out.get(timeout=20) for _ in processes]
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0
    return results


def test_consumption_replay_reconcile_and_explicit_recovery(tmp_path, monkeypatch):
    vault, anchor, request = _fixture(tmp_path)
    assert vault.reconcile_consumption(request, history_anchor=anchor) is None
    receipt = vault.consume_authorization(request, history_anchor=anchor)
    assert receipt.consumption_state == "DURABLE_CONSUMED"
    assert receipt.peek_count == 1
    raw = vault.peeklog_path.read_bytes()
    for operation in (vault.consume_authorization, vault.reconcile_consumption):
        found = operation(request, history_anchor=anchor)
        assert found.record_sha256 == receipt.record_sha256
        assert found.consumption_state == "DURABILITY_UNPROVEN"
        assert vault.peeklog_path.read_bytes() == raw
    def no_write(*args, **kwargs):
        pytest.fail("read-only reconciliation attempted a write or fsync")
    with monkeypatch.context() as patch:
        patch.setattr(os, "write", no_write)
        patch.setattr(os, "fsync", no_write)
        assert vault.reconcile_consumption(request, history_anchor=anchor).record_sha256 == receipt.record_sha256
    recovered = vault.recover_consumption(request, history_anchor=anchor)
    assert recovered.consumption_state == "DURABLE_RECONCILED"
    assert recovered.record_sha256 == receipt.record_sha256
    assert recovered.snapshot_sha256 == hashlib.sha256(raw).hexdigest()
    assert recovered.snapshot_bytes == len(raw)
    assert vault.peek_count() == 1


def test_two_stale_instances_do_not_fork_chain_or_double_charge(tmp_path):
    first, anchor, request = _fixture(tmp_path)
    second = HoldoutVault(tmp_path)
    a = first.consume_authorization(request, history_anchor=anchor)
    b = second.consume_authorization(request, history_anchor=anchor)
    assert a.record_sha256 == b.record_sha256
    second.peek("legacy", window_id="W", result={"invented": 0})
    first.consume_authorization(replace(request, request_id="request-2"), history_anchor=anchor)
    fresh = HoldoutVault(tmp_path)
    assert fresh.verify_chain() and fresh.peek_count() == 3
    first.retire("hyp-1")
    with pytest.raises(VaultError, match="retired"):
        second.consume_authorization(replace(request, request_id="request-3"), history_anchor=anchor)


def test_two_processes_same_id_charge_once(tmp_path):
    vault, anchor, request = _fixture(tmp_path)
    results = _parallel(tmp_path, anchor, request, ["consume", "consume"])
    assert all(result[0] == "ok" for result in results)
    assert results[0][1] == results[1][1]
    assert HoldoutVault(tmp_path).peek_count() == 1
    assert HoldoutVault(tmp_path).verify_chain()


def test_process_legacy_and_consumption_share_writer_lock(tmp_path):
    vault, anchor, request = _fixture(tmp_path)
    assert all(r[0] == "ok" for r in _parallel(tmp_path, anchor, request, ["consume", "peek"]))
    assert HoldoutVault(tmp_path).peek_count() == 2
    assert HoldoutVault(tmp_path).verify_chain()


def test_process_retirement_cannot_be_followed_by_consumption(tmp_path):
    vault, anchor, request = _fixture(tmp_path)
    results = _parallel(tmp_path, anchor, request, ["consume", "retire"])
    assert any(r[0] == "ok" for r in results)
    fresh = HoldoutVault(tmp_path)
    assert fresh.verify_chain() and fresh.is_retired(request.hypothesis_id)
    rows = [json.loads(line) for line in vault.peeklog_path.read_text().splitlines()]
    assert rows[-1]["kind"] == "retire"


@pytest.mark.parametrize("field,value", [
    ("original_root_id", "other-root"), ("original_family_id", "other-family"),
    ("hypothesis_id", "other-hypothesis"), ("source_sha256", "c" * 64),
    ("protocol_sha256", "c" * 64), ("seal_sha256", "c" * 64), ("window_id", "other-window")])
def test_same_request_id_never_changes_identity(tmp_path, field, value):
    vault, anchor, request = _fixture(tmp_path)
    vault.consume_authorization(request, history_anchor=anchor)
    raw = vault.peeklog_path.read_bytes()
    for operation in (vault.consume_authorization, vault.reconcile_consumption, vault.recover_consumption):
        with pytest.raises(VaultError):
            operation(replace(request, **{field: value}), history_anchor=anchor)
    assert vault.peeklog_path.read_bytes() == raw


def test_successful_sync_and_cold_readback_precede_fixture_label_release(tmp_path, monkeypatch):
    vault, anchor, request = _fixture(tmp_path)
    events = []
    original_sync, original_cold = os.fsync, vault._cold_adopt
    def sync(fd):
        events.append("file_sync" if stat_module.S_ISREG(os.fstat(fd).st_mode) else "directory_sync")
        return original_sync(fd)
    def cold(*args, **kwargs):
        value = original_cold(*args, **kwargs)
        events.append("cold_readback")
        return value
    import stat as stat_module
    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(vault, "_cold_adopt", cold)
    receipt = vault.consume_authorization(request, history_anchor=anchor)
    assert receipt.consumption_state == "DURABLE_CONSUMED"
    events.append("fixture_only_label_release")
    assert events == ["file_sync", "directory_sync", "cold_readback", "fixture_only_label_release"]


@pytest.mark.parametrize("failure", ["write", "fsync_file", "fsync_directory", "cold_readback"])
def test_uncertain_append_never_releases_and_same_id_recovery_does_not_recharge(tmp_path, monkeypatch, failure):
    vault, anchor, request = _fixture(tmp_path)
    original_write, original_sync = os.write, os.fsync
    def fail(*args, **kwargs):
        raise OSError("injected persistence failure")
    import stat as stat_module
    def sync(fd):
        regular = stat_module.S_ISREG(os.fstat(fd).st_mode)
        if regular == (failure == "fsync_file"):
            fail()
        return original_sync(fd)
    with monkeypatch.context() as patch:
        if failure == "write":
            patch.setattr(os, "write", fail)
        elif failure.startswith("fsync"):
            patch.setattr(os, "fsync", sync)
        else:
            patch.setattr(vault, "_cold_adopt", fail)
        released = []
        with pytest.raises(VaultError):
            receipt = vault.consume_authorization(request, history_anchor=anchor)
            released.append(receipt)
        assert released == [] and vault.peek_count() == 0
    cold = HoldoutVault(tmp_path)
    found = cold.reconcile_consumption(request, history_anchor=anchor)
    if failure == "write":
        assert found is None
        with pytest.raises(VaultError, match="absent"):
            cold.recover_consumption(request, history_anchor=anchor)
    else:
        assert found.consumption_state == "DURABILITY_UNPROVEN"
        raw = vault.peeklog_path.read_bytes()
        assert cold.recover_consumption(request, history_anchor=anchor).consumption_state == "DURABLE_RECONCILED"
        assert vault.peeklog_path.read_bytes() == raw and cold.peek_count() == 1


def test_partial_append_remains_uncertain_not_absent(tmp_path, monkeypatch):
    vault, anchor, request = _fixture(tmp_path)
    original_write = os.write
    def partial(fd, data):
        original_write(fd, data[:20])
        raise OSError("interruption after partial write")
    monkeypatch.setattr(os, "write", partial)
    with pytest.raises(VaultError):
        vault.consume_authorization(request, history_anchor=anchor)
    assert vault.peeklog_path.stat().st_size == 20
    with pytest.raises(VaultError, match="torn"):
        vault.reconcile_consumption(request, history_anchor=anchor)


def test_crash_after_append_preserves_original_record(tmp_path, monkeypatch):
    vault, anchor, request = _fixture(tmp_path)
    def crash(*args, **kwargs):
        raise KeyboardInterrupt("crash before response")
    monkeypatch.setattr(vault, "_cold_adopt", crash)
    with pytest.raises(KeyboardInterrupt):
        vault.consume_authorization(request, history_anchor=anchor)
    fresh = HoldoutVault(tmp_path)
    raw = fresh.peeklog_path.read_bytes()
    found = fresh.reconcile_consumption(request, history_anchor=anchor)
    assert found.consumption_state == "DURABILITY_UNPROVEN"
    assert fresh.recover_consumption(request, history_anchor=anchor).record_sha256 == found.record_sha256
    assert fresh.peeklog_path.read_bytes() == raw and fresh.peek_count() == 1


@pytest.mark.parametrize("target", ["seals", "log"])
def test_missing_history_or_seals_cannot_become_genesis(tmp_path, target):
    vault, anchor, request = _fixture(tmp_path)
    (vault.seals_path if target == "seals" else vault.peeklog_path).unlink()
    for operation in (vault.consume_authorization, vault.reconcile_consumption, vault.recover_consumption):
        with pytest.raises(VaultError, match="missing"):
            operation(request, history_anchor=anchor)
    with pytest.raises(VaultError, match="missing"):
        vault.peek("legacy", window_id="W", result=None)


@pytest.mark.parametrize("replacement", [
    b'{"W":"' + b'a' * 64 + b'","W":"' + b'a' * 64 + b'"}',
    b'[]', b'{"W": NaN}', b'{"W": true}', b'{"W": null}'])
def test_malformed_seals_refuse(tmp_path, replacement):
    vault, anchor, request = _fixture(tmp_path)
    vault.seals_path.write_bytes(replacement)
    with pytest.raises(VaultError):
        vault.reconcile_consumption(request, history_anchor=anchor)


@pytest.mark.parametrize("replacement", [b'[]\n', b'null\n', b'{"kind":"peek","kind":"retire"}\n',
    b'{"kind":"unknown"}\n', b'{"kind":"peek","result":Infinity}\n', b'\n'])
def test_malformed_log_refuses_instead_of_absent(tmp_path, replacement):
    vault, anchor, request = _fixture(tmp_path)
    vault.peeklog_path.write_bytes(replacement)
    with pytest.raises(VaultError):
        vault.reconcile_consumption(request, history_anchor=anchor)


def test_accepted_prefix_detects_chain_valid_rewrite_and_truncation(tmp_path):
    vault, _, request = _fixture(tmp_path)
    vault.peek("legacy", window_id="W", result={"invented": 1})
    raw = vault.peeklog_path.read_bytes()
    row = json.loads(raw)
    anchor = VaultHistoryAnchor(hashlib.sha256(vault.seals_path.read_bytes()).hexdigest(),
        hashlib.sha256(raw).hexdigest(), len(raw), row["record_hash"])
    row["result"] = {"invented": 2}
    row["record_hash"] = vault_module._sha({k: v for k, v in row.items() if k != "record_hash"})
    vault.peeklog_path.write_text(json.dumps(row) + "\n")
    assert HoldoutVault(tmp_path).verify_chain()  # a recomputed chain alone is insufficient
    with pytest.raises(VaultError, match="anchor"):
        vault.consume_authorization(request, history_anchor=anchor)
    vault.peeklog_path.write_bytes(b"")
    with pytest.raises(VaultError, match="anchor"):
        vault.reconcile_consumption(request, history_anchor=anchor)


@pytest.mark.parametrize("field", ["result", "hypothesis_id", "window_hash", "commit"])
def test_chain_valid_consumption_metadata_disagreement_refuses(tmp_path, field):
    vault, anchor, request = _fixture(tmp_path)
    vault.consume_authorization(request, history_anchor=anchor)
    row = json.loads(vault.peeklog_path.read_bytes())
    row[field] = "c" * 64 if field == "window_hash" else "altered"
    row["record_hash"] = vault_module._sha({k: v for k, v in row.items() if k != "record_hash"})
    vault.peeklog_path.write_text(json.dumps(row) + "\n")
    with pytest.raises(VaultError):
        vault.reconcile_consumption(request, history_anchor=anchor)


@pytest.mark.parametrize("target", ["log", "seals", "lock"])
@pytest.mark.parametrize("alias", ["symlink", "hardlink"])
def test_unsafe_file_aliases_refuse(tmp_path, target, alias):
    vault, anchor, request = _fixture(tmp_path)
    path = {"log": vault.peeklog_path, "seals": vault.seals_path,
            "lock": vault.peeklog_path.parent / ".holdout-vault.lock"}[target]
    original = tmp_path / "preserved-original"
    path.rename(original)
    if alias == "symlink":
        path.symlink_to(original)
    else:
        os.link(original, path)
    with pytest.raises(VaultError):
        vault.consume_authorization(request, history_anchor=anchor)


def test_log_path_swap_after_write_refuses_success(tmp_path, monkeypatch):
    vault, anchor, request = _fixture(tmp_path)
    original_sync = os.fsync
    swapped = False
    def swap(fd):
        nonlocal swapped
        result = original_sync(fd)
        if not swapped and os.fstat(fd).st_size > 0:
            swapped = True
            vault.peeklog_path.rename(tmp_path / "original-history")
            vault.peeklog_path.write_bytes(b"")
        return result
    monkeypatch.setattr(os, "fsync", swap)
    with pytest.raises(VaultError, match="identity"):
        vault.consume_authorization(request, history_anchor=anchor)
    assert vault.peek_count() == 0


def test_hostile_types_rejected_before_hooks(tmp_path):
    vault, anchor, request = _fixture(tmp_path)
    class Hostile(str):
        def __eq__(self, other):
            pytest.fail("custom equality executed")
        def __str__(self):
            pytest.fail("custom string hook executed")
    with pytest.raises(VaultError):
        replace(request, request_id=Hostile("request-1"))
    with pytest.raises(VaultError):
        replace(anchor, peek_prefix_bytes=True)
    class RequestSubclass(VaultConsumptionRequest):
        pass
    with pytest.raises(VaultError):
        vault.consume_authorization(RequestSubclass(**request.__dict__), history_anchor=anchor)
    object.__setattr__(request, "source_sha256", Hostile("a" * 64))
    with pytest.raises(VaultError):
        vault.consume_authorization(request, history_anchor=anchor)
    with pytest.raises(VaultError):
        vault.peek("legacy", window_id="W", result={"bad": Hostile("text")})


@pytest.mark.parametrize("operation", ["retire", "seal"])
def test_failed_persistence_does_not_mutate_cached_governance(tmp_path, monkeypatch, operation):
    vault, anchor, request = _fixture(tmp_path)
    def fail(*args, **kwargs):
        raise OSError("injected sync failure")
    monkeypatch.setattr(os, "fsync", fail)
    with pytest.raises(VaultError):
        if operation == "retire":
            vault.retire(request.hypothesis_id, "fixture")
        else:
            vault.seal("new-window", {"invented": 1})
    assert not vault.is_retired(request.hypothesis_id)
    assert not vault.is_sealed("new-window")


def test_failed_atomic_replace_does_not_publish_seal(tmp_path, monkeypatch):
    vault, _, _ = _fixture(tmp_path)
    original = vault.seals_path.read_bytes()
    def fail(*args, **kwargs):
        raise OSError("injected replace failure")
    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(VaultError):
        vault.seal("new-window", {"invented": 2})
    assert vault.seals_path.read_bytes() == original
    assert not vault.is_sealed("new-window")
    assert list(vault.seals_path.parent.glob(".seals-*.tmp"))


def test_fifo_history_fails_without_blocking(tmp_path):
    vault, anchor, request = _fixture(tmp_path)
    vault.peeklog_path.unlink()
    os.mkfifo(vault.peeklog_path)
    with pytest.raises(VaultError, match="regular"):
        vault.reconcile_consumption(request, history_anchor=anchor)


def test_changed_seals_before_atomic_publication_are_preserved(tmp_path, monkeypatch):
    vault, _, _ = _fixture(tmp_path)
    original_sync = os.fsync
    replacement = b'{"outside-writer":"' + b'd' * 64 + b'"}'
    changed = False
    def sync(fd):
        nonlocal changed
        original_sync(fd)
        if not changed:
            changed = True
            vault.seals_path.write_bytes(replacement)
    monkeypatch.setattr(os, "fsync", sync)
    with pytest.raises(VaultError, match="changed before publication"):
        vault.seal("new-window", {"invented": 1})
    assert vault.seals_path.read_bytes() == replacement
    assert not vault.is_sealed("new-window")


def test_final_directory_identity_failure_does_not_update_memory(tmp_path, monkeypatch):
    vault, anchor, request = _fixture(tmp_path)
    original_cold = vault._cold_adopt
    def swap_after_readback(*args, **kwargs):
        state = original_cold(*args, **kwargs)
        vault.peeklog_path.parent.rename(tmp_path / "preserved-directory")
        vault.peeklog_path.parent.mkdir()
        return state
    monkeypatch.setattr(vault, "_cold_adopt", swap_after_readback)
    with pytest.raises(VaultError):
        vault.consume_authorization(request, history_anchor=anchor)
    assert vault.peek_count() == 0


@pytest.mark.parametrize("fresh_instance", [False, True])
@pytest.mark.parametrize("operation", ["seal", "retire"])
def test_lost_seals_and_history_never_reinitialize_behind_persistent_lock(tmp_path, fresh_instance, operation):
    vault, anchor, request = _fixture(tmp_path)
    vault.consume_authorization(request, history_anchor=anchor)
    vault.seals_path.unlink()
    vault.peeklog_path.unlink()
    if fresh_instance:
        vault = HoldoutVault(tmp_path)
    with pytest.raises(VaultError, match="missing"):
        if operation == "seal":
            vault.seal("W", {"invented": [1, 2, 3]})
        else:
            vault.retire("new-hypothesis")
    assert not vault.seals_path.exists() and not vault.peeklog_path.exists()


def test_known_instance_refuses_genesis_after_even_lock_removed(tmp_path):
    vault, anchor, request = _fixture(tmp_path)
    vault.consume_authorization(request, history_anchor=anchor)
    for path in (vault.seals_path, vault.peeklog_path, vault.peeklog_path.parent / ".holdout-vault.lock"):
        path.unlink()
    with pytest.raises(VaultError, match="missing"):
        vault.seal("W", {"invented": [1, 2, 3]})


def test_foreign_owner_path_hooks_are_not_called():
    class ForeignPath:
        def __fspath__(self):
            pytest.fail("foreign path hook called")
    class ForeignString(str):
        def __fspath__(self):
            pytest.fail("foreign string path hook called")
    for root in (ForeignPath(), ForeignString("/unused")):
        with pytest.raises(VaultError, match="exact owner root"):
            HoldoutVault(root)


def test_same_instance_threads_cannot_publish_older_cached_state(tmp_path, monkeypatch):
    import threading
    vault, _, _ = _fixture(tmp_path)
    old_commit_waiting = threading.Event()
    release_old = threading.Event()
    second_attempting = threading.Event()
    second_done = threading.Event()
    original_adopt = vault._adopt
    outcomes = {}
    def pause_old(seals, records):
        if len(records) == 1:
            old_commit_waiting.set()
            assert release_old.wait(5)
        return original_adopt(seals, records)
    monkeypatch.setattr(vault, "_adopt", pause_old)
    def first():
        outcomes["first"] = vault.peek("first", window_id="W", result=None)
    def second():
        second_attempting.set()
        outcomes["second"] = vault.peek("second", window_id="W", result=None)
        second_done.set()
    a, b = threading.Thread(target=first), threading.Thread(target=second)
    a.start()
    assert old_commit_waiting.wait(5)
    b.start()
    assert second_attempting.wait(5)
    try:
        assert not second_done.wait(0.1)
    finally:
        release_old.set()
        a.join(5)
        b.join(5)
    assert not a.is_alive() and not b.is_alive()
    assert outcomes["first"]["peek_n"] == 1
    assert outcomes["second"]["peek_n"] == 2
    assert vault.peek_count() == HoldoutVault(tmp_path).peek_count() == 2
    assert vault.verify_chain()
