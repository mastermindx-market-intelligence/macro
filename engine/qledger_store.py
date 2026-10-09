"""Read-only source seam for the existing QLedger claims owner.

This module reads only the explicitly supplied legacy JSONL path. It performs
no discovery, catalog detection, segmented-format interpretation, or writes.
Raw lines are available for later consumers with their own parsing policies;
the legacy decoder below preserves the existing QLedger loader's behavior.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_raw_lines(path: Path) -> list[str]:
    """Return legacy UTF-8 splitlines, preserving order and line whitespace.

    A missing file has no rows. Other I/O and decoding failures propagate,
    including a file disappearing after the existence check. Read the whole
    file before returning, as the existing loader does; never return a partial
    successfully decoded prefix.
    """
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8").splitlines()


def read_legacy_rows(path: Path) -> list[Any]:
    """Apply the existing forgiving JSONL policy without changing row identity.

    Blank or undecodable JSON lines are skipped. Every successfully decoded
    value is retained, including scalars and nulls, unknown fields, and repeated
    occurrences. Registration and downstream callers keep their own policies.
    """
    rows: list[Any] = []
    for line in read_raw_lines(path):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001 — match the existing legacy reader
            continue
    return rows
