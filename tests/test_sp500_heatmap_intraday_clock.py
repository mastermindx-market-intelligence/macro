"""Exact elapsed-time returns, never row-count or reconstructed price clocks."""
import json

import numpy as np
import pandas as pd
import pytest

from engine.sp500_heatmap import build_heatmap, intraday_returns


def frame(times, values):
    return pd.DataFrame({'close': values}, index=pd.to_datetime(times, utc=True))


def test_missing_hour_is_two_hours_not_one():
    bars = frame(['2026-10-12T14:00Z', '2026-10-12T16:00Z'], [100., 105.])
    assert intraday_returns({'X': bars}) == {'X': {'2H': 5.0}}


def test_weekend_gap_is_not_intraday():
    bars = frame(['2026-10-09T19:00Z', '2026-10-12T14:00Z'], [100., 105.])
    assert intraday_returns({'X': bars}) == {}


def test_five_minute_rows_do_not_become_an_hour():
    bars = frame(['2026-10-12T14:00Z', '2026-10-12T14:05Z'], [100., 105.])
    assert intraday_returns({'X': bars}) == {'X': {'5M': 5.0}}


def test_complete_hourly_legacy_values_are_unchanged():
    bars = pd.DataFrame({'close': [100., 101., 102., 103., 104.]},
                        index=pd.date_range('2026-10-12T14:00Z', periods=5, freq='h'))
    assert intraday_returns({'X': bars}) == {'X': {
        '1H': round((104/103-1)*100, 2),
        '2H': round((104/102-1)*100, 2), '4H': 4.0}}


def test_all_declared_minute_windows_use_their_actual_endpoints():
    bars = pd.DataFrame({'close': np.arange(100., 149.)},
                        index=pd.date_range('2026-10-12T14:00Z', periods=49, freq='5min'))
    expected = {k: round((148/(148-m/5)-1)*100, 2)
                for k, m in [('5M',5),('10M',10),('15M',15),('30M',30),('1H',60),('2H',120),('4H',240)]}
    assert intraday_returns({'X': bars}) == {'X': expected}


def test_missing_target_does_not_use_nearest_or_forward_filled_price():
    bars = frame(['2026-10-12T14:00Z','2026-10-12T14:55Z','2026-10-12T16:00Z'], [100.,103.,105.])
    assert intraday_returns({'X': bars}) == {'X': {'2H': 5.0}}


def test_missing_interior_does_not_destroy_an_observed_endpoint_return():
    # This is endpoint arithmetic, NOT a certificate of intermediate path coverage.
    bars = frame(['2026-10-12T14:00Z','2026-10-12T18:00Z'], [100.,104.])
    assert intraday_returns({'X': bars}) == {'X': {'4H': 4.0}}


@pytest.mark.parametrize('bad', [np.nan,np.inf,-np.inf,0.,-1.,True,'bad'])
def test_invalid_latest_price_cannot_rewind_to_an_older_good_row(bad):
    bars = frame(['2026-10-12T14:00Z','2026-10-12T15:00Z','2026-10-12T16:00Z'], [100.,102.,bad])
    assert intraday_returns({'X': bars}) == {}


@pytest.mark.parametrize('index', [pd.RangeIndex(2),pd.date_range('2026-10-12',periods=2,freq='h'),pd.Index(['a','b'])])
def test_absent_or_naive_clock_is_not_assumed(index):
    assert intraday_returns({'X': pd.DataFrame({'close':[100.,105.]},index=index)}) == {}


def test_duplicate_clocks_are_ambiguous_even_if_prices_match():
    bars = frame(['2026-10-12T14:00Z','2026-10-12T14:00Z','2026-10-12T15:00Z'], [100.,100.,105.])
    assert intraday_returns({'X': bars}) == {}


def test_unordered_input_is_sorted_without_mutation():
    bars = frame(['2026-10-12T15:00Z','2026-10-12T14:00Z'], [105.,100.])
    before = bars.copy(deep=True)
    assert intraday_returns({'X': bars}) == {'X': {'1H': 5.0}}
    pd.testing.assert_frame_equal(bars, before)


def test_timezone_representation_does_not_change_elapsed_returns():
    bars = frame(['2026-10-12T14:00Z','2026-10-12T15:00Z'], [100.,105.])
    converted = bars.tz_convert('America/New_York')
    assert intraday_returns({'X': bars}) == intraday_returns({'X': converted})


def test_invalid_reference_is_omitted_without_losing_other_valid_horizons():
    bars = frame(['2026-10-12T14:00Z','2026-10-12T15:00Z','2026-10-12T16:00Z'], [100.,0.,105.])
    assert intraday_returns({'X': bars}) == {'X': {'2H': 5.0}}


def test_nat_and_duplicate_close_columns_are_unusable():
    a = frame(['2026-10-12T14:00Z',None], [100.,105.])
    b = pd.DataFrame([[100.,101.],[105.,106.]],columns=['close','close'],
                     index=pd.date_range('2026-10-12T14:00Z',periods=2,freq='h'))
    assert intraday_returns({'A':a,'B':b}) == {}


def test_empty_missing_and_unrelated_columns_are_safe():
    assert intraday_returns({}) == {}
    assert intraday_returns({'X':None,'Y':pd.DataFrame({'open':[100.,105.]})}) == {}


def test_real_payload_consumer_enables_only_observed_window_and_preserves_daily():
    cons = pd.DataFrame({'name':['Example'],'sector':['Technology']},index=['X'])
    daily = pd.DataFrame({'X':[100.,101.]},index=pd.to_datetime(['2026-10-09','2026-10-12']))
    bars = frame(['2026-10-12T14:00Z','2026-10-12T14:05Z'], [100.,105.])
    old = build_heatmap(cons,daily)
    got = build_heatmap(cons,daily,intraday_bars={'X':bars})
    available = {r['key']:r['available'] for r in got['timeframes']}
    assert available['5M'] is True
    assert available['1H'] is False
    assert got['tiles'][0]['perf']['1D'] == old['tiles'][0]['perf']['1D']
    assert got['tiles'][0]['perf']['5M'] == 5.0
    json.dumps(got,allow_nan=False)
