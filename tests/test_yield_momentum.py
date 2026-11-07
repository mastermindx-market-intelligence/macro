"""Contract tests for the display-only, correction-safe yield momentum read."""
from __future__ import annotations

import copy
import unittest

import numpy as np
import pytest
import pandas as pd

from engine import yield_momentum


def _build(frame: pd.DataFrame) -> dict:
    return yield_momentum.build_yield_momentum(frame)


def _frame(n: int = 100) -> pd.DataFrame:
    index = pd.bdate_range("2026-01-01", periods=n)
    out = pd.DataFrame(index=index)
    for offset, column in enumerate(("us2y", "us5y", "us10y", "us20y", "us30y")):
        out[column] = 3.0 + offset / 10 + np.linspace(0.0, 0.5, n)
    return out


def test_multi_horizon_read_is_display_only_and_includes_ccw_us20y():
    read = _build(_frame())

    assert read["schema"] == "yield_momentum.v1"
    assert read["display_only"] is True
    assert read["authority"] is False
    assert all(read[key] is False for key in ("can_score", "can_size", "can_trade"))
    assert set(read["series"]) == {"2y", "5y", "10y", "20y", "30y"}
    twenty = read["series"]["20y"]
    assert twenty["source_column"] == "us20y"
    assert twenty["status"] == "available"
    assert twenty["level"] is not None
    assert set(twenty["velocity_bp"]) == {"5d", "22d", "63d"}
    assert twenty["velocity_bp"]["63d"] > 0


def test_missing_and_short_series_are_explicit_null_states():
    read = _build(_frame(20).drop(columns=["us20y"]))

    missing = read["series"]["20y"]
    assert missing["status"] == "missing"
    assert missing["level"] is None
    assert missing["null_reason"] == "source column us20y unavailable"

    short = read["series"]["10y"]
    assert short["status"] == "insufficient_history"
    assert short["velocity_bp"]["63d"] is None
    assert short["null_reason"] == "requires 64 grid points for 63-interval velocity"


def test_turn_watch_is_trailing_and_correction_rebuild_is_idempotent():
    values = np.concatenate([
        np.linspace(2.0, 3.8, 1000),
        np.linspace(3.8, 4.0, 100),
        np.linspace(4.0, 3.84, 22),
    ])
    frame = _frame(len(values))
    frame["us20y"] = values

    # Unreceipted frames retain endpoints but cannot certify a turn.
    assert _build(frame)["series"]["20y"]["turn_watch"] is None

    def qualified(f):
        f.attrs[yield_momentum.ORIGIN_ATTR] = {
            col: yield_momentum.capture_rate_observations(
                f[col], f[col], source_id=None, source_column=col)
            for col in yield_momentum.SERIES.values()
        }
        return f

    frame = qualified(frame)
    first = _build(frame)
    second = _build(frame.copy())
    corrected = frame.copy()
    corrected.loc[corrected.index[-23], "us20y"] -= 0.10
    assert _build(corrected)["series"]["20y"]["origin_status"] == "frame_mismatch"
    corrected = qualified(corrected)
    corrected_once = _build(corrected)
    corrected_twice = _build(corrected.copy())

    assert first == second
    assert corrected_once == corrected_twice
    twenty = first["series"]["20y"]
    assert twenty["turn_watch"] == "rolldown_forming"
    assert twenty["velocity_bp"]["22d"] <= -12
    assert twenty["available_at"] is None
    assert twenty["availability_status"] == "not_provided_by_feature_frame"


# Fixed-grid and source-origin regressions are enrolled in the existing rates CI job.
def _fixed_frame(n=100):
    return pd.DataFrame({"us10y": 4.0 + np.arange(n) / 100},
                        index=pd.bdate_range("2025-01-02", periods=n))


def _fixed_read(f):
    return yield_momentum.build_yield_momentum(f)["series"]["10y"]


class FixedGridAcceptance(unittest.TestCase):
    def test_complete_grid_five_interval_change(self):
        self.assertEqual(_fixed_read(_fixed_frame())["velocity_bp"]["5d"], 5.0)

    def test_missing_middle_does_not_move_five_interval_anchor(self):
        f = _fixed_frame(); f.iloc[-3, 0] = np.nan
        self.assertEqual(_fixed_read(f)["velocity_bp"]["5d"], 5.0)

    def test_missing_endpoint_is_not_replaced_by_an_earlier_date(self):
        f = _fixed_frame(); f.iloc[-6, 0] = np.nan
        self.assertIsNone(_fixed_read(f)["velocity_bp"]["5d"])

    def test_valid_acceleration_boundaries_survive_missing_middle(self):
        f = _fixed_frame(); f.iloc[-3, 0] = np.nan
        self.assertEqual(_fixed_read(f)["acceleration_bp"], 0.0)

    def test_missing_acceleration_boundary_withholds_acceleration(self):
        f = _fixed_frame(); f.iloc[-23, 0] = np.nan
        self.assertIsNone(_fixed_read(f)["acceleration_bp"])

    def test_63_interval_endpoints_do_not_require_64_nonnull_rows(self):
        f = _fixed_frame(64); f.iloc[30, 0] = np.nan
        self.assertEqual(_fixed_read(f)["velocity_bp"]["63d"], 63.0)

    def test_nonfinite_last_value_is_not_an_available_measurement(self):
        f = _fixed_frame(); f.iloc[-1, 0] = float("inf")
        self.assertIsNone(_fixed_read(f)["level"])

    def test_genuinely_observed_flat_values_are_zero_not_unavailable(self):
        f = _fixed_frame(); f["us10y"] = 4.0
        self.assertEqual(_fixed_read(f)["velocity_bp"]["5d"], 0.0)

    def test_input_is_not_mutated(self):
        f = _fixed_frame(); before = f.copy(deep=True)
        _fixed_read(f)
        pd.testing.assert_frame_equal(f, before)

    def test_missing_latest_stays_stale(self):
        f = _fixed_frame(); f.iloc[-1, 0] = np.nan
        out = _fixed_read(f)
        self.assertEqual(out["status"], "stale")
        self.assertIsNone(out["level"])


