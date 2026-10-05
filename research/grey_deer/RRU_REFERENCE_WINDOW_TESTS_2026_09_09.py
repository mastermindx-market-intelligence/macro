"""Reference-union membership tests against actual profiles and consumers."""
from __future__ import annotations
import json
import unittest
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate

OBSERVED = []
class ReferenceWindowTests(unittest.TestCase):
    pass

def case_test(profile, case):
    def test(self):
        sub = a.fixture(profile)
        if case == 'outside':
            next(iter(sub.values())).iloc[0] = a.np.nan
        elif case == 'member':
            next(iter(sub.values())).iloc[-100] = a.np.nan
        else:
            for values in sub.values():
                values.iloc[-100] = a.np.nan
        out = a.compute(profile, sub)
        q = out['composition']
        OBSERVED.append({'market': profile.key, 'case': case,
            'comparison_comparable': q['comparison_comparable'],
            'recent_incomplete': q['comparison_incomplete_sessions'],
            'reference_sessions': q.get('comparison_reference_sessions'),
            'reference_incomplete': q.get('comparison_reference_incomplete_sessions')})
        self.assertEqual(q['status'], 'COMPLETE')
        self.assertTrue(q['score_current'])
        self.assertEqual(q['comparison_incomplete_sessions'], 0)
        self.assertEqual(q['comparison_comparable'], case == 'outside',
            'Latest-30 completeness does not establish the ranks reference composition')
        rd = a.project(out)
        self.assertEqual(rd['composition'], q)
        if case != 'outside':
            self.assertFalse((rd.get('recovery') or {}).get('receding', False))
            self.assertIn('Recovery comparison unavailable', a.render(rd))
        self.assertEqual(q['freshness'], 'not_assessed')
        self.assertEqual(q['calibration_status'], 'unreviewed_corrected_construction')
    return test

for profile in a.radar.PROFILES.values():
    for case in ('member', 'all_null', 'outside'):
        setattr(ReferenceWindowTests, f'test_{profile.key}_{case}', case_test(profile, case))

if __name__ == '__main__':
    before = {p: (a.ROOT / p).read_bytes() for p in a.PATHS[:3]}
    a.apply_bundle(candidate.bundle)
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ReferenceWindowTests))
    unchanged = all((a.ROOT / p).read_bytes() == raw for p, raw in before.items())
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'source_unchanged': unchanged,
        'synthetic_only': True, 'cases': OBSERVED}))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
