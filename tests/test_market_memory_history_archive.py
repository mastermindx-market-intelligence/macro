"""Archive composes existing Data OS evidence; never upgrades its admission."""
from datetime import date, timedelta
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

NAME = 'engine.neuralweb.market_memory_history_archive'

def module():
    assert importlib.util.find_spec(NAME) is not None, 'evidence-bound history archive is not implemented'
    return importlib.import_module(NAME)

def request():
    return {'schema':'market_memory.history_inputs.v1','mode':'RETROSPECTIVE_EXPLORATORY',
            'basis':'tradj','benchmark':'SPY','start':'2020-01-01','end':'2020-01-12',
            'warmup_start':'2019-01-01','capture_cutoff':'2026-10-15T00:00:00Z',
            'acknowledge_hindsight':True,'symbols':[{'vendor_symbol':'SPY','refs':[['2026-10-13','a'*64]]}],
            'selection':'Explicit test proxy universe, not point-in-time membership.'}

def fake_reader(*args, **kwargs):
    rows=tuple({'market_date':(date(2020,1,1)+timedelta(days=i)).isoformat(),
                'close_raw':100+i,'close_tradj':50+i/2,'volume_raw':1000} for i in range(10))
    return SimpleNamespace(rows=rows,source_partitions=(('2026-10-13','a'*64),),
        metadata=lambda:{'source':'eod-bars','vendor_symbol':'SPY','pit_backtest_eligible':False,
                         'redistribution_admitted':False,'historical_identity_admitted':False,
                         'market_session_completeness_proven':False})

def test_history_archive_exists():
    assert callable(module().assemble_history)

@pytest.mark.parametrize('field,value',[
    ('mode','RECONSTRUCT'),('mode','REPLAY'),('acknowledge_hindsight',False),
    ('basis','close'),('capture_cutoff','2026-10-15'),('warmup_start','2021-01-01')])
def test_ineligible_requests_refuse_before_source_read(monkeypatch,field,value):
    m=module(); r=request(); r[field]=value
    monkeypatch.setattr(m,'read_research_history',lambda *a,**k: pytest.fail('source read before validation'))
    with pytest.raises(ValueError): m.assemble_history(r)

def test_duplicate_symbols_and_refs_refuse(monkeypatch):
    m=module(); monkeypatch.setattr(m,'read_research_history',lambda *a,**k: pytest.fail('unexpected read'))
    for r in [request(),request()]:
        if len(r['symbols'])==1 and not r['symbols'][0].get('duplicate'):
            r['symbols'].append(dict(r['symbols'][0]))
        with pytest.raises(ValueError): m.assemble_history(r)
    r=request(); r['symbols'][0]['refs']*=2
    with pytest.raises(ValueError): m.assemble_history(r)

def test_calls_existing_reader_with_explicit_capture_and_hindsight(monkeypatch):
    m=module(); calls=[]
    def reader(*args,**kwargs): calls.append((args,kwargs)); return fake_reader(*args,**kwargs)
    monkeypatch.setattr(m,'read_research_history',reader)
    packet=m.assemble_history(request())
    assert calls[0][0][:2]==('eod-bars','SPY')
    assert calls[0][1]['acknowledge_hindsight'] is True
    assert packet['manifest']['pit_backtest_eligible'] is False
    assert packet['manifest']['redistribution_admitted'] is False
    assert packet['manifest']['scope']=='explicit_vendor_proxy_panel'
    assert packet['manifest']['coverage']['last_observed_date']=='2020-01-10'
    assert packet['manifest']['coverage']['requested_end_after_last_observation'] is True
    assert len(packet['states'])==10
    assert 'outcomes' not in packet['states'][0]

def test_source_refusal_is_not_replaced_by_unqualified_parquet(monkeypatch):
    m=module()
    def deny(*a,**k): raise ValueError('conflicting vendor revisions')
    monkeypatch.setattr(m,'read_research_history',deny)
    with pytest.raises(ValueError,match='conflicting vendor revisions'): m.assemble_history(request())

def make_archive(monkeypatch,tmp_path):
    m=module(); monkeypatch.setattr(m,'read_research_history',fake_reader)
    packet=m.assemble_history(request()); destination=tmp_path/'history'
    result=m.write_archive(packet,destination)
    return m,destination,result

def test_source_to_archive_to_exact_date(monkeypatch,tmp_path):
    m,root,receipt=make_archive(monkeypatch,tmp_path)
    assert receipt['manifest_sha256']==hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()
    actual=m.read_day(root,'2020-01-05',expected_manifest_sha256=receipt['manifest_sha256'])
    assert actual['rows'][0]['close_tradj']==52.0
    assert 'outcomes' not in actual
    assert actual['mode']=='RETROSPECTIVE_EXPLORATORY'
    absent=m.read_day(root,'2020-01-12',expected_manifest_sha256=receipt['manifest_sha256'])
    assert absent['status']=='NO_OBSERVATION' and absent['rows']==[]

