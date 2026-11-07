"""Candidate contract shape/consistency tests, not native owner acceptance."""
from copy import deepcopy
import json
import unittest
from fixtures import candidate_example
from contract_check import validate_json


class CandidateContractConformance(unittest.TestCase):
    def setUp(self):
        self.example = candidate_example()

    def validate(self):
        return validate_json(json.dumps(self.example, allow_nan=False))

    def test_01_valid_synthetic_shape(self):
        self.assertEqual(self.validate(), self.example)

    def test_02_authority_escalation_refused(self):
        self.example['authority']['may_size'] = True
        with self.assertRaises(ValueError): self.validate()

    def test_03_unavailable_cannot_carry_numeric_value(self):
        self.example['observations'][0]['return'].update(status='UNAVAILABLE', reasons=['MISSING_PRICE'])
        with self.assertRaises(ValueError): self.validate()

    def test_04_semantic_only_cannot_manufacture_series(self):
        self.example['status'] = 'SEMANTIC_ONLY'; self.example['reasons'] = ['NO_COHORT']
        with self.assertRaises(ValueError): self.validate()

    def test_05_numeric_zero_is_not_missing(self):
        self.example['observations'][0]['return']['value'] = 0.0
        result = self.validate()
        self.assertIsInstance(result, dict)
        self.assertEqual(result['observations'][0]['return']['value'], 0.0)

    def test_06_pit_missing_selection_clock_refused(self):
        self.example['observations'][0]['selection_cutoff'] = None
        with self.assertRaises(ValueError): self.validate()

    def test_07_pit_selection_after_holding_start_refused(self):
        self.example['observations'][0]['selection_cutoff'] = '2026-09-03T00:00:00Z'
        with self.assertRaises(ValueError): self.validate()

    def test_08_outcome_after_selection_is_allowed_at_measurement_cutoff(self):
        result = self.validate()
        self.assertIsInstance(result, dict)
        self.assertLess(result['observations'][0]['selection_cutoff'], result['observations'][0]['interval_end'])

    def test_09_outcome_after_measurement_cutoff_refused(self):
        self.example['request']['measurement_cutoff'] = '2026-09-03T19:59:59Z'
        with self.assertRaises(ValueError): self.validate()

    def test_10_observed_count_cannot_exceed_eligible(self):
        self.example['metrics']['hhi']['coverage']['observed_count'] = 4
        with self.assertRaises(ValueError): self.validate()

    def test_11_count_ratio_must_match_denominator(self):
        self.example['metrics']['hhi']['coverage']['count_fraction'] = .9
        with self.assertRaises(ValueError): self.validate()

    def test_12_nan_json_refused(self):
        text = json.dumps(self.example).replace('105.0', 'NaN')
        with self.assertRaises(ValueError): validate_json(text)

    def test_13_overflow_json_number_refused(self):
        text = json.dumps(self.example).replace('105.0', '1e999')
        with self.assertRaises(ValueError): validate_json(text)

    def test_14_duplicate_json_keys_refused(self):
        text = json.dumps(self.example).replace('"contract_status": "PROPOSED"', '"contract_status": "PROPOSED", "contract_status": "PROPOSED"')
        with self.assertRaises(ValueError): validate_json(text)

    def test_15_extra_authority_or_identity_store_refused(self):
        self.example['membership_store'] = []
        with self.assertRaises(ValueError): self.validate()

    def test_16_corrected_revision_needs_reason(self):
        self.example['calculation']['supersedes_ref'] = 'fixture:revision:prior'
        with self.assertRaises(ValueError): self.validate()

    def test_17_unknown_whole_price_basis_cannot_be_ready_total_return(self):
        self.example['series_spec']['price_basis'] = None
        with self.assertRaises(ValueError): self.validate()

    def test_18_house_curation_ref_does_not_replace_price_ref(self):
        self.example['owner_receipt_refs']['prices'] = []
        with self.assertRaises(ValueError): self.validate()

    def test_19_explicit_semantic_only_unavailable_example(self):
        self.example['status'] = 'SEMANTIC_ONLY'; self.example['reasons'] = ['NO_QUALIFIED_COHORT']
        self.example['descriptor'].update(cohort_ref=None, relationship='SEMANTIC_ONLY', factor_class='microtheme')
        self.example['observations'] = []; self.example['metrics'] = {}
        self.assertEqual(self.validate(), self.example)

    def test_20_null_level_after_gap_cannot_claim_fully_ready(self):
        self.example['observations'][0]['index_level'].update(value=None, status='UNAVAILABLE', reasons=['BROKEN_CHAIN'])
        with self.assertRaises(ValueError): self.validate()

    def test_21_duplicate_return_interval_refused(self):
        self.example['observations'].append(deepcopy(self.example['observations'][0]))
        with self.assertRaises(ValueError): self.validate()

    def test_22_current_roster_requires_frozen_snapshot(self):
        self.example['request']['history_mode'] = 'CURRENT_ROSTER'
        with self.assertRaises(ValueError): self.validate()

    def test_23_schema_validation_does_not_authenticate_fixture_rights(self):
        result = self.validate()
        self.assertIsInstance(result, dict)
        self.assertEqual(result['owner_receipt_refs']['rights'], ['fixture:rights:unverified-placeholder'])
        # Deliberate: shape-valid refs remain unverified. This is not an admission validator.


if __name__ == '__main__': unittest.main()