def _origin_frame(n=100):
    return pd.DataFrame({'us10y': 4.0 + np.arange(n) / 100},
                        index=pd.bdate_range('2025-01-02', periods=n))


def _attach_origin(f, raw=None):
    raw = f.us10y.copy() if raw is None else raw
    f.attrs['rate_observations'] = {'us10y': yield_momentum.capture_rate_observations(
        raw, f.us10y, source_id='DGS10', source_column='us10y')}
    return f


def _origin_read(f):
    return yield_momentum.build_yield_momentum(f)['series']['10y']


def test_identical_flat_frames_distinguish_new_observations_from_carry():
    f = _origin_frame(); f['us10y'] = 4.0
    observed = _origin_read(_attach_origin(f.copy()))
    carried = _origin_read(_attach_origin(f.copy(), f.us10y.iloc[:-1]))
    assert observed['observation_origin'] == 'captured_source_row'
    assert observed['velocity_bp']['5d'] == 0.0
    assert carried['observation_origin'] == 'carried'
    # A-RIC-F3-W2: one trailing carried row is a publication lag within tolerance,
    # so the carry is measured AT the last captured row and dated there -- the
    # distinction from a fresh observation is the origin + dating, not a null.
    assert observed['measurement_origin'] == 'latest_grid_row'
    assert carried['measurement_origin'] == 'last_captured_source_row'
    assert carried['trailing_publication_lag_rows'] == 1
    assert carried['level'] == 4.0
    assert carried['carried_level'] == 4.0
    assert carried['as_of'] == str(f.index[-2].date())
    assert carried['frame_as_of'] == str(f.index[-1].date())
    assert carried['velocity_bp']['5d'] == 0.0
    assert carried['turn_watch'] == observed['turn_watch']


def test_unverified_frame_never_certifies_a_turn():
    out = _origin_read(_origin_frame())
    assert out['observation_origin'] == 'unverified'
    assert out['turn_watch'] is None
    assert out['available_at'] is None
    assert out['path_qualified'] is False


def test_stale_attributes_do_not_certify_corrected_values():
    f = _attach_origin(_origin_frame()); f.iloc[-1, 0] += 0.1
    out = _origin_read(f)
    assert out['observation_origin'] == 'unverified'
    assert out['origin_status'] == 'frame_mismatch'
    assert out['turn_watch'] is None


def test_valid_endpoints_do_not_certify_a_missing_interior_path():
    f = _origin_frame(); raw = f.us10y.drop(f.index[-3])
    f.iloc[-3, 0] = f.iloc[-4, 0]
    out = _origin_read(_attach_origin(f, raw))
    assert out['velocity_bp']['5d'] == 5.0
    assert out['path_qualified'] is False
    assert out['turn_watch'] is None


def test_missing_fixed_endpoint_is_not_a_carried_measurement():
    f = _origin_frame(); raw = f.us10y.drop(f.index[-6])
    f.iloc[-6, 0] = f.iloc[-7, 0]
    out = _origin_read(_attach_origin(f, raw))
    assert out['velocity_bp']['5d'] is None
    assert out['velocity_bp']['22d'] == 22.0
    assert out['endpoint_dates']['5d'][0] == str(f.index[-6].date())


def test_capture_is_bounded_json_and_survives_frame_copy():
    import json
    f = _attach_origin(_origin_frame(2000)); before = copy.deepcopy(f.attrs)
    assert len(f.attrs['rate_observations']['us10y']['origin_dates']) <= 1260
    json.dumps(f.attrs, allow_nan=False)
    assert _origin_read(f.copy()) == _origin_read(f)
    assert f.attrs == before
    assert _origin_read(f)['source_id'] == 'DGS10'


def test_metadata_does_not_invent_historical_receipts():
    out = _origin_read(_attach_origin(_origin_frame()))
    assert out['available_at'] is None
    assert out['availability_status'] == 'not_provided_by_feature_frame'
    assert out['historical_availability_qualified'] is False
    assert out['horizon_basis'] == 'fixed_weekday_grid_intervals'


def test_nonfinite_raw_endpoint_is_unqualified():
    f = _origin_frame(); f.iloc[-1, 0] = np.inf
    out = _origin_read(_attach_origin(f))
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
    # A-RIC-F3-W2: this IS the nightly production shape (FRED prints T+1); the
    # single carried frame row is a publication lag, measured at the captured row.
    assert out['measurement_origin'] == 'last_captured_source_row'
    assert out['trailing_publication_lag_rows'] == 1
    assert out['level'] == round(raw.iloc[-1], 3)
    assert out['status'] == 'available' and out['null_reason'] is None
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
    out = _origin_read(inputs.build_features(overrides={'us10y': raw + 1.0}))
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
    monkeypatch.setattr(yield_momentum, 'capture_rate_observations', unavailable)
    out = inputs.build_features()
    evidence = _origin_read(out)
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


# Dated measured context must survive a stale latest frame without becoming fresh.
def test_carried_tail_retains_last_measured_change_with_its_own_dates():
    f = _origin_frame()
    raw = f.us10y.iloc[:-3].copy()
    f.loc[f.index[-3:], 'us10y'] = raw.iloc[-1]
    out = _origin_read(_attach_origin(f, raw))
    last = out['last_observed']
    # A-RIC-F3-W2: three trailing carried rows sit at the tolerance edge -> measured
    # at the last captured row; `last_observed` still describes the FULL grid.
    assert out['status'] == 'available' and out['level'] == round(raw.iloc[-1], 3)
    assert out['as_of'] == str(raw.index[-1].date())
    assert out['trailing_publication_lag_rows'] == 3
    assert out['velocity_bp']['5d'] == 5.0
    assert out['endpoint_dates']['5d'] == [str(f.index[-9].date()), str(f.index[-4].date())]
    assert out['turn_watch'] == 'extreme_high_watch'
    assert last['as_of'] == str(raw.index[-1].date())
    assert last['previous_as_of'] == str(raw.index[-2].date())
    assert last['level'] == round(raw.iloc[-1], 3)
    assert last['change_bp'] == 1.0
    assert last['age_grid_intervals'] == 3
    assert last['is_current_grid_row'] is False
    assert last['historical_availability_qualified'] is False