def test_default_state_read_does_not_read_outcomes(monkeypatch,tmp_path):
    m,root,receipt=make_archive(monkeypatch,tmp_path)
    manifest=json.loads((root/'manifest.json').read_text())
    outcomes=next(x for x in manifest['files'] if x['kind']=='outcomes')
    (root/outcomes['name']).unlink()
    assert m.read_day(root,'2020-01-05',expected_manifest_sha256=receipt['manifest_sha256'])['rows']
    with pytest.raises(ValueError):
        m.read_day(root,'2020-01-05',expected_manifest_sha256=receipt['manifest_sha256'],reveal_outcomes=True)

def test_corruption_and_manifest_mismatch_refuse(monkeypatch,tmp_path):
    m,root,receipt=make_archive(monkeypatch,tmp_path)
    with pytest.raises(ValueError): m.read_day(root,'2020-01-05',expected_manifest_sha256='f'*64)
    manifest=json.loads((root/'manifest.json').read_text())
    state=next(x for x in manifest['files'] if x['kind']=='states')
    (root/state['name']).write_bytes(b'corruption')
    with pytest.raises(ValueError): m.read_day(root,'2020-01-05',expected_manifest_sha256=receipt['manifest_sha256'])

def test_no_clobber_and_reproducible_artifact_identity(monkeypatch,tmp_path):
    m,root,receipt=make_archive(monkeypatch,tmp_path)
    packet=m.assemble_history(request())
    assert packet['manifest']['artifact_id']==receipt['artifact_id']
    with pytest.raises(FileExistsError): m.write_archive(packet,root)

def test_rejects_unknown_request_fields(monkeypatch):
    m=module(); r=request(); r['pit_backtest_eligible']=True
    with pytest.raises(ValueError): m.assemble_history(r)

def test_outcome_reveal_is_explicit_and_bound(monkeypatch,tmp_path):
    m,root,receipt=make_archive(monkeypatch,tmp_path)
    got=m.read_day(root,'2020-01-01',expected_manifest_sha256=receipt['manifest_sha256'],reveal_outcomes=True)
    assert got['outcomes'][0]['forward_return_5ob_pct']==pytest.approx(5)

@pytest.mark.parametrize('change',[{'basis':'raw'},{'historical_identity_admitted':True},{'coverage':{'observed_dates':999999}}])
def test_manifest_metadata_cannot_change_without_new_semantic_identity(monkeypatch,tmp_path,change):
    m=module();monkeypatch.setattr(m,'read_research_history',fake_reader)
    p=m.assemble_history(request());p['manifest'].update(change)
    destination=tmp_path/'tampered'
    with pytest.raises(ValueError):m.write_archive(p,destination)
    assert not destination.exists()

def test_parquet_preserves_raw_share_volume_integer_schema(monkeypatch,tmp_path):
    import pyarrow.parquet as pq
    m,root,r=make_archive(monkeypatch,tmp_path)
    schema=pq.read_schema(next(root.glob('states-*.parquet')))
    assert str(schema.field('volume_raw').type)=='int64'

def test_preexisting_v1_archives_remain_readable_with_their_original_identity(monkeypatch,tmp_path):
    m,root,r=make_archive(monkeypatch,tmp_path)
    manifest=json.loads((root/'manifest.json').read_text())
    manifest['schema']='market_memory.history_archive.v1'
    identity={k:manifest[k] for k in ['request','sources','feature_version','source_code_sha256','states_sha256','outcomes_sha256']}
    manifest['artifact_id']='mmhist_'+hashlib.sha256(m._bytes(identity)).hexdigest()
    raw=m._bytes(manifest);(root/'manifest.json').write_bytes(raw)
    result=m.read_day(root,'2020-01-05',expected_manifest_sha256=hashlib.sha256(raw).hexdigest())
    assert result['rows'][0]['close_tradj']==52.0


def test_changed_v2_metadata_cannot_be_read_under_old_semantic_identity(monkeypatch,tmp_path):
    m,root,r=make_archive(monkeypatch,tmp_path)
    manifest=json.loads((root/'manifest.json').read_text())
    assert manifest['schema']=='market_memory.history_archive.v2'
    manifest['coverage']['observed_dates']=99999
    raw=m._bytes(manifest);(root/'manifest.json').write_bytes(raw)
    with pytest.raises(ValueError,match='identity'):
        m.read_day(root,'2020-01-05',expected_manifest_sha256=hashlib.sha256(raw).hexdigest())


