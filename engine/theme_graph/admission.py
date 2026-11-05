"""Private-root admission classifier for theme-research evidence (T03).

Given a candidate evidence root, decide — as pure path logic plus one read of the
candidate's own ``evidence.parquet`` — whether that root may be bound as PRIVATE
evidence or must be refused, and say why in one status. The classifier owns no
custody: no store, no writer, no lane gate, and deliberately NO environment
override (the store's ``COLLECT_LANE`` lesson generalized — a trust decision that
can be flipped by an env var is not a trust decision). Callers pass the roots they
assert are public and the columns their evidence contract requires; everything else
follows from the filesystem.

Statuses, evaluated in order, first match wins:
``missing`` → ``public_root`` → ``symlink_to_public`` → ``no_parquet`` →
``unreadable`` → ``missing_column`` → ``empty_private`` → ``private_ok``
(``no_parquet`` and ``unreadable`` are mutually exclusive — an absent file is never
attempted as a read — so the file-presence check precedes the read).

Known classification edge (review nit, carrier #7870): a root that IS a declared
public root but is passed through a platform symlink (macOS ``/var`` →
``/private/var``) while the public root was passed already resolved is reported as
``symlink_to_public`` rather than ``public_root``. Both are refusals; there is no
permissive escape when the resolved root lies inside a resolved public root.

The two public refusals are deliberately separate: a root that sits inside a public
tree by PATH is a different mistake from a root that only ARRIVES there through a
symlink, and collapsing them would hide the traversal from whoever audits the
binding.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import pandas as pd

#: The evidence file name, mirroring ``store.evidence_path()``. store.py keeps the
#: literal inline in that function, and importing the store here would drag the lane
#: gate and repo config into a module that must stay pure — so the name is restated,
#: with this comment as the tie that binds them.
EVIDENCE_FILENAME = "evidence.parquet"

__all__ = ["EVIDENCE_FILENAME", "classify_private_evidence_root"]


def _inside(child: Path, parent: Path) -> bool:
    """``child`` equals or lives under ``parent``."""
    return child == parent or child.is_relative_to(parent)


def _is_public(candidate: Path, public_roots: Sequence[tuple[Path, Path]]) -> bool:
    """``candidate`` equals-or-inside any public root, compared both lexically and
    symlink-resolved so a caller's own symlinked public root still matches."""
    return any(_inside(candidate, lexical) or _inside(candidate, resolved)
               for lexical, resolved in public_roots)


def classify_private_evidence_root(root: str | Path, *,
                                   public_roots: Sequence[str | Path],
                                   required_columns: Sequence[str]) -> dict:
    """Classify ``root`` for private-evidence binding; never raises for a state it
    can name. Returns ``{"status", "reason", "root"}`` with ``root`` the resolved
    root path as a string.
    """
    root_path = Path(root)
    unresolved = Path(os.path.abspath(str(root_path)))
    resolved_root = str(root_path.resolve())
    public = [(Path(os.path.abspath(str(p))), Path(str(p)).resolve())
              for p in (public_roots or [])]

    if not root_path.exists():
        return {"status": "missing", "reason": "root does not exist",
                "root": resolved_root}

    if _is_public(unresolved, public):
        return {"status": "public_root",
                "reason": "root is inside a declared public root",
                "root": resolved_root}

    try:
        resolved = root_path.resolve(strict=True)
    except OSError:  # a dangling traversal cannot be followed; treat as the path given
        resolved = unresolved
    if (str(resolved) != str(unresolved) and _is_public(resolved, public)):
        return {"status": "symlink_to_public",
                "reason": "root traverses a symlink into a declared public root",
                "root": resolved_root}

    evidence = unresolved / EVIDENCE_FILENAME
    if not evidence.is_file():
        return {"status": "no_parquet",
                "reason": f"no {EVIDENCE_FILENAME} under root",
                "root": resolved_root}
    try:
        frame = pd.read_parquet(evidence)
    except Exception as exc:  # noqa: BLE001 — unreadable evidence is a named state, not a crash
        return {"status": "unreadable",
                "reason": f"evidence parquet unreadable ({type(exc).__name__})",
                "root": resolved_root}
    absent = [str(col) for col in (required_columns or [])
              if str(col) not in frame.columns]
    if absent:
        return {"status": "missing_column",
                "reason": f"missing required column(s): {', '.join(absent[:3])}"
                          + ("…" if len(absent) > 3 else ""),
                "root": resolved_root}
    if len(frame) == 0:
        return {"status": "empty_private",
                "reason": "evidence parquet has zero rows",
                "root": resolved_root}
    return {"status": "private_ok",
            "reason": "private evidence root admitted",
            "root": resolved_root}
