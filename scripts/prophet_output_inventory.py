"""Importable form of the incumbent Prophet build-owned output inventory.

This module is the SAME closed allowlist, digest and snapshot closure that the
two extracted-verbatim Python heredocs inside
``scripts/ci/daily_engine_prophet_nightly.sh`` embed inline (that file is the
workflow step body pinned by ``tests/test_prophet_durable_checkpoint.py``, so
its literals cannot be replaced by an import without breaking the verbatim
extraction contract). It exists so the V4-A2 issuer-side settlement preflight
(``scripts/prophet_settlement_preflight.py``) can re-derive the authoritative
FULL population inventory from live bytes through the incumbent owner's exact
path definitions instead of declaring a second, drift-prone copy.

This is a reading helper only. It owns no writer, no store, no publisher and no
hash registry: every hash it returns is recomputed from the bytes that exist at
call time, and nothing is persisted here.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

__all__ = [
    "EXACT_PATHS",
    "DIRECTORY_GLOBS",
    "CANDIDATE_STORE_DIR",
    "BOARD_REL",
    "INDEX_REL",
    "digest",
    "snapshot",
    "candidate_store_entries",
    "store_sha256",
    "canonical_json",
]

# Build-owned publication paths, exactly as in the nightly step's two heredocs.
# Correction ledgers are INPUTS, never outputs, and stay deliberately absent.
EXACT_PATHS = (
    "site/prophet/index.json",
    "site/prophet/showcase.json",
    # G-D board read: the ticker-keyed spark bodies that
    # index.json plans[].board_read.fields.spark reference. Build-owned
    # like showcase.json; without this entry the artifact is
    # runner-local and the references resolve to nothing on main.
    "site/prophet/board_read_sparks.json",
    "data/prophet/ledger.jsonl",
    "data/prophet/ledger_quarantine.json",
    "data/prophet_arena/scoreboard.json",
    "data/prophet_arena/price_basis_trigger_v2/C0_champion_mirror.jsonl",
    "data/prophet_arena/price_basis_trigger_v2/C1_buy_soon_first.jsonl",
    "data/prophet_arena/price_basis_trigger_v2/C3_door_w_union.jsonl",
    "data/prophet_arena/price_basis_trigger_v2/C4_dispersion_cap.jsonl",
    "data/prophet_arena/price_basis_trigger_v2/C5_align2_gate.jsonl",
    "data/prophet_arena/price_basis_trigger_v2/C6_time_stop_21.jsonl",
    "data/prophet_arena/price_basis_trigger_v2/C7_buy_soon_admitted.jsonl",
)

# Globbed build-owned directories, exactly as in the nightly step's heredocs.
DIRECTORY_GLOBS = {
    "site/prophet/plans": "*.json",
    "site/prophet/states": "*.json",
    "data/prophet/origination_receipts": "*.json",
    "data/prophet/origination_sources": "*.json.gz",
    # §6.5 legacy shadow: month-grouped DAY parts
    # (legacy_shadow/YYYY-MM/YYYY-MM-DD.parquet). Build-owned and
    # append-only like the receipts; without this the accrual store
    # is runner-local and dies with the runner.
    "data/prophet/legacy_shadow": "*/*.parquet",
}

CANDIDATE_STORE_DIR = "site/prophet/plans"

# The frozen origination source board and the final producer index, exactly as
# bound by the nightly snapshot and the checkpoint's R2 arming fingerprint.
BOARD_REL = "site/factordata/us_standouts.json"
INDEX_REL = "site/prophet/index.json"


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
        "utf-8"
    )


def digest(path: Path) -> str:
    """Incumbent fingerprint: ``mode:sha256`` of raw bytes, symlinks refused."""
    if path.is_symlink():
        raise RuntimeError(f"refusing symlinked Prophet output: {path}")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return f"{path.stat().st_mode & 0o7777:04o}:{h.hexdigest()}"


def snapshot(root: Path) -> dict[str, str]:
    """Full closed-allowlist inventory, identical semantics to the nightly step."""
    root = Path(root)
    paths = {root / rel for rel in EXACT_PATHS}
    for rel_dir, pattern in DIRECTORY_GLOBS.items():
        directory = root / rel_dir
        if directory.is_dir():
            paths.update(directory.glob(pattern))
    return {
        path.relative_to(root).as_posix(): digest(path)
        for path in sorted(paths)
        if path.is_file()
    }


def candidate_store_entries(inventory: dict[str, str]) -> dict[str, str]:
    """The candidate store subset: every plan file fingerprint in the inventory."""
    prefix = CANDIDATE_STORE_DIR + "/"
    return {
        path: fingerprint
        for path, fingerprint in inventory.items()
        if path.startswith(prefix) and path.endswith(".json")
    }


def store_sha256(entries: dict[str, str]) -> str:
    """Deterministic whole-store digest over path + raw-byte SHA256 pairs.

    The raw-byte hash is the part of the incumbent ``mode:sha256`` fingerprint
    after the colon, so this digest is invariant to mode-bit noise yet still
    binds the FULL population (path + bytes), never a changed-only subset.
    """
    raw = {path: fingerprint.split(":", 1)[1] for path, fingerprint in entries.items()}
    return hashlib.sha256(canonical_json(raw)).hexdigest()
