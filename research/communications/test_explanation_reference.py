"""Tests of the offline reference-pack checker, not the application."""
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import unittest
ROOT=Path(__file__).parent

class ReferenceChecks(unittest.TestCase):
    def setUp(self):
        self.pack=json.loads((ROOT/'COMMUNICATIONS_A1_EXPLANATION_SCENARIOS_2026-09-24.json').read_text())
        module=ROOT/'replay_communications_explanation_cases.py'
        self.assertTrue(module.is_file(), 'offline reference checker has not been written')
        spec=importlib.util.spec_from_file_location('reference_checker',module)
        self.mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.mod)
    def test_reference_pack_passes(self):
        r=self.mod.evaluate(self.pack)
        self.assertEqual(r['scenarios_checked'],20)
        self.assertEqual(r['panels_checked'],4)
        self.assertEqual(r['production_tests'],0)
    def test_missing_prior_does_not_erase_current(self):
        t=set(self.pack['baseline_tokens'])-{'prior_source'}
        out=self.mod.emissions(self.pack,t)
        self.assertIn('reported_level',out); self.assertNotIn('period_change',out)
    def test_denied_entitlement_erases_private_output(self):
        self.assertEqual(self.mod.emissions(self.pack,set(self.pack['baseline_tokens']),denied=True),set())
    def test_fake_live_identity_fails(self):
        p=deepcopy(self.pack);p['panels'][0]['native_issuer_id']='invented'
        with self.assertRaisesRegex(ValueError,'native identity'):
            self.mod.evaluate(p)
    def test_source_scope_drift_fails(self):
        p=deepcopy(self.pack);p['panels'][1]['headline_measures'][0]['reporting_scope']='issuer consolidated'
        with self.assertRaisesRegex(ValueError,'frozen numeric or scope'):
            self.mod.evaluate(p)
    def test_wrong_period_fails(self):
        p=deepcopy(self.pack);p['panels'][0]['headline_measures'][0]['prior_period']=['2026-01-01','2026-03-31']
        with self.assertRaisesRegex(ValueError,'period'):
            self.mod.evaluate(p)
    def test_three_company_coverage_fails(self):
        p=deepcopy(self.pack);p['panels'].pop()
        with self.assertRaisesRegex(ValueError,'roster'):
            self.mod.evaluate(p)
    def test_final_guidance_cannot_be_assumed(self):
        p=deepcopy(self.pack);p['panels'][0]['expectation']['final_pre_result_history']='complete'
        with self.assertRaisesRegex(ValueError,'history'):
            self.mod.evaluate(p)
    def test_incomplete_translation_fails(self):
        p=deepcopy(self.pack);p['panels'][0]['headline']['zh']=''
        with self.assertRaisesRegex(ValueError,'bilingual'):
            self.mod.evaluate(p)
    def test_unbounded_copy_fails(self):
        p=deepcopy(self.pack);p['panels'][0]['interpretation']['en']='x'*241
        with self.assertRaisesRegex(ValueError,'240'):
            self.mod.evaluate(p)
    def test_false_author_annotation_remains_blind_spot(self):
        # The checker can accept a false but internally consistent annotation.
        out=self.mod.emissions(self.pack,set(self.pack['baseline_tokens']))
        self.assertIn('original_guide_delivery',out)
        # No language claim: the tokens contain no actual source text to verify.
        self.assertFalse(hasattr(self.mod,'parse_transcript'))
if __name__=='__main__': unittest.main(verbosity=2)
