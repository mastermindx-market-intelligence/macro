"""Measured native-cost and reserve integration; all inputs explicitly synthetic."""
from __future__ import annotations
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import unittest

from engine.provider_quota_economics import QuotaEconomicsError, preview_document
from engine.provider_quota_economics_costs import MEASURED_INPUT_SCHEMA, current_measurements

NOW = datetime(2026, 9, 13, 16, tzinfo=timezone.utc)

def at(hours=0):
    return (NOW + timedelta(hours=hours)).isoformat()


def measured_input():
    aliases = ['fable', 'opus']
    resources = [
        {'resource_id': 'shared', 'entitlement_generation': 'synthetic-g1', 'applies_to': aliases,
         'unit': 'credits', 'window_type': 'fixed', 'horizon': 'weekly', 'limit': 100,
         'remaining': 90, 'observed_at': at(), 'valid_until': at(1), 'evidence': 'provider_reported',
         'reset_at': at(9), 'window_seconds': 604800, 'reserves': {}},
        {'resource_id': 'fable-subset', 'entitlement_generation': 'synthetic-g1', 'applies_to': ['fable'],
         'unit': 'credits', 'window_type': 'fixed', 'horizon': 'weekly', 'limit': 50,
         'remaining': 45, 'observed_at': at(), 'valid_until': at(1), 'evidence': 'provider_reported',
         'reset_at': at(9), 'window_seconds': 604800, 'reserves': {}},
        {'resource_id': 'slots', 'entitlement_generation': 'synthetic-host1', 'applies_to': aliases,
         'unit': 'concurrent_sessions', 'window_type': 'instant', 'horizon': 'concurrency', 'limit': 3,
         'remaining': 3, 'observed_at': at(), 'valid_until': at(1), 'evidence': 'exact'},
    ]
    cohort = {'effort': 'high', 'context_band': 'medium', 'rate_generation': 'synthetic-rate1', 'rate_band': 'standard'}
    options = [dict(option_id=alias, provider='claude', model_alias=alias, model_family='claude',
                    costs={r['resource_id']: {'unit': r['unit'], 'amount': 1 if r['unit'] == 'concurrent_sessions' else None}
                           for r in resources if alias in r['applies_to']},
                    duration_seconds=None, marginal_cash=0, permitted=True, harness_ready=True,
                    usage_allowed=True, useful_jobs_per_hour=None) for alias in aliases]
    usage = []
    for alias in aliases:
        for i in range(5):
            for resource in resources:
                if alias not in resource['applies_to'] or resource['unit'] == 'concurrent_sessions':
                    continue
                usage.append(dict(measurement_id=f'{alias}-{i}-{resource["resource_id"]}', revision=1,
                                  attempt_id=f'{alias}-attempt-{i}', provider='claude', model_alias=alias,
                                  task_kind='build', **cohort, resource_id=resource['resource_id'],
                                  entitlement_generation='synthetic-g1', unit='credits', amount=10 if alias == 'fable' else 5,
                                  duration_seconds=300, completed_at=at(-5+i*.5), observed_at=at(-5+i*.5),
                                  accepted=True, attribution='provider_attempt', evidence='provider_reported', retracted=False))
    return dict(schema=MEASURED_INPUT_SCHEMA, as_of=at(), resources=resources, options=options,
                task=dict(kind='build', state='READY', authorized=True, ready_jobs=10,
                          suitability_tiers=[{'tier_id': 'qualified', 'model_aliases': aliases}]),
                policy=dict(burst_cap=3, paid_spend_allowed=False, provider_precedence=[]),
                usage=usage, cohorts={alias: dict(cohort) for alias in aliases},
                calibration=dict(min_samples=3, quantile='.9', safety_factor='1.2',
                                 window_start_at=at(-24), history_complete=True),
                reserve_targets=[dict(resource_id='shared', option_id='fable', fraction='.5', demand_jobs=2, demand_complete=True)])


