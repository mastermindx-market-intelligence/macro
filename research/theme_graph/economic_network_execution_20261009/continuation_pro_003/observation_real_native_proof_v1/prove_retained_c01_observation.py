#!/usr/bin/env python3
"""PREPARED ONLY. Principal-owned real retained-C01 private observation proof.

This lane may syntax-compile this file, but may not run it. The principal supplies
an independently reviewed exact code manifest and authorizes the new private
store/output locations. No source acquisition, Git, store factory or test fixture
is used. Application execution is intentionally confined to the real public APIs.
Full results belong only in the exclusive private receipt and private child pipes.
"""

import argparse
import contextlib
from datetime import datetime, timezone
import hashlib
import importlib
import importlib.machinery
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import signal
import socket
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
CODE_ROOT = Path('/Volumes/Mastermind/agent-workspaces/macro/web/gmi-economic-observations-20261009-pro-003')
CACHE = Path('/Users/chriswong/Library/Caches/Mastermind/economic-network-20261009')
OPERATION = 'gmi-economic-observations-20261009-pro-003'
SOURCE_SCHEMA = 'economic_network.observation_native_source_manifest/v1'
PROOF_SCHEMA = 'economic_network.retained_c01_observation_native_proof/v1'
CHILD_SCHEMA = 'economic_network.retained_c01_observation_fresh_reader/v1'
REFERENCE_SCHEMA = 'company_intelligence.relationship_observation_reference/v1'
MANIFEST_SCHEMA = 'company_intelligence.relationship_observation_manifest/v1'
PACKAGE_SCHEMA = 'company_intelligence.relationship_observation_package/v1'
CONTRACT = 'c01_private_observation/v1'
PREFIX = 'company_intelligence/relationship_observations/v1/'
REVIEW_SET_ID = 'retained-micron-C01-observation-v1'
HISTORY_AS_OF = '2024-02-26T12:00:00Z'
CURRENT_INSPECTION_SHA = '6bbb39a463030c992760fb3309006f94bc10c37126894f0ae76a1288e46fb8b4'
CHUNK_LIMIT, PACKAGE_LIMIT, CHUNK_COUNT_LIMIT = 16384, 1048576, 64
CODE_FILE_LIMIT, CODE_TOTAL_LIMIT, RECEIPT_LIMIT = 4 * 1048576, 32 * 1048576, 16 * 1048576
AUTHORITY = {key: False for key in ('rank', 'gate', 'size', 'trade', 'prediction')}
RESEARCH_PREFIX = 'research/theme_graph/economic_network_execution_20261009/'
INPUTS = {
    'source': (CACHE / 'micron-hbm3e-a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e.html',
               504119, 'a7efabf9cec581ba684688368118e3e13df6a3043aff56667927e24df97e8b2e'),
    'candidate': (CACHE / 'micron-manual-candidate.json',
                  1930, '5e2a2c789599e5e146b6e2969ccc243ee5c85b7d74c67af76b7c437857c4383c'),
    'source_record': (CODE_ROOT / (RESEARCH_PREFIX + 'MICRON_SOURCE_CASE.json'),
                      1588, 'dd72d31afce12ca727a171e6f635d7085c8c2d6bff6bea2750f9c29a04fe101b'),
    'pilot_adjudications': (CODE_ROOT / (RESEARCH_PREFIX + 'native_adoption_pilot_v1/case_adjudications.jsonl'),
                            23612, '039cfbfa04738612457e5ed04be4b20864c088103bb5a8309ff7839938830b25'),
    'semantic_review': (CODE_ROOT / (RESEARCH_PREFIX + 'native_adoption_pilot_v1/supporting_evidence/independent_semantic_judgments.json'),
                         10309, '4357ab18cd8dddafd944b30641bf4c9168f755e1da60059a6ee5d8ded9192652'),
    'retained_first_review': (CODE_ROOT / (RESEARCH_PREFIX + 'retained_micron_semantic_addendum_v1/first_reader_judgment.json'),
                              6032, '3a9ce686a0593f9731c89ef63c20afb92dce810681aa3d0039bd72ce0f4d6408'),
    'retained_independent_review': (CODE_ROOT / (RESEARCH_PREFIX + 'retained_micron_semantic_addendum_v1/principal_independent_judgment.json'),
                                    3732, '96c5a97fd64a3c4330bba160310e5ade8babb211fd61d567fc5b119346837d9a'),
}
PINNED_CODE = {
    'engine/company_intelligence/relationship_observations.py':
        (42756, '85c07b309ff7b7220ec12f2b3f25c924a2ef4c9ab495ce9030f61038cbb9e8c7'),
    'engine/company_intelligence/relationship_candidates.py':
        (45473, 'a558922c0586a5532f3912524b48f3cf592c3c6c9c21f689e3d416976e9cae55'),
    'engine/research_vault/r2_store.py':
        (47498, '7ba42eb8f74c034413997707a35156e67342fb9a30ca2b80dde0f11d1dc7e2bd'),
    'lib/dataos/registry.py':
        (16599, 'b57ec16a61086b8d35beb2f81af30efc4af55f1ac07ec95cfcfd87beefeef0a5'),
}
FIRST_PARTY = {'engine', 'lib', 'collectors', 'scripts', 'tests', 'config'}
BLOCKED_ROOTS = {'collectors', 'tests', 'pytest', 'requests', 'urllib3', 'httpx',
                 'aiohttp', 'boto3', 'botocore'}
BLOCKED_MODULES = {
    'urllib.request', 'http.client', 'capture_one_native_sec_filing',
    'test_company_relationship_observations', 'engine.earnings_release.collector',
    'engine.earnings_release.capture', 'engine.earnings_release.source_capture',
    'engine.collectors', 'engine.captures',
}
IMPORT_CONTROLS = (
    'collectors', 'collectors.sec_document_spine',
    'collectors.fundamental_forensics_acquisition',
    'collectors.fundamental_forensics_companyfacts', 'collectors.edgar_forensics',
    'tests', 'tests.test_company_relationship_observations', 'pytest',
    'requests', 'urllib3', 'httpx', 'aiohttp', 'boto3', 'botocore',
    'urllib.request', 'http.client', 'capture_one_native_sec_filing',
    'test_company_relationship_observations',
)
PROOF_LIMITS = [
    'Private retained C01 observation only; NOT_ADMITTED; no production or Graph1 promotion.',
    'No rights, legal-party identity, semantic truth, review authorship or independence authentication.',
    'No native relationship dataset or historical system replay; empty-registry history must abstain.',
    'No current commerce, magnitudes, prediction or decision authority established.',
    'LocalStore witness only; no cloud/provider/backend equivalence claim.',
    'Exact code bytes and observed import closure are verified; Git/source adjudication belongs to the principal.',
    'Python audit and descriptor guards witness reviewed execution; they are not an operating-system sandbox.',
    'Two fresh processes share one interpreter installation and verified code; this is not cross-platform proof.',
]


class ProofError(RuntimeError):
    """Messages are fixed public-safe codes, never interpolated evidence bodies."""


class GuardDenied(ProofError):
    pass


def require(condition, code):
    if not condition:
        raise ProofError(code)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                      separators=(',', ':')).encode('utf-8')


def parse(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'JSON_DUPLICATE_KEY')
            result[key] = value
        return result
    def constant(_):
        raise ProofError('JSON_NONFINITE')
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)


def digest(value, length=64):
    return (type(value) is str and re.fullmatch(r'[0-9a-f]{%d}' % length, value) is not None
            and value != '0' * length)


def absolute(value):
    require(type(value) is str and value and '\x00' not in value and '\\' not in value,
            'ABSOLUTE_PATH_INVALID')
    path = Path(value)
    require(path.is_absolute() and str(path) == value
            and all(part not in {'.', '..', ''} for part in value.split('/')[1:]),
            'ABSOLUTE_PATH_NONCANONICAL')
    return path


