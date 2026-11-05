"""Exact selection/reopen composition using synthetic stores; no live proof."""
from dataclasses import replace
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sys
import types

import pytest
from tests import test_observe_options_matrix_identity as I
from tests import test_observe_options_matrix_publication as F
from engine import options_matrix_retention as R
from engine.intelligence_workspace.entity import IdentityArtifactRead

from scripts import observe_options_matrix_publication as O
NOW = I.NOW


def selected(strike='500', side='call', **changes):
    doc = {'schema':'options_matrix_selection.v1',
           'primary':{'expiry':'2026-10-16','strike':strike,'side':side},
           'comparisons':[], 'view':{'lens':'chain','metric':'volume','side':'all',
                                    'expiry':'all','display_mode':'3d'}}
    doc.update(changes)
    return json.dumps(doc, separators=(',',':')).encode()


def captured(raw=None, **changes):
    raw = selected() if raw is None else raw
    return replace(IdentityArtifactRead(raw, hashlib.sha256(raw).hexdigest(), NOW), **changes)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(I, 'O', O)
    return I.setup.__wrapped__(tmp_path, monkeypatch)


def observe(s, **kw):
    args = dict(output_dir=s[2],client=s[3],bucket='fixture',roots=('SPY',),
                identity_inputs=s[4],now=NOW)
    args.update(kw)
    return O.observe_publication(**args)


def prior_pair(s):
    # Same source day, distinct bytes and disjoint coordinates distinguish A from B.
    a = F._payload('SPY',session='2026-10-12',spot=90,strike=500)
    a_ref = F._install(s[2],s[3],a,'SPY')
    prior = observe(s)
    path = s[0]/'prior.json'
    path.write_text(json.dumps(F._prior_from_result(prior)))
    b = F._payload('SPY',session='2026-10-12',spot=110,strike=505)
    b_ref = F._install(s[2],s[3],b,'SPY')
    s[3].calls.clear()
    return path,a_ref,b_ref,a,b


def test_current_exact_bytes_and_capture_identity(setup):
    input_ = captured()
    result = observe(setup,selection_input=input_)
    proof = result['selection']
    assert result['complete'] and result['stable'] and result['identity']['complete']
    assert proof['complete'] is True and proof['status']=='RESOLVED' and proof['target']=='current'
    assert proof['root']=='SPY' and proof['session']=='2026-10-12'
    assert proof['matrix_sha256']==hashlib.sha256(setup[-1]).hexdigest()
    assert proof['version_ref']==result['roots']['SPY']['version_ref']
    assert proof['security_id']=='SEC:US-ARCX-SYNTH'
    assert proof['selection_sha256']==input_.sha256
    assert proof['selection_read_at']==NOW.isoformat()==proof['matrix_read_at']
    assert proof['decision_at']==NOW.isoformat()==proof['available_at']
    assert proof['primary']=={'expiry':'2026-10-16','strike':'500','side':'call'}
    assert proof['comparisons']==[] and proof['comparisons_hidden']==[]
    assert proof['primary_hidden'] is False
    assert not result['natural_invocation_verified'] and not result['mutable_writes']
    assert setup[3].calls.count(('get',R.R2_PREFIX+'SPY.json'))==2
    assert len(setup[3].calls)==3 and all(s.closed for s in setup[3].streams)


def test_prior_uses_a_once_and_current_b_is_distinct(setup):
    prior, a_ref, b_ref, a, b = prior_pair(setup)
    result=observe(setup,prior_path=prior,selection_target='prior',selection_input=captured())
    proof=result['selection']
    assert result['complete'] and result['stable'] and proof['complete']
    assert result['roots']['SPY']['sha256']==b_ref.sha256
    assert proof['matrix_sha256']==a_ref.sha256 and proof['version_ref']==a_ref.version_ref
    assert proof['primary']['strike']=='500' and proof['target']=='prior'
    assert setup[3].calls.count(('get',a_ref.key))==1
    assert setup[3].calls.count(('get',b_ref.key))==1
    assert setup[3].calls.count(('get',R.R2_PREFIX+'SPY.json'))==3
    assert len(setup[3].calls)==5 and all(s.closed for s in setup[3].streams)


@pytest.mark.parametrize('target,strike', [('prior','505'),('current','500')])
def test_no_fallback_between_a_and_b(setup,target,strike):
    prior, *_=prior_pair(setup)
    result=observe(setup,prior_path=prior,selection_target=target,selection_input=captured(selected(strike)))
    assert result['complete'] and result['identity']['complete']
    assert result['selection']['complete'] is False and result['selection']['status']=='UNAVAILABLE'
    assert result['selection']['reason']


def test_hidden_pins_and_roles_are_preserved(setup):
    point={'expiry':'2026-10-16','strike':'500','side':'call'}
    other={**point,'side':'put'}
    raw=selected(comparisons=[other,point],view={'lens':'chain','metric':'deltaOi','side':'put',
                                              'expiry':'all','display_mode':'table'})
    proof=observe(setup,selection_input=captured(raw))['selection']
    assert proof['complete'] and proof['primary_hidden']
    assert proof['comparisons']==[other,point] and proof['comparisons_hidden']==[False,True]
    assert proof['view']['metric']=='deltaOi' and proof['view']['display_mode']=='table'


