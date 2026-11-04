"""Bounded reader for a retained International Library build.

One successful International analysis is expensive: it consumes the
``intl_search`` inputs and produces the published ``intlstockdata`` /
``intlohlc`` outputs plus the ``site/factordata/intl_setups.json`` standouts document.
When a continuation needs the library but must not analyze again, the trusted
native builder captures a receipt over the retained tree and hands the
continuation the two roots plus that receipt.  This module is the reader for
that hand-off.

What this reader proves
-----------------------
Exactly one thing: the bytes currently on disk under ``data_root`` and
``site_root`` are the bytes the receipt recorded.  Every listed file is read
within a byte cap, hashed, and compared against the receipt; the returned
document is parsed from the very bytes that were hashed, so the caller's
decision is bound to the same content the reader verified.

What this reader does NOT prove
--------------------------------
The receipt is written by the caller, so everything the receipt *claims* about
the world is taken on trust and is not re-established here:

* ``source_head`` is recorded provenance only.  It is checked for shape (exactly
  40 lowercase hex characters) and is never resolved against a Git object, a
  ref, or a signed commit; a caller may put any well-formed value there.
* ``schema`` and ``producer`` are structural assertions.  Nothing here proves
  that ``scripts.build_intl_library.main`` ran, that it ran at ``source_head``,
  or that it emitted these files.
* Provider rights, data licensing, the wall clock, and the freshness of the
  analysis are outside this reader.  It cannot establish any of them and does
  not try.
* The reader never re-analyzes, never repairs and never falls back.  A
  retained tree that does not match its receipt is an error, not a reason to
  recompute.

The reader is read-only.  It opens files ``O_RDONLY`` / ``O_NOFOLLOW``, hashes
them, parses one JSON document and returns it.  It writes nothing, fetches
nothing, executes nothing and creates no store.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import unicodedata
from collections.abc import Mapping
from pathlib import Path

__all__ = [
    "RETAINED_LIBRARY_PRODUCER",
    "RETAINED_LIBRARY_SCHEMA",
    "REQUIRED_DATA_PATHS",
    "REQUIRED_SITE_PATHS",
    "RetainedLibraryError",
    "load_retained_library",
]


RETAINED_LIBRARY_SCHEMA = "intl.library_retained.v1"
RETAINED_LIBRARY_PRODUCER = "scripts.build_intl_library.main"

#: Data-root paths the retained build must carry, relative to ``data_root``.
REQUIRED_DATA_PATHS = (
    "intl_search/closes.parquet",
    "intl_search/members.parquet",
    "intl_search/coverage.parquet",
)

#: Site-root paths the retained build must carry, relative to ``site_root``.
REQUIRED_SITE_PATHS = (
    "intlstockdata/index.json",
    "factordata/intl_setups.json",
)

_RECEIPT_KEYS = frozenset(
    {"schema", "producer", "source_head", "data_files", "site_files"}
)
_SITE_TREES = ("intlstockdata", "intlohlc")
_SETUPS_PATH = "factordata/intl_setups.json"

_MAX_MAP_ENTRIES = 20000
_MAX_FILES = 20000
_MAX_FILE_BYTES = 32 * 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024

_HEX_DIGITS = "0123456789abcdef"


class RetainedLibraryError(ValueError):
    """The retained tree cannot be bound to the receipt it was handed."""


# ── receipt shape ──────────────────────────────────────────────────────────
def _is_hex(value: object, *, length: int) -> bool:
    if not isinstance(value, str) or len(value) != length:
        return False
    return all(char in _HEX_DIGITS for char in value)


def _normalize_relative_path(value: object, *, label: str) -> str:
    """Return the canonical relative POSIX path for ``value`` or raise.

    Only already-canonical paths are accepted: an absolute path, a path with a
    backslash, a path with a control character, and a path carrying an empty,
    ``.`` or ``..`` component are all refused rather than repaired.
    """
    if not isinstance(value, str):
        raise RetainedLibraryError(f"{label}: path must be a string")
    if not value:
        raise RetainedLibraryError(f"{label}: path must not be empty")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in value):
        raise RetainedLibraryError(f"{label}: path contains a control character")
    if "\\" in value:
        raise RetainedLibraryError(f"{label}: path contains a backslash")
    if value.startswith("/"):
        raise RetainedLibraryError(f"{label}: path must be relative")
    if len(value) > 1 and value[1] == ":":
        raise RetainedLibraryError(f"{label}: path must be relative")
    for part in value.split("/"):
        if not part:
            raise RetainedLibraryError(f"{label}: path contains an empty component")
        if part == ".":
            raise RetainedLibraryError(f"{label}: path contains a '.' component")
        if part == "..":
            raise RetainedLibraryError(f"{label}: path contains a '..' component")
    return "/".join(value.split("/"))


def _validate_manifest(value: object, *, label: str) -> dict[str, str]:
    """Return the receipt's path -> sha256 map after checking every entry."""
    if not isinstance(value, Mapping):
        raise RetainedLibraryError(f"{label} must be a mapping")
    if not value:
        raise RetainedLibraryError(f"{label} must not be empty")
    if len(value) > _MAX_MAP_ENTRIES:
        raise RetainedLibraryError(
            f"{label} exceeds the {_MAX_MAP_ENTRIES}-entry cap"
        )
    manifest: dict[str, str] = {}
    folded: dict[str, str] = {}
    for raw_path, raw_digest in value.items():
        path = _normalize_relative_path(raw_path, label=label)
        # Two distinct keys may still denote one normalized path (Unicode
        # composition).  Refuse rather than let one of them shadow the other.
        key = unicodedata.normalize("NFC", path)
        if key in folded:
            raise RetainedLibraryError(
                f"{label}: duplicate normalized path {key!r}"
            )
        folded[key] = path
        if not _is_hex(raw_digest, length=64):
            raise RetainedLibraryError(
                f"{label}: {path} must carry a lowercase 64-hex sha256"
            )
        manifest[path] = raw_digest
    return manifest


