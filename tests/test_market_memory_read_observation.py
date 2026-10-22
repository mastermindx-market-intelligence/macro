"""Bounded read diagnostics preserve the pre-existing route contract."""
import ast
import hashlib
import inspect
import json
import logging
import subprocess
import sys
from contextlib import ExitStack
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, get_native_id

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


def test_stage_fields_are_bounded_and_require_an_active_catalog_read(caplog):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    with api._observe_admitted_read('retained_catalog') as seq:
        for stage, wall, cpu in [('private-user/path', 1, 1), ('projections', float('nan'), 1),
                                 ('projections', 1, -1), ('projections', True, 1)]:
            api._read_observation_stage(seq, stage, wall, cpu)
        api._read_observation_stage(seq, 'projections', 12.5, 3.25)
    api._read_observation_stage(seq, 'projections', 1, 1)
    stages = [r.args[1] for r in caplog.records if '.stage ' in r.getMessage()]
    assert stages == [{'tag': 'retained_catalog', 'seq': seq, 'stage': 'projections',
                       'native_thread_id': get_native_id(),
                       'elapsed_ms': 12.5, 'thread_cpu_ms': 3.25}]
    assert 'private-user/path' not in caplog.text


def test_concurrent_reads_keep_their_own_thread_in_every_event(caplog):
    caplog.set_level(logging.INFO, logger=api._read_observation_log.name)
    barrier = Barrier(2)

    def run(_):
        with api._observe_admitted_read('retained_catalog') as seq:
            barrier.wait(timeout=10)
            api._read_observation_stage(seq, 'projections', 12.5, 3.25)
            api._read_observation_busy('retained_saved')
            barrier.wait(timeout=10)
            return seq, get_native_id()

    with ThreadPoolExecutor(max_workers=2) as pool:
        observed = dict(pool.map(run, range(2)))
    assert len(set(observed.values())) == 2
    events = [(record.args[0], record.args[1]) for record in caplog.records]
    for seq, native_thread_id in observed.items():
        own = [(event, fields) for event, fields in events if fields.get('seq') == seq]
        assert [event for event, _ in own] == ['start', 'stage', 'finish']
        assert all(fields['native_thread_id'] == native_thread_id for _, fields in own)
    for event, fields in events:
        if event == 'busy':
            assert {holder['seq']: holder['native_thread_id']
                    for holder in fields['holders']} == observed


def test_thread_lookup_failure_does_not_change_the_read(monkeypatch):
    def fail():
        raise RuntimeError('thread lookup failed')

    monkeypatch.setattr(api.threading, 'get_native_id', fail)
    with api._observe_admitted_read('retained_catalog') as seq:
        assert seq is None
        api._read_observation_stage(seq, 'projections', 12.5, 3.25)
        assert not api._read_observation_active


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
with api._observe_admitted_read('retained_catalog') as seq:
    api._read_observation_stage(seq, 'projections', 12.5, 3.25)
    api._read_observation_busy('retained_saved')
'''
    result = subprocess.run([sys.executable, '-c', script], capture_output=True,
                            text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr
    assert all('market_memory.read.' + event in result.stderr
               for event in ('start', 'stage', 'busy', 'finish'))


# Frozen from pre-implementation bbfd64b2ba58b5c44ad8ba38a05bcd319f13708c.
# Original source bytes:469222d2112d524ceea2d29124434d74a2e1b5ec7bb6bf4a0f84e8f3b31fb00a.
# Re-serialized structurally after CI exposed ast.dump version drift.
def _ast_digest(node):
    """Stable structural hash; ast.dump formatting changed in Python 3.13.

    Omit only empty list fields (including version-added type_params). Keep
    semantic None, False and zero distinct, along with node/field identities
    and list ordering. No source locations or printer formatting enter it.
    """
    def canonical(value):
        if isinstance(value, ast.AST):
            return {"node": type(value).__name__, "fields": {
                name: canonical(field) for name, field in ast.iter_fields(value)
                if not (isinstance(field, list) and not field)
            }}
        if isinstance(value, list):
            return [canonical(item) for item in value]
        return {"type": type(value).__name__, "value": value}
    body = json.dumps(canonical(node), sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(body.encode()).hexdigest()


ORIGINAL_AST = {
    'operational_playback_catalog': '8184ee9f2de3d5c57495bd78dd8424ef26f5c2171e53ac718f82c8332fbb018d',
    'retained_macro_for_user': '26f2f39c90ce7d53998e88a4c41c2b2b4cace30acdb5d6df81e67e4f30176302',
    'retained_catalog_for_user': '553c88cc52a3e6c725de5f42a1c3294040b8c1463b694904599143d9ed0e1382',
    'retained_saved_for_user': 'ee67f3f9dd582c9aaf0b135fc6e1f02ef47e16bb6c4343e0750e248482e18fb1',
}


class StripObserver(ast.NodeTransformer):
    def visit_With(self, node):
        self.generic_visit(node)
        if len(node.items) == 1 and isinstance(node.items[0].context_expr, ast.Call):
            call = node.items[0].context_expr
            if isinstance(call.func, ast.Name) and call.func.id in {
                    '_observe_admitted_read', '_observe_catalog_stage'}:
                return node.body
        return node

    def visit_Call(self, node):
        self.generic_visit(node)
        if (isinstance(node.func, ast.Attribute) and node.func.attr == 'read_catalog'
                and isinstance(node.func.value, ast.Name) and node.func.value.id == 'catalog'):
            node.keywords = [item for item in node.keywords if item.arg != 'stage_observer']
        return node

    def visit_FunctionDef(self, node):
        self.generic_visit(node)
        if node.name == 'read_catalog':
            for index, arg in reversed(list(enumerate(node.args.kwonlyargs))):
                if arg.arg == 'stage_observer':
                    del node.args.kwonlyargs[index]
                    del node.args.kw_defaults[index]
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
    assert _ast_digest(actual) == digest


def test_catalog_preserves_the_entire_pre_timing_read_contract():
    from engine.neuralweb import market_memory_retained_catalog as catalog
    node = ast.parse(inspect.getsource(catalog.read_catalog)).body[0]
    # Exact fa559344 pre-timing body, with only timing scopes/argument removed.
    assert _ast_digest(StripObserver().visit(node)) == (
        'c9e0315bcd0fbbfbecd7dcfabaff1e98de4feab27b2632cc061435859509eede')


@pytest.mark.parametrize('left,right', [
    ('allowed = True', 'allowed = False'),
    ('limit = 0', 'limit = False'),
    ('payload = None', 'payload = 0'),
    ('value > 10', 'value > 11'),
])
def test_route_oracle_keeps_semantic_changes_visible(left, right):
    assert _ast_digest(ast.parse(left)) != _ast_digest(ast.parse(right))