@pytest.mark.parametrize('raw',[b'{',b'null',b'{}',selected('501'),selected().replace(b'"500"',b'"500.0"'),
                               b'{"schema":1,"schema":2}',selected().replace(b'"volume"',b'NaN')])
def test_bad_selection_never_changes_publication_semantics(setup,raw):
    result=observe(setup,selection_input=captured(raw))
    assert result['complete'] and result['stable'] and result['identity']['complete']
    assert not result['selection']['complete']


@pytest.mark.parametrize('bad', [
    'bytes-as-text', {}, captured(b''), captured(b'x'*2049), captured(sha256='0'*64),
    captured(read_at=NOW+timedelta(seconds=1)), captured(read_at='2026-10-12T17:02:00.000000001Z'),
    captured(read_at='invalid'), captured(read_at='2026-10-12T17:02:00'),
    captured(body=bytearray(selected())), captured(body=memoryview(selected()))])
def test_capture_refused_before_get_or_receipt(setup,bad):
    receipt=setup[0]/'never.json'
    with pytest.raises(O.ObservationRefused):observe(setup,selection_input=bad,receipt_path=receipt)
    assert not setup[3].calls and not receipt.exists()


@pytest.mark.parametrize('extra', [
    {'identity_inputs':None}, {'selection_target':'prior'}, {'selection_target':'unknown'},
    {'selection_target':None}, {'selection_target':True}])
def test_invalid_combinations_are_pre_get(setup,extra):
    with pytest.raises(O.ObservationRefused):observe(setup,selection_input=captured(),**extra)
    assert setup[3].calls==[]


def test_target_without_selection_refuses(setup):
    with pytest.raises(O.ObservationRefused):observe(setup,selection_target='prior')
    assert not setup[3].calls


@pytest.mark.parametrize('kind',['missing_prior','denied_prior','changed_b','missing_current_history','unbound_a'])
def test_failed_reopen_or_identity_cannot_become_selected(setup,kind):
    prior,a_ref,b_ref,a,b=prior_pair(setup)
    if kind=='missing_prior':del setup[3].objects[a_ref.key]
    elif kind=='denied_prior':setup[3].get_faults[a_ref.key]=F.S3Error('AccessDenied',403)
    elif kind=='missing_current_history':del setup[3].objects[b_ref.key]
    elif kind=='changed_b':
        original=setup[3].get_object
        def get(*,Bucket,Key):
            response=original(Bucket=Bucket,Key=Key)
            if Key==a_ref.key:setup[3].objects[R.R2_PREFIX+'SPY.json']=F._payload('SPY',session='2026-10-12',spot=999)
            return response
        setup[3].get_object=get
    else:
        older=F._payload('SPY',session='2026-10-11',spot=90)
        a_ref=F._install(setup[2],setup[3],older,'SPY')
        prior.write_text(json.dumps(F._prior_from_result(observe(setup))))
        F._install(setup[2],setup[3],b,'SPY');setup[3].calls.clear()
    result=observe(setup,selection_input=captured(),selection_target='prior',prior_path=prior)
    assert not result['selection']['complete']
    if kind=='unbound_a':assert result['complete'] and result['identity']['complete']
    else:assert not result['complete']
    assert setup[3].calls.count(('get',a_ref.key))==1
    if kind=='changed_b':assert not result['stable']


def test_receipt_contains_same_selection_proof(setup):
    receipt=setup[0]/'observed.json'
    result=observe(setup,selection_input=captured(),receipt_path=receipt)
    assert json.loads(receipt.read_text())==result
    before=receipt.read_bytes();setup[3].calls.clear()
    with pytest.raises(O.ObservationRefused):observe(setup,selection_input=captured(),receipt_path=receipt)
    assert not setup[3].calls and receipt.read_bytes()==before


@pytest.mark.parametrize('prior_requested',[False,True])
def test_legacy_has_no_new_field_or_reads(setup,prior_requested):
    prior=prior_pair(setup)[0] if prior_requested else None
    result=observe(setup,prior_path=prior)
    assert result['complete'] and result['identity']['complete'] and 'selection' not in result
    assert len(setup[3].calls)==(5 if prior_requested else 3)


def cli_args(s):
    return ['--repo',str(s[0]),'--out',str(s[2]),'--bucket','fixture']


def install_cli_stub(monkeypatch):
    stub=types.ModuleType('scripts.build_options_matrix');stub.DEFAULT_ROOTS=O.DEFAULT_ROOTS
    stub._r2_client=lambda:pytest.fail('no runtime client construction in tests')
    monkeypatch.setitem(sys.modules,'scripts.build_options_matrix',stub)


