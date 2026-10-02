"""Verify exact Forex review inputs, never browser or production acceptance."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
CASES = ('matched', 'different_dates', 'unavailable', 'raw_fallback')
FONTS = {'.woff', '.woff2', '.ttf', '.otf', '.ttc', '.eot'}


class ForexReviewInputChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert (HERE / 'candidate.zip').is_file(), 'No exact-source Forex review input has been produced'
        cls.source = json.loads((HERE / 'SOURCE.json').read_text())
        cls.spec = json.loads((HERE / 'SPEC.json').read_text())
        with zipfile.ZipFile(HERE / 'candidate.zip') as archive:
            cls.names = archive.namelist()
            cls.members = {name: archive.read(name) for name in cls.names}
            cls.crc_error = archive.testzip()

    def test_exact_safe_archive_and_no_font_binaries(self):
        self.assertIsNone(self.crc_error)
        self.assertEqual(len(self.names), len(set(self.names)))
        for name in self.names:
            path = PurePosixPath(name)
            self.assertFalse(path.is_absolute()); self.assertNotIn('..', path.parts)
            self.assertNotIn(path.suffix.lower(), FONTS)
        for name, record in self.source['rendered_files'].items():
            self.assertEqual(len(self.members[name]), record['bytes'], name)
            self.assertEqual(hashlib.sha256(self.members[name]).hexdigest(), record['sha256'], name)
        self.assertEqual(set(self.source['rendered_files']), {name for name in self.names if name.startswith('cases/')})

    def test_source_and_each_complete_forex_page_identity(self):
        self.assertEqual(self.source['source_commit'], 'ac79e07634ec3903167969d2922d411d3969817d')
        self.assertEqual(set(self.source['cases']), set(CASES))
        for name in CASES:
            data = self.members[f'cases/{name}/site/forex.html']
            self.assertEqual(hashlib.sha256(data).hexdigest(), self.spec['expected_html_sha256'][name])

    def test_required_user_states_are_real_rendered_template_output(self):
        from bs4 import BeautifulSoup
        for name in CASES:
            soup = BeautifulSoup(self.members[f'cases/{name}/site/forex.html'], 'html.parser')
            panel = soup.select_one('#fx-movement-evidence')
            self.assertEqual(len(soup.select('#fx-movement-evidence')), 1)
            self.assertIn('The pairs', soup.get_text())
            self.assertIn(self.spec['fixed_build_label'], soup.select_one('.meta-foot').get_text())
            self.assertIn('Source freshness unknown', panel.get_text())
            self.assertIn('来源新鲜度未知', panel.get_text())
            self.assertIsNone(panel.select_one('script'))
            self.assertIsNone(panel.select_one('input'))
            if name == 'unavailable':
                self.assertIn('Movement evidence unavailable', panel.get_text())
                self.assertEqual(panel.select('[data-currency]'), [])
            elif name == 'different_dates':
                self.assertIsNotNone(panel.select_one('[data-movement-comparison="withheld"]'))
                self.assertIn('different calculation dates', panel.get_text())
                self.assertIn('−0.19%', panel.get_text())
                self.assertIsNotNone(panel.select_one('time[datetime="2026-09-22"]'))
            elif name == 'matched':
                self.assertIsNotNone(panel.select_one('[data-movement-comparison="calculation_dates_match"]'))
                self.assertIn('The currency fell', panel.get_text())
                self.assertIn('Relative momentum is above', panel.get_text())
            else:
                self.assertIsNotNone(panel.select_one('[data-adjustment-status="raw_fallback"]'))
                self.assertIn('Unadjusted fallback move', panel.get_text())
                self.assertIn('No dollar effect was removed', panel.get_text())

    def test_source_clocks_and_acceptance_are_not_invented(self):
        for flag in ['browser_navigation_performed', 'server_started', 'screenshot_acceptance', 'production_deployment']:
            self.assertIs(self.source[flag], False)
        self.assertIn('NOT_PROVEN', self.source['runtime_dynamic_network_closure'])
        for name in CASES:
            snapshot = json.loads(self.members[f'cases/{name}/kinematics.json'])
            self.assertEqual(snapshot['freshness'], 'unknown')
            self.assertIs(snapshot['metric_dates_available'], False)
            for row in snapshot['rows']:
                self.assertTrue(all(value is None for value in row['observed_at'].values()))

    def test_static_resources_are_accounted_for_and_icons_present(self):
        for name, case in self.source['cases'].items():
            self.assertEqual(case['unresolved_direct_static_resources'], [])
            self.assertIn(f'cases/{name}/site/apple-touch-icon.png', self.members)
            self.assertEqual(case['component_css_sha256'], 'b9b73065256ea260677d35b1212d6a37f8453cee4923e4aefeeb5adb93dffd90')
        self.assertGreater(len(self.source['font_assets_not_bundled']), 0)

    def test_embedded_rebuild_material_matches_the_published_input(self):
        for name in ['README.md', 'SOURCE.json', 'SPEC.json', 'prepare.py', 'verify_input.py']:
            self.assertEqual(self.members[name], (HERE / name).read_bytes(), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
