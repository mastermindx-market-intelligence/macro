"""Thin registration for the ``uranium_miners`` anchor. Fuel cycle only.

``compose`` calls the nuclear composer. This module adds no schema, no
assertions, and no tickers. The uranium basket page does not mount it:
membership is not identity, and no primary crosswalk row claims that basket.
"""
from __future__ import annotations

from typing import Any

from engine.market_ontology.nuclear_owner_bundle import load_nuclear_owner_bundle
from engine.market_ontology.nuclear_theme_research import (
    DEFINITION_VERSION,
    EVIDENCE_SCHEMA_ID,
    SCHEMA_ID,
    VIEW_KEYS,
    ResearchQuery,
    compose_nuclear_research,
    select_authorized_evidence,
)

ANCHOR_THEME_ID = "uranium_miners"
SLICE_KEYS = ("fuel_cycle",)


def build_query(**fields: Any) -> ResearchQuery:
    """The nuclear query type. Slice membership is refused by the composer."""
    return ResearchQuery(**fields)


def load_bundle(query: Any, *, rights_snapshot: Any = None) -> Any:
    """The nuclear owner bundle. It is empty; there is no second reader."""
    return load_nuclear_owner_bundle(query, rights_snapshot=rights_snapshot)


def compose(query: Any, bundle: Any) -> dict[str, Any]:
    return compose_nuclear_research(query, bundle)


def select_evidence(query: Any, bundle: Any, assertion_ref: str) -> dict[str, Any]:
    return select_authorized_evidence(query, bundle, assertion_ref)
