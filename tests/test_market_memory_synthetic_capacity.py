"""Failure-path checks for the offline capacity measurement harness."""
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

FILE = Path(__file__).resolve().parents[1] / 'research/market_memory/performance_20261015/benchmark.py'
spec = importlib.util.spec_from_file_location('capacity_benchmark', FILE)
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)


@pytest.mark.parametrize('message,returned,accepted', [
    ('whole_generation_capture_bound_exceeded', False, True),
    ('whole_generation_other_failure', False, False),
    (None, True, False),
])
def test_refusal_requires_exact_bound_and_reports_unexpected_capability(tmp_path, message, returned, accepted):
    class CohortError(Exception):
        pass

    def read(*args, **kwargs):
        if message is not None:
            raise CohortError(message)
        return object()

    (tmp_path / benchmark.QUERY_META_NAME).write_text(json.dumps({'subject_id': 'fixture'}))
    result = tmp_path / 'result.json'
    mods = SimpleNamespace(
        owner=lambda _: (object(), SimpleNamespace(captures=list(range(257)))),
        cohort=SimpleNamespace(MAX_CAPTURES=256, RetainedContextCohortError=CohortError,
                               read_retained_context_cohort=read),
        CUTOFF='fixture', Policy=lambda: object())
    rc = benchmark.child_refusal(SimpleNamespace(corpus_dir=str(tmp_path), result=str(result)), mods)
    data = json.loads(result.read_text())
    assert (rc == 0) is accepted
    assert data['ok'] is accepted
    assert data['capability_returned'] is returned
    assert data['no_false_acceptance'] is accepted
    assert data['retrieval_attempted'] is False


def test_build_failure_never_runs_query_trials(tmp_path, monkeypatch):
    (tmp_path / benchmark.TRIALS_DIRNAME).mkdir()
    calls = []
    def timed_out(script, repo, args, env):
        calls.append(args)
        return {'timeout': True, 'wall_seconds': 300.0}
    monkeypatch.setattr(benchmark, 'run_child', timed_out)
    report, gaps = benchmark.run_size(None, FILE, tmp_path, tmp_path, 16, {})
    assert report['status'] == 'build_failed' and gaps
    assert len(calls) == 1 and calls[0][0] == '--child-build'


def test_child_timeout_is_bounded_and_reported(monkeypatch, tmp_path):
    def timeout(command, **kwargs):
        assert kwargs['timeout'] == 300
        raise subprocess.TimeoutExpired(command, 300)
    monkeypatch.setattr(benchmark.subprocess, 'run', timeout)
    result = benchmark.run_child(FILE, tmp_path, ['--child-build'], {})
    assert result['timeout'] is True


def test_storage_separates_fixture_and_harness_metadata(tmp_path):
    (tmp_path / benchmark.FIXTURE_NAME).write_bytes(b'123')
    (tmp_path / benchmark.QUERY_META_NAME).write_bytes(b'45')
    (tmp_path / 'retained').write_bytes(b'6789')
    result = benchmark.corpus_stats(tmp_path)
    assert result['retained_artifacts'] == {'files': 1, 'logical_bytes': 4}
    assert result['harness_metadata'] == {'files': 1, 'logical_bytes': 2}
    assert result['total'] == {'files': 3, 'logical_bytes': 9}
