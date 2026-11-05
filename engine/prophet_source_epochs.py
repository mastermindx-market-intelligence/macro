"""Deterministic, read-only projection of prophet source-board epoch identity.

Answers one question: does the *current* live source board still carry the
same raw byte identity as the immutable origination snapshot the board index
is bound to?

Deliberately not done here: nothing is settled (this reader has no A2 exact
four-family source-published / source-read receipt, so every outcome carries
``settlement_status == "PENDING"`` plus the standing reason code
``FOUR_FAMILY_RECEIPT_NOT_EVALUATED`` -- two identical raw hashes are not a
settlement); nothing is published, mutated, bundled, created or written; and
no caller-supplied free-form text is copied into the result.

Public API
----------
``project_source_epochs(board_bytes=..., index_bytes=..., snapshot_bytes=...)``
    Pure projection over three raw byte blobs; ``snapshot_bytes`` are the
    exact *decompressed* bytes of the frozen raw board.  No I/O.
``read_source_epochs(board_bytes=..., index_bytes=..., data_dir=...)``
    Reads the single canonical gzip
    ``<data_dir>/prophet/origination_sources/<sha>.json.gz``, then defers to
    the pure projector.

Result shape (exact, frozen): ``schema`` ("prophet_source_epochs.v1"),
``relation`` ("SAME_SOURCE" | "SEPARATE_EPOCHS" | "UNAVAILABLE"),
``settlement_status`` ("PENDING"), ``reason_codes`` (fixed vocabulary) and
three sub-objects -- ``current_board`` {sha256, source_asof}, ``index``
{sha256, asof, source_asof}, ``origination_board`` {sha256, source_asof,
snapshot_verified}.  Every sha256 is the SHA-256 of the *exact raw bytes* of
that artifact (live board, index document, decompressed frozen board) and is
still reported when the artifact is not valid JSON.  ``index["sha256"]`` is
the identity of the index document itself; the board digest the index binds
is verified against the frozen snapshot and surfaces as
``origination_board["sha256"]`` with ``origination_board["snapshot_verified"]``.

Stdlib only: no third-party imports, no network, no writes.
"""

from __future__ import annotations

import errno
import gzip
import os
import stat
from contextlib import ExitStack
import hashlib
import json
import pathlib
import re
import zlib
from datetime import date
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

__all__ = [
    "MAX_SNAPSHOT_BYTES",
    "REASON_CODES",
    "SCHEMA",
    "SETTLEMENT_STATUS",
    "project_source_epochs",
    "read_source_epochs",
]

SCHEMA = "prophet_source_epochs.v1"
SETTLEMENT_STATUS = "PENDING"

RELATION_SAME_SOURCE = "SAME_SOURCE"
RELATION_SEPARATE_EPOCHS = "SEPARATE_EPOCHS"
RELATION_UNAVAILABLE = "UNAVAILABLE"

#: Upper bound for the decompressed frozen board (32 MiB; the current board
#: is ~2.6 MB).  A larger payload is refused, never truncated.
MAX_SNAPSHOT_BYTES = 32 * 1024 * 1024

_SNAPSHOT_ENCODING = "gzip"
_SNAPSHOT_RELATIVE_DIR = ("prophet", "origination_sources")
_SNAPSHOT_PATH_TEMPLATE = "data/prophet/origination_sources/{sha}.json.gz"

_SHA256_RE = re.compile(r"\A[0-9a-f]{64}\Z")
_ISO_DATE_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

# ---------------------------------------------------------------------------
# Fixed reason-code vocabulary.  Nothing outside this set may ever appear in
# ``result["reason_codes"]``.
# ---------------------------------------------------------------------------

