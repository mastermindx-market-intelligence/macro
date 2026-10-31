"""Canonical account reuse; synthetic service observations, no network."""
import json
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path

from lib.frozen_options_account import frozen_options_account

ID = '10000000-0000-4000-8000-000000000001'
AT = '2026-10-21T14:00:00Z'


def test_canonical_me_and_unlimited_overlay_not_parallel_policy(monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, 'urlopen', lambda *a, **k: (_ for _ in ()).throw(AssertionError('network')))
    from engine import alert_delivery_drain as drain
    from app import main, billing
    user = {'id': ID, 'email': 'synthetic@example.invalid', 'user_metadata': {
        'alert_email_optin': True, 'alert_categories': ['options_exposure_node'], 'unrelated_secret': 'not-in-protocol'}}
    monkeypatch.setattr(drain, 'fetch_user_record', lambda principal: (drain.READ_OK, user))
    monkeypatch.setattr(billing, 'read_entitlement', lambda principal: {
        'tier': 'free', 'features': [], 'status': 'none', 'current_period_end': None, 'source': 'stripe'})
    monkeypatch.setattr(main, '_brain_module', lambda: SimpleNamespace(get_user_quotas=lambda *a, **k: {'tier': 'unlimited', 'quotas': {'private': 1}}))
    result = frozen_options_account(ID, AT)
    assert result['account']['me']['tier'] == 'unlimited'  # actual me callable overlay
    assert result['principal'] == ID and result['evaluationAt'] == AT
    assert result['account']['user']['user_metadata'] == {
        'alert_email_optin': True, 'alert_categories': ['options_exposure_node']}
    text = json.dumps(result)
    for private in ('synthetic@example.invalid', 'unrelated_secret', 'chat_budget', 'private', 'Bearer'):
        assert private not in text
    user['user_metadata'].update(alert_email_optin=' TRUE ', alert_categories=[' OPTIONS_EXPOSURE_NODE '])
    assert frozen_options_account(ID, AT)['account']['user']['user_metadata'] == {
        'alert_email_optin': True, 'alert_categories': ['options_exposure_node']}
    user['user_metadata']['alert_categories'].append('future')
    assert frozen_options_account(ID, AT)['account']['user']['user_metadata']['alert_categories'][-1] == 'future'
    monkeypatch.setattr(drain, 'fetch_user_record', lambda principal: (drain.READ_OK, {**user, 'id': 'other'}))
    monkeypatch.setattr(main, 'me', lambda **kwargs: (_ for _ in ()).throw(AssertionError('must not evaluate mismatched account')))
    assert frozen_options_account(ID, AT) is None
    monkeypatch.setattr(drain, 'fetch_user_record', lambda principal: (drain.READ_UNAVAILABLE, None))
    assert frozen_options_account(ID, AT) is None


def test_cli_malformed_input_never_reads_account():
    script = Path(__file__).parents[1] / 'scripts/frozen_options_account.py'
    for raw in (b'{}', b'{broken', b'\xff', b'x' * 4097):
        result = subprocess.run([sys.executable, str(script)], input=raw, capture_output=True, timeout=12)
        assert result.returncode == 2
        assert json.loads(result.stdout)['kind'] == 'unavailable'