def relative(value):
    require(type(value) is str and value and '\\' not in value and '\x00' not in value,
            'SOURCE_PATH_INVALID')
    require(not value.startswith('/') and all(part not in {'', '.', '..'} for part in value.split('/'))
            and str(PurePosixPath(value)) == value, 'SOURCE_PATH_UNSAFE')
    return value


def real_chain(path):
    for item in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(item.lstat().st_mode), 'SYMLINK_OR_NON_DIRECTORY_CHAIN')


def identity(s):
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, stat.S_IMODE(s.st_mode)]


def checked_bytes(path, maximum):
    """Read exact regular bytes through O_NOFOLLOW directory descriptors."""
    path = absolute(str(path))
    directory_fd = file_fd = None
    try:
        directory_fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for part in path.parts[1:-1]:
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory_fd)
            os.close(directory_fd)
            directory_fd = next_fd
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory_fd)
        before = os.fstat(file_fd)
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum,
                'INPUT_NOT_BOUNDED_REGULAR_FILE')
        chunks, total = [], 0
        while total <= maximum:
            part = os.read(file_fd, min(65536, maximum + 1 - total))
            if not part:
                break
            chunks.append(part)
            total += len(part)
        raw, after = b''.join(chunks), os.fstat(file_fd)
        require(identity(before) == identity(after) and len(raw) == before.st_size,
                'FILE_CHANGED_DURING_READ')
        require(identity(path.lstat()) == identity(after), 'FILE_PATH_IDENTITY_CHANGED')
        real_chain(path.parent)
        return raw, {'identity': identity(after), 'byte_length': len(raw), 'sha256': sha(raw)}
    finally:
        if file_fd is not None:
            os.close(file_fd)
        if directory_fd is not None:
            os.close(directory_fd)


def source_preflight(request):
    manifest_path = absolute(request['source_manifest'])
    harness_path = absolute(request['harness_path'])
    require(harness_path == absolute(os.path.abspath(__file__)), 'HARNESS_PATH_MISMATCH')
    require(digest(request['source_manifest_sha256']) and digest(request['harness_sha256']),
            'SOURCE_OR_HARNESS_DIGEST_INVALID')
    require(not manifest_path.is_relative_to(CODE_ROOT) or manifest_path.suffix == '.json',
            'MANIFEST_PATH_INVALID')
    manifest_raw, manifest_state = checked_bytes(manifest_path, 1048576)
    require(sha(manifest_raw) == request['source_manifest_sha256'], 'SOURCE_MANIFEST_DIGEST_MISMATCH')
    harness_raw, harness_state = checked_bytes(harness_path, 1048576)
    require(sha(harness_raw) == request['harness_sha256'], 'HARNESS_DIGEST_MISMATCH')
    manifest = parse(manifest_raw)
    require(type(manifest) is dict and set(manifest) == {
        'schema', 'repository', 'operation_id', 'workspace', 'reviewed_head', 'phase', 'files'},
        'SOURCE_MANIFEST_SHAPE_INVALID')
    require(manifest['schema'] == SOURCE_SCHEMA
            and manifest['repository'] == 'mastermindx-market-intelligence/macro'
            and manifest['operation_id'] == OPERATION and manifest['workspace'] == str(CODE_ROOT),
            'SOURCE_MANIFEST_SCOPE_MISMATCH')
    require(digest(manifest['reviewed_head'], 40) and manifest['phase'] in {
        'PREMERGE_FROZEN_CANDIDATE', 'POSTMERGE_ACCEPTED_SOURCE'}, 'SOURCE_PHASE_INVALID')
    rows = manifest['files']
    require(type(rows) is list and 4 <= len(rows) <= 256, 'SOURCE_MANIFEST_COUNT_INVALID')
    states, hashes, total = {}, {}, 0
    for row in rows:
        require(type(row) is dict and set(row) == {'path', 'byte_length', 'sha256'},
                'SOURCE_MANIFEST_ROW_INVALID')
        name = relative(row['path'])
        require(name.endswith('.py') and name.split('/')[0] in FIRST_PARTY,
                'SOURCE_MANIFEST_CODE_ONLY_REQUIRED')
        require(name not in hashes and type(row['byte_length']) is int
                and 0 <= row['byte_length'] <= CODE_FILE_LIMIT and digest(row['sha256']),
                'SOURCE_MANIFEST_DUPLICATE_OR_BAD_PIN')
        raw, state = checked_bytes(CODE_ROOT / name, CODE_FILE_LIMIT)
        require(len(raw) == row['byte_length'] and sha(raw) == row['sha256'], 'SOURCE_BYTES_MISMATCH')
        states[str(CODE_ROOT / name)] = state
        hashes[name] = (row['byte_length'], row['sha256'])
        total += len(raw)
        require(total <= CODE_TOTAL_LIMIT, 'SOURCE_TOTAL_LIMIT')
    require(all(hashes.get(name) == expected for name, expected in PINNED_CODE.items()),
            'REQUIRED_FROZEN_CODE_MISMATCH')
    require(str(harness_path) not in states and str(manifest_path) not in states
            and manifest_path != harness_path, 'PROOF_INPUT_PATH_COLLISION')
    states[str(manifest_path)] = manifest_state
    states[str(harness_path)] = harness_state
    return manifest, hashes, states


def original_preflight():
    data, states = {}, {}
    for role, (path, length, expected) in INPUTS.items():
        raw, state = checked_bytes(path, PACKAGE_LIMIT)
        require(len(raw) == length and sha(raw) == expected, 'RETAINED_INPUT_PIN_MISMATCH')
        require(raw.decode('utf-8').encode('utf-8') == raw, 'RETAINED_INPUT_NOT_EXACT_UTF8')
        data[role], states[str(path)] = raw, state
    require(len(data) == 7, 'RETAINED_INPUT_ROLE_COUNT')
    return data, states


def states_now(baseline):
    return {name: checked_bytes(Path(name), max(CODE_FILE_LIMIT, row['byte_length']))[1]
            for name, row in baseline.items()}


def tree_state(root):
    real_chain(root)
    result, total = {}, 0
    for directory, names, files in os.walk(root, followlinks=False):
        names.sort()
        files.sort()
        parent = Path(directory)
        for path in [parent, *(parent / name for name in names)]:
            s = path.lstat()
            require(stat.S_ISDIR(s.st_mode), 'STORE_DIRECTORY_LINK_OR_SPECIAL')
            result[str(path.relative_to(root))] = {'type': 'directory', 'identity': identity(s)}
        for name in files:
            path = parent / name
            raw, state = checked_bytes(path, CHUNK_LIMIT)
            total += len(raw)
            result[str(path.relative_to(root))] = {'type': 'file', **state}
        require(len(result) <= 96 and total <= PACKAGE_LIMIT + CHUNK_LIMIT,
                'STORE_INVENTORY_BOUND_EXCEEDED')
    return result


def blocked_import(name):
    return (name.split('.')[0] in BLOCKED_ROOTS or
            any(name == part or name.startswith(part + '.') for part in BLOCKED_MODULES))