REASON_FOUR_FAMILY_RECEIPT_NOT_EVALUATED = "FOUR_FAMILY_RECEIPT_NOT_EVALUATED"
REASON_CURRENT_BOARD_MISSING = "CURRENT_BOARD_MISSING"
REASON_CURRENT_BOARD_JSON_INVALID = "CURRENT_BOARD_JSON_INVALID"
REASON_CURRENT_BOARD_ASOF_INVALID = "CURRENT_BOARD_ASOF_INVALID"
REASON_INDEX_MISSING = "INDEX_MISSING"
REASON_INDEX_JSON_INVALID = "INDEX_JSON_INVALID"
REASON_INDEX_SOURCE_BOARD_SHA256_INVALID = "INDEX_SOURCE_BOARD_SHA256_INVALID"
REASON_INDEX_SNAPSHOT_PATH_INVALID = "INDEX_SNAPSHOT_PATH_INVALID"
REASON_INDEX_SNAPSHOT_ENCODING_INVALID = "INDEX_SNAPSHOT_ENCODING_INVALID"
REASON_INDEX_ASOF_INVALID = "INDEX_ASOF_INVALID"
REASON_INDEX_SOURCE_ASOF_INVALID = "INDEX_SOURCE_ASOF_INVALID"
REASON_INDEX_SOURCE_BOARD_ASOF_INVALID = "INDEX_SOURCE_BOARD_ASOF_INVALID"
REASON_SNAPSHOT_MISSING = "SNAPSHOT_MISSING"
REASON_SNAPSHOT_NOT_READ = "SNAPSHOT_NOT_READ"
REASON_SNAPSHOT_FILE_MISSING = "SNAPSHOT_FILE_MISSING"
REASON_SNAPSHOT_FILE_UNREADABLE = "SNAPSHOT_FILE_UNREADABLE"
REASON_SNAPSHOT_DECOMPRESS_FAILED = "SNAPSHOT_DECOMPRESS_FAILED"
REASON_SNAPSHOT_TOO_LARGE = "SNAPSHOT_TOO_LARGE"
REASON_SNAPSHOT_PATH_ESCAPE = "SNAPSHOT_PATH_ESCAPE"
REASON_DATA_DIR_UNAVAILABLE = "DATA_DIR_UNAVAILABLE"
REASON_SNAPSHOT_SHA_MISMATCH = "SNAPSHOT_SHA_MISMATCH"
REASON_SNAPSHOT_JSON_INVALID = "SNAPSHOT_JSON_INVALID"
REASON_SNAPSHOT_ASOF_INVALID = "SNAPSHOT_ASOF_INVALID"
REASON_SOURCE_BOARD_ASOF_MISMATCH = "SOURCE_BOARD_ASOF_MISMATCH"

REASON_CODES = frozenset([
    REASON_FOUR_FAMILY_RECEIPT_NOT_EVALUATED, REASON_CURRENT_BOARD_MISSING,
    REASON_CURRENT_BOARD_JSON_INVALID, REASON_CURRENT_BOARD_ASOF_INVALID,
    REASON_INDEX_MISSING, REASON_INDEX_JSON_INVALID,
    REASON_INDEX_SOURCE_BOARD_SHA256_INVALID, REASON_INDEX_SNAPSHOT_PATH_INVALID,
    REASON_INDEX_SNAPSHOT_ENCODING_INVALID, REASON_INDEX_ASOF_INVALID,
    REASON_INDEX_SOURCE_ASOF_INVALID, REASON_INDEX_SOURCE_BOARD_ASOF_INVALID,
    REASON_SNAPSHOT_MISSING, REASON_SNAPSHOT_NOT_READ,
    REASON_SNAPSHOT_FILE_MISSING, REASON_SNAPSHOT_FILE_UNREADABLE,
    REASON_SNAPSHOT_DECOMPRESS_FAILED, REASON_SNAPSHOT_TOO_LARGE,
    REASON_SNAPSHOT_PATH_ESCAPE, REASON_DATA_DIR_UNAVAILABLE,
    REASON_SNAPSHOT_SHA_MISMATCH, REASON_SNAPSHOT_JSON_INVALID,
    REASON_SNAPSHOT_ASOF_INVALID, REASON_SOURCE_BOARD_ASOF_MISMATCH,
])


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


class _DuplicateKeyError(ValueError):
    """Raised when a JSON object contains the same key twice."""


def _reject_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    seen = set()
    for key, _value in pairs:
        if key in seen:
            raise _DuplicateKeyError("duplicate key")
        seen.add(key)
    return dict(pairs)


def _reject_constant(name: str) -> Any:
    """Refuse NaN/Infinity: they are not JSON and cannot be asserted as data."""
    raise ValueError("non-finite JSON constant: %s" % name)


