import copy
import unittest
from admin.capacity_intelligence import analyze
from admin.tests.test_capacity_history import NOW


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
    def test_disconnected_explicit(self):self.assertFalse(analyze({'ok':False},now=NOW)['ok'])

if __name__=='__main__':unittest.main()
