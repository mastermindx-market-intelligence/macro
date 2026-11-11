"""Synthetic regression tests; no prices, live data or replay builds are read."""
import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from scripts import prophet_pit_replay as replay


def run_alpha(tmp_path, result, stderr=b'', returncode=0):
    vintage = tmp_path / 'vintage'
    vintage.mkdir()
    artifact = vintage / 'site/factordata/alpha.json'
    artifact.parent.mkdir(parents=True)
    artifact.write_text('{"fixture":true}')
    work = tmp_path / 'work'

    def completed(command, **kwargs):
        Path(command[-1]).write_text(json.dumps(result))
        return subprocess.CompletedProcess(command, returncode, b'', stderr)

    with patch.object(replay.subprocess, 'run', side_effect=completed):
        return replay.build_alpha(vintage, through='2026-07-15', work=work)


def test_no_result_reports_upstream_cause_not_a_date_mismatch(tmp_path):
    with pytest.raises(replay.PitReplayRefused, match='returned no alpha result') as exc:
        run_alpha(tmp_path, {'ok': False, 'as_of': None, 'n': None},
                  b'WARNING residual_alpha: no close matrix\n')
    assert 'no close matrix' in str(exc.value)
    assert 'did not truncate' not in str(exc.value)


def test_real_date_mismatch_still_refuses(tmp_path):
    with pytest.raises(replay.PitReplayRefused, match="not '2026-07-15'"):
        run_alpha(tmp_path, {'ok': True, 'as_of': '2026-07-14', 'n': 12})


def test_valid_result_preserves_receipt(tmp_path):
    result = run_alpha(tmp_path, {'ok': True, 'as_of': '2026-07-15', 'n': 12})
    assert result['as_of'] == '2026-07-15'
    assert result['names'] == 12
    assert len(result['sha256']) == 64


def test_invalid_result_shape_fails_closed(tmp_path):
    with pytest.raises(replay.PitReplayRefused, match='invalid result object'):
        run_alpha(tmp_path, [])


def test_subprocess_failure_still_refuses(tmp_path):
    with pytest.raises(replay.PitReplayRefused, match='residual-alpha rebuild failed'):
        run_alpha(tmp_path, {'ok': False}, b'fixture child failure', returncode=1)
