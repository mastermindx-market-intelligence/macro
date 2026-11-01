"""Temporary files only; never read host cgroups/proc or launch workloads."""
import errno
import os

import pytest
import cgroup_observer as c


def controls(path, cpu="max 100000", memory="max", swap="max", pids="max"):
    path.mkdir(exist_ok=True)
    for name, value in zip(c.LIMIT_FILES, (cpu, memory, swap, pids)):
        (path / name).write_text(value + "\n")


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    parent = root / "system.slice"
    controls(parent, cpu="25000 100000", memory="134217728", pids="32")
    leaf = parent / "docker-owned.scope"
    controls(leaf, cpu="50000 100000", memory="268435456", swap="0", pids="64")
    (leaf / "cgroup.type").write_text("domain\n")
    (leaf / "cgroup.events").write_text("populated 1\nfrozen 0\n")
    (leaf / "cgroup.procs").write_text("11\n12\n")
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    expected = c.identity(os.fstat(fd))
    def observe(**kw):
        args = dict(expected_root_identity=expected, deadline=101., clock=lambda: 100.)
        args.update(kw)
        return c.observe(fd, ("system.slice", "docker-owned.scope"), **args)
    try:
        yield root, parent, leaf, fd, expected, observe
    finally:
        os.close(fd)


def test_tighter_ancestors_unknown_root_and_proof_flags(tree):
    root, parent, leaf, fd, expected, observe = tree
    result = observe()
    limits = result["configured_visible_ancestor_limits"]
    assert limits["cpu.max"] == {"observed_minimum": {"numerator": 1, "denominator": 4},
                                 "unit": "cpu_seconds_per_second", "source_depths": [1],
                                 "visible_level_absent": True, "summary_is_complete": False}
    assert limits["memory.max"]["observed_minimum"] == 134217728
    assert limits["memory.swap.max"]["observed_minimum"] == 0
    assert limits["pids.max"]["observed_minimum"] == 32
    assert result["observation"]["leaf"]["cgroup.procs"]["value"] == [11, 12]
    assert result["raw_bytes_read"] > 0
    assert all(value is False for key, value in result.items()
               if key.endswith("proven") or key in ("complete_helper_census", "candidate_admission", "containment_qualified"))
    assert c.identity(os.fstat(fd)) == expected


def test_complete_visible_max_is_not_effective_limit_proof(tree):
    root, parent, leaf, *_, observe = tree
    for directory in (root, parent, leaf):
        controls(directory)
    result = observe()
    assert all(x["observed_minimum"] is None and x["source_depths"] == []
               and x["visible_level_absent"] is False and x["summary_is_complete"] is False
               for x in result["configured_visible_ancestor_limits"].values())
    assert result["effective_enforcement_proven"] is False


@pytest.mark.parametrize("parts", [(), ("..",), (".",), ("/tmp",), ("a/b",), ("",), ("x\x00",), ("x",)*17, ["x"]])
def test_bad_path_refuses_before_open(tree, parts, monkeypatch):
    _, _, _, fd, expected, _ = tree
    monkeypatch.setattr(c.os, "dup", lambda *_: pytest.fail("opened before path check"))
    with pytest.raises(c.ObservationRefused):
        c.observe(fd, parts, expected_root_identity=expected, deadline=101., clock=lambda: 100.)


@pytest.mark.parametrize("name", c.LIMIT_FILES)
def test_missing_required_control_never_unlimited(tree, name):
    _, parent, *_, observe = tree
    (parent / name).unlink()
    with pytest.raises(c.ObservationRefused, match="required_control_missing"):
        observe()


@pytest.mark.parametrize("kind", ["directory", "control"])
def test_symlinks_refused(tree, kind):
    root, parent, leaf, *_, observe = tree
    if kind == "directory":
        moved = root / "moved"
        parent.rename(moved)
        parent.symlink_to(moved, target_is_directory=True)
    else:
        original = leaf / "memory.max"
        saved = leaf / "saved"
        original.rename(saved)
        original.symlink_to(saved)
    with pytest.raises(c.ObservationRefused, match="filesystem_refused"):
        observe()


def test_permission_refusal_has_no_retry(tree, monkeypatch):
    *_, observe = tree
    original = c.os.open
    calls = []
    def deny(name, *a, **kw):
        if name == "pids.max":
            calls.append(name)
            raise PermissionError(errno.EACCES, "private path must not be emitted")
        return original(name, *a, **kw)
    monkeypatch.setattr(c.os, "open", deny)
    with pytest.raises(c.ObservationRefused, match="^permission_refused$"):
        observe()
    assert calls == ["pids.max"]


@pytest.mark.parametrize("name,value", [
    ("cpu.max", "0 100000\n"), ("cpu.max", "max 0\n"),
    ("cpu.max", "1  100000\n"), ("memory.max", "-1\n"),
    ("pids.max", "99999999999999999999\n"), ("memory.max", "max"),
    ("memory.swap.max", "nan\n"), ("cgroup.type", "threaded\n"),
    ("cgroup.events", "populated 1\npopulated 0\nfrozen 0\n"),
    ("cgroup.events", "populated 1\n"), ("cgroup.events", "populated 2\nfrozen 0\n"),
    ("cgroup.procs", "0\n"), ("cgroup.procs", "2147483648\n"),
    ("cgroup.procs", "1")])