def _parse_json_object(raw: bytes) -> Optional[Dict[str, Any]]:
    """Return the decoded JSON object, or ``None`` when it is not a plain
    object with strictly valid, duplicate-free, finite content."""
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (ValueError, RecursionError):
        # ValueError covers JSONDecodeError, UnicodeDecodeError and the
        # duplicate-key / non-finite refusals above.
        return None
    return value if isinstance(value, dict) else None


def _iso_date(value: Any) -> Optional[str]:
    """Return ``value`` when it is a strict ISO ``YYYY-MM-DD`` calendar date."""
    if not isinstance(value, str) or not _ISO_DATE_RE.match(value):
        return None
    try:
        date.fromisoformat(value)
    except ValueError:
        return None
    return value


def _as_bytes(raw: Any, name: str) -> Optional[bytes]:
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray, memoryview)):
        return bytes(raw)
    raise TypeError("%s must be bytes-like or None, got %s" % (name, type(raw).__name__))


def _sha256_hex(raw: Optional[bytes]) -> Optional[str]:
    return None if raw is None else hashlib.sha256(raw).hexdigest()


def _ordered_codes(codes: List[str]) -> List[str]:
    """De-duplicate, keep insertion order, pin the standing marker first."""
    seen = set()
    ordered = []
    for code in codes:
        if code not in seen:
            seen.add(code)
            ordered.append(code)
    return [REASON_FOUR_FAMILY_RECEIPT_NOT_EVALUATED] + ordered


# ---------------------------------------------------------------------------
# Per-artifact facts
# ---------------------------------------------------------------------------


class _BoardFacts(NamedTuple):
    present: bool
    codes: Tuple[str, ...]
    asof: Optional[str]
    sha256: Optional[str]
    valid: bool


class _IndexFacts(NamedTuple):
    present: bool
    codes: Tuple[str, ...]
    declared_board_sha256: Optional[str]
    raw_sha256: Optional[str]
    asof: Optional[str]
    source_asof: Optional[str]
    source_board_asof: Optional[str]
    accepted: bool


class _SnapshotFacts(NamedTuple):
    present: bool
    codes: Tuple[str, ...]
    asof: Optional[str]
    sha256: Optional[str]
    verified: bool


def _analyze_board(board_bytes: Optional[bytes]) -> _BoardFacts:
    if board_bytes is None:
        return _BoardFacts(False, (REASON_CURRENT_BOARD_MISSING,), None, None, False)
    sha256 = _sha256_hex(board_bytes)
    obj = _parse_json_object(board_bytes)
    if obj is None:
        return _BoardFacts(True, (REASON_CURRENT_BOARD_JSON_INVALID,), None, sha256, False)
    asof = _iso_date(obj.get("as_of"))
    if asof is None:
        return _BoardFacts(True, (REASON_CURRENT_BOARD_ASOF_INVALID,), None, sha256, False)
    return _BoardFacts(True, (), asof, sha256, True)


def _analyze_index(index_bytes: Optional[bytes]) -> _IndexFacts:
    if index_bytes is None:
        return _IndexFacts(False, (REASON_INDEX_MISSING,), None, None, None, None, None, False)
    raw_sha256 = _sha256_hex(index_bytes)
    obj = _parse_json_object(index_bytes)
    if obj is None:
        return _IndexFacts(True, (REASON_INDEX_JSON_INVALID,), None, raw_sha256,
                           None, None, None, False)

    codes: List[str] = []

    declared = obj.get("source_board_sha256")
    declared_sha: Optional[str] = None
    if isinstance(declared, str) and _SHA256_RE.match(declared):
        declared_sha = declared
    else:
        codes.append(REASON_INDEX_SOURCE_BOARD_SHA256_INVALID)

    expected_path = (
        _SNAPSHOT_PATH_TEMPLATE.format(sha=declared_sha) if declared_sha else None
    )
    declared_path = obj.get("source_board_snapshot_path")
    if not (isinstance(declared_path, str) and expected_path is not None
            and declared_path == expected_path):
        codes.append(REASON_INDEX_SNAPSHOT_PATH_INVALID)

    encoding = obj.get("source_board_snapshot_encoding")
    if not (isinstance(encoding, str) and encoding == _SNAPSHOT_ENCODING):
        codes.append(REASON_INDEX_SNAPSHOT_ENCODING_INVALID)

    asof = _iso_date(obj.get("asof"))
    if asof is None:
        codes.append(REASON_INDEX_ASOF_INVALID)

    source_asof = _iso_date(obj.get("source_asof"))
    if source_asof is None:
        codes.append(REASON_INDEX_SOURCE_ASOF_INVALID)

    source_board_asof = _iso_date(obj.get("source_board_asof"))
    if source_board_asof is None:
        codes.append(REASON_INDEX_SOURCE_BOARD_ASOF_INVALID)

    return _IndexFacts(True, tuple(codes), declared_sha, raw_sha256, asof,
                       source_asof, source_board_asof, not codes)


