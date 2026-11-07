"""Candidate composition with real retained-byte and canonical identity readers.

Synthetic captured inputs only; no store, rights or Save admission.
"""
import dataclasses
from datetime import date, datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re

import pandas as pd
import pytest

from engine import options_matrix_retention as R
from engine.intelligence_workspace.entity import IdentityArtifactRead, IdentityResolutionError
from lib.dataos import identity

from engine.intelligence_workspace import options_identity as M
NOW = datetime(2026, 10, 12, 17, 2, tzinfo=timezone.utc)


def capture(body, at=NOW):
    return IdentityArtifactRead(body, hashlib.sha256(body).hexdigest(), at)


def parquet(rows, clocks=()):
    frame = pd.DataFrame(rows)
    for key in clocks:
        frame[key] = pd.to_datetime(frame[key])
    out = io.BytesIO()
    frame.to_parquet(out, index=False)
    return out.getvalue()


def coordinate(strike='500', side='call', expiry='2026-10-16'):
    return dict(expiry=expiry, strike=strike, side=side)


def selection(**changes):
    value = dict(schema='options_matrix_selection.v1', primary=coordinate(), comparisons=[],
                 view=dict(lens='chain', metric='volume', side='all', expiry='all', display_mode='3d'))
    value.update(changes)
    return value


def encoded(value):
    return json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()


@pytest.fixture
def inputs():
    evidence = encoded({'synthetic': True, 'purpose': 'selection composition test'})
    alias = dict(vendor='thetadata', vendor_symbol='SPY', security_id='SEC:US-ARCX-SYNTH',
                 valid_from=date(2026, 10, 12), valid_to=date(2026, 10, 13),
                 known_at='2026-10-12T16:00:00Z', alias_kind='occ_root',
                 ingested_at='2026-10-12T16:01:00', evidence_sha256=hashlib.sha256(evidence).hexdigest())
    alias['binding_sha256'] = identity.option_root_binding_sha256(
        alias['vendor'], alias['vendor_symbol'], alias['security_id'], alias['valid_from'],
        alias['valid_to'], alias['known_at'], alias['evidence_sha256'])
    master = dict(security_id='SEC:US-ARCX-SYNTH', listing_key='US-ARCX-SYNTH', country='US',
                  mic='ARCX', inception_code='SYNTH', effective_at='2026-10-11T00:00:00',
                  ingested_at='2026-10-12T15:00:00', security_state=None, superseded_by=None)
    doc = dict(schema=R.SCHEMA, root='SPY', session='2026-10-12', cells=[
        dict(strike=500, expiry='2026-10-16', call_oi=0, put_vol=0),
        dict(strike=505, expiry='2026-10-23', call_oi=1),
        dict(strike=510, expiry='2026-10-30'),
    ])
    return dict(doc=doc, master=master,
                kwargs=dict(vendor='thetadata', decision_at=NOW,
                            aliases=capture(parquet([alias], ['ingested_at'])),
                            security_master=capture(parquet([master], ['effective_at', 'ingested_at'])),
                            root_evidence=capture(evidence)))


def resolve(inputs, value=None, *, selection_raw=None, matrix_raw=None, ref=None, matrix=None):
    raw = matrix_raw if matrix_raw is not None else encoded(inputs['doc'])
    ref = ref or R.reference_for_bytes('SPY', raw)
    matrix = matrix or capture(raw)
    selected = selection_raw if selection_raw is not None else encoded(value or selection())
    return M.resolve_option_matrix_selection(ref, matrix, selected, **inputs['kwargs'])


def test_exact_subject_and_zero_side_witness(inputs):
    result = resolve(inputs)
    assert result.matrix.underlying.binding.security_id == 'SEC:US-ARCX-SYNTH'
    assert result.primary.strike == '500' and result.primary.side == 'call'
    assert result.matrix.snapshot.sha256 == hashlib.sha256(encoded(inputs['doc'])).hexdigest()
    assert result.matrix.available_at == NOW
    assert result.comparisons == () and result.comparisons_hidden == ()
    assert result.primary_hidden is False
    # Volume is syntactically preserved; call OI=0 witnesses side, not volume availability.
    assert result.view.metric == 'volume'
    assert not hasattr(result, 'allowed') and not hasattr(result, 'save_allowed')


def test_order_hidden_pins_and_primary_in_comparisons(inputs):
    value = selection(comparisons=[coordinate('505', expiry='2026-10-23'), coordinate(), coordinate(side='put')])
    value['view'].update(side='put', expiry='2026-10-16', metric='deltaOi', display_mode='table')
    before = encoded(value)
    result = resolve(inputs, value)
    assert [(x.strike, x.side) for x in result.comparisons] == [('505', 'call'), ('500', 'call'), ('500', 'put')]
    assert result.primary_hidden is True and result.comparisons_hidden == (True, True, False)
    assert result.view.metric == 'deltaOi' and result.view.display_mode == 'table'
    assert encoded(value) == before
    for obj, attr, val in [(result, 'primary_hidden', False), (result.primary, 'strike', '505'),
                           (result.view, 'side', 'all')]:
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(obj, attr, val)


