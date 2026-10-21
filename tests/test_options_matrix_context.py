"""Native context integration: synthetic captures/policy, no grant or I/O effects."""
import dataclasses
import hashlib
import json
import uuid

import pytest

from engine.intelligence_workspace import options_matrix_context as C
from engine.intelligence_workspace import options_source_use as S
from engine.intelligence_workspace.options_use import OptionUseRequest
from lib.dataos.registry import Registry
from tests import test_options_selection_composition as F
from tests import test_options_source_use as P


@pytest.fixture
def captured():
    f = F.inputs.__wrapped__()
    # Native producer-shaped members, including embedded observations and
    # derived quantities. Fixtures are synthetic, never production metadata.
    f['doc'].update(asof='2026-10-12T17:00:00Z', spot=500, expiries=['2026-10-16'],
                    strikes=[500, 505], levels={'call_wall': 505},
                    heat_seeker={'gex': {'strike': 500}}, authority_tier='display',
                    experimental=True, reliability={'gex': 'assumption-signed'},
                    _build_meta={'source_dates': {'eod': '2026-10-12'}})
    f['doc']['cells'][0].update(call_vol=12, put_oi=3, gex=100,
        delta_oi={'call': 2, 'put': None}, unusual={'call': {'ratio': 2.1}}, vex_mn=.4)
    raw = F.encoded(f['doc'])
    selected = F.encoded(F.selection())
    ident = F.resolve(f, selection_raw=selected)
    leaf = P.source_contract(dataset_id='synthetic.theta-input', vendor='thetadata', rights={})
    row = P.source_contract(layer='L3', dataset_id='synthetic.matrix', vendor='thetadata',
        inputs=[leaf.dataset_id], temporal_profile='DERIVED',
        schema={key: {'type': 'json'} for key in f['doc']})
    reg = Registry([row, leaf])
    binding = C.MatrixDatasetBinding(ident.matrix.snapshot, row.dataset_id, row.version,
                                    row.vendor, 'synthetic.matrix-family')
    resolver = C.MatrixDisplayContextResolver(
        identity=ident, matrix=F.capture(raw), selection=selected, release_body=raw,
        principal_id=P.PRINCIPAL, principal_issuer=P.ISSUER, auth_epoch=P.EPOCH,
        registry=reg, dataset_binding=binding,
        required_rights_rationale=(('redistribution', 'SYNTHETIC audited whole document delivery scope'),))
    q = OptionUseRequest(uuid.uuid4().hex, P.PRINCIPAL, P.ISSUER, P.EPOCH,
        S.MATRIX_OWNER, S.MATRIX_SCHEMA, 'SPY', ident.matrix.snapshot.sha256, len(raw),
        '2026-10-12', 'thetadata', ident.matrix.underlying.binding.security_id,
        hashlib.sha256(selected).hexdigest(), 'display')
    return dict(f=f, raw=raw, selected=selected, row=row, leaf=leaf, reg=reg,
                binding=binding, resolver=resolver, request=q)


def test_full_payload_not_selected_metric_and_new_nonce(captured):
    x = captured
    ctx = x['resolver'](x['request'])
    assert ctx.fields == tuple(sorted(x['f']['doc']))
    assert {'cells', 'levels', 'heat_seeker', '_build_meta', 'spot'} <= set(ctx.fields)
    assert ctx.output == 'derived'
    assert ctx.channel == '/api/flow?f=matrix:SPY'
    assert ctx.recipients == ('authenticated_customer',) and ctx.customer_id == P.PRINCIPAL
    assert ctx.required_rights == ('redistribution',)  # explicit audited input, no verb default
    fresh = dataclasses.replace(x['request'], request_id=uuid.uuid4().hex)
    assert x['resolver'](fresh).binding is fresh
    # cells names the WHOLE delivered subtree: volume, OI, delta, GEX, unusual,
    # VEX all remain in release_body although the selected view says volume.
    assert {'call_vol', 'call_oi', 'delta_oi', 'gex', 'unusual', 'vex_mn'} <= set(
        json.loads(x['resolver'].release_body)['cells'][0])


@pytest.mark.parametrize('field', ['principal_id', 'principal_issuer', 'auth_epoch',
    'owner', 'schema', 'root', 'sha256', 'byte_length', 'session', 'vendor',
    'underlying_id', 'selection_sha256', 'action'])
