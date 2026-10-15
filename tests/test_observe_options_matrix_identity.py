"""Copied observer integration: real canonical reader, fake store; no live proof."""
from pathlib import Path
from datetime import date, datetime, timezone
from dataclasses import replace
import io
import pandas as pd
import json
import hashlib
import sys
import types
import pytest

from scripts import observe_options_matrix_publication as O
from tests import test_observe_options_matrix_publication as F
from lib.dataos import identity
from engine import options_matrix_retention as retention
from engine.intelligence_workspace.entity import IdentityArtifactRead


def _prior_for_current_fixture(s, *, session="2026-10-11"):
    root, _, out, store, _, current = s
    prior_ref = F._install(out, store, F._payload("SPY", session=session), "SPY")
    prior = O.observe_publication(output_dir=out, client=store, bucket="fixture", roots=("SPY",))
    path = root / "prior.json"
    path.write_text(json.dumps(F._prior_from_result(prior)))
    F._install(out, store, current, "SPY")
    store.calls.clear()
    return path, prior_ref


def captured(body, at):
    return IdentityArtifactRead(body, hashlib.sha256(body).hexdigest(), at)


def parquet(rows, *, clocks=()):
    frame = pd.DataFrame(rows)
    for name in clocks:
        frame[name] = pd.to_datetime(frame[name])
    out = io.BytesIO()
    frame.to_parquet(out, index=False)
    return out.getvalue()


def master_record(**changes):
    row = dict(security_id="SEC:US-ARCX-SYNTH", listing_key="US-ARCX-SYNTH",
               country="US", mic="ARCX", inception_code="SYNTH",
               effective_at="2026-10-11T00:00:00", ingested_at="2026-10-12T15:00:00",
               security_state=None, superseded_by=None)
    row.update(changes)
    return row


def alias_record(**changes):
    row = dict(vendor="thetadata", vendor_symbol="SPY", security_id="SEC:US-ARCX-SYNTH",
               valid_from=date(2026,10,12), valid_to=date(2026,10,13),
               known_at="2026-10-12T16:00:00Z", alias_kind="occ_root",
               ingested_at="2026-10-12T16:01:00", binding_sha256="assigned-below")
    changes.pop("root", None)
    row.update(changes)
    return row

NOW=datetime(2026,10,12,17,2,tzinfo=timezone.utc)

