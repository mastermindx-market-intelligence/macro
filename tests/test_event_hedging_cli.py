"""Synthetic end-to-end checks for the incumbent scenario CLI.

No browser, market collection, forecast fitting or deployment is performed.
"""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.event_hedging_diagnostics import build_event_variance_diagnostic, compare_hedge_path_targets
from engine.event_hedging_evaluation import score_event_hedging_forecasts
from engine.options_scenario_surface import build_hedge_target_change
from tests.test_event_hedging_diagnostics import variance_input, target_input
from tests.test_event_hedging_evaluation import inputs

ROOT = Path(__file__).resolve().parents[1]


def _cli(mode, payload):
    return subprocess.run(
        [sys.executable, '-m', 'scripts.build_options_scenario_surface', '--mode', mode, '--input', '-'],
        input=json.dumps(payload), text=True, capture_output=True, cwd=ROOT, timeout=20,
    )


def test_variance_cli_matches_pure_owner(variance_input):
    result = _cli('event-variance', variance_input)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == build_event_variance_diagnostic(**variance_input)


def test_path_cli_matches_pure_owner(target_input):
    checkpoint = build_hedge_target_change(**target_input)
    terminal = build_hedge_target_change(**dict(target_input, target_at='2026-10-08T18:45:00Z', target_spot=6020.))
    payload = dict(checkpoint=checkpoint, terminal=terminal, path_ref='fixture:path')
    result = _cli('hedge-path', payload)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == compare_hedge_path_targets(**payload)


def test_scorecard_cli_matches_pure_owner(inputs):
    result = _cli('event-scorecard', inputs)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == score_event_hedging_forecasts(**inputs)


def test_cli_refuses_duplicate_json_keys():
    result = subprocess.run(
        [sys.executable, '-m', 'scripts.build_options_scenario_surface', '--mode', 'event-variance', '--input', '-'],
        input='{"as_of":1,"as_of":2}', text=True, capture_output=True, cwd=ROOT, timeout=20,
    )
    assert result.returncode != 0
    assert 'duplicate JSON member' in result.stderr
    assert result.stdout == ''


def test_cli_refuses_late_inputs_without_emitting_artifact(variance_input):
    variance_input['counterfactual']['known_at'] = '2026-10-08T19:00:00Z'
    result = _cli('event-variance', variance_input)
    assert result.returncode != 0
    assert result.stdout == ''


@pytest.mark.parametrize('bad', [True, None, float('nan'), float('inf'), -1.])
def test_cli_refuses_invalid_variance(variance_input, bad):
    variance_input['observed']['value'] = bad
    result = _cli('event-variance', variance_input)
    assert result.returncode != 0
    assert result.stdout == ''


def test_explicit_file_input_and_output_match_stdout(variance_input, tmp_path):
    source = tmp_path / 'request.json'
    target = tmp_path / 'result.json'
    source.write_text(json.dumps(variance_input))
    result = subprocess.run(
        [sys.executable, '-m', 'scripts.build_options_scenario_surface', '--mode', 'event-variance',
         '--input', str(source), '--output', str(target)],
        text=True, capture_output=True, cwd=ROOT, timeout=20,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ''
    assert json.loads(target.read_text()) == build_event_variance_diagnostic(**variance_input)
