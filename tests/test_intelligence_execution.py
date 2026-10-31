"""A28 safety boundary: real local subprocesses; no estate/production loads."""
import json
import os
from pathlib import Path
import signal
import sys
import time

import pytest
from admin import intelligence_execution as execution
from engine import qledger_store


def collect(script, *, seconds=2, limit=1024):
    return execution._collect([sys.executable, '-c', script], cwd=Path.cwd(), seconds=seconds, limit=limit)


@pytest.mark.skipif(sys.platform != "linux", reason="Linux execution boundary; macOS is refused")
def test_complete_child_result():
    assert collect('print("complete")') == b'complete\n'


@pytest.mark.skipif(sys.platform != "linux", reason="Linux execution boundary; macOS is refused")
@pytest.mark.parametrize('script,exception', [
    ('import time; time.sleep(10)', TimeoutError),
    ('import sys; sys.stdout.write("x" * 1025)', ValueError),
    ('import sys; print("partial"); sys.exit(2)', ValueError),
    ('import os,time; os.close(1); time.sleep(10)', TimeoutError),
])
def test_child_failures_are_bounded(script, exception):
    started = time.monotonic()
    with pytest.raises(exception):
        collect(script, seconds=.3)
    assert time.monotonic() - started < 3


@pytest.mark.skipif(sys.platform != "linux", reason="Linux execution boundary; macOS is refused")
def test_descendant_cleanup_even_after_leader_exits(tmp_path):
    marker = tmp_path / 'survived'
    script = ('import os,sys,subprocess\n'
              'subprocess.Popen([sys.executable,"-c",'
              + repr('import time; from pathlib import Path; time.sleep(.7); Path('+repr(str(marker))+').touch()')
              + '], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\nprint("done")')
    assert collect(script) == b'done\n'
    time.sleep(.9)
    assert not marker.exists()


def test_parent_binding_refused_before_child(monkeypatch):
    token = qledger_store._SYNTHETIC_BINDINGS.set(((Path('/synthetic'), object()),))
    monkeypatch.setattr(execution, '_collect', lambda *a, **k: pytest.fail('child launched'))
    try:
        assert execution.response('panel')['error_code'] == 'evidence_binding_not_transferable'
    finally:
        qledger_store._SYNTHETIC_BINDINGS.reset(token)


def test_existing_read_scope_is_not_lost(monkeypatch):
    token = qledger_store._READ_SCOPES.set(((Path('/synthetic'), object(), object()),))
    try:
        assert execution.response('panel')['error_code'] == 'evidence_binding_not_transferable'
    finally:
        qledger_store._READ_SCOPES.reset(token)


def test_unsupported_enforcement_never_derives(monkeypatch):
    monkeypatch.setattr(execution.sys, 'platform', 'darwin')
    original_collect = execution._collect
    monkeypatch.setattr(execution, '_collect', lambda *a, **k: pytest.fail('child launched'))
    assert execution.response('panel')['error_code'] == 'evidence_limits_unavailable'
    with pytest.raises(RuntimeError):
        execution._establish_limits()
    with pytest.raises(RuntimeError):
        original_collect([sys.executable, "-c", "raise AssertionError()"], cwd=Path.cwd(), seconds=1, limit=1)


def test_concurrent_derivation_refuses_without_child(monkeypatch):
    monkeypatch.setattr(execution.sys, 'platform', 'linux')
    assert execution._SLOT.acquire(blocking=False)
    try:
        assert execution.response('panel')['error_code'] == 'evidence_derivation_busy'
    finally:
        execution._SLOT.release()


@pytest.mark.parametrize('raw', [b'{', b'{"complete":true}', b'{"complete":false,"result":{}}', b'[]'])
def test_partial_or_invalid_frames_never_succeed(monkeypatch, raw):
    monkeypatch.setattr(execution.sys, 'platform', 'linux')
    monkeypatch.setattr(execution, '_collect', lambda *a, **k: raw)
    assert execution.response('panel')['error_code'] == 'evidence_execution_unavailable'


def test_complete_frame_and_owned_arguments(monkeypatch, tmp_path):
    monkeypatch.setattr(execution.sys, 'platform', 'linux')
    seen = []
    def run(command, **kw):
        seen.append((command, kw))
        return b'{"complete":true,"result":{"ok":true,"generation":"immutable-fixture"}}'
    monkeypatch.setattr(execution, '_collect', run)
    assert execution.response('detail', engine_id='engine::a', root=tmp_path)['generation'] == 'immutable-fixture'
    assert seen[0][0][-4:] == ['detail', str(tmp_path), 'engine::a', '0']
    assert seen[0][1]['seconds'] == 45 and seen[0][1]['limit'] == 16 * 1024 * 1024


