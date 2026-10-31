"""Full market-state consumer proof; synthetic observations, no policy/ledger IO.

CN_PROFILE's actual component readers are used with a declared no-tape fixture.
Separate harness profiles enable existing independent guards ONLY to exercise
composition; that is not a claim those guards are enabled on the CN product.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import replace
import importlib
import json
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from RRU_FORCE_APPLICABILITY_TESTS_2026_09_09 import sample

class FullConsumerTests(unittest.TestCase):
    def setUp(self):
        from engine import market_state_cn
        # Mirror fresh module import binding after installing the in-memory source.
        self.cn = importlib.reload(market_state_cn)
        self.profile = self.cn.CN_PROFILE
        self.latest = dict(date='2026-09-08', conditions=dict(roro=dict(roro_state='risk-on')),
                           risk_radar=sample())
        self.assertIs(self.profile.radar_override, a.market_state._radar_override_intl)

    def run_consumer(self, profile=None, alerts=None):
        saved = deepcopy(self.latest)
        with patch.object(a.market_state, '_rr_scorecard_track', return_value=None), \
             patch.object(a.recovery, '_liquidity_catalysts', return_value=[]), \
             patch.object(a.recovery, '_market_catalysts', return_value=None):
            result = a.market_state.market_state_snapshot(self.latest, frame=None,
                       alerts=alerts, profile=profile or self.profile)
        self.assertIsNotNone(result, 'Full consumer must return a usable result')
        self.assertEqual(self.latest, saved, 'Consumer must not mutate input or policy evidence')
        return result

    def test_actual_cn_profile_preserves_measured_score_for_unpromoted_reading(self):
        result = self.run_consumer()
        self.assertEqual((result['raw_score'], result['score']), (78, 78))
        self.assertEqual(result['score_source'], 'blend')
        self.assertEqual(result['overrides'], [])
        self.assertFalse(result['radar']['binding'])

    def test_actual_cn_profile_preserves_legacy_authorized_ceiling(self):
        self.latest['risk_radar'] = sample(False)
        result = self.run_consumer()
        self.assertEqual((result['raw_score'], result['score']), (78, 26))
        self.assertEqual(result['score_source'], 'radar_ceiling')
        self.assertTrue(result['radar']['binding'])
        self.assertEqual(result['score_caps'][-1]['limit'], 26)

    def test_missing_current_radar_does_not_remove_the_measured_component(self):
        self.latest['risk_radar'].update(state=None, top_score=None)
        self.latest['risk_radar']['composition'].update(status='UNAVAILABLE', score_current=False)
        result = self.run_consumer()
        self.assertEqual(result['score'], result['raw_score'])
        self.assertEqual(result['components'][0]['key'], 'risk')
        self.assertFalse(result['radar']['can_force'])

    def test_actual_cn_profile_does_not_gain_harness_override_authority(self):
        self.assertEqual(self.profile.overrides, frozenset())
        self.latest['conditions']['systemic_stress'] = {'state': 'acute'}
        result = self.run_consumer(alerts=[{'severity': 'act'}])
        self.assertEqual(result['score'], 78)
        self.assertEqual(result['overrides'], [])

def independent_case(kind, limit):
    def test(self):
        profile = replace(self.profile, overrides=frozenset({'alert_act', 'new_regime', 'stress_band', 'dislocation'}))
        alerts = [{'severity': 'act'}] if kind == 'alert' else []
        if kind == 'stress': self.latest['conditions']['systemic_stress'] = {'state': 'acute'}
        if kind == 'regime': self.latest['transition_state'] = 'NEW_REGIME'
        if kind == 'dislocation': self.latest['dislocation'] = dict(dislocation_active=True, verdict='stand_aside')
        result = self.run_consumer(profile, alerts)
        self.assertEqual(result['score'], limit)
        self.assertEqual([v['kind'] for v in result['overrides']], [kind])
        self.assertNotIn('radar_ceiling', [v['kind'] for v in result['score_caps']])
    return test

for kind, limit in (('stress', 41), ('dislocation', 41), ('alert', 59), ('regime', 59)):
    setattr(FullConsumerTests, 'test_independent_harness_' + kind + '_guard_survives', independent_case(kind, limit))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--original-consumer', action='store_true')
    original = parser.parse_args().original_consumer
    paths = set(candidate.bundle) | {'engine/market_state_cn.py'}
    before = {p:(a.ROOT/p).read_bytes() if (a.ROOT/p).exists() else None for p in paths}
    a.apply_bundle(candidate.bundle)
    text = a.committed('engine/market_state.py') if original else candidate.edited['engine/market_state.py']
    exec(compile(text, 'engine/market_state.py', 'exec'), a.market_state.__dict__)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(FullConsumerTests))
    unchanged = all(((a.ROOT/p).read_bytes() if (a.ROOT/p).exists() else None)==v for p,v in before.items())
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        original_consumer=original, source_unchanged=unchanged, full_consumer=True,
        full_pipeline=False, synthetic_only=True, independent_guards_use_harness_profile=True)))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
