"""Options root/canonical SEC join; real in-memory Parquet, no live identity publication."""
from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib
import io
import json
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from lib.dataos import identity as I
from scripts import build_security_master as W
from engine.intelligence_workspace import entity as E
from engine.intelligence_workspace import options_identity as O
from engine import options_matrix_retention as R

D=date(2026,10,12)
SEC='SEC:US-ARCX-SYNTH'
CLOCK='2026-10-12T16:00:00Z'
CUTOFF='2026-10-12T17:00:00Z'
SOURCE=b'{"synthetic":"root-to-underlying fixture only"}'


def read(body, at=CUTOFF):
    return E.IdentityArtifactRead(body,hashlib.sha256(body).hexdigest(),at)


def parquet(rows, *, clocks=()):
    frame=pd.DataFrame(rows)
    for col in clocks:
        if col in frame: frame[col]=pd.to_datetime(frame[col])
    out=io.BytesIO()
    frame.to_parquet(out,index=False)
    return out.getvalue()


def master_record(**changes):
    row=dict(security_id=SEC,listing_key=SEC[4:],country='US',mic='ARCX',inception_code='SYNTH',
             effective_at='2026-10-11T00:00:00',ingested_at='2026-10-12T15:00:00',
             security_state=None,superseded_by=None)
    row.update(changes)
    return row


def alias_record(target=SEC,root='ROOTA',**changes):
    digest=hashlib.sha256(SOURCE).hexdigest()
    seal=I.option_root_binding_sha256('thetadata',root,target,D,None,CLOCK,digest)
    row=dict(vendor='thetadata',vendor_symbol=root,security_id=target,valid_from=D,valid_to=None,
             known_at=CLOCK,evidence_sha256=digest,binding_sha256=seal,alias_kind='occ_root',
             ingested_at='2026-10-12T16:01:00')
    row.update(changes)
    return row


def inputs(master=None, aliases=None):
    return dict(vendor='thetadata',root='ROOTA',on=D,decision_at=CUTOFF,
                aliases=read(parquet(aliases or [alias_record()],clocks=['ingested_at'])),
                security_master=read(parquet(master or [master_record()],clocks=['effective_at','ingested_at'])),
                root_evidence=read(SOURCE))


def resolve(**changes):
    args=inputs()
    args.update(changes)
    return E.resolve_option_underlying_security(**args)


@pytest.mark.parametrize('field', ['attempt_id', 'alias_family_id', 'alias_revision_id'])
def test_revision_metadata_cannot_disappear_at_projection(field, tmp_path):
    row = alias_record(**{field: 'unadmitted-revision'})
    body = parquet([row], clocks=['ingested_at'])
    with pytest.raises(E.IdentityResolutionError, match='observation history'):
        resolve(aliases=read(body))
    path = tmp_path / 'aliases.parquet'
    path.write_bytes(body)
    with pytest.raises(I.IdentityError, match='observation history writer'):
        W._read_existing(path, W.ALIAS_COLUMNS, W.ALIAS_DTYPES)


def test_nullable_revision_columns_do_not_require_context():
    row = alias_record(attempt_id=None, alias_family_id=None, alias_revision_id=None)
    result = resolve(aliases=read(parquet([row], clocks=['ingested_at'])))
    assert result.binding.vendor_symbol == 'ROOTA'


def test_actual_parquet_success_uses_current_record_and_preserves_inception_identity(tmp_path):
    # Exact extracted existing writer, including its declared naive UTC storage.
    path=tmp_path/'master.parquet'
    rows=[master_record()]
    W._write_parquet(rows,tuple(rows[0]),path,{'effective_at':'datetime','ingested_at':'datetime'})
    result=resolve(security_master=read(path.read_bytes()))
    assert result.binding.security_id==SEC
    assert result.binding.vendor_symbol=='ROOTA'  # no root == ticker assumption
    assert result.listing_key=='US-ARCX-SYNTH'
    assert result.available_at==datetime(2026,10,12,17,tzinfo=timezone.utc)
    assert result.master_sha256==hashlib.sha256(path.read_bytes()).hexdigest()