def _analyze_snapshot(
    snapshot_bytes: Optional[bytes], declared_sha: Optional[str]
) -> _SnapshotFacts:
    if snapshot_bytes is None:
        return _SnapshotFacts(False, (), None, None, False)
    codes: List[str] = []
    sha256 = _sha256_hex(snapshot_bytes)
    sha_ok = declared_sha is not None and sha256 == declared_sha
    if not sha_ok:
        codes.append(REASON_SNAPSHOT_SHA_MISMATCH)
    obj = _parse_json_object(snapshot_bytes)
    asof: Optional[str] = None
    if obj is None:
        codes.append(REASON_SNAPSHOT_JSON_INVALID)
    else:
        asof = _iso_date(obj.get("as_of"))
        if asof is None:
            codes.append(REASON_SNAPSHOT_ASOF_INVALID)
    # ``verified`` is a byte-identity statement only: the bytes are exactly
    # the declared digest and parse as a JSON object.  The date-agreement
    # gate is applied separately when choosing the relation.
    return _SnapshotFacts(True, tuple(codes), asof, sha256, bool(sha_ok and obj is not None))


# ---------------------------------------------------------------------------
# Pure projection
# ---------------------------------------------------------------------------


def _project(
    *,
    board_bytes: Optional[bytes],
    index_bytes: Optional[bytes],
    snapshot_bytes: Optional[bytes],
    extra_codes: Tuple[str, ...],
    snapshot_absence_code: Optional[str],
) -> Dict[str, Any]:
    board = _analyze_board(board_bytes)
    index = _analyze_index(index_bytes)
    snapshot = _analyze_snapshot(snapshot_bytes, index.declared_board_sha256)

    codes: List[str] = []
    codes.extend(board.codes)
    codes.extend(index.codes)
    codes.extend(snapshot.codes)
    if (index.source_board_asof is not None and snapshot.asof is not None
            and index.source_board_asof != snapshot.asof):
        codes.append(REASON_SOURCE_BOARD_ASOF_MISMATCH)
    if snapshot_bytes is None and snapshot_absence_code is not None:
        codes.append(snapshot_absence_code)
    codes.extend(extra_codes)

    snapshot_usable = (
        snapshot.verified
        and snapshot.asof is not None
        and index.source_board_asof is not None
        and index.source_board_asof == snapshot.asof
    )

    if board.valid and index.accepted and snapshot_usable:
        relation = (
            RELATION_SAME_SOURCE
            if board.sha256 == snapshot.sha256
            else RELATION_SEPARATE_EPOCHS
        )
    else:
        relation = RELATION_UNAVAILABLE

    return {
        "schema": SCHEMA,
        "relation": relation,
        "settlement_status": SETTLEMENT_STATUS,
        "reason_codes": _ordered_codes(codes),
        "current_board": {"sha256": board.sha256, "source_asof": board.asof},
        "index": {
            "sha256": index.raw_sha256,
            "asof": index.asof,
            "source_asof": index.source_asof,
        },
        "origination_board": {
            "sha256": snapshot.sha256,
            "source_asof": snapshot.asof,
            "snapshot_verified": bool(snapshot.verified),
        },
    }


