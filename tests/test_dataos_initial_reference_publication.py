"""Synthetic receipt-only initial publication through the existing Data OS owner.

All six inputs are made under tmp_path. These tests exercise a new commit/recovery
boundary; no repository market data, source capture, or canonical generation is used.
"""
from __future__ import annotations

from datetime import date
import errno
import hashlib
import json
import os
from pathlib import Path
import select
import stat
import subprocess
import sys
import threading

import pytest

from engine.entry_radar.replay import identity_observation_snapshot as reader
from engine.neuralweb import market_memory_identity_candidate as candidate
from lib.dataos.identity import IdentityError
from scripts import build_security_master as BUILD
from tests.test_dataos_identity import _obs_base, _obs_iso, _obs_json
from tests.test_market_memory_identity_candidate import _r23_actual_parquet_supplied


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@pytest.fixture
def initial(tmp_path, monkeypatch):
    original, _history, aliases, master = _obs_base()
    receipt = {"prospective_reference": original,
               "legacy_metadata": {"preserve": [None, False, 0, "original"]}}
    receipt_bytes, artifacts = _r23_actual_parquet_supplied(
        (receipt, {}, aliases, master))
    root = tmp_path / "reference"
    root.mkdir()
    for name, raw in {**artifacts, BUILD.RECEIPT_NAME: receipt_bytes}.items():
        (root / name).write_bytes(raw)
    (root / BUILD.RECEIPT_NAME).chmod(0o640)
    monkeypatch.setattr(BUILD, "_git_sha", lambda: "3" * 40)
    return root, receipt_bytes, artifacts


def _expected(initial):
    _root, receipt, artifacts = initial
    return {"expected_receipt_sha256": _sha(receipt),
            "expected_artifact_sha256": {n: _sha(raw) for n, raw in artifacts.items()}}


def _promote(initial):
    return BUILD.promote_initial_reference_generation(initial[0], **_expected(initial))


def _prepared(initial):
    return candidate.build_parquet_bound_initial_candidate(
        initial[1], initial[2], code_version="3" * 40)


def _inspect(initial, prepared=None):
    prepared = prepared or _prepared(initial)
    return BUILD.inspect_initial_reference_publication(
        initial[0], original_receipt_sha256=_sha(initial[1]),
        candidate_receipt_sha256=prepared.candidate.candidate_receipt_sha256,
        artifact_sha256={n: _sha(raw) for n, raw in initial[2].items()})


def _files(root):
    return {path.name: path.read_bytes() for path in root.iterdir()}


def _original_files(initial):
    return {**initial[2], BUILD.RECEIPT_NAME: initial[1]}


