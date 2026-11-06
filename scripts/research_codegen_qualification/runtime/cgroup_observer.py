"""Read one caller-authorized cgroup-v2 hierarchy; never grant host trust.

The caller binds the real host cgroupfs root/namespace and container association,
plus an outer deadline supervisor. Local time checks cannot interrupt blocked
kernel I/O. Two equal snapshots are observations, not atomicity or ABA protection.
No scanning, writes, signals, cleanup, admission or enforcement proof occurs here.
"""
import errno
import math
import os
import re
import stat
import time
from fractions import Fraction

MAX_DEPTH = 16
MAX_FILE = 8192
MAX_TOTAL = 131072
MAX_MEMBERS = 256
MAX_SECONDS = 2.0
LIMIT_FILES = ("cpu.max", "memory.max", "memory.swap.max", "pids.max")
_COMPONENT = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_UINT = re.compile(rb"(?:0|[1-9][0-9]{0,18})\Z")


class ObservationRefused(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ObservationRefused(reason)


def identity(info):
    return (info.st_dev, info.st_ino)


def integer(raw, positive=False):
    require(_UINT.fullmatch(raw) is not None, "integer_syntax")
    value = int(raw)
    require(value <= 2**63 - 1 and (not positive or value > 0), "integer_range")
    return value


def parse_limit(name, raw):
    require(raw.endswith(b"\n") and raw.count(b"\n") == 1, "limit_line")
    body = raw[:-1]
    if name == "cpu.max":
        parts = body.split(b" ")
        require(len(parts) == 2, "cpu_syntax")
        quota = None if parts[0] == b"max" else integer(parts[0], positive=True)
        return {"quota": quota, "period": integer(parts[1], positive=True)}
    return None if body == b"max" else integer(body)


def parse_events(raw):
    require(raw.endswith(b"\n"), "events_line")
    out = {}
    for line in raw[:-1].split(b"\n"):
        parts = line.split(b" ")
        require(len(parts) == 2 and parts[0] in (b"populated", b"frozen"), "events_key")
        key = parts[0].decode("ascii")
        require(key not in out and parts[1] in (b"0", b"1"), "events_value")
        out[key] = int(parts[1])
    require(set(out) == {"populated", "frozen"}, "events_incomplete")
    return out


def parse_members(raw):
    if not raw:
        return []
    require(raw.endswith(b"\n"), "members_line")
    rows = raw[:-1].split(b"\n")
    require(len(rows) <= MAX_MEMBERS, "members_bound")
    members = [integer(row, positive=True) for row in rows]
    require(all(pid <= 2**31 - 1 for pid in members), "pid_range")
    # The kernel may repeat a PID while a task migrates. Retain only the bounded
    # set, and still require the second complete observation to match.
    return sorted(set(members))


class _Read:
    def __init__(self, root, deadline, clock):
        self.root = root
        self.deadline = deadline
        self.clock = clock
        self.used = 0

    def time_check(self):
        now = self.clock()
        require(type(now) in (int, float) and math.isfinite(now)
                and now < self.deadline, "deadline")

    def file(self, directory, name, optional_root=False):
        self.time_check()
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                         | os.O_NONBLOCK, dir_fd=directory)
        except FileNotFoundError:
            if not optional_root:
                raise ObservationRefused("required_control_missing") from None
            return {"state": "ABSENT_UNKNOWN", "identity": None, "value": None}
        try:
            before = os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_dev == self.root[0], "control_type")
            chunks = []
            size = 0
            while True:
                self.time_check()
                data = os.read(fd, min(1024, MAX_FILE - size + 1))
                self.time_check()
                self.used += len(data)
                size += len(data)
                require(size <= MAX_FILE and self.used <= MAX_TOTAL, "read_bound")
                if not data:
                    break
                chunks.append(data)
            after = os.fstat(fd)
            # Advisory metadata consistency only: kernfs metadata is not a data
            # version, and two matching reads cannot exclude changes or ABA.
            require(identity(before) == identity(after)
                    and before.st_mtime_ns == after.st_mtime_ns
                    and before.st_size == after.st_size, "control_changed")
            raw = b"".join(chunks)
            if name in LIMIT_FILES:
                value = parse_limit(name, raw)
            elif name == "cgroup.type":
                require(raw == b"domain\n", "unsupported_cgroup_type")
                value = "domain"
            elif name == "cgroup.events":
                value = parse_events(raw)
            else:
                value = parse_members(raw)
            return {"state": "OBSERVED", "identity": identity(before), "value": value}
        finally:
            os.close(fd)

    def snapshot(self, root_fd, parts):
        self.time_check()
        fds = [os.dup(root_fd)]
        try:
            root_info = os.fstat(fds[0])
            require(stat.S_ISDIR(root_info.st_mode) and identity(root_info) == self.root,
                    "root_identity")
            for part in parts:
                self.time_check()
                fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                             | os.O_CLOEXEC, dir_fd=fds[-1])
                fds.append(fd)
                meta = os.fstat(fd)
                require(meta.st_dev == self.root[0], "directory_device")
            levels = []
            for depth, fd in enumerate(fds):
                levels.append({"depth": depth, "identity": identity(os.fstat(fd)),
                               "limits": {name: self.file(fd, name, optional_root=depth == 0)
                                          for name in LIMIT_FILES}})
            leaf = {name: self.file(fds[-1], name) for name in
                    ("cgroup.type", "cgroup.events", "cgroup.procs")}
            self.time_check()
            return {"levels": levels, "leaf": leaf}
        finally:
            for fd in reversed(fds):
                os.close(fd)


