"""Forward Options-root relations: synthetic evidence, actual owner functions."""
from dataclasses import replace
from datetime import date, datetime, timezone
import hashlib
import pandas as pd
import pytest
from lib.dataos import identity as I
from scripts import build_security_master as W

D = date(2026, 10, 12)
CLOCK = '2026-10-12T16:00:00Z'
SEC = 'SEC:US-XNAS-SYNTH'
IDX = 'IDX:SYNTH-INDEX'
EVIDENCE = b'{"fixture":"synthetic root relation, no market authority"}'
DIGEST = hashlib.sha256(EVIDENCE).hexdigest()
NOW = '2026-10-15T07:00:00'

def root_row(root='ROOTA', target=SEC, start=D, end=None, known=CLOCK, vendor='thetadata'):
    seal = I.option_root_binding_sha256(vendor, root, target, start, end, known, DIGEST)
    return I.AliasRow(vendor, root, target, start, end, known, DIGEST, seal, alias_kind='occ_root')


def records(rows):
    return W.merge_alias_rows(rows, [], NOW)


def lookup(table, root='ROOTA', on=D, cutoff=CLOCK, evidence=EVIDENCE, vendor='thetadata'):
    return table.resolve_option_underlying(vendor, root, on, decision_at=cutoff, evidence_bytes=evidence)


@pytest.mark.parametrize('target,kind', [(SEC, 'security'), (IDX, 'index')])
def test_many_roots_one_target_stays_forward_only(target, kind):
    table = I.VendorAliasTable([root_row('ROOTA', target), root_row('ROOTB', target)])
    assert lookup(table).security_id == target
    assert lookup(table, 'ROOTB').underlying_kind == kind
    assert table.resolve('thetadata', 'ROOTA', D) is None
    assert table.vendor_symbol_for('thetadata', target, D) is None


def test_ordinary_reverse_uniqueness_and_native_cutoff_still_apply():
    with pytest.raises(I.IdentityError, match='ambiguous'):
        I.VendorAliasTable([I.AliasRow('yahoo', 'A', SEC), I.AliasRow('yahoo', 'B', SEC)])
    args = ('polygon', 'SYNTH', SEC, D, None, CLOCK, DIGEST)
    row = I.AliasRow(*args, I.alias_binding_sha256(*args))
    table = I.VendorAliasTable([row, root_row()])
    assert table.resolve('polygon', 'SYNTH', D, decision_at='2026-10-12T15:00:00Z') is None
    assert table.vendor_symbol_for('polygon', SEC, D, decision_at=CLOCK) == 'SYNTH'


def test_legacy_file_without_kind_remains_readable(tmp_path):
    rows = records([I.AliasRow('yahoo', 'SYNTH', SEC)])
    columns = tuple(c for c in W.ALIAS_COLUMNS if c != 'alias_kind')
    path = tmp_path / 'legacy.parquet'
    W._write_parquet(rows, columns, path, W.ALIAS_DTYPES)
    reread = W._read_existing(path, W.ALIAS_COLUMNS, W.ALIAS_DTYPES,
                             allow_missing=W.OPTIONAL_ALIAS_COLUMNS)
    assert reread == rows
    assert I.VendorAliasTable.from_records(reread).resolve('yahoo', 'SYNTH', D) == SEC


def test_new_alias_writes_emit_the_full_declared_schema(tmp_path):
    from lib.dataos.registry import load_registry
    path = tmp_path / 'current.parquet'
    rows = records([root_row(), I.AliasRow('yahoo', 'SYNTH', SEC)])
    W._write_parquet(rows, W.ALIAS_COLUMNS, path, W.ALIAS_DTYPES)
    frame = pd.read_parquet(path)
    assert list(frame.columns) == list(load_registry().get('reference.vendor_aliases').schema)
    assert frame.loc[frame.vendor == 'thetadata', 'alias_kind'].tolist() == ['occ_root']
    assert frame.loc[frame.vendor == 'yahoo', 'alias_kind'].isna().all()


def test_revisioned_context_cannot_be_read_as_static_root():
    table = I.VendorAliasTable([root_row()])
    table._observation_state = ('synthetic unadmitted context',)
    with pytest.raises(I.IdentityError, match='admitted observation context'):
        lookup(table)


def test_theme_loader_preserves_forward_relation_and_revision_refusal(tmp_path):
    from engine.theme_graph import identity_resolution as graph
    ref = tmp_path / 'reference'
    ref.mkdir()
    pd.DataFrame([{'security_id': SEC, 'listing_key': 'US-XNAS-SYNTH',
                   'inception_code': 'SYNTH'}]).to_parquet(ref / 'security_master.parquet', index=False)
    (ref / '_receipt.json').write_text('{}')
    rows = records([root_row(), root_row('ROOTB'), I.AliasRow('yahoo', 'SYNTH', SEC)])
    path = ref / 'vendor_aliases.parquet'
    W._write_parquet(rows, W.ALIAS_COLUMNS, path, W.ALIAS_DTYPES)
    got = graph.load_master_inputs(tmp_path)
    assert lookup(got.alias_table).security_id == SEC
    assert got.alias_table.resolve('thetadata', 'ROOTA', D) is None
    assert got.alias_table.resolve('yahoo', 'SYNTH', D) == SEC
    frame = pd.read_parquet(path)
    frame['attempt_id'] = 'unadmitted'
    frame.to_parquet(path, index=False)
    with pytest.raises(I.IdentityError, match='observation history'):
        graph.load_master_inputs(tmp_path)


