"""Native immutable ledger through the real page builder; mutations are controls."""
import copy
import json
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from engine.capital_structure.covenant_terms import observation_id_for
from engine.capital_structure.source_ledger_io import write_source_ledger
from engine.covenant_headroom import compute_headroom
from scripts.build_capital_structure_page import _covenant_headroom
from scripts.compile_capital_structure_covenant_terms import _to_frame

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / 'tests/fixtures/capital_structure/covenant_eprt_native.json'


def native():
    return json.loads(NATIVE.read_text())


def seed(root, observations=None, manifest=None):
    fixture = native()
    data = root / 'data/capital_structure'; data.mkdir(parents=True, exist_ok=True)
    write_source_ledger([manifest or fixture['manifest']], data / 'source_manifest.jsonl')
    _to_frame(observations if observations is not None else [fixture['observation']]).to_parquet(data / 'covenant_term_observations.parquet', index=False)


def template(payload):
    env = Environment(loader=FileSystemLoader(str(ROOT / 'templates')), autoescape=True, undefined=StrictUndefined)
    return env.get_template('capital_structure.html.j2').render(active_section='research', active_page='capital_structure', covenant_headroom=payload)


def test_native_contract_is_consumed_without_inventing_financial_inputs():
    row = native()['observation']
    model = compute_headroom([row], {}, {'0001728951': 'EPRT'})
    assert model['issuer']['cik'] == '0001728951'
    assert model['state'] == 'refused'
    term = model['terms'][0]
    assert term['term_name'] == 'minimum_fixed_charge_coverage_ratio'
    assert term['filing_term_raw'] == '1.50 to 1.00'
    assert term['receipt']['filing_date'] == '2026-09-16'  # not observation/retention date
    assert term['receipt']['source_url'] == row['document']['canonical_url']
    assert term['limit_raw'] is None and term['room_turns'] is None and term['inside_limit'] is None


def test_actual_source_lineage_reaches_rendered_page(tmp_path):
    seed(tmp_path)
    model = _covenant_headroom(tmp_path)
    html = template(model)
    assert model['issuer']['ticker'] == 'EPRT'
    for text in ['1.50 to 1.00', 'Minimum fixed-charge coverage', '最低固定费用覆盖倍数', '2026-09-16', '0001728951-26-000066', 'EPRT']:
        assert text in html
    assert 'financial inputs' in html and '财务输入' in html
    assert 'capital_structure.covenant_term_observation.v1' not in html


def test_absent_ledger_renders_honest_unavailable(tmp_path):
    assert _covenant_headroom(tmp_path)['refusal'] == 'no_terms_extracted'


@pytest.mark.parametrize('mutate,reason', [
    (lambda row: row['document'].__setitem__('content_sha256', '0'*64), 'detached'),
    (lambda row: row.__setitem__('issuer_id', 'sec:cik:0000000001'), 'issuer'),
    (lambda row: row['document'].__setitem__('canonical_url', 'https://example.org/fake'), 'citation'),
])
def test_detached_or_wrong_issuer_source_cannot_publish(tmp_path, mutate, reason):
    row = native()['observation']; mutate(row); row['observation_id'] = observation_id_for(row)
    seed(tmp_path, [row])
    with pytest.raises(ValueError, match=reason): _covenant_headroom(tmp_path)


def test_inconsistent_transcription_fails_even_when_source_version_id_matches(tmp_path):
    row = native()['observation']; row['reported']['raw'] = '9.99 to 1.00'
    assert observation_id_for(row) == row['observation_id']  # not a full-content digest
    seed(tmp_path, [row])
    with pytest.raises(ValueError, match='transcription'): _covenant_headroom(tmp_path)


def test_public_fact_only_cannot_publish_arbitrary_source_prose(tmp_path):
    row = native()['observation']
    row['reported']['raw'] = row['normalized']['raw'] = 'Unbounded source prose'
    seed(tmp_path, [row])
    with pytest.raises(ValueError, match='literal ratio'): _covenant_headroom(tmp_path)


def test_out_of_bounds_source_span_fails(tmp_path):
    row = native()['observation']
    row['evidence']['spans'][0]['locator'] = 'bytes:9000000-9000012'
    seed(tmp_path, [row])
    with pytest.raises(ValueError, match='out of bounds'): _covenant_headroom(tmp_path)


@pytest.mark.parametrize('key,value', [('rights_class','internal_only'), ('privacy_classification','restricted')])
def test_nonpublic_source_is_not_in_static_html(tmp_path, key, value):
    row = native()['observation']; row['evidence'][key] = value; row['observation_id'] = observation_id_for(row)
    seed(tmp_path, [row])
    assert '1.50 to 1.00' not in template(_covenant_headroom(tmp_path))


def test_newer_ambiguous_correction_does_not_resurrect_old_direct_term(tmp_path):
    first = native()['observation']; second = copy.deepcopy(first)
    second['state'] = {'disposition':'ambiguous','reason':'ambiguous_extraction'}
    second['version'].update(correction_version=2, correction_of=first['observation_id'])
    second['observation_id'] = observation_id_for(second)
    seed(tmp_path, [first, second])
    result = _covenant_headroom(tmp_path)
    assert result['refusal'] == 'terms_ambiguous' and not result['terms']


def test_future_record_cannot_be_published_now(tmp_path):
    row = native()['observation']; row['point_in_time']['available_at'] = '2099-01-01T00:00:00Z'; row['observation_id'] = observation_id_for(row)
    seed(tmp_path, [row]); assert not _covenant_headroom(tmp_path)['terms']


def test_existing_nightly_covenant_step_has_shared_source_namespace():
    workflow = yaml.safe_load((ROOT / '.github/workflows/daily.yml').read_text())
    step = next(s for job in workflow['jobs'].values() for s in job.get('steps', []) if s.get('run') == 'python -m scripts.compile_capital_structure_covenant_terms')
    for key in ['R2_ENDPOINT','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET']:
        assert step['env'][key] == '${{ secrets.' + key + ' }}'
