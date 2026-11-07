"""Regression tests for the offline R16 research example; not product tests.

These test whether comparison prerequisites apply to every text-bearing output.
No native source, permission, financial, identity or publication owner is invoked.
"""
import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'materials_r16_review_target', ROOT / 'R16_CHANGE_CONTENT_EXERCISE_2026-09-24.py')
TARGET = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TARGET)
BASE = json.loads((ROOT / 'R16_CHANGE_CONTENT_CASES_2026-09-24.json').read_text())['base']


def example(path, public=False):
    case = copy.deepcopy(BASE)
    if path == 'background':
        case['item']['source_time'] = '2030-03-10T09:00:00Z'
    elif path == 'correction':
        case['item']['corrects'] = 'fixture-r1'
    if public:
        case['context']['surface'] = 'public_brief'
        case['item']['fixture_permissions']['public_summary'] = True
        case['item']['public_text'] = 'The fictional result exceeded an earlier comparison.'
    return case


class ComparisonGuardTests(unittest.TestCase):
    def assert_refused(self, case, reason):
        before = copy.deepcopy(case)
        result = TARGET.assess(case)
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(result['reason'], reason)
        self.assertIsNone(result['text'])
        self.assertIsNone(result['evidence_ref'])
        self.assertEqual(case, before)
        for flag in ('production_admitted', 'can_rank', 'can_notify'):
            self.assertIs(result[flag], False)

    def each_presentation(self):
        for path in ('current', 'background', 'correction'):
            for public in (False, True):
                yield path, public, example(path, public)

    def test_surprise_without_comparison_refused_on_every_presentation(self):
        for path, public, case in self.each_presentation():
            with self.subTest(path=path, public=public):
                case['item'].update(claim_type='consensus_surprise', comparison='none',
                                    baseline_kind='none', baseline_ref=None, baseline_time=None)
                self.assert_refused(case, 'consensus_baseline_required')

    def test_missing_reference_refused_on_every_presentation(self):
        for path, public, case in self.each_presentation():
            with self.subTest(path=path, public=public):
                case['item'].update(claim_type='consensus_surprise', baseline_kind='consensus',
                                    baseline_ref=None)
                self.assert_refused(case, 'baseline_missing')

    def test_non_prior_baseline_refused_on_every_presentation(self):
        for path, public, case in self.each_presentation():
            with self.subTest(path=path, public=public):
                case['item']['baseline_time'] = case['item']['source_time']
                self.assert_refused(case, 'baseline_not_prior')

    def test_unknown_baseline_time_refused_on_every_presentation(self):
        for path, public, case in self.each_presentation():
            with self.subTest(path=path, public=public):
                case['item']['baseline_time'] = None
                self.assert_refused(case, 'baseline_time_unknown')

    def test_incomparable_input_refused_on_every_presentation(self):
        for path, public, case in self.each_presentation():
            with self.subTest(path=path, public=public):
                case['item']['comparison'] = 'not_comparable'
                self.assert_refused(case, 'comparison_unqualified')

    def test_valid_comparison_keeps_its_presentation_and_permissions(self):
        expected = {'current': ('eligible_context', 'economic_change'),
                    'background': ('background', 'newly_learned_old_source'),
                    'correction': ('eligible_context', 'correction')}
        for path, public, case in self.each_presentation():
            with self.subTest(path=path, public=public):
                case['item'].update(claim_type='consensus_surprise', baseline_kind='consensus')
                before = copy.deepcopy(case)
                result = TARGET.assess(case)
                self.assertEqual((result['status'], result['kind']), expected[path])
                self.assertIsNotNone(result['text'])
                if public:
                    self.assertIsNone(result['evidence_ref'])
                    self.assertEqual(result['text'], case['item']['public_text'])
                self.assertEqual(case, before)
                self.assertNotIn('decision_snapshot', result)

    def test_noncomparative_correction_needs_no_fabricated_consensus(self):
        for public in (False, True):
            with self.subTest(public=public):
                case = example('correction', public)
                case['item'].update(comparison='none', baseline_kind='none',
                                    baseline_ref=None, baseline_time=None)
                result = TARGET.assess(case)
                self.assertEqual((result['status'], result['kind']),
                                 ('eligible_context', 'correction'))

    def test_permissions_still_precede_comparison_detail(self):
        case = example('background', True)
        case['item'].update(claim_type='consensus_surprise', comparison='none')
        case['item']['fixture_permissions']['public_summary'] = False
        self.assert_refused(case, 'public_representation_not_approved')

    def test_exact_repeat_still_emits_no_content(self):
        case = copy.deepcopy(BASE)
        case['item'].update({key: case['prior'][key] for key in TARGET.PRIOR})
        result = TARGET.assess(case)
        self.assertEqual(result['status'], 'no_delta')
        self.assertIsNone(result['text'])
        self.assertIsNone(result['evidence_ref'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