class ExecutionGuard:
    """Ordinary Python I/O guard; descriptor attribution closes dir_fd ambiguity.

    The audit event for open() omits dir_fd. The os.open wrapper resolves that
    descriptor against tracked directory identities and supplies the exact path
    to the audit hook for this one call. Unknown descriptors fail closed.
    """

    def __init__(self, request, hashes, *, child, output_fd=None):
        self.request, self.hashes, self.child = request, hashes, child
        self.root = absolute(request['store_root'])
        self.code_files = {str(CODE_ROOT / name) for name in hashes}
        self.proof_files = {request['source_manifest'], request['harness_path']}
        self.runtime_roots = {Path(sys.prefix), Path(sys.base_prefix), Path(sys.exec_prefix), Path(sys.base_exec_prefix)}
        self.runtime_roots = {p for p in self.runtime_roots if p.is_absolute() and str(p) != '/'}
        self.stage, self.active_key, self.call_path = 'readonly', None, None
        self.control, self.controls, self.unexpected, self.loaded = None, [], [], set()
        self.constructor_events, self.mutations = [], []
        self.read_files, self.fds, self.children = set(), {}, set()
        self.output_fd, self.private_output = output_fd, request.get('private_output')
        self.allow_original_reads = False
        self.child_command = [sys.executable, '-I', '-B', request['harness_path'], '--child']
        self.spawn_active, self.spawn_count, self.process_observations = False, 0, []
        if output_fd is not None:
            self.fds[output_fd] = (self.private_output, True, False)
        self.saved = {name: getattr(os, name) for name in (
            'open', 'close', 'dup', 'read', 'write', 'fsync', 'mkdir', 'replace', 'rename',
            'unlink', 'remove', 'pipe')}

    def deny(self, event):
        record = {'requested': self.control, 'denied_event': event}
        (self.controls if self.control is not None else self.unexpected).append(record)
        raise GuardDenied('EXECUTION_GUARD_DENIED')

    def path_at(self, path, dir_fd=None):
        value = os.fsdecode(path)
        if os.path.isabs(value):
            candidate = os.path.normpath(value)
        elif dir_fd is not None and dir_fd != -1:
            known = self.fds.get(dir_fd)
            if known is None or not known[2]:
                self.deny('filesystem:unknown_directory_descriptor')
            candidate = os.path.normpath(os.path.join(known[0], value))
        else:
            candidate = os.path.abspath(value)
        return Path(candidate)

    def readable_file(self, path):
        value = str(path)
        if value in self.code_files or value in self.proof_files or path.is_relative_to(self.root):
            return True
        if any(path.is_relative_to(p) for p in self.runtime_roots):
            return True
        if self.allow_original_reads and not self.child and value in {str(p) for p, _, _ in INPUTS.values()}:
            return True
        return self.stage == 'private_receipt' and not self.child and value == self.private_output

    def readable_directory(self, path):
        targets = [self.root, CODE_ROOT, *(Path(x) for x in self.proof_files),
                   *(Path(x) for x in self.code_files), *self.runtime_roots]
        if self.allow_original_reads and not self.child:
            targets.extend(p for p, _, _ in INPUTS.values())
        if self.stage == 'private_receipt' and self.private_output:
            targets.append(Path(self.private_output))
        return any(path == target or path in target.parents for target in targets) or self.readable_file(path)

    def is_temp(self, path):
        if self.active_key is None:
            return False
        target = self.root / self.active_key
        return path.parent == target.parent and re.fullmatch(
            r'\.' + re.escape(target.name) + r'\.cas\.[1-9][0-9]*\.[1-9][0-9]*', path.name) is not None

    def check_open(self, path, mode, flags):
        writing = ((isinstance(mode, str) and any(c in mode for c in 'wax+')) or
                   (isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)))
        if type(path) is int:
            known = self.fds.get(path)
            if path in (0, 1, 2) and not writing:
                return
            if known is None or (writing and not self.writable_fd(path)):
                self.deny('filesystem:unknown_or_forbidden_descriptor_open')
            return
        actual = self.call_path if self.call_path is not None else self.path_at(path)
        if writing:
            lock = actual == self.root / '.strict-conditional-write.lock'
            flags_ok = type(flags) is int and bool(flags & os.O_NOFOLLOW) and not flags & (os.O_TRUNC | os.O_APPEND)
            if not (self.stage == 'append' and self.active_key is not None and flags_ok
                    and (lock or self.is_temp(actual))):
                self.deny('filesystem:write_open')
            self.mutations.append({'event': 'open_write', 'path': str(actual.relative_to(self.root))})
        else:
            directory = type(flags) is int and bool(flags & os.O_DIRECTORY)
            if not (self.readable_directory(actual) if directory else self.readable_file(actual)):
                self.deny('filesystem:read_outside_bound_files')
            if not directory:
                self.read_files.add((self.stage, str(actual)))

    def writable_fd(self, fd):
        known = self.fds.get(fd)
        if known is None:
            return False
        if fd == self.output_fd:
            return self.stage == 'private_receipt' and not self.child
        if known[0] == '<child-pipe-write>':
            return self.spawn_active and not self.child
        return self.stage == 'append' and self.active_key is not None and self.is_temp(Path(known[0]))

    def check_import(self, name):
        if blocked_import(name):
            self.deny('import:' + name)

    def audit(self, event, args):
        if event == 'import':
            self.check_import(args[0])
        if event.startswith('socket.'):
            self.deny(event)
        if event in {'subprocess.Popen', 'os.posix_spawn'}:
            if not self.spawn_active or self.child or args[0] != sys.executable or list(args[1]) != self.child_command:
                self.deny(event)
            if event == 'subprocess.Popen':
                self.spawn_count += 1
                require(self.spawn_count <= 2, 'CHILD_PROCESS_COUNT_EXCEEDED')
        elif event in {'os.system', 'os.exec', 'os.fork', 'os.forkpty', 'pty.spawn'}:
            self.deny(event)
        if event == 'os.kill':
            if not (self.spawn_active and not self.child and args[0] in self.children and args[1] == signal.SIGKILL):
                self.deny(event)
        if event == 'open':
            self.check_open(*args[:3])
        if event == 'os.mkdir':
            path = self.path_at(args[0], args[2])
            if self.stage == 'constructor' and path == self.root:
                if self.child:
                    require(stat.S_ISDIR(path.lstat().st_mode), 'CHILD_EXISTING_ROOT_CHANGED')
                self.constructor_events.append('existing_store_directory_mkdir' if self.child else 'new_store_directory_mkdir')
                require(len(self.constructor_events) == 1, 'CONSTRUCTOR_MKDIR_COUNT')
                return
            if self.stage == 'append' and self.active_key is not None:
                target = self.root / self.active_key
                if path != self.root and path.is_relative_to(self.root) and path in target.parents:
                    self.mutations.append({'event': 'mkdir_attempt', 'path': str(path.relative_to(self.root))})
                    return
            self.deny(event)
        if event == 'os.rename':
            source, target = self.path_at(args[0], args[2]), self.path_at(args[1], args[3])
            if not (self.stage == 'append' and self.is_temp(source)
                    and target == self.root / self.active_key):
                self.deny(event)
            require(not os.path.lexists(target), 'GUARD_WOULD_REPLACE_EXISTING_OBJECT')
            self.mutations.append({'event': 'publish_new_object', 'path': str(target.relative_to(self.root))})
        elif event == 'os.remove':
            path = self.path_at(args[0], args[1])
            if not (self.stage == 'append' and self.is_temp(path)):
                self.deny(event)
            self.mutations.append({'event': 'temporary_cleanup_attempt', 'path': str(path.relative_to(self.root))})
        elif event in {'os.rmdir', 'os.link', 'os.symlink', 'os.chmod', 'os.chown', 'os.utime',
                       'os.truncate', 'os.chflags', 'os.setxattr', 'os.removexattr',
                       'shutil.copyfile', 'shutil.copytree', 'shutil.rmtree', 'os.chdir', 'os.fchdir'}:
            self.deny(event)

    def install(self):
        require(not any(blocked_import(name) for name in sys.modules), 'PROHIBITED_MODULE_PRELOADED')
        require(not any(name.split('.')[0] in FIRST_PARTY for name in sys.modules),
                'FIRST_PARTY_MODULE_PRELOADED')
        guard = self

        class VerifiedSourceLoader(importlib.machinery.SourceFileLoader):
            def get_code(loader, fullname):
                path = Path(loader.path)
                name = path.relative_to(CODE_ROOT).as_posix()
                require(name in guard.hashes, 'FIRST_PARTY_IMPORT_UNPINNED')
                raw, state = checked_bytes(path, CODE_FILE_LIMIT)
                require((len(raw), state['sha256']) == guard.hashes[name], 'IMPORT_BYTES_CHANGED')
                guard.loaded.add(name)
                return compile(raw, loader.path, 'exec', dont_inherit=True)

        class ImportBoundary:
            def find_spec(boundary, fullname, path=None, target=None):
                guard.check_import(fullname)
                if fullname.split('.')[0] not in FIRST_PARTY:
                    return None
                spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
                require(spec is not None and type(spec.origin) is str, 'FIRST_PARTY_SOURCE_ORIGIN_REQUIRED')
                origin = Path(spec.origin)
                require(origin.is_relative_to(CODE_ROOT) and origin.suffix == '.py'
                        and origin.relative_to(CODE_ROOT).as_posix() in guard.hashes
                        and type(spec.loader) is importlib.machinery.SourceFileLoader,
                        'FIRST_PARTY_SOURCE_NOT_EXACT_PIN')
                spec.loader = VerifiedSourceLoader(fullname, str(origin))
                return spec

        def guarded_open(path, flags, mode=0o777, *, dir_fd=None):
            actual = guard.path_at(path, dir_fd)
            previous, guard.call_path = guard.call_path, actual
            try:
                fd = guard.saved['open'](path, flags, mode, dir_fd=dir_fd)
            finally:
                guard.call_path = previous
            s = os.fstat(fd)
            guard.fds[fd] = (str(actual), bool(flags & (os.O_WRONLY | os.O_RDWR)), stat.S_ISDIR(s.st_mode))
            if not stat.S_ISDIR(s.st_mode):
                require(stat.S_ISREG(s.st_mode), 'GUARDED_OPEN_SPECIAL_FILE')
            return fd

        def guarded_close(fd):
            result = guard.saved['close'](fd)
            guard.fds.pop(fd, None)
            return result

        def guarded_dup(fd):
            require(fd in guard.fds, 'DUP_UNTRACKED_DESCRIPTOR')
            result = guard.saved['dup'](fd)
            guard.fds[result] = guard.fds[fd]
            return result

        def guarded_read(fd, length):
            if fd not in guard.fds:
                guard.deny('filesystem:read_untracked_descriptor')
            return guard.saved['read'](fd, length)

        def guarded_write(fd, data):
            if not guard.writable_fd(fd):
                guard.deny('filesystem:write_descriptor')
            return guard.saved['write'](fd, data)

        def guarded_fsync(fd):
            known = guard.fds.get(fd)
            if not (guard.writable_fd(fd) or (known is not None and known[2]
                    and guard.stage == 'append' and Path(known[0]).is_relative_to(guard.root))):
                guard.deny('filesystem:fsync_descriptor')
            return guard.saved['fsync'](fd)

        def guarded_pipe():
            if not guard.spawn_active or guard.child:
                guard.deny('process:unexpected_pipe')
            read_fd, write_fd = guard.saved['pipe']()
            guard.fds[read_fd] = ('<child-pipe-read>', False, False)
            guard.fds[write_fd] = ('<child-pipe-write>', True, False)
            return read_fd, write_fd

        os.open, os.close, os.dup = guarded_open, guarded_close, guarded_dup
        os.read, os.write, os.fsync, os.pipe = guarded_read, guarded_write, guarded_fsync, guarded_pipe
        sys.path.insert(0, str(CODE_ROOT))
        sys.meta_path.insert(0, ImportBoundary())
        sys.addaudithook(self.audit)

    @contextlib.contextmanager
    def phase(self, value, *, active_key=None, original_reads=False):
        old = self.stage, self.active_key, self.allow_original_reads
        self.stage, self.active_key, self.allow_original_reads = value, active_key, original_reads
        try:
            yield
        finally:
            self.stage, self.active_key, self.allow_original_reads = old

    def positive_controls(self):
        fallthroughs = []

        class LaterFinder:
            def find_spec(self, fullname, path=None, target=None):
                if fullname in IMPORT_CONTROLS:
                    fallthroughs.append(fullname)
                    raise ProofError('GUARD_CONTROL_FELL_THROUGH')
                return None

        later = LaterFinder()
        sys.meta_path.insert(1, later)
        try:
            for name in IMPORT_CONTROLS:
                require(name not in sys.modules, 'GUARD_CONTROL_PRELOADED')
                self.run_control(name, lambda name=name: importlib.import_module(name), 'import:')
                require(name not in sys.modules, 'GUARD_CONTROL_IMPORT_SUCCEEDED')
        finally:
            sys.meta_path.remove(later)
        require(not fallthroughs, 'GUARD_CONTROL_FALLTHROUGH')
        self.run_control('socket.socket', lambda: socket.socket(), 'socket.')
        self.run_control('create_outside_append', lambda: os.open(
            self.root / '.guard-must-not-create', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
            'filesystem:write_open')
        self.run_control('original_source_read', lambda: os.open(
            INPUTS['source'][0], os.O_RDONLY | os.O_NOFOLLOW), 'filesystem:read_outside_bound_files')
        require(importlib.import_module('urllib.parse').urlparse('https://example.invalid/path').path == '/path',
                'PURE_IMPORT_POSITIVE_CONTROL_FAILED')
        require(not self.unexpected, 'UNEXPECTED_PREIMPORT_GUARD_ATTEMPT')

    def run_control(self, name, callback, expected_prefix):
        count, self.control = len(self.controls), name
        try:
            callback()
        except GuardDenied:
            pass
        else:
            raise ProofError('GUARD_CONTROL_WAS_NOT_DENIED')
        finally:
            self.control = None
        require(len(self.controls) == count + 1 and self.controls[-1]['denied_event'].startswith(expected_prefix),
                'GUARD_CONTROL_WRONG_DENIAL')

    def receipt(self):
        return {
            'preimport_intentional_controls': self.controls,
            'allowed_pure_import': 'urllib.parse', 'control_fallthroughs': [],
            'unexpected_guard_attempts': self.unexpected,
            'constructor_events': self.constructor_events,
            'first_party_compiled_from_verified_bytes': sorted(self.loaded),
            'first_party_pyc_read_or_write': False,
            'factory_invoked_by_harness': False, 'test_or_fixture_imported': False,
            'original_input_file_reads_during_application_or_child': False,
            'spawned_process_observations': self.process_observations,
            'unique_permitted_file_open_paths_by_phase': {
                phase: sum(seen_phase == phase for seen_phase, _ in self.read_files)
                for phase in sorted({seen_phase for seen_phase, _ in self.read_files})},
        }


class TracedStore:
    """Delegate only the incumbent APIs; retain metadata, never object bodies."""

    def __init__(self, store, guard):
        self.store, self.guard = store, guard
        self.events, self.phase, self.expected_reference = [], 'idle', None
        self.manifest_written = False

    def key(self, value):
        require(type(value) is str and re.fullmatch(re.escape(PREFIX) +
            r'(chunks/sha256/[0-9a-f]{64}\.bin|commits/sha256/[0-9a-f]{64}\.json)', value) is not None,
            'STORE_KEY_OUT_OF_SCOPE')
        return value

    def validate_strict_conditional_write_capability(self):
        self.events.append({'phase': self.phase, 'api': 'validate_strict_conditional_write_capability'})
        return self.store.validate_strict_conditional_write_capability()

    def get_bytes_strict_bounded(self, key, *, expected_byte_length, max_byte_length):
        self.key(key)
        require(type(expected_byte_length) is int and 0 < expected_byte_length <= CHUNK_LIMIT
                and max_byte_length == CHUNK_LIMIT, 'STORE_READ_BOUND_CHANGED')
        if '/commits/' in key:
            ref = {'schema': REFERENCE_SCHEMA, 'sha256': Path(key).stem, 'byte_length': expected_byte_length}
            if self.expected_reference is None:
                self.expected_reference = ref
            require(ref == self.expected_reference, 'STORE_REFERENCE_CHANGED')
        event = {'phase': self.phase, 'api': 'get_bytes_strict_bounded', 'key': key,
                 'expected_byte_length': expected_byte_length, 'max_byte_length': max_byte_length}
        self.events.append(event)
        raw = self.store.get_bytes_strict_bounded(
            key, expected_byte_length=expected_byte_length, max_byte_length=max_byte_length)
        require(raw is None or (type(raw) is bytes and len(raw) == expected_byte_length), 'STORE_READ_PROTOCOL_CHANGED')
        event.update({'present': raw is not None, 'byte_length': len(raw) if raw is not None else None,
                      'sha256': sha(raw) if raw is not None else None})
        return raw

    def put_bytes_strict_conditional(self, key, data, *, expected_version, content_type):
        self.key(key)
        require(self.phase == 'append' and type(data) is bytes and 0 < len(data) <= CHUNK_LIMIT
                and expected_version is None and not self.manifest_written, 'STORE_WRITE_OUTSIDE_APPEND')
        final = '/commits/' in key
        require(Path(key).stem == sha(data) and content_type == (
            'application/json' if final else 'application/octet-stream'), 'STORE_WRITE_BINDING_CHANGED')
        if final:
            manifest = parse(data)
            last_put = max((i for i, row in enumerate(self.events) if row['api'] == 'put_bytes_strict_conditional'), default=-1)
            recent = self.events[last_put + 1:]
            for chunk in manifest['chunks']:
                require(any(row['api'] == 'get_bytes_strict_bounded' and row.get('present') is True
                    and row['key'] == PREFIX + 'chunks/sha256/' + chunk['sha256'] + '.bin'
                    and row['sha256'] == chunk['sha256'] and row['byte_length'] == chunk['byte_length']
                    for row in recent), 'MANIFEST_PRECOMMIT_CLOSURE_NOT_OBSERVED')
            self.expected_reference = {'schema': REFERENCE_SCHEMA, 'sha256': sha(data), 'byte_length': len(data)}
            self.manifest_written = True
        event = {'phase': self.phase, 'api': 'put_bytes_strict_conditional', 'key': key,
                 'byte_length': len(data), 'sha256': sha(data), 'expected_version': None,
                 'content_type': content_type, 'final_manifest': final}
        self.events.append(event)
        with self.guard.phase('append', active_key=key):
            result = self.store.put_bytes_strict_conditional(
                key, data, expected_version=expected_version, content_type=content_type)
        event['returned'] = result
        require(type(result) is bool, 'STORE_CONDITIONAL_RESULT_PROTOCOL_CHANGED')
        return result

    def __getattr__(self, name):
        raise ProofError('UNAPPROVED_STORE_API')


def boundary(result):
    require(result.get('admission') == 'NOT_ADMITTED' and result.get('authority') == AUTHORITY
            and result.get('graph1_projection') is None, 'AUTHORITY_BOUNDARY_CHANGED')
    if 'purpose_scope' in result:
        require(result['purpose_scope'] == {
            'operation': 'private_current_inspection', 'source_purpose_permission': 'NOT_ESTABLISHED',
            'production': False, 'public_export': False, 'training': False}, 'PURPOSE_BOUNDARY_CHANGED')
    nested = result.get('inspection')
    if nested is not None:
        boundary(nested)


def inspector_checks(current, support, historical):
    for result in (current, support, historical):
        boundary(result)
    require(current['inspection_status'] == 'INSPECTABLE' and sha(canonical(current)) == CURRENT_INSPECTION_SHA,
            'REAL_CURRENT_INSPECTION_DIGEST_CHANGED')
    require(current['support'].get('replayed_value_text') is None
            and support['support'].get('replayed_value_text') is not None, 'SUPPORT_OPT_IN_NOT_OBSERVED')
    view = current['current_candidate_view']
    require(view['assertion']['kind'] == 'product_integration' and view['assertion']['lifecycle'] == 'planned'
            and all(view[key] is None for key in ('shipments', 'revenue', 'economic_weight', 'theme_membership',
                                                  'canonical_subject_id', 'canonical_object_id')),
            'ECONOMIC_SCOPE_OR_UNKNOWN_MAGNITUDE_CHANGED')
    require(historical['inspection_status'] == 'REFUSED'
            and historical['refusal'] == {'code': 'AS_OF_DATASET_REQUIRED'}
            and all(historical[key] is None for key in ('current_candidate_view', 'source_provenance', 'support')),
            'ACTUAL_HISTORICAL_ABSTENTION_CHANGED')


def read_three(module, registry_type, store, reference):
    result = {}
    for name, options in (
        ('current', {}), ('support', {'include_support_text': True}),
        ('historical', {'as_of': HISTORY_AS_OF, 'registry': registry_type([])}),
    ):
        store.phase = 'read_' + name
        result[name] = module.read_relationship_observation(store, reference, **options)
        boundary(result[name])
    require(result['current']['status'] == 'VERIFIED'
            and result['current']['replay_status'] == 'MATCHED_SEALED_REQUEST', 'CURRENT_READ_NOT_VERIFIED')
    require(result['support']['status'] == 'VERIFIED'
            and result['support']['replay_status'] == 'CHANGED_REQUEST_NOT_SEALED_EQUALITY',
            'SUPPORT_READ_NOT_FRESH')
    history = result['historical']
    require(history['status'] == 'ABSTAINED' and history['replay_status'] == 'FRESH_REQUEST_ABSTAINED'
            and history['integrity_status'] == 'VERIFIED_COMPONENT_BYTES'
            and history['review_provenance'] is None and history['prior_observation'] is None,
            'HISTORY_LEAKS_SAVED_POSITIVE_OR_REVIEW')
    inspector_checks(*(result[name]['inspection'] for name in ('current', 'support', 'historical')))
    return result


def persisted_closure(root, reference, originals=None):
    require(type(reference) is dict and set(reference) == {'schema', 'sha256', 'byte_length'}
            and reference['schema'] == REFERENCE_SCHEMA and digest(reference['sha256'])
            and type(reference['byte_length']) is int and 0 < reference['byte_length'] <= CHUNK_LIMIT,
            'RETURNED_REFERENCE_INVALID')
    manifest_key = PREFIX + 'commits/sha256/' + reference['sha256'] + '.json'
    manifest_raw, _ = checked_bytes(root / manifest_key, CHUNK_LIMIT)
    require(len(manifest_raw) == reference['byte_length'] and sha(manifest_raw) == reference['sha256'],
            'PERSISTED_MANIFEST_REFERENCE_MISMATCH')
    manifest = parse(manifest_raw)
    require(type(manifest) is dict and set(manifest) == {
        'schema', 'producer_contract', 'package_sha256', 'package_byte_length', 'chunks'}
        and manifest['schema'] == MANIFEST_SCHEMA and manifest['producer_contract'] == CONTRACT
        and canonical(manifest) == manifest_raw, 'PERSISTED_MANIFEST_SHAPE_CHANGED')
    length, descriptors = manifest['package_byte_length'], manifest['chunks']
    require(type(length) is int and 0 < length <= PACKAGE_LIMIT and type(descriptors) is list
            and 1 <= len(descriptors) <= CHUNK_COUNT_LIMIT
            and len(descriptors) == (length + CHUNK_LIMIT - 1) // CHUNK_LIMIT,
            'PERSISTED_PACKAGE_BOUND_CHANGED')
    chunks, keys = [], {manifest_key, '.strict-conditional-write.lock'}
    for index, item in enumerate(descriptors):
        require(type(item) is dict and set(item) == {'sha256', 'byte_length'} and digest(item['sha256'])
                and type(item['byte_length']) is int
                and item['byte_length'] == min(CHUNK_LIMIT, length - index * CHUNK_LIMIT),
                'PERSISTED_CHUNK_DESCRIPTOR_INVALID')
        key = PREFIX + 'chunks/sha256/' + item['sha256'] + '.bin'
        raw, _ = checked_bytes(root / key, CHUNK_LIMIT)
        require(len(raw) == item['byte_length'] and sha(raw) == item['sha256'], 'PERSISTED_CHUNK_PIN_MISMATCH')
        chunks.append(raw)
        keys.add(key)
    payload = b''.join(chunks)
    require(len(payload) == length and sha(payload) == manifest['package_sha256'], 'PERSISTED_PACKAGE_DIGEST_MISMATCH')
    package = parse(payload)
    require(package['schema'] == PACKAGE_SCHEMA and package['producer_contract'] == CONTRACT
            and package['case_id'] == 'C01' and package['review_set_id'] == REVIEW_SET_ID
            and canonical(package) == payload, 'PERSISTED_PACKAGE_NOT_EXPECTED_CANONICAL_C01')
    require(type(package['components']) is dict and set(package['components']) == set(INPUTS),
            'PERSISTED_SEVEN_ROLES_MISMATCH')
    rows = []
    for role, (_, expected_length, expected_sha) in sorted(INPUTS.items()):
        part = package['components'][role]
        require(type(part) is dict and set(part) == {'sha256', 'byte_length', 'encoding', 'text'}
                and part['encoding'] == 'utf-8' and type(part['text']) is str, 'PERSISTED_COMPONENT_SHAPE')
        raw = part['text'].encode('utf-8')
        require(len(raw) == expected_length == part['byte_length']
                and sha(raw) == expected_sha == part['sha256'], 'PERSISTED_ORIGINAL_PIN_MISMATCH')
        if originals is not None:
            require(raw == originals[role], 'PERSISTED_ORIGINAL_BYTE_EQUALITY_FAILED')
        rows.append({'role': role, 'byte_length': len(raw), 'sha256': sha(raw)})
    boundary(package)
    require(package['inspection_request'] == {'as_of': None, 'include_support_text': False, 'registry_supplied': False}
            and package['prior_observation'] is None, 'PERSISTED_REQUEST_CHANGED')
    binding = package['review_binding']
    require(binding['scope_summary'] == {'component': '24GB 8H HBM3E',
            'target': 'NVIDIA H200 Tensor Core GPUs', 'lifecycle': 'planned', 'source_local_only': True}
            and all(binding[name] == 'NOT_AUTHENTICATED' for name in (
                'authorship', 'review_independence', 'source_custody', 'semantic_truth')),
            'RETAINED_REVIEW_SCOPE_OR_AUTHENTICATION_BOUNDARY_CHANGED')
    inventory = tree_state(root)
    actual_files = {name for name, row in inventory.items() if row['type'] == 'file'}
    require(actual_files == keys, 'UNEXPECTED_STORE_FILE_OR_LATEST_POINTER')
    lock = inventory['.strict-conditional-write.lock']
    require(lock['byte_length'] == 0, 'INCUMBENT_LOCK_NOT_EMPTY')
    return package, {'reference': reference, 'manifest_byte_length': len(manifest_raw),
                     'package_byte_length': len(payload), 'package_sha256': sha(payload),
                     'chunk_count': len(descriptors), 'unique_chunk_count': len(keys) - 2,
                     'largest_chunk_byte_length': max(map(len, chunks)), 'input_count': len(rows),
                     'exact_persisted_inputs': rows, 'regular_store_file_count': len(actual_files),
                     'latest_pointer_count': 0, 'incumbent_empty_lock_count': 1}, inventory


def actual_modules(guard):
    module = importlib.import_module('engine.company_intelligence.relationship_observations')
    inspector = importlib.import_module('engine.company_intelligence.relationship_candidates')
    store_module = importlib.import_module('engine.research_vault.r2_store')
    registry_module = importlib.import_module('lib.dataos.registry')
    require(module.inspect_candidate is inspector.inspect_candidate, 'REAL_INSPECTOR_BINDING_CHANGED')
    require(not guard.unexpected, 'UNEXPECTED_APP_IMPORT_ATTEMPT')
    return module, inspector, store_module.LocalStore, registry_module.Registry


def construct_store(local_store, guard):
    # The incumbent constructor owns the mkdir. A temporary process umask makes
    # its one new leaf private without changing the constructor or store API.
    previous_umask = os.umask(0o077) if not guard.child else None
    try:
        with guard.phase('constructor'):
            actual = local_store(guard.root)
    finally:
        if previous_umask is not None:
            os.umask(previous_umask)
    require(guard.constructor_events == [
        'existing_store_directory_mkdir' if guard.child else 'new_store_directory_mkdir'], 'CONSTRUCTOR_WITNESS_MISSING')
    real_chain(guard.root)
    require(stat.S_IMODE(guard.root.lstat().st_mode) & 0o077 == 0, 'STORE_ROOT_NOT_PRIVATE')
    return TracedStore(actual, guard)


def child_main(request):
    require(set(request) == {'source_manifest', 'source_manifest_sha256', 'harness_path',
                            'harness_sha256', 'store_root', 'reference'}, 'CHILD_REQUEST_EXTRA_INPUT')
    root = absolute(request['store_root'])
    require(root.parent == CACHE and root.name.startswith('c01-observation-'), 'CHILD_STORE_ROOT_OUT_OF_SCOPE')
    manifest, hashes, baseline = source_preflight(request)
    real_chain(root)
    guard = ExecutionGuard(request, hashes, child=True)
    guard.install()
    guard.positive_controls()
    before = tree_state(root)
    module, _, local_store, registry_type = actual_modules(guard)
    store = construct_store(local_store, guard)
    results = read_three(module, registry_type, store, request['reference'])
    package, closure, after = persisted_closure(root, request['reference'])
    require(package['inspection'] == results['current']['inspection'], 'CHILD_COMPLETE_SEALED_RESULT_MISMATCH')
    require(before == after == tree_state(root), 'CHILD_CHANGED_STORE_BYTES_OR_METADATA')
    require(states_now(baseline) == baseline, 'CHILD_CHANGED_CODE_OR_PROOF_INPUT')
    require(not guard.unexpected and not guard.mutations, 'CHILD_MUTATION_OR_UNEXPECTED_ATTEMPT')
    require(all(event['api'] == 'get_bytes_strict_bounded' for event in store.events), 'CHILD_USED_WRITE_OR_FALLBACK_API')
    return {'schema': CHILD_SCHEMA, 'status': 'PASS', 'results': results, 'closure': closure,
            'store_events': store.events, 'guard': guard.receipt(),
            'source_manifest_sha256': request['source_manifest_sha256'],
            'harness_sha256': request['harness_sha256'],
            'principal_attributed_reviewed_head': manifest['reviewed_head'],
            'store_unchanged': True, 'code_and_proof_inputs_unchanged': True,
            'original_files_required': False}


def run_child(guard, request):
    require(not guard.child, 'NESTED_CHILD_FORBIDDEN')
    raw = canonical(request)
    require(len(raw) <= 32768, 'CHILD_REQUEST_BOUND')
    environment = {'PATH': str(Path(sys.executable).parent) + ':/usr/bin:/bin',
                   'LANG': 'C', 'LC_ALL': 'C', 'PYTHONDONTWRITEBYTECODE': '1'}
    guard.spawn_active = True
    process, observation = None, None
    try:
        process = subprocess.Popen(guard.child_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, cwd=str(CODE_ROOT), env=environment, close_fds=True)
        guard.children.add(process.pid)
        observation = {'pid': process.pid, 'returncode': None, 'reconciled': False}
        guard.process_observations.append(observation)
        try:
            stdout, stderr = process.communicate(raw, timeout=60)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=10)
            return {'pid': process.pid, 'returncode': process.returncode, 'timed_out': True,
                    'stdout': stdout, 'stderr': stderr}
        return {'pid': process.pid, 'returncode': process.returncode, 'timed_out': False,
                'stdout': stdout, 'stderr': stderr}
    finally:
        try:
            if process is not None:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=10)
                observation.update(returncode=process.returncode, reconciled=process.returncode is not None)
        finally:
            guard.spawn_active = False