def observe(root_fd, parts, *, expected_root_identity, deadline, clock=time.monotonic):
    """Observe only a non-root child under an already trusted, held root fd.

    Missing controls at the passed root are UNKNOWN; a limited namespace/mount
    can hide ancestors, so these minima never assert complete effective limits.
    A permission or other read failure refuses the entire observation.
    """
    require(type(root_fd) is int and root_fd >= 0, "root_fd")
    require(type(parts) is tuple and 0 < len(parts) <= MAX_DEPTH, "path_depth")
    require(all(type(p) is str and p not in (".", "..")
                and _COMPONENT.fullmatch(p) is not None for p in parts), "path_component")
    require(type(expected_root_identity) is tuple and len(expected_root_identity) == 2
            and all(type(v) is int and v >= 0 for v in expected_root_identity), "root_binding")
    require(type(deadline) in (int, float) and math.isfinite(deadline), "deadline")
    started = clock()
    require(type(started) in (int, float) and math.isfinite(started)
            and 0 < deadline - started <= MAX_SECONDS, "deadline_window")
    reader = _Read(expected_root_identity, deadline, clock)
    try:
        first = reader.snapshot(root_fd, parts)
        second = reader.snapshot(root_fd, parts)
    except PermissionError:
        raise ObservationRefused("permission_refused") from None
    except OSError as exc:
        raise ObservationRefused("filesystem_refused_" + errno.errorcode.get(exc.errno, "UNKNOWN")) from None
    require(first == second, "snapshot_changed")
    summaries = {}
    for name in LIMIT_FILES:
        entries = [level["limits"][name] for level in first["levels"]]
        known = [(depth, row["value"]) for depth, row in enumerate(entries)
                 if row["state"] == "OBSERVED"]
        if name == "cpu.max":
            finite = [(depth, Fraction(value["quota"], value["period"]))
                      for depth, value in known if value["quota"] is not None]
            unit = "cpu_seconds_per_second"
        else:
            finite = [(depth, value) for depth, value in known if value is not None]
            unit = "tasks" if name == "pids.max" else "bytes"
        value = min(v for _, v in finite) if finite else None
        minimum = ({"numerator": value.numerator, "denominator": value.denominator}
                   if name == "cpu.max" and value is not None else value)
        summaries[name] = {
            "observed_minimum": minimum, "unit": unit,
            "source_depths": [depth for depth, v in finite if v == value],
            "visible_level_absent": any(x["state"] != "OBSERVED" for x in entries),
            "summary_is_complete": False,
        }
    reader.time_check()
    return {"schema": "rf.cgroup_v2_observation.v2", "observation": first,
            "configured_visible_ancestor_limits": summaries, "raw_bytes_read": reader.used,
            "ancestors_above_root_observed": False, "mid_read_stability_proven": False,
            "host_trust_proven": False, "container_association_proven": False,
            "effective_enforcement_proven": False, "complete_helper_census": False,
            "cleanup_proven": False, "candidate_admission": False, "containment_qualified": False}
