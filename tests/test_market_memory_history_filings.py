"""Historical filing metadata cannot become inferred price or earnings evidence."""
import hashlib
import importlib
import io
from pathlib import Path
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from engine.neuralweb.market_memory_history import HistoricalExperienceError


def module():
    assert importlib.util.find_spec('engine.neuralweb.market_memory_history_filings'), 'filing context projection missing'
    return importlib.import_module('engine.neuralweb.market_memory_history_filings')


def row(**changes):
    value={'ticker':'SOURCE_LABEL','cik':320193,'accession':'0000320193-20-000001','form':'8-K',
        'filing_date':'2020-03-16','acceptance_datetime':'2020-03-16T20:28:05.000Z',
        'report_date':'2020-03-12','items':'2.02,9.01'}
    return {**value,**changes}


def payload(rows=None):
    sink=pa.BufferOutputStream();pq.write_table(pa.Table.from_pylist(rows if rows is not None else [row()]),sink,compression='zstd')
    return sink.getvalue().to_pybytes()


def read(raw=None,day='2020-03-16',**kwargs):
    raw=payload() if raw is None else raw
    return module().read_filing_date(raw,day,expected_sha256=hashlib.sha256(raw).hexdigest(),**kwargs)


def test_exact_filing_date_not_report_date_and_no_forecast_or_cause():
    result=read()
    assert result['events'][0]['filing_key']=='0000320193:0000320193-20-000001'
    assert result['events'][0]['report_date']=='2020-03-12'
    assert result['events'][0]['ticker_source_label']=='SOURCE_LABEL'
    assert result['events'][0]['acceptance_datetime_source']=='2020-03-16T20:28:05.000Z'
    assert result['events'][0]['acceptance_datetime_utc']=='2020-03-16T20:28:05+00:00'
    assert result['historical_ticker_identity_proven'] is False
    assert result['intraday_publication_time_verified'] is False
    assert result['point_in_time_eligible'] is False
    assert not {'eps','consensus','surprise','cause'}&set(result['events'][0])
    assert read(day='2020-03-12')['events']==[]


def test_amendment_is_distinct_not_collapsed():
    raw=payload([row(),row(accession='0000320193-20-000002',form='8-K/A')])
    result=read(raw);assert result['total_events']==2
    assert len({r['filing_key'] for r in result['events']})==2


def test_duplicate_filing_key_refuses():
    with pytest.raises(HistoricalExperienceError):read(payload([row(),row(ticker='DIFFERENT_ALIAS')]))


@pytest.mark.parametrize('change',[
    {'items':'12.02,9.01'},{'items':'2.020'},{'cik':True},
    {'accession':'unknown'},{'form':'10-K'},{'filing_date':'2020-3-16'},
    {'acceptance_datetime':'not-a-date'},{'acceptance_datetime':'2020-03-16T10:30:00'},
    {'ticker':'bad\nlabel'},{'items':'2.02,'+'x'*10000},
])
def test_bad_source_row_refuses(change):
    with pytest.raises(HistoricalExperienceError):read(payload([row(**change)]))


def test_missing_acceptance_and_report_date_stay_unknown():
    result=read(payload([row(acceptance_datetime='',report_date='')]))
    assert result['events'][0]['acceptance_datetime_utc'] is None
    assert result['events'][0]['report_date'] is None
    assert result['missing_acceptance_count']==1


def test_source_digest_mismatch_and_extra_field_refuse():
    raw=payload()
    with pytest.raises(HistoricalExperienceError):module().read_filing_date(raw,'2020-03-16',expected_sha256='0'*64)
    with pytest.raises(HistoricalExperienceError):read(payload([row(eps_forecast=99)]))


def test_exact_date_pagination_is_distinct_from_source_row_positions():
    rows=[row(accession=f'0000320193-20-{i:06}') for i in range(102)]
    raw=payload(list(reversed(rows)))
    first=read(raw);second=read(raw,offset=50);last=read(raw,offset=100)
    assert [len(x['events']) for x in (first,second,last)]==[50,50,2]
    assert [x['next_offset'] for x in (first,second,last)]==[50,100,None]
    assert all(x['total_events']==102 for x in (first,second,last))
    assert len({r['filing_key'] for x in (first,second,last) for r in x['events']})==102


