"""Current finite-policy source join, synthetic receipts only; no acquisition."""
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from engine import intl_inputs
from lib import config
from lib.intl_history_materialization import capture_history_context, describe_history_write
from scripts import build_intl

ROOT = Path(__file__).resolve().parents[1]
CURRENT = '07a2cf4a7958d845969ce0bdf2ef1ab9b127fadfd516883b757c421dbcc11d20'


def settings():
    return yaml.safe_load((ROOT / 'config.yml').read_text())


def receipt_for(source):
    """Genuine helper serialization of explicitly synthetic, non-economic rows."""
    frame = pd.DataFrame({'growth_score': [0.25, -0.5], 'inflation_score': [0.0, 0.75]},
                         index=pd.to_datetime(['2026-01-01', '2026-01-02']))
    context = capture_history_context('JP', source['intl']['countries']['JP'],
                                     source['intl']['engine'], frame, source_root=ROOT)
    sink = BytesIO(); frame.to_parquet(sink)
    materialization = describe_history_write('JP', frame, context, sink.getvalue(),
                                             '2026-01-03T00:00:00Z')
    return {'status': 'ready', 'frame': frame, 'materialization': materialization}


def test_adopted_policy_retains_exact_finite_scope_and_current_input_digest():
    source = settings(); policy = source['intl']['history_publication']
    assert policy == dict(
        status='confirmed', scope='intl-current-reconstruction-score-history-v1',
        decision_ref='https://github.com/mastermindx-market-intelligence/macro/pull/7949#issuecomment-6589273748',
        audience='anonymous-and-registered-intl-html',
        fields=['observation_at', 'growth_score', 'inflation_score'],
        metadata=['artifact_ref', 'read_at', 'method_ref', 'universe_ref'],
        markets=['JP', 'KR', 'TW', 'IN', 'AU', 'GB', 'EZ'],
        input_classes=['configured-native-intl-yahoo', 'configured-native-intl-macro',
                       'configured-native-shared-yahoo'],
        history_kind='current_reconstruction', input_configuration_sha256=CURRENT)
    actual = sha256(json.dumps({key: source['intl'][key] for key in ('countries', 'macro', 'yahoo')},
                              sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    assert actual == CURRENT


def test_current_policy_requires_actual_bound_materialization(monkeypatch):
    source = settings(); monkeypatch.setattr(config, 'load', lambda: source)
    receipt = receipt_for(source); policy = source['intl']['history_publication']
    assert build_intl._history_disclosure_allowed(receipt, 'JP', policy)
    assert not build_intl._history_disclosure_allowed(receipt, 'JP', None)
    for status in ('missing', 'failed', 'invalid', 'empty', 'unknown'):
        assert not build_intl._history_disclosure_allowed({**receipt, 'status': status}, 'JP', policy)
    assert not build_intl._history_disclosure_allowed({'status': 'ready'}, 'JP', policy)
    assert not build_intl._history_disclosure_allowed(receipt, 'US', policy)
    assert not build_intl._history_disclosure_allowed(receipt, 'KR', policy)
    bad = deepcopy(receipt); bad['frame'].iloc[0, 0] = 99
    assert not build_intl._history_disclosure_allowed(bad, 'JP', policy)
    monkeypatch.setattr(config, 'ROOT', ROOT / 'nonexistent-test-source-root')
    assert not build_intl._history_disclosure_allowed(receipt, 'JP', policy)


@pytest.mark.parametrize('key,value', [
    ('status', 'proposed'), ('audience', 'any-public-data'),
    ('fields', ['observation_at', 'growth_score', 'inflation_score', 'raw_series']),
    ('metadata', ['artifact_ref', 'read_at', 'method_ref', 'universe_ref', 'provider_body']),
    ('markets', ['JP', 'KR', 'TW', 'IN', 'AU', 'GB', 'EZ', 'US']),
    ('input_configuration_sha256', '4c4086708c9823025c9e61d38fd19874ca7444fec792eb801443aa4db4a59d24'),
])
def test_widened_or_old_policy_refuses(monkeypatch, key, value):
    source = settings(); monkeypatch.setattr(config, 'load', lambda: source)
    policy = {**source['intl']['history_publication'], key: value}
    assert not build_intl._history_disclosure_allowed(receipt_for(source), 'JP', policy)


def test_whole_config_guard_still_refuses_unused_collector_change(monkeypatch):
    source = settings(); receipt = receipt_for(source)
    policy = deepcopy(source['intl']['history_publication'])
    source['intl']['macro'].setdefault('official_series', {})['GB_bank_rate_official'] = {'provider': 'test-only'}
    monkeypatch.setattr(config, 'load', lambda: source)
    assert not build_intl._history_disclosure_allowed(receipt, 'JP', policy)


def test_actual_macro_frame_does_not_read_four_official_join_columns(monkeypatch):
    source = settings(); monkeypatch.setattr(config, 'load', lambda: source)
    seen = []
    def read(group, column):
        assert group == 'intl_macro'; seen.append(column); return None
    monkeypatch.setattr(intl_inputs.store, 'read', read)
    assert intl_inputs._macro_frame().empty
    assert seen == [f'{market}_{metric}' for market in source['intl']['countries']
                    for metric in intl_inputs._METRICS] + intl_inputs._EXTRAS
    assert not set(seen) & {'GB_bank_rate_official', 'EZ_gdp_yoy_official',
                            'EZ_hicp_yoy_official', 'EZ_current_account_gdp_official'}