def _validate_receipt(receipt: object) -> tuple[dict[str, str], dict[str, str]]:
    """Return the receipt's data/site manifests after checking every field."""
    if not isinstance(receipt, Mapping):
        raise RetainedLibraryError("receipt must be a mapping")
    present = set(receipt)
    missing = sorted(_RECEIPT_KEYS - present)
    if missing:
        raise RetainedLibraryError(
            f"receipt is missing required keys: {', '.join(missing)}"
        )
    extra = sorted(str(key) for key in present - _RECEIPT_KEYS)
    if extra:
        raise RetainedLibraryError(
            f"receipt carries unbound extra keys: {', '.join(extra)}"
        )
    if receipt["schema"] != RETAINED_LIBRARY_SCHEMA:
        raise RetainedLibraryError(
            f"receipt schema must be {RETAINED_LIBRARY_SCHEMA!r}"
        )
    if receipt["producer"] != RETAINED_LIBRARY_PRODUCER:
        raise RetainedLibraryError(
            f"receipt producer must be {RETAINED_LIBRARY_PRODUCER!r}"
        )
    if not _is_hex(receipt["source_head"], length=40):
        raise RetainedLibraryError(
            "receipt source_head must be exactly 40 lowercase hex characters"
        )
    data_files = _validate_manifest(receipt["data_files"], label="receipt data_files")
    site_files = _validate_manifest(receipt["site_files"], label="receipt site_files")
    return data_files, site_files


def _check_canonical_site_paths(manifest: Mapping[str, str]) -> None:
    """Refuse any site path outside the canonical library outputs."""
    for path in manifest:
        if path == _SETUPS_PATH:
            continue
        if any(path.startswith(f"{tree}/") for tree in _SITE_TREES):
            continue
        raise RetainedLibraryError(
            f"site_files may only list canonical library paths: {path}"
        )


