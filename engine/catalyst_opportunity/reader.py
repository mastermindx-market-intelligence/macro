"""Bounded read of the existing owner artifact. Never creates a second publisher."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Callable
import hashlib
import json
import os
import stat

from .projection import _base, _seal, _utc, build_opportunity_view

SOURCE_PATH = Path("site/basketdata/sector_pulse.json")
MAX_BYTES = 3_000_000


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError("nonfinite JSON constant")


def read_current_view(root: Path, *, clock: Callable[[], datetime] | None = None) -> dict:
    """Read the fixed source path, then stamp actual observation and compose.

    The source date is not an arrival clock. Requests cannot override the path
    or request a historical cutoff. A racing read is unavailable, without retry.
    """
    clock = clock or (lambda: datetime.now(timezone.utc))
    fd = None
    reason = "SOURCE_UNAVAILABLE"
    try:
        path = Path(root) / SOURCE_PATH
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
            raise ValueError("invalid source file")
        pieces, total = [], 0
        while True:
            piece = os.read(fd, min(65536, MAX_BYTES + 1 - total))
            if not piece:
                break
            pieces.append(piece)
            total += len(piece)
            if total > MAX_BYTES:
                raise ValueError("source too large")
        after = os.fstat(fd)
        current = path.stat(follow_symlinks=False)
        identity = lambda v: (v.st_dev, v.st_ino, v.st_size, v.st_mtime_ns, v.st_ctime_ns)
        if identity(before) != identity(after) or identity(after) != identity(current):
            reason = "SOURCE_CHANGED_DURING_READ"
            raise ValueError("changed input")
        raw = b"".join(pieces)
        if len(raw) != before.st_size:
            raise ValueError("incomplete input")
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique,
                             parse_constant=_reject_constant)
        observed_at = _utc(clock(), "clock")
        view = build_opportunity_view(payload, received_at=observed_at, assessed_at=observed_at)
        if view["source"] is not None:
            view["source"]["content_sha256"] = hashlib.sha256(raw).hexdigest()
        return _seal(view)
    except FileNotFoundError:
        pass
    except (OSError, ValueError, UnicodeError, RecursionError, TypeError):
        if reason == "SOURCE_UNAVAILABLE":
            reason = "SOURCE_INVALID_OR_UNREADABLE"
    finally:
        if fd is not None:
            os.close(fd)
    return _seal(_base(_utc(clock(), "clock"), reason))
