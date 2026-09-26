"""Synthetic actual-audit/tuner cohort tests; no ledger IO or policy effects."""
from __future__ import annotations
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import json
import argparse
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate
from engine import risk_radar_intl_audit as audit, risk_radar_intl_tune as tuner

ABSENT = object()
MODERN = {'method': 'available_group_weight.v1', 'status': 'COMPLETE',
          'calibration_status': 'unreviewed_corrected_construction'}

def rows(n=50, composition=ABSENT):
    result = []
    for i, date in enumerate(a.pd.bdate_range('2026-05-01', periods=n)):
        alert = i % 5 == 0
        hit = alert if composition is ABSENT else not alert
        r = {'asof': str(date.date()), 'state': 'risk-off' if alert else 'calm',
             'alert': alert, 'graded': {'any_dd5_within_h21': hit,
             'outcome': ('true_positive' if hit else 'false_positive') if alert else ('calm_dd' if hit else 'calm_quiet'),
             'fwd_dd': {h: -.06 if hit else .01 for h in audit.HORIZONS}}}
        if composition is not ABSENT:
            r['composition'] = deepcopy(composition)
        result.append(r)
    return result

class MemorySink:
    def __init__(self):
        self.payloads = []
    def write_text(self, text):
        self.payloads.append(text)
        return len(text)

class CohortTests(unittest.TestCase):
    def invoke(self, method, fixture):
        before = deepcopy(fixture)
        sink = MemorySink()
        with ExitStack() as stack:
            stack.enter_context(patch.object(audit, '_path', return_value=Path('SYNTHETIC_UNUSED')))
            stack.enter_context(patch.object(audit, '_read', return_value=fixture))
            stack.enter_context(patch.object(audit, '_write', side_effect=AssertionError('No ledger write')))
            stack.enter_context(patch.object(audit, '_log_can_force_governance', side_effect=AssertionError('No grant write')))
            stack.enter_context(patch.object(tuner, '_calib_path', return_value=sink))
            stack.enter_context(patch.object(tuner, '_log_review', return_value=None))
            stack.enter_context(patch.object(tuner, '_append_governance_a6', return_value=None))
            p = a.radar.CN_PROFILE
            stack.enter_context(patch.object(tuner.R, '_calib', return_value=deepcopy(
                {'prob_cal': p.prob_cal, 'prob_base': p.prob_base})))
            result = (tuner.tune(p) if method == 'tune' else
                      audit.scorecard('cn', log_governance=False) if method == 'scorecard' else
                      audit.realized_odds('cn'))
        self.assertEqual(fixture, before, 'Cohort selection must not rewrite issued rows')
        return result, sink.payloads

    def test_legacy_scorecard_control_keeps_actual_counts(self):
        result, _ = self.invoke('scorecard', rows())
        self.assertEqual((result['n_graded'], result['n_alerts']), (50, 10))
        self.assertEqual(result['base_rate_dd5_h21'], .2)
        self.assertEqual(result['realized_odds']['risk-off']['h21'], 1.0)

    def test_modern_only_cannot_supply_legacy_eligibility(self):
        result, _ = self.invoke('scorecard', rows(composition=MODERN))
        self.assertEqual(result['n_graded'], 0)
        self.assertFalse(result['can_force'])

    def test_mixed_scorecard_keeps_legacy_statistics(self):
        old, _ = self.invoke('scorecard', rows())
        mixed, _ = self.invoke('scorecard', rows() + rows(100, MODERN))
        for key in ('n_graded', 'base_rate_dd5_h21', 'n_alerts', 'can_force',
                    'by_state', 'realized_odds', 'recent_mistakes'):
            self.assertEqual(mixed[key], old[key], key)
        self.assertEqual(mixed.get('excluded_composition_rows'), 100)

    def test_realized_odds_share_the_legacy_cohort(self):
        old, _ = self.invoke('odds', rows())
        mixed, _ = self.invoke('odds', rows() + rows(100, MODERN))
        self.assertEqual(mixed, old)
        modern, _ = self.invoke('odds', rows(composition=MODERN))
        self.assertEqual(modern, {})

    def test_modern_only_cannot_start_legacy_tuning(self):
        result, writes = self.invoke('tune', rows(100, MODERN))
        self.assertEqual(result['status'], 'accruing')
        self.assertEqual(result['n_graded'], 0)
        self.assertEqual(writes, [])

    def test_mixed_tuner_sample_and_brier_share_legacy_cohort(self):
        old, old_writes = self.invoke('tune', rows())
        mixed, mixed_writes = self.invoke('tune', rows() + rows(100, MODERN))
        for key in ('status', 'n_graded', 'brier', 'realized'):
            self.assertEqual(mixed.get(key), old.get(key), key)
        self.assertEqual(mixed.get('excluded_composition_rows'), 100)
        self.assertEqual(len(mixed_writes), len(old_writes))
        for left, right in zip(old_writes, mixed_writes):
            old_payload, mixed_payload = json.loads(left), json.loads(right)
            for key in ('prob_cal', 'n_graded', 'brier_before', 'brier_after'):
                self.assertEqual(old_payload[key], mixed_payload[key], key)

    def test_explicit_invalid_composition_never_becomes_implicit_legacy(self):
        for value in (None, {}, [], True, {'method': 'future_unknown'}):
            with self.subTest(composition=value):
                result, _ = self.invoke('scorecard', rows(composition=value))
                self.assertEqual(result['n_graded'], 0)

if __name__ == '__main__':
    before = {p: (a.ROOT / p).read_bytes() for p in (
        'engine/risk_radar_intl_audit.py', 'engine/risk_radar_intl_tune.py')}
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    if not args.baseline:
        a.apply_bundle(candidate.bundle)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CohortTests))
    unchanged = all((a.ROOT / p).read_bytes() == raw for p, raw in before.items())
    print(json.dumps({'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
                     'source_unchanged': unchanged, 'ledger_io': False, 'synthetic_only': True}))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
