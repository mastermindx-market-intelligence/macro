from pathlib import Path
import datetime
import hashlib
import json
import os
import re
import stat
import subprocess
import sys

A = 'e45bde2cac07ac3b29285ff70c40d68900fad62c'
R = '93e303cc32566e72fb086af6d04ba3aa41866c5c'
OWNER_SHA = 'c6759cc653e0f19102a015ec52842795bde24eb85766d2e73f3024b4eefe409d'
BETA = Path('/opt/terminal/beta')
APP = BETA / 'terminal'
LOCK = Path('/opt/terminal/.terminal-build-resource.lock')
SOURCE_RECORD = Path('/var/lib/mastermind-terminal-beta/source-provisioned/source-provisioned-' + A + '-efb499b6d0108d69.json')
PROD = {'pid': '2336355', 'start_monotonic': '7552363880288',
        'deployment_sha': '50a8c01553ee92731a53dfcff36256308cfb5f0e',
        'next_build_id': 'build-TfctsWXpff2fKS',
        'owner_sha256': '6d05d3d5745e0e0a29262c89ba61cf881c2605201cce5b0fc85a52bde0e42ec8',
        'caddy_sha256': '6de6d01adbe40a5c71f8d80472f3d0deca5a02a99c4e27779984b3bff4d274b1'}


def need(value, message):
    if not value:
        raise RuntimeError('ENTRY REFUSED: ' + message)


