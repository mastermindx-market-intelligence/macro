"""Synthetic metadata/contracts and real composition code, no live grants/I/O."""
import dataclasses
import hashlib

import pytest

from app import options_auth as A
from engine.intelligence_workspace import options_matrix_delivery as D
from engine.intelligence_workspace.options_matrix_context import MatrixDatasetBinding
from engine.intelligence_workspace.options_source_use import SourceUseRefused
from lib.dataos.registry import Registry, load_registry
from tests import test_options_auth as Auth
from tests.test_options_auth import env  # existing fake Auth/billing fixture
from tests import test_options_matrix_context as C
from tests import test_options_selection_composition as F
from tests import test_options_source_use as P


@pytest.fixture
def native():
    x = C.captured.__wrapped__()
    doc = x['f']['doc']
    doc['_build_meta'] = dict(
        asof_date='2026-10-12', t2_date='2026-10-09',
        source_dates=dict(eod='2026-10-12', greeks='2026-10-12',
            oi_publication='2026-10-12', previous_oi_publication='2026-10-09',
            latest_oi_publication='2026-10-13'),
        unusual_history_sessions_available=2,
        unusual_history_window_start='2026-10-08',
        unusual_history_window_end='2026-10-09',
    )
    x['raw'] = F.encoded(doc)
    x['identity'] = F.resolve(x['f'])
    x['ref'] = x['identity'].matrix.snapshot
    x['matrix'] = F.capture(x['raw'])
    leaves = [P.source_contract(dataset_id='synthetic.'+role, vendor='thetadata', rights={})
              for role in ('oi', 'eod', 'greeks')]
    x['row'] = dataclasses.replace(x['row'], inputs=tuple(r.dataset_id for r in leaves))
    x['reg'] = Registry([x['row'], *leaves])
    x['inputs'] = tuple(D.MatrixInputContract(role, row.dataset_id, row.version)
                        for role, row in zip(('oi', 'eod', 'greeks'), leaves))
    x['binding'] = MatrixDatasetBinding(x['ref'], x['row'].dataset_id, x['row'].version,
                                        'thetadata', 'synthetic.matrix-family')
    return x


def capture(x):
    raw = F.encoded(x['f']['doc'])
    ref = dataclasses.replace(x['ref'], sha256=hashlib.sha256(raw).hexdigest(), byte_length=len(raw))
    return D.capture_matrix_provenance(ref, raw)


def test_native_clocks_are_observations_not_known_at(native):
    p = capture(native)
    assert p.oi_publication == p.snapshot.session == '2026-10-12'
    assert p.latest_oi_publication == '2026-10-13'
    assert p.build_asof.isoformat() == '2026-10-12T17:00:00+00:00'
    assert not hasattr(p, 'known_at') and not hasattr(p, 'input_sha256')
    assert D.bind_matrix_contracts(p, native['binding'], native['inputs'], native['reg']) == native['binding']


def test_explicit_absence_not_zero_or_synthetic_date(native):
    meta = native['f']['doc']['_build_meta']
    meta['source_dates'].update(eod=None, greeks=None, previous_oi_publication=None)
    meta.update(t2_date=None, unusual_history_sessions_available=0,
                unusual_history_window_start=None, unusual_history_window_end=None)
    p = capture(native)
    assert p.eod is p.greeks is p.previous_oi_publication is p.history_start is None
    assert p.history_sessions == 0


@pytest.mark.parametrize('field,value', [
    ('oi_publication', None), ('oi_publication', '2026-10-13'),
    ('previous_oi_publication', '2026-10-12'), ('previous_oi_publication', '2026-10-08'),
    ('latest_oi_publication', '2026-10-11'), ('eod', '2026-10-11'),
    ('greeks', '2026-10-13'), ('greeks', True), ('eod', 20261012),
    ('eod', '2026-02-30'), ('eod', '2026-1-12'), ('latest_oi_publication', None),
])
def test_source_clock_conflicts_refuse(native, field, value):
    native['f']['doc']['_build_meta']['source_dates'][field] = value
    with pytest.raises(SourceUseRefused): capture(native)


@pytest.mark.parametrize('field,value', [
    ('asof_date', '2026-10-13'), ('source_dates', None), ('t2_date', None),
    ('unusual_history_sessions_available', True), ('unusual_history_sessions_available', -1),
    ('unusual_history_sessions_available', 31), ('unusual_history_sessions_available', 0),
    ('unusual_history_sessions_available', 1), ('unusual_history_window_start', None),
    ('unusual_history_window_end', '2026-10-12'), ('unusual_history_window_start', '2026-10-10'),
])
def test_metadata_conflicts_refuse(native, field, value):
    native['f']['doc']['_build_meta'][field] = value
    with pytest.raises(SourceUseRefused): capture(native)


@pytest.mark.parametrize('value', [None, '', '2026-10-12', '2026-10-12T17:00:00', True, 'not-time'])
def test_build_clock_is_not_guessed(native, value):
    native['f']['doc']['asof'] = value
    with pytest.raises(SourceUseRefused): capture(native)


@pytest.mark.parametrize('key', ['asof_date', 'source_dates', 't2_date',
    'unusual_history_window_start', 'unusual_history_window_end', 'unusual_history_sessions_available'])
def test_missing_metadata_refuses(native, key):
    del native['f']['doc']['_build_meta'][key]
    with pytest.raises(SourceUseRefused): capture(native)


