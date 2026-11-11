"""Existing Data & Lab source-owner integration for PAYEMS historical vintages.

All tests use a synthetic Parquet source under an explicitly bound temporary
root; they never touch a provider, an installed selector or an actual archive.
"""
from contextlib import contextmanager
from datetime import datetime
import hashlib
from pathlib import Path

import pytest

pa = pytest.importorskip('pyarrow')
pq = pytest.importorskip('pyarrow.parquet')

from lib.dataos.web_api import dispatch
from lib.dataos.web_workspace import DataWorkspace, RootBinding, WorkspaceError
from tests.test_dataos_web_history import case

PAYEMS = 'macro_snapshot:fred_vintage/payems_all_vintages.parquet'


@pytest.fixture
def bound(case):
    folder=case.base/'fred_vintage'
    folder.mkdir()
    target=folder/'payems_all_vintages.parquet'
    rows=[
        ('2019-12-01','2020-01-10','2020-02-06',151000.0),
        ('2020-01-01','2020-02-07','2020-03-05',152000.0),
        ('2020-02-01','2020-03-06','2020-04-02',152544.0),
        ('2020-02-01','2020-04-03','2026-01-01',152400.0),
        ('2020-02-01','2026-07-02','9999-12-31',152293.0),
    ]
    def dates(col):
        return pa.array([datetime.fromisoformat(item[col]) for item in rows],type=pa.timestamp('us'))
    table=pa.table({
        'period':dates(0),
        'realtime_start':dates(1),
        'realtime_end':dates(2),
        'value':pa.array([row[3] for row in rows],type=pa.float64()),
    })
    pq.write_table(table,target,compression='zstd')
    ws=DataWorkspace((
        RootBinding('fixture',case.base,'research_capture'),
        RootBinding('macro_snapshot',case.base,'unqualified_snapshot'),
    ),case.base/'registry.yml',source_revision='a'*40)
    with ws._file(PAYEMS) as (stream, source):
        observed_version=source['file_version']
    return case,ws,target,observed_version,hashlib.sha256(target.read_bytes()).hexdigest()


def query(bound, date='2020-03-16', **changes):
    case,ws,target,version,digest=bound
    r={'action':'history_dossier',
       'ref':'fixture:history/manifest.json',
       'manifest_sha256':case.receipt['manifest_sha256'],
       'date':date,
       'payems_ref':PAYEMS,'payems_version':version,'payems_sha256':digest}
    r.update(changes)
    return dispatch(ws,r,config_path=case.config)


def test_exact_owner_version_and_digest_return_historical_value(bound):
    result=query(bound)
    assert result['action']=='history_dossier'
    assert result['result']['payems_vintage']['latest_value']==152544.0
    assert result['result']['payems_vintage']['latest_vintage_start']=='2020-03-06'
    assert result['result']['payems_vintage']['source_sha256_verified_by_projection'] is True
    assert result['result']['payems_vintage']['intraday_publication_time_verified'] is False
    assert 'realtime_end' not in str(result['result']['payems_vintage'])
    assert result['result']['coverage']['full_macro_revision_history']=='NOT_INCLUDED'
    assert result['result']['coverage']['payems_recorded_vintages']=='SELECTED_RECORDED_DATE_ONLY_NOT_INTRADAY'
    assert not result['result']['outcomes_revealed']
    assert any(f['ref']==PAYEMS and f['content_sha256']==bound[4]
               for f in result['source_files'])


def test_later_revision_not_backfilled_on_earlier_day(bound):
    before=query(bound,date='2020-03-16')['result']['payems_vintage']
    after=query(bound,date='2020-04-08')['result']['payems_vintage']
    assert before['latest_value']==152544.0
    # The latest observed economic period remains February 2020, but its
    # selected vintage changed only after its recorded April revision.
    assert after['latest_value']==152400.0
    assert after['latest_vintage_start']=='2020-04-03'


def test_no_precoverage_vintage_is_fabricated(bound):
    result=query(bound,date='1990-10-01')['result']
    assert result['payems_vintage']['status']=='NO_RETAINED_VINTAGE_AT_CUTOFF'
    assert result['payems_vintage']['latest_value'] is None


def test_missing_price_date_can_still_include_macro_vintage(bound):
    result=query(bound,date='2020-03-16')['result']
    assert result['market']['status']=='NO_OBSERVATION'
    assert result['payems_vintage']['status']=='OBSERVED'


@pytest.mark.parametrize('changes',[
    {'payems_ref':'fixture:history/outcomes-2020.parquet'},
    {'payems_version':'wrong'},
    {'payems_sha256':'0'*64},
    {'payems_version':None},
    {'payems_sha256':None},
    {'payems_max_periods':0},
    {'payems_max_periods':25},
    {'payems_max_periods':True},
    {'payems_ref':None},
    {'payems_version':'statv1:'+'0'*64},
])
def test_bad_source_or_binding_is_refused(bound,changes):
    with pytest.raises(WorkspaceError):
        query(bound,**changes)


def test_irrelevant_executable_fields_remain_forbidden(bound):
    with pytest.raises(WorkspaceError,match='INVALID_REQUEST_FIELDS'):
        query(bound, output_path='/tmp/nonexistent')


def test_no_payems_binding_preserves_old_response_and_no_extra_source(bound):
    case,ws,target,version,digest=bound
    r={'action':'history_dossier','ref':'fixture:history/manifest.json',
       'manifest_sha256':case.receipt['manifest_sha256'],'date':'2020-03-16'}
    result=dispatch(ws,r,config_path=case.config)
    assert 'payems_vintage' not in result['result']
    assert 'payems_recorded_vintages' not in result['result']['coverage']
    assert all(s['ref']!=PAYEMS for s in result['source_files'])


def test_capability_is_limited_to_existing_source_owner(bound):
    case,ws,*_=bound
    caps=dispatch(ws,{'action':'capabilities'},config_path=case.config)
    fields=caps['history']['payems_vintages']
    assert fields['required_source_ref']==PAYEMS
    assert fields['point_in_time_trading_eligible'] is False
    assert 'history_dossier' in caps['actions']


def test_mutated_source_version_refused_before_return(bound):
    case,ws,target,version,digest=bound
    original=ws._file
    @contextmanager
    def changed(ref,*args,**kwargs):
        with original(ref,*args,**kwargs) as opened:
            yield opened
            if ref==PAYEMS:
                # A source owner must refuse a changed path while the request
                # is still open, even if the supplied byte digest was correct.
                target.touch()
    ws._file=changed
    with pytest.raises(WorkspaceError):
        query(bound)


def test_content_mismatch_refuses_before_return(bound):
    case,ws,target,version,digest=bound
    with pytest.raises(WorkspaceError):
        query(bound,payems_sha256='f'*64)


def test_derived_byte_budget_is_disclosed_not_peak_ram_claim(bound):
    result=query(bound)['result']['payems_vintage']
    assert result['source_encoded_bytes']==bound[2].stat().st_size
    assert result['source_actual_arrow_bytes']<=64*1024*1024
    assert result['source_current_to_selected_date_proven'] is False
