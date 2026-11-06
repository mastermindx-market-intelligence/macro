"""Fail-closed Options source-use consumer; callbacks are test fixtures.

Real identity/membership readers, synthetic captured data; no grant or network.
"""
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import hashlib

import pytest
from tests import test_options_selection_composition as F

from engine.intelligence_workspace import options_use as M

NOW = F.NOW
KEYS = ('request_id', 'principal_id', 'principal_issuer', 'auth_epoch', 'owner',
        'schema', 'root', 'sha256', 'byte_length', 'session', 'vendor',
        'underlying_id', 'selection_sha256', 'action')


def allow(req, **changes):
    data = dict(status='allowed', binding=req.as_dict(), source_family='fixture.theta',
                policy_id='fixture.options-use', policy_revision='fixture.r1',
                registry_revision='fixture.registry1', decided_at=NOW.isoformat())
    data.update(changes)
    return data


@pytest.fixture
def setup():
    f = F.inputs.__wrapped__()
    raw = F.encoded(f['doc'])
    kw = dict(f['kwargs'])
    kw.pop('decision_at')
    calls = []
    def entitlement(req):
        calls.append(('entitlement', req))
        return True
    def rights(req):
        calls.append(('rights', req))
        return allow(req)
    kw.update(principal_id='fixture-alice', principal_issuer='https://fixture.invalid',
              auth_epoch='fixture.epoch1', action='display', fresh_entitlement=entitlement,
              source_use_decision=rights, clock=lambda: NOW)
    return dict(ref=F.R.reference_for_bytes('SPY', raw), matrix=F.capture(raw),
                selected=F.encoded(F.selection()), kw=kw, calls=calls)


def run(s, **changes):
    return M.resolve_authorized_option_selection(s['ref'], s['matrix'], s['selected'],
                                                **dict(s['kw'], **changes))


def refuses(s, **changes):
    with pytest.raises(M.OptionUseRefused) as exc:
        run(s, **changes)
    assert type(exc.value.code) is str and exc.value.code
    return exc.value


@pytest.mark.parametrize('action', ['display', 'export'])
def test_success_real_readers_exact_binding_and_immutable_return(setup, action):
    s = setup
    r = run(s, action=action)
    q = r.request.as_dict()
    assert set(q) == set(KEYS)
    assert q['principal_id'] == 'fixture-alice' and q['auth_epoch'] == 'fixture.epoch1'
    assert q['owner'] == 'options_structure.matrix' and q['schema'] == 'options_structure.matrix/v1'
    assert q['root'] == 'SPY' and q['session'] == '2026-10-12'
    assert q['sha256'] == s['ref'].sha256 and q['byte_length'] == len(s['matrix'].body)
    assert q['selection_sha256'] == hashlib.sha256(s['selected']).hexdigest()
    assert q['underlying_id'] == 'SEC:US-ARCX-SYNTH' and q['action'] == action
    assert r.selection.primary.strike == '500'
    assert r.source_family == 'fixture.theta' and r.decided_at == NOW
    assert [x[0] for x in s['calls']] == ['entitlement', 'rights']
    assert s['calls'][0][1] is s['calls'][1][1] is r.request
    with pytest.raises((FrozenInstanceError, AttributeError)):
        r.request.principal_id = 'bob'
    with pytest.raises((FrozenInstanceError, AttributeError)):
        r.policy_revision = 'changed'
    q['root'] = 'QQQ'
    assert r.request.root == 'SPY'
    assert not hasattr(r, 'save_allowed')


@pytest.mark.parametrize('field', ['principal_id', 'principal_issuer', 'auth_epoch', 'vendor'])
@pytest.mark.parametrize('bad', ['', None, 7, ' leading', 'trailing ', 'a\nb', 'x\x85y', 'é' * 129])
def test_bad_context_before_callbacks(setup, field, bad):
    refuses(setup, **{field: bad})
    assert setup['calls'] == []


@pytest.mark.parametrize('bad', ['save', 'Display', 'export ', None, 1, True])
def test_invalid_action(setup, bad):
    refuses(setup, action=bad)
    assert setup['calls'] == []


