"""One logical US board snapshots ledger over a frozen base file and bounded parts.

``data/us_board_ledger/snapshots.jsonl`` is the append-only PIT fire log of the
published US board: one JSON object per line, appended by
``scripts/grade_us_board.py``. It is close to GitHub's 100 MiB per-blob limit
(88,488,651 B on 2026-10-16, about 2.5 MB per nightly row), so from the
rollover on its bytes are an immutable prefix and new rows go to contiguous
``snapshots_parts/part-NNNNNN.jsonl`` files of at most ``PART_MAX_BYTES``.

Readers see the base file and then each part, in that order, as one logical
stream. Nothing is rotated away or truncated, so no reader loses a row. The
layout mirrors ``outcomes_session_parts`` (``engine/options_signal_episode.py``).

Every function takes the BASE path (``.../snapshots.jsonl``) and finds the
parts directory beside it, so path overrides (tests, vintage trees, a
``--snapshots`` flag) keep working unchanged.
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

PARTS_DIRNAME = "snapshots_parts"
PART_MAX_BYTES = 48 * 1024 * 1024
_PART_RE = re.compile(r"^part-(\d{6})\.jsonl$")


class SnapshotLedgerError(ValueError):
    """The files cannot be read as one ledger without losing or merging rows."""


def parts_dir(base: Path | str) -> Path:
    """The directory that holds this ledger's parts (it may not exist)."""
    return Path(base).parent / PARTS_DIRNAME


def part_paths(base: Path | str) -> list[Path]:
    """The parts in order. Numbering must run part-000001, part-000002, ... with no gap.

    Hidden files (a Finder ``.DS_Store``) are not parts and are skipped; any other
    name in the directory is refused, because a reader cannot tell whether it holds rows.
    """
    d = parts_dir(base)
    if d.is_symlink():
        raise SnapshotLedgerError(f"snapshot parts directory is a symlink: {d}")
    if not d.exists():
        return []
    if not d.is_dir():
        raise SnapshotLedgerError(f"snapshot parts path is not a directory: {d}")
    indexed: list[tuple[int, Path]] = []
    for entry in d.iterdir():
        if entry.name.startswith("."):
            continue
        match = _PART_RE.fullmatch(entry.name)
        if match is None:
            raise SnapshotLedgerError(f"unexpected file in snapshot parts: {entry}")
        if entry.is_symlink() or not entry.is_file():
            raise SnapshotLedgerError(f"snapshot part is not a regular file: {entry}")
        indexed.append((int(match.group(1)), entry))
    indexed.sort()
    if [n for n, _ in indexed] != list(range(1, len(indexed) + 1)):
        raise SnapshotLedgerError(
            "snapshot part numbering is not contiguous from part-000001: "
            + ", ".join(p.name for _, p in indexed))
    return [p for _, p in indexed]


def physical_paths(base: Path | str) -> list[Path]:
    """``[base, part-000001, ...]``; empty when there is no ledger at all.

    Parts without the base file are refused: the base holds every row before the
    rollover, so reading the parts alone would silently drop history.
    """
    base = Path(base)
    parts = part_paths(base)
    if not base.exists():
        if parts:
            raise SnapshotLedgerError(f"snapshot parts exist without the base file {base}")
        return []
    if not base.is_file():
        raise SnapshotLedgerError(f"snapshot base is not a file: {base}")
    return [base, *parts]


def exists(base: Path | str) -> bool:
    """True when the ledger has a base file (with or without parts)."""
    return bool(physical_paths(base))


def _ends_clean(path: Path) -> bool:
    size = path.stat().st_size
    if size == 0:
        return True
    with open(path, "rb") as fh:
        fh.seek(size - 1)
        return fh.read(1) == b"\n"


def _checked_paths(base: Path | str) -> list[Path]:
    paths = physical_paths(base)
    for p in paths[:-1]:
        if not _ends_clean(p):
            raise SnapshotLedgerError(
                f"{p} does not end with a newline, so its last row would merge with the "
                f"first row of the next file")
    return paths


def iter_lines(base: Path | str) -> Iterator[str]:
    """Every line of the ledger in order, newline kept, as ``for line in fh`` yields them.

    Streams one line at a time (never the whole ledger in memory). Every file
    except the last must end with a newline; the last may end torn, exactly as
    a single file could before the rollover.
    """
    for p in _checked_paths(base):
        with open(p, encoding="utf-8") as fh:
            yield from fh


def read_text(base: Path | str) -> str:
    """The whole ledger as one string (base then parts), ``""`` when there is none."""
    return "".join(p.read_text(encoding="utf-8") for p in _checked_paths(base))


def read_lines(base: Path | str) -> list[str]:
    """``base.read_text().splitlines()`` over the whole ledger, parts included."""
    return read_text(base).splitlines()


def append_line(base: Path | str, line: str, *, max_bytes: int = PART_MAX_BYTES) -> Path:
    """Append one row and return the file that took it.

    ``line`` is one JSON object with no newline inside (a trailing one is
    allowed). The base file takes the row only while no part exists and it stays
    within ``max_bytes``; otherwise the last part takes it while that part stays
    within ``max_bytes``, else a new part with the next number. Existing bytes
    are never rewritten or truncated. A file that ends without a newline is
    never appended to or followed by a new part, because the row would merge.
    """
    base = Path(base)
    row = line[:-1] if line.endswith("\n") else line
    if "\n" in row or "\r" in row:
        raise SnapshotLedgerError("a snapshot row must be a single line")
    data = (row + "\n").encode("utf-8")
    if len(data) > max_bytes:
        raise SnapshotLedgerError(
            f"one snapshot row is {len(data)} bytes, over the {max_bytes}-byte part ceiling")
    paths = _checked_paths(base)
    if paths and not _ends_clean(paths[-1]):
        raise SnapshotLedgerError(f"refusing to append after a torn final line in {paths[-1]}")
    parts = paths[1:]
    if not paths:
        target = base
    elif not parts and base.stat().st_size + len(data) <= max_bytes:
        target = base
    elif parts and parts[-1].stat().st_size + len(data) <= max_bytes:
        target = parts[-1]
    else:
        target = parts_dir(base) / f"part-{len(parts) + 1:06d}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "ab") as fh:
        fh.write(data)
    return target