def test_measured_change_spans_missing_interior_without_daily_relabel():
    f = _origin_frame(); raw = f.us10y.drop(f.index[-2])
    f.iloc[-2, 0] = f.iloc[-3, 0]
    last = _origin_read(_attach_origin(f, raw))['last_observed']
    assert last['change_bp'] == 2.0
    assert last['elapsed_grid_intervals'] == 2
    assert last['previous_as_of'] == str(f.index[-3].date())
    assert last['is_current_grid_row'] is True


def test_one_measured_row_has_no_invented_previous_change():
    f = _origin_frame(); f['us10y'] = np.nan; f.iloc[-1, 0] = 4.5
    out = _origin_read(_attach_origin(f, f.us10y.dropna()))
    last = out['last_observed']
    assert last['level'] == 4.5 and last['is_current_grid_row'] is True
    assert last['previous_as_of'] is None and last['change_bp'] is None
    assert last['elapsed_grid_intervals'] is None


def test_unknown_or_changed_origin_cannot_create_measured_history():
    assert _origin_read(_origin_frame())['last_observed'] is None
    f = _attach_origin(_origin_frame()); f.iloc[-1, 0] += 0.1
    assert _origin_read(f)['last_observed'] is None


def test_caller_override_is_not_canonical_measured_history(monkeypatch):
    inputs, raw = _builder_fixture(monkeypatch)
    out = _origin_read(inputs.build_features(overrides={'us10y': raw}))
    assert out['observation_origin'] == 'caller_supplied_row'
    assert out['last_observed'] is None


def test_true_flat_observations_keep_zero_measured_change():
    f = _origin_frame(); f['us10y'] = 4.0
    last = _origin_read(_attach_origin(f))['last_observed']
    assert last['change_bp'] == 0.0
    assert last['elapsed_grid_intervals'] == 1


def test_weekend_elapsed_days_are_not_called_one_calendar_day():
    idx = pd.bdate_range('2026-01-01', '2026-04-06')  # Monday after Friday.
    f = pd.DataFrame({'us10y': np.arange(len(idx)) / 100 + 4.0}, index=idx)
    last = _origin_read(_attach_origin(f))['last_observed']
    assert last['elapsed_grid_intervals'] == 1
    assert last['elapsed_calendar_days'] == 3
    assert last['basis'] == 'latest_two_captured_source_rows_on_retained_grid'


def test_nonfinite_latest_does_not_erase_prior_measured_context():
    f = _origin_frame(); f.iloc[-1, 0] = np.inf
    out = _origin_read(_attach_origin(f))
    assert out['level'] is None and out['turn_watch'] is None
    assert out['last_observed']['as_of'] == str(f.index[-2].date())
    assert out['last_observed']['age_grid_intervals'] == 1
    assert out['last_observed']['is_current_grid_row'] is False


def test_no_observed_samples_in_retained_window_means_no_history():
    f = _origin_frame(1400); f['us10y'] = np.nan; f.iloc[0, 0] = 4.0
    out = _origin_read(_attach_origin(f, f.us10y.dropna()))
    assert out['last_observed'] is None


# A-RIC-F3-W1 — Expected-absence path qualification for US federal holidays.
# The fixed weekday grid is not a verified Treasury-session calendar; carried
# prints on US federal holidays are expected and do NOT withhold path
# qualification. Carried prints on any other weekday still do. A holiday row
# remains unmeasured, so an endpoint landing on a holiday is not promoted to
# a measurement.
def test_expected_holiday_absence_keeps_path_qualified():
    f = _origin_frame(100)
    holidays = [pd.Timestamp(d) for d in ('2025-01-20', '2025-02-17')
                if pd.Timestamp(d) in f.index]
    assert len(holidays) == 2  # Both fall on weekdays inside this grid.
    raw = f.us10y.drop([d for d in holidays])
    out = _origin_read(_attach_origin(f.copy(), raw))
    assert out['path_qualified'] is True
    assert out['holiday_basis'] == 'us_federal_holidays_plus_good_friday_v1'
    assert out['path_qualification_basis'] == 'captured_source_rows_or_expected_absent'
    # Calendar census, not a carry census: MLK + Presidents' Day (carried) and
    # Good Friday 2025-04-18 (printed in this fixture) are all expected absences.
    assert out['expected_absent_grid_rows'] == 3
    assert out['unexpected_carried_grid_rows'] == 0
    assert out['observation_origin'] == 'captured_source_row'
    # Monotonic +1 bp/day fixture → trailing percentile == 1.0; the 22d/44d
    # endpoints (index[-23] and index[-45]) do not land on the two holidays.
    assert f.index[-23] not in holidays and f.index[-45] not in holidays
    assert out['velocity_bp']['22d'] == 22.0
    assert out['acceleration_bp'] == 0.0  # 22d change equals the 22d change 22 rows earlier
    assert out['turn_watch'] == 'extreme_high_watch'


def test_unexpected_weekday_absence_still_withholds_path_qualification():
    f = _origin_frame(100)
    # 2025-03-05 is an ordinary Wednesday — a carried print here is unexpected.
    unexpected = pd.Timestamp('2025-03-05')
    assert unexpected in f.index
    raw = f.us10y.drop([unexpected])
    out = _origin_read(_attach_origin(f.copy(), raw))
    assert out['path_qualified'] is False
    assert out['expected_absent_grid_rows'] == 3  # Holidays + Good Friday still counted.
    assert out['unexpected_carried_grid_rows'] == 1
    assert out['turn_watch'] is None
    assert (out['null_reason']
            == 'endpoint comparisons only; complete observed path not qualified')


def test_holiday_endpoint_is_still_not_a_measurement():
    # 100 bdays ending 2025-02-24; index[-6] = 2025-02-17 (Presidents' Day).
    idx = pd.bdate_range(end='2025-02-24', periods=100)
    assert idx[-6] == pd.Timestamp('2025-02-17')
    f = pd.DataFrame({'us10y': 4.0 + np.arange(100) / 100}, index=idx)
    raw = f.us10y.drop([idx[-6]])
    out = _origin_read(_attach_origin(f.copy(), raw))
    assert out['path_qualified'] is True
    assert out['velocity_bp']['5d'] is None  # Holiday endpoint is unmeasured.
    assert isinstance(out['velocity_bp']['22d'], float)
    assert out['velocity_bp']['22d'] == 22.0


