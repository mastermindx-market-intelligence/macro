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
