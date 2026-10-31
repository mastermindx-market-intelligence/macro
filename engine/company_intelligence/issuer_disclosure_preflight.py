"""Same-process producer preflight gate; stdlib only.

Fail-closed Linux qualification immediately before exclusive reservation.
On-disk module hashes are provenance under a fresh trusted interpreter and a
parent-filled qualified deployment; they are not exhaustive loaded-code
attestation. Mount rw metadata does not promise a later write will succeed.
F04 retains API read-only/hidden-publisher evidence. exec(2) may preserve
PID/starttime/namespace; wrappers are not rejected on that identity alone.
"""
from __future__ import annotations

import errno
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from . import issuer_disclosures as native

EXPECTED_SCHEMA = 'company_intelligence.expected_deployment/v1'
CENSUS_SCHEMA = 'company_intelligence.f04_api_census/v1'
EVIDENCE_SCHEMA = 'company_intelligence.producer_preflight_evidence/v1'
PRODUCTION_ROOT = Path('/var/lib/macro-company-intelligence')
CENSUS_MAX_AGE_LIMIT = 300
MAX_DEPLOYMENT_BYTES = 16 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024
MAX_PROC_BYTES = 1024 * 1024
MODULE_NAMES = (
    'engine.company_intelligence.issuer_disclosures',
    'engine.company_intelligence.issuer_disclosure_owner',
    'engine.company_intelligence.issuer_disclosure_publication',
    'engine.company_intelligence.issuer_disclosure_preflight',
    'engine.company_intelligence.current_context_runtime',
    'scripts.publish_company_disclosure',
)
APPEND_MODULE_NAMES = (
    'engine.company_intelligence.sec_supplier_adoption',
    'engine.fundamental_forensics.filing_attestation',
    'engine.fundamental_forensics.source_sync',
    'engine.fundamental_forensics.sec_document_spine',
    'engine.fundamental_forensics.models',
    'engine.research_vault.r2_store',
)
ROOT_KEYS = ('.', 'state', 'state/generations', 'artifacts', 'publisher',
             'publisher/source', 'publisher/operations')
WRITE_ROOTS = ROOT_KEYS
_OID = re.compile(r'[0-9a-f]{40}\Z')
_SHA = re.compile(r'[0-9a-f]{64}\Z')
_NS = re.compile(r'mnt:\[\d+\]\Z')
_UNIT = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:@-]{0,255}\Z')
_INVOC = re.compile(r'(?:[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\Z')
_MODE = frozenset({'STAGE_MEMBERS', 'PROMOTE_CURRENT', 'APPEND_CURRENT_MEMBER'})
_SYS_KEYS = frozenset({'MainPID', 'InvocationID', 'ControlGroup', 'Id'})


def evidence_bytes(value: dict) -> bytes:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                         allow_nan=False).encode()
    except (TypeError, ValueError, UnicodeError):
        raise native.DisclosureError('PREFLIGHT_JSON_INVALID') from None
    native._require(0 < len(raw) <= MAX_EVIDENCE_BYTES, 'PREFLIGHT_EVIDENCE_INVALID')
    return raw


def evidence_digest(value: dict) -> str:
    return hashlib.sha256(evidence_bytes(value)).hexdigest()


def refuse_payload(code: str, *, effect_unknown: bool = False) -> dict:
    payload = {'state': 'RECONCILIATION_REQUIRED' if effect_unknown else 'REFUSED',
               'error_code': code, 'automatic_retry_permitted': False}
    if effect_unknown:
        payload['effect_unknown'] = True
    return payload


