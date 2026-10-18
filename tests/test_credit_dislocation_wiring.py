"""Single-producer/dead-wire checks for the additive CCW implementation."""
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(None)
def read_yaml(path):
    return yaml.safe_load((ROOT / path).read_text())


def nested_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nested_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from nested_dicts(child)


def test_one_existing_lane_producer_after_credit_momentum():
    source = (ROOT / '.github/workflows/daily.yml').read_text()
    assert source.count('python -m engine.credit_dislocation') == 1
    assert source.index('python -m engine.credit_dislocation') > source.index('python -m engine.credit_momentum')
    assert 'credit_dislocation source unavailable (non-fatal)' in source
    read_yaml('.github/workflows/daily.yml')


def test_dag_has_one_step_and_one_artifact_edge():
    nodes = list(nested_dicts(read_yaml('config/dag.yml')))
    assert len([n for n in nodes if n.get('id') == 'credit_dislocation']) == 1
    edges = [n for n in nodes if n.get('module') == 'engine.credit_dislocation' and 'writes' in n]
    assert len(edges) == 1
    assert edges[0]['writes'] == ['data/corp_bonds/credit_dislocation.json']
    assert edges[0]['needs_secrets'] is False


def test_synapse_owner_and_no_scored_surface():
    nodes = list(nested_dicts(read_yaml('config/synapse.yml')))
    artifacts = [n for n in nodes if n.get('path') == 'data/corp_bonds/credit_dislocation.json']
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact['owner_program'] == 'ccw'
    assert artifact['horizon_role'] == 'context'
    assert artifact['tier'] == 'display'
    assert artifact['scored_path_surfaces'] == []
    assert artifact['asof_field'] == 'source_as_of'
    assert 'engine/credit_dislocation_view.py' in artifact['consumers']


def test_existing_ci_job_includes_all_cdi_tests():
    jobs = read_yaml('.github/ci/legacy-jobs.yml')['jobs']
    job = jobs['ccw-w4-credit-desk']
    commands = '\n'.join(step.get('run', '') for step in job['steps'])
    for name in ['test_credit_dislocation.py', 'test_credit_dislocation_view.py', 'test_credit_dislocation_wiring.py']:
        assert f'tests/{name}' in commands
        assert f'tests/{name}' in job['paths']
