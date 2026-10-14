"""Fixed canary bootstrap. Imported by the exact root-reviewed stdin carrier.

No default execution, shell, privilege escalation, host selection or retry.
Existing-root credentials are neither discovered nor copied. Payload bytes are
integrity-bound by a separately embedded expected capsule hash, not authority.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import sys
import time
import types

ROOT = '01a1333c-a475-7052-95a8-72a88eb8c17b'
BASE = Path('/var/lib/mastermind/rf-canary-01a1333c-v4')
FILES = frozenset({'runsc_install.py', 'qualification_smoke.py',
    'qualification_runsc_smoke.py', 'fixed_smoke_probe.py', 'transport.py',
    'qualification_manifest.py', 'cli29_anonymous_config.py', 'phase_budget.py',
    'pinned_archive_phase.py', 'image_preparation_gate.py', 'fixed_image_phase.py',
    'fixed_canary.py'})


class BootstrapRefused(ValueError):
    pass


def _check(ok, reason):
    if not ok:
        raise BootstrapRefused(reason)


def _pairs(pairs):
    doc = {}
    for key, value in pairs:
        _check(key not in doc, 'duplicate_key')
        doc[key] = value
    return doc


def decode(capsule, expected_sha):
    _check(type(capsule) is bytes and 0 < len(capsule) <= 500000, 'capsule_bound')
    _check(hashlib.sha256(capsule).hexdigest() == expected_sha, 'capsule_sha256')
    doc = json.loads(capsule, object_pairs_hook=_pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(BootstrapRefused('nonfinite')))
    _check(type(doc) is dict and set(doc) == {'schema','root','files'}, 'capsule_fields')
    _check(doc['schema'] == 'rf.fixed_canary_capsule.v2' and doc['root'] == ROOT, 'capsule_identity')
    _check(type(doc['files']) is dict and set(doc['files']) == FILES, 'source_set')
    result, total = {}, 0
    for name, record in doc['files'].items():
        _check(type(record) is dict and set(record) == {'size','sha256','base64'}, 'file_fields')
        _check(type(record['size']) is int and 0 < record['size'] <= 125000, 'file_size')
        data = base64.b64decode(record['base64'], validate=True)
        _check(len(data) == record['size'] and hashlib.sha256(data).hexdigest() == record['sha256'],
               'file_integrity')
        total += len(data)
        _check(total <= 350000, 'source_total')
        compile(data, name, 'exec')  # Reject incomplete source before writes.
        result[name] = data
    return result


def safe_dir(path, mode=None):
    m = path.lstat()
    _check(stat.S_ISDIR(m.st_mode) and m.st_uid == m.st_gid == 0
           and not stat.S_IMODE(m.st_mode) & 0o022, 'unsafe_directory')
    if mode is not None:
        _check(stat.S_IMODE(m.st_mode) == mode, 'directory_mode')


def _new_file(path, data, checkpoint):
    checkpoint()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        rest = memoryview(data)
        while rest:
            checkpoint(); n = os.write(fd, rest)
            _check(type(n) is int and 0 < n <= len(rest), 'write_progress')
            rest = rest[n:]
        checkpoint(); os.fsync(fd)
    finally:
        os.close(fd)


def bootstrap(capsule, capsule_sha, commission_sha, *, clock=time.monotonic):
    start = clock()
    files = decode(capsule, capsule_sha)
    _check(os.geteuid() == 0 and platform.system() == 'Linux'
           and platform.machine() == 'x86_64', 'privileged_platform')
    _check(type(commission_sha) is str and len(commission_sha) == 64
           and set(commission_sha) <= set('0123456789abcdef'), 'commission_digest')
    module = types.ModuleType('phase_budget')
    exec(compile(files['phase_budget.py'], 'phase_budget.py', 'exec'), module.__dict__)
    # Include decoding/bootstrap time in the original immutable start.
    first = True
    def original_clock():
        nonlocal first
        if first:
            first = False
            return start
        return clock()
    budget = module.QualificationBudget(original_clock)
    def checkpoint():
        _check(not budget.snapshot().frozen, 'overall_deadline')
    checkpoint()
    for parent in (Path('/'), Path('/var'), Path('/var/lib')):
        safe_dir(parent)
    parent = BASE.parent
    try:
        safe_dir(parent)
    except FileNotFoundError:
        checkpoint(); os.mkdir(parent, 0o700); safe_dir(parent, 0o700)
    # Exclusive directory creation is persistent local replay evidence. An
    # existing partial directory is never adopted, erased, renamed or retried.
    checkpoint(); os.mkdir(BASE, 0o700); safe_dir(BASE, 0o700)
    for name in ('source', 'work'):
        checkpoint(); os.mkdir(BASE / name, 0o700); safe_dir(BASE / name, 0o700)
    for name, data in files.items():
        _new_file(BASE / 'source' / name, data, checkpoint)
    checkpoint()
    fd = os.open(BASE / 'source', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    for name, data in files.items():
        checkpoint()
        path = BASE / 'source' / name
        meta = path.lstat()
        _check(stat.S_ISREG(meta.st_mode) and meta.st_uid == meta.st_gid == 0
               and stat.S_IMODE(meta.st_mode) == 0o600 and meta.st_size == len(data), 'source_metadata')
        _check(path.read_bytes() == data, 'source_readback')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(BASE / 'source'))
    sys.modules['phase_budget'] = module
    import fixed_canary
    return fixed_canary.execute(str(BASE / 'source'), str(BASE / 'work'), budget, commission_sha)