def test_expected_absent_grid_is_pure_and_bounded():
    # Pure helper: empty index returns an empty list.
    assert yield_momentum.expected_absent_grid(pd.DatetimeIndex([])) == []
    # 2025 has 11 US federal holidays, every one of them a weekday.
    idx = pd.bdate_range('2025-01-02', periods=100)
    flags = yield_momentum.expected_absent_grid(idx)
    assert len(flags) == len(idx)
    assert sum(flags) == 3  # MLK Day (Jan 20) + Presidents' Day (Feb 17) + Good Friday (Apr 18).
    # Pin identities (not just count) so any calendar drift fails loudly.
    flagged = [idx[i] for i, f in enumerate(flags) if f]
    assert flagged == [pd.Timestamp('2025-01-20'), pd.Timestamp('2025-02-17'),
                       pd.Timestamp('2025-04-18')]
    assert yield_momentum.HOLIDAY_BASIS == 'us_federal_holidays_plus_good_friday_v1'


def test_turn_watch_percentile_excludes_carried_holiday_nans():
    # Regression: on a 1260-row weekday grid ~58 expected absences fall inside
    # (53 federal holidays + 5 Good Fridays) and a grid-length denominator scored
    # each carried NaN as "not <= latest", dragging a true ~0.92 percentile to
    # ~0.88 and suppressing extreme_high_watch. `_turn_watch` keeps its grid-based
    # guard/window and excludes the NaNs from the percentile denominator only.
    idx = pd.bdate_range(end='2026-09-23', periods=1260)
    holiday_flags = yield_momentum.expected_absent_grid(idx)
    holiday_rows = [idx[i] for i, f in enumerate(holiday_flags) if f]
    assert len(holiday_rows) == 58  # 53 federal + 5 Good Fridays on this grid.

    # Construct values so 97 measured samples are above the last measured sample
    # and the remaining 1105 are <= it — observed percentile 1105/1202 =
    # 0.9193 (above the 0.90 extreme_high_watch threshold) which a
    # grid-length denominator scores as 1105/1260 = 0.877 (below 0.90 -> None).
    n = 1260
    holiday_positions = {idx.get_loc(d) for d in holiday_rows}
    measured_positions = [i for i in range(n) if i not in holiday_positions]
    assert len(measured_positions) == 1202
    last_position = measured_positions[-1]  # Last grid point is a Wednesday.
    high_positions = measured_positions[:97]  # 97 measured samples above last.
    values = np.full(n, 4.0)
    for pos in high_positions:
        values[pos] = 5.0
    values[last_position] = 4.5

    f = pd.DataFrame({'us10y': values}, index=idx)
    raw = f.us10y.drop(holiday_rows)
    out = _origin_read(_attach_origin(f.copy(), raw))
    assert out['path_qualified'] is True
    assert out['expected_absent_grid_rows'] == 58
    assert out['unexpected_carried_grid_rows'] == 0
    below = len(measured_positions) - 97
    assert below / len(measured_positions) > 0.90 > below / n
    assert out['turn_watch'] == 'extreme_high_watch'


# --- A-RIC-F3-W2 (2026-09-25): trailing publication-lag tolerance -------------
def _lagged(n, f=None):
    f = _origin_frame(100) if f is None else f
    raw = f.us10y.iloc[:-n].copy()
    f.loc[f.index[-n:], 'us10y'] = raw.iloc[-1]
    return f, raw


@pytest.mark.parametrize('n', [1, 2, 3])
def test_trailing_publication_lag_within_tolerance_measures_at_last_captured_row(n):
    f, raw = _lagged(n)
    out = _origin_read(_attach_origin(f, raw))
    assert out['measurement_origin'] == 'last_captured_source_row'
    assert out['trailing_publication_lag_rows'] == n
    assert out['trailing_expected_absent_rows'] == 0
    assert out['lag_tolerance_rows'] == 3
    assert out['lag_basis'] == 'fred_next_business_day_publication_v1'
    assert out['observation_origin'] == 'carried'  # the FRAME's latest row is still a carry
    assert out['as_of'] == str(raw.index[-1].date())
    assert out['frame_as_of'] == str(f.index[-1].date())
    assert out['level'] == round(raw.iloc[-1], 3)
    assert out['path_qualified'] is True and out['status'] == 'available'
    assert out['null_reason'] is None
    assert out['velocity_bp']['5d'] == 5.0 and out['velocity_bp']['22d'] == 22.0
    assert out['endpoint_dates']['5d'] == [str(f.index[-n - 6].date()), str(f.index[-n - 1].date())]
    assert out['turn_watch'] == 'extreme_high_watch'


def test_trailing_lag_beyond_tolerance_stays_stale_and_names_the_lag():
    f, raw = _lagged(4)
    out = _origin_read(_attach_origin(f, raw))
    assert out['measurement_origin'] == 'latest_grid_row'
    assert out['trailing_publication_lag_rows'] == 4
    assert out['status'] == 'stale' and out['level'] is None
    assert all(v is None for v in out['velocity_bp'].values())
    assert out['turn_watch'] is None
    assert out['null_reason'].startswith('latest grid value is missing, nonfinite or carried')
    assert out['null_reason'].endswith('; trailing publication lag 4 rows exceeds tolerance 3')


def test_interior_unexpected_absence_plus_trailing_lag_withholds_the_path():
    f = _origin_frame(100)
    unexpected = pd.Timestamp('2025-03-05')  # an ordinary Wednesday inside the grid
    assert unexpected in f.index
    raw = f.us10y.drop([unexpected]).iloc[:-2].copy()
    f.loc[f.index[-2:], 'us10y'] = raw.iloc[-1]
    out = _origin_read(_attach_origin(f, raw))
    assert out['path_qualified'] is False
    assert out['measurement_origin'] == 'latest_grid_row'
    assert out['trailing_publication_lag_rows'] == 2
    assert out['unexpected_carried_grid_rows'] == 3  # interior + 2 trailing
    assert out['level'] is None and out['turn_watch'] is None
    assert out['null_reason'].endswith('; interior unexpected absence withholds the path')


