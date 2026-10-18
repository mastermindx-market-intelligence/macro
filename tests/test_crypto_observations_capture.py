"""Fake-HTTP capture pipeline: occurrence identity, receipt clocks, failed persist.

Joins the R11/R12 response-capture adapter to OKX, BGeometrics, and the
display-only intraday CVD consumer. Every HTTP call is a stand-in for
``requests.get``; every store path is ``tmp_path``. No provider network.
"""
from __future__ import annotations

import errno
import inspect
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

FUNDING_URL = 'https://www.okx.com/api/v5/public/funding-rate-history'
TAKER_URL = 'https://www.okx.com/api/v5/rubik/stat/taker-volume'
BGEO_URL = 'https://bitcoin-data.com/v1/funding-rate'
# 2026-01-01 00:00:00 UTC. Settlement is before every receipt in these fixtures.
FUNDING_MS = '1767225600000'


class _FakeResponse:
    def __init__(self, payload, url: str):
        self.payload = payload
        self.content = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        self.status_code = 200
        self.url = url
        self.headers = {
            'X-RateLimit-Remaining-Hour': '9',
            'X-RateLimit-Remaining-Day': '14',
        }

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f'HTTP {self.status_code}', response=self)


class _Http:
    """One logical clock and one requests.get seam for both collectors."""

    def __init__(self):
        self.events: list[tuple] = []
        self.t = pd.Timestamp('2026-02-01T00:00:00+00:00')
        self.frozen: str | None = None
        self.realized = '0.00021'
        self.predicted = '0.0002'
        self.hourly: list[list[str]] = _hours(6, buy='3', sell='1')
        self.daily: list[list[str]] = [[FUNDING_MS, '2', '3']]
        self.bgeo: list[dict] = [_bgeo_row('-0.0001')]

    def now(self) -> str:
        if self.frozen is None:
            self.t += pd.Timedelta(seconds=1)
            iso = self.t.isoformat()
        else:
            iso = self.frozen
        self.events.append(('clock', iso))
        return iso

    def freeze(self, iso: str) -> None:
        self.frozen = pd.Timestamp(iso).tz_convert('UTC').isoformat()

    def get(self, url, params=None, timeout=None, headers=None, **kwargs):
        self.events.append(('http', url))
        if url == FUNDING_URL:
            payload = {
                'code': '0',
                'data': [{
                    'instId': 'BTC-USDT-SWAP',
                    'instType': 'SWAP',
                    'fundingTime': FUNDING_MS,
                    'fundingRate': self.predicted,
                    'realizedRate': self.realized,
                    'formulaType': 'withRate',
                    'method': 'current_period',
                    # A source field that looks like finality must not be promoted.
                    'finality': 'final',
                }],
            }
        elif url == TAKER_URL:
            period = (params or {}).get('period')
            payload = {'code': '0', 'data': self.hourly if period == '1H' else self.daily}
        elif url == BGEO_URL:
            payload = self.bgeo
        else:
            payload = {'code': '0', 'data': []}
        return _FakeResponse(payload, url)


def _hours(n: int, buy: str, sell: str, start: str = '2026-01-01') -> list[list[str]]:
    idx = pd.date_range(start, periods=n, freq='h')
    rows = []
    for ts in idx:
        ms = str(int(pd.Timestamp(ts).tz_localize('UTC').timestamp() * 1000))
        rows.append([ms, sell, buy])
    return rows


def _bgeo_row(rate: str) -> dict:
    return {
        'd': '2026-01-01T16:00:00Z',
        'unixTs': '1767283200',
        'fundingRate': rate,
        'markPrice': 90,
        'delayed': True,
        'message': 'delayed',
        'finality': 'final',
    }


def _install(monkeypatch, tmp_path, http: _Http):
    from collectors import _crypto_observations as observations
    from collectors import base, bgeo, okx
    monkeypatch.setattr(observations.config, 'data_dir', lambda: tmp_path)
    monkeypatch.setattr(observations, 'now_utc', http.now)
    monkeypatch.setattr(base.requests, 'get', http.get)
    monkeypatch.setattr(bgeo.requests, 'get', http.get)
    monkeypatch.setattr(base.time, 'sleep', lambda *_a, **_k: None)
    monkeypatch.setattr(okx.time, 'sleep', lambda *_a, **_k: None)
    monkeypatch.setattr(bgeo.time, 'sleep', lambda *_a, **_k: None)
    monkeypatch.setattr(okx, 'MAX_PAGES_FIRST_RUN', 1)
    return observations


