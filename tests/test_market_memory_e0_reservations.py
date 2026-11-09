"""Real filesystem and process checks; these do not prove study admission."""
import hashlib
import json
import multiprocessing
import os
from pathlib import Path

import pytest

from engine.research_factory import market_memory_e0_reservations as reservations


BINDING = {"study_id": "study-1", "installation_id": "installed-1", "installation_epoch": "epoch-1",
           "registration_sha256": "a" * 64, "publication_sha256": "b" * 64}
INTENT = {"task_id": "task-1", "condition": "with-memory", "source": "c" * 64}


@pytest.fixture
def store(tmp_path):
    directory = tmp_path / "study"
    directory.mkdir(mode=0o700)
    return reservations.ReservationStore(directory, BINDING)


def _race(directory, operation_id, start, result):
    store = reservations.ReservationStore(directory, BINDING)
    start.wait(15)
    try:
        result.put(store.reserve(operation_id, INTENT)["status"])
    except reservations.ReservationError as exc:
        result.put(str(exc))


def _crash_after_reservation(directory):
    store = reservations.ReservationStore(directory, BINDING)
    assert store.reserve("crashed", INTENT)["status"] == "NEW"
    os._exit(23)


def test_explicit_initialization_and_no_implicit_admission(store):
    with pytest.raises(reservations.ReservationError, match="uninitialized"):
        store.reserve("operation", INTENT)
    assert list(store.directory.iterdir()) == []
    assert store.initialize(2) == store.initialize(2)
    assert store.snapshot()["reserved_looks"] == 0
    with pytest.raises(reservations.ReservationError, match="initialization_conflict"):
        store.initialize(3)
    changed = reservations.ReservationStore(store.directory, {**BINDING, "installation_epoch": "epoch-2"})
    with pytest.raises(reservations.ReservationError, match="binding_conflict"):
        changed.snapshot()


def test_pending_is_never_a_second_execution_permission(store):
    store.initialize(2)
    result = store.reserve("first", INTENT)
    assert result["status"] == "NEW" and result["result"] is None
    result["binding"]["installation_epoch"] = "forged"
    assert store.reserve("first", INTENT)["status"] == "EXISTING_PENDING"
    assert store.snapshot() == {"binding": BINDING, "sequence": 1, "maximum_looks": 2,
                                "consumed_looks": 0, "reserved_looks": 1}
    with pytest.raises(reservations.ReservationError, match="operation_intent_conflict"):
        store.reserve("first", {**INTENT, "condition": "changed"})
    with pytest.raises(reservations.ReservationError, match="completed_result_unavailable"):
        store.read_completed("first", INTENT)
    store.reserve("second", INTENT)
    with pytest.raises(reservations.ReservationError, match="look_budget_exhausted"):
        store.reserve("third", INTENT)


def test_finish_and_retained_exact_result(store):
    store.initialize(1)
    with pytest.raises(reservations.ReservationError, match="reservation_required"):
        store.finish("unknown", INTENT, b"answer")
    store.reserve("first", INTENT)
    first = store.finish("first", INTENT, b"answer\x00")
    assert first == store.finish("first", INTENT, b"answer\x00")
    assert store.reserve("first", INTENT)["status"] == "COMPLETE"
    assert store.read_completed("first", INTENT) == b"answer\x00"
    assert store.snapshot()["consumed_looks"] == 1
    assert store.snapshot()["reserved_looks"] == 0
    with pytest.raises(reservations.ReservationError, match="result_conflict"):
        store.finish("first", INTENT, b"different")
    result_file = next(store.directory.glob("result-*.bin"))
    result_file.write_bytes(b"edited\x00")  # same size; hash must catch it
    with pytest.raises(reservations.ReservationError, match="result_digest_mismatch"):
        store.read_completed("first", INTENT)
    with pytest.raises(reservations.ReservationError, match="result_digest_mismatch"):
        store.finish("first", INTENT, b"answer\x00")


