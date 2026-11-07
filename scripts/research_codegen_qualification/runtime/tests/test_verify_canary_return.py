import base64
import hashlib
import json
import pytest
import verify_canary_return as m


def raw(v):return json.dumps(v,separators=(',',':'),sort_keys=True).encode()
def sha(v):return hashlib.sha256(v).hexdigest()


def fixture():
    data=b'invented'
    doc={'schema':'rf.fixed_canary.v1','root':m.ROOT,'operation':m.OPERATION,
        'commission_sha256':'a'*64,'status':'FIXED_SMOKE_PASSED',
        'completed_phases':list(m.PHASE_ORDER),'candidate_admission':False,'containment_qualified':False,
        'budget':{'complete':True,'frozen':False,'activephase':None,'nextphase':None,'usedraw':8},
        'captured_raw_bytes':8,'observations':{
            'cli':{'status':'PASS','real_daemon_or_registry_used':False,'path_only_owned_helpers':True,
                'owned_fixture_removed':True,'positive_control_helper_get_count':1,
                'anonymous_helper_get_count':0,'raw_output_bytes':0},
            'installer':{'status':'OK_INSTALLED','receipt_write_failed':False,'unknowns':[],
                         'rollback':{},'commands':[]},
            'image':{'status':'PRESENT'},
            'smoke_execution':{'frozen':False,'known_container_id':'c'*64,
                'ledger':[{'stdout_b64':base64.b64encode(data).decode(),'stderr_b64':'',
                           'output_sha256':sha(data)}]},
            'smoke_verdict':{'mechanical_checks_passed':True,'candidate_admission':False,
                             'containment_qualified':False}}}
    return doc


def carrier(doc):
    output=raw(doc)+b'\n'
    return {'schema':'rf.fixed_canary_carrier.v1','root':m.ROOT,'operation':m.OPERATION,
        'commission_sha256':'a'*64,'capsule_sha256':'b'*64,'bootstrap_sha256':'d'*64,
        'rc':0,'problem':None,'supervision':'NOT_REQUIRED','stdin_complete':True,
        'same_operation_reconciliation_required':False,'physical_result_accepted':False,
        'candidate_admission':False,'containment_qualified':False,'elapsed_seconds':100,
        'output_bytes':len(output),'output_sha256':sha(output),'output_b64':base64.b64encode(output).decode()}


def verify(c):
    b=raw(c)
    return m.verify(b,retained_sha=sha(b),commission_sha='a'*64,capsule_sha='b'*64,bootstrap_sha='d'*64)


def test_full_bound_fixture_never_grants_candidate_or_parent_acceptance():
    r=verify(carrier(fixture()))
    assert r['parent_review_still_required'] is True
    assert r['candidate_admission'] is r['containment_qualified'] is False


@pytest.mark.parametrize('field,value', [('rc',False),('rc',1),('problem','timeout'),
    ('stdin_complete',False),('elapsed_seconds',901),('supervision','SIGNAL_SENT_NOT_TERMINATION_PROOF'),
    ('commission_sha256','f'*64),('output_sha256','0'*64),('physical_result_accepted',True)])
def test_carrier_rc_or_claim_alone_does_not_accept(field,value):
    c=carrier(fixture());c[field]=value
    with pytest.raises(m.ReturnRefused):verify(c)


@pytest.mark.parametrize('field,value',[('status','STOPPED_NO_RETRY'),('captured_raw_bytes',9),
    ('completed_phases',['cli','archive']),('candidate_admission',True)])
def test_partial_or_escalated_claim_refuses(field,value):
    d=fixture();d[field]=value
    with pytest.raises(m.ReturnRefused):verify(carrier(d))


def test_invented_capture_hash_or_unknown_install_is_rejected():
    d=fixture();d['observations']['smoke_execution']['ledger'][0]['output_sha256']='0'*64
    with pytest.raises(m.ReturnRefused):verify(carrier(d))
    d=fixture();d['observations']['installer']['unknowns']=['unconfirmed']
    with pytest.raises(m.ReturnRefused):verify(carrier(d))
