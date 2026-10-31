#!/usr/bin/env python3
"""Provision only the fixed MedTech identity and empty namespace anchors.

Called before canonical macro-api unit validation/restart. This never installs,
enables, or starts a refresh, writes source configuration, or repairs ownership.
"""
from __future__ import annotations

import grp
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys

ACCOUNT = "macro-medtech"
PARENT = Path("/srv")
ROOT_NAME = "medtech"
OPEN_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class PrerequisiteError(RuntimeError):
    pass


def _validate_directory(fd: int, uid: int, gid: int, mode: int | None = None) -> None:
    value = os.fstat(fd)
    if not stat.S_ISDIR(value.st_mode) or (value.st_uid, value.st_gid) != (uid, gid):
        raise PrerequisiteError("unsafe directory identity")
    permissions = stat.S_IMODE(value.st_mode)
    if (mode is not None and permissions != mode) or (mode is None and permissions & 0o022):
        raise PrerequisiteError("unsafe directory permissions")


def _open_parent(path: Path, uid: int = 0, gid: int = 0) -> int:
    if not path.is_absolute() or ".." in path.parts:
        raise PrerequisiteError("unsafe parent path")
    descriptor = os.open("/", OPEN_DIRECTORY)
    try:
        _validate_directory(descriptor, uid, gid)
        for part in path.parts[1:]:
            child = os.open(part, OPEN_DIRECTORY, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            _validate_directory(descriptor, uid, gid)
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _existing(parent: int, name: str) -> int | None:
    try:
        return os.open(name, OPEN_DIRECTORY, dir_fd=parent)
    except FileNotFoundError:
        return None


def _same_entry(parent: int, name: str, descriptor: int) -> None:
    entry = os.stat(name, dir_fd=parent, follow_symlinks=False)
    opened = os.fstat(descriptor)
    if (entry.st_dev, entry.st_ino) != (opened.st_dev, opened.st_ino):
        raise PrerequisiteError("directory changed during provisioning")


def _provision_at(parent: int, uid: int, gid: int, *, anchor_uid: int = 0,
                  anchor_gid: int = 0) -> None:
    """Descriptor-relative core; explicit identities support isolated fixtures."""
    _validate_directory(parent, anchor_uid, anchor_gid)
    held: dict[str, int] = {}
    root = _existing(parent, ROOT_NAME)
    try:
        # Validate every pre-existing node before creating any missing sibling.
        if root is not None:
            _validate_directory(root, anchor_uid, anchor_gid, 0o711)
            for name in ("private", "public"):
                child = _existing(root, name)
                if child is not None:
                    held[name] = child
                    _validate_directory(child, uid, gid, 0o700)
        else:
            os.mkdir(ROOT_NAME, 0o711, dir_fd=parent)
            root = os.open(ROOT_NAME, OPEN_DIRECTORY, dir_fd=parent)
            # Only a newly created directory may be assigned its expected mode.
            os.fchmod(root, 0o711)
            _validate_directory(root, anchor_uid, anchor_gid, 0o711)
        for name in ("private", "public"):
            if name not in held:
                os.mkdir(name, 0o700, dir_fd=root)
                child = os.open(name, OPEN_DIRECTORY, dir_fd=root)
                held[name] = child
                os.fchown(child, uid, gid)
                _validate_directory(child, uid, gid, 0o700)
        _same_entry(parent, ROOT_NAME, root)
        for name, child in held.items():
            _same_entry(root, name, child)
    finally:
        for child in held.values():
            os.close(child)
        if root is not None:
            os.close(root)


def _identity() -> tuple[int, int] | None:
    try:
        account = pwd.getpwnam(ACCOUNT)
    except KeyError:
        account = None
    try:
        group = grp.getgrnam(ACCOUNT)
    except KeyError:
        group = None
    if account is None and group is None:
        return None
    if account is None or group is None:
        raise PrerequisiteError("conflicting service identity")
    if (account.pw_uid <= 0 or group.gr_gid <= 0 or account.pw_gid != group.gr_gid
            or account.pw_dir != "/nonexistent" or account.pw_shell != "/usr/sbin/nologin"
            or set(os.getgrouplist(ACCOUNT, group.gr_gid)) != {group.gr_gid}
            or set(group.gr_mem) - {ACCOUNT}):
        raise PrerequisiteError("unsafe service identity")
    for other in pwd.getpwall():
        if other.pw_name != ACCOUNT and (other.pw_uid == account.pw_uid or other.pw_gid == group.gr_gid):
            raise PrerequisiteError("shared service identity")
    return account.pw_uid, group.gr_gid


def main() -> int:
    if len(sys.argv) != 1 or os.geteuid() != 0:
        print("medtech-prereqs: root and fixed paths required", file=sys.stderr)
        return 1
    descriptor = None
    try:
        descriptor = _open_parent(PARENT)
        identity = _identity()
        if identity is None:
            # An orphaned existing tree needs operator review, never automatic adoption.
            existing = _existing(descriptor, ROOT_NAME)
            if existing is not None:
                os.close(existing)
                raise PrerequisiteError("existing tree has no dedicated owner")
            subprocess.run(
                ["/usr/sbin/useradd", "--system", "--user-group", "--home-dir", "/nonexistent",
                 "--no-create-home", "--shell", "/usr/sbin/nologin", ACCOUNT],
                check=True, capture_output=True, timeout=30,
            )
            identity = _identity()
            if identity is None:
                raise PrerequisiteError("service identity was not created")
        _provision_at(descriptor, *identity)
        return 0
    except (OSError, PrerequisiteError, subprocess.SubprocessError):
        print("medtech-prereqs: unsafe or unavailable identity/root; no existing paths repaired", file=sys.stderr)
        return 1
    finally:
        if descriptor is not None:
            os.close(descriptor)


if __name__ == "__main__":
    raise SystemExit(main())