def _okx(monkeypatch, tmp_path, http: _Http):
    from collectors.okx import OkxAdapter
    observations = _install(monkeypatch, tmp_path, http)
    return OkxAdapter(), observations


def _bgeo(monkeypatch, tmp_path, http: _Http):
    from collectors.bgeo import BgeoAdapter
    observations = _install(monkeypatch, tmp_path, http)
    adapter = BgeoAdapter()
    adapter.cfg = {**adapter.cfg, 'metrics': {'funding-rate': 'funding_rate'}}
    return adapter, observations


def _funding_rows(observations, tmp_path, as_of: str):
    frame = observations.load_asof('okx_funding', as_of, root=tmp_path)
    return frame.sort_values(['received_at', 'capture_id']).reset_index(drop=True)


def _assert_receipt_follows_http(events, url: str, received_at: str) -> None:
    clocks = [i for i, event in enumerate(events) if event == ('clock', received_at)]
    assert clocks, received_at
    clock_at = clocks[0]
    prior_http = [
        i for i, event in enumerate(events[:clock_at])
        if event[0] == 'http' and event[1] == url
    ]
    assert prior_http, url
    assert not any(event == ('clock', received_at) for event in events[:prior_http[-1]])
    assert events[clock_at][1] == received_at


def _raise_fault(fault: str):
    if fault == 'enospc':
        def fail(*_a, **_k):
            raise OSError(errno.ENOSPC, 'No space left on device')
        return fail
    if fault == 'permission':
        def fail(*_a, **_k):
            raise PermissionError(errno.EACCES, 'Permission denied')
        return fail
    raise AssertionError(fault)


def test_same_occurrence_is_idempotent_and_reversion_keeps_three_receipts(tmp_path, monkeypatch):
    http = _Http()
    http.freeze('2026-01-02T08:00:00Z')
    adapter, observations = _okx(monkeypatch, tmp_path, http)
    path = observations.capture_path('okx_funding', root=tmp_path)

    first = adapter.fetch()
    assert 'funding_rate' in first and 'taker_volume_hourly' in first
    funding = [row for row in adapter.source_capture_status if row['source_id'] == 'okx_funding']
    assert len(funding) == 1 and funding[0]['status'] == 'stored'
    original_id = funding[0]['capture_id']
    after_first = path.read_bytes()

    replay = adapter.fetch()
    funding = [row for row in adapter.source_capture_status if row['source_id'] == 'okx_funding']
    assert len(funding) == 1
    assert funding[0]['status'] == 'already_present'
    assert funding[0]['capture_id'] == original_id
    assert path.read_bytes() == after_first
    seen = _funding_rows(observations, tmp_path, '2026-01-05T00:00:00Z')
    assert list(seen.capture_id) == [original_id]
    original_payload = seen.iloc[0].payload_json
    original_hash = seen.iloc[0].payload_sha256

    http.freeze('2026-01-02T09:00:00Z')
    http.realized = '0.00031'
    adapter.fetch()
    revised = _funding_rows(observations, tmp_path, '2026-01-05T00:00:00Z')
    assert len(revised) == 2
    assert list(revised.capture_id).count(original_id) == 1
    assert revised.loc[revised.capture_id == original_id, 'payload_json'].iloc[0] == original_payload

    http.freeze('2026-01-02T10:00:00Z')
    http.realized = '0.00021'
    adapter.fetch()
    restored = _funding_rows(observations, tmp_path, '2026-01-05T00:00:00Z')
    assert len(restored) == 3
    assert restored.capture_id.nunique() == 3
    kept = restored.loc[restored.capture_id == original_id].iloc[0]
    assert kept.payload_json == original_payload
    assert kept.payload_sha256 == original_hash
    assert kept.received_at.startswith('2026-01-02T08:00:00')
    reverted = restored.loc[restored.received_at.str.startswith('2026-01-02T10:00:00')].iloc[0]
    middle = restored.loc[restored.received_at.str.startswith('2026-01-02T09:00:00')].iloc[0]
    assert reverted.capture_id != original_id
    assert reverted.payload_sha256 == original_hash
    assert middle.payload_sha256 != original_hash
    assert json.loads(middle.payload_json)['data'][0]['realizedRate'] == '0.00031'
    assert json.loads(kept.payload_json)['data'][0]['realizedRate'] == '0.00021'

    # The 10:00 occurrence captured again is the same receipt, not a fourth.
    again = path.read_bytes()
    adapter.fetch()
    funding = [row for row in adapter.source_capture_status if row['source_id'] == 'okx_funding']
    assert funding[0]['status'] == 'already_present'
    assert funding[0]['capture_id'] == reverted.capture_id
    assert len(_funding_rows(observations, tmp_path, '2026-01-05T00:00:00Z')) == 3
    assert path.read_bytes() == again

    early = observations.funding_asof(restored, '2026-01-02T08:30:00Z')
    mid = observations.funding_asof(restored, '2026-01-02T09:30:00Z')
    late = observations.funding_asof(restored, '2026-01-02T10:30:00Z')
    assert early[0]['settled_rate'] == float('0.00021')
    assert mid[0]['settled_rate'] == float('0.00031')
    assert late[0]['settled_rate'] == float('0.00021')
    assert late[0]['capture_id'] == reverted.capture_id
    assert early[0]['capture_id'] == original_id


