"""Private original-run evidence, never a recovery or writer-admission grant.

The existing producer may explicitly supply this sink before adopting BUILDING.
Each append is durable before returning; a failed append closes further effects.
The file stays on its original host/private artifact carrier. Nothing here opens
a store, retries a write, resumes a generation, or releases an original owner.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat


SCHEMA = "research_vault.generation_evidence.v1"
MAX_BYTES = 128 * 1024 * 1024
MAX_LINE_BYTES = 32 * 1024 * 1024
KINDS = frozenset({"write_intent", "write_result", "catalog_observed",
                   "publication_plan", "terminal", "continuation_origin"})


class EvidenceUnavailable(RuntimeError):
    """Missing, corrupt, active, or unpersisted original-run evidence."""


def _identity(value):
    if (type(value) is not dict or set(value) != {"source_commit", "run"}
            or type(value["source_commit"]) is not str
            or re.fullmatch(r"[0-9a-f]{40}", value["source_commit"]) is None
            or type(value["run"]) is not str or not value["run"]
            or value["run"] != value["run"].strip()):
        raise EvidenceUnavailable("exact original producer identity required")
    return dict(value)


def _limit(value):
    if type(value) is not int or not 0 < value <= MAX_BYTES:
        raise EvidenceUnavailable("invalid evidence byte bound")
    return value


def _private_regular(fd):
    info = os.fstat(fd)
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1):
        raise EvidenceUnavailable("private same-owner regular evidence file required")
    return info


class FileGenerationEvidence:
    """Exclusive append-only sink; retain it for the whole producer invocation."""

    @classmethod
    def create(cls, path, identity, *, max_bytes=MAX_BYTES):
        identity, bound = _identity(identity), _limit(max_bytes)
        path = Path(path)
        try:
            parent = path.parent.stat()
        except OSError as exc:
            raise EvidenceUnavailable("evidence directory unavailable: " + type(exc).__name__) from None
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
                or parent.st_mode & 0o077):
            raise EvidenceUnavailable("existing private original-run directory required")
        fd, obj = None, None
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            _private_regular(fd)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            obj = cls()
            obj._fd, obj._bound, obj._bytes = fd, bound, 0
            obj._sequence, obj._previous, obj._poisoned = 0, None, False
            obj._capture_hash, obj._capture_sha256 = hashlib.sha256(), None
            obj._identity = identity
            obj._append("header", {"identity": identity})
            # Persist the directory entry too. An incomplete file remains as
            # evidence of a failed start; never unlink and silently reuse it.
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            return obj
        except Exception as exc:
            if obj is not None:
                obj._fd = None
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    # close may already have released the descriptor. Never
                    # retry it: the process may have reused that integer.
                    pass
            raise EvidenceUnavailable("evidence creation unavailable: " + type(exc).__name__) from None

    def append(self, kind, payload, *, reserve_bytes=0):
        if type(kind) is not str or kind not in KINDS:
            raise EvidenceUnavailable("unsupported evidence event")
        return self._append(kind, payload, reserve_bytes=reserve_bytes)

    @property
    def identity(self):
        return dict(self._identity)

    @property
    def capture_sha256(self):
        """Digest of this original process's durable bytes after clean close.

        Retain through the original run's trusted output/custody path. This
        value authenticates neither the caller/source nor remote settlement,
        and a partial journal is not evidence that publication completed.
        It never recomputes a digest from a later, possibly changed file.
        """
        if self._capture_sha256 is None:
            raise EvidenceUnavailable("original capture not closed and durable")
        return self._capture_sha256

    def _append(self, kind, payload, *, reserve_bytes=0):
        if self._fd is None or self._poisoned:
            raise EvidenceUnavailable("evidence sink closed or uncertain")
        if type(payload) is not dict:
            raise EvidenceUnavailable("evidence payload must be a mapping")
        if type(reserve_bytes) is not int or not 0 <= reserve_bytes <= self._bound:
            raise EvidenceUnavailable("invalid evidence reservation budget")
        event = {"kind": kind, "payload": payload}
        document = {"schema": SCHEMA, "sequence": self._sequence,
                    "previous_sha256": self._previous, "event": event}
        try:
            data = (json.dumps(document, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")
        except (TypeError, ValueError, UnicodeError):
            raise EvidenceUnavailable("noncanonical evidence payload") from None
        if len(data) > MAX_LINE_BYTES or self._bytes + len(data) + reserve_bytes > self._bound:
            raise EvidenceUnavailable("evidence byte budget exhausted")
        try:
            remaining = memoryview(data)
            while remaining:
                written = os.write(self._fd, remaining)
                if written <= 0:
                    raise OSError("no evidence write progress")
                remaining = remaining[written:]
            os.fsync(self._fd)
        except Exception as exc:
            self._poisoned = True
            raise EvidenceUnavailable("evidence append uncertain: " + type(exc).__name__) from None
        sequence = self._sequence
        self._sequence += 1
        self._bytes += len(data)
        self._previous = hashlib.sha256(data).hexdigest()
        self._capture_hash.update(data)
        return sequence

    def close(self):
        if self._fd is not None:
            fd = self._fd
            self._fd = None
            try:
                os.close(fd)
            except OSError as exc:
                self._poisoned = True
                raise EvidenceUnavailable("evidence close uncertain: " + type(exc).__name__) from None
            if not self._poisoned:
                self._capture_sha256 = self._capture_hash.hexdigest()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def _pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            raise EvidenceUnavailable("duplicate evidence field")
        out[key] = value
    return out


def _nonfinite(_):
    raise EvidenceUnavailable("nonfinite evidence value")


def read_evidence(path, *, expected_identity, expected_sha256=None, max_bytes=MAX_BYTES):
    """Inspect a settled local file. A valid chain is not source authentication.

    Exclusive nonblocking locking refuses a currently open original writer.
    This only describes this host/file; it does not settle remote delayed I/O.
    An independently retained capture digest can bind the whole file, including
    complete-line truncation. Computing that digest from the current file is not
    evidence of an original capture, custody, or source authentication.
    """
    identity, bound = _identity(expected_identity), _limit(max_bytes)
    if expected_sha256 is not None and (type(expected_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None):
        raise EvidenceUnavailable("invalid original capture digest")
    fd = None
    try:
        # A non-regular path (notably a FIFO) must fail fstat, not block open
        # forever before the type check can run. This flag is inert on a file.
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = _private_regular(fd)
        if not 0 < before.st_size <= bound:
            raise EvidenceUnavailable("evidence file outside byte bound")
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with os.fdopen(os.dup(fd), "rb") as stream:
            events, previous, total = [], None, 0
            digest = hashlib.sha256()
            while True:
                line = stream.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                total += len(line)
                if (total > bound or len(line) > MAX_LINE_BYTES or not line.endswith(b"\n")):
                    raise EvidenceUnavailable("truncated or oversized evidence record")
                document = json.loads(line, object_pairs_hook=_pairs, parse_constant=_nonfinite)
                if (type(document) is not dict
                        or set(document) != {"schema", "sequence", "previous_sha256", "event"}
                        or document["schema"] != SCHEMA
                        or type(document["sequence"]) is not int
                        or document["sequence"] != len(events)
                        or document["previous_sha256"] != previous):
                    raise EvidenceUnavailable("evidence chain mismatch")
                event = document["event"]
                if (type(event) is not dict or set(event) != {"kind", "payload"}
                        or type(event["payload"]) is not dict
                        or event["kind"] not in (KINDS if events else {"header"})):
                    raise EvidenceUnavailable("invalid evidence event")
                if not events and event["payload"] != {"identity": identity}:
                    raise EvidenceUnavailable("original evidence identity mismatch")
                events.append(event)
                digest.update(line)
                previous = hashlib.sha256(line).hexdigest()
        after = os.fstat(fd)
        if not events or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise EvidenceUnavailable("evidence changed during inspection")
        if expected_sha256 is not None and digest.hexdigest() != expected_sha256:
            raise EvidenceUnavailable("original capture digest mismatch")
        return events
    except EvidenceUnavailable:
        raise
    except Exception as exc:
        raise EvidenceUnavailable("evidence inspection unavailable: " + type(exc).__name__) from None
    finally:
        if fd is not None:
            os.close(fd)