def test_malformed_or_partial_control_refuses(tree, name, value):
    _, _, leaf, *_, observe = tree
    (leaf / name).write_text(value)
    with pytest.raises(c.ObservationRefused):
        observe()


@pytest.mark.parametrize("kind", ["membership", "limit", "directory"])
def test_changed_complete_snapshot_refuses(tree, monkeypatch, kind):
    _, parent, leaf, *_, observe = tree
    original = c._Read.snapshot
    calls = []
    def changed(self, *args):
        result = original(self, *args)
        calls.append(1)
        if len(calls) == 1:
            if kind == "membership": (leaf / "cgroup.procs").write_text("13\n")
            elif kind == "limit": (leaf / "pids.max").write_text("63\n")
            else:
                old = parent / "old"
                leaf.rename(old)
                import shutil
                shutil.copytree(old, leaf)
        return result
    monkeypatch.setattr(c._Read, "snapshot", changed)
    with pytest.raises(c.ObservationRefused, match="snapshot_changed"):
        observe()


def test_member_order_and_kernel_duplicates_are_not_new_members(tree):
    _, _, leaf, *_, observe = tree
    (leaf / "cgroup.procs").write_text("12\n11\n12\n")
    assert observe()["observation"]["leaf"]["cgroup.procs"]["value"] == [11, 12]


@pytest.mark.parametrize("kind", ["file", "total", "pids", "deadline", "root"])
def test_resource_and_identity_bounds(tree, monkeypatch, kind):
    _, _, leaf, fd, expected, observe = tree
    kw = {}
    if kind == "file": (leaf / "memory.max").write_bytes(b"1" * 8193)
    elif kind == "total": monkeypatch.setattr(c, "MAX_TOTAL", 5)
    elif kind == "pids": (leaf / "cgroup.procs").write_text("1\n" * 257)
    elif kind == "deadline":
        times = iter([100., 100.5, 102.])
        kw["clock"] = lambda: next(times)
    else: kw["expected_root_identity"] = (expected[0], expected[1]+1)
    with pytest.raises(c.ObservationRefused): observe(**kw)
    assert c.identity(os.fstat(fd)) == expected


@pytest.mark.parametrize("failure", [False, True])
def test_helper_descriptors_closed_caller_preserved(tree, monkeypatch, failure):
    _, _, leaf, fd, expected, observe = tree
    if failure: (leaf / "pids.max").write_text("broken")
    opened = []; active = set()
    real_open, real_dup, real_close = c.os.open, c.os.dup, c.os.close
    def track_open(*a, **k):
        n = real_open(*a, **k); opened.append(n); active.add(n); return n
    def track_dup(*a, **k):
        n = real_dup(*a, **k); opened.append(n); active.add(n); return n
    def track_close(n):
        assert n != fd  # The caller's descriptor is never owned by the helper.
        real_close(n)
        active.remove(n) # Only a successful close settles this acquisition.
    with monkeypatch.context() as ctx:
        ctx.setattr(c.os, "open", track_open); ctx.setattr(c.os, "dup", track_dup)
        ctx.setattr(c.os, "close", track_close)
        if failure:
            try: observe()
            except c.ObservationRefused: pass
            else: pytest.fail("expected refusal")
        else: observe()
    assert opened and not active
    assert c.identity(os.fstat(fd)) == expected


@pytest.mark.parametrize("deadline", [True, float("nan"), float("inf"), 100., 103.])
def test_invalid_deadline_window_refuses(tree, deadline):
    *_, observe = tree
    with pytest.raises(c.ObservationRefused): observe(deadline=deadline)


def test_fifo_control_refuses_without_blocking(tree):
    _, _, leaf, *_, observe = tree
    path = leaf / "pids.max"
    path.unlink()
    os.mkfifo(path)
    with pytest.raises(c.ObservationRefused, match="control_type"):
        observe()


def test_changed_device_refuses_and_closes(tree, monkeypatch):
    _, _, _, fd, expected, observe = tree
    original = c.os.fstat
    def different_device(n):
        info = original(n)
        if n == fd: return info
        class Changed:
            st_mode = info.st_mode
            st_ino = info.st_ino
            st_dev = info.st_dev + 1
        return Changed()
    # Keep the fault local to the observer; patching the shared os module also
    # replaces pytest capture's fstat, which requires the full stat result.
    class ObserverOS:
        fstat = staticmethod(different_device)

        def __getattr__(self, name):
            return getattr(os, name)

    monkeypatch.setattr(c, "os", ObserverOS())
    with pytest.raises(c.ObservationRefused, match="root_identity"):
        observe()
    assert os.fstat is original
    assert c.identity(original(fd)) == expected
