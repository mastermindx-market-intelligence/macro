"""Exact ECB flags and successful-store identity through the native collector."""
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from unittest.mock import Mock
import pytest
from collectors.intl_macro import IntlMacroAdapter
from collectors.base import run_adapter
from lib import config
from lib.intl_ecb_policy_publication import SOURCE_URL, read_ecb_policy_materialization
from tests.test_intl_ecb_policy_source import NATIVE_HEADER,NATIVE_ROWS

RAW=(NATIVE_HEADER+NATIVE_ROWS).encode()
NOW='2026-11-04T12:00:00+00:00'
class FixedDatetime(datetime):
    @classmethod
    def now(cls,tz=None):
        v=datetime.fromisoformat(NOW)
        return v if tz else v.replace(tzinfo=None)

def collector(root,monkeypatch,raw=RAW):
    cfg=deepcopy(config.load());cfg['storage']['data_dir']=str(root);cfg['storage']['run_status_file']=str(root/'run_status.json')
    cfg['intl']['countries']={};cfg['intl']['macro']['extra_series']={}
    spec=cfg['intl']['macro']['official_series']['ez_depo_rate'];cfg['intl']['macro']['official_series']={'ez_depo_rate':spec}
    (root/'native').mkdir();(root/'native/response.csv').write_bytes(raw)
    receipt={'status':200,'url':SOURCE_URL,'sha256':hashlib.sha256(raw).hexdigest(),'requested_at':'2026-11-04T05:42:42+00:00','received_at':'2026-11-04T05:42:44+00:00'}
    (root/'native/receipt.json').write_text(json.dumps(receipt));spec['native_input']={'response':'native/response.csv','receipt':'native/receipt.json'}
    monkeypatch.setattr(config,'load',lambda:cfg);monkeypatch.setattr('collectors.intl_macro.datetime',FixedDatetime);monkeypatch.setattr('collectors.base.datetime',FixedDatetime)
    a=IntlMacroAdapter();a.http_get=Mock(side_effect=AssertionError('no new acquisition'));return a,cfg

def test_original_flags_reach_committed_immutable_capture(tmp_path,monkeypatch):
    a,_=collector(tmp_path,monkeypatch);result=run_adapter(a)
    assert result.status=='ok' and result.rows==3
    materialized=read_ecb_policy_materialization(data_root=tmp_path)
    assert materialized['status']=='ready'
    assert [(r['date'],r['value'],r['status'])for r in materialized['parsed']['observations']]==[('2026-08-28',2.25,'observed'),('2026-09-30',2.5,'observed'),('2026-11-04',2.5,'observed')]
    assert materialized['receipt']['provider_published_at'] is None
    assert materialized['receipt']['revision_vintage'] is None
    assert a._ecb_policy_response is None;a.http_get.assert_not_called()
    from lib.intl_macro_publication import read_ecb_deposit_materialization
    from scripts.build_intl import _ecb_publication_measure
    field=_ecb_publication_measure(read_ecb_deposit_materialization(data_root=tmp_path), evaluated_at=NOW,
        generation='im-workspace-generation:4979a6c3-b834-4c69-8f1b-c8961cc5e11a')
    assert field['quality']=='qualified' and field['value']==2.5

@pytest.mark.parametrize('fault',['pointer','blob','store'])
def test_changed_capture_or_missing_dependency_fails_closed(tmp_path,monkeypatch,fault):
    a,_=collector(tmp_path,monkeypatch);run_adapter(a);m=read_ecb_policy_materialization(data_root=tmp_path)
    directory=tmp_path/'intl_macro/publication/ez_depo_rate_policy'
    if fault=='pointer':
        p=directory/'current.json';r=json.loads(p.read_text());r['committed_at']='2026-11-05T00:00:00+00:00';p.write_text(json.dumps(r))
    elif fault=='blob': (directory/(m['receipt']['source_sha256']+'.csv')).unlink()
    else:(tmp_path/'intl_macro/ez_depo_rate.parquet').write_bytes(b'changed')
    assert read_ecb_policy_materialization(data_root=tmp_path)['status']=='failed'

def test_poststore_capture_failure_never_reacquires(tmp_path,monkeypatch):
    a,_=collector(tmp_path,monkeypatch)
    monkeypatch.setattr('lib.intl_ecb_policy_publication.capture_ecb_policy_commit',Mock(side_effect=OSError('failed evidence')))
    result=run_adapter(a)
    assert result.status=='ok' and result.rows==3
    assert a._ecb_policy_response is None and (tmp_path/'intl_macro/ez_depo_rate.parquet').exists()
    a.http_get.assert_not_called();assert any('post-store evidence unavailable' in n for n in result.notes)

def test_withheld_last_native_row_cannot_lend_current_display_status(tmp_path,monkeypatch):
    raw=RAW.replace(b'2026-11-04,2.5,A,F',b'2026-11-04,2.5,A,C')
    a,_=collector(tmp_path,monkeypatch,raw);run_adapter(a);m=read_ecb_policy_materialization(data_root=tmp_path)
    assert m['status']=='ready' and m['parsed']['observations'][-1]['value'] is None
    assert a.source_meta['ez_depo_rate']['status']=='official_withheld'
