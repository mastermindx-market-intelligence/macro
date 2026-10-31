#!/usr/bin/env python3
"""Exact owned-Git-index-lock identity helpers for Options nightly publication.

This is the former inline Python of options_signal_nightly.sh. It is invoked as
a real file, not an inline shell here-document: the macOS Actions bash worker
can otherwise block while writing the heredoc within command substitution.

Acquiring and releasing only a still-empty, single-linked, regular inode is
the security boundary. Never assume a pathname alone proves ownership.
"""
from __future__ import annotations

import os
import stat
import sys


def check(path: str, identity: str) -> int:
    """Inspect the same existing empty inode without releasing it."""
    try:
        expected = tuple(int(value) for value in identity.split(":"))
        if len(expected) != 2:
            return 1
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            st = os.fstat(fd)
            named = os.stat(path, follow_symlinks=False)
            return 0 if (stat.S_ISREG(st.st_mode) and st.st_nlink == 1 and st.st_size == 0
                and (st.st_dev, st.st_ino) == expected == (named.st_dev, named.st_ino)) else 1
        finally:
            os.close(fd)
    except (OSError, ValueError):
        return 1


class OwnedEmptyIndexLock:
    """Process-bound owner resource; index custody is not publication admission."""
    def __init__(self, path):
        self.path, self.pid = str(path), os.getpid()
        self.fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_NONBLOCK, 0o666)
        info = os.fstat(self.fd)
        self.identity = f'{info.st_dev}:{info.st_ino}'
        try:
            self.assert_valid()
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise

    def assert_valid(self):
        if self.fd is None or os.getpid() != self.pid or check(self.path, self.identity):
            raise OSError('original empty index lock identity changed')
        info = os.fstat(self.fd)
        if f'{info.st_dev}:{info.st_ino}' != self.identity or info.st_nlink != 1 or info.st_size != 0:
            raise OSError('original index lock descriptor changed')

    def close(self, *, preserve=False):
        if self.fd is None:
            return
        try:
            self.assert_valid()
            if not preserve and release(self.path, self.identity):
                raise OSError('original index lock cannot be safely released')
        finally:
            os.close(self.fd)
            self.fd = None

    def __reduce__(self):
        raise TypeError('owned index resource cannot transfer')


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


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) == 2 and args[0] == "acquire":
        return acquire(args[1])
    if len(args) == 3 and args[0] == "release":
        return release(args[1], args[2])
    if len(args) == 3 and args[0] == "check":
        return check(args[1], args[2])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