def test_expectation_index_excludes_roots_and_refuses_revision_projection():
    from engine import k3e_expectation_surface as reader
    roots = records([root_row(vendor='yahoo')])
    roots[0]['ingested_at'] = datetime.fromisoformat(NOW)
    assert reader._build_alias_index(roots) == ('CHECKED', {})
    ordinary = records([I.AliasRow('yahoo', 'SYNTH', SEC)])
    ordinary[0]['ingested_at'] = datetime.fromisoformat(NOW)
    status, index = reader._build_alias_index(ordinary + roots)
    assert status == 'CHECKED' and set(index) == {('yahoo', 'SYNTH')}
    assert reader._build_alias_index([{**ordinary[0], 'attempt_id': 'unadmitted'}]) == ('ALIAS_TABLE_INVALID', {})


def test_forward_conflict_refuses_in_reader_and_writer():
    rows = [root_row(), root_row(target=IDX)]
    with pytest.raises(I.IdentityError, match='ambiguous'):
        I.VendorAliasTable(rows)
    with pytest.raises(I.IdentityError, match='ambiguous'):
        records(rows)


def test_root_reuse_has_exclusive_end_and_explicit_cutoff():
    early = root_row(start=date(2026, 10, 1), end=D)
    late = root_row(target=IDX)
    table = I.VendorAliasTable([early, late])
    assert lookup(table, on=date(2026, 10, 11)).security_id == SEC
    assert lookup(table).security_id == IDX
    assert lookup(table, on=date(2026, 9, 30)) is None
    assert lookup(table, on=date(2026, 10, 13)) is None  # future event at cutoff
    assert lookup(table, cutoff='2026-10-12T15:59:59Z') is None


def test_no_ticker_or_other_vendor_fallback_and_no_namespace_collision():
    ordinary = I.AliasRow('thetadata', 'ROOTA', 'SEC:US-XNAS-OTHER')
    table = I.VendorAliasTable([ordinary, root_row()])
    assert table.resolve('thetadata', 'ROOTA', D) == ordinary.security_id
    assert table.vendor_symbol_for('thetadata', ordinary.security_id, D) == 'ROOTA'
    assert lookup(table).security_id == SEC
    assert lookup(table, vendor='yahoo') is None
    assert lookup(I.VendorAliasTable([ordinary])) is None


@pytest.mark.parametrize('changes', [
    {'known_at': None}, {'known_at': '2026-10-12T16:00:00'},
    {'known_at': '2026-10-11T16:00:00Z'}, {'evidence_sha256': None},
    {'evidence_sha256': 'A'*64}, {'binding_sha256': '0'*64},
    {'valid_from': None}, {'valid_from': datetime(2026, 10, 12)},
    {'valid_to': D}, {'valid_to': '2026-10-13'},
    {'alias_kind': 'vendor_symbol'}, {'alias_kind': False},
    {'vendor': 'ThetaData'}, {'vendor_symbol': 'roota'},
    {'vendor_symbol': 'ROOT..A'}, {'vendor_symbol': ' ROOTA'},
])
def test_bad_root_row_refuses(changes):
    with pytest.raises(I.IdentityError):
        replace(root_row(), **changes)


@pytest.mark.parametrize('target', [None, 'SPX', 'SEC:US-XNAS-SYNTH ', 'sec:US-XNAS-SYNTH',
                                  'ISS:US-XNAS-SYNTH', 'US-XNAS-SYNTH', 'IDX:SYNTH-INDEX\n',
                                  'IDX:unknown-index', 'FUT:XCME:ES:202610'])
def test_untyped_or_coerced_target_refuses(target):
    with pytest.raises(I.IdentityError):
        I.option_underlying_kind(target)


@pytest.mark.parametrize('on,cutoff', [(None,CLOCK), ('2026-10-12',CLOCK),
                                      (datetime(2026,10,12),CLOCK),
                                      (D,None), (D,datetime(2026,10,12)), (D,'bad')])
def test_query_requires_event_and_decision_clocks_even_when_unmapped(on, cutoff):
    with pytest.raises(I.IdentityError):
        lookup(I.VendorAliasTable(), on=on, cutoff=cutoff)


def test_nanosecond_availability_rounds_up_and_decision_rounds_down():
    table = I.VendorAliasTable([root_row(known='2026-10-12T16:00:00.000000001Z')])
    assert lookup(table, cutoff='2026-10-12T16:00:00.000000999Z') is None
    assert lookup(table, cutoff='2026-10-12T16:00:00.000001Z') is not None
    assert lookup(table, cutoff='2026-10-12T09:00:00.000001-07:00') is not None