def test_promote_receipt_only_and_use_actual_read(initial):
    root, receipt_before, artifacts = initial
    artifact_stats = {n: (root / n).stat() for n in artifacts}
    result = _promote(initial)
    prepared = result.prepared
    raw = (root / BUILD.RECEIPT_NAME).read_bytes()
    context = json.loads(raw)
    assert raw == prepared.candidate.candidate_receipt_bytes
    assert result.directory_synced is True
    assert result.read.receipt.receipt_sha256 == _sha(raw)
    assert result.read.receipt.generation_id == prepared.candidate.generation_id
    assert dict(result.read.receipt.artifact_sha256) == {
        n: _sha(value) for n, value in artifacts.items()}
    assert context["publication"]["code_version"] == "3" * 40
    assert context["identity_observations"]["attempts"] == []
    assert {key: context[key] for key in json.loads(receipt_before)} == json.loads(receipt_before)
    assert not prepared.source_authenticated
    assert not prepared.records_bound_to_artifacts
    assert not prepared.identity_admitted and not prepared.current_read_admitted
    assert not prepared.published and not prepared.candidate.published
    assert set(_files(root)) == {*artifacts, BUILD.RECEIPT_NAME}
    for name, before in artifact_stats.items():
        after = (root / name).stat()
        assert (root / name).read_bytes() == artifacts[name]
        assert (after.st_ino, after.st_mtime_ns, after.st_ctime_ns) == (
            before.st_ino, before.st_mtime_ns, before.st_ctime_ns)
    assert stat.S_IMODE((root / BUILD.RECEIPT_NAME).stat().st_mode) == 0o640

    observed = result.read
    completed = int(observed.receipt.read_completed_at_utc_ns)
    assert completed >= int(observed.receipt.read_started_at_utc_ns)
    table = observed.alias_table()
    kwargs = {"snapshot_receipts": (observed.receipt,)}
    too_early = table.resolve_binding(
        "polygon", "MU", date(2026, 10, 7),
        decision_at=_obs_iso(completed - 1), **kwargs)
    assert (too_early.status, too_early.reason) == (
        "UNAVAILABLE", "NO_ENROLLED_SNAPSHOT_BY_CUTOFF")
    bound = table.resolve_binding(
        "polygon", "MU", date(2026, 10, 7),
        decision_at=_obs_iso(completed), **kwargs)
    assert (bound.status, bound.security_id) == ("BOUND", "SEC:US-XNAS-MU")
    for symbol in ("SPY", "QQQ", "SMH"):
        refused = table.resolve_binding(
            "polygon", symbol, date(2026, 10, 7),
            decision_at=_obs_iso(completed), **kwargs)
        assert (refused.status, refused.reason) == ("REFUSED", "canonical_identity_refused")
    with pytest.raises(IdentityError, match="cannot be preserved"):
        BUILD._assert_no_unpreserved_native_generation(root)


@pytest.mark.parametrize("member", (*reader.REFERENCE_ARTIFACTS, BUILD.RECEIPT_NAME))
def test_stale_preimage_refuses_before_replacement(initial, member, monkeypatch):
    root = initial[0]
    (root / member).write_bytes((root / member).read_bytes() + b"\nchanged")
    before = _files(root)
    monkeypatch.setattr(BUILD.os, "replace",
                        lambda *_a, **_kw: pytest.fail("stale preimage was replaced"))
    with pytest.raises(IdentityError, match="preimage"):
        _promote(initial)
    assert _files(root) == before


@pytest.mark.parametrize("member", (*reader.REFERENCE_ARTIFACTS, BUILD.RECEIPT_NAME))
def test_every_preimage_is_rechecked_after_preparation(initial, member, monkeypatch):
    root = initial[0]
    real = candidate.build_parquet_bound_initial_candidate
    def change_after_prepare(*args, **kwargs):
        prepared = real(*args, **kwargs)
        (root / member).write_bytes((root / member).read_bytes() + b"\nchanged")
        return prepared
    monkeypatch.setattr(candidate, "build_parquet_bound_initial_candidate", change_after_prepare)
    monkeypatch.setattr(BUILD.os, "replace",
                        lambda *_a, **_kw: pytest.fail("changed preimage was replaced"))
    with pytest.raises(IdentityError, match="preimage"):
        _promote(initial)
    expected = _original_files(initial)
    expected[member] += b"\nchanged"
    assert _files(root) == expected


@pytest.mark.parametrize("change", ("missing", "extra", "uppercase", "wrong_type"))
def test_expected_vector_is_closed_and_validated_before_any_write(initial, change):
    kwargs = _expected(initial)
    if change == "missing":
        kwargs["expected_artifact_sha256"].pop(reader.REFERENCE_ARTIFACTS[0])
    elif change == "extra":
        kwargs["expected_artifact_sha256"]["unowned.parquet"] = "a" * 64
    elif change == "uppercase":
        kwargs["expected_receipt_sha256"] = "A" * 64
    else:
        kwargs["expected_artifact_sha256"] = list(kwargs["expected_artifact_sha256"].items())
    with pytest.raises(IdentityError):
        BUILD.promote_initial_reference_generation(initial[0], **kwargs)
    assert _files(initial[0]) == _original_files(initial)


