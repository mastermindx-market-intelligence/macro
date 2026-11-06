"""Bounded, read-only observation of one Linux PID through held descriptors.

The caller must establish a trusted host/procfs and authorize this exact PID.
This does not correlate an earlier runtime declaration with this process, find
all helpers, inspect resource enforcement, or prove cleanup. It is excluded from
the commissioned canary capsule. No I/O occurs on import.
"""
from dataclasses import dataclass
import errno
import hashlib
import os
import re
import select
import stat
import sys

MAX_RECORD_BYTES = 4096


class ObservationRefused(ValueError):
    pass


def _require(ok, reason):
    if not ok:
        raise ObservationRefused(reason)


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _stat_identity(raw, expected_pid):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_RECORD_BYTES,
             "stat_bound")
    body = raw[:-1] if raw.endswith(b"\n") else raw
    head, opening, rest = body.partition(b" (")
    comm, closing, suffix = rest.rpartition(b") ")
    _require(opening and closing and head == str(expected_pid).encode("ascii")
             and len(comm) <= 256, "stat_identity")
    # Field 2 is opaque: comm can contain spaces, parentheses and newlines.
    # The remaining fields contain no parentheses; field 22 is index 19 here.
    fields = suffix.split(b" ")
    _require(50 <= len(fields) <= 64 and fields[0] in
             (b"R", b"S", b"D", b"T", b"t", b"K", b"W", b"P", b"I"),
             "stat_shape_or_dead")
    _require(all(re.fullmatch(rb"-?[0-9]{1,20}", x) for x in fields[1:]),
             "stat_numeric_fields")
    start = fields[19]
    _require(re.fullmatch(rb"[0-9]{1,20}", start), "stat_starttime")
    ticks = int(start)
    _require(ticks < 2**64, "stat_starttime")
    return ticks, fields[0].decode("ascii")


def _cgroup_identity(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= MAX_RECORD_BYTES,
             "cgroup_bound")
    body = raw[:-1] if raw.endswith(b"\n") else raw
    # Narrow unified-hierarchy profile; do not resolve a namespace-relative path.
    _require(body.startswith(b"0::/") and all(32 <= c < 127 for c in body),
             "cgroup_unified_record")
    path = body[3:]
    _require(not path.endswith(b" (deleted)"), "cgroup_deleted")
    _require(path == b"/" or all(part not in (b"", b".", b"..")
                                  for part in path[1:].split(b"/")),
             "cgroup_path_shape")
    return _digest(path), path == b"/"


@dataclass(frozen=True)
class ProcessObservation:
    pid: int
    start_ticks: int
    state: str
    cgroup_path_sha256: str
    cgroup_is_root: bool
    stat_before_sha256: str
    stat_after_sha256: str
    cgroup_sha256: str
    container_identity_verified: bool = False
    helper_census_complete: bool = False
    limits_verified: bool = False
    cleanup_proven: bool = False


def observe_pid(pid):
    """Capture one bounded observation, or refuse without retrying any effect.

    The held pidfd brackets all reads with nonblocking liveness checks. The held
    proc directory prevents child-file lookups from following a reused PID path.
    Equal start ticks alone are not unique identity, and PID reuse before this
    acquisition is not ruled out. No path, executable or raw command is returned.
    This function supplies no wall-time guarantee for a blocked kernel syscall;
    a later qualified caller still owes a trusted outer supervisor/deadline.
    """
    _require(type(pid) is int and 0 < pid < 2**31, "pid_shape")
    _require(sys.platform == "linux" and hasattr(os, "pidfd_open")
             and hasattr(select, "poll"), "pidfd_platform_unsupported")
    fds = []
    try:
        pidfd = os.pidfd_open(pid, 0)
        fds.append(pidfd)
        directory = os.open(f"/proc/{pid}", os.O_RDONLY | os.O_DIRECTORY
                            | os.O_NOFOLLOW | os.O_CLOEXEC)
        fds.append(directory)
        poller = select.poll()
        poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)

        def live():
            _require(not poller.poll(0), "pidfd_not_live")

        def read(name):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                         | os.O_NONBLOCK, dir_fd=directory)
            fds.append(fd)
            _require(stat.S_ISREG(os.fstat(fd).st_mode), "proc_record_not_regular")
            raw = os.read(fd, MAX_RECORD_BYTES + 1)
            _require(0 < len(raw) <= MAX_RECORD_BYTES, "proc_record_bound")
            _require(os.read(fd, 1) == b"", "proc_record_not_complete")
            return raw

        live()
        before = read("stat")
        ticks, _ = _stat_identity(before, pid)
        cgroup = read("cgroup")
        path_digest, is_root = _cgroup_identity(cgroup)
        after = read("stat")
        later_ticks, state = _stat_identity(after, pid)
        live()
        _require(ticks == later_ticks, "process_identity_changed")
        return ProcessObservation(pid, ticks, state, path_digest, is_root,
                                  _digest(before), _digest(after), _digest(cgroup))
    except OSError as exc:
        reason = ("permission_refused" if exc.errno in (errno.EACCES, errno.EPERM)
                  else "kernel_observation_failed")
        raise ObservationRefused(reason) from None
    finally:
        failed = False
        for fd in reversed(fds):
            try:
                os.close(fd)
            except OSError:
                # A close error is not permission to retry a possibly reused FD.
                failed = True
        if failed:
            raise ObservationRefused("descriptor_cleanup_unproven")
