"""T07 pins for the mining evidence drawer and the recorded cutoff.

Three facts the economics panel's caller already depends on. The composer
is not rewritten here: a changed source refuses with ``generation_changed``,
a date-only ``recorded_cutoff`` is echoed unchanged, and a three-pair
``revision_tuple`` is echoed without collapsing the two account pairs.
Synthetic cases only. No network.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from engine.market_ontology import mining_theme_research as composition
from engine.market_ontology.mining_dependency_binding import MiningResearchRefusal
from tests.mining_casebook import synthetic_case

_STALE = "interpretation_stale"


def _contains(value: object, token: str) -> bool:
    if isinstance(value, str):
        return token in value
    if isinstance(value, dict):
        return any(_contains(key, token) or _contains(item, token) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_contains(item, token) for item in value)
    return False


def test_t07_changed_source_refuses_generation_changed_and_omits_interpretation_stale() -> None:
    """A changed source refuses with generation_changed and does not publish interpretation_stale."""
    case = synthetic_case("changed_source")
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.select_mining_evidence(case.query, case.bundle, "assertion:synthetic")
    assert raised.value.code == "generation_changed"
    assert _STALE not in MiningResearchRefusal.CODES

    result = composition.compose_mining_research(case.query, case.bundle)
    assert _STALE not in result["limitations"]
    assert not any(_contains(code, _STALE) for code in result["limitations"])
    assert not _contains(result["economics"]["native_blocks"], _STALE)
    assert not _contains(result["industrial_views"], _STALE)


def test_t07_date_only_recorded_cutoff_is_not_rewritten() -> None:
    """A date-only recorded_cutoff is echoed at replay_cutoff as that exact string."""
    case = synthetic_case("copper_complete")
    recorded = "2026-09-24"
    query = replace(case.query, recorded_cutoff=recorded)
    result = composition.compose_mining_research(query, case.bundle)
    assert result["request"]["replay_cutoff"] == recorded
    assert result["request"]["replay_cutoff"] != recorded + "Z"


def test_t07_revision_tuple_is_echoed_and_replay_is_byte_equal() -> None:
    """Three revision pairs stay intact, and an unchanged one-identity compose is byte-equal."""
    case = synthetic_case("copper_complete")
    assert len(case.bundle.identity_results) == 1
    account = case.account_generation
    middle = next(pair for pair in case.bundle.revision_tuple if pair[0] != "account_generation")
    revision_tuple = (
        ("account_generation", account),
        middle,
        ("account_generation", account + "-later"),
    )
    assert revision_tuple[0][0] == "account_generation"
    assert revision_tuple[2][0] == "account_generation"
    assert revision_tuple[0][1] != revision_tuple[2][1]
    bundle = replace(case.bundle, revision_tuple=revision_tuple)
    echoed = composition.compose_mining_research(case.query, bundle)
    selected = echoed["summary"]["selected_revisions"]
    assert len(selected) == 3
    assert selected == [list(pair) for pair in revision_tuple]
    assert selected[0][1] == account
    assert selected[2][1] == account + "-later"

    first = composition.compose_mining_research(case.query, case.bundle)
    second = composition.compose_mining_research(case.query, case.bundle)
    assert json.dumps(first, sort_keys=True).encode() == json.dumps(
        second, sort_keys=True
    ).encode()
