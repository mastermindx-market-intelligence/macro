"""Five existing collector contracts, checked on hermetic actual producer output."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pandas as pd
import pytest
from jsonschema import Draft202012Validator

from collectors import sbir_awards as sbir
from tests.test_sbir_awards import (
    CELL, CELLS, OBSERVED, OBSERVED_2, _FixtureSession, _award, _collector,
)


@pytest.fixture
def source_bundle(tmp_path):
    row = _award('schema-1')
    row['contract'] = None
    collector = _collector(tmp_path, _FixtureSession({CELL: [row]}))
    status = collector.collect(cells=CELLS, observed_at=OBSERVED)
    paths = collector._paths()
    state = json.loads(paths['state'].read_text())
    receipts = [json.loads(line) for line in paths['receipts'].read_text().splitlines()]
    frame = pd.read_parquet(paths['observations'])
    observation = {key: sbir._generation_value(frame.iloc[0][key]) for key in sbir.SBIR_OBSERVATION_COLUMNS}
    return collector, paths, frame, {
        sbir.SBIR_OBSERVATION_SCHEMA: observation,
        sbir.SBIR_COLLECTION_RECEIPT_SCHEMA: receipts[0],
        sbir.SBIR_PROJECTION_STATE_SCHEMA: state,
        sbir.SBIR_INGEST_STATUS_SCHEMA: status,
        sbir.SBIR_COVERAGE_MANIFEST_SCHEMA: status['coverage_manifest'],
    }


def test_actual_success_artifacts_validate_all_five_contracts(source_bundle):
    _, _, frame, artifacts = source_bundle
    for contract, artifact in artifacts.items():
        Draft202012Validator.check_schema(sbir._sbir_contract_validator(contract).schema)
        sbir.validate_sbir_source_contract(artifact, contract)
    sbir.validate_sbir_source_bundle(frame, artifacts[sbir.SBIR_PROJECTION_STATE_SCHEMA], artifacts[sbir.SBIR_INGEST_STATUS_SCHEMA])
    observation = artifacts[sbir.SBIR_OBSERVATION_SCHEMA]
    assert observation['contract'] is None
    assert 'schema_version' not in observation
    # Procurement number stays a nullable source field; it is never a schema tag.
    observation['contract'] = 'FA8650-SOURCE-1'
    sbir.validate_sbir_source_contract(observation, sbir.SBIR_OBSERVATION_SCHEMA)


def test_successful_empty_scoped_collection_validates_without_corpus_claim(tmp_path):
    collector = _collector(tmp_path, _FixtureSession({CELL: []}))
    status = collector.collect(cells=CELLS, observed_at=OBSERVED)
    state = json.loads(collector._paths()['state'].read_text())
    frame = pd.read_parquet(collector._paths()['observations'])
    sbir.validate_sbir_source_bundle(frame, state, status)
    assert status['observations_total'] == 0
    assert status['completeness']['full_sbir_corpus'] is False
    assert status['first_baseline'] is True


@pytest.mark.parametrize('contract', [sbir.SBIR_OBSERVATION_SCHEMA, sbir.SBIR_COLLECTION_RECEIPT_SCHEMA,
    sbir.SBIR_PROJECTION_STATE_SCHEMA, sbir.SBIR_INGEST_STATUS_SCHEMA, sbir.SBIR_COVERAGE_MANIFEST_SCHEMA])
@pytest.mark.parametrize('mutation', ['missing', 'private', 'raw', 'clock_or_authority'])
def test_closed_artifact_schemas_refuse_hostile_edits(source_bundle, contract, mutation):
    artifact = copy.deepcopy(source_bundle[3][contract])
    if mutation == 'missing':
        artifact.pop(next(iter(artifact)))
    elif mutation == 'private':
        if contract == sbir.SBIR_OBSERVATION_SCHEMA:
            artifact['poc_email'] = 'synthetic-private@example.invalid'
            artifact['observation_state_sha256'] = sbir._observation_state_sha256(artifact)
        else:
            target = artifact.get('coverage_manifest', artifact)
            target['pi_name'] = 'synthetic-private-value'
            if 'coverage_manifest_id' in artifact:
                artifact['coverage_manifest_id'] = sbir.sbir_coverage_manifest_id(target)
    elif mutation == 'raw':
        artifact['abstract'] = {'raw_response_body': 'synthetic-private-value'}
    elif contract == sbir.SBIR_COVERAGE_MANIFEST_SCHEMA:
        artifact['omissions']['full_sbir_corpus'] = True
    elif contract in {sbir.SBIR_PROJECTION_STATE_SCHEMA, sbir.SBIR_INGEST_STATUS_SCHEMA}:
        artifact['authority']['can_rank'] = True
    else:
        artifact['observed_at'] = '2026-02-30T12:00:00+00:00'
    with pytest.raises(ValueError, match='schema violation') as error:
        sbir.validate_sbir_source_contract(artifact, contract)
    assert 'synthetic-private' not in str(error.value)


@pytest.mark.parametrize('mutation', ['uei', 'hash', 'phase', 'nonfinite', 'backdated_known'])
def test_observation_shape_and_semantics_refuse_rehashed_bad_values(source_bundle, mutation):
    row = copy.deepcopy(source_bundle[3][sbir.SBIR_OBSERVATION_SCHEMA])
    if mutation == 'uei': row['uei'] = 'ABCDEFGHI012'  # Forbidden I/O alphabet.
    elif mutation == 'hash': row['source_response_sha256'] = 'x'*64
    elif mutation == 'phase': row['phase'] = 'III'
    elif mutation == 'nonfinite': row['award_amount'] = float('inf')
    else: row['known_at'] = '2020-01-01T00:00:00+00:00'
    if mutation != 'nonfinite':
        row['observation_state_sha256'] = sbir._observation_state_sha256(row)
    with pytest.raises(ValueError):
        if mutation == 'nonfinite': sbir.validate_sbir_source_contract(row, sbir.SBIR_OBSERVATION_SCHEMA)
        else: sbir._validate_sbir_observation_frame(pd.DataFrame([row], columns=sbir.SBIR_OBSERVATION_COLUMNS))


@pytest.mark.parametrize('mutation', ['generation', 'manifest', 'clock', 'count'])
def test_shape_valid_bundle_mutations_fail_cross_field_binding(source_bundle, mutation):
    _, _, frame, artifacts = source_bundle
    state = copy.deepcopy(artifacts[sbir.SBIR_PROJECTION_STATE_SCHEMA])
    status = copy.deepcopy(artifacts[sbir.SBIR_INGEST_STATUS_SCHEMA])
    if mutation == 'generation': status['projection_generation_id'] = 'sbir-'+'0'*24
    elif mutation == 'manifest': status['coverage_manifest_id'] = 'sbir-coverage-'+'0'*64
    elif mutation == 'clock': status['known_at'] = '2020-01-01T00:00:00+00:00'
    else: status['observations_total'] += 1
    sbir.validate_sbir_source_contract(state, sbir.SBIR_PROJECTION_STATE_SCHEMA)
    sbir.validate_sbir_source_contract(status, sbir.SBIR_INGEST_STATUS_SCHEMA)
    with pytest.raises(ValueError, match='semantic binding'):
        sbir.validate_sbir_source_bundle(frame, state, status)


@pytest.mark.parametrize('mutation', ['request_hash', 'receipt_id', 'query_private', 'offset', 'short_page'])
def test_shape_valid_receipt_cannot_lie_about_request_or_identity(source_bundle, mutation):
    receipt = copy.deepcopy(source_bundle[3][sbir.SBIR_COLLECTION_RECEIPT_SCHEMA])
    if mutation == 'request_hash': receipt['request_sha256'] = '0'*64
    elif mutation == 'receipt_id': receipt['receipt_id'] = 'sbir-award:'+'0'*64
    elif mutation == 'query_private': receipt['query'] += '&poc_email=synthetic-private'
    elif mutation == 'offset': receipt['offset'] += 1
    else: receipt['short_page'] = not receipt['short_page']
    with pytest.raises(ValueError, match='binding') as error:
        sbir.validate_sbir_source_contract(receipt, sbir.SBIR_COLLECTION_RECEIPT_SCHEMA)
    assert 'synthetic-private' not in str(error.value)


@pytest.mark.parametrize('mutation', ['rows_seen', 'rows_accepted', 'requests', 'phases', 'exhausted', 'cell_identity', 'run'])
def test_shape_valid_status_counts_and_cells_stay_bound(source_bundle, mutation):
    _, _, frame, artifacts = source_bundle
    state = copy.deepcopy(artifacts[sbir.SBIR_PROJECTION_STATE_SCHEMA])
    status = copy.deepcopy(artifacts[sbir.SBIR_INGEST_STATUS_SCHEMA])
    if mutation == 'rows_seen': status['rows_seen'] += 1
    elif mutation == 'rows_accepted': status['rows_accepted'] += 1
    elif mutation == 'requests': status['requests_this_run'] += 1
    elif mutation == 'phases': status['phase_counts_this_run']['II'] += 1
    elif mutation == 'exhausted': status['cells_source_exhausted'] = 0
    elif mutation == 'cell_identity': state['cells'][0]['agency'] = 'DOE'
    else: state['run_id'] = status['run_id'] = 'sbir-'+'0'*24
    with pytest.raises(ValueError, match='semantic binding'):
        sbir.validate_sbir_source_bundle(frame, state, status)


def test_invalid_final_bundle_cannot_change_receipts_or_last_good(source_bundle, monkeypatch):
    _, paths, _, _ = source_bundle
    before = {name: path.read_bytes() for name, path in paths.items() if path.exists()}
    monkeypatch.setitem(sbir.AUTHORITY, 'can_rank', True)
    root = paths['state'].parents[2]
    collector = _collector(root, _FixtureSession({CELL: [_award('schema-2')]}))
    with pytest.raises(ValueError, match='schema violation'):
        collector.collect(cells=CELLS, observed_at=OBSERVED_2)
    assert {name: paths[name].read_bytes() for name in before} == before


def test_invalid_page_receipt_is_refused_before_any_persistence(tmp_path, monkeypatch):
    collector = _collector(tmp_path, _FixtureSession({CELL: [_award('schema-1')]}))
    receipt_factory = collector._receipt
    def bad_receipt(**kwargs):
        receipt = receipt_factory(**kwargs)
        receipt['request_sha256'] = 'invalid'
        return receipt
    monkeypatch.setattr(collector, '_receipt', bad_receipt)
    with pytest.raises(ValueError, match='schema violation'):
        collector.collect(cells=CELLS, observed_at=OBSERVED)
    assert not any(path.exists() for path in collector._paths().values())


def test_invalid_accrued_observation_refuses_before_next_request(source_bundle):
    _, paths, frame, _ = source_bundle
    frame.loc[0, 'known_at'] = '2000-01-01T00:00:00+00:00'
    frame.to_parquet(paths['observations'], index=False)
    # Rebinding the full-ledger hash cannot legitimize backdated knowledge.
    state = json.loads(paths['state'].read_text())
    state.update(sbir.sbir_projection_generation(frame))
    paths['state'].write_text(json.dumps(state))
    before = {name: path.read_bytes() for name, path in paths.items() if path.exists()}
    session = _FixtureSession({CELL: [_award('schema-2')]})
    collector = _collector(paths['state'].parents[2], session)
    with pytest.raises(ValueError, match='semantic binding'):
        collector.collect(cells=CELLS, observed_at=OBSERVED_2)
    assert session.calls == []
    assert {name: paths[name].read_bytes() for name in before} == before
