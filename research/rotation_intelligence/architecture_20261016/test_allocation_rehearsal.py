from __future__ import annotations
import math
import unittest
import allocation_rehearsal as a

class FirstContracts(unittest.TestCase):
    def test_sixty_three_intervals_require_sixty_four_prices(self):
        with self.assertRaises(ValueError):
            a.log_return([100.0]*63,63)
        self.assertAlmostEqual(a.log_return([100.0+i for i in range(64)],63),math.log(163/100))

    def test_thirteen_series_emit_all_five_reference_choices(self):
        frames=[a.frame(t,((i,100.0) for i in range(253))) for t in a.INPUTS]
        d=a.decide(frames,252,25308,tuple(range(300)))
        self.assertEqual(d['status'],'available')
        self.assertEqual(set(d['weights']),{'B0','B1','B2','B3','B4'})
        self.assertEqual(d['weights']['B4'],{'BIL':1.0})

    def test_missing_bill_input_is_not_a_cash_choice(self):
        frames=[a.frame(t,((i,100.0) for i in range(253))) for t in a.INPUTS if t!='BIL']
        d=a.decide(frames,252,25308,tuple(range(300)))
        self.assertEqual(d['status'],'unavailable')
        self.assertIn('MISSING:BIL',d['reasons'])
        self.assertEqual(d['weights'],{})


from copy import deepcopy

