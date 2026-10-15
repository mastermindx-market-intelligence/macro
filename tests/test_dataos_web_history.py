"""Existing Data & Lab transport keeps its descriptor-confined source access."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import pytest
from lib.dataos.web_workspace import DataWorkspace,RootBinding,WorkspaceError
from lib.dataos.web_api import dispatch
from tests.test_market_memory_history_archive import make_archive
from tests.test_market_memory_history_dossier import macro

@pytest.fixture
def case(monkeypatch,tmp_path):
    ar,root,r=make_archive(monkeypatch,tmp_path)
    registry=tmp_path/'registry.yml';registry.write_text('schema: dataset_registry.v1\ndatasets: []\n')
    ws=DataWorkspace((RootBinding('fixture',tmp_path,'research_capture'),),registry,source_revision='a'*40)
    return SimpleNamespace(ws=ws,root=root,receipt=r,base=tmp_path,ar=ar,config=tmp_path/'host.json')

def query(case,**changes):
    q={'action':'history_dossier','ref':'fixture:history/manifest.json','manifest_sha256':case.receipt['manifest_sha256'],'date':'2020-01-05'}
    q.update(changes);return q

def test_existing_transport_exposes_hash_bound_daily_dossier(case):
    result=dispatch(case.ws,query(case),config_path=case.config)
    assert result['action']=='history_dossier'
    assert result['result']['market']['rows'][0]['close_tradj']==52.0
    assert result['source_access']=='read_only'
    assert result['implementation_revision']=='a'*40
    assert len(result['source_files'])==2
    assert all(r['content_sha256'] for r in result['source_files'])
    assert len(result['query_receipt_sha256'])==64
    assert 'outcomes' not in result['result']['market']

def test_history_capability_is_explicit_not_a_new_transport(case):
    result=dispatch(case.ws,{'action':'capabilities'},config_path=case.config)
    assert 'history_dossier' in result['actions']
    assert result['history']['source_access']=='existing_descriptor_confined_roots'
    assert result['history']['point_in_time_eligible'] is False

def test_bare_filesystem_reader_is_never_used_by_transport(case,monkeypatch):
    from engine.neuralweb import market_memory_history_macro as mm
    def forbidden(*a,**k):pytest.fail('transport must use existing descriptor-confined file owner')
    mp,mh=macro(case.base)
    monkeypatch.setattr(case.ar,'_regular_file',forbidden)
    monkeypatch.setattr(mm,'_regular_file',forbidden)
    result=dispatch(case.ws,query(case,date='2020-02-13',macro_ref='fixture:macro.json',macro_sha256=mh),config_path=case.config)
    assert result['result']['macro']['total_events']==1
    assert result['result']['market']['status']=='NO_OBSERVATION'

def test_default_transport_does_not_open_outcome_file(case):
    for p in case.root.glob('outcomes-*.parquet'):p.unlink()
    assert dispatch(case.ws,query(case),config_path=case.config)['result']['market']['rows']
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case,reveal_outcomes=True),config_path=case.config)

def test_explicit_reveal_stays_explicit(case):
    r=dispatch(case.ws,query(case,reveal_outcomes=True),config_path=case.config)
    assert r['result']['outcomes_revealed'] is True
    assert r['result']['market']['outcomes']

@pytest.mark.parametrize('change',[
    {'ref':'fixture:../outside/manifest.json'},
    {'ref':'unbound:history/manifest.json'},
    {'ref':'fixture:history/secret-manifest.json'},
    {'ref':'fixture:history/states-2020.parquet'},
    {'manifest_sha256':'bad'}, {'reveal_outcomes':'false'},
    {'macro_ref':'fixture:macro.json'},
    {'macro_sha256':'a'*64}, {'date':'2020-1-5'},
])
def test_unsafe_history_requests_are_refused(case,change):
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case,**change),config_path=case.config)

@pytest.mark.parametrize('field',['command','sql','output','root','api_key','pit_backtest_eligible'])
def test_no_write_or_provider_arguments_are_admitted(case,field):
    with pytest.raises(WorkspaceError,match='INVALID_REQUEST_FIELDS'):
        dispatch(case.ws,query(case,**{field:'not-admitted'}),config_path=case.config)

def test_symlink_and_hardlink_data_refused_by_original_owner(case):
    target=next(case.root.glob('states-*.parquet'));data=target.read_bytes();target.unlink()
    other=case.base/'outside.parquet';other.write_bytes(data);target.symlink_to(other)
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case),config_path=case.config)
    target.unlink();os.link(other,target)
    with pytest.raises(WorkspaceError):dispatch(case.ws,query(case),config_path=case.config)

def test_changed_source_version_during_read_refuses_before_return(case,monkeypatch):
    original=case.ws._file
    @contextmanager
    def changed(ref,*args,**kwargs):
        with original(ref,*args,**kwargs) as opened:
            yield opened
            if ref.endswith('states-2020.parquet'):
                p=case.root/'states-2020.parquet';p.write_bytes(p.read_bytes()+b'changed')
    monkeypatch.setattr(case.ws,'_file',changed)
    with pytest.raises(WorkspaceError,match='SOURCE_CHANGED'):
        dispatch(case.ws,query(case),config_path=case.config)

def test_no_files_written_by_history_request(case):
    before={str(p.relative_to(case.base)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in case.base.rglob('*') if p.is_file()}
    dispatch(case.ws,query(case),config_path=case.config)
    after={str(p.relative_to(case.base)):(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in case.base.rglob('*') if p.is_file()}
    assert before==after


@pytest.mark.parametrize('value', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_json_request_is_a_typed_refusal(case, value):
    with pytest.raises(WorkspaceError, match='INVALID_REQUEST'):
        dispatch(case.ws, {'action': 'capabilities', 'limit': value}, config_path=case.config)


def test_macro_reference_cannot_open_historical_outcome_file(case, monkeypatch):
    outcome = next(case.root.glob('outcomes-*.parquet'))
    opened = []
    original = case.ws._file
    @contextmanager
    def record(ref, *args, **kwargs):
        opened.append(ref)
        with original(ref, *args, **kwargs) as item:
            yield item
    monkeypatch.setattr(case.ws, '_file', record)
    with pytest.raises(WorkspaceError):
        dispatch(case.ws, query(case, macro_ref='fixture:history/' + outcome.name,
            macro_sha256=hashlib.sha256(outcome.read_bytes()).hexdigest()), config_path=case.config)
    assert not any('outcomes-' in name for name in opened)


def test_history_publishes_encoded_and_decoded_limits_separately(case):
    result = dispatch(case.ws, {'action': 'capabilities'}, config_path=case.config)
    assert result['history']['max_price_file_bytes'] == case.ar.MAX_FILE_BYTES
    assert result['history']['max_decoded_price_file_bytes'] == case.ar.MAX_DATE_DECODE_BYTES
    assert result['history']['budget_is_peak_process_memory_limit'] is False


def test_large_admitted_source_provenance_has_bounded_day_projection(monkeypatch, tmp_path):
    from tests.test_market_memory_history_archive import module, request, fake_reader
    m = module()
    r = request()
    names = ['SPY'] + [f'P{i:02}' for i in range(63)]
    refs = [['2026-10-13', f'{i + 1:064x}'] for i in range(20)]
    r['symbols'] = [{'vendor_symbol': name, 'refs': refs} for name in names]
    assert len(m._bytes(r)) < 128 * 1024
    def source(*args, **kwargs):
        rowset = fake_reader(*args, **kwargs)
        selected = tuple(tuple(ref) for ref in args[2])
        return SimpleNamespace(rows=rowset.rows, source_partitions=selected,
            metadata=lambda: {'source': 'eod-bars', 'vendor_symbol': args[1],
                              'source_partitions': [list(ref) for ref in selected],
                              'pit_backtest_eligible': False})
    monkeypatch.setattr(m, 'read_research_history', source)
    packet = m.assemble_history(r)
    root = tmp_path / 'large'
    receipt = m.write_archive(packet, root)
    result = m.read_day(root, '2010-01-01', expected_manifest_sha256=receipt['manifest_sha256'])
    assert result['rows'] == []
    assert len(m._bytes(result['source_references'])) < 32768
    assert result['source_references']['SPY']['source_partition_count'] == 20
    retained = json.loads((root / 'manifest.json').read_text())
    assert retained['sources']['SPY']['source_partitions'] == refs
    assert result['source_reference_detail'] == 'compact_digests; full_detail_in_retained_manifest'
    from lib.dataos.web_workspace import DataWorkspace, RootBinding
    from lib.dataos.web_api import dispatch
    registry = tmp_path / 'registry.yml'
    registry.write_text('schema: dataset_registry.v1\ndatasets: []\n')
    ws = DataWorkspace((RootBinding('fixture', tmp_path, 'research_capture'),), registry,
                       source_revision='a' * 40)
    q = {'action': 'history_dossier', 'ref': 'fixture:large/manifest.json',
         'manifest_sha256': receipt['manifest_sha256'], 'date': '2010-01-01'}
    assert dispatch(ws, q, config_path=tmp_path / 'host.json')['result']['market']['rows'] == []


class TestHistoricalFilings:
    def source(self, case, rows=None):
        from tests.test_market_memory_history_filings import payload
        raw=payload(rows);path=case.base/'earnings_8k_dates.parquet';path.write_bytes(raw)
        return {'filings_ref':'fixture:earnings_8k_dates.parquet','filings_sha256':hashlib.sha256(raw).hexdigest()}

    def test_existing_daily_action_includes_only_explicitly_bound_filing_context(self,case):
        binding=self.source(case)
        result=dispatch(case.ws,query(case,date='2020-03-16',**binding),config_path=case.config)
        assert result['result']['filings']['total_events']==1
        assert result['result']['market']['status']=='NO_OBSERVATION'
        assert result['result']['coverage']['issuer_filings_and_earnings_context']=='SELECTED_ITEM_202_FILING_METADATA_ONLY'
        assert any(r['ref']==binding['filings_ref'] and r['content_sha256']==binding['filings_sha256'] for r in result['source_files'])
        assert not result['result']['outcomes_revealed']

    def test_unselected_filing_source_is_not_opened(self,case,monkeypatch):
        binding=self.source(case);original=case.ws._file;opened=[]
        @contextmanager
        def observe(ref,*a,**kw):
            opened.append(ref)
            with original(ref,*a,**kw) as value:yield value
        monkeypatch.setattr(case.ws,'_file',observe)
        result=dispatch(case.ws,query(case),config_path=case.config)
        assert binding['filings_ref'] not in opened and 'filings' not in result['result']

    @pytest.mark.parametrize('change',[{'filings_ref':'fixture:earnings_8k_dates.parquet'},
        {'filings_sha256':'a'*64},{'filings_offset':-1},{'filings_offset':True},{'filings_offset':100}])
    def test_unpaired_or_unbound_filing_fields_refuse(self,case,change):
        with pytest.raises(WorkspaceError):dispatch(case.ws,query(case,**change),config_path=case.config)

    def test_outcome_partition_cannot_masquerade_as_filing_source(self,case,monkeypatch):
        binding=self.source(case);binding['filings_ref']='fixture:history/outcomes-2020.parquet'
        def forbidden(*a,**k):pytest.fail('invalid filing source must refuse before any file opens')
        monkeypatch.setattr(case.ws,'_file',forbidden)
        with pytest.raises(WorkspaceError):dispatch(case.ws,query(case,**binding),config_path=case.config)

    def test_wrong_filing_digest_is_typed_and_no_partial_result(self,case):
        binding=self.source(case);binding['filings_sha256']='0'*64
        with pytest.raises(WorkspaceError,match='HISTORY_SOURCE_OR_CONTRACT_INVALID'):
            dispatch(case.ws,query(case,**binding),config_path=case.config)

    def test_filing_date_pagination_uses_explicit_matched_offset(self,case):
        from tests.test_market_memory_history_filings import row
        binding=self.source(case,[row(accession=f'0000320193-20-{i:06}') for i in range(51)])
        first=dispatch(case.ws,query(case,date='2020-03-16',**binding),config_path=case.config)
        second=dispatch(case.ws,query(case,date='2020-03-16',filings_offset=50,**binding),config_path=case.config)
        assert len(first['result']['filings']['events'])==50 and len(second['result']['filings']['events'])==1
        assert first['query_receipt_sha256']!=second['query_receipt_sha256']

    def test_filing_capability_preserves_scientific_limits(self,case):
        capabilities=dispatch(case.ws,{'action':'capabilities'},config_path=case.config)
        assert capabilities['history']['filings']['source_kind']=='retained_item_202_filing_metadata'
        assert capabilities['history']['filings']['max_records_per_date_page']==50
        assert capabilities['history']['filings']['intraday_publication_time_verified'] is False


def test_filing_source_keeps_original_descriptor_change_guard(case,monkeypatch):
    from tests.test_market_memory_history_filings import payload
    raw=payload();file=case.base/'earnings_8k_dates.parquet';file.write_bytes(raw)
    original=case.ws._file
    @contextmanager
    def changed(ref,*a,**k):
        with original(ref,*a,**k) as opened:
            yield opened
            if ref.endswith('earnings_8k_dates.parquet'):
                file.write_bytes(raw+b'changed')
    monkeypatch.setattr(case.ws,'_file',changed)
    with pytest.raises(WorkspaceError,match='SOURCE_CHANGED'):
        dispatch(case.ws,query(case,date='2020-03-16',filings_ref='fixture:earnings_8k_dates.parquet',filings_sha256=hashlib.sha256(raw).hexdigest()),config_path=case.config)


def test_filing_source_symlink_and_hardlink_are_refused(case):
    from tests.test_market_memory_history_filings import payload
    raw=payload();source=case.base/'other.parquet';source.write_bytes(raw)
    file=case.base/'earnings_8k_dates.parquet';file.symlink_to(source)
    q=query(case,filings_ref='fixture:earnings_8k_dates.parquet',filings_sha256=hashlib.sha256(raw).hexdigest())
    with pytest.raises(WorkspaceError):dispatch(case.ws,q,config_path=case.config)
    file.unlink();os.link(source,file)
    with pytest.raises(WorkspaceError):dispatch(case.ws,q,config_path=case.config)
