"""Actual local PDF -> extraction -> corpus -> selector; permission/meter are fixtures."""
from pathlib import Path
import copy, dataclasses, hashlib, json, sqlite3, tempfile, unittest
import bridge
from fixtures import load_corpus, make_source, populate, catalog_item

class BridgeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='rv-r12-originals-')
        p=Path(cls.temp.name);cls.pdf=p/'original.pdf';cls.corrected=p/'corrected.pdf'
        cls.source=make_source(cls.pdf);cls.revised=make_source(cls.corrected,29)
        cls.corpus=load_corpus()
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='rv-r12-db-');self.addCleanup(self.tmp.cleanup)
        self.db=Path(self.tmp.name)/'corpus.sqlite';self.item=catalog_item()
        populate(self.corpus,self.db,self.item,self.source)
        self.scope={'decision':'allowed','generation':'review-g1','items':{
            self.item['id']:{'catalog':self.item,'pdf_sha256':self.source['pdf_sha256'],
                             'body_sha256':self.source['body_sha256']}}}
        self.counts={'scope':0,'connections':0,'source_reads':0,'meter':0}
        self.meter_answer=True;self.read_file=self.pdf
        def scope(purpose):
            self.counts['scope']+=1;return copy.deepcopy(self.scope)
        def conn():
            self.counts['connections']+=1
            c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row;return c
        def source(rid):
            self.counts['source_reads']+=1;return self.read_file.read_bytes()
        def meter(rid):
            self.counts['meter']+=1;return self.meter_answer
        self.scope_fn=scope;self.conn_fn=conn;self.source_fn=source;self.meter_fn=meter
    def discover(self,**kw):
        args={'corpus':self.corpus,'scope_provider':self.scope_fn,'connection_factory':self.conn_fn,
              'query':'orionquartz margin','scope':'source_text','limit':3}
        args.update(kw);return bridge.discover(**args)
    def selected(self):
        d=self.discover();self.assertEqual(d['status'],'ready');return d['items'][0]['selection']
    def read(self,ticket,**kw):
        args={'corpus':self.corpus,'scope_provider':self.scope_fn,'connection_factory':self.conn_fn,
              'selection':ticket,'source_reader':self.source_fn,'meter':self.meter_fn}
        args.update(kw);return bridge.read_selected(**args)
    def test_original_pdf_body_only_can_be_discovered(self):
        text=json.dumps(self.item).lower();self.assertNotIn('orionquartz',text);self.assertNotIn('margin',text)
        d=self.discover();self.assertEqual(d['status'],'ready');self.assertEqual(d['items'][0]['id'],'example-report')
        self.assertEqual(self.counts['meter'],0);self.assertEqual(self.counts['source_reads'],0)
    def test_discovery_does_not_return_unmetered_passages(self):
        d=self.discover();self.assertEqual(d['status'],'ready')
        s=json.dumps(d);self.assertNotIn('31%',s);self.assertNotIn('commissioning',s);self.assertNotIn('"excerpt"',s)
    def test_existing_selector_returns_page_two_literal_and_hashes(self):
        r=self.read(self.selected());self.assertEqual(r['status'],'matched');p=r['passages'][0]
        self.assertEqual(p['locator']['page'],2);a,b=p['locator']['start_char'],p['locator']['end_char']
        self.assertEqual(p['text'],self.source['body'][a:b]);self.assertIn('31% to 28%',p['text'])
        self.assertEqual(r['source_binding']['content_sha256'],hashlib.sha256(self.pdf.read_bytes()).hexdigest())
        self.assertEqual(r['source_binding']['stored_body_sha256'],self.source['body_sha256'])
        self.assertEqual(self.counts['meter'],1)
    def test_denied_discovery_never_opens_corpus(self):
        self.scope={'decision':'denied'};r=self.discover()
        self.assertEqual(r['status'],'denied');self.assertEqual(self.counts['connections'],0)
        self.assertNotIn('example-report',json.dumps(r))
    def test_scope_resolver_failure_is_not_permission(self):
        def fail(purpose):raise RuntimeError('private detail must not escape')
        r=self.discover(scope_provider=fail);self.assertEqual(r['status'],'scope_unavailable')
        self.assertNotIn('private detail',json.dumps(r));self.assertEqual(self.counts['connections'],0)
    def test_no_implicit_body_escalation(self):
        r=self.discover(scope='metadata');self.assertEqual(r['status'],'scope_not_selected');self.assertEqual(self.counts['connections'],0)
    def test_empty_allowed_set_does_not_open_corpus(self):
        self.scope['items']={};r=self.discover();self.assertEqual(r['status'],'ready');self.assertEqual(r['items'],[])
        self.assertEqual(self.counts['connections'],0)
    def test_healthy_no_match_not_original_absence(self):
        r=self.discover(query='unmentionedquartz');self.assertEqual(r['status'],'ready');self.assertEqual(r['items'],[])
        self.assertEqual(r['search_surface'],'stored_corpus_text');self.assertIs(r['complete_original_search'],False)
    def test_missing_fts_is_unavailable(self):
        c=sqlite3.connect(self.db);c.execute('DROP TABLE documents_fts');c.commit();c.close()
        r=self.discover();self.assertEqual(r['status'],'search_unavailable');self.assertEqual(r['items'],[])
    def test_noneligible_candidate_does_not_consume_limit(self):
        c=self.corpus.open_db(self.db)
        for i in range(5):
            x=catalog_item('hidden-'+str(i));x['title']='Orionquartz margin orionquartz margin'
            self.corpus.upsert(c,x,'orionquartz margin '*12,facts={'content_sha256':self.source['pdf_sha256']})
        c.close();r=self.discover(limit=1)
        self.assertEqual(r['status'],'ready');self.assertEqual([x['id'] for x in r['items']],['example-report'])
    def test_scope_generation_change_requires_rediscovery(self):
        t=self.selected();self.scope['generation']='review-g2';r=self.read(t)
        self.assertEqual(r['status'],'selection_stale');self.assertEqual(self.counts['source_reads'],0);self.assertEqual(self.counts['meter'],0)
    def test_permission_removed_after_discovery(self):
        t=self.selected();self.scope={'decision':'denied'};r=self.read(t)
        self.assertEqual(r['status'],'denied');self.assertEqual(self.counts['source_reads'],0);self.assertEqual(self.counts['meter'],0)
    def test_id_removed_after_discovery(self):
        t=self.selected();self.scope['items']={};r=self.read(t)
        self.assertEqual(r['status'],'selection_stale');self.assertEqual(self.counts['meter'],0)
    def test_source_byte_drift_refused(self):
        t=self.selected();self.read_file=self.corrected;r=self.read(t)
        self.assertEqual(r['status'],'source_mismatch');self.assertEqual(self.counts['meter'],0);self.assertEqual(r['passages'],[])
    def test_corpus_body_drift_refused(self):
        t=self.selected();c=sqlite3.connect(self.db);c.execute("UPDATE documents SET body=body || ' changed' WHERE doc_id='example-report'");c.commit();c.close()
        r=self.read(t);self.assertEqual(r['status'],'source_mismatch');self.assertEqual(self.counts['meter'],0)
    def test_missing_source_refused(self):
        t=self.selected()
        def missing(rid):raise FileNotFoundError('secret path')
        r=self.read(t,source_reader=missing);self.assertEqual(r['status'],'source_unavailable');self.assertEqual(self.counts['meter'],0)
    def test_meter_denial_has_no_body(self):
        t=self.selected();self.meter_answer=False;r=self.read(t)
        self.assertEqual(r['status'],'view_denied');self.assertEqual(r['passages'],[]);self.assertNotIn('31%',json.dumps(r));self.assertEqual(self.counts['meter'],1)
    def test_meter_exception_is_not_auto_retried(self):
        t=self.selected()
        def fail(rid):self.counts['meter']+=1;raise RuntimeError('outcome unknown')
        r=self.read(t,meter=fail);self.assertEqual(r['status'],'accounting_unknown');self.assertEqual(r['passages'],[]);self.assertEqual(self.counts['meter'],1)
    def test_new_accepted_version_old_selection_rejected_then_new_succeeds(self):
        t=self.selected();populate(self.corpus,self.db,self.item,self.revised);self.read_file=self.corrected
        self.scope['generation']='review-g2';self.scope['items']['example-report'].update(pdf_sha256=self.revised['pdf_sha256'],body_sha256=self.revised['body_sha256'])
        self.assertEqual(self.read(t)['status'],'selection_stale');r=self.read(self.selected())
        self.assertEqual(r['status'],'matched');self.assertIn('31% to 29%',r['passages'][0]['text']);self.assertEqual(self.counts['meter'],1)
    def test_caller_cannot_supply_report_path(self):
        t=self.selected();t['id']='../../secrets';r=self.read(t)
        self.assertEqual(r['status'],'selection_invalid');self.assertEqual(self.counts['source_reads'],0)
    def test_limit_bool_invalid(self):
        self.assertEqual(self.discover(limit=True)['status'],'invalid_request');self.assertEqual(self.counts['connections'],0)
    def test_query_over_budget_refused(self):
        self.assertEqual(self.discover(query='x'*257)['status'],'invalid_request');self.assertEqual(self.counts['connections'],0)
    def test_stopwords_no_scan(self):
        self.assertEqual(self.discover(query='what is the')['status'],'query_too_short');self.assertEqual(self.counts['connections'],0)
    def test_bound_result_budget_reports_more(self):
        c=self.corpus.open_db(self.db)
        for rid in ('extra-a','extra-b'):
            item=catalog_item(rid);self.corpus.upsert(c,item,self.source['body'],facts={'content_sha256':self.source['pdf_sha256'],'char_count':self.source['char_count'],'pages':2})
            self.scope['items'][rid]={**self.scope['items']['example-report'],'catalog':item}
        c.close();r=self.discover(limit=1);self.assertEqual(len(r['items']),1);self.assertIs(r['has_more'],True)
    def test_selection_not_reused_as_permission(self):
        t=self.selected();self.scope['decision']='unknown';r=self.read(t)
        self.assertEqual(r['status'],'scope_unavailable');self.assertEqual(self.counts['meter'],0)
    def test_whitelist_no_trade_authority(self):
        r=self.read(self.selected());self.assertEqual(r['status'],'matched')
        for forbidden in ('signal','rank','sizing','confidence','trade_action'):self.assertNotIn(forbidden,r)
    def test_scope_change_during_source_read_not_served(self):
        t=self.selected()
        def changed(rid):self.scope['generation']='review-g2';return self.pdf.read_bytes()
        r=self.read(t,source_reader=changed);self.assertEqual(r['status'],'selection_stale');self.assertEqual(self.counts['meter'],0)
    def test_catalog_only_match_does_not_fabricate_source_support_or_debit(self):
        d=self.discover(query='manufacturing');self.assertEqual(d['status'],'ready');self.assertTrue(d['items'])
        r=self.read(d['items'][0]['selection']);self.assertEqual(r['status'],'no_matching_passage')
        self.assertEqual(self.counts['meter'],0);self.assertEqual(r['passages'],[])
    def test_source_hash_disagreement_rejects_discovery(self):
        c=sqlite3.connect(self.db);c.execute("UPDATE documents SET content_sha256=?",('0'*64,));c.commit();c.close()
        r=self.discover();self.assertEqual(r['status'],'source_mismatch');self.assertEqual(r['items'],[])
    def test_declared_prefix_is_not_claimed_complete(self):
        c=sqlite3.connect(self.db);c.execute("UPDATE documents SET char_count=char_count+1000");c.commit();c.close()
        r=self.read(self.selected());self.assertEqual(r['status'],'matched')
        self.assertEqual(r['source_binding']['coverage'],'prefix_partial');self.assertIs(r['source_binding']['tail_omitted'],True)
    def test_access_change_during_accounting_does_not_serve(self):
        t=self.selected()
        def changed(rid):self.counts['meter']+=1;self.scope={'decision':'denied'};return True
        r=self.read(t,meter=changed);self.assertEqual(r['status'],'access_changed_after_accounting')
        self.assertEqual(r['passages'],[]);self.assertEqual(self.counts['meter'],1)
    def test_legacy_corpus_default_contract_unchanged(self):
        c=sqlite3.connect(self.db);c.row_factory=sqlite3.Row
        r=self.corpus.search(c,'orionquartz');self.assertEqual(r[0]['id'],'example-report');c.close()

if __name__=='__main__': unittest.main(verbosity=2)
