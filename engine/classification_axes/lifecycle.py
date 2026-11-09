"""Lifecycle classification axis — a node's status as known on date D.

A pure, read-only display-tier reader over the theme-graph store. It wraps
``engine.theme_graph.store.read_nodes(current=False, strict=True)`` (the
write-once node rows, never the latest-as-of-now overlay, which cannot answer
a historical date) and ``store.read_node_lifecycle(latest=False,
strict=True)`` (the append-only lineage), then applies its own ``as_of``
overlay: the last lineage row whose ``computed_at`` day is on or before
``as_of`` wins, else the node row itself. Strict reads surface a corrupt or
wrong-shape artifact as an exception, which this reader maps to the typed
``unavailable/owner_degraded`` status instead of laundering it into an empty
frame. Retired/merged detection reuses ``store.RETIRED_LIKE_STATUSES``.

The subject id IS the graph node id. ``root`` is accepted for registry
uniformity only — the store owns its table paths, so this reader never
resolves a path and never writes. No network, no wall-clock, no cache;
``as_of`` is the only clock. Cells are built through
``engine.classification_axes.cell`` and every return passes
``cell.validate_cell``.
"""
from __future__ import annotations

import datetime
import re

import pandas as pd

from engine.classification_axes import cell
from engine.theme_graph import store

AXIS = "lifecycle"
SOURCE_OWNER = "engine/theme_graph/store.py"
SOURCE_ARTIFACT = "data/theme_graph/nodes.parquet"
MAX_AGE_DAYS = None
SUBJECT_KINDS = ("co", "theme", "basket", "etf")
RIGHTS_CONTEXT = None

_SOURCE = {"owner": SOURCE_OWNER, "artifact": SOURCE_ARTIFACT, "field": "status"}

# Columns this reader actually reads, checked in NODE_COLUMNS /
# NODE_LIFECYCLE_COLUMNS order so the report names the first gap.
_NODE_REQUIRED = (
    "node_id", "status", "tier", "birth_date", "retire_date", "merged_into",
    "computed_at",
)
_LIFECYCLE_REQUIRED = ("node_id", "status", "retire_date", "merged_into", "computed_at")


