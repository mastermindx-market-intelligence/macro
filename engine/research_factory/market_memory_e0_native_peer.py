"""Fixed Linux machine-service observation, not recipient or study admission.

The v2 composed profile authenticates the dedicated protected M2 service key
and Linux key-option/process lineage. The qualified installed M2 root owner is
part of the trusted implementation: its fixed SSH client supplies no untrusted
environment/options. This is NOT standalone environment confinement for arbitrary
holders of the key, and does not prove a daemon's historical configuration.

Native admin grants must explicitly authorize this profile and bind the observed
executable/version/parser. Actual M2 Control, sole protected invocation and key
custody require separate installed acceptance; neither a caller flag nor these
bytes prove them. No key enrollment or configuration change occurs here.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import weakref

COMMAND = '/opt/macro-api/.venv/bin/python -I -B /opt/macro/scripts/market_memory_e0_native_issuer.py'
KEY_FILE = '/etc/macro/market-memory-e0/authorized_keys'
PROFILE = 'memory.e0.protected_m2_service_ssh.v2'
JOURNAL_PROFILE = 'memory.e0.openssh_authenticated_key_option_journal.v1'
_TOKEN = object()
_ISSUED = weakref.WeakKeyDictionary()
_pid, _ppid, _uid = os.getpid, os.getppid, os.geteuid
_fs_open, _fs_read, _fs_close = os.open, os.read, os.close
_fs_fstat, _fs_stat = os.fstat, os.stat
_version_run = subprocess.run
_platform = lambda: sys.platform
_ticks_per_second = lambda: os.sysconf('SC_CLK_TCK')
_runtime_path = lambda: os.path.realpath('/opt/macro-api/.venv/bin/python')


class NativePeerError(ValueError):
    """Stable refusal only; never export raw journal, key or process contents."""


def _need(value, reason='broker_authentication_unqualified'):
    if not value:
        raise NativePeerError(reason)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _secure_key_file():
    """Fixed path, held nonsymlink root-controlled ancestors and exact leaf."""
    parts = KEY_FILE.lstrip('/').split('/')
    held, records = [], []
    try:
        current = _fs_open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        held.append(current)
        root = _fs_fstat(current)
        _need(root.st_uid == 0 and not root.st_mode & 0o022)
        records.append(_identity(root))
        for part in parts[:-1]:
            fd = _fs_open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                         dir_fd=current)
            info = _fs_fstat(fd)
            _need(info.st_uid == 0 and not info.st_mode & 0o022)
            held.append(fd)
            records.append(_identity(info))
            current = fd
        leaf = _fs_open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                       dir_fd=current)
        held.append(leaf)
        info = _fs_fstat(leaf)
        _need(stat.S_ISREG(info.st_mode) and info.st_uid == 0
              and stat.S_IMODE(info.st_mode) == 0o600 and info.st_nlink == 1
              and 1 <= info.st_size <= 16384, 'broker_confinement_unqualified')
        body = _fs_read(leaf, 16385)
        records.append(_identity(info))
        _need(len(body) == info.st_size, 'broker_confinement_unqualified')
        for index, fd in enumerate(held):
            _need(_identity(_fs_fstat(fd)) == records[index], 'broker_confinement_unqualified')
            if index:
                named = _fs_stat(parts[index - 1], dir_fd=held[index - 1], follow_symlinks=False)
                _need(_identity(named) == records[index], 'broker_confinement_unqualified')
        return body, tuple(records)
    except OSError as exc:
        raise NativePeerError('broker_service_not_enrolled') from exc
    finally:
        for fd in reversed(held): _fs_close(fd)


def _fingerprint(body):
    prefix = ('restrict,command="' + COMMAND + '",no-port-forwarding,no-agent-forwarding,'
              'no-X11-forwarding,no-pty,no-user-rc ssh-ed25519 ').encode()
    _need(type(body) is bytes and body.startswith(prefix) and body.endswith(b'\n')
          and body.count(b'\n') == 1, 'broker_confinement_unqualified')
    encoded = body[len(prefix):-1]
    try:
        blob = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise NativePeerError('broker_confinement_unqualified') from exc
    _need(base64.b64encode(blob) == encoded and len(blob) == 51
          and blob[:4] == struct.pack('>I', 11) and blob[4:15] == b'ssh-ed25519'
          and blob[15:19] == struct.pack('>I', 32), 'broker_confinement_unqualified')
    return 'SHA256:' + base64.b64encode(sha256(blob).digest()).rstrip(b'=').decode()


def _kernel_read(path, limit=65536):
    with open(path, 'rb', buffering=0) as stream:
        body = stream.read(limit + 1)
    _need(len(body) <= limit)
    return body


def _kernel_link(path):
    return os.readlink(path)


def _kernel_fds(pid):
    return os.listdir('/proc/' + str(pid) + '/fd')


def _process(pid):
    text = _kernel_read('/proc/' + str(pid) + '/stat', 8192).decode('ascii')
    end = text.rfind(')')
    head, fields = text[:text.index('(')].strip(), text[end + 2:].split()
    _need(head == str(pid) and len(fields) >= 20 and fields[0] not in ('Z', 'X', 'x'))
    parent, ticks = int(fields[1]), int(fields[19])
    status = _kernel_read('/proc/' + str(pid) + '/status', 16384).decode('ascii')
    uid_rows = [row.split()[1:] for row in status.splitlines() if row.startswith('Uid:')]
    _need(uid_rows == [['0', '0', '0', '0']] and ticks > 0)
    return {'pid': pid, 'parent': parent, 'start_ticks': ticks}


def _connection(parent):
    inodes = set()
    for fd in _kernel_fds(parent):
        _need(type(fd) is str and fd.isdecimal())
        try: link = _kernel_link('/proc/' + str(parent) + '/fd/' + fd)
        except FileNotFoundError: continue
        match = re.fullmatch(r'socket:\[(\d+)\]', link)
        if match: inodes.add(match[1])
    matches = []
    table = _kernel_read('/proc/' + str(parent) + '/net/tcp', 1024 * 1024).decode('ascii')
    def address(value):
        raw, port = value.split(':')
        _need(len(raw) == 8)
        raw = bytes.fromhex(raw)
        if sys.byteorder == 'little': raw = raw[::-1]
        return str(ipaddress.IPv4Address(raw)), int(port, 16)
    for line in table.splitlines()[1:]:
        fields = line.split()
        if len(fields) < 10 or fields[3] != '01' or fields[9] not in inodes: continue
        local, remote = address(fields[1]), address(fields[2])
        matches.append({'local_address': local[0], 'local_port': local[1],
                        'remote_address': remote[0], 'remote_port': remote[1], 'inode': fields[9]})
    _need(len(matches) == 1)
    return matches[0]


def _run(argv, limit):
    result = subprocess.run(argv, check=True, stdin=subprocess.DEVNULL, capture_output=True,
                            timeout=4, cwd='/', env={'PATH': '/usr/sbin:/usr/bin:/bin', 'LC_ALL': 'C'})
    _need(not result.stderr and 0 < len(result.stdout) <= limit)
    return result.stdout


def _native_image(parent):
    """Read the fixed executable and bind it to the actual running kernel image."""
    path = '/usr/sbin/sshd'
    fd = _fs_open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = _fs_fstat(fd)
        _need(stat.S_ISREG(before.st_mode) and before.st_uid == 0
              and not before.st_mode & 0o022 and before.st_nlink == 1
              and 0 < before.st_size <= 16 * 1024 * 1024)
        _need((before.st_dev, before.st_ino) == (lambda s: (s.st_dev, s.st_ino))(
            _fs_stat('/proc/' + str(parent) + '/exe')))
        chunks, total = [], 0
        while True:
            chunk = _fs_read(fd, 65536)
            if not chunk: break
            total += len(chunk); _need(total <= 16 * 1024 * 1024); chunks.append(chunk)
        body = b''.join(chunks)
        _need(len(body) == before.st_size and _identity(_fs_fstat(fd)) == _identity(before)
              and _identity(_fs_stat(path, follow_symlinks=False)) == _identity(before))
        # OpenSSH writes -V to stderr; accept only its bounded version output.
        version = _version_run([path, '-V'], stdin=subprocess.DEVNULL, capture_output=True,
            timeout=4, cwd='/', env={'PATH': '/usr/sbin:/usr/bin:/bin', 'LC_ALL': 'C'})
        _need(version.returncode == 0 and not version.stdout and 0 < len(version.stderr) < 512)
        text = version.stderr.decode('ascii').strip()
        _need(text.startswith('OpenSSH_') and '\n' not in text)
        return {'path': path, 'sha256': sha256(body).hexdigest(), 'bytes': len(body), 'version': text}
    finally:
        _fs_close(fd)


def _journal(parent, boot, process, connection, fingerprint, chain):
    body = _run(['/usr/bin/journalctl', '--quiet', '--no-pager', '--output=json',
                 '--lines=256', '_PID=' + str(parent), '_UID=0', '_EXE=/usr/sbin/sshd',
                 '_BOOT_ID=' + boot], 1024 * 1024)
    lines = body.splitlines()
    _need(0 < len(lines) < 256)
    events = []
    hz = _ticks_per_second()
    for line in lines:
        row = json.loads(line)
        _need(type(row) is dict and row.get('_PID') == str(parent) and row.get('_UID') == '0'
              and row.get('_EXE') == '/usr/sbin/sshd' and row.get('_BOOT_ID') == boot)
        stamp, realtime = int(row['__MONOTONIC_TIMESTAMP']), int(row['__REALTIME_TIMESTAMP'])
        if stamp * hz < process['start_ticks'] * 1000000: continue
        _need(type(row.get('MESSAGE')) is str and len(row['MESSAGE']) < 4096)
        events.append((stamp, realtime, row['MESSAGE']))
    _need(events and events == sorted(events, key=lambda x: x[0]))
    remote = connection['remote_address'] + ' port ' + str(connection['remote_port'])
    anchor = 'Connection from ' + remote + ' on ' + connection['local_address'] + ' port ' + str(connection['local_port'])
    starts = [i for i, (_, _, m) in enumerate(events) if m == anchor or m == anchor + ' rdomain ""']
    _need(len(starts) == 1)
    events = events[starts[0]:]
    accepted = 'Accepted publickey for root from ' + remote + ' ssh2: ED25519 ' + fingerprint
    accepted_rows = [i for i, (_, _, m) in enumerate(events) if m.startswith('Accepted publickey ')]
    _need(len(accepted_rows) == 1 and events[accepted_rows[0]][2] == accepted)
    accepted_index = accepted_rows[0]
    location = 'Accepted key ED25519 ' + fingerprint + ' found at ' + KEY_FILE + ':1'
    locations = [i for i, (_, _, m) in enumerate(events) if m.startswith('Accepted key ')]
    _need(locations and all(i < accepted_index and events[i][2] == location for i in locations))
    # Every ancestor and the leaf must retain its historical path identity; an
    # old leaf moved underneath a new directory cannot satisfy this predicate.
    first_location_time = events[locations[0]][1] * 1000
    _need(all(max(record[-2:]) <= first_location_time for record in chain))
    session = "Starting session: forced-command (key-option) '" + COMMAND + "' for root from " + remote + ' id '
    sessions = [i for i, (_, _, m) in enumerate(events) if m.startswith('Starting session: ')]
    _need(len(sessions) == 1 and sessions[0] > accepted_index
          and re.fullmatch(re.escape(session) + r'\d+', events[sessions[0]][2]) is not None)
    forbidden = ('Accepted password ', 'Accepted keyboard-interactive ', 'Partial ', 'Accepted certificate ')
    _need(not any(m.startswith(forbidden) for _, _, m in events))
    # Retain only exact qualified anchors, never an unrelated latest log line.
    return sha256(_canonical([events[0], *[events[i] for i in locations],
                              events[accepted_index], events[sessions[0]]])).hexdigest()


def _native_snapshot():
    _need(_platform() == 'linux' and _uid() == 0)
    pid, parent = _pid(), _ppid()
    own, daemon = _process(pid), _process(parent)
    _need(own['parent'] == parent and _kernel_link('/proc/' + str(parent) + '/exe') == '/usr/sbin/sshd')
    own_executable = _kernel_link('/proc/' + str(pid) + '/exe')
    _need(own_executable == _runtime_path()
          and _kernel_read('/proc/' + str(pid) + '/cmdline', 4096) ==
          b'/opt/macro-api/.venv/bin/python\x00-I\x00-B\x00/opt/macro/scripts/market_memory_e0_native_issuer.py\x00')
    boot = _kernel_read('/proc/sys/kernel/random/boot_id', 64).decode('ascii').strip().replace('-', '')
    _need(re.fullmatch('[0-9a-f]{32}', boot) is not None)
    key, chain = _secure_key_file()
    fingerprint = _fingerprint(key)
    connection = _connection(parent)
    image = _native_image(parent)
    journal = _journal(parent, boot, daemon, connection, fingerprint, chain)
    # Client-input confinement is supplied by the separately qualified protected
    # M2 root client (-F /dev/null, literal argv, minimal fixed environment,
    # root-only separate service key and current Control/socket/source checks).
    # A new -T -C parse cannot establish the running daemon's old environment
    # settings. Do not issue the old standalone profile from such a parse.
    final_key, final_chain = _secure_key_file()
    _need(key == final_key and chain == final_chain and _process(pid) == own and _process(parent) == daemon
          and _pid() == pid and _ppid() == parent and _connection(parent) == connection
          and _kernel_link('/proc/' + str(pid) + '/exe') == own_executable)
    return {'ssh_key_fingerprint': fingerprint, 'restriction_profile': PROFILE, 'forced_command': COMMAND,
            'native_executable': image, 'journal_profile': JOURNAL_PROFILE,
            'observation': {'own': own, 'parent': daemon, 'boot': boot, 'connection': connection,
                'key_file_sha256': sha256(key).hexdigest(), 'path_chain': chain,
                'authentication_sequence_sha256': journal,
                'protected_client_contract': 'mastermind.protected_memory_fixed_ssh_client.v1'}}


class NativeBrokerServiceCapability:
    __slots__ = ('_body', '_seal', '__weakref__')
    def __init__(self, *args, **kwargs): raise NativePeerError('native_peer_factory_required')
    def __copy__(self): raise NativePeerError('native_peer_copy_forbidden')
    def __deepcopy__(self, memo): raise NativePeerError('native_peer_copy_forbidden')
    def __reduce__(self): raise NativePeerError('native_peer_copy_forbidden')


def _body(capability):
    _need(type(capability) is NativeBrokerServiceCapability, 'native_peer_capability_required')
    body = _ISSUED.get(capability)
    _need(type(body) is bytes and getattr(capability, '_seal', None) is _TOKEN
          and type(getattr(capability, '_body', None)) is bytes and capability._body == body,
          'native_peer_capability_required')
    return body


def observe_current_broker_service():
    try:
        body = _canonical(_native_snapshot())
        _need(_canonical(_native_snapshot()) == body)
        cap = object.__new__(NativeBrokerServiceCapability)
        cap._body, cap._seal = body, _TOKEN
        _ISSUED[cap] = body
        return cap
    except NativePeerError: raise
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
        raise NativePeerError('broker_authentication_unqualified') from exc


def require_current_broker_service(capability):
    try:
        body = _body(capability)
        _need(_canonical(_native_snapshot()) == body)
        _need(_body(capability) == body)
    except NativePeerError: raise
    except (OSError, ValueError, KeyError, IndexError, subprocess.SubprocessError) as exc:
        raise NativePeerError('broker_authentication_unqualified') from exc


def broker_service_binding(capability):
    require_current_broker_service(capability)
    body = _body(capability)
    value = json.loads(body)
    return {k: value[k] for k in ('ssh_key_fingerprint', 'restriction_profile', 'forced_command',
                                'native_executable', 'journal_profile')} | {
        'native_observation_sha256': sha256(body).hexdigest()}