def signature(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_uid, s.st_gid, s.st_nlink,
            s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def metadata(path, s):
    return {'path': str(path), 'dev': s.st_dev, 'ino': s.st_ino,
            'mode': oct(stat.S_IMODE(s.st_mode)), 'uid': s.st_uid,
            'gid': s.st_gid, 'nlink': s.st_nlink, 'size': s.st_size}


def directory(path, exact_mode=None):
    path = Path(path)
    need(path.resolve(strict=True) == path, 'directory alias: ' + str(path))
    s = path.lstat()
    need(stat.S_ISDIR(s.st_mode) and s.st_uid == 0 and not stat.S_IMODE(s.st_mode) & 0o022,
         'directory custody: ' + str(path))
    if exact_mode is not None:
        need(s.st_gid == 0 and stat.S_IMODE(s.st_mode) == exact_mode, 'private directory mode')
    return metadata(path, s)


def regular(path, maximum=4 * 1024 * 1024):
    path = Path(path)
    before = path.lstat()
    need(stat.S_ISREG(before.st_mode) and before.st_uid == 0 and
         not stat.S_IMODE(before.st_mode) & 0o022 and 0 < before.st_size <= maximum,
         'file custody: ' + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        need(signature(opened) == signature(before), 'file changed while opening')
        data = bytearray()
        while len(data) <= maximum:
            chunk = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        need(len(data) == opened.st_size and len(data) <= maximum, 'file size changed')
        need(signature(opened) == signature(os.fstat(fd)) == signature(path.lstat()),
             'file changed while reading')
    finally:
        os.close(fd)
    m = metadata(path, opened)
    m['sha256'] = hashlib.sha256(data).hexdigest()
    return bytes(data), m


def digest(path):
    return regular(path)[1]['sha256']


def value(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=45)
    need(p.returncode == 0, 'read failed: ' + repr(args) + ': ' + p.stderr.strip())
    return p.stdout.strip()


def service(name):
    text = value(['systemctl', 'show', name, '--property=ActiveState,SubState,UnitFileState,MainPID,ExecMainStartTimestampMonotonic'])
    return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)


def release_owners():
    matches = []
    checked = 0
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            raw = (p / 'cmdline').read_bytes()
            if not raw:
                continue
            need(len(raw) <= 1024 * 1024, 'process argument read exceeds bound')
            args = [os.fsdecode(x) for x in raw.rstrip(b'\0').split(b'\0')]
            executable = os.path.basename(os.readlink(p / 'exe'))
            checked += 1
            script = None
            if executable in {'bash', 'dash', 'sh', 'zsh'}:
                for arg in args[1:]:
                    if arg == '--':
                        continue
                    if arg.startswith('-'):
                        if arg.startswith('--') or 'c' in arg[1:]:
                            break
                        continue
                    script = arg
                    break
            elif os.path.basename(args[0]) == 'terminal-build.sh':
                script = args[0]
            if script and re.fullmatch(r'(?:[A-Za-z0-9_.-]+/|/)*terminal-build\.sh', script):
                matches.append({'pid': int(p.name), 'script': script, 'executable': executable})
        except FileNotFoundError:
            continue
        except ProcessLookupError:
            continue
    return {'complete': True, 'checked_processes': checked, 'matches': matches,
            'scope': 'Executable/script argv of ordinary shell release owners; no whole-command substring matching or environment read'}


def main():
    need(os.geteuid() == 0, 'deployment principal must be root')
    need(len(sys.argv) == 2, 'exact private owner artifact argument required')
    script = Path(sys.argv[1])
    need(script.name == 'terminal-build.sh' and script.parent.parent == Path('/root') and
         re.fullmatch(r'mastermind-beta-owner-93e303cc-[A-Za-z0-9_-]+', script.parent.name),
         'artifact is outside this protected entrance')
    private = directory(script.parent, 0o700)
    data, owner = regular(script)
    need(owner['gid'] == 0 and owner['mode'] == '0o700' and owner['nlink'] == 1 and
         len(data) == 207242 and owner['sha256'] == OWNER_SHA, 'protected script identity')
    need(sorted(x.name for x in script.parent.iterdir()) == ['terminal-build.sh'], 'script-only fallback boundary')
    need(digest('/opt/terminal/terminal-build.sh') == PROD['owner_sha256'], 'global owner changed')
    need(digest('/etc/caddy/Caddyfile') == PROD['caddy_sha256'], 'Caddy changed')
    need(digest('/usr/local/sbin/terminal-volume-guard') ==
         '1a7e39a4188d9dcfd55907e741a1b27850ed65835f4525cc6bc3a48eca122de9', 'volume guard changed')
    need(not os.path.lexists('/etc/terminal-storage-maintenance'), 'storage maintenance active')
    lock = directory(LOCK, 0o700)
    lock_entries = sorted(x.name for x in LOCK.iterdir())
    need(not lock_entries and not os.path.lexists(LOCK / 'hold'), 'shared resource owner or archive present')
    owners = release_owners()
    need(not owners['matches'], 'another release owner is executing')
    prod = service('terminal.service')
    expected_prod = {'ActiveState': 'active', 'SubState': 'running', 'UnitFileState': 'enabled',
                     'MainPID': PROD['pid'], 'ExecMainStartTimestampMonotonic': PROD['start_monotonic']}
    need(prod == expected_prod, 'production service identity changed')
    beta_service = service('terminal-beta.service')
    need(all(beta_service.get(k) == v for k, v in {'ActiveState': 'inactive', 'SubState': 'dead',
         'UnitFileState': 'disabled', 'MainPID': '0'}.items()), 'beta lifecycle changed')
    need(regular('/opt/terminal/terminal/.deployment-id', 512)[0].decode().strip() == PROD['deployment_sha'] and
         regular('/opt/terminal/terminal/.next/BUILD_ID', 512)[0].decode().strip() == PROD['next_build_id'],
         'production deployment or build changed')
    need(value(['git', '-C', '/opt/terminal/.gitsrc-beta', 'rev-parse', 'HEAD']) == A, 'beta source changed')
    need(digest('/opt/terminal/.gitsrc-beta/ops/terminal_source_audit.beta.json') ==
         '9b6c95d2f3134f37640312106fcf10dd2be5a1d4c01002e959ac5cb71614fae9', 'canonical A policy changed')
    directory(BETA)
    directory(SOURCE_RECORD.parent)
    pointer = BETA / '.source-provisioned'
    pointer_stat = pointer.lstat()
    need(stat.S_ISLNK(pointer_stat.st_mode) and pointer_stat.st_uid == 0 and
         os.readlink(pointer) == str(SOURCE_RECORD), 'source receipt pointer changed')
    source_bytes, source_meta = regular(SOURCE_RECORD)
    need(source_meta['sha256'] == '9aac8ec8c132eecf4d2664d8f1e18e8a6bffce5f6d7176e4021b15d6d953cfa4', 'source receipt changed')
    source = json.loads(source_bytes)
    need(source['accepted_runtime'] is False and source['rollback_baseline'] is False, 'source receipt is not source-only')
    need(not os.path.lexists(BETA / '.runtime-accepted') and not os.path.lexists(BETA / '.release-pending'), 'canonical lifecycle pointer appeared')
    need(regular(APP / '.deployment-id', 512)[0].decode().strip() == A and
         not os.path.lexists(APP / '.next/BUILD_ID'), 'partial application identity changed')
    need(not any(x.name.startswith('.stage.') for x in BETA.iterdir()), 'beta stage remains')
    pair = []
    for name, inode in [('esbuild/bin/esbuild', 336939), ('@esbuild/linux-x64/bin/esbuild', 330749)]:
        path = APP / 'node_modules' / name
        s = path.lstat()
        actual = [s.st_dev, s.st_ino, s.st_nlink, s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode), s.st_size]
        need(stat.S_ISREG(s.st_mode) and actual == [2048, inode, 1, 0, 0, 0o744, 9707520], 'dependency partial-state identity changed')
        pair.append(metadata(path, s))
    space = {p: os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in ['/', '/opt/terminal']}
    need(space['/'] >= 1100000000 and space['/opt/terminal'] >= 16000000000, 'reviewed capacity floor no longer holds')
    receipt = {'schema': 'mastermind.attended.beta_protected_entry.v2',
               'entry_fenced_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
               'protected_owner_R': R, 'application_A': A, 'protected_owner_artifact': str(script),
               'artifact': owner, 'artifact_parent': private, 'production_entry': PROD,
               'production_service': prod, 'beta_service': beta_service,
               'source_receipt': source_meta, 'dependency_pair': pair, 'space': space,
               'shared_resource_parent': lock, 'shared_resource_parent_entries': lock_entries,
               'release_owners': owners, 'canonical_pointer_checked': '.runtime-accepted',
               'owner_invoked_at_receipt': False,
               'next_effect': 'exec exact protected owner once with canonical --target beta --bootstrap --target-sha A; owner retains all locks, admission, publication and cleanup authority'}
    print('PROTECTED_R_ENTRY_FENCE ' + json.dumps(receipt, sort_keys=True), flush=True)
    os.execv(str(script), [str(script), '--target', 'beta', '--bootstrap', '--target-sha', A])


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('PROTECTED_R_ENTRY_REFUSED ' + json.dumps({'error': str(exc), 'owner_invoked': False,
              'at': datetime.datetime.now(datetime.timezone.utc).isoformat()}, sort_keys=True), flush=True)
        raise SystemExit(65)
