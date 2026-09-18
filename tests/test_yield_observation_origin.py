"""Captured-source qualification, not historical availability certification."""
import copy
import numpy as np
import pandas as pd
from engine import yield_momentum as ym


def frame(n=100):
    return pd.DataFrame({'us10y': 4.0 + np.arange(n) / 100},
                        index=pd.bdate_range('2025-01-02', periods=n))


def attach(f, raw=None):
    raw = f.us10y.copy() if raw is None else raw
    f.attrs['rate_observations'] = {'us10y': ym.capture_rate_observations(
        raw, f.us10y, source_id='DGS10', source_column='us10y')}
    return f


def read(f):
    return ym.build_yield_momentum(f)['series']['10y']


def test_identical_flat_frames_distinguish_new_observations_from_carry():
    f = frame(); f['us10y'] = 4.0
    observed = read(attach(f.copy()))
    carried = read(attach(f.copy(), f.us10y.iloc[:-1]))
    assert observed['observation_origin'] == 'captured_source_row'
    assert observed['velocity_bp']['5d'] == 0.0
    assert carried['observation_origin'] == 'carried'
    assert carried['level'] is None
    assert carried['carried_level'] == 4.0
    assert carried['as_of'] == str(f.index[-2].date())
    assert all(v is None for v in carried['velocity_bp'].values())
    assert carried['turn_watch'] is None


def test_unverified_frame_never_certifies_a_turn():
    out = read(frame())
    assert out['observation_origin'] == 'unverified'
    assert out['turn_watch'] is None
    assert out['available_at'] is None
    assert out['path_qualified'] is False


def test_stale_attributes_do_not_certify_corrected_values():
    f = attach(frame()); f.iloc[-1, 0] += 0.1
    out = read(f)
    assert out['observation_origin'] == 'unverified'
    assert out['origin_status'] == 'frame_mismatch'
    assert out['turn_watch'] is None


def test_valid_endpoints_do_not_certify_a_missing_interior_path():
    f = frame(); raw = f.us10y.drop(f.index[-3])
    f.iloc[-3, 0] = f.iloc[-4, 0]
    out = read(attach(f, raw))
    assert out['velocity_bp']['5d'] == 5.0
    assert out['path_qualified'] is False
    assert out['turn_watch'] is None


def test_missing_fixed_endpoint_is_not_a_carried_measurement():
    f = frame(); raw = f.us10y.drop(f.index[-6])
    f.iloc[-6, 0] = f.iloc[-7, 0]
    out = read(attach(f, raw))
    assert out['velocity_bp']['5d'] is None
    assert out['velocity_bp']['22d'] == 22.0
    assert out['endpoint_dates']['5d'][0] == str(f.index[-6].date())


def test_capture_is_bounded_json_and_survives_frame_copy():
    import json
    f = attach(frame(2000)); before = copy.deepcopy(f.attrs)
    assert len(f.attrs['rate_observations']['us10y']['origin_dates']) <= 1260
    json.dumps(f.attrs, allow_nan=False)
    assert read(f.copy()) == read(f)
    assert f.attrs == before
    assert read(f)['source_id'] == 'DGS10'


def test_metadata_does_not_invent_historical_receipts():
    out = read(attach(frame()))
    assert out['available_at'] is None
    assert out['availability_status'] == 'not_provided_by_feature_frame'
    assert out['historical_availability_qualified'] is False
    assert out['horizon_basis'] == 'fixed_weekday_grid_intervals'


def test_nonfinite_raw_endpoint_is_unqualified():
    f = frame(); f.iloc[-1, 0] = np.inf
    out = read(attach(f))
    assert out['level'] is None and out['turn_watch'] is None


def test_real_feature_builder_preserves_numeric_fill_but_carries_origin(monkeypatch):
    from engine import inputs, rate_inflation_transmission as tx
    idx = pd.bdate_range('2025-01-02', periods=100)
    tickers = {t for group in inputs.config.load()['yahoo']['tickers'].values() for t in group}
    closes = pd.DataFrame({t: [100.0] * len(idx) for t in tickers}, index=idx)
    raw = pd.Series(4.0 + np.arange(99) / 100, index=idx[:-1])
    monkeypatch.setattr(inputs, 'yahoo_closes', lambda: closes)
    monkeypatch.setattr(inputs, '_fred', lambda _aliases: {'us10y': raw})
    monkeypatch.setattr(inputs.store, 'read', lambda *a, **k: None)
    monkeypatch.setattr(tx, 'load_calibration', lambda: None)
    f = inputs.build_features()
    assert f.us10y.iloc[-1] == raw.iloc[-1]  # Global fill remains unchanged.
    out = tx.snapshot(f.copy())['yield_momentum']['series']['10y']
    assert out['observation_origin'] == 'carried'
    assert out['carried_level'] == raw.iloc[-1]
    assert out['level'] is None and out['turn_watch'] is None
    assert out['source_id'] == 'DGS10'
    assert out['as_of'] == str(idx[-2].date())
    assert out['frame_as_of'] == str(idx[-1].date())
    assert out['historical_availability_qualified'] is False


def _builder_fixture(monkeypatch):
    from engine import inputs
    idx = pd.bdate_range('2025-01-02', periods=100)
    tickers = {t for g in inputs.config.load()['yahoo']['tickers'].values() for t in g}
    closes = pd.DataFrame({t: np.arange(100) + 100.0 for t in tickers}, index=idx)
    raw = pd.Series(np.arange(100) / 100 + 4.0, index=idx)
    monkeypatch.setattr(inputs, 'yahoo_closes', lambda: closes)
    monkeypatch.setattr(inputs, '_fred', lambda _aliases: {'us10y': raw})
    monkeypatch.setattr(inputs.store, 'read', lambda *a, **k: None)
    return inputs, raw


def test_override_retains_caller_basis_not_canonical_source(monkeypatch):
    inputs, raw = _builder_fixture(monkeypatch)
    out = read(inputs.build_features(overrides={'us10y': raw + 1.0}))
    assert out['observation_origin'] == 'caller_supplied_row'
    assert out['source_id'] is None
    assert out['level'] == round(raw.iloc[-1] + 1.0, 3)
    assert out['path_qualified'] is False and out['turn_watch'] is None
    assert out['historical_availability_qualified'] is False


def test_optional_capture_failure_preserves_all_numeric_features(monkeypatch):
    inputs, _ = _builder_fixture(monkeypatch)
    baseline = inputs.build_features()
    def unavailable(*args, **kwargs):
        raise ValueError('controlled metadata failure')
    monkeypatch.setattr(ym, 'capture_rate_observations', unavailable)
    out = inputs.build_features()
    evidence = read(out)
    baseline.attrs.clear(); out.attrs.clear()
    pd.testing.assert_frame_equal(out, baseline)
    assert evidence['observation_origin'] == 'unverified'
    assert evidence['path_qualified'] is False and evidence['turn_watch'] is None


def test_ric_preserves_exact_transmission_origin_contract(tmp_path, monkeypatch):
    import json
    from engine import rates_inflation_command as ric, rate_inflation_transmission as tx
    inputs, _ = _builder_fixture(monkeypatch)
    monkeypatch.setattr(tx, 'load_calibration', lambda: None)
    snapshot = tx.snapshot(inputs.build_features().copy())
    data_dir = tmp_path / 'transmission'; data_dir.mkdir()
    (data_dir / 'latest.json').write_text(json.dumps(snapshot, default=str))
    board = ric.build_board(tmp_path)
    assert board['yield_momentum'] == snapshot['yield_momentum']
    assert board['authority'] is False and board['display_only'] is True
