"""Additional adversarial cases; synthetic observations and actual consumer code."""
from __future__ import annotations
import argparse
import copy
import json
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a

class CompositionEdges(unittest.TestCase):
    def test_partial_card_has_no_calm_checkmark(self):
        p = a.radar.PROFILES['cn']
        sub = a.fixture(p)
        sub[next(iter(sub))].iloc[-1] = a.np.nan
        rd = a.project(a.compute(p, sub))
        html = a.render(rd)
        self.assertIn('Partial reading', html)
        self.assertNotIn('✅', html)
        self.assertNotIn('rrx-calm', html)

    def test_snapshot_exception_remains_explicitly_unavailable(self):
        with patch.object(a.radar, '_read', side_effect=ValueError('synthetic unavailable source')):
            out = a.radar.snapshot(a.radar.PROFILES['cn'])
        self.assertEqual(out.get('composition', {}).get('status'), 'UNAVAILABLE')
        self.assertIsNone(out.get('state'))
        self.assertIn('Reading unavailable', a.render(a.project(out)))

    def test_invalid_profile_is_not_a_calm_default(self):
        out = a.radar.snapshot(None)
        self.assertEqual(out.get('composition', {}).get('status'), 'UNAVAILABLE')

    def test_all_input_gap_is_not_lost_by_dropping_unscored_dates(self):
        p = a.radar.PROFILES['cn']
        sub = a.fixture(p)
        for s in sub.values():
            s.iloc[-15] = a.np.nan
        q = a.compute(p, sub)['composition']
        self.assertEqual(q['status'], 'COMPLETE')
        self.assertFalse(q['comparison_comparable'])
        self.assertEqual(q['comparison_incomplete_sessions'], 1)

    def test_comparison_recovers_after_its_window_clears(self):
        p = a.radar.PROFILES['cn']
        sub = a.fixture(p)
        for s in sub.values():
            s.iloc[-80:-70] = a.np.nan
        q = a.compute(p, sub)['composition']
        self.assertTrue(q['comparison_comparable'])
        self.assertEqual(q['comparison_incomplete_sessions'], 0)

    def test_old_score_date_is_retained_as_history_not_current(self):
        p = a.radar.PROFILES['cn']
        sub = a.fixture(p)
        for s in sub.values():
            s.iloc[-5:] = a.np.nan
        out = a.compute(p, sub)
        self.assertEqual(out['composition']['score_asof'], str(a.INDEX[-6].date()))
        self.assertFalse(out['composition']['score_current'])
        self.assertIsNone(out.get('top_score'))

    def test_profile_group_keys_and_weights_are_well_formed(self):
        for p in a.radar.PROFILES.values():
            self.assertEqual(len({g[0] for g in p.comp_legs}), len(p.comp_legs))
            self.assertTrue(all(g[2] > 0 for g in p.comp_legs))
            self.assertTrue(all(len(set(g[1])) == len(g[1]) for g in p.comp_legs))

    def test_projection_does_not_change_source_authority_or_input(self):
        p = a.radar.PROFILES['cn']
        out = a.compute(p, a.fixture(p))
        out.update(state='elevated', can_force=True,
                   authority={'tier': 'binding', 'can_force': True, 'reason': 'fixture'})
        saved = copy.deepcopy(out)
        rd = a.project(out)
        self.assertEqual(out, saved)
        self.assertTrue(rd['can_force'])
        self.assertEqual(rd['authority'], saved['authority'])
        self.assertIsNone(rd['dd21'])

if __name__ == '__main__':
    import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
    a.apply_bundle(candidate.bundle)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CompositionEdges)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures),
                         errors=len(result.errors), synthetic_only=True)))
    raise SystemExit(0 if result.wasSuccessful() else 1)
