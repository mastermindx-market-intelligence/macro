"""Pure forward-entry serialization checks; no ledger is opened or advanced."""
from __future__ import annotations
import json
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from engine import risk_radar_intl_audit as audit

class ConstructionSerialization(unittest.TestCase):
    def test_corrected_entry_must_retain_composition_and_calibration_identity(self):
        out = a.compute(a.radar.CN_PROFILE, a.fixture(a.radar.CN_PROFILE))
        self.assertEqual(out['composition']['method'], 'available_group_weight.v1')
        with patch.object(audit, '_path', side_effect=AssertionError('No ledger IO')), \
             patch.object(audit, '_read', side_effect=AssertionError('No ledger IO')):
            entry = audit._entry_from_snapshot(out)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.get('composition'), out['composition'],
                         'Current serializer loses construction and applicability before grading')

    def test_legacy_entry_still_serializes_without_new_composition_claims(self):
        out = {'asof': '2026-09-08', 'market': 'cn', 'state': 'risk-off', 'top_score': 99}
        entry = audit._entry_from_snapshot(out)
        self.assertEqual(entry['state'], 'risk-off')
        self.assertTrue(entry['alert'])
        self.assertNotIn('composition', entry)

def modern_case(name):
    def test(self):
        q = {'score_current': True, 'status': 'COMPLETE', 'method': 'available_group_weight.v1'}
        if name == 'null': q = None
        elif name == 'list': q = []
        elif name == 'empty': q = {}
        elif name == 'old': q['score_current'] = False
        elif name == 'truthy': q['score_current'] = 1
        elif name == 'unavailable': q['status'] = 'UNAVAILABLE'
        elif name == 'nonfinite': q['bad'] = float('nan')
        with patch.object(audit, '_path', side_effect=AssertionError('No ledger IO')), patch.object(audit, '_read', side_effect=AssertionError('No ledger IO')):
            entry = audit._entry_from_snapshot({'asof': '2026-09-08', 'state': 'risk-off', 'composition': q})
        self.assertIsNone(entry, 'Explicit invalid modern metadata must not become a legacy entry')
    return test

for name in ('null', 'list', 'empty', 'old', 'truthy', 'unavailable', 'nonfinite'):
    setattr(ConstructionSerialization, 'test_modern_' + name, modern_case(name))

def copy_test(self):
    q = {'score_current': True, 'status': 'PARTIAL', 'method': 'available_group_weight.v1', 'groups': [{'missing': ['credit']}]}
    entry = audit._entry_from_snapshot({'asof': '2026-09-08', 'state': 'watch', 'composition': q})
    self.assertIn('composition', entry)
    self.assertEqual(entry['composition'], q)
    q['groups'][0]['missing'].append('fx')
    self.assertEqual(entry['composition']['groups'][0]['missing'], ['credit'])

ConstructionSerialization.test_valid_partial_metadata_is_copied_without_aliasing = copy_test

if __name__ == '__main__':
    a.apply_bundle(candidate.bundle)
    source = a.ROOT / 'engine/risk_radar_intl_audit.py'
    before = source.read_bytes()
    result = unittest.TextTestRunner(verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ConstructionSerialization))
    unchanged = source.read_bytes() == before
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures),
        'errors': len(result.errors), 'source_unchanged': unchanged,
        'ledger_io': False, 'synthetic_only': True}))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