def open_directory(path) -> int:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open('/', flags)
    try:
        for part in Path(os.path.abspath(path)).parts[1:]:
            next_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def parse_stat_starttime(text: str) -> int:
    """Field 22; comm may contain spaces and parentheses."""
    native._require(type(text) is str and text, 'PREFLIGHT_PROCESS_INVALID')
    close = text.rfind(')')
    native._require(close > 0 and text.find('(') != -1, 'PREFLIGHT_PROCESS_INVALID')
    fields = text[close + 1:].split()
    native._require(len(fields) >= 20, 'PREFLIGHT_PROCESS_INVALID')
    try:
        starttime = int(fields[19])
    except (TypeError, ValueError):
        raise native.DisclosureError('PREFLIGHT_PROCESS_INVALID') from None
    native._require(starttime >= 0, 'PREFLIGHT_PROCESS_INVALID')
    return starttime


def unescape_mount(value: str) -> str:
    native._require(type(value) is str, 'PREFLIGHT_MOUNT_INVALID')

    def _octal(match):
        return chr(int(match.group(1), 8))

    return re.sub(r'\\([0-7]{3})', _octal, value)


def parse_mountinfo(text: str) -> list:
    native._require(type(text) is str and text, 'PREFLIGHT_MOUNT_INVALID')
    mounts = []
    for line in text.splitlines():
        if not line:
            continue
        left, sep, right = line.partition(' - ')
        native._require(sep == ' - ' and left and right, 'PREFLIGHT_MOUNT_INVALID')
        fields = left.split()
        filesystem = right.split()
        native._require(len(fields) >= 6 and len(filesystem) >= 3, 'PREFLIGHT_MOUNT_INVALID')
        mounts.append({
            'mount_id': fields[0],
            'parent_id': fields[1],
            'dev': fields[2],
            'root': unescape_mount(fields[3]),
            'mountpoint': unescape_mount(fields[4]),
            'options': fields[5],
            'super_options': filesystem[2],
        })
    native._require(mounts, 'PREFLIGHT_MOUNT_INVALID')
    return mounts


def covering_mount(mounts: list, path: str) -> dict | None:
    path = os.path.abspath(path)
    best = None
    for mount in mounts:
        point = mount['mountpoint']
        if point == '/' or path == point or path.startswith(point.rstrip('/') + '/'):
            if best is None or len(point) > len(best['mountpoint']):
                best = mount
    return best


def _abs_path(value: object) -> str:
    native._require(type(value) is str and value.startswith('/') and '\x00' not in value
                    and len(value) <= 4096, 'PREFLIGHT_DEPLOYMENT_INVALID')
    parts = Path(value).parts
    native._require('..' not in parts and all(p != '.' for p in parts[1:]), 'PREFLIGHT_DEPLOYMENT_INVALID')
    return value


def _int(value: object, minimum: int, maximum: int, code: str = 'PREFLIGHT_DEPLOYMENT_INVALID') -> int:
    native._require(type(value) is int and not isinstance(value, bool)
                    and minimum <= value <= maximum, code)
    return value


def census_identity(census: dict) -> dict:
    return {key: census[key] for key in (
        'schema', 'captured_at', 'pid', 'starttime', 'mountnamespace', 'cgroup',
        'unit', 'invocation_id', 'qualified_runtime_source')}


def census_digest(census: dict) -> str:
    return hashlib.sha256(evidence_bytes(census_identity(census))).hexdigest()