@pytest.mark.parametrize("same_id", [True, False])
def test_real_process_contention_reserves_only_once_and_enforces_budget(store, same_id):
    store.initialize(2)
    context = multiprocessing.get_context("spawn")
    start, results = context.Event(), context.Queue()
    processes = [context.Process(target=_race, args=(str(store.directory),
                 "same" if same_id else f"unique-{index}", start, results)) for index in range(5)]
    for process in processes:
        process.start()
    start.set()
    returned = [results.get(timeout=30) for _ in processes]
    for process in processes:
        process.join(30)
        assert process.exitcode == 0
    results.close()
    if same_id:
        assert sorted(returned) == ["EXISTING_PENDING"] * 4 + ["NEW"]
        assert store.snapshot()["reserved_looks"] == 1
    else:
        assert sorted(returned) == ["NEW"] * 2 + ["look_budget_exhausted"] * 3
        assert store.snapshot()["reserved_looks"] == 2


def test_process_dies_after_reserving_and_reopen_cannot_replay(store):
    store.initialize(1)
    process = multiprocessing.get_context("spawn").Process(
        target=_crash_after_reservation, args=(str(store.directory),))
    process.start()
    process.join(30)
    assert process.exitcode == 23
    reopened = reservations.ReservationStore(store.directory, BINDING)
    assert reopened.reserve("crashed", INTENT)["status"] == "EXISTING_PENDING"
    assert reopened.snapshot()["reserved_looks"] == 1


@pytest.mark.parametrize("boundary", [1, 2, 3, 4])
def test_fsync_failure_never_returns_new_and_never_clears_evidence(store, monkeypatch, boundary):
    store.initialize(1)
    actual = os.fsync
    calls = 0

    def fail_once(fd):
        nonlocal calls
        calls += 1
        if calls == boundary:
            raise OSError("injected fsync failure")
        return actual(fd)

    with monkeypatch.context() as scoped:
        scoped.setattr(os, "fsync", fail_once)
        with pytest.raises(reservations.ReservationError, match="storage_io_failure"):
            store.reserve("first", INTENT)
    retained = {p.name: p.read_bytes() for p in store.directory.iterdir()}
    try:
        result = store.reserve("first", INTENT)
        assert result["status"] == "EXISTING_PENDING"
    except reservations.ReservationError:
        pass  # partial/orphan publication is intentionally not auto-repaired
    assert retained == {p.name: p.read_bytes() for p in store.directory.iterdir()}


@pytest.mark.parametrize("action", ["reserve", "finish"])
def test_interrupted_head_replacement_retains_orphan_and_refuses_retry(store, monkeypatch, action):
    store.initialize(1)
    if action == "finish":
        store.reserve("first", INTENT)

    def fail_replace(*args, **kwargs):
        raise OSError("injected rename failure")

    with monkeypatch.context() as scoped:
        scoped.setattr(os, "replace", fail_replace)
        with pytest.raises(reservations.ReservationError, match="storage_io_failure"):
            if action == "reserve":
                store.reserve("first", INTENT)
            else:
                store.finish("first", INTENT, b"already-produced")
    assert (store.directory / "HEAD.next").exists()
    before = set(store.directory.iterdir())
    with pytest.raises(reservations.ReservationError, match="uncertain_publication"):
        store.reserve("first", INTENT)
    assert set(store.directory.iterdir()) == before


@pytest.mark.parametrize("unsafe", ["symlink", "hardlink", "mode", "fifo"])
def test_unsafe_head_refused_without_following_or_waiting(store, tmp_path, unsafe):
    store.initialize(1)
    head = store.directory / "HEAD.json"
    if unsafe == "mode":
        head.chmod(0o644)
    else:
        original = tmp_path / "original"
        head.rename(original)
        if unsafe == "symlink":
            head.symlink_to(original)
        elif unsafe == "hardlink":
            os.link(original, head)
        else:
            os.mkfifo(head, 0o600)
    with pytest.raises(reservations.ReservationError):
        store.snapshot()


