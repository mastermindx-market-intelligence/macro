"""Temporary C3 witness: actual builder + real Jinja, synthetic market inputs.

Reuses the incumbent R12 fixture's market/writer isolation. Changes only its
stubbed rendering boundary and dollar VM in memory; no owner file is edited.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from scripts import build_forex as BF
from engine import forex_alerts

ROOT = Path.cwd()
OUT = Path(__file__).resolve().parent
NOW = '2026-10-17T09:05:00+00:00'
MARKET_DATE = '2026-10-16'
TRACKED = ['engine/forex_signals.py', 'engine/forex_alerts.py',
           'engine/forex_dollar.py', 'scripts/build_forex.py',
           'scripts/build_macro_context.py', 'engine/neuralweb/mastermind_context.py',
           'templates/forex.html.j2', 'tests/test_forex_context_bus.py']


def hashes():
    return {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in TRACKED}


spec = importlib.util.spec_from_file_location('c3_existing_fx_fixture', ROOT / 'tests/test_forex_context_bus.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
real_main = BF.main
real_vm = BF.dollar_vm
real_environment = BF.Environment
full_cfg = copy.deepcopy(BF.config.load()['forex'])
legacy_pairs = fixture._fake_pairs
bound_before = hashes()


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        value = datetime.fromisoformat(NOW)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


class TimestampProxy:
    def __call__(self, *args, **kwargs):
        return pd.Timestamp(*args, **kwargs)

    @staticmethod
    def now(tz=None):
        value = pd.Timestamp(NOW)
        return value.tz_convert(tz) if tz else value.tz_localize(None)


class PandasProxy:
    Timestamp = TimestampProxy()

    def __getattr__(self, key):
        return getattr(pd, key)


receipts = []
for case in ('known_zero_risk', 'missing_risk'):
    location = OUT / case
    captures = []
    page_paths = []
    missing = case == 'missing_risk'
    index = pd.bdate_range(end=MARKET_DATE, periods=300)
    market = pd.DataFrame({
        'smile_regime': None if missing else 'US growth premium',
        'risk_off': np.nan if missing else 0.0,
        'dollar_roc': 0.01, 'broad': 100.0, 'dxy': 104.0,
        'dollar_day_z': 0.0,
        'smile_unavailable_reason': 'missing_or_invalid_risk_or_direction' if missing else None,
        'smile_last_confirmed': 'US growth premium',
        'smile_last_confirmed_asof': pd.Timestamp('2026-10-15'),
    }, index=index)
    event = {'id': 'forex:EURUSD:momentum:2026-10-16T16:00:accelerating',
             'ts': '2026-10-16T16:00:00+00:00', 'type': 'momentum', 'asset': 'EURUSD',
             'severity': 'medium', 'headline': 'Synthetic momentum change',
             'headline_zh': '合成动量变化', 'anchor': 'EURUSD',
             'context': {'from': 'steady', 'to': 'accelerating'}}

    class CapturingEnvironment(real_environment):
        def get_template(self, name, *args, **kwargs):
            template = super().get_template(name, *args, **kwargs)
            if name != 'forex.html.j2':
                return template

            class RenderBoundary:
                def render(self, **context):
                    captures.append(context)
                    return template.render(**context)

            return RenderBoundary()

    def temporary_page_sink(path, html):
        path = Path(path)
        assert path.is_relative_to(location), path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')
        page_paths.append(path)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(BF, 'datetime', FixedDateTime)
        mp.setattr(BF, 'pd', PandasProxy())
        mp.setattr(fixture, '_dol_frame', lambda *args, **kwargs: market.copy(deep=True))
        mp.setattr(fixture, '_r12_cfg', lambda: copy.deepcopy(full_cfg))

        def renderable_pairs():
            rows = legacy_pairs()
            # The old no-op template fixture omitted a real required field.
            rows[0]['conviction']['factors'][0]['value'] = 0.4
            return rows

        mp.setattr(fixture, '_fake_pairs', renderable_pairs)

        def controlled_main():
            # The incumbent fixture sets its old stub VM/renderer immediately
            # before main. Restore real production projection/render functions.
            mp.setattr(BF, 'dollar_vm', real_vm)
            mp.setattr(BF, 'Environment', CapturingEnvironment)
            mp.setattr(BF, 'write_page', temporary_page_sink)
            mp.setattr(forex_alerts, 'rebuild', lambda *args, **kwargs: [copy.deepcopy(event)])
            return real_main()

        mp.setattr(BF, 'main', controlled_main)
        snapshot, unused_stub_contexts = fixture._r12_build_fixture(location, mp, fixture._r12_table())

    assert not unused_stub_contexts, 'the obsolete stub renderer ran'
    assert len(captures) == len(page_paths) == 1
    html = page_paths[0].read_text(encoding='utf-8')
    match = re.search(r'<script id="forex-decision-context" type="application/json">(.*?)</script>', html, re.S)
    assert match, 'real rendered HTML does not embed the decision record'
    embedded = json.loads(match.group(1))
    projected = captures[0]['decision_context']
    assert embedded == snapshot['decision_context'] == projected
    json.dumps(snapshot, allow_nan=False)
    assert snapshot['asof'] == MARKET_DATE
    assert projected['assembled_at'] == NOW
    assert projected['changes'][0]['id'] == event['id']
    assert projected['changes'][0]['context'] == event['context']
    assert projected['pairs'][0]['pair'] == 'EURUSD'
    assert projected['pairs'][0]['literal_quote'] == 1.082
    assert projected['pairs'][0]['calculated_asof'] == MARKET_DATE
    assert projected['dependencies']['EURUSD:literal_quote']['source_available_at'] is None
    assert projected['capabilities']['EURUSD:price_close_4h']['allowed'] is False
    assert projected['current_read']['available'] is (not missing)
    assert ('class="smile-dot"' in html) is (not missing)
    if missing:
        assert snapshot['risk'] is snapshot['risk_off'] is snapshot['regime'] is None
        assert 'Current regime unavailable' in html and 'Risk context unavailable' in html
    else:
        assert snapshot['risk_off'] == 0.0 and snapshot['risk'] == 'risk-on'
    assert not list(location.rglob('*.jsonl')), 'a lifecycle/ledger writer ran'
    receipts.append({'case': case, 'status': 'PASS', 'html': str(page_paths[0]),
                     'snapshot': str(location / 'data/forex/latest.json'),
                     'html_bytes': len(html.encode()),
                     'snapshot_id': projected['snapshot_id'],
                     'current_available': projected['current_read']['available'],
                     'strict_json': True, 'shared_record_parity': True,
                     'known_market_date': MARKET_DATE, 'controlled_build_time': NOW,
                     'event_id_retained': event['id'], 'ledger_writes': 0})

bound_after = hashes()
report = {'status': 'PASS', 'cases': receipts, 'source_hashes_before': bound_before,
          'source_hashes_after': bound_after, 'candidate_stable': bound_before == bound_after,
          'scope': 'actual main assembly + real Jinja + isolated snapshot write; market engines stubbed',
          'production_io': False, 'native_page_writer_tested': False}
(OUT / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
