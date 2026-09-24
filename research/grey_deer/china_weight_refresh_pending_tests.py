"""Pending source-supply acceptance: 16 RED cases; implementation write refused.
Not part of passing tests. Run this file explicitly when the same-carrier gate clears.
"""
from io import BytesIO
import pandas as pd
import pytest
from collectors import china_universe as cu
from tests.test_china_universe_index_constituents import adapter, _weight_frame, _Resp


@pytest.fixture()
def weight_adapter(adapter, tmp_path, monkeypatch):
    adapter.dir = tmp_path / 'china_search'
    adapter.dir.mkdir()
    adapter.cfg = {**adapter.cfg, 'index_constituents': ['000300']}
    for key in ('RENDER_NO_DRIP', 'CHINA_FAST_RENDER'):
        monkeypatch.delenv(key, raising=False)
    return adapter


def _weight_response(monkeypatch, adapter, frame=None):
    buf = BytesIO()
    (_weight_frame() if frame is None else frame).to_excel(buf, index=False)
    payload = buf.getvalue()
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        return _Resp(payload)
    monkeypatch.setattr(adapter, 'http_get', get)
    return payload, calls


def _seed_weight_cache(adapter, date='20260831'):
    frame = _weight_frame(); frame['日期'] = date
    saved = cu._close_weight_snapshot(frame, symbol='000300', observed_at='2026-09-22T00:00:00Z')
    path = adapter.dir / 'index_weights.parquet'
    saved.to_parquet(path, index=False)
    return path, path.read_bytes()


def test_weight_refresh_supplies_existing_reader_with_all_members(weight_adapter, monkeypatch):
    import hashlib
    from lib import store
    ad = weight_adapter
    payload, calls = _weight_response(monkeypatch, ad)
    result = ad._refresh_index_weights(now='2026-09-24T00:00:00Z')
    assert result['status'] == 'updated' and result['weight_date'] == '2026-08-31'
    assert len(calls) == 1 and calls[0][0] == cu._CSINDEX_WEIGHT_URL.format(symbol='000300')
    assert calls[0][1]['timeout'] == int(ad.cfg.get('index_fetch_timeout_s', 30))
    monkeypatch.setattr(cu.config, 'data_dir', lambda: ad.dir.parent)
    saved = store.read('china_search', 'index_weights')
    assert len(saved) == saved.ticker.nunique() == 300
    assert set(saved.source_sha256) == {hashlib.sha256(payload).hexdigest()}
    assert set(saved.observed_at) == {'2026-09-24T00:00:00+00:00'}


def test_weight_refresh_unchanged_preserves_first_observation_and_bytes(weight_adapter, monkeypatch):
    path, original = _seed_weight_cache(weight_adapter)
    _weight_response(monkeypatch, weight_adapter)
    result = weight_adapter._refresh_index_weights(now='2026-09-24T00:00:00Z')
    assert result['status'] == 'unchanged'
    assert path.read_bytes() == original


def test_weight_refresh_rejects_older_source_without_overwriting(weight_adapter, monkeypatch):
    path, original = _seed_weight_cache(weight_adapter)
    frame = _weight_frame(); frame['日期'] = 20260731
    _weight_response(monkeypatch, weight_adapter, frame)
    assert weight_adapter._refresh_index_weights(now='2026-09-24T00:00:00Z')['status'] == 'failed'
    assert path.read_bytes() == original


@pytest.mark.parametrize('fault', ['short', 'duplicate', 'wrong_index', 'future', 'bad_total', 'network', 'html'])
def test_weight_refresh_failure_preserves_cache(weight_adapter, monkeypatch, capsys, fault):
    ad = weight_adapter
    path, original = _seed_weight_cache(ad)
    frame = _weight_frame()
    if fault == 'short': frame = frame.iloc[:-1]
    elif fault == 'duplicate': frame.loc[1, '成分券代码'] = frame.loc[0, '成分券代码']
    elif fault == 'wrong_index': frame['指数代码'] = 905
    elif fault == 'future': frame['日期'] = 20261001
    elif fault == 'bad_total': frame['权重'] = 0.1
    _weight_response(monkeypatch, ad, frame)
    if fault == 'network':
        monkeypatch.setattr(ad, 'http_get', lambda *a, **k: (_ for _ in ()).throw(TimeoutError('offline')))
    elif fault == 'html':
        monkeypatch.setattr(ad, 'http_get', lambda *a, **k: _Resp(b'<html>unavailable</html>'))
    result = ad._refresh_index_weights(now='2026-09-24T00:00:00Z')
    assert result['status'] == 'failed'
    assert path.read_bytes() == original
    assert any(line.startswith('::warning title=china-index-weights::') for line in capsys.readouterr().out.splitlines())


@pytest.mark.parametrize('flag', ['RENDER_NO_DRIP', 'CHINA_FAST_RENDER'])
def test_weight_refresh_never_fetches_from_render(weight_adapter, monkeypatch, flag):
    _, calls = _weight_response(monkeypatch, weight_adapter)
    monkeypatch.setenv(flag, '1')
    assert weight_adapter._refresh_index_weights()['status'] == 'disabled'
    assert not calls and not (weight_adapter.dir / 'index_weights.parquet').exists()


def test_weight_refresh_without_configured_csi300_is_disabled(weight_adapter, monkeypatch):
    _, calls = _weight_response(monkeypatch, weight_adapter)
    weight_adapter.cfg['index_constituents'] = ['000905']
    assert weight_adapter._refresh_index_weights()['status'] == 'disabled'
    assert not calls


@pytest.mark.parametrize('failure', ['serialization', 'replace'])
def test_weight_refresh_publication_failure_keeps_last_good_bytes(weight_adapter, monkeypatch, failure):
    import os
    path, original = _seed_weight_cache(weight_adapter)
    frame = _weight_frame(); frame['日期'] = 20260923
    _weight_response(monkeypatch, weight_adapter, frame)
    def fail(*args, **kwargs):
        raise OSError('simulated write failure')
    if failure == 'serialization': monkeypatch.setattr(pd.DataFrame, 'to_parquet', fail)
    else: monkeypatch.setattr(os, 'replace', fail)
    result = weight_adapter._refresh_index_weights(now='2026-09-24T00:00:00Z')
    assert result['status'] == 'failed' and path.read_bytes() == original
    assert set(p.name for p in weight_adapter.dir.iterdir()) == {'index_weights.parquet'}


def test_weight_refresh_corrupt_existing_table_is_not_silently_replaced(weight_adapter, monkeypatch):
    path = weight_adapter.dir / 'index_weights.parquet'; path.write_bytes(b'corrupt prior evidence')
    _weight_response(monkeypatch, weight_adapter)
    assert weight_adapter._refresh_index_weights(now='2026-09-24T00:00:00Z')['status'] == 'failed'
    assert path.read_bytes() == b'corrupt prior evidence'