def test_directory_mode_symlink_and_swapped_inode_refused(store, tmp_path, monkeypatch):
    store.directory.chmod(0o755)
    with pytest.raises(reservations.ReservationError, match="unsafe_storage_object"):
        store.initialize(1)
    store.directory.chmod(0o700)
    alias = tmp_path / "alias"
    alias.symlink_to(store.directory)
    with pytest.raises(reservations.ReservationError):
        reservations.ReservationStore(alias, BINDING).initialize(1)
    store.initialize(1)
    original = store._write_new

    def swap(fd, name, body):
        original(fd, name, body)
        if name == "HEAD.next":
            store.directory.rename(tmp_path / "detached")
            store.directory.mkdir(mode=0o700)

    monkeypatch.setattr(store, "_write_new", swap)
    with pytest.raises(reservations.ReservationError, match="directory_identity_changed"):
        store.reserve("first", INTENT)
    assert (tmp_path / "detached" / "HEAD.next").exists()


@pytest.mark.parametrize("corruption", ["torn", "duplicate", "noncanonical", "chain", "orphan", "missing"])
def test_corrupt_and_uncertain_journal_is_never_reset(store, corruption):
    store.initialize(1)
    head = store.directory / "HEAD.json"
    if corruption == "torn":
        head.write_bytes(b'{"sequence":')
    elif corruption == "duplicate":
        head.write_bytes(b'{"sequence":0,"sequence":1,"sha256":"' + b"a" * 64 + b'"}')
    elif corruption == "noncanonical":
        head.write_text(json.dumps(json.loads(head.read_bytes()), indent=2))
    elif corruption == "chain":
        event = store.directory / "event-0000.json"
        event.write_bytes(event.read_bytes().replace(b'"maximum_looks":1', b'"maximum_looks":2'))
    elif corruption == "missing":
        head.unlink()
    else:
        (store.directory / "event-0001.json").write_bytes(b"partial")
    before = {p.name: p.read_bytes() for p in store.directory.iterdir()}
    with pytest.raises(reservations.ReservationError):
        store.initialize(1)
    assert before == {p.name: p.read_bytes() for p in store.directory.iterdir()}


@pytest.mark.parametrize("maximum", [True, 0, 1025, 1.0, "1"])
def test_exact_maximum_type_and_bound(store, maximum):
    with pytest.raises(reservations.ReservationError, match="invalid_maximum_looks"):
        store.initialize(maximum)


def test_strict_intent_types_cycles_unicode_and_bounds(store):
    class DictSubclass(dict):
        pass

    store.initialize(1)
    cycle = []
    cycle.append(cycle)
    deep = []
    for _ in range(20):
        deep = [deep]
    for invalid in (DictSubclass(a=1), {"n": float("nan")}, {1: "key"},
                    {"cycle": cycle}, {"deep": deep}, {"surrogate": "\ud800"},
                    {"big": "x" * 65536}, {"many": [0] * 4096}):
        with pytest.raises(reservations.ReservationError):
            store.reserve("first", invalid)
    assert store.snapshot()["reserved_looks"] == 0
    assert store.reserve("first", {"legal": [None, False, 1, 1.2, "中文"]})["status"] == "NEW"


def test_identifiers_binding_and_result_bounds(store):
    for key in ("study_id", "registration_sha256"):
        with pytest.raises(reservations.ReservationError):
            reservations.ReservationStore(store.directory, {**BINDING, key: "../escape"})
    store.initialize(1)
    for op in ("", "../escape", "x" * 129, 1, True):
        with pytest.raises(reservations.ReservationError):
            store.reserve(op, INTENT)
    store.reserve("first", INTENT)
    for result in (b"", b"x" * (1024 * 1024 + 1), bytearray(b"x"), "text"):
        with pytest.raises(reservations.ReservationError, match="bounded_result"):
            store.finish("first", INTENT, result)
    store.finish("first", INTENT, b"x" * (1024 * 1024))
    assert hashlib.sha256(store.read_completed("first", INTENT)).digest() == hashlib.sha256(b"x" * (1024 * 1024)).digest()
