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


# One synthetic causal view, replaced onto a bundle through ``dataclasses.replace`` —
# never written into a fixture. The view is the subject of both arms below.
_VIEW = {
    "stable_subject_id": "subject:ardent-copper",
    "view_kind": "industrial",
    "description": "fictional smelter constraint carried over from the prior source revision",
    "evidence_refs": ["synthetic-copper-source-4"],
}


def test_t07_changed_source_refuses_generation_changed_and_omits_interpretation_stale() -> None:
    """A changed source refuses with generation_changed and does not publish interpretation_stale.

    W10-1 strengthening. The drawer-refusal pins (CODES and ``generation_changed``) are
    unchanged; what changed is where the payload asserts run. They used to search the
    ``changed_source`` compose, whose ``native_blocks`` is empty because
    ``_suppress_native_blocks`` withdraws the economics channel — so
    ``_contains(result["economics"]["native_blocks"], _STALE)`` was a negative assertion
    over ``[]``, and the W9-V ``native_blocks_basis_token`` mutant (stale vocabulary
    injected into a real block's ``basis``) survived it. Both arms now run against a
    bundle that carries an industrial view:

    * WITHDRAWN — ``changed_source``: still no stale vocabulary anywhere in the payload,
      and (W10-1) the withdrawn channel withdraws its causal text with it, so
      ``industrial_views == []`` beside ``native_blocks == []``;
    * POPULATED — ``copper_complete``, OBSERVEDly one native block and one view: the same
      asserts now have content to search, which is what kills the mutant.

    Synthetic cases only. No network, no fixture edit.
    """
    case = synthetic_case("changed_source")
    with pytest.raises(MiningResearchRefusal) as raised:
        composition.select_mining_evidence(case.query, case.bundle, "assertion:synthetic")
    assert raised.value.code == "generation_changed"
    assert _STALE not in MiningResearchRefusal.CODES

    withdrawn = composition.compose_mining_research(
        case.query, replace(case.bundle, interpretation_blocks=(_VIEW,))
    )
    assert withdrawn["limitations"] == ["changed_source"], withdrawn["limitations"]
    assert _STALE not in withdrawn["limitations"]
    assert not any(_contains(code, _STALE) for code in withdrawn["limitations"])
    assert not _contains(withdrawn["economics"]["native_blocks"], _STALE)
    # W10-1: an emptied economics panel must not be paired with stale causal text.
    assert withdrawn["industrial_views"] == [], withdrawn["industrial_views"]
    assert not _contains(withdrawn, _STALE)

    copper = synthetic_case("copper_complete")
    published = composition.compose_mining_research(
        copper.query, replace(copper.bundle, interpretation_blocks=(_VIEW,))
    )
    # The mutant needs a non-empty payload to hide in; pin that it is not empty first.
    assert len(published["economics"]["native_blocks"]) == 1, published["economics"]["native_blocks"]
    assert len(published["industrial_views"]) == 1, published["industrial_views"]
    assert _STALE not in published["limitations"]
    assert not any(_contains(code, _STALE) for code in published["limitations"])
    assert not _contains(published["economics"]["native_blocks"], _STALE)
    assert not _contains(published["industrial_views"], _STALE)
    assert not _contains(published, _STALE)


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