def test_receipt_clock_follows_request_completion_and_finality_is_none(tmp_path, monkeypatch):
    http = _Http()
    adapter, observations = _okx(monkeypatch, tmp_path, http)
    frames = adapter.fetch()
    assert 'funding_rate' in frames
    funding = _funding_rows(observations, tmp_path, '2026-03-01T00:00:00Z')
    assert len(funding) == 1
    received = funding.iloc[0].received_at
    _assert_receipt_follows_http(http.events, FUNDING_URL, received)
    assert funding.iloc[0].first_seen == received
    assert funding.iloc[0].fetched_at == received
    # Exact unknown sentinel: the source cannot prove finality, so the field is None.
    assert funding.iloc[0].finality is None
    assert 'finality' not in funding.iloc[0].payload_json
    tampered = funding.iloc[0].to_dict()
    tampered['finality'] = 'unknown'
    with pytest.raises(ValueError):
        observations.checked(tampered)

    taker = observations.load_asof('okx_taker', '2026-03-01T00:00:00Z', root=tmp_path)
    hourly = taker.loc[taker.params_json.str.contains('"period":"1H"')]
    assert len(hourly) == 1
    _assert_receipt_follows_http(http.events, TAKER_URL, hourly.iloc[0].received_at)
    assert hourly.iloc[0].finality is None

    bgeo_adapter, observations = _bgeo(monkeypatch, tmp_path, http)
    http.events.clear()
    bgeo_frames = bgeo_adapter.fetch()
    assert 'funding_rate' in bgeo_frames
    bgeo_rows = observations.load_asof('bgeo_funding', '2026-03-01T00:00:00Z', root=tmp_path)
    assert len(bgeo_rows) == 1
    row = bgeo_rows.iloc[0]
    _assert_receipt_follows_http(http.events, BGEO_URL, row.received_at)
    assert row.finality is None
    retained = json.loads(row.payload_json)[0]
    assert retained['delayed'] is True and retained['message'] == 'delayed'
    assert 'finality' not in retained
    assert row.provider_first_published_at is None


