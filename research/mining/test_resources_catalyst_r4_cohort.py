"""Research-only scope and target counterexamples; no production admission."""
import copy
import unittest
from resources_catalyst_r4_cohort import (
    screen_observation, enrollment_fingerprint, horizon_date,
    milestone_at_horizon as _milestone_at_horizon, settlement_value, audit_summary,
)


def milestone_at_horizon(*args, **kwargs):
    return _milestone_at_horizon(*args, project_key="example_project", **kwargs)


def observation(**changes):
    row = dict(observation_key='example_obs', project_key='example_project',
               issuer_key='example_issuer', claim_key='example_claim',
               source_ref='example_source', known_on='2020-07-21',
               effective_lower='2020-07-21', effective_upper='2020-07-21',
               listing_venue='TSX', primary_product='gold',
               stage_kind='BUILD_APPROVED', prior_stage_entry=None)
    row.update(changes)
    return row


def event(**changes):
    row = dict(id='example_event', project_key='example_project', source_ref='example_source',
               target='issuer_commercial', kind='attained_first',
               lower='2021-08-01', upper='2021-08-01', known_on='2021-08-03',
               recorded_on='2026-09-27')
    row.update(changes)
    return row


class ScopeTests(unittest.TestCase):
    def test_build_is_scope_match_not_incident_admission(self):
        r=screen_observation(observation())
        self.assertEqual((r.get('scope'),r.get('stratum'),r.get('incident')),
                         ('MATCHED_OBSERVATION','construction_decision','UNVERIFIED'))
        self.assertIs(r.get('production_admission'),False)
    def test_foreign_project_does_not_erase_toronto_listing(self):
        # Project geography is deliberately not an eligibility argument.
        self.assertEqual(screen_observation(observation(project_key='example_mexico')).get('scope'),'MATCHED_OBSERVATION')
    def test_unknown_listing_is_not_canadian_by_company_name(self):
        self.assertEqual(screen_observation(observation(listing_venue=None)).get('scope'),'UNRESOLVED')
    def test_us_crosslisting_is_not_substituted(self):
        self.assertEqual(screen_observation(observation(listing_venue='NYSE')).get('scope'),'OUT_OF_SCOPE')
    def test_no_options_input_required(self):
        self.assertEqual(screen_observation(observation(stage_kind='FINANCING_ATTEMPT')).get('stratum'),'financing_attempt')
    def test_early_works_not_formal_build(self):
        self.assertEqual(screen_observation(observation(stage_kind='EARLY_WORKS')).get('stratum'),'preparatory_observation')
    def test_conditional_build_retains_condition(self):
        self.assertEqual(screen_observation(observation(stage_kind='BUILD_CONDITIONAL')).get('stratum'),'conditional_build')
    def test_prevalent_financing_is_not_incident_construction(self):
        r=screen_observation(observation(stage_kind='FINANCING_ATTEMPT',prior_stage_entry=True))
        self.assertEqual((r.get('stratum'),r.get('incident')),('financing_attempt','PREVALENT'))
    def test_old_work_reported_later_stays_outside_window(self):
        r=screen_observation(observation(known_on='2019-04-02',effective_lower='2017-09-01',effective_upper='2017-09-30'))
        self.assertEqual(r.get('scope'),'OUT_OF_SCOPE')
    def test_partial_date_crossing_window_is_not_forced(self):
        r=screen_observation(observation(effective_lower='2017-12-01',effective_upper='2018-01-31',known_on='2018-02-01'))
        self.assertEqual(r.get('scope'),'UNRESOLVED')
    def test_later_disclosure_not_backdated(self):
        self.assertEqual(screen_observation(observation(known_on='2023-01-03')).get('scope'),'OUT_OF_SCOPE')
    def test_gold_scope_not_any_critical_mineral(self):
        self.assertEqual(screen_observation(observation(primary_product='nickel')).get('scope'),'OUT_OF_SCOPE')
    def test_future_planned_build_is_not_completed_decision(self):
        self.assertEqual(screen_observation(observation(known_on='2020-01-01')).get('scope'),'UNRESOLVED')
    def test_outcome_field_rejected_in_enrollment(self):
        with self.assertRaises(ValueError): screen_observation(observation(eventual_success=True))
    def test_missing_source_rejected(self):
        with self.assertRaises(ValueError): screen_observation(observation(source_ref=''))
    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError): screen_observation(observation(stage_kind='FULLY_DERISKED'))
    def test_integer_not_prior_entry_boolean(self):
        with self.assertRaises(ValueError): screen_observation(observation(prior_stage_entry=1))
    def test_digest_order_independent(self):
        a=observation();b=observation(observation_key='example_second')
        self.assertEqual(enrollment_fingerprint([a,b]),enrollment_fingerprint([b,a]))
    def test_digest_changes_when_universe_changes(self):
        self.assertNotEqual(enrollment_fingerprint([observation()]),enrollment_fingerprint([observation(observation_key='different')]))
    def test_duplicate_observation_rejected(self):
        with self.assertRaises(ValueError): enrollment_fingerprint([observation(),observation()])
    def test_labels_cannot_enter_digest(self):
        with self.assertRaises(ValueError): enrollment_fingerprint([observation(outcome='failure')])
    def test_empty_denominator_rejected(self):
        with self.assertRaises(ValueError): enrollment_fingerprint([])