def test_unobserved_expiry_is_still_in_full_snapshot(inputs):
    value = selection()
    value['view']['expiry'] = '2026-10-30'
    result = resolve(inputs, value)
    assert result.primary_hidden and result.primary.strike == '500'


@pytest.mark.parametrize('value', [coordinate('501'), coordinate('505', side='put', expiry='2026-10-23'),
                                  coordinate('510', expiry='2026-10-30')])
def test_missing_coordinate_or_own_side_refuses(inputs, value):
    with pytest.raises(IdentityResolutionError):
        resolve(inputs, selection(primary=value))


def test_missing_comparison_is_not_dropped(inputs):
    with pytest.raises(IdentityResolutionError):
        resolve(inputs, selection(comparisons=[coordinate(), coordinate('501')]))


def test_lossless_large_decimal_and_rounded_ui_value(inputs):
    raw = encoded(inputs['doc']).replace(b'"strike":500', b'"strike":999999999999.12345678')
    result = resolve(inputs, selection(primary=coordinate('999999999999.12345678')), matrix_raw=raw)
    assert result.primary.strike == '999999999999.12345678'
    with pytest.raises(IdentityResolutionError):
        resolve(inputs, selection(primary=coordinate('999999999999.1234')), matrix_raw=raw)


@pytest.mark.parametrize('change', ['duplicate_cell', 'fractional_count', 'bad_unselected_count', 'empty', 'null', 'wrong_session'])
def test_invalid_retained_membership(inputs, change):
    if change == 'duplicate_cell': inputs['doc']['cells'].append(dict(inputs['doc']['cells'][0]))
    elif change == 'fractional_count': inputs['doc']['cells'][0]['call_oi'] = 0.5
    elif change == 'bad_unselected_count': inputs['doc']['cells'][1]['put_vol'] = '1'
    elif change == 'empty': inputs['doc']['cells'] = []
    elif change == 'null': inputs['doc']['cells'] = None
    else: inputs['doc']['session'] = '2026-10-11'
    with pytest.raises(IdentityResolutionError): resolve(inputs)


@pytest.mark.parametrize('change', ['digest', 'future_read', 'retired', 'missing_target', 'wrong_vendor'])
def test_identity_prerequisites_are_real(inputs, change):
    args = {}
    if change == 'digest': args['matrix'] = dataclasses.replace(capture(encoded(inputs['doc'])), sha256='0' * 64)
    elif change == 'future_read': args['matrix'] = capture(encoded(inputs['doc']), '2026-10-12T17:03:00Z')
    elif change == 'wrong_vendor': inputs['kwargs']['vendor'] = 'yahoo'
    else:
        inputs['master']['security_state' if change == 'retired' else 'security_id'] = 'RETIRED' if change == 'retired' else 'SEC:US-ARCX-OTHER'
        inputs['kwargs']['security_master'] = capture(parquet([inputs['master']], ['effective_at', 'ingested_at']))
    with pytest.raises(IdentityResolutionError): resolve(inputs, **args)


@pytest.mark.parametrize('raw', [b'', b'{}', b'null', b'[]', b'\xff', b'{' + b'"a":[' * 340,
                                b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}',
                                b'{}' + b' ' * 2047, b'[' * 1000 + b']' * 1000])
def test_bad_encoded_selection_refuses(inputs, raw):
    with pytest.raises(IdentityResolutionError): resolve(inputs, selection_raw=raw)


def test_duplicate_keys_and_utf8_byte_limit(inputs):
    raw = encoded(selection())
    for old, new in [(b'"schema":', b'"schema":"ignored","schema":'),
                     (b'"strike":"500"', b'"strike":"501","strike":"500"')]:
        with pytest.raises(IdentityResolutionError): resolve(inputs, selection_raw=raw.replace(old, new, 1))
    assert resolve(inputs, selection_raw=raw + b' ' * (2048 - len(raw))).primary.strike == '500'
    with pytest.raises(IdentityResolutionError): resolve(inputs, selection_raw=raw + b' ' * (2049 - len(raw)))
    with pytest.raises(IdentityResolutionError): resolve(inputs, selection_raw=raw.decode())


@pytest.mark.parametrize('kind', ['bytearray', 'memoryview', 'dict'])
def test_selection_requires_immutable_bytes(inputs, kind):
    raw = encoded(selection())
    supplied = {'bytearray': bytearray(raw), 'memoryview': memoryview(raw), 'dict': selection()}[kind]
    with pytest.raises(IdentityResolutionError): resolve(inputs, selection_raw=supplied)


