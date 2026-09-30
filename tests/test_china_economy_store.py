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


# FAI period-basis repair: two different measures in one existing owner table.
def _fai_fields(value=-7.2, period='2026-08', definition=None):
    import json
    from pathlib import Path
    from engine.china_economy_store import frames_from_receipt
    cat = json.loads((Path(__file__).parents[1]/'config/china_economy_catalog.json').read_text())['metrics']
    assert cat['investment_ytd']['owner_path']=='china_macro/fai.fai_ytd_yoy'
    assert cat['investment_ytd']['definition_id']=='investment_ytd.nbs_comparable.v2'
    if definition:
        from copy import deepcopy
        cat = deepcopy(cat); cat['investment_ytd']['definition_id']=definition
    receipt={'url':'https://www.stats.gov.cn/sj/zxfb/202609/investment.html',
             'published_at':'2026-09-15T10:00:00+08:00','observed_at':'2026-09-29T10:00:00+08:00',
             'response_sha256':'a'*64,'publication_precision':'minute'}
    return frames_from_receipt([{'metric_id':'investment_ytd','period':period,'value':value}],receipt,cat)['china_macro/fai']


def _fai_views(frame, day=None):
    from datetime import date
    from engine.china_macro_evidence import build_snapshot
    from engine.china_economy_store import read_metric_from_store
    day=day or date(2026,9,29)
    read=lambda group,table:frame if (group,table)==('china_macro','fai') else None
    overview=read_metric_from_store('investment_ytd',read,day.isoformat()+'T23:59:59+08:00')
    snapshot=build_snapshot(read,day)
    dialog=next(m for m in snapshot['panels']['policy']['metrics'] if m['id']=='macro_fai_yoy')
    return overview,dialog


def test_fai_two_period_bases_are_distinct_and_dialog_matches_overview():
    import pandas as pd
    frame=_fai_fields();frame['fai_yoy']=-13.51
    before=frame.copy(deep=True)
    economy,dialog=_fai_views(frame)
    pd.testing.assert_frame_equal(frame,before)
    assert economy['value']==dialog['value']==-7.2
    assert economy['chart']==dialog['chart']
    assert economy['definition_id']==dialog['definition_id']
    assert dialog['unit']=='% YTD YoY' and dialog['delta_unit']=='pp'
    assert dialog['source']['store_path']=='china_macro/fai.fai_ytd_yoy'
    assert dialog['source']['value_receipt_verified'] is True
    assert dialog['source']['publication_time']==economy['published_at']
    assert dialog['n']==1 and dialog['delta'] is None


def test_fai_legacy_monthly_is_never_cumulative_fallback():
    import pandas as pd
    frame=pd.DataFrame({'fai_yoy':[-13.51]},index=pd.to_datetime(['2026-08-01']))
    a,b=_fai_views(frame)
    assert a['value'] is None and b['value'] is None


@pytest.mark.parametrize('defect',['value','digest','definition','future_acquisition','missing_metadata','url'])
def test_fai_bad_receipt_is_refused_by_both_views(defect):
    frame=_fai_fields();col='fai_ytd_yoy'
    if defect=='value':frame[col]=-13.51
    if defect=='digest':frame[col+'__value_sha256']='bad'
    if defect=='definition':frame=_fai_fields(definition='investment_ytd.v1')
    if defect=='future_acquisition':frame[col+'__observed_at']='2026-10-01T00:00:00+08:00'
    if defect=='missing_metadata':frame=frame[[col]]
    if defect=='url':frame[col+'__source_url']='https://unapproved.example/value'
    frame['fai_yoy']=-13.51
    a,b=_fai_views(frame)
    assert a['value'] is None and b['value'] is None


def test_fai_null_and_older_period_do_not_manufacture_cumulative_change():
    import pandas as pd
    from datetime import date
    a,b=_fai_views(_fai_fields(None))
    assert a['value'] is None and b['value'] is None
    # Older official reference stays labeled older, never relabeled October.
    a,b=_fai_views(_fai_fields(),date(2026,10,5))
    assert a['status']=='older_period' and b['status']=='stale'
    assert b['reference_label']=='2026-08' and b['delta'] is None