def test_holiday_inside_the_trailing_run_is_skipped_to_the_last_captured_row():
    # 100 bdays ending 2025-02-18 (Tue); index[-2] = 2025-02-17 (Presidents' Day).
    idx = pd.bdate_range(end='2025-02-18', periods=100)
    assert idx[-2] == pd.Timestamp('2025-02-17')
    f = pd.DataFrame({'us10y': 4.0 + np.arange(100) / 100}, index=idx)
    raw = f.us10y.iloc[:-2].copy()          # holiday did not print; Tuesday not yet published
    f.loc[idx[-2:], 'us10y'] = raw.iloc[-1]
    out = _origin_read(_attach_origin(f, raw))
    assert out['trailing_publication_lag_rows'] == 1
    assert out['trailing_expected_absent_rows'] == 1
    assert out['measurement_origin'] == 'last_captured_source_row'
    assert out['path_qualified'] is True
    assert out['as_of'] == str(idx[-3].date())
    assert out['level'] == round(raw.iloc[-1], 3)
    assert out['velocity_bp']['5d'] == 5.0


def test_frame_ending_on_a_holiday_without_lag_keeps_the_w1_state():
    # W1 state (a): the latest grid row is an expected absence and nothing lags
    # behind it -> path qualified, but no measurement is promoted.
    idx = pd.bdate_range(end='2025-02-17', periods=100)
    f = pd.DataFrame({'us10y': 4.0 + np.arange(100) / 100}, index=idx)
    raw = f.us10y.iloc[:-1].copy()
    f.loc[idx[-1:], 'us10y'] = raw.iloc[-1]
    out = _origin_read(_attach_origin(f, raw))
    assert out['trailing_publication_lag_rows'] == 0
    assert out['trailing_expected_absent_rows'] == 1
    assert out['measurement_origin'] == 'latest_grid_row'
    assert out['path_qualified'] is True and out['status'] == 'stale'
    assert out['level'] is None


def test_nonfinite_trailing_print_is_not_a_publication_lag():
    f = _origin_frame(100); raw = f.us10y.copy(); raw.iloc[-1] = np.inf
    f.iloc[-1, 0] = np.inf
    out = _origin_read(_attach_origin(f, raw))
    assert out['measurement_origin'] == 'latest_grid_row'
    assert out['level'] is None and out['turn_watch'] is None


def test_lag_read_is_deterministic_and_keeps_every_wire_key():
    f, raw = _lagged(2)
    a = _origin_read(_attach_origin(f.copy(), raw))
    b = _origin_read(_attach_origin(f.copy(), raw))
    assert a == b
    baseline = _origin_read(_attach_origin(_origin_frame(100)))
    assert set(baseline) <= set(a)
    payload = yield_momentum.build_yield_momentum(_attach_origin(f.copy(), raw))
    assert payload['calculation_version'] == 'fixed_grid_origin.v4'
    assert any('publication lag' in c and 'at most 3' in c for c in payload['caveats'])


