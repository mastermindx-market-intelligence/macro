"""Geography classification axis — where is this company node's listing?

Lane L06 of WS:GMI-THEME-GRAPH Taxonomy V2. A pure, read-only DISPLAY/CONTEXT
reader that wraps two incumbents: the identity resolver
``engine.theme_graph.identity_resolution.resolve_graph_node_identity`` (graph
node -> security_id/listing_key) and the house security master
``data/reference/security_master.parquet`` (written by
``scripts/build_security_master.py``). This module writes nothing, caches
nothing, calls nothing on the network, and mints no identity — it joins the
resolver's answer against the master's own country/MIC history and reports
what the joined evidence supports, with a typed null and a reason otherwise.

Domicile has no owner today, so ``value["domicile"]`` is always ``None`` and
the provenance carries ``domicile:no_owner`` instead of a guess.

Point-in-time law: the resolver is always invoked with the caller's explicit
asof (HISTORICAL mode) — never with a null asof, which would read the wall
clock and the latest sidecar generation. A master row whose effective date is
after ``as_of`` is not yet visible and yields
``unknown/history_not_supported``.

``finviz_themes``, ``ths_concepts`` and ``ltheme:*`` are internal-only and are
never subjects (Gate #2). This is a reader over incumbent artifacts, not a
producer, store, or rights resolver (Gate #8); everything it returns is an
AxisCell v1 record built through ``engine.classification_axes.cell``.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from engine.classification_axes import cell
from engine.theme_graph import identity_resolution

AXIS = "geography"

#: The incumbent producer of the master — provenance owner, never imported.
SOURCE_OWNER = "scripts/build_security_master.py"

#: The incumbent artifact this axis reads.
SOURCE_ARTIFACT = "data/reference/security_master.parquet"

#: The master carries dated rows forever; age never makes a listing stale.
MAX_AGE_DAYS = None

#: Company nodes only — the resolver's v1 row scope.
SUBJECT_KINDS = ("co",)

#: No rights resolution happens here; the master is house-owned reference data.
RIGHTS_CONTEXT = None

#: Master columns the join cannot answer without; the first missing one degrades.
_REQUIRED_COLUMNS = (
    "security_id",
    "listing_key",
    "country",
    "mic",
    "effective_at",
    "security_state",
    "superseded_by",
)

_MASTER_RELATIVE = Path("data") / "reference" / "security_master.parquet"


def _clean(value: object) -> object:
    """None for the missing-cell shapes pandas can hand back (None, NaN, NaT)."""
    if value is None:
        return None
    try:
        absent = bool(pd.isna(value))
    except (TypeError, ValueError):
        return value
    return None if absent else value


def _text(value: object) -> str | None:
    """The value as plain text, or None when pandas reports it missing."""
    cleaned = _clean(value)
    return None if cleaned is None else str(cleaned)


def _source() -> dict:
    return {"owner": SOURCE_OWNER, "artifact": SOURCE_ARTIFACT, "field": "country"}


def _missing(
    subject_id: str, as_of: str, status: str, reason_code: str, provenance: list[str]
) -> dict:
    return cell.missing(
        axis=AXIS,
        subject_id=subject_id,
        status=status,
        reason_code=reason_code,
        as_of=as_of,
        source=_source(),
        labels=[],
        provenance=provenance,
        rights_context=RIGHTS_CONTEXT,
    )


def _master_path(root: str | Path | None) -> Path:
    base = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    return base / _MASTER_RELATIVE


def read_geography(
    subject_id: str,
    *,
    as_of: str,
    root: str | Path | None = None,
    resolve: Callable[..., dict] | None = None,
    master: pd.DataFrame | None = None,
) -> dict:
    """One company node's listing country + MIC as of ``as_of``, as an AxisCell.

    ``resolve`` defaults to the incumbent
    ``identity_resolution.resolve_graph_node_identity`` and is ALWAYS invoked
    with the caller's ``as_of`` as its explicit asof, so resolution runs in
    HISTORICAL mode over committed inputs — the persisted-sidecar/wall-clock
    path is never taken. ``master`` defaults to a fresh read of
    ``SOURCE_ARTIFACT`` under ``root`` (default: the repo root) on every call.

    Deterministic: no wall clock, no caching, stable ordering inside the value
    and across identical calls. Raises only what ``cell.parse_subject`` raises
    for a malformed subject id; every other failure is a typed null cell.
    """
    kind, _rest = cell.parse_subject(subject_id)
    if kind not in SUBJECT_KINDS:
        return _missing(
            subject_id, as_of, "not_applicable", "not_applicable",
            [f"subject_kind_not_covered:{kind}"],
        )

    if master is None:
        path = _master_path(root)
        if not path.exists():
            return _missing(
                subject_id, as_of, "unavailable", "owner_missing",
                ["master_file_absent"],
            )
        try:
            frame = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001 — a corrupt artifact degrades, never fatal
            return _missing(
                subject_id, as_of, "unavailable", "owner_degraded",
                [f"read_error:{type(exc).__name__}"],
            )
    else:
        frame = master
    columns = set(getattr(frame, "columns", ()))
    for required in _REQUIRED_COLUMNS:
        if required not in columns:
            return _missing(
                subject_id, as_of, "unavailable", "owner_degraded",
                [f"missing_column:{required}"],
            )

    resolver = (
        resolve if resolve is not None
        else identity_resolution.resolve_graph_node_identity
    )
    try:
        row = resolver(subject_id, asof=as_of)
    except identity_resolution.UnknownGraphNodeError:
        return _missing(
            subject_id, as_of, "unknown", "value_missing", ["graph_node_absent"]
        )
    except Exception as exc:  # noqa: BLE001 — a broken resolver degrades, never fatal
        return _missing(
            subject_id, as_of, "unavailable", "owner_degraded",
            [f"resolver_error:{type(exc).__name__}"],
        )

    state = _text(row.get("resolution_state")) if hasattr(row, "get") else None
    if state != "RESOLVED":
        if state == "UNSUPPORTED_MARKET":
            return _missing(
                subject_id, as_of, "not_applicable", "not_applicable",
                ["resolution_state:UNSUPPORTED_MARKET"],
            )
        return _missing(
            subject_id, as_of, "unknown", "value_missing",
            [f"resolution_state:{state}"],
        )

    security_id = _text(row.get("security_id"))
    listing_key = _text(row.get("listing_key"))
    matches: list[dict] = []
    if security_id is not None:
        for record in frame.to_dict("records"):
            if _text(record.get("security_id")) != security_id:
                continue
            if (listing_key is not None
                    and _text(record.get("listing_key")) != listing_key):
                continue
            matches.append(record)
    if not matches:
        return _missing(
            subject_id, as_of, "unknown", "value_missing",
            ["security_id_absent_from_master"],
        )

    as_of_text = str(as_of)
    eligible = [r for r in matches if str(r.get("effective_at"))[:10] <= as_of_text]
    if not eligible:
        return _missing(
            subject_id, as_of, "unknown", "history_not_supported",
            ["effective_after_as_of"],
        )

    dated = "ingested_at" in columns

    def _sort_key(record: dict) -> tuple[str, str]:
        ingested = _text(record.get("ingested_at")) if dated else ""
        return (str(record.get("effective_at")), ingested or "")

    chosen = sorted(eligible, key=_sort_key)[-1]

    security_state = _text(chosen.get("security_state"))
    superseded_by = _text(chosen.get("superseded_by"))
    if security_state is not None or superseded_by is not None:
        provenance = []
        if security_state is not None:
            provenance.append(f"security_state:{security_state}")
        if superseded_by is not None:
            provenance.append(f"superseded_by:{superseded_by}")
        return _missing(
            subject_id, as_of, "not_applicable", "superseded_entity", provenance
        )

    effective = str(chosen.get("effective_at"))[:10]
    provenance = ["resolution_state:RESOLVED", "domicile:no_owner"]
    join_method = _text(row.get("join_method"))
    if join_method is not None:
        provenance.append(f"join_method:{join_method}")
    return cell.available(
        axis=AXIS,
        subject_id=subject_id,
        value={
            "listing_country": _clean(chosen.get("country")),
            "listing_mic": _clean(chosen.get("mic")),
            "listing_key": _clean(chosen.get("listing_key")),
            "domicile": None,
        },
        as_of=as_of,
        source=_source(),
        unit=None,
        observed_at=effective,
        effective_at=effective,
        freshness=None,
        labels=["source_local"],
        provenance=provenance,
        rights_context=RIGHTS_CONTEXT,
    )