def project_source_epochs(
    *,
    board_bytes: Optional[bytes],
    index_bytes: Optional[bytes],
    snapshot_bytes: Optional[bytes],
) -> Dict[str, Any]:
    """Project the source-epoch relation from three raw byte blobs.

    ``snapshot_bytes`` are the exact *decompressed* bytes of the frozen raw
    board.  This function performs no I/O and is fully deterministic.
    """
    return _project(
        board_bytes=_as_bytes(board_bytes, "board_bytes"),
        index_bytes=_as_bytes(index_bytes, "index_bytes"),
        snapshot_bytes=_as_bytes(snapshot_bytes, "snapshot_bytes"),
        extra_codes=(),
        snapshot_absence_code=REASON_SNAPSHOT_MISSING,
    )


# ---------------------------------------------------------------------------
# File-bound reader
# ---------------------------------------------------------------------------


def _load_snapshot(
    data_dir: pathlib.Path, declared_sha: str
) -> Tuple[Optional[bytes], Optional[str]]:
    """Open the canonical snapshot once, without following child symlinks.

    Descriptor-relative directory traversal pins the existing data root.
    The gzip probe and decompression consume one open file, so a path replacement
    cannot switch the source between a successful probe and the digest check.
    """
    try:
        root = pathlib.Path(data_dir).resolve(strict=True)
        if not root.is_dir():
            return None, REASON_DATA_DIR_UNAVAILABLE
    except (OSError, RuntimeError, ValueError):
        return None, REASON_DATA_DIR_UNAVAILABLE

    try:
        with ExitStack() as stack:
            directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            directory = os.open(root, directory_flags)
            stack.callback(os.close, directory)
            for part in _SNAPSHOT_RELATIVE_DIR:
                directory = os.open(part, directory_flags, dir_fd=directory)
                stack.callback(os.close, directory)
            descriptor = os.open(
                "%s.json.gz" % declared_sha,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
            stack.callback(os.close, descriptor)
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                return None, REASON_SNAPSHOT_FILE_UNREADABLE
            raw = stack.enter_context(os.fdopen(descriptor, "rb", closefd=False))
            if raw.read(2) != b"\x1f\x8b":
                return None, REASON_SNAPSHOT_DECOMPRESS_FAILED
            raw.seek(0)
            with gzip.GzipFile(fileobj=raw, mode="rb") as handle:
                payload = handle.read(MAX_SNAPSHOT_BYTES + 1)
    except FileNotFoundError:
        return None, REASON_SNAPSHOT_FILE_MISSING
    except (gzip.BadGzipFile, EOFError, zlib.error):
        return None, REASON_SNAPSHOT_DECOMPRESS_FAILED
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            return None, REASON_SNAPSHOT_PATH_ESCAPE
        return None, REASON_SNAPSHOT_FILE_UNREADABLE
    if len(payload) > MAX_SNAPSHOT_BYTES:
        return None, REASON_SNAPSHOT_TOO_LARGE
    return payload, None


def read_source_epochs(
    *,
    board_bytes: Optional[bytes],
    index_bytes: Optional[bytes],
    data_dir: pathlib.Path,
) -> Dict[str, Any]:
    """Read the canonical frozen snapshot and project the source-epoch relation.

    The index binding is validated first; a file is read only when
    ``source_board_sha256`` is a strict lowercase 64-hex digest,
    ``source_board_snapshot_path`` is exactly
    ``data/prophet/origination_sources/<sha>.json.gz`` and
    ``source_board_snapshot_encoding`` is exactly ``gzip``.  Anything else
    fails closed without touching the filesystem.
    """
    board = _as_bytes(board_bytes, "board_bytes")
    index = _as_bytes(index_bytes, "index_bytes")

    facts = _analyze_index(index)
    snapshot: Optional[bytes] = None
    extra_codes: List[str] = []
    absence_code: Optional[str] = REASON_SNAPSHOT_MISSING

    if not facts.accepted:
        # No accepted binding -> no file is read at all.
        extra_codes.append(REASON_SNAPSHOT_NOT_READ)
        absence_code = None
    else:
        snapshot, failure = _load_snapshot(
            pathlib.Path(data_dir), facts.declared_board_sha256)
        if failure is not None:
            extra_codes.append(failure)
            absence_code = None

    return _project(
        board_bytes=board,
        index_bytes=index,
        snapshot_bytes=snapshot,
        extra_codes=tuple(extra_codes),
        snapshot_absence_code=absence_code,
    )
