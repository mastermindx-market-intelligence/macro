"""Contract tests over the actual curated audit. No live source/model qualification."""
import copy
import json
from pathlib import Path
import unittest
from resources_catalyst_r4_cohort import enrollment_fingerprint, screen_observation, audit_summary
ROOT=Path(__file__).resolve().parent
S=json.loads((ROOT/'R4_SOURCE_MANIFEST.json').read_text())
E=json.loads((ROOT/'R4_ENROLLMENT_AUDIT.json').read_text())
L=json.loads((ROOT/'R4_TARGET_AND_CLAIM_LABELS.json').read_text())

class AuditArtifactTests(unittest.TestCase):
    def test_all_source_keys_unique(self):
        keys=[s['id'] for s in S['sources']];self.assertEqual(len(keys),len(set(keys)))
    def test_every_observation_source_is_present(self):
        keys={s['id'] for s in S['sources']};self.assertTrue(all(r['source_ref'] in keys for r in E['observations']))
    def test_every_label_source_is_present(self):
        keys={s['id'] for s in S['sources']};self.assertTrue(all(r['source_ref'] in keys for r in L['events']))
    def test_disclosure_dates_match_the_inspected_source(self):
        dates={s['id']:s['publication_date'] for s in S['sources']}
        for row in E['observations']+L['events']:self.assertEqual(row['known_on'],dates[row['source_ref']])
    def test_no_market_fields_fabricated(self):
        for obj in (S,E,L):
            self.assertIsNone(obj['metadata']['population_success_rate'])
            self.assertIsNone(obj['metadata']['fitted_probability'])
            self.assertIsNone(obj['metadata']['expected_return'])
            self.assertFalse(obj['metadata']['production_admission'])
    def test_sample_not_claimed_blind_or_complete(self):
        self.assertFalse(E['metadata']['researcher_outcome_blind'])
        self.assertFalse(E['metadata']['historical_listing_roster_complete'])
    def test_project_and_landmark_counts_separate(self):
        result=audit_summary(E['observations']);self.assertEqual((result['observations'],result['projects']),(15,12))
    def test_old_sugar_works_not_new_build(self):
        self.assertEqual(E['dispositions']['sugar_prior']['scope'],'OUT_OF_SCOPE')
    def test_early_blackwater_work_not_formal_fid(self):
        self.assertEqual(E['dispositions']['blackwater_early']['stratum'],'preparatory_observation')
    def test_old_body_venue_not_current_page_header(self):
        row=next(r for r in E['observations'] if r['observation_key']=='blackwater_early')
        self.assertEqual(row['listing_venue'],'TSXV')
    def test_same_ascot_project_different_landmarks_do_not_reset_original_target(self):
        vals=L['worked_labels']
        self.assertFalse(vals['premier_first_gold_24m_original_finance']['value'])
        self.assertTrue(vals['premier_first_gold_24m_refinance']['value'])
    def test_cote_date_conflict_not_forced(self):
        self.assertEqual(L['worked_labels']['cote_operating_date_conflict']['state'],'CONFLICT')
    def test_future_label_corruption_does_not_change_enrollment(self):
        before=enrollment_fingerprint(E['observations']);other=copy.deepcopy(L)
        other['worked_labels']['puregold_24m']['value']=False
        self.assertEqual(before,enrollment_fingerprint(E['observations']))
    def test_public_possession_and_system_possession_separate(self):
        self.assertTrue(L['worked_labels']['puregold_24m_as_known_then']['value'])
        self.assertIsNone(L['worked_labels']['puregold_24m_system_possession']['value'])
    def test_unknown_recovery_not_zero(self):
        claim=next(c for c in L['claims'] if c['project']=='madsen')
        self.assertIsNone(claim['legal_extinction']);self.assertIsNone(claim['recovery_amount'])
    def test_original_vague_window_remains_vague(self):
        row=next(x for x in L['original_windows'] if x['project']=='valentine')
        self.assertIsNone(row['normalized_start']);self.assertIsNone(row['normalized_end'])
    def test_all_scope_dispositions_reproduce(self):
        self.assertEqual(E['dispositions'],{r['observation_key']:screen_observation(r) for r in E['observations']})

if __name__=='__main__': unittest.main(verbosity=2)