def test_failed_limit_precedes_import_and_source_read(monkeypatch):
    monkeypatch.setattr(execution, '_establish_limits', lambda: (_ for _ in ()).throw(ValueError('limit failed')))
    assert execution._child() == 4


def test_cache_retention_is_aggregate_and_preserves_other_panels(monkeypatch):
    from admin import server
    monkeypatch.setattr(server, '_EVIDENCE_CACHE_BYTES', 10)
    server._clear_response_cache()
    generation = server._API_RESPONSE_CACHE_GENERATION
    try:
        server._store_api_body('fixture:/api/other', b'unchanged-other', generation)
        server._store_api_body('fixture:/api/intelligence_os/engine?id=1', b'123456', generation)
        server._store_api_body('fixture:/api/intelligence_os/engine?id=2', b'abcdef', generation)
        assert server._cached_api_body('fixture:/api/intelligence_os/engine?id=1') is None
        assert server._cached_api_body('fixture:/api/intelligence_os/engine?id=2') == b'abcdef'
        assert server._cached_api_body('fixture:/api/other') == b'unchanged-other'
        server._store_api_body('fixture:/api/intelligence_os', b'x' * 11, generation)
        assert server._cached_api_body('fixture:/api/intelligence_os') is None
    finally:
        server._clear_response_cache()


def test_limit_installation_is_confirmed_and_cannot_raise_existing_hard_limit(monkeypatch):
    import resource
    monkeypatch.setattr(execution.sys, 'platform', 'linux')
    state = {resource.RLIMIT_AS: (512 * 1024 * 1024, 512 * 1024 * 1024)}
    monkeypatch.setattr(resource, 'getrlimit', lambda kind: state[kind])
    monkeypatch.setattr(resource, 'setrlimit', lambda kind, value: state.__setitem__(kind, value))
    execution._establish_limits()
    assert state[resource.RLIMIT_AS] == (512 * 1024 * 1024,) * 2
    assert state[resource.RLIMIT_CORE] == (0, 0)


def test_unconfirmed_limit_is_refused(monkeypatch):
    import resource
    monkeypatch.setattr(execution.sys, 'platform', 'linux')
    monkeypatch.setattr(resource, 'getrlimit', lambda kind: (resource.RLIM_INFINITY,) * 2)
    monkeypatch.setattr(resource, 'setrlimit', lambda *args: None)
    with pytest.raises(RuntimeError, match='unconfirmed'):
        execution._establish_limits()


def test_deadline_result_is_typed_and_slot_released(monkeypatch):
    monkeypatch.setattr(execution.sys, 'platform', 'linux')
    monkeypatch.setattr(execution, '_collect', lambda *a, **k: (_ for _ in ()).throw(TimeoutError()))
    assert execution.response('panel')['error_code'] == 'evidence_deadline_exceeded'
    assert execution._SLOT.acquire(blocking=False)
    execution._SLOT.release()


@pytest.mark.skipif(sys.platform != 'linux', reason='Requires real Linux RLIMIT_AS enforcement')
def test_actual_linux_address_space_limit_prevents_large_allocation():
    script = ('from admin.intelligence_execution import _establish_limits; '
              '_establish_limits(); import resource; '
              'assert resource.getrlimit(resource.RLIMIT_AS)[0] <= 1024**3; '
              'bytearray(2 * 1024**3)')
    with pytest.raises(ValueError, match='worker failed'):
        collect(script, seconds=3)


def test_cleanup_unknown_latches_without_replacement(monkeypatch):
    import threading
    monkeypatch.setattr(execution.sys, 'platform', 'linux')
    monkeypatch.setattr(execution, '_CLEANUP_UNCONFIRMED', threading.Event())
    calls = []
    def refused(*a, **k):
        calls.append(1)
        raise execution.CleanupUnconfirmed()
    monkeypatch.setattr(execution, '_collect', refused)
    assert execution.response('panel')['error_code'] == 'evidence_cleanup_unconfirmed'
    assert execution.response('detail', engine_id='fixture')['error_code'] == 'evidence_cleanup_unconfirmed'
    assert len(calls) == 1
