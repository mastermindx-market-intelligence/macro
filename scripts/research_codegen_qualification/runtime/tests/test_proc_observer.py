"""Hermetic syscall fixtures; one separately marked, owned Linux process check."""
from dataclasses import asdict, FrozenInstanceError
import errno
import hashlib
import json
import os
import stat
import sys
from types import SimpleNamespace
import pytest
import proc_observer as m

PID = 1234


def stat_record(pid=PID, start=123456, state=b"S", comm=b"owned ) (test\n name"):
    # Fields 3..52; sentinels around field22 catch an off-by-one decoder.
    fields = [state] + [b"0"] * 49
    fields[18:21] = [b"654", str(start).encode(), b"987"]
    return str(pid).encode() + b" (" + comm + b") " + b" ".join(fields) + b"\n"


class KernelFixture:
    O_RDONLY = os.O_RDONLY
    O_DIRECTORY = os.O_DIRECTORY
    O_NOFOLLOW = os.O_NOFOLLOW
    O_CLOEXEC = os.O_CLOEXEC
    O_NONBLOCK = os.O_NONBLOCK

    def __init__(self):
        self.calls = []
        self.opened = []
        self.closed = []
        self.content = {}
        self.stat_records = [stat_record(), stat_record(state=b"R")]
        self.cgroup = b"0::/owned/private-fixture\n"
        self.polls = [[], []]
        self.fail = None
        self.close_fail = None
        self.extra_byte = False
        self.regular = True

    def _call(self, label):
        self.calls.append(label)
        if label == self.fail:
            raise PermissionError(errno.EACCES, "private details must be redacted")

    def _allocate(self, raw=None):
        fd = 10 + len(self.opened)
        self.opened.append(fd)
        self.content[fd] = [raw, b"x" if self.extra_byte else b""]
        return fd

    def pidfd_open(self, pid, flags):
        self._call("pidfd")
        assert (pid, flags) == (PID, 0)
        return self._allocate()

    def open(self, name, flags, *, dir_fd=None):
        self._call("open:" + name)
        if dir_fd is None:
            assert name == "/proc/1234"
            assert flags == self.O_RDONLY | self.O_DIRECTORY | self.O_NOFOLLOW | self.O_CLOEXEC
            return self._allocate()
        assert dir_fd == 11
        assert flags == self.O_RDONLY | self.O_NOFOLLOW | self.O_CLOEXEC | self.O_NONBLOCK
        assert name in ("stat", "cgroup")
        return self._allocate(self.stat_records.pop(0) if name == "stat" else self.cgroup)

    def fstat(self, fd):
        self._call("fstat:" + str(fd))
        return SimpleNamespace(st_mode=stat.S_IFREG if self.regular else stat.S_IFIFO)

    def read(self, fd, size):
        self._call("read:" + str(fd))
        assert size in (4097, 1)
        return self.content[fd].pop(0)

    def close(self, fd):
        self.closed.append(fd)
        if fd == self.close_fail:
            raise OSError(errno.EIO, "injected close failure")

    def poll(self):
        kernel = self

        class Poll:
            def register(self, fd, flags):
                kernel._call("register")
                assert fd == 10 and flags == 25

            def poll(self, timeout):
                kernel._call("poll")
                assert timeout == 0
                return kernel.polls.pop(0)
        return Poll()