@pytest.fixture
def setup(tmp_path,monkeypatch):
    monkeypatch.setattr(O,'_utc_now',lambda:NOW)
    reference=tmp_path/'data/reference';reference.mkdir(parents=True)
    evidence={'schema':'mastermind.spy_option_root_sources.v1','vendor':'thetadata','root':'SPY','synthetic':True}
    body=(json.dumps(evidence,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()
    row=alias_record(root='SPY',evidence_sha256=hashlib.sha256(body).hexdigest(),valid_to=date(2026,10,13))
    row['binding_sha256']=identity.option_root_binding_sha256(row['vendor'],row['vendor_symbol'],row['security_id'],row['valid_from'],row['valid_to'],row['known_at'],row['evidence_sha256'])
    (reference/'vendor_aliases.parquet').write_bytes(parquet([row],clocks=['ingested_at']))
    (reference/'security_master.parquet').write_bytes(parquet([master_record()],clocks=['effective_at','ingested_at']))
    (reference/'_receipt.json').write_text(json.dumps({'spy_option_root':evidence,'other_writer_fields':'preserved'}))
    out=tmp_path/'matrix';out.mkdir();store=F.ReadOnlyStore()
    raw=F._payload('SPY',session='2026-10-12');F._install(out,store,raw,'SPY')
    inputs=O.capture_spy_identity_inputs(tmp_path,vendor='thetadata')
    return tmp_path,reference,out,store,inputs,raw

def observe(s,**kw):
    _,_,out,store,inputs,_=s
    return O.observe_publication(output_dir=out,client=store,bucket='fixture',roots=('SPY',),identity_inputs=inputs,**kw)

def test_resolves_exact_store_bytes_and_existing_canonical_target(setup):
    result=observe(setup);item=result['identity']['roots']['SPY']
    assert result['complete'] and result['identity']['complete']
    assert result['identity']['scope']==['SPY']
    assert item['security_id']=='SEC:US-ARCX-SYNTH' # deliberately no ticker equality
    assert item['matrix_sha256']==hashlib.sha256(setup[-1]).hexdigest()
    assert item['version_ref']==result['roots']['SPY']['version_ref']
    assert item['aliases_sha256']==setup[4]['aliases'].sha256
    assert item['available_at']==NOW.isoformat()
    assert item['matrix_read_at']==NOW.isoformat()
    assert result['natural_invocation_verified'] is False
    assert result['mutable_writes'] is False
    assert all(call[0]=='get' for call in setup[3].calls)
    assert all(stream.closed for stream in setup[3].streams)

def test_legacy_path_does_not_claim_identity(setup):
    _,_,out,store,_,_=setup
    result=O.observe_publication(output_dir=out,client=store,bucket='fixture',roots=('SPY',))
    assert result['complete'] and 'identity' not in result

@pytest.mark.parametrize('session',['2026-10-11','2026-10-13'])
def test_session_is_taken_from_exact_matrix_not_current_root(setup,session):
    F._install(setup[2],setup[3],F._payload('SPY',session=session),'SPY')
    result=observe(setup)
    assert result['complete'] and not result['identity']['complete']
    assert result['identity']['roots']['SPY']['status']=='UNAVAILABLE'

@pytest.mark.parametrize('name',['aliases','security_master','root_evidence'])
def test_changed_captured_digest_refuses_identity_without_relabeling_store(setup,name):
    setup[4][name]=replace(setup[4][name],sha256='0'*64)
    result=observe(setup)
    assert result['complete'] and not result['identity']['complete']
    assert result['identity']['roots']['SPY']['reason']=='identity_contract_invalid'

@pytest.mark.parametrize('change',[{'security_state':'RETIRED'},{'superseded_by':'SEC:US-ARCX-OTHER'},{'security_id':'SEC:US-ARCX-OTHER'}])
def test_real_reader_rejects_retired_superseded_missing_target(setup,change):
    body=parquet([master_record(**change)],clocks=['effective_at','ingested_at'])
    setup[4]['security_master']=captured(body,NOW)
    result=observe(setup)
    assert result['identity']['roots']['SPY']=={'status':'UNAVAILABLE','reason':'identity_contract_invalid'}

@pytest.mark.parametrize('kind',['changed_head','missing_history','denied_head'])
def test_failed_store_observation_has_no_resolved_identity(setup,kind):
    store=setup[3];ref=retention.reference_for_bytes('SPY',setup[-1])
    if kind=='changed_head':store.head_revisions[retention.R2_PREFIX+'SPY.json']=[setup[-1],F._payload('SPY',session='2026-10-12',spot=101)]
    elif kind=='missing_history':del store.objects[ref.key]
    else:store.get_faults[retention.R2_PREFIX+'SPY.json']=F.S3Error('AccessDenied',403)
    result=observe(setup)
    assert not result['complete'] and not result['identity']['complete']
    assert result['identity']['roots']['SPY']=={'status':'UNAVAILABLE','reason':'snapshot_not_verified'}

def test_input_completion_after_decision_refuses(setup):
    setup[4]['aliases']=replace(setup[4]['aliases'],read_at='2026-10-12T17:02:00.000000001Z')
    assert observe(setup)['identity']['roots']['SPY']['reason']=='identity_contract_invalid'

@pytest.mark.parametrize('raw',[b'{}',b'[]',b'{"spy_option_root":null}',b'{"spy_option_root":{},"spy_option_root":{}}',b'{"spy_option_root":{"x":NaN}}'])
def test_bad_canonical_receipt_refused_before_store(setup,raw):
    (setup[1]/'_receipt.json').write_bytes(raw)
    with pytest.raises(O.ObservationRefused):O.capture_spy_identity_inputs(setup[0],vendor='thetadata')
    assert setup[3].calls==[]

@pytest.mark.parametrize('vendor',['yahoo',None,''])
def test_vendor_is_explicit_and_never_inferred_from_ticker(setup,vendor):
    with pytest.raises(O.ObservationRefused):O.capture_spy_identity_inputs(setup[0],vendor=vendor)

def test_missing_reference_file_refused(setup):
    (setup[1]/'security_master.parquet').unlink()
    with pytest.raises(O.ObservationRefused):O.capture_spy_identity_inputs(setup[0],vendor='thetadata')

@pytest.mark.parametrize('field,value',[('roots',('QQQ',)),('aliases',None),('writer_receipt_sha256','bad'),('vendor','yahoo')])
def test_invalid_bundle_is_pre_io_refusal(setup,field,value):
    setup[4][field]=value
    with pytest.raises(O.ObservationRefused):observe(setup)
    assert setup[3].calls==[]

def test_missing_requested_spy_root_is_pre_io_refusal(setup):
    with pytest.raises(O.ObservationRefused):O.observe_publication(output_dir=setup[2],client=setup[3],bucket='fixture',roots=('QQQ',),identity_inputs=setup[4])
    assert setup[3].calls==[]

def test_capture_binds_writer_serialization_and_completion_clocks(setup,monkeypatch):
    times=iter(datetime(2026,10,12,17,3,s,tzinfo=timezone.utc) for s in (1,2,3))
    monkeypatch.setattr(O,'_utc_now',lambda:next(times))
    inputs=O.capture_spy_identity_inputs(setup[0],vendor='thetadata')
    assert inputs['aliases'].read_at.second==1
    assert inputs['security_master'].read_at.second==2
    assert inputs['root_evidence'].read_at.second==3
    assert inputs['writer_receipt_sha256']==hashlib.sha256((setup[1]/'_receipt.json').read_bytes()).hexdigest()
    assert inputs['root_evidence'].body==setup[4]['root_evidence'].body

def test_no_postcapture_mutable_identity_fallback(setup):
    (setup[1]/'vendor_aliases.parquet').write_bytes(b'new unavailable bytes')
    assert observe(setup)['identity']['roots']['SPY']['aliases_sha256']==setup[4]['aliases'].sha256

@pytest.mark.parametrize('requested,session,expected',[(True,'2026-10-12',0),(True,'2026-10-11',1),(False,'2026-10-11',0)])
def test_cli_optin_and_legacy_exit_semantics(setup,monkeypatch,capsys,requested,session,expected):
    for root in O.DEFAULT_ROOTS:F._install(setup[2],setup[3],F._payload(root,session=session),root)
    stub=types.ModuleType('scripts.build_options_matrix');stub.DEFAULT_ROOTS=O.DEFAULT_ROOTS
    stub._r2_client=lambda:pytest.fail('injected store must remain selected')
    monkeypatch.setitem(sys.modules,'scripts.build_options_matrix',stub)
    argv=['--repo',str(setup[0]),'--out',str(setup[2]),'--bucket','fixture']
    if requested:argv+=['--identity-vendor','thetadata']
    assert O.main(argv,client=setup[3])==expected
    result=json.loads(capsys.readouterr().out)
    assert result['complete']
    if requested:assert result['identity']['scope']==['SPY']
    else:assert 'identity' not in result

def test_cli_missing_identity_precedes_client_creation(setup,monkeypatch):
    (setup[1]/'_receipt.json').unlink()
    stub=types.ModuleType('scripts.build_options_matrix');stub.DEFAULT_ROOTS=O.DEFAULT_ROOTS
    stub._r2_client=lambda:pytest.fail('client must not be constructed after input refusal')
    monkeypatch.setitem(sys.modules,'scripts.build_options_matrix',stub)
    assert O.main(['--repo',str(setup[0]),'--out',str(setup[2]),'--bucket','fixture','--identity-vendor','thetadata'])==2
    assert setup[3].calls==[]

def test_receipt_includes_identity_and_keeps_exclusive_publication(setup):
    path=setup[0]/'observation.json';result=observe(setup,receipt_path=path)
    assert json.loads(path.read_text())==result
    before=path.read_bytes()
    with pytest.raises(O.ObservationRefused):observe(setup,receipt_path=path)
    assert path.read_bytes()==before


@pytest.mark.parametrize("change", ["remote", "local", "both", "remote_missing", "local_missing", "denied"])
def test_prior_reopen_rechecks_current_heads_before_identity_success(setup, change):
    prior, ref = _prior_for_current_fixture(setup)
    _, _, out, store, _, _ = setup
    head = retention.R2_PREFIX + "SPY.json"
    original = store.get_object
    fired = []

    def during_prior(*, Bucket, Key):
        response = original(Bucket=Bucket, Key=Key)
        if Key == ref.key:
            fired.append(Key)
            changed = F._payload("SPY", session="2026-10-12", spot=125)
            if change in {"remote", "both"}:
                store.objects[head] = changed
            if change in {"local", "both"}:
                (out / "SPY.json").write_bytes(changed)
            if change == "remote_missing":
                del store.objects[head]
            if change == "local_missing":
                (out / "SPY.json").unlink()
            if change == "denied":
                store.get_faults[head] = F.S3Error("AccessDenied", 403)
        return response

    store.get_object = during_prior
    result = observe(setup, prior_path=prior)
    assert fired == [ref.key]
    assert not result["complete"] and not result["stable"] and not result["advancing"]
    assert result["issues"].count("unstable") == 1
    expected = "denied" if change == "denied" else "concurrent_head_change"
    assert result["failures"]["SPY"]["code"] == expected
    assert not result["identity"]["complete"]
    assert result["identity"]["roots"]["SPY"]["reason"] == "snapshot_not_verified"
    assert all(stream.closed for stream in store.streams)


@pytest.mark.parametrize("session,advancing", [("2026-10-11", True), ("2026-10-12", False)])
def test_prior_reopen_stable_heads_keep_identity_and_session_semantics(setup, session, advancing):
    prior, _ = _prior_for_current_fixture(setup, session=session)
    result = observe(setup, prior_path=prior)
    assert result["complete"] and result["stable"] and result["identity"]["complete"]
    assert result["advancing"] is advancing
    assert result["repeated_source_date"] is not advancing
    assert not result["natural_invocation_verified"]
    assert result["natural_session_count"] is None
    head = retention.R2_PREFIX + "SPY.json"
    assert setup[3].calls.count(("get", head)) == 3


def test_prior_reopen_denial_does_not_add_post_failure_head_read(setup):
    prior, ref = _prior_for_current_fixture(setup)
    store = setup[3]
    store.get_faults[ref.key] = F.S3Error("AccessDenied", 403)
    result = observe(setup, prior_path=prior)
    assert not result["complete"] and not result["identity"]["complete"]
    assert result["failures"]["_prior"]["code"] == "denied_prior_history"
    assert store.calls.count(("get", ref.key)) == 1
    assert store.calls.count(("get", retention.R2_PREFIX + "SPY.json")) == 2


def test_no_prior_observation_keeps_existing_head_read_count(setup):
    result = observe(setup)
    assert result["identity"]["complete"]
    assert setup[3].calls.count(("get", retention.R2_PREFIX + "SPY.json")) == 2