def test_two_roots_share_canonical_security_and_ordinary_reverse_stays_separate():
    args=inputs(aliases=[alias_record(),alias_record(root='ROOTB')])
    first=E.resolve_option_underlying_security(**args)
    second=E.resolve_option_underlying_security(**(args|{'root':'ROOTB'}))
    assert first.binding.security_id==second.binding.security_id==SEC
    rows=E._identity_parquet(args['aliases'],frozenset(alias_record()),frozenset({'ingested_at'}))
    table=I.VendorAliasTable.from_records(rows)
    assert table.resolve('thetadata','ROOTA',D) is None
    assert table.vendor_symbol_for('thetadata',SEC,D) is None


@pytest.mark.parametrize('field,value,match',[
    ('security_id','SEC:US-XNAS-OTHER','unknown canonical'),
    ('security_state','SUPERSEDED_DUPLICATE_MINT','retired or superseded'),
    ('security_state','RETIRED','retired or superseded'),
    ('security_state','','retired or superseded'),
    ('superseded_by','SEC:US-XNAS-OTHER','retired or superseded'),
    ('superseded_by','','retired or superseded'),
    ('listing_key','US-XNAS-SYNTH','listing fields conflict'),
    ('listing_key','us-arcx-synth','listing fields conflict'),
    ('country','CA','listing fields conflict'),
    ('mic','XNYS','listing fields conflict'),
    ('inception_code','ROOTA','listing fields conflict'),
    ('effective_at','2026-10-13T00:00:00','evidence clocks conflict'),
    ('ingested_at','2026-10-12T17:00:00.000000001','evidence clocks conflict'),
    ('ingested_at','2026-10-10T16:00:00','evidence clocks conflict'),
])
def test_bad_master_record_refuses(field,value,match):
    args=inputs(master=[master_record(**{field:value})])
    with pytest.raises(E.IdentityResolutionError,match=match): E.resolve_option_underlying_security(**args)


@pytest.mark.parametrize('duplicate', [master_record(), master_record(security_state='RETIRED')])
def test_duplicate_master_id_refuses_before_issuer_reader_fold(duplicate):
    args=inputs(master=[master_record(),duplicate])
    with pytest.raises(E.IdentityResolutionError,match='duplicate security'): E.resolve_option_underlying_security(**args)


def test_index_target_never_coerces_into_security():
    args=inputs(aliases=[alias_record(target='IDX:SYNTH-INDEX')])
    with pytest.raises(E.IdentityResolutionError,match='index underlying canonical'): E.resolve_option_underlying_security(**args)


@pytest.mark.parametrize('name',['aliases','security_master','root_evidence'])
def test_each_captured_body_is_hash_bound(name):
    args=inputs()
    args[name]=replace(args[name],body=args[name].body+b'changed')
    with pytest.raises(E.IdentityResolutionError,match='digest mismatch'): E.resolve_option_underlying_security(**args)


@pytest.mark.parametrize('name',['aliases','security_master','root_evidence'])
@pytest.mark.parametrize('bad_clock',['2026-10-12T17:00:01Z','2026-10-12T17:00:00.000000001Z','2026-10-12T17:00:00'])
def test_each_read_clock_requires_awareness_and_cutoff(name,bad_clock):
    args=inputs()
    args[name]=replace(args[name],read_at=bad_clock)
    with pytest.raises(E.IdentityResolutionError): E.resolve_option_underlying_security(**args)


def test_old_ingested_at_cannot_launder_new_master_capture():
    args=inputs(master=[master_record(ingested_at='2026-10-11T00:00:00')])
    args['security_master']=replace(args['security_master'],read_at='2026-10-13T00:00:00Z')
    with pytest.raises(E.IdentityResolutionError,match='after decision cutoff'): E.resolve_option_underlying_security(**args)


def test_root_source_exact_bytes_required_even_with_self_consistent_capture():
    with pytest.raises(E.IdentityResolutionError,match='source bytes do not match'): resolve(root_evidence=read(b'another synthetic source'))


@pytest.mark.parametrize('change',[
    {'root_evidence':read(SOURCE,'2026-10-12T15:59:59Z')},
    {'aliases':inputs()['aliases'].__class__(inputs()['aliases'].body,inputs()['aliases'].sha256,'2026-10-12T16:00:59Z')},
])
def test_relation_and_capture_clock_order_refuses(change):
    with pytest.raises(E.IdentityResolutionError,match='availability clocks conflict'): resolve(**change)


@pytest.mark.parametrize('name',['aliases','security_master'])
def test_invalid_parquet_is_typed_unavailable(name):
    with pytest.raises(E.IdentityResolutionError,match='Parquet'): resolve(**{name:read(b'not parquet')})