@pytest.mark.parametrize('evidence', [None, b'', EVIDENCE+b' ', bytearray(EVIDENCE), 'fixture'])
def test_exact_retained_bytes_required(evidence):
    with pytest.raises(I.IdentityError):
        lookup(I.VendorAliasTable([root_row()]), evidence=evidence)


def test_seal_covers_namespace_and_each_semantic_field():
    row = root_row()
    old_seal = I.alias_binding_sha256(row.vendor, row.vendor_symbol, row.security_id,
                                     D, None, CLOCK, DIGEST)
    assert old_seal != row.binding_sha256
    with pytest.raises(I.IdentityError):
        replace(row, binding_sha256=old_seal)
    for key, value in [('vendor','other'), ('vendor_symbol','ROOTB'), ('security_id',IDX),
                       ('valid_from',date(2026,10,11)), ('valid_to',date(2026,10,13)),
                       ('known_at','2026-10-12T17:00:00Z'), ('evidence_sha256','b'*64)]:
        with pytest.raises(I.IdentityError):
            replace(row, **{key:value})


def test_raw_record_types_and_bounds_are_not_string_coerced():
    rec = records([root_row()])[0]
    for key, value in [('vendor', None), ('vendor_symbol', 123), ('security_id', None),
                       ('valid_from','2026-10-12T12:00:00'), ('valid_from','20261012'),
                       ('valid_from','2026-10-12junk'), ('valid_to','2026-10-13junk')]:
        bad = {**rec, key:value}
        with pytest.raises(I.IdentityError):
            I.VendorAliasTable.from_records([bad])
        with pytest.raises(I.IdentityError):
            W.merge_alias_rows([], [bad], NOW)


def test_writer_preserves_root_kind_and_seals_and_original_ingestion():
    fresh = [root_row(), root_row('ROOTB',IDX), I.AliasRow('yahoo','SYNTH',SEC)]
    merged = records(fresh)
    assert len(merged) == 3
    again = W.merge_alias_rows(fresh, merged, '2026-10-16T00:00:00')
    assert again == merged
    assert lookup(I.VendorAliasTable.from_records(again)).underlying_kind == 'security'
    assert I.VendorAliasTable.from_records(again).vendor_symbol_for('yahoo',SEC,D) == 'SYNTH'


def test_writer_refuses_root_revision_duplicate_and_prune():
    existing = records([root_row()])
    changed = root_row(known='2026-10-12T17:00:00Z')
    with pytest.raises(I.IdentityError):
        W.merge_alias_rows([changed],existing,NOW)
    with pytest.raises(I.IdentityError):
        W.merge_alias_rows([],existing*2,NOW)
    with pytest.raises(W.VendorAliasPruneConflict):
        W._prune_stale_aliases(existing, [], frozenset({SEC}))
    with pytest.raises(I.IdentityError):
        W._prune_stale_aliases(existing,[root_row(end=date(2026,10,13))],frozenset())
    kept, pruned = W._prune_stale_aliases(existing,[root_row('ROOTB')],frozenset())
    assert kept == existing and pruned == []


def test_root_date_is_not_laundered_by_parquet_reader(tmp_path):
    bad = {**records([root_row()])[0], 'valid_from':'2026-10-12garbage'}
    path = tmp_path/'invalid-date.parquet'
    pd.DataFrame([bad]).to_parquet(path,index=False)
    with pytest.raises(I.IdentityError):
        W._read_existing(path,W.ALIAS_COLUMNS,W.ALIAS_DTYPES,allow_missing=W.OPTIONAL_ALIAS_COLUMNS)


@pytest.mark.parametrize('field,value', [('valid_from','2026-10-12garbage'),
                                       ('vendor_symbol',123), ('alias_kind','unknown')])
def test_writer_refuses_before_creating_a_malformed_artifact(tmp_path, field, value):
    bad = {**records([root_row()])[0],field:value}
    path = tmp_path/'must-not-exist.parquet'
    with pytest.raises(I.IdentityError):
        W._write_parquet([bad],W.ALIAS_COLUMNS,path,W.ALIAS_DTYPES)
    assert not path.exists()


def test_mixed_closed_open_bounds_and_ordinary_nulls_roundtrip(tmp_path):
    rows = records([root_row(end=date(2026,10,13)),root_row('ROOTB',IDX),
                    I.AliasRow('yahoo','SYNTH',SEC)])
    path = tmp_path/'mixed.parquet'
    W._write_parquet(rows,W.ALIAS_COLUMNS,path,W.ALIAS_DTYPES)
    read = W._read_existing(path,W.ALIAS_COLUMNS,W.ALIAS_DTYPES,allow_missing=W.OPTIONAL_ALIAS_COLUMNS)
    assert read == rows
    direct = I.VendorAliasTable.from_records(pd.read_parquet(path).to_dict('records'))
    assert lookup(direct,'ROOTB').security_id == IDX
