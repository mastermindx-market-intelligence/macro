"""Existing CLI -> analytical artifact -> real Options template integration.

All market examples are synthetic. Tests make no live-data or forecasting claim.
"""
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine.event_hedging_diagnostics import build_event_variance_diagnostic, compare_hedge_path_targets
from engine.options_scenario_surface import build_hedge_target_change
from scripts.options_event_hedging_view import build_event_hedging_view
from scripts.build_options_command import build_context, render
from tests.test_event_hedging_diagnostics import variance_input, target_input

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 8, 22, tzinfo=timezone.utc)
EMPTY = dict(flow_desk=None, screener=None, leaders=None, market_structure=None, vol=None, gex={}, gex_index=None)


def _cli(mode, payload):
    return subprocess.run(
        [sys.executable, '-m', 'scripts.build_options_scenario_surface', '--mode', mode, '--input', '-'],
        input=json.dumps(payload), text=True, capture_output=True, cwd=ROOT, timeout=20,
    )


def _reseal(out):
    prefix = out['content_id'].split(':')[0] + ':'
    raw = {k: v for k, v in out.items() if k != 'content_id'}
    out['content_id'] = prefix + sha256(json.dumps(raw, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return out


def test_variance_cli_matches_pure_owner(variance_input):
    result = _cli('event-variance', variance_input)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == build_event_variance_diagnostic(**variance_input)


def test_path_cli_matches_pure_owner(target_input):
    a = build_hedge_target_change(**target_input)
    b = build_hedge_target_change(**dict(target_input, target_at='2026-10-08T18:45:00Z', target_spot=6020.))
    inputs = dict(checkpoint=a, terminal=b, path_ref='fixture:path')
    result = _cli('hedge-path', inputs)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == compare_hedge_path_targets(**inputs)


def test_cli_refuses_duplicate_json_keys():
    result = subprocess.run([sys.executable, '-m', 'scripts.build_options_scenario_surface',
        '--mode', 'event-variance', '--input', '-'], input='{"as_of":1,"as_of":2}',
        text=True, capture_output=True, cwd=ROOT, timeout=20)
    assert result.returncode != 0
    assert 'duplicate JSON member' in result.stderr
    assert result.stdout == ''


def test_cli_refuses_late_inputs_without_emitting_artifact(variance_input):
    variance_input['counterfactual']['known_at'] = '2026-10-08T19:00:00Z'
    result = _cli('event-variance', variance_input)
    assert result.returncode != 0
    assert result.stdout == ''


def test_absence_does_not_add_ui_or_change_other_context():
    left = build_context(ROOT, stores=EMPTY, now=NOW)
    right = build_context(ROOT, stores=EMPTY, now=NOW, event_hedging=None)
    assert left['event_hedging_view'] is None
    left.pop('built'); right.pop('built')
    assert left == right
    assert 'data-event-hedging-research' not in render(ROOT, stores=EMPTY, now=NOW)


def test_real_options_template_renders_source_bound_variance(variance_input):
    artifact = build_event_variance_diagnostic(**variance_input)
    view = build_event_hedging_view(artifact, now=NOW)
    assert view['available'] is True
    assert view['rows'][0]['value'] == '0.00040000'
    assert view['rows'][2]['value'] == '2.000'
    html = render(ROOT, stores=EMPTY, now=NOW, event_hedging=artifact)
    assert 'data-event-hedging-research' in html
    assert 'Recorded scenario' in html
    assert 'Decision snapshot' in html and artifact['inputs']['as_of'] in html
    assert '2.000' in html and 'fixture:observed' in html
    assert 'not yet qualified' in html
    assert artifact['content_id'] in html
    assert '事件对冲研究' in html
    assert 'aria-labelledby="event-hedging-heading"' in html
    assert '<details class="eh-evidence">' in html
    assert 'forecast' in html


def test_zero_and_negative_are_not_missing(variance_input):
    variance_input['counterfactual']['value'] = variance_input['observed']['value']
    view = build_event_hedging_view(build_event_variance_diagnostic(**variance_input), now=NOW)
    assert view['rows'][2]['value'] == '0.000'
    variance_input['counterfactual']['value'] += .001
    view = build_event_hedging_view(build_event_variance_diagnostic(**variance_input), now=NOW)
    assert view['rows'][0]['value'].startswith('-')
    assert view['rows'][2]['value'] is None


def test_unknown_overlap_renders_unavailable_isolated_measure(variance_input):
    variance_input.update(calendar_complete=None, overlap_event_ids=None)
    artifact = build_event_variance_diagnostic(**variance_input)
    html = render(ROOT, stores=EMPTY, now=NOW, event_hedging=artifact)
    assert 'event_overlap_coverage_unknown' in html
    view = build_event_hedging_view(artifact, now=NOW)
    assert view['rows'][0]['value'] is not None
    assert view['rows'][1]['value'] is None


def test_tampered_authority_and_future_artifacts_refuse(variance_input):
    artifact = build_event_variance_diagnostic(**variance_input)
    before = datetime(2026, 10, 8, 18, tzinfo=timezone.utc)
    assert build_event_hedging_view(artifact, now=before)['available'] is False
    artifact['authority']['trading'] = True
    _reseal(artifact)
    assert build_event_hedging_view(artifact, now=NOW)['available'] is False
    html = render(ROOT, stores=EMPTY, now=NOW, event_hedging=artifact)
    assert 'This calculation is unavailable' in html
    assert '2.000' not in html


@pytest.mark.parametrize('bad', [False, [], 'unknown', {'schema': 'other'}, {'schema': 'options.event_variance_diagnostic/v1'}])
def test_malformed_optional_inputs_fail_soft(bad):
    out = build_event_hedging_view(bad, now=NOW)
    assert out['available'] is False
    assert not out['rows']


def test_source_text_is_escaped(variance_input):
    variance_input['observed']['source_ref'] = '<script>evil()</script>'
    artifact = build_event_variance_diagnostic(**variance_input)
    html = render(ROOT, stores=EMPTY, now=NOW, event_hedging=artifact)
    assert '<script>evil()</script>' not in html
    assert '&lt;script&gt;evil()&lt;/script&gt;' in html


def test_stale_owner_result_never_prints_zero(variance_input):
    variance_input['as_of'] = '2026-10-08T18:02:00Z'
    artifact = build_event_variance_diagnostic(**variance_input)
    view = build_event_hedging_view(artifact, now=NOW)
    assert view['available'] is False and view['rows'] == []
    assert view['reasons'] == ['stale_variance_evidence']


def test_path_view_labels_risk_units_and_does_not_imply_execution(target_input):
    a = build_hedge_target_change(**target_input)
    b = build_hedge_target_change(**dict(target_input, target_at='2026-10-08T18:45:00Z', target_spot=6020.))
    artifact = compare_hedge_path_targets(checkpoint=a, terminal=b, path_ref='fixture:path')
    html = render(ROOT, stores=EMPTY, now=NOW, event_hedging=artifact)
    assert 'SPX risk units' in html
    assert 'not cash flow' in html
    assert 'not executable shares or futures contracts' in html
    assert 'fixture:path' in html


def test_view_does_not_mutate_evidence(variance_input):
    artifact = build_event_variance_diagnostic(**variance_input)
    original = deepcopy(artifact)
    build_event_hedging_view(artifact, now=NOW)
    assert artifact == original


def test_scorecard_mode_is_the_same_owner_calculation():
    from tests.test_event_hedging_evaluation import inputs
    from engine.event_hedging_evaluation import score_event_hedging_forecasts
    payload = inputs.__wrapped__()
    result = _cli('event-scorecard', payload)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == score_event_hedging_forecasts(**payload)


@pytest.mark.parametrize('body', ['{"x":1,"x":2}', '{"x":NaN}', '[]'])
def test_explicit_view_loader_rejects_ambiguous_json(tmp_path, body):
    from scripts.options_event_hedging_view import load_event_hedging_artifact
    path = tmp_path / 'input.json'
    path.write_text(body)
    with pytest.raises(ValueError):
        load_event_hedging_artifact(str(path))


def test_view_loader_is_bounded(tmp_path):
    from scripts.options_event_hedging_view import load_event_hedging_artifact
    path = tmp_path / 'input.json'
    path.write_bytes(b' ' * 2_000_001)
    with pytest.raises(ValueError, match='exceeds'):
        load_event_hedging_artifact(str(path))


def test_explicit_view_loader_roundtrip(variance_input, tmp_path):
    from scripts.options_event_hedging_view import load_event_hedging_artifact
    artifact = build_event_variance_diagnostic(**variance_input)
    path = tmp_path / 'input.json'
    path.write_text(json.dumps(artifact))
    assert load_event_hedging_artifact(str(path)) == artifact