def test_plain_string_naive_storage_clock_is_not_promoted_to_utc():
    body=parquet([master_record()])
    with pytest.raises(E.IdentityResolutionError,match='column type'): resolve(security_master=read(body))


def test_typed_utc_timestamp_storage_is_supported():
    row=master_record(effective_at='2026-10-11T00:00:00Z',ingested_at='2026-10-12T15:00:00Z')
    assert E.resolve_option_underlying_security(**inputs(master=[row])).binding.security_id==SEC


def test_nanosecond_storage_evidence_not_truncated_early():
    args=inputs(master=[master_record(ingested_at='2026-10-12T16:59:59.999999999')])
    args['security_master']=replace(args['security_master'],read_at='2026-10-12T16:59:59.999999Z')
    with pytest.raises(E.IdentityResolutionError,match='evidence clocks conflict'): E.resolve_option_underlying_security(**args)


@pytest.mark.parametrize('changes',[{'on':datetime(2026,10,12,tzinfo=timezone.utc)}, {'on':'2026-10-12'}, {'decision_at':'2026-10-12T17:00:00'}, {'root':'roota'}])
def test_exact_query_refuses_coercion(changes):
    with pytest.raises(E.IdentityResolutionError): resolve(**changes)


def test_unmapped_and_future_or_expired_root_remain_unavailable():
    assert resolve(root='MISSING') is None
    assert resolve(on=date(2026,10,13)) is None
    args=inputs()
    args['decision_at']='2026-10-12T17:00:00.000000999Z' # cutoff floors; not authority to see future captures
    args['security_master']=replace(args['security_master'],read_at='2026-10-12T17:00:00.000000001Z')
    with pytest.raises(E.IdentityResolutionError): E.resolve_option_underlying_security(**args)


def test_byte_and_row_caps_before_decode(monkeypatch):
    monkeypatch.setattr(E,'_IDENTITY_MAX_BYTES',2)
    with pytest.raises(E.IdentityResolutionError,match='bound'): resolve()
    monkeypatch.setattr(E,'_IDENTITY_MAX_BYTES',16*1024*1024)
    monkeypatch.setattr(E,'_IDENTITY_MAX_ROWS',0)
    with pytest.raises(E.IdentityResolutionError,match='row bound'): resolve()


def test_missing_and_duplicate_columns_refuse():
    row=master_record();del row['listing_key']
    with pytest.raises(E.IdentityResolutionError,match='columns missing'): E.resolve_option_underlying_security(**inputs(master=[row]))
    table=pa.table([pa.array([1]),pa.array([2])],names=['security_id','security_id'])
    out=io.BytesIO();pq.write_table(table,out)
    with pytest.raises(E.IdentityResolutionError,match='columns missing or duplicated'): resolve(security_master=read(out.getvalue()))




@pytest.mark.parametrize('known,expected', [('2026-10-12T16:00:00.123456789Z',True), ('2026-10-12T17:00:00.000000001Z',False)])
def test_second_precision_writer_does_not_invent_subsecond_order(known,expected):
    row=alias_record(known_at=known,ingested_at='2026-10-12T16:00:00')
    row['binding_sha256']=I.option_root_binding_sha256(row['vendor'],row['vendor_symbol'],row['security_id'],D,None,known,row['evidence_sha256'])
    args=inputs(aliases=[row])
    result=E.resolve_option_underlying_security(**args)
    assert (result is not None) is expected


def matrix_inputs(root='ROOTA',session='2026-10-12',payload=None,aliases=None):
    value=payload if payload is not None else dict(schema=R.SCHEMA,root=root,session=session,cells=[])
    raw=json.dumps(value,separators=(',',':')).encode()
    ref=R.reference_for_bytes(root,raw)
    args=inputs(aliases=aliases)
    for key in ('root','on'): args.pop(key)
    return dict(ref=ref,matrix=read(raw),**args)


def test_matrix_join_exact_matrix_drives_root_session_and_identity_without_ticker_equality():
    args=matrix_inputs()
    result=O.resolve_option_matrix_security(**args)
    assert result.snapshot is args['ref']
    assert result.underlying.binding.vendor_symbol=='ROOTA'
    assert result.underlying.binding.security_id=='SEC:US-ARCX-SYNTH'
    assert result.available_at==datetime(2026,10,12,17,tzinfo=timezone.utc)
    # Empty cells are identity-only: no implicit membership, rights or Save claim.
    assert R.matrix_observed_side_tokens(result.snapshot,args['matrix'].body)==()


