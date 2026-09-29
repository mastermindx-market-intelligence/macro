from pathlib import Path
import sys,json
import pandas as pd
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.china_economy_store import document_from_store,build_from_store,frames_from_receipt,binding
from engine.china_economy import build_economy
from collectors.china_economy_release_parser import checked_source
CAT=json.loads((Path(__file__).resolve().parent/'fixtures/china_economy_review.json').read_text())['catalog']

def receipt():return checked_source('https://www.stats.gov.cn/sj/pmi.html','2026-08-31T09:30:00+08:00','2026-09-29T12:00:00+08:00',html='PARSER SHAPE FIXTURE NOT MARKET HISTORY')

def test_existing_receipt_roundtrip():
 p=[{'metric_id':'pmi_mfg','period':f'2026-{i:02}','value':50.1} for i in range(3,9)]
 frames=frames_from_receipt(p,receipt(),CAT)
 assert list(frames)==['china_macro/pmi'] and frames['china_macro/pmi'].index.is_unique
 d=document_from_store(lambda g,n:frames.get(g+'/'+n),CAT,'2026-09-29T12:00:00+08:00')
 m=build_economy(d)['metrics']['pmi_mfg']
 assert m['value']==50.1 and m['status']=='current'
 assert d['input_class']=='existing_parquet_owners_with_publication_receipts'

def test_no_review_fallback_when_store_empty():
 s=build_from_store(lambda g,n:None,CAT,'2026-09-29T12:00:00+08:00')
 assert s['counts']['valid_current']==0 and s['breadth']['covered']==0
 assert all(m['value'] is None for m in s['metrics'].values())

def test_no_fake_publication_for_legacy_values():
 f=pd.DataFrame({'pmi_mfg':[49.8]},index=pd.to_datetime(['2026-08-01']))
 s=build_from_store(lambda g,n:f if n=='pmi' else None,CAT,'2026-09-29T12:00:00+08:00')
 assert s['metrics']['pmi_mfg']['value'] is None
 assert 'publication_receipt_missing' in s['source_errors']['china_macro/pmi.pmi_mfg']

def test_one_source_failure_does_not_destroy_other_paths():
 frames=frames_from_receipt([{'metric_id':'retail_sa','period':'2026-08','value':-.13}],receipt(),CAT)
 def read(g,n):
  if n=='pmi':raise OSError('test failure')
  return frames.get(g+'/'+n)
 s=build_from_store(read,CAT,'2026-09-29T12:00:00+08:00')
 assert s['metrics']['retail_sa']['value']==-.13
 assert 'china_macro/pmi' in s['source_errors']

def test_shared_frame_not_overwritten_by_second_series():
 p=[{'metric_id':'pmi_mfg','period':'2026-08','value':49.8},{'metric_id':'pmi_nonmfg','period':'2026-08','value':49.0}]
 f=frames_from_receipt(p,receipt(),CAT)['china_macro/pmi']
 assert len(f)==1 and 'pmi_mfg' in f and 'pmi_nonmfg' in f

def test_duplicate_column_period_refused():
 p={'metric_id':'pmi_mfg','period':'2026-08','value':49.8}
 with pytest.raises(ValueError,match='duplicate'):frames_from_receipt([p,p],receipt(),CAT)

@pytest.mark.parametrize('path',['../../file.x','x/../y.z','x/no_column','x/table.bad-col'])
def test_no_path_escape(path):
 with pytest.raises(ValueError):binding(path)

def test_each_owner_read_once():
 counts={}
 def read(g,n):counts[g+'/'+n]=counts.get(g+'/'+n,0)+1;return None
 document_from_store(read,CAT,'2026-09-29T12:00:00+08:00')
 assert max(counts.values())==1

@pytest.mark.parametrize('field,value,expected',[
 ('pmi_mfg__response_sha256','z'*64,'incomplete_publication_receipt'),
 ('pmi_mfg__observed_at','2026-08-01T00:00:00+08:00','invalid_receipt_chronology'),
 ('pmi_mfg__observed_at','2026-09-30T00:00:00+08:00','acquisition_after_cutoff'),
 ('pmi_mfg__published_at','not a time','invalid_receipt_chronology'),
])
def test_receipts_are_checked_not_just_present(field,value,expected):
 f=frames_from_receipt([{'metric_id':'pmi_mfg','period':'2026-08','value':49.8}],receipt(),CAT)['china_macro/pmi']
 f[field]=value
 s=build_from_store(lambda g,n:f if n=='pmi' else None,CAT,'2026-09-29T12:00:00+08:00')
 assert s['metrics']['pmi_mfg']['value'] is None
 assert expected in s['source_errors']['china_macro/pmi.pmi_mfg']
