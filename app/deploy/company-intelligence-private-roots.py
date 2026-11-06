#!/usr/bin/env python3
"""Provision empty Company Intelligence directories before the API mount boundary.

The production entry point accepts no path override. Existing unsafe nodes are
refused without chmod, chown, deletion, or recursive repair. This does not create
current.json, manifests, artifacts, retained sources, or publisher journals.
The API reads state and artifacts; its namespace hides publisher entirely.
"""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

ROOT_NAME = "macro-company-intelligence"
PRODUCTION_PARENT = Path("/var/lib")
PRIVATE_PATHS = (
    (ROOT_NAME,),
    (ROOT_NAME, "state"),
    (ROOT_NAME, "state", "generations"),
    (ROOT_NAME, "artifacts"),
    (ROOT_NAME, "publisher"),
    (ROOT_NAME, "publisher", "source"),
    (ROOT_NAME, "publisher", "operations"),
)
OPEN_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC


class ProvisioningError(RuntimeError):
    """The private directory boundary could not be safely established."""


def _validate_directory(fd: int, uid: int, gid: int, *, private: bool) -> None:
    info = os.fstat(fd)
    mode = stat.S_IMODE(info.st_mode)
    if not stat.S_ISDIR(info.st_mode):
        raise ProvisioningError("not a directory")
    if info.st_uid != uid or info.st_gid != gid:
        raise ProvisioningError("unexpected directory owner or group")
    if (private and mode != 0o700) or (not private and mode & 0o022):
        raise ProvisioningError("unsafe directory mode")


def _open_parent(path: Path, uid: int, gid: int) -> int:
    """Open every lexical ancestor without following symlinks; create nothing."""
    if not path.is_absolute() or ".." in path.parts:
        raise ProvisioningError("parent must be an absolute lexical path")
    fd = os.open("/", OPEN_DIRECTORY)
    try:
        _validate_directory(fd, uid, gid, private=False)
        for component in path.parts[1:]:
            next_fd = os.open(component, OPEN_DIRECTORY, dir_fd=fd)
            os.close(fd)
            fd = next_fd
            _validate_directory(fd, uid, gid, private=False)
        return fd
    except BaseException:
        os.close(fd)
        raise


def _provision_at(parent_fd: int, uid: int, gid: int) -> None:
    """Use an already trusted parent descriptor (isolated temp parent in tests).

    Validate all existing private nodes before creating any missing sibling.
    Descriptor-relative operations never resolve a slot through a symlink.
    The parent and every private directory must remain owned by this identity;
    concurrently replacing them is refused, never silently adopted.
    """
    _validate_directory(parent_fd, uid, gid, private=False)
    opened = {(): os.dup(parent_fd)}
    try:
        for parts in PRIVATE_PATHS:
            parent = opened.get(parts[:-1])
            if parent is None:
                continue
            try:
                child = os.open(parts[-1], OPEN_DIRECTORY, dir_fd=parent)
            except FileNotFoundError:
                continue
            opened[parts] = child
            _validate_directory(child, uid, gid, private=True)

        for parts in PRIVATE_PATHS:
            if parts not in opened:
                parent = opened[parts[:-1]]
                os.mkdir(parts[-1], 0o700, dir_fd=parent)
                child = os.open(parts[-1], OPEN_DIRECTORY, dir_fd=parent)
                opened[parts] = child
                _validate_directory(child, uid, gid, private=True)

        for parts in PRIVATE_PATHS:
            info = os.stat(parts[-1], dir_fd=opened[parts[:-1]], follow_symlinks=False)
            held = os.fstat(opened[parts])
            if (info.st_dev, info.st_ino) != (held.st_dev, held.st_ino):
                raise ProvisioningError("directory changed during provisioning")
            _validate_directory(opened[parts], uid, gid, private=True)
    except OSError as exc:
        raise ProvisioningError("cannot establish private directory boundary") from exc
    finally:
        for fd in reversed(tuple(opened.values())):
            os.close(fd)


def provision_private_roots() -> None:
    """Production-only fixed root, owned root:root, with trusted system ancestors."""
    try:
        parent = _open_parent(PRODUCTION_PARENT, 0, 0)
        try:
            _provision_at(parent, 0, 0)
        finally:
            os.close(parent)
    except OSError as exc:
        raise ProvisioningError("cannot open trusted production parent") from exc


def main(argv: list[str] | None = None) -> int:
    if (sys.argv[1:] if argv is None else argv):
        print("company-intelligence-private-roots: no arguments permitted", file=sys.stderr)
        return 2
    if os.geteuid() != 0:
        print("company-intelligence-private-roots: requires root", file=sys.stderr)
        return 2
    try:
        provision_private_roots()
    except ProvisioningError as exc:
        print(f"company-intelligence-private-roots: {exc}", file=sys.stderr)
        return 1
    print("company-intelligence-private-roots: empty directory boundary ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
