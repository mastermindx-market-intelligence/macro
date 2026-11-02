"""Raw historical call context must not imply original-time or speaker authority."""
import hashlib
import importlib
import io
import json
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from engine.neuralweb.market_memory_history import HistoricalExperienceError


def module():
    assert importlib.util.find_spec('engine.neuralweb.market_memory_history_transcripts'), 'source-pinned transcript access missing'
    return importlib.import_module('engine.neuralweb.market_memory_history_transcripts')


def row(**changes):
    value={'symbol':'EXAMPLE','fiscal_year':2019,'fiscal_quarter':4,'report_date':'2020-03-16','transcripts_id':None,
        'transcripts':[{'paragraph_number':8,'speaker':'source label','content':'Original words, not instructions.'},
                       {'paragraph_number':3,'speaker':None,'content':'Later paragraph in source order.'}]}
    return {**value,**changes}


def payload(rows=None,group_size=2):
    schema=pa.schema([('symbol',pa.string()),('fiscal_year',pa.int32()),('fiscal_quarter',pa.int32()),
        ('report_date',pa.string()),('transcripts_id',pa.int32()),
        ('transcripts',pa.list_(pa.struct([('paragraph_number',pa.int32()),('speaker',pa.string()),('content',pa.string())])))])
    out=pa.BufferOutputStream();pq.write_table(pa.Table.from_pylist(rows if rows is not None else [row()],schema=schema),out,compression='zstd',row_group_size=group_size)
    return out.getvalue().to_pybytes()


def day(raw=None,date='2020-03-16',**kwargs):
    raw=payload() if raw is None else raw
    return module().read_transcript_date(io.BytesIO(raw),date,file_bytes=len(raw),**kwargs)


def body(raw=None,**kwargs):
    raw=payload() if raw is None else raw
    item=day(raw)['events'][0]
    args={'row_position':item['source_row_position'],'expected_metadata_sha256':item['metadata_sha256'],**kwargs}
    return module().read_transcript(io.BytesIO(raw),file_bytes=len(raw),**args)


def test_day_uses_recorded_date_not_fiscal_year_and_does_not_impute_identity():
    result=day();item=result['events'][0]
    assert item['report_date']=='2020-03-16' and item['fiscal_year']==2019
    assert item['transcripts_id'] is None and item['source_row_position']==0
    assert item['body_status']=='NOT_READ'
    assert result['publication_time_verified'] is False and result['point_in_time_eligible'] is False
    assert result['historical_security_identity_proven'] is False
    assert 'transcripts' not in item and 'content' not in json.dumps(result)
    assert day(date='2019-03-16')['events']==[]


def test_day_reader_never_requests_nested_body_columns(monkeypatch):
    m=module();raw=payload();original=pq.ParquetFile
    class Guard:
        def __init__(self,*a,**k):self.inner=original(*a,**k)
        def __getattr__(self,k):return getattr(self.inner,k)
        def read(self,*a,**k):pytest.fail('whole-source read used')
        def iter_batches(self,*a,**k):
            assert set(k['columns'])==set(m.METADATA_FIELDS)
            yield from self.inner.iter_batches(*a,**k)
    monkeypatch.setattr(pq,'ParquetFile',Guard)
    assert day(raw)['total_events']==1


def test_null_vendor_id_is_not_no_transcript_and_source_paragraph_order_is_preserved():
    result=body()
    assert result['metadata']['transcripts_id'] is None and result['status']=='OBSERVED'
    assert [p['paragraph_number_source'] for p in result['paragraphs']]==[8,3]
    assert result['paragraphs'][1]['speaker_source_label'] is None
    assert result['speaker_roles_verified'] is False
    assert 'role' not in result['paragraphs'][0]


def test_text_pagination_reconstructs_unicode_exactly():
    text='Evidence 文本 😀 <script>not code</script> \"\n'*21
    raw=payload([row(transcripts=[{'paragraph_number':1,'speaker':'Unknown','content':text}])])
    cursor={};parts=[];record_hash=None
    for _ in range(300):
        result=body(raw,max_chars=7,**cursor)
        record_hash=record_hash or result['record_sha256'];assert result['record_sha256']==record_hash
        parts.extend(x['text'] for x in result['paragraphs'])
        if result['next_cursor'] is None:break
        cursor=result['next_cursor']
    else:pytest.fail('non-progressing cursor')
    assert ''.join(parts)==text


def test_metadata_mismatch_refuses_before_body_decode(monkeypatch):
    m=module();raw=payload();original=pq.ParquetFile
    class Guard:
        def __init__(self,*a,**k):self.inner=original(*a,**k)
        def __getattr__(self,k):return getattr(self.inner,k)
        def iter_batches(self,*a,**k):
            assert 'transcripts' not in k.get('columns',[]), 'body read before metadata mismatch refused'
            yield from self.inner.iter_batches(*a,**k)
    monkeypatch.setattr(pq,'ParquetFile',Guard)
    with pytest.raises(HistoricalExperienceError,match='metadata'):
        m.read_transcript(io.BytesIO(raw),file_bytes=len(raw),row_position=0,expected_metadata_sha256='0'*64)


