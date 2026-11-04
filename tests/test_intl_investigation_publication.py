"""Trusted source composition reaches the optional in-memory Investigation sink."""
from copy import deepcopy

import pytest

from lib import config
from scripts.build_intl import _publication_workspace
from tests.test_intl_eod_publication import _setup
from tests.test_intl_real_field_publication import annual_materialized, yield_materialized, EVALUATED


IDS = ['JP.yield_10y', 'JP.annual_current_account']


def request():
    return {
        'context': {
            'researchMarket': 'JP', 'toolBindingVersion': '2', 'periodIdentity': '3m',
            'currencyBasis': 'local', 'returnBasis': 'price',
            'owner': 'test-only-intl-source-owner', 'query': 'Explicit test source question',
            'cohort': 'test-only-JP-fields', 'temporalPolicy': 'test-only-current-materialization',
            'selectedMeasureIds': IDS.copy(),
        },
        'requirements': {'requiredMeasureIds': IDS.copy(), 'unmetPrerequisites': []},
        'owner': {
            'lang': 'en', 'question': 'Explicit test source question',
            'marketLabel': 'Japan', 'toolLabel': 'International', 'periodLabel': '3 months',
            'basisLabel': 'Local price', 'savedAt': None, 'updatedAt': None,
            'sourceGenerationAt': None, 'rightsAt': None,
            'measureLabels': {'JP.yield_10y': '10-year yield',
                              'JP.annual_current_account': 'Annual current account'},
            'unmetLabels': [],
        },
        'prior': None, 'prior_authorized': False, 'read': 'ok', 'membership': 'complete',
        'enumerated_measure_ids': IDS.copy(), 'facts': {}, 'tombstones': [],
    }


def setup_sources(tmp_path, monkeypatch, *, adopt=True):
    frame, _ = _setup(tmp_path)
    annual_materialized(tmp_path)
    yield_materialized(tmp_path)
    cfg = deepcopy(config.load())
    cfg['intl']['field_publication'] = {
        sid: {'status': 'confirmed', 'policy_ref': 'INTERNAL_TEST_ONLY:explicit-source-fixture',
              'metadata': 'allowed', 'value_permission': 'allowed'} for sid in IDS
    } if adopt else {}
    monkeypatch.setattr(config, 'load', lambda: cfg)
    return frame


def test_normal_publication_sink_preserves_actual_generation_and_original_source_clocks(tmp_path, monkeypatch):
    frame = setup_sources(tmp_path, monkeypatch)
    sink = {}
    workspace = _publication_workspace(frame, data_root=tmp_path, evaluated_at=EVALUATED,
                                        investigation_request=request(), investigation_sink=sink)
    packet = sink['packet']
    assert packet['prior'] is None
    assert packet['current']['generation'] == workspace['config']['source_reference']
    assert packet['exactContext'] == request()['context']
    observations = {x['id']: x for x in packet['current']['observations']}
    assert observations[IDS[0]]['interpretation']['value'] == 1.7
    assert observations[IDS[1]]['interpretation']['value'] == 4.125
    assert all(x['qualified'] and x['qualificationIdentity'] for x in observations.values())
    assert packet['owner']['savedAt'] is packet['owner']['sourceGenerationAt'] is None
    assert packet['owner']['observedAtByMeasureId'] == {
        'JP.yield_10y': '2026-10-01', 'JP.annual_current_account': '2026-09-24'}
    # The private packet is not inserted into public/template workspace state.
    assert 'investigation' not in workspace and 'packet' not in workspace
    assert '2026-10-13T02:00:00Z' in str(sink['provenance'])
    assert '2026-09-24' in str(sink['provenance'])


def test_normal_publisher_missing_adoption_cannot_issue_qualification_or_dynamic_metadata(tmp_path, monkeypatch):
    frame = setup_sources(tmp_path, monkeypatch, adopt=False)
    sink = {}
    _publication_workspace(frame, data_root=tmp_path, evaluated_at=EVALUATED,
                           investigation_request=request(), investigation_sink=sink)
    assert all(x['interpretation'] is None and x['qualificationIdentity'] is None
               for x in sink['packet']['current']['observations'])
    assert 'https://' not in str(sink['provenance'])
    assert '2026-10-13' not in str(sink['provenance'])


