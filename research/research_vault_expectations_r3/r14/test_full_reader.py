"""Full pending Brain report reader + actual local store and ledger.

Synthetic source/identity, not real gateway authentication or product acceptance.
Expected source files are hash checked by run_review.py before these imports.
"""
from __future__ import annotations
import copy, hashlib, json, os, sqlite3, sys, tempfile, types, unittest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch

ROOT=Path(os.environ['RV_R14_ROOT'])
for name in ('engine','engine.research_vault','engine.neuralweb'):
    module=types.ModuleType(name); module.__path__=[]; sys.modules[name]=module

def load(name,filename):
    m=types.ModuleType(name);m.__file__=str(ROOT/'upstream'/filename);sys.modules[name]=m
    exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec'),m.__dict__)
    parent,_,child=name.rpartition('.')
    if parent in sys.modules:setattr(sys.modules[parent],child,m)
    return m

store_mod=load('engine.research_vault.r2_store','r2_store.py')
corpus=load('engine.research_vault.corpus','corpus_pending.py')
limiter=load('engine.research_vault.view_ratelimit','view_ratelimit.py')
brain=load('engine.neuralweb.brain_market_intel',os.environ.get('RV_R14_BRAIN','brain_pending.py'))
from source_guard import make_guard
NOW=datetime(2026,9,16,12,tzinfo=timezone.utc)

class FullReaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='rv-r14-case-');self.root=Path(self.tmp.name).resolve()
        self.store=store_mod.LocalStore(self.root/'store')
        self.env=patch.dict(os.environ,{'MACRO_API_STATE_DIR':str(self.root/'state'),'RESEARCH_VIEW_HOURLY':'2','RESEARCH_LOCAL_STORE':str(self.store.root)})
        self.env.start();corpus.reset_cache()
        self.pdf=(ROOT/'fixtures/source.pdf').read_bytes();self.body=(ROOT/'fixtures/source.txt').read_text()
        self.item={'id':'synthetic-reader','title':'Industrial operations review','institution':'Fictional Test Publisher','published_at':'2026-09-16T12:00:00Z','side':'independent','summary_points':['General manufacturing conditions.']}
        self.query='orionquartz margin'
        self.expected={'pdf_sha256':hashlib.sha256(self.pdf).hexdigest(),'body_sha256':hashlib.sha256(self.body.encode()).hexdigest(),'catalog':copy.deepcopy(self.item),'byte_length':len(self.pdf)}
        self.scope={'decision':'allowed','generation':'g1','items':{self.item['id']:copy.deepcopy(self.expected)}}
        self.selection={'id':self.item['id'],'query':self.query,'generation':'g1','pdf_sha256':self.expected['pdf_sha256'],'body_sha256':self.expected['body_sha256']}
        self._publish();self.calls=[]
        real_allow=limiter.allow
        def counted(*args,**kwargs):
            self.calls.append('allow');return real_allow(*args,**kwargs)
        self.spy=patch.object(limiter,'allow',side_effect=counted);self.spy.start()
        self.after_charge=None

    def _publish(self):
        p=self.root/'data/research_vault/catalog.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'items':[self.item]}))
        db=self.root/'corpus.sqlite';c=corpus.open_db(db)
        corpus.upsert(c,self.item,self.body,facts={'pages':2,'char_count':len(self.body),'content_sha256':self.expected['pdf_sha256'],'text_layer':'text'})
        c.close();self.store.put_bytes('research_vault/corpus.sqlite',db.read_bytes());self.store.put_bytes('research_vault/synthetic-reader.pdf',self.pdf);corpus.reset_cache()

    def tearDown(self):
        corpus.reset_cache();self.spy.stop();self.env.stop();self.tmp.cleanup()
    def guard(self):
        return make_guard(selection=copy.deepcopy(self.selection),scope_provider=lambda purpose:copy.deepcopy(self.scope),store=self.store,maximum_source_bytes=30_000_000)
    def read(self,guard=True,query=None,uid='synthetic-user'):
        args={'query':self.query if query is None else query,'mode':'report','report_id':self.item['id'],'user_ctx':{'user_id':uid},'now':NOW}
        if guard:args['_source_guard']=self.guard()
        return brain.search_research(self.root,**args)
    def count(self):
        p=self.root/'state/research_view_rl/vh_synthetic-user_2026-09-16T12.json'
        return json.loads(p.read_text())['count'] if p.exists() else 0
    def assert_empty(self,r):
        self.assertFalse((r.get('report')or{}).get('body_text'));self.assertFalse((r.get('evidence')or{}).get('passages'))

    def test_legacy_reader_works_without_new_guard(self):
        r=self.read(False);self.assertEqual(r['evidence']['status'],'matched');self.assertEqual(self.count(),1)
    def test_legacy_no_match_is_not_charged(self):
        r=self.read(False,query='nonexistentquartz');self.assertEqual(r['evidence']['status'],'no_matching_passage');self.assertEqual(self.count(),0)
    def test_legacy_generic_preserved(self):
        r=self.read(False,query='');self.assertIsNone(r['evidence']);self.assertTrue(r['report']['body_text']);self.assertEqual(self.count(),1)
    def test_legacy_missing_identity(self):
        r=self.read(False,uid='');self.assertEqual(r['error'],'pro_required');self.assertEqual(self.count(),0)
    def test_guarded_full_reader_returns_exact_page(self):
        r=self.read();self.assertEqual(r['evidence']['status'],'matched');p=r['evidence']['passages'][0];loc=p['locator'];self.assertEqual(loc['page'],2);self.assertEqual(p['text'],self.body[loc['start_char']:loc['end_char']]);self.assertEqual(self.count(),1)
    def test_guarded_reader_has_one_debit(self):
        self.read();self.assertEqual(self.calls,['allow'])
    def test_last_permitted_slot_still_served(self):
        self.read();r=self.read();self.assertTrue(r['report']['body_text']);self.assertEqual(r['quota']['remaining'],0);self.assertEqual(self.count(),2)
    def test_exhausted_next_read_denied(self):
        self.read();self.read();r=self.read();self.assertEqual(r['error'],'view_limit_reached');self.assertEqual(len(self.calls),2);self.assert_empty(r)
    def test_missing_original_before_debit(self):
        (self.store.root/'research_vault/synthetic-reader.pdf').unlink();r=self.read();self.assertEqual(r['error'],'source_unavailable');self.assertEqual(self.count(),0);self.assert_empty(r)
    def test_modified_original_before_debit(self):
        self.store.put_bytes('research_vault/synthetic-reader.pdf',b'%PDF- altered');r=self.read();self.assertIn(r['error'],('source_unavailable','source_mismatch'));self.assertEqual(self.count(),0);self.assert_empty(r)
    def test_source_hash_mismatch_before_debit(self):
        changed=dict(self.expected);changed['pdf_sha256']='f'*64
        self.scope['items'][self.item['id']]=changed;r=self.read();self.assertEqual(r['error'],'selection_stale');self.assertEqual(self.count(),0)
    def test_stored_body_mismatch_before_debit(self):
        self.body+=' changed';self._publish();r=self.read();self.assertEqual(r['error'],'source_mismatch');self.assertEqual(self.count(),0)
    def test_stale_selection_before_debit(self):
        self.scope['generation']='g2';r=self.read();self.assertEqual(r['error'],'selection_stale');self.assertEqual(self.count(),0)
    def test_removed_source_access(self):
        self.scope['items']={};r=self.read();self.assertEqual(r['error'],'selection_stale');self.assertEqual(self.count(),0)
    def test_denied_scope_before_body_read(self):
        self.scope['decision']='denied'
        with patch.object(corpus,'get_evidence_document',side_effect=AssertionError('must not read body')) as get:
            r=self.read();self.assertEqual(r['error'],'source_access_denied');get.assert_not_called();self.assertEqual(self.count(),0)
    def test_catalog_identity_drift(self):
        self.item['institution']='Different Publisher';self._publish();r=self.read();self.assertEqual(r['error'],'source_mismatch');self.assertEqual(self.count(),0)
    def test_selection_query_not_silently_changed(self):
        r=self.read(query='factory schedule');self.assertEqual(r['error'],'selection_stale');self.assertEqual(self.count(),0)
    def test_generic_request_does_not_bypass_source_selection(self):
        r=self.read(query='summarize this report');self.assertEqual(r['error'],'source_request_invalid');self.assertEqual(self.count(),0)
    def test_guard_not_ignored_in_metadata_mode(self):
        r=brain.search_research(self.root,query=self.query,now=NOW,_source_guard=self.guard());self.assertEqual(r['error'],'source_request_invalid')
    def test_no_match_not_debited_with_guard(self):
        self.query='nonexistentquartz';self.selection['query']=self.query;r=self.read();self.assertEqual(r['evidence']['status'],'no_matching_passage');self.assertEqual(self.count(),0)
    def test_revoked_during_selection_before_debit(self):
        real=brain._fit_evidence_response_budget
        def revoke(r):
            value=real(r);self.scope['decision']='denied';return value
        with patch.object(brain,'_fit_evidence_response_budget',side_effect=revoke):r=self.read()
        self.assertEqual(r['error'],'source_access_denied');self.assertEqual(self.count(),0);self.assert_empty(r)
    def test_revoked_during_accounting_withholds_not_refunds(self):
        original=limiter.allow.side_effect
        def revoke(*a,**k):
            r=original(*a,**k);self.scope['decision']='denied';return r
        limiter.allow.side_effect=revoke;r=self.read();self.assertEqual(r['error'],'access_changed_after_accounting');self.assertEqual(self.count(),1);self.assertEqual(len(self.calls),1);self.assert_empty(r)
    def test_original_read_uses_strict_bound(self):
        with patch.object(self.store,'get_bytes_strict_bounded',wraps=self.store.get_bytes_strict_bounded) as spy:
            self.read();self.assertGreaterEqual(spy.call_count,1)
            self.assertEqual(spy.call_args.kwargs['expected_byte_length'],len(self.pdf));self.assertEqual(spy.call_args.kwargs['max_byte_length'],30_000_000)
    def test_output_budget_preserved(self):
        r=self.read();self.assertLessEqual(brain._response_string_total(r),brain.REPORT_BODY_MAX_CHARS)

if __name__=='__main__':unittest.main()
