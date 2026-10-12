"""Offline integration: exact quota/normalizer modules, synthetic access/source.

The real authentication service, full gateway and production storage are NOT used.
No network, provider calls or shared filesystem state.
"""
from __future__ import annotations
import copy, datetime as dt, hashlib, importlib.util, json, os, sqlite3, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
NOW = dt.datetime(2026, 9, 16, 23, 55, tzinfo=dt.timezone.utc)

def load(name, path, expected_git=None, expected_sha=None):
    b=path.read_bytes()
    if expected_git:
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==expected_git
    if expected_sha:assert hashlib.sha256(b).hexdigest()==expected_sha
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

quota=load('r13_quota',ROOT/'upstream/view_ratelimit.py','5e33b4d213ff3b9497134343712921e3d3ac6b77')
tiers=load('r13_tiers',ROOT/'upstream/tiers.py','cf59370147d735a84f791ac7469c87136d7b9572')
corpus=load('r13_corpus',ROOT/'prior/upstream/corpus_review.py',expected_sha='58bfdaf91f1cb7f9a4f7e1f700bd90be3269fe9ea7d6cc156661a9a456b89d6f')
bridge=load('r13_prior_bridge',ROOT/'prior/r12/bridge.py',expected_sha='4a3376301c711512a5d4d96c07a32e5d7091dafbb6df193f4bb232944e068929')
from owner_adapter import OwnerAdapter

