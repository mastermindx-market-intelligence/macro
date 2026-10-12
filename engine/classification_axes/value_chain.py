"""value_chain classification-axis reader (WS:GMI-THEME-GRAPH Taxonomy V2, lane L10).

Answers "where in its parent theme's value chain does this sub-theme /
micro-theme sit, as known on date D?" by reading the house-curated
``value_chain_position`` (one of ``upstream``, ``midstream``, ``downstream``,
``enabler``) from a theme node's ``source_meta`` JSON in the theme-graph node
table. Most nodes have no position yet (a later lane populates it), so
``unknown/value_missing`` is the honest common answer.

Pure reader, Gate #8: it writes nothing, persists nothing, calls nothing on
the network, and resolves no rights. The sibling axis readers are never
imported — this lane applies its own ``as_of`` overlay per the L10 ruling,
reading the store's raw tables (``read_nodes(current=False)`` and
``read_node_lifecycle(latest=False)``) rather than the current-view collapse.

Diagnostics that distinguish one absent/degraded answer from another travel
in ``provenance``; the ``reason_code`` stays inside the AxisCell v1
vocabulary.
"""
from __future__ import annotations

import json

import pandas as pd

from engine.classification_axes import cell
from engine.theme_graph.store import RETIRED_LIKE_STATUSES, read_node_lifecycle, read_nodes

AXIS = "value_chain"
SOURCE_OWNER = "engine/theme_graph/store.py"
SOURCE_ARTIFACT = "data/theme_graph/nodes.parquet"
MAX_AGE_DAYS: int | None = None
SUBJECT_KINDS = ("theme",)
RIGHTS_CONTEXT: dict | None = None
POSITIONS = ("upstream", "midstream", "downstream", "enabler")

_POSITION_KEY = "value_chain_position"
_SOURCE_FIELD = f"source_meta.{_POSITION_KEY}"
_SOURCE = {"owner": SOURCE_OWNER, "artifact": SOURCE_ARTIFACT, "field": _SOURCE_FIELD}

# A missing column is a degraded store, not a missing value.
_REQUIRED_NODE_COLUMNS = ("node_id", "tier", "status", "birth_date", "source_meta")
_REQUIRED_LIFECYCLE_COLUMNS = ("node_id", "status", "computed_at")

_POSITION_TIERS = ("sub_theme", "micro_theme")


def _blank(value: object) -> bool:
    """Null, NaN/NaT, or whitespace-only."""
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except (TypeError, ValueError):
        return False
    return isinstance(value, str) and not value.strip()


def _day(value: object) -> str | None:
    """First 10 chars of an ISO date/datetime, or None when blank."""
    if _blank(value):
        return None
    return str(value)[:10]


def _refusal(
    subject_id: str,
    as_of: str,
    status: str,
    reason_code: str,
    provenance: tuple[str, ...],
) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status=status,
        reason_code=reason_code,
        as_of=as_of,
        source=dict(_SOURCE),
        provenance=provenance,
    )


def _usable(frame: object, required: tuple[str, ...]) -> pd.DataFrame | None:
    """The frame when it carries every required column, else None (absent)."""
    if not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    if not set(required) <= set(frame.columns):
        return None
    return frame


