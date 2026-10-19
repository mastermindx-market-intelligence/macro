"""Canonical on-disk paths for the capital-structure event spine.

Producer and tests share these resolvers so a tmp_path monkeypatch cannot
silently point the valuation panel at an empty directory while a second
patch still names the compiler's private _data_root.
"""
from __future__ import annotations

from pathlib import Path


def capital_data_root() -> Path:
    """Return the capital-structure data directory (patchable in tests)."""
    from lib import config

    return config.data_dir() / "capital_structure"


def event_versions_path(data_root: Path | str | None = None) -> Path:
    """Return event_versions.parquet under data_root, or the canonical root."""
    root = Path(data_root) if data_root is not None else capital_data_root()
    return root / "event_versions.parquet"


def chronicle_events_path() -> Path:
    """Return Chronicle's events.jsonl, honoring an absolute EVENTS_REL patch."""
    from engine.chronicle import spine as chronicle_spine

    rel = Path(chronicle_spine.EVENTS_REL)
    if rel.is_absolute():
        return rel
    return Path(chronicle_spine.__file__).resolve().parents[2] / rel