def validate_expected_deployment(value: object) -> dict:
    native._require(type(value) is dict, 'PREFLIGHT_DEPLOYMENT_INVALID')
    native._closed(value, {'schema', 'code_version', 'mode', 'root', 'producer',
                           'api_census', 'census_max_age_seconds'})
    native._require(value['schema'] == EXPECTED_SCHEMA, 'PREFLIGHT_DEPLOYMENT_INVALID')
    native._require(type(value['code_version']) is str and _OID.fullmatch(value['code_version']),
                    'PREFLIGHT_DEPLOYMENT_INVALID')
    native._require(type(value['mode']) is str and value['mode'] in _MODE,
                    'PREFLIGHT_DEPLOYMENT_INVALID')
    native._require(value['root'] == str(PRODUCTION_ROOT), 'PREFLIGHT_DEPLOYMENT_ROOT')
    producer = native._closed(value['producer'], {'uid', 'repo'})
    _int(producer['uid'], 0, 2 ** 31 - 1)
    _abs_path(producer['repo'])
    _int(value['census_max_age_seconds'], 1, CENSUS_MAX_AGE_LIMIT)
    census = native._closed(value['api_census'], {
        'schema', 'captured_at', 'pid', 'starttime', 'mountnamespace', 'cgroup',
        'unit', 'invocation_id', 'qualified_runtime_source', 'digests'})
    native._require(census['schema'] == CENSUS_SCHEMA, 'PREFLIGHT_DEPLOYMENT_INVALID')
    native._instant(census['captured_at'])
    _int(census['pid'], 1, 2 ** 31 - 1)
    _int(census['starttime'], 0, 2 ** 63 - 1)
    native._require(type(census['mountnamespace']) is str and _NS.fullmatch(census['mountnamespace']),
                    'PREFLIGHT_DEPLOYMENT_INVALID')
    native._require(type(census['cgroup']) is str and census['cgroup'].startswith('/')
                    and 1 < len(census['cgroup']) <= 512 and '\x00' not in census['cgroup'],
                    'PREFLIGHT_DEPLOYMENT_INVALID')
    native._require(type(census['unit']) is str and _UNIT.fullmatch(census['unit']),
                    'PREFLIGHT_DEPLOYMENT_INVALID')
    native._require(type(census['invocation_id']) is str and _INVOC.fullmatch(census['invocation_id']),
                    'PREFLIGHT_DEPLOYMENT_INVALID')
    source = native._closed(census['qualified_runtime_source'],
                            {'code_version', 'repo', 'attestation_sha256'})
    native._require(type(source['code_version']) is str and _OID.fullmatch(source['code_version'])
                    and source['code_version'] == value['code_version'], 'PREFLIGHT_API_SOURCE')
    _abs_path(source['repo'])
    native._require(type(source['attestation_sha256']) is str
                    and _SHA.fullmatch(source['attestation_sha256']), 'PREFLIGHT_API_SOURCE')
    digests = native._closed(census['digests'], {'census_sha256'})
    native._require(type(digests['census_sha256']) is str and _SHA.fullmatch(digests['census_sha256'])
                    and digests['census_sha256'] == census_digest(census), 'PREFLIGHT_DEPLOYMENT_INVALID')
    return value


def load_expected_deployment(path, *, reader=None) -> dict:
    raw = reader(path) if reader is not None else _read_regular(path, MAX_DEPLOYMENT_BYTES)
    try:
        value = json.loads(raw, object_pairs_hook=native._pairs,
                           parse_constant=lambda *_: native._require(False, 'PREFLIGHT_JSON_INVALID'))
    except native.DisclosureError:
        raise native.DisclosureError('PREFLIGHT_JSON_INVALID') from None
    except (ValueError, UnicodeError, RecursionError, TypeError):
        raise native.DisclosureError('PREFLIGHT_JSON_INVALID') from None
    native._require(type(value) is dict, 'PREFLIGHT_JSON_INVALID')
    return validate_expected_deployment(value)


def _read_regular(path, maximum: int) -> bytes:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptors = [os.open('/', flags)]
    try:
        parts = Path(os.path.abspath(path)).parts
        native._require(len(parts) >= 2, 'PREFLIGHT_DEPLOYMENT_INVALID')
        for part in parts[1:-1]:
            descriptors.append(os.open(part, flags, dir_fd=descriptors[-1]))
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptors[-1])
        descriptors.append(fd)
        before = os.fstat(fd)
        native._require(stat.S_ISREG(before.st_mode) and 0 < before.st_size <= maximum,
                        'PREFLIGHT_DEPLOYMENT_INVALID')
        raw = bytearray()
        while len(raw) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(fd)
        native._require(len(raw) == before.st_size == after.st_size, 'PREFLIGHT_DEPLOYMENT_INVALID')
        return bytes(raw)
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def read_proc_text(path: str, maximum: int = MAX_PROC_BYTES) -> str:
    native._require(type(path) is str and path.startswith('/proc/') and '..' not in path.split('/'),
                    'PREFLIGHT_PROCESS_INVALID')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        raw = bytearray()
        while len(raw) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        native._require(0 < len(raw) <= maximum, 'PREFLIGHT_PROCESS_INVALID')
        return bytes(raw).decode()
    finally:
        os.close(fd)


