"""Synthetic force-compatibility proof through actual functions and source assignments.

Runner probes execute the exact assignment AST, not an entire production pipeline.
No ledger, feed, policy store, real position, or production writer is used.
"""
from __future__ import annotations
import ast
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import RRU_COMPOSITION_ACCEPTANCE_2026_09_08 as a
import RRU_COMPOSITION_BUILD_BUNDLE_2026_09_08 as candidate

RUNNERS = ('engine/intl_run.py', 'scripts/build_china.py', 'scripts/build_hk.py',
           'scripts/build_canada.py', 'scripts/build_china_risk_state.py')

def override(payload, overrides=None):
    entries = [] if overrides is None else overrides
    with patch.object(a.market_state, '_rr_scorecard_track', return_value=None), \
         patch.object(a.recovery, 'assess', return_value=None):
        return a.market_state._radar_override_intl(payload, entries)

def sample(composition=True):
    out = dict(market='cn', state='risk-off', top_score=99, can_force=True,
               forward_log=dict(market='cn', n_graded=200, can_force=True))
    if composition:
        out['composition'] = dict(method='available_group_weight.v1', score_current=True,
            status='COMPLETE', calibration_status='unreviewed_corrected_construction')
    return out

class ForceTests(unittest.TestCase):
    def test_foreign_grant_cannot_override_named_policies_or_mutate_inputs(self):
        policy = dict(policy_id='fixture-only-existing-policy', action='NO_ADD',
                      expiry='2026-10-01', authority_basis='fixture')
        latest = dict(risk_radar=sample(), risk_envelope=dict(policies=[policy]))
        entries = [dict(kind='independent_policy', policy=deepcopy(policy))]
        saved, original_entries = deepcopy(latest), deepcopy(entries)
        rd = override(latest, entries)
        self.assertFalse(rd['can_force'])
        self.assertFalse(rd['binding'])
        self.assertIsNone(rd['ceiling'])
        self.assertEqual(entries, original_entries)
        self.assertEqual(latest, saved)
        self.assertTrue(latest['risk_radar']['forward_log']['can_force'])

    def test_reported_binding_object_cannot_bypass_effective_projection(self):
        out = sample()
        out['authority'] = dict(tier='binding', can_force=True, reason='old-fixture')
        saved = deepcopy(out)
        rd = override(dict(risk_radar=out))
        self.assertFalse(rd['authority']['can_force'])
        self.assertNotEqual(rd['authority']['tier'], 'binding')
        self.assertEqual(out, saved)
        html = a.render(rd)
        self.assertNotIn('Binding guard', html)
        self.assertNotIn('仅调整仓位', html)

def metadata_case(value):
    def test(self):
        out = sample()
        out['composition'] = deepcopy(value)
        saved = deepcopy(out)
        rd = override(dict(risk_radar=out))
        self.assertFalse(rd['can_force'])
        self.assertFalse(rd['binding'])
        self.assertEqual(out, saved)
    return test

for name, value in dict(null=None, empty={}, list=[], boolean=True,
        unknown={'method': 'future.v99'}, reviewed_claim={'method': 'available_group_weight.v1',
        'calibration_status': 'reviewed', 'status': 'COMPLETE', 'score_current': True}).items():
    setattr(ForceTests, 'test_modern_' + name + '_is_not_legacy_permission', metadata_case(value))

def producer_case(profile):
    def test(self):
        sub = a.fixture(profile)
        for values in sub.values():
            values.iloc[-1] = .99
        out = a.compute(profile, sub)
        self.assertIn(out['state'], ('caution', 'elevated', 'risk-off'))
        out['can_force'] = True
        rd = override(dict(risk_radar=out))
        self.assertFalse(rd['can_force'])
        self.assertFalse(rd['binding'])
    return test

for profile in a.radar.PROFILES.values():
    setattr(ForceTests, 'test_producer_' + profile.key, producer_case(profile))

def runner_case(path, modern):
    def test(self):
        raw = getattr(a, 'RUNNER_SOURCES', {}).get(path) or a.committed(path)
        nodes = [n for n in ast.walk(ast.parse(raw)) if isinstance(n, ast.Assign)
                 and len(n.targets) == 1 and isinstance(n.targets[0], ast.Subscript)
                 and isinstance(n.targets[0].slice, ast.Constant)
                 and n.targets[0].slice.value == 'can_force']
        self.assertEqual(len(nodes), 2, 'Every selected runner has exactly two grant assignments')
        for i, node in enumerate(nodes):
            for proposed in (False, True):
                with self.subTest(path=path, assignment=i, grant=proposed):
                    snap = sample(modern)
                    snap['forward_log']['can_force'] = proposed
                    rec = dict(risk_radar=snap)
                    ns = dict(rec=rec, latest=rec, _latest_nightly=rec, latest_live=rec,
                              _sc=snap['forward_log'], sc=snap['forward_log'],
                              can_force=proposed, _rra=a.radar_audit,
                              risk_radar_intl_audit=a.radar_audit)
                    code = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
                    exec(compile(code, path, 'exec'), ns)
                    self.assertEqual(snap['can_force'], False if modern else proposed)
                    self.assertEqual(snap['forward_log']['can_force'], proposed)
    return test

for i, path in enumerate(RUNNERS):
    for modern in (True, False):
        setattr(ForceTests, f'test_runner_{i}_' + ('modern' if modern else 'legacy'),
                runner_case(path, modern))

def legacy_test(self):
    for state, ceiling in (('caution', 56), ('elevated', 38), ('risk-off', 26)):
        out = sample(False)
        out['state'] = state
        saved = deepcopy(out)
        rd = override(dict(risk_radar=out))
        self.assertTrue(rd['binding'])
        self.assertEqual(rd['ceiling'], ceiling)
        self.assertNotIn('reported_can_force', rd, 'Keep legacy projection free of new provenance fields')
        self.assertEqual(out, saved)
ForceTests.test_legacy_ceiling_and_source_preserved = legacy_test

def record_display_test(self):
    out = sample()
    rd = override(dict(risk_radar=out))
    html = a.render(rd)
    self.assertIn('Earlier construction record', html)
    self.assertNotIn('moving the verdict', html)
    self.assertNotIn('参与定调', html)
    self.assertTrue(out['forward_log']['can_force'])
ForceTests.test_prior_record_is_not_current_force_claim = record_display_test

if __name__ == '__main__':
    from pathlib import Path
    paths = set(candidate.bundle) | set(RUNNERS)
    before = {p: (a.ROOT / p).read_bytes() if (a.ROOT / p).exists() else None for p in paths}
    a.apply_bundle(candidate.bundle)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ForceTests))
    unchanged = all(((a.ROOT / p).read_bytes() if (a.ROOT / p).exists() else None) == v for p, v in before.items())
    print(json.dumps(dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                         source_unchanged=unchanged, synthetic_only=True, full_pipeline=False)))
    raise SystemExit(0 if result.wasSuccessful() and unchanged else 1)