# --- Y0 (RIC-INCLUDED-CORE): curve convention + endpoint qualification ---------
# Golden v4 payloads captured at base 402b57defb3 with /tmp/y0_golden.py (never
# committed); the control test proves every pre-existing output byte is unchanged.
_GOLDEN_G1 = '{"asof": "2025-05-21", "authority": false, "calculation_version": "fixed_grid_origin.v4", "can_score": false, "can_size": false, "can_trade": false, "caveats": ["Weekday grid intervals are not verified Treasury trading sessions.", "Captured source rows do not certify historical availability.", "Endpoint changes do not prove continuous deceleration or a market turn.", "Expected absences are US federal holidays and Good Friday only; a carried print on any other weekday still withholds path qualification.", "A trailing publication lag of at most 3 weekday rows is an expected absence: momentum is then measured and dated at the last captured source row (as_of), never at the frame date."], "display_only": true, "schema": "yield_momentum.v1", "series": {"10y": {"acceleration_bp": 0.0, "as_of": "2025-05-21", "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": ["2025-04-21", "2025-05-21"], "5d": ["2025-05-14", "2025-05-21"], "63d": ["2025-02-21", "2025-05-21"]}, "expected_absent_grid_rows": 3, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": {"age_calendar_days": 0, "age_grid_intervals": 0, "as_of": "2025-05-21", "basis": "latest_two_captured_source_rows_on_retained_grid", "change_bp": 1.0, "elapsed_calendar_days": 1, "elapsed_grid_intervals": 1, "historical_availability_qualified": false, "is_current_grid_row": true, "level": 4.99, "previous_as_of": "2025-05-20", "previous_level": 4.98}, "level": 4.99, "measurement_origin": "latest_grid_row", "null_reason": null, "observation_origin": "captured_source_row", "origin_status": "matched_captured_alignment", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": true, "source_basis": "captured_source_rows", "source_column": "us10y", "source_digest": "753242c43199b3031f40faea72065a7b3194420d7af18fe343746ac6d029fd86", "source_id": "DGS10", "status": "available", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": "extreme_high_watch", "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": 22.0, "5d": 5.0, "63d": 63.0}}, "20y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us20y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us20y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}, "2y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us2y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us2y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}, "30y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us30y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us30y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}, "5y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us5y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us5y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}}}'
_GOLDEN_G2 = '{"asof": "2025-05-21", "authority": false, "calculation_version": "fixed_grid_origin.v4", "can_score": false, "can_size": false, "can_trade": false, "caveats": ["Weekday grid intervals are not verified Treasury trading sessions.", "Captured source rows do not certify historical availability.", "Endpoint changes do not prove continuous deceleration or a market turn.", "Expected absences are US federal holidays and Good Friday only; a carried print on any other weekday still withholds path qualification.", "A trailing publication lag of at most 3 weekday rows is an expected absence: momentum is then measured and dated at the last captured source row (as_of), never at the frame date."], "display_only": true, "schema": "yield_momentum.v1", "series": {"10y": {"acceleration_bp": 0.0, "as_of": "2025-05-19", "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": 4.97, "endpoint_dates": {"22d": ["2025-04-17", "2025-05-19"], "5d": ["2025-05-12", "2025-05-19"], "63d": ["2025-02-19", "2025-05-19"]}, "expected_absent_grid_rows": 3, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": {"age_calendar_days": 2, "age_grid_intervals": 2, "as_of": "2025-05-19", "basis": "latest_two_captured_source_rows_on_retained_grid", "change_bp": 1.0, "elapsed_calendar_days": 3, "elapsed_grid_intervals": 1, "historical_availability_qualified": false, "is_current_grid_row": false, "level": 4.97, "previous_as_of": "2025-05-16", "previous_level": 4.96}, "level": 4.97, "measurement_origin": "last_captured_source_row", "null_reason": null, "observation_origin": "carried", "origin_status": "matched_captured_alignment", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": true, "source_basis": "captured_source_rows", "source_column": "us10y", "source_digest": "09250db561f503f32cecadf5d29799d38fd2ddbc27a3d1b376d5b48959709d84", "source_id": "DGS10", "status": "available", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 2, "turn_watch": "extreme_high_watch", "unexpected_carried_grid_rows": 2, "velocity_bp": {"22d": 22.0, "5d": 5.0, "63d": 63.0}}, "20y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us20y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us20y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}, "2y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us2y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us2y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}, "30y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us30y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us30y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}, "5y": {"acceleration_bp": null, "as_of": null, "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": null, "5d": null, "63d": null}, "expected_absent_grid_rows": 0, "frame_as_of": "2025-05-21", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": null, "measurement_origin": "latest_grid_row", "null_reason": "source column us5y unavailable", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us5y", "source_id": null, "status": "missing", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": null, "5d": null, "63d": null}}}}'
_GOLDEN_G3 = '{"asof": "2027-02-24", "authority": false, "calculation_version": "fixed_grid_origin.v4", "can_score": false, "can_size": false, "can_trade": false, "caveats": ["Weekday grid intervals are not verified Treasury trading sessions.", "Captured source rows do not certify historical availability.", "Endpoint changes do not prove continuous deceleration or a market turn.", "Expected absences are US federal holidays and Good Friday only; a carried print on any other weekday still withholds path qualification.", "A trailing publication lag of at most 3 weekday rows is an expected absence: momentum is then measured and dated at the last captured source row (as_of), never at the frame date."], "display_only": true, "schema": "yield_momentum.v1", "series": {"10y": {"acceleration_bp": 0.0, "as_of": "2027-02-24", "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": ["2027-01-25", "2027-02-24"], "5d": ["2027-02-17", "2027-02-24"], "63d": ["2026-11-27", "2027-02-24"]}, "expected_absent_grid_rows": 0, "frame_as_of": "2027-02-24", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": 3.7, "measurement_origin": "latest_grid_row", "null_reason": "endpoint comparisons only; complete observed path not qualified", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us10y", "source_id": null, "status": "available", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": 3.7, "5d": 0.8, "63d": 10.5}}, "20y": {"acceleration_bp": 0.0, "as_of": "2027-02-24", "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": ["2027-01-25", "2027-02-24"], "5d": ["2027-02-17", "2027-02-24"], "63d": ["2026-11-27", "2027-02-24"]}, "expected_absent_grid_rows": 0, "frame_as_of": "2027-02-24", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": 3.8, "measurement_origin": "latest_grid_row", "null_reason": "endpoint comparisons only; complete observed path not qualified", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us20y", "source_id": null, "status": "available", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": 3.7, "5d": 0.8, "63d": 10.5}}, "2y": {"acceleration_bp": 0.0, "as_of": "2027-02-24", "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": ["2027-01-25", "2027-02-24"], "5d": ["2027-02-17", "2027-02-24"], "63d": ["2026-11-27", "2027-02-24"]}, "expected_absent_grid_rows": 0, "frame_as_of": "2027-02-24", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": 3.5, "measurement_origin": "latest_grid_row", "null_reason": "endpoint comparisons only; complete observed path not qualified", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us2y", "source_id": null, "status": "available", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": 3.7, "5d": 0.8, "63d": 10.5}}, "30y": {"acceleration_bp": 0.0, "as_of": "2027-02-24", "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": ["2027-01-25", "2027-02-24"], "5d": ["2027-02-17", "2027-02-24"], "63d": ["2026-11-27", "2027-02-24"]}, "expected_absent_grid_rows": 0, "frame_as_of": "2027-02-24", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": 3.9, "measurement_origin": "latest_grid_row", "null_reason": "endpoint comparisons only; complete observed path not qualified", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us30y", "source_id": null, "status": "available", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": 3.7, "5d": 0.8, "63d": 10.5}}, "5y": {"acceleration_bp": 0.0, "as_of": "2027-02-24", "availability_status": "not_provided_by_feature_frame", "available_at": null, "carried_level": null, "endpoint_dates": {"22d": ["2027-01-25", "2027-02-24"], "5d": ["2027-02-17", "2027-02-24"], "63d": ["2026-11-27", "2027-02-24"]}, "expected_absent_grid_rows": 0, "frame_as_of": "2027-02-24", "historical_availability_qualified": false, "holiday_basis": "us_federal_holidays_plus_good_friday_v1", "horizon_basis": "fixed_weekday_grid_intervals", "lag_basis": "fred_next_business_day_publication_v1", "lag_tolerance_rows": 3, "last_observed": null, "level": 3.6, "measurement_origin": "latest_grid_row", "null_reason": "endpoint comparisons only; complete observed path not qualified", "observation_origin": "unverified", "origin_status": "not_provided", "path_qualification_basis": "captured_source_rows_or_expected_absent", "path_qualified": false, "source_column": "us5y", "source_id": null, "status": "available", "trailing_expected_absent_rows": 0, "trailing_publication_lag_rows": 0, "turn_watch": null, "unexpected_carried_grid_rows": 0, "velocity_bp": {"22d": 3.7, "5d": 0.8, "63d": 10.5}}}}'


