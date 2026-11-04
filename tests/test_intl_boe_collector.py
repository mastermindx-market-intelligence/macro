"""BoE normal collector path, with retained real response and no source requests."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock
import hashlib
import json
import pytest
from collectors.intl_macro import IntlMacroAdapter
from collectors.base import run_adapter
from lib import config

RAW = Path(__file__).parent / 'fixtures/intl_workspace/boe_iudbedr_2026.xml'
URL = 'https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?CodeVer=new&xml.x=yes&Datefrom=01%2FJan%2F2026&Dateto=02%2FNov%2F2026&SeriesCodes=IUDBEDR&VPD=N&VFD=Y&VUD=A'
NOW = '2026-11-04T10:10:00+00:00'
COLUMN = 'GB_bank_rate_official'

class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime.fromisoformat(NOW)
        return value if tz is not None else value.replace(tzinfo=None)

def collector(root, monkeypatch, native=True):
    cfg = deepcopy(config.load())
    cfg['storage']['data_dir'] = str(root)
    cfg['storage']['run_status_file'] = str(root / 'run_status.json')
    cfg['intl']['countries'] = {}
    cfg['intl']['macro']['extra_series'] = {}
    spec = cfg['intl']['macro']['official_series'][COLUMN]
    cfg['intl']['macro']['official_series'] = {COLUMN: spec}
    if native:
        (root / 'native').mkdir(parents=True)
        (root / 'native/response.xml').write_bytes(RAW.read_bytes())
        receipt = {'status': 200, 'sha256': hashlib.sha256(RAW.read_bytes()).hexdigest(),
            'url_final': URL, 'requested_at': '2026-11-04T08:57:22.722700+00:00',
            'settled_at': '2026-11-04T08:57:23.674719+00:00'}
        (root / 'native/receipt.json').write_text(json.dumps(receipt))
        spec['native_input'] = {'response':'native/response.xml','receipt':'native/receipt.json'}
    monkeypatch.setattr(config, 'load', lambda: cfg)
    monkeypatch.setattr('collectors.intl_macro.datetime', FixedDatetime)
    monkeypatch.setattr('collectors.base.datetime', FixedDatetime)
    return IntlMacroAdapter(), cfg

def test_actual_retained_response_reaches_normal_store_then_immutable_capture(tmp_path, monkeypatch):
    from lib.intl_boe_publication import read_boe_materialization
    adapter, cfg = collector(tmp_path, monkeypatch)
    adapter.http_get = Mock(side_effect=AssertionError('no new acquisition'))
    result = run_adapter(adapter)
    assert result.status == 'ok' and result.rows == 212
    adapter.http_get.assert_not_called()
    m = read_boe_materialization(data_root=tmp_path)
    assert m['status'] == 'ready'
    assert m['series'].loc['2026-08-28'] == 3.75
    assert m['series'].loc['2026-09-30'] == 3.75
    assert m['series'].iloc[-1] == 3.75
    assert adapter._boe_response is None
    assert adapter.source_meta[COLUMN]['source_updated'] == '2026-11-03 09:30:00'
    assert adapter.source_meta[COLUMN]['source_updated_timezone'] is None


def test_configured_native_http_path_uses_only_one_calendar_year_and_bank_rate(tmp_path, monkeypatch):
    adapter, _ = collector(tmp_path, monkeypatch, native=False)
    calls = []
    def http(url, **kwargs):
        calls.append((url, kwargs))
        from urllib.parse import urlencode
        return type('Response', (), {'content':RAW.read_bytes(),'url':url+'?'+urlencode(kwargs['params']),'status_code':200})()
    adapter.http_get = http
    result = run_adapter(adapter)
    assert result.status == 'ok' and result.rows == 212
    from lib.intl_boe_publication import read_boe_materialization
    materialized = read_boe_materialization(data_root=tmp_path)
    assert materialized['status'] == 'ready'
    assert materialized['receipt']['source_query']['Dateto'] == '04/Nov/2026'
    assert len(calls) == 1
    url, kw = calls[0]
    assert url == 'https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp'
    assert kw['params']['SeriesCodes'] == 'IUDBEDR'
    assert kw['params']['Datefrom'] == '01/Jan/2026'
    assert kw['params']['Dateto'] == '04/Nov/2026'
    assert kw['retries'] == 1

@pytest.mark.parametrize('change', ['hash','clock','foreign','duplicate','wrong_series'])
def test_retained_contract_failure_has_no_fetch_or_store(tmp_path, monkeypatch, change):
    adapter, cfg = collector(tmp_path, monkeypatch)
    f = tmp_path / 'native/receipt.json'; receipt = json.loads(f.read_text())
    if change == 'hash': receipt['sha256'] = '0'*64
    if change == 'clock': receipt['settled_at'] = '2026-11-04T11:00:00+00:00'
    if change == 'foreign': receipt['url_final'] = URL.replace('www.bankofengland.co.uk','example.com')
    if change == 'duplicate': receipt['url_final'] = URL+'&SeriesCodes=IUDBEDR'
    if change == 'wrong_series': receipt['url_final'] = URL.replace('IUDBEDR','IUDSOIA')
    f.write_text(json.dumps(receipt));adapter.http_get=Mock(side_effect=AssertionError('no acquisition fallback'))
    with pytest.raises(ValueError): adapter._fetch_official(COLUMN, cfg['intl']['macro']['official_series'][COLUMN])
    adapter.http_get.assert_not_called()
    assert adapter._boe_response is None and not (tmp_path/'intl_macro'/f'{COLUMN}.parquet').exists()


def test_poststore_evidence_failure_does_not_reacquire_or_undo_committed_data(tmp_path, monkeypatch):
    adapter, _ = collector(tmp_path, monkeypatch)
    adapter.http_get=Mock(side_effect=AssertionError('no acquisition'))
    monkeypatch.setattr('lib.intl_boe_publication.capture_boe_commit', Mock(side_effect=OSError('evidence failure')))
    result = run_adapter(adapter)
    assert result.status == 'ok' and result.rows == 212
    assert (tmp_path/'intl_macro'/f'{COLUMN}.parquet').exists()
    assert adapter._boe_response is None
    adapter.http_get.assert_not_called()
    assert any('post-store evidence unavailable' in x for x in result.notes)
