"""Synthetic Mining cases for the future shared research contract."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from engine.market_ontology.mining_dependency_binding import (
    MiningOwnerBundle,
    MiningResearchQuery,
)

CASE_NAMES = (
    "copper_complete",
    "rare_earth_complete",
    "missing_basis",
    "missing_issuer",
    "source_only",
    "missing_stream_threshold",
    "changed_source",
    "signed_loss",
    "same_horizon_revision",
    "denied_source",
    "page_generation_change",
)


@dataclass(frozen=True)
class MiningCase:
    query: MiningResearchQuery
    bundle: MiningOwnerBundle
    expected: dict[str, Any]
    account_generation: str


def _fixture_path(name: str) -> Path:
    return Path(__file__).parent / "fixtures" / "mining_economic_dossier" / f"{name}.json"


def _merge(value: Any, overrides: Any) -> Any:
    if isinstance(value, dict) and isinstance(overrides, dict):
        merged = dict(value)
        for key, override in overrides.items():
            merged[key] = _merge(merged.get(key), override)
        return merged
    return copy.deepcopy(overrides)


def _query(fixture: dict[str, Any]) -> MiningResearchQuery:
    domain = fixture["domain"]
    return MiningResearchQuery(
        anchor_theme_id=domain["anchor_theme_id"],
        slice_key=domain["slice_key"],
        view="economics",
        time_mode="system_replay",
        source_cutoff="2026-09-24T00:00:00Z",
        recorded_cutoff="2026-09-24T00:00:00Z",
        offset=0,
        limit=50,
        expected_generation=fixture["account_generation"],
    )


def _bundle(fixture: dict[str, Any]) -> MiningOwnerBundle:
    return MiningOwnerBundle(
        revision_tuple=tuple(
            (str(key), str(value)) for key, value in fixture["revision_tuple"]
        ),
        rights_revision=fixture["source"]["rights_revision"],
        assertions=(dict(fixture["assertion"]),),
        identity_results=(dict(fixture["issuer"]),) if "issuer" in fixture else (),
        event_workspaces=(dict(fixture["event_workspace"]),),
        financial_packets=(dict(fixture["economics"]),) if "economics" in fixture else (),
        interpretation_blocks=(),
        native_refs=(dict(fixture["source"]),),
        omissions=tuple(fixture["omissions"]),
    )


def financial_packets_from_event_facts(
    rows: Any,
    *,
    stable_subject_id: str,
) -> tuple[dict[str, Any], ...]:
    """Map ``event_fact.v1`` rows into financial packets. ``period`` is carried.

    Absent rows are not packets. The composer does not import the witness module;
    the composition test calls the profile and passes the rows here.
    """
    if not isinstance(stable_subject_id, str) or not stable_subject_id.strip():
        raise ValueError("stable_subject_id is required")
    packets: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("event fact row must be a mapping")
        if row.get("schema") != "event_fact.v1":
            raise ValueError("row schema is not event_fact.v1")
        if "typed_absence" in row or "value" not in row:
            continue
        period = row.get("period")
        if not isinstance(period, str) or not period.strip():
            raise ValueError("event_fact.v1 period must be carried")
        basis = row.get("basis")
        if not isinstance(basis, str) or not basis.strip():
            raise ValueError("event_fact.v1 basis must be carried")
        metric = str(row.get("metric") or "")
        if not metric:
            raise ValueError("event_fact.v1 metric must be carried")
        packets.append(
            {
                "stable_subject_id": stable_subject_id,
                "measure": metric,
                "value": row["value"],
                "basis": basis,
                "source_label": metric,
                "period": period,
            }
        )
    return tuple(packets)


def expectations_packets_from_event_facts(
    rows: Any,
    *,
    stable_subject_id: str,
    perimeter: str,
) -> tuple[dict[str, Any], ...]:
    """Map ``event_fact.v1`` rows into at most one copper ``sales`` mev packet.

    The mapper is structural only: it does NOT police value polarity, value
    equality, missing definition fields or per-pair domain rules. The composer
    (mining_theme_research.py:868-873 and ``_missing_required_fields``) is
    responsible for the equal-values withhold, ``definition_unqualified:*``
    mints, the unit / perimeter / basis presence check and the comparable-fields
    check. This build does not edit ``engine/``; the mapper emits a packet and
    the existing mev path is the one that runs against it.

    Pairing contract:

    * earlier_point_estimate comes from the row whose ``metric`` is
      ``management_issued_copper_sales_estimate``;
    * later_actual comes from the row whose ``metric`` is
      ``consolidated_copper_sales``.

    Both rows must be ``event_fact.v1`` with a non-empty ``value`` and no
    ``typed_absence`` (the same gate ``financial_packets_from_event_facts``
    uses for the native-block channel). Unit and basis are taken from each
    row's literal ``unit`` / ``basis`` field (the ``_present`` shape in
    mining_issuer_profiles.py:422-424), NOT derived from ``period_kind``.
    Each leg carries its own row's ``period``; a missing or blank
    ``period`` on either paired row raises :class:`ValueError`; the composer's
    COMPARABILITY_FIELDS check, not this mapper, decides whether the two legs
    are commensurable.

    ``perimeter`` is the caller-supplied perimeter word (T04b's table uses
    ``"consolidated"``). Empty ``perimeter`` raises :class:`ValueError`.

    Returns an empty tuple when fewer than both rows are present -- today's
    T04b exhibit publishes only the actual row, so a T04b-only input maps to
    zero packets and the composer produces an ``omitted:expectations``
    payload rather than a fabricated comparison.
    """
    if not isinstance(stable_subject_id, str) or not stable_subject_id.strip():
        raise ValueError("stable_subject_id is required")
    if not isinstance(perimeter, str) or not perimeter.strip():
        raise ValueError("perimeter is required")

    _ESTIMATE_METRIC = "management_issued_copper_sales_estimate"
    _ACTUAL_METRIC = "consolidated_copper_sales"

    estimate_row: Mapping[str, Any] | None = None
    actual_row: Mapping[str, Any] | None = None
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("event fact row must be a mapping")
        if row.get("schema") != "event_fact.v1":
            raise ValueError("row schema is not event_fact.v1")
        if "typed_absence" in row or "value" not in row:
            continue
        metric = str(row.get("metric") or "")
        if metric == _ESTIMATE_METRIC and estimate_row is None:
            estimate_row = row
        elif metric == _ACTUAL_METRIC and actual_row is None:
            actual_row = row

    if estimate_row is None or actual_row is None:
        return ()

    # Mirrors financial_packets_from_event_facts's period gate: a paired row
    # whose period is absent or blank raises instead of emitting a
    # period-blind packet that the composer would polarise on blank legs.
    for paired_row in (estimate_row, actual_row):
        paired_period = paired_row.get("period")
        if not isinstance(paired_period, str) or not paired_period.strip():
            raise ValueError("event_fact.v1 period must be carried")

    packet: dict[str, Any] = {
        "kind": "management_estimate_vs_actual",
        "pair": "sales",
        "earlier_point_estimate": {
            "value": estimate_row["value"],
            "unit": str(estimate_row.get("unit") or ""),
            "perimeter": perimeter,
            "basis": str(estimate_row.get("basis") or ""),
            "period": str(estimate_row.get("period") or ""),
        },
        "later_actual": {
            "value": actual_row["value"],
            "unit": str(actual_row.get("unit") or ""),
            "perimeter": perimeter,
            "basis": str(actual_row.get("basis") or ""),
            "period": str(actual_row.get("period") or ""),
        },
    }
    return (packet,)


def synthetic_case(name: str, **overrides) -> MiningCase:
    """Load one closed synthetic case and apply recursively cloned overrides."""
    if name not in CASE_NAMES:
        raise KeyError(f"unknown case {name!r}; known: {', '.join(CASE_NAMES)}")

    with _fixture_path(name).open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    if fixture.get("synthetic") is not True:
        raise ValueError(f"case {name!r} is not marked synthetic")
    fixture = _merge(fixture, overrides)
    if fixture.get("synthetic") is not True:
        raise ValueError(f"case {name!r} overrides removed its synthetic mark")

    return MiningCase(
        query=_query(fixture),
        bundle=_bundle(fixture),
        expected=dict(fixture["expected"]),
        account_generation=str(fixture["account_generation"]),
    )
