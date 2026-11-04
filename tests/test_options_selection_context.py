"""Adversarial selection-question parser and wrapper cases with mocked authority.

Direct cross-binding refusals plus fail-closed wrapper cases over synthetic
captured artifact reads; no live auth, store, rights, network or provider.
"""
from dataclasses import FrozenInstanceError
from datetime import datetime
import hashlib
import json
from types import SimpleNamespace

import pytest

from engine.intelligence_workspace.entity import IdentityArtifactRead
from engine.intelligence_workspace.options_use import OptionUseRequest
from engine.neuralweb import options_selection_context as M
from tests import test_options_selection_composition as F

NOW = F.NOW
ROOT = 'SPY'
SESSION = '2026-10-12'
DIGEST = 'a' * 64
BODY_BYTES = 1234
VERSION_REF = f'sha256:{DIGEST}:bytes:{BODY_BYTES}:session:{SESSION}'
UID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
OTHER_UID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
ISSUER = 'https://fixture.invalid/auth/v1'
TOKEN = 'e30.fixture-payload.sig'
MATRIX_BODY = b'fixture-matrix-body'
RECEIPT_KEYS = {'schema', 'state', 'authority', 'owner', 'object_type', 'object_id',
                'root', 'session', 'source_session_available', 'version_ref',
                'fingerprint', 'byte_length', 'selection_sha256', 'underlying_id',
                'vendor', 'source_family', 'identity_available_at',
                'source_decided_at', 'action', 'primary', 'comparisons', 'view',
                'scope'}


def pin(strike='500', side='call', expiry='2026-10-16'):
    """One minted pin in object-id field order: expiry, side, strike."""
    return (expiry, side, strike)


def object_id(primary=None, comparisons=(), view=('volume', 'all', 'all', '3d'),
              *, root=ROOT, session=SESSION):
    segments = [
        M._MINT_TAG, root, session, ','.join(primary or pin()),
        ';'.join(','.join(item) for item in comparisons), ','.join(view),
    ]
    return '/'.join(segments)


def evidence(**changes):
    value = dict(owner=M.OWNER, object_type=M.OBJECT_TYPE, object_id=object_id(),
                 mode=M.MODE, version_ref=VERSION_REF, fingerprint=DIGEST)
    value.update(changes)
    return value


