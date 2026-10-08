"""Boundary regressions for the frozen-pivot research projection."""
from __future__ import annotations
import copy
import unittest
import test_entry_radar_leader_pivot_progress as helpers
from test_entry_radar_leader_pivot_descriptor import witness
from test_entry_radar_rs_pullback_phase1 import candidate
from engine.entry_radar.replay import leader_pivot_descriptor as owner
from engine.entry_radar.replay.rs_pullback_launch_data import InputContractError


class LeaderPivotProgressEdgeTests(unittest.TestCase):
    def setUp(self):
        self.helper = helpers.LeaderPivotProgressTests()
        self.helper.api()

    def test_positive_integer_buffer_roundtrips(self):
        b, _ = self.helper.fixture()
        r = owner.freeze_pivot_reference(b, 'pivot', tick_size=1,
                                        episode_expires_at='2026-10-06T17:00:00Z')
        try:
            self.helper.run_view(b, r, 'WAITING_CONFIRMATION')
        except InputContractError as exc:
            self.fail('valid integer buffer rejected on reference read: ' + str(exc))

    def test_equal_integer_float_buffers_have_one_identity(self):
        b = witness()
        a = owner.freeze_pivot_reference(b, 'pivot', tick_size=1,
                                        episode_expires_at='2026-10-06T17:00:00Z')
        z = owner.freeze_pivot_reference(b, 'pivot', tick_size=1.0,
                                        episode_expires_at='2026-10-06T17:00:00Z')
        self.assertEqual(a, z)

    def test_non_minute_deadline_is_not_clean_expiry(self):
        b, r = self.helper.fixture(decision='2026-10-06T16:06:00Z',
                                    expiry='2026-10-06T16:05:02Z')
        v = self.helper.run_view(b, r, 'UNAVAILABLE')
        self.assertIn('PARTIAL_MINUTE_AT_EXPIRY', v['refusals'])
        self.assertEqual(v['evaluated_through'], '2026-10-06T16:05:00Z')

    def test_current_eligibility_does_not_rewrite_origin(self):
        b, r = self.helper.fixture(); self.helper.confirm(b)
        origin = copy.deepcopy(r)
        b['contexts'][0]['payload']['is_leader'] = False
        v = self.helper.run_view(b, r, 'PIVOT_CONFIRMED')
        self.assertEqual(r, origin)
        self.assertTrue(r['formation']['eligible'])
        self.assertFalse(v['source_admitted'])

    def test_input_kind_cannot_relabel_frozen_synthetic_evidence(self):
        b, r = self.helper.fixture(); b['input_kind'] = 'OBSERVED_MARKET'
        v = self.helper.run_view(b, r, 'UNAVAILABLE')
        self.assertIn('INPUT_KIND_CHANGED', v['refusals'])

    def test_changed_session_window_refuses(self):
        b, r = self.helper.fixture()
        b['calendar']['sessions']['2026-10-06']['close'] = '2026-10-06T16:30:00Z'
        v = self.helper.run_view(b, r, 'UNAVAILABLE')
        self.assertIn('FROZEN_SESSION_NOT_BOUND', v['refusals'])

    def test_first_minute_after_decision_cannot_be_invented(self):
        b, r = self.helper.fixture()
        b['minutes'] = [x for x in b['minutes'] if x.get('stream') != 'stock'
                        or x['start'] != '2026-10-06T16:00:00Z']
        self.helper.run_view(b, r, 'UNAVAILABLE')

    def test_invalidated_reference_does_not_rearm_after_rebound(self):
        b, r = self.helper.fixture(); self.helper.invalidate(b, 151)
        self.helper.confirm(b, 155)
        v = self.helper.run_view(b, r, 'INVALIDATED')
        self.assertIsNone(v['confirmation'])
        self.assertEqual(v['complete_minutes_evaluated'], 2)


if __name__ == '__main__':
    unittest.main()
