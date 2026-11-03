"""Replay display gate for Robotics interpretation prose (ruling 14b).

Synthetic bundles only, loaded through ``tests.robotics_research_helpers``.
A ``system_replay`` response's interpretation prose does not change when the
bundle gains a post-cutoff assertion, and a carried input that failed the
time or slice gate is not labelled ``interpretation_inputs_absent``.
"""

from __future__ import annotations

import copy
import dataclasses
import json

from engine.market_ontology.robotics_theme_research import compose_robotics_research
from engine.theme_graph.curation_assertion import encode_assertion
from tests.robotics_research_helpers import load_bundle_case, load_case

# Block reviewed_at on the witness fixture is 2026-09-23T07:00:00Z. This
# cutoff is later, so the block's own review clock admits it. The added
# assertion's published_at is the following day, so only that input is
# outside the replay window.
_CUTOFF = "2026-09-23T08:00:00Z"
_PROSE_KEYS = ("why_it_matters", "offset", "next_evidence")


def _restamp(payload: dict, **nested) -> dict:
    mutant = copy.deepcopy(payload)
    for path, value in nested.items():
        node = mutant
        keys = path.split(".")
        for key in keys[:-1]:
            node = node[key]
        node[keys[-1]] = value
    mutant["curation_revision"] = None
    return json.loads(encode_assertion(mutant))


def _replay_query(query):
    return dataclasses.replace(
        query,
        time_mode="system_replay",
        source_cutoff=_CUTOFF,
        recorded_cutoff=_CUTOFF,
        view="composition",
    )


def _prose(response) -> list[str]:
    summary = response["summary"]
    return [
        item.get("text", "")
        for key in _PROSE_KEYS
        for item in summary[key]
    ]


def _post_cutoff_pair():
    """Same query and recorded cutoff. The second bundle adds one assertion
    whose ``published_at`` is after the cutoff and whose
    ``curation_revision`` the interpretation block cites."""
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    case = load_case("witness_perception_orbbec_twinny")
    base = case["bundle"]["assertions"][0]
    block_src = case["bundle"]["interpretation_blocks"][0]
    post = _restamp(
        base,
        **{
            "source.published_at": "2026-09-24T00:00:00Z",
            "source.published_at_grain": "instant",
        },
    )
    block = {**block_src, "input_revisions": [post["curation_revision"]]}
    without = dataclasses.replace(bundle, interpretation_blocks=(block,))
    with_post = dataclasses.replace(
        bundle,
        assertions=bundle.assertions + (post,),
        interpretation_blocks=(block,),
    )
    replay = _replay_query(query)
    first = compose_robotics_research(replay, without)
    second = compose_robotics_research(replay, with_post)
    return first, second, block_src, post


def test_replay_served_text_ignores_a_post_cutoff_input():
    first, second, block_src, post = _post_cutoff_pair()
    assert _prose(first) == _prose(second)
    assert block_src["mechanism"] not in _prose(second)
    assert "[stale interpretation] " + block_src["mechanism"] not in _prose(second)
    assert post["curation_revision"] not in second["summary"]["input_refs"]


def test_time_excluded_input_is_not_labeled_interpretation_inputs_absent():
    _first, second, _block_src, _post = _post_cutoff_pair()
    assert not any(
        item.startswith("interpretation_inputs_absent")
        for item in second["limitations"]
    )


def test_cross_slice_input_does_not_unlock_interpretation_prose():
    query, bundle = load_bundle_case("witness_perception_orbbec_twinny")
    case = load_case("witness_perception_orbbec_twinny")
    base = case["bundle"]["assertions"][0]
    block_src = case["bundle"]["interpretation_blocks"][0]
    assert base["scope"]["technology_facet"] == "perception"
    crossed = _restamp(base, **{"scope.technology_facet": "precision_motion"})
    assert crossed["scope"]["technology_facet"] == "precision_motion"
    block = {**block_src, "input_revisions": [crossed["curation_revision"]]}
    rebuilt = dataclasses.replace(
        bundle,
        assertions=(crossed,),
        interpretation_blocks=(block,),
    )
    response = compose_robotics_research(_replay_query(query), rebuilt)
    mechanism = block_src["mechanism"]
    texts = _prose(response)
    assert mechanism not in texts
    assert "[stale interpretation] " + mechanism not in texts
    assert not any(
        item.startswith("interpretation_inputs_absent")
        for item in response["limitations"]
    )