@pytest.mark.parametrize("kind", ("relative", "parent", "missing", "symlink"))
def test_target_must_be_existing_absolute_directory(initial, tmp_path, kind):
    root = initial[0]
    if kind == "relative":
        target = Path("relative-reference")
    elif kind == "parent":
        target = root / ".." / root.name
    elif kind == "missing":
        target = tmp_path / "not-created"
    else:
        target = tmp_path / "reference-link"
        target.symlink_to(root, target_is_directory=True)
    with pytest.raises(IdentityError):
        BUILD.promote_initial_reference_generation(target, **_expected(initial))
    assert _files(root) == _original_files(initial)
    if kind == "missing":
        assert not target.exists()


@pytest.mark.parametrize("member", (BUILD.RECEIPT_NAME, "issuer_migrations.parquet"))
def test_file_symlink_refusal_cannot_replace_outside_target(initial, tmp_path, member):
    root = initial[0]
    outside = tmp_path / "outside"
    raw = (root / member).read_bytes()
    outside.write_bytes(raw)
    (root / member).unlink()
    (root / member).symlink_to(outside)
    with pytest.raises(IdentityError):
        _promote(initial)
    assert (root / member).is_symlink()
    assert outside.read_bytes() == raw


@pytest.mark.parametrize("key", ("publication", "identity_observations"))
def test_existing_native_key_is_never_overwritten(initial, key):
    root, old, artifacts = initial
    receipt = json.loads(old)
    receipt[key] = None
    raw = _obs_json(receipt)
    (root / BUILD.RECEIPT_NAME).write_bytes(raw)
    changed = (root, raw, artifacts)
    with pytest.raises(IdentityError):
        _promote(changed)
    assert _files(root) == _original_files(changed)


def test_refuse_changed_source_identity_before_commit(initial, monkeypatch):
    identities = iter(("3" * 40, "4" * 40))
    monkeypatch.setattr(BUILD, "_git_sha", lambda: next(identities))
    with pytest.raises(IdentityError, match="code identity"):
        _promote(initial)
    assert _files(initial[0]) == _original_files(initial)


def test_missing_code_identity_does_not_stage_or_publish(initial, monkeypatch):
    monkeypatch.setattr(BUILD, "_git_sha", lambda: None)
    with pytest.raises(IdentityError):
        _promote(initial)
    assert _files(initial[0]) == _original_files(initial)


@pytest.mark.parametrize("after_replace, expected", ((False, "NOT_APPLIED"), (True, "APPLIED")))
def test_atomic_replace_failure_is_reconciled_without_retry(initial, monkeypatch, after_replace, expected):
    real = BUILD.os.replace
    calls = []
    failure = OSError(errno.EIO, "SYNTHETIC replacement response lost")
    def fail_replace(*args, **kwargs):
        calls.append((args, kwargs))
        if after_replace:
            real(*args, **kwargs)
        raise failure
    monkeypatch.setattr(BUILD.os, "replace", fail_replace)
    with pytest.raises(BUILD.InitialReferencePromotionError) as caught:
        _promote(initial)
    error = caught.value
    assert error.__cause__ is failure
    assert error.effect_state == expected
    assert error.directory_synced is False
    assert len(calls) == 1
    assert calls[0][1]["src_dir_fd"] == calls[0][1]["dst_dir_fd"]
    assert _inspect(initial, error.prepared) == expected
    expected_files = _original_files(initial)
    if after_replace:
        expected_files[BUILD.RECEIPT_NAME] = error.prepared.candidate.candidate_receipt_bytes
    assert _files(initial[0]) == expected_files


def test_file_flush_failure_preserves_original_and_primary_error(initial, monkeypatch):
    failure = OSError(errno.ENOSPC, "SYNTHETIC staged receipt flush failure")
    monkeypatch.setattr(BUILD.os, "fsync", lambda _fd: (_ for _ in ()).throw(failure))
    with pytest.raises(OSError) as caught:
        _promote(initial)
    assert caught.value is failure
    assert _files(initial[0]) == _original_files(initial)