def canonical(doc):
    return json.dumps(doc, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def question(selection_doc=None, *, evidence_dict=None):
    doc = F.selection() if selection_doc is None else selection_doc
    return {'schema': M.SCHEMA, 'evidence': evidence_dict or evidence(),
            'selection': canonical(doc)}


def change_evidence(question_value, **changes):
    value = dict(question_value)
    value['evidence'] = dict(value['evidence'], **changes)
    return value


def refuses(parse, code):
    with pytest.raises(M.OptionsQuestionUnavailable) as exc:
        parse()
    assert type(exc.value.code) is str and exc.value.code == code
    assert exc.value.args == (code,)
    return exc.value


def capture_bundle():
    return M.OptionsQuestionCapture(
        matrix=F.capture(MATRIX_BODY), aliases=F.capture(b'fixture-aliases'),
        security_master=F.capture(b'fixture-master'),
        root_evidence=F.capture(b'fixture-root-evidence'))


_UNSET = object()


def authorized(ref, selection, *, principal_id=UID, action='export', vendor='thetadata',
               request_id='fixture-request', underlying_id='SEC:US-ARCX-SYNTH',
               binding_security_id=None, selection_sha256=None, root=None, sha256=None,
               byte_length=None, session=_UNSET, owner='options_structure.matrix',
               schema='options_structure.matrix/v1', snapshot=None,
               available_at=NOW, decided_at=NOW, source_family='fixture.theta',
               primary=None, comparisons=(), primary_hidden=False,
               comparisons_hidden=(), view=None):
    """One synthetic authorized return built from actual incumbent types."""
    verified = SimpleNamespace(
        matrix=SimpleNamespace(
            snapshot=snapshot or ref,
            underlying=SimpleNamespace(
                binding=SimpleNamespace(
                    security_id=underlying_id if binding_security_id is None
                    else binding_security_id)),
            available_at=available_at),
        primary=primary or SimpleNamespace(expiry='2026-10-16', strike='500', side='call'),
        comparisons=comparisons,
        view=view or SimpleNamespace(lens='chain', metric='volume', side='all',
                                     expiry='all', display_mode='3d'),
        primary_hidden=primary_hidden, comparisons_hidden=comparisons_hidden)
    request = OptionUseRequest(
        request_id=request_id, principal_id=principal_id, principal_issuer=ISSUER,
        auth_epoch='fixture-session-id', owner=owner, schema=schema,
        root=root or ref.root, sha256=sha256 or ref.sha256,
        byte_length=ref.byte_length if byte_length is None else byte_length,
        session=ref.session if session is _UNSET else session, vendor=vendor,
        underlying_id=underlying_id,
        selection_sha256=selection_sha256 or hashlib.sha256(selection).hexdigest(),
        action=action)
    return SimpleNamespace(selection=verified, request=request,
                           source_family=source_family, policy_id='fixture.policy',
                           policy_revision='fixture.r1',
                           registry_revision='fixture.registry', decided_at=decided_at)


@pytest.fixture
def setup():
    q = question()
    parsed = M.parse_options_question(q)
    calls = []
    decision_calls = []

    def decision(request):
        decision_calls.append(request)
        return {'status': 'allowed'}

    def resolver(ref, matrix, selection, **kw):
        calls.append({'ref': ref, 'matrix': matrix, 'selection': selection, 'kw': kw})
        return authorized(ref, selection)

    capture = capture_bundle()

    def run(_question=None, **changes):
        kw = dict(access_token=TOKEN, expected_user_id=UID, captured=capture,
                  vendor='thetadata', source_use_decision=decision)
        kw.update(changes)
        return M.resolve_options_question(q if _question is None else _question, **kw)

    return SimpleNamespace(question=q, parsed=parsed, capture=capture, run=run,
                           calls=calls, decision_calls=decision_calls, decision=decision,
                           resolver=resolver)


def bind(monkeypatch, resolver):
    monkeypatch.setattr(M, 'resolve_authenticated_option_selection', resolver)


# --- direct parser ------------------------------------------------------------

def test_parse_exact_bindings_and_frozen_return():
    q = question()
    p = M.parse_options_question(q)
    assert type(p.ref).__name__ == 'SnapshotReference'
    assert (p.ref.root, p.ref.sha256, p.ref.byte_length, p.ref.session) == \
        (ROOT, DIGEST, BODY_BYTES, SESSION)
    assert p.ref.version_ref == VERSION_REF
    assert type(p.selection) is bytes and p.selection == q['selection'].encode('utf-8')
    assert json.loads(p.evidence_json) == q['evidence']
    assert p.evidence_json == canonical(q['evidence'])
    with pytest.raises((FrozenInstanceError, AttributeError)):
        p.selection = b'changed'


def test_parse_uses_native_reference_and_selection_contracts(monkeypatch):
    seen = []
    real_ref, real_doc, real_docs = M.parse_reference, M._parse_selection_document, \
        M._selection_documents

    def wrap_ref(root, version_ref, fingerprint):
        seen.append('reference')
        return real_ref(root, version_ref, fingerprint)

    def wrap_doc(raw):
        seen.append('document')
        return real_doc(raw)

    def wrap_docs(document):
        seen.append('closed-schema')
        return real_docs(document)

    monkeypatch.setattr(M, 'parse_reference', wrap_ref)
    monkeypatch.setattr(M, '_parse_selection_document', wrap_doc)
    monkeypatch.setattr(M, '_selection_documents', wrap_docs)
    p = M.parse_options_question(question())
    assert seen == ['reference', 'document', 'closed-schema']
    assert p.ref.root == ROOT


@pytest.mark.parametrize('change', [
    'extra_top_key', 'missing_selection', 'schema_wrong', 'schema_type',
    'evidence_type', 'evidence_extra_key', 'evidence_missing_key', 'owner_wrong',
    'object_type_wrong', 'mode_wrong', 'object_id_type', 'version_ref_type',
    'object_id_oversize', 'version_ref_oversize', 'selection_type',
    'selection_empty', 'selection_oversize', 'not_a_dict',
])
def test_closed_envelope_refusals(change):
    q = question()
    if change == 'extra_top_key':
        q['root'] = ROOT
    elif change == 'missing_selection':
        del q['selection']
    elif change == 'schema_wrong':
        q['schema'] = 'options.selection_question/v2'
    elif change == 'schema_type':
        q['schema'] = 7
    elif change == 'evidence_type':
        q['evidence'] = [q['evidence']]
    elif change == 'evidence_extra_key':
        q['evidence']['root'] = ROOT
    elif change == 'evidence_missing_key':
        del q['evidence']['mode']
    elif change == 'owner_wrong':
        q = change_evidence(q, owner='terminal.options_exposure.other')
    elif change == 'object_type_wrong':
        q = change_evidence(q, object_type='options_selection')
    elif change == 'mode_wrong':
        q = change_evidence(q, mode='live')
    elif change == 'object_id_type':
        q = change_evidence(q, object_id=7)
    elif change == 'version_ref_type':
        q = change_evidence(q, version_ref=None)
    elif change == 'object_id_oversize':
        q = change_evidence(q, object_id='x' * 257)
    elif change == 'version_ref_oversize':
        q = change_evidence(q, version_ref='sha256:' + DIGEST + ':bytes:' + '9' * 300)
    elif change == 'selection_type':
        q['selection'] = canonical(F.selection()).encode()
    elif change == 'selection_empty':
        q['selection'] = ''
    elif change == 'selection_oversize':
        q['selection'] = ' ' * 2049
    else:
        q = [q]
    expected = 'selection_oversize' if change == 'selection_oversize' else 'request_invalid'
    refuses(lambda: M.parse_options_question(q), expected)


@pytest.mark.parametrize('changes,code', [
    (dict(fingerprint='A' * 64), 'reference_invalid'),
    (dict(fingerprint='b' * 64), 'reference_invalid'),
    (dict(object_id=object_id(root='spy')), 'reference_invalid'),
    (dict(object_id=object_id(root='SP..Y')), 'reference_invalid'),
    (dict(object_id=object_id(root='')), 'reference_invalid'),
    (dict(version_ref=f'sha256:{DIGEST}:bytes:0:session:{SESSION}'), 'reference_invalid'),
    (dict(version_ref=f'sha256:{DIGEST}:bytes:1234:session:2026-10-13'), 'session_mismatch'),
], ids=lambda value: str(value)[:40])
def test_reference_incumbent_and_session_refusals(changes, code):
    q = change_evidence(question(), **changes)
    refuses(lambda: M.parse_options_question(q), code)


def test_unknown_session_requires_the_matching_version_ref():
    q = question()
    q = change_evidence(q, version_ref=f'sha256:{DIGEST}:bytes:{BODY_BYTES}:session:unknown')
    refuses(lambda: M.parse_options_question(q), 'session_mismatch')
    paired = change_evidence(question(), object_id=object_id(session='unknown'),
                             version_ref=f'sha256:{DIGEST}:bytes:{BODY_BYTES}:session:unknown')
    refuses(lambda: M.parse_options_question(paired), 'session_unavailable')


@pytest.mark.parametrize('session', ['2026-10-11', '2026-13-40', '20261012',
                                     '', '2026-10-12 ', '2026-02-30'])
def test_object_id_session_grammar(session):
    q = change_evidence(question(), object_id=object_id(session=session))
    code = 'session_mismatch' if session == '2026-10-11' else 'request_invalid'
    refuses(lambda: M.parse_options_question(q), code)


@pytest.mark.parametrize('primary', [
    pin('501'), pin(side='put'), pin(expiry='2026-10-23'), pin('500.0'), pin('0500'),
    pin('0'), pin('5e2'), pin('500.000000001'), ('2026-10-16', 'call'),
    ('2026-10-16', 'all', '500'), ('2026-02-30', 'call', '500'), ('', 'call', '500'),
])
def test_object_id_primary_cross_binding_and_grammar(primary):
    q = change_evidence(question(), object_id=object_id(primary=primary))
    expected = 'binding_mismatch' if primary in (pin('501'), pin(side='put'),
                                                 pin(expiry='2026-10-23')) \
        else 'request_invalid'
    refuses(lambda: M.parse_options_question(q), expected)


@pytest.mark.parametrize('comparisons', [
    (),
    (pin(),),
    (pin('506', expiry='2026-10-23'),),
    (pin('505', expiry='2026-10-23'), pin()),
    (pin(), pin('505', expiry='2026-10-23')),
], ids=['absent', 'wrong_pin', 'wrong_strike', 'extra_pin', 'swapped_order'])
def test_object_id_comparison_mismatch_refuses(comparisons):
    doc = F.selection(comparisons=[F.coordinate('505', expiry='2026-10-23')])
    q = question(selection_doc=doc)
    q = change_evidence(q, object_id=object_id(comparisons=comparisons))
    refuses(lambda: M.parse_options_question(q), 'binding_mismatch')


def test_matching_comparisons_parse_in_order():
    doc = F.selection(comparisons=[F.coordinate('505', expiry='2026-10-23'),
                                   F.coordinate(side='put')])
    minted = (pin('505', expiry='2026-10-23'), pin(side='put'))
    q = question(selection_doc=doc)
    q = change_evidence(q, object_id=object_id(comparisons=minted))
    p = M.parse_options_question(q)
    assert p.ref.root == ROOT  # exact ordered comparison raised no refusal


@pytest.mark.parametrize('view', [('iv', 'all', 'all', '3d'), ('volume', 'ALL', 'all', '3d'),
                                  ('volume', 'all', '2026-02-29', '3d'),
                                  ('volume', 'all', 'all', 'auto'), ('volume', 'all', 'all'),
                                  ('volume', 'all', 'all', '3d', 'extra')])
def test_object_id_view_grammar(view):
    q = change_evidence(question(), object_id=object_id(view=view))
    refuses(lambda: M.parse_options_question(q), 'request_invalid')


@pytest.mark.parametrize('view,field', [
    (('deltaOi', 'all', 'all', '3d'), 'metric'),
    (('volume', 'put', 'all', '3d'), 'side'),
    (('volume', 'all', '2026-10-16', '3d'), 'expiry'),
    (('volume', 'all', 'all', 'table'), 'display_mode'),
])
def test_object_id_view_cross_binding(view, field):
    q = change_evidence(question(), object_id=object_id(view=view))
    refuses(lambda: M.parse_options_question(q), 'binding_mismatch')


@pytest.mark.parametrize('mutation', ['duplicate_key', 'bad_schema', 'extra_root_key',
                                      'unknown_metric', 'four_comparisons',
                                      'strike_decimal', 'impossible_date', 'not_object',
                                      'invalid_json', 'nan_constant'])
def test_selection_contract_refusals_are_native(mutation):
    doc = F.selection()
    raw = canonical(doc)
    if mutation == 'duplicate_key':
        text = raw.replace('"schema":"options_matrix_selection.v1"',
                           '"schema":"options_matrix_selection.v1","schema":"ignored"', 1)
    elif mutation == 'bad_schema':
        doc['schema'] = 'options_matrix_selection.v2'
        text = canonical(doc)
    elif mutation == 'extra_root_key':
        doc['root'] = ROOT
        text = canonical(doc)
    elif mutation == 'unknown_metric':
        doc['view']['metric'] = 'iv'
        text = canonical(doc)
    elif mutation == 'four_comparisons':
        doc['comparisons'] = [F.coordinate()] * 4
        text = canonical(doc)
    elif mutation == 'strike_decimal':
        doc['primary']['strike'] = '500.0'
        text = canonical(doc)
    elif mutation == 'impossible_date':
        doc['primary']['expiry'] = '2026-02-30'
        text = canonical(doc)
    elif mutation == 'not_object':
        text = canonical([doc])
    elif mutation == 'nan_constant':
        text = '{"schema":"options_matrix_selection.v1","primary":NaN}'
    else:
        text = raw[:-1] + ',}'
    q = question()
    q['selection'] = text
    refuses(lambda: M.parse_options_question(q), 'selection_invalid')


@pytest.mark.parametrize('text', [canonical(F.selection()) + ' ',
                                  '{"primary":{"expiry":"2026-10-16","side":"call","strike":"500"},'
                                  '"comparisons":[],"schema":"options_matrix_selection.v1",'
                                  '"view":{"display_mode":"3d","expiry":"all","lens":"chain",'
                                  '"metric":"volume","side":"all"}}'])
def test_noncanonical_selection_string_refuses(text):
    q = question()
    q['selection'] = text
    refuses(lambda: M.parse_options_question(q), 'selection_noncanonical')


def test_root_follows_the_minted_object_id_through_the_incumbent_grammar():
    q = change_evidence(question(), object_id=object_id(root='QQQ'))
    p = M.parse_options_question(q)
    assert p.ref.root == 'QQQ'
    assert json.loads(p.evidence_json)['object_id'].split('/')[1] == 'QQQ'


# --- wrapper ------------------------------------------------------------------

def never_authenticate(*args, **kwargs):
    raise AssertionError('authentication reached before validation')


@pytest.mark.parametrize('changes', [
    dict(source_use_decision=None), dict(source_use_decision='native.source.policy'),
    dict(clock='now'), dict(access_token=None), dict(access_token=7),
    dict(access_token=''), dict(access_token='bad\ntoken'),
    dict(access_token='x' * 16385), dict(expected_user_id=None),
    dict(expected_user_id=''), dict(expected_user_id=' alice'),
    dict(expected_user_id='x' * 257), dict(vendor=None), dict(vendor=7),
    dict(captured=None), dict(captured={}), dict(source_use_decision=True),
])
def test_wrapper_scalar_and_callback_inputs_refuse_before_auth(monkeypatch, setup, changes):
    bind(monkeypatch, never_authenticate)
    if 'captured' in changes:
        expected = 'capture_invalid'
    elif set(changes) <= {'access_token', 'expected_user_id', 'vendor'}:
        expected = 'request_invalid'
    else:
        expected = 'callback_invalid'
    refuses(lambda: setup.run(**changes), expected)
    assert setup.calls == []


@pytest.mark.parametrize('bad', [None, {}, ['aliases'],
                                 M.OptionsQuestionCapture(matrix=None, aliases=None,
                                                          security_master=None,
                                                          root_evidence=None)])
def test_capture_bundle_requires_exact_artifact_reads(monkeypatch, setup, bad):
    bind(monkeypatch, never_authenticate)
    refuses(lambda: setup.run(captured=bad), 'capture_invalid')
    assert setup.calls == []


def test_identity_artifact_reads_are_accepted(monkeypatch, setup):
    bundle = capture_bundle()
    assert all(type(read) is IdentityArtifactRead for read in
               (bundle.matrix, bundle.aliases, bundle.security_master, bundle.root_evidence))


@pytest.mark.parametrize('mutation', ['wrong_schema', 'wrong_evidence', 'not_a_dict'])
def test_wrapper_invalid_question_refuses_before_auth(monkeypatch, setup, mutation):
    bind(monkeypatch, never_authenticate)
    q = dict(setup.question)
    if mutation == 'wrong_schema':
        q['schema'] = 'other/v1'
    elif mutation == 'wrong_evidence':
        q['evidence'] = dict(q['evidence'], mode='live')
    else:
        q = 'options.selection_question/v1'
    refuses(lambda: setup.run(q), 'request_invalid')
    assert setup.calls == []


def test_missing_source_decision_binding_refuses_before_auth(monkeypatch, setup):
    bind(monkeypatch, never_authenticate)
    refuses(lambda: setup.run(source_use_decision=None), 'callback_invalid')
    assert setup.calls == []


def test_success_forwards_exact_bindings_and_emits_bounded_context(monkeypatch, setup):
    bind(monkeypatch, setup.resolver)
    clock = lambda: NOW  # noqa: E731
    ctx = setup.run(clock=clock)
    assert len(setup.calls) == 1
    call = setup.calls[0]
    assert call['ref'] == setup.parsed.ref
    assert call['matrix'] is setup.capture.matrix
    assert call['selection'] == setup.parsed.selection
    kw = call['kw']
    assert kw['access_token'] == TOKEN and kw['vendor'] == 'thetadata'
    assert kw['action'] == 'export'
    assert kw['aliases'] is setup.capture.aliases
    assert kw['security_master'] is setup.capture.security_master
    assert kw['root_evidence'] is setup.capture.root_evidence
    assert kw['source_use_decision'] is setup.decision
    assert kw['clock'] is clock
    assert setup.decision_calls == []  # the wrapper never invokes the callback itself
    receipt = ctx.receipt
    assert set(receipt) == RECEIPT_KEYS
    assert receipt['schema'] == M.RECEIPT_SCHEMA and receipt['authority'] == 'context_only'
    assert (receipt['root'], receipt['session'], receipt['fingerprint']) == \
        (ROOT, SESSION, DIGEST)
    assert receipt['version_ref'] == VERSION_REF and receipt['byte_length'] == BODY_BYTES
    assert receipt['object_id'] == setup.question['evidence']['object_id']
    assert receipt['selection_sha256'] == hashlib.sha256(setup.parsed.selection).hexdigest()
    assert receipt['underlying_id'] == 'SEC:US-ARCX-SYNTH' and receipt['action'] == 'export'
    assert receipt['source_session_available'] is True
    assert receipt['identity_available_at'] == NOW.isoformat()
    assert receipt['source_decided_at'] == NOW.isoformat()
    assert receipt['primary'] == {'expiry': '2026-10-16', 'strike': '500', 'side': 'call',
                                  'hidden': False}
    assert receipt['comparisons'] == []
    assert receipt['view'] == {'lens': 'chain', 'metric': 'volume', 'side': 'all',
                               'expiry': 'all', 'display_mode': '3d'}
    assert receipt['scope'] == {'membership_only': True, 'metric_values_unavailable': True,
                                'quote_not_established': True, 'no_save_grant': True}
    prompt = ctx.prompt_block
    assert prompt.startswith('[UNTRUSTED SOURCE EVIDENCE')
    receipt_json = json.dumps(receipt, sort_keys=True, separators=(',', ':'),
                              ensure_ascii=False)
    assert f'Receipt: {receipt_json}\n' in prompt
    assert '"membership_only":true' in prompt and '"metric_values_unavailable":true' in prompt
    assert len(receipt_json.encode('utf-8')) <= M._MAX_RECEIPT_BYTES
    assert len(prompt.encode('utf-8')) <= M._MAX_PROMPT_BYTES
    with pytest.raises((FrozenInstanceError, AttributeError)):
        ctx.prompt_block = 'changed'


def test_receipt_primitives_stay_bounded(monkeypatch, setup):
    bind(monkeypatch, setup.resolver)
    ctx = setup.run()

    def bounded(value):
        if value is None or type(value) is bool:
            return True
        if type(value) is int:
            return 0 <= value <= 2**53 - 1
        if type(value) is str:
            return len(value.encode('utf-8')) <= M._MAX_SCALAR_BYTES
        if type(value) is list:
            return len(value) <= M._SELECTION_MAX_COMPARISONS and all(map(bounded, value))
        if type(value) is dict:
            return len(value) <= 32 and all(type(key) is str for key in value) \
                and all(bounded(item) for item in value.values())
        return False

    assert bounded(ctx.receipt)
    assert json.loads(json.dumps(ctx.receipt)) == ctx.receipt


def test_receipt_hides_token_subject_epoch_policy_and_matrix_body(monkeypatch, setup):
    bind(monkeypatch, setup.resolver)
    ctx = setup.run()
    blob = json.dumps(ctx.receipt) + ctx.prompt_block
    for secret in (TOKEN, UID, OTHER_UID, ISSUER, 'auth_epoch', 'request_id',
                   'principal', 'policy', 'registry', MATRIX_BODY.decode(), 'body'):
        assert secret not in blob


def test_receipt_carries_hidden_flags_for_filtered_pins(monkeypatch, setup):
    comparisons = (SimpleNamespace(expiry='2026-10-16', strike='505', side='put'),)
    view = SimpleNamespace(lens='chain', metric='volume', side='put', expiry='all',
                           display_mode='3d')

    def resolver(ref, matrix, selection, **kw):
        return authorized(ref, selection, comparisons=comparisons, primary_hidden=True,
                          comparisons_hidden=(False,), view=view)

    bind(monkeypatch, resolver)
    ctx = setup.run()
    assert ctx.receipt['primary']['hidden'] is True
    assert ctx.receipt['comparisons'] == [{'expiry': '2026-10-16', 'strike': '505',
                                           'side': 'put', 'hidden': False}]


@pytest.mark.parametrize('field,value,code', [
    ('principal_id', OTHER_UID, 'principal_mismatch'),
    ('action', 'display', 'action_mismatch'),
    ('selection_sha256', 'b' * 64, 'binding_mismatch'),
    ('root', 'QQQ', 'binding_mismatch'),
    ('sha256', 'c' * 64, 'binding_mismatch'),
    ('byte_length', 99, 'binding_mismatch'),
    ('session', '2026-10-11', 'binding_mismatch'),
    ('session', None, 'binding_mismatch'),
    ('vendor', 'yahoo', 'binding_mismatch'),
    ('owner', 'other.owner', 'binding_mismatch'),
    ('schema', 'other/v1', 'binding_mismatch'),
])
def test_release_refuses_mismatched_request(monkeypatch, setup, field, value, code):
    def resolver(ref, matrix, selection, **kw):
        return authorized(ref, selection, **{field: value})

    bind(monkeypatch, resolver)
    refuses(lambda: setup.run(), code)


def test_release_refuses_mismatched_snapshot(monkeypatch, setup):
    other = F.R.parse_reference('QQQ', VERSION_REF, DIGEST)

    def resolver(ref, matrix, selection, **kw):
        return authorized(ref, selection, snapshot=other)

    bind(monkeypatch, resolver)
    refuses(lambda: setup.run(), 'binding_mismatch')


def test_release_refuses_mismatched_underlying_binding(monkeypatch, setup):
    def resolver(ref, matrix, selection, **kw):
        return authorized(ref, selection, underlying_id='SEC:US-ARCX-OTHER',
                          binding_security_id='SEC:US-ARCX-SYNTH')

    bind(monkeypatch, resolver)
    refuses(lambda: setup.run(), 'binding_mismatch')


@pytest.mark.parametrize('bad', [None, {'status': 'allowed'}, 'allowed', 7])
def test_malformed_authority_return_refuses(monkeypatch, setup, bad):
    bind(monkeypatch, lambda *args, **kwargs: bad)
    refuses(lambda: setup.run(), 'context_invalid')


@pytest.mark.parametrize('code', ['authentication_unavailable', 'entitlement_denied',
                                  'entitlement_unavailable', 'rights_unavailable',
                                  'source_denied', 'source_unavailable',
                                  'selection_unavailable', 'clock_invalid'])
def test_incumbent_refusal_codes_pass_through_sanitized(monkeypatch, setup, code):
    def resolver(ref, matrix, selection, **kw):
        raise M.OptionUseRefused(code)

    bind(monkeypatch, resolver)
    refuses(lambda: setup.run(), code)


def test_unexpected_resolver_failure_is_sanitized(monkeypatch, setup):
    def resolver(ref, matrix, selection, **kw):
        raise RuntimeError('raw upstream transport detail')

    bind(monkeypatch, resolver)
    value = refuses(lambda: setup.run(), 'source_unavailable')
    assert 'raw upstream' not in str(value)


def test_unexpected_context_failure_is_sanitized(monkeypatch, setup):
    def resolver(ref, matrix, selection, **kw):
        value = authorized(ref, selection)
        value.request = SimpleNamespace(principal_id=UID)
        return value

    bind(monkeypatch, resolver)
    value = refuses(lambda: setup.run(), 'context_invalid')
    assert value.args == ('context_invalid',)


def test_each_invocation_resolves_fresh(monkeypatch, setup):
    bind(monkeypatch, setup.resolver)
    first = setup.run()
    second = setup.run()
    assert len(setup.calls) == 2
    assert first is not second and first.receipt is not second.receipt
    assert first.prompt_block == second.prompt_block
    other = change_evidence(setup.question, object_id=object_id(root='QQQ'))
    third = setup.run(other)
    assert len(setup.calls) == 3
    assert third.receipt['root'] == 'QQQ' and third.receipt['root'] != first.receipt['root']


def test_options_question_unavailable_is_stable_value_error():
    assert issubclass(M.OptionsQuestionUnavailable, ValueError)
    value = M.OptionsQuestionUnavailable('code_x')
    assert value.code == 'code_x' and value.args == ('code_x',)


def test_resolved_instants_are_aware_and_normalized(monkeypatch, setup):
    decided = datetime(2026, 10, 12, 18, 2, tzinfo=F.timezone.utc)

    def resolver(ref, matrix, selection, **kw):
        return authorized(ref, selection, available_at=decided, decided_at=decided)

    bind(monkeypatch, resolver)
    ctx = setup.run()
    assert ctx.receipt['identity_available_at'] == '2026-10-12T18:02:00+00:00'
    assert ctx.receipt['source_decided_at'] == '2026-10-12T18:02:00+00:00'


def test_actual_terminal_mint_fixture_is_consumable():
    """Captured from Terminal's real prepareOptionsQuestion, not this module's tag."""
    from pathlib import Path
    fixture = Path(__file__).parent / 'fixtures/options_selection_question/terminal-mint-v1.json'
    q = json.loads(fixture.read_text())
    parsed = M.parse_options_question(q)
    assert parsed.ref.root == 'SPY'
    assert parsed.ref.session == '2026-10-15'
    assert json.loads(parsed.selection)['primary']['strike'] == '600'


def test_unknown_session_refuses_even_when_both_tokens_agree():
    q = change_evidence(question(), object_id=object_id(session='unknown'),
                        version_ref=f'sha256:{DIGEST}:bytes:{BODY_BYTES}:session:unknown')
    refuses(lambda: M.parse_options_question(q), 'session_unavailable')


from tests.test_options_auth import env  # noqa: E402,F401 -- incumbent inert auth/DB fixture
from tests import test_options_auth as A  # noqa: E402
from tests import test_options_use as U  # noqa: E402


def test_native_auth_identity_membership_and_revocation_compose(env):
    """No authority mock: real readers, synthetic bytes and inert Auth/DB edges."""
    inputs = F.inputs.__wrapped__()
    raw = F.encoded(inputs['doc'])
    ref = F.R.reference_for_bytes('SPY', raw)
    q = {
        'schema': 'options.selection_question/v1',
        'evidence': {'owner': 'terminal.options_exposure', 'object_type': 'options_matrix_selection',
                     'mode': 'pinned', 'object_id': 'v1/SPY/2026-10-12/2026-10-16,call,500//volume,all,all,3d',
                     'version_ref': ref.version_ref, 'fingerprint': ref.sha256},
        'selection': canonical(F.selection()),
    }
    captured = M.OptionsQuestionCapture(matrix=F.capture(raw),
        **{k: inputs['kwargs'][k] for k in ('aliases', 'security_master', 'root_evidence')})
    decisions = []
    def source_use(req):
        decisions.append(req)
        return U.allow(req)
    kwargs = dict(access_token=A.token(), expected_user_id=A.UID, captured=captured,
                  vendor='thetadata', source_use_decision=source_use, clock=lambda: NOW)
    context = M.resolve_options_question(q, **kwargs)
    assert context.receipt['primary'] == {'expiry': '2026-10-16', 'strike': '500', 'side': 'call', 'hidden': False}
    assert context.receipt['underlying_id'] == 'SEC:US-ARCX-SYNTH'
    assert context.receipt['scope']['metric_values_unavailable'] is True
    assert context.receipt['identity_available_at'] == NOW.isoformat()
    assert decisions[0].action == 'export'
    assert (env.auth_calls, env.store_calls) == (2, 1)
    assert A.UID not in context.prompt_block and A.token() not in context.prompt_block
    env.row = None
    refuses(lambda: M.resolve_options_question(q, **kwargs), 'entitlement_denied')
    assert (env.auth_calls, env.store_calls) == (4, 2)
    assert len(decisions) == 1  # no source disclosure decision after entitlement withdrawal