class Integration(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='rv-r13-');self.root=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{'MACRO_API_STATE_DIR':str(self.root/'state'),'RESEARCH_VIEW_HOURLY':'3'});self.env.start()
        # Package seams select the complete, unchanged real quota module. They are
        # not a substitute for executing the full engine/gateway packages.
        eng=types.ModuleType('engine');eng.__path__=[]
        rv=types.ModuleType('engine.research_vault');rv.__path__=[];rv.view_ratelimit=quota;eng.research_vault=rv
        self.modules=patch.dict(sys.modules,{'engine':eng,'engine.research_vault':rv,'engine.research_vault.view_ratelimit':quota});self.modules.start()
        self.acct={};exec(compile((ROOT/'upstream/brain_accounting_excerpt.py.txt').read_text(),'accounting_excerpt','exec'),self.acct)
        tiers.ROOT=self.root/'no-plan-catalog';tiers.reset_cache()
        self.ent={'tier':'pro','status':'active'};self.resolve_calls=[];self.scope_calls=[];self.db_calls=0;self.pdf_calls=0;self.peek_calls=0;self.charge_calls=0;self.metadata_calls=0
        self.use='allowed';self.after_charge=None;self.now=NOW
        pdf=(ROOT/'prior/demo/synthetic_original.pdf').read_bytes();body=(ROOT/'prior/demo/extracted_original.txt').read_text()
        self.pdf=pdf;self.body=body
        self.pdf_hash=hashlib.sha256(pdf).hexdigest();self.body_hash=hashlib.sha256(body[:60000].encode()).hexdigest()
        self.item={'id':'example-report','title':'Industrial operations review','institution':'Example Research Laboratory','summary_points':['General operating conditions.'],'published_at':'2026-09-16T12:00:00Z','side':'independent'}
        self.scope={'decision':'allowed','generation':'fixture-v1','items':{'example-report':{'pdf_sha256':self.pdf_hash,'body_sha256':self.body_hash,'catalog':self.item}}}
        self.db=self.root/'corpus.sqlite';c=corpus.open_db(self.db);corpus.upsert(c,self.item,body,facts={'content_sha256':self.pdf_hash,'char_count':len(body),'pages':2,'text_layer':'text'});c.close()
        self.owners={'corpus':corpus,'bridge':bridge,'normalize_tier':tiers.normalize_tier,'resolve_tier':self.resolve,'source_scope':self.source_scope,'connection_factory':self.connect,'source_reader':self.read_pdf,'peek_view':self.peek,'charge_view':self.charge,'metadata_search':self.metadata}
        self.adapter=OwnerAdapter(**self.owners)
    def tearDown(self):self.modules.stop();self.env.stop();self.tmp.cleanup()
    def resolve(self,user_id):self.resolve_calls.append(user_id);return copy.deepcopy(self.ent)
    def source_scope(self,user_id,purpose):
        self.scope_calls.append((user_id,purpose))
        if self.use!='allowed':return {'decision':self.use}
        return copy.deepcopy(self.scope)
    def connect(self):
        self.db_calls+=1
        c=sqlite3.connect(self.db.as_uri()+"?mode=ro",uri=True)
        c.row_factory=sqlite3.Row
        c.execute("PRAGMA query_only=ON")
        return c
    def read_pdf(self,rid):self.pdf_calls+=1;return self.pdf
    def peek(self,uid,now):self.peek_calls+=1;return self.acct['_peek_report_view'](uid,now)
    def charge(self,uid,now):
        self.charge_calls+=1;r=self.acct['_charge_report_view'](uid,now)
        if self.after_charge:self.after_charge()
        return r
    def metadata(self,**kw):self.metadata_calls+=1;return {'status':'metadata_control','query':kw['query'],'results':[]}
    def discover(self,**kw):return self.adapter.dispatch(user_id=kw.pop('user_id','user-a'),scope='source_text',action='discover',query=kw.pop('query','orionquartz margin'),now=self.now,**kw)
    def select(self):return self.discover()['items'][0]['selection']
    def read(self,selection=None,**kw):return self.adapter.dispatch(user_id=kw.pop('user_id','user-a'),scope='source_text',action='read',selection=selection or self.select(),now=self.now,**kw)
    def exhaust(self,uid='user-a'):
        for _ in range(3):quota.allow(uid,'brain:'+uid,now=self.now)
    def count(self,uid='user-a'):
        p=quota._user_file(uid,quota._period_key(self.now));return json.loads(p.read_text())['count'] if p.exists() else 0
    def assert_no_body(self,r):self.assertNotIn('31%',json.dumps(r));self.assertEqual(r.get('passages',[]),[])

    def test_01_missing_identity_refused_before_any_access(self):
        r=self.discover(user_id='');self.assertEqual(r['status'],'essential_required');self.assertFalse(self.resolve_calls);self.assertEqual(self.db_calls,0)
    def test_02_free_refused(self):
        self.ent['tier']='free';self.assertEqual(self.discover()['status'],'essential_required');self.assertEqual(self.peek_calls,0)
    def test_03_essential_source_refused(self):
        self.ent['tier']='essential';self.assertEqual(self.discover()['status'],'pro_required');self.assertEqual(self.db_calls,0)
    def test_04_legacy_insider_metadata_retained(self):
        self.ent['tier']='insider';r=self.adapter.dispatch(user_id='a',scope='metadata',action='discover',query='margin',now=self.now);self.assertEqual(r['status'],'metadata_control');self.assertEqual(self.peek_calls,0)
    def test_05_legacy_insider_source_not_promoted(self):
        self.ent['tier']='insider';self.assertEqual(self.discover()['status'],'pro_required')
    def test_06_pro_trialing_allowed(self):
        self.ent['status']='trialing';self.assertEqual(self.discover()['status'],'ready')
    def test_07_cancelled_pro_denied(self):
        self.ent['status']='canceled';self.assertEqual(self.discover()['status'],'essential_required')
    def test_08_missing_status_preserves_existing_default(self):
        self.ent.pop('status');self.assertEqual(self.discover()['status'],'ready')
    def test_09_unlimited_preserved(self):
        self.ent['tier']='unlimited';self.assertEqual(self.discover()['status'],'ready')
    def test_10_unknown_tier_does_not_become_pro(self):
        self.ent['tier']='superpro';self.assertEqual(self.discover()['status'],'essential_required')
    def test_11_missing_resolver_fails_closed(self):
        self.adapter.owners['resolve_tier']=lambda uid:None;self.assertEqual(self.discover()['status'],'entitlement_unavailable');self.assertEqual(self.db_calls,0)
    def test_12_raised_resolver_fails_closed(self):
        def broken(uid):raise OSError('fixture')
        self.adapter.owners['resolve_tier']=broken;self.assertEqual(self.discover()['status'],'entitlement_unavailable')
    def test_13_explicit_unknown_scope_not_escalated(self):
        r=self.adapter.dispatch(user_id='user-a',scope='automatic',action='discover',query='margin',now=self.now);self.assertEqual(r['status'],'scope_not_selected');self.assertEqual(self.db_calls,0)
    def test_14_source_grant_unknown_fails(self):
        self.use='unknown';self.assertEqual(self.discover()['status'],'scope_unavailable');self.assertEqual(self.db_calls,0)
    def test_15_source_grant_denied_fails(self):
        self.use='denied';self.assertEqual(self.discover()['status'],'denied');self.assertEqual(self.db_calls,0)
    def test_16_discovery_does_not_debit(self):
        r=self.discover();self.assertEqual(r['status'],'ready');self.assertEqual(self.charge_calls,0);self.assertEqual(self.count(),0);self.assert_no_body(r)
    def test_17_exhausted_discovery_no_body_or_catalog_probe(self):
        self.exhaust();r=self.discover();self.assertEqual(r['status'],'view_limit_reached');self.assertFalse(self.scope_calls);self.assertEqual(self.db_calls,0)
    def test_18_exhausted_nonmatching_query_same_denial(self):
        self.exhaust();r=self.discover(query='unseenxyz');self.assertEqual(r['status'],'view_limit_reached');self.assertEqual(self.db_calls,0)
    def test_19_exhausted_read_precedes_source_fetch(self):
        s=self.select();self.exhaust();self.db_calls=0;self.scope_calls=[];r=self.read(s);self.assertEqual(r['status'],'view_limit_reached');self.assertEqual(self.db_calls,0);self.assertEqual(self.pdf_calls,0)
    def test_20_one_read_exact_one_owner_allow(self):
        r=self.read();self.assertEqual(r['status'],'matched');self.assertEqual(self.charge_calls,1);self.assertEqual(self.count(),1);self.assertEqual(r['quota']['remaining'],2)
    def test_21_last_allowed_read_still_served(self):
        s=self.select();quota.allow('user-a','brain:user-a',now=self.now);quota.allow('user-a','brain:user-a',now=self.now)
        r=self.read(s);self.assertEqual(r['status'],'matched');self.assertEqual(r['quota']['remaining'],0);self.assertEqual(self.count(),3)
    def test_22_next_read_denied_and_not_double_debited(self):
        s=self.select();self.read(s);self.read(s);self.read(s);r=self.read(s);self.assertEqual(r['status'],'view_limit_reached');self.assertEqual(self.charge_calls,3);self.assertEqual(self.count(),3)
    def test_23_user_b_has_separate_allowance(self):
        s=self.select();self.exhaust('user-a');r=self.read(s,user_id='user-b');self.assertEqual(r['status'],'matched');self.assertEqual(self.count('user-b'),1);self.assertEqual(self.count('user-a'),3)
    def test_24_next_hour_resets_existing_period(self):
        s=self.select();self.exhaust();self.now+=dt.timedelta(hours=1);self.assertEqual(self.read(s)['status'],'matched');self.assertEqual(self.count(),1)
    def test_25_no_match_does_not_debit(self):
        s=self.select();s['query']='unseenxyz';r=self.read(s);self.assertEqual(r['status'],'no_matching_passage');self.assertEqual(self.charge_calls,0)
    def test_26_source_mismatch_does_not_debit(self):
        s=self.select();self.pdf+=b'changed';r=self.read(s);self.assertEqual(r['status'],'source_mismatch');self.assertEqual(self.charge_calls,0)
    def test_27_stale_generation_does_not_debit(self):
        s=self.select();self.scope['generation']='fixture-v2';r=self.read(s);self.assertEqual(r['status'],'selection_stale');self.assertEqual(self.charge_calls,0)
    def test_28_revoked_tier_at_read_does_not_probe(self):
        s=self.select();self.ent['tier']='essential';self.db_calls=0;r=self.read(s);self.assertEqual(r['status'],'pro_required');self.assertEqual(self.db_calls,0)
    def test_29_access_loss_during_charge_withholds_no_refund(self):
        s=self.select();self.after_charge=lambda:self.ent.update(tier='essential');r=self.read(s);self.assertEqual(r['status'],'access_changed_after_accounting');self.assertEqual(self.count(),1);self.assert_no_body(r)
    def test_30_real_owner_failopen_io_policy_preserved(self):
        s=self.select();bad=self.root/'not_a_directory';bad.write_text('x')
        with patch.dict(os.environ,{'MACRO_API_STATE_DIR':str(bad)}),self.assertLogs(quota.log,level='ERROR'):
            r=self.read(s)
        self.assertEqual(r['status'],'matched');self.assertEqual(self.charge_calls,1);self.assertEqual(r['accounting']['persistence'],'not_attested');self.assertFalse((bad/'research_view_rl').exists())
    def test_31_success_boolean_not_persistence_receipt(self):
        r=self.read();self.assertEqual(r['status'],'matched');self.assertEqual(r['accounting']['persistence'],'not_attested');self.assertNotIn('charged',r['accounting'])
    def test_32_false_tuple_is_not_truthy_authorization(self):
        s=self.select();self.adapter.owners['charge_view']=lambda *x:(False,{'remaining':0,'limit':3})
        r=self.read(s);self.assertEqual(r['status'],'view_denied');self.assert_no_body(r)
    def test_33_unknown_callback_effect_not_retried(self):
        s=self.select();calls=[]
        def uncertain(*x):calls.append(1);raise OSError('fixture effect unknown')
        self.adapter.owners['charge_view']=uncertain;r=self.read(s);self.assertEqual(r['status'],'accounting_unknown');self.assertEqual(calls,[1]);self.assert_no_body(r)
    def test_34_native_wrapper_exception_failopen_preserved(self):
        s=self.select()
        with patch.object(quota,'allow',side_effect=OSError('fixture')):r=self.read(s)
        self.assertEqual(r['status'],'matched');self.assertIsNone(r['quota']['remaining']);self.assertEqual(r['accounting']['persistence'],'not_attested')
    def test_35_unknown_preflight_preserves_owner_failopen(self):
        with patch.object(quota,'peek',side_effect=OSError('fixture')):r=self.discover()
        self.assertEqual(r['status'],'ready');self.assertEqual(self.charge_calls,0)
    def test_36_metadata_allowed_when_views_exhausted(self):
        self.exhaust();r=self.adapter.dispatch(user_id='user-a',scope='metadata',action='discover',query='margin',now=self.now);self.assertEqual(r['status'],'metadata_control');self.assertEqual(self.peek_calls,0)
    def test_37_ledger_uses_existing_brain_prefix(self):
        self.read();names=[p.name for p in quota._rl_dir().glob('*.json')];expected='vip_'+hashlib.sha256(b'brain:user-a').hexdigest()[:16]+'_'+quota._period_key(self.now)+'.json';self.assertIn(expected,names);self.assertEqual(len(names),2)
    def test_38_document_and_source_unchanged_by_access(self):
        before=self.db.read_bytes();self.read();self.assertEqual(self.db.read_bytes(),before);self.assertEqual(hashlib.sha256(self.pdf).hexdigest(),self.pdf_hash)
    def test_39_denied_empty_missing_inputs_are_not_probe_oracles(self):
        self.exhaust();r=self.adapter.dispatch(user_id='user-a',scope='source_text',action='read',selection=None,now=self.now);self.assertEqual(r['status'],'view_limit_reached');self.assertEqual(self.db_calls,0)
    def test_40_invalid_action_refused(self):
        r=self.adapter.dispatch(user_id='user-a',scope='source_text',action='trade',query='margin',now=self.now);self.assertEqual(r['status'],'invalid_request');self.assertEqual(self.db_calls,0)
    def test_41_current_source_use_revoked_during_charge(self):
        s=self.select();self.after_charge=lambda:setattr(self,'use','denied');r=self.read(s);self.assertEqual(r['status'],'access_changed_after_accounting');self.assert_no_body(r);self.assertEqual(self.count(),1)
    def test_42_current_request_clock_passed_to_both_owner_calls(self):
        seen=[];original_peek=self.peek;original_charge=self.charge
        self.adapter.owners['peek_view']=lambda u,n:(seen.append(n),original_peek(u,n))[1]
        self.adapter.owners['charge_view']=lambda u,n:(seen.append(n),original_charge(u,n))[1]
        self.read();self.assertTrue(seen);self.assertTrue(all(n is self.now for n in seen))
    def test_43_prior_reader_is_not_called_after_bridge_debit(self):
        self.adapter.owners['full_report_reader']=lambda **kw:(_ for _ in ()).throw(AssertionError('double reader path'))
        r=self.read();self.assertEqual(r['status'],'matched');self.assertEqual(self.charge_calls,1)
    def test_44_malformed_charge_return_does_not_leak(self):
        s=self.select();self.adapter.owners['charge_view']=lambda *x:("allowed",{})
        self.assertEqual(self.read(s)['status'],'accounting_unknown')
    def test_45_essential_metadata_response_unchanged(self):
        self.ent['tier']='essential';r=self.adapter.dispatch(user_id='user-a',scope='metadata',action='discover',query='q',now=self.now)
        self.assertEqual(r,{'status':'metadata_control','query':'q','results':[]});self.assertEqual(self.metadata_calls,1);self.assertFalse(self.scope_calls)
    def test_46_body_locator_still_exact(self):
        r=self.read();p=r['passages'][0];self.assertEqual(p['text'],self.body[p['locator']['start_char']:p['locator']['end_char']]);self.assertEqual(p['locator']['page'],2)

if __name__=='__main__':unittest.main(verbosity=2)
