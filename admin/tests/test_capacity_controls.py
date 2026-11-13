"""Control safety proofs. Fixture config only; no production routing or model calls."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from admin import capacity_control_owner as owner
from admin import capacity_control_transport as transport
from admin.capacity_config_transaction import configuration_writer, WriterBusy, PendingConfiguration
from admin.capacity_fabric_schema import clean_snapshot
from admin.tests.test_capacity_history import snapshot, NOW

EPOCH = 'a'*32

class Route:
    def __init__(self, r):
        self.route_id=r['route_id'];self.pool=r.get('pool','pool');self.models=tuple(r['models'])
        self.priority=r.get('priority',100);self.weight=r.get('weight',1)
        self.model_priority=r.get('model_priority',{});self.model_weight=r.get('model_weight',{})
    def effective_weight(self,model):
        return self.model_weight.get(model,self.weight)


def read_document(path):
    raw=path.read_bytes();return json.loads(raw),hashlib.sha256(raw).hexdigest()

class Refresh:
    def __init__(self,path):
        self.path=path;self.digest=read_document(path)[1];self.error=None;self.calls=0;self.reject=False
    def refresh(self,app,parser,force=False):
        self.calls+=1
        if self.reject:return False
        doc,self.digest=read_document(self.path)
        app.state.settings=SimpleNamespace(routes=parser(doc),aliases=tuple(doc['aliases'].items()))
        return True

class OwnerControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'routes.json'
        self.doc={'routes':[{'route_id':'r1','models':['m1','m2'],'weight':1,'priority':10,'pool':'shared'},
                            {'route_id':'r2','models':['m1'],'weight':2,'priority':20,'pool':'shared'}],
                  'aliases':{'fabric/fast':['m1','m2']},'model_routing':{'version':'preserve'},
                  'private_field':'fixture-preserved-not-exported'}
        self.path.write_text(json.dumps(self.doc))
        self.gateway=SimpleNamespace(read_document=read_document,_routes_from_document=lambda d:tuple(Route(r) for r in d['routes']))
        self.native=Refresh(self.path);self.app=SimpleNamespace(state=SimpleNamespace(config_refresh=self.native))
        self.native.refresh(self.app,self.gateway._routes_from_document)
    def tearDown(self):self.tmp.cleanup()
    def intent(self,patch_,action='apply',number=1):
        return {'operation_id':f'{number:032x}','action':action,'epoch':EPOCH,'expires_at':NOW+20,
                'expected_revision':self.native.digest,'patch':patch_}
    def handle(self,request,**kw):
        return owner.handle(request,self.app,self.gateway,epoch=EPOCH,enabled=True,now=NOW,**kw)
    def test_validate_never_writes_config_or_journal(self):
        before=self.path.read_bytes();r=self.handle(self.intent({'interval_s':.5},'validate'))
        self.assertEqual(r['state'],'VALIDATED');self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(self.path.with_name('routes.json.admin-receipts.json').exists())
    def test_apply_reads_effective_revision_and_preserves_unrelated_values(self):
        r=self.handle(self.intent({'interval_s':.5,'routes':[{'id':'r1','priority':12,'model_weight':{'m2':.4}}]}))
        self.assertEqual(r['state'],'APPLIED');doc,sha=read_document(self.path)
        self.assertEqual(sha,self.native.digest);self.assertEqual(sha,r['effective_revision'])
        self.assertEqual(doc['private_field'],self.doc['private_field']);self.assertEqual(doc['model_routing'],self.doc['model_routing'])
        self.assertEqual(doc['observability']['interval_s'],.5)
        self.assertEqual(self.path.stat().st_mode&0o777,0o600)
    def test_stale_revision_refuses_without_write(self):
        request=self.intent({'interval_s':.5});request['expected_revision']='f'*64
        before=self.path.read_bytes();r=self.handle(request)
        self.assertEqual(r['state'],'CONFLICT');self.assertEqual(before,self.path.read_bytes())
    def test_same_operation_is_reconciled_not_applied_again(self):
        request=self.intent({'interval_s':.5});first=self.handle(request);before=self.path.stat().st_mtime_ns
        second=self.handle(request);self.assertEqual(second['state'],'APPLIED')
        self.assertEqual(first['after_revision'],second['after_revision']);self.assertEqual(before,self.path.stat().st_mtime_ns)
    def test_same_id_different_intent_refused(self):
        request=self.intent({'interval_s':.5});self.handle(request)
        request['patch']['interval_s']=1;r=self.handle(request)
        self.assertEqual(r['state'],'CONFLICT');self.assertEqual(r['code'],'OPERATION_ID_CONFLICT')
    def test_noop_is_not_claimed_as_write(self):
        r=self.handle(self.intent({'routes':[{'id':'r1','priority':10}]}))
        self.assertEqual(r['state'],'NOT_APPLIED');self.assertEqual(r['code'],'NO_CHANGES')
    def test_expired_and_wrong_epoch_and_disabled_are_not_applied(self):
        for field,value in [('expires_at',NOW-1),('epoch','b'*32)]:
            with self.subTest(field=field):
                request=self.intent({'interval_s':.5});request[field]=value
                self.assertEqual(self.handle(request)['state'],'NOT_APPLIED')
        r=owner.handle(self.intent({'interval_s':.5}),self.app,self.gateway,epoch=EPOCH,enabled=False,now=NOW)
        self.assertEqual(r['state'],'NOT_APPLIED')
        self.assertNotIn('observability',read_document(self.path)[0])
    def test_allowlist_rejects_secrets_spend_enrollment_and_bad_numbers(self):
        bad=[{'token':'not-allowed'},{'allow_metered':True},{'routes':[{'id':'r1','base_url':'https://invalid'}]},
             {'interval_s':True},{'interval_s':.1},{'routes':[{'id':'r1','weight':float('nan')}]},
             {'routes':[{'id':'r1','priority':1.1}]},{'routes':[{'id':'r1','weight':-1}]},
             {'aliases':{'fabric/fast':['m1','new-model']}},{'routes':[{'id':'unknown','weight':2}]},
             {'routes':[{'id':'r1','model_weight':{'unknown':2}}]}]
        for change in bad:
            with self.subTest(change=change):
                before=self.path.read_bytes();r=self.handle(self.intent(change));self.assertEqual(r['state'],'NOT_APPLIED');self.assertEqual(before,self.path.read_bytes())
    def test_last_model_path_cannot_be_disabled(self):
        r=self.handle(self.intent({'routes':[{'id':'r1','weight':0}]}));self.assertEqual(r['state'],'NOT_APPLIED')
        r=self.handle(self.intent({'routes':[{'id':'r1','model_weight':{'m1':0}}]}));self.assertEqual(r['state'],'APPLIED')
    def test_alias_membership_fixed_but_order_can_change(self):
        r=self.handle(self.intent({'aliases':{'fabric/fast':['m2','m1']}}));self.assertEqual(r['state'],'APPLIED')
    def test_projection_does_not_export_document_secrets(self):
        p=owner.projection(self.app,self.gateway,enabled=True);self.assertTrue(p['writable'])
        self.assertNotIn('fixture-preserved',json.dumps(p));self.assertEqual(p['effective_revision'],p['revision'])
    def test_interruption_after_prepare_before_write_reconciles_no_effect(self):
        request=self.intent({'interval_s':.5});actual=owner.atomic_private
        def stop_config(path,body):
            if path==self.path:raise OSError('fixture interruption')
            return actual(path,body)
        with patch.object(owner,'atomic_private',side_effect=stop_config):
            first=self.handle(request)
        self.assertEqual(first['state'],'EFFECT_UNKNOWN')
        reconciled=self.handle(request);self.assertEqual(reconciled['state'],'NOT_APPLIED')
        self.assertEqual(reconciled['code'],'INTERRUPTED_BEFORE_WRITE')
        self.assertNotIn('observability',read_document(self.path)[0])
    def test_interruption_after_write_reconciles_effect_without_rewriting(self):
        request=self.intent({'interval_s':.5});actual=owner.atomic_private;calls=0
        def fail_receipt(path,body):
            nonlocal calls
            if path.name.endswith('.admin-receipts.json'):
                calls+=1
                if calls==2:raise OSError('receipt interruption')
            return actual(path,body)
        with patch.object(owner,'atomic_private',side_effect=fail_receipt):
            first=self.handle(request)
        self.assertEqual(first['state'],'EFFECT_UNKNOWN');mtime=self.path.stat().st_mtime_ns
        second=self.handle(request);self.assertEqual(second['state'],'APPLIED');self.assertEqual(mtime,self.path.stat().st_mtime_ns)
    def test_config_change_after_prepared_receipt_does_not_get_overwritten(self):
        request=self.intent({'interval_s':.5});actual=owner.atomic_private
        def concurrent_change(path,body):
            actual(path,body)
            if path.name.endswith('.admin-receipts.json') and json.loads(body)[-1]['state']=='PREPARED':
                d=copy.deepcopy(self.doc);d['external_writer']='preserved';self.path.write_text(json.dumps(d))
        with patch.object(owner,'atomic_private',side_effect=concurrent_change):r=self.handle(request)
        self.assertEqual(r['state'],'CONFLICT');self.assertEqual(read_document(self.path)[0]['external_writer'],'preserved')
    def test_native_refresh_callback_used_for_state_mutation(self):
        calls=[]
        def refresh():calls.append(True);return self.native.refresh(self.app,self.gateway._routes_from_document,force=True)
        r=self.handle(self.intent({'interval_s':.5}),refresh_owner=refresh)
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(len(calls),2)

    def reconciliation(self, original, observed_epoch=EPOCH):
        return {'action':'reconcile','operation_id':original['operation_id'],'epoch':observed_epoch,
                'request_id':'e'*32,'original':original}
    def test_busy_writer_is_known_no_effect(self):
        before=self.path.read_bytes()
        with configuration_writer(self.path):
            r=self.handle(self.intent({'interval_s':.5}))
        self.assertEqual(r['state'],'NOT_APPLIED');self.assertEqual(r['code'],'CONTROL_OWNER_BUSY')
        self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(self.path.with_name('routes.json.admin-receipts.json').exists())
    def test_shared_writer_cannot_enter_after_final_revision_check(self):
        request=self.intent({'interval_s':.5});actual=owner.atomic_private;blocked=[]
        def competing(path,body):
            if path==self.path:
                with self.assertRaises(WriterBusy):
                    with configuration_writer(self.path):
                        self.fail('competing native writer entered the transaction')
                blocked.append(True)
            return actual(path,body)
        with patch.object(owner,'atomic_private',side_effect=competing):r=self.handle(request)
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(blocked,[True])
        with configuration_writer(self.path):
            document,_=read_document(self.path);document['external_writer']='preserved'
            actual(self.path,owner._bytes(document))
        document,_=read_document(self.path)
        self.assertEqual(document['observability']['interval_s'],.5)
        self.assertEqual(document['external_writer'],'preserved')
    def test_uncertain_adoption_reconciles_without_second_config_write(self):
        original=self.intent({'interval_s':.5});actual=owner.atomic_private;writes=[]
        def pause_adoption(path,body):
            result=actual(path,body)
            if path==self.path:writes.append(True);self.native.reject=True
            return result
        with patch.object(owner,'atomic_private',side_effect=pause_adoption):first=self.handle(original)
        self.assertEqual(first['state'],'EFFECT_UNKNOWN')
        with self.assertRaises(PendingConfiguration):
            with configuration_writer(self.path):pass
        self.native.reject=False;stamp=self.path.stat().st_mtime_ns
        with patch.object(owner,'atomic_private',side_effect=pause_adoption):
            second=self.handle(self.reconciliation(original))
        self.assertEqual(second['state'],'APPLIED');self.assertEqual(len(writes),1)
        self.assertEqual(self.path.stat().st_mtime_ns,stamp)
        with configuration_writer(self.path):pass
    def test_old_epoch_apply_refused_but_reconcile_only_observes(self):
        original=self.intent({'interval_s':.5});self.handle(original);stamp=self.path.stat().st_mtime_ns
        self.assertEqual(owner.handle(original,self.app,self.gateway,epoch='b'*32,enabled=True,now=NOW)['state'],'NOT_APPLIED')
        request=self.reconciliation(original,'b'*32)
        r=owner.handle(request,self.app,self.gateway,epoch='b'*32,enabled=False,now=NOW)
        self.assertEqual(r['state'],'APPLIED');self.assertEqual(r['origin_epoch'],EPOCH)
        self.assertEqual(r['epoch'],'b'*32);self.assertEqual(self.path.stat().st_mtime_ns,stamp)
    def test_prepared_fences_later_writers_until_no_effect_reconciled(self):
        original=self.intent({'interval_s':.5});actual=owner.atomic_private
        def stop(path,body):
            if path==self.path:raise OSError('interrupted before configuration write')
            return actual(path,body)
        with patch.object(owner,'atomic_private',side_effect=stop):r=self.handle(original)
        self.assertEqual(r['state'],'EFFECT_UNKNOWN')
        with self.assertRaises(PendingConfiguration):
            with configuration_writer(self.path):pass
        stamp=self.path.stat().st_mtime_ns;r=self.handle(self.reconciliation(original))
        self.assertEqual(r['state'],'NOT_APPLIED');self.assertEqual(self.path.stat().st_mtime_ns,stamp)
        with configuration_writer(self.path):pass
    def test_unqualified_aba_does_not_invent_no_effect(self):
        original=self.intent({'interval_s':.5});actual=owner.atomic_private;before=self.path.read_bytes()
        def stop(path,body):
            if path==self.path:raise OSError('interrupted')
            return actual(path,body)
        with patch.object(owner,'atomic_private',side_effect=stop):self.handle(original)
        actual(self.path,before)
        r=self.handle(self.reconciliation(original))
        self.assertEqual(r['state'],'EFFECT_UNKNOWN');self.assertEqual(r['code'],'PREIMAGE_WRITER_CONTINUITY_UNKNOWN')
    def test_missing_receipt_history_stays_uncertain(self):
        original=self.intent({'interval_s':.5});stamp=self.path.stat().st_mtime_ns
        r=self.handle(self.reconciliation(original))
        self.assertEqual(r['state'],'EFFECT_UNKNOWN');self.assertEqual(r['code'],'RECEIPT_STORE_CONTINUITY_UNKNOWN')
        self.assertEqual(self.path.stat().st_mtime_ns,stamp)
    def test_reconcile_cannot_substitute_intent(self):
        original=self.intent({'interval_s':.5});self.handle(original);stamp=self.path.stat().st_mtime_ns
        altered=copy.deepcopy(original);altered['patch']['interval_s']=1
        r=self.handle(self.reconciliation(altered))
        self.assertEqual(r['code'],'OPERATION_ID_CONFLICT');self.assertEqual(self.path.stat().st_mtime_ns,stamp)

class TransportControls(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'snapshot.json'
        s=snapshot();s['controls']={'ok':True,'writable':True,'revision':'b'*64,'effective_revision':'b'*64,
            'interval_s':2,'routes':[{'id':'r1','provider':'pool','models':['m1'],'priority':10,'weight':1}],
            'aliases':{'fabric/fast':['m1']},'receipts':[]};self.path.write_text(json.dumps(s))
        self.body={'action':'apply','expected_revision':'b'*64,'patch':{'interval_s':.5}}
    def tearDown(self):self.tmp.cleanup()
    def test_timeout_fences_next_mutation_and_readback(self):
        result,status=transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        self.assertEqual(status,202);self.assertEqual(result['state'],'EFFECT_UNKNOWN');self.assertFalse(result['retry_allowed'])
        second,status=transport.submit(self.body,path=self.path,now=NOW,timeout=0);self.assertEqual(status,409)
        self.assertFalse(transport.settings(path=self.path,now=NOW)['writable'])
    def test_exact_receipt_unlocks_but_unrelated_receipt_is_rejected(self):
        result,status=transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        receipt={'operation_id':result['operation_id'],'state':'APPLIED','epoch':EPOCH,'code':'EFFECTIVE_REVISION_VERIFIED','at':NOW}
        bad=dict(receipt,operation_id='f'*32);self.assertFalse(transport.accept_result(bad,path=self.path))
        self.assertTrue(transport.accept_result(receipt,path=self.path))
        self.assertIsNone(transport.next_request(EPOCH,path=self.path))
        self.assertTrue(transport.settings(path=self.path,now=NOW)['writable'])
    def test_nonterminal_receipt_keeps_writes_fenced(self):
        result,_=transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        transport.accept_result({'operation_id':result['operation_id'],'epoch':EPOCH,'state':'EFFECT_UNKNOWN','at':NOW},path=self.path)
        self.assertFalse(transport.settings(path=self.path,now=NOW)['writable'])
    def test_wrong_epoch_never_receives_control_request(self):
        transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        self.assertIsNone(transport.next_request('c'*32,path=self.path))
        self.assertIsNotNone(transport.next_request(EPOCH,path=self.path))
    def test_catalog_validation_precedes_persistence(self):
        for patch_ in [{'routes':[{'id':'PRIVATE_UNKNOWN','weight':2}]},
                       {'routes':[{'id':'r1','model_weight':{'PRIVATE_MODEL':2}}]},
                       {'aliases':{'fabric/fast':['PRIVATE_MODEL']}}]:
            with self.subTest(patch_=patch_):
                result,status=transport.submit(dict(self.body,patch=patch_),path=self.path,now=NOW,timeout=0)
                self.assertEqual(status,400);self.assertFalse(transport.paths(self.path)[0].exists())
    def test_stale_telemetry_disables_writes(self):
        self.assertFalse(transport.settings(path=self.path,now=NOW+100)['writable'])
        self.assertEqual(transport.submit(self.body,path=self.path,now=NOW+100,timeout=0)[1],503)
    def test_control_schema_drops_unknowns(self):
        s=json.loads(self.path.read_text());s['controls']['token']='PRIVATE';s['controls']['routes'][0]['secret']='PRIVATE'
        clean=clean_snapshot(s);self.assertNotIn('PRIVATE',json.dumps(clean))

    def test_native_terminal_receipt_supersedes_cached_unknown(self):
        result,_=transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        receipt={'operation_id':result['operation_id'],'epoch':EPOCH,'state':'EFFECT_UNKNOWN','at':NOW}
        transport.accept_result(receipt,path=self.path)
        s=json.loads(self.path.read_text());s['controls']['receipts']=[dict(receipt,state='APPLIED',at=NOW+1)]
        self.path.write_text(json.dumps(s))
        effective=transport.settings(path=self.path,now=NOW+1)
        self.assertTrue(effective['writable']);self.assertEqual(effective['last_operation']['state'],'APPLIED')
    def test_explicit_reconciliation_uses_new_delivery_not_new_apply(self):
        result,_=transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        original=transport.next_request(EPOCH,path=self.path)
        transport.accept_result({'operation_id':result['operation_id'],'epoch':EPOCH,'state':'EFFECT_UNKNOWN','at':NOW},path=self.path)
        response,status=transport.submit({'action':'reconcile','operation_id':result['operation_id']},path=self.path,now=NOW,timeout=0)
        self.assertEqual(status,202);request=transport.next_request(EPOCH,path=self.path)
        self.assertEqual(request['action'],'reconcile');self.assertEqual(request['original'],original)
        receipt={'operation_id':result['operation_id'],'request_id':request['request_id'],'epoch':EPOCH,'state':'APPLIED','at':NOW+1}
        self.assertTrue(transport.accept_result(receipt,path=self.path));self.assertIsNone(transport.next_request(EPOCH,path=self.path))
        self.assertTrue(transport.settings(path=self.path,now=NOW+1)['writable'])
    def test_reconciliation_after_epoch_change_preserves_original_epoch(self):
        result,_=transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        s=json.loads(self.path.read_text());s['epoch']='c'*32;self.path.write_text(json.dumps(s))
        self.assertIsNone(transport.next_request('c'*32,path=self.path))
        response,status=transport.submit({'action':'reconcile','operation_id':result['operation_id']},path=self.path,now=NOW,timeout=0)
        self.assertEqual(status,202);request=transport.next_request('c'*32,path=self.path)
        self.assertEqual(request['epoch'],'c'*32);self.assertEqual(request['original']['epoch'],EPOCH)
    def test_late_uncertainty_cannot_downgrade_terminal_result(self):
        result,_=transport.submit(self.body,path=self.path,now=NOW,timeout=0)
        receipt={'operation_id':result['operation_id'],'epoch':EPOCH,'state':'APPLIED','at':NOW}
        self.assertTrue(transport.accept_result(receipt,path=self.path))
        self.assertFalse(transport.accept_result(dict(receipt,state='EFFECT_UNKNOWN',at=NOW+1),path=self.path))
        self.assertTrue(transport.settings(path=self.path,now=NOW+1)['writable'])

if __name__=='__main__':unittest.main()
