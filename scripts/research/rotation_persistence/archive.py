"""Strict normalization of the existing published US basket-snapshot archive."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from lib.nyse_calendar import is_session
from .contracts import ArchiveReceipt, ContractError

_REQUIRED_COLUMNS = frozenset({"asof", "logged_at", "snapshot_json"})
_NORMALIZED_COLUMNS = ("rank", "score", "label", "breadth")


def _finite_number(value: Any, *, field: str, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ContractError(f"{field} must be a finite number, not boolean")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{field} must be a finite number") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        rule = "finite positive" if positive else "finite"
        raise ContractError(f"{field} must be {rule}")
    return result


def _optional_finite(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _parse_archive_date(value: Any, *, field: str) -> date:
    text = str(value).strip()
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ContractError(f"{field} must be an ISO date, got {text!r}") from exc
    if text != parsed.isoformat():
        raise ContractError(f"{field} must be an exact ISO date, got {text!r}")
    return parsed


def _normalize_snapshot(raw: Any, archive_asof: date) -> pd.DataFrame:
    if not isinstance(raw, str):
        raise ContractError(f"snapshot_json for {archive_asof} must be a JSON string")
    try:
        snapshot = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ContractError(f"snapshot_json for {archive_asof} is invalid JSON") from exc
    if not isinstance(snapshot, dict):
        raise ContractError(f"snapshot_json for {archive_asof} must decode to an object")
    snapshot_asof = _parse_archive_date(snapshot.get("as_of"), field="snapshot as_of")
    if snapshot_asof != archive_asof:
        raise ContractError(
            f"snapshot as_of {snapshot_asof} does not match archive asof {archive_asof}"
        )
    themes = snapshot.get("themes")
    if not isinstance(themes, list) or not themes:
        raise ContractError(f"themes for {archive_asof} must be a non-empty array")

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for position, theme in enumerate(themes):
        if not isinstance(theme, dict):
            raise ContractError(f"theme row {position} for {archive_asof} must be an object")
        theme_id = theme.get("id")
        if not isinstance(theme_id, str) or not theme_id.strip():
            raise ContractError(f"theme id at row {position} for {archive_asof} is missing")
        theme_id = theme_id.strip()
        if theme_id in seen:
            raise ContractError(f"duplicate theme id {theme_id!r} for {archive_asof}")
        seen.add(theme_id)
        rank = _finite_number(theme.get("rank"), field=f"rank[{theme_id}]", positive=True)
        score = _finite_number(theme.get("score"), field=f"score[{theme_id}]")
        label = theme.get("label")
        if label is not None and not isinstance(label, str):
            raise ContractError(f"label[{theme_id}] must be a string or null")
        components = theme.get("components")
        breadth = None
        if isinstance(components, dict):
            breadth = _optional_finite(components.get("breadth"))
        rows.append(
            {
                "theme_id": theme_id,
                "rank": rank,
                "score": score,
                "label": label,
                "breadth": breadth,
            }
        )

    frame = pd.DataFrame(rows).set_index("theme_id")
    return frame.loc[:, list(_NORMALIZED_COLUMNS)]


def load_basket_archive(path: Path) -> tuple[dict[date, pd.DataFrame], ArchiveReceipt]:
    """Load and normalize the keep-first published theme archive.

    Duplicate dates retain the first physical row in the parquet, matching the source
    archive's keep-first truth.  Non-session rows are omitted with an explicit receipt.
    Contract failures on session rows fail the whole research run rather than quietly
    shrinking the evidence set.
    """
    path = Path(path)
    if not path.is_file():
        raise ContractError(f"archive file not found: {path}")
    source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        archive = pd.read_parquet(path)
    except Exception as exc:  # noqa: BLE001 - normalized to a typed contract failure
        raise ContractError(f"archive could not be read: {path}") from exc
    missing = sorted(_REQUIRED_COLUMNS.difference(archive.columns))
    if missing:
        raise ContractError(f"archive missing required columns: {', '.join(missing)}")

    frames: dict[date, pd.DataFrame] = {}
    seen_dates: set[date] = set()
    duplicate_rows: list[str] = []
    non_session_rows: list[str] = []

    for _, row in archive.iterrows():
        asof = _parse_archive_date(row["asof"], field="archive asof")
        if asof in seen_dates:
            duplicate_rows.append(asof.isoformat())
            continue
        seen_dates.add(asof)
        if not is_session(asof):
            non_session_rows.append(asof.isoformat())
            continue
        frames[asof] = _normalize_snapshot(row["snapshot_json"], asof)

    frames = dict(sorted(frames.items()))
    valid_dates = list(frames)
    receipt = ArchiveReceipt(
        source_path=str(path),
        source_sha256=source_sha256,
        rows_read=int(len(archive)),
        rows_valid=len(frames),
        first_asof=valid_dates[0].isoformat() if valid_dates else None,
        last_asof=valid_dates[-1].isoformat() if valid_dates else None,
        non_session_rows=tuple(non_session_rows),
        duplicate_asof_rows=tuple(duplicate_rows),
    )
    if not frames:
        raise ContractError("archive contains no valid NYSE-session snapshots")
    return frames, receipt