@pytest.mark.parametrize('strike', ['0', '00', '0500', '500.0', '+500', '-500', '5e2', '500\n',
                                   '0.000000001', '1000000000000', '999999999999.123456789', 500, None, True])
def test_noncanonical_strike_refuses(inputs, strike):
    with pytest.raises(IdentityResolutionError): resolve(inputs, selection(primary=coordinate(strike)))


@pytest.mark.parametrize('expiry', ['2026-02-29', '1900-02-29', '0000-01-01', '20261016', '2026-10-16\n', None])
def test_bad_date_refuses(inputs, expiry):
    with pytest.raises(IdentityResolutionError): resolve(inputs, selection(primary=coordinate(expiry=expiry)))


@pytest.mark.parametrize('change', ['extra_root', 'missing_primary', 'extra_coordinate', 'extra_view',
                                  'bad_schema', 'bad_metric', 'bad_lens', 'bad_mode', 'bad_side',
                                  'missing_view_field', 'four_comparisons', 'duplicate_comparisons',
                                  'missing_expiry', 'bad_view_expiry'])
def test_closed_shape_and_view_membership(inputs, change):
    value = selection()
    if change == 'extra_root': value['root'] = 'SPY'
    elif change == 'missing_primary': del value['primary']
    elif change == 'extra_coordinate': value['primary']['root'] = 'SPY'
    elif change == 'extra_view': value['view']['camera'] = 1
    elif change == 'bad_schema': value['schema'] = 'options_matrix_selection.v2'
    elif change == 'bad_metric': value['view']['metric'] = 'iv'
    elif change == 'bad_lens': value['view']['lens'] = 'volatility'
    elif change == 'bad_mode': value['view']['display_mode'] = 'auto'
    elif change == 'bad_side': value['primary']['side'] = 'all'
    elif change == 'missing_view_field': del value['view']['metric']
    elif change == 'four_comparisons': value['comparisons'] = [coordinate()] * 4
    elif change == 'duplicate_comparisons': value['comparisons'] = [coordinate(), dict(reversed(list(coordinate().items())))]
    elif change == 'missing_expiry': value['view']['expiry'] = '2026-11-06'
    else: value['view']['expiry'] = '2026-02-29'
    with pytest.raises(IdentityResolutionError): resolve(inputs, value)


VECTORS = json.loads((Path(__file__).parent / 'fixtures' / 'options_matrix_selection_vectors_v1.json').read_text())['vectors']


@pytest.mark.parametrize('vector', VECTORS, ids=lambda v: v['name'])
def test_shared_iw2_vectors_with_exact_source_membership(inputs, vector):
    """Reuse the unchanged cross-language corpus against this new composition.

    Matrix rows are synthetic and populated for every representable coordinate;
    these are end-to-end outcomes, not an independent parser-only test count.
    """
    value = vector['input']
    positions = []
    if isinstance(value, dict):
        positions.append(value.get('primary'))
        if isinstance(value.get('comparisons'), list): positions.extend(value['comparisons'])
    rows = {}
    for position in positions:
        if not isinstance(position, dict): continue
        expiry, strike = position.get('expiry'), position.get('strike')
        if not isinstance(expiry, str) or not isinstance(strike, str): continue
        if not re.fullmatch(r'(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{0,7}[1-9])?', strike) or strike == '0': continue
        try: date.fromisoformat(expiry)
        except ValueError: continue
        rows[(expiry, strike)] = ('{"strike":' + strike + ',"expiry":' + json.dumps(expiry)
                                  + ',"call_oi":0,"put_vol":0}')
    # The expiry filter can legitimately address a row with no selected pin.
    view = value.get('view', {}) if isinstance(value, dict) else {}
    expiry = view.get('expiry') if isinstance(view, dict) else None
    if isinstance(expiry, str) and expiry != 'all':
        try: date.fromisoformat(expiry)
        except ValueError: pass
        else: rows.setdefault((expiry, '777'), '{"strike":777,"expiry":' + json.dumps(expiry) + ',"call_oi":0}')
    raw = ('{"schema":"options_structure.matrix/v1","root":"SPY","session":"2026-10-12","cells":['
           + ','.join(rows.values()) + ']}').encode()
    if vector['valid']:
        result = resolve(inputs, selection_raw=encoded(value), matrix_raw=raw)
        assert dataclasses.asdict(result.primary) == value['primary']
        assert [dataclasses.asdict(c) for c in result.comparisons] == value['comparisons']
        assert dataclasses.asdict(result.view) == value['view']
    else:
        with pytest.raises(IdentityResolutionError):
            resolve(inputs, selection_raw=encoded(value), matrix_raw=raw)
