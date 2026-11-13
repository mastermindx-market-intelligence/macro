import copy
from contextlib import closing
import json
from pathlib import Path
import tempfile
import unittest
from admin import capacity_history
from admin.capacity_ingest import ingest
from admin.capacity_intelligence import analyze, panel
from admin.tests.test_capacity_history import NOW, snapshot


def live():
    return {'ok':True,'generated_at':NOW,'routes':[
        {'id':'a','provider':'shared-1','models':['alpha','beta'],'cooling':False},
        {'id':'b','provider':'shared-1','models':['alpha'],'cooling':False},
        {'id':'c','provider':'pool-2','models':['beta'],'cooling':True}],
        'aliases':{'fabric/advanced':['alpha','beta']},'active':[],'recent':[], 'claude':None,'overflow':None}


def quota(at,used=50,reset=NOW+86400):
    return {'reachable':True,'observed_at':at,'accounts':[
        {'id':'seat-1','drain':False,'cooldown_until':0,'families':{
            'family-a':{'budget_weekly':100,'used_weekly':used,'remaining_weekly':100-used,
                        'weekly_resets_at':reset,'weekly_reset_source':'provider','cooldown_until':0}}}]}

class Intelligence(unittest.TestCase):
    def test_catalog_adapts_without_model_or_pool_constants(self):
        s=live();s['routes'].append({'id':'future','provider':'new-pool','models':['future-model'],'cooling':False})
        d=analyze(s,now=NOW)
        self.assertIn('future-model',[r['model'] for r in d['models']])
        self.assertIn('new-pool',[r['pool'] for r in d['pools']])
    def test_shared_pool_routes_are_not_independent_subscriptions(self):
        d=analyze(live(),now=NOW);pool=next(r for r in d['pools'] if r['pool']=='shared-1')
        self.assertEqual(pool['routes'],2);self.assertIsNone(pool['subscriptions']);self.assertIsNone(pool['quota_limit'])
    def test_alternatives_are_class_eligibility_not_quota_claim(self):
        d=analyze(live(),now=NOW);m=next(r for r in d['models'] if r['model']=='alpha');alt=m['alternatives'][0]
        self.assertEqual(alt['model'],'beta');self.assertIsNone(alt['quota_available']);self.assertEqual(alt['routes_outside_cooldown'],1)
    def test_demand_and_primary_pool_are_measured(self):
        h={'ok':True,'demand':[{'provider':'shared-1','model':'alpha','lane':'fabric/advanced','requests':80,'failed':2,'output_tokens':100,'output_tokens_known':70},
                            {'provider':'pool-2','model':'alpha','lane':'fabric/advanced','requests':20,'failed':0,'output_tokens':20,'output_tokens_known':20}]}
        d=analyze(live(),h,now=NOW);m=d['models'][0]
        self.assertEqual(m['requests'],100);self.assertEqual(m['pool_concentration_pct'],80);self.assertEqual(m['output_tokens'],120)
    def test_new_observer_does_not_invent_purchase_recommendation(self):
        s=live();s['claude']=quota(NOW);d=analyze(s,now=NOW)
        self.assertIsNone(d['quota_families'][0]['suggested_additional_subscriptions'])
        self.assertFalse(any(r['kind']=='subscription_scenario' for r in d['recommendations']))
    def test_comparable_hour_creates_conditional_not_automatic_scenario(self):
        s=live();s['claude']=quota(NOW,used=70);d=analyze(s,previous=quota(NOW-7200,used=50),now=NOW)
        f=d['quota_families'][0];self.assertEqual(f['units_per_hour'],10);self.assertGreater(f['suggested_additional_subscriptions'],0)
        self.assertEqual(f['unit'],'gateway_weekly_budget_units_not_tokens')
        self.assertTrue(any(r['kind']=='subscription_scenario' for r in d['recommendations']))
    def test_short_burst_stale_cooling_and_reset_invalidate_numeric_advice(self):
        for scenario in ['short','stale','cooling','reset','estimated','budget_change']:
            with self.subTest(scenario=scenario):
                s=live();s['claude']=quota(NOW,used=70);prior=quota(NOW-7200,used=50)
                if scenario=='short':prior['observed_at']=NOW-300
                if scenario=='stale':s['generated_at']=NOW-100
                if scenario=='cooling':s['claude']['accounts'][0]['cooldown_until']=NOW+200
                if scenario=='reset':prior['accounts'][0]['families']['family-a']['weekly_resets_at']=NOW-100
                if scenario=='estimated':s['claude']['accounts'][0]['families']['family-a']['weekly_reset_source']='estimated'
                if scenario=='budget_change':prior['accounts'][0]['families']['family-a']['budget_weekly']=80
                d=analyze(s,previous=prior,now=NOW);self.assertIsNone(d['quota_families'][0]['suggested_additional_subscriptions'])
                self.assertFalse(any(r['kind']=='subscription_scenario' for r in d['recommendations']))
    def test_persisted_panel_anchors_baseline_to_observation_clock(self):
        current_at = NOW+10
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'snapshot.json'
            for sequence, at in enumerate((current_at-3630, current_at-3595, current_at), 1):
                frame = snapshot(sequence, at=at)
                frame['claude'] = quota(at, used=50+(at-current_at)*10/3600)
                self.assertTrue(ingest(json.dumps(frame).encode(), path, now=at))
            result = panel(path=path, now=current_at+10)
            family = result['quota_families'][0]
            self.assertEqual(family['units_per_hour'], 10)
            self.assertEqual(family['sample_hours'], round(3630/3600, 2))
            self.assertIsNotNone(family['suggested_additional_subscriptions'])

    def test_persisted_quota_matrix_all_collector_phases_and_fresh_ages(self):
        # Two hours of real ingress at a 30-second collection cadence. Every
        # phase and each fresh cached age must compare the same observation pair.
        for phase in range(30):
            current_at = NOW+phase
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as td:
                path = Path(td)/'snapshot.json'
                with closing(capacity_history.Recorder(capacity_history.database_path(path))) as recorder:
                    sequence = 0
                    for at in range(current_at-7200, current_at+1, 30):
                        sequence += 1
                        frame = snapshot(sequence, at=at, started=NOW-8000)
                        frame['claude'] = quota(at, used=50+(at-current_at)*10/3600)
                        self.assertTrue(ingest(json.dumps(frame).encode(), path, now=at, recorder=recorder))
                    baseline = None
                    for age in range(91):
                        sequence += 1
                        frame = snapshot(sequence, at=current_at+age, started=NOW-8000)
                        frame['claude'] = quota(current_at, used=50)
                        self.assertTrue(ingest(json.dumps(frame).encode(), path, now=current_at+age, recorder=recorder))
                        result = panel(path=path, now=current_at+age)
                        family = result['quota_families'][0]
                        self.assertEqual(family['units_per_hour'], 10, (phase, age))
                        self.assertGreaterEqual(family['sample_hours'], 1, (phase, age))
                        self.assertIsNotNone(family['suggested_additional_subscriptions'], (phase, age))
                        measured = {k: family[k] for k in ('units_per_hour', 'sample_hours',
                            'weekly_budget_units', 'weekly_remaining_units', 'suggested_additional_subscriptions')}
                        if baseline is None:
                            baseline = measured
                        self.assertEqual(measured, baseline, (phase, age))

    def test_persisted_panel_preserves_advice_abstention_gates(self):
        for kind in ('short_history', 'stale_quota', 'stale_snapshot', 'rolled_window',
                     'estimated_reset', 'budget_change', 'draining', 'cooldown', 'no_quota',
                     'future_quota', 'missing_time', 'invalid_time'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as td:
                path = Path(td)/'snapshot.json'
                prior_at = NOW-1800 if kind == 'short_history' else NOW-7200
                before = snapshot(1, at=prior_at, started=NOW-8000)
                before['claude'] = quota(prior_at, used=20)
                current = snapshot(2, at=NOW, started=NOW-8000)
                current['claude'] = quota(NOW, used=40)
                if kind == 'stale_quota': current['claude']['observed_at'] = NOW-91
                if kind == 'stale_snapshot': current['generated_at'] = NOW-16
                if kind == 'rolled_window': before['claude']['accounts'][0]['families']['family-a']['weekly_resets_at'] = NOW-1
                if kind == 'estimated_reset': current['claude']['accounts'][0]['families']['family-a']['weekly_reset_source'] = 'estimated'
                if kind == 'budget_change': before['claude']['accounts'][0]['families']['family-a']['budget_weekly'] = 80
                if kind == 'draining': current['claude']['accounts'][0]['drain'] = True
                if kind == 'cooldown': current['claude']['accounts'][0]['cooldown_until'] = NOW+200
                if kind == 'no_quota': current['claude'] = None
                if kind == 'future_quota': current['claude']['observed_at'] = NOW+1
                if kind == 'missing_time': current['claude']['observed_at'] = None
                if kind == 'invalid_time': current['claude']['observed_at'] = 'invalid'
                self.assertTrue(ingest(json.dumps(before).encode(), path, now=prior_at))
                self.assertTrue(ingest(json.dumps(current).encode(), path, now=NOW))
                result = panel(path=path, now=NOW)
                self.assertFalse(any(r['kind']=='subscription_scenario' for r in result['recommendations']))
                self.assertTrue(all(r['suggested_additional_subscriptions'] is None for r in result['quota_families']))

    def test_disconnected_explicit(self):self.assertFalse(analyze({'ok':False},now=NOW)['ok'])

if __name__=='__main__':unittest.main()