def read_process_identity(pid='self', *, stat_text=None, exe=None, cwd=None,
                          mountnamespace=None, uid=None) -> dict:
    label = 'self' if pid == 'self' else str(_int(pid, 1, 2 ** 31 - 1, 'PREFLIGHT_PROCESS_INVALID'))
    base = '/proc/' + label
    if stat_text is None:
        stat_text = read_proc_text(base + '/stat')
    starttime = parse_stat_starttime(stat_text)
    if exe is None:
        exe = os.readlink(base + '/exe')
    if cwd is None:
        cwd = os.readlink(base + '/cwd')
    if mountnamespace is None:
        mountnamespace = os.readlink(base + '/ns/mnt')
    if uid is None:
        uid = os.geteuid() if label == 'self' else os.stat(base).st_uid
    native._require(type(exe) is str and type(cwd) is str and type(mountnamespace) is str
                    and _NS.fullmatch(mountnamespace) and type(uid) is int, 'PREFLIGHT_PROCESS_INVALID')
    live_pid = os.getpid() if label == 'self' else int(label)
    return {'pid': live_pid, 'starttime': starttime, 'uid': uid, 'exe': exe, 'cwd': cwd,
            'mountnamespace': mountnamespace}


def read_mountinfo(text: str | None = None) -> list:
    if text is None:
        text = read_proc_text('/proc/self/mountinfo')
    return parse_mountinfo(text)


def parse_cgroup(text: str) -> str:
    native._require(type(text) is str and text, 'PREFLIGHT_API_CGROUP')
    path = None
    for line in text.splitlines():
        if not line:
            continue
        parts = line.split(':', 2)
        native._require(len(parts) == 3, 'PREFLIGHT_API_CGROUP')
        path = parts[2]
    native._require(type(path) is str and path.startswith('/') and '\x00' not in path,
                    'PREFLIGHT_API_CGROUP')
    return path


def cgroup_covered(live: str, expected: str) -> bool:
    native._require(type(live) is str and type(expected) is str, 'PREFLIGHT_API_CGROUP')
    if not live.startswith('/'):
        live = '/' + live
    if not expected.startswith('/'):
        expected = '/' + expected
    return live == expected or live.startswith(expected.rstrip('/') + '/')


def parse_systemctl_show(text: str) -> dict:
    native._require(type(text) is str and text, 'PREFLIGHT_API_UNIT')
    result = {}
    for line in text.splitlines():
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        native._require(sep == '=', 'PREFLIGHT_API_UNIT')
        if key in _SYS_KEYS:
            native._require(key not in result, 'PREFLIGHT_API_UNIT')
            result[key] = value
    native._require(set(result) == _SYS_KEYS, 'PREFLIGHT_API_UNIT')
    try:
        pid = int(result['MainPID'])
    except (TypeError, ValueError):
        raise native.DisclosureError('PREFLIGHT_API_PID') from None
    native._require(type(pid) is int and pid >= 1, 'PREFLIGHT_API_PID')
    native._require(type(result['InvocationID']) is str and _INVOC.fullmatch(result['InvocationID']),
                    'PREFLIGHT_API_INVOCATION')
    native._require(type(result['Id']) is str and _UNIT.fullmatch(result['Id']), 'PREFLIGHT_API_UNIT')
    native._require(type(result['ControlGroup']) is str and result['ControlGroup'].startswith('/'),
                    'PREFLIGHT_API_CGROUP')
    result['MainPID'] = pid
    return result


