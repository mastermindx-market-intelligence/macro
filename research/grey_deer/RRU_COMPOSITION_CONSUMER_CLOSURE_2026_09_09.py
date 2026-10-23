"""Adversarial consumer-contract tests; synthetic input, no production writes.

Freeze: unavailable calibration must not appear in active forecast/sizing fields.
Independent observed catalysts must survive an unavailable composite comparison.
These assertions specify release requirements, not authorization to alter policies.
"""
from __future__ import annotations
import json
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate

class ConsumerClosure(unittest.TestCase):
    def setUp(self):
        self.profile = a.radar.CN_PROFILE
        self.out = a.compute(self.profile, a.fixture(self.profile))

    def test_complete_unreviewed_card_is_descriptive_not_an_all_clear(self):
        self.assertEqual(self.out['composition']['status'], 'COMPLETE')
        self.assertEqual(self.out['composition']['calibration_status'],
                         'unreviewed_corrected_construction')
        original_state = self.out.get('state')
        html = a.render(a.project(self.out))
        self.assertIn('Descriptive reading', html)
        self.assertNotIn('✅', html)
        self.assertNotIn('rrx-calm', html)
        self.assertEqual(self.out.get('state'), original_state)

    def test_raw_forecast_is_not_current_under_unreviewed_calibration(self):
        self.assertFalse(self.out.get('drawdown_prob'),
                         'Active forecast field must not carry the old calibration')

    def test_raw_sizing_is_not_current_under_unreviewed_calibration(self):
        self.assertIsNone(self.out.get('gross_factor'),
                          'Old sizing cannot be hidden only in the card projection')

    def test_raw_trajectory_does_not_publish_unreviewed_forecast_odds(self):
        trajectory = self.out.get('trajectory') or {}
        self.assertTrue(trajectory, 'Control: actual trajectory must be reached')
        self.assertIsNone(trajectory.get('odds_now'))

    def test_actual_sleeve_consumer_withholds_unreviewed_sizing(self):
        with patch.object(a.radar, 'snapshot', return_value=self.out):
            chip = a.radar.cn_sleeve_chip()
        self.assertIsNone(chip.get('sleeve_factor'))
        self.assertNotIn('Validated forward-drawdown',
                         (chip.get('passport') or {}).get('note', ''))

    def test_incomparable_recovery_preserves_independent_catalysts(self):
        sub = a.fixture(self.profile)
        next(iter(sub.values())).iloc[-1] = a.np.nan
        out = a.compute(self.profile, sub)
        cats = [{'key': 'fixture_liquidity', 'fresh': True}]
        with patch.object(a.recovery, '_liquidity_catalysts', return_value=cats), \
             patch.object(a.recovery, '_market_catalysts', return_value=None):
            view = a.recovery.assess({'risk_radar': out}) or {}
        self.assertFalse(out['composition']['comparison_comparable'])
        self.assertEqual(view.get('catalysts'), cats)
        self.assertFalse(view.get('turn_confirmed', False))

    def test_legacy_us_projection_still_preserves_existing_fields(self):
        out = {'state': 'elevated', 'top_score': 88, 'can_force': True,
               'gross_factor': .78, 'drawdown_prob': {'h21': .4}, 'market': 'us'}
        rd = a.project(out)
        self.assertEqual((rd['dd21'], rd['gross'], rd['can_force']), (.4, .78, True))

if __name__ == '__main__':
    def file_state(p):
        path = a.ROOT / p
        return path.read_bytes() if path.exists() else None
    before = {p: file_state(p) for p in a.PATHS}
    a.apply_bundle(candidate.bundle)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ConsumerClosure)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged = all(file_state(p) == raw for p, raw in before.items())
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
                      'errors': len(result.errors), 'source_unchanged': unchanged,
                      'synthetic_only': True, 'candidate_not_installed': True}))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