class HorizonTests(unittest.TestCase):
    def test_calendar_anniversary_not_730_days(self):
        self.assertEqual(horizon_date('2019-08-07',24),'2021-08-07')
    def test_leap_day_calendar_rule(self):
        self.assertEqual(horizon_date('2020-02-29',12),'2021-02-28')
    def test_month_end_calendar_rule(self):
        self.assertEqual(horizon_date('2020-01-31',1),'2020-02-29')
    def test_boolean_month_rejected(self):
        with self.assertRaises(ValueError): horizon_date('2020-01-01',True)
    def test_noncanonical_day_rejected(self):
        with self.assertRaises(ValueError): horizon_date('20200101',12)
    def test_puregold_first_milestone_survives_later_suspension(self):
        rows=[event(),event(id='stop',target='operating_suspension',lower='2022-10-24',upper='2022-10-24',known_on='2022-10-24')]
        r=milestone_at_horizon(rows,'issuer_commercial','2019-08-07',24,'2026-09-27')
        self.assertEqual((r.get('state'),r.get('value')),('ACHIEVED',True))
    def test_suspension_not_commercial_milestone(self):
        r=milestone_at_horizon([event(target='operating_suspension')],'issuer_commercial','2019-08-07',24,'2026-09-27')
        self.assertEqual((r.get('state'),r.get('value')),('UNKNOWN',None))
    def test_future_failure_not_visible_at_old_label_cutoff(self):
        r=milestone_at_horizon([event()],'issuer_commercial','2019-08-07',24,'2021-08-07')
        self.assertEqual(r.get('state'),'ACHIEVED')
    def test_attained_but_not_published_by_cutoff_is_not_known(self):
        self.assertEqual(milestone_at_horizon([event()],'issuer_commercial','2019-08-07',24,'2021-08-02').get('state'),'PENDING')
    def test_same_source_not_historical_system_possession(self):
        r=milestone_at_horizon([event()],'issuer_commercial','2019-08-07',24,'2021-08-07',mode='system_replay')
        self.assertEqual(r.get('state'),'UNKNOWN')
    def test_unknown_recorded_time_blocks_replay_not_public_reconstruction(self):
        row=event(recorded_on=None)
        self.assertEqual(milestone_at_horizon([row],'issuer_commercial','2019-08-07',24,'2026-09-27',mode='system_replay').get('state'),'UNKNOWN')
        self.assertEqual(milestone_at_horizon([row],'issuer_commercial','2019-08-07',24,'2026-09-27').get('state'),'ACHIEVED')
    def test_late_first_gold_confirms_original_24m_miss(self):
        row=event(target='first_gold',lower='2025-06-30',upper='2025-06-30',known_on='2025-06-30')
        r=milestone_at_horizon([row],'first_gold','2022-09-07',24,'2026-09-27')
        self.assertEqual((r.get('state'),r.get('value')),('NOT_ACHIEVED_BY_HORIZON',False))
    def test_no_source_not_evidence_of_failure(self):
        self.assertEqual(milestone_at_horizon([],'first_gold','2022-09-07',24,'2026-09-27').get('state'),'UNKNOWN')
    def test_unmatured_horizon_pending(self):
        self.assertEqual(milestone_at_horizon([],'first_gold','2022-09-07',24,'2023-09-07').get('state'),'PENDING')
    def test_positive_can_resolve_before_horizon(self):
        self.assertEqual(milestone_at_horizon([event()],'issuer_commercial','2019-08-07',24,'2021-08-03').get('state'),'ACHIEVED')
    def test_interval_crossing_horizon_unresolved(self):
        row=event(lower='2021-08-01',upper='2021-08-31',known_on='2021-09-01')
        self.assertEqual(milestone_at_horizon([row],'issuer_commercial','2019-08-07',24,'2026-09-27').get('state'),'INTERVAL_STRADDLES_HORIZON')
    def test_conflicting_first_dates_not_silently_latest_wins(self):
        rows=[event(),event(id='conflict',lower='2021-08-02',upper='2021-08-02')]
        self.assertEqual(milestone_at_horizon(rows,'issuer_commercial','2019-08-07',24,'2026-09-27').get('state'),'CONFLICT')
    def test_not_yet_after_horizon_supports_nonattainment(self):
        row=event(kind='not_yet',lower='2021-09-01',upper='2021-09-01',known_on='2021-09-01')
        self.assertEqual(milestone_at_horizon([row],'issuer_commercial','2019-08-07',24,'2026-09-27').get('state'),'NOT_ACHIEVED_BY_HORIZON')
    def test_not_yet_before_horizon_does_not_fill_gap(self):
        row=event(kind='not_yet',lower='2021-07-01',upper='2021-07-01',known_on='2021-07-01')
        self.assertEqual(milestone_at_horizon([row],'issuer_commercial','2019-08-07',24,'2026-09-27').get('state'),'UNKNOWN')
    def test_incompatible_first_and_not_yet_conflict(self):
        rows=[event(),event(id='ny',kind='not_yet',lower='2021-09-01',upper='2021-09-01',known_on='2021-09-01')]
        self.assertEqual(milestone_at_horizon(rows,'issuer_commercial','2019-08-07',24,'2026-09-27').get('state'),'CONFLICT')
    def test_preexisting_milestone_not_new_success(self):
        self.assertEqual(milestone_at_horizon([event()],'issuer_commercial','2022-01-01',24,'2026-09-27').get('state'),'PRE_ENTRY_ATTAINMENT')
    def test_interval_at_entry_is_not_forced_incident(self):
        row=event(lower='2021-07-20',upper='2021-08-02')
        self.assertEqual(milestone_at_horizon([row],'issuer_commercial','2021-08-01',24,'2026-09-27').get('state'),'AMBIGUOUS_ENTRY')
    def test_duplicate_event_rejected(self):
        with self.assertRaises(ValueError): milestone_at_horizon([event(),event()],'issuer_commercial','2019-08-07',24,'2026-09-27')
    def test_future_achievement_not_accepted_as_observed(self):
        with self.assertRaises(ValueError): milestone_at_horizon([event(known_on='2021-07-01')],'issuer_commercial','2019-08-07',24,'2026-09-27')
    def test_different_target_not_contract_trigger(self):
        self.assertEqual(milestone_at_horizon([event()],'joint_venture_commercial','2019-08-07',24,'2026-09-27').get('state'),'UNKNOWN')

    def test_other_project_cannot_supply_milestone(self):
        with self.assertRaises(ValueError): milestone_at_horizon([event(project_key='other_project')],'issuer_commercial','2019-08-07',24,'2026-09-27')
    def test_unbounded_not_yet_interval_not_silently_exact(self):
        with self.assertRaises(ValueError): milestone_at_horizon([event(kind='not_yet',lower='2021-07-01')],'issuer_commercial','2019-08-07',24,'2026-09-27')


