"""Bounded read diagnostics preserve the pre-existing route contract."""
import ast
import hashlib
import inspect
import logging
import subprocess
import sys
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app import market_memory as api


@pytest.fixture(autouse=True)
def clean_registry():
    assert not api._read_observation_active
    yield
    assert not api._read_observation_active


@pytest.mark.parametrize('failure', [None, RuntimeError, KeyboardInterrupt])
def test_body_result_or_exception_survives_and_registry_cleans(caplog, failure):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    def run():
        with api._observe_admitted_read('retained_saved'):
            assert len(api._read_observation_active) == 1
            if failure:
                raise failure('private body detail')
            return {'unchanged': True}
    if failure:
        with pytest.raises(failure, match='private body detail'):
            run()
    else:
        assert run() == {'unchanged': True}
    assert 'market_memory.read.start' in caplog.text
    assert 'market_memory.read.finish' in caplog.text
    assert 'private body detail' not in caplog.text
    assert "'success': " + str(failure is None) in caplog.text


def test_busy_names_only_the_two_actual_holders(caplog):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    with ExitStack() as stack:
        stack.enter_context(api._observe_admitted_read('retained_macro'))
        stack.enter_context(api._observe_admitted_read('retained_saved'))
        stack.enter_context(api._observe_admitted_read('retained_catalog'))
        assert len(api._read_observation_active) == 2
        api._read_observation_busy('legacy_playback_catalog')
    busy = [r.getMessage() for r in caplog.records if '.busy ' in r.getMessage()]
    assert len(busy) == 1
    assert all(t in busy[0] for t in ('retained_macro', 'retained_saved', 'legacy_playback_catalog'))
    assert 'retained_catalog' not in busy[0]


def test_concurrent_observers_stay_bounded_and_do_not_consume_permits():
    barrier = Barrier(8)
    def run(_):
        with api._observe_admitted_read('retained_catalog'):
            barrier.wait(timeout=10)
            assert len(api._read_observation_active) <= 2
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(run, range(8)))
    assert api._playback_slots.acquire(False)
    assert api._playback_slots.acquire(False)
    try:
        assert not api._playback_slots.acquire(False)
    finally:
        api._playback_slots.release()
        api._playback_slots.release()


def test_logging_failure_cannot_change_result_or_exception(monkeypatch):
    lock_available = []
    def fail(*args, **kwargs):
        acquired = api._read_observation_lock.acquire(False)
        lock_available.append(acquired)
        if acquired:
            api._read_observation_lock.release()
        raise RuntimeError('logger failure')
    monkeypatch.setattr(api._read_observation_log, 'info', fail)
    with api._observe_admitted_read('retained_macro'):
        api._read_observation_busy('retained_saved')
    with pytest.raises(ValueError, match='original'):
        with api._observe_admitted_read('retained_macro'):
            raise ValueError('original')
    assert len(lock_available) == 5 and all(lock_available)


def test_invalid_tag_is_neither_recorded_nor_logged(caplog):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    with api._observe_admitted_read('Bearer private-user-query'):
        api._read_observation_busy('https://private.invalid/token')
        assert not api._read_observation_active
    assert not caplog.records


def test_info_events_reach_the_default_server_handler():
    script = '''
import logging.config
# Uvicorn default INFO parent with propagation to its stderr handler.
logging.config.dictConfig({
    'version': 1, 'disable_existing_loggers': False,
    'handlers': {'default': {'class': 'logging.StreamHandler', 'stream': 'ext://sys.stderr'}},
    'loggers': {'uvicorn': {'handlers': ['default'], 'level': 'INFO', 'propagate': False},
                'uvicorn.error': {'level': 'INFO'}},
})
from app import market_memory as api
with api._observe_admitted_read('retained_catalog'):
    api._read_observation_busy('retained_saved')
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True,
                            text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert all('market_memory.read.' + event in result.stderr
               for event in ('start', 'busy', 'finish'))


# Frozen by the assigning parent before worker return or implementation.
ORIGINAL_AST = {
    'operational_playback_catalog': 'a092fa93c347826a79320e2476303fa5760c91fea291e5d4a87ab7abf8cfa592',
    'retained_macro_for_user': 'b2437de891eaf68fe3f5c5e21695221657f4e8ee5fb1de03520e196cdf6fbe1c',
    'retained_catalog_for_user': '9fd543ef2f8491566bed9f7bc6e040597615d4f84434974e37087e606e32d755',
    'retained_saved_for_user': '58ef4907d193a5df84ff2046c6c10bb53215b8bbb248612ad6cfd7f25a6677fe',
}


class StripObserver(ast.NodeTransformer):
    def visit_With(self, node):
        self.generic_visit(node)
        if len(node.items) == 1 and isinstance(node.items[0].context_expr, ast.Call):
            call = node.items[0].context_expr
            if isinstance(call.func, ast.Name) and call.func.id == '_observe_admitted_read':
                return node.body
        return node

    def visit_Expr(self, node):
        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
            if node.value.func.id == '_read_observation_busy':
                return None
        return node


@pytest.mark.parametrize('name,digest', ORIGINAL_AST.items())
def test_routes_preserve_exact_original_authorization_limits_and_payloads(name, digest):
    node = ast.parse(inspect.getsource(getattr(api, name))).body[0]
    actual = StripObserver().visit(node)
    assert hashlib.sha256(ast.dump(actual, include_attributes=False).encode()).hexdigest() == digest