def public_result(row):
    return {key: row.get(key) for key in ('operation', 'status', 'reference', 'expected_reference',
                                        'integrity_status', 'replay_status', 'effect_state', 'refusal')}


def write_private(fd, raw, guard):
    require(len(raw) <= RECEIPT_LIMIT, 'PRIVATE_RECEIPT_BOUND_EXCEEDED')
    manager = guard.phase('private_receipt') if guard is not None else contextlib.nullcontext()
    with manager:
        offset = 0
        while offset < len(raw):
            count = os.write(fd, raw[offset:])
            require(count > 0, 'PRIVATE_RECEIPT_SHORT_WRITE')
            offset += count
        os.fsync(fd)


def parent_main(request, captured_streams):
    private = {'schema': PROOF_SCHEMA, 'status': 'INCOMPLETE', 'operation_id': OPERATION,
               'started_at_utc': datetime.now(timezone.utc).isoformat(), 'proof_limits': PROOF_LIMITS}
    public = {'schema': PROOF_SCHEMA, 'status': 'FAIL', 'operation_id': OPERATION,
              'automatic_retry_permitted': False, 'proof_limits': PROOF_LIMITS}
    output_fd, guard, store, failure = None, None, None, None
    try:
        private['stage'] = 'preflight'
        root, output = absolute(request['store_root']), absolute(request['private_output'])
        require(root.parent == CACHE and root.name.startswith('c01-observation-')
                and output.parent == CACHE and output.name.startswith('c01-observation-')
                and output.suffix == '.json' and root != output, 'PRIVATE_PATH_SCOPE_INVALID')
        real_chain(CACHE)
        require(not os.path.lexists(root) and not os.path.lexists(output), 'NEW_STORE_AND_OUTPUT_REQUIRED_NO_RETRY')
        manifest, hashes, baseline = source_preflight(request)
        originals, original_states = original_preflight()
        baseline.update(original_states)
        require(str(output) not in baseline and str(root) not in baseline, 'PROOF_OUTPUT_COLLISION')
        private['source_manifest'], private['immutable_before'] = manifest, baseline
        private['request_metadata'] = request
        output_fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        require(stat.S_ISREG(os.fstat(output_fd).st_mode), 'PRIVATE_OUTPUT_NOT_REGULAR')
        guard = ExecutionGuard(request, hashes, child=False, output_fd=output_fd)
        guard.install()
        guard.positive_controls()
        private['stage'] = 'actual_imports_and_direct_inspections'
        module, inspector, local_store, registry_type = actual_modules(guard)
        candidate, source = parse(originals['candidate']), originals['source'].decode('utf-8')
        direct = {
            'current': inspector.inspect_candidate(candidate, source=source),
            'support': inspector.inspect_candidate(candidate, source=source, include_support_text=True),
            'historical': inspector.inspect_candidate(candidate, source=source,
                                                       as_of=HISTORY_AS_OF, registry=registry_type([])),
        }
        private['direct_inspections'] = direct
        inspector_checks(*(direct[name] for name in ('current', 'support', 'historical')))
        require(not guard.unexpected, 'DIRECT_INSPECTION_GUARD_VIOLATION')
        store = construct_store(local_store, guard)
        require(set(tree_state(root)) == {'.'}, 'NEW_STORE_NOT_EMPTY')
        append_args = {role + '_bytes': raw for role, raw in originals.items()}
        append_args.update(review_set_id=REVIEW_SET_ID, case_id='C01')
        private['stage'], store.phase = 'append', 'append'
        committed = module.append_relationship_observation(store, **append_args)
        private['append'] = committed
        public['append'] = public_result(committed)
        require(committed['status'] == 'COMMITTED', 'APPEND_NOT_COMMITTED_STOP_NO_RETRY')
        require(not guard.unexpected, 'APPEND_UNEXPECTED_GUARD_ATTEMPT_STOP_NO_RETRY')
        require(committed['reference'] == store.expected_reference, 'APPEND_REFERENCE_WITNESS_MISMATCH')
        boundary(committed)
        require(committed['inspection'] == direct['current'], 'APPEND_COMPLETE_INSPECTION_MISMATCH')
        reference = committed['reference']
        package, closure, post_append = persisted_closure(root, reference, originals)
        require(package['inspection'] == direct['current'], 'PERSISTED_COMPLETE_INSPECTION_MISMATCH')
        private['persisted_closure'], private['store_after_append'] = closure, post_append
        writes = [row for row in store.events if row['api'] == 'put_bytes_strict_conditional']
        require(len(writes) == closure['unique_chunk_count'] + 1
                and writes[-1]['final_manifest'] is True
                and all(not row['final_manifest'] and row['returned'] is True for row in writes[:-1])
                and writes[-1]['returned'] is True, 'ACTUAL_MANIFEST_LAST_WRITE_WITNESS_FAILED')
        with guard.phase('immutable_snapshot', original_reads=True):
            require(states_now(baseline) == baseline, 'APPEND_CHANGED_ORIGINAL_OR_CODE')
        private['stage'], store.phase = 'repeat_no_writes', 'repeat'
        before_events, before_mutations = len(store.events), len(guard.mutations)
        repeated = module.append_relationship_observation(store, **append_args)
        private['repeat'] = repeated
        public['repeat'] = public_result(repeated)
        require(repeated['status'] == 'REPEATED', 'ACTUAL_REPEAT_NOT_REPEATED')
        require({**committed, 'status': 'REPEATED'} == repeated, 'COMPLETE_REPEAT_RESULT_CHANGED')
        require(all(row['api'] != 'put_bytes_strict_conditional' for row in store.events[before_events:])
                and len(guard.mutations) == before_mutations and tree_state(root) == post_append,
                'REPEAT_CHANGED_STORE_OR_WROTE')
        with guard.phase('immutable_snapshot', original_reads=True):
            require(states_now(baseline) == baseline, 'REPEAT_CHANGED_ORIGINAL_OR_CODE')
        private['stage'] = 'actual_current_support_historical_reads'
        reads = read_three(module, registry_type, store, reference)
        private['reads'] = reads
        for name in direct:
            require(reads[name]['inspection'] == direct[name], 'COMPLETE_ACTUAL_INSPECTOR_COMPARISON_FAILED')
        require(reads['current']['review_provenance'] == committed['review_provenance']
                and reads['support']['review_provenance'] == committed['review_provenance'],
                'FRESH_READ_REVIEW_PROVENANCE_CHANGED')
        require(tree_state(root) == post_append and len(guard.mutations) == before_mutations,
                'READ_CHANGED_STORE_OR_WROTE')
        with guard.phase('immutable_snapshot', original_reads=True):
            require(states_now(baseline) == baseline, 'READ_CHANGED_ORIGINAL_OR_CODE')
        private['stage'] = 'two_fresh_store_only_processes'
        child_request = {key: request[key] for key in (
            'source_manifest', 'source_manifest_sha256', 'harness_path', 'harness_sha256', 'store_root')}
        child_request['reference'] = reference
        private['child_request'] = child_request
        runs = []
        private['child_processes'] = runs
        for _ in range(2):
            run = run_child(guard, child_request)
            require(len(run['stdout']) <= RECEIPT_LIMIT and len(run['stderr']) <= 65536, 'CHILD_OUTPUT_LIMIT')
            record = {key: run[key] for key in ('pid', 'returncode', 'timed_out')}
            record.update(stdout_byte_length=len(run['stdout']), stdout_sha256=sha(run['stdout']),
                          stdout_text=run['stdout'].decode('utf-8', 'replace'),
                          stderr_byte_length=len(run['stderr']), stderr_sha256=sha(run['stderr']),
                          stderr_text=run['stderr'].decode('utf-8', 'replace'))
            runs.append(record)
            require(not run['timed_out'] and run['returncode'] == 0 and run['stderr'] == b'', 'FRESH_CHILD_FAILED')
            child = parse(run['stdout'])
            require(child['status'] == 'PASS' and child['schema'] == CHILD_SCHEMA
                    and child['results'] == reads and child['closure'] == closure, 'FRESH_CHILD_COMPLETE_RESULT_MISMATCH')
            require(not child['guard']['unexpected_guard_attempts'], 'FRESH_CHILD_GUARD_ATTEMPT')
            require(tree_state(root) == post_append, 'CHILD_CHANGED_PARENT_STORE_SNAPSHOT')
        require(runs[0]['pid'] != runs[1]['pid'] and runs[0]['stdout_text'] == runs[1]['stdout_text']
                and runs[0]['stdout_sha256'] == runs[1]['stdout_sha256'], 'FRESH_PROCESSES_NOT_BYTE_IDENTICAL')
        with guard.phase('immutable_snapshot', original_reads=True):
            final_states = states_now(baseline)
            require(final_states == baseline, 'FINAL_ORIGINAL_CODE_OR_PROOF_INPUT_CHANGED')
        require(tree_state(root) == post_append and len(guard.mutations) == before_mutations
                and not guard.unexpected, 'FINAL_STORE_OR_GUARD_VIOLATION')
        private['immutable_after'] = final_states
        private['stage'], private['status'] = 'complete', 'PASS'
        public.update(status='PASS', reference=reference, persisted_closure=closure,
                      complete_current_inspection_sha256=sha(canonical(direct['current'])),
                      complete_support_inspection_sha256=sha(canonical(direct['support'])),
                      complete_historical_inspection_sha256=sha(canonical(direct['historical'])),
                      historical_status='ABSTAINED', historical_reason='AS_OF_DATASET_REQUIRED',
                      historical_saved_positive_or_review_released=False,
                      seven_originals_code_and_proof_inputs_unchanged=True,
                      store_unchanged_after_append_through_repeat_reads_and_children=True,
                      actual_conditional_write_count=len(writes), actual_manifest_write_count=1,
                      repeat_conditional_write_count=0, read_conditional_write_count=0,
                      fresh_process_count=2, fresh_processes_byte_identical=True,
                      fresh_process_output_sha256=runs[0]['stdout_sha256'],
                      fresh_processes=[{key: row[key] for key in (
                          'pid', 'returncode', 'timed_out', 'stdout_byte_length', 'stdout_sha256',
                          'stderr_byte_length', 'stderr_sha256')} for row in runs],
                      source_manifest_sha256=request['source_manifest_sha256'],
                      harness_sha256=request['harness_sha256'],
                      principal_attributed_reviewed_head=manifest['reviewed_head'],
                      principal_attributed_source_phase=manifest['phase'])
    except BaseException as exc:
        failure = str(exc) if isinstance(exc, ProofError) else 'UNEXPECTED_HARNESS_EXCEPTION'
        private.update(status='FAIL', failure_code=failure, exception_type=type(exc).__name__)
        public.update(status='FAIL', failure_code=failure, failed_stage=private.get('stage'),
                      expected_reference=store.expected_reference if store is not None else None,
                      operator_action='Reconcile the exact expected reference and private receipt before any further modifying attempt.')
    finally:
        if store is not None:
            private['store_events'] = store.events
            private['expected_reference'] = store.expected_reference
        if guard is not None:
            private['guard'], private['filesystem_mutation_events'] = guard.receipt(), guard.mutations
            private['permitted_file_open_paths_by_phase'] = [
                {'phase': phase, 'path': path} for phase, path in sorted(guard.read_files)]
            public['guard'] = guard.receipt()
        captured = {name: stream.getvalue() for name, stream in captured_streams.items()}
        private['captured_application_stdio'] = captured
        public['captured_application_stdio'] = {
            name: {'byte_length': len(value.encode('utf-8')), 'sha256': sha(value.encode('utf-8'))}
            for name, value in captured.items()}
        if any(captured.values()):
            private.update(status='FAIL', failure_code='UNEXPECTED_APPLICATION_STDIO')
            public.update(status='FAIL', failure_code='UNEXPECTED_APPLICATION_STDIO',
                          expected_reference=store.expected_reference if store is not None else None)
        private['finished_at_utc'] = datetime.now(timezone.utc).isoformat()
        if output_fd is not None:
            try:
                encoded = canonical(private) + b'\n'
                write_private(output_fd, encoded, guard)
                os.close(output_fd)
                output_fd = None
                with guard.phase('private_receipt') if guard is not None else contextlib.nullcontext():
                    observed, _ = checked_bytes(Path(request['private_output']), RECEIPT_LIMIT)
                require(observed == encoded, 'PRIVATE_RECEIPT_READBACK_MISMATCH')
                public['private_receipt'] = {'path': request['private_output'], 'byte_length': len(encoded),
                                             'sha256': sha(encoded), 'verified_readback': True}
            except BaseException:
                public.update(status='FAIL', private_receipt_error='EXCLUSIVE_PRIVATE_RECEIPT_NOT_PROVEN')
                if output_fd is not None:
                    try:
                        os.close(output_fd)
                    except BaseException:
                        pass
        else:
            public['private_receipt'] = None
    return public


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--child', action='store_true', help=argparse.SUPPRESS)
    for flag in ('source-manifest', 'source-manifest-sha256', 'harness-sha256', 'store-root', 'private-output'):
        parser.add_argument('--' + flag)
    args = parser.parse_args()
    if args.child:
        try:
            raw = sys.stdin.buffer.read(32769)
            require(len(raw) <= 32768, 'CHILD_REQUEST_TOO_LARGE')
            result = child_main(parse(raw))
        except BaseException as exc:
            result = {'schema': CHILD_SCHEMA, 'status': 'FAIL',
                      'failure_code': str(exc) if isinstance(exc, ProofError) else 'UNEXPECTED_CHILD_EXCEPTION',
                      'exception_type': type(exc).__name__}
        # This private full result is consumed only by the parent pipe.
        sys.stdout.buffer.write(canonical(result) + b'\n')
        return 0 if result['status'] == 'PASS' else 2
    require(all(getattr(args, name) for name in (
        'source_manifest', 'source_manifest_sha256', 'harness_sha256', 'store_root', 'private_output')),
        'REQUIRED_PRINCIPAL_ARGUMENT_MISSING')
    request = {name: getattr(args, name) for name in (
        'source_manifest', 'source_manifest_sha256', 'harness_sha256', 'store_root', 'private_output')}
    request['harness_path'] = os.path.abspath(__file__)
    captured = {'stdout': io.StringIO(), 'stderr': io.StringIO()}
    with contextlib.redirect_stdout(captured['stdout']), contextlib.redirect_stderr(captured['stderr']):
        result = parent_main(request, captured)
    sys.stdout.buffer.write(canonical(result) + b'\n')
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