@pytest.mark.parametrize('target,strike,expected',[('current','500',0),('current','501',1),('prior','500',0),('prior','501',1)])
def test_cli_selected_outcome(setup,monkeypatch,capsys,target,strike,expected):
    install_cli_stub(monkeypatch)
    for root in O.DEFAULT_ROOTS:F._install(setup[2],setup[3],F._payload(root,session='2026-10-12'),root)
    prior=None
    if target=='prior':
        result=O.observe_publication(output_dir=setup[2],client=setup[3],bucket='fixture')
        prior=setup[0]/'all-prior.json';prior.write_text(json.dumps(F._prior_from_result(result)))
    path=setup[0]/'selection.json';path.write_bytes(selected(strike))
    args=cli_args(setup)+['--identity-vendor','thetadata','--selection',str(path),'--selection-target',target]
    if prior:args+=['--prior',str(prior)]
    assert O.main(args,client=setup[3])==expected
    result=json.loads(capsys.readouterr().out)
    assert result['complete'] and result['identity']['complete']
    assert result['selection']['complete'] is (expected==0)


@pytest.mark.parametrize('case',['no_identity','prior_without_path','no_selection','missing','oversize','empty'])
def test_cli_invalid_request_before_client(setup,monkeypatch,case):
    install_cli_stub(monkeypatch)
    path=setup[0]/'selection.json';path.write_bytes(selected())
    args=cli_args(setup)
    if case!='no_identity':args+=['--identity-vendor','thetadata']
    if case!='no_selection':args+=['--selection',str(path)]
    if case in {'prior_without_path','no_selection'}:args+=['--selection-target','prior']
    if case=='missing':path.unlink()
    if case=='oversize':path.write_bytes(b'x'*2049)
    if case=='empty':path.write_bytes(b'')
    assert O.main(args)==2
    assert not setup[3].calls


def test_prior_read_clock_is_not_later_decision_clock(setup,monkeypatch):
    prior,a_ref,_,_,_=prior_pair(setup)
    clock={'at':NOW}
    monkeypatch.setattr(O,'_utc_now',lambda:clock['at'])
    original_load=R.load_snapshot
    def load(client,bucket,ref):
        raw=original_load(client,bucket,ref)
        if ref.sha256==a_ref.sha256:clock['at']=NOW+timedelta(seconds=1)
        return raw
    monkeypatch.setattr(R,'load_snapshot',load)
    original_heads=O._reread_heads
    def heads(*args,**kw):
        value=original_heads(*args,**kw)
        if clock['at']>NOW:clock['at']=NOW+timedelta(seconds=2)
        return value
    monkeypatch.setattr(O,'_reread_heads',heads)
    proof=observe(setup,prior_path=prior,selection_target='prior',selection_input=captured())['selection']
    assert proof['complete']
    assert proof['matrix_read_at']==(NOW+timedelta(seconds=1)).isoformat()
    assert proof['available_at']==proof['matrix_read_at']
    assert proof['decision_at']==(NOW+timedelta(seconds=2)).isoformat()
    assert proof['selection_read_at']==NOW.isoformat()


@pytest.mark.parametrize('change',['corrupt_remote','corrupt_local','wrong_side_digest'])
def test_prior_mismatch_cannot_produce_selection(setup,change):
    prior,ref,_,_,_=prior_pair(setup)
    if change=='corrupt_remote':setup[3].objects[ref.key]=b'x'*ref.byte_length
    elif change=='corrupt_local':(setup[2]/'history'/'SPY'/f'{ref.sha256}.json').write_bytes(b'x')
    else:
        doc=json.loads(prior.read_text());doc['roots']['SPY']['observed_side_token_set_digest']='0'*64
        prior.write_text(json.dumps(doc))
    result=observe(setup,prior_path=prior,selection_target='prior',selection_input=captured())
    assert not result['complete'] and not result['selection']['complete']
    assert setup[3].calls.count(('get',ref.key))==1
    assert setup[3].calls.count(('get',R.R2_PREFIX+'SPY.json'))==2


def test_partial_other_root_blocks_selection_even_when_spy_bytes_valid(setup):
    result=observe(setup,roots=('SPY','QQQ'),selection_input=captured())
    assert result['roots']['SPY']['sha256']==hashlib.sha256(setup[-1]).hexdigest()
    assert not result['complete'] and not result['identity']['complete'] and not result['selection']['complete']


def test_current_selection_also_requires_requested_prior_retention(setup):
    prior,a_ref,_,_,_=prior_pair(setup)
    setup[3].get_faults[a_ref.key]=F.S3Error('AccessDenied',403)
    result=observe(setup,prior_path=prior,selection_input=captured(selected('505')))
    assert not result['complete'] and not result['selection']['complete']


def test_selection_clock_revalidated_at_final_decision(setup,monkeypatch):
    calls={'n':0}
    def clock():
        calls['n']+=1
        return NOW+timedelta(seconds=3 if calls['n']==1 else 1)
    monkeypatch.setattr(O,'_utc_now',clock)
    result=observe(setup,selection_input=captured(read_at=NOW+timedelta(seconds=2)))
    assert result['complete'] and result['identity']['complete']
    assert not result['selection']['complete']