def systemctl_show(unit: str, *, runner=None) -> dict:
    native._require(type(unit) is str and _UNIT.fullmatch(unit), 'PREFLIGHT_API_UNIT')
    if runner is None:
        env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C'}
        try:
            completed = subprocess.run(
                ['systemctl', 'show', unit, '--property=MainPID', '--property=InvocationID',
                 '--property=ControlGroup', '--property=Id'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3, check=True, env=env)
        except (OSError, subprocess.SubprocessError):
            raise native.DisclosureError('PREFLIGHT_API_UNIT') from None
        text = completed.stdout.decode()
    else:
        text = runner(unit)
    return parse_systemctl_show(text)


def revalidate_api_census(census: dict, *, stat_text=None, mountnamespace=None,
                          cgroup_text=None, unit_properties=None) -> dict:
    pid = census['pid']
    try:
        if stat_text is None:
            stat_text = read_proc_text(f'/proc/{pid}/stat')
        starttime = parse_stat_starttime(stat_text)
    except (FileNotFoundError, ProcessLookupError, OSError):
        raise native.DisclosureError('PREFLIGHT_API_PID') from None
    native._require(starttime == census['starttime'], 'PREFLIGHT_API_STARTTIME')
    try:
        if mountnamespace is None:
            mountnamespace = os.readlink(f'/proc/{pid}/ns/mnt')
    except (FileNotFoundError, OSError):
        raise native.DisclosureError('PREFLIGHT_API_NAMESPACE') from None
    native._require(mountnamespace == census['mountnamespace'], 'PREFLIGHT_API_NAMESPACE')
    try:
        if cgroup_text is None:
            cgroup_text = read_proc_text(f'/proc/{pid}/cgroup')
        live_cg = parse_cgroup(cgroup_text)
    except (FileNotFoundError, OSError):
        raise native.DisclosureError('PREFLIGHT_API_CGROUP') from None
    native._require(cgroup_covered(live_cg, census['cgroup']), 'PREFLIGHT_API_CGROUP')
    if unit_properties is None:
        unit_properties = systemctl_show(census['unit'])
    else:
        unit_properties = parse_systemctl_show(unit_properties) if type(unit_properties) is str else unit_properties
    native._require(unit_properties['MainPID'] == census['pid'], 'PREFLIGHT_API_PID')
    native._require(unit_properties['InvocationID'] == census['invocation_id'], 'PREFLIGHT_API_INVOCATION')
    native._require(unit_properties['Id'] == census['unit'], 'PREFLIGHT_API_UNIT')
    native._require(cgroup_covered(unit_properties['ControlGroup'], census['cgroup']), 'PREFLIGHT_API_CGROUP')
    return {
        'pid': census['pid'], 'starttime': starttime, 'mountnamespace': mountnamespace,
        'cgroup': live_cg, 'unit': census['unit'], 'invocation_id': census['invocation_id'],
        'qualified_runtime_source': census['qualified_runtime_source'],
    }


def evaluate_census_time(expected: dict, invocation_at: str, now: str) -> None:
    captured = native._instant(expected['api_census']['captured_at'])
    invoked = native._instant(invocation_at)
    present = native._instant(now)
    native._require(captured <= present, 'PREFLIGHT_CENSUS_FUTURE')
    native._require(captured <= invoked <= present, 'PREFLIGHT_CENSUS_AFTER_INVOCATION')
    age = (present - captured).total_seconds()
    native._require(age <= expected['census_max_age_seconds'], 'PREFLIGHT_CENSUS_STALE')


def _write_options(options: str) -> None:
    tokens = options.split(',')
    native._require('rw' in tokens and 'ro' not in tokens, 'PREFLIGHT_MOUNT_RO')


def descriptor_mount_id(fd: int) -> str:
    """Linux binds an opened descriptor to one mount even at stacked paths."""
    text = read_proc_text(f'/proc/self/fdinfo/{fd}')
    ids = re.findall(r'^mnt_id:\s*([0-9]+)\s*$', text, re.MULTILINE)
    native._require(len(ids) == 1, 'PREFLIGHT_MOUNT_ID')
    return ids[0]


def exact_mount(mounts: list, mount_id: str) -> dict:
    found = [mount for mount in mounts if mount['mount_id'] == mount_id]
    native._require(len(found) == 1, 'PREFLIGHT_MOUNT_ID')
    return found[0]


def qualify_roots(root, uid: int, mounts: list) -> dict:
    native._require(Path(os.path.abspath(root)) == Path(os.path.abspath(PRODUCTION_ROOT)),
                    'PREFLIGHT_DEPLOYMENT_ROOT')
    records = {}
    for key in ROOT_KEYS:
        path = Path(root) / key
        try:
            fd = open_directory(path)
        except FileNotFoundError:
            raise native.DisclosureError('PREFLIGHT_ROOT_MISSING') from None
        except OSError as exc:
            if exc.errno in (errno.ELOOP, errno.ENOTDIR):
                raise native.DisclosureError('PREFLIGHT_ROOT_SYMLINK') from None
            raise native.DisclosureError('PREFLIGHT_ROOT_MISSING') from None
        try:
            info = os.fstat(fd)
            native._require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700,
                            'PREFLIGHT_ROOT_MODE')
            native._require(info.st_uid == uid, 'PREFLIGHT_PRODUCER_UID')
            mount_id = descriptor_mount_id(fd)
            mount = exact_mount(mounts, mount_id)
            if key in WRITE_ROOTS:
                _write_options(mount['options'])
                _write_options(mount['super_options'])
            records[key] = {'device': info.st_dev, 'inode': info.st_ino,
                            'uid': info.st_uid, 'gid': info.st_gid,
                            'mode': stat.S_IMODE(info.st_mode),
                            'mount_id': mount_id}
        finally:
            os.close(fd)
    return records