@pytest.mark.parametrize('fault', ['enospc', 'permission'])
def test_okx_failed_persist_keeps_prior_bytes_and_returns_frames(tmp_path, monkeypatch, fault):
    http = _Http()
    http.freeze('2026-01-02T08:00:00Z')
    adapter, observations = _okx(monkeypatch, tmp_path, http)
    adapter.fetch()
    path = observations.capture_path('okx_funding', root=tmp_path)
    before = path.read_bytes()
    prior = _funding_rows(observations, tmp_path, '2026-01-05T00:00:00Z')
    assert len(prior) == 1
    prior_id = prior.iloc[0].capture_id

    http.freeze('2026-01-02T09:00:00Z')
    # Legacy OKX funding frame is the predicted fundingRate, not realizedRate.
    http.predicted = '0.00044'
    http.realized = '0.00055'
    http.hourly = _hours(6, buy='8', sell='1')
    monkeypatch.setattr(observations.fss, 'atomic_write', _raise_fault(fault))
    expected_funding = adapter._funding(False)
    expected_hourly = adapter._taker_volume_hourly()
    expected_daily = adapter._taker_volume()
    frames = adapter.fetch()
    pd.testing.assert_frame_equal(frames['funding_rate'], expected_funding)
    pd.testing.assert_frame_equal(frames['taker_volume_hourly'], expected_hourly)
    pd.testing.assert_frame_equal(frames['taker_volume'], expected_daily)
    assert frames['funding_rate']['funding_rate_okx'].iloc[0] == float('0.00044')
    assert frames['taker_volume_hourly']['taker_buy_vol'].iloc[0] == 8.0
    assert adapter.fetch_result_status(frames) == 'stale'
    assert adapter.source_capture_status
    assert {row['status'] for row in adapter.source_capture_status} == {'unavailable'}
    assert all('capture_id' not in row for row in adapter.source_capture_status)
    assert {row['error_type'] for row in adapter.source_capture_status} == {'ValueError'}
    assert path.read_bytes() == before
    assert not path.with_suffix(path.suffix + '.tmp').exists()
    survived = _funding_rows(observations, tmp_path, '2026-01-05T00:00:00Z')
    assert list(survived.capture_id) == [prior_id]
    assert '0.00044' not in survived.iloc[0].payload_json
    assert json.loads(survived.iloc[0].payload_json)['data'][0]['realizedRate'] == '0.00021'


@pytest.mark.parametrize('fault', ['enospc', 'permission'])
def test_bgeo_failed_persist_keeps_prior_bytes_and_returns_frames(tmp_path, monkeypatch, fault):
    http = _Http()
    http.freeze('2026-01-03T00:00:00Z')
    adapter, observations = _bgeo(monkeypatch, tmp_path, http)
    adapter.fetch()
    path = observations.capture_path('bgeo_funding', root=tmp_path)
    before = path.read_bytes()
    prior = observations.load_asof('bgeo_funding', '2026-01-05T00:00:00Z', root=tmp_path)
    assert len(prior) == 1

    http.freeze('2026-01-03T01:00:00Z')
    http.bgeo = [_bgeo_row('0.0007')]
    monkeypatch.setattr(observations.fss, 'atomic_write', _raise_fault(fault))
    expected = adapter._fetch_metric('funding-rate', 'funding_rate', adapter.cfg['window_start'])
    frames = adapter.fetch()
    pd.testing.assert_frame_equal(frames['funding_rate'], expected)
    assert float(frames['funding_rate']['funding_rate_fundingRate'].iloc[0]) == float('0.0007')
    assert adapter.fetch_result_status(frames) == 'stale'
    assert {row['status'] for row in adapter.source_capture_status} == {'unavailable'}
    assert all('capture_id' not in row for row in adapter.source_capture_status)
    assert {row['error_type'] for row in adapter.source_capture_status} == {'ValueError'}
    assert path.read_bytes() == before
    survived = observations.load_asof('bgeo_funding', '2026-01-05T00:00:00Z', root=tmp_path)
    assert len(survived) == 1
    assert survived.iloc[0].capture_id == prior.iloc[0].capture_id
    assert '0.0007' not in survived.iloc[0].payload_json
    assert json.loads(survived.iloc[0].payload_json)[0]['fundingRate'] == '-0.0001'


def _hourly_frame(triplets: list) -> pd.DataFrame:
    frame = pd.DataFrame(triplets, columns=['ts', 'sell_vol', 'buy_vol'])
    frame['ts'] = pd.to_datetime(pd.to_numeric(frame['ts']), unit='ms')
    frame['taker_buy_vol'] = pd.to_numeric(frame['buy_vol'])
    frame['taker_sell_vol'] = pd.to_numeric(frame['sell_vol'])
    return frame.set_index('ts')[['taker_buy_vol', 'taker_sell_vol']].sort_index()


