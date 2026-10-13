"""P1/A34 hostile qualification cases over the existing D2 identity owner."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from engine.government_revenue.entity_resolution import load_recipient_entity_graph

CONTRIBUTION = Path(__file__).resolve().parents[1]
if (CONTRIBUTION / 'archetype_extension.py.txt').exists():
    spec = importlib.util.spec_from_file_location(
        'engine.government_revenue.identity_atlas_archetype_test',
        CONTRIBUTION / 'engine/government_revenue/identity_atlas.py')
    ia = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ia)
else:
    from engine.government_revenue import identity_atlas as ia


@pytest.fixture
def inputs():
    graph = json.loads((CONTRIBUTION / 'tests/fixtures/government_revenue/archetypes/recipient_entity_graph.json').read_text())
    curated = json.loads((CONTRIBUTION / 'tests/fixtures/government_revenue/archetypes/identity_atlas_curated.json').read_text())
    return graph, curated


def build(inputs, **kwargs):
    graph, curated = inputs
    return ia.build_identity_atlas(graph=graph, curated=curated,
        generated_at=curated['generated_at'], **kwargs)


def issuer(payload, ticker):
    return next(row for row in payload['issuers'] if row['ticker'] == ticker)


def test_real_jv_owner_graph_admitted_and_hash_qualified(inputs):
    graph, _ = inputs
    assert load_recipient_entity_graph(graph, as_of=graph['graph_known_at'])['status'] == 'ready'
    out = build(inputs)
    assert ia.is_valid_identity_atlas_payload(out)
    case = issuer(out, 'LMT')['archetype_context']['ownership_cases'][0]
    assert case['documentary_counterparties'] == [{'name_as_printed': 'The Boeing Company', 'ownership_interest': 0.5, 'identity_path': 'not_established'}]
    assert case['ownership_interest'] == 0.5
    assert case['accounting_basis'] == 'equity_method'
    assert case['source_as_of'] == '2026-06-28'
    assert case['effective_interval_state'] == 'disclosed_snapshot_only'
    assert case['recipient_attribution'] == 'not_established'
    assert case['revenue_capture'] == case['workshare'] == case['cash_capture'] == 'not_established'
    assert case['interest_basis'] == 'direct_edge_interest_not_issuer_capture'


def test_foreign_parent_and_otc_adr_are_distinct_and_nonlive(inputs):
    out = build(inputs)
    row = issuer(out, 'BAESY')
    assert row['public_security']['state'] == 'not_in_si_universe'
    assert row['issuer_attribution'] == 'not_asserted'
    listings = row['archetype_context']['listing_cases']
    assert len(listings) == 2
    ordinary, adr = listings
    assert ordinary['native_identity']['issuer_native_id'] == adr['native_identity']['issuer_native_id'] == '01470151'
    assert ordinary['native_identity']['venue'] != adr['native_identity']['venue']
    assert ordinary['native_identity']['security_kind'] == 'ordinary_share'
    assert adr['native_identity']['security_kind'] == 'adr'
    assert ordinary['ordinary_shares_per_adr'] is None
    assert adr['ordinary_shares_per_adr'] == 4
    assert adr['quote_currency'] == 'USD'
    assert all(x['listing_admission'] == x['economic_capture'] == 'not_established' for x in listings)
    assert all(x['rights_state'] == 'unknown' and x['state'] == 'source_observed' for x in listings)


def test_old_cutoff_excludes_later_known_jv_and_foreign_observation(inputs):
    out = build(inputs, graph_as_of='2026-08-19T12:00:00+00:00')
    assert issuer(out, 'LMT')['archetype_context']['ownership_cases'] == []
    assert issuer(out, 'BAESY')['archetype_context']['listing_cases'] == []


@pytest.mark.parametrize('field,value', [('known_at', '2099-01-01T00:00:00Z'),
    ('review_state', 'not_reviewed'), ('valid_to', '2026-09-01T00:00:00Z')])
def test_foreign_unreviewed_future_known_and_expired_are_absent(inputs, field, value):
    inputs = copy.deepcopy(inputs)
    for row in inputs[1]['issuers']['BAESY']['listing_qualifications']:
        row[field] = value
    assert issuer(build(inputs), 'BAESY')['archetype_context']['listing_cases'] == []


def test_unknown_accounting_does_not_imply_consolidation(inputs):
    inputs = copy.deepcopy(inputs)
    inputs[1]['issuers']['LMT']['ownership_qualifications'] = []
    context = issuer(build(inputs), 'LMT')['archetype_context']
    assert context['ownership_cases'][0]['accounting_basis'] == 'not_established'
    assert 'accounting_basis_not_established' in context['gaps']


def test_ownership_metadata_cannot_attach_by_name_or_ticker(inputs):
    inputs = copy.deepcopy(inputs)
    inputs[1]['issuers']['LMT']['ownership_qualifications'][0]['entity_id'] = 'legal:other:same-name'
    case = issuer(build(inputs), 'LMT')['archetype_context']['ownership_cases'][0]
    assert case['accounting_basis'] == 'not_established'


def test_ownership_interest_mismatch_cannot_change_graph(inputs):
    inputs = copy.deepcopy(inputs)
    inputs[1]['issuers']['LMT']['ownership_qualifications'][0]['ownership_interest'] = 1
    case = issuer(build(inputs), 'LMT')['archetype_context']['ownership_cases'][0]
    assert case['ownership_interest'] == 0.5 and case['accounting_basis'] == 'not_established'


@pytest.mark.parametrize('ratio', [None, True, 0, -4, float('nan')])
def test_adr_bad_ratio_cannot_confer_security_equivalence(inputs, ratio):
    inputs = copy.deepcopy(inputs)
    inputs[1]['issuers']['BAESY']['listing_qualifications'][1]['ordinary_shares_per_adr'] = ratio
    out = issuer(build(inputs), 'BAESY')['archetype_context']
    assert len(out['listing_cases']) == 1
    assert 'adr_ratio_not_established' in out['gaps']


def test_unsafe_source_link_and_missing_hash_do_not_enter_context(inputs):
    inputs = copy.deepcopy(inputs)
    for row in inputs[1]['issuers']['BAESY']['listing_qualifications']:
        row['evidence'][0]['url'] = 'javascript:alert(1)'
    assert issuer(build(inputs), 'BAESY')['archetype_context']['listing_cases'] == []


def test_frozen_irdm_d4_and_historical_acquisition_are_preserved(inputs):
    graph, curated = inputs
    out = build(inputs)
    assert issuer(out, 'IRDM')['issuer_attribution'] == 'reviewed'
    assert issuer(out, 'SPR')['public_security']['state'] == 'listing_terminated'
    assert issuer(out, 'SPR')['listing_events'][0]['event'] == 'acquisition_close'
    assert all(out['authority'][key] is False for key in ('can_rank', 'can_size', 'can_gate', 'can_originate_signal'))
    assert inputs == (graph, curated)


def test_no_bespoke_ticker_branch_or_award_money_calculation():
    source = Path(ia.__file__).read_text()
    start = source.index('def _archetype_context(')
    end = source.index('# Per-issuer assembly', start)
    body = source[start:end]
    assert not any(ticker in body for ticker in ('LMT', 'BAESY', 'IRDM', 'HII'))
    assert 'attributable_amount' not in body and 'government_amount' not in body