def test_changed_retained_bytes_refuse(native):
    with pytest.raises(SourceUseRefused):
        D.capture_matrix_provenance(native['ref'], native['raw'] + b' ')


def test_actual_builder_metadata_from_synthetic_parquets(tmp_path):
    from tests.test_options_matrix import _session_repair_store
    from engine.options_matrix import build_matrix
    # Exercises the existing producer, not a copied/reimplemented metadata schema.
    doc = build_matrix('SPY', _session_repair_store(tmp_path), asof='2026-09-22')
    raw = F.encoded(doc)
    p = D.capture_matrix_provenance(F.R.reference_for_bytes('SPY', raw), raw)
    assert p.snapshot.session == p.eod == p.greeks == p.oi_publication == '2026-09-22'
    assert p.latest_oi_publication == '2026-09-23'
    assert p.previous_oi_publication == '2026-09-21'
    assert p.history_sessions == 1 and p.history_start == p.history_end == '2026-09-21'


@pytest.mark.parametrize('defect', ['missing', 'role', 'version', 'duplicate', 'dag', 'retired', 'snapshot'])
def test_native_contract_join_refuses(native, defect):
    x = native
    inputs, binding, reg = x['inputs'], x['binding'], x['reg']
    if defect == 'missing': reg = Registry([])
    if defect == 'role': inputs = (dataclasses.replace(inputs[0], role='invented'), *inputs[1:])
    if defect == 'version': inputs = (dataclasses.replace(inputs[0], version='2'), *inputs[1:])
    if defect == 'duplicate': inputs = (inputs[0], inputs[0], inputs[2])
    if defect == 'dag': reg = Registry([dataclasses.replace(x['row'], inputs=x['row'].inputs[:2]), *reg.all()[1:]])
    if defect == 'retired':
        from lib.dataos.registry import DatasetStatus
        reg = Registry([dataclasses.replace(row, status=DatasetStatus.RETIRED) for row in reg.all()])
    if defect == 'snapshot': binding = dataclasses.replace(binding, snapshot=dataclasses.replace(x['ref'], sha256='0'*64))
    with pytest.raises(SourceUseRefused): D.bind_matrix_contracts(capture(x), binding, inputs, reg)


@pytest.mark.parametrize('field,value', [('role', []), ('dataset_id', True), ('version', '')])
def test_malformed_role_bindings_refuse(native, field, value):
    inputs = (dataclasses.replace(native['inputs'][0], **{field: value}), *native['inputs'][1:])
    with pytest.raises(SourceUseRefused):
        D.bind_matrix_contracts(capture(native), native['binding'], inputs, native['reg'])


def source(x, tmp_path):
    record = P.policy_record(dataset_id=x['row'].dataset_id, vendor='thetadata',
                             source_family=x['binding'].source_family, known_at='2026-10-01T00:00:00Z')
    record['actions'] = {'display': dict(record['actions']['display'],
        fields=list(x['f']['doc']), output='derived', channel='/api/flow?f=matrix:SPY',
        principal_id=Auth.UID, principal_issuer=Auth.ISS, auth_epoch=Auth.SID, customer_id=Auth.UID,
        required_rights={'redistribution': 'SYNTHETIC audit of whole payload'})}
    digest = P.write_policy(tmp_path, P.policy_bytes(record))
    return D.MatrixDisplaySource(x['reg'], x['binding'], x['inputs'],
        (('redistribution', 'SYNTHETIC whole payload audit'),), digest, record['registry_revision'], tmp_path)


def deliver(x, src, **changes):
    kw = {k: v for k, v in x['f']['kwargs'].items() if k != 'decision_at'}
    kw.update(release_body=x['raw'], access_token=Auth.token(), source=src, clock=lambda: F.NOW)
    kw.update(changes)
    return A.resolve_authenticated_matrix_display(x['ref'], x['matrix'], x['selected'], **kw)


def test_real_auth_composition_returns_exact_captured_body(native, tmp_path, env):
    result = deliver(native, source(native, tmp_path))
    assert result.body is native['raw']
    assert result.authorization.request.sha256 == hashlib.sha256(result.body).hexdigest()
    assert result.authorization.request.action == 'display'
    assert env.auth_calls == 2 and env.store_calls == 1
    assert not hasattr(result, 'save_allowed')


@pytest.mark.parametrize('failure', ['body', 'source', 'binding', 'registry', 'policy', 'entitlement', 'rights'])
def test_no_response_body_when_any_gate_missing(native, tmp_path, env, failure):
    src = source(native, tmp_path)
    changes = {}
    if failure == 'body': changes['release_body'] = native['raw'] + b' '
    if failure == 'source': src = None
    if failure == 'binding': src = dataclasses.replace(src, binding=None)
    if failure == 'registry': src = dataclasses.replace(src, registry=load_registry())
    if failure == 'policy': src = dataclasses.replace(src, evidence_sha256='0'*64)
    if failure == 'entitlement': env.row = dict(tier='free', features=[])
    if failure == 'rights': src = dataclasses.replace(src, required_rights_rationale=())
    with pytest.raises(A.OptionUseRefused): deliver(native, src, **changes)
    if failure in ('body', 'source', 'binding', 'registry'):
        assert env.auth_calls == env.store_calls == 0