def read_value_chain(
    subject_id: str,
    *,
    as_of: str,
    root: object = None,
    nodes: object = None,
    lifecycle: object = None,
) -> dict:
    """Where in its parent theme's value chain this subject sits, as known on
    ``as_of``.

    ``root`` is accepted for registry uniformity only — the store owns its
    paths and this reader never resolves one. Injected ``nodes`` /
    ``lifecycle`` DataFrames (``store.NODE_COLUMNS`` /
    ``store.NODE_LIFECYCLE_COLUMNS`` shape) replace the store calls; without
    them the store's raw tables are read on every call. ``as_of`` is the only
    clock: no wall-clock, no cache, stable ordering throughout.
    """
    kind, _ = cell.parse_subject(subject_id)
    if kind not in SUBJECT_KINDS:
        return _refusal(subject_id, as_of, "not_applicable", "not_applicable",
                        (f"subject_kind:{kind}",))

    try:
        nodes_frame = read_nodes(current=False) if nodes is None else nodes
        lifecycle_frame = read_node_lifecycle(latest=False) if lifecycle is None else lifecycle
    except Exception:  # noqa: BLE001 — a degraded store is a typed answer, never a raise
        return _refusal(subject_id, as_of, "unavailable", "owner_degraded", ("store_read_failed",))

    if not isinstance(nodes_frame, pd.DataFrame) or not set(_REQUIRED_NODE_COLUMNS) <= set(nodes_frame.columns):
        return _refusal(subject_id, as_of, "unavailable", "owner_degraded", ("nodes_frame_unusable",))
    if nodes_frame.empty:
        return _refusal(subject_id, as_of, "unavailable", "owner_missing", ())

    rows = nodes_frame[nodes_frame["node_id"] == subject_id]
    if rows.empty:
        return _refusal(subject_id, as_of, "unknown", "value_missing", ())
    node = rows.sort_values("computed_at", kind="stable").iloc[0]

    birth = _day(node.get("birth_date"))
    if birth is not None and birth > as_of:
        return _refusal(subject_id, as_of, "unknown", "history_not_supported", ("birth_after_as_of",))

    status = node.get("status")
    retire_date = node.get("retire_date")
    merged_into = node.get("merged_into")

    lineage = _usable(lifecycle_frame, _REQUIRED_LIFECYCLE_COLUMNS)
    if lineage is not None:
        mine = lineage[lineage["node_id"] == subject_id]
        if not mine.empty:
            mine = mine.sort_values("computed_at", kind="stable")
            known = [
                row for _, row in mine.iterrows()
                if (day := _day(row.get("computed_at"))) is not None and day <= as_of
            ]
            if known:
                latest = known[-1]
                status = latest.get("status")
                retire_date = latest.get("retire_date")
                merged_into = latest.get("merged_into")

    status_text = None if _blank(status) else str(status)
    if status_text in RETIRED_LIKE_STATUSES:
        retire = _day(retire_date)
        if retire is not None and retire > as_of:
            return _refusal(subject_id, as_of, "unknown", "history_not_supported", ("retire_after_as_of",))
        if status_text == "retired":
            return _refusal(subject_id, as_of, "not_applicable", "retired_entity", ())
        target = None if _blank(merged_into) else f"merged_into:{merged_into}"
        return _refusal(subject_id, as_of, "not_applicable", "superseded_entity",
                        (target,) if target else ())

    tier = node.get("tier")
    if tier == "theme":
        return _refusal(subject_id, as_of, "not_applicable", "not_applicable", ("tier:theme",))
    if tier not in _POSITION_TIERS:
        return _refusal(subject_id, as_of, "not_applicable", "not_applicable", (f"tier:{tier}",))

    meta = node.get("source_meta")
    if _blank(meta):
        return _refusal(subject_id, as_of, "unknown", "value_missing", ())
    if isinstance(meta, dict):
        meta_dict = meta
    else:
        try:
            parsed = json.loads(str(meta))
        except (TypeError, ValueError):
            return _refusal(subject_id, as_of, "unavailable", "owner_degraded",
                            ("source_meta_unparseable",))
        if not isinstance(parsed, dict):
            return _refusal(subject_id, as_of, "unavailable", "owner_degraded",
                            ("source_meta_unparseable",))
        meta_dict = parsed

    if _POSITION_KEY not in meta_dict:
        return _refusal(subject_id, as_of, "unknown", "value_missing", ())
    position = meta_dict[_POSITION_KEY]
    if position not in POSITIONS:
        return _refusal(subject_id, as_of, "unavailable", "owner_degraded",
                        (f"invalid_value_chain_position:{position}",))

    return cell.available(
        axis=AXIS,
        subject_id=subject_id,
        value={"value_chain_position": position, "tier": str(tier)},
        as_of=as_of,
        source=dict(_SOURCE),
        unit=None,
        observed_at=None,
        effective_at=birth,
        freshness=None,
        labels=("house_curated",),
    )
