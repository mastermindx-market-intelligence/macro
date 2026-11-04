"""Real native auth/identity/policy with inert Auth and captured synthetic source.

The tiny adapter models the Lab callback signature; a separate integration check
must qualify the actual independently owned Lab source before release.
"""
from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json
from types import SimpleNamespace

import pytest

from app import options_auth as A
from app.options_matrix_http import MatrixHTTPInputs, MatrixHTTPRuntime
from engine.intelligence_workspace import options_matrix_question as Q
from engine.intelligence_workspace import options_source_use as S
from tests import test_options_auth as Auth
from tests.test_options_auth import env
from tests import test_options_matrix_delivery as D
from tests.test_options_matrix_delivery import native
from tests import test_options_selection_composition as F
from tests import test_options_source_use as P

DEST = S.ProcessorDestination('synthetic', 'https://processor.invalid/v1/messages', 'model-1')


@pytest.fixture
def setup(native, tmp_path, env):
    x = native
    source = D.source(x, tmp_path)
    r = json.loads((tmp_path / P.POINTER).read_text())
    r['schema'] = 'options.source_use.question/v2'
    r['actions'] = {'export': dict(r['actions']['display'], channel='/api/brain/chat',
        recipients=['authenticated_customer', 'external_processor'], processor=asdict(DEST))}
    digest = P.write_policy(tmp_path, P.policy_bytes(r))
    policy = Q.QuestionPolicyBinding(digest, r['registry_revision'],
                                    (('redistribution', 'synthetic processor use'),))
    f = x['f']['kwargs']
    captured = MatrixHTTPInputs(x['matrix'], f['aliases'], f['security_master'], f['root_evidence'], source)
    state = SimpleNamespace(now=F.NOW, captured=captured, captures=0, sends=[], env=env)
    def capture(ref):
        state.captures += 1
        assert ref == x['ref']
        return state.captured
    def resolve(reference, *, access_token, expected_user_id, captured, vendor,
                source_use_decision, clock):
        result = A.resolve_authenticated_option_selection(
            x['ref'], captured.matrix, x['selected'], access_token=access_token,
            vendor=vendor, action='export', aliases=captured.aliases,
            security_master=captured.security_master, root_evidence=captured.root_evidence,
            source_use_decision=source_use_decision, clock=clock)
        assert result.request.principal_id == expected_user_id
        return SimpleNamespace(prompt_block='synthetic verified selection '+result.request.selection_sha256,
                               receipt={'authority': 'context_only'})
    adapter = SimpleNamespace(
        parse_options_question=lambda r: SimpleNamespace(ref=x['ref'], selection=x['selected']),
        OptionsQuestionCapture=lambda matrix, aliases, security_master, root_evidence:
            SimpleNamespace(matrix=matrix, aliases=aliases, security_master=security_master, root_evidence=root_evidence),
        resolve_options_question=resolve)
    state.args = dict(reference={}, access_token=Auth.token(), expected_user_id=Auth.UID,
                     runtime=MatrixHTTPRuntime(capture), processor=DEST, channel='/api/brain/chat',
                     policy=policy, clock=lambda: state.now, question_adapter=adapter)
    state.policy_record = r
    state.tmp_path = tmp_path
    return state


def extractor(payload):
    record = json.loads(payload)
    assert set(record) == {'source'} and type(record['source']) is str
    return record['source'].encode()


def send(s, prepared, *, body=None, **changes):
    payload = body if body is not None else json.dumps({'source': prepared.prompt_block}).encode()
    kw = dict(processor=DEST, channel='/api/brain/chat', extract_source_block=extractor)
    kw.update(changes)
    verified = prepared.authorize_dispatch(payload, **kw)
    s.sends.append(verified)  # inert existing transport; reached only after final check
    return verified


def test_real_composition_and_single_attempt(setup):
    s = setup; p = Q.prepare_matrix_question(**s.args)
    assert s.env.auth_calls >= 3 and s.captures == 1 and not s.sends
    v = send(s, p)
    assert v.payload_sha256 == hashlib.sha256(v.payload).hexdigest()
    assert v.processor == DEST and s.env.store_calls >= 2
    with pytest.raises(S.SourceUseRefused): send(s, p)
    assert len(s.sends) == 1


@pytest.mark.parametrize('failure', ['destination', 'model', 'channel', 'payload', 'late',
                                    'revoked', 'session', 'policy', 'extractor'])
def test_pre_disclosure_refusals(setup, failure):
    s = setup; p = Q.prepare_matrix_question(**s.args); kw = {}
    if failure == 'destination': kw['processor'] = replace(DEST, endpoint='https://other.invalid')
    if failure == 'model': kw['processor'] = replace(DEST, model='fallback')
    if failure == 'channel': kw['channel'] = '/api/brain/stream'
    if failure == 'payload': kw['body'] = b'{"source":"different"}'
    if failure == 'late': s.now += timedelta(seconds=10)
    if failure == 'revoked': s.env.row = dict(tier='free', features=[])
    if failure == 'session': s.env.user['id'] = Auth.SID
    if failure == 'policy':
        s.policy_record['state'] = 'revoked'
        P.write_policy(s.tmp_path, P.policy_bytes(s.policy_record))
    if failure == 'extractor': kw['extract_source_block'] = lambda b: None
    with pytest.raises((S.SourceUseRefused, A.OptionUseRefused)):
        send(s, p, **kw)
    assert not s.sends


def test_late_auth_result_refuses(setup, monkeypatch):
    s = setup; p = Q.prepare_matrix_question(**s.args)
    original = A.fresh_options_entitlement
    def delayed(*a, **kw):
        result = original(*a, **kw)
        s.now += timedelta(seconds=11)
        return result
    monkeypatch.setattr(A, 'fresh_options_entitlement', delayed)
    with pytest.raises(S.SourceUseRefused): send(s, p)
    assert not s.sends


def test_wrong_user_before_capture(setup):
    s = setup; s.args['expected_user_id'] = 'someone-else'
    with pytest.raises(S.SourceUseRefused): Q.prepare_matrix_question(**s.args)
    assert s.captures == 0


@pytest.mark.parametrize('failure', ['matrix', 'missing', 'binding', 'display_policy'])
def test_capture_or_display_grant_cannot_authorize_question(setup, failure):
    s = setup
    if failure == 'matrix':
        s.captured = replace(s.captured, matrix=replace(s.captured.matrix, body=s.captured.matrix.body+b' '))
    if failure == 'missing': s.captured = None
    if failure == 'binding': s.captured = replace(s.captured, source=replace(s.captured.source, binding=None))
    if failure == 'display_policy':
        r = s.policy_record
        r.pop('schema'); scope = r['actions'].pop('export'); scope.pop('processor')
        scope.update(channel='/api/flow?f=matrix:SPY', recipients=['authenticated_customer'])
        r['actions']['display'] = scope
        digest = P.write_policy(s.tmp_path, P.policy_bytes(r))
        s.args['policy'] = replace(s.args['policy'], evidence_sha256=digest)
    with pytest.raises(Exception): Q.prepare_matrix_question(**s.args)
    assert not s.sends
