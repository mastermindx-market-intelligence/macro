#!/usr/bin/env python3
"""Preparation artifact: root must review and separately authorize host execution.

Run with /opt/macro-api/.venv/bin/python -I -B. Reads pinned /opt/macro source;
all synthetic kernel writes are confined to one private TemporaryDirectory.
The Python audit guard is an effect fence, not an OS sandbox or authentication.
Actual accepted source bytes are compiled, never a copied owner implementation.
The close_pass package initializer is deliberately NOT executed: this is bounded
installed function conformance, not normal package/application/API conformance.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import copy
import dataclasses
import decimal
import fcntl
import hashlib
import http.client
import importlib.util
import io
import json
import os
import pathlib
import re
import stat
import subprocess
import tempfile
import time
import types
import urllib.error
import urllib.parse
import urllib.request
import uuid
from unittest.mock import patch
from zoneinfo import ZoneInfo


ROOT = pathlib.Path('/opt/macro')
SOURCE_HEAD = 'd657ab26781e87a19d9c8705d5ac293c816acbb5'
KNOWN_MERGED_TREE = '4221f0f1eafc1805c9e284df6030a15b80f2365b'
REGISTRY = 'config/dataset_registry.yml'
# Path: (Git blob, SHA-256). Binds exact source bytes, not just import names.
BINDINGS = {
    'engine/__init__.py': ('e69de29bb2d1d6434b8b29ae775ad8c2e48c5391', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
    'engine/close_pass/__init__.py': ('120844e3f0808e206c6cf1b33ef7be8cc521ca75', '3dd4087aea6dbbb8d846d5302c64d60fc3eb60add7d72c16d58b5f5d18a3770d'),
    'engine/close_pass/massive_close.py': ('c5c61536bbba04fd9f8f72b893528bf00e94ee62', '43bc800dedba38a35ea5a94bc2f1de539401350a683123ecd9d40e6581e7bb66'),
    'engine/close_pass/massive_split_evidence.py': ('f7123e761ea83011f603a8e3cd37d4240ab5d59b', 'a1d32eacd48c90f793df717a7284fa044054c476241c622e9b9f9abc997c6942'),
    'engine/neuralweb/__init__.py': ('ffdf5aa13745cfc47e2e3e535fcacdc1e8eda10c', 'b4bb1e4f8374b687034d1d6ff6f303915bc0228ebaae463e12c1b0303284ad8d'),
    'engine/neuralweb/market_memory.py': ('adffe89b75ea72d58d06fc6618da7ba487b6598a', 'd64a53df452eeece71588e61006cb103e8930c6c7a8f3bc1c97b20a7dc747bc5'),
    'engine/neuralweb/market_memory_source_kernel.py': ('2a75c5016c07e9c1a5377fe4331a4f06b95e79dd', '270f6efdab81d464b7f251d0440c1d82b371bab35a08fab7ee35b8a3e26fffbc'),
    'engine/neuralweb/market_memory_sources_spy.py': ('42a4e08923e7f216a2031c36644185dd77c8612d', '8cb7a3b46afe4653e2da6c507b6f21c20f8b4fa7d244f0d5f40dd7984068ee22'),
    'engine/prophet_live/__init__.py': ('37586f93f8627acf3422bc6e24cbac27c70ba1c8', '215a1254dd4e767a1f19fe68a029a6a3a34195f8dbc3ae8da07716028f590fcc'),
    'engine/prophet_live/interval.py': ('e92bd6c49ac3f02c4e81c733ce1b59135e236cc8', 'd8e53f26b90ae5a80c3b1e37f9813e3e1005263ed011dbaa03905643b754bfe3'),
    'tests/test_close_pass_split_evidence.py': ('aaad1fd285846435eb9b84a4ca097b413503117f', 'c289ae9c4c4f9facc042d855f7252590167487f0cc13a00c9e36309026d24757'),
    'research/live_entry_radar/rs_pullback_launch/SPLIT_EVIDENCE_OWNER_CONTRACT_2026-10-07.md': ('d2ae5b8d1ab005a1053fcd353c55caba93eef3d5', '0bf1692ff80046cc99190907cd2fa9e2c02cec317e42149912ff843702210597'),
}
REGISTRY_BLOCKS = {
    'reference.corporate_actions.massive_split_evidence': (998, '4a2c5456a5ac3d0bdf79526b38f92d3ce88a0564f0db4d4124963418e0eb4e22'),
    'reference.vendor_aliases': (5644, 'b93c1ae64ac86527423c5bb44511c618cf450ede986cf4654c8a116c99293cd6'),
}
PREFIX_SHA = '3eca10507261c4939263aee1a70e01a3be5ad56854f1409d5b343e19f6406211'
SYNTHETIC_KEY = 'VERIFIER_SYNTHETIC_CREDENTIAL_NO_ACCOUNT'
UNRETAINED_TEXT = 'VERIFIER_UNRETAINED_METADATA'
FIRST_BODY = (
    b'{"status":"OK","results":[{"id":"Synthetic.Native-01",'
    b'"ticker":"SPY","execution_date":"2026-01-02",'
    b'"split_from":1.00000000000000000001,"split_to":2e+0,'
    b'"adjustment_type":"forward_split",'
    b'"historical_adjustment_factor":5.00000000000000000000e-1,'
    b'"unretained":"VERIFIER_UNRETAINED_METADATA"}]}'
)
REQUEST_ARGS = ('SPY', '2025-01-01', '2026-01-01')
AUTHORITY = {'tier': 'display', 'horizon_role': 'context', 'context_only': True, 'proposal_weight': 0,
             'may_rank': False, 'may_gate': False, 'may_size': False, 'may_escalate': False,
             'may_trade': False, 'may_originate': False, 'may_select_options_candidate': False,
             'may_execute': False, 'may_write_options_episode': False, 'may_append_outcome': False,
             'may_train_prophet': False}


class ProofFailure(RuntimeError):
    """Fixed control identifier; never arbitrary provider/host exception text."""


def require(ok, control):
    if not ok:
        raise ProofFailure(control)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def blob(body):
    return hashlib.sha1(b'blob ' + str(len(body)).encode('ascii') + b'\0' + body).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def export_ns(value, key=''):
    # No floats/datetimes are used for proof clocks. Convert only at JSON boundary.
    if isinstance(value, dict):
        return {k: export_ns(v, k) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [export_ns(v, key) for v in value]
    if key.endswith('_ns') and value is not None:
        require(type(value) is int, 'nanosecond_serialization_type')
        return str(value)
    return value


class EffectFence:
    """Deny network, non-Git children, credential reads, writes outside own temp."""
    def __init__(self):
        self.temp_root = None
        self.creating_temp = False
        self.temp_created = False
        self.allowed_git = None
        self.open_context = None
        self.original_os_open = os.open
        self.blocked = 0
        self.writes = 0
        self.source_paths = {str(ROOT / p) for p in (*BINDINGS, REGISTRY)}
        self.python_roots = tuple(os.path.realpath(p) for p in {sys.base_prefix, sys.prefix})

    def refuse(self, reason):
        self.blocked += 1
        raise ProofFailure('effect_fence_' + reason)

    def install(self):
        # CPython's open audit event omits dir_fd. Carry its resolved path through
        # the synchronous call so stdlib fd-relative cleanup is checked exactly.
        # This wrapper changes no flags/mode/result and grants no extra directory.
        def checked_open(path, flags, mode=0o777, *, dir_fd=None):
            previous = self.open_context
            self.open_context = self.path(path, dir_fd)
            try:
                return self.original_os_open(path, flags, mode, dir_fd=dir_fd)
            finally:
                self.open_context = previous
        os.open = checked_open
        sys.addaudithook(self)

    def path(self, value, dir_fd=None):
        if isinstance(value, int):
            value = os.readlink('/proc/self/fd/' + str(value))
        value = os.fsdecode(value)
        if not os.path.isabs(value) and dir_fd not in (None, -1):
            value = os.path.join(os.readlink('/proc/self/fd/' + str(dir_fd)), value)
        return os.path.realpath(value)

    def inside_temp(self, path):
        return self.temp_root is not None and (path == self.temp_root or path.startswith(self.temp_root + '/'))

    def write(self, value, dir_fd=None):
        if not self.inside_temp(self.path(value, dir_fd)):
            self.refuse('write_outside_private_temp')
        self.writes += 1

    def __call__(self, event, args):
        if event.startswith('socket.') or event in {'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'pty.spawn'}:
            self.refuse('external_execution_or_network')
        if event == 'subprocess.Popen':
            if self.allowed_git is None or tuple(args[1]) != self.allowed_git:
                self.refuse('subprocess')
        elif event == 'tempfile.mkdtemp':
            path = self.path(args[0])
            if (not self.creating_temp or self.temp_created or os.path.dirname(path) != '/tmp'
                    or not os.path.basename(path).startswith('installed-split-proof-')):
                self.refuse('unexpected_temporary_directory')
            self.temp_root = path
        elif event == 'open':
            if isinstance(args[0], int) and self.allowed_git is not None:
                target = os.readlink('/proc/self/fd/' + str(args[0]))
                if target.startswith('pipe:') and not args[2] & (os.O_WRONLY | os.O_RDWR):
                    return  # Read-only stdout/stderr pipes for the exact permitted Git child.
            path = self.open_context if self.open_context is not None else self.path(args[0])
            mode, flags = args[1], args[2]
            if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                self.write(path)
            else:
                parts = pathlib.PurePath(path).parts
                if '.ssh' in parts or '.aws' in parts or any(p == '.env' or p.startswith('.env.') for p in parts):
                    self.refuse('credential_read')
                allowed = (path in self.source_paths or self.inside_temp(path)
                           or path in {'/dev/urandom', '/dev/null', '/etc/localtime'}
                           or path.startswith('/usr/share/zoneinfo/')
                           or any(path == p or path.startswith(p + '/') for p in self.python_roots))
                # Python's venv might itself live below /opt; no broad /opt/macro read.
                if path.startswith(str(ROOT) + '/') and path not in self.source_paths:
                    allowed = False
                if not allowed:
                    self.refuse('read_outside_bound_sources_or_python')
        elif event in {'os.mkdir', 'os.remove', 'os.rmdir', 'os.chmod', 'os.chown', 'os.utime', 'os.truncate'}:
            positions = {'os.mkdir': 2, 'os.remove': 1, 'os.rmdir': 1, 'os.chmod': 2, 'os.chown': 3, 'os.utime': 3}
            pos = positions.get(event)
            self.write(args[0], args[pos] if pos is not None and len(args) > pos else None)
        elif event in {'os.rename', 'os.link'}:
            self.write(args[0], args[2] if len(args) > 2 else None)
            self.write(args[1], args[3] if len(args) > 3 else None)
        elif event == 'os.symlink':
            self.refuse('symlink')
        elif event == 'shutil.rmtree':
            self.write(args[0], args[1] if len(args) > 1 else None)
        elif event == 'import' and (args[0] == 'lib.config' or args[0] == 'app' or args[0].startswith('app.')):
            self.refuse('application_import')


def git_read(fence, *args):
    command = ('/usr/bin/git', '--no-optional-locks', '-C', str(ROOT), *args)
    fence.allowed_git = command
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, check=True, timeout=15,
                                env={'PATH': '/usr/bin:/bin', 'LANG': 'C', 'GIT_OPTIONAL_LOCKS': '0',
                                     'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null',
                                     'GIT_TERMINAL_PROMPT': '0', 'GIT_NO_LAZY_FETCH': '1'})
        return result.stdout.decode('ascii').strip()
    finally:
        fence.allowed_git = None


def read_sources():
    bodies, evidence = {}, {}
    for name in (*BINDINGS, REGISTRY):
        path = ROOT / name
        require(not path.is_symlink() and path.resolve() == path, 'installed_source_symlink_' + name)
        started = time.time_ns()
        with path.open('rb') as stream:
            before = os.fstat(stream.fileno())
            body = stream.read(1024 * 1024 + 1)
            after = os.fstat(stream.fileno())
        completed = time.time_ns()
        require(stat.S_ISREG(before.st_mode) and len(body) <= 1024 * 1024
                and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
                and before.st_size == len(body), 'installed_source_changed_during_read_' + name)
        require(started <= completed, 'installed_read_clock_regression')
        if name in BINDINGS:
            require((blob(body), sha(body)) == BINDINGS[name], 'installed_source_hash_' + name)
        bodies[name] = body
        evidence[name] = {'blob': blob(body), 'sha256': sha(body), 'bytes': len(body),
                          'read_started_utc_ns': started, 'read_completed_utc_ns': completed}
    require(sha(bodies['engine/close_pass/massive_close.py'][:28996]) == PREFIX_SHA,
            'legacy_wrapper_prefix')
    # Exact lexical projections, not a second YAML parser or dataset registry owner.
    lines = bodies[REGISTRY].splitlines(keepends=True)
    projections = {}
    for dataset, expected in REGISTRY_BLOCKS.items():
        marker = ('  - dataset_id: ' + dataset + '\n').encode('ascii')
        starts = [i for i, line in enumerate(lines) if line == marker]
        require(len(starts) == 1, 'registry_projection_occurrence_' + dataset)
        start = starts[0]
        end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith(b'  - dataset_id:')), len(lines))
        block = b''.join(lines[start:end])
        require((len(block), sha(block)) == expected, 'registry_projection_hash_' + dataset)
        projections[dataset] = {'bytes': len(block), 'sha256': sha(block)}
    evidence[REGISTRY]['exact_lexical_projections'] = projections
    return bodies, evidence


def load_owners(bodies):
    require(not any(n == 'engine' or n.startswith('engine.') for n in sys.modules), 'unexpected_preloaded_engine')
    loaded = []

    def load(name, path, package=False):
        spec = importlib.util.spec_from_file_location(name, ROOT / path,
                  submodule_search_locations=[str((ROOT / path).parent)] if package else None)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        if '.' in name:
            parent, leaf = name.rsplit('.', 1)
            setattr(sys.modules[parent], leaf, module)
        # Compile the exact verified source bytes; do not trust preexisting .pyc files.
        exec(compile(bodies[path], str(ROOT / path), 'exec'), module.__dict__)
        loaded.append({'module': name, 'path': path, 'sha256': sha(bodies[path])})
        return module

    load('engine', 'engine/__init__.py', True)
    load('engine.neuralweb', 'engine/neuralweb/__init__.py', True)
    load('engine.prophet_live', 'engine/prophet_live/__init__.py', True)
    load('engine.prophet_live.interval', 'engine/prophet_live/interval.py')
    load('engine.neuralweb.market_memory', 'engine/neuralweb/market_memory.py')
    load('engine.neuralweb.market_memory_source_kernel', 'engine/neuralweb/market_memory_source_kernel.py')
    namespace = types.ModuleType('engine.close_pass')
    namespace.__path__ = [str(ROOT / 'engine/close_pass')]
    namespace.__package__ = 'engine.close_pass'
    sys.modules['engine.close_pass'] = namespace
    sys.modules['engine'].close_pass = namespace
    owner = load('engine.close_pass.massive_close', 'engine/close_pass/massive_close.py')
    helper = load('engine.close_pass.massive_split_evidence', 'engine/close_pass/massive_split_evidence.py')
    require('lib.config' not in sys.modules and 'app' not in sys.modules, 'forbidden_import_absent')
    expected_bounds = (8, 1000, 1048576, 4096, 1048576, 65536, 4194304, 4096)
    actual_bounds = (helper.MAX_PAGES, helper.PAGE_LIMIT, helper.MAX_RESPONSE_BYTES, helper.MAX_ROWS,
                     helper.K._MAX_OBJECT_BYTES, helper.K._MAX_RECEIPT_BYTES,
                     helper.K._MAX_GENERATION_BYTES, helper.K._MAX_GENERATION_RECEIPTS)
    require(actual_bounds == expected_bounds, 'accepted_bounds')
    require(helper.ENDPOINT == 'https://api.massive.com/stocks/v1/splits', 'accepted_endpoint')
    require(dict(helper.AUTHORITY) == AUTHORITY, 'accepted_authority')
    return owner, helper, loaded


def framed(body, *, mode='length', missing=0):
    if mode == 'length':
        wire = b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body) + missing).encode('ascii') + b'\r\n\r\n' + body
    else:
        wire = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n' + format(len(body), 'x').encode('ascii') + b'\r\n' + body + b'\r\n'
        if mode == 'chunked':
            wire += b'0\r\n\r\n'

    class MemorySocket:
        def makefile(self, mode):
            require(mode == 'rb', 'synthetic_http_mode')
            return io.BytesIO(wire)

    response = http.client.HTTPResponse(MemorySocket())
    response.begin()
    return response


def files(root):
    result = {}
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'synthetic_store_symlink')
        if path.is_file():
            body = path.read_bytes()
            require(len(body) <= 4 * 1024 * 1024, 'synthetic_file_bound')
            result[str(path.relative_to(root))] = body
    require(len(result) <= 160 and sum(map(len, result.values())) <= 2 * 1024 * 1024,
            'verifier_total_temporary_budget')
    return result


def controls(owner, S, root, output):
    attempts = []
    calls = []
    pending = []

    def forbidden(*args, **kwargs):
        raise ProofFailure('unmocked_transport_or_credentials')

    def transport(request):
        require(bool(pending), 'unexpected_synthetic_request')
        require(request.get_header('Authorization') == 'Bearer ' + SYNTHETIC_KEY,
                'synthetic_credential_only')
        parsed = urllib.parse.urlsplit(request.full_url)
        require(parsed.scheme == 'https' and parsed.netloc == 'api.massive.com'
                and parsed.path == '/stocks/v1/splits' and not parsed.fragment,
                'synthetic_request_endpoint')
        query = urllib.parse.parse_qs(parsed.query, strict_parsing=True)
        require(query == {'ticker': ['SPY'], 'execution_date.gte': ['2025-01-01'],
                          'sort': ['execution_date.asc'], 'limit': ['1000']}
                or query == {'cursor': ['synthetic_next']}, 'synthetic_request_scope')
        calls.append({'query_keys': sorted(query), 'mock_only': True})
        response = pending.pop(0)
        if isinstance(response, Exception):
            raise response
        return framed(response) if isinstance(response, bytes) else response

    def read_record(name, stored):
        output['active_control'] = name
        before = time.time_ns()
        snap = S.SplitEvidenceReader(root, generation_id=stored.generation_id).read(stored.receipt['receipt_id'])
        after = time.time_ns()
        a, r, read = snap.artifact, snap.owner_receipt, snap.read_receipt
        require(a == stored.artifact and r == stored.receipt, name + '_consumer_roundtrip')
        require(a['started_utc_ns'] <= a['completed_utc_ns'] <= r['owner_intake_started_utc_ns']
                <= r['owner_receipt_assembled_utc_ns'] <= before
                <= read['read_started_utc_ns'] <= read['read_completed_utc_ns'] <= after,
                name + '_actual_clock_order')
        require(uuid.UUID(hex=a['acquisition_id']).version == 4, name + '_actual_uuid4')
        require(a['basis_eligible'] is False and r['basis_eligible'] is False
                and read['basis_eligible'] is False, name + '_basis_unavailable')
        require(a['authority'] == dict(S.AUTHORITY) == r['authority']
                and all(v is False for k, v in a['authority'].items() if k.startswith('may_'))
                and a['authority']['proposal_weight'] == 0, name + '_authority_false')
        object_body = (root / r['object_key']).read_bytes()
        require(object_body == S.K._canonical_bytes(a) and sha(object_body) == r['artifact_sha256']
                == read['artifact_sha256'], name + '_object_hash')
        require(read['receipt_sha256'] == sha(S.K._canonical_bytes(r))
                and read['read_receipt_sha256'] == sha(S.K._canonical_bytes({k: v for k, v in read.items() if k != 'read_receipt_sha256'})), name + '_custody_seals')
        attempts.append({'control': name, 'acquisition_id': a['acquisition_id'],
                         'acquisition_sha256': a['acquisition_sha256'], 'artifact_sha256': r['artifact_sha256'],
                         'capture_id': r['capture_id'], 'vintage_id': r['vintage_id'], 'revision_id': r['revision_id'],
                         'receipt_id': r['receipt_id'], 'generation_id': stored.generation_id,
                         'status': a['status'], 'failure_kind': a['failure_kind'],
                         'row_count': len(a['rows']), 'rows_sha256': sha(canonical(a['rows'])),
                         'pages': a['pages'], 'started_utc_ns': a['started_utc_ns'],
                         'completed_utc_ns': a['completed_utc_ns'],
                         'owner_intake_started_utc_ns': r['owner_intake_started_utc_ns'],
                         'owner_receipt_assembled_utc_ns': r['owner_receipt_assembled_utc_ns'],
                         'read_receipt': read, 'basis_id': None, 'basis_eligible': False})
        return snap

    def retain(name, *responses, status='complete', failure=None, row_count=1):
        output['active_control'] = name
        require(not pending, name + '_prior_queue_drained')
        pending.extend(responses)
        stored = owner.retain_split_history(*REQUEST_ARGS, store_root=root)
        require(not pending, name + '_expected_requests_consumed')
        snap = read_record(name, stored)
        require(snap.artifact['status'] == status and snap.artifact['failure_kind'] == failure
                and len(snap.artifact['rows']) == row_count, name + '_status_and_population')
        return stored, snap

    # No real API-key lookup or URL opener is invoked, even when inputs fail.
    with patch.object(owner, 'api_key', return_value=SYNTHETIC_KEY), \
         patch.object(S, '_open_split_request', transport), \
         patch.object(urllib.request, 'urlopen', forbidden), \
         patch.object(urllib.request, 'build_opener', forbidden):
        first, first_snap = retain('complete_exact_lexemes', FIRST_BODY)
        row = first_snap.artifact['rows'][0]
        require(row == {'id': 'Synthetic.Native-01', 'ticker': 'SPY', 'execution_date': '2026-01-02',
                        'split_from': '1.00000000000000000001', 'split_to': '2e+0',
                        'adjustment_type': 'forward_split', 'historical_adjustment_factor': '5.00000000000000000000e-1',
                        'page_index': 0, 'row_index': 0}, 'exact_native_fields_and_lexemes')
        page = first_snap.artifact['pages'][0]
        require(page['observed_body_sha256'] == sha(FIRST_BODY) and page['body_bytes_observed'] == len(FIRST_BODY)
                and page['body_complete'] is True, 'exact_observed_body_identity')
        require(row['execution_date'] > first_snap.artifact['request']['basis_date'], 'named_basis_date_not_applicability')
        output['retained_first_row'] = row
        output['synthetic_fixture'] = {'body_sha256': sha(FIRST_BODY), 'body_bytes': len(FIRST_BODY),
                                       'event_date': row['execution_date'], 'named_basis_date': REQUEST_ARGS[2],
                                       'provider_publication_time': None, 'whole_raw_body_stored': False}
        pinned = S.SplitEvidenceReader(root, generation_id=first.generation_id)
        immutable = files(root)

        empty, _ = retain('complete_empty', b'{"status":"OK","results":[]}', row_count=0)
        optional = b',"historical_adjustment_factor":5.00000000000000000000e-1'
        _, absent_factor = retain('optional_factor_absent', FIRST_BODY.replace(optional, b''))
        require('historical_adjustment_factor' not in absent_factor.artifact['rows'][0], 'absent_factor_not_imputed')
        retain('optional_factor_null', FIRST_BODY.replace(optional, b',"historical_adjustment_factor":null'),
               status='failed', failure='malformed_row', row_count=0)
        for label, body in [('results_missing', b'{"status":"OK"}'),
                            ('results_null', b'{"status":"OK","results":null}')]:
            retained, snap = retain(label, body, status='failed', failure='results_missing', row_count=0)
            require(snap.artifact['pages'][0]['rows_received'] is None, label + '_unknown_not_zero')
        _, failed = retain('transport_no_response', urllib.error.URLError('SYNTHETIC_TRANSPORT'),
                           status='failed', failure='transport', row_count=0)
        require(failed.artifact['pages'][0]['observed_body_sha256'] is None
                and failed.artifact['pages'][0]['http_status'] is None
                and failed.artifact['pages'][0]['rows_received'] is None, 'transport_null_fields')

        # Types are tested through raw JSON parsing, not by pre-normalizing rows.
        for label, token in [('string', b'"2"'), ('boolean', b'true'), ('null', b'null')]:
            retain('numeric_type_' + label, FIRST_BODY.replace(b'"split_to":2e+0', b'"split_to":' + token),
                   status='failed', failure='malformed_row', row_count=0)
        retain('native_id_null', FIRST_BODY.replace(b'"id":"Synthetic.Native-01"', b'"id":null'),
               status='failed', failure='malformed_row', row_count=0)

        for label, response in [('short_content_length', framed(FIRST_BODY, missing=10)),
                                ('incomplete_chunked', framed(FIRST_BODY, mode='truncated_chunked'))]:
            _, snap = retain(label, response, status='failed', failure='http_framing', row_count=0)
            p = snap.artifact['pages'][0]
            require(p['body_complete'] is False and p['rows_received'] is None
                    and p['body_bytes_observed'] == len(FIRST_BODY)
                    and p['observed_body_sha256'] == sha(FIRST_BODY), label + '_observed_prefix_only')

        class Interrupted(io.BytesIO):
            code = 200
            def read(self, amount):
                raise http.client.IncompleteRead(b'x' * amount, 10)
        _, incomplete = retain('bounded_incomplete_read', Interrupted(), status='failed', failure='http_framing', row_count=0)
        require(incomplete.artifact['pages'][0]['body_bytes_observed'] == 65536
                and incomplete.artifact['pages'][0]['observed_body_sha256'] == sha(b'x' * 65536), 'incomplete_read_bounded_prefix')

        later = FIRST_BODY[:-1] + b',"next_url":"https://api.massive.com/stocks/v1/splits?cursor=synthetic_next"}'
        _, partial = retain('later_page_transport_failure', later, urllib.error.URLError('SYNTHETIC_LATER'),
                            status='partial', failure='transport')
        require(len(partial.artifact['pages']) == 2 and partial.artifact['pages'][1]['rows_received'] is None,
                'partial_keeps_prior_row_and_failed_page')
        corrected_body = FIRST_BODY.replace(b'"split_to":2e+0', b'"split_to":3.000')
        corrected, _ = retain('correction_recovery', corrected_body)
        repeated, _ = retain('identical_body_new_occurrence', framed(FIRST_BODY, mode='chunked'))
        require(repeated.artifact['rows'] == first.artifact['rows'] and len({x.receipt['capture_id'] for x in (first, corrected, repeated)}) == 3
                and len({x.receipt['revision_id'] for x in (first, corrected, repeated)}) == 3
                and len({x.receipt['vintage_id'] for x in (first, corrected, repeated)}) == 1,
                'correction_and_aba_occurrence_identity_not_price_vintage')
        old_read = pinned.read(first.receipt['receipt_id'])
        require(old_read.artifact == first_snap.artifact and old_read.owner_receipt == first_snap.owner_receipt
                and old_read.read_receipt['generation_id'] == first.generation_id, 'old_generation_preserved')
        try:
            pinned.read(corrected.receipt['receipt_id'])
        except S.K.SourceNotFound:
            pass
        else:
            raise ProofFailure('old_generation_must_refuse_later_receipt')
        for path, body in immutable.items():
            if path != 'SOURCE_HEAD.json':
                require((root / path).read_bytes() == body, 'immutable_first_generation_bytes')

        before = files(root)
        replay = S.intake_split_acquisition(first.artifact, store_root=root)
        require(replay.created is False and files(root) == before, 'same_occurrence_idempotent_without_writes')
        conflict = copy.deepcopy(first.artifact)
        conflict['rows'][0]['split_to'] = '9'
        S._seal(conflict)
        try:
            S.intake_split_acquisition(conflict, store_root=root)
        except S.SplitEvidenceError as exc:
            require(str(exc) == 'acquisition_id_conflict', 'same_occurrence_conflict_type')
        else:
            raise ProofFailure('same_occurrence_conflict_missing')
        require(files(root) == before, 'same_occurrence_conflict_preserves_store')

        # Only this synthetic store's HEAD replacement is fault-injected.
        output['active_control'] = 'failed_head_and_exact_orphan_recovery'
        pending.append(FIRST_BODY)
        acquired = S.acquire_split_history(*REQUEST_ARGS)
        require(not pending, 'publication_recovery_acquired_once')
        call_count = len(calls)
        head_path = S.K._head_path(root)
        old_head = head_path.read_bytes()
        old_count = len(S.SplitEvidenceReader(root).receipts())
        original_replace = os.replace
        def fail_head(source, destination, *args, **kwargs):
            if pathlib.Path(destination) == head_path:
                raise OSError('SYNTHETIC_HEAD_REFUSAL')
            return original_replace(source, destination, *args, **kwargs)
        with patch.object(S.K.os, 'replace', fail_head):
            try:
                S.intake_split_acquisition(acquired, store_root=root)
            except S.K.SourceStoreError as exc:
                require(str(exc) == 'cannot advance source HEAD', 'publication_failure_type')
            else:
                raise ProofFailure('publication_failure_missing')
        require(head_path.read_bytes() == old_head and len(S.SplitEvidenceReader(root).receipts()) == old_count,
                'failed_publication_keeps_published_generation')
        recovered = S.intake_split_acquisition(acquired, store_root=root)
        read_record('exact_orphan_publication_recovery', recovered)
        require(len(calls) == call_count and len(S.SplitEvidenceReader(root).receipts()) == old_count + 1,
                'publication_recovery_without_new_acquisition')

        all_receipts = S.SplitEvidenceReader(root).receipts()
        require(len(all_receipts) == len(attempts) and len({x['receipt_id'] for x in all_receipts}) == len(attempts),
                'all_attempts_retained_once')
        final_files = files(root)
        require(not any(SYNTHETIC_KEY.encode() in b or UNRETAINED_TEXT.encode() in b for b in final_files.values()),
                'credentials_and_arbitrary_body_text_not_persisted')
        require(all(a['basis_eligible'] is False and a['basis_id'] is None for a in attempts), 'no_basis_promotion')
        output['attempts'] = attempts
        output['checks'] = {
            'complete_and_empty_vs_unknown': 'PASS', 'native_fields_exact_numeric_lexemes_and_types': 'PASS',
            'real_http_response_length_and_chunked_framing': 'PASS', 'bounded_incomplete_read': 'PASS',
            'partial_failed_and_recovery_retained': 'PASS', 'aba_and_old_generation_replay': 'PASS',
            'same_occurrence_idempotency_and_conflict': 'PASS', 'failed_head_and_exact_orphan_recovery': 'PASS',
            'actual_nanosecond_clocks_and_uuid4': 'PASS', 'no_factor_or_basis_authority': 'PASS',
            'sanitized_storage': 'PASS',
        }
        output['temporary_store'] = {'file_count': len(final_files), 'bytes': sum(map(len, final_files.values())),
                                     'file_map_sha256': sha(canonical({p: sha(b) for p, b in sorted(final_files.items())})),
                                     'receipt_count': len(all_receipts), 'mock_http_attempts': len(calls),
                                     'family': dataclasses.asdict(S.FAMILY), 'authority': dict(S.AUTHORITY)}
        output.pop('active_control', None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--merged-release', required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    started = time.time_ns()
    output = {'schema': 'mastermind.installed_split_function_conformance.v1',
              'status': 'FAIL', 'proof_id': uuid.uuid4().hex, 'started_utc_ns': started,
              'accepted_source_head': SOURCE_HEAD, 'reviewed_merge_tree': KNOWN_MERGED_TREE,
              'expected_installed_head': args.expected_head, 'merged_release': args.merged_release,
              'phase1': 'NOT_ADMITTED', 'hypotheses': {'H1': 'NOT_TESTED', 'H2': 'NOT_TESTED', 'H3': 'NOT_TESTED'},
              'authority': dict(AUTHORITY),
              'basis_id': None, 'factor_applicability': None, 'factor_basis_admitted': False,
              'claims': {'installed_functions_with_synthetic_inputs': False, 'normal_package_initialization': False,
                         'live_market_acquisition': False, 'live_http_api': False, 'source_authenticity': False,
                         'price_or_volume_reconstruction': False, 'production_cadence': False},
              'limits': ['Whole raw response bodies are not stored; hashes/counts bind observed bytes and retained numeric lexemes.',
                         'Owner receipt assembly precedes HEAD publication; read clocks are actual later custody, not market publication.',
                         'Named basis date and kernel request vintage do not establish price/factor vintage or applicability.',
                         'Namespace-only close_pass loader bypasses unrelated initializer; ordinary package/application integration unverified.',
                         'Root must pair installed hash evidence with full-M2 release lineage; caller SHA is not authentication.']}
    fence = EffectFence()
    fence.install()
    phase = 'installed_source_binding'
    temp_path = None
    try:
        for value in (args.expected_head, args.merged_release):
            require(re.fullmatch('[a-f0-9]{40}', value) is not None, 'full_sha_arguments')
        require(sys.flags.dont_write_bytecode, 'python_B_flag_required')
        require(pathlib.Path(sys.prefix).resolve() == pathlib.Path('/opt/macro-api/.venv'), 'expected_python_runtime')
        head = git_read(fence, 'rev-parse', 'HEAD')
        require(head == args.expected_head, 'expected_installed_head')
        shallow = git_read(fence, 'rev-parse', '--is-shallow-repository')
        require(shallow in {'true', 'false'}, 'git_shallow_state')
        output['release_relation'] = {'installed_head': head, 'shallow': shallow == 'true',
                                      'ancestry': 'UNAVAILABLE_NOT_CHECKED', 'required_pairing': 'root_full_M2_lineage_receipt'}
        bodies, before = read_sources()
        output['installed_source_before'] = before
        phase = 'isolated_actual_owner_loading'
        owner, helper, loaded = load_owners(bodies)
        output['loaded_source_modules'] = loaded
        phase = 'temporary_owner_conformance'
        fence.creating_temp = True
        with tempfile.TemporaryDirectory(prefix='installed-split-proof-', dir='/tmp') as directory:
            fence.creating_temp = False
            fence.temp_created = True
            temp_path = pathlib.Path(directory)
            require(str(temp_path.resolve()) == fence.temp_root and stat.S_IMODE(temp_path.stat().st_mode) == 0o700,
                    'private_temporary_directory')
            controls(owner, helper, temp_path / helper.ROOT_LEAF, output)
        require(not temp_path.exists(), 'temporary_cleanup_completed')
        output['temporary_cleanup'] = 'OWN_DIRECTORY_REMOVED'
        phase = 'installed_source_unchanged'
        after_bodies, after = read_sources()
        require(after_bodies == bodies and git_read(fence, 'rev-parse', 'HEAD') == head, 'installed_bytes_and_head_unchanged')
        output['installed_source_after'] = after
        require(fence.blocked == 0, 'no_effect_fence_violation')
        output['claims']['installed_functions_with_synthetic_inputs'] = True
        output['status'] = 'PASS'
    except Exception as exc:
        output['failure'] = {'phase': phase, 'exception_type': type(exc).__name__,
                             'control': str(exc) if isinstance(exc, ProofFailure) else output.get('active_control', 'unexpected_exception')}
        if temp_path is not None:
            output['temporary_cleanup'] = 'OWN_DIRECTORY_REMOVED' if not temp_path.exists() else 'NOT_CONFIRMED_ROOT_RECONCILE_EXACT_PATH'
            if temp_path.exists():
                output['remaining_owned_temporary_path'] = str(temp_path)
    finally:
        output['effect_guard'] = {'blocked_operations': fence.blocked, 'temporary_write_events': fence.writes,
                                  'scope': 'Python audit guard; not an OS sandbox', 'network_permitted': False,
                                  'credentials': 'synthetic replacement only', 'real_provider_calls': 0}
        output['completed_utc_ns'] = time.time_ns()
        if output['completed_utc_ns'] < started:
            output['status'] = 'FAIL'
            output['failure'] = {'phase': 'completion', 'control': 'outer_clock_regression'}
        print(json.dumps(export_ns(output), sort_keys=True, separators=(',', ':'), allow_nan=False))
    return 0 if output['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