class SettlementAndAuditTests(unittest.TestCase):
    def test_known_share_exchange_not_zero_payoff(self):
        self.assertEqual(settlement_value('0.3867','10','0','CAD','CAD'),'3.8670')
    def test_missing_successor_price_not_zero(self):
        self.assertIsNone(settlement_value('0.3867',None,'0','CAD','CAD'))
    def test_zero_successor_price_is_real_zero_if_qualified(self):
        self.assertEqual(settlement_value('0.3867','0','0','CAD','CAD'),'0.0000')
    def test_cash_only_settlement_needs_no_fictional_stock_price(self):
        self.assertEqual(settlement_value("0",None,"5","CAD","CAD"),"5")
    def test_fx_mismatch_withheld(self):
        with self.assertRaises(ValueError): settlement_value('0.3867','10','0','CAD','USD')
    def test_nonfinite_price_rejected(self):
        with self.assertRaises(ValueError): settlement_value('0.3867','NaN','0','CAD','CAD')
    def test_negative_ratio_rejected(self):
        with self.assertRaises(ValueError): settlement_value('-0.1','10','0','CAD','CAD')
    def test_same_project_two_observations_not_two_projects(self):
        rows=[observation(),observation(observation_key='example_new',stage_kind='FINANCING_ATTEMPT')]
        r=audit_summary(rows)
        self.assertEqual((r.get('observations'),r.get('projects'),r.get('claims')),(2,1,1))
    def test_fully_labeled_purposeful_sample_cannot_create_population_rate(self):
        self.assertIsNone(audit_summary([observation()]).get('population_success_rate','ERROR'))
        self.assertIs(audit_summary([observation()]).get('empirically_qualified'),False)
    def test_independent_label_edit_cannot_change_enrollment_digest(self):
        rows=[observation()]; before=enrollment_fingerprint(rows)
        labels={'example_project':'success'};labels['example_project']='failure'
        self.assertEqual(enrollment_fingerprint(rows),before)
    def test_empty_audit_rejected(self):
        with self.assertRaises(ValueError): audit_summary([])

if __name__=='__main__': unittest.main(verbosity=2)
