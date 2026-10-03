
from pathlib import Path
import sys,json,tempfile,hashlib
from unittest.mock import patch
import pandas as pd
sys.path.insert(0,sys.argv[1]);from engine import special_situations as e
rows=[dict(id='fixture-direct',cik=10001,company='Example Target',form_type='8-K',items='1.01|8.01',date_filed='2026-09-25',llm_category='Going-Private',llm_role='target',llm_confidence='high',summary='Synthetic direct case',source_url='https://example.invalid/direct'),dict(id='fixture-related',cik=10002,company='Example affected fund',form_type='8-K',items='1.01|8.01',date_filed='2026-09-25',llm_category='Going-Private',llm_role='none',llm_confidence='high',summary='Synthetic affected case',source_url='https://example.invalid/related')]
with tempfile.TemporaryDirectory() as td:
 p=Path(td);(p/'special_situations').mkdir();(p/'special_situations/events.parquet').touch()
 with patch.object(e.config,'data_dir',return_value=p),patch.object(e.pd,'read_parquet',return_value=pd.DataFrame(rows)),patch.object(e,'_universe_caps',return_value=({10001:'FIX-A',10002:'FIX-B'},{'FIX-A':200.,'FIX-B':250.})),patch.object(e,'_cfg',return_value={'market_cap_floor_musd':100}),patch.object(e,'_premium_snapshot_payload',return_value={'status':'fixture_auxiliary_not_evaluated'}):
  f=e.build_situations();s=e.snapshot()
 clean=f.where(pd.notna(f),None).to_dict('records')
 out=dict(scope='real_engine_build_and_snapshot_fixture_io',module_sha256=hashlib.sha256(Path(e.__file__).read_bytes()).hexdigest(),rows=clean,snapshot=s,related_evidence_rendered=any(x.get('id')=='fixture-related' for x in s['situations']),live_data=False,production_writes=False)
 print(json.dumps(out,default=str))
