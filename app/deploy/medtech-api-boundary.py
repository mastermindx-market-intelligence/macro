#!/usr/bin/env python3
"""Refuse a refresh unless the running API has the reviewed MedTech boundary.

Fixed root-only ExecStartPre, with no marker, admission database, repair or
activation. Inspect the host from outside the worker's own mount namespace.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import os
from pathlib import Path
import pwd
import re
import stat
import subprocess
import sys

API_UNIT = "macro-api.service"
SOURCE_UNIT = Path("/opt/macro/app/deploy/macro-api.service")
INSTALLED_UNIT = Path("/etc/systemd/system/macro-api.service")
ENVIRONMENT_FILE = Path("/etc/macro-medtech.env")
PRIVATE_ROOT = Path("/srv/medtech/private")
PUBLIC_ROOT = Path("/srv/medtech/public")
OPEN_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
REQUIRED_LINES = (
    "ExecStartPre=+/usr/bin/python3 -I /opt/macro/app/deploy/medtech-prereqs.py",
    "Environment=MEDTECH_PUBLIC_ROOT=/srv/medtech/public",
    "ReadOnlyPaths=/srv/medtech/public",
    "InaccessiblePaths=/srv/medtech/private",
)
PROPERTIES = (
    "LoadState", "ActiveState", "SubState", "MainPID", "FragmentPath", "DropInPaths",
    "NeedDaemonReload", "Transient", "InvocationID",
)


class BoundaryError(RuntimeError):
    pass


def _root_parent(path: Path) -> int:
    if not path.is_absolute() or ".." in path.parts:
        raise BoundaryError("unsafe fixed path")
    descriptor = os.open("/", OPEN_DIRECTORY)
    try:
        for part in (None, *path.parts[1:]):
            if part is not None:
                child = os.open(part, OPEN_DIRECTORY, dir_fd=descriptor)
                os.close(descriptor)
                descriptor = child
            value = os.fstat(descriptor)
            if (value.st_uid, value.st_gid) != (0, 0) or stat.S_IMODE(value.st_mode) & 0o022:
                raise BoundaryError("unsafe fixed path owner/mode")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _read_safe_file(path: Path, *, mode: int | None = None, limit: int = 131072) -> bytes:
    parent = _root_parent(path.parent)
    descriptor = None
    try:
        descriptor = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        value = os.fstat(descriptor)
        permissions = stat.S_IMODE(value.st_mode)
        if (not stat.S_ISREG(value.st_mode) or (value.st_uid, value.st_gid) != (0, 0)
                or permissions & 0o022 or (mode is not None and permissions != mode)
                or value.st_size > limit):
            raise BoundaryError("unsafe fixed file")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            content = handle.read(limit + 1)
        if len(content) > limit:
            raise BoundaryError("oversized fixed file")
        current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        if (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_size) != (
                value.st_dev, value.st_ino, value.st_mtime_ns, value.st_size):
            raise BoundaryError("fixed file changed during read")
        return content
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _validate_environment(content: bytes) -> None:
    lines = [line.strip() for line in content.decode("ascii").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    if len(lines) != 1 or not re.fullmatch(r"MEDTECH_START_ON=\d{4}-\d{2}-\d{2}", lines[0]):
        raise BoundaryError("environment may contain only MEDTECH_START_ON")
    start = date.fromisoformat(lines[0].partition("=")[2])
    if start > datetime.now(timezone.utc).date():
        raise BoundaryError("coverage start is in the future")


def _unit_state() -> dict[str, str]:
    result = subprocess.run(
        ["/usr/bin/systemctl", "show", "--no-pager", API_UNIT,
         "--property=" + ",".join(PROPERTIES)],
        capture_output=True, text=True, check=True, timeout=10,
        env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
    )
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition("=")
        if not separator or key in values or key not in PROPERTIES:
            raise BoundaryError("ambiguous API unit state")
        values[key] = value
    return values


def _validate_unit_state(values: dict[str, str]) -> int:
    required = {
        "LoadState": "loaded", "ActiveState": "active", "SubState": "running",
        "FragmentPath": str(INSTALLED_UNIT), "DropInPaths": "",
        "NeedDaemonReload": "no", "Transient": "no",
    }
    if any(values.get(key) != value for key, value in required.items()):
        raise BoundaryError("API unit is not the active reviewed fragment")
    if not re.fullmatch(r"[1-9][0-9]*", values.get("MainPID", "")):
        raise BoundaryError("API has no stable main process")
    if not re.fullmatch(r"[a-f0-9]{32}", values.get("InvocationID", "")):
        raise BoundaryError("API invocation identity missing")
    return int(values["MainPID"])


def _process_stamp(pid: int) -> tuple[str, int, int]:
    # /proc/<pid>/stat permits spaces and ')' in comm; split at its final ')'.
    fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
    started = fields[19]
    namespace = os.stat(f"/proc/{pid}/ns/mnt")
    if (namespace.st_dev, namespace.st_ino) == _identity(os.stat("/proc/self/ns/mnt")):
        raise BoundaryError("API has no separate mount namespace")
    return started, namespace.st_dev, namespace.st_ino


def _check_api_environment(pid: int) -> None:
    # EnvironmentFile may override Environment in the fragment. Inspect only
    # the fixed key, bounded in memory; never emit any environment values.
    limit = 1048576
    with Path(f"/proc/{pid}/environ").open("rb") as handle:
        content = handle.read(limit + 1)
    if len(content) > limit:
        raise BoundaryError("API environment exceeds inspection bound")
    roots = [entry for entry in content.split(b"\0") if entry.startswith(b"MEDTECH_PUBLIC_ROOT=")]
    if roots != [b"MEDTECH_PUBLIC_ROOT=/srv/medtech/public"]:
        raise BoundaryError("API publication environment differs from the fenced root")


def _identity(value: os.stat_result) -> tuple[int, int]:
    return value.st_dev, value.st_ino


def _host_directory(path: Path) -> os.stat_result:
    parent = _root_parent(path.parent)
    descriptor = None
    try:
        descriptor = os.open(path.name, OPEN_DIRECTORY, dir_fd=parent)
        value = os.fstat(descriptor)
        account = pwd.getpwnam("macro-medtech")
        if (account.pw_uid <= 0 or account.pw_gid <= 0
                or (value.st_uid, value.st_gid) != (account.pw_uid, account.pw_gid)
                or stat.S_IMODE(value.st_mode) != 0o700):
            raise BoundaryError("MedTech root has an unsafe identity/mode")
        return value
    finally:
        if descriptor is not None:
            os.close(descriptor)
        os.close(parent)


def _mounts(content: str) -> dict[str, set[str]]:
    mounts: dict[str, set[str]] = {}
    for line in content.splitlines():
        fields = line.split(" - ", 1)[0].split()
        if len(fields) < 6:
            raise BoundaryError("invalid API mount table")
        path = re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4])
        # Scope ambiguity to this boundary; unrelated systemd mount stacks are
        # owned by their existing services and are not evidence of a MedTech leak.
        relevant = any(path == str(root) or path.startswith(str(root) + "/")
                       for root in (PUBLIC_ROOT, PRIVATE_ROOT))
        if relevant and path in mounts:
            raise BoundaryError("stacked API mountpoint")
        mounts[path] = set(fields[5].split(","))
    return mounts


def _validate_namespace(mountinfo: str, host_public: os.stat_result,
                        host_private: os.stat_result, api_public: os.stat_result,
                        api_private: os.stat_result) -> None:
    mounts = _mounts(mountinfo)
    public, private = str(PUBLIC_ROOT), str(PRIVATE_ROOT)
    if public not in mounts or "ro" not in mounts[public] or "rw" in mounts[public]:
        raise BoundaryError("API publication mount is missing or writable")
    if private not in mounts:
        raise BoundaryError("API private deny mount is missing")
    for path, options in mounts.items():
        if path.startswith(public + "/") and ("ro" not in options or "rw" in options):
            raise BoundaryError("API publication has a writable submount")
        if path.startswith(private + "/"):
            raise BoundaryError("API private deny mount has a nested exposure")
    if not stat.S_ISDIR(api_public.st_mode) or _identity(host_public) != _identity(api_public):
        raise BoundaryError("API publication inode differs from the host root")
    if (not stat.S_ISDIR(api_private.st_mode) or _identity(host_private) == _identity(api_private)
            or stat.S_IMODE(api_private.st_mode) != 0):
        raise BoundaryError("API can reach the retained private root")


def attest() -> None:
    source = _read_safe_file(SOURCE_UNIT)
    installed = _read_safe_file(INSTALLED_UNIT)
    if source != installed or any(source.decode("utf-8").splitlines().count(line) != 1
                                  for line in REQUIRED_LINES):
        raise BoundaryError("API fragment differs from reviewed source")
    environment = _read_safe_file(ENVIRONMENT_FILE, mode=0o600, limit=4096)
    _validate_environment(environment)
    before = _unit_state()
    pid = _validate_unit_state(before)
    stamp = _process_stamp(pid)
    _check_api_environment(pid)
    host_public, host_private = _host_directory(PUBLIC_ROOT), _host_directory(PRIVATE_ROOT)
    mountinfo = Path(f"/proc/{pid}/mountinfo").read_text()
    api_public = os.stat(f"/proc/{pid}/root{PUBLIC_ROOT}", follow_symlinks=False)
    api_private = os.stat(f"/proc/{pid}/root{PRIVATE_ROOT}", follow_symlinks=False)
    _validate_namespace(mountinfo, host_public, host_private, api_public, api_private)
    after = _unit_state()
    _validate_unit_state(after)
    if (after != before or stamp != _process_stamp(pid)
            or _identity(host_public) != _identity(_host_directory(PUBLIC_ROOT))
            or _identity(host_private) != _identity(_host_directory(PRIVATE_ROOT))
            or source != _read_safe_file(SOURCE_UNIT)
            or installed != _read_safe_file(INSTALLED_UNIT)
            or environment != _read_safe_file(ENVIRONMENT_FILE, mode=0o600, limit=4096)):
        raise BoundaryError("API process, reviewed inputs or roots changed during proof")


def main() -> int:
    if len(sys.argv) != 1 or os.geteuid() != 0:
        print("medtech-api-boundary: root and fixed paths required", file=sys.stderr)
        return 1
    try:
        attest()
    except (BoundaryError, OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
        # No source records, environment values or subprocess stderr in logs.
        reason = str(exc) if isinstance(exc, BoundaryError) else "boundary inspection failed"
        print("medtech-api-boundary: refused: " + reason, file=sys.stderr)
        return 1
    print("medtech-api-boundary: active API private/public namespace verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