def test_directory_flush_failure_reports_visible_bytes_without_claiming_durability(initial, monkeypatch):
    real = BUILD.os.fsync
    failure = OSError(errno.EIO, "SYNTHETIC directory flush failure")
    def fail_directory(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise failure
        return real(fd)
    monkeypatch.setattr(BUILD.os, "fsync", fail_directory)
    with pytest.raises(BUILD.InitialReferencePromotionError) as caught:
        _promote(initial)
    assert caught.value.__cause__ is failure
    assert caught.value.effect_state == "APPLIED"
    assert caught.value.directory_synced is False
    assert _inspect(initial, caught.value.prepared) == "APPLIED"


def test_readback_failure_retains_applied_receipt_and_no_fabricated_read(initial, monkeypatch):
    failure = IdentityError("SYNTHETIC actual native read failure")
    monkeypatch.setattr(reader, "read_identity_snapshot",
                        lambda _root: (_ for _ in ()).throw(failure))
    with pytest.raises(BUILD.InitialReferencePromotionError) as caught:
        _promote(initial)
    assert caught.value.__cause__ is failure
    assert caught.value.effect_state == "APPLIED"
    assert caught.value.directory_synced is True
    assert not hasattr(caught.value, "read")
    assert _inspect(initial, caught.value.prepared) == "APPLIED"


def test_unexpected_postcommit_artifact_is_unknown_and_never_rolled_back(initial, monkeypatch):
    root = initial[0]
    real = BUILD.os.replace
    calls = []
    changed_name = "security_migrations.parquet"
    def replace_then_change(*args, **kwargs):
        calls.append(1)
        real(*args, **kwargs)
        (root / changed_name).write_bytes(b"SYNTHETIC noncooperating writer")
    monkeypatch.setattr(BUILD.os, "replace", replace_then_change)
    with pytest.raises(BUILD.InitialReferencePromotionError) as caught:
        _promote(initial)
    assert caught.value.effect_state == "EFFECT_UNKNOWN"
    assert len(calls) == 1
    assert (root / BUILD.RECEIPT_NAME).read_bytes() == (
        caught.value.prepared.candidate.candidate_receipt_bytes)
    assert (root / changed_name).read_bytes() == b"SYNTHETIC noncooperating writer"
    assert _inspect(initial, caught.value.prepared) == "EFFECT_UNKNOWN"


def test_directory_substitution_before_commit_cannot_write_replacement(initial, tmp_path, monkeypatch):
    root = initial[0]
    moved = tmp_path / "moved-original"
    real = candidate.build_parquet_bound_initial_candidate
    def substitute(*args, **kwargs):
        prepared = real(*args, **kwargs)
        root.rename(moved)
        root.mkdir()
        (root / "sentinel").write_bytes(b"replacement directory")
        return prepared
    monkeypatch.setattr(candidate, "build_parquet_bound_initial_candidate", substitute)
    with pytest.raises(IdentityError, match="target changed"):
        _promote(initial)
    assert _files(root) == {"sentinel": b"replacement directory"}
    assert _files(moved) == _original_files(initial)


def test_promotion_participates_in_the_existing_writer_lock(initial):
    root = initial[0]
    entered = threading.Event()
    release = threading.Event()
    errors = []
    def hold_existing_writer():
        try:
            with BUILD._reference_writer_scope(root):
                entered.set()
                if not release.wait(15):
                    raise RuntimeError("test writer release timeout")
        except BaseException as exc:
            errors.append(exc)
            entered.set()
    holder = threading.Thread(target=hold_existing_writer)
    holder.start()
    try:
        assert entered.wait(15)
        assert not errors
        with pytest.raises(IdentityError, match="writer busy"):
            _promote(initial)
        assert _files(root) == _original_files(initial)
    finally:
        release.set()
        holder.join(15)
    assert not holder.is_alive()
    assert not errors
    assert _promote(initial).directory_synced is True


def test_reconciliation_is_read_only_and_distinguishes_all_three_states(initial, monkeypatch):
    prepared = _prepared(initial)
    original_files = _files(initial[0])
    with monkeypatch.context() as guarded:
        guarded.setattr(BUILD, "_reference_writer_scope",
                        lambda _root: pytest.fail("inspection acquired a writer scope"))
        real_open = os.open
        def read_only_open(path, flags, *args, **kwargs):
            assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
            return real_open(path, flags, *args, **kwargs)
        guarded.setattr(BUILD.os, "open", read_only_open)
        assert _inspect(initial, prepared) == "NOT_APPLIED"
    assert _files(initial[0]) == original_files
    result = _promote(initial)
    assert _inspect(initial, prepared) == "APPLIED"
    (initial[0] / "issuer_master.parquet").write_bytes(b"unexpected")
    assert _inspect(initial, prepared) == "EFFECT_UNKNOWN"
    (initial[0] / BUILD.RECEIPT_NAME).unlink()
    assert _inspect(initial, result.prepared) == "EFFECT_UNKNOWN"


def test_interrupt_after_replace_preserves_interrupt_and_reconciliation_note(initial, monkeypatch):
    real = BUILD.os.replace
    failure = KeyboardInterrupt("SYNTHETIC interruption after replace")
    def interrupt(*args, **kwargs):
        real(*args, **kwargs)
        raise failure
    monkeypatch.setattr(BUILD.os, "replace", interrupt)
    with pytest.raises(KeyboardInterrupt) as caught:
        _promote(initial)
    assert caught.value is failure
    assert any("effect_state=APPLIED" in note and "directory_synced=False" in note
               for note in caught.value.__notes__)
    assert _inspect(initial) == "APPLIED"


def test_process_death_after_replace_is_reconciled_without_republication(initial):
    # A fresh interpreter avoids forking an Arrow/BLAS-loaded interpreter.
    # This child stops immediately after the real rename, before directory fsync.
    program = """
import json, signal, sys
from pathlib import Path
from scripts import build_security_master as owner
owner._git_sha = lambda: "3" * 40
real = owner.os.replace
def stop_after_replace(*args, **kwargs):
    real(*args, **kwargs)
    print("REPLACED", flush=True)
    signal.pause()
owner.os.replace = stop_after_replace
owner.promote_initial_reference_generation(Path(sys.argv[1]), **json.loads(sys.argv[2]))
"""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1",
               OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", VECLIB_MAXIMUM_THREADS="1",
               NUMEXPR_NUM_THREADS="1")
    process = subprocess.Popen(
        [sys.executable, "-c", program, str(initial[0]), json.dumps(_expected(initial))],
        cwd=BUILD.ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        readable, _, _ = select.select([process.stdout], [], [], 30)
        assert readable, "fresh child did not reach the receipt commit point"
        line = process.stdout.readline()
        assert line == "REPLACED\n", (line, process.poll())
    finally:
        if process.poll() is None:
            process.kill()
        stdout, stderr = process.communicate(timeout=15)
    assert process.returncode == -9, (stdout, stderr)
    assert _inspect(initial) == "APPLIED"
    for name, raw in initial[2].items():
        assert (initial[0] / name).read_bytes() == raw
    # Recovery observes; a second initial invocation refuses native history.
    current = (initial[0], (initial[0] / BUILD.RECEIPT_NAME).read_bytes(), initial[2])
    with pytest.raises(IdentityError):
        _promote(current)
    assert _inspect(initial) == "APPLIED"


@pytest.mark.parametrize("progress", ("short", "zero"))
def test_staged_short_writes_are_complete_or_refused_before_commit(initial, monkeypatch, progress):
    real = os.write
    calls = []
    def write_part(fd, raw):
        calls.append(len(raw))
        return real(fd, raw[:17]) if progress == "short" else 0
    monkeypatch.setattr(BUILD.os, "write", write_part)
    if progress == "short":
        result = _promote(initial)
        assert len(calls) > 1
        assert (initial[0] / BUILD.RECEIPT_NAME).read_bytes() == (
            result.prepared.candidate.candidate_receipt_bytes)
    else:
        with pytest.raises(OSError) as caught:
            _promote(initial)
        assert caught.value.errno == errno.EIO
        assert len(calls) == 1
        assert _files(initial[0]) == _original_files(initial)


@pytest.mark.parametrize("cleanup", ("close", "unlink", "both"))
def test_staging_cleanup_never_masks_the_original_flush_failure(initial, monkeypatch, cleanup):
    real_open, real_close, real_unlink = os.open, os.close, os.unlink
    staged_fd = None
    close_calls = []
    failure = OSError(errno.ENOSPC, "SYNTHETIC primary staging flush failure")
    def track_open(path, *args, **kwargs):
        nonlocal staged_fd
        fd = real_open(path, *args, **kwargs)
        if isinstance(path, str) and path.startswith(".initial-reference-"):
            staged_fd = fd
        return fd
    def fail_close(fd):
        real_close(fd)
        if fd == staged_fd:
            close_calls.append(fd)
            if cleanup in ("close", "both"):
                raise OSError(errno.EIO, "SYNTHETIC secondary close failure")
    def fail_unlink(path, *args, **kwargs):
        if isinstance(path, str) and path.startswith(".initial-reference-"):
            if cleanup in ("unlink", "both"):
                raise OSError(errno.EIO, "SYNTHETIC secondary unlink failure")
        return real_unlink(path, *args, **kwargs)
    monkeypatch.setattr(BUILD.os, "open", track_open)
    monkeypatch.setattr(BUILD.os, "close", fail_close)
    monkeypatch.setattr(BUILD.os, "unlink", fail_unlink)
    monkeypatch.setattr(BUILD.os, "fsync", lambda _fd: (_ for _ in ()).throw(failure))
    with pytest.raises(OSError) as caught:
        _promote(initial)
    assert caught.value is failure
    assert len(close_calls) == 1
    assert len(caught.value.__notes__) == (2 if cleanup == "both" else 1)
    for name, raw in _original_files(initial).items():
        assert (initial[0] / name).read_bytes() == raw
    temporary = [p for p in initial[0].iterdir() if p.name.startswith(".initial-reference-")]
    assert len(temporary) == (1 if cleanup in ("unlink", "both") else 0)


def test_staging_name_collision_never_deletes_an_unowned_file(initial, monkeypatch):
    import uuid
    token = uuid.UUID("f" * 32)
    monkeypatch.setattr(uuid, "uuid4", lambda: token)
    foreign = initial[0] / f".initial-reference-{token.hex}.tmp"
    foreign.write_bytes(b"SYNTHETIC pre-existing unrelated stage")
    before = _files(initial[0])
    with pytest.raises(FileExistsError):
        _promote(initial)
    assert _files(initial[0]) == before


def test_lock_cleanup_failure_after_successful_read_reports_actual_effect(initial, monkeypatch):
    import fcntl
    real = fcntl.flock
    failure = OSError(errno.EIO, "SYNTHETIC writer unlock response failure")
    def fail_unlock(fd, operation):
        real(fd, operation)
        if operation == fcntl.LOCK_UN:
            raise failure
    monkeypatch.setattr(fcntl, "flock", fail_unlock)
    with pytest.raises(BUILD.InitialReferencePromotionError) as caught:
        _promote(initial)
    assert caught.value.__cause__ is failure
    assert caught.value.effect_state == "APPLIED"
    assert caught.value.directory_synced is True
    assert _inspect(initial, caught.value.prepared) == "APPLIED"


def test_postcommit_directory_clone_cannot_claim_effect_on_the_original_target(
    initial, tmp_path, monkeypatch,
):
    root = initial[0]
    moved = tmp_path / "replaced-original-directory"
    real = BUILD.os.replace
    def substitute_after_replace(*args, **kwargs):
        real(*args, **kwargs)
        root.rename(moved)
        root.mkdir()
        for path in moved.iterdir():
            (root / path.name).write_bytes(path.read_bytes())
    monkeypatch.setattr(BUILD.os, "replace", substitute_after_replace)
    with pytest.raises(BUILD.InitialReferencePromotionError) as caught:
        _promote(initial)
    assert caught.value.effect_state == "EFFECT_UNKNOWN"
    assert _files(root) == _files(moved)
    # Standalone inspection only observes the current path's bytes; it does not
    # establish that this operation affected the original directory object.
    assert _inspect(initial, caught.value.prepared) == "APPLIED"
