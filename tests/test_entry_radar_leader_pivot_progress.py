"""Synthetic follow-up conformance for one frozen research pivot.

No registered detector, event writer, probability or market-admission claim.
"""
from __future__ import annotations
import copy
import unittest
from test_entry_radar_leader_pivot_descriptor import witness, stock_minute
from test_entry_radar_rs_pullback_phase1 import candidate
from engine.entry_radar.replay import leader_pivot_descriptor as owner
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError, digest


class LeaderPivotProgressTests(unittest.TestCase):
    def api(self):
        self.assertTrue(callable(getattr(owner, 'freeze_pivot_reference', None)),
                        'freeze_pivot_reference is not implemented')
        self.assertTrue(callable(getattr(owner, 'describe_pivot_progress', None)),
                        'describe_pivot_progress is not implemented')

    def fixture(self, decision='2026-10-06T16:10:00Z', expiry='2026-10-06T18:00:00Z'):
        self.api()
        b = witness()
        for row in b['minutes']:
            if row['stream'] == 'stock' and row['start'] >= '2026-10-06T16:00:00Z':
                row.update(open=101.0, high=101.5, low=100.5, close=101.0)
        ref = owner.freeze_pivot_reference(b, 'pivot', tick_size=0.01,
                                          episode_expires_at=expiry)
        b['candidates'].append(candidate('followup', decision))
        return b, ref

    def run_view(self, b, ref, state):
        view = owner.describe_pivot_progress(b, 'followup', reference=ref)
        self.assertEqual(view['state'], state)
        self.assertEqual(view['reference_sha256'], ref['reference_sha256'])
        self.assertFalse(view['source_admitted'])
        self.assertFalse(view['actual_issuance_proven'])
        self.assertFalse(view['detector_registered'])
        self.assertFalse(view['outcomes_computed'])
        self.assertTrue(all(v is False for v in view['authority'].values()))
        self.assertEqual(view['progress_sha256'], digest({k:v for k,v in view.items()
                                                        if k != 'progress_sha256'}))
        return view

    def confirm(self, b, index=151):
        stock_minute(b, index).update(high=102.2, close=102.02)

    def invalidate(self, b, index=153):
        stock_minute(b, index).update(low=98.98)

    def test_reference_freezes_geometry_and_caps_expiry(self):
        b, r = self.fixture()
        self.assertEqual(r['formation']['pivot']['low'], 99.0)
        self.assertEqual(r['formation']['pivot']['high'], 102.0)
        self.assertEqual(r['expires_at'], '2026-10-06T17:00:00Z')
        self.assertEqual(r['first_minute_start'], '2026-10-06T16:00:00Z')
        self.assertEqual(r['confirmation_level'], '102.01')
        self.assertEqual(r['invalidation_level'], '98.99')
        self.assertFalse(r['actual_issuance_proven'])

    def test_waiting_is_not_confirmation(self):
        b, r = self.fixture()
        v = self.run_view(b, r, 'WAITING_CONFIRMATION')
        self.assertIsNone(v['confirmation'])
        self.assertIsNone(v['invalidation'])
        self.assertEqual(v['complete_minutes_evaluated'], 10)

    def test_later_completed_close_confirms(self):
        b, r = self.fixture(); self.confirm(b)
        v = self.run_view(b, r, 'PIVOT_CONFIRMED')
        self.assertEqual(v['confirmation']['bar_start'], '2026-10-06T16:01:00Z')
        self.assertEqual(v['confirmation']['known_at'], '2026-10-06T16:02:00Z')

    def test_equal_confirmation_level_does_not_cross(self):
        b, r = self.fixture()
        stock_minute(b, 151).update(high=102.2, close=102.01)
        self.run_view(b, r, 'WAITING_CONFIRMATION')

    def test_high_touch_without_close_is_not_confirmation(self):
        b, r = self.fixture(); stock_minute(b, 151)['high'] = 110.0
        self.run_view(b, r, 'WAITING_CONFIRMATION')

    def test_low_breach_invalidates(self):
        b, r = self.fixture(); self.invalidate(b)
        v = self.run_view(b, r, 'INVALIDATED')
        self.assertEqual(v['invalidation']['bar_start'], '2026-10-06T16:03:00Z')
        self.assertIsNone(v['confirmation'])

    def test_equal_invalidation_level_is_not_breach(self):
        b, r = self.fixture(); stock_minute(b, 153)['low'] = 98.99
        self.run_view(b, r, 'WAITING_CONFIRMATION')

    def test_same_minute_breach_precedes_close_confirmation(self):
        b, r = self.fixture(); self.confirm(b); self.invalidate(b, 151)
        v = self.run_view(b, r, 'INVALIDATED')
        self.assertIsNone(v['confirmation'])
        self.assertEqual(v['ordering_rule'], 'LOW_BREACH_BEFORE_FINAL_CLOSE')

    def test_confirmation_is_retained_after_failure(self):
        b, r = self.fixture(); self.confirm(b); self.invalidate(b)
        v = self.run_view(b, r, 'INVALIDATED')
        self.assertIsNotNone(v['confirmation'])
        self.assertIsNotNone(v['invalidation'])

    def test_gap_before_confirmation_prevents_first_event_claim(self):
        b, r = self.fixture(); self.confirm(b, 153)
        b['minutes'].remove(stock_minute(b, 150))
        v = self.run_view(b, r, 'UNAVAILABLE')
        self.assertIsNone(v['confirmation'])
        self.assertTrue(v['refusals'])

    def test_gap_after_confirmation_preserves_observed_confirmation(self):
        b, r = self.fixture(); self.confirm(b)
        b['minutes'].remove(stock_minute(b, 153))
        v = self.run_view(b, r, 'UNAVAILABLE')
        self.assertIsNotNone(v['confirmation'])
        self.assertIsNone(v['invalidation'])

    def test_gap_after_terminal_invalidation_does_not_erase_it(self):
        b, r = self.fixture(); self.invalidate(b, 151)
        b['minutes'].remove(stock_minute(b, 153))
        v = self.run_view(b, r, 'INVALIDATED')
        self.assertEqual(v['complete_minutes_evaluated'], 2)

    def test_incomplete_minute_cannot_confirm(self):
        b, r = self.fixture(decision='2026-10-06T16:01:30Z'); self.confirm(b)
        v = self.run_view(b, r, 'WAITING_CONFIRMATION')
        self.assertEqual(v['complete_minutes_evaluated'], 1)

    def test_future_prices_do_not_change_earlier_progress(self):
        b, r = self.fixture(); original = self.run_view(b, r, 'WAITING_CONFIRMATION')
        for row in b['minutes']:
            if row['known_at'] > '2026-10-06T16:10:00Z':
                row.update(open=500.0, high=600.0, low=400.0, close=550.0)
        self.assertEqual(original, self.run_view(b, r, 'WAITING_CONFIRMATION'))

    def test_late_correction_visible_only_after_receipt(self):
        b, r = self.fixture(); before = self.run_view(b, r, 'WAITING_CONFIRMATION')
        correction = copy.deepcopy(stock_minute(b, 151))
        correction.update(high=102.2, close=102.02, known_at='2026-10-06T16:15:00Z',
                          revision_id='late-confirmation-correction')
        b['minutes'].append(correction)
        self.assertEqual(before, self.run_view(b, r, 'WAITING_CONFIRMATION'))
        b['candidates'][-1]['decision_at'] = '2026-10-06T16:16:00Z'
        v = self.run_view(b, r, 'PIVOT_CONFIRMED')
        self.assertEqual(v['confirmation']['known_at'], '2026-10-06T16:15:00Z')

    def test_late_earlier_minute_delays_confirmation_knowledge(self):
        b, r = self.fixture(); self.confirm(b)
        stock_minute(b, 150)['known_at'] = '2026-10-06T16:05:00Z'
        v = self.run_view(b, r, 'PIVOT_CONFIRMED')
        self.assertEqual(v['confirmation']['known_at'], '2026-10-06T16:05:00Z')
        self.assertEqual(v['confirmation']['bar_end'], '2026-10-06T16:02:00Z')

    def test_later_formation_correction_cannot_move_frozen_level(self):
        b, r = self.fixture(); before = copy.deepcopy(r); self.invalidate(b)
        correction = copy.deepcopy(stock_minute(b, 125))
        correction.update(low=90.0, known_at='2026-10-06T16:05:00Z', revision_id='later-pivot-low')
        b['minutes'].append(correction)
        self.run_view(b, r, 'INVALIDATED')
        self.assertEqual(r, before)
        self.assertEqual(r['formation']['pivot']['low'], 99.0)

    def test_expiry_and_missed_confirmation_remain_explicit(self):
        b, r = self.fixture(decision='2026-10-06T17:01:00Z')
        self.confirm(b, 210)
        v = self.run_view(b, r, 'EXPIRED')
        self.assertIsNone(v['confirmation'])
        self.assertEqual(v['complete_minutes_evaluated'], 60)

    def test_expired_confirmation_is_not_deleted(self):
        b, r = self.fixture(decision='2026-10-06T17:01:00Z'); self.confirm(b)
        v = self.run_view(b, r, 'EXPIRED')
        self.assertIsNotNone(v['confirmation'])

    def test_missing_pre_expiry_minute_is_not_clean_expiry(self):
        b, r = self.fixture(decision='2026-10-06T17:01:00Z')
        b['minutes'].remove(stock_minute(b, 180))
        self.run_view(b, r, 'UNAVAILABLE')

    def test_reference_uses_session_close_and_episode_expiry(self):
        self.api(); b = witness()
        b['calendar']['sessions']['2026-10-06']['close'] = '2026-10-06T16:20:00Z'
        r = owner.freeze_pivot_reference(b, 'pivot', tick_size=0.01,
                                        episode_expires_at='2026-10-06T16:45:00Z')
        self.assertEqual(r['expires_at'], '2026-10-06T16:20:00Z')
        r2 = owner.freeze_pivot_reference(b, 'pivot', tick_size=0.01,
                                         episode_expires_at='2026-10-06T16:10:00Z')
        self.assertEqual(r2['expires_at'], '2026-10-06T16:10:00Z')

    def test_late_formation_skips_the_straddling_minute(self):
        self.api(); b = witness()
        for row in b['minutes']:
            if row['stream'] == 'stock' and row['start'] >= '2026-10-06T16:00:00Z':
                row.update(open=101.0, high=101.5, low=100.5, close=101.0)
        b['candidates'][0]['decision_at'] = '2026-10-06T16:00:02Z'
        r = owner.freeze_pivot_reference(b, 'pivot', tick_size=0.01,
                                        episode_expires_at='2026-10-06T17:00:00Z')
        self.invalidate(b, 150)
        b['candidates'].append(candidate('followup', '2026-10-06T16:02:00Z'))
        v = self.run_view(b, r, 'WAITING_CONFIRMATION')
        self.assertEqual(r['first_minute_start'], '2026-10-06T16:01:00Z')
        self.assertEqual(v['complete_minutes_evaluated'], 1)

    def test_wrong_basis_or_security_cannot_follow_reference(self):
        b, r = self.fixture()
        b['streams']['stock']['basis']['basis_id'] = 'other-basis'
        self.run_view(b, r, 'UNAVAILABLE')
        b, r = self.fixture()
        b['streams']['stock']['security_id'] = 'SYNTHETIC:other'
        self.run_view(b, r, 'UNAVAILABLE')

    def test_terminal_basis_refusal_is_preserved(self):
        b, r = self.fixture()
        stock_minute(b, 150)['source_ref'] = 'terminal-minute-capture:fixture'
        v = self.run_view(b, r, 'UNAVAILABLE')
        self.assertTrue(any('TERMINAL_BASIS_UNPROVEN' in x for x in v['refusals']))

    def test_reference_tamper_and_authority_escalation_refuse(self):
        b, r = self.fixture(); r['confirmation_level'] = '1'
        with self.assertRaises(InputContractError):
            owner.describe_pivot_progress(b, 'followup', reference=r)
        b, r = self.fixture(); r['formation']['authority']['can_gate'] = True
        r['reference_sha256'] = digest({k:v for k,v in r.items() if k != 'reference_sha256'})
        with self.assertRaises(InputContractError):
            owner.describe_pivot_progress(b, 'followup', reference=r)

    def test_invalid_parameters_and_nonpivot_refuse(self):
        self.api(); b = witness()
        for tick in (True, 0, -1, float('nan'), float('inf'), '0.01'):
            with self.subTest(tick=tick), self.assertRaises(InputContractError):
                owner.freeze_pivot_reference(b, 'pivot', tick_size=tick,
                                            episode_expires_at='2026-10-06T17:00:00Z')
        for expiry in ('2026-10-06T16:00:00Z', '2026-10-06T17:00:00'):
            with self.subTest(expiry=expiry), self.assertRaises(InputContractError):
                owner.freeze_pivot_reference(b, 'pivot', tick_size=0.01, episode_expires_at=expiry)
        b['contexts'][0]['payload']['is_leader'] = False
        with self.assertRaises(InputContractError):
            owner.freeze_pivot_reference(b, 'pivot', tick_size=0.01,
                                        episode_expires_at='2026-10-06T17:00:00Z')

    def test_before_formation_and_other_session_refuse(self):
        b, r = self.fixture(decision='2026-10-06T15:59:00Z')
        with self.assertRaises(InputContractError):
            owner.describe_pivot_progress(b, 'followup', reference=r)
        b, r = self.fixture(); b['candidates'][-1]['session'] = '2026-10-07'
        with self.assertRaises(InputContractError):
            owner.describe_pivot_progress(b, 'followup', reference=r)

    def test_inputs_and_reference_are_never_mutated(self):
        b, r = self.fixture(); before = copy.deepcopy((b, r))
        self.run_view(b, r, 'WAITING_CONFIRMATION')
        self.assertEqual((b, r), before)


if __name__ == '__main__':
    unittest.main()