# ── filesystem inventory ───────────────────────────────────────────────────
def _inventory_tree(root: Path, *, label: str, path_prefix: str = "") -> dict[str, Path]:
    """Return every regular file under ``root`` keyed by relative POSIX path.

    Symlinks are refused rather than resolved, so an inventory can never
    reach outside the tree it was asked about.
    """
    found: dict[str, Path] = {}
    pending: list[tuple[Path, str]] = [(root, "")]
    while pending:
        directory, prefix = pending.pop()
        try:
            with os.scandir(directory) as scan:
                entries = sorted(scan, key=lambda entry: entry.name)
        except OSError as exc:
            raise RetainedLibraryError(
                f"{label}: cannot list {directory}: {exc}"
            ) from exc
        for entry in entries:
            relative = f"{prefix}{entry.name}"
            _normalize_relative_path(relative, label=label)
            try:
                if entry.is_symlink():
                    raise RetainedLibraryError(
                        f"{label}: symlink is not allowed: {relative}"
                    )
                if entry.is_dir(follow_symlinks=False):
                    pending.append((Path(entry.path), relative + "/"))
                    continue
                if not entry.is_file(follow_symlinks=False):
                    # Sockets, fifos and devices are not regular files and so
                    # are not part of the regular-file inventory.
                    continue
            except OSError as exc:
                raise RetainedLibraryError(
                    f"{label}: cannot inspect {relative}: {exc}"
                ) from exc
            found[relative] = Path(entry.path)
            if len(found) > _MAX_FILES:
                raise RetainedLibraryError(
                    f"{label} exceeds the {_MAX_FILES}-file cap"
                )
    return {f"{path_prefix}{path}": full for path, full in found.items()}


def _require_plain_directory(path: Path, *, label: str) -> None:
    """Require ``path`` to be a real directory that is not a symlink."""
    try:
        link_stat = os.lstat(path)
    except OSError as exc:
        raise RetainedLibraryError(f"{label}: cannot stat {path}: {exc}") from exc
    if stat.S_ISLNK(link_stat.st_mode):
        raise RetainedLibraryError(f"{label}: {path} is a symlink")
    if not stat.S_ISDIR(link_stat.st_mode):
        raise RetainedLibraryError(f"{label}: {path} is not a directory")


def _site_inventory(site_root: Path) -> dict[str, Path]:
    """Return the canonical site outputs published by the retained build."""
    found: dict[str, Path] = {}
    for tree in _SITE_TREES:
        directory = site_root / tree
        _require_plain_directory(directory, label=f"site_root/{tree}")
        found.update(
            _inventory_tree(
                directory, label=f"site_root/{tree}", path_prefix=f"{tree}/"
            )
        )
    factordata = site_root / "factordata"
    _require_plain_directory(factordata, label="site_root/factordata")
    setups = factordata / "intl_setups.json"
    try:
        link_stat = os.lstat(setups)
    except OSError as exc:
        raise RetainedLibraryError(
            f"site_root/{_SETUPS_PATH}: cannot stat {setups}: {exc}"
        ) from exc
    if stat.S_ISLNK(link_stat.st_mode):
        raise RetainedLibraryError(f"site_root/{_SETUPS_PATH} is a symlink")
    if not stat.S_ISREG(link_stat.st_mode):
        raise RetainedLibraryError(
            f"site_root/{_SETUPS_PATH} is not a regular file"
        )
    found[_SETUPS_PATH] = setups
    return found


