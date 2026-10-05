"""T08 Semiconductor Theme Intelligence B: honest temporal modes.

latest / source_history / system_replay must differ exactly as the contract
says: archival sources recorded later than publication are allowed ONLY in
source_history (labelled retrospective), replay needs BOTH cutoffs, refuses
unknown availability, never synthesizes midnight for a date-only publication
on the cutoff day, never resolves an identity before its mapping was learned
(a 1970 listing epoch is not evidence), and a stale interpretation is labelled
stale while the newly supported observation stays visible.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace

import pytest

from engine.theme_graph.curation_assertion import encode_assertion

from engine.market_ontology.semiconductor_theme_research import (
    ResearchRefusal,
    compose_semiconductor_research,
)

from tests.semiconductor_research_helpers import load_bundle_case


def _restamp(payload: dict, **changes) -> dict:
    body = copy.deepcopy(dict(payload))
    body.update(changes)
    body['curation_revision'] = None
    return json.loads(encode_assertion(body))


def _restamp_source(payload: dict, **source_changes) -> dict:
    body = copy.deepcopy(dict(payload))
    source = dict(body['source'])
    source.update(source_changes)
    body['source'] = source
    body['curation_revision'] = None
    return json.loads(encode_assertion(body))


def _capacity_rows(response):
    return response['industrial_views']['capacity']['rows']


# ─────────────────────────────────────────────────────────────────────────────
# latest vs source_history vs system_replay
# ─────────────────────────────────────────────────────────────────────────────


def test_latest_includes_all_native_inputs_without_retrospective_label():
    query, bundle = load_bundle_case('recorded_later')
    response = compose_semiconductor_research(replace(query, time_mode='latest',
                                                      source_cutoff=None, recorded_cutoff=None), bundle)
    rows = _capacity_rows(response)
    assert rows, 'latest sees all native inputs'
    assert all(row['retrospective'] is False for row in rows)


def test_source_history_includes_archival_source_labelled_retrospective():
    query, bundle = load_bundle_case('recorded_later')
    response = compose_semiconductor_research(query, bundle)
    assert query.time_mode == 'source_history'
    rows = _capacity_rows(response)
    assert rows, 'an archival source recorded later than its publication is allowed in source_history'
    assert all(row['retrospective'] is True for row in rows), (
        'recorded later than publication must be labelled retrospective: true'
    )
    assert response['authorized_coverage']['selected'] == len(bundle.assertions)


def test_source_history_cutoff_excludes_later_publication():
    query, bundle = load_bundle_case('recorded_later')
    early = replace(query, source_cutoff='2026-02-01T00:00:00Z')  # before the February publication
    response = compose_semiconductor_research(early, bundle)
    assert _capacity_rows(response) == []
    assert response['authorized_coverage']['selected'] == 0


def test_system_replay_includes_when_both_cutoffs_satisfied():
    query, bundle = load_bundle_case('recorded_later')
    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-06-30T00:00:00Z', recorded_cutoff='2026-06-30T00:00:00Z')
    response = compose_semiconductor_research(replay, bundle)
    rows = _capacity_rows(response)
    assert rows, 'retained before the recorded cutoff and available before the source cutoff → included'
    assert response['authorized_coverage']['selected'] == len(bundle.assertions)


def test_system_replay_excludes_source_retained_after_recorded_cutoff():
    query, bundle = load_bundle_case('recorded_later')
    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-06-30T00:00:00Z', recorded_cutoff='2026-03-01T00:00:00Z')
    response = compose_semiconductor_research(replay, bundle)
    assert _capacity_rows(response) == [], 'the system had not recorded the artifact yet at that instant'


def test_system_replay_requires_both_cutoffs():
    query, bundle = load_bundle_case('recorded_later')
    for variant in (
        replace(query, time_mode='system_replay', source_cutoff=None, recorded_cutoff='2026-06-30T00:00:00Z'),
        replace(query, time_mode='system_replay', source_cutoff='2026-06-30T00:00:00Z', recorded_cutoff=None),
    ):
        with pytest.raises(ResearchRefusal) as exc:
            compose_semiconductor_research(variant, bundle)
        assert exc.value.code == 'replay_cutoffs_required'


# ─────────────────────────────────────────────────────────────────────────────
# Unknown availability
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize('available_at', ['unknown', None])
def test_replay_excludes_unknown_availability_with_limitation(available_at):
    query, bundle = load_bundle_case('recorded_later')
    body = copy.deepcopy(dict(bundle.assertions[0]))
    if available_at is None:  # an absent key is the only null form the schema allows
        body['source'].pop('available_at', None)
    else:
        body['source']['available_at'] = available_at
    body['curation_revision'] = None
    unknown = json.loads(encode_assertion(body))
    b2 = replace(bundle, assertions=(unknown,))
    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-06-30T00:00:00Z', recorded_cutoff='2026-06-30T00:00:00Z')
    response = compose_semiconductor_research(replay, b2)
    assert _capacity_rows(response) == []
    assert 'availability_unknown_excluded' in response['limitations']


def test_latest_mode_does_not_exclude_unknown_availability():
    query, bundle = load_bundle_case('recorded_later')
    unknown = _restamp_source(bundle.assertions[0], available_at='unknown')
    b2 = replace(bundle, assertions=(unknown,))
    response = compose_semiconductor_research(
        replace(query, time_mode='latest', source_cutoff=None, recorded_cutoff=None), b2)
    assert _capacity_rows(response), 'latest does not gate on availability'


# ─────────────────────────────────────────────────────────────────────────────
# Same-day grain ambiguity — never synthesize midnight
# ─────────────────────────────────────────────────────────────────────────────


def test_replay_same_day_date_only_publication_excluded():
    query, bundle = load_bundle_case('recorded_later')
    same_day = _restamp_source(
        bundle.assertions[0],
        published_at='2026-02-10',
        published_at_grain='date',
        available_at='2026-02-10T09:30:00Z',
    )
    b2 = replace(bundle, assertions=(same_day,))
    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-02-10T12:00:00Z', recorded_cutoff='2026-06-30T00:00:00Z')
    response = compose_semiconductor_research(replay, b2)
    assert _capacity_rows(response) == [], (
        'a date-only publication on the cutoff day cannot be placed before or after the cutoff instant'
    )
    assert 'same_day_grain_ambiguous' in response['limitations']


def test_replay_prior_day_date_only_publication_included():
    query, bundle = load_bundle_case('recorded_later')
    prior_day = _restamp_source(
        bundle.assertions[0],
        published_at='2026-02-09',
        published_at_grain='date',
        available_at='2026-02-09T09:30:00Z',
    )
    b2 = replace(bundle, assertions=(prior_day,))
    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-02-10T12:00:00Z', recorded_cutoff='2026-06-30T00:00:00Z')
    response = compose_semiconductor_research(replay, b2)
    assert _capacity_rows(response), 'a full day of margin is not ambiguous'


# ─────────────────────────────────────────────────────────────────────────────
# Identity: late mapping never resolves retroactively; 1970 epoch is not evidence
# ─────────────────────────────────────────────────────────────────────────────


def test_late_mapping_degrades_identity_in_replay():
    query, bundle = load_bundle_case('witness_hbm_packaging')
    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-05-01T00:00:00Z', recorded_cutoff='2026-05-01T00:00:00Z')
    response = compose_semiconductor_research(replay, bundle)
    rows = {row['source_business_label']: row for row in response['companies']['rows']}
    anchor = rows['Synthetic Foundry Alpha']
    assert anchor['company_node_id'] is None, 'a mapping learned after the cutoff never resolves retroactively'
    assert anchor['navigation']['status'] == 'unavailable'
    assert anchor['navigation']['reason'] == 'identity_not_yet_learned'
    # a mapping learned before the cutoff stays resolved
    early = rows['Synthetic Substrate Vendor Delta']
    assert early['company_node_id'] is not None
    assert early['navigation']['status'] == 'ready'


def test_epoch_listing_valid_from_is_not_evidence_of_listing():
    query, bundle = load_bundle_case('witness_hbm_packaging')
    anchor_result = next(
        r for r in bundle.identity_results
        if r['source_business_label'] == 'Synthetic Foundry Alpha'
    )
    epoch = dict(anchor_result)
    epoch['listing_valid_from'] = '1970-01-01'  # the epoch placeholder must not prove ancient listing

    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-05-01T00:00:00Z', recorded_cutoff='2026-05-01T00:00:00Z')
    degraded = compose_semiconductor_research(replay, replace(bundle, identity_results=(epoch,)))
    row = next(r for r in degraded['companies']['rows']
               if r['source_business_label'] == 'Synthetic Foundry Alpha')
    assert row['company_node_id'] is None, (
        '1970-01-01 is not historical evidence for any as-of before mapping_learned_at'
    )

    # after the mapping was learned, the identity resolves — the MAPPING is the evidence, not the epoch
    after = replace(query, time_mode='system_replay',
                    source_cutoff='2026-06-01T00:00:00Z', recorded_cutoff='2026-06-01T00:00:00Z')
    resolved = compose_semiconductor_research(after, replace(bundle, identity_results=(epoch,)))
    row = next(r for r in resolved['companies']['rows']
               if r['source_business_label'] == 'Synthetic Foundry Alpha')
    assert row['company_node_id'] is not None


def test_replay_with_pre_event_cutoffs_loses_the_witness_economics():
    # events recorded after the recorded_cutoff must not leak into a replay
    query, bundle = load_bundle_case('witness_hbm_packaging')
    replay = replace(query, time_mode='system_replay',
                     source_cutoff='2026-05-01T00:00:00Z', recorded_cutoff='2026-05-01T00:00:00Z')
    response = compose_semiconductor_research(replay, bundle)
    assert response['economics']['witness_gate'] == 'missing'


# ─────────────────────────────────────────────────────────────────────────────
# Stale interpretation labelling
# ─────────────────────────────────────────────────────────────────────────────


def test_corrected_interpretation_marks_stale_and_keeps_new_observation():
    query, bundle = load_bundle_case('corrected_interpretation')
    response = compose_semiconductor_research(query, bundle)
    summary = response['summary']
    stale = [item for item in summary['why_it_matters'] if item.get('stale')]
    assert stale, 'the superseded block is emitted with stale: true'
    assert all(item['text'].startswith('[stale interpretation] ') for item in stale)
    assert all(item['label'] == 'interpretation' for item in stale)
    current = [item for item in summary['why_it_matters'] if not item.get('stale')]
    assert current, 'the supported interpretation stays visible unlabelled'
    facts = [item for item in summary['what_changed'] if item['label'] == 'fact']
    assert facts, 'the newly supported observation stays visible as a fact'
    assert summary['status'] == 'degraded', 'new facts cannot retain stale causal text as one ready generation'
    assert response['economics']['witness_gate'] == 'missing'


def test_freshness_stale_block_is_labelled_stale_even_with_selected_inputs():
    query, bundle = load_bundle_case('corrected_interpretation')
    first = compose_semiconductor_research(query, bundle)
    fresh_revision = first['summary']['what_changed'][0]['input_refs'][0]
    block = dict(bundle.interpretation_blocks[0])
    block['input_revisions'] = [fresh_revision]  # ⊆ selected now…
    block['freshness'] = 'stale'                  # …but the owner marked it stale
    b2 = replace(bundle, interpretation_blocks=(block,))
    second = compose_semiconductor_research(query, b2)
    why = second['summary']['why_it_matters']
    stale = [item for item in why if item.get('stale')]
    assert stale and stale[0]['text'].startswith('[stale interpretation] ')
    # no clean interpretation item may carry the stale-marked revision
    clean_carrying = [item for item in why if not item.get('stale')
                      and fresh_revision in item['input_refs']
                      and item['label'] == 'interpretation']
    assert not clean_carrying
    assert second['summary']['status'] == 'degraded'