def operation_names_absent(root, operation_id: str) -> None:
    fd = open_directory(Path(root) / 'publisher/operations')
    try:
        for suffix, code in (('.json', 'PREFLIGHT_OPERATION_EXISTS'),
                             ('.result.json', 'PREFLIGHT_OUTCOME_EXISTS')):
            try:
                probe = os.open(operation_id + suffix,
                                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            except FileNotFoundError:
                continue
            os.close(probe)
            raise native.DisclosureError(code)
    finally:
        os.close(fd)


def repo_relative(repo, file_path: str) -> str:
    repo_abs = os.path.abspath(repo)
    file_abs = os.path.abspath(file_path)
    native._require(file_abs.startswith(repo_abs + os.sep), 'PREFLIGHT_MODULE_ORIGIN')
    rel = file_abs[len(repo_abs) + 1:]
    native._require(rel and '..' not in Path(rel).parts, 'PREFLIGHT_MODULE_ORIGIN')
    return rel


def read_repo_file(repo, rel: str, maximum: int = MAX_PROC_BYTES) -> bytes:
    parts = Path(rel).parts
    native._require(parts and all(p not in {'', '.', '..'} and '/' not in p for p in parts),
                    'PREFLIGHT_MODULE_ORIGIN')
    dir_fd = open_directory(repo)
    descriptors = [dir_fd]
    try:
        for part in parts[:-1]:
            descriptors.append(os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                       dir_fd=descriptors[-1]))
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptors[-1])
        descriptors.append(fd)
        info = os.fstat(fd)
        native._require(stat.S_ISREG(info.st_mode) and 0 < info.st_size <= maximum,
                        'PREFLIGHT_MODULE_ORIGIN')
        raw = bytearray()
        while len(raw) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        native._require(len(raw) == info.st_size, 'PREFLIGHT_MODULE_ORIGIN')
        return bytes(raw)
    finally:
        for fd in reversed(descriptors):
            os.close(fd)