# ── byte-bound reads ───────────────────────────────────────────────────────
def _read_bounded(fd: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit
    while remaining:
        chunk = os.read(fd, min(_READ_CHUNK_BYTES, remaining))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_stable_once(path: Path, *, limit: int, label: str) -> tuple[str, bytes]:
    """Return the sha256 hex and the exact bytes of one regular file."""
    try:
        link_stat = os.lstat(path)
    except OSError as exc:
        raise RetainedLibraryError(f"{label}: cannot stat {path}: {exc}") from exc
    if stat.S_ISLNK(link_stat.st_mode):
        raise RetainedLibraryError(f"{label}: {path} is a symlink")
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise RetainedLibraryError(f"{label}: cannot open {path}: {exc}") from exc
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise RetainedLibraryError(f"{label}: {path} is not a regular file")
        if before.st_size > limit:
            raise RetainedLibraryError(
                f"{label}: {path} exceeds its {limit}-byte limit"
            )
        payload = _read_bounded(fd, limit)
        after = os.fstat(fd)
        stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
        if tuple(getattr(before, field) for field in stable_fields) != tuple(
            getattr(after, field) for field in stable_fields
        ):
            raise RetainedLibraryError(
                f"{label}: {path} changed while it was being read"
            )
        if len(payload) != before.st_size:
            raise RetainedLibraryError(f"{label}: {path} was not read completely")
    finally:
        os.close(fd)
    final = os.lstat(path)
    if (final.st_dev, final.st_ino) != (before.st_dev, before.st_ino):
        raise RetainedLibraryError(f"{label}: {path} was replaced while it was read")
    if final.st_mode != before.st_mode:
        raise RetainedLibraryError(f"{label}: {path} changed mode while it was read")
    return hashlib.sha256(payload).hexdigest(), payload


def _verify_tree(
    manifest: Mapping[str, str],
    inventory: Mapping[str, Path],
    *,
    label: str,
) -> dict[str, bytes]:
    """Bind every listed file to its receipt hash; return captured payloads."""
    listed = set(manifest)
    present = set(inventory)
    for path in sorted(present - listed):
        raise RetainedLibraryError(
            f"{label}: file is present but not listed in the receipt: {path}"
        )
    for path in sorted(listed - present):
        raise RetainedLibraryError(
            f"{label}: receipt lists a file that is not present: {path}"
        )
    payloads: dict[str, bytes] = {}
    for path in sorted(listed):
        digest, payload = _read_stable_once(
            inventory[path], limit=_MAX_FILE_BYTES, label=f"{label}: {path}"
        )
        if digest != manifest[path]:
            raise RetainedLibraryError(f"{label}: sha256 mismatch for {path}")
        if path == _SETUPS_PATH:
            payloads[path] = payload
    return payloads


def _parse_setups(payload: bytes) -> dict[str, object]:
    """Decode the retained standouts document from its verified bytes."""
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RetainedLibraryError(
            f"site_root/{_SETUPS_PATH} is not valid UTF-8"
        ) from exc
    try:
        document = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except ValueError as exc:
        raise RetainedLibraryError(
            f"site_root/{_SETUPS_PATH} is not valid JSON"
        ) from exc
    if not isinstance(document, dict):
        raise RetainedLibraryError(
            f"site_root/{_SETUPS_PATH} must decode to an object"
        )
    return document


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


# ── public entry point ─────────────────────────────────────────────────────
def _local_root(value: Path | str, *, label: str) -> Path:
    """Return ``value`` as a local path, refusing a URL-shaped root."""
    if isinstance(value, str) and "://" in value:
        raise RetainedLibraryError(
            f"{label} must be a local path, never a URL or API parameter"
        )
    text = os.fspath(value)
    if not text:
        raise RetainedLibraryError(f"{label} must not be empty")
    return Path(text)


def load_retained_library(
    *,
    data_root: Path | str,
    site_root: Path | str,
    receipt: Mapping[str, object],
) -> dict[str, object]:
    """Return the retained standouts document bound to ``receipt``.

    ``data_root`` and ``site_root`` are the roots the trusted native builder
    retained; they are never taken from a URL or an API parameter.  The
    returned document is the parsed ``site/factordata/intl_setups.json``, read
    from the bytes whose sha256 the receipt recorded.  An empty setup document
    is returned as-is when the original producer emitted one.

    Raises :class:`RetainedLibraryError` when the receipt is malformed, when
    the retained tree does not match it, or when the setup document cannot be
    decoded.  The reader never repairs, re-analyzes or falls back.
    """
    data_files, site_files = _validate_receipt(receipt)
    _check_canonical_site_paths(site_files)
    for required in REQUIRED_DATA_PATHS:
        if required not in data_files:
            raise RetainedLibraryError(
                f"receipt data_files is missing required path: {required}"
            )
    for required in REQUIRED_SITE_PATHS:
        if required not in site_files:
            raise RetainedLibraryError(
                f"receipt site_files is missing required path: {required}"
            )

    data_base = _local_root(data_root, label="data_root")
    site_base = _local_root(site_root, label="site_root")
    _require_plain_directory(data_base, label="data_root")
    _require_plain_directory(site_base, label="site_root")
    data_inventory = _inventory_tree(data_base, label="data_root")
    site_inventory = _site_inventory(site_base)

    _verify_tree(data_files, data_inventory, label="data_root")
    payloads = _verify_tree(site_files, site_inventory, label="site_root")
    return _parse_setups(payloads[_SETUPS_PATH])
