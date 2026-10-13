"""Canonical on-disk form for the immutable source-manifest ledger.

A manifest ID commits to the record's own canonical body, so the stored form
must be a function of that record alone.  Parquet cannot provide that.  pyarrow
unifies nested struct schemas across every row at write time, so a single new
row introducing a nested key that no existing row carries back-fills that key as
null into *all* pre-existing rows.  Their bodies then hash differently and the
IDs they were written with stop matching.

That is not a hypothetical.  ``filing.file_number_provenance`` and
``filing.collection_scope`` (added by #4243, after the last ledger commit)
invalidated all 1258 retained rows on the next read, which is what failed
``scripts.compile_capital_structure_events`` every night from 2026-08-05.  The
drifted file is never committed, so each night restored the clean ledger,
re-drifted it identically, and failed again -- deterministic, not flaky.

JSON Lines stores each record independently: one canonical JSON object per
line, no cross-row schema to unify.  The bytes on disk are exactly the canonical
body the ID commits to, so identity survives any future schema growth without a
migration or an ID re-pin.

Sharding (DEC:CS-V2-SOURCE-LEDGER-SHARDS-BYTE-EXACTLY)
-------------------------------------------------------
The ledger is append-only and git-retained, and GitHub refuses any blob over
100 MiB.  ``source_manifest.jsonl`` reached 97.6 MiB on 2026-09-26 and every
nightly from 2026-09-27 compiled a generation and lost it at push (``GH001``),
silently at first and terminally from 2026-10-09.  Rewriting or compacting the
file is forbidden by the append-only evidence law (``jsonl_prefix`` in
``config/append_only_artifacts.json``), and Git LFS is forbidden fleet-wide, so
the ledger is sharded *byte-exactly* instead:

* ``source_manifest.jsonl`` is part 1 and is never rewritten once it is sealed.
* Continuation parts ``source_manifest.part-NNNN.jsonl`` (``NNNN`` zero-padded,
  contiguous from ``0002``) hold the bytes that follow.
* The LOGICAL ledger is the ordered byte concatenation of every part; every
  reader in this module decodes that concatenation, so compilers, the
  companyfacts anchor reader and the nightly handoff receipt all see one ledger.
* A part is *sealed* once it holds at least ``SOURCE_LEDGER_PART_ROLL_BYTES``;
  a sealed part must be a byte prefix of the new body at its running offset or
  the write is refused.  Only the last (active) part may be rewritten, which is
  exactly the single-file overwrite semantics every existing caller relies on.
* Parts split on line boundaries only, so each part is itself a valid,
  newline-terminated JSON Lines file.
* ``source_manifest.part-NNNN.tmp.jsonl`` is the atomic-write scratch name and
  never matches ``SOURCE_LEDGER_PART_PATTERN``.

Nothing about record identity changes: a record's bytes are the same whether
they sit in part 1 or part 7, and ``source_ledger_prefix_hash`` over the decoded
records is unaffected by where a part boundary falls.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

from .source_identity import (
    ManifestIdentityError,
    canonical_manifest_bytes,
    validate_manifest_ledger,
)


SOURCE_LEDGER_FILENAME = "source_manifest.jsonl"
LEGACY_SOURCE_LEDGER_FILENAME = "source_manifest.parquet"

#: Continuation-part filenames: ``source_manifest.part-0002.jsonl`` and up.
SOURCE_LEDGER_PART_PATTERN = re.compile(r"^source_manifest\.part-(\d{4})\.jsonl$")
SOURCE_LEDGER_PART_TEMPLATE = "source_manifest.part-{index:04d}.jsonl"
#: Part 1 is ``SOURCE_LEDGER_FILENAME``; the first continuation part is 0002.
SOURCE_LEDGER_FIRST_CONTINUATION_PART = 2
#: A part holding at least this many bytes is sealed and never rewritten.  Well
#: under GitHub's 100 MiB blob limit even after one more line is appended, and
#: large enough that the ledger's ~2.5 MB/night growth opens a new part every
#: ~20 nights rather than every night.
SOURCE_LEDGER_PART_ROLL_BYTES = 48 * 1024 * 1024


def source_ledger_path(root: Path) -> Path:
    """Return the canonical ledger path (part 1) inside a capital-structure data root."""
    return Path(root) / SOURCE_LEDGER_FILENAME


def source_ledger_part_name(index: int) -> str:
    """Filename of continuation part ``index`` (``index >= 2``)."""
    if index < SOURCE_LEDGER_FIRST_CONTINUATION_PART:
        raise ValueError(
            f"continuation parts start at {SOURCE_LEDGER_FIRST_CONTINUATION_PART}, got {index}"
        )
    return SOURCE_LEDGER_PART_TEMPLATE.format(index=index)


def source_ledger_part_names(names: Iterable[str]) -> list[str]:
    """Return the continuation-part filenames among ``names``, in ledger order.

    Pure: takes any iterable of basenames (a directory listing, a git tree
    listing reduced to basenames, a fixture).  Fails closed: a gap in the
    numbering, a duplicate, or a part numbered below the first continuation
    index is a corrupt ledger, never a set of parts to skip or reorder around.
    """
    indexed: dict[int, str] = {}
    for name in names:
        match = SOURCE_LEDGER_PART_PATTERN.match(str(name))
        if match is None:
            continue
        index = int(match.group(1))
        if index < SOURCE_LEDGER_FIRST_CONTINUATION_PART:
            raise ManifestIdentityError(
                f"source ledger part {name!r} is numbered below the first continuation "
                f"part ({SOURCE_LEDGER_FIRST_CONTINUATION_PART:04d})"
            )
        if index in indexed:
            raise ManifestIdentityError(
                f"source ledger part index {index:04d} appears twice: "
                f"{indexed[index]!r} and {name!r}"
            )
        indexed[index] = str(name)
    ordered: list[str] = []
    expected = SOURCE_LEDGER_FIRST_CONTINUATION_PART
    for index in sorted(indexed):
        if index != expected:
            raise ManifestIdentityError(
                f"source ledger parts are not contiguous: expected part {expected:04d} "
                f"before {indexed[index]!r}"
            )
        ordered.append(indexed[index])
        expected += 1
    return ordered


def source_ledger_part_paths(path: Path) -> tuple[Path, ...]:
    """Every on-disk part of the ledger whose part 1 is ``path``, in ledger order.

    Part 1 is always first even when it does not exist yet (a fresh root).
    Continuation parts are discovered from the directory listing.  Continuation
    parts without a part 1 are a corrupt ledger and raise.
    """
    path = Path(path)
    try:
        names = os.listdir(path.parent)
    except FileNotFoundError:
        return (path,)
    except OSError as exc:
        raise ManifestIdentityError(
            f"source ledger directory unreadable: {path.parent}: {exc}"
        ) from exc
    parts = source_ledger_part_names(names)
    if parts and not path.exists():
        raise ManifestIdentityError(
            f"source ledger {path} is absent but continuation parts exist: "
            + ", ".join(parts)
        )
    return (path, *(path.with_name(name) for name in parts))


def encode_source_ledger(records: Sequence[Mapping[str, Any]]) -> bytes:
    """Return canonical JSON Lines bytes, one full record per line.

    Deliberately does not validate: callers that build fixtures need to write
    ledgers this repository's identity law rejects.  ``write_source_ledger`` is
    the validating boundary.
    """
    if isinstance(records, (str, bytes, Mapping)):
        raise TypeError("source ledger records must be a sequence of mappings")
    lines = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            raise TypeError(f"source ledger row {index}: record must be a mapping")
        lines.append(canonical_manifest_bytes(record))
    return b"".join(line + b"\n" for line in lines)


def decode_source_ledger(body: bytes, *, label: str) -> list[dict[str, Any]]:
    """Parse canonical JSON Lines bytes into full manifest records.

    Strict by construction: a blank line, a trailing partial line, or a non-object
    line is a corrupt ledger, never a row to skip.
    """
    if not isinstance(body, (bytes, bytearray)):
        raise TypeError("source ledger body must be bytes")
    text = bytes(body).decode("utf-8")
    if not text:
        return []
    if not text.endswith("\n"):
        raise ManifestIdentityError(
            f"source ledger {label}: final row is not newline-terminated"
        )
    records: list[dict[str, Any]] = []
    for index, line in enumerate(text[:-1].split("\n")):
        if not line.strip():
            raise ManifestIdentityError(f"source ledger {label} row {index}: blank line")
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ManifestIdentityError(
                f"source ledger {label} row {index}: unreadable JSON: {exc}"
            ) from exc
        if not isinstance(record, dict):
            raise ManifestIdentityError(
                f"source ledger {label} row {index}: record must be a JSON object"
            )
        records.append(record)
    return records


def _read_part(part: Path) -> bytes:
    try:
        return part.read_bytes()
    except OSError as exc:
        raise ManifestIdentityError(f"source ledger unreadable: {part}: {exc}") from exc


def read_source_ledger_parts(path: Path) -> list[tuple[Path, bytes]]:
    """Return ``(part_path, bytes)`` for every on-disk part, in ledger order.

    ``[]`` when no ledger is retained.  A leftover parquet ledger is a hard error
    rather than a silent empty read: that file holds real retained provenance,
    and treating it as absent would drop the whole immutable prefix.
    """
    path = Path(path)
    parts = source_ledger_part_paths(path)
    if not path.exists():
        legacy = path.parent / LEGACY_SOURCE_LEDGER_FILENAME
        if legacy.exists():
            raise ManifestIdentityError(
                f"source ledger {legacy} is the superseded parquet form; migrate it to "
                f"{SOURCE_LEDGER_FILENAME} (scripts/migrate_source_manifest_to_jsonl.py)"
            )
        return []
    return [(part, _read_part(part)) for part in parts]


def read_source_ledger_body(path: Path) -> bytes:
    """The logical ledger: the ordered byte concatenation of every part."""
    return b"".join(body for _part, body in read_source_ledger_parts(path))


def read_source_ledger(path: Path) -> list[dict[str, Any]]:
    """Return every retained manifest record across all parts, or ``[]``.

    Each part is decoded under its own label so a corrupt row names the file
    that holds it.
    """
    records: list[dict[str, Any]] = []
    for part, body in read_source_ledger_parts(path):
        records.extend(decode_source_ledger(body, label=str(part)))
    return records


def source_ledger_receipt(path: Path) -> dict[str, Any] | None:
    """Byte-level handoff receipt over the LOGICAL ledger, or ``None`` if absent.

    ``rows`` is the newline count and ``sha256`` the digest of the ordered
    concatenation of every part -- exactly ``wc -l`` / ``shasum -a 256`` of the
    single file while no continuation part exists, so a receipt stamped before
    the first roll compares equal to one computed by this function.  Computed
    without decoding on purpose: the receipt proves *which bytes* crossed the
    job boundary, and the compilers that follow are the ones that judge them.
    """
    parts = read_source_ledger_parts(path)
    if not parts:
        return None
    digest = hashlib.sha256()
    rows = 0
    size = 0
    listing: list[dict[str, Any]] = []
    for part, body in parts:
        digest.update(body)
        part_rows = body.count(b"\n")
        rows += part_rows
        size += len(body)
        listing.append(
            {
                "name": part.name,
                "bytes": len(body),
                "rows": part_rows,
                "sha256": hashlib.sha256(body).hexdigest(),
            }
        )
    return {"rows": rows, "bytes": size, "sha256": digest.hexdigest(), "parts": listing}


def _atomic_write(target: Path, body: bytes) -> None:
    tmp = target.with_suffix(".tmp.jsonl")
    tmp.write_bytes(body)
    os.replace(tmp, target)


def _split_line_aligned(body: bytes, roll_bytes: int) -> tuple[bytes, bytes]:
    """Split ``body`` into a sealed-size chunk (>= ``roll_bytes``, ending on a
    newline) and the remainder.  The remainder is empty when ``body`` is not
    long enough to seal a part."""
    if len(body) <= roll_bytes:
        return body, b""
    cut = body.find(b"\n", roll_bytes - 1)
    if cut == -1:
        return body, b""
    return body[: cut + 1], body[cut + 1 :]


def write_source_ledger(
    records: Sequence[Mapping[str, Any]],
    path: Path,
    *,
    validate: bool = True,
    roll_bytes: int | None = None,
) -> None:
    """Atomically persist the ledger across its parts, refusing to rewrite a
    sealed part or a drifted prefix.

    Validation runs at the write boundary on purpose.  The failure this format
    replaces was only ever observable one process later, in the compiler; a
    ledger that cannot be re-read as the IDs it carries must not reach disk.

    Every sealed part (every part but the last on disk, plus the last one when
    it is already full) must be a byte prefix of the new body at its running
    offset.  Only the active part is rewritten; bytes beyond it open new parts,
    split on line boundaries at ``roll_bytes``.
    """
    path = Path(path)
    if roll_bytes is None:
        roll_bytes = SOURCE_LEDGER_PART_ROLL_BYTES
    if roll_bytes <= 0:
        raise ValueError("roll_bytes must be positive")
    if validate:
        validate_manifest_ledger(list(records))
    body = encode_source_ledger(records)
    path.parent.mkdir(parents=True, exist_ok=True)

    existing = [part for part in source_ledger_part_paths(path) if part.exists()]
    offset = 0
    active_index = SOURCE_LEDGER_FIRST_CONTINUATION_PART - 1  # part 1
    active: Path = path
    for position, part in enumerate(existing):
        current = _read_part(part)
        last = position == len(existing) - 1
        matches = body[offset : offset + len(current)] == current
        if last and (not matches or len(current) < roll_bytes):
            # The active part: rewritten below with the bytes from ``offset``.
            active = part
            active_index = position + 1
            break
        if not matches:
            raise ManifestIdentityError(
                f"source ledger {part} is sealed ({len(current)} bytes at offset {offset}) "
                f"and the new body does not extend it byte-for-byte; sealed parts are "
                f"never rewritten"
            )
        offset += len(current)
        active_index = position + 2
        active = path if active_index == 1 else path.with_name(source_ledger_part_name(active_index))

    remaining = body[offset:]
    while True:
        chunk, remaining = _split_line_aligned(remaining, roll_bytes)
        if not chunk and active != path:
            # A continuation part that would be empty: remove it rather than
            # leave an empty shard (part 1 may legitimately be empty).
            if active.exists():
                active.unlink()
            break
        _atomic_write(active, chunk)
        if not remaining:
            break
        active_index += 1
        active = path.with_name(source_ledger_part_name(active_index))

    # Any stale continuation part beyond the last one written is a leftover of a
    # longer earlier body; it cannot be part of this ledger, so drop it.  (Sealed
    # parts are never reached here: they were verified above and left untouched.)
    stale_index = active_index + 1
    while True:
        stale = path.with_name(source_ledger_part_name(stale_index))
        if not stale.exists():
            break
        stale.unlink()
        stale_index += 1
