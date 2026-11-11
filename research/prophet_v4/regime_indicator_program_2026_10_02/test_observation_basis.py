import unittest
from intake_audit import audit_comparison
from test_intake_audit import manifest


def asof_manifest(grain='1D'):
    value = manifest()
    value.update(grain=grain, completed_bars_only=False,
                 bar_observation_policy='asof_snapshot', asof_snapshot_qualified=True,
                 snapshot_cut_digest=value['decision_cut_digest'],
                 asof_snapshot_receipt='owner:immutable-fixture')
    return value


class TestObservationBasis(unittest.TestCase):
    def test_qualified_asof_not_rejected_as_unfinished(self):
        a,b=asof_manifest(),asof_manifest('3D')
        self.assertTrue(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_missing_snapshot_qualification(self):
        a,b=asof_manifest(),asof_manifest('3D');b.pop('asof_snapshot_qualified')
        self.assertIn('right:unqualified_asof_snapshot',audit_comparison(a,b,contrast='policy_bundle')['reasons'])

    def test_wrong_snapshot_cut(self):
        a,b=asof_manifest(),asof_manifest('3D');b['snapshot_cut_digest']='later-cut'
        self.assertIn('right:asof_snapshot_cut_mismatch',audit_comparison(a,b,contrast='policy_bundle')['reasons'])

    def test_receipt_required_not_merely_claimed(self):
        a,b=asof_manifest(),asof_manifest('3D');b.pop('asof_snapshot_receipt')
        self.assertIn('right:missing_asof_snapshot_receipt',audit_comparison(a,b,contrast='policy_bundle')['reasons'])

    def test_mixed_basis_not_pure_grain(self):
        self.assertIn('confounded:bar_observation_policy',audit_comparison(manifest(),asof_manifest('3D'),contrast='grain_memory_matched')['reasons'])

    def test_basis_only_change_is_labeled_bundle(self):
        self.assertTrue(audit_comparison(manifest(),asof_manifest(),contrast='policy_bundle')['consistent'])

    def test_unknown_basis_not_accepted(self):
        a,b=manifest(),manifest();b.update(grain='3D',bar_observation_policy='finalized_hindsight')
        self.assertFalse(audit_comparison(a,b,contrast='policy_bundle')['consistent'])

    def test_asof_still_requires_boolean_completion(self):
        a,b=asof_manifest(),asof_manifest('3D');b['completed_bars_only']='false'
        self.assertIn('right:unqualified_bar_completion',audit_comparison(a,b,contrast='policy_bundle')['reasons'])

    def test_asof_policy_can_observe_a_closed_daily_bar(self):
        a,b=asof_manifest(),asof_manifest('3D');a['completed_bars_only']=True
        self.assertTrue(audit_comparison(a,b,contrast='grain_memory_matched')['consistent'])

    def test_explicit_and_implicit_complete_not_treatment(self):
        a,b=manifest(),manifest();b['bar_observation_policy']='completed_only'
        self.assertIn('no_declared_treatment_difference',audit_comparison(a,b,contrast='policy_bundle')['reasons'])


if __name__=='__main__':unittest.main()
