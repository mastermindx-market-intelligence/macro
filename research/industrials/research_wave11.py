"""Research-only characterization and arithmetic; not an application gate or fix.

The cache probe re-expresses the path-keyed cache boundary observed in native
engine/theme_graph/rights.py. It is NOT an import/execution of that complete
module, a production rights check, or evidence of a live disclosure incident.
Only temporary local files are changed. PyYAML is an existing local dependency.
"""
from __future__ import annotations
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import yaml

@lru_cache(maxsize=8)
def fixture_registry(path: str) -> dict:
    """Re-express the retrieved cache/read boundary for temporary fixtures only."""
    doc = yaml.safe_load(Path(path).read_text(encoding='utf-8')) or {}
    return {str(name): row for name, row in (doc.get('families') or {}).items()
            if isinstance(row, dict)}

class CacheCharacterization(unittest.TestCase):
    def setUp(self):
        fixture_registry.cache_clear()
        self.directory = TemporaryDirectory()
        self.path = Path(self.directory.name) / 'policy.yml'
        self.write('direct_display_ok')

    def tearDown(self):
        fixture_registry.cache_clear()
        self.directory.cleanup()

    def write(self, rights: str):
        self.path.write_text('families:\n  example:\n    rights_class: '+rights+'\n', encoding='utf-8')

    def test_same_path_does_not_automatically_observe_change(self):
        first = fixture_registry(str(self.path))
        self.assertEqual(first.get('example', {}).get('rights_class'), 'direct_display_ok')
        self.write('unresolved')
        second = fixture_registry(str(self.path))
        self.assertEqual(second.get('example', {}).get('rights_class'), 'direct_display_ok')
        self.assertIs(first, second)
        self.assertIn('unresolved', self.path.read_text())

    def test_explicit_cache_clear_reloads_fixture_only(self):
        fixture_registry(str(self.path))
        self.write('unresolved')
        fixture_registry.cache_clear()
        self.assertEqual(fixture_registry(str(self.path)).get('example', {}).get('rights_class'), 'unresolved')

    def test_different_paths_have_distinct_cache_entries(self):
        first = fixture_registry(str(self.path))
        other = self.path.with_name('other.yml')
        other.write_text('families:\n  example:\n    rights_class: internal_only\n')
        second = fixture_registry(str(other))
        self.assertEqual(first.get('example', {}).get('rights_class'), 'direct_display_ok')
        self.assertEqual(second.get('example', {}).get('rights_class'), 'internal_only')

class ArithmeticBoundaryExamples(unittest.TestCase):
    def test_company_contract_matrix_reconciles(self):
        self.assertEqual(68+12, 80)
        self.assertEqual(19+1, 20)
        self.assertEqual(68+12+19+1, 100)

    def test_company_share_is_not_within_segment_share(self):
        # Ratios of rounded disclosures are illustrative, not exact issuer metrics.
        self.assertNotEqual(Fraction(68,100), Fraction(68,68+19))
        self.assertGreater(Fraction(68,68+19), Fraction(68,100))

    def test_quarter_and_half_year_are_distinct(self):
        self.assertNotEqual(80, 78)
        self.assertEqual(Fraction(78-80,80), Fraction(-1,40))
        self.assertEqual(78-80, -2)

    def test_hypothetical_concentration_is_not_contradictory(self):
        # Equal-size quarters are chosen solely as a possibility proof.
        self.assertEqual((Fraction(9,100)+Fraction(11,100))/2, Fraction(10,100))

    def test_paired_adjustment_preserves_pretax(self):
        operating, other, paired = 28022, 15000, 11783
        self.assertEqual(operating+other, (operating+paired)+(other-paired))

if __name__ == '__main__':
    unittest.main(verbosity=2)