def test_matrix_join_meta_session_is_taken_only_from_verified_native_fallback():
    args=matrix_inputs(payload=dict(schema=R.SCHEMA,root='ROOTA',_build_meta={'asof_date':'2026-10-12'},cells=[]))
    assert O.resolve_option_matrix_security(**args).snapshot.session=='2026-10-12'


@pytest.mark.parametrize('change',[
    {'root':'ROOTB'}, {'session':'2026-10-11'}, {'sha256':'0'*64}, {'byte_length':1},
])
def test_matrix_join_reference_cannot_substitute_root_session_digest_or_length(change):
    args=matrix_inputs();args['ref']=replace(args['ref'],**change)
    with pytest.raises(E.IdentityResolutionError): O.resolve_option_matrix_security(**args)


@pytest.mark.parametrize('body',[
    b'{"schema":"options_structure.matrix/v1","root":"ROOTA","root":"ROOTB","session":"2026-10-12"}',
    b'{"schema":"options_structure.matrix/v1","root":"ROOTA","session":"2026-10-12","_build_meta":{"asof_date":"2026-10-11"}}',
    b'{"schema":"other","root":"ROOTA","session":"2026-10-12"}',
    b'{"schema":"options_structure.matrix/v1","root":"ROOTA","session":"2026-10-12","value":NaN}',
])
def test_matrix_join_matched_digest_does_not_admit_invalid_native_matrix(body):
    args=matrix_inputs(); args['matrix']=read(body)
    args['ref']=R.SnapshotReference('ROOTA',hashlib.sha256(body).hexdigest(),len(body),'2026-10-12')
    with pytest.raises(E.IdentityResolutionError): O.resolve_option_matrix_security(**args)


def test_matrix_join_missing_source_session_refuses_before_identity_lookup(monkeypatch):
    args=matrix_inputs(session=None)
    monkeypatch.setattr(O,'resolve_option_underlying_security',lambda *a,**k: pytest.fail('must not resolve'))
    with pytest.raises(E.IdentityResolutionError,match='source session unavailable'):
        O.resolve_option_matrix_security(**args)


@pytest.mark.parametrize('field,value,match',[
    ('read_at','2026-10-12T17:00:00.000000001Z','after decision cutoff'),
    ('read_at','2026-10-11T23:59:59Z','source session is after'),
    ('read_at','2026-10-12T16:00:00','invalid UTC clock'),
    ('sha256','0'*64,'digest mismatch'),
    ('body',b'changed','digest mismatch'),
])
def test_matrix_join_bad_matrix_read_refuses_before_identity_lookup(field,value,match,monkeypatch):
    args=matrix_inputs(); args['matrix']=replace(args['matrix'],**{field:value})
    monkeypatch.setattr(O,'resolve_option_underlying_security',lambda *a,**k: pytest.fail('must not resolve'))
    with pytest.raises(E.IdentityResolutionError,match=match): O.resolve_option_matrix_security(**args)


@pytest.mark.parametrize('change',[{'root':'UNBOUND'}, {'session':'2026-10-11'}])
def test_matrix_join_no_current_root_or_session_fallback(change):
    assert O.resolve_option_matrix_security(**matrix_inputs(**change)) is None


def test_matrix_join_vendor_namespace_is_explicit_and_no_ordinary_alias_fallback():
    args=matrix_inputs();args['vendor']='other_vendor'
    assert O.resolve_option_matrix_security(**args) is None


def test_matrix_join_available_at_includes_matrix_capture_completion():
    args=matrix_inputs();args['decision_at']='2026-10-12T17:01:00Z'
    args['matrix']=replace(args['matrix'],read_at='2026-10-12T17:00:30Z')
    result=O.resolve_option_matrix_security(**args)
    assert result.available_at==datetime(2026,10,12,17,0,30,tzinfo=timezone.utc)
    assert result.underlying.available_at==datetime(2026,10,12,17,tzinfo=timezone.utc)


def test_matrix_join_existing_resolver_error_stays_unavailable():
    args=matrix_inputs();row=master_record(security_state='RETIRED')
    args['security_master']=read(parquet([row],clocks=['effective_at','ingested_at']))
    with pytest.raises(E.IdentityResolutionError,match='retired or superseded'):
        O.resolve_option_matrix_security(**args)