class AvailabilityAndSelection(unittest.TestCase):
    def setUp(self):
        self.calendar=tuple(range(320));self.anchor=252;self.cutoff=25308
        self.frames=[a.frame(t,((i,100.0) for i in range(253))) for t in a.INPUTS]

    def decision(self, frames=None):
        return a.decide(self.frames if frames is None else frames,252,25308,self.calendar)

    def test_each_required_input_cannot_disappear(self):
        for t in a.INPUTS:
            d=self.decision([f for f in self.frames if f['ticker']!=t])
            self.assertEqual(d['status'],'unavailable');self.assertEqual(d['weights'],{})

    def test_late_receipt_is_not_backdated(self):
        self.frames[-1]['read_clock']=25309
        self.assertIn('MISSING:BIL',self.decision()['reasons'])

    def test_receipt_exactly_at_cutoff_is_allowed(self):
        self.frames[-1]['read_clock']=25308
        self.assertEqual(self.decision()['status'],'available')

    def test_future_snapshot_does_not_change_previous_decision(self):
        old=self.decision();future=deepcopy(self.frames[-1]);future.update(read_clock=27322,durable_clock=27321,capture_clock=27320,revision='future')
        future['rows']=tuple((i,777.0) for i in range(273))
        self.assertEqual(self.decision(self.frames+[future]),old)

    def test_newest_eligible_invalid_snapshot_does_not_rewind(self):
        latest=deepcopy(self.frames[-1]);latest.update(read_clock=25300,durable_clock=25299,capture_clock=25298,revision='revision2')
        latest['rows']=latest['rows'][:-1]
        d=self.decision(self.frames+[latest]);self.assertIn('INCOMPLETE_PREFIX:BIL',d['reasons'])

    def test_duplicate_latest_snapshots_are_ambiguous(self):
        self.assertIn('AMBIGUOUS_VINTAGE:BIL',self.decision(self.frames+[deepcopy(self.frames[-1])])['reasons'])

    def test_one_month_cannot_be_filled_from_mutable_cache(self):
        self.frames[-1]['rows']=self.frames[-1]['rows'][-22:]
        self.assertIn('INCOMPLETE_PREFIX:BIL',self.decision()['reasons'])

    def test_missing_interior_session_refuses(self):
        self.frames[0]['rows']=tuple(r for r in self.frames[0]['rows'] if r[0]!=100)
        self.assertIn('INCOMPLETE_PREFIX:XLB',self.decision()['reasons'])

    def test_zero_return_is_data_not_missingness(self):
        d=self.decision();self.assertEqual(d['status'],'available');self.assertEqual(d['weights']['B4'],{'BIL':1.0})

    def test_invalid_prices_are_not_zero_returns(self):
        for value in (None,0,-1,True,float('nan'),float('inf')):
            fs=deepcopy(self.frames);fs[0]['rows']=fs[0]['rows'][:-1]+((252,value),)
            self.assertIn('INVALID_PRICE:XLB',self.decision(fs)['reasons'])

    def test_clock_regression_refuses(self):
        self.frames[-1]['capture_clock']=25307
        self.assertIn('CLOCK_ORDER:BIL',self.decision()['reasons'])

    def test_event_after_capture_refuses(self):
        self.frames[-1]['rows']+=((253,100),)
        self.assertIn('EVENT_AFTER_CAPTURE:BIL',self.decision()['reasons'])

    def test_price_basis_or_real_mode_cannot_be_laundered(self):
        for key,value in [('basis','price'),('evidence_mode','naturally_observed')]:
            fs=deepcopy(self.frames);fs[0][key]=value
            self.assertIn('BASIS_OR_MODE:XLB',self.decision(fs)['reasons'])

    def test_label_and_path_fields_refuse(self):
        for key in ('future_return','runtime_path','authority_granted'):
            fs=deepcopy(self.frames);fs[0][key]=True
            self.assertIn('FRAME_SCHEMA',self.decision(fs)['reasons'])

    def test_foreign_cutoff_refuses(self):
        with self.assertRaises(ValueError):a.decide(self.frames,252,25309,self.calendar)

    def test_252_prices_do_not_meet_252_prior_session_warmup(self):
        fs=deepcopy(self.frames)
        for f in fs:f['rows']=f['rows'][1:]
        self.assertEqual(self.decision(fs)['status'],'unavailable')

    def test_deterministic_tie_and_strict_cash_hurdle(self):
        d=self.decision();self.assertEqual(tuple(d['weights']['B3']),a.SECTORS[:3])
        self.assertEqual(d['weights']['B4'],{'BIL':1.0})

    def test_mixed_bill_slots_are_aggregated(self):
        rates={t:-0.03-j*0.01 for j,t in enumerate(a.SECTORS)}
        rates.update(XLB=0.06,XLC=-0.01,XLE=-0.02,SPY=0.05,BIL=0.0)
        for f in self.frames:
            f['rows']=tuple((i,100*math.exp(rates[f['ticker']]*i/252)) for i in range(253))
        d=self.decision();self.assertEqual(set(d['weights']['B3']),{'XLB','XLC','XLE'})
        self.assertEqual(d['weights']['B4'],{'BIL':2/3,'XLB':1/3})

    def test_ranking_unchanged_by_common_benchmark_and_currency_scale(self):
        fs=deepcopy(self.frames)
        for f in fs:
            j=a.INPUTS.index(f['ticker']);f['rows']=tuple((i,100*math.exp((13-j)*i/100000)) for i in range(253))
        d=self.decision(fs)
        for f in fs:
            if f['ticker']=='SPY':f['rows']=tuple((i,100*math.exp(i/10000)) for i in range(253))
        self.assertEqual(d['weights']['B3'],self.decision(fs)['weights']['B3'])
        for f in fs:f['rows']=tuple((i,v*1000) for i,v in f['rows'])
        self.assertEqual(d['weights'],self.decision(fs)['weights'])

    def test_does_not_mutate_source(self):
        before=deepcopy(self.frames);self.decision();self.assertEqual(self.frames,before)

