"""tests/test_semiconductor_research_inputs.py — input-contract tests for the
synthetic semiconductor theme research fixture corpus.

These tests pin the loader contract and the fixture-shape contract for the
T01 inputs of operation gmi-semiconductors-fable-ceo-e2e-20260923-chairman-001.
No native paid data may land in this corpus; every fixture must be explicitly
flagged synthetic, self-named, and free of real issuer identity. The two
positive witnesses (W-A, W-B) carry the full management-sequence payload
that later tasks (T05, T07, T08, T11) will operate on.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from tests.semiconductor_research_helpers import FIXTURE_ROOT, load_case


WITNESS_NAMES = ('witness_hbm_packaging', 'witness_sic_gan')
TASK_REF_PATTERN = re.compile(r'^T(0[1-9]|1[0-2])$')


def _all_fixture_paths() -> list[Path]:
    return sorted(FIXTURE_ROOT.glob('*.json'))


def test_two_positive_witnesses_have_three_distinct_economic_roles():
    for name in WITNESS_NAMES:
        case = load_case(name)
        assert case['synthetic'] is True
        assert set(case['management_roles']) == {'prior_outlook', 'actual', 'new_outlook'}
        assert case['required_company_link'] is True
        assert case['optional_external_consensus'] == 'unavailable'


def test_every_fixture_is_explicitly_synthetic_and_self_named():
    paths = _all_fixture_paths()
    assert paths, 'fixture corpus must contain at least one json file'
    for path in paths:
        with path.open() as fh:
            value = json.load(fh)
        assert isinstance(value, dict), f'{path.name}: top-level must be dict'
        assert value.get('synthetic') is True, f'{path.name}: synthetic must be True'
        assert value.get('case_key') == path.stem, f'{path.name}: case_key must match stem'
        task_refs = value.get('task_refs')
        assert isinstance(task_refs, list) and task_refs, f'{path.name}: task_refs must be non-empty list'
        for ref in task_refs:
            assert isinstance(ref, str) and TASK_REF_PATTERN.match(ref), (
                f'{path.name}: task_ref {ref!r} does not match T01..T12'
            )
        expected_regression = value.get('expected_regression')
        assert isinstance(expected_regression, str) and expected_regression, (
            f'{path.name}: expected_regression must be a non-empty string'
        )
        assert value.get('status') in {'ready', 'stub_pending'}, (
            f'{path.name}: status must be ready or stub_pending'
        )


def test_stub_fixtures_carry_no_invented_data():
    expected_keys = {'synthetic', 'case_key', 'task_refs', 'expected_regression', 'status'}
    for path in _all_fixture_paths():
        with path.open() as fh:
            value = json.load(fh)
        if value.get('status') != 'stub_pending':
            continue
        assert set(value.keys()) == expected_keys, (
            f'{path.name}: stub keys are exactly {sorted(expected_keys)}, got {sorted(value.keys())}'
        )


def test_fixture_corpus_contains_no_real_issuer_identity():
    forbidden = (
        'tsmc', 'taiwan semiconductor', 'onsemi', 'on semiconductor',
        '1046179', '1097864', 'investor.', 'sec.gov', 'http://', 'https://',
    )
    blob_parts: list[str] = []
    for path in _all_fixture_paths():
        blob_parts.append(path.read_text().lower())
    blob = '\n'.join(blob_parts)
    for needle in forbidden:
        assert needle not in blob, f'fixture corpus contains forbidden token {needle!r}'


def test_loader_refuses_invalid_names_and_non_synthetic(tmp_path, monkeypatch):
    fake_root = tmp_path / 'semiconductor_theme_research'
    fake_root.mkdir()

    bad_payload = fake_root / 'x.json'
    bad_payload.write_text(json.dumps({'synthetic': True}))
    monkeypatch.setattr('tests.semiconductor_research_helpers.FIXTURE_ROOT', fake_root)
    # invalid name characters
    try:
        load_case('../x')
    except ValueError:
        pass
    else:
        raise AssertionError('load_case("../x") should have raised ValueError')

    # synthetic=false
    (fake_root / 'a.json').write_text(json.dumps({'synthetic': False}))
    try:
        load_case('a')
    except ValueError:
        pass
    else:
        raise AssertionError('load_case with synthetic=false should have raised ValueError')

    # synthetic missing
    (fake_root / 'b.json').write_text(json.dumps({'case_key': 'b'}))
    try:
        load_case('b')
    except ValueError:
        pass
    else:
        raise AssertionError('load_case with synthetic missing should have raised ValueError')


def test_witness_new_outlook_is_a_later_period_not_a_revision():
    for name in WITNESS_NAMES:
        case = load_case(name)
        sequence = case['management_sequence']
        assert sequence['new_outlook']['fiscal_period'] != sequence['actual']['fiscal_period'], (
            f'{name}: new_outlook must target a later period than actual'
        )
        assert sequence['prior_outlook']['fiscal_period'] == sequence['actual']['fiscal_period'], (
            f'{name}: prior_outlook must target the same period as actual'
        )
        comparability = case['comparability']
        assert comparability['actual_vs_new_outlook'] == 'different_period_not_comparable', (
            f'{name}: actual vs new_outlook comparability must be different_period_not_comparable'
        )
        assert sequence['actual']['statement_mode'] == 'REPORTED_FACT'
        assert sequence['prior_outlook']['statement_mode'] == 'FORWARD_TARGET'
        assert sequence['new_outlook']['statement_mode'] == 'FORWARD_TARGET'


def test_witness_query_matches_research_query_field_set():
    query_keys = {
        'anchor_theme_id', 'slice_key', 'view', 'time_mode',
        'source_cutoff', 'recorded_cutoff', 'offset', 'limit', 'expected_generation',
    }
    bundle_keys = {
        'revision_tuple', 'rights_revision', 'assertions', 'identity_results',
        'event_workspaces', 'financial_packets', 'interpretation_blocks',
        'native_refs', 'omissions',
    }
    valid_slices = {'hbm_packaging', 'sic_gan_specialty'}
    valid_views = {'composition', 'manufacturing', 'commercial', 'capacity', 'economics'}
    valid_time_modes = {'latest', 'source_history', 'system_replay'}
    for name in WITNESS_NAMES:
        case = load_case(name)
        assert set(case['query'].keys()) == query_keys, (
            f'{name}: query keys must equal {sorted(query_keys)}'
        )
        assert case['query']['slice_key'] in valid_slices, f'{name}: slice_key invalid'
        assert case['query']['view'] in valid_views, f'{name}: view invalid'
        assert case['query']['time_mode'] in valid_time_modes, f'{name}: time_mode invalid'
        assert set(case['bundle'].keys()) == bundle_keys, (
            f'{name}: bundle keys must equal {sorted(bundle_keys)}'
        )


def test_sic_gan_witness_makes_no_ai_assumption():
    case = load_case('witness_sic_gan')
    assert case['ai_assumption'] is False
    assert case['slice_key'] == 'sic_gan_specialty'


def test_witness_issuer_identity_is_unbound_in_fixtures():
    for name in WITNESS_NAMES:
        case = load_case(name)
        issuer = case['issuer']
        assert issuer['company_node_id'] is None
        assert issuer['cik'] is None
