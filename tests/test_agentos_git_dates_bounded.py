"""Bounded date acquisition: real threads, canonical Git semantics, no cache."""
from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
import subprocess
import threading

import pytest

from scripts import agentos


def batch_reader():
    reader = getattr(agentos, "git_dates_batch", None)
    assert callable(reader), "bounded canonical git date acquisition is absent"
    return reader


def test_parallel_dates_are_bounded_and_preserve_input_order(monkeypatch):
    reader = batch_reader()
    paths = [Path(f"WS-{i:02}.md") for i in range(12)]
    barrier = threading.Barrier(4)
    lock = threading.Lock()
    active = peak = 0
    seen = []

    def dates(path):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            seen.append(path)
        try:
            barrier.wait(timeout=5)
            return ("2026-01-01", str(path))
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(agentos, "git_dates", dates)
    result = reader(paths)
    assert list(result) == paths
    assert result == {path: ("2026-01-01", str(path)) for path in paths}
    assert sorted(seen) == paths
    assert peak == 4 and active == 0


def test_submission_does_not_eagerly_queue_the_whole_store(monkeypatch):
    reader = batch_reader()
    release = threading.Event()
    first_batch_started = threading.Event()
    lock = threading.Lock()
    yielded = []
    calls = 0
    output = []
    errors = []

    def paths():
        for i in range(40):
            yielded.append(Path(f"WS-{i}.md"))
            yield yielded[-1]

    def dates(path):
        nonlocal calls
        with lock:
            calls += 1
            if calls == 4:
                first_batch_started.set()
        assert release.wait(timeout=5)
        return None, None

    def collect():
        try:
            output.append(reader(paths()))
        except BaseException as exc:
            errors.append(exc)

    monkeypatch.setattr(agentos, "git_dates", dates)
    thread = threading.Thread(target=collect)
    thread.start()
    try:
        assert first_batch_started.wait(timeout=5)
        assert len(yielded) == 4
    finally:
        release.set()
        thread.join(timeout=5)
    assert not thread.is_alive() and not errors
    assert len(output[0]) == 40 and calls == 40


def test_empty_input_does_not_construct_an_executor(monkeypatch):
    reader = batch_reader()
    def forbidden(*args, **kwargs):
        raise AssertionError("empty store must not create worker threads")
    monkeypatch.setattr(agentos, "ThreadPoolExecutor", forbidden)
    assert reader([]) == {}


def test_repeat_read_observes_new_dates_without_a_persistent_cache(monkeypatch):
    reader = batch_reader()
    path = Path("WS-ONE.md")
    answer = [(None, None)]
    monkeypatch.setattr(agentos, "git_dates", lambda _: answer[0])
    assert reader([path]) == {path: (None, None)}
    answer[0] = ("2026-01-01", "2026-02-02")
    assert reader([path]) == {path: answer[0]}


def test_unexpected_failure_is_propagated_after_other_calls_finish(monkeypatch):
    reader = batch_reader()
    barrier = threading.Barrier(4)
    finished = []
    def dates(path):
        barrier.wait(timeout=5)
        try:
            if path.name == "bad":
                raise ValueError("fixture failure")
            return None, None
        finally:
            finished.append(path.name)
    monkeypatch.setattr(agentos, "git_dates", dates)
    with pytest.raises(ValueError, match="fixture failure"):
        reader([Path(name) for name in ("bad", "b", "c", "d")])
    assert sorted(finished) == ["b", "bad", "c", "d"]


def test_build_records_uses_one_batch_and_keeps_sorted_workstream_output(tmp_path, monkeypatch):
    batch_reader()
    store = agentos.Store(tmp_path / "agentos")
    for key in ("ZETA", "ALPHA"):
        store.records[f"WS/{key}"] = {
            "key": key, "title": key, "status": "proposed", "waves": [],
        }
        store.paths[f"WS/{key}"] = tmp_path / f"WS-{key}.md"
    calls = []
    def batch(paths):
        paths = list(paths)
        calls.append(paths)
        return {path: ("2026-01-01", "2026-02-02") for path in paths}
    monkeypatch.setattr(agentos, "git_dates_batch", batch)
    rows, _ = agentos.build_records(store, now=dt.datetime(2026, 9, 7, tzinfo=dt.timezone.utc),
        builds=None, p0_status=None, worktrees={"branches": []})
    assert len(calls) == 1
    assert calls[0] == [store.paths["WS/ALPHA"], store.paths["WS/ZETA"]]
    assert [row["key"] for row in rows] == ["ALPHA", "ZETA"]
    assert all(row["created"] == "2026-01-01" and row["updated"] == "2026-02-02" for row in rows)


@pytest.fixture
def history(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    def git(*args, date=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="Fixture", GIT_COMMITTER_NAME="Fixture",
            GIT_AUTHOR_EMAIL="fixture@example.test", GIT_COMMITTER_EMAIL="fixture@example.test")
        if date:
            env.update(GIT_AUTHOR_DATE=date + "T12:00:00+0000", GIT_COMMITTER_DATE=date + "T12:00:00+0000")
        return subprocess.check_output(["git", "-C", str(root), *args], env=env,
            text=True, stderr=subprocess.DEVNULL, timeout=10)
    git("init", "-q")
    git("config", "core.hooksPath", str(tmp_path / "no-hooks"))
    first, renamed, other = [root / name for name in ("old.md", "renamed.md", "other.md")]
    first.write_text("original\n")
    other.write_text("other\n")
    git("add", "--", ".")
    git("commit", "-qm", "initial", date="2026-01-01")
    first.write_text("original\nchanged\n")
    git("add", "--", ".")
    git("commit", "-qm", "modify", date="2026-02-02")
    git("mv", "old.md", "renamed.md")
    git("commit", "-qm", "rename", date="2026-03-03")
    first.write_text("readded\n")
    git("add", "--", "old.md")
    git("commit", "-qm", "readd", date="2026-04-04")
    (root / "untracked.md").write_text("untracked\n")
    monkeypatch.setattr(agentos, "_ROOT", root)
    return root, git


@pytest.mark.parametrize("name", ["old.md", "renamed.md", "other.md", "untracked.md", "absent.md"])
def test_real_git_rename_readd_and_missing_paths_match_canonical_dates(history, name):
    root, _ = history
    path = root / name
    expected = agentos.git_dates(path)
    assert batch_reader()([path])[path] == expected
    if name == "old.md":
        assert expected == ("2026-01-01", "2026-04-04")
    elif name == "other.md":
        assert expected == ("2026-01-01", "2026-01-01")
    elif name in {"untracked.md", "absent.md"}:
        assert expected == (None, None)


def test_git_read_failures_keep_existing_unknown_semantics(monkeypatch):
    monkeypatch.setattr(agentos, "_git", lambda *args, **kwargs: None)
    paths = [agentos._ROOT / f"WS-{i}.md" for i in range(9)]
    assert batch_reader()(paths) == {path: (None, None) for path in paths}


def test_path_outside_repository_does_not_gain_history(tmp_path):
    path = tmp_path / "outside.md"
    path.write_text("not an organizational record")
    assert batch_reader()([path]) == {path: (None, None)}