class QuotaEconomicsMeasuredTests(unittest.TestCase):
    def estimate(self, result, alias='fable', resource='shared'):
        row = next(r for r in result['cost_calibration'] if r['option_id'] == alias)
        return next(r for r in row['resources'] if r['resource_id'] == resource)

    def test_usage_drives_real_preview_and_preserves_authority(self):
        result = preview_document(measured_input())
        self.assertEqual(self.estimate(result)['upper_native_cost'], '12')
        self.assertEqual(self.estimate(result, 'opus')['upper_native_cost'], '6')
        self.assertEqual(result['reserve_proposals'][0]['total_preview_reserve'], '24.000000000000')
        self.assertEqual(result['status'], 'PREVIEW_READY')
        self.assertFalse(result['live_admission'])
        self.assertFalse(result['reserve_proposals'][0]['runtime_reservation_created'])

    def test_revision_correction_changes_forecast_not_historical_input(self):
        doc = measured_input()
        original = copy.deepcopy(doc)
        changed = dict(doc['usage'][0], revision=2, amount=30, observed_at=at(-1))
        doc['usage'].append(changed)
        result = preview_document(doc)
        self.assertEqual(self.estimate(result)['upper_native_cost'], '36')
        self.assertEqual(self.estimate(result)['sample_count'], 5)
        self.assertEqual(original['usage'][0]['amount'], doc['usage'][0]['amount'])

    def test_retraction_does_not_fall_back_to_old_sample(self):
        doc = measured_input()
        doc['usage'].append(dict(doc['usage'][0], revision=2, retracted=True, observed_at=at(-1)))
        result = preview_document(doc)
        self.assertEqual(self.estimate(result)['sample_count'], 4)
        self.assertEqual(result['measurement_exclusions'][doc['usage'][0]['measurement_id']], 'RETRACTED')

    def test_duplicate_delivery_does_not_inflate_samples(self):
        doc = measured_input()
        doc['usage'] += copy.deepcopy(doc['usage'])
        self.assertEqual(self.estimate(preview_document(doc))['sample_count'], 5)

    def test_changed_same_revision_is_refused(self):
        doc = measured_input()
        doc['usage'].append(dict(doc['usage'][0], amount=50))
        with self.assertRaisesRegex(QuotaEconomicsError, 'CONFLICTING_USAGE_REVISION'):
            preview_document(doc)

    def test_revision_identity_and_time_cannot_drift(self):
        for field, value in [('resource_id', 'other'), ('observed_at', at(-6))]:
            doc = measured_input()
            row = dict(doc['usage'][0], revision=2, **{field: value})
            if field == 'observed_at':
                row['completed_at'] = at(-7)
            doc['usage'].append(row)
            with self.assertRaises(QuotaEconomicsError):
                preview_document(doc)

    def test_future_correction_is_not_current_evidence(self):
        doc = measured_input()
        doc['usage'].append(dict(doc['usage'][0], revision=2, amount=50, observed_at=at(1)))
        self.assertEqual(self.estimate(preview_document(doc))['upper_native_cost'], '12')

    def test_ambiguous_shared_usage_is_excluded(self):
        doc = measured_input()
        for row in doc['usage']:
            if row['model_alias'] == 'fable':
                row['attribution'] = 'ambiguous'
        result = preview_document(doc)
        self.assertEqual(result['suggested_option'], 'opus')
        self.assertEqual(self.estimate(result)['sample_count'], 0)
        self.assertEqual(result['reserve_proposals'][0]['reason'], 'UNKNOWN_COST_TARGET_PROTECTED')

    def test_generation_and_native_unit_must_match(self):
        for field, value in [('entitlement_generation', 'old-generation'), ('unit', 'tokens'),
                             ('rate_generation', 'old-rate'), ('rate_band', 'offpeak'),
                             ('effort', 'low'), ('context_band', 'large')]:
            doc = measured_input()
            for row in doc['usage']:
                if row['model_alias'] == 'fable':
                    row[field] = value
            result = preview_document(doc)
            self.assertEqual(self.estimate(result)['sample_count'], 0)
            self.assertEqual(result['suggested_option'], 'opus')

    def test_failures_are_charged_to_useful_output(self):
        doc = measured_input()
        for row in doc['usage']:
            if row['model_alias'] == 'fable' and row['attempt_id'] != 'fable-attempt-0':
                row['accepted'] = False
        estimate = self.estimate(preview_document(doc))
        self.assertEqual(estimate['upper_native_cost'], '60')
        self.assertEqual(estimate['rejected_count'], 4)

    def test_zero_accepted_is_not_free_capacity(self):
        doc = measured_input()
        for row in doc['usage']:
            row['accepted'] = False
        result = preview_document(doc)
        self.assertEqual(result['status'], 'NO_ELIGIBLE_OPTION')
        self.assertEqual(self.estimate(result)['reason'], 'NO_ACCEPTED_OUTCOME')

    def test_partial_history_does_not_invent_throughput(self):
        doc = measured_input()
        doc['calibration']['history_complete'] = False
        result = preview_document(doc)
        self.assertTrue(all(r['useful_jobs_per_hour'] is None for r in result['cost_calibration']))

    def test_unknown_cost_is_explicit_not_a_baseline_fallback(self):
        doc = measured_input()
        doc['usage'] = []
        for row in doc['options']:
            row['costs']['shared']['amount'] = '.001'
        result = preview_document(doc)
        self.assertEqual(result['status'], 'NO_ELIGIBLE_OPTION')
        self.assertIsNone(result['derived_inputs']['options'][0]['costs']['shared']['amount'])

    def test_complete_zero_demand_releases_only_soft_not_hard(self):
        doc = measured_input()
        doc['resources'][0]['reserves'] = {'fable': 8}
        doc['reserve_targets'][0]['demand_jobs'] = 0
        result = preview_document(doc)
        self.assertEqual(result['reserve_proposals'][0]['total_preview_reserve'], '8.000000000000')
        self.assertEqual(result['reserve_proposals'][0]['reason'], 'NO_DEMAND_SOFT_RESERVE_RELEASED')

    def test_partial_zero_demand_protects_target(self):
        doc = measured_input()
        doc['reserve_targets'][0].update(demand_jobs=0, demand_complete=False)
        result = preview_document(doc)
        self.assertEqual(result['reserve_proposals'][0]['total_preview_reserve'], '50.000000000000')

    def test_reserve_is_prorated_under_shared_shortage(self):
        doc = measured_input()
        doc['resources'][0]['remaining'] = 10
        doc['reserve_targets'][0].update(demand_jobs=None, demand_complete=False)
        doc['reserve_targets'].append(dict(resource_id='shared', option_id='opus', fraction='.5', demand_jobs=None, demand_complete=False))
        result = preview_document(doc)
        self.assertEqual(sum(float(r['total_preview_reserve']) for r in result['reserve_proposals']), 10)
        self.assertTrue(all(r['shortage_prorated'] for r in result['reserve_proposals']))

    def test_reserves_do_not_refill_exhausted_shared_parent(self):
        doc = measured_input()
        doc['resources'][0]['remaining'] = 0
        result = preview_document(doc)
        self.assertEqual(result['status'], 'NO_ELIGIBLE_OPTION')
        self.assertEqual(float(result['reserve_proposals'][0]['total_preview_reserve']), 0)

    def test_stale_resource_does_not_get_fresh_reserve_proposal(self):
        doc = measured_input()
        doc['resources'][0].update(observed_at=at(-2), valid_until=at(-1))
        result = preview_document(doc)
        self.assertEqual(result['status'], 'NO_ELIGIBLE_OPTION')
        self.assertEqual(result['reserve_proposals'][0]['status'], 'RESERVE_SOURCE_UNKNOWN_HARD_FLOORS_RETAINED')

    def test_no_quality_or_started_attempt_override(self):
        doc = measured_input()
        doc['task']['suitability_tiers'] = [{'tier_id': 'best', 'model_aliases': ['opus']}]
        self.assertEqual(preview_document(doc)['suggested_option'], 'opus')
        for state in ('STARTED', 'EFFECT_UNKNOWN'):
            doc['task']['state'] = state
            self.assertEqual(preview_document(doc)['status'], 'RECONCILE_EXISTING_ATTEMPT')

    def test_unknown_fields_and_bad_safety_factor_refused(self):
        doc = measured_input()
        doc['calibration']['safety_factor'] = '.9'
        with self.assertRaises(QuotaEconomicsError):
            preview_document(doc)
        doc = measured_input()
        doc['usage'][0]['secret'] = 'must-not-be-accepted'
        with self.assertRaises(QuotaEconomicsError):
            preview_document(doc)

    def test_second_measurement_for_same_attempt_resource_refused(self):
        doc = measured_input()
        doc['usage'].append(dict(doc['usage'][0], measurement_id='duplicate-source-row'))
        with self.assertRaisesRegex(QuotaEconomicsError, 'MULTIPLE_MEASUREMENTS'):
            preview_document(doc)

    def test_inconsistent_cross_resource_outcome_refused(self):
        doc = measured_input()
        doc['usage'][0]['accepted'] = False
        with self.assertRaisesRegex(QuotaEconomicsError, 'INCONSISTENT_ATTEMPT_OUTCOME'):
            preview_document(doc)

    def test_original_input_never_mutated(self):
        doc = measured_input()
        before = copy.deepcopy(doc)
        preview_document(doc)
        self.assertEqual(doc, before)

    def test_real_cli_derives_cost_and_reserve(self):
        cli = Path(__file__).resolve().parents[1] / 'scripts/preview_provider_quota_economics.py'
        proc = subprocess.run([sys.executable, str(cli), '--input', '-'], input=json.dumps(measured_input()),
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(self.estimate(result)['upper_native_cost'], '12')
        self.assertFalse(result['live_admission'])


if __name__ == '__main__':
    unittest.main()
