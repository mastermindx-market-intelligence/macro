#!/usr/bin/env python3
"""Exact owned-Git-index-lock identity helpers for Options nightly publication.

This is the former inline Python of options_signal_nightly.sh. It is invoked as
a real file, not an inline shell here-document: the macOS Actions bash worker
can otherwise block while writing the heredoc within command substitution.

Ownership is a single-linked regular inode plus its exact phase-specific bytes.
Descriptor writes prevent pathname redirection; installation still assumes
cooperative writers across its final pathname check/rename interval.
"""
from __future__ import annotations

import hashlib
import os
import stat
import sys


def acquire(path: str) -> int:
    try:
        fd = os.open(
            path,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK,
            0o666,
        )
        try:
            st = os.fstat(fd)
            named = os.stat(path, follow_symlinks=False)
            if (
                not stat.S_ISREG(st.st_mode)
                or st.st_nlink != 1
                or st.st_size != 0
                or (st.st_dev, st.st_ino) != (named.st_dev, named.st_ino)
            ):
                raise ValueError("not the owned empty lock")
            print(f"{st.st_dev}:{st.st_ino}")
        finally:
            os.close(fd)
    except (OSError, ValueError):
        return 1
    return 0


def release(path: str, identity: str) -> int:
    try:
        expected = tuple(int(value) for value in identity.split(":"))
        if len(expected) != 2:
            raise ValueError("invalid owned lock identity")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            st = os.fstat(fd)
            named = os.stat(path, follow_symlinks=False)
            if (
                not stat.S_ISREG(st.st_mode)
                or st.st_nlink != 1
                or st.st_size != 0
                or (st.st_dev, st.st_ino) != expected
                or (named.st_dev, named.st_ino) != expected
            ):
                raise ValueError("lock identity changed; preserve it")
            os.unlink(path)
        finally:
            os.close(fd)
    except (OSError, ValueError):
        return 1
    return 0



def _identity(value: str) -> tuple[int, int]:
    parts = tuple(int(item) for item in value.split(":"))
    if len(parts) != 2 or any(item < 0 for item in parts):
        raise ValueError("invalid owned lock identity")
    return parts


def _fingerprint(data: bytes) -> str:
    return f"{len(data)}:{hashlib.sha256(data).hexdigest()}"


def _close(fd: int | None) -> None:
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            # Closing this helper's descriptor cannot undo an acknowledged
            # rename; process exit also releases it. Do not misreport the effect.
            pass


def _read_regular(path: str) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError("source is not a private regular index")
        chunks = []
        while chunk := os.read(fd, 65536):
            chunks.append(chunk)
        after = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        if (
            (before.st_dev, before.st_ino) != (named.st_dev, named.st_ino)
            or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            or after.st_nlink != 1
        ):
            raise ValueError("source index changed while reading")
        return b"".join(chunks)
    finally:
        _close(fd)


def _verify_owned(fd: int, path: str, identity: str, expected: str) -> None:
    owner = _identity(identity)
    before = os.fstat(fd)
    named = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISREG(before.st_mode)
        or before.st_nlink != 1
        or (before.st_dev, before.st_ino) != owner
        or (named.st_dev, named.st_ino) != owner
    ):
        raise ValueError("owned lock identity changed")
    # Reject a FIFO above before attempting any content read.
    os.lseek(fd, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    size = 0
    while chunk := os.read(fd, 65536):
        digest.update(chunk)
        size += len(chunk)
    actual = f"{size}:{digest.hexdigest()}"
    wanted = _fingerprint(b"") if expected == "empty" else expected
    after = os.fstat(fd)
    named = os.stat(path, follow_symlinks=False)
    if (
        actual != wanted
        or after.st_nlink != 1
        or (named.st_dev, named.st_ino) != owner
        or (before.st_size, before.st_mtime_ns, before.st_ctime_ns)
        != (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
    ):
        raise ValueError("owned lock content or pathname changed")


def fingerprint(path: str) -> int:
    try:
        print(_fingerprint(_read_regular(path)))
    except (OSError, ValueError):
        return 1
    return 0


def fill(path: str, identity: str, previous: str, source: str, expected: str) -> int:
    """Write only through the verified descriptor, never a reopened pathname."""
    fd = None
    writing = False
    try:
        data = _read_regular(source)
        if _fingerprint(data) != expected:
            raise ValueError("private snapshot fingerprint changed")
        fd = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
        _verify_owned(fd, path, identity, previous)
        os.lseek(fd, 0, os.SEEK_SET)
        writing = True
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            count = os.write(fd, view[offset:])
            if count <= 0:
                raise OSError("short owned-index write")
            offset += count
        os.ftruncate(fd, len(data))
        _verify_owned(fd, path, identity, expected)
    except (OSError, ValueError):
        print("UNKNOWN" if writing else "NOT_APPLIED")
        return 2 if writing else 1
    finally:
        _close(fd)
    print("PREPARED")
    return 0


def verify(path: str, identity: str, expected: str) -> int:
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        _verify_owned(fd, path, identity, expected)
    except (OSError, ValueError):
        return 1
    finally:
        _close(fd)
    return 0


def install(path: str, identity: str, expected: str, destination: str) -> int:
    """Distinguish pre-install refusal from an unconfirmed replacement outcome.

    The final pathname check/rename interval and concurrent same-inode writes
    still require cooperative filesystem writers; this is not hostile-FS CAS.
    """
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        _verify_owned(fd, path, identity, expected)
    except (OSError, ValueError):
        _close(fd)
        print("NOT_APPLIED")
        return 1
    try:
        os.replace(path, destination)
    except OSError:
        # Do not turn an unconfirmed filesystem replacement into permission to
        # roll back the ref or rebuild the live index.
        print("UNKNOWN")
        return 2
    finally:
        _close(fd)
    print("APPLIED")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2 and args[0] == "acquire":
        return acquire(args[1])
    if len(args) == 3 and args[0] == "release":
        return release(args[1], args[2])
    if len(args) == 2 and args[0] == "fingerprint":
        return fingerprint(args[1])
    if len(args) == 6 and args[0] == "fill":
        return fill(*args[1:])
    if len(args) == 4 and args[0] == "verify":
        return verify(*args[1:])
    if len(args) == 5 and args[0] == "install":
        return install(*args[1:])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