def _g1_payload():
    return yield_momentum.build_yield_momentum(_attach_origin(_origin_frame(100)))


def _g2_payload_and_frame():
    f, raw = _lagged(2)
    return yield_momentum.build_yield_momentum(_attach_origin(f, raw)), f


def _g3_payload():
    return yield_momentum.build_yield_momentum(_frame(300))


def _y0_carried_fixture():
    # An interior unexpected absence: 2025-05-14 is an ordinary Wednesday whose
    # frame value is a carried prior print.
    f = _origin_frame(100)
    d = f.index[-6]
    assert d == pd.Timestamp('2025-05-14')
    assert not yield_momentum.expected_absent_grid(pd.DatetimeIndex([d]))[0]
    raw = f.us10y.drop([d]).copy()
    f.loc[d, 'us10y'] = f.us10y.loc[f.index[-7]]
    return _origin_read(_attach_origin(f, raw)), f


def _y0_holiday_fixture(carried_fill=False):
    # 100 bdays ending 2025-02-24; index[-6] = 2025-02-17 (Presidents' Day).
    idx = pd.bdate_range(end='2025-02-24', periods=100)
    assert idx[-6] == pd.Timestamp('2025-02-17')
    f = pd.DataFrame({'us10y': 4.0 + np.arange(100) / 100}, index=idx)
    if carried_fill:
        f.loc[idx[-6], 'us10y'] = f.us10y.loc[idx[-7]]
    raw = f.us10y.drop([idx[-6]])
    return _origin_read(_attach_origin(f.copy(), raw))


def _y0_caller_fixture():
    f = _origin_frame(100)
    f.attrs['rate_observations'] = {'us10y': yield_momentum.capture_rate_observations(
        f.us10y, f.us10y, source_id='DGS10', source_column='us10y',
        source_basis='caller_override')}
    return _origin_read(f)


def _y0_endpoint_points(payload):
    for read in payload['series'].values():
        for endpoint in read.get('endpoints', {}).values():
            if endpoint is None:
                continue
            for side in ('start', 'end'):
                yield endpoint[side]


def test_y0_golden_control_keeps_every_v4_byte():
    import json
    golden = {'G1': _GOLDEN_G1, 'G2': _GOLDEN_G2, 'G3': _GOLDEN_G3}
    builds = {'G1': _g1_payload(), 'G2': _g2_payload_and_frame()[0],
              'G3': _g3_payload()}
    for name, payload in builds.items():
        stripped = dict(payload)
        stripped.pop('qualification_version', None)
        stripped['series'] = {
            label: {k: v for k, v in read.items() if k not in (
                'curve_convention', 'level_unit', 'change_unit', 'endpoints',
                'turn_certified')}
            for label, read in payload['series'].items()}
        assert json.dumps(stripped, sort_keys=True, ensure_ascii=False,
                          default=str) == golden[name]
    for payload in builds.values():
        assert list(payload)[-1] == 'qualification_version'
        for read in payload['series'].values():
            assert list(read)[-5:] == ['curve_convention', 'level_unit',
                                       'change_unit', 'endpoints',
                                       'turn_certified']


def test_captured_endpoints_are_certified_par_with_units():
    read = _g1_payload()['series']['10y']
    f = _origin_frame(100)
    assert read['curve_convention'] == 'par'
    assert read['level_unit'] == 'pct_ann_rate'
    assert read['change_unit'] == 'bp'
    for h in (5, 22, 63):
        endpoint = read['endpoints'][f'{h}d']
        assert endpoint is not None
        assert endpoint['certified'] is True
        assert endpoint['not_certified_reason'] is None
        assert endpoint['change_unit'] == 'bp'
        for side, date in zip(('start', 'end'), read['endpoint_dates'][f'{h}d']):
            point = endpoint[side]
            assert point['origin'] == 'captured_source_row'
            assert point['value_state'] == 'present'
            assert point['unit'] == 'pct_ann_rate'
            assert point['curve_convention'] == 'par'
            assert point['quality'] == [] and point['limitations'] == []
            assert point['carried_from'] is None
            assert point['date'] == date
            assert point['level'] == round(float(f.loc[pd.Timestamp(date), 'us10y']), 3)
    assert read['turn_certified'] is True


def test_carried_endpoint_never_certifies():
    read, f = _y0_carried_fixture()
    endpoint = read['endpoints']['5d']
    start = endpoint['start']
    assert start['origin'] == 'carried'
    assert start['value_state'] == 'stale'
    assert start['quality'] == ['carried']
    assert start['level'] is None
    assert start['carried_from'] == str(f.index[-7].date())
    assert endpoint['certified'] is False
    assert endpoint['not_certified_reason'] == 'start_endpoint_carried'
    assert read['velocity_bp']['5d'] is None  # v4 unchanged by qualification.
    assert read['endpoints']['22d']['certified'] is True  # endpoint comparison.
    assert read['turn_certified'] is False  # the PATH is not qualified.


def test_holiday_endpoint_is_expected_absent_not_certified():
    read = _y0_holiday_fixture()
    endpoint = read['endpoints']['5d']
    start = endpoint['start']
    assert start['origin'] == 'expected_absent'
    assert 'expected_absence_holiday_basis' in start['limitations']
    assert start['level'] is None
    assert start['value_state'] == 'missing'
    assert start['carried_from'] is None  # frame kept its own (unequal) value.
    assert endpoint['certified'] is False
    assert endpoint['not_certified_reason'] == 'start_endpoint_expected_absent'
    assert read['endpoints']['22d']['certified'] is True

    carried = _y0_holiday_fixture(carried_fill=True)
    start = carried['endpoints']['5d']['start']
    assert start['origin'] == 'expected_absent'  # precedence 3 beats 4.
    assert start['value_state'] == 'stale'
    assert start['quality'] == ['carried']
    assert start['carried_from'] == '2025-02-14'
    assert carried['endpoints']['5d']['certified'] is False


