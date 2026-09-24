"""Synthetic tests only: no historical outcomes or network access."""
import json

import numpy as np
import pandas as pd
import pytest

from engine.rates_direction_research import (
    ForecastSpec, build_features, prepare_panel, summarize, walk_forward,
)


def sources(n=320):
    index = pd.bdate_range('2018-01-01', periods=n)
    rng = np.random.default_rng(9271)
    common = np.cumsum(rng.normal(0, 0.035, n))
    return {key: pd.Series(level + common + rng.normal(0, 0.004, n), index=index)
            for key, level in [('2y', 2.0), ('5y', 2.3), ('10y', 2.5),
                               ('30y', 2.9), ('real10y', 0.7)]}


def small_spec():
    return ForecastSpec(train_min=40, train_max=90, calibration_min=20,
                        calibration_max=30, refit_every=7)


def test_panel_uses_anchor_without_compacting_other_series():
    raw = sources()
    missing = raw['2y'].index[200]
    raw['2y'] = raw['2y'].drop(missing)
    panel = prepare_panel(raw)
    assert missing in panel.index
    assert pd.isna(panel.loc[missing, '2y'])
    assert len(panel) == 320


def test_duplicate_dates_refused_instead_of_last_write_wins():
    raw = sources()
    raw['10y'] = pd.concat([raw['10y'], raw['10y'].iloc[-1:]])
    with pytest.raises(ValueError, match='unique'):
        prepare_panel(raw)


def test_features_are_in_basis_points():
    panel = prepare_panel(sources())
    features = build_features(panel, '10y')
    assert features.iloc[-1, 0] == pytest.approx(
        100 * (panel['10y'].iloc[-1] - panel['10y'].iloc[-6]))


def test_fit_and_calibration_labels_are_matured_and_disjoint():
    result = walk_forward(prepare_panel(sources()), '10y', 5, small_spec())
    assert result['rows']
    for row in result['rows']:
        assert row['fit_target_end'] < row['calibration_start']
        assert row['calibration_target_end'] < row['origin']
        assert row['forecast_available_at'] is None
        assert row['historical_availability_qualified'] is False
        assert row['authority'] is False


def test_mutating_future_rows_cannot_change_past_predictions():
    raw = sources()
    cut = raw['10y'].index[245]
    original = walk_forward(prepare_panel(raw), '10y', 5, small_spec())
    for series in raw.values():
        series.loc[series.index > cut] += 7.0
    changed = walk_forward(prepare_panel(raw), '10y', 5, small_spec())
    for before, after in zip(original['rows'], changed['rows']):
        if before['origin'] > str(cut.date()):
            break
        fields = ['origin', 'model', 'forecast_bp', 'lower_bp', 'upper_bp',
                  'p_up', 'p_flat', 'p_down', 'p_jump_up', 'p_jump_down']
        assert {k: before[k] for k in fields} == {k: after[k] for k in fields}


def test_missing_real_history_abstains_instead_of_zero_imputation():
    raw = sources()
    del raw['real10y']
    result = walk_forward(prepare_panel(raw), '10y', 5, small_spec())
    assert result['rows'] == []
    assert result['coverage']['eligible_feature_origins'] == 0


def test_missing_target_inside_horizon_is_not_compacted():
    raw = sources()
    day = raw['5y'].index[220]
    raw['5y'].loc[day] = np.nan
    result = walk_forward(prepare_panel(raw), '5y', 5, small_spec())
    affected = str(raw['5y'].index[217].date())
    rows = [r for r in result['rows'] if r['origin'] == affected]
    assert rows and all(r['observed_change_bp'] is None for r in rows)


def test_probabilities_intervals_and_serialization_are_finite():
    result = walk_forward(prepare_panel(sources()), '10y', 5, small_spec())
    for row in result['rows']:
        assert row['p_up'] + row['p_down'] + row['p_flat'] == pytest.approx(1)
        assert 0 <= row['p_jump_up'] + row['p_jump_down'] <= 1
        assert row['lower_bp'] <= row['upper_bp']
        assert row['jump_threshold_bp'] >= 10
    json.dumps(result, allow_nan=False)
    report = summarize(result, start='2018-01-01', end='2020-12-31')
    assert len(report['models']) == 4
    assert report['paired_ridge_vs_no_change']['n'] > 0
    json.dumps(report, allow_nan=False)


def test_unknown_tenor_horizon_and_invalid_spec_rejected():
    panel = prepare_panel(sources())
    with pytest.raises(ValueError):
        walk_forward(panel, '3y', 5, small_spec())
    with pytest.raises(ValueError):
        walk_forward(panel, '10y', 0, small_spec())
    with pytest.raises(ValueError):
        ForecastSpec(train_min=90, train_max=40)


def test_large_source_gap_withholds_feature_path():
    raw = sources()
    anchor = raw['10y']
    raw['10y'] = anchor.drop(anchor.index[170:180])
    panel = prepare_panel(raw)
    features = build_features(panel, '10y')
    assert features.loc[anchor.index[181]].isna().all()


def test_constant_rates_have_finite_ridge_and_probability_output():
    raw = {key: series * 0 + 3.0 for key, series in sources().items()}
    result = walk_forward(prepare_panel(raw), '10y', 5, small_spec())
    assert result['rows']
    assert all(abs(r['forecast_bp']) < 1e-9 for r in result['rows'])
    assert all(r['p_flat'] > 0.8 for r in result['rows'])


def test_preregistration_matches_code_and_rejects_drift(tmp_path):
    from scripts.research.ric_rates_direction import load_prereg
    prereg = load_prereg()
    assert prereg['config_count'] == 48
    prereg['ridge_penalty'] = 1.0
    changed = tmp_path / 'changed.json'
    changed.write_text(json.dumps(prereg))
    with pytest.raises(ValueError, match='mismatch'):
        load_prereg(changed)


def test_real_data_cannot_be_read_before_registration(monkeypatch, tmp_path):
    from scripts.research import ric_rates_direction as runner
    calls = []
    def register(*args):
        calls.append('registered')
        return {}
    def read(*args):
        assert calls == ['registered']
        raise RuntimeError('synthetic stop before real source read')
    monkeypatch.setattr(runner, 'register_before_data', register)
    monkeypatch.setattr(runner, 'read_sources', read)
    with pytest.raises(RuntimeError, match='synthetic stop'):
        runner.run(tmp_path, tmp_path / 'output')


def test_missing_canonical_ledger_is_not_silently_created(tmp_path):
    from scripts.research.ric_rates_direction import load_prereg, register_before_data
    absent = tmp_path / 'absent.jsonl'
    with pytest.raises(ValueError, match='canonical TrialLedger'):
        register_before_data(load_prereg(), absent)
    assert not absent.exists()


def test_spec_settings_survive_into_score_consumer():
    result = walk_forward(prepare_panel(sources()), '10y', 5,
                          ForecastSpec(train_min=40, train_max=90,
                                       calibration_min=20, calibration_max=30,
                                       flat_band_bp=500))
    report = summarize(result, start='2018-01-01', end='2020-12-31')
    assert report['models']['no_change']['direction_log_loss'] < 0.1


def test_direct_entrypoint_pins_this_checkout_before_foreign_packages(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    foreign = tmp_path / 'engine'
    foreign.mkdir()
    (foreign / '__init__.py').write_text("raise RuntimeError('FOREIGN_CHECKOUT')\n")
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    done = subprocess.run([sys.executable, str(root / 'scripts/research/ric_rates_direction.py'),
                           '--help'], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert '--register-and-run' in done.stdout