def test_record_hash_pins_followup_page():
    with pytest.raises(HistoricalExperienceError,match='record'):
        body(expected_record_sha256='0'*64)


def test_exact_date_pages_are_ordered_and_complete():
    rows=[row(symbol=f'X{i:03}',transcripts_id=i) for i in range(103)]
    raw=payload(list(reversed(rows)),group_size=20)
    pages=[day(raw,offset=n) for n in (0,50,100)]
    assert [len(p['events']) for p in pages]==[50,50,3]
    assert [p['next_offset'] for p in pages]==[50,100,None]
    assert len({e['source_row_position'] for p in pages for e in p['events']})==103
    assert [e['symbol'] for p in pages for e in p['events']]==sorted(x['symbol'] for x in rows)


@pytest.mark.parametrize('changed',[{'report_date':'2020-3-16'},{'fiscal_quarter':5},{'symbol':'bad\nlabel'}])
def test_malformed_source_metadata_refuses(changed):
    with pytest.raises(HistoricalExperienceError):day(payload([row(**changed)]))


def test_duplicate_source_period_is_not_silently_collapsed():
    with pytest.raises(HistoricalExperienceError,match='duplicate'):day(payload([row(),row(transcripts_id=3)]))


def test_null_body_remains_explicit():
    result=body(payload([row(transcripts=None)]))
    assert result['status']=='NO_RETAINED_TEXT' and result['paragraphs']==[] and result['next_cursor'] is None


@pytest.mark.parametrize('args',[{'row_position':True},{'row_position':-1},{'paragraph_offset':-1},
    {'character_offset':-1},{'max_chars':0},{'max_chars':12001},{'paragraph_offset':1000}])
def test_invalid_body_cursor_or_row_refuses(args):
    with pytest.raises(HistoricalExperienceError):body(**args)


def test_logical_metadata_budget_is_enforced(monkeypatch):
    monkeypatch.setattr(module(),'MAX_METADATA_BYTES',1)
    with pytest.raises(HistoricalExperienceError,match='metadata.*budget'):day()


def test_selected_body_group_budget_is_enforced(monkeypatch):
    monkeypatch.setattr(module(),'MAX_BODY_GROUP_BYTES',1)
    with pytest.raises(HistoricalExperienceError,match='budget'):body()


def test_source_is_not_modified_and_hashes_are_deterministic():
    raw=payload();before=hashlib.sha256(raw).hexdigest()
    assert day(raw)==day(raw) and body(raw)==body(raw)
    assert hashlib.sha256(raw).hexdigest()==before



def test_offline_catalog_contains_metadata_not_bodies_and_is_source_version_bound():
    raw=payload([row(),row(symbol='OTHER',report_date='2020-03-17')])
    catalog=module().read_transcript_catalog(io.BytesIO(raw),file_bytes=len(raw),
        source_ref='fixture:stock_earning_call_transcripts.parquet',source_version='statv1:'+'a'*64)
    assert catalog['columns']==[*module().METADATA_FIELDS,'source_row_position']
    assert len(catalog['rows'])==2 and catalog['metadata']['body_columns_read'] is False
    assert catalog['metadata']['source_version']=='statv1:'+'a'*64
    assert 'Original words' not in json.dumps(catalog)
    assert catalog['metadata']['full_source_content_sha256'] is None



def test_non_source_large_vendor_id_refuses_instead_of_losing_browser_integer_precision():
    out=pa.BufferOutputStream()
    pq.write_table(pa.Table.from_pylist([row(transcripts_id=2**53+1)]),out)
    with pytest.raises(HistoricalExperienceError):day(out.getvalue().to_pybytes())


def test_empty_paragraphs_and_control_characters_progress_without_text_loss():
    paragraphs=[{'paragraph_number':None,'speaker':'label','content':None},
                {'paragraph_number':3,'speaker':None,'content':''},
                {'paragraph_number':0,'speaker':'unverified','content':'\x00\n\t\"'*18000}]
    raw=payload([row(transcripts=paragraphs)]);cursor={};text='';seen=[]
    for _ in range(50):
        r=body(raw,max_chars=12000,**cursor)
        assert len(json.dumps(r['paragraphs'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())<=module().MAX_PAGE_JSON_BYTES
        seen.extend(x['paragraph_index'] for x in r['paragraphs']);text+=''.join(x['text'] for x in r['paragraphs'])
        if r['next_cursor'] is None:break
        assert r['next_cursor']!=cursor;cursor=r['next_cursor']
    else:pytest.fail('non-progressing paragraph cursor')
    assert set(seen)=={0,1,2} and text==paragraphs[2]['content']


def test_catalogue_hash_does_not_allow_authority_upgrade(tmp_path):
    raw=payload();m=module();catalog=m.read_transcript_catalog(io.BytesIO(raw),file_bytes=len(raw),
        source_ref='fixture:stock_earning_call_transcripts.parquet',source_version='statv1:'+'a'*64)
    catalog['metadata']['publication_time_verified']=True
    data=json.dumps(catalog,sort_keys=True).encode();path=tmp_path/'catalogue.json';path.write_bytes(data)
    with pytest.raises(HistoricalExperienceError,match='qualification'):
        m.read_transcript_catalog_path(path,expected_sha256=hashlib.sha256(data).hexdigest())