def test_lagged_end_endpoint_is_the_last_captured_row():
    payload, f = _g2_payload_and_frame()
    read = payload['series']['10y']
    endpoint = read['endpoints']['5d']
    assert endpoint['end']['date'] == str(f.index[-3].date())
    assert endpoint['end']['origin'] == 'captured_source_row'
    assert endpoint['certified'] is True
    latest = str(f.index[-1].date())
    for h in (5, 22, 63):
        for side in ('start', 'end'):
            assert read['endpoints'][f'{h}d'][side]['date'] != latest


def test_unverified_frame_endpoints_never_certify():
    for read in _g3_payload()['series'].values():
        assert read['turn_certified'] is False
        for h in (5, 22, 63):
            endpoint = read['endpoints'][f'{h}d']
            assert endpoint is not None
            assert endpoint['certified'] is False
            assert endpoint['not_certified_reason'] == 'origin_not_provided'
            for side in ('start', 'end'):
                point = endpoint[side]
                assert point['origin'] == 'unverified'
                assert point['limitations'] == ['observation_origin_unverified']
                assert point['value_state'] == 'present'
                assert isinstance(point['level'], float)
    f = _attach_origin(_origin_frame(100))
    f.iloc[-1, 0] += 0.1  # frame no longer matches the captured alignment.
    read = _origin_read(f)
    assert read['origin_status'] == 'frame_mismatch'
    for h in (5, 22, 63):
        endpoint = read['endpoints'][f'{h}d']
        assert endpoint is not None
        assert endpoint['certified'] is False
        assert endpoint['not_certified_reason'] == 'origin_frame_mismatch'


def test_caller_override_endpoints_are_not_certified():
    read = _y0_caller_fixture()
    endpoint = read['endpoints']['5d']
    for side in ('start', 'end'):
        assert endpoint[side]['origin'] == 'caller_supplied_row'
        assert endpoint[side]['value_state'] == 'present'
    assert endpoint['certified'] is False
    assert endpoint['not_certified_reason'] == 'caller_override_basis'
    assert read['turn_certified'] is False


def test_missing_and_short_series_have_no_invented_endpoints():
    missing = _build(_frame(100).drop(columns=['us30y']))['series']['30y']
    assert missing['endpoints'] == {'5d': None, '22d': None, '63d': None}
    assert missing['turn_certified'] is False
    assert missing['curve_convention'] == 'par'
    assert missing['level_unit'] == 'pct_ann_rate'
    short = _build(_frame(10))['series']['10y']
    assert short['endpoints']['5d'] is not None
    assert short['endpoints']['22d'] is None
    assert short['endpoints']['63d'] is None
    # A non-captured, non-unverified endpoint NEVER carries a numeric level
    # (missing is never 0, a carry is never a print).
    payloads = [_g1_payload(), _g2_payload_and_frame()[0], _g3_payload(),
                _build(_frame(10)), _build(_frame(100).drop(columns=['us30y']))]
    for payload in payloads:
        for point in _y0_endpoint_points(payload):
            assert point['level'] is None or point['origin'] in (
                'captured_source_row', 'caller_supplied_row', 'unverified')


def test_treasury_cmt_endpoints_are_par_never_zero():
    assert set(yield_momentum.CURVE_CONVENTION) == set(yield_momentum.SERIES.values())
    assert set(yield_momentum.CURVE_CONVENTION.values()) == {'par'}
    for payload in (_g1_payload(), _g2_payload_and_frame()[0], _g3_payload()):
        for read in payload['series'].values():
            assert read['curve_convention'] != 'zero'
            for point in _y0_endpoint_points(payload):
                assert point['curve_convention'] != 'zero'
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setitem(yield_momentum.SERIES, '7y', 'us7y')
        f = _frame(100)
        f['us7y'] = 4.0 + np.arange(100) / 100
        seven = _build(f)['series']['7y']
    assert seven['curve_convention'] is None  # unknown, never par or zero.
    for h in (5, 22, 63):
        endpoint = seven['endpoints'][f'{h}d']
        if endpoint is None:
            continue
        for side in ('start', 'end'):
            assert endpoint[side]['curve_convention'] is None


def test_turn_certified_only_on_a_qualified_turn():
    read = _g1_payload()['series']['10y']
    assert read['turn_watch'] is not None
    assert read['turn_certified'] is True
    f = _origin_frame(100)
    unexpected = pd.Timestamp('2025-03-05')  # ordinary Wednesday inside the grid
    assert unexpected in f.index
    raw = f.us10y.drop([unexpected])
    withheld = _origin_read(_attach_origin(f.copy(), raw))
    assert withheld['path_qualified'] is False
    assert withheld['turn_certified'] is False
    for read in _g3_payload()['series'].values():
        assert read['turn_certified'] is False


def test_authority_flags_stay_false_and_versions():
    for payload in (_g1_payload(), _g2_payload_and_frame()[0], _g3_payload()):
        assert payload['display_only'] is True
        for key in ('authority', 'can_score', 'can_size', 'can_trade'):
            assert payload[key] is False
        assert payload['calculation_version'] == 'fixed_grid_origin.v4'
        assert payload['qualification_version'] == 'curve_endpoint_qualification.v1'


@pytest.mark.parametrize('index_kind', ['range_index', 'date_strings', 'tz_utc'])
def test_invalid_grid_read_never_raises_and_dates_no_endpoint(index_kind):
    # A frame whose index is not a naive weekday date grid reads as the explicit
    # invalid_grid null state; the endpoint provenance must never index that
    # undated grid by date. Origin is deliberately not attached.
    f = _origin_frame(100)
    if index_kind == 'range_index':
        f.index = pd.RangeIndex(len(f))
    elif index_kind == 'date_strings':
        f.index = [str(d.date()) for d in f.index]
    else:
        f.index = f.index.tz_localize('UTC')
    p = yield_momentum.build_yield_momentum(f)  # must not raise
    read = p['series']['10y']
    assert read['status'] == 'invalid_grid'
    assert all(value is None for value in read['endpoints'].values())
    assert read['turn_certified'] is False
    assert read['curve_convention'] == 'par'
    assert read['level_unit'] == 'pct_ann_rate'
    assert p['qualification_version'] == 'curve_endpoint_qualification.v1'