class ContinuousPolicy(unittest.TestCase):
    def test_schedule_geometry_and_no_reanchor(self):
        p,d,s=a.demo();self.assertEqual([x['anchor'] for x in s],[252,272,292])
        self.assertEqual([x['entry'] for x in s],[253,273,293]);self.assertEqual(s[-1]['end'],313)
        d[1]['status']='unavailable'
        self.assertEqual(a.policy_path(p,d,s,'B0')['status'],'unavailable')
        self.assertEqual(d[2]['anchor'],292)

    def test_flat_zero_cost_never_manufactures_return(self):
        p,d,s=a.demo()
        for policy in a.POLICIES:self.assertAlmostEqual(a.policy_path(p,d,s,policy,0)['terminal_wealth'],1.0)

    def test_flat_roundtrip_exact_all_policies(self):
        p,d,s=a.demo();c=.001
        for policy in a.POLICIES:
            r=a.policy_path(p,d,s,policy,c)
            self.assertAlmostEqual(r['terminal_wealth'],(1-c)/(1+c),places=12)
            self.assertAlmostEqual(r['entries'][1]['fees'],0,places=12)

    def test_buyhold_paths_match_endpoint_oracle(self):
        p,d,s=a.demo('leadership_then_reversal');c=.001
        for policy,t in [('B0','BIL'),('B1','SPY')]:
            expected=p[t][313]/p[t][253]*(1-c)/(1+c)
            r=a.policy_path(p,d,s,policy,c);self.assertAlmostEqual(r['terminal_wealth'],expected,places=12)
            self.assertAlmostEqual(r['entries'][1]['fees'],0,places=12)

    def test_no_signal_close_fill(self):
        p,d,s=a.demo();p['SPY'][253]=200
        r=a.policy_path(p,d,s,'B1',0);self.assertAlmostEqual(r['terminal_wealth'],.5)

    def test_final_liquidation_is_in_drawdown(self):
        p,d,s=a.demo();c=.001;r=a.policy_path(p,d,s,'B1',c)
        self.assertAlmostEqual(r['max_drawdown'],r['terminal_wealth']-1,places=12)
        self.assertLess(r['terminal_wealth'],r['daily_wealth'][-1][1])

    def test_missing_future_mark_does_not_reset_capital(self):
        p,d,s=a.demo();del p['XLB'][280]
        for policy in a.POLICIES:
            r=a.policy_path(p,d,s,policy);self.assertEqual(r['status'],'unavailable');self.assertIsNone(r['terminal_wealth'])

    def test_cost_sensitivity_holds_for_fixed_choices(self):
        p,d,s=a.demo('leadership_then_reversal')
        for policy in a.POLICIES:
            values=[a.policy_path(p,d,s,policy,c)['terminal_wealth'] for c in (.0005,.001,.0025,.005)]
            self.assertTrue(all(a>=b-1e-12 for a,b in zip(values,values[1:])))

    def test_future_return_changes_wealth_not_frozen_choice(self):
        p,d,s=a.demo();original=deepcopy(d);p['XLB'][313]*=2
        self.assertGreater(a.policy_path(p,d,s,'B3',0)['terminal_wealth'],1.0)
        self.assertEqual(d,original)

    def test_every_output_denies_investment_authority(self):
        p,d,s=a.demo()
        for x in d+[a.policy_path(p,d,s,'B1')]:
            self.assertFalse(x['flags']['investment_authority']);self.assertFalse(x['flags']['native_scientific_qualification'])

class AdditionalRegressions(unittest.TestCase):
    def test_wrong_62_interval_integration_changes_cash_decision(self):
        fs=[a.frame(t,((i,100.0) for i in range(253))) for t in a.INPUTS]
        x=fs[0];rows=dict(x['rows']);rows[189]=200.;rows[190]=50.;x['rows']=tuple(rows.items())
        d=a.decide(fs,252,25308,tuple(range(320)))
        self.assertEqual(d['weights']['B4'],{'BIL':1.0})

    def test_selected_image_identity_is_not_forecast_admission(self):
        fs=[a.frame(t,((i,100.0) for i in range(253))) for t in a.INPUTS]
        d=a.decide(fs,252,25308,tuple(range(320)))
        self.assertEqual(len(d['selected_images']),13)
        self.assertFalse(d['flags']['source_rights_qualified'])
        self.assertFalse(d['flags']['native_adaptation_built'])

if __name__=='__main__':unittest.main()