@pytest.mark.parametrize('field', ['fresh_entitlement', 'source_use_decision'])
@pytest.mark.parametrize('bad', [None, True, {}])
def test_unconfigured_backend_refuses(setup, field, bad):
    refuses(setup, **{field: bad})
    assert setup['calls'] == []


@pytest.mark.parametrize('defect', ['digest', 'selection_bytes', 'coordinate', 'session', 'vendor'])
def test_real_identity_or_selection_failure_never_calls_authority(setup, defect):
    s = setup
    if defect == 'digest': s['matrix'] = replace(s['matrix'], sha256='0' * 64)
    elif defect == 'selection_bytes': s['selected'] = bytearray(s['selected'])
    elif defect == 'coordinate': s['selected'] = s['selected'].replace(b'500', b'501')
    elif defect == 'session': s['ref'] = replace(s['ref'], session='2026-10-11')
    else: s['kw']['vendor'] = 'yahoo'
    refuses(s)
    assert s['calls'] == []


@pytest.mark.parametrize('value', [False, None, 1, 'true', {}, [True]])
def test_entitlement_strict_bool_and_rights_not_called(setup, value):
    refuses(setup, fresh_entitlement=lambda req: value)
    assert setup['calls'] == []


@pytest.mark.parametrize('stage', ['fresh_entitlement', 'source_use_decision'])
def test_callback_failure_no_secret_exposure(setup, stage):
    def fail(req): raise RuntimeError('PRIVATE_CALLBACK_SECRET')
    exc = refuses(setup, **{stage: fail})
    assert 'PRIVATE_CALLBACK_SECRET' not in str(exc)


@pytest.mark.parametrize('field', KEYS)
@pytest.mark.parametrize('kind', ['missing', 'different'])
def test_every_binding_field_exact(setup, field, kind):
    def mismatch(req):
        d = allow(req)
        if kind == 'missing': del d['binding'][field]
        else: d['binding'][field] = req.byte_length + 1 if field == 'byte_length' else 'foreign'
        return d
    refuses(setup, source_use_decision=mismatch)


@pytest.mark.parametrize('defect', ['bool_count', 'extra_binding', 'extra_response', 'missing_status',
                                  'status_bool', 'denied', 'unavailable', 'list', 'none'])
def test_response_closed_schema(setup, defect):
    def response(req):
        d = allow(req)
        if defect == 'bool_count': d['binding']['byte_length'] = True
        elif defect == 'extra_binding': d['binding']['scope'] = '*'
        elif defect == 'extra_response': d['allowed'] = True
        elif defect == 'missing_status': del d['status']
        elif defect == 'status_bool': d['status'] = True
        elif defect in ('denied', 'unavailable'): d['status'] = defect
        elif defect == 'list': return [d]
        else: return None
        return d
    refuses(setup, source_use_decision=response)


@pytest.mark.parametrize('field', ['source_family', 'policy_id', 'policy_revision', 'registry_revision'])
@pytest.mark.parametrize('bad', [None, '', ' padded ', 'x\ny', 'é' * 129])
def test_policy_provenance_required(setup, field, bad):
    refuses(setup, source_use_decision=lambda req: allow(req, **{field: bad}))


@pytest.mark.parametrize('bad', ['2026-10-12', '2026-10-12T17:02:00', '2026-10-12 17:02:00Z',
                              '2026-10-12T17:01:59Z', '2026-10-12T17:02:01Z',
                              '2026-10-12T17:02:00+0000', None, True])
def test_decision_clock_format_and_live_interval(setup, bad):
    refuses(setup, source_use_decision=lambda req: allow(req, decided_at=bad))


@pytest.mark.parametrize('bad_sequence', [
    [NOW, NOW-timedelta(seconds=1)],
    [NOW, NOW, NOW-timedelta(seconds=1)],
    [NOW.replace(tzinfo=None)],
    [NOW, '2026-10-12T17:02:00Z'],
])
def test_clock_never_regresses_or_coerces(setup, bad_sequence):
    it = iter(bad_sequence)
    refuses(setup, clock=lambda: next(it))


