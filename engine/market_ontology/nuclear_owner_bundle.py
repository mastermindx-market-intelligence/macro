"""Declared-absent Nuclear owner-bundle loader."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from engine.market_ontology.nuclear_theme_research import OwnerBundle, ResearchQuery
from engine.market_ontology.theme_research_binding import BundleUnavailable
from engine.theme_graph.rights import load_registry_snapshot

PUBLIC_ASSERTIONS_UNCURATED = "public_assertions_uncurated"


def _rights_revision(rights_snapshot: object) -> str:
    snapshot = rights_snapshot
    if snapshot is None:
        snapshot = load_registry_snapshot()
    if not (isinstance(snapshot, tuple) and len(snapshot) == 2
            and isinstance(snapshot[0], str) and snapshot[0]):
        raise BundleUnavailable("rights snapshot carries no revision")
    return snapshot[0]


def load_nuclear_owner_bundle(
    query: ResearchQuery,
    *,
    rights_snapshot: tuple[str, Mapping[str, Any]] | None = None,
) -> OwnerBundle:
    del query
    from engine.market_ontology.semiconductor_owner_bundle import (  # noqa: PLC0415 — lazy by design
        PRIVATE_ASSERTIONS_UNBOUND,
    )
    return OwnerBundle(
        revision_tuple=(),
        rights_revision=_rights_revision(rights_snapshot),
        assertions=(),
        identity_results=(),
        event_workspaces=(),
        financial_packets=(),
        interpretation_blocks=(),
        native_refs=(),
        omissions=(PRIVATE_ASSERTIONS_UNBOUND, PUBLIC_ASSERTIONS_UNCURATED),
    )