def _hourly_captures(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for record in frame.to_dict('records'):
        if json.loads(record['params_json']).get('period') == '1H':
            rows.append(record)
    return pd.DataFrame(rows)


def test_asof_consumers_exclude_later_received_rows(tmp_path, monkeypatch):
    from engine import btc_intraday_cvd as cvd

    signature = inspect.signature(cvd.compute)
    assert signature.parameters['sig_df'].default is None
    assert signature.parameters['as_of'].kind is inspect.Parameter.KEYWORD_ONLY

    early_hours = _hours(30, buy='3', sell='1', start='2026-01-01')
    later_hours = early_hours + _hours(24, buy='1', sell='10', start='2026-01-02 06:00')
    http = _Http()
    http.hourly = early_hours
    http.freeze('2026-01-02T05:00:01Z')
    adapter, observations = _okx(monkeypatch, tmp_path, http)
    adapter.fetch()

    http.hourly = later_hours
    http.realized = '0.00031'
    http.freeze('2026-01-03T06:00:00Z')
    adapter.fetch()

    early_cut = '2026-01-02T05:00:01Z'
    just_before_late = '2026-01-03T05:59:59Z'
    late_cut = '2026-01-03T06:00:00Z'
    early_funding = _funding_rows(observations, tmp_path, early_cut)
    before_late = _funding_rows(observations, tmp_path, just_before_late)
    late_funding = _funding_rows(observations, tmp_path, late_cut)
    assert len(early_funding) == 1
    assert len(before_late) == 1
    assert len(late_funding) == 2
    assert list(before_late.capture_id) == list(early_funding.capture_id)
    assert observations.funding_asof(late_funding, early_cut)[0]['settled_rate'] == float('0.00021')
    assert observations.funding_asof(late_funding, just_before_late)[0]['settled_rate'] == float('0.00021')
    assert observations.funding_asof(late_funding, late_cut)[0]['settled_rate'] == float('0.00031')
    # The later receipt revises the same settlement timestamp; it stays on disk.
    assert early_funding.iloc[0].capture_id in set(late_funding.capture_id)

    early_taker = _hourly_captures(observations.load_asof('okx_taker', early_cut, root=tmp_path))
    late_taker = _hourly_captures(observations.load_asof('okx_taker', late_cut, root=tmp_path))
    assert len(early_taker) == 1 and len(late_taker) == 2
    early_payload = json.loads(early_taker.iloc[0].payload_json)['data']
    late_only = late_taker.loc[~late_taker.capture_id.isin(early_taker.capture_id)]
    assert len(late_only) == 1
    late_payload = json.loads(late_only.iloc[0].payload_json)['data']
    assert len(early_payload) == 30 and len(late_payload) == 54
    early_frame = _hourly_frame(early_payload)
    full_frame = _hourly_frame(late_payload)
    assert len(early_frame) == 30 and len(full_frame) == 54

    holder = {'frame': full_frame}

    def _read(group, name):
        if group == 'okx' and name == 'taker_volume_hourly':
            return holder['frame']
        return None

    monkeypatch.setattr(cvd.store, 'read', _read)
    label_cut = '2026-01-02T05:00:00Z'
    on_full = cvd.compute(sig_df=None, as_of=label_cut)
    holder['frame'] = early_frame
    on_visible = cvd.compute(sig_df=None, as_of=label_cut)
    holder['frame'] = full_frame
    on_late = cvd.compute(sig_df=None, as_of=late_cut)

    assert on_full['stored_rows'] == 30
    assert on_full['n_hours'] == 30
    assert on_full['asof'] == str(early_frame.index[-1])
    assert on_full['net_flow_24h_native'] == on_visible['net_flow_24h_native'] == 48.0
    assert on_full['cvd_native'] == on_visible['cvd_native'] == 60.0
    assert on_full['causally_qualified'] is False
    assert on_late['stored_rows'] == 54
    assert on_late['n_hours'] == 54
    assert on_late['net_flow_24h_native'] == -216.0
    assert on_late['asof'] != on_full['asof']
    assert pd.Timestamp(on_full['asof']) < pd.Timestamp('2026-01-02 06:00:00')
