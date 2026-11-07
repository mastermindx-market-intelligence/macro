"""Bounded dated reference intake for the existing stock-library producer.

Run inside the existing engine reference-refresh binding. One explicitly named
pilot (MU), at most 20 sequential requests and no retry/redirect/alternate key.
A refusal stops the capture; incomplete evidence never replaces the prior file.
This does not collect bars, run an identity protocol or publish site artifacts.
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.liquidity_profile import _expected_sessions
from engine.liquidity_currency import qualify_currency
from lib.massive_ticker import artifact_relative_path
from scripts.stock_liquidity_profile import read_profile

PILOT_TICKERS = ('MU',)
MAX_RESPONSE_BYTES = 131072


def capture(ticker: str, *, data_root: Path, client, get, clock=lambda: datetime.now(timezone.utc)) -> dict:
    # The caller never receives credentials in returned data or exceptions.
    now = clock()
    if ticker not in PILOT_TICKERS:
        return {'status': 'NOT_ADMITTED', 'requests_sent': 0}
    try:
        origin = urlsplit(client.base)
        admitted_origin = (origin.scheme == 'https'
                           and origin.hostname in {'api.polygon.io', 'api.massive.com'}
                           and origin.port in (None, 443)
                           and not (origin.username or origin.password or origin.query or origin.fragment)
                           and origin.path in ('', '/'))
    except (TypeError, ValueError):
        admitted_origin = False
    if not client.enabled() or not admitted_origin:
        return {'status': 'SOURCE_NOT_CONFIGURED', 'requests_sent': 0}
    profile = read_profile(ticker, data_root=data_root, recorded_at=now)
    if profile['reason'] not in (None, 'CURRENCY_NOT_QUALIFIED'):
        return {'status': 'RAW_SOURCE_NOT_QUALIFIED', 'reason': profile['reason'], 'requests_sent': 0}
    sessions = _expected_sessions(date.fromisoformat(profile['expected_session']), 20)
    dest = data_root / 'stock_currency' / artifact_relative_path(ticker).with_suffix('.json')
    if profile['status'] == 'READ_OK':
        return {'status': 'EXISTING_WINDOW_QUALIFIED', 'requests_sent': 0}
    # Only exact, already-qualified observations may be reused. A changed window
    # gets a complete bounded capture; there is no unverified rolling-cache merge.
    receipt = {'schema': 'liquidity_currency_observations.v1', 'ticker': ticker, 'observations': []}
    sent = 0
    for day in sessions:
        path = f'/v3/reference/tickers/{ticker}'
        start = clock()
        sent += 1
        try:
            with get(client.base.rstrip('/') + path,
                     params={'date': day.isoformat(), 'apiKey': client.key},
                     timeout=(8, 20), allow_redirects=False, stream=True) as response:
                if response.status_code != 200:
                    return {'status': 'PROVIDER_STOP', 'http_status': response.status_code, 'requests_sent': sent}
                chunks, size = [], 0
                for chunk in response.iter_content(8192):
                    size += len(chunk)
                    if size > MAX_RESPONSE_BYTES:
                        return {'status': 'RESPONSE_OVER_BOUND', 'requests_sent': sent}
                    chunks.append(chunk)
                body = b''.join(chunks).decode('utf-8')
                if client.key in body:
                    return {'status': 'RESPONSE_SECRET_REFUSED', 'requests_sent': sent}
            end = clock()
            obj = json.loads(body)
            if (obj.get('status') != 'OK' or obj.get('results', {}).get('ticker') != ticker
                    or str(obj.get('results', {}).get('currency_name', '')).upper() != 'USD'):
                return {'status': 'SOURCE_CONTRACT_REFUSED', 'requests_sent': sent}
        except Exception:
            # requests exceptions may contain the query-string key. Never return
            # exception text, response URLs, headers or credentials.
            return {'status': 'SOURCE_READ_FAILED', 'requests_sent': sent}
        receipt['observations'].append({
            'session': day.isoformat(), 'request_path': path, 'request_params': {'date': day.isoformat()},
            'request_started_at': start.isoformat(), 'response_received_at': end.isoformat(),
            'http_status': 200, 'response_sha256': hashlib.sha256(body.encode()).hexdigest(), 'response_body': body,
        })
    if qualify_currency(receipt, ticker=ticker, sessions=sessions, recorded_at=clock()) is None:
        return {'status': 'CAPTURE_NOT_QUALIFIED', 'requests_sent': sent}
    if dest.is_symlink() or dest.parent.is_symlink():
        return {'status': 'DESTINATION_NOT_REGULAR', 'requests_sent': sent}
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(receipt, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n')
    tmp.replace(dest)
    return {'status': 'CAPTURED', 'requests_sent': sent, 'source_asof': sessions[-1].isoformat()}


def main() -> int:
    from types import SimpleNamespace
    from lib import config
    import requests
    # The same existing polygon config and provisioned aliases used by the
    # native stock-reference client; do not import its retired options engine.
    settings = config.load()["polygon"]
    key = (config.secret(settings.get("api_key_env", "POLYGON_API_KEY"))
           or config.secret("MASSIVE_API_KEY"))
    client = SimpleNamespace(base=settings["base_url"].rstrip("/"), key=key,
                             enabled=lambda: bool(key))
    statuses = {ticker: capture(ticker, data_root=config.data_dir(), client=client, get=requests.get)
                for ticker in PILOT_TICKERS}
    print(json.dumps(statuses, sort_keys=True))
    return 0 if all(s['status'] in {'CAPTURED', 'EXISTING_WINDOW_QUALIFIED'} for s in statuses.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