def _plain(value: object) -> object:
    """None for a null/NaN/NaT cell, the value otherwise."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _day(value: object) -> str | None:
    """First ten chars of a timestamp-ish value (its calendar day), or None."""
    plain = _plain(value)
    return None if plain is None else str(plain)[:10]


def _birth_day(value: object) -> tuple[bool, str | None]:
    """Normalise a node row's ``birth_date`` once, before any comparison.

    ``(True, None)`` for a null/blank birth (the cell proceeds with
    ``birth_date: None``), ``(True, "YYYY-MM-DD")`` for a clean calendar day,
    ``(False, None)`` when unparseable — a typed refusal, never a raise.
    Mirrors ``cell._read_temporal``, the rule ``make_cell`` enforces on
    ``effective_at``, so a malformed birth cannot escape the reader as an
    ``AxisCellError``.
    """
    plain = _plain(value)
    if plain is None:
        return True, None
    if isinstance(plain, datetime.date):  # date, datetime and pd.Timestamp
        text = plain.isoformat()
    else:
        text = str(plain).strip()
        if not text:
            return True, None
    if (
        re.fullmatch(r"\d{4}-\d{2}-\d{2}", text[:10]) is None
        or not (len(text) == 10 or text[10] in "T ")
    ):
        return False, None
    try:
        datetime.date.fromisoformat(text[:10])
    except ValueError:
        return False, None
    return True, text[:10]


def _first_missing_column(columns: object, required: tuple[str, ...]) -> str | None:
    present = set(columns)
    for name in required:
        if name not in present:
            return name
    return None


def _owner_missing(subject_id: str, as_of: str) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status="unavailable",
        reason_code="owner_missing",
        as_of=as_of,
        source=dict(_SOURCE),
    )


def _degraded(subject_id: str, as_of: str, note: str) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status="unavailable",
        reason_code="owner_degraded",
        as_of=as_of,
        source=dict(_SOURCE),
        provenance=[note],
    )


def _history(subject_id: str, as_of: str) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status="unknown",
        reason_code="history_not_supported",
        as_of=as_of,
        source=dict(_SOURCE),
    )


def read_lifecycle(
    subject_id: str,
    *,
    as_of: str,
    root: str | None = None,
    nodes: pd.DataFrame | None = None,
    lifecycle: pd.DataFrame | None = None,
) -> dict:
    """The lifecycle AxisCell for a graph node on ``as_of`` (YYYY-MM-DD).

    ``nodes`` / ``lifecycle`` accept injected frames (the store's own column
    contracts); when omitted, the store readers run on every call with no
    caching. ``root`` is accepted for registry uniformity only: theme-graph
    data reaches this reader exclusively through the store, which owns its
    table paths.
    """
    kind, _rest = cell.parse_subject(subject_id)
    if kind not in SUBJECT_KINDS:
        return cell.missing(
            axis=AXIS,
            subject_id=subject_id,
            status="not_applicable",
            reason_code="not_applicable",
            as_of=as_of,
            source=dict(_SOURCE),
        )

    if nodes is None:
        try:
            nodes = store.read_nodes(current=False, strict=True)
        except FileNotFoundError:
            return _owner_missing(subject_id, as_of)
        except Exception as exc:  # noqa: BLE001 — strict read: unreadable or wrong-shape artifact
            return _degraded(subject_id, as_of, f"read_error:{type(exc).__name__}")
    if nodes.empty:
        return _owner_missing(subject_id, as_of)
    missing_column = _first_missing_column(nodes.columns, _NODE_REQUIRED)
    if missing_column is not None:
        return _degraded(subject_id, as_of, f"missing_column:{missing_column}")

    if lifecycle is None:
        try:
            lifecycle = store.read_node_lifecycle(latest=False, strict=True)
        except FileNotFoundError:
            # An absent lifecycle table is normal, not a degradation.
            lifecycle = pd.DataFrame(columns=list(store.NODE_LIFECYCLE_COLUMNS))
        except Exception as exc:  # noqa: BLE001 — same typed refusal as above
            return _degraded(subject_id, as_of, f"read_error:{type(exc).__name__}")
    if not lifecycle.empty:
        missing_column = _first_missing_column(lifecycle.columns, _LIFECYCLE_REQUIRED)
        if missing_column is not None:
            return _degraded(subject_id, as_of, f"missing_column:{missing_column}")

    rows = nodes[nodes["node_id"] == subject_id]
    if rows.empty:
        return cell.missing(
            axis=AXIS,
            subject_id=subject_id,
            status="unknown",
            reason_code="value_missing",
            as_of=as_of,
            source=dict(_SOURCE),
        )
    # Keep-first on computed_at, matching the store's write-once NODE_KEY.
    node_row = rows.sort_values("computed_at", kind="stable", na_position="last").iloc[0]

    birth_ok, birth = _birth_day(node_row["birth_date"])
    if not birth_ok:
        return _degraded(subject_id, as_of, "birth_date_unparseable")
    if birth is not None and birth > as_of:
        return _history(subject_id, as_of)

    # The last lineage row computed on or before as_of; a row without a
    # computable day cannot be placed in time and is skipped.
    effective = node_row
    used_lifecycle = False
    if not lifecycle.empty:
        node_lf = lifecycle[lifecycle["node_id"] == subject_id]
        if not node_lf.empty:
            in_window = node_lf["computed_at"].map(
                lambda value: (day := _day(value)) is not None and day <= as_of
            )
            eligible = node_lf[in_window]
            if not eligible.empty:
                # Latest wins, matching the store's latest-by-computed_at collapse.
                effective = eligible.sort_values(
                    "computed_at", kind="stable", na_position="last"
                ).iloc[-1]
                used_lifecycle = True

    status = _plain(effective["status"])
    retire = _day(effective["retire_date"])
    merged_into = _plain(effective["merged_into"])
    provenance = ["status_source:lifecycle"] if used_lifecycle else ["status_source:node_row"]

    if status is not None and status in store.RETIRED_LIKE_STATUSES:
        if retire is not None and retire > as_of:
            # Not yet retired on as_of, and the earlier status is not recorded.
            return _history(subject_id, as_of)
        if status == "retired":
            return cell.missing(
                axis=AXIS,
                subject_id=subject_id,
                status="not_applicable",
                reason_code="retired_entity",
                as_of=as_of,
                source=dict(_SOURCE),
                provenance=provenance,
            )
        if merged_into is not None:
            provenance = provenance + [f"merged_into:{merged_into}"]
        return cell.missing(
            axis=AXIS,
            subject_id=subject_id,
            status="not_applicable",
            reason_code="superseded_entity",
            as_of=as_of,
            source=dict(_SOURCE),
            provenance=provenance,
        )

    return cell.available(
        axis=AXIS,
        subject_id=subject_id,
        value={
            "node_status": status,
            "tier": _plain(node_row["tier"]) or None,
            "kind": kind,
            "birth_date": birth or None,
        },
        as_of=as_of,
        source=dict(_SOURCE),
        effective_at=birth or None,
        provenance=provenance,
    )