def test_unobserved_date_does_not_claim_no_market_events():
    result=read(day='1999-01-01')
    assert result['status']=='NO_RETAINED_FILING'
    assert result['within_observed_source_range'] is False
    assert result['source_date_range']=={'first':'2020-03-16','last':'2020-03-16'}
    assert result['calendar_completeness_proven'] is False


def test_budget_refusals_precede_decode(monkeypatch):
    m=module();raw=payload()
    monkeypatch.setattr(m,'MAX_SOURCE_BYTES',1)
    monkeypatch.setattr(pq,'ParquetFile',lambda *a,**k:pytest.fail('decoded after source byte refusal'))
    with pytest.raises(HistoricalExperienceError):read(raw)


def test_declared_decode_budget_refuses_before_table_materialization(monkeypatch):
    m=module();monkeypatch.setattr(m,'MAX_DECODED_BYTES',1)
    with pytest.raises(HistoricalExperienceError,match='decoded'):read()


# An ordinary dictionary-encoded file, not a forged footer, can have a much
# larger logical Arrow result than its declared Parquet page bytes.
def test_logical_decoded_budget_is_enforced_not_only_footer(monkeypatch):
    m = module()
    raw = payload([row(accession=f'0000320193-20-{i:06}') for i in range(2000)])
    with pq.ParquetFile(pa.BufferReader(raw), pre_buffer=False) as pf:
        declared = sum(pf.metadata.row_group(i).total_byte_size for i in range(pf.metadata.num_row_groups))
        logical = pf.read(use_threads=False).nbytes
    assert logical > declared + 1024, (declared, logical)
    monkeypatch.setattr(m, 'MAX_DECODED_BYTES', declared + 1)
    with pytest.raises(HistoricalExperienceError, match='logical decoded'):
        read(raw)


def test_filing_scan_never_materializes_the_whole_source_table(monkeypatch):
    original = pq.ParquetFile
    observed = []
    class BoundedFile:
        def __init__(self, *args, **kwargs): self.inner = original(*args, **kwargs)
        def __getattr__(self, name): return getattr(self.inner, name)
        def read(self, *args, **kwargs): pytest.fail('whole-source table materialized')
        def iter_batches(self, *args, **kwargs):
            assert kwargs['batch_size'] <= 2048 and kwargs['use_threads'] is False
            for batch in self.inner.iter_batches(*args, **kwargs):
                observed.append(batch.num_rows)
                yield batch
    monkeypatch.setattr(pq, 'ParquetFile', BoundedFile)
    raw = payload([row(accession=f'0000320193-20-{i:06}') for i in range(3000)])
    result = read(raw)
    assert result['total_events'] == 3000 and len(result['events']) == 50
    assert sum(observed) == 3000 and max(observed) <= 2048



def test_timeline_uses_the_same_validator_and_keeps_named_columns():
    raw = payload([row(accession='0000320193-20-000002'), row()])
    m = module()
    timeline = m.read_filing_timeline(raw, expected_sha256=hashlib.sha256(raw).hexdigest())
    assert timeline['mode'] == 'RETROSPECTIVE_EXPLORATORY'
    events = [dict(zip(timeline['columns'], values)) for values in timeline['rows']]
    assert [e['filing_key'] for e in events] == sorted(e['filing_key'] for e in events)
    assert events[0]['filing_date'] == '2020-03-16'
    assert timeline['metadata']['source_rows'] == 2
    assert timeline['metadata']['point_in_time_eligible'] is False
    assert timeline['metadata']['source_sha256'] == hashlib.sha256(raw).hexdigest()
    assert not any(c.startswith(('forward_', 'outcome')) for c in timeline['columns'])
    with pytest.raises(HistoricalExperienceError):
        invalid = payload([row(), row()])
        m.read_filing_timeline(invalid, expected_sha256=hashlib.sha256(invalid).hexdigest())
