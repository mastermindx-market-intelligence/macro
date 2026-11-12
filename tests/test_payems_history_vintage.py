"""Synthetic, source-version-bounded PAYEMS vintage reconstruction tests.

This is a research projection, not data acquisition, a historical macro release
clock, production alert or trading admission. A real source evidence gate remains.
"""
import pandas as pd
import pytest

from engine.neuralweb import market_memory_history_payems_vintage as subject
from engine.neuralweb.market_memory_history import HistoricalExperienceError

SOURCE = dict(
    source_ref='macro_snapshot:fred_vintage/payems_all_vintages.parquet',
    source_version='statv1:'+'a'*64, source_sha256='b'*64,
)


def rows():
    return pd.DataFrame([
        ('2019-12-01','2020-01-10','2020-02-06',151000.0),
        ('2020-01-01','2020-02-07','2020-03-05',152000.0),
        ('2020-02-01','2020-03-06','2020-04-02',152544.0),
        ('2020-02-01','2020-04-03','2026-01-01',152400.0),
        ('2020-02-01','2026-07-02',None,152293.0),
        ('2020-01-01','2020-03-06',None,151900.0),
        ('2020-03-01','2020-04-03',None,151500.0),
    ], columns=['period','realtime_start','realtime_end','value'])


def query(df=None, day='2020-03-16', **kwargs):
    return subject.select_payems_date(rows() if df is None else df, day, **SOURCE, **kwargs)


def test_previous_as_of_never_discloses_later_revision_or_its_end():
    value=query()
    assert value['status']=='OBSERVED'
    assert (value['latest_period'], value['latest_value'], value['latest_vintage_start']) == (
        '2020-02-01',152544.0,'2020-03-06')
    assert value['available_periods']==3
    assert 'realtime_end' not in str(value) and '2026-07-02' not in str(value)
    assert value['intraday_publication_time_verified'] is False
    assert value['point_in_time_trading_eligible'] is False
    assert value['source_sha256_verified_by_projection'] is False


def test_after_new_revision_can_show_then_available_value():
    value=query(day='2020-04-08')
    feb=next(x for x in value['periods'] if x['period']=='2020-02-01')
    assert (feb['value'],feb['realtime_start'])==(152400.0,'2020-04-03')
    assert (value['latest_period'],value['latest_value'])==('2020-03-01',151500.0)
    assert '152293' not in str(value)


def test_future_prefix_extension_invariance():
    before=query()
    newer=rows()
    newer.loc[len(newer)]=('2020-02-01','2026-09-01',None,999999.0)
    assert query(newer)==before


def test_no_pre1997_vintage_is_invented():
    value=query(day='1990-10-01')
    assert value['status']=='NO_RETAINED_VINTAGE_AT_CUTOFF'
    assert value['latest_period'] is None and value['periods']==[]


def test_staleness_is_separate_from_historical_available_value():
    value=query(day='2026-10-16')
    assert value['source_last_recorded_vintage']=='2026-07-02'
    assert value['source_recorded_through_cutoff'] is True
    assert value['source_current_to_selected_date_proven'] is False


def test_newer_null_does_not_backfill_original_value():
    df=rows();df.loc[len(df)]=('2020-03-01','2020-04-07',None,float('nan'))
    value=query(df,day='2020-04-08')
    assert value['latest_value'] is None and value['periods'][0]['value'] is None


def test_duplicate_period_vintage_even_with_identical_value_refuses():
    df=rows();df.loc[len(df)]=df.iloc[2]
    with pytest.raises(HistoricalExperienceError):query(df)


def test_future_period_not_published_in_advance():
    df=rows();df.loc[len(df)]=('2020-03-01','2020-01-01',None,10.)
    with pytest.raises(HistoricalExperienceError):query(df)


@pytest.mark.parametrize('cutoff',['2020-3-16','2020-03-16T15:30:00Z','garbage','2020-02-30',None])
def test_date_only_no_inferred_intraday(cutoff):
    with pytest.raises(HistoricalExperienceError):query(day=cutoff)


@pytest.mark.parametrize('field,bad',[
    ('source_ref','macro_snapshot:fred_vintage/vintages.parquet'),
    ('source_version','wrong'),('source_sha256','z'*64),
])
def test_exact_owner_and_declared_digest_contract(field,bad):
    values=dict(SOURCE);values[field]=bad
    with pytest.raises(HistoricalExperienceError):
        subject.select_payems_date(rows(),'2020-03-16',**values)


def test_input_row_budget_refuses():
    with pytest.raises(HistoricalExperienceError):query(max_rows=3)


def test_latest_observation_order_and_period_limit():
    value=query(max_periods=2)
    assert [x['period'] for x in value['periods']]==['2020-02-01','2020-01-01']


def test_empty_retained_source_preserves_gap():
    assert query(rows().iloc[:0])['status']=='NO_RETAINED_VINTAGE_AT_CUTOFF'


def test_nonfinite_value_is_rejected():
    df=rows();df.loc[0,'value']=float('inf')
    with pytest.raises(HistoricalExperienceError):query(df)


def test_original_source_table_never_mutated():
    df=rows();original=df.copy(deep=True);query(df)
    pd.testing.assert_frame_equal(df,original)


def test_open_ended_9999_year_sentinel_is_not_a_missing_record():
    df=rows();df.loc[4,'realtime_end']='9999-12-31 00:00:00'
    assert query(df,day='2026-10-16')['latest_period']=='2020-03-01'


def test_unparsable_revision_end_is_a_refusal():
    df=rows();df.loc[0,'realtime_end']='bogus'
    with pytest.raises(HistoricalExperienceError):query(df)


def test_reversed_recorded_revision_interval_refuses():
    df=rows();df.loc[2,'realtime_end']='2020-02-01'
    with pytest.raises(HistoricalExperienceError,match='reversed'):
        query(df)


def test_duplicate_column_label_refuses():
    df=rows();df.insert(1,'value_copy',df['value'])
    df.columns=['period','value','realtime_start','realtime_end','value']
    with pytest.raises(HistoricalExperienceError):query(df)


def test_future_vendor_adjustment_does_not_change_earlier_report():
    df=rows();before=query(df)
    df.loc[df['realtime_start']=='2026-07-02','value']=999999.0
    assert query(df)==before


def test_nonfinite_last_released_value_refuses():
    df=rows();df.loc[df['realtime_start']=='2020-03-06','value']=float('inf')
    with pytest.raises(HistoricalExperienceError):query(df)


def test_vintage_date_is_not_claimed_as_tradable_release_time():
    value=query(day='2020-03-06')
    assert value['vintage_records_on_selected_date']==2
    assert value['intraday_publication_time_verified'] is False


def test_negative_value_stays_data_not_trading_signal():
    df=rows();df.loc[2,'value']=-10.0
    assert query(df)['latest_value']==-10.0
    assert query(df)['point_in_time_trading_eligible'] is False


def test_invalid_period_count_refuses():
    with pytest.raises(HistoricalExperienceError):query(max_periods=25)


def test_unsorted_source_rows_produce_same_date_view():
    assert query(rows().sample(frac=1,random_state=23))==query(rows())
