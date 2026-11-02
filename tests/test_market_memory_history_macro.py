"""First-print chronology must not masquerade as a full as-of macro state."""
import hashlib
import importlib
import importlib.util
import json
import pytest

NAME='engine.neuralweb.market_memory_history_macro'

def module():
    assert importlib.util.find_spec(NAME) is not None,'first-print chronology composer is not implemented'
    return importlib.import_module(NAME)

def packet():
    rows=[{'series':'CPIAUCSL','period':'2020-01-01T00:00:00','value':258.687,
           'realtime_start':'2020-02-13T00:00:00','realtime_end':'2020-03-10T00:00:00'},
          {'series':'CPIAUCSL','period':'2020-02-01T00:00:00','value':258.824,
           'realtime_start':'2020-03-11T00:00:00','realtime_end':'2020-04-09T00:00:00'}]
    raw=(json.dumps(rows,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    return {'schema':'market_memory.macro_source_selection.v1','profile':'FRED_INITIAL_RELEASE_ONLY',
            'source':{'ref':'macro_snapshot:fred_vintage/vintages.parquet','file_version':'statv1:'+'a'*64,'evidence_kind':'unqualified_snapshot'},
            'query_receipts':['b'*64],'rows_sha256':hashlib.sha256(raw).hexdigest(),'rows':rows,
            'pit_backtest_eligible':False,'intraday_publication_time_known':False,'full_revision_history':False}

def resign(p):
    p['rows_sha256']=hashlib.sha256((json.dumps(p['rows'],sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()).hexdigest()
    return p

def test_macro_chronology_exists():
    assert callable(module().build_macro_chronology)

def test_exact_initial_print_date_not_economic_period_date():
    m=module(); result=m.build_macro_chronology(packet(),start='2020-01-01',end='2020-03-31')
    assert m.select_macro_date(result,'2020-01-01')['events']==[]
    selected=m.select_macro_date(result,'2020-02-13')
    assert selected['events'][0]['period']=='2020-01-01'
    assert selected['events'][0]['value']==258.687
    assert selected['date_basis']=='fred_realtime_start_date_only'
    assert selected['pit_backtest_eligible'] is False
    assert selected['full_revision_history'] is False
    assert selected['intraday_publication_time_known'] is False
    assert selected['units_retained'] is False

def test_source_hash_mismatch_refuses():
    p=packet();p['rows'][0]['value']=999
    with pytest.raises(ValueError,match='digest'):module().build_macro_chronology(p,start='2020-01-01',end='2020-03-31')

def test_revision_rows_cannot_be_passed_off_as_one_first_print():
    p=packet();p['rows'].append(dict(p['rows'][0],value=259.0,realtime_start='2020-02-14T00:00:00'));resign(p)
    with pytest.raises(ValueError,match='duplicate'):module().build_macro_chronology(p,start='2020-01-01',end='2020-03-31')

@pytest.mark.parametrize('key',['pit_backtest_eligible','intraday_publication_time_known','full_revision_history'])
def test_claim_upgrades_refuse(key):
    p=packet();p[key]=True
    with pytest.raises(ValueError):module().build_macro_chronology(p,start='2020-01-01',end='2020-03-31')

def test_does_not_manufacture_intraday_timestamp_or_surprise():
    c=module().build_macro_chronology(packet(),start='2020-01-01',end='2020-03-31')
    for e in c['events']:
        assert 'published_at' not in e and 'surprise' not in e and 'consensus' not in e
        assert e['source_units']=='NOT_RETAINED'

def test_non_midnight_clock_refuses_date_only_projection():
    p=packet();p['rows'][0]['realtime_start']='2020-02-13T08:30:00';resign(p)
    with pytest.raises(ValueError):module().build_macro_chronology(p,start='2020-01-01',end='2020-03-31')

def test_day_selection_is_bounded_and_reports_truncation():
    p=packet();p['rows']=[dict(p['rows'][0],series='S'+str(i)) for i in range(101)];resign(p)
    c=module().build_macro_chronology(p,start='2020-01-01',end='2020-03-31')
    selected=module().select_macro_date(c,'2020-02-13',limit=20)
    assert len(selected['events'])==20 and selected['total_events']==101 and selected['remaining_events']==81

def test_later_first_print_cannot_change_prior_event_selection():
    m=module();p=packet();a=m.build_macro_chronology(p,start='2020-01-01',end='2020-03-31')
    p['rows'][1]['value']=9999;resign(p);b=m.build_macro_chronology(p,start='2020-01-01',end='2020-03-31')
    assert m.select_macro_date(a,'2020-02-13')['events']==m.select_macro_date(b,'2020-02-13')['events']

def test_roundtrip_verified_chronology_and_tamper_refusal(tmp_path):
    m=module();c=m.build_macro_chronology(packet(),start='2020-01-01',end='2020-03-31')
    out=tmp_path/'macro.json';r=m.write_macro_chronology(c,out)
    assert m.read_macro_chronology(out,expected_sha256=r['sha256'])==c
    with pytest.raises(FileExistsError):m.write_macro_chronology(c,out)
    out.write_text('{}')
    with pytest.raises(ValueError):m.read_macro_chronology(out,expected_sha256=r['sha256'])


def test_daily_projection_withholds_revision_end_metadata_without_mutating_evidence():
    m = module()
    original = m.build_macro_chronology(packet(), start='2020-01-01', end='2020-03-31')
    before = json.dumps(original, sort_keys=True)
    changed = packet()
    changed['rows'][0]['realtime_end'] = '2021-12-31T00:00:00'
    later = m.build_macro_chronology(resign(changed), start='2020-01-01', end='2020-03-31')
    a = m.select_macro_date(original, '2020-02-13')
    b = m.select_macro_date(later, '2020-02-13')
    assert all('first_vintage_valid_through' not in row for row in a['events'])
    assert a['events'] == b['events']
    assert a['revision_end_metadata'] == 'withheld_from_daily_projection'
    assert original['events'][0]['first_vintage_valid_through'] == '2020-03-10'
    assert json.dumps(original, sort_keys=True) == before


def test_macro_projection_distinguishes_archive_window_from_empty_date():
    m = module()
    chronology = m.build_macro_chronology(packet(), start='2020-01-01', end='2020-03-31')
    inside = m.select_macro_date(chronology, '2020-01-05')
    outside = m.select_macro_date(chronology, '2019-12-31')
    assert inside['events'] == outside['events'] == []
    assert inside['within_declared_archive_window'] is True
    assert outside['within_declared_archive_window'] is False
    assert inside['declared_archive_window'] == {'start': '2020-01-01', 'end': '2020-03-31'}
    assert inside['calendar_completeness_proven'] is False


@pytest.mark.parametrize('key', ['start', 'end'])
def test_missing_macro_window_field_is_a_typed_refusal(key):
    m = module()
    chronology = m.build_macro_chronology(packet(), start='2020-01-01', end='2020-03-31')
    del chronology[key]
    unsigned = {k: v for k, v in chronology.items() if k != 'chronology_id'}
    chronology['chronology_id'] = 'mmfirst_' + hashlib.sha256(m._bytes(unsigned)).hexdigest()
    with pytest.raises(m.HistoricalExperienceError):
        m.select_macro_date(chronology, '2020-02-13')