def test_request_substitution_refuses(captured, field):
    x = captured
    bad = x['request'].byte_length + 1 if field == 'byte_length' else (
        'export' if field == 'action' else '0' * 64 if 'sha256' in field else 'different')
    with pytest.raises(S.SourceUseRefused):
        x['resolver'](dataclasses.replace(x['request'], **{field: bad}))


@pytest.mark.parametrize('change', ['missing_binding', 'wrong_snapshot', 'version',
    'family', 'missing_mapping', 'unknown_right', 'blank_rationale', 'raw_layer',
    'augmented_release', 'selection', 'matrix'])
def test_missing_or_changed_native_inputs_refuse(captured, change):
    x = captured
    updates = {}
    if change == 'missing_binding': updates['dataset_binding'] = None
    if change == 'wrong_snapshot': updates['dataset_binding'] = dataclasses.replace(
        x['binding'], snapshot=dataclasses.replace(x['binding'].snapshot, sha256='0' * 64))
    if change == 'version': updates['dataset_binding'] = dataclasses.replace(x['binding'], dataset_version='2')
    if change == 'family': updates['dataset_binding'] = dataclasses.replace(x['binding'], source_family='')
    if change == 'missing_mapping': updates['required_rights_rationale'] = ()
    if change == 'unknown_right': updates['required_rights_rationale'] = (('display', 'not native'),)
    if change == 'blank_rationale': updates['required_rights_rationale'] = (('redistribution', ''),)
    if change == 'raw_layer': updates['registry'] = Registry([
        dataclasses.replace(x['row'], layer=C.Layer.L0_SOURCE), x['leaf']])
    if change == 'augmented_release': updates['release_body'] = x['raw'][:-1] + b',"stale":true}'
    if change == 'selection': updates['selection'] = x['selected'] + b' '
    if change == 'matrix': updates['matrix'] = dataclasses.replace(x['resolver'].matrix, body=x['raw'] + b' ')
    with pytest.raises(S.SourceUseRefused):
        dataclasses.replace(x['resolver'], **updates)(x['request'])


def backend(tmp_path, x, *, scope_changes=None, registry=None, resolver=None):
    record = P.policy_record(dataset_id=x['row'].dataset_id, vendor='thetadata',
        source_family=x['binding'].source_family)
    record['actions'] = {'display': dict(record['actions']['display'],
        fields=list(x['f']['doc']), channel='/api/flow?f=matrix:SPY',
        required_rights={'redistribution': 'SYNTHETIC full payload scope'})}
    record['actions']['display'].update(scope_changes or {})
    # F.NOW predates the older adapter fixture's window; keep all synthetic.
    record.update(known_at='2026-10-01T00:00:00Z')
    digest = P.write_policy(tmp_path, P.policy_bytes(record))
    return S.OptionsSourceUseBackend(registry=registry or x['reg'],
        dataset_id=x['row'].dataset_id, expected_evidence_sha256=digest,
        expected_registry_revision=record['registry_revision'],
        expected_source_family=record['source_family'],
        use_context_for_request=resolver or x['resolver'], evidence_root=tmp_path,
        clock=lambda: F.NOW)


def test_composite_explicit_policy_and_native_lineage_join(captured, tmp_path):
    x = captured
    assert backend(tmp_path, x).decision(x['request'])['status'] == 'allowed'
    # Input rights are not inherited, and no requirement is guessed for inputs:
    # the leaf's rights block is empty; the explicit composite evidence applies.
    assert not x['leaf'].rights


@pytest.mark.parametrize('defect', ['missing', 'duplicate', 'cycle', 'proposed', 'derived_no_inputs'])
def test_native_lineage_gap_refuses(captured, tmp_path, defect):
    x = captured
    leaf = x['leaf']
    rows = [x['row'], leaf]
    if defect == 'missing': rows.pop()
    if defect == 'duplicate': rows.append(dataclasses.replace(leaf, version='other'))
    if defect == 'cycle': rows[1] = dataclasses.replace(leaf, inputs=(x['row'].dataset_id,))
    if defect == 'proposed':
        from lib.dataos.registry import DatasetStatus
        rows[1] = dataclasses.replace(leaf, status=DatasetStatus.PROPOSED)
    if defect == 'derived_no_inputs': rows[1] = dataclasses.replace(leaf, layer=C.Layer.L3_DERIVED)
    reg = Registry(rows)
    b = backend(tmp_path, x, registry=reg, resolver=dataclasses.replace(x['resolver'], registry=reg))
    with pytest.raises(S.SourceUseRefused) as e: b.decision(x['request'])
    assert e.value.code == 'registry_contract_invalid'