def collect_on_disk_provenance(git, modules, *, mode=None) -> dict:
    """On-disk provenance only; not an attestation of previously loaded code."""
    head = git._head()
    native._require(type(head) is str and _OID.fullmatch(head), 'PREFLIGHT_PRODUCER_HEAD')
    repo = Path(git.repo)
    found = []
    native._require(mode is None or (type(mode) is str and mode in _MODE), 'PREFLIGHT_MODE_DRIFT')
    names = MODULE_NAMES + (APPEND_MODULE_NAMES if mode == 'APPEND_CURRENT_MEMBER' else ())
    for name in names:
        mod = modules.get(name)
        if name == 'scripts.publish_company_disclosure':
            main = modules.get('__main__')
            if getattr(getattr(main, '__spec__', None), 'name', None) == name:
                mod = main  # python -m executes this module under __main__.
        native._require(mod is not None, 'PREFLIGHT_MODULE_ORIGIN')
        file_path = getattr(mod, '__file__', None)
        native._require(type(file_path) is str and file_path, 'PREFLIGHT_MODULE_ORIGIN')
        if file_path.endswith('.pyc'):
            try:
                file_path = importlib.util.source_from_cache(file_path)
            except ValueError:
                raise native.DisclosureError('PREFLIGHT_MODULE_ORIGIN') from None
        rel = repo_relative(repo, file_path)
        found.append((name, rel))
    native._require(found, 'PREFLIGHT_MODULE_ORIGIN')
    objects = git._objects(head, tuple(rel for _, rel in found))
    blobs = git._read(objects)
    records = []
    for name, rel in found:
        on_disk = hashlib.sha256(read_repo_file(repo, rel)).hexdigest()
        blob = hashlib.sha256(blobs[rel]).hexdigest()
        native._require(on_disk == blob, 'PREFLIGHT_MODULE_ORIGIN')
        records.append({'module': name, 'path': rel, 'sha256': on_disk, 'blob_sha256': blob})
    return {
        'kind': 'on_disk_provenance',
        'premises': ['fresh_trusted_interpreter', 'qualified_deployment'],
        'attestation': 'on_disk_source_hashes_match_committed_blobs',
        'not_claimed': 'exhaustive_loaded_code_attestation',
        'head': head,
        'modules': records,
    }


def bind_prepared_intent(source, intent, expected, *, same_manifest=None) -> object:
    """Re-read source just before reservation; bind the single prepared intent."""
    append = type(intent) is dict and intent.get('schema') == 'company_intelligence.native_publication_intent/v2'
    native._closed(intent, {'schema', 'manifest', 'manifest_reference',
                            'expected_current_version', 'expected_current_sha256', 'mode'}
        | ({'prior_manifest', 'preserved_members', 'collection', 'collection_reference'} if append else set()))
    native._require(intent['schema'] == ('company_intelligence.native_publication_intent/v2' if append
        else 'company_intelligence.native_publication_intent/v1'),
                    'PREFLIGHT_SOURCE_DRIFT')
    snapshot = source.snapshot()
    native._require(snapshot.code_version == expected['code_version']
                    == intent['manifest']['code_version'], 'PREFLIGHT_SOURCE_DRIFT')
    mode = 'APPEND_CURRENT_MEMBER' if append else ('PROMOTE_CURRENT' if snapshot.dataset_status == 'PRODUCED' else 'STAGE_MEMBERS')
    native._require(not append or (snapshot.dataset_status == 'PRODUCED' and same_manifest is not None),
                    'PREFLIGHT_APPEND_BINDING_REQUIRED')
    native._require(mode == expected['mode'] == intent['mode'], 'PREFLIGHT_MODE_DRIFT')
    native._require(intent['manifest_reference']['sha256']
                    and type(intent['manifest_reference']['sha256']) is str, 'PREFLIGHT_SOURCE_DRIFT')
    if same_manifest is not None:
        native._require(same_manifest(snapshot, intent), 'PREFLIGHT_SOURCE_DRIFT')
    return snapshot


