"""Limitation-code coverage and wire-grammar checks."""

from __future__ import annotations

import re

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import (
    N03, N04, X02, X02B, X04, X04B, X05, nuclear_bundle, nuclear_query,
)


def payloads():
    fixtures = {
        "reactor_technology": (N03, X04, X04B),
        "nuclear_components": (N04, X02, X02B, X05),
        "fuel_cycle": (X04, X04B),
    }
    for slice_key, assertions in fixtures.items():
        for view in nuclear.VIEWS:
            for changes in ({}, {"time_mode": "source_history", "source_cutoff": "2026-12-31"}):
                yield nuclear.compose_nuclear_research(
                    nuclear_query(slice_key, view, **changes),
                    nuclear_bundle(*assertions))


def test_every_emitted_limitation_matches_exactly_one_declared_code():
    for payload in payloads():
        unmatched = [
            token for token in payload["limitations"]
            if sum(token == code or token.startswith(code)
                   for code in nuclear.LIMITATION_CODES) != 1
        ]
        assert unmatched == []


def test_every_declared_limitation_fits_the_contract_pattern():
    pattern = re.compile(r"^[a-z0-9_]+(?::[A-Za-z0-9_.-]+)?$")
    assert all(pattern.fullmatch(code.rstrip(":")) for code in nuclear.LIMITATION_CODES)
