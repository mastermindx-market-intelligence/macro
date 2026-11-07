"""Synthetic Linux/sshd syscall data, never actual native authentication.

The real peer parser, filesystem guards, kernel parsers, journal joins, factory,
nominal identity and rechecks run. Only syscall/process/command primitives are
substituted. No grant, policy, successful runtime or peer capability is supplied.
"""
import base64
from hashlib import sha256
import json
import os
from types import SimpleNamespace

import pytest

from engine.research_factory import market_memory_e0_native_peer as peer


@pytest.fixture
def native_peer_primitives(monkeypatch):
    blob = b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + bytes(range(32))
    key = ('restrict,command="' + peer.COMMAND + '",no-port-forwarding,no-agent-forwarding,'
        'no-X11-forwarding,no-pty,no-user-rc ssh-ed25519 ').encode() + base64.b64encode(blob) + b'\n'
    fingerprint = 'SHA256:' + base64.b64encode(sha256(blob).digest()).rstrip(b'=').decode()
    image = b'\x7fELF synthetic native image; no executable or real service'
    nodes = {}
    paths = ['/', '/etc', '/etc/macro', '/etc/macro/market-memory-e0', peer.KEY_FILE, '/usr/sbin/sshd']
    for index, path in enumerate(paths):
        is_file = path in (peer.KEY_FILE, '/usr/sbin/sshd')
        body = key if path == peer.KEY_FILE else image if is_file else b''
        nodes[path] = {'body': body, 'meta': SimpleNamespace(st_dev=1, st_ino=index + 1,
            st_mode=(0o100600 if path == peer.KEY_FILE else 0o100755 if is_file else 0o40755),
            st_uid=0, st_nlink=1, st_size=len(body), st_mtime_ns=1000000, st_ctime_ns=1000000)}
    fds, next_fd = {}, [10]
    def fs_open(path, flags, dir_fd=None):
        if dir_fd is not None:
            parent = fds[dir_fd]['path']; path = parent.rstrip('/') + '/' + path
        assert path in nodes
        next_fd[0] += 1; fd = next_fd[0]
        fds[fd] = {'path': path, 'offset': 0}; return fd
    def fs_fstat(fd): return nodes[fds[fd]['path']]['meta']
    def fs_stat(path, *, dir_fd=None, follow_symlinks=True):
        if path == '/proc/100/exe': path = '/usr/sbin/sshd'
        elif dir_fd is not None: path = fds[dir_fd]['path'].rstrip('/') + '/' + path
        return nodes[path]['meta']
    def fs_read(fd, count):
        entry = fds[fd]; start = entry['offset']; result = nodes[entry['path']]['body'][start:start+count]
        entry['offset'] += len(result); return result
    def proc_stat(pid, parent):
        fields = ['S', str(parent)] + ['0'] * 17 + ['100']
        return (str(pid) + ' (fixture) ' + ' '.join(fields)).encode()
    kernel = {'/proc/200/stat': proc_stat(200,100), '/proc/100/stat': proc_stat(100,1),
        '/proc/200/cmdline': b'/opt/macro-api/.venv/bin/python\x00-I\x00-B\x00/opt/macro/scripts/market_memory_e0_native_issuer.py\x00',
        '/proc/200/status': b'Uid:\t0\t0\t0\t0\n', '/proc/100/status': b'Uid:\t0\t0\t0\t0\n',
        '/proc/sys/kernel/random/boot_id': b'11111111-1111-1111-1111-111111111111\n',
        '/proc/100/net/tcp': b'header\n0: 0100007F:0016 0200007F:C350 01 0 0 0 0 0 123\n'}
    connection = '127.0.0.2 port 50000'
    messages = ['Connection from ' + connection + ' on 127.0.0.1 port 22 rdomain ""',
        'Accepted key ED25519 ' + fingerprint + ' found at ' + peer.KEY_FILE + ':1',
        'Accepted publickey for root from ' + connection + ' ssh2: ED25519 ' + fingerprint,
        "Starting session: forced-command (key-option) '" + peer.COMMAND + "' for root from " + connection + ' id 0']
    rows = [{'_PID':'100','_UID':'0','_EXE':'/usr/sbin/sshd','_BOOT_ID':'1'*32,
        '__MONOTONIC_TIMESTAMP':str(2000000+i*1000),'__REALTIME_TIMESTAMP':str(2000000+i*1000),
        'MESSAGE':message} for i,message in enumerate(messages)]
    config = {'usedns':'no','strictmodes':'yes','permituserenvironment':'no',
        'authorizedkeyscommand':'none','authorizedkeysfile':peer.KEY_FILE,'forcecommand':'none',
        'pubkeyauthentication':'yes','acceptenv':'LANG LC_*'}
    calls = []
    def run(argv, limit):
        calls.append(tuple(argv))
        if argv[0] == '/usr/bin/journalctl': return b'\n'.join(json.dumps(r).encode() for r in rows)
        assert argv[:3] == ['/usr/sbin/sshd','-T','-C'] and len(argv)==4
        assert argv[3] == 'user=root,host=127.0.0.2,addr=127.0.0.2,laddr=127.0.0.1,lport=22'
        return ''.join(k+' '+v+'\n' for k,v in config.items()).encode()
    monkeypatch.setattr(peer,'_platform',lambda:'linux');monkeypatch.setattr(peer,'_uid',lambda:0)
    monkeypatch.setattr(peer,'_pid',lambda:200);monkeypatch.setattr(peer,'_ppid',lambda:100)
    monkeypatch.setattr(peer,'_fs_open',fs_open);monkeypatch.setattr(peer,'_fs_read',fs_read)
    monkeypatch.setattr(peer,'_fs_close',lambda fd:fds.pop(fd))
    monkeypatch.setattr(peer,'_fs_fstat',fs_fstat);monkeypatch.setattr(peer,'_fs_stat',fs_stat)
    monkeypatch.setattr(peer,'_kernel_read',lambda path,limit=65536:kernel[path])
    monkeypatch.setattr(peer,'_kernel_fds',lambda pid:['3'])
    monkeypatch.setattr(peer,'_kernel_link',lambda path:'/usr/bin/python3.12' if path=='/proc/200/exe' else '/usr/sbin/sshd' if path.endswith('/exe') else 'socket:[123]')
    monkeypatch.setattr(peer,'_run',run)
    monkeypatch.setattr(peer,'_version_run',lambda *a,**k:SimpleNamespace(returncode=0,stdout=b'',stderr=b'OpenSSH_9.6p1 Ubuntu-SYNTHETIC\n'))
    # Kernel tick frequency is fixture data, not the Mac's Linux substitute.
    monkeypatch.setattr(peer,'_ticks_per_second',lambda:100)
    monkeypatch.setattr(peer,'_runtime_path',lambda:'/usr/bin/python3.12')
    return {'nodes':nodes,'kernel':kernel,'rows':rows,'config':config,'calls':calls,'fingerprint':fingerprint}


@pytest.fixture
def native_peer_capability(native_peer_primitives):
    return peer.observe_current_broker_service()