def assemble_evidence(*, expected, process, api, provenance, intent, mounts,
                      root_records, captured_at, revalidated_at) -> dict:
    root = str(PRODUCTION_ROOT)
    covered = {}
    for key in ROOT_KEYS:
        mount = exact_mount(mounts, root_records[key]['mount_id'])
        covered[key] = {'mountpoint': mount['mountpoint'], 'options': mount['options'],
                        'super_options': mount['super_options'],
                        'mount_id': mount['mount_id'], **root_records[key]}
    evidence = {
        'schema': EVIDENCE_SCHEMA,
        'captured_at': captured_at,
        'revalidated_at': revalidated_at,
        'expected_deployment': expected,
        'premises': ['fresh_trusted_interpreter', 'qualified_deployment'],
        'not_claimed': 'exhaustive_loaded_code_attestation',
        'producer': process,
        'api': {
            'pid': api['pid'], 'starttime': api['starttime'],
            'mountnamespace': api['mountnamespace'], 'cgroup': api['cgroup'],
            'unit': api['unit'], 'invocation_id': api['invocation_id'],
            'qualified_runtime_source': api['qualified_runtime_source'],
        },
        'root': root,
        'roots': covered,
        'on_disk_provenance': provenance,
        'intent_binding': {
            'code_version': intent['manifest']['code_version'],
            'mode': intent['mode'],
            'manifest_sha256': intent['manifest_reference']['sha256'],
        },
        'limits': {
            'census_max_age_seconds': expected['census_max_age_seconds'],
            'mount_rw_does_not_promise_future_writes': True,
        },
    }
    evidence_bytes(evidence)
    return evidence


def finalize_gate(expected, capture, source, intent, mounts, *, now: str | None = None,
                  process=None, api=None, provenance=None, modules=None,
                  same_manifest=None) -> dict:
    process = process if process is not None else read_process_identity('self')
    native._require(process['pid'] == capture['process']['pid']
                    and process['starttime'] == capture['process']['starttime']
                    and process['exe'] == capture['process']['exe']
                    and process['cwd'] == capture['process']['cwd'],
                    'PREFLIGHT_PROCESS_CHANGED')
    native._require(process['mountnamespace'] == capture['process']['mountnamespace'],
                    'PREFLIGHT_NAMESPACE_CHANGED')
    native._require(process['mountnamespace'] != expected['api_census']['mountnamespace'],
                    'PREFLIGHT_NAMESPACE_SHARED')
    native._require(process['uid'] == expected['producer']['uid'] == capture['process']['uid'],
                    'PREFLIGHT_PRODUCER_UID')
    native._require(os.path.abspath(expected['producer']['repo'])
                    == os.path.abspath(source.git.repo), 'PREFLIGHT_PRODUCER_REPO')
    bind_prepared_intent(source, intent, expected, same_manifest=same_manifest)
    if provenance is None:
        if expected['mode'] == 'APPEND_CURRENT_MEMBER':
            provenance = collect_on_disk_provenance(source.git, modules if modules is not None else {}, mode=expected['mode'])
        else:
            provenance = collect_on_disk_provenance(source.git, modules if modules is not None else {})
    native._require(source.git._head() == provenance['head'] == expected['code_version']
                    == intent['manifest']['code_version'] == capture['provenance']['head'],
                    'PREFLIGHT_SOURCE_DRIFT')
    api = api if api is not None else revalidate_api_census(expected['api_census'])
    # A namespace ID may stay the same while its mount table changes. Re-read
    # mounts and every provisioned root after preparation, never reuse the
    # pre-prepare observation as the final write-boundary qualification.
    mounts = read_mountinfo()
    roots = qualify_roots(expected['root'], expected['producer']['uid'], mounts)
    if 'roots' in capture:
        native._require(roots == capture['roots'], 'PREFLIGHT_ROOT_CHANGED')
    if now is None:
        now = datetime.now(timezone.utc).isoformat()
    evaluate_census_time(expected, capture['captured_at'], now)
    return assemble_evidence(
        expected=expected, process=process, api=api, provenance=provenance, intent=intent,
        mounts=mounts, root_records=roots, captured_at=capture['captured_at'], revalidated_at=now)
