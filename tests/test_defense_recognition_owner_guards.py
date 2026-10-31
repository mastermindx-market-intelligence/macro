"""Synthetic owner-envelope regressions; these do not admit real market data."""
from copy import deepcopy
from pathlib import Path
import importlib.util,json,os,unittest
ROOT=Path(os.environ.get('DFE_TEST_ROOT',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('defense_guard_subject',ROOT/'engine/government_revenue/defense_economics.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
NOW='2026-10-13T03:00:00Z'
SUBJECT={'issuer_id':'ISS:US-XNYS-NOC','security_id':'SEC:US-XNYS-NOC'}
def inputs_and_bindings(*,relative=False,basis='raw'):
    bindings={'identity':{'sha256':'a'*64,**SUBJECT},'market':{'sha256':'b'*64,'owner_family':'market','price_adjustment':basis,**SUBJECT}}
    response={'state':'supported','owner_ref':'market','observed_at':'2026-10-13T02:00:00Z','security_id':SUBJECT['security_id'],'price_adjustment':basis,'price_vintage':'2026-10-12T23:00:00Z','window_sessions':20,'return_pct':-6.64,'market_as_of':'2026-10-12','previous_session':'2026-09-14','sessions_behind':0}
    if relative:
        response.update(relative_return_pct=0,benchmark='SEC:US-ARCX-SPY')
        bindings['market'].update(benchmark='SEC:US-ARCX-SPY',benchmark_price_adjustment=basis,benchmark_window_sessions=20)
    axis={'state':'supported','display_scope':'government_revenue_entitled','owner_ref':'market','observed_at':response['observed_at'],'price_response':response}
    inputs={'NOC':{'identity_owner_ref':'identity','identity':{'identity_mode':'current','issuer_binding':{'issuer_id':SUBJECT['issuer_id']},'security_id':SUBJECT['security_id']},'axes':{'recognition':axis}}}
    return inputs,bindings

def compose(inputs,bindings):return module.compose_defense_economics(inputs,generated_at=NOW,source_bindings=bindings)
def profile(payload):return next(v for v in payload['profiles'] if v['ticker_display']=='NOC')
def response(payload):return profile(payload)['axes']['recognition']['price_response']
class RecognitionOwnerGuards(unittest.TestCase):
    def test_matching_owner_basis_quotes_standalone_raw_and_adjusted(self):
        for basis in ('raw','split_and_dividend_adjusted'):
            with self.subTest(basis=basis):
                x,b=inputs_and_bindings(basis=basis);p=compose(x,b)
                self.assertEqual(response(p)['state'],'supported');self.assertEqual(response(p)['price_adjustment'],basis)
                self.assertTrue(module.validate_defense_economics_payload(p))
    def test_missing_or_mismatched_owner_basis_refuses(self):
        for value in (None,'','sadj','unknown_unqualified'):
            with self.subTest(value=value):
                x,b=inputs_and_bindings();r=x['NOC']['axes']['recognition']['price_response']
                if value is None:b['market'].pop('price_adjustment')
                else:r['price_adjustment']=value
                self.assertEqual(response(compose(x,b))['state'],'missing_owner')
    def test_zero_relative_return_needs_nonempty_matched_benchmark(self):
        for value in (None,'','SEC:US-ARCX-ITA'):
            with self.subTest(value=value):
                x,b=inputs_and_bindings(relative=True);x['NOC']['axes']['recognition']['price_response']['benchmark']=value
                self.assertEqual(response(compose(x,b))['state'],'missing_owner')
    def test_relative_return_missing_owner_relation_refuses(self):
        for field in ('benchmark','benchmark_price_adjustment','benchmark_window_sessions'):
            with self.subTest(field=field):
                x,b=inputs_and_bindings(relative=True);b['market'].pop(field)
                self.assertEqual(response(compose(x,b))['state'],'missing_owner')
    def test_relative_return_mismatched_basis_or_window_refuses(self):
        for change in ({'benchmark_price_adjustment':'sadj'},{'benchmark_window_sessions':21}):
            with self.subTest(change=change):
                x,b=inputs_and_bindings(relative=True);b['market'].update(change)
                self.assertEqual(response(compose(x,b))['state'],'missing_owner')
    def test_matching_relative_owner_relation_roundtrips_and_validates_schema(self):
        x,b=inputs_and_bindings(relative=True);p=compose(x,b)
        self.assertEqual(response(p)['relative_return_pct'],0)
        self.assertEqual(p['source_bindings']['market']['benchmark_window_sessions'],20)
        self.assertTrue(module.validate_defense_economics_payload(p))
        from jsonschema import Draft202012Validator
        Draft202012Validator(json.loads((ROOT/'contracts/government_revenue/defense_economics.v1.schema.json').read_text())).validate(p)
    def test_invalid_benchmark_window_binding_refuses_finite_json(self):
        for v in (0,-1,2.5,True,'20'):
            with self.subTest(v=v):
                x,b=inputs_and_bindings(relative=True);b['market']['benchmark_window_sessions']=v
                with self.assertRaises(ValueError):compose(x,b)
    def test_unbound_or_wrong_identity_demotes_recognition(self):
        for mutation in ('unbound','issuer','security'):
            with self.subTest(mutation=mutation):
                x,b=inputs_and_bindings()
                if mutation=='unbound':x['NOC']['identity_owner_ref']='unknown'
                elif mutation=='issuer':b['identity']['issuer_id']='ISS:US-XNYS-LMT'
                else:b['identity']['security_id']='SEC:US-XNYS-LMT'
                p=compose(x,b);a=profile(p)['axes']['recognition']
                self.assertEqual(a['state'],'unreviewed');self.assertEqual(a['reason_code'],'issuer_identity_unqualified')
                self.assertNotIn('price_response',a);self.assertNotIn('valuation_scenario',a)
                self.assertEqual(a['expectations_kind'],'not_observed');self.assertTrue(module.validate_defense_economics_payload(p))
    def test_rehashed_supported_recognition_with_null_identity_refuses(self):
        x,b=inputs_and_bindings();p=compose(x,b);r=profile(p)
        for key in ('issuer_id','security_id','identity_owner_ref','identity_mode'):r[key]=None
        p['content_id']=module.defense_economics_content_id(p)
        with self.assertRaises(ValueError):module.validate_defense_economics_payload(p)
    def test_rehashed_owner_relative_relation_mismatch_refuses(self):
        x,b=inputs_and_bindings(relative=True);p=compose(x,b)
        p['source_bindings']['market']['benchmark_price_adjustment']='sadj'
        p['content_id']=module.defense_economics_content_id(p)
        with self.assertRaises(ValueError):module.validate_defense_economics_payload(p)
    def test_supported_response_does_not_promote_expectations(self):
        x,b=inputs_and_bindings(relative=True);r=profile(compose(x,b))
        self.assertEqual(r['axes']['recognition']['expectations_kind'],'not_observed')
        self.assertFalse(r['authority']['can_originate_signal']);self.assertIsNone(r['program_workshare'])
if __name__=='__main__':unittest.main(verbosity=2)