@pytest.mark.parametrize(('field', 'value'), [
    ('researchMarket', 'US'), ('periodIdentity', '99m'),
    ('currencyBasis', 'EUR'), ('returnBasis', 'total'), ('toolBindingVersion', '1'),
])
def test_caller_scope_cannot_widen_the_native_workspace(tmp_path, monkeypatch, field, value):
    frame = setup_sources(tmp_path, monkeypatch)
    req = request(); req['context'][field] = value
    with pytest.raises(ValueError):
        _publication_workspace(frame, data_root=tmp_path, evaluated_at=EVALUATED,
                               investigation_request=req, investigation_sink={})


def test_explicit_selection_is_not_all_available_fields(tmp_path, monkeypatch):
    frame = setup_sources(tmp_path, monkeypatch)
    req = request(); req['context']['selectedMeasureIds'] = IDS[:1]
    req['enumerated_measure_ids'] = IDS[:1]; req['requirements']['requiredMeasureIds'] = IDS[:1]
    req['owner']['measureLabels'] = {IDS[0]: '10-year yield'}
    sink = {}
    _publication_workspace(frame, data_root=tmp_path, evaluated_at=EVALUATED,
                           investigation_request=req, investigation_sink=sink)
    assert [x['id'] for x in sink['packet']['current']['observations']] == IDS[:1]


@pytest.mark.parametrize('kwargs', [
    {'investigation_request': request()}, {'investigation_sink': {}},
    {'investigation_request': request(), 'investigation_sink': {'occupied': True}},
])
def test_sink_is_optional_paired_and_cannot_overwrite_prior_result(tmp_path, kwargs):
    with pytest.raises(ValueError, match='invalid_international_investigation_sink'):
        _publication_workspace(None, data_root=tmp_path, evaluated_at=EVALUATED, **kwargs)


def test_mismatched_native_panel_generation_cannot_issue_a_packet(tmp_path):
    from engine.intl_workspace_overview import build_workspace_overviews
    from scripts.build_intl import _project_investigation_sink
    frame, _ = _setup(tmp_path)
    workspace = build_workspace_overviews(frame,
        workspace_generation='im-workspace-generation:df4a2d6b-aed5-4d0c-a211-68f3a4627eb4')
    workspace['panels'][0]['generation'] = 'im-workspace-generation:dc93afef-841f-44be-b068-5df89d15a37c'
    with pytest.raises(ValueError, match='workspace_scope_mismatch'):
        _project_investigation_sink(workspace=workspace, request=request(), sink={},
                                   measures={}, materialized={}, decisions={})


def test_actual_ecb_reader_column_descriptor_is_projected_to_exact_receipt_pair(tmp_path):
    import json
    from tests.test_intl_ecb_deposit_admission import inputs as ecb_inputs
    from lib.intl_macro_publication import read_ecb_deposit_materialization
    frame, _ = _setup(tmp_path)
    source = ecb_inputs()
    directory = tmp_path / 'intl_macro'; directory.mkdir()
    source['series'].to_frame().to_parquet(directory / 'ez_depo_rate.parquet')
    (directory / 'provenance.json').write_text(json.dumps({'series': {'ez_depo_rate': source['provenance']}}))
    owned = read_ecb_deposit_materialization(data_root=tmp_path)
    assert set(owned['materialized_identity']) == {'column', 'artifact_sha256', 'provenance_sha256'}
    req = request(); selected = ['EZ.policy_rate']
    req['context'].update(researchMarket='EZ', selectedMeasureIds=selected)
    req['requirements']['requiredMeasureIds'] = selected
    req['enumerated_measure_ids'] = selected
    req['owner']['measureLabels'] = {'EZ.policy_rate': 'ECB deposit facility rate'}
    sink = {}
    workspace = _publication_workspace(frame, data_root=tmp_path, evaluated_at='2026-10-07T10:00:00Z',
                                       investigation_request=req, investigation_sink=sink)
    observation = sink['packet']['current']['observations'][0]
    assert observation['qualified'] and observation['interpretation']['value'] == 2.5
    assert set(sink['provenance']['measures']['EZ.policy_rate']['receiptIdentity']) == {'artifact_sha256', 'provenance_sha256'}
    assert observation['qualificationIdentity'] is not None
    assert workspace['config']['source_reference'] == sink['packet']['current']['generation']