def test_no_inherited_grant_no_new_field_or_raw_escape(captured, tmp_path):
    x = captured
    with pytest.raises(S.SourceUseRefused):
        backend(tmp_path / 'field', x, scope_changes={'fields': ['cells']}).decision(x['request'])
    raw_context = lambda req: dataclasses.replace(x['resolver'](req), output='raw')
    with pytest.raises(S.SourceUseRefused):
        backend(tmp_path / 'raw', x, resolver=raw_context,
                scope_changes={'output': 'raw'}).decision(x['request'])
    row = dataclasses.replace(x['row'], rights={})
    reg = Registry([row, x['leaf']])
    with pytest.raises(S.SourceUseRefused) as e:
        backend(tmp_path / 'grant', x, registry=reg,
            resolver=dataclasses.replace(x['resolver'], registry=reg)).decision(x['request'])
    assert e.value.code == 'right_not_granted'


def test_selection_bytes_must_match_native_identity_even_when_request_digest_matches(captured):
    x = captured
    changed = F.selection()
    changed['view']['metric'] = 'deltaOi'
    raw = F.encoded(changed)
    request = dataclasses.replace(x['request'], selection_sha256=hashlib.sha256(raw).hexdigest())
    resolver = dataclasses.replace(x['resolver'], selection=raw)
    with pytest.raises(S.SourceUseRefused) as e:
        resolver(request)
    assert e.value.code == 'context_binding_mismatch'


def test_new_top_level_release_member_needs_explicit_scope(captured, tmp_path):
    x = captured
    changed = dict(x['f']['doc'], new_vendor_payload={'restricted': 1})
    raw = F.encoded(changed)
    f = dict(x['f'], doc=changed)
    ident = F.resolve(f, selection_raw=x['selected'])
    binding = dataclasses.replace(x['binding'], snapshot=ident.matrix.snapshot)
    resolver = dataclasses.replace(x['resolver'], identity=ident, matrix=F.capture(raw),
                                  release_body=raw, dataset_binding=binding)
    row = dataclasses.replace(x['row'], schema=dict(x['row'].schema, new_vendor_payload={'type': 'json'}))
    reg = Registry([row, x['leaf']])
    resolver = dataclasses.replace(resolver, registry=reg)
    request = dataclasses.replace(x['request'], sha256=ident.matrix.snapshot.sha256, byte_length=len(raw))
    # Old policy has every old field; it cannot silently cover the new member.
    with pytest.raises(S.SourceUseRefused) as e:
        backend(tmp_path, x, registry=reg, resolver=resolver).decision(request)
    assert e.value.code == 'scope_mismatch'


@pytest.mark.parametrize('binding_present', [True, False])
def test_existing_composed_consumer_uses_native_context_or_rights_unavailable(captured, tmp_path, binding_present):
    from engine.intelligence_workspace.options_use import (
        resolve_authorized_option_selection, OptionUseRefused)
    x = captured
    calls = []
    resolver = x['resolver'] if binding_present else dataclasses.replace(x['resolver'], dataset_binding=None)
    b = backend(tmp_path, x, resolver=resolver)
    kwargs = dict(x['f']['kwargs'])
    kwargs.pop('decision_at')
    def entitlement(request):
        calls.append(request)
        return True
    kwargs.update(principal_id=P.PRINCIPAL, principal_issuer=P.ISSUER, auth_epoch=P.EPOCH,
        action='display', fresh_entitlement=entitlement, source_use_decision=b.decision,
        clock=lambda: F.NOW)
    args = (x['binding'].snapshot, x['resolver'].matrix, x['selected'])
    if binding_present:
        result = resolve_authorized_option_selection(*args, **kwargs)
        assert result.request is calls[0] and result.source_family == x['binding'].source_family
    else:
        with pytest.raises(OptionUseRefused) as e:
            resolve_authorized_option_selection(*args, **kwargs)
        assert e.value.code == 'rights_unavailable'
    assert len(calls) == 1
