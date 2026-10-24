"""Pure parent-side evidence gate for one exact retained canary result.

This validates returned facts; it is not host attestation, Fabric admission,
full containment acceptance, or authority to activate candidate execution.
"""
import base64
import hashlib
import json

from fixed_canary import ROOT, OPERATION
from phase_budget import PHASE_ORDER


class ReturnRefused(ValueError):
    pass


def check(ok, reason):
    if not ok:
        raise ReturnRefused(reason)


def pairs(items):
    out={}
    for k,v in items:
        check(k not in out,'duplicate_json_key');out[k]=v
    return out


def read(raw):
    try:
        return json.loads(raw,object_pairs_hook=pairs,
            parse_constant=lambda _:(_ for _ in ()).throw(ReturnRefused('nonfinite')))
    except (ValueError,TypeError,UnicodeError,RecursionError):
        raise ReturnRefused('json') from None


def verify(retained, *, retained_sha, commission_sha, capsule_sha, bootstrap_sha):
    """Expected hashes come from the original parent's commission and collector."""
    check(type(retained) is bytes and len(retained)<=100000,'retained_bound')
    check(hashlib.sha256(retained).hexdigest()==retained_sha,'retained_sha')
    carrier=read(retained)
    try:
        check(carrier['schema']=='rf.fixed_canary_carrier.v1'
              and carrier['root']==ROOT and carrier['operation']==OPERATION,'carrier_identity')
        check(carrier['commission_sha256']==commission_sha
              and carrier['capsule_sha256']==capsule_sha
              and carrier['bootstrap_sha256']==bootstrap_sha,'commission_binding')
        check(type(carrier['rc']) is int and carrier['rc']==0
              and carrier['problem'] is None and carrier['supervision']=='NOT_REQUIRED'
              and carrier['stdin_complete'] is True
              and carrier['same_operation_reconciliation_required'] is False,'carrier_settlement')
        check(carrier['physical_result_accepted'] is False
              and carrier['candidate_admission'] is False
              and carrier['containment_qualified'] is False,'carrier_scope')
        check(type(carrier['elapsed_seconds']) in (int,float)
              and 0<=carrier['elapsed_seconds']<=900,'carrier_time')
        output=base64.b64decode(carrier['output_b64'],validate=True)
        check(type(carrier['output_bytes']) is int and 0<len(output)<=65536
              and len(output)==carrier['output_bytes']
              and hashlib.sha256(output).hexdigest()==carrier['output_sha256'],'output_binding')
        doc=read(output)
        check(doc['schema']=='rf.fixed_canary.v1' and doc['root']==ROOT
              and doc['operation']==OPERATION and doc['commission_sha256']==commission_sha,
              'result_identity')
        check(doc['status']=='FIXED_SMOKE_PASSED'
              and doc['completed_phases']==list(PHASE_ORDER),'phase_settlement')
        check(doc['candidate_admission'] is False and doc['containment_qualified'] is False,'result_scope')
        budget=doc['budget']
        check(budget['complete'] is True and budget['frozen'] is False
              and budget['activephase'] is None and budget['nextphase'] is None,'budget_settlement')
        check(type(doc['captured_raw_bytes']) is int and doc['captured_raw_bytes']>=0
              and doc['captured_raw_bytes']==budget['usedraw']
              and doc['captured_raw_bytes']+len(output)<=65536,'total_output')
        observations=doc['observations'];cli=observations['cli'];installer=observations['installer']
        check(cli['status']=='PASS' and cli['real_daemon_or_registry_used'] is False
              and cli['path_only_owned_helpers'] is True and cli['owned_fixture_removed'] is True
              and cli['positive_control_helper_get_count']==1
              and cli['anonymous_helper_get_count']==0,'cli_isolation')
        check(installer['status'] in ('OK_INSTALLED','OK_REUSE_EXISTING')
              and installer['receipt_write_failed'] is False
              and installer['unknowns']==[] and installer['rollback']=={},'install_settlement')
        check(observations['image']['status']=='PRESENT','image')
        execution=observations['smoke_execution'];verdict=observations['smoke_verdict']
        check(execution['frozen'] is False and type(execution['known_container_id']) is str
              and len(execution['known_container_id'])==64
              and set(execution['known_container_id'])<=set('0123456789abcdef'),'smoke_identity')
        check(verdict['mechanical_checks_passed'] is True
              and verdict['candidate_admission'] is False
              and verdict['containment_qualified'] is False,'smoke_verdict')
        captured=cli['raw_output_bytes']
        captured+=sum(c['out_len']+c['err_len'] for c in installer['commands'])
        for k,record in observations.items():
            if k.startswith('image_capture_'):
                data=base64.b64decode(record['raw_b64'],validate=True)
                check(len(data)==record['raw_bytes'] and hashlib.sha256(data).hexdigest()==record['raw_sha256'],
                      'image_capture_hash')
                captured+=len(data)
        for record in execution['ledger']:
            out=base64.b64decode(record['stdout_b64'],validate=True)
            err=base64.b64decode(record['stderr_b64'],validate=True)
            check(hashlib.sha256(out+err).hexdigest()==record['output_sha256'],'smoke_capture_hash')
            captured+=len(out)+len(err)
        check(captured==doc['captured_raw_bytes'],'capture_accounting')
    except ReturnRefused:
        raise
    except (KeyError,TypeError,ValueError,OverflowError):
        raise ReturnRefused('malformed_return') from None
    return {'state':'FIXED_CANARY_EVIDENCE_STRUCTURALLY_QUALIFIED',
            'retained_sha256':retained_sha,'output_sha256':carrier['output_sha256'],
            'operation':OPERATION,'root':ROOT,
            'candidate_admission':False,'containment_qualified':False,
            'parent_review_still_required':True}