def test_clock_error_fails_closed(setup):
    def fail(): raise RuntimeError('PRIVATE_CLOCK_SECRET')
    assert 'PRIVATE_CLOCK_SECRET' not in str(refuses(setup, clock=fail))


def test_decision_must_follow_entitlement_completion(setup):
    it = iter([NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=2)])
    # Its otherwise well-bound decision happened during entitlement, before this rights call.
    refuses(setup, clock=lambda: next(it))


def test_future_submicrosecond_timestamp_is_not_truncated_into_allow(setup):
    refuses(setup, source_use_decision=lambda req: allow(req, decided_at='2026-10-12T17:02:00.0000009Z'))


def test_nonzero_call_interval_with_offset_timestamp(setup):
    it = iter([NOW, NOW + timedelta(seconds=1), NOW + timedelta(seconds=3)])
    d = (NOW + timedelta(seconds=2)).astimezone(timezone(timedelta(hours=-7)))
    r = run(setup, clock=lambda: next(it), source_use_decision=lambda req: allow(req, decided_at=d.isoformat()))
    assert r.decided_at == NOW + timedelta(seconds=2)


def test_nonce_rejects_previous_decision_even_at_same_time(setup):
    saved = []
    def first(req):
        saved.append(allow(req))
        return saved[-1]
    a = run(setup, source_use_decision=first)
    refuses(setup, source_use_decision=lambda req: saved[0])
    b = run(setup)
    assert a.request.request_id != b.request.request_id


def test_display_decision_cannot_authorize_export(setup):
    def wrong(req):
        d = allow(req)
        d['binding']['action'] = 'display'
        return d
    refuses(setup, action='export', source_use_decision=wrong)


def test_account_and_epoch_changes_do_not_reuse_prior_allow(setup):
    run(setup)
    r = run(setup, principal_id='fixture-bob', auth_epoch='fixture.epoch2')
    assert r.request.principal_id == 'fixture-bob' and r.request.auth_epoch == 'fixture.epoch2'
    assert [k for k, _ in setup['calls']] == ['entitlement', 'rights'] * 2


def test_callback_mutation_of_returned_dict_cannot_change_authority_request(setup):
    def callback(req):
        attempt = req.as_dict()
        attempt['principal_id'] = 'mallory'
        return allow(req)
    assert run(setup, source_use_decision=callback).request.principal_id == 'fixture-alice'


def test_later_response_mutation_cannot_change_result(setup):
    emitted = []
    def callback(req):
        emitted.append(allow(req))
        return emitted[-1]
    result = run(setup, source_use_decision=callback)
    emitted[0]['source_family'] = 'foreign'
    emitted[0]['binding']['root'] = 'QQQ'
    assert result.source_family == 'fixture.theta' and result.request.root == 'SPY'



def test_default_clock_works_without_injection(setup, monkeypatch):
    class LiveClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 12, 17, 2, tzinfo=timezone.utc)
    monkeypatch.setattr(M, 'datetime', LiveClock)
    result = run(setup, clock=None)
    assert result.request.underlying_id == 'SEC:US-ARCX-SYNTH'


@pytest.mark.parametrize('field', ['principal_id', 'principal_issuer', 'auth_epoch', 'vendor'])
def test_unpaired_surrogate_context_is_structured_refusal(setup, field):
    refuses(setup, **{field: 'x\ud800y'})
    assert setup['calls'] == []


@pytest.mark.parametrize('field', ['source_family', 'policy_id', 'policy_revision', 'registry_revision'])
def test_unpaired_surrogate_metadata_is_structured_refusal(setup, field):
    refuses(setup, source_use_decision=lambda req: allow(req, **{field: 'x\ud800y'}))


@pytest.mark.parametrize('stamp', ['0001-01-01T00:00:00+00:01', '9999-12-31T23:59:59-00:01',
                                  '2026-10-12T16:02:00-00:60'])
def test_overflow_and_non_rfc3339_zone_are_structured_refusals(setup, stamp):
    refuses(setup, source_use_decision=lambda req: allow(req, decided_at=stamp))