@pytest.fixture
def kernel(monkeypatch):
    k = KernelFixture()
    monkeypatch.setattr(m, "os", k)
    monkeypatch.setattr(m, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(m, "select", SimpleNamespace(poll=k.poll, POLLIN=1, POLLHUP=16, POLLERR=8))
    yield k
    assert k.closed == list(reversed(k.opened))
    assert len(k.closed) == len(set(k.closed))


def test_held_pidfd_and_directory_bracket_reads_and_redact_output(kernel):
    result = m.observe_pid(PID)
    assert result.start_ticks == 123456 and result.state == "R"
    assert result.stat_before_sha256 == hashlib.sha256(stat_record()).hexdigest()
    assert result.cgroup_path_sha256 == hashlib.sha256(b"/owned/private-fixture").hexdigest()
    assert kernel.calls.count("poll") == 2
    assert kernel.calls.index("poll") < kernel.calls.index("open:stat")
    assert kernel.calls[-1] == "poll"
    public = asdict(result)
    assert all(public[key] is False for key in
               ("container_identity_verified", "helper_census_complete", "limits_verified", "cleanup_proven"))
    assert "private-fixture" not in json.dumps(public) and "owned" not in repr(result)
    with pytest.raises(FrozenInstanceError):
        result.pid = 2


@pytest.mark.parametrize("pid", [True, False, 0, -1, 2**31, "1234", None, 12.0])
def test_bad_pid_refuses_before_io(kernel, pid):
    with pytest.raises(m.ObservationRefused, match="pid_shape"):
        m.observe_pid(pid)
    assert not kernel.calls


@pytest.mark.parametrize("stage", ["pidfd", "open:/proc/1234", "register", "poll",
                                      "open:stat", "fstat:12", "read:12", "open:cgroup",
                                      "fstat:13", "read:13", "fstat:14", "read:14"])
def test_permission_failure_once_and_every_acquired_fd_closed(kernel, stage):
    kernel.fail = stage
    with pytest.raises(m.ObservationRefused, match="^permission_refused$"):
        m.observe_pid(PID)
    assert kernel.calls.count(stage) == 1


@pytest.mark.parametrize("events", [[[(10, 1)]], [[], [(10, 16)]], [[], [(10, 32)]]])
def test_pidfd_exit_error_or_invalidity_refuses(kernel, events):
    kernel.polls = events
    with pytest.raises(m.ObservationRefused, match="pidfd_not_live"):
        m.observe_pid(PID)


def test_changed_starttime_refuses_without_unique_pid_claim(kernel):
    kernel.stat_records[1] = stat_record(start=123457)
    with pytest.raises(m.ObservationRefused, match="process_identity_changed"):
        m.observe_pid(PID)


@pytest.mark.parametrize("record", [b"", b"x" * 4097, stat_record(pid=4321),
                                       stat_record(state=b"Z"), stat_record(state=b"X"),
                                       stat_record(start=-1), stat_record(start=2**64),
                                       b"1234 (bad) S 1\n",
                                       stat_record().replace(b" 654 ", b" NaN ")])
def test_bad_stat_never_returns_observation(kernel, record):
    kernel.stat_records[0] = record
    with pytest.raises(m.ObservationRefused):
        m.observe_pid(PID)


@pytest.mark.parametrize("record", [b"", b"x" * 4097, b"0::/x\n0::/y\n", b"1:cpu:/x\n",
                                       b"1:cpu:/x\n0::/x\n", b"0::/../x\n", b"0::/x/./y\n",
                                       b"0::/x//y\n", b"0::/x/\n", b"0::/x (deleted)\n",
                                       b"0::/x\x00y\n", b"0::/x\r\n", b"0::relative\n"])
def test_bad_or_unsupported_cgroup_refuses_without_path_access(kernel, record):
    kernel.cgroup = record
    with pytest.raises(m.ObservationRefused):
        m.observe_pid(PID)
    assert all(not call.startswith("open:/x") for call in kernel.calls)


def test_root_membership_is_not_custody_or_limit_proof(kernel):
    kernel.cgroup = b"0::/\n"
    result = m.observe_pid(PID)
    assert result.cgroup_is_root and not result.limits_verified


def test_partial_record_refuses(kernel):
    kernel.extra_byte = True
    with pytest.raises(m.ObservationRefused, match="proc_record_not_complete"):
        m.observe_pid(PID)


def test_nonregular_record_refuses_without_read(kernel):
    kernel.regular = False
    with pytest.raises(m.ObservationRefused, match="proc_record_not_regular"):
        m.observe_pid(PID)
    assert not any(call.startswith("read:") for call in kernel.calls)


def test_cleanup_failure_closes_other_fds_once_and_refuses(kernel):
    kernel.close_fail = 13
    with pytest.raises(m.ObservationRefused, match="descriptor_cleanup_unproven"):
        m.observe_pid(PID)


def test_unsupported_platform_has_no_io(kernel, monkeypatch):
    monkeypatch.setattr(m, "sys", SimpleNamespace(platform="darwin"))
    with pytest.raises(m.ObservationRefused, match="pidfd_platform_unsupported"):
        m.observe_pid(PID)
    assert not kernel.calls


@pytest.mark.skipif(os.environ.get("RF_QUALIFICATION_OWNED_PIDFD_SMOKE") != "1"
                    or sys.platform != "linux" or not hasattr(os, "pidfd_open"),
                    reason="explicit owned Linux pidfd qualification only")
def test_live_one_owned_process_only():
    import subprocess
    child = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(5)"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    try:
        result = m.observe_pid(child.pid)
        assert result.pid == child.pid and not result.container_identity_verified
    finally:
        child.terminate()
        child.wait(timeout=3)