def test_single_date_reader_never_starts_an_async_dataset_scan(monkeypatch,tmp_path):
    import pyarrow.parquet as pq
    m,root,r=make_archive(monkeypatch,tmp_path)
    def forbidden(*a,**k):pytest.fail('async dataset scan can deadlock Python finalization')
    monkeypatch.setattr(pq,'read_table',forbidden)
    result=m.read_day(root,'2020-01-05',expected_manifest_sha256=r['manifest_sha256'])
    assert len(result['rows'])==1


def test_date_reader_refuses_decoded_year_over_64mib_before_materializing(monkeypatch,tmp_path):
    from types import SimpleNamespace
    import pyarrow.parquet as pq
    m,root,r=make_archive(monkeypatch,tmp_path)
    record=next(f for f in json.loads((root/'manifest.json').read_text())['files'] if f['kind']=='states')
    calls=[]
    class OversizedMetadata:
        metadata=SimpleNamespace(num_rows=record['rows'],num_row_groups=1,
            row_group=lambda i:SimpleNamespace(total_byte_size=64*1024*1024+1))
        def read(self,**kwargs):
            pytest.fail('decode budget must be checked before table materialization')
        def close(self):calls.append('closed')
    monkeypatch.setattr(pq,'ParquetFile',lambda *a,**k:OversizedMetadata())
    with pytest.raises(ValueError,match='decoded size'):
        m.read_day(root,'2020-01-05',expected_manifest_sha256=r['manifest_sha256'])
    assert calls==['closed']


def test_malformed_source_date_is_refused_before_coverage(monkeypatch):
    m=module()
    def reader(*a,**k):
        h=fake_reader(); h.rows=({'close_tradj':50.0,'volume_raw':1},); return h
    monkeypatch.setattr(m,'read_research_history',reader)
    with pytest.raises(ValueError,match='date'):
        m.assemble_history(request())


def test_empty_source_keeps_declared_denominator_without_inventing_price(monkeypatch):
    m=module()
    def reader(*a,**k):h=fake_reader();h.rows=();return h
    monkeypatch.setattr(m,'read_research_history',reader)
    result=m.assemble_history(request())
    assert result['states']==[]
    assert result['manifest']['coverage']['selected_proxy_count']==1
    assert result['manifest']['coverage']['by_symbol']['SPY']['observations']==0


def test_capture_cutoff_is_normalized_to_utc_by_existing_temporal_owner():
    m=module()
    assert m.utc('2024-01-15T23:59:59-05:00').isoformat()=='2024-01-16T04:59:59+00:00'


# Independent integration-review reproducers: do not weaken the retained archive.
def test_day_reader_discloses_stored_calculation_vintage(monkeypatch, tmp_path):
    m, root, receipt = make_archive(monkeypatch, tmp_path)
    manifest = json.loads((root / 'manifest.json').read_text())
    manifest['feature_version'] = 'retained-older-features.v0'
    manifest['artifact_id'] = m._semantic_identity(manifest)
    raw = m._bytes(manifest)
    (root / 'manifest.json').write_bytes(raw)
    result = m.read_day(root, '2020-01-05', expected_manifest_sha256=m._hash(raw))
    assert result['feature_version'] == 'retained-older-features.v0'
    assert result['feature_version_matches_reader'] is False
    assert result['source_code_sha256'] == manifest['source_code_sha256']
    assert result['rows'][0]['close_tradj'] == 52.0


@pytest.mark.parametrize('missing', ['sources', 'feature_version', 'source_code_sha256',
                                     'state_schema', 'states_sha256', 'outcomes_sha256'])
def test_missing_read_contract_fields_refuse_typed(monkeypatch, tmp_path, missing):
    m, root, receipt = make_archive(monkeypatch, tmp_path)
    manifest = json.loads((root / 'manifest.json').read_text())
    del manifest[missing]
    manifest['artifact_id'] = m._semantic_identity(manifest)
    raw = m._bytes(manifest)
    (root / 'manifest.json').write_bytes(raw)
    with pytest.raises(m.HistoricalExperienceError):
        m.read_day(root, '2020-01-05', expected_manifest_sha256=m._hash(raw))


def test_exhausted_build_budget_refuses_before_another_source_read(monkeypatch):
    m = module()
    r = request()
    r['symbols'].append({'vendor_symbol': 'OTHER', 'refs': [['2026-10-13', 'b' * 64]]})
    calls = []
    def reader(*args, **kwargs):
        calls.append(kwargs['max_rows'])
        if len(calls) > 1:
            pytest.fail('exhausted budget must refuse before another source read')
        return fake_reader(*args, **kwargs)
    monkeypatch.setattr(m, 'MAX_TOTAL_ROWS', 10)
    monkeypatch.setattr(m, 'read_research_history', reader)
    with pytest.raises(m.HistoricalExperienceError, match='total row budget'):
        m.assemble_history(r)
    assert calls == [10]
