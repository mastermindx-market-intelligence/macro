"""Nuclear query refusal parity with the shared shell."""

from __future__ import annotations

import pytest

from engine.market_ontology import nuclear_theme_research as nuclear
from tests.nuclear_research_helpers import N04, nuclear_bundle, nuclear_query


def refusal(changes, code):
    with pytest.raises(nuclear.ResearchRefusal) as caught:
        nuclear.compose_nuclear_research(
            nuclear_query(**changes), nuclear_bundle(N04))
    assert caught.value.code == code


def test_query_refusal_codes_match_shared_shell():
    refusal({"anchor_theme_id": "other"}, "not_available")
    refusal({"slice_key": "other"}, "slice_not_supported")
    refusal({"view": "other"}, "view_not_supported")
    refusal({"offset": -1}, "offset_negative")
    refusal({"limit": 0}, "limit_out_of_range")
    refusal({"limit": 101}, "limit_out_of_range")
    refusal({"offset": 1}, "expected_generation_required")
    refusal({"expected_generation": "gen_" + "0" * 32}, "generation_changed")


def test_replay_cutoffs_required_and_identity_vintage_unsupported():
    refusal({"time_mode": "system_replay"}, "replay_cutoffs_required")
    bundle = nuclear_bundle(N04)
    query = nuclear_query(
        "nuclear_components", "economics", time_mode="system_replay",
        source_cutoff="2026-09-20", recorded_cutoff="2026-09-21",
        expected_generation=None)
    first = nuclear.compose_nuclear_research(query, bundle)
    generation = first["generation"]
    with pytest.raises(nuclear.ResearchRefusal) as caught:
        nuclear.compose_nuclear_research(dataclasses_replace(query, expected_generation=generation), dataclasses_replace(bundle, identity_results=({
            "source_business_label": "BWX Technologies", "resolution": "RESOLVED",
            "company_node_id": "co:us:BWXT", "security_id": None,
            "listing_valid_from": None, "listing_valid_to": None,
            "mapping_learned_at": None,
        },)))
    assert caught.value.code == "identity_vintage_unsupported"


def dataclasses_replace(query, **changes):
    import dataclasses
    return dataclasses.replace(query, **changes)
